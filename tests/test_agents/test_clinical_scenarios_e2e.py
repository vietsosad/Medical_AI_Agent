"""Seven realistic conversations, driven through the real runtime.

Each scenario is written the way a patient would actually type it, and asserted
on what the system does rather than on which functions it called. Between them
they cover the behaviours that distinguish a triage conversation from a form:
asking different questions for different presentations, reading time correctly,
noticing when new information invalidates an earlier conclusion, and refusing
to treat a remembered emergency as a current one.
"""

from __future__ import annotations

from typing import Any

import pytest

from src.agents.canonical_state import CanonicalPatientState
from src.agents.clinical_state_view import ClinicalStateView
from src.agents.conversation_memory import ConversationMemory, MemoryScope
from src.agents.deepagent_runtime.tools import TurnContext, update_intake_phase
from src.agents.nodes.action_planner import update_conversation_memory_node
from src.agents.nodes.contextual_emergency_detector import (
    ContextualEmergencyAssessment,
    assess_contextual_emergency_node,
)
from src.agents.nodes.redflag_detector import detect_redflag_node

PATIENT = "patient-e2e"
SESSION = "session-e2e"

BASE: dict[str, Any] = {
    "intent": "TRIAGE_NEW_SYMPTOM",
    "clinical_memory_confirmation_status": "CONFIRMED",
    "vital_signs_status": "REVIEWED",
    "patient_id": PATIENT,
    "session_id": SESSION,
}


class _ScriptedValidator:
    """A contextual validator with a fixed verdict.

    The contextual check is the one place these scenarios would otherwise reach
    a language model, which would make them slow, networked and -- worse --
    non-deterministic about a safety decision. Scripting the verdict keeps the
    scenario about the pipeline while leaving the real node, the real
    precedence and the real state transitions in place.
    """

    def __init__(self, *, context_type: str, current: bool) -> None:
        self.context_type = context_type
        self.current = current

    def with_structured_output(self, _schema: Any) -> _ScriptedValidator:
        return self

    async def ainvoke(self, _prompt: str) -> ContextualEmergencyAssessment:
        return ContextualEmergencyAssessment(
            context_type=self.context_type,
            is_current_personal_event=self.current,
            is_time_critical_emergency=self.current,
            confidence=0.95,
            risk_category="CARDIAC" if self.current else "NONE",
            observed_signals=["đau ngực"] if self.current else [],
            evidence_summary="Kết luận ngữ cảnh của bộ kiểm chứng.",
        )


@pytest.fixture(autouse=True)
def _offline_contextual_validator(monkeypatch: pytest.MonkeyPatch) -> None:
    """Default: context says this is not a current personal emergency.

    Scenarios that need the opposite set the state directly, so nothing here
    weakens the safety path -- the node still runs, still decides, and still
    owns the transition.
    """
    monkeypatch.setattr(
        "src.agents.nodes.contextual_emergency_detector.get_deepagent_llm",
        lambda: _ScriptedValidator(context_type="HISTORICAL_OR_QUOTED", current=False),
    )


async def _safety(state: dict[str, Any], query: str, turn_id: str) -> dict[str, Any]:
    """The deterministic safety pass that runs before anything else."""
    incoming = {**BASE, **state, "query": query, "current_turn_id": turn_id}
    merged = {**incoming, **await detect_redflag_node(incoming)}
    return {**merged, **await assess_contextual_emergency_node(merged)}


async def _turn(
    state: dict[str, Any],
    query: str,
    turn_id: str = "t1",
    *,
    with_safety: bool = True,
) -> dict[str, Any]:
    """One full turn: safety, then intake, planning, dispatch, memory."""
    start = await _safety(state, query, turn_id) if with_safety else {
        **BASE, **state, "query": query, "current_turn_id": turn_id
    }
    context = TurnContext(dict(start))
    context.called_tools.update({"assess_contextual_emergency", "classify_request"})
    await update_intake_phase(context)
    memory_update = await update_conversation_memory_node(context.state)
    return {**context.state, **memory_update}


def _view(state: dict[str, Any]) -> ClinicalStateView:
    return ClinicalStateView(
        CanonicalPatientState.from_dict(state.get("canonical_state") or {})
    )


def _action(state: dict[str, Any]) -> str | None:
    return (state.get("selected_action") or {}).get("action_type")


# --------------------------------------------------------------------------
# Scenario A -- possible ACS runs the whole pipeline
# --------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_scenario_a_possible_acs_reaches_evidence_through_the_planner() -> None:
    state = await _turn({}, "Tôi bị đau ngực từ sáng nay", "t1")
    assert _view(state).is_present("symptom.chest_pain")
    # A bare complaint is not a characterised presentation, so the agent asks
    # about the chest pain rather than putting a summary up to be confirmed.
    # The question it chooses is about *this* problem, not the next slot in a
    # fixed order.
    assert _action(state) == "ASK"
    assert state["selected_action"]["target"].startswith(
        ("chest_pain.", "symptom.", "vital.")
    )
    assert "severity_score" in state["provisional_readiness_hints"]["missing_fields"]

    # Confirmation, not completion of an unreviewed questionnaire, authorizes
    # authority retrieval. The reasoner may ask for severity later if the cited
    # decision point actually needs it.
    state = await _turn(
        {**state, "patient_confirmed_intake": True},
        "Vâng đúng rồi",
        "t2",
    )
    assert _action(state) == "RETRIEVE_RAG"
    assert state.get("next_step") == "retrieve_evidence"
    assert state.get("active_question") is None
    # And no ESI has been invented anywhere along the way.
    assert state.get("current_esi_level") is None


# --------------------------------------------------------------------------
# Scenario B -- a benign presentation is not run through a cardiac workup
# --------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_scenario_b_an_ankle_injury_is_not_asked_chest_pain_questions() -> None:
    ankle = await _turn({}, "Tôi bị bong gân mắt cá chân từ hôm qua", "t1")
    chest = await _turn({}, "Tôi bị đau ngực từ sáng nay", "t1")

    ankle_missing = set(
        ankle["provisional_readiness_hints"].get("missing_fields") or []
    )
    chest_missing = set(
        chest["provisional_readiness_hints"].get("missing_fields") or []
    )

    # The chest presentation asks for things the ankle presentation does not.
    assert "severity_score" in chest_missing
    assert chest_missing != ankle_missing
    # The hints stay audit-only: what the chest case actually asks about comes
    # from its problem state, scoped to the chest pain itself.
    chest_targets = chest.get("missing_critical_fields") or []
    assert chest_targets
    assert all(
        target.startswith("chest_pain.") or target.startswith(("symptom.", "vital."))
        for target in chest_targets
    )
    # This phrase is outside the current canonical complaint lexicon, so the
    # integrity gate asks for a canonical complaint; it still never opens any
    # chest-pain profile requirement.
    assert ankle.get("missing_critical_fields") == ["chief_complaint"]
    assert ankle["selected_action"]["target"] == "chief_complaint"
    assert not any(
        target.startswith("chest_pain.")
        for target in (ankle.get("missing_critical_fields") or [])
    )
    assert chest.get("symptom_cluster") == "chest_pain"
    assert ankle.get("symptom_cluster") != "chest_pain"

    # And nothing cardiac was recorded about the ankle patient.
    ankle_view = _view(ankle)
    assert not ankle_view.is_present("symptom.chest_pain")
    assert ankle_view.is_unknown("radiation")


# --------------------------------------------------------------------------
# Scenario C -- temporal reading of a fever that has resolved
# --------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_scenario_c_a_resolved_fever_is_not_a_current_fever() -> None:
    """"Last week I had a 39 fever, it's gone now" is not a fever now."""
    state = await _turn({}, "Tuần trước tôi sốt 39 độ, giờ tôi hết sốt rồi", "t1")
    view = _view(state)

    assert view.is_negated("symptom.fever")
    assert not view.is_present("symptom.fever")

    # The history is not thrown away, it is just not the present.
    canonical = CanonicalPatientState.from_dict(state["canonical_state"])
    assert canonical.was_ever_reported("symptom.fever")
    assert canonical.historical_values("symptom.fever")


@pytest.mark.asyncio
async def test_a_current_fever_is_still_read_as_current() -> None:
    """The resolution rule must not swallow a real symptom."""
    state = await _turn({}, "Tôi đang sốt cao lắm", "t1")

    assert _view(state).is_present("symptom.fever")


# --------------------------------------------------------------------------
# Scenario D -- late dyspnea forces a reassessment
# --------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_scenario_d_late_dyspnea_triggers_reassessment() -> None:
    state = await _turn({"patient_confirmed_intake": True},
                        "Tôi bị đau họng từ hôm qua, đau nhẹ thôi", "t1")
    concluded = {
        **state,
        "current_esi_level": 4,
        "sbar_report": {"situation": "sore throat"},
    }

    after = await _turn(concluded, "Bây giờ tôi thấy khó thở nhiều", "t2")

    assert _action(after) == "REASSESS"
    assert (after.get("action_execution") or {}).get("handler") == "assessment_invalidation"
    assert after.get("current_esi_level") is None, "the stale ESI must not survive"
    assert after.get("sbar_report") is None


# --------------------------------------------------------------------------
# Scenario E -- configured deterministic rules remain authoritative
# --------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_scenario_e_a_historical_match_cannot_clear_the_rule_lock() -> None:
    """Semantic context is enrichment and cannot reverse a rule match."""
    state = await _safety(
        {},
        "Năm ngoái tôi từng bị đau ngực dữ dội, giờ tôi chỉ hỏi thôi",
        "t1",
    )

    assert state.get("red_flag_status") == "CONFIRMED"
    assert state.get("is_red_flag") is True
    assert state.get("current_esi_level") == 2
    assert state.get("emergency_detection_source") == "DETERMINISTIC_REFLEX"
    assert state.get("semantic_emergency_status") == "CLEAR"


@pytest.mark.asyncio
async def test_a_present_tense_red_flag_locks_before_the_validator() -> None:
    """The configured rule owns the safety decision before model work."""
    incoming = {**BASE, "query": "Tôi đang đau ngực dữ dội", "current_turn_id": "t1"}
    screened = await detect_redflag_node(incoming)

    assert screened.get("red_flag_status") == "CONFIRMED"
    assert screened.get("is_red_flag") is True
    assert screened.get("current_esi_level") == 2
    assert screened.get("emergency_detection_source") == "DETERMINISTIC_REFLEX"


# --------------------------------------------------------------------------
# Scenario F -- a confirmed emergency escalates and stops everything else
# --------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_scenario_f_a_confirmed_emergency_executes_escalation() -> None:
    state = await _turn(
        {"is_red_flag": True, "red_flag_status": "CONFIRMED"},
        "Tôi đau ngực dữ dội và khó thở",
        "t1",
        with_safety=False,
    )

    assert _action(state) == "ESCALATE"
    assert state["action_lifecycle"] == "EXECUTED"
    assert (state.get("action_execution") or {}).get("handler") == "emergency_handoff"
    assert state.get("next_step") == "complete"


# --------------------------------------------------------------------------
# Scenario G -- a long conversation keeps what matters
# --------------------------------------------------------------------------

LONG = [
    "Tôi bị đau ngực từ sáng nay",
    "Vâng",
    "Đau khoảng 7 trên 10",
    "Cảm ơn bác sĩ",
    "Tôi có tiền sử cao huyết áp",
    "Hôm nay trời mưa quá",
    "Thật ra đau 9 trên 10 chứ không phải 7",
    "Ừ",
    "Đau lan xuống tay trái",
    "Vâng ạ",
    "Không, tôi không bị nôn",
    "Ok",
    "Tôi thấy buồn nôn nhẹ",
    "Vâng",
    "Tôi có dị ứng penicillin",
    "Cảm ơn nhiều",
]


@pytest.mark.asyncio
async def test_scenario_g_a_long_conversation_preserves_clinical_content() -> None:
    state: dict[str, Any] = {}
    for index, message in enumerate(LONG, start=1):
        state = await _turn(state, message, f"t{index}")

    view = _view(state)
    assert view.is_present("symptom.chest_pain")
    assert view.read("severity_score").value == 9, "the correction must win"
    assert view.read("radiation").value
    assert view.is_present("symptom.nausea")

    memory = ConversationMemory.from_dict(state.get("conversation_memory"))
    scope = MemoryScope(patient_id=PATIENT, session_id=SESSION)

    # Pinned events scale with what happened, not with how long the chat ran.
    events = memory.important_events(scope)
    assert 0 < len(events) < len(LONG)

    # The planner is still choosing and executing at the end.
    assert _action(state) is not None
    assert state.get("action_lifecycle") == "EXECUTED"


@pytest.mark.asyncio
async def test_a_long_conversation_never_leaks_to_another_patient() -> None:
    state: dict[str, Any] = {}
    for index, message in enumerate(LONG[:8], start=1):
        state = await _turn(state, message, f"t{index}")

    memory = ConversationMemory.from_dict(state.get("conversation_memory"))
    other = MemoryScope(patient_id="someone-else", session_id=SESSION)

    assert memory.recent(other) == []
    assert memory.search("đau ngực", other) == []
