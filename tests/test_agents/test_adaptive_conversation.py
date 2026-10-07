"""The conversation is adaptive, and the agent decides when it has enough.

These are the invariants the form-led flow could not hold. Each was observed
failing against the running system before it was written here:

* one complaint used to be enough to put a summary up for confirmation, so the
  patient was handed a form before anything had been asked;
* the patient, not the agent, decided when the information was sufficient;
* a second symptom mentioned mid-conversation restarted intake or was lost;
* a question already answered was asked again.

The pipeline under test is the real one. Only the outside world -- the model
provider -- is replaced, and the intake half of a turn runs no model at all.
"""

from __future__ import annotations

from typing import Any

import pytest

from src.agents.canonical_state import CanonicalPatientState
from src.agents.clinical_state_view import ClinicalStateView
from src.agents.nodes.action_planner import (
    execute_selected_action_node,
    plan_next_action_node,
)
from src.agents.nodes.answer_validator import validate_answer_node
from src.agents.nodes.contradiction_detector import detect_contradictions_node
from src.agents.nodes.fact_extraction import apply_message_to_state
from src.agents.nodes.intake_analyzer import analyze_patient_intake
from src.agents.nodes.readiness_evaluator import (
    evaluate_pre_retrieval_readiness_node,
)
from src.agents.problem_state import build_problem_state
from src.agents.question_planning import plan_questions

_PIPELINE = (
    validate_answer_node,
    analyze_patient_intake,
    detect_contradictions_node,
    evaluate_pre_retrieval_readiness_node,
    plan_next_action_node,
    execute_selected_action_node,
)


class Chat:
    """Drive the intake half of a turn exactly as the runtime drives it."""

    def __init__(self, **overrides: Any) -> None:
        self.state: dict[str, Any] = {
            "session_id": "session-adaptive",
            "patient_id": "patient-adaptive",
            "profile_id": "patient-adaptive",
            "clinical_memory_confirmation_status": "CONFIRMED",
            "vital_signs_status": "NOT_REVIEWED",
            "patient_confirmed_intake": False,
            **overrides,
        }
        self._turn = 0

    async def say(self, message: str) -> dict[str, Any]:
        self._turn += 1
        self.state.update(
            {
                "query": message,
                "current_turn_id": f"t{self._turn}",
                "intent": (
                    "TRIAGE_NEW_SYMPTOM" if self._turn == 1 else "TRIAGE_FOLLOW_UP"
                ),
            }
        )
        for node in _PIPELINE:
            self.state = {**self.state, **await node(self.state)}
        return dict(self.state)

    @property
    def target(self) -> str | None:
        return (self.state.get("selected_action") or {}).get("target")

    @property
    def action(self) -> str | None:
        return (self.state.get("selected_action") or {}).get("action_type")

    def problems(self) -> list[str]:
        view = ClinicalStateView(
            CanonicalPatientState.from_dict(self.state.get("canonical_state"))
        )
        return [item.concept for item in build_problem_state(view).active_problems]


def _view(*messages: str) -> ClinicalStateView:
    state = CanonicalPatientState()
    for index, message in enumerate(messages):
        apply_message_to_state(state, message, turn_id=f"t{index + 1}")
    return ClinicalStateView(state)


# ---------------------------------------------------------------------------
# Problem decomposition
# ---------------------------------------------------------------------------


def test_two_complaints_in_one_sentence_become_two_problems() -> None:
    problem_state = build_problem_state(_view("Tôi bị đau đầu và buồn nôn"))
    concepts = [item.concept for item in problem_state.active_problems]

    assert concepts == ["headache", "nausea"]
    # The one the patient led with is the one the conversation treats as
    # primary, not whichever the lexicon happened to scan first.
    assert problem_state.primary is not None
    assert problem_state.primary.concept == "headache"
    # And each carries its own open questions rather than sharing one checklist.
    assert "onset_time" in problem_state.problem("headache").unknown_relevant_facts
    assert "vomiting" in problem_state.problem("nausea").unknown_relevant_facts


def test_a_global_detail_is_not_copied_onto_every_problem() -> None:
    """"6/10" said about the headache is not a claim about the nausea."""
    problem_state = build_problem_state(
        _view("Tôi bị đau đầu và buồn nôn", "Đau khoảng 6/10")
    )

    assert problem_state.problem("headache").known_facts["severity_score"] == 6
    assert "severity_score" not in problem_state.problem("nausea").known_facts


@pytest.mark.asyncio
async def test_a_new_symptom_mid_conversation_joins_without_restarting() -> None:
    chat = Chat()
    await chat.say("Tôi bị đau đầu và buồn nôn")
    await chat.say("Đau từ sáng nay, khoảng 6/10")
    before = chat.problems()

    after_state = await chat.say("Tôi còn hơi chóng mặt nữa")

    assert chat.problems() == [*before, "dizziness"]
    # Nothing collected earlier was lost.
    problem_state = build_problem_state(
        ClinicalStateView(
            CanonicalPatientState.from_dict(after_state["canonical_state"])
        )
    )
    assert problem_state.problem("headache").known_facts["severity_score"] == 6
    # And the turn is still a question, not a restarted intake.
    assert after_state["response_type"] in {"TEXT", "STRUCTURED_QUESTION"}
    assert after_state["next_step"] == "wait_for_patient"


# ---------------------------------------------------------------------------
# Adaptive questioning
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_a_bare_complaint_is_asked_about_not_handed_a_form() -> None:
    """The regression this phase exists for."""
    chat = Chat()
    state = await chat.say("Tôi bị đau đầu và buồn nôn")

    assert chat.action == "ASK"
    assert state["response_type"] != "INTAKE_REVIEW"
    assert state["clinical_sufficiency"] != "SUFFICIENT_FOR_CONFIRMATION"
    # The question is about one of the patient's own problems.
    assert chat.target is not None
    assert chat.target.startswith(("headache.", "nausea.", "symptom.", "vital."))


@pytest.mark.asyncio
async def test_a_question_already_answered_is_not_asked_again() -> None:
    """No target is put to the patient once its answer is already on record.

    Checked at the moment each question is chosen, which is the only place the
    property is meaningful: a target asked *before* it was answered is the
    conversation working, and one asked *after* is the system not listening.
    """
    chat = Chat()

    def answered_now() -> set[str]:
        problem = build_problem_state(
            ClinicalStateView(
                CanonicalPatientState.from_dict(
                    chat.state.get("canonical_state") or {}
                )
            )
        ).problem("headache")
        if problem is None:
            return set()
        return {
            f"headache.{attribute}"
            for attribute, fact in problem.facts.items()
            if fact.is_answered
        }

    await chat.say("Tôi bị đau đầu")
    for reply in (
        "Từ sáng nay",
        "Không, chưa bao giờ đau như vậy",
        "Không yếu tay chân, không nói khó",
        "Đau tăng dần lên",
    ):
        await chat.say(reply)
        if chat.target:
            assert chat.target not in answered_now(), (
                f"asked {chat.target} after it was already answered"
            )

    # And the exchange really did settle several of them along the way.
    assert len(answered_now()) >= 3


@pytest.mark.asyncio
async def test_onset_answer_from_live_log_is_not_asked_again() -> None:
    """A bare Vietnamese time expression answers the onset question."""
    chat = Chat()

    await chat.say("Tôi hơi sổ mũi, đau họng nhẹ, không sốt, không khó thở, vẫn sinh hoạt bình thường.")
    await chat.say("tối hôm qua")

    assert chat.target != "sore_throat.onset_time"
    assert chat.target != "onset_time"
    view = ClinicalStateView(
        CanonicalPatientState.from_dict(chat.state.get("canonical_state"))
    )
    problem = build_problem_state(view).problem("sore_throat")
    assert problem is not None
    assert problem.facts["onset_time"].is_answered


@pytest.mark.parametrize("reply", ["vừa bị", "mới bị", "sáng nay", "đêm qua", "2 tiếng"])
def test_common_vietnamese_onset_replies_validate(reply: str) -> None:
    from src.agents.nodes.answer_validator import validate_answer_alignment

    result = validate_answer_alignment(reply, {"field": "onset_time"})

    assert result.alignment == "DIRECT_ANSWER"


def test_the_next_question_is_chosen_by_value_not_by_slot_order() -> None:
    """A different presentation asks a different question first."""
    headache = plan_questions(build_problem_state(_view("Tôi bị đau đầu")))
    ankle = plan_questions(build_problem_state(_view("Tôi bị đau lưng")))
    chest = plan_questions(build_problem_state(_view("Tôi bị đau ngực")))

    assert headache.next_question is not None
    assert chest.next_question is not None
    # The chest presentation carries safety probes the back-pain one does not,
    # so their candidate sets differ in kind rather than only in order.
    chest_targets = {item.target for item in chest.candidates}
    ankle_targets = {item.target for item in ankle.candidates}
    assert chest_targets != ankle_targets
    assert any(item.importance == "SAFETY" for item in chest.candidates)
    assert not any(item.importance == "SAFETY" for item in ankle.candidates)


# ---------------------------------------------------------------------------
# Stopping: sufficient is not complete
# ---------------------------------------------------------------------------


def test_sufficient_is_not_complete() -> None:
    """A case reaches the checkpoint with optional detail still unknown.

    The invariant that keeps the conversation from becoming a questionnaire in
    a different order: only what could change the triage decision may block.
    """
    problem_state = build_problem_state(
        _view("Tôi bị đau họng từ hôm qua, đau nhẹ thôi")
    )
    plan = plan_questions(problem_state)

    assert plan.sufficiency in {
        "SUFFICIENT_FOR_CONFIRMATION",
        "USEFUL_BUT_OPTIONAL",
    }
    assert plan.should_ask is False
    # Explicitly incomplete: things are still unknown, and none of them block.
    assert problem_state.problem("sore_throat").unknown_relevant_facts


@pytest.mark.asyncio
async def test_a_case_missing_a_decision_critical_fact_is_not_offered_the_form() -> None:
    chat = Chat()
    state = await chat.say("Tôi bị đau ngực")

    assert state["clinical_sufficiency"] in {
        "SAFETY_CRITICAL_MISSING",
        "DECISION_CRITICAL_MISSING",
    }
    assert state["response_type"] != "INTAKE_REVIEW"
    assert state["intake_confirmation_status"] == "NOT_READY"


def test_an_explicit_dont_know_settles_the_question() -> None:
    """Asking again after "I don't know" is how software says it was not listening."""
    state = CanonicalPatientState()
    apply_message_to_state(state, "Tôi bị đau đầu", turn_id="t1")
    state.record(
        "headache.course",
        "không rõ",
        status="UNCERTAIN",
        turn_id="t2",
        raw_span="tôi không biết",
        note="declined_unknown",
    )

    problem = build_problem_state(ClinicalStateView(state)).problem("headache")
    assert problem is not None
    assert problem.facts["course"].is_answered
    assert "course" not in problem.unknown_relevant_facts


def test_questioning_stops_when_answers_stop_arriving() -> None:
    """A bounded stop, recorded as one rather than dressed up as sufficiency."""
    problem_state = build_problem_state(_view("Tôi bị đau ngực"))
    plan = plan_questions(
        problem_state,
        consecutive_questions=3,
        information_gained_last_turn=False,
    )

    assert plan.should_ask is False
    assert plan.stop_reason == "NO_INFORMATION_GAIN"


def test_the_question_budget_is_a_circuit_breaker_not_a_question_count() -> None:
    problem_state = build_problem_state(_view("Tôi bị đau ngực"))

    within = plan_questions(problem_state, consecutive_questions=3)
    exhausted = plan_questions(
        problem_state,
        consecutive_questions=8,
        max_consecutive_questions=8,
    )

    assert within.should_ask is True
    assert within.stop_reason is None
    assert exhausted.should_ask is False
    assert exhausted.stop_reason == "QUESTION_BUDGET_EXHAUSTED"


# ---------------------------------------------------------------------------
# Objective measurements
# ---------------------------------------------------------------------------


def test_a_vital_the_patient_already_gave_is_not_asked_for() -> None:
    problem_state = build_problem_state(_view("Tôi bị sốt, nhiệt độ 38.5"))
    plan = plan_questions(problem_state)

    assert problem_state.vitals.get("temperature_c") == 38.5
    assert not any(item.target == "vital.temperature_c" for item in plan.candidates)


def test_having_no_way_to_measure_is_an_answer_not_a_gap() -> None:
    problem_state = build_problem_state(_view("Tôi bị sốt"))

    with_device = plan_questions(problem_state, vitals_available=True)
    without_device = plan_questions(problem_state, vitals_available=False)

    assert any(
        item.canonical_key.startswith("vital.") for item in with_device.candidates
    )
    assert not any(
        item.canonical_key.startswith("vital.") for item in without_device.candidates
    )


# ---------------------------------------------------------------------------
# Confirmation is a checkpoint, not a questionnaire
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_the_agent_reaches_the_checkpoint_on_its_own() -> None:
    chat = Chat()
    await chat.say("Tôi bị đau họng từ hôm qua, đau nhẹ thôi")

    assert chat.action == "END"
    assert chat.state["response_type"] == "INTAKE_REVIEW"
    assert chat.state["intake_confirmation_status"] == "AWAITING_CONFIRMATION"
    assert chat.state["intake_summary"]["chief_complaint"]


@pytest.mark.asyncio
async def test_a_symptom_the_patient_mentioned_reaches_the_review() -> None:
    """Whatever the patient said has to be visible where they can correct it.

    "hơi chóng mặt" is the patient reporting mild dizziness, so it belongs in
    the complaint list. What matters for this test either way is that it
    reaches the review at all: a symptom that appears nowhere cannot be
    confirmed, cannot be denied, and gives the patient no sign it was heard.
    """
    chat = Chat()
    await chat.say("Tôi bị đau họng từ hôm qua, đau nhẹ thôi")
    # Raising a new symptom reopens questioning, so the review is reached again
    # by answering rather than by the mention alone.
    await chat.say("Tôi hơi chóng mặt nữa")
    state = chat.state
    for _ in range(8):
        if state.get("response_type") == "INTAKE_REVIEW":
            break
        state = await chat.say("Tôi không rõ")

    assert state["response_type"] == "INTAKE_REVIEW"
    summary = state.get("intake_summary") or {}
    shown = " ".join(
        [
            *(summary.get("chief_complaint") or []),
            *(summary.get("uncertain_symptoms") or []),
            *(summary.get("associated_symptoms") or []),
        ]
    )
    assert "chóng mặt" in shown


@pytest.mark.asyncio
async def test_a_genuinely_hedged_symptom_is_shown_as_uncertain() -> None:
    """Doubt is preserved: "hình như" is not an affirmation."""
    chat = Chat()
    await chat.say("Tôi bị đau họng từ hôm qua, đau nhẹ thôi")
    await chat.say("Hình như tôi bị sốt nữa, tôi không chắc")
    state = chat.state
    for _ in range(8):
        if state.get("response_type") == "INTAKE_REVIEW":
            break
        state = await chat.say("Tôi không rõ")

    summary = state.get("intake_summary") or {}
    assert "sốt" in " ".join(summary.get("uncertain_symptoms") or [])
    assert "sốt" not in " ".join(summary.get("chief_complaint") or [])


@pytest.mark.asyncio
async def test_confirming_does_not_send_the_patient_back_into_questioning() -> None:
    """The checkpoint is sticky; pressing confirm must not reopen the intake."""
    chat = Chat()
    await chat.say("Tôi bị đau họng từ hôm qua, đau nhẹ thôi")
    assert chat.state["response_type"] == "INTAKE_REVIEW"

    chat.state["patient_confirmed_intake"] = True
    state = await chat.say("Tôi xác nhận thông tin trên là chính xác")

    assert state["next_step"] == "retrieve_evidence"
    assert state["clinical_sufficiency"] == "SUFFICIENT_FOR_CONFIRMATION"


@pytest.mark.asyncio
async def test_a_new_problem_after_confirmation_reopens_questioning() -> None:
    """The one thing that should reopen a closed checkpoint."""
    chat = Chat()
    await chat.say("Tôi bị đau họng từ hôm qua, đau nhẹ thôi")
    chat.state["patient_confirmed_intake"] = True
    await chat.say("Tôi xác nhận thông tin trên là chính xác")

    state = await chat.say("Giờ tôi thấy khó thở nữa")

    assert "dyspnea" in chat.problems()
    assert state["next_step"] != "retrieve_evidence"
    assert state["clinical_sufficiency"] in {
        "SAFETY_CRITICAL_MISSING",
        "DECISION_CRITICAL_MISSING",
    }
