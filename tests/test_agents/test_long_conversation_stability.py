"""Long conversations must not degrade the loop, the memory, or the escalation.

Every test here exists because a defect got past the shorter end-to-end tests.
None of them ran past seven turns, and all three problems below only appear
after that: an action budget meant for one turn that was never reset, an
escalation that a spent budget could suppress, and a pinned-event set that grew
once per turn instead of once per event.

The shape of the bug matters more than the specific numbers. A conversation
that gets longer is the normal case for a distressed patient who answers in
fragments, and "the system quietly stopped acting" is the worst possible
failure mode because silence is indistinguishable from having nothing to do.
"""

from __future__ import annotations

from typing import Any

import pytest

from src.agents.action_validator import validate_action
from src.agents.canonical_state import CanonicalPatientState
from src.agents.clinical_state_view import ClinicalStateView
from src.agents.conversation_memory import ConversationMemory, MemoryScope
from src.agents.next_best_action import (
    MAX_ACTIONS_PER_TURN,
    ActionContext,
    select_next_best_action,
)
from src.agents.nodes.action_planner import (
    plan_next_action_node,
    update_conversation_memory_node,
)
from src.agents.nodes.intake_analyzer import analyze_patient_intake
from src.agents.nodes.readiness_evaluator import evaluate_readiness_node
from src.agents.nodes.redflag_detector import detect_redflag_node

PATIENT = "patient-long"
SESSION = "session-long"


def _empty_view() -> ClinicalStateView:
    return ClinicalStateView(CanonicalPatientState())


async def _turn(state: dict[str, Any], message: str, turn: int) -> dict[str, Any]:
    incoming = {
        **state,
        "query": message,
        "current_turn_id": f"t{turn}",
        "intent": "TRIAGE_NEW_SYMPTOM",
        "patient_id": PATIENT,
        "session_id": SESSION,
        "clinical_memory_confirmation_status": "CONFIRMED",
    }
    merged = {**incoming, **await detect_redflag_node(incoming)}
    merged = {**merged, **await analyze_patient_intake(merged)}
    merged = {**merged, **await evaluate_readiness_node(merged)}
    merged = {**merged, **await plan_next_action_node(merged)}
    return {**merged, **await update_conversation_memory_node(merged)}


# --------------------------------------------------------------------------
# The per-turn action budget is per turn
# --------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_the_planner_still_acts_far_beyond_the_per_turn_budget() -> None:
    """A budget for one turn must not accumulate across a conversation."""
    state: dict[str, Any] = {}
    actions: list[str | None] = []

    for turn in range(1, 21):
        state = await _turn(state, "Tôi vẫn còn đau", turn)
        action = state.get("selected_action") or {}
        actions.append(action.get("action_type"))

    late = actions[MAX_ACTIONS_PER_TURN:]
    assert late, "the run must actually get past the budget"
    assert all(item is not None for item in late), (
        f"planner fell silent after the budget: {actions}"
    )


@pytest.mark.asyncio
async def test_the_turn_action_count_resets_on_each_new_turn() -> None:
    state: dict[str, Any] = {}
    for turn in range(1, 13):
        state = await _turn(state, "Tôi vẫn còn đau", turn)
        loop = state.get("action_loop_state") or {}
        assert loop.get("turn_action_count") == 1


@pytest.mark.asyncio
async def test_repeat_question_limits_still_survive_the_reset() -> None:
    """Resetting the turn budget must not also reset loop prevention."""
    state: dict[str, Any] = {}
    for turn in range(1, 9):
        state = await _turn(state, "Tôi không nhớ", turn)

    loop = state.get("action_loop_state") or {}
    asked = loop.get("asked_targets") or {}
    assert asked, "asked_targets must persist across turns"
    assert all(count <= 2 for count in asked.values()), asked


# --------------------------------------------------------------------------
# A spent budget must never suppress a mandated escalation
# --------------------------------------------------------------------------

@pytest.mark.parametrize("red_flag_status", ["CONFIRMED", "SAFETY_FALLBACK"])
def test_escalation_survives_an_exhausted_action_budget(red_flag_status: str) -> None:
    """Running out of internal actions is our problem, not a clinical finding."""
    context = ActionContext(
        red_flag_status=red_flag_status,
        is_red_flag=red_flag_status == "CONFIRMED",
        turn_action_count=MAX_ACTIONS_PER_TURN + 5,
    )
    proposed = select_next_best_action(context)
    assert proposed.action_type == "ESCALATE"

    result = validate_action(proposed, context, _empty_view())

    assert result.outcome != "BLOCKED", result.block_reason
    assert result.action is not None
    assert result.action.action_type == "ESCALATE"


def test_an_uncertain_red_flag_clarifies_rather_than_escalating() -> None:
    """Pins the actual precedence: UNCERTAIN is resolved, not assumed.

    An unresolved candidate is not yet an emergency, so the selector asks the
    question that would settle it. The candidate itself is carried forward by
    the red-flag node, so declining to escalate here does not drop it.
    """
    context = ActionContext(red_flag_status="UNCERTAIN")

    assert context.safety_state == "REQUIRES_ESCALATION"
    assert select_next_best_action(context).action_type == "CLARIFY"


def test_a_spent_budget_still_blocks_an_ordinary_question() -> None:
    """The budget is only lifted for escalation, never generally."""
    from src.agents.next_best_action import NextBestAction

    context = ActionContext(
        readiness_outcome="NOT_READY",
        decision_relevant_unknowns=("severity_score",),
        turn_action_count=MAX_ACTIONS_PER_TURN + 1,
    )
    action = NextBestAction(
        action_type="ASK",
        rationale_code="MISSING_REQUIRED_FACT",
        target="severity_score",
    )

    result = validate_action(action, context, _empty_view())
    assert result.outcome == "BLOCKED"
    assert result.block_reason == "TURN_ACTION_LIMIT_REACHED"


# --------------------------------------------------------------------------
# Pinned events grow with events, not with turns
# --------------------------------------------------------------------------

def test_a_recurring_event_is_pinned_once_and_counted() -> None:
    """Important events are never summarised away, so they must not pile up."""
    memory = ConversationMemory()
    scope = MemoryScope(patient_id=PATIENT, session_id=SESSION)

    for turn in range(1, 31):
        memory.record_event(
            "NEW_SYMPTOM",
            "chest_pain",
            patient_id=PATIENT,
            session_id=SESSION,
            turn_id=f"t{turn}",
        )

    events = memory.important_events(scope)
    assert len(events) == 1
    assert events[0].occurrence_count == 30
    assert events[0].last_turn_id == "t30"


def test_distinct_events_are_all_kept() -> None:
    memory = ConversationMemory()
    scope = MemoryScope(patient_id=PATIENT, session_id=SESSION)

    for symptom in ("chest_pain", "dyspnea", "nausea"):
        for turn in range(3):
            memory.record_event(
                "NEW_SYMPTOM",
                symptom,
                patient_id=PATIENT,
                session_id=SESSION,
                turn_id=f"t{turn}",
            )

    events = memory.important_events(scope)
    assert {item.content for item in events} == {"chest_pain", "dyspnea", "nausea"}
    assert len(events) == 3


def test_deduplication_is_still_scoped_per_patient() -> None:
    """Two patients reporting the same symptom are two separate events."""
    memory = ConversationMemory()
    for patient in ("patient-A", "patient-B"):
        memory.record_event(
            "NEW_SYMPTOM",
            "chest_pain",
            patient_id=patient,
            session_id=SESSION,
            turn_id="t1",
        )

    for patient in ("patient-A", "patient-B"):
        scope = MemoryScope(patient_id=patient, session_id=SESSION)
        events = memory.important_events(scope)
        assert len(events) == 1
        assert events[0].patient_id == patient
        assert events[0].occurrence_count == 1


def test_occurrence_count_survives_serialisation() -> None:
    memory = ConversationMemory()
    for turn in range(4):
        memory.record_event(
            "RED_FLAG_CANDIDATE",
            "đau ngực",
            patient_id=PATIENT,
            session_id=SESSION,
            turn_id=f"t{turn}",
        )

    restored = ConversationMemory.from_dict(memory.to_dict())
    events = restored.important_events(
        MemoryScope(patient_id=PATIENT, session_id=SESSION)
    )
    assert len(events) == 1
    assert events[0].occurrence_count == 4
    assert events[0].last_turn_id == "t3"


# --------------------------------------------------------------------------
# A 50-turn conversation stays bounded and keeps its clinical content
# --------------------------------------------------------------------------

LONG_CONVERSATION = [
    "Tôi bị đau ngực từ sáng nay",
    "Vâng",
    "Đau khoảng 7/10",
    "Ừ",
    "Tôi cũng hơi khó thở",
    "Cảm ơn bác sĩ",
    "Thật ra không phải 7, mà là 9/10",
    "Vâng ạ",
    "Tôi có tiền sử cao huyết áp",
    "Hôm nay trời mưa quá",
    "Cơn đau lan xuống tay trái",
    "Hiểu rồi",
    "Tôi thấy buồn nôn nữa",
    "Vâng",
    "Con tôi hôm qua cũng ốm",
    "Ừ",
    "Không, tôi không bị nôn",
    "Vâng ạ",
    "Tôi có dị ứng penicillin",
    "Ok",
] * 2


@pytest.mark.asyncio
async def test_a_forty_turn_conversation_stays_bounded_and_keeps_its_facts() -> None:
    state: dict[str, Any] = {}
    for turn, message in enumerate(LONG_CONVERSATION, start=1):
        state = await _turn(state, message, turn)

    scope = MemoryScope(patient_id=PATIENT, session_id=SESSION)
    memory = ConversationMemory.from_dict(state.get("conversation_memory"))

    # Pinned events are proportional to what happened, not to turn count.
    events = memory.important_events(scope)
    assert len(events) < len(LONG_CONVERSATION) // 2, (
        f"{len(events)} pinned events over {len(LONG_CONVERSATION)} turns"
    )

    # The clinically important content is still there.
    view = ClinicalStateView(
        CanonicalPatientState.from_dict(state.get("canonical_state") or {})
    )
    assert view.is_present("symptom.chest_pain")
    assert view.read("severity_score").value == 9, "the correction must win"
    assert view.is_negated("symptom.vomiting"), "an explicit denial is an answer"

    # And the planner is still choosing actions at the end of the conversation.
    assert state.get("selected_action") is not None
