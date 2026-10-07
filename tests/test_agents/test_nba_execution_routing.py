"""The selected action must decide what runs, not merely describe what would.

Before this suite existed, ``selected_action`` was written to state, persisted
to the audit trail, and read by nothing: routing branched on ``decision_status``
and the question engine picked its own field. The planner was a commentary
track. Every test here therefore asserts two things together -- which action was
selected, *and* which handler actually ran -- because either one alone is
exactly the evidence that was previously missing.

These drive the real ``update_intake_phase`` with real nodes, so a regression
anywhere between extraction, readiness, selection, validation and dispatch shows
up here rather than in a unit test that stubs the interesting half away.
"""

from __future__ import annotations

from typing import Any

import pytest

from src.agents.action_execution import execute_action
from src.agents.action_validator import validate_action
from src.agents.canonical_state import CanonicalPatientState
from src.agents.clinical_state_view import ClinicalStateView
from src.agents.deepagent_runtime.tools import TurnContext, update_intake_phase
from src.agents.next_best_action import ActionContext, NextBestAction

BASE: dict[str, Any] = {
    "intent": "TRIAGE_NEW_SYMPTOM",
    "clinical_memory_confirmation_status": "CONFIRMED",
    "vital_signs_status": "REVIEWED",
    "patient_id": "patient-1",
    "session_id": "session-1",
}


async def _turn(state: dict[str, Any], query: str, turn_id: str = "t1") -> dict[str, Any]:
    """One real intake turn through the tool-gated runtime."""
    context = TurnContext({**BASE, **state, "query": query, "current_turn_id": turn_id})
    context.called_tools.update({"assess_contextual_emergency", "classify_request"})
    await update_intake_phase(context)
    return context.state


def _action(state: dict[str, Any]) -> str | None:
    return (state.get("selected_action") or {}).get("action_type")


def _handler(state: dict[str, Any]) -> str | None:
    return (state.get("action_execution") or {}).get("handler")


def _empty_view() -> ClinicalStateView:
    return ClinicalStateView(CanonicalPatientState())


# --------------------------------------------------------------------------
# Case B / A -- a relevant unknown asks, and a satisfied case stops asking
# --------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_case_b_a_provisional_unknown_does_not_preempt_authority_retrieval() -> None:
    """The provisional profile informs the audit; the problem state asks."""
    state = await _turn({}, "Tôi bị đau ngực")

    assert _action(state) == "ASK"
    assert state["action_lifecycle"] == "EXECUTED"
    assert _handler(state) == "question_engine"
    assert state.get("response")
    # The question is chosen from the chest pain's own open attributes, not
    # lifted out of the provisional profile's residual field list.
    assert state["selected_action"]["target"].startswith(
        ("chest_pain.", "symptom.", "vital.")
    )
    assert "severity_score" in state["provisional_readiness_hints"]["missing_fields"]



@pytest.mark.asyncio
async def test_case_a_a_sufficient_case_stops_asking_and_moves_on() -> None:
    """Confirmed and ready: the next operation is retrieval, not another question."""
    state = await _turn(
        {"patient_confirmed_intake": True},
        "Tôi bị đau họng từ hôm qua, đau nhẹ thôi",
    )

    assert _action(state) in {"RETRIEVE_RAG", "END"}
    assert state["action_lifecycle"] == "EXECUTED"
    assert state.get("next_step") == "retrieve_evidence"


@pytest.mark.asyncio
async def test_an_unconfirmed_ready_case_asks_for_confirmation_not_evidence() -> None:
    state = await _turn(
        {"patient_confirmed_intake": False},
        "Tôi bị đau họng từ hôm qua, đau nhẹ thôi",
    )

    assert _action(state) == "END"
    assert _handler(state) == "patient_confirmation"
    assert state.get("next_step") != "retrieve_evidence"


# --------------------------------------------------------------------------
# Case C -- an open contradiction clarifies
# --------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_case_c_a_contradiction_executes_the_clarification_flow() -> None:
    state = await _turn(
        {"unresolved_contradictions": [{"field": "onset_time"}]},
        "Tôi bị đau ngực",
    )

    assert _action(state) == "CLARIFY"
    assert _handler(state) == "question_engine"
    assert state.get("response")
    # Nothing may be concluded while the contradiction is open.
    assert state.get("current_esi_level") is None


# --------------------------------------------------------------------------
# Case D -- retrieval is actually entered
# --------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_case_d_retrieve_rag_hands_the_turn_to_the_evidence_gate() -> None:
    state = await _turn(
        {"patient_confirmed_intake": True},
        "Tôi bị đau họng từ hôm qua, đau nhẹ thôi",
    )

    assert state.get("next_step") == "retrieve_evidence"
    assert _handler(state) == "evidence_gate_handoff"


# --------------------------------------------------------------------------
# Case E -- memory retrieval actually runs, scoped
# --------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_case_e_an_unresolved_reference_executes_memory_retrieval() -> None:
    state = await _turn({}, "Cơn đau tôi nói lúc nãy vẫn còn")

    assert _action(state) == "RETRIEVE_MEMORY"
    assert _handler(state) == "conversation_memory_search"
    # The key exists even when nothing matched, so a caller can tell "searched
    # and found nothing" from "never searched".
    assert "retrieved_memory" in state


@pytest.mark.asyncio
async def test_memory_retrieval_never_returns_another_patients_turn() -> None:
    from src.agents.conversation_memory import ConversationMemory

    memory = ConversationMemory()
    memory.remember("Tôi bị đau ngực dữ dội", patient_id="patient-2",
                    session_id="session-2")

    state = await _turn(
        {"conversation_memory": memory.to_dict()},
        "Cơn đau tôi nói lúc nãy vẫn còn",
    )

    assert _handler(state) == "conversation_memory_search"
    assert state["retrieved_memory"] == []


@pytest.mark.asyncio
async def test_retrieved_memory_is_never_labelled_a_clinical_fact() -> None:
    from src.agents.conversation_memory import ConversationMemory

    memory = ConversationMemory()
    memory.remember("Cơn đau ngực của tôi", patient_id="patient-1",
                    session_id="session-1")

    state = await _turn(
        {"conversation_memory": memory.to_dict()},
        "Cơn đau tôi nói lúc nãy vẫn còn",
    )

    for item in state.get("retrieved_memory") or []:
        assert item["is_clinical_fact"] is False


# --------------------------------------------------------------------------
# Case F -- a late change invalidates the stale assessment
# --------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_case_f_a_late_change_executes_reassessment() -> None:
    """A conclusion already drawn is invalidated, not amended."""
    first = await _turn(
        {"patient_confirmed_intake": True},
        "Tôi bị đau họng từ hôm qua, đau nhẹ thôi",
        turn_id="t1",
    )
    concluded = {
        **first,
        "current_esi_level": 4,
        "sbar_report": {"situation": "sore throat"},
    }

    state = await _turn(concluded, "Bây giờ tôi thấy khó thở nhiều", turn_id="t2")

    assert _action(state) == "REASSESS"
    assert _handler(state) == "assessment_invalidation"
    # The stale conclusion is gone rather than carried forward.
    assert state.get("current_esi_level") is None
    assert state.get("sbar_report") is None
    assert state.get("next_step") == "retrieve_evidence"


# --------------------------------------------------------------------------
# Case G -- a confirmed emergency escalates, and nothing else runs
# --------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_case_g_a_confirmed_red_flag_executes_escalation() -> None:
    state = await _turn(
        {"is_red_flag": True, "red_flag_status": "CONFIRMED"},
        "Tôi đau ngực dữ dội",
    )

    assert _action(state) == "ESCALATE"
    assert state["action_lifecycle"] == "EXECUTED"
    assert _handler(state) == "emergency_handoff"
    assert state.get("next_step") == "complete"


@pytest.mark.asyncio
async def test_a_safety_fallback_also_executes_escalation() -> None:
    state = await _turn(
        {"is_red_flag": True, "red_flag_status": "SAFETY_FALLBACK"},
        "Tôi đau ngực dữ dội",
    )

    assert _action(state) == "ESCALATE"
    assert _handler(state) == "emergency_handoff"


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "proposed",
    ["ASK", "CLARIFY", "RETRIEVE_RAG", "RETRIEVE_MEMORY", "REASSESS", "EXPLAIN", "END"],
)
async def test_the_dispatcher_refuses_a_non_escalation_under_an_emergency(
    proposed: str,
) -> None:
    """Precedence is re-checked at execution, not merely trusted from selection."""
    execution = await execute_action(
        {"is_red_flag": True, "red_flag_status": "CONFIRMED"},
        {"action_type": proposed, "rationale_code": "DECISION_RELEVANT_UNKNOWN"},
    )

    assert execution.lifecycle == "BLOCKED"
    assert execution.handler == "emergency_precedence"
    assert execution.state_update == {}


# --------------------------------------------------------------------------
# The emergency END hole
# --------------------------------------------------------------------------

@pytest.mark.parametrize(
    "safety_state", ["CONFIRMED", "SAFETY_FALLBACK"],
)
def test_end_is_not_permitted_under_an_emergency(safety_state: str) -> None:
    """Ending is a claim that nothing further is needed. Not during an emergency."""
    context = ActionContext(
        intent="TRIAGE_NEW_SYMPTOM",
        red_flag_status=safety_state,
        is_red_flag=safety_state == "CONFIRMED",
    )
    proposed = NextBestAction(
        action_type="END",
        rationale_code="SUFFICIENT_TO_CONCLUDE",
    )

    result = validate_action(proposed, context, _empty_view())

    assert result.outcome == "REPLACED"
    assert result.block_reason == "EMERGENCY_PERMITS_ONLY_ESCALATION"
    assert result.action is not None
    assert result.action.action_type == "ESCALATE"


def test_escalation_remains_the_one_permitted_emergency_action() -> None:
    from src.agents.action_validator import _EMERGENCY_PERMITTED

    assert _EMERGENCY_PERMITTED == frozenset({"ESCALATE"})


# --------------------------------------------------------------------------
# Failure handling
# --------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_no_approved_action_fails_closed_to_a_clinician_handoff() -> None:
    """A blocked decision is safe; leaving the patient with silence is not."""
    execution = await execute_action({"step": 2}, None)

    assert execution.lifecycle == "EXECUTION_FAILED"
    assert execution.handler == "insufficient_evidence_handoff"
    assert execution.state_update["decision_status"] == "INSUFFICIENT_EVIDENCE"
    assert execution.state_update["current_esi_level"] is None
    assert execution.state_update["response"]


@pytest.mark.asyncio
async def test_an_unknown_action_type_fails_closed() -> None:
    execution = await execute_action(
        {"step": 2},
        {"action_type": "DELETE_EVERYTHING", "rationale_code": "X"},
    )

    assert execution.lifecycle == "EXECUTION_FAILED"
    assert execution.state_update["current_esi_level"] is None


@pytest.mark.asyncio
async def test_a_handler_raising_is_reported_not_swallowed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def boom(_state: dict) -> dict:
        raise RuntimeError("question engine unavailable")

    monkeypatch.setattr(
        "src.agents.action_execution.run_question_engine_node", boom
    )

    execution = await execute_action(
        {"step": 2},
        {"action_type": "ASK", "rationale_code": "DECISION_RELEVANT_UNKNOWN",
         "target": "severity_score"},
    )

    assert execution.lifecycle == "EXECUTION_FAILED"
    # It fails to a handoff, never to an invented answer.
    assert execution.state_update["current_esi_level"] is None
    assert "RuntimeError" in execution.detail


@pytest.mark.asyncio
async def test_memory_retrieval_without_a_scope_does_not_read_anything() -> None:
    execution = await execute_action(
        {"step": 2, "query": "cơn đau lúc nãy"},
        {"action_type": "RETRIEVE_MEMORY", "rationale_code": "UNRESOLVED_REFERENCE",
         "target": "entity_reference"},
    )

    assert execution.lifecycle == "EXECUTED"
    assert execution.state_update["retrieved_memory"] == []


# --------------------------------------------------------------------------
# Lifecycle auditability
# --------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_proposed_and_executed_are_recorded_separately() -> None:
    state = await _turn({}, "Tôi bị đau ngực")

    assert state["selected_action"]["action_type"] == "ASK"
    assert state["action_validation"]["outcome"] in {"APPROVED", "REPLACED"}
    assert state["action_execution"]["action_type"] == "ASK"
    assert state["action_lifecycle"] == "EXECUTED"


@pytest.mark.asyncio
async def test_the_execution_audit_carries_no_patient_text() -> None:
    state = await _turn({}, "Tôi bị đau ngực dữ dội và rất sợ")
    audit = state["action_execution"]

    assert set(audit) == {"action_type", "lifecycle", "handler", "detail"}
    for value in audit.values():
        assert "sợ" not in str(value)


def test_every_action_type_has_exactly_one_handler() -> None:
    """An unhandled action type must be impossible, not merely unlikely."""
    from typing import get_args

    from src.agents.action_execution import _HANDLERS
    from src.agents.next_best_action import ActionType

    assert set(_HANDLERS) == set(get_args(ActionType))
