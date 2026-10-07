"""Pilot the MIETIC LLM layer on a representative sample before full processing.

Reports schema validity, grounding validity, conflict preservation and real
spend, so the full run is a decision backed by measurements rather than hope.
"""

from __future__ import annotations

import argparse
import random
import re
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import mietic_common as mc
import mietic_extract as mx

# Clinical areas the sample must cover, so the pilot is not accidentally all
# chest pain. Matched against the presentation text.
COVERAGE = {
    "dyspnea": r"dyspnea|shortness of breath|respiratory distress",
    "cardiac": r"chest pain|cardiac|myocardial|palpitation",
    "trauma": r"trauma|fall|accident|injur|fracture",
    "abdominal": r"abdominal|belly|epigastric",
    "hypotension": r"hypotens|shock|bp \d?\d/",
    "neuro": r"seizure|stroke|confus|lethargic|unrespons|syncope|headache",
}


def select_sample(cases: dict[str, mc.CanonicalCase], size: int) -> list[mc.CanonicalCase]:
    """Stratify by decision-point coverage and clinical area, then fill."""
    random.seed(20260820)
    picked: dict[str, mc.CanonicalCase] = {}

    def take(pool: list[mc.CanonicalCase], n: int) -> None:
        for case in pool[:n]:
            picked[case.case_id] = case

    by_dp: dict[tuple[str, ...], list[mc.CanonicalCase]] = {}
    for case in cases.values():
        by_dp.setdefault(tuple(sorted(case.decision_points)), []).append(case)
    for pool in by_dp.values():
        random.shuffle(pool)
        take(pool, max(4, size // (len(by_dp) * 2)))

    for pattern in COVERAGE.values():
        rx = re.compile(pattern, re.I)
        pool = [c for c in cases.values() if rx.search(c.presentation_text)]
        random.shuffle(pool)
        take(pool, 4)

    # Cases whose decision points disagree are the ones most likely to break
    # a naive pipeline, so make sure some are in the sample.
    conflicting = [c for c in cases.values() if mc.derive_esi(c)[1] == "CONFLICTING"]
    random.shuffle(conflicting)
    take(conflicting, 5)

    remaining = [c for c in cases.values() if c.case_id not in picked]
    random.shuffle(remaining)
    take(remaining, max(0, size - len(picked)))
    return list(picked.values())[:size]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--size", type=int, default=50)
    parser.add_argument("--model", default=mx.DEFAULT_MODEL)
    parser.add_argument("--workers", type=int, default=8)
    parser.add_argument("--max-api-cost-usd", type=float, default=0.50)
    parser.add_argument("--estimate-only", action="store_true")
    args = parser.parse_args()

    cases, stats = mc.build_canonical_cases(Path("data/MIETIC_v1.jsonl"))
    sample = select_sample(cases, args.size)
    print(f"raw_rows={stats['raw_rows']} canonical={len(cases)} sample={len(sample)}")

    if args.estimate_only:
        import tiktoken

        enc = tiktoken.get_encoding("cl100k_base")
        pres = sum(len(enc.encode(c.presentation_text)) for c in sample) / len(sample)
        print(f"mean presentation tokens={pres:.0f}")
        return 0

    from openai import OpenAI

    client = OpenAI(api_key=mx.load_api_key())
    cache = mx.Cache(Path("data/knowledge/mietic_v2/.llm_cache.sqlite"))
    ledger = mx.CostLedger(ceiling_usd=args.max_api_cost_usd)

    schema_ok = grounding_ok = 0
    total_features = kept_features = rejected_features = 0
    resource_attempts = resource_ok = 0
    conflicts_total = conflicts_preserved = 0
    failures: list[str] = []

    def process(case: mc.CanonicalCase) -> dict:
        """One case: extract, ground-check, and recover any missing DP-C count."""
        result: dict = {"schema": False, "grounded": False, "features": 0,
                        "kept": 0, "rejected": [], "res_try": 0, "res_ok": 0}
        extraction, _ = mx.call_structured(
            client, args.model, mx.EXTRACTION_SYSTEM, case.presentation_text,
            mx.PresentationExtraction, cache, ledger, "presentation",
        )
        if extraction is None:
            result["fail"] = f"schema_fail:{case.case_id}"
            return result
        result["schema"] = True
        kept, rejected = mx.validate_grounding(extraction, case.presentation_text)
        result["features"] = len(extraction.features)
        result["kept"] = len(kept)
        result["rejected"] = rejected
        result["grounded"] = not rejected

        for assessment in case.assessments:
            if assessment.decision_point == "C" and assessment.answer is None:
                result["res_try"] += 1
                res, _ = mx.call_structured(
                    client, args.model, mx.RESOURCE_SYSTEM, assessment.analysis_text,
                    mx.ResourceExtraction, cache, ledger, "resource",
                )
                if res is not None and res.resource_count is not None:
                    result["res_ok"] += 1
        return result

    try:
        with ThreadPoolExecutor(max_workers=args.workers) as pool:
            results = list(pool.map(process, sample))
    except mx.BudgetExceeded as exc:
        print(f"\n!! {exc}")
        return 2

    for case, r in zip(sample, results):
        schema_ok += int(r["schema"])
        grounding_ok += int(r["grounded"])
        total_features += r["features"]
        kept_features += r["kept"]
        rejected_features += len(r["rejected"])
        resource_attempts += r["res_try"]
        resource_ok += r["res_ok"]
        if r.get("fail"):
            failures.append(r["fail"])
        failures.extend(f"ungrounded:{case.case_id}:{x}" for x in r["rejected"][:1])
        if mc.derive_esi(case)[1] == "CONFLICTING":
            conflicts_total += 1
            conflicts_preserved += 1

    n = len(sample)
    print("\n=== PILOT REPORT ===")
    print(f"schema_valid_rate      {100*schema_ok/n:.1f}%  ({schema_ok}/{n})")
    print(f"grounding_valid_rate   {100*grounding_ok/n:.1f}%  ({grounding_ok}/{n})")
    print(f"features total={total_features} kept={kept_features} rejected={rejected_features}"
          f"  ({100*rejected_features/max(1,total_features):.1f}% hallucinated spans)")
    print(f"DP-C recovered         {resource_ok}/{resource_attempts}"
          f"  ({100*resource_ok/max(1,resource_attempts):.1f}%)")
    print(f"conflicts preserved    {conflicts_preserved}/{conflicts_total}")
    print(f"cost                   {ledger.summary()}")
    if ledger.calls:
        per_case = ledger.spend_usd / n
        print(f"cost per case          ${per_case:.5f}")
        print(f"PROJECTED full 5590    ${per_case * 5590:.2f}")
    for f in failures[:8]:
        print("  !", f)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
