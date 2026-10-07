"""Deterministic ESI 3-5 resource-count estimator.

This node is deliberately narrow: it only runs after emergency/high-risk gates
are negative and after the evidence gate has retrieved authorized ESI resource
rules.  It does not diagnose.  It estimates the *resource-count branch* of the
ESI algorithm so low-acuity presentations do not depend on a model inventing
Decision Point C from free text.
"""

from __future__ import annotations

import re
import unicodedata
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from src.agents.clinical_state_view import ClinicalStateView
from src.agents.guardrails import filter_output_diagnosis
from src.agents.state import AgentState


HIGH_RISK_SYMPTOMS = {
    "chest_pain",
    "dyspnea",
    "syncope",
    "seizure",
    "bleeding",
    "diaphoresis",
    "palpitations",
}


@dataclass(frozen=True)
class ResourceEstimate:
    esi_level: int
    resource_count: int
    resource_category: str
    rationale_vi: str
    cues: tuple[str, ...]


def estimate_resource_count_esi(state: AgentState) -> ResourceEstimate | None:
    """Return a conservative ESI 3/4/5 estimate from confirmed patient facts.

    Preconditions intentionally mirror the clinical safety contract:

    * confirmed intake only;
    * no deterministic/semantic red-flag lock;
    * no unresolved contradictions;
    * no obvious high-risk symptom cluster that belongs to ESI 1/2 logic.
    """

    if state.get("patient_confirmed_intake") is not True:
        return None
    if state.get("is_red_flag") is True:
        return None
    if state.get("current_esi_level") in {1, 2}:
        return None
    if state.get("unresolved_contradictions"):
        return None

    view = ClinicalStateView.from_agent_state(state)
    present_symptoms = set(view.present_symptoms())
    if present_symptoms.intersection(HIGH_RISK_SYMPTOMS):
        return None
    if _has_danger_zone_vitals(state):
        return None

    text = _case_text(state)
    folded = _fold(text)
    severity = _severity(state, view)
    has_active_problem = bool(present_symptoms or view.current_complaints())

    # ESI resource counting is an acuity ladder. Specific resource needs must be
    # considered before zero-resource phrases, because patients commonly deny
    # associated symptoms ("không có triệu chứng đi kèm") while still having a
    # real chief complaint such as abdominal pain. Reading that denial as "no
    # current symptom" is how serious-but-stable abdominal pain fell to ESI 5.
    if _likely_two_or_more_resources(folded, present_symptoms, severity):
        return ResourceEstimate(
            esi_level=3,
            resource_count=2,
            resource_category="two_or_more",
            rationale_vi=(
                "Thông tin hiện tại không cho thấy dấu hiệu tối khẩn, nhưng triệu "
                "chứng có khả năng cần từ hai nguồn lực cấp cứu trở lên để đánh giá."
            ),
            cues=tuple(sorted(_two_resource_cues(folded, present_symptoms, severity))),
        )

    if _likely_one_resource(folded, present_symptoms, severity):
        return ResourceEstimate(
            esi_level=4,
            resource_count=1,
            resource_category="one",
            rationale_vi=(
                "Thông tin hiện tại không gợi ý báo động đỏ; triệu chứng có khả năng "
                "cần một nguồn lực cấp cứu hoặc thủ thuật đơn giản để đánh giá."
            ),
            cues=tuple(sorted(_one_resource_cues(folded, present_symptoms, severity))),
        )

    if (
        not has_active_problem
        and _matches_any(
            folded,
            (
                r"\b(kiem tra|hoi|tu van|xac nhan|lay|xin)\b.*\b(don thuoc|giay|lich hen|ket qua|bao hiem)\b",
                r"\b(tai kham|hen kham)\b.*\b(khong dau|khong sot|khong kho tho|khong trieu chung)\b",
                r"\b(khong co trieu chung|hien khong dau|hien tai khong dau)\b",
            ),
        )
    ):
        return ResourceEstimate(
            esi_level=5,
            resource_count=0,
            resource_category="none",
            rationale_vi=(
                "Thông tin hiện tại không gợi ý dấu hiệu khẩn và có vẻ không cần "
                "nguồn lực cấp cứu ngoài đánh giá ban đầu."
            ),
            cues=("administrative_or_no_current_symptom",),
        )

    if _likely_no_resources(folded):
        return ResourceEstimate(
            esi_level=5,
            resource_count=0,
            resource_category="none",
            rationale_vi=(
                "Thông tin hiện tại mô tả vấn đề rất nhẹ, không gợi ý dấu hiệu "
                "khẩn và có khả năng không cần nguồn lực cấp cứu ngoài đánh giá ban đầu."
            ),
            cues=tuple(sorted(_no_resource_cues(folded))),
        )

    return None


def build_resource_count_proposal(
    state: AgentState,
    estimate: ResourceEstimate,
) -> dict[str, Any] | None:
    """Create a PROPOSED update linked to retrieved resource-count authority."""

    citation_ids = _resource_citation_ids_for_level(state, estimate.esi_level)
    if not citation_ids:
        return None
    citations = [
        citation
        for citation in state.get("turn_rag_citations", [])
        if isinstance(citation, dict) and str(citation.get("id")) in citation_ids
    ]
    evidence = [
        item
        for item in state.get("retrieved_evidence", [])
        if isinstance(item, dict) and str(item.get("citation_id")) in citation_ids
    ]
    criteria = list(
        dict.fromkeys(
            criterion
            for item in evidence
            for criterion in item.get("protocol_criteria", [])
            if str(criterion).strip()
        )
    )
    if not citations or not evidence or not criteria:
        return None

    safe_response = filter_output_diagnosis(estimate.rationale_vi)
    message = {
        "id": str(uuid.uuid4()),
        "sender": "bot",
        "timestamp": datetime.now(UTC).isoformat(),
        "content": safe_response,
        "step": 3,
        "ragCitations": citations,
    }
    return {
        "step": 3,
        "current_esi_level": estimate.esi_level,
        "preliminary_esi_reasoning": safe_response,
        "rag_citations": citations,
        "turn_rag_citations": citations,
        "messages": [message],
        "response": safe_response,
        "response_type": "TRIAGE_PROPOSAL",
        "workflow_phase": "REASONING",
        "decision_status": "PROPOSED",
        "evidence_status": "SUFFICIENT",
        "evidence_sufficiency_outcome": "READY_FOR_REASONING",
        "evidence_authority_status": "AUTHORIZED",
        "uncertainty_reasons": [],
        "matched_protocol_criteria": criteria,
        "resource_count_estimate": {
            "source": "DETERMINISTIC_DECISION_POINT_C",
            "resource_count": estimate.resource_count,
            "resource_category": estimate.resource_category,
            "cues": list(estimate.cues),
        },
        "next_step": "summary_creator",
    }


def _resource_citation_ids_for_level(state: AgentState, esi_level: int) -> set[str]:
    ids: set[str] = set()
    for item in state.get("retrieved_evidence", []):
        if not isinstance(item, dict):
            continue
        text = " ".join(
            str(value)
            for value in (
                item.get("section"),
                item.get("protocol_content"),
                " ".join(item.get("protocol_criteria", [])),
                " ".join(item.get("retrieval_facets", [])),
            )
        )
        folded = _fold(text)
        if "resource" not in folded:
            continue
        if esi_level == 3 and re.search(r"\b(esi level 3|level 3|two or more resources|2 or more resources)\b", folded):
            ids.add(str(item.get("citation_id")))
        elif esi_level == 4 and re.search(r"\b(esi level 4|level 4|one resource)\b", folded):
            ids.add(str(item.get("citation_id")))
        elif esi_level == 5 and re.search(r"\b(esi level 5|level 5|no resources|none maps to esi level 5)\b", folded):
            ids.add(str(item.get("citation_id")))

    if not ids:
        for item in state.get("retrieved_evidence", []):
            if not isinstance(item, dict):
                continue
            facets = {str(facet).upper() for facet in item.get("retrieval_facets", [])}
            if "RESOURCE" in facets:
                ids.add(str(item.get("citation_id")))
    return {item for item in ids if item}


def _case_text(state: AgentState) -> str:
    blueprint = state.get("clinical_blueprint", {}) or {}
    parts: list[str] = [
        str(state.get("query") or ""),
        str(blueprint.get("clinical_context_note") or ""),
    ]
    for key in (
        "chief_complaint",
        "associated_symptoms",
        "onset_time",
        "course",
        "character",
        "location",
        "radiation",
        "recent_procedure",
    ):
        value = blueprint.get(key)
        if isinstance(value, list):
            parts.extend(str(item) for item in value)
        elif value:
            parts.append(str(value))
    view = ClinicalStateView.from_agent_state(state)
    parts.extend(view.current_complaints())
    parts.extend(view.current_associated())
    parts.extend(obs.raw_span for obs in view.recent_events(limit=20) if obs.raw_span)
    return " ".join(parts)


def _severity(state: AgentState, view: ClinicalStateView) -> int | None:
    blueprint = state.get("clinical_blueprint", {}) or {}
    for value in (
        view.current_value("severity_score"),
        blueprint.get("severity_score"),
    ):
        try:
            if value is not None:
                return int(value)
        except (TypeError, ValueError):
            continue
    return None


def _has_danger_zone_vitals(state: AgentState) -> bool:
    blueprint = state.get("clinical_blueprint", {}) or {}
    vitals = blueprint.get("vital_signs") or {}
    if not isinstance(vitals, dict):
        return False
    checks = (
        ("spo2", lambda value: value < 92),
        ("systolic_bp", lambda value: value < 90),
        ("heart_rate", lambda value: value > 130),
        ("respiratory_rate", lambda value: value > 30 or value < 8),
    )
    for key, predicate in checks:
        try:
            value = vitals.get(key)
            if value is not None and predicate(float(value)):
                return True
        except (TypeError, ValueError):
            continue
    return False


def _likely_two_or_more_resources(
    folded: str,
    present_symptoms: set[str],
    severity: int | None,
) -> bool:
    return bool(_two_resource_cues(folded, present_symptoms, severity))


def _likely_no_resources(folded: str) -> bool:
    return bool(_no_resource_cues(folded))


def _no_resource_cues(folded: str) -> set[str]:
    cues: set[str] = set()
    if _matches_any(
        folded,
        (
            r"\b(tray xuoc|xay xat|vet xuoc)\b.*\b(nho|nhe)\b",
            r"\b(nho|nhe)\b.*\b(tray xuoc|xay xat|vet xuoc)\b",
            r"\bchi\s+bi\s+(?:tray xuoc|xay xat|vet xuoc)\s+nho\b",
        ),
    ):
        cues.add("minor_abrasion_self_care")
    if _matches_any(
        folded,
        (
            r"\b(muoi dot|con trung dot)\b.*\b(nhe|hoi ngua|khong sung|khong kho tho)\b",
            r"\b(hoi ngua|ngua nhe)\b.*\b(khong phat ban|khong kho tho|khong sung)\b",
        ),
    ):
        cues.add("minor_itch_or_insect_bite")
    return cues


def _two_resource_cues(
    folded: str,
    present_symptoms: set[str],
    severity: int | None,
) -> set[str]:
    cues: set[str] = set()
    if "abdominal_pain" in present_symptoms and (
        severity is not None and severity >= 4
        or {"vomiting", "fever"}.intersection(present_symptoms)
    ):
        cues.add("abdominal_pain_workup")
    if {"vomiting", "diarrhea"}.intersection(present_symptoms) and _matches_any(
        folded,
        (
            r"\b(nhieu lan|lien tuc|mat nuoc|khat nhieu|tieu chay)\b",
            r"\b(>=?\s*3|3\s*lan|4\s*lan|5\s*lan)\b",
        ),
    ):
        cues.add("gastrointestinal_dehydration_workup")
    if "fever" in present_symptoms and (
        severity is not None and severity >= 4
        or _matches_any(folded, (r"\b38[.,]?[5-9]\b", r"\b39[.,]?\d*\b", r"\bsot cao\b"))
    ):
        cues.add("fever_workup")
    if _matches_any(
        folded,
        (
            r"\b(sung|phu)\b.*\b(bap chan|cang chan|chan)\b.*\b(di xe|bay|nam lau|ngoi lau|12 tieng|duong dai)\b",
            r"\b(bap chan|cang chan)\b.*\b(sung|phu|dau)\b.*\b(di xe|bay|nam lau|ngoi lau|duong dai)\b",
        ),
    ):
        cues.add("unilateral_leg_swelling_workup")
    if _matches_any(folded, (r"\b(nghi gay xuong|bien dang|khong dung duoc|khong di duoc)\b",)):
        cues.add("possible_fracture_workup")
    return cues


def _likely_one_resource(
    folded: str,
    present_symptoms: set[str],
    severity: int | None,
) -> bool:
    return bool(_one_resource_cues(folded, present_symptoms, severity))


def _one_resource_cues(
    folded: str,
    present_symptoms: set[str],
    severity: int | None,
) -> set[str]:
    cues: set[str] = set()
    if _matches_any(folded, (r"\b(vet cat|rach da|vet rach)\b", r"\b(khau|can khau)\b")):
        cues.add("simple_laceration")
    if _matches_any(folded, (r"\b(bong gan|trat|sai khop|dau co chan|lat co chan)\b",)):
        cues.add("minor_musculoskeletal_injury")
    if "sore_throat" in present_symptoms:
        cues.add("sore_throat_possible_test")
    if "rash" in present_symptoms:
        cues.add("rash_simple_treatment")
    if {"vomiting", "nausea", "diarrhea"}.intersection(present_symptoms) and (
        severity is None or severity <= 3
    ):
        cues.add("mild_gastrointestinal_symptom")
    if "fever" in present_symptoms and severity is None:
        cues.add("isolated_fever")
    return cues


def _matches_any(text: str, patterns: tuple[str, ...]) -> bool:
    return any(re.search(pattern, text) for pattern in patterns)


def _fold(text: str) -> str:
    normalized = unicodedata.normalize("NFD", text.lower().replace("đ", "d"))
    return "".join(ch for ch in normalized if unicodedata.category(ch) != "Mn")
