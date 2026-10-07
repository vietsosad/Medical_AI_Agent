"""Build the reproducible canonical MIETIC artifact from raw JSONL.

Deterministic and free: no API calls happen here. Running this twice on the
same input produces byte-identical output, which is what makes the corpus
auditable. The LLM enrichment is applied as a separate, cached pass so that a
model or prompt change never silently rewrites the deterministic base.

Outputs under data/knowledge/mietic_v2/:
    canonical_cases.jsonl   one record per patient case
    conflicts.jsonl         cases whose decision points disagree
    rejected.jsonl          rows that could not be used, with the reason
    processing_report.json  counts and distributions for audit
"""

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path

import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
import mietic_common as mc

OUT_DIR = Path("data/knowledge/mietic_v2")


def build_retrieval_text(case: mc.CanonicalCase) -> str:
    """Representation C: structured, source-grounded, patient facts only.

    The generated analysis is deliberately excluded — embedding it would make
    cases similar because their write-ups are similar, not because the patients
    are. The instruction template is excluded for the same reason.
    """
    lines: list[str] = []
    demo: list[str] = []
    if case.age_years is not None:
        demo.append(
            f"{case.age_years:.0f} years"
            if case.age_years >= 1
            else f"{case.age_years * 12:.0f} months"
        )
    if case.sex:
        demo.append(case.sex)
    if demo:
        lines.append("Patient: " + ", ".join(demo))
    if case.vitals:
        rendered = ", ".join(f"{k} {v}" for k, v in sorted(case.vitals.items()))
        lines.append(f"Vitals: {rendered}")
    lines.append(f"Presentation: {case.presentation_text}")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", default="data/MIETIC_v1.jsonl")
    parser.add_argument("--out-dir", default=str(OUT_DIR))
    args = parser.parse_args()

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    cases, stats = mc.build_canonical_cases(Path(args.input))

    label_counts: Counter[str] = Counter()
    esi_counts: Counter[object] = Counter()
    dp_counts: Counter[str] = Counter()
    parsed_counts: Counter[str] = Counter()

    canonical_path = out_dir / "canonical_cases.jsonl"
    conflicts_path = out_dir / "conflicts.jsonl"

    with canonical_path.open("w", encoding="utf-8") as out, \
         conflicts_path.open("w", encoding="utf-8") as conflicts:
        for case_id in sorted(cases):
            case = cases[case_id]
            candidates, status, validated = mc.derive_esi(case)
            label_counts[status] += 1
            esi_counts[validated] += 1
            dp_counts["+".join(sorted(case.decision_points))] += 1

            assessments = []
            for a in sorted(case.assessments, key=lambda x: x.source_line):
                parsed_counts[f"{a.decision_point}:{a.parse_method}"] += 1
                assessments.append({
                    "decision_point": a.decision_point,
                    "source_record_id": a.source_record_id,
                    "answer": a.answer,
                    "parse_method": a.parse_method,
                    # The analysis is retained as provenance, never as fact.
                    "analysis_text": a.analysis_text,
                })

            retrieval_text = build_retrieval_text(case)
            record = {
                "case_id": case.case_id,
                "presentation_text": case.presentation_text,
                "presentation_sha256": case.presentation_sha256,
                "retrieval_text": retrieval_text,
                "retrieval_text_sha256": mc.sha256(retrieval_text),
                "age_years": case.age_years,
                "age_band": case.age_band,
                "sex": case.sex,
                "vitals": case.vitals,
                "assessments": assessments,
                "candidate_esi_levels": candidates,
                "label_status": status,
                "validated_esi_level": validated,
                "source_record_ids": sorted(case.source_record_ids),
                "source_record_count": len(case.source_record_ids),
                "dataset_version": mc.DATASET_VERSION,
                "parser_version": mc.PARSER_VERSION,
                "document_type": "case_example",
                "retrieval_scope": "CASE_SUPPORT",
                "authority_status": "NOT_PROTOCOL",
            }
            out.write(json.dumps(record, ensure_ascii=False) + "\n")
            if status == "CONFLICTING":
                conflicts.write(json.dumps(record, ensure_ascii=False) + "\n")

    report = {
        "dataset_version": mc.DATASET_VERSION,
        "parser_version": mc.PARSER_VERSION,
        "raw_rows": stats["raw_rows"],
        "malformed_rows": stats["malformed"],
        "canonical_cases": len(cases),
        "decision_point_coverage": dict(dp_counts),
        "assessment_parse_methods": dict(sorted(parsed_counts.items())),
        "label_status": dict(label_counts),
        "validated_esi_distribution": {
            str(k): v for k, v in sorted(esi_counts.items(), key=lambda x: (x[0] is None, x[0]))
        },
        "demographics_coverage": {
            "age": sum(1 for c in cases.values() if c.age_years is not None),
            "sex": sum(1 for c in cases.values() if c.sex),
            "any_vital": sum(1 for c in cases.values() if c.vitals),
        },
    }
    (out_dir / "processing_report.json").write_text(
        json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
