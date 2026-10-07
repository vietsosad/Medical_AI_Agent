"""Planner targets must control questions and contradiction resolution."""

from __future__ import annotations

from typing import Any

import pytest

from src.agents.action_execution import execute_action
from src.agents.canonical_state import CanonicalPatientState
from src.agents.deepagent_runtime.tools import TurnContext, update_intake_phase
from src.agents.nodes.intake_analyzer import analyze_patient_intake
from src.agents.nodes.question_engine import (
    build_targeted_question,
    run_question_engine_node,
)


BASE: dict[str, Any] = {
    "intent": "TRIAGE_NEW_SYMPTOM",
    "clinical_memory_confirmation_status": "CONFIRMED",
    "vital_signs_status": "REVIEWED",
    "patient_id": "patient-target",
    "session_id": "session-target",
}


@pytest.mark.asyncio
async def test_selected_target_overrides_the_legacy_fixed_question_order() -> None:
    result = await run_question_engine_node(
        {
            "clinical_blueprint": {"chief_complaint": ["đau ngực"]},
            "missing_critical_fields": ["onset_time", "severity_score"],
            "selected_action": {
                "action_type": "ASK",
                "target": "severity_score",
            },
        }
    )

    assert result["active_question"]["field"] == "severity_score"
    assert "0 đến 10" in result["response"]
    assert len(result["messages"]) == 1


@pytest.mark.asyncio
async def test_explicit_target_api_can_be_reused_without_rewriting_state() -> None:
    result = await run_question_engine_node(
        {
            "clinical_blueprint": {"chief_complaint": ["đau ngực"]},
            "missing_critical_fields": ["severity_score", "onset_time"],
            "selected_action": {"action_type": "ASK", "target": "severity_score"},
        },
        target="onset_time",
    )

    assert result["active_question"]["field"] == "onset_time"
    assert "bắt đầu" in result["response"]


@pytest.mark.asyncio
async def test_an_unsupported_target_falls_back_without_leaking_it() -> None:
    result = await run_question_engine_node(
        {
            "clinical_blueprint": {},
            "missing_critical_fields": ["chief_complaint", "onset_time"],
            "selected_action": {
                "action_type": "ASK",
                "target": "symptom.favourite_colour",
            },
        }
    )

    assert result["active_question"]["field"] == "chief_complaint"
    assert "favourite" not in result["response"]
    assert "symptom." not in result["response"]


def test_canonical_symptom_target_builds_one_bounded_question() -> None:
    question = build_targeted_question("symptom.dyspnea", {}, {})

    assert question is not None
    assert question.field == "associated_symptoms"
    assert "khó thở" in question.text
    assert question.structured_payload is not None
    assert len(question.structured_payload["options"]) == 3


@pytest.mark.asyncio
async def test_executor_passes_the_exact_validated_action_to_question_engine() -> None:
    execution = await execute_action(
        {
            "clinical_blueprint": {"chief_complaint": ["đau ngực"]},
            "missing_critical_fields": ["onset_time", "severity_score"],
            "selected_action": {"action_type": "ASK", "target": "onset_time"},
        },
        {
            "action_type": "ASK",
            "rationale_code": "DECISION_RELEVANT_UNKNOWN",
            "target": "severity_score",
        },
    )

    assert execution.lifecycle == "EXECUTED"
    assert execution.state_update["active_question"]["field"] == "severity_score"


@pytest.mark.asyncio
async def test_confirmed_runtime_retrieves_before_provisional_severity_question() -> None:
    context = TurnContext(
        {
            **BASE,
            "query": "Tôi bị đau ngực",
            "current_turn_id": "t1",
            "patient_confirmed_intake": True,
        }
    )
    context.called_tools.update({"assess_contextual_emergency", "classify_request"})

    await update_intake_phase(context)

    assert context.state["selected_action"]["action_type"] == "RETRIEVE_RAG"
    assert context.state["decision_status"] == "READY_FOR_EVIDENCE"
    assert context.state["next_step"] == "retrieve_evidence"
    assert context.state.get("active_question") is None
    # The old profile remains inspectable, but it cannot choose the question
    # before ESI authority has been retrieved.
    hints = context.state["provisional_readiness_hints"]
    assert hints["non_blocking"] is True
    assert "severity_score" in hints["missing_fields"]
    assert context.state["missing_critical_fields"] == []


@pytest.mark.asyncio
async def test_minimal_complaint_confirmation_reaches_retrieval_without_question() -> None:
    first = TurnContext(
        {
            **BASE,
            # A complaint whose decision-relevant attributes are already
            # answered in the first sentence, so the agent has nothing worth
            # asking and goes straight to the checkpoint. Sufficient is not
            # complete: location, character and radiation are still unknown.
            "query": "Tôi bị đau họng từ hôm qua, đau nhẹ thôi",
            "current_turn_id": "t1",
            "patient_confirmed_intake": False,
        }
    )
    first.called_tools.update({"assess_contextual_emergency", "classify_request"})

    await update_intake_phase(first)

    assert first.state["selected_action"]["action_type"] == "END"
    assert first.state["action_execution"]["handler"] == "patient_confirmation"
    assert first.state["next_step"] == "wait_for_patient_confirmation"

    second = TurnContext(
        {
            **first.state,
            "intent": "TRIAGE_FOLLOW_UP",
            "query": "Tôi xác nhận thông tin trên là đúng",
            "current_turn_id": "t2",
            "patient_confirmed_intake": True,
        }
    )
    second.called_tools.update({"assess_contextual_emergency", "classify_request"})

    await update_intake_phase(second)

    assert second.state["selected_action"]["action_type"] == "RETRIEVE_RAG"
    assert second.state["next_step"] == "retrieve_evidence"
    assert second.state.get("active_question") is None


@pytest.mark.asyncio
async def test_exhausted_structural_unknown_hands_off_instead_of_reconfirming() -> None:
    context = TurnContext(
        {
            **BASE,
            "query": "không nhớ",
            "current_turn_id": "t3",
            "patient_confirmed_intake": True,
            "action_loop_state": {
                "asked_targets": {"chief_complaint": 2},
                "accepted_unknown_targets": ["chief_complaint"],
            },
            "intake_confirmation_status": "AWAITING_CONFIRMATION",
        }
    )
    context.called_tools.update({"assess_contextual_emergency", "classify_request"})

    await update_intake_phase(context)

    assert context.state["selected_action"]["action_type"] == "EXPLAIN"
    assert context.state["action_execution"]["handler"] == "insufficient_evidence_handoff"
    assert context.state["decision_status"] == "INSUFFICIENT_EVIDENCE"
    assert context.state["next_step"] == "complete"
    assert context.state["intake_confirmation_status"] == "NOT_READY"


@pytest.mark.asyncio
async def test_real_contradiction_target_controls_the_clarification() -> None:
    context = TurnContext(
        {
            **BASE,
            "query": "Tôi bị đau ngực",
            "current_turn_id": "t1",
            "unresolved_contradictions": [{"key": "onset_time"}],
        }
    )
    context.called_tools.update({"assess_contextual_emergency", "classify_request"})

    await update_intake_phase(context)

    assert context.state["selected_action"]["target"] == "contradiction_onset_time"
    assert context.state["active_question"]["field"] == "contradiction_onset_time"
    assert context.state.get("current_esi_level") is None


def _conflicted_onset_state() -> CanonicalPatientState:
    canonical = CanonicalPatientState()
    canonical.record("onset_time", "8 giờ", temporal="RELATIVE", turn_id="t1")
    canonical.record("onset_time", "5 giờ", temporal="RELATIVE", turn_id="t2")
    assert canonical.unresolved_contradictions()
    return canonical


@pytest.mark.asyncio
async def test_structured_contradiction_answer_resolves_canonical_and_legacy_state() -> None:
    canonical = _conflicted_onset_state()
    result = await analyze_patient_intake(
        {
            "intent": "TRIAGE_FOLLOW_UP",
            "query": "Thời điểm đúng là từ 5 giờ",
            "current_turn_id": "t3",
            "answer_alignment": "DIRECT_ANSWER",
            "active_question": {
                "field": "contradiction_onset_time",
                "question_id": "contradiction_onset_time",
                "options_type": "text_only",
            },
            "canonical_state": canonical.to_dict(),
            "clinical_blueprint": {"onset_time": "5 giờ"},
            # Canonical contradictions serialize with ``key`` while the
            # legacy detector uses ``field``; resolution must close both.
            "unresolved_contradictions": [{"key": "onset_time"}],
        }
    )
    resolved = CanonicalPatientState.from_dict(result["canonical_state"])

    assert resolved.unresolved_contradictions() == []
    assert resolved.value_of("onset_time") == "5 giờ"
    assert result["unresolved_contradictions"] == []
    assert any(
        item.note == "contradiction_resolved_by_patient"
        for item in resolved.history_of("onset_time")
    )


@pytest.mark.asyncio
async def test_an_unstructured_non_answer_does_not_clear_a_contradiction() -> None:
    canonical = _conflicted_onset_state()
    result = await analyze_patient_intake(
        {
            "intent": "TRIAGE_FOLLOW_UP",
            "query": "Tôi không biết",
            "current_turn_id": "t3",
            "answer_alignment": "DIRECT_ANSWER",
            "active_question": {"field": "contradiction_onset_time"},
            "canonical_state": canonical.to_dict(),
            "clinical_blueprint": {"onset_time": "5 giờ"},
            "unresolved_contradictions": [{"field": "onset_time"}],
        }
    )
    still_open = CanonicalPatientState.from_dict(result["canonical_state"])

    assert still_open.unresolved_contradictions()
    assert result["unresolved_contradictions"] == [{"field": "onset_time"}]


@pytest.mark.asyncio
async def test_negated_symptom_resolution_stays_negated_in_canonical_state() -> None:
    canonical = CanonicalPatientState()
    canonical.record(
        "symptom.dyspnea",
        True,
        status="KNOWN",
        temporal="CURRENT",
        turn_id="t1",
    )
    canonical.record(
        "symptom.dyspnea",
        False,
        status="NEGATED",
        temporal="CURRENT",
        turn_id="t2",
    )
    result = await analyze_patient_intake(
        {
            "intent": "TRIAGE_FOLLOW_UP",
            "query": "Không có khó thở",
            "current_turn_id": "t3",
            "answer_alignment": "DIRECT_ANSWER",
            "active_question": {"field": "contradiction_symptom.dyspnea"},
            "canonical_state": canonical.to_dict(),
            "unresolved_contradictions": [{"field": "symptom.dyspnea"}],
        }
    )
    resolved = CanonicalPatientState.from_dict(result["canonical_state"])

    assert resolved.unresolved_contradictions() == []
    assert resolved.status_of("symptom.dyspnea") == "NEGATED"
    assert resolved.is_affirmed("symptom.dyspnea") is False
