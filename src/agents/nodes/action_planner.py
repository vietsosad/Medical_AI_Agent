"""The adaptive turn step: plan an action, validate it, record the outcome.

This node replaces nothing. It runs after safety evaluation and readiness, reads
what they concluded, and chooses what the conversation should do next. Every
clinical gate it depends on has already run, so there is no state in which this
node can talk its way past one.

It does not execute the action. The existing deterministic pipeline still owns
execution - question generation, retrieval, reasoning and verification are
unchanged. What is new is that the *choice* is now explicit, typed, validated
and auditable, instead of being implied by a fixed tool ordering.
"""

from __future__ import annotations

from typing import Any

from src.agents.action_execution import execute_action
from src.agents.action_validator import plan_and_validate
from src.agents.clinical_state_view import ClinicalStateView
from src.agents.conversation_memory import ConversationMemory, MemoryScope
from src.agents.next_best_action import ActionContext
from src.agents.state import AgentState
from src.agents.nodes.readiness_evaluator import WORKFLOW_GATE_FIELDS
from src.agents.nodes.temporal_context import has_anaphoric_reference


def _loop_state(state: AgentState) -> dict[str, Any]:
    return dict(state.get("action_loop_state") or {})


def _record_ask(loop: dict[str, Any], target: str | None) -> dict[str, Any]:
    """Count how often a target has been asked, so a loop cannot run forever."""
    if not target:
        return loop
    asked = dict(loop.get("asked_targets") or {})
    asked[target] = int(asked.get(target, 0)) + 1
    return {**loop, "asked_targets": asked}


async def plan_next_action_node(state: AgentState) -> dict[str, Any]:
    """Select and validate this turn's next best action."""
    view = ClinicalStateView.from_agent_state(state)
    loop = _loop_state(state)

    # ``turn_action_count`` bounds the actions taken *within* one turn, but the
    # loop state it lives in is carried across turns alongside asked_targets.
    # Without this reset the counter accumulates over the conversation and the
    # planner falls permanently silent a few turns in -- which is both wrong
    # and dangerous, since silence is indistinguishable from "nothing to do".
    # asked_targets is deliberately NOT reset: repeat-question limits are a
    # property of the conversation, not of a turn.
    turn_id = str(state.get("current_turn_id") or "")
    if loop.get("counted_turn_id") != turn_id:
        loop["counted_turn_id"] = turn_id
        loop["turn_action_count"] = 0
    loop["turn_action_count"] = int(loop.get("turn_action_count") or 0) + 1

    # "triệu chứng đó" said while a question about a specific symptom is open
    # refers to that symptom. Treating it as an unresolved reference made the
    # agent stop and ask "which symptom do you mean?" in the middle of an
    # answer it had just requested -- twice, in the live audit -- and the
    # patient's actual answer went unrecorded both times.
    # Read from the alignment alone, not from ``active_question``: the intake
    # analyzer consumes and clears the open question before this node runs, so
    # testing for it here always found None and the guard never fired.
    # ``DIRECT_ANSWER`` is only ever produced when a question *was* open and the
    # reply answered it, which is exactly the condition wanted.
    answering_open_question = state.get("answer_alignment") == "DIRECT_ANSWER"
    context = ActionContext.from_agent_state(
        {
            **state,
            "action_loop_state": loop,
            "has_unresolved_reference": (
                not answering_open_question
                and has_anaphoric_reference(str(state.get("query") or ""))
            ),
        }
    )

    result = plan_and_validate(
        context,
        view,
        planner_available=True,
        authorized_patient_id=state.get("patient_id") or state.get("profile_id"),
        action_patient_id=state.get("patient_id") or state.get("profile_id"),
        authorized_session_id=state.get("session_id"),
        action_session_id=state.get("session_id"),
    )

    if result.may_execute and result.action.action_type in {"ASK", "CLARIFY"}:
        loop = _record_ask(loop, result.action.target)
        # Counted across turns, not within one: the budget bounds how long a
        # patient can be kept answering, which is a property of the
        # conversation. Any turn that does not ask resets it, so a case that
        # returns to questioning after a confirmation edit starts fresh.
        #
        # Workflow gates are excluded. Confirming an EHR record is not a
        # clinical question and produces no canonical fact, so counting it fed
        # the no-information-gain circuit breaker two "failed" questions before
        # the conversation had asked a clinical one -- and the breaker then
        # declared the case sufficiently characterised.
        if str(result.action.target or "") not in WORKFLOW_GATE_FIELDS:
            loop["consecutive_questions"] = (
                int(loop.get("consecutive_questions") or 0) + 1
            )
    elif result.may_execute:
        loop["consecutive_questions"] = 0
    # A target asked to the limit is accepted as UNKNOWN rather than re-asked.
    exhausted = [
        target
        for target, count in (loop.get("asked_targets") or {}).items()
        if count >= 2
    ]
    if exhausted:
        loop["accepted_unknown_targets"] = sorted(
            set(loop.get("accepted_unknown_targets") or []) | set(exhausted)
        )

    return {
        "action_loop_state": loop,
        "selected_action": result.action.to_dict() if result.action else None,
        "action_validation": result.to_dict(),
        "action_lifecycle": (
            "BLOCKED"
            if result.outcome == "BLOCKED"
            else "REPLACED"
            if result.outcome == "REPLACED"
            else "VALIDATED"
        ),
        "has_unresolved_reference": context.has_unresolved_reference,
    }


async def execute_selected_action_node(state: AgentState) -> dict[str, Any]:
    """Carry out the action the planner selected and the validator allowed.

    Kept as a separate node from selection so that the audit trail records two
    distinct facts -- what was chosen, and what actually ran. Collapsing them
    would make "ESCALATE was selected" and "the system escalated" the same log
    line, and those are exactly the two things an incident review needs to be
    able to tell apart.
    """
    execution = await execute_action(state, state.get("selected_action"))
    return {
        **execution.state_update,
        "action_lifecycle": execution.lifecycle,
        "action_execution": execution.audit(),
    }


async def update_conversation_memory_node(state: AgentState) -> dict[str, Any]:
    """Write the turn into memory under the write policy, then compact if needed."""
    patient_id = str(state.get("patient_id") or state.get("profile_id") or "")
    session_id = str(state.get("session_id") or "")
    if not patient_id or not session_id:
        # Unscoped memory is memory that could be read by the wrong person.
        return {}

    memory = ConversationMemory.from_dict(state.get("conversation_memory"))
    scope = MemoryScope(patient_id=patient_id, session_id=session_id)
    turn_id = str(state.get("current_turn_id") or "")

    memory.remember(
        str(state.get("query") or ""),
        patient_id=patient_id,
        session_id=session_id,
        turn_id=turn_id,
        source="PATIENT",
    )

    # Clinically notable turns are pinned so summarisation cannot lose them.
    red_flag_status = str(state.get("red_flag_status") or "")
    if red_flag_status in {"CANDIDATE", "CONFIRMED", "SAFETY_FALLBACK"}:
        memory.record_event(
            f"RED_FLAG_{red_flag_status}"
            if red_flag_status != "CANDIDATE"
            else "RED_FLAG_CANDIDATE",
            str(state.get("red_flag_candidate_reason") or "dấu hiệu cần đánh giá"),
            patient_id=patient_id,
            session_id=session_id,
            turn_id=turn_id,
        )
    for key in state.get("pending_reassessment_keys") or []:
        if str(key).startswith("symptom."):
            memory.record_event(
                "NEW_SYMPTOM",
                str(key).removeprefix("symptom."),
                patient_id=patient_id,
                session_id=session_id,
                turn_id=turn_id,
            )
    if state.get("requires_triage_reassessment"):
        memory.record_event(
            "TRIAGE_REASSESSMENT",
            "Thông tin lâm sàng mới làm mất hiệu lực kết luận trước",
            patient_id=patient_id,
            session_id=session_id,
            turn_id=turn_id,
        )

    if memory.needs_summary(scope):
        memory.build_rolling_summary(scope)

    return {"conversation_memory": memory.to_dict()}
