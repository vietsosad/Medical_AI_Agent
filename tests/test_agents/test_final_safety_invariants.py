"""The invariants that must hold no matter what else changes.

Everything else in this repository is an implementation that could reasonably
be rewritten. These are the properties that make the rewrite safe or unsafe.
They are written as flatly as possible -- one claim per test, no scenario
setup beyond what the claim needs -- so that a failure here names the broken
guarantee directly rather than a broken workflow.

The grouping follows the safety contract: what a status means, what time
means, where a fact came from, who owns a clinical decision, and who is
allowed to see it.
"""

from __future__ import annotations

import pytest

from src.agents.action_validator import validate_action
from src.agents.canonical_state import CanonicalPatientState
from src.agents.clinical_state_view import ClinicalStateView
from src.agents.conversation_memory import ConversationMemory, MemoryScope
from src.agents.next_best_action import (
    MAX_ACTIONS_PER_TURN,
    ActionContext,
    NextBestAction,
    select_next_best_action,
)

PATIENT = "patient-inv"
SESSION = "session-inv"
KEY = "symptom.chest_pain"


def _view(state: CanonicalPatientState) -> ClinicalStateView:
    return ClinicalStateView(state)


def _empty_view() -> ClinicalStateView:
    return ClinicalStateView(CanonicalPatientState())


# --------------------------------------------------------------------------
# What a status means
# --------------------------------------------------------------------------

def test_unknown_is_not_negated() -> None:
    view = _empty_view()
    assert view.is_unknown(KEY)
    assert not view.is_negated(KEY)


def test_unknown_is_not_false() -> None:
    """Nobody asked is not the same as the patient said no."""
    view = _empty_view()
    assert view.is_unknown(KEY)
    assert not view.is_present(KEY)
    assert view.read(KEY).value is None


def test_negated_is_not_a_current_positive() -> None:
    state = CanonicalPatientState()
    state.record(KEY, False, status="NEGATED", source="PATIENT_REPORTED",
                 temporal="CURRENT", turn_id="t1")
    view = _view(state)

    assert view.is_negated(KEY)
    assert not view.is_present(KEY)
    assert not view.is_unknown(KEY), "a denial is an answer, not a gap"


def test_uncertain_is_neither_present_nor_negated() -> None:
    state = CanonicalPatientState()
    state.record(KEY, True, status="UNCERTAIN", source="PATIENT_REPORTED",
                 temporal="CURRENT", turn_id="t1")
    view = _view(state)

    assert view.is_uncertain(KEY)
    assert not view.is_present(KEY)
    assert not view.is_negated(KEY)


# --------------------------------------------------------------------------
# What time means
# --------------------------------------------------------------------------

def test_historical_is_not_current() -> None:
    state = CanonicalPatientState()
    state.record("symptom.fever", 39.0, status="KNOWN", source="PATIENT_REPORTED",
                 temporal="HISTORICAL", temporal_label="tuần trước", turn_id="t1")

    assert _view(state).is_unknown("symptom.fever")


def test_a_historical_fact_is_still_recorded_and_recoverable() -> None:
    """Not current does not mean discarded; the history must survive."""
    state = CanonicalPatientState()
    state.record("symptom.fever", 39.0, status="KNOWN", source="PATIENT_REPORTED",
                 temporal="HISTORICAL", temporal_label="tuần trước", turn_id="t1")

    assert state.was_ever_reported("symptom.fever")
    assert state.historical_values("symptom.fever")


# --------------------------------------------------------------------------
# Where a fact came from
# --------------------------------------------------------------------------

def test_inferred_is_not_patient_reported() -> None:
    state = CanonicalPatientState()
    state.record(KEY, True, status="INFERRED", source="SYSTEM_INFERENCE",
                 temporal="CURRENT", turn_id="t1")
    observation = state.observation_of(KEY)

    assert observation is not None
    assert observation.source == "SYSTEM_INFERENCE"
    assert observation.source != "PATIENT_REPORTED"
    assert _view(state).read(KEY).is_inferred


def test_synthetic_is_not_patient_reported() -> None:
    state = CanonicalPatientState()
    state.record(KEY, True, status="KNOWN", source="SYNTHETIC",
                 temporal="CURRENT", turn_id="t1")
    observation = state.observation_of(KEY)

    assert observation is not None
    assert observation.source == "SYNTHETIC"
    assert observation.source != "PATIENT_REPORTED"


def test_a_missing_source_never_defaults_to_patient_reported() -> None:
    """Deserialising an incomplete record must not upgrade its provenance."""
    restored = CanonicalPatientState.from_dict({
        "facts": {
            KEY: {
                "key": KEY,
                "observations": [
                    {"value": True, "status": "KNOWN", "temporal": "CURRENT"}
                ],
            }
        }
    })
    observation = restored.observation_of(KEY)

    assert observation is not None
    assert observation.source != "PATIENT_REPORTED"


def test_legacy_recovered_is_distinguishable_from_a_live_observation() -> None:
    state = CanonicalPatientState()
    state.record(KEY, True, status="KNOWN", source="LEGACY_RECOVERED",
                 temporal="UNKNOWN_TIME", turn_id="legacy")
    observation = state.observation_of(KEY)

    assert observation is not None
    assert observation.source == "LEGACY_RECOVERED"
    assert _view(state).has_degraded_provenance()


# --------------------------------------------------------------------------
# Memory is not clinical authority
# --------------------------------------------------------------------------

def test_memory_is_not_canonical_authority() -> None:
    memory = ConversationMemory()
    memory.remember("Tôi bị đau ngực nặng lắm",
                    patient_id=PATIENT, session_id=SESSION)

    state = CanonicalPatientState()
    state.record(KEY, False, status="NEGATED", source="PATIENT_REPORTED",
                 temporal="CURRENT", turn_id="t1")

    assert memory.search("đau ngực", MemoryScope(PATIENT, SESSION))
    assert _view(state).is_negated(KEY)


def test_memory_never_writes_to_canonical_state() -> None:
    """There is no code path from a memory item into the clinical record."""
    state = CanonicalPatientState()
    before = dict(state.facts)

    memory = ConversationMemory()
    memory.remember("Tôi bị đau ngực", patient_id=PATIENT, session_id=SESSION)
    memory.record_event("NEW_SYMPTOM", "chest_pain",
                        patient_id=PATIENT, session_id=SESSION, turn_id="t1")

    assert dict(state.facts) == before


# --------------------------------------------------------------------------
# The red-flag lifecycle
# --------------------------------------------------------------------------

def test_a_candidate_is_not_a_confirmed_red_flag() -> None:
    context = ActionContext(intent="TRIAGE_NEW_SYMPTOM", red_flag_status="CANDIDATE")

    assert context.safety_state != "CONFIRMED_RED_FLAG"
    assert select_next_best_action(context).action_type != "ESCALATE"


def test_a_safety_fallback_is_not_recorded_as_a_confirmed_emergency() -> None:
    """A precaution taken because a validator was down is not a finding."""
    context = ActionContext(intent="TRIAGE_NEW_SYMPTOM",
                            red_flag_status="SAFETY_FALLBACK")

    assert context.safety_state == "SAFETY_FALLBACK"
    action = select_next_best_action(context)
    assert action.action_type == "ESCALATE"
    assert action.rationale_code == "SAFETY_FALLBACK_PENDING_REVIEW"
    assert action.rationale_code != "CONFIRMED_RED_FLAG"


@pytest.mark.parametrize(
    "action_type",
    ["ASK", "CLARIFY", "RETRIEVE_RAG", "RETRIEVE_MEMORY", "REASSESS", "EXPLAIN"],
)
def test_a_safety_fallback_cannot_be_downgraded(action_type: str) -> None:
    context = ActionContext(intent="TRIAGE_NEW_SYMPTOM",
                            red_flag_status="SAFETY_FALLBACK")
    proposed = NextBestAction(
        action_type=action_type,
        rationale_code="DECISION_RELEVANT_UNKNOWN",
        target="severity_score" if action_type in {"ASK", "CLARIFY"} else None,
    )

    result = validate_action(proposed, context, _empty_view())

    assert result.outcome == "REPLACED"
    assert result.action is not None
    assert result.action.action_type == "ESCALATE"


@pytest.mark.parametrize(
    "action_type",
    ["ASK", "CLARIFY", "RETRIEVE_RAG", "RETRIEVE_MEMORY", "REASSESS", "EXPLAIN"],
)
def test_a_confirmed_red_flag_cannot_be_downgraded(action_type: str) -> None:
    context = ActionContext(intent="TRIAGE_NEW_SYMPTOM",
                            red_flag_status="CONFIRMED", is_red_flag=True)
    proposed = NextBestAction(
        action_type=action_type,
        rationale_code="DECISION_RELEVANT_UNKNOWN",
        target="severity_score" if action_type in {"ASK", "CLARIFY"} else None,
    )

    result = validate_action(proposed, context, _empty_view())

    assert result.action is not None
    assert result.action.action_type == "ESCALATE"


def test_an_escalation_is_never_suppressed_by_a_loop_budget() -> None:
    context = ActionContext(intent="TRIAGE_NEW_SYMPTOM", red_flag_status="CONFIRMED",
                            is_red_flag=True,
                            turn_action_count=MAX_ACTIONS_PER_TURN * 3)
    result = validate_action(select_next_best_action(context), context, _empty_view())

    assert result.outcome != "BLOCKED"
    assert result.action is not None
    assert result.action.action_type == "ESCALATE"


# --------------------------------------------------------------------------
# What the planner may not decide
# --------------------------------------------------------------------------

@pytest.mark.parametrize(
    "target",
    ["esi_level", "current_esi_level", "final_clinical_esi"],
)
def test_the_planner_cannot_set_an_esi(target: str) -> None:
    context = ActionContext(intent="TRIAGE_NEW_SYMPTOM",
                            missing_critical_fields=(target,))
    proposed = NextBestAction(action_type="ASK",
                              rationale_code="DECISION_RELEVANT_UNKNOWN",
                              target=target)

    result = validate_action(proposed, context, _empty_view())

    assert result.outcome == "BLOCKED"
    assert result.block_reason == "ESI_NOT_PLANNER_AUTHORITY"


def test_the_planner_cannot_confirm_a_red_flag() -> None:
    context = ActionContext(intent="TRIAGE_NEW_SYMPTOM",
                            missing_critical_fields=("is_red_flag",))
    proposed = NextBestAction(action_type="ASK",
                              rationale_code="DECISION_RELEVANT_UNKNOWN",
                              target="is_red_flag")

    result = validate_action(proposed, context, _empty_view())

    assert result.outcome == "BLOCKED"
    assert result.block_reason == "RED_FLAG_NOT_PLANNER_AUTHORITY"


def test_the_planner_never_concludes_while_readiness_says_not_ready() -> None:
    """Stopping is a claim. It may only be made when readiness supports it."""
    context = ActionContext(intent="TRIAGE_NEW_SYMPTOM", readiness_outcome="NOT_READY")
    action = select_next_best_action(context)

    assert action.action_type != "END"
    assert action.rationale_code != "SUFFICIENT_TO_CONCLUDE"


def test_no_action_may_ask_for_a_fact_already_answered() -> None:
    state = CanonicalPatientState()
    state.record("severity_score", 7, status="KNOWN", source="PATIENT_REPORTED",
                 temporal="CURRENT", turn_id="t1")
    context = ActionContext(intent="TRIAGE_NEW_SYMPTOM",
                            missing_critical_fields=("severity_score",))
    proposed = NextBestAction(action_type="ASK",
                              rationale_code="DECISION_RELEVANT_UNKNOWN",
                              target="severity_score")

    result = validate_action(proposed, context, _view(state))
    assert result.outcome == "BLOCKED"


def test_a_negated_fact_counts_as_answered() -> None:
    """A denial is an answer; re-asking it treats "no" as silence."""
    state = CanonicalPatientState()
    state.record("symptom.vomiting", False, status="NEGATED",
                 source="PATIENT_REPORTED", temporal="CURRENT", turn_id="t1")
    context = ActionContext(intent="TRIAGE_NEW_SYMPTOM",
                            missing_critical_fields=("symptom.vomiting",))
    proposed = NextBestAction(action_type="ASK",
                              rationale_code="DECISION_RELEVANT_UNKNOWN",
                              target="symptom.vomiting")

    result = validate_action(proposed, context, _view(state))
    assert result.outcome == "BLOCKED"


def test_an_untargeted_question_is_blocked() -> None:
    context = ActionContext(intent="TRIAGE_NEW_SYMPTOM")
    proposed = NextBestAction(action_type="ASK",
                              rationale_code="DECISION_RELEVANT_UNKNOWN",
                              target=None)

    result = validate_action(proposed, context, _empty_view())
    assert result.outcome == "BLOCKED"
    assert result.block_reason == "UNTARGETED_QUESTION"


def test_a_target_asked_to_the_limit_is_not_asked_again() -> None:
    context = ActionContext(intent="TRIAGE_NEW_SYMPTOM",
                            missing_critical_fields=("severity_score",),
                            asked_targets={"severity_score": 2})
    proposed = NextBestAction(action_type="ASK",
                              rationale_code="DECISION_RELEVANT_UNKNOWN",
                              target="severity_score")

    result = validate_action(proposed, context, _empty_view())
    assert result.outcome == "BLOCKED"


def test_an_exhausted_target_is_accepted_unknown_never_fabricated() -> None:
    context = ActionContext(intent="TRIAGE_NEW_SYMPTOM",
                            missing_critical_fields=("severity_score",),
                            asked_targets={"severity_score": 2},
                            accepted_unknown_targets=("severity_score",))
    action = select_next_best_action(context)

    assert action.action_type != "ASK"
    assert "must_not_fabricate_missing_value" in action.safety_constraints


# --------------------------------------------------------------------------
# Who is allowed to see what
# --------------------------------------------------------------------------

def test_no_cross_patient_memory() -> None:
    memory = ConversationMemory()
    memory.remember("Tôi bị đau ngực", patient_id="patient-A", session_id=SESSION)

    assert memory.recent(MemoryScope("patient-B", SESSION)) == []
    assert memory.search("đau ngực", MemoryScope("patient-B", SESSION)) == []


def test_no_cross_session_memory() -> None:
    memory = ConversationMemory()
    memory.remember("Tôi bị đau ngực", patient_id=PATIENT, session_id="session-1")

    assert memory.recent(MemoryScope(PATIENT, "session-2")) == []


def test_an_empty_scope_reads_nothing() -> None:
    """A missing identifier must fail closed, not match everything."""
    memory = ConversationMemory()
    memory.remember("Tôi bị đau ngực", patient_id=PATIENT, session_id=SESSION)

    assert memory.recent(MemoryScope("", SESSION)) == []
    assert memory.recent(MemoryScope(PATIENT, "")) == []
    assert memory.recent(MemoryScope("", "")) == []


def test_no_cross_patient_action() -> None:
    context = ActionContext(intent="TRIAGE_NEW_SYMPTOM",
                            missing_critical_fields=("severity_score",))
    proposed = NextBestAction(action_type="ASK",
                              rationale_code="DECISION_RELEVANT_UNKNOWN",
                              target="severity_score")

    result = validate_action(proposed, context, _empty_view(),
                             authorized_patient_id="patient-A",
                             action_patient_id="patient-B")

    assert result.outcome == "BLOCKED"
    assert result.block_reason == "CROSS_PATIENT_ACCESS"
