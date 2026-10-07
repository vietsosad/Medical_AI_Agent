"""Build auditable Vietnamese, English and sparse retrieval channels from facts."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

from src.agents.nodes.intent_classifier import normalize_vietnamese_text
from src.agents.blueprint_projection import project_blueprint
from src.agents.clinical_state_view import ClinicalStateView
from src.agents.state import AgentState


CONTROLLED_TRANSLATIONS: tuple[tuple[str, str, str], ...] = (
    ("đau ngực", "chest pain", "chest_pain"),
    ("tức ngực", "chest pressure", "chest_pain"),
    ("khó thở", "dyspnea", "dyspnea"),
    ("đau bụng", "abdominal pain", "abdominal_pain"),
    ("đau đầu", "headache", "headache"),
    ("sốt", "fever", "fever"),
    ("buồn nôn", "nausea", "nausea"),
    ("nôn", "vomiting", "vomiting"),
    ("tiêu chảy", "diarrhea", "diarrhea"),
    ("chóng mặt", "dizziness", "dizziness"),
    ("choáng", "lightheadedness", "lightheadedness"),
    ("chảy máu", "bleeding", "bleeding"),
    ("phát ban", "rash", "rash"),
    ("vã mồ hôi", "diaphoresis", "diaphoresis"),
)


@dataclass(frozen=True)
class RetrievalQueryBundle:
    query_vi: str
    query_en: str
    sparse_terms: list[str]
    symptom_cluster: str | None
    degraded_modes: list[str]


def _unique(parts: list[str]) -> list[str]:
    return list(dict.fromkeys(part.strip() for part in parts if part.strip()))


def _controlled_english_and_sparse(texts: list[str]) -> tuple[list[str], list[str]]:
    folded_text = normalize_vietnamese_text(" ".join(texts))
    english: list[str] = []
    sparse: list[str] = []
    for vietnamese, canonical_english, sparse_term in CONTROLLED_TRANSLATIONS:
        if normalize_vietnamese_text(vietnamese) in folded_text:
            english.append(canonical_english)
            sparse.append(sparse_term)
    return _unique(english), _unique(sparse)


def build_retrieval_queries(
    blueprint: dict[str, Any],
    verified_profile_context: dict[str, Any] | None = None,
    symptom_cluster: str | None = None,
) -> RetrievalQueryBundle:
    """Translate only controlled, already-extracted facts; never add a diagnosis."""
    complaints = [str(item) for item in blueprint.get("chief_complaint", [])]
    associated = [str(item) for item in blueprint.get("associated_symptoms", [])]
    onset = str(blueprint.get("onset_time") or "").strip()
    severity = blueprint.get("severity_score")
    radiation = str(blueprint.get("radiation") or "").strip()
    vitals = dict(blueprint.get("vital_signs", {}))
    profile_context = verified_profile_context or {}
    chronic_conditions = [
        str(item).strip()
        for item in profile_context.get("chronic_conditions", [])
        if str(item).strip()
    ]

    vi_parts = [*complaints]
    if onset:
        vi_parts.append(f"khởi phát {onset}")
    if severity is not None:
        vi_parts.append(f"mức độ {severity}/10")
    if radiation:
        vi_parts.append(f"lan {radiation}")
    vi_parts.extend(associated)
    vi_parts.extend(f"bệnh nền đã xác nhận {item}" for item in chronic_conditions)
    for key, value in sorted(vitals.items()):
        if key in {"systolic_bp", "diastolic_bp"}:
            continue
        vi_parts.append(f"{key} {value}")

    english_terms, sparse_terms = _controlled_english_and_sparse(
        [*complaints, *associated, *chronic_conditions]
    )
    sparse_terms.extend(
        normalize_vietnamese_text(item).replace(" ", "_")
        for item in chronic_conditions
    )
    en_parts = list(english_terms)
    if onset:
        # Preserve the patient-provided duration as a quoted fact rather than
        # asking a model to reinterpret or expand it.
        en_parts.append(f"patient-reported onset: {onset}")
    if severity is not None:
        en_parts.append(f"severity {severity}/10")
    if radiation:
        en_parts.append(f"patient-reported radiation: {radiation}")
    for key, value in sorted(vitals.items()):
        if key in {"systolic_bp", "diastolic_bp"}:
            continue
        en_parts.append(f"{key} {value}")
        sparse_terms.append(f"vital:{key}")
        numeric = re.sub(r"[^0-9./-]", "", str(value))
        if numeric:
            sparse_terms.append(f"{key}:{numeric}")

    degraded_modes: list[str] = []
    if not en_parts or not english_terms:
        degraded_modes.append("EN_CHANNEL_UNAVAILABLE")
        en_parts = []
    if not sparse_terms:
        degraded_modes.append("SPARSE_CHANNEL_EMPTY")

    return RetrievalQueryBundle(
        query_vi="; ".join(_unique(vi_parts)),
        query_en="; ".join(_unique(en_parts)),
        sparse_terms=_unique(sparse_terms),
        symptom_cluster=symptom_cluster,
        degraded_modes=degraded_modes,
    )


async def build_bilingual_query_node(state: AgentState) -> dict[str, Any]:
    if state.get("unresolved_contradictions"):
        return {
            "retrieval_query_vi": "",
            "retrieval_query_en": "",
            "retrieval_sparse_terms": [],
            "retrieval_degraded_modes": ["BLOCKED_BY_CONTRADICTION"],
            "decision_status": "NEEDS_CLARIFICATION",
            "evidence_status": "NOT_REQUESTED",
            "next_step": "question_engine",
        }
    # Retrieval reads canonical-derived facts. The blueprint reaching this node
    # is already a projection, but re-deriving it here means a denied or
    # historical-only symptom cannot become a positive query term even if some
    # future caller hands us a stale blueprint.
    view = ClinicalStateView.from_agent_state(state)
    # The cluster is decision-critical downstream: it filters protocol scope in
    # the retriever and must match the calibration profile at the evidence gate.
    # It comes from canonical state, never from blueprint wording.
    bundle = build_retrieval_queries(
        project_blueprint(view.canonical, state.get("clinical_blueprint", {})),
        state.get("verified_profile_context", {}),
        symptom_cluster=view.symptom_cluster(),
    )
    age = state.get("patient_age")
    population = (
        "pediatric"
        if age is not None and age < 16
        else "geriatric"
        if age is not None and age >= 65
        else "adult"
        if age is not None
        else "unknown_population"
    )
    return {
        "retrieval_query_vi": bundle.query_vi,
        "retrieval_query_en": bundle.query_en,
        "retrieval_sparse_terms": bundle.sparse_terms,
        "retrieval_degraded_modes": bundle.degraded_modes,
        "retrieval_channels": [],
        "retrieval_refinement_count": 0,
        "retrieval_refined_query": "",
        "retrieval_decision_point": None,
        "retrieval_facets": [],
        "symptom_cluster": bundle.symptom_cluster,
        "retrieval_population": population,
        "workflow_phase": "RETRIEVAL",
        "evidence_status": "NOT_REQUESTED",
        "next_step": "retrieve_evidence",
    }
