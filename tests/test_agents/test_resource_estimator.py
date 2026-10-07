from __future__ import annotations

from typing import Any

from src.agents.canonical_state import CanonicalPatientState
from src.agents.nodes.resource_estimator import (
    build_resource_count_proposal,
    estimate_resource_count_esi,
)


def _canonical(*facts: tuple[str, Any, str]) -> dict[str, Any]:
    state = CanonicalPatientState()
    for key, value, raw_span in facts:
        state.record(key, value, raw_span=raw_span)
    return state.to_dict()


def _resource_authority(level: int) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    doc_id = f"ESI-RESOURCE-{level}"
    if level == 3:
        content = "Decision Point C: two or more resources maps to ESI Level 3."
    elif level == 4:
        content = "Decision Point C: one resource maps to ESI Level 4."
    else:
        content = "Decision Point C: no resources maps to ESI Level 5."
    evidence = [
        {
            "citation_id": doc_id,
            "protocol_code": doc_id,
            "section": "Decision Point C",
            "protocol_content": content,
            "protocol_criteria": [f"{doc_id}:facet:RESOURCE"],
            "retrieval_facets": ["RESOURCE"],
        }
    ]
    citations = [
        {
            "id": doc_id,
            "protocolId": doc_id,
            "title": "Decision Point C",
            "sourceType": "validated_protocol",
        }
    ]
    return evidence, citations


def _state(
    *,
    query: str,
    facts: tuple[tuple[str, Any, str], ...],
    authority_level: int,
    severity: int | None = None,
    chief_complaint: list[str] | None = None,
) -> dict[str, Any]:
    evidence, citations = _resource_authority(authority_level)
    blueprint: dict[str, Any] = {"chief_complaint": chief_complaint or [query]}
    if severity is not None:
        blueprint["severity_score"] = severity
    return {
        "query": query,
        "patient_confirmed_intake": True,
        "is_red_flag": False,
        "red_flag_status": "NO_CANDIDATE",
        "canonical_state": _canonical(*facts),
        "clinical_blueprint": blueprint,
        "retrieved_evidence": evidence,
        "turn_rag_citations": citations,
        "evidence_status": "RETRIEVED",
        "evidence_authority_status": "AUTHORIZED",
    }


def test_abdominal_pain_with_workup_cues_maps_to_esi3() -> None:
    state = _state(
        query="Tôi đau bụng quanh rốn từ tối qua, đau 7/10.",
        facts=(
            ("symptom.abdominal_pain", True, "đau bụng quanh rốn"),
            ("severity_score", 7, "đau 7/10"),
        ),
        authority_level=3,
        severity=7,
        chief_complaint=["đau bụng quanh rốn"],
    )

    estimate = estimate_resource_count_esi(state)
    assert estimate is not None
    assert estimate.esi_level == 3
    proposal = build_resource_count_proposal(state, estimate)
    assert proposal is not None
    assert proposal["decision_status"] == "PROPOSED"
    assert proposal["current_esi_level"] == 3
    assert proposal["evidence_status"] == "SUFFICIENT"


def test_denied_associated_symptoms_do_not_turn_abdominal_pain_into_esi5() -> None:
    state = _state(
        query=(
            "Tôi bị đau bụng từ tối qua, đau quanh rốn. Đau bụng tăng dần, "
            "hiện giờ đau mức 7 trên 10. Không có sốt. Không có nôn."
        ),
        facts=(
            ("symptom.abdominal_pain", True, "đau bụng"),
            ("severity_score", 7, "đau mức 7 trên 10"),
            ("associated.khong_co_trieu_chung_di_kem", "không có triệu chứng đi kèm", "không có triệu chứng đi kèm"),
            ("symptom.fever", False, "sốt"),
            ("symptom.vomiting", False, "nôn"),
        ),
        authority_level=3,
        severity=7,
        chief_complaint=["đau bụng", "đau quanh rốn"],
    )

    estimate = estimate_resource_count_esi(state)
    assert estimate is not None
    assert estimate.esi_level == 3
    assert "abdominal_pain_workup" in estimate.cues


def test_simple_laceration_maps_to_esi4() -> None:
    state = _state(
        query="Tôi bị vết cắt nhỏ ở tay, chảy máu ít, cần khâu.",
        facts=(("symptom.rash", True, "vết cắt nhỏ ở tay cần khâu"),),
        authority_level=4,
        chief_complaint=["vết cắt nhỏ ở tay cần khâu"],
    )

    estimate = estimate_resource_count_esi(state)
    assert estimate is not None
    assert estimate.esi_level == 4
    proposal = build_resource_count_proposal(state, estimate)
    assert proposal is not None
    assert proposal["current_esi_level"] == 4


def test_administrative_no_current_symptom_maps_to_esi5() -> None:
    state = _state(
        query="Tôi muốn kiểm tra lại đơn thuốc, hiện không đau, không sốt, không khó thở.",
        facts=(),
        authority_level=5,
        chief_complaint=["kiểm tra lại đơn thuốc"],
    )

    estimate = estimate_resource_count_esi(state)
    assert estimate is not None
    assert estimate.esi_level == 5
    proposal = build_resource_count_proposal(state, estimate)
    assert proposal is not None
    assert proposal["current_esi_level"] == 5


def test_minor_abrasion_self_care_maps_to_esi5() -> None:
    state = _state(
        query="Tôi bị trầy xước nhỏ ở tay, đã rửa sạch, không đau và không chảy máu.",
        facts=(),
        authority_level=5,
        chief_complaint=["trầy xước nhỏ ở tay"],
    )

    estimate = estimate_resource_count_esi(state)
    assert estimate is not None
    assert estimate.esi_level == 5
    assert "minor_abrasion_self_care" in estimate.cues
    proposal = build_resource_count_proposal(state, estimate)
    assert proposal is not None
    assert proposal["current_esi_level"] == 5


def test_minor_abrasion_repeated_short_answer_maps_to_esi5() -> None:
    state = _state(
        query="tôi chỉ bị trầy xước nhỏ ở tay",
        facts=(),
        authority_level=5,
        chief_complaint=["tôi chỉ bị trầy xước nhỏ ở tay"],
    )

    estimate = estimate_resource_count_esi(state)
    assert estimate is not None
    assert estimate.esi_level == 5


def test_resource_estimate_does_not_bypass_missing_authority_citation() -> None:
    state = _state(
        query="Tôi đau bụng quanh rốn từ tối qua, đau 7/10.",
        facts=(
            ("symptom.abdominal_pain", True, "đau bụng quanh rốn"),
            ("severity_score", 7, "đau 7/10"),
        ),
        authority_level=3,
        severity=7,
    )
    state["retrieved_evidence"] = []
    state["turn_rag_citations"] = []

    estimate = estimate_resource_count_esi(state)
    assert estimate is not None
    assert build_resource_count_proposal(state, estimate) is None
