"""Apply the LLM layer to the whole canonical MIETIC corpus.

Reads canonical_cases.jsonl produced by build_mietic_canonical.py, adds
source-grounded clinical features and the DP-C resource counts that prose
defeated, and writes canonical_cases.enriched.jsonl.

Safe to interrupt and re-run: every call is cached by content, so a restart
resumes rather than re-buys. A budget ceiling is enforced in code, not in
documentation — the run aborts before it can cross it.
"""

from __future__ import annotations

import argparse
import json
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from threading import Lock

sys.path.insert(0, str(Path(__file__).resolve().parent))

import mietic_common as mc
import mietic_extract as mx

IN_DIR = Path("data/knowledge/mietic_v2")


def estimate(
    records: list[dict], model: str, cache: mx.Cache | None = None
) -> tuple[int, float]:
    """Price only the calls that would actually be billed.

    Cached calls are excluded: a re-run after a derivation fix re-reads every
    answer from the cache and costs nothing, and a ceiling that counted them
    anyway would block the free path and push you toward raising the limit.
    """
    import tiktoken

    enc = tiktoken.get_encoding("cl100k_base")
    sys_pres = len(enc.encode(mx.EXTRACTION_SYSTEM))
    sys_res = len(enc.encode(mx.RESOURCE_SYSTEM))
    calls = 0
    prompt_tokens = 0

    def billable(content: str, kind: str) -> bool:
        if cache is None:
            return True
        key = mx.Cache.key(content, model, mx.PROMPT_VERSION, kind)
        return cache.get(key) is None

    for record in records:
        if billable(record["presentation_text"], "presentation"):
            prompt_tokens += sys_pres + len(enc.encode(record["presentation_text"]))
            calls += 1
        for a in record["assessments"]:
            if a["decision_point"] == "C" and a["answer"] is None:
                if billable(a["analysis_text"], "resource"):
                    prompt_tokens += sys_res + len(enc.encode(a["analysis_text"]))
                    calls += 1
    rate_in, rate_out = mx.PRICING[model]
    # Completion size measured in the pilot: ~130 for extraction, ~60 for resources.
    completion_tokens = calls * 120
    cost = (prompt_tokens * rate_in + completion_tokens * rate_out) / 1e6
    return calls, cost


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--in-dir", default=str(IN_DIR))
    parser.add_argument("--model", default=mx.DEFAULT_MODEL)
    parser.add_argument("--workers", type=int, default=12)
    parser.add_argument("--max-api-cost-usd", type=float, default=2.00)
    parser.add_argument("--estimate-only", action="store_true")
    parser.add_argument("--limit", type=int, default=0)
    args = parser.parse_args()

    in_dir = Path(args.in_dir)
    records = [
        json.loads(line)
        for line in (in_dir / "canonical_cases.jsonl").read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    if args.limit:
        records = records[: args.limit]

    cache = mx.Cache(in_dir / ".llm_cache.sqlite")
    calls, projected = estimate(records, args.model, cache)
    print(f"cases={len(records)} uncached_calls={calls} projected_cost=${projected:.4f} "
          f"ceiling=${args.max_api_cost_usd:.2f}")
    if projected > args.max_api_cost_usd:
        print("REFUSING: projected cost exceeds the ceiling. Reduce scope or raise the ceiling.")
        return 2
    if args.estimate_only:
        return 0

    from openai import OpenAI

    client = OpenAI(api_key=mx.load_api_key())
    ledger = mx.CostLedger(ceiling_usd=args.max_api_cost_usd)

    progress = {"done": 0, "schema_fail": 0, "rejected": 0, "kept": 0, "dpc": 0}
    progress_lock = Lock()

    def enrich(record: dict) -> dict:
        extraction, _ = mx.call_structured(
            client, args.model, mx.EXTRACTION_SYSTEM, record["presentation_text"],
            mx.PresentationExtraction, cache, ledger, "presentation",
        )
        features: list[dict] = []
        rejected: list[str] = []
        if extraction is None:
            record["extraction_status"] = "SCHEMA_FAILED"
        else:
            kept, rejected = mx.validate_grounding(extraction, record["presentation_text"])
            features = [
                {
                    "concept": f.concept,
                    "present": f.present,
                    "source_span": f.source_span,
                    "source_field": "input",
                }
                for f in kept
            ]
            record["extraction_status"] = "OK"
            record["chief_complaint"] = extraction.chief_complaint
            record["mental_status_altered"] = extraction.mental_status_altered
            record["trauma"] = extraction.trauma
            record["recent_intervention"] = extraction.recent_intervention

        record["clinical_features"] = features
        record["rejected_spans"] = rejected
        record["symptom_concepts"] = sorted({f["concept"] for f in features if f["present"]})

        recovered = 0
        for assessment in record["assessments"]:
            if assessment["decision_point"] == "C" and assessment["answer"] is None:
                result, _ = mx.call_structured(
                    client, args.model, mx.RESOURCE_SYSTEM, assessment["analysis_text"],
                    mx.ResourceExtraction, cache, ledger, "resource",
                )
                if result is not None and result.resource_count is not None:
                    assessment["answer"] = result.resource_count
                    assessment["parse_method"] = "llm"
                    assessment["resources"] = result.resources
                    recovered += 1

        with progress_lock:
            progress["done"] += 1
            progress["kept"] += len(features)
            progress["rejected"] += len(rejected)
            progress["dpc"] += recovered
            if record["extraction_status"] == "SCHEMA_FAILED":
                progress["schema_fail"] += 1
            if progress["done"] % 250 == 0:
                print(f"  {progress['done']}/{len(records)} {ledger.summary()}", flush=True)
        return record

    try:
        with ThreadPoolExecutor(max_workers=args.workers) as pool:
            enriched = list(pool.map(enrich, records))
    except mx.BudgetExceeded as exc:
        print(f"!! {exc}")
        return 2

    # Re-derive ESI now that DP-C answers exist; the label must reflect the
    # answers actually available, not the ones available before enrichment.
    relabelled = {"CONSISTENT": 0, "CONFLICTING": 0, "UNKNOWN": 0}
    esi_dist: dict[str, int] = {}
    for record in enriched:
        case = mc.CanonicalCase(
            case_id=record["case_id"],
            presentation_text=record["presentation_text"],
            presentation_sha256=record["presentation_sha256"],
            age_years=record["age_years"],
            age_band=record["age_band"],
            sex=record["sex"],
            vitals=record["vitals"],
            assessments=[
                mc.TaskAssessment(
                    decision_point=a["decision_point"],
                    source_record_id=a["source_record_id"],
                    source_line=0,
                    answer=a["answer"],
                    parse_method=a["parse_method"],
                    analysis_text=a["analysis_text"],
                )
                for a in record["assessments"]
            ],
        )
        candidates, status, validated = mc.derive_esi(case)
        record["candidate_esi_levels"] = candidates
        record["label_status"] = status
        record["validated_esi_level"] = validated
        record["llm_model"] = args.model
        record["llm_prompt_version"] = mx.PROMPT_VERSION
        relabelled[status] += 1
        esi_dist[str(validated)] = esi_dist.get(str(validated), 0) + 1

    out_path = in_dir / "canonical_cases.enriched.jsonl"
    with out_path.open("w", encoding="utf-8") as out:
        for record in enriched:
            out.write(json.dumps(record, ensure_ascii=False) + "\n")

    report = {
        "cases": len(enriched),
        "model": args.model,
        "prompt_version": mx.PROMPT_VERSION,
        "schema_failures": progress["schema_fail"],
        "features_kept": progress["kept"],
        "spans_rejected": progress["rejected"],
        "dp_c_recovered_by_llm": progress["dpc"],
        "label_status": relabelled,
        "validated_esi_distribution": dict(sorted(esi_dist.items())),
        "api_calls": ledger.calls,
        "api_spend_usd": round(ledger.spend_usd, 4),
    }
    (in_dir / "enrichment_report.json").write_text(
        json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
