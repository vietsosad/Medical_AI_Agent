from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from eval.simple_runtime.corpus_reader import load_postgres_corpus
from eval.simple_runtime.golden_builder import build_cases, write_dataset
from eval.simple_runtime.schemas import Seed

ROOT = Path(__file__).resolve().parents[1]
CASES = ROOT / "eval" / "cases"
RESULTS = ROOT / "eval" / "results"


def _invalidate_snapshot() -> None:
    """A snapshot belongs to the exact golden checksum that produced it."""
    for name in (
        "current_observations.jsonl", "current_ragas_results.jsonl",
        "current_metrics.json", "current_run_metadata.json", "current_report.md",
    ):
        (RESULTS / name).unlink(missing_ok=True)


def main() -> int:
    parser = argparse.ArgumentParser(description="Build Simple Agent golden cases from the five PostgreSQL corpus tables.")
    parser.add_argument("--count", type=int, default=30)
    parser.add_argument("--output", type=Path, default=CASES / "simple_agent_golden_30.jsonl")
    parser.add_argument("--validate-only", action="store_true")
    args = parser.parse_args()
    if args.count != 30:
        raise SystemExit("This benchmark is intentionally fixed at 30 cases.")
    output = args.output
    manifest = output.with_suffix(".manifest.json")
    seed_path = output.parent / "simple_agent_seed_manifest.json"
    corpus = load_postgres_corpus()
    if args.validate_only:
        if not output.exists() or not manifest.exists():
            raise SystemExit("Golden dataset or manifest is missing; run without --validate-only first.")
        dataset = output.read_bytes()
        expected = json.loads(manifest.read_text(encoding="utf-8"))["dataset_sha256"]
        if hashlib.sha256(dataset).hexdigest() != expected:
            raise SystemExit("Golden dataset SHA256 does not match its manifest.")
        table_drift = json.loads(manifest.read_text(encoding="utf-8")).get("table_fingerprints") != corpus.table_fingerprints
        if table_drift:
            print("Golden dataset validation passed; PostgreSQL has additive or non-selected-row drift. Run the evaluator preflight for selected-row validation.")
        else:
            print("Golden dataset and five-table corpus validation passed.")
        return 0
    # The seed manifest is a reviewed, reproducible selection from the five
    # PostgreSQL tables.  Reuse it when present instead of silently selecting a
    # different atom/concept set on every regeneration.
    seeds = None
    if seed_path.exists():
        raw_seeds = json.loads(seed_path.read_text(encoding="utf-8"))
        seeds = [Seed.model_validate(item) for item in raw_seeds]
    cases, seeds = build_cases(corpus, seeds=seeds)
    write_dataset(cases, seeds, corpus, output=output, seed_path=seed_path, manifest_path=manifest)
    _invalidate_snapshot()
    print(f"Wrote {len(cases)} database-only golden cases to {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
