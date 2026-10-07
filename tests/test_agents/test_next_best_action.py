"""The planner proposes; deterministic policy decides; canonical state knows.

These pin the three properties that make NBA safe: fixed safety precedence,
selection separated from execution, and a validator no model can talk past.
"""

from __future__ import annotations


from src.agents.action_validator import plan_and_validate, validate_action
from src.agents.canonical_state import CanonicalPatientState
from src.agents.clinical_state_view import ClinicalStateView
from src.agents.next_best_action import (
    ActionContext,
    NextBestAction,
    select_next_best_action,
    deterministic_fallback_action,
)
from src.agents.nodes.fact_extraction import apply_message_to_state

TRIAGE = "TRIAGE_NEW_SYMPTOM"


def _view(*messages: str) -> ClinicalStateView:
    state = CanonicalPatientState()
    for index, message in enumerate(messages):
        apply_message_to_state(state, message, turn_id=f"t{index + 1}")
    return ClinicalStateView(state)


def _empty_view() -> ClinicalStateView:
    return ClinicalStateView(CanonicalPatientState())


# --------------------------------------------------------------------------
# §8 Precedence
# --------------------------------------------------------------------------

def test_confirmed_red_flag_permits_only_escalation() -> None:
    context = ActionContext(
        red_flag_status="CONFIRMED",
        is_red_flag=True,
        intent=TRIAGE,
        missing_critical_fields=("onset_time",),
    )
    action = select_next_best_action(context)
    assert action.action_type == "ESCALATE"
    assert "no_further_questioning" in action.safety_constraints


def test_safety_fallback_is_audited_distinctly_from_a_confirmed_emergency() -> None:
    fallback = ActionContext(
        red_flag_status="SAFETY_FALLBACK", is_red_flag=True, intent=TRIAGE
    )
    confirmed = ActionContext(
        red_flag_status="CONFIRMED", is_red_flag=True, intent=TRIAGE
    )
    assert fallback.safety_state == "SAFETY_FALLBACK"
    assert confirmed.safety_state == "CONFIRMED_RED_FLAG"
    # Both escalate, but the reason recorded differs.
    assert select_next_best_action(fallback).rationale_code == (
        "SAFETY_FALLBACK_PENDING_REVIEW"
    )
    assert select_next_best_action(confirmed).rationale_code == "CONFIRMED_RED_FLAG"


def test_unresolved_safety_context_asks_rather_than_guessing() -> None:
    action = select_next_best_action(
        ActionContext(red_flag_status="UNCERTAIN", intent=TRIAGE)
    )
    assert action.action_type == "CLARIFY"
    assert action.target == "red_flag_context"


def test_precedence_is_strictly_ordered() -> None:
    """A lower band can never pre-empt a higher one."""
    context = ActionContext(
        red_flag_status="CONFIRMED",
        is_red_flag=True,
        intent=TRIAGE,
        relevant_uncertainties=("symptom.dyspnea",),
        unresolved_contradictions=("onset_time",),
        missing_critical_fields=("severity_score",),
        requires_reassessment=True,
    )
    assert select_next_best_action(context).action_type == "ESCALATE"


# --------------------------------------------------------------------------
# Adaptive questioning
# --------------------------------------------------------------------------

def test_the_highest_value_open_requirement_is_asked_first() -> None:
    action = select_next_best_action(
        ActionContext(
            intent=TRIAGE,
            missing_critical_fields=("vital_signs", "chief_complaint", "onset_time"),
        )
    )
    assert action.action_type == "ASK"
    assert action.target == "chief_complaint"


def test_a_contradiction_outranks_an_ordinary_question() -> None:
    action = select_next_best_action(
        ActionContext(
            intent=TRIAGE,
            unresolved_contradictions=("onset_time",),
            missing_critical_fields=("severity_score",),
        )
    )
    assert action.action_type == "CLARIFY"
    assert action.target == "contradiction_onset_time"


def test_relevant_uncertainty_produces_clarification_not_a_question() -> None:
    action = select_next_best_action(
        ActionContext(intent=TRIAGE, relevant_uncertainties=("symptom.dyspnea",))
    )
    assert action.action_type == "CLARIFY"
    assert action.target == "symptom.dyspnea"


def test_non_triage_intent_explains_rather_than_interrogating() -> None:
    action = select_next_best_action(ActionContext(intent="GREETING_HELP"))
    assert action.action_type == "EXPLAIN"


# --------------------------------------------------------------------------
# §12 Dynamic stopping
# --------------------------------------------------------------------------

def test_a_ready_case_stops_asking() -> None:
    action = select_next_best_action(
        ActionContext(intent=TRIAGE, readiness_outcome="READY", next_step="complete")
    )
    assert action.action_type == "END"
    assert action.rationale_code == "SUFFICIENT_TO_CONCLUDE"


def test_a_ready_case_moves_to_evidence_when_the_gate_allows() -> None:
    action = select_next_best_action(
        ActionContext(
            intent=TRIAGE, readiness_outcome="READY", next_step="retrieve_evidence"
        )
    )
    assert action.action_type == "RETRIEVE_RAG"


def test_stopping_does_not_require_every_field_to_be_filled() -> None:
    """READY with no open requirement stops, even though vitals were never given."""
    action = select_next_best_action(
        ActionContext(intent=TRIAGE, readiness_outcome="READY", next_step="complete")
    )
    assert action.action_type == "END"


# --------------------------------------------------------------------------
# §14 Loop prevention
# --------------------------------------------------------------------------

def test_a_target_asked_twice_is_not_asked_a_third_time() -> None:
    action = select_next_best_action(
        ActionContext(
            intent=TRIAGE,
            missing_critical_fields=("onset_time",),
            asked_targets={"onset_time": 2},
        )
    )
    assert action.action_type != "ASK"
    assert action.rationale_code == "REPEATED_WITHOUT_PROGRESS"


def test_moving_on_never_fabricates_the_missing_value() -> None:
    action = select_next_best_action(
        ActionContext(
            intent=TRIAGE,
            missing_critical_fields=("onset_time",),
            asked_targets={"onset_time": 2},
        )
    )
    assert "must_not_fabricate_missing_value" in action.safety_constraints


def test_an_accepted_unknown_is_not_reopened() -> None:
    action = select_next_best_action(
        ActionContext(
            intent=TRIAGE,
            missing_critical_fields=("onset_time",),
            accepted_unknown_targets=("onset_time",),
        )
    )
    assert action.action_type != "ASK"


def test_the_validator_blocks_an_exhausted_target_even_if_proposed() -> None:
    context = ActionContext(
        intent=TRIAGE,
        missing_critical_fields=("onset_time",),
        asked_targets={"onset_time": 2},
    )
    proposal = NextBestAction(
        action_type="ASK",
        rationale_code="DECISION_RELEVANT_UNKNOWN",
        target="onset_time",
    )
    result = validate_action(proposal, context, _empty_view())
    assert result.outcome == "BLOCKED"
    assert result.block_reason == "TARGET_ALREADY_EXHAUSTED"


def test_the_turn_action_limit_is_enforced() -> None:
    context = ActionContext(intent=TRIAGE, turn_action_count=8)
    proposal = NextBestAction(
        action_type="ASK", rationale_code="DECISION_RELEVANT_UNKNOWN", target="x"
    )
    result = validate_action(proposal, context, _empty_view())
    assert result.outcome == "BLOCKED"
    assert result.block_reason == "TURN_ACTION_LIMIT_REACHED"


# --------------------------------------------------------------------------
# §7 The validator cannot be talked past
# --------------------------------------------------------------------------

def test_an_emergency_replaces_any_non_escalating_proposal() -> None:
    context = ActionContext(red_flag_status="CONFIRMED", is_red_flag=True, intent=TRIAGE)
    proposal = NextBestAction(
        action_type="ASK", rationale_code="DECISION_RELEVANT_UNKNOWN", target="onset_time"
    )
    result = validate_action(proposal, context, _empty_view())
    assert result.outcome == "REPLACED"
    assert result.action.action_type == "ESCALATE"
    assert result.replaced_from == "ASK"


def test_the_planner_cannot_target_esi() -> None:
    result = validate_action(
        NextBestAction(
            action_type="ASK", rationale_code="DECISION_RELEVANT_UNKNOWN",
            target="esi_level",
        ),
        ActionContext(intent=TRIAGE),
        _empty_view(),
    )
    assert result.outcome == "BLOCKED"
    assert result.block_reason == "ESI_NOT_PLANNER_AUTHORITY"


def test_the_planner_cannot_target_the_red_flag_flag() -> None:
    result = validate_action(
        NextBestAction(
            action_type="ASK", rationale_code="DECISION_RELEVANT_UNKNOWN",
            target="is_red_flag",
        ),
        ActionContext(intent=TRIAGE),
        _empty_view(),
    )
    assert result.outcome == "BLOCKED"
    assert result.block_reason == "RED_FLAG_NOT_PLANNER_AUTHORITY"


def test_every_question_must_have_a_target() -> None:
    result = validate_action(
        NextBestAction(action_type="ASK", rationale_code="DECISION_RELEVANT_UNKNOWN"),
        ActionContext(intent=TRIAGE),
        _empty_view(),
    )
    assert result.outcome == "BLOCKED"
    assert result.block_reason == "UNTARGETED_QUESTION"


def test_a_fact_already_answered_is_not_re_asked() -> None:
    view = _view("Bây giờ tôi đau ngực")
    result = validate_action(
        NextBestAction(
            action_type="ASK", rationale_code="DECISION_RELEVANT_UNKNOWN",
            target="symptom.chest_pain",
        ),
        ActionContext(intent=TRIAGE, missing_critical_fields=("symptom.chest_pain",)),
        view,
    )
    assert result.outcome == "BLOCKED"
    assert result.block_reason == "TARGET_ALREADY_ANSWERED"


def test_a_denied_fact_counts_as_answered() -> None:
    """A denial is an answer; asking again ignores what the patient said."""
    view = _view("Tôi không đau ngực")
    result = validate_action(
        NextBestAction(
            action_type="ASK", rationale_code="DECISION_RELEVANT_UNKNOWN",
            target="symptom.chest_pain",
        ),
        ActionContext(intent=TRIAGE, missing_critical_fields=("symptom.chest_pain",)),
        view,
    )
    assert result.outcome == "BLOCKED"
    assert result.block_reason == "TARGET_ALREADY_ANSWERED"


def test_a_question_outside_the_live_requirements_is_blocked() -> None:
    result = validate_action(
        NextBestAction(
            action_type="ASK", rationale_code="DECISION_RELEVANT_UNKNOWN",
            target="favourite_colour",
        ),
        ActionContext(intent=TRIAGE, missing_critical_fields=("onset_time",)),
        _empty_view(),
    )
    assert result.outcome == "BLOCKED"
    assert result.block_reason == "TARGET_NOT_A_LIVE_REQUIREMENT"


def test_retrieval_cannot_bypass_the_evidence_gate() -> None:
    result = validate_action(
        NextBestAction(action_type="RETRIEVE_RAG", rationale_code="READY_FOR_EVIDENCE"),
        ActionContext(intent=TRIAGE, next_step="question_engine"),
        _empty_view(),
    )
    assert result.outcome == "BLOCKED"
    assert result.block_reason == "EVIDENCE_GATE_NOT_SATISFIED"


# --------------------------------------------------------------------------
# Security
# --------------------------------------------------------------------------

def test_a_cross_patient_action_is_blocked_before_anything_else() -> None:
    result = validate_action(
        NextBestAction(action_type="ESCALATE", rationale_code="CONFIRMED_RED_FLAG"),
        ActionContext(red_flag_status="CONFIRMED", is_red_flag=True, intent=TRIAGE),
        _empty_view(),
        authorized_patient_id="alice",
        action_patient_id="bob",
    )
    assert result.outcome == "BLOCKED"
    assert result.block_reason == "CROSS_PATIENT_ACCESS"


def test_a_session_mismatch_is_blocked() -> None:
    result = validate_action(
        NextBestAction(action_type="END", rationale_code="SUFFICIENT_TO_CONCLUDE"),
        ActionContext(intent=TRIAGE),
        _empty_view(),
        authorized_session_id="s1",
        action_session_id="s2",
    )
    assert result.outcome == "BLOCKED"
    assert result.block_reason == "SESSION_MISMATCH"


# --------------------------------------------------------------------------
# §36 Failure modes
# --------------------------------------------------------------------------

def test_planner_unavailable_falls_back_without_fabricating() -> None:
    context = ActionContext(intent=TRIAGE, missing_critical_fields=("onset_time",))
    action = deterministic_fallback_action(context)
    assert action.action_type == "ASK"
    assert action.rationale_code == "PLANNER_UNAVAILABLE_FALLBACK"
    assert action.audit_metadata["planner"] == "unavailable"


def test_the_fallback_still_respects_safety_precedence() -> None:
    action = deterministic_fallback_action(
        ActionContext(red_flag_status="CONFIRMED", is_red_flag=True, intent=TRIAGE)
    )
    assert action.action_type == "ESCALATE"


# --------------------------------------------------------------------------
# Auditability
# --------------------------------------------------------------------------

def test_every_decision_carries_a_structured_audit_trail() -> None:
    result = plan_and_validate(
        ActionContext(intent=TRIAGE, missing_critical_fields=("onset_time",)),
        _empty_view(),
    )
    audit = result.to_dict()
    assert audit["outcome"] == "APPROVED"
    assert audit["action"]["rationale_code"] == "DECISION_RELEVANT_UNKNOWN"
    assert audit["safety_state"] == "NOT_READY"
    assert audit["readiness_outcome"] == "NOT_READY"


def test_the_audit_trail_holds_no_free_text_reasoning() -> None:
    """Structured reason codes only - never a chain of thought."""
    action = select_next_best_action(
        ActionContext(intent=TRIAGE, missing_critical_fields=("onset_time",))
    )
    payload = action.to_dict()
    assert isinstance(payload["rationale_code"], str)
    assert len(payload["rationale_code"]) < 60
    assert "reasoning" not in payload
    assert "thought" not in payload
