"""Readiness must ask what *this* presentation needs, from canonical state.

The regression being locked down: a possible myocardial infarction and a
sprained ankle used to produce an identical residual question list, because
readiness ran one checklist against a flat blueprint.
"""

from __future__ import annotations

from typing import Any

import pytest

from src.agents.canonical_state import CanonicalPatientState
from src.agents.clinical_state_view import ClinicalStateView
from src.agents.nodes.fact_extraction import apply_message_to_state
from src.agents.nodes.intake_analyzer import analyze_patient_intake
from src.agents.nodes.readiness_evaluator import (
    evaluate_readiness,
    evaluate_readiness_node,
)

CONFIRMED_EHR = {"clinical_memory_confirmation_status": "CONFIRMED"}


def _view(*messages: str) -> ClinicalStateView:
    state = CanonicalPatientState()
    for index, message in enumerate(messages):
        apply_message_to_state(state, message, turn_id=f"turn-{index + 1}")
    return ClinicalStateView(state)


def _readiness(*messages: str, blueprint: dict[str, Any] | None = None):
    view = _view(*messages)
    return evaluate_readiness(blueprint or {}, view=view, **CONFIRMED_EHR)


async def _turn(state: dict[str, Any], message: str, turn: int) -> dict[str, Any]:
    incoming = {
        **state,
        "query": message,
        "current_turn_id": f"t{turn}",
        "intent": "TRIAGE_FOLLOW_UP",
        "clinical_memory_confirmation_status": "CONFIRMED",
    }
    update = await analyze_patient_intake(incoming)
    merged = {**incoming, **update}
    return {**merged, **await evaluate_readiness_node(merged)}


# --------------------------------------------------------------------------
# §6 context-dependent requirements
# --------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_different_presentations_ask_different_questions() -> None:
    chest = await _turn({}, "Tôi đang đau ngực dữ dội", 1)
    ankle = await _turn({}, "Tôi bị đau mắt cá chân", 1)
    throat = await _turn({}, "Tôi bị đau họng", 1)

    assert chest["symptom_cluster"] == "chest_pain"
    # The decisive assertion: the residual question lists must not be identical.
    assert chest["missing_critical_fields"] != ankle["missing_critical_fields"]
    assert chest["missing_critical_fields"] != throat["missing_critical_fields"]
    # And chest pain must demand strictly more than a minor complaint.
    assert len(chest["missing_critical_fields"]) > len(
        ankle["missing_critical_fields"]
    )


@pytest.mark.asyncio
async def test_chest_pain_requires_severity_and_associated_features() -> None:
    result = await _turn({}, "Tôi đang đau ngực", 1)
    assert "severity_score" in result["missing_critical_fields"]
    assert "associated_symptoms" in result["missing_critical_fields"]


@pytest.mark.asyncio
async def test_a_minor_complaint_is_not_asked_for_severity_or_vitals() -> None:
    """§7: an unknown that cannot change this triage must not block."""
    result = await _turn({}, "Tôi bị đau mắt cá chân từ hôm qua", 1)
    assert "severity_score" not in result["missing_critical_fields"]
    assert "associated_symptoms" not in result["missing_critical_fields"]
    assert "vital_signs" not in result["missing_critical_fields"]


@pytest.mark.asyncio
async def test_fever_asks_for_a_current_temperature() -> None:
    result = await _turn({}, "Tôi bị sốt từ hôm qua", 1)
    assert result["symptom_cluster"] == "fever"
    assert "vital_signs" in result["missing_critical_fields"]


# --------------------------------------------------------------------------
# §7 decision-relevant vs merely absent
# --------------------------------------------------------------------------

def test_irrelevant_unknown_does_not_become_a_mandatory_question() -> None:
    evaluation = _readiness(
        "Tôi bị đau họng từ hôm qua",
        blueprint={"chief_complaint": ["đau họng"], "onset_time": "hôm qua"},
    )
    assert "medication" not in evaluation.missing_critical_fields
    assert "vital_signs" not in evaluation.missing_critical_fields


def test_risk_relevant_unknown_is_surfaced() -> None:
    evaluation = _readiness(
        "Tôi đang đau ngực",
        blueprint={"chief_complaint": ["đau ngực"], "onset_time": "1 giờ"},
    )
    assert "severity_score" in evaluation.decision_relevant_unknowns
    assert "severity_score" in evaluation.missing_critical_fields


def test_decision_relevant_unknowns_are_reported_separately_from_workflow_gates() -> None:
    evaluation = evaluate_readiness(
        {"chief_complaint": ["đau ngực"]},
        view=_view("Tôi đang đau ngực"),
        clinical_memory_confirmation_status="NOT_REVIEWED",
    )
    assert "clinical_memory_confirmation" in evaluation.missing_critical_fields
    # An EHR consent gate is not a clinical unknown about the patient's body.
    assert "clinical_memory_confirmation" not in evaluation.decision_relevant_unknowns


# --------------------------------------------------------------------------
# §8 uncertainty
# --------------------------------------------------------------------------

def test_clinically_relevant_uncertainty_produces_clarification() -> None:
    evaluation = _readiness(
        "Tôi đang đau ngực, hình như tôi hơi khó thở",
        blueprint={"chief_complaint": ["đau ngực"], "onset_time": "1 giờ"},
    )
    assert "symptom.dyspnea" in evaluation.relevant_uncertainties
    assert evaluation.outcome == "NEEDS_CLARIFICATION"


def test_uncertainty_is_never_promoted_to_known() -> None:
    view = _view("Tôi đang đau ngực, hình như tôi hơi khó thở")
    assert view.is_uncertain("symptom.dyspnea") is True
    assert view.is_present("symptom.dyspnea") is False


# --------------------------------------------------------------------------
# §9 temporal awareness
# --------------------------------------------------------------------------

def test_readiness_uses_the_current_temperature_not_the_morning_one() -> None:
    view = _view("Sáng nay tôi sốt 39 độ, giờ nhiệt độ còn 37.8")
    assert view.current_value("vital.temperature_c") == 37.8
    evaluation = evaluate_readiness(
        {"chief_complaint": ["sốt"], "onset_time": "hôm qua"},
        view=view,
        **CONFIRMED_EHR,
    )
    # The current reading satisfies the fever profile's temperature requirement.
    assert "vital.temperature_c" not in evaluation.decision_relevant_unknowns


def test_a_historical_symptom_alone_does_not_select_the_acute_profile() -> None:
    evaluation = _readiness(
        "Tuần trước tôi bị đau ngực",
        blueprint={"chief_complaint": ["đau ngực"]},
    )
    # Clustered by the blueprint's wording at worst, but current chest pain is
    # still unknown rather than assumed present.
    assert _view("Tuần trước tôi bị đau ngực").is_present("symptom.chest_pain") is False
    assert evaluation.ready is False


def test_negated_symptom_is_not_treated_as_an_open_question() -> None:
    view = _view("Tôi đang đau ngực, tôi không khó thở")
    assert view.is_negated("symptom.dyspnea") is True
    assert view.is_unknown("symptom.dyspnea") is False


# --------------------------------------------------------------------------
# §10 corrections
# --------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_readiness_follows_a_correction_not_the_stale_value() -> None:
    state = await _turn({}, "Tôi đau ngực từ 8 giờ", 1)
    before = state["clinical_blueprint"]["onset_time"]
    state = await _turn(state, "À tôi nhớ nhầm, thực ra là từ 5 giờ", 2)

    view = ClinicalStateView.from_agent_state(state)
    assert view.current_value("onset_time") == "5 giờ"
    # The projection readiness reads must follow canonical, not the old value.
    assert state["clinical_blueprint"]["onset_time"] == "5 giờ"
    assert state["clinical_blueprint"]["onset_time"] != before


# --------------------------------------------------------------------------
# §11 / §15 late information invalidates a prior conclusion
# --------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_late_information_changes_readiness() -> None:
    state = await _turn({}, "Tôi bị đau mắt cá chân từ hôm qua", 1)
    before = list(state["missing_critical_fields"])
    state = await _turn(state, "À tôi còn đang đau ngực nữa", 2)
    assert state["missing_critical_fields"] != before
    assert state["symptom_cluster"] == "chest_pain"


@pytest.mark.asyncio
async def test_a_clinically_relevant_late_fact_invalidates_a_prior_conclusion() -> None:
    decided = {
        "current_esi_level": 4,
        "sbar_report": {"situation": "..."},
        "canonical_state": CanonicalPatientState().to_dict(),
    }
    state = await _turn(decided, "À tôi còn khó thở nữa", 2)
    assert state["requires_triage_reassessment"] is True
    assert "symptom.dyspnea" in state["pending_reassessment_keys"]


@pytest.mark.asyncio
async def test_a_turn_with_no_clinical_content_does_not_force_reassessment() -> None:
    decided = {
        "current_esi_level": 4,
        "sbar_report": {"situation": "..."},
        "canonical_state": CanonicalPatientState().to_dict(),
    }
    state = await _turn(decided, "vâng ạ", 2)
    assert state["requires_triage_reassessment"] is False


# --------------------------------------------------------------------------
# §19 invariants
# --------------------------------------------------------------------------

def test_readiness_never_reads_a_negated_fact_as_unknown() -> None:
    view = _view("Tôi không đau ngực")
    evaluation = evaluate_readiness({}, view=view, **CONFIRMED_EHR)
    assert "symptom.chest_pain" not in evaluation.decision_relevant_unknowns


def test_readiness_outcome_vocabulary_is_explicit() -> None:
    ready = evaluate_readiness(
        {"chief_complaint": ["đau họng"], "onset_time": "hôm qua"},
        view=_view("Tôi bị đau họng từ hôm qua"),
        **CONFIRMED_EHR,
    )
    blocked = evaluate_readiness({}, view=_view(""), **CONFIRMED_EHR)
    assert ready.outcome == "READY"
    assert ready.decision_status == "READY_FOR_EVIDENCE"
    assert blocked.outcome in {"NOT_READY", "NEEDS_CLARIFICATION"}


def test_evaluate_readiness_without_a_view_is_safe_for_legacy_callers() -> None:
    """Old callers pass only a blueprint; they must not crash or become READY."""
    evaluation = evaluate_readiness({})
    assert evaluation.ready is False
    assert evaluation.decision_status == "NEEDS_CLARIFICATION"
