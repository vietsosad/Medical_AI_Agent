"""Regressions for every defect the live conversational audit found.

Each test here reproduces a failure that was observed against the running
system -- real database, real LLM provider, real retrieval corpus -- during the
full audit recorded in ``docs/deep_agent_audit/``. The transcript that produced
each one is named in the test, so a future change that reintroduces the bug
fails against evidence rather than against an opinion.

The pipeline under test is the real intake pipeline. Only the model provider is
absent, and the intake half of a turn runs no model at all.
"""

from __future__ import annotations

from typing import Any

import pytest

from src.agents.canonical_state import CanonicalPatientState
from src.agents.clinical_state_view import ClinicalStateView
from src.agents.confirmation_lifecycle import evaluate_confirmation, fact_snapshot
from src.agents.nodes.action_planner import (
    execute_selected_action_node,
    plan_next_action_node,
)
from src.agents.nodes.answer_validator import validate_answer_node
from src.agents.nodes.contradiction_detector import detect_contradictions_node
from src.agents.nodes.fact_extraction import (
    extract_symptom_facts,
    symptom_key_for_phrase,
)
from src.agents.nodes.intake_analyzer import analyze_patient_intake
from src.agents.nodes.readiness_evaluator import (
    WORKFLOW_GATE_FIELDS,
    evaluate_pre_retrieval_readiness_node,
)

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
            "session_id": "session-audit",
            "patient_id": "patient-audit",
            "profile_id": "patient-audit",
            "clinical_memory_confirmation_status": "CONFIRMED",
            "vital_signs_status": "NOT_REVIEWED",
            "patient_confirmed_intake": False,
            **overrides,
        }
        self._turn = 0

    async def say(self, message: str, **payload: Any) -> dict[str, Any]:
        self._turn += 1
        self.state.update(
            {
                "query": message,
                "current_turn_id": f"t{self._turn}",
                "intent": (
                    "TRIAGE_NEW_SYMPTOM" if self._turn == 1 else "TRIAGE_FOLLOW_UP"
                ),
                **payload,
            }
        )
        for node in _PIPELINE:
            self.state = {**self.state, **await node(self.state)}
        return dict(self.state)

    @property
    def target(self) -> str | None:
        return (self.state.get("selected_action") or {}).get("target")


def _view(*messages: str) -> ClinicalStateView:
    from src.agents.nodes.fact_extraction import apply_message_to_state

    state = CanonicalPatientState()
    for index, message in enumerate(messages, start=1):
        apply_message_to_state(state, message, turn_id=f"t{index}")
    return ClinicalStateView(state)


# ---------------------------------------------------------------------------
# F-03  Accent folding invented symptoms out of ordinary words.
# Transcript: eval/conversations/before/S02_headache_nausea.json, turn 1.
# ---------------------------------------------------------------------------

def test_confirming_an_ehr_record_does_not_report_a_cough() -> None:
    """"hồ sơ" folds to "ho so"; "ho" is the lexicon's word for a cough.

    Live, this put ``symptom.cough`` into canonical state, added "ho" to the
    problem list, characterised it, and carried it into the review -- a
    fabricated clinical finding created by the patient answering a workflow
    form.
    """
    facts = extract_symptom_facts("Đúng, tôi xác nhận hồ sơ sức khỏe hiện tại.")
    assert [item.key for item in facts] == []
    assert symptom_key_for_phrase("hồ sơ sức khỏe") is None


def test_a_little_bit_is_not_fainting() -> None:
    """"một xíu" folds onto "xỉu" (syncope). Same class of defect, worse."""
    facts = extract_symptom_facts("Tôi đau một xíu thôi")
    assert "symptom.syncope" not in {item.key for item in facts}


def test_unaccented_typing_still_reports_the_symptom() -> None:
    """The guard must not cost real reports from people who type plainly."""
    facts = extract_symptom_facts("toi bi ho tu hom qua")
    assert "symptom.cough" in {item.key for item in facts}
    accented = extract_symptom_facts("Tôi bị ho khan hai hôm nay")
    assert "symptom.cough" in {item.key for item in accented}


# ---------------------------------------------------------------------------
# F-05  "hơi" was read as doubt, so a stated complaint could never be given.
# Transcript: eval/conversations/before/S07_dyspnea.json.
# ---------------------------------------------------------------------------

def test_mild_is_not_doubt() -> None:
    view = _view("Mấy hôm nay tôi hơi khó thở khi leo cầu thang")
    assert view.read("symptom.dyspnea").status == "KNOWN"


def test_genuine_doubt_is_still_uncertain() -> None:
    view = _view("Hình như tôi bị sốt, tôi không chắc")
    assert view.read("symptom.fever").status == "UNCERTAIN"


def test_sweating_does_not_hedge_the_symptom_after_it() -> None:
    """"vã mồ hôi" contains "hoi"; a substring test hedged whatever followed."""
    view = _view("Tôi vã mồ hôi và khó thở")
    assert view.read("symptom.dyspnea").status == "KNOWN"


@pytest.mark.asyncio
async def test_a_hedged_complaint_does_not_end_in_a_handoff() -> None:
    """The patient described the same symptom three times and was handed off.

    Live, every reply was read as "no complaint given", the target hit its
    repeat limit, and the turn produced a clinician handoff whose reason was
    ``QUESTION_SPACE_EXHAUSTED`` -- which is not a clinical finding and not
    what happened.
    """
    chat = Chat()
    await chat.say("Mấy hôm nay tôi hơi khó thở khi leo cầu thang")
    assert chat.state.get("handoff_reason") is None
    assert "chief_complaint" not in chat.state["missing_critical_fields"]


# ---------------------------------------------------------------------------
# F-01  Confirmation was owned by the request payload, so it un-confirmed
#       itself on the next ordinary message.
# Transcript: eval/conversations/before/S01_headache.json (STUCK_ON_CONFIRMATION).
# ---------------------------------------------------------------------------

def test_adding_a_fact_after_confirmation_does_not_invalidate_it() -> None:
    """Answering one more question strengthens the summary; it does not undo it."""
    before = _view("Tôi bị đau đầu từ sáng nay")
    state = {
        "patient_confirmed_intake": True,
        "confirmed_fact_snapshot": fact_snapshot(before),
    }
    after = _view("Tôi bị đau đầu từ sáng nay", "Đau khoảng 6 trên 10")
    result = evaluate_confirmation(
        state, after, newly_mentioned=[], unresolved_contradictions=[]
    )
    assert result["patient_confirmed_intake"] is True
    assert result["confirmation_stale_reason"] is None


def test_correcting_a_confirmed_fact_invalidates_the_confirmation() -> None:
    """§17: "thực ra đau bắt đầu tối qua" must reopen the checkpoint."""
    before = _view("Tôi bị đau đầu từ sáng nay")
    state = {
        "patient_confirmed_intake": True,
        "confirmed_fact_snapshot": fact_snapshot(before),
    }
    after = _view(
        "Tôi bị đau đầu từ sáng nay",
        "Thực ra đau bắt đầu từ tối qua, không phải sáng nay",
    )
    result = evaluate_confirmation(
        state, after, newly_mentioned=[], unresolved_contradictions=[]
    )
    assert result["patient_confirmed_intake"] is False
    assert result["confirmation_stale_reason"] in {
        "FACT_SUPERSEDED",
        "CONTRADICTION",
    }


def test_a_new_problem_after_confirmation_invalidates_it() -> None:
    before = _view("Tôi bị đau đầu từ sáng nay")
    state = {
        "patient_confirmed_intake": True,
        "confirmed_fact_snapshot": fact_snapshot(before),
    }
    after = _view("Tôi bị đau đầu từ sáng nay", "Tôi còn chóng mặt nữa")
    result = evaluate_confirmation(
        state,
        after,
        newly_mentioned=["dizziness"],
        unresolved_contradictions=[],
    )
    assert result["patient_confirmed_intake"] is False
    assert result["confirmation_stale_reason"] == "NEW_PROBLEM"


def test_a_confirmation_with_no_snapshot_is_not_treated_as_stale() -> None:
    """A recovered session, or a client that confirms and describes at once.

    There is no record of what was confirmed, so there is no evidence anything
    changed. Inventing staleness here sent a first turn straight back to the
    review it had just answered.
    """
    view = _view("Tôi bị đau họng từ hôm qua")
    result = evaluate_confirmation(
        {"patient_confirmed_intake": True},
        view,
        newly_mentioned=["sore_throat"],
        unresolved_contradictions=[],
    )
    assert result["patient_confirmed_intake"] is True


def test_a_contradiction_always_invalidates_a_confirmation() -> None:
    view = _view("Tôi bị đau đầu từ sáng nay")
    result = evaluate_confirmation(
        {"patient_confirmed_intake": True, "confirmed_fact_snapshot": {}},
        view,
        newly_mentioned=[],
        unresolved_contradictions=[{"field": "onset_time"}],
    )
    assert result["patient_confirmed_intake"] is False
    assert result["confirmation_stale_reason"] == "CONTRADICTION"


# ---------------------------------------------------------------------------
# F-02  Workflow gates were counted as clinical questions, so the
#       no-information-gain breaker declared the case sufficient before a
#       single clinical question had been asked.
# Transcript: eval/conversations/before/S02_headache_nausea.json, turns 0-2.
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_the_ehr_review_is_not_the_first_thing_asked() -> None:
    """A patient with a headache is asked about the headache first."""
    chat = Chat(clinical_memory_confirmation_status="NOT_REVIEWED")
    await chat.say("Tôi bị đau đầu và buồn nôn.")
    assert chat.target not in WORKFLOW_GATE_FIELDS
    assert chat.target is not None


@pytest.mark.asyncio
async def test_workflow_turns_do_not_exhaust_the_question_budget() -> None:
    """Two EHR turns used to read as two failed questions and stop questioning."""
    chat = Chat(clinical_memory_confirmation_status="NOT_REVIEWED")
    await chat.say("Tôi bị đau đầu và buồn nôn.")
    loop = chat.state.get("action_loop_state") or {}
    assert int(loop.get("consecutive_questions") or 0) <= 1
    assert chat.state.get("question_plan", {}).get("stop_reason") != (
        "NO_INFORMATION_GAIN"
    )


@pytest.mark.asyncio
async def test_a_first_turn_does_not_go_straight_to_the_review() -> None:
    """Live, every scenario reached the confirmation form with zero questions."""
    chat = Chat(clinical_memory_confirmation_status="NOT_REVIEWED")
    state = await chat.say("Tôi bị đau đầu và buồn nôn.")
    assert state["response_type"] != "INTAKE_REVIEW"
    assert state["clinical_sufficiency"] in {
        "SAFETY_CRITICAL_MISSING",
        "DECISION_CRITICAL_MISSING",
    }


# ---------------------------------------------------------------------------
# F-06  A repeated question was repeated verbatim, with no sign it was a
#       clarification rather than the planner having forgotten.
# Transcript: eval/conversations/before/S02_headache_nausea.json, turns 5 and 7.
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_a_re_asked_target_is_marked_and_reworded() -> None:
    from src.agents.nodes.question_engine import run_question_engine_node

    state = {
        "session_id": "s",
        "clinical_blueprint": {"chief_complaint": ["đau đầu"]},
        "missing_critical_fields": ["severity_score"],
        "selected_action": {"action_type": "ASK", "target": "severity_score"},
        "action_loop_state": {"asked_targets": {"severity_score": 2}},
    }
    update = await run_question_engine_node(state)
    assert update["active_question"]["question_type"] == "CLARIFICATION"
    assert "hỏi lại" in update["response"]

    first = await run_question_engine_node(
        {**state, "action_loop_state": {"asked_targets": {"severity_score": 1}}}
    )
    assert first["active_question"]["question_type"] == "QUESTION"
    assert first["response"] != update["response"]


# ---------------------------------------------------------------------------
# F-14  The reasoner cancelled the confirmation just to ask one more question,
#       so answering it put the patient back at the review. Forever.
# Transcript: eval/conversations/after/S01_headache.json (first fix pass).
# ---------------------------------------------------------------------------

def test_requesting_one_more_fact_does_not_cancel_the_confirmation() -> None:
    from src.agents.nodes.triage_reasoner import _patient_info_result

    result = _patient_info_result(
        "severity_score",
        "Mức độ đau quyết định nhánh phân loại",
        citation_ids=["ESI-1"],
    )
    assert "patient_confirmed_intake" not in result
    # The retrieval snapshot *is* stale: it was built without the fact.
    assert result["evidence_status"] == "NOT_REQUESTED"
    assert result["evidence_requested_fact"] == "severity_score"


def test_a_contradiction_from_the_reasoner_still_cancels_it() -> None:
    from src.agents.nodes.triage_reasoner import _contradiction_result

    result = _contradiction_result({"unresolved_contradictions": [{"field": "onset_time"}]})
    assert result["patient_confirmed_intake"] is False


# ---------------------------------------------------------------------------
# F-13  The deterministic completion path could not reach reasoning once the
#       supervisor model had called retrieval itself and then timed out.
# Transcript: eval/conversations/after/S01_headache.json turns 5-6 (stale reply).
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_reasoning_completes_even_when_the_model_stopped_after_retrieval() -> None:
    from src.agents.deepagent_runtime import tools as runtime_tools

    ran: list[str] = []

    async def _fake_reasoning(context: Any) -> dict[str, Any]:
        ran.append("reasoning")
        context.called_tools.add("reason_and_prepare_handoff")
        return {}

    original = runtime_tools.reasoning_phase
    runtime_tools.reasoning_phase = _fake_reasoning
    try:
        context = runtime_tools.TurnContext(
            {
                "intent": "TRIAGE_NEW_SYMPTOM",
                # What the state looks like after the *model* ran retrieval and
                # the evidence gate authorised reasoning.
                "next_step": "triage_reasoner",
                "red_flag_status": "NO_CANDIDATE",
            }
        )
        context.called_tools.update(
            {
                "assess_contextual_emergency",
                "classify_request",
                "update_intake",
                "retrieve_clinical_evidence",
                "verify_clinical_output",
            }
        )
        await runtime_tools.run_remaining_required_tools(context)
    finally:
        runtime_tools.reasoning_phase = original

    assert ran == ["reasoning"]


# ---------------------------------------------------------------------------
# F-17  A denial became an associated symptom, and was read back as one.
# Transcript: eval/conversations/fix_pass1/S01_headache.json, turn 10.
# ---------------------------------------------------------------------------

def test_a_negative_answer_is_not_an_associated_symptom() -> None:
    from src.agents.nodes.intake_analyzer import (
        NO_ASSOCIATED_SYMPTOM_PHRASE,
        extract_blueprint_deterministically,
    )

    updated = extract_blueprint_deterministically(
        "Không có dấu hiệu nào đi kèm.",
        {"chief_complaint": ["đau đầu"]},
        {"field": "associated_symptoms"},
        "DIRECT_ANSWER",
    )
    associated = updated["associated_symptoms"]
    # The slot is settled, so the question stops being asked ...
    assert associated == [NO_ASSOCIATED_SYMPTOM_PHRASE]
    # ... and the patient's sentence did not become a clinical entity.
    assert not any("dấu hiệu nào đi kèm" in item for item in associated)


# ---------------------------------------------------------------------------
# F-18  After confirmation the reasoner walked its whole 32-target menu one
#       question at a time and never concluded. SUFFICIENT is not COMPLETE.
# Transcript: eval/conversations/after/S01_headache.json (second fix pass),
#             turns 5-14: severity, associated, vitals, chest pain, BP,
#             dyspnoea, temperature, SpO2, nausea -- all post-confirmation.
# ---------------------------------------------------------------------------

def test_the_reasoner_has_a_bounded_question_budget() -> None:
    from src.config import get_settings

    assert get_settings().evidence_question_budget >= 1


@pytest.mark.asyncio
async def test_the_reasoner_stops_asking_once_the_budget_is_spent() -> None:
    from src.agents.nodes import triage_reasoner
    from src.config import get_settings

    budget = int(get_settings().evidence_question_budget)
    captured: dict[str, Any] = {}

    class _Model:
        def with_structured_output(self, _schema: Any) -> Any:
            return self

        async def ainvoke(self, prompt: str) -> Any:
            captured["prompt"] = prompt
            return triage_reasoner.TriageEvaluation(
                decision="NEED_MORE_PATIENT_INFO",
                requested_fact="severity_score",
                reasoning="Cần thêm mức độ đau để chọn nhánh phân loại phù hợp.",
                uncertainty_reasons=["mức độ chưa rõ"],
                citation_ids=["ESI-1"],
                matched_criteria=[],
            )

    original = triage_reasoner.get_resilient_llm
    triage_reasoner.get_resilient_llm = lambda **_kwargs: _Model()
    try:
        state = {
            "action_loop_state": {"evidence_questions": budget},
            "retrieved_evidence": [
                {
                    "citation_id": "ESI-1",
                    "protocol_code": "P1",
                    "protocol_content": "criteria",
                    "protocol_criteria": ["c1"],
                }
            ],
            "turn_rag_citations": [{"id": "ESI-1"}],
            "canonical_state": {},
            "clinical_blueprint": {"chief_complaint": ["đau đầu"]},
            "evidence_status": "RETRIEVED",
            "evidence_authority_status": "AUTHORIZED",
            "patient_confirmed_intake": True,
        }
        update = await triage_reasoner.run_triage_reasoner_node(state)
    finally:
        triage_reasoner.get_resilient_llm = original

    assert "TUYỆT ĐỐI không chọn" in captured["prompt"]
    assert update["handoff_reason"] == "EVIDENCE_QUESTION_BUDGET_EXHAUSTED"
    # A budget stop is not a claim that the evidence was insufficient.
    assert update["decision_status"] == "INSUFFICIENT_EVIDENCE"


# ---------------------------------------------------------------------------
# F-20  The router threw away the open question whenever a reply carried a
#       symptom word, so the answer never bound and the question came back.
# Transcript: eval/conversations/after/S01_headache.json (second fix pass),
#             turns 1-3: "Không, tôi từng đau hơn hồi năm ngoái" answered
#             "is this the worst headache of your life?" and was asked again.
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_a_negative_answer_binds_even_when_it_mentions_pain() -> None:
    from src.agents.nodes.intake_analyzer import analyze_patient_intake

    state = {
        "query": "Không, tôi từng đau hơn hồi năm ngoái.",
        "current_turn_id": "t3",
        # What the live router returns for this reply: it contains "đau".
        "intent": "TRIAGE_NEW_SYMPTOM",
        "answer_alignment": "DIRECT_ANSWER",
        "active_question": {
            "field": "headache.worst_ever",
            "question_id": "headache.worst_ever",
        },
        "canonical_state": {},
        "clinical_blueprint": {"chief_complaint": ["đau đầu"]},
    }
    update = await analyze_patient_intake(state)
    facts = (update.get("canonical_state") or {}).get("facts") or {}
    assert "headache.worst_ever" in facts, (
        "a clear 'no' must bind to the question that was asked"
    )
    observation = facts["headache.worst_ever"]["observations"][-1]
    assert observation["status"] == "NEGATED"


# ---------------------------------------------------------------------------
# F-19  The final proposal was written to a Vietnamese patient in English,
#       in third-person clinical prose, because the authority corpus is
#       English.
# Transcript: eval/conversations/after/S01_headache.json turn 8 (sanity run).
# ---------------------------------------------------------------------------

def test_the_reasoner_is_told_to_answer_the_patient_in_vietnamese() -> None:
    from src.agents.nodes.triage_reasoner import TriageEvaluation

    description = TriageEvaluation.model_fields["reasoning"].description or ""
    assert "TIẾNG VIỆT" in description


# ---------------------------------------------------------------------------
# F-22  A symptom probe is rendered through the legacy associated-symptoms
#       slot, so its answer settled the slot and left the symptom UNKNOWN --
#       and the probe was asked again.
# Transcript: eval/conversations/fix_pass3/S02_headache_nausea.json turns 8-9.
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_a_symptom_probe_answer_binds_to_the_symptom() -> None:
    from src.agents.nodes.intake_analyzer import analyze_patient_intake

    state = {
        "query": "Không có.",
        "current_turn_id": "t9",
        "intent": "TRIAGE_FOLLOW_UP",
        "answer_alignment": "DIRECT_ANSWER",
        # Exactly what the question engine emits for a symptom probe.
        "active_question": {
            "field": "associated_symptoms",
            "question_id": "associated_symptoms",
            "semantic_target": "symptom.chest_pain",
            "options_type": "single",
        },
        "canonical_state": {},
        "clinical_blueprint": {"chief_complaint": ["đau đầu"]},
    }
    update = await analyze_patient_intake(state)
    facts = (update.get("canonical_state") or {}).get("facts") or {}
    assert "symptom.chest_pain" in facts, (
        "a probe answered 'no' must settle the symptom it asked about"
    )
    assert facts["symptom.chest_pain"]["observations"][-1]["status"] == "NEGATED"


# ---------------------------------------------------------------------------
# F-21  An anaphor inside an answer to an open question was treated as an
#       unresolved reference, so the agent interrupted its own question to ask
#       which symptom the patient meant.
# Transcript: eval/conversations/fix_pass3/S03_headache_nausea_dizziness.json
#             turns 3-6.
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_an_anaphor_in_an_answer_is_not_an_unresolved_reference() -> None:
    from src.agents.nodes.action_planner import plan_next_action_node

    state = {
        "session_id": "s",
        "patient_id": "p",
        "profile_id": "p",
        "query": "Không có, tôi không có triệu chứng đó.",
        "current_turn_id": "t4",
        "intent": "TRIAGE_FOLLOW_UP",
        "answer_alignment": "DIRECT_ANSWER",
        # The intake analyzer has already consumed and cleared the open
        # question by the time the planner runs -- which is exactly why the
        # guard must read the alignment rather than the question.
        "active_question": None,
        "readiness_outcome": "NOT_READY",
        "missing_critical_fields": ["headache.course"],
        "canonical_state": {},
    }
    update = await plan_next_action_node(state)
    assert update["has_unresolved_reference"] is False
    assert (update["selected_action"] or {}).get("target") != "entity_reference"


@pytest.mark.asyncio
async def test_a_bare_anaphor_with_no_open_question_still_asks() -> None:
    """The guard must not remove the case it was built for."""
    from src.agents.nodes.action_planner import plan_next_action_node

    state = {
        "session_id": "s",
        "patient_id": "p",
        "profile_id": "p",
        "query": "Cái đó nặng hơn rồi.",
        "current_turn_id": "t2",
        "intent": "TRIAGE_FOLLOW_UP",
        "answer_alignment": "NOT_APPLICABLE",
        "active_question": None,
        "readiness_outcome": "NOT_READY",
        "missing_critical_fields": ["headache.course"],
        "canonical_state": {},
    }
    update = await plan_next_action_node(state)
    assert update["has_unresolved_reference"] is True
