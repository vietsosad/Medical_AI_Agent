"""Execute a validated action, and record what actually happened.

Until now the planner chose an action and the pipeline ignored it: routing
branched on ``decision_status`` while ``selected_action`` was written to the
audit trail and read by nothing. That gap is the difference between a system
that plans and a system that merely narrates its plans, and it is also a
safety problem in its own right -- an audit record of "ESCALATE was selected"
means very little if nothing checks that escalation was carried out.

This module closes that gap. It maps each of the eight action types to exactly
one handler, exhaustively, and fails closed on anything it does not recognise.

Three properties are deliberate:

* **No tool names cross the boundary.** The dispatcher takes an
  ``ActionType`` -- a closed enum -- and looks up a handler in a table defined
  here. Nothing can ask it to run an arbitrary node by name, so a compromised
  or confused planner cannot reach a capability the type system does not
  already grant it.

* **Safety sits above dispatch, not inside it.** By the time an action arrives
  here it has passed the validator, and a confirmed emergency has already
  terminated the turn upstream. The dispatcher does not re-decide safety; it
  refuses to execute anything that contradicts it.

* **Proposed is not executed.** The lifecycle is recorded as distinct states so
  that an audit can tell "the planner wanted to escalate" apart from "the
  system escalated". A failure to execute is recorded as a failure, never
  quietly folded into success.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from typing import Any, Literal

from src.agents.conversation_memory import ConversationMemory, MemoryScope
from src.agents.next_best_action import ActionType
from src.agents.nodes.evidence_gate import build_insufficient_evidence_handoff
from src.agents.nodes.patient_confirmation import request_patient_confirmation_node
from src.agents.nodes.question_engine import run_question_engine_node

# Where an action got to. "SELECTED" and "VALIDATED" are recorded by the
# planner; the rest are recorded here.
ActionLifecycle = Literal[
    "SELECTED",
    "VALIDATED",
    "REPLACED",
    "BLOCKED",
    "EXECUTED",
    "EXECUTION_FAILED",
]

# Safety states in which only an escalation may be carried out. Kept in step
# with the validator's own precedence rather than re-derived.
_EMERGENCY_STATES: frozenset[str] = frozenset(
    {"CONFIRMED_RED_FLAG", "SAFETY_FALLBACK", "REQUIRES_ESCALATION"}
)


@dataclass
class ActionExecution:
    """What was attempted, what ran, and how it ended."""

    action_type: ActionType | None
    lifecycle: ActionLifecycle
    handler: str
    state_update: dict[str, Any] = field(default_factory=dict)
    detail: str = ""

    def audit(self) -> dict[str, Any]:
        """Structured, short, and free of patient text or reasoning."""
        return {
            "action_type": self.action_type,
            "lifecycle": self.lifecycle,
            "handler": self.handler,
            "detail": self.detail,
        }


Handler = Callable[[dict[str, Any]], Awaitable[ActionExecution]]


# -------------------------------------------------------------------------
# Handlers. One per action type; each returns a state update, never mutates.
# -------------------------------------------------------------------------

async def _execute_ask(state: dict[str, Any]) -> ActionExecution:
    """Ask the patient for the fact the planner named.

    The question engine still owns the wording. What has changed is that it now
    runs because an action said to ask, rather than because a status code
    happened to be NOT_READY.
    """
    update = await run_question_engine_node(state)
    return ActionExecution(
        action_type="ASK",
        lifecycle="EXECUTED",
        handler="question_engine",
        state_update=update,
    )


async def _execute_clarify(state: dict[str, Any]) -> ActionExecution:
    """Resolve an ambiguity or a contradiction before anything is concluded."""
    update = await run_question_engine_node(state)
    return ActionExecution(
        action_type="CLARIFY",
        lifecycle="EXECUTED",
        handler="question_engine",
        state_update=update,
    )


async def _execute_retrieve_rag(state: dict[str, Any]) -> ActionExecution:
    """Hand the turn to the evidence gate.

    Retrieval itself is not performed here. The gate owns authority filtering,
    scope matching and abstention, and routing through it is the only way those
    checks cannot be skipped.
    """
    return ActionExecution(
        action_type="RETRIEVE_RAG",
        lifecycle="EXECUTED",
        handler="evidence_gate_handoff",
        state_update={"next_step": "retrieve_evidence"},
    )


async def _execute_retrieve_memory(state: dict[str, Any]) -> ActionExecution:
    """Look back at this patient's earlier turns to resolve a reference.

    Scope is rebuilt from the turn's authorised identifiers, not from anything
    the planner supplied, so a planner cannot widen its own read access. If the
    turn has no usable scope the retrieval yields nothing and the conversation
    continues from canonical state -- an unresolved reference is a reason to
    ask, never a reason to guess.
    """
    patient_id = str(state.get("patient_id") or state.get("profile_id") or "")
    session_id = str(state.get("session_id") or "")
    if not patient_id or not session_id:
        update = await run_question_engine_node(state)
        return ActionExecution(
            action_type="RETRIEVE_MEMORY",
            lifecycle="EXECUTED",
            handler="question_engine",
            state_update={**update, "retrieved_memory": []},
            detail="unscoped turn; continued from canonical state",
        )

    memory = ConversationMemory.from_dict(state.get("conversation_memory"))
    scope = MemoryScope(patient_id=patient_id, session_id=session_id)
    hits = memory.search(str(state.get("query") or ""), scope)
    retrieved = [
        {
            "id": item.id,
            "content": item.content,
            "temporal_context": item.temporal_context,
            "source": item.source,
            # Carried so a caller cannot mistake recalled talk for a finding.
            "is_clinical_fact": False,
        }
        for item, _score in hits
    ]
    update = await run_question_engine_node(state)
    return ActionExecution(
        action_type="RETRIEVE_MEMORY",
        lifecycle="EXECUTED",
        handler="conversation_memory_search",
        state_update={**update, "retrieved_memory": retrieved},
        detail=f"{len(retrieved)} item(s) within scope",
    )


async def _execute_reassess(state: dict[str, Any]) -> ActionExecution:
    """Invalidate a conclusion that new information has overtaken.

    The earlier ESI and SBAR are cleared rather than amended. A conclusion that
    was reached without the new fact is not a conclusion about this patient any
    more, and leaving it in place while re-entering assessment would let a
    stale proposal survive into the handoff.
    """
    return ActionExecution(
        action_type="REASSESS",
        lifecycle="EXECUTED",
        handler="assessment_invalidation",
        state_update={
            "current_esi_level": None,
            "preliminary_esi_reasoning": None,
            "sbar_report": None,
            "turn_rag_citations": [],
            "decision_status": "NEEDS_CLARIFICATION",
            "workflow_phase": "REASSESSMENT",
            "next_step": "retrieve_evidence",
            "requires_triage_reassessment": False,
        },
    )


async def _execute_explain(state: dict[str, Any]) -> ActionExecution:
    """Say something without asking for anything.

    Reached when there is nothing left that may be asked -- every remaining
    target has been put to the patient as often as policy allows. The reply
    must not invent the missing value or imply the case is complete, so it
    says plainly that a clinician will follow up.
    """
    return ActionExecution(
        action_type="EXPLAIN",
        lifecycle="EXECUTED",
        handler="insufficient_evidence_handoff",
        state_update={
            **build_insufficient_evidence_handoff(
                "Không thể thu thập thêm dữ kiện bắt buộc sau số lượt hỏi cho phép",
                step=int(state.get("step") or 2),
                handoff_reason="QUESTION_SPACE_EXHAUSTED",
            ),
            "active_question": None,
            "structured_question": None,
            "intake_confirmation_status": "NOT_READY",
        },
    )


async def _execute_escalate(state: dict[str, Any]) -> ActionExecution:
    """Carry out an escalation the safety layer has already established.

    This handler does not decide that an emergency exists and cannot create
    one: ``is_red_flag`` and the ESI are owned by the red-flag lifecycle and the
    contextual validator, both of which run before the planner. In the normal
    path they also end the turn before dispatch is reached. Arriving here means
    the planner is mirroring a safety state that is already in force, so the
    turn is marked terminal and left for output verification.
    """
    return ActionExecution(
        action_type="ESCALATE",
        lifecycle="EXECUTED",
        handler="emergency_handoff",
        state_update={
            "workflow_phase": "HANDOFF",
            "next_step": "complete",
        },
    )


async def _execute_end(state: dict[str, Any]) -> ActionExecution:
    """Stop asking, and move the case toward its conclusion.

    Ending does not conclude anything by itself. Intake still has to be
    confirmed by the patient, and the ESI still has to come from the evidence
    gate and the reasoner, so this either asks for confirmation or hands off to
    retrieval. It never writes an ESI.
    """
    if state.get("patient_confirmed_intake") is not True:
        update = await request_patient_confirmation_node(state)
        return ActionExecution(
            action_type="END",
            lifecycle="EXECUTED",
            handler="patient_confirmation",
            state_update=update,
        )
    return ActionExecution(
        action_type="END",
        lifecycle="EXECUTED",
        handler="evidence_gate_handoff",
        state_update={"next_step": "retrieve_evidence"},
    )


# The whole dispatch surface. A closed table, not a name lookup: an action type
# that is not a key here cannot be executed, by construction.
_HANDLERS: dict[ActionType, Handler] = {
    "ASK": _execute_ask,
    "CLARIFY": _execute_clarify,
    "RETRIEVE_RAG": _execute_retrieve_rag,
    "RETRIEVE_MEMORY": _execute_retrieve_memory,
    "REASSESS": _execute_reassess,
    "EXPLAIN": _execute_explain,
    "ESCALATE": _execute_escalate,
    "END": _execute_end,
}


def _fail_closed(reason: str, state: dict[str, Any]) -> ActionExecution:
    """Give the patient a safe, honest answer and hand off to a clinician."""
    return ActionExecution(
        action_type=None,
        lifecycle="EXECUTION_FAILED",
        handler="insufficient_evidence_handoff",
        state_update=build_insufficient_evidence_handoff(
            reason,
            step=int(state.get("step") or 2),
            handoff_reason="ACTION_EXECUTION_FAILED",
        ),
        detail=reason,
    )


async def execute_action(
    state: dict[str, Any],
    action: dict[str, Any] | None,
) -> ActionExecution:
    """Run the validated action this turn selected.

    ``action`` is the serialized ``NextBestAction`` the validator approved or
    substituted. A missing action means the validator blocked everything, which
    is a safe outcome for the decision but not a safe outcome for the patient,
    who is still waiting: the turn fails closed to a clinician handoff rather
    than returning silence.
    """
    if not action:
        return _fail_closed(
            "Không có hành động hợp lệ nào được phê duyệt cho lượt này",
            state,
        )

    action_type = action.get("action_type")

    # Safety precedence is re-checked at the point of execution, not merely
    # trusted from selection time. If an emergency is in force, the only thing
    # that may run is the escalation -- and a dispatcher that quietly executed
    # something else would defeat every check upstream of it.
    if _emergency_in_force(state) and action_type != "ESCALATE":
        return ActionExecution(
            action_type=action_type,
            lifecycle="BLOCKED",
            handler="emergency_precedence",
            state_update={},
            detail=(
                f"{action_type} refused; an emergency permits only escalation"
            ),
        )

    handler = _HANDLERS.get(action_type)  # type: ignore[arg-type]
    if handler is None:
        return _fail_closed(
            f"Loại hành động không được hỗ trợ: {action_type}",
            state,
        )

    try:
        # The executor receives the action that was actually validated. Pass
        # that exact object to handlers through an immutable state overlay so
        # the question engine cannot accidentally follow a stale planner
        # target left on state (and direct callers behave like the runtime).
        execution_state = {**state, "selected_action": dict(action)}
        return await handler(execution_state)
    except Exception as exc:
        # An execution failure is reported as one. It never becomes a
        # fabricated answer, and never looks like a successful turn.
        return _fail_closed(
            f"Hành động {action_type} không thực hiện được: {type(exc).__name__}",
            state,
        )


def _emergency_in_force(state: dict[str, Any]) -> bool:
    if state.get("is_red_flag"):
        return True
    return str(state.get("red_flag_status") or "") in {
        "CONFIRMED",
        "SAFETY_FALLBACK",
        "UNCERTAIN",
    }


def emergency_states() -> frozenset[str]:
    """Exposed for tests that assert precedence rather than re-implement it."""
    return _EMERGENCY_STATES
