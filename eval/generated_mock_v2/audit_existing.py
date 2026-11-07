"""Phase 1: audit bộ ca vàng hiện có (30 và 300 ca), chỉ đọc, không sửa gì.

Ghi ``existing_dataset_audit.json`` làm bằng chứng cho dataset_audit_report.md.
Chỉ dùng thư viện chuẩn:

    python eval/generated_mock_v2/audit_existing.py
"""

from __future__ import annotations

import json
import re
import unicodedata
from collections import Counter
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
DATASETS = {
    "golden_30": REPO / "eval/cases/simple_agent_golden_30.jsonl",
    "golden_300": REPO / "eval/cases/simple_agent_golden_300.jsonl",
}
FACT_TOTAL = 243  # simple_agent_fact_targets, xem manifest của bộ 300 ca
TEMPLATE_HINT = re.compile(r"(Đặc điểm|Tình trạng|Mức độ|Hiện diện|Vị trí|Kiểu|Tính chất)[^.:]{0,40}: ")


def _rows(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def _norm(text: str) -> str:
    text = unicodedata.normalize("NFKD", text.lower())
    return re.sub(r"\s+", " ", "".join(ch for ch in text if not unicodedata.combining(ch))).strip()


def audit(rows: list[dict[str, Any]]) -> dict[str, Any]:
    triage = [r for r in rows if r.get("kind") == "triage"]
    openings = Counter(_norm(r["presentation"]["initial_message"]) for r in rows)
    signatures = Counter(json.dumps(sorted(r.get("expected_state", {}).get("facts", {}).items()), default=str) for r in triage)
    key_signatures = Counter(tuple(sorted(r.get("expected_state", {}).get("facts", {}))) for r in triage)
    facts_used = {k for r in triage for k in r["expected_state"]["facts"]}
    unused = {
        "negated_concept_ids": sum(1 for r in triage if r["expected_state"].get("negated_concept_ids")),
        "unknown_fact_ids": sum(1 for r in triage if r["expected_state"].get("unknown_fact_ids")),
        "qualitative_observations": sum(1 for r in triage if r["expected_state"].get("qualitative_observations")),
        "acceptable_answer_variants": sum(1 for r in triage if r["adaptive_dialogue"].get("acceptable_answer_variants")),
        "forbidden_question_target_ids": sum(1 for r in triage if r["adaptive_dialogue"].get("forbidden_question_target_ids")),
        "forbidden_atom_ids": sum(1 for r in triage if r["expected_retrieval"].get("forbidden_atom_ids")),
    }
    default_answer = Counter()
    for r in triage:
        answers = r["adaptive_dialogue"]["answers_by_fact_target"]
        default_answer[sum(1 for v in answers.values() if v == "Tôi chưa rõ thông tin này.")] += 1
    return {
        "records": len(rows),
        "categories": dict(Counter(r["category"] for r in rows)),
        "kinds": dict(Counter(r["kind"] for r in rows)),
        "terminal_actions": dict(Counter(r["expected_decision"].get("terminal_action") for r in rows)),
        "clinical_review_status": dict(Counter(r["clinical_review_status"] for r in rows)),
        "smoke_cases": sum(1 for r in rows if r.get("smoke")),
        "profile_age_years": dict(Counter(r["profile"].get("age_years") for r in rows)),
        "profile_age_band": dict(Counter(r["profile"].get("age_band") for r in rows)),
        "profile_sex": dict(Counter(r["profile"].get("sex") for r in rows)),
        "profile_relationship": dict(Counter(r["profile"].get("relationship_type") for r in rows)),
        "profiles_with_conditions_meds_or_allergies": sum(
            1 for r in rows
            if r["profile"].get("chronic_conditions") or r["profile"].get("daily_medications") or r["profile"].get("allergies")
        ),
        "presentation_style": dict(Counter(r["presentation"].get("style") for r in rows)),
        "contains_temporal_context": sum(1 for r in rows if r["presentation"].get("contains_temporal_context")),
        "openings_with_form_label_template": sum(1 for r in rows if TEMPLATE_HINT.search(r["presentation"]["initial_message"])),
        "exact_duplicate_openings": sum(n for n in openings.values() if n > 1),
        "triage_records_sharing_identical_facts_and_values": sum(n for n in signatures.values() if n > 1),
        "triage_records_sharing_identical_fact_keys": sum(n for n in key_signatures.values() if n > 1),
        "distinct_fact_key_sets": len(key_signatures),
        "distinct_fact_targets_valued": len(facts_used),
        "fact_targets_total_in_corpus": FACT_TOTAL,
        "records_using_optional_fields": unused,
        "default_unknown_answers_per_triage_record": dict(default_answer),
        "distinct_primary_atoms": len({r["expected_retrieval"].get("primary_atom_id") for r in triage} - {None}),
        "opening_length_chars": {
            "min": min(len(r["presentation"]["initial_message"]) for r in rows),
            "median": sorted(len(r["presentation"]["initial_message"]) for r in rows)[len(rows) // 2],
            "max": max(len(r["presentation"]["initial_message"]) for r in rows),
        },
        "example_openings": [r["presentation"]["initial_message"] for r in triage[:3]],
    }


def main() -> None:
    result = {name: audit(_rows(path)) for name, path in DATASETS.items()}
    out = HERE / "existing_dataset_audit.json"
    out.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
