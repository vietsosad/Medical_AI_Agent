import pytest

from src.agents.deepagent_runtime.tools import (
    TurnContext,
    classify_request_phase,
    reasoning_phase,
    retrieve_evidence_phase,
    update_intake_phase,
    verify_output_phase,
)


@pytest.mark.asyncio
async def test_retrieval_tool_rejects_unconfirmed_intake() -> None:
    context = TurnContext(
        {
            "decision_status": "READY_FOR_EVIDENCE",
            "patient_confirmed_intake": False,
            "next_step": "patient_confirmation",
        }
    )

    result = await retrieve_evidence_phase(context)

    assert result["status"] == "REJECTED"
    assert context.state.get("retrieved_evidence") is None


@pytest.mark.asyncio
async def test_reasoning_tool_rejects_without_evidence_tool() -> None:
    context = TurnContext(
        {
            "next_step": "triage_reasoner",
            "evidence_status": "SUFFICIENT",
        }
    )

    result = await reasoning_phase(context)

    assert result["status"] == "REJECTED"
    assert context.state.get("current_esi_level") is None


@pytest.mark.asyncio
async def test_final_verifier_fails_closed_on_ungrounded_proposal() -> None:
    context = TurnContext(
        {
            "decision_status": "PROPOSED",
            "current_esi_level": 3,
            "patient_confirmed_intake": True,
            "evidence_status": "SUFFICIENT",
            "evidence_authority_status": "AUTHORIZED",
            "turn_rag_citations": [],
            "sbar_report": {"situation": "Unsupported"},
            "response": "Bạn đã bị một bệnh cụ thể.",
        }
    )
    context.called_tools.update(
        {
            "assess_contextual_emergency",
            "classify_request",
            "update_intake",
            "retrieve_clinical_evidence",
            "reason_and_prepare_handoff",
        }
    )

    await verify_output_phase(context)

    assert context.state["decision_status"] == "INSUFFICIENT_EVIDENCE"
    assert context.state["current_esi_level"] is None
    assert context.state["sbar_report"] is None
    assert context.state["turn_rag_citations"] == []
    assert context.state["workflow_phase"] == "HANDOFF"
    assert "chờ điều dưỡng xác nhận" in context.state["response"].lower()


def _proposal_context(*, matched_criterion: str) -> TurnContext:
    context = TurnContext(
        {
            "decision_status": "PROPOSED",
            "current_esi_level": 3,
            "patient_confirmed_intake": True,
            "evidence_status": "SUFFICIENT",
            "evidence_authority_status": "AUTHORIZED",
            "retrieved_evidence": [
                {
                    "citation_id": "AUTH-A",
                    "protocol_criteria": ["CRITERION-A"],
                }
            ],
            "turn_rag_citations": [{"id": "AUTH-A"}],
            "matched_protocol_criteria": [matched_criterion],
            "sbar_report": {"situation": "Evidence-linked proposal"},
            "response": "Mức ưu tiên đề xuất cần điều dưỡng xác nhận.",
        }
    )
    context.called_tools.update(
        {
            "assess_contextual_emergency",
            "classify_request",
            "update_intake",
            "retrieve_clinical_evidence",
            "reason_and_prepare_handoff",
        }
    )
    return context


@pytest.mark.asyncio
async def test_final_verifier_accepts_exact_citation_criterion_link() -> None:
    context = _proposal_context(matched_criterion="CRITERION-A")

    await verify_output_phase(context)

    assert context.state["decision_status"] == "PROPOSED"
    assert context.state["current_esi_level"] == 3


@pytest.mark.asyncio
async def test_final_verifier_rejects_cross_document_criterion() -> None:
    context = _proposal_context(matched_criterion="CRITERION-B")

    await verify_output_phase(context)

    assert context.state["decision_status"] == "INSUFFICIENT_EVIDENCE"
    assert context.state["current_esi_level"] is None
    assert context.state["sbar_report"] is None
    assert context.state["turn_rag_citations"] == []


@pytest.mark.asyncio
async def test_final_verifier_rejects_when_agent_skips_prerequisites() -> None:
    context = TurnContext({"query": "Tôi đau đầu"})

    result = await verify_output_phase(context)

    assert result["status"] == "REJECTED"
    assert "verify_clinical_output" not in context.called_tools


@pytest.mark.asyncio
async def test_classifier_rejects_when_semantic_emergency_check_is_skipped() -> None:
    context = TurnContext({"query": "Tôi đau đầu"})

    result = await classify_request_phase(context)

    assert result["status"] == "REJECTED"
    assert result["allowed_next_tools"] == ["assess_contextual_emergency"]
    assert "classify_request" not in context.called_tools


@pytest.mark.asyncio
async def test_update_intake_clarifies_a_contradiction_through_the_planner(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A contradiction reaches clarification via the action the planner chose.

    This used to be a short circuit inside ``update_intake_phase``: a
    contradiction jumped straight to the question engine and readiness never
    ran. That was a second routing authority sitting beside the planner, and
    the two had to be kept in agreement by hand. Now the contradiction flows
    through readiness into the planner, which selects CLARIFY for it, and the
    dispatcher runs the clarification. The guarantee under test is unchanged --
    a contradiction is clarified and nothing is concluded -- but there is only
    one thing deciding it.
    """
    async def empty_update(_state: dict) -> dict:
        return {}

    async def contradiction_update(_state: dict) -> dict:
        return {
            "unresolved_contradictions": [{"field": "onset_time"}],
            "decision_status": "NEEDS_CLARIFICATION",
            "next_step": "question_engine",
        }

    async def clarification_update(_state: dict) -> dict:
        return {
            "response": "Vui lòng xác nhận lại thời điểm khởi phát.",
            "next_step": "wait_for_patient",
        }

    for target in ("validate_answer_node", "analyze_patient_intake"):
        monkeypatch.setattr(
            f"src.agents.deepagent_runtime.tools.{target}",
            empty_update,
        )
    monkeypatch.setattr(
        "src.agents.deepagent_runtime.tools.detect_contradictions_node",
        contradiction_update,
    )
    # The question engine is now reached through the dispatcher, so it is
    # patched where the dispatcher looks it up.
    monkeypatch.setattr(
        "src.agents.action_execution.run_question_engine_node",
        clarification_update,
    )

    context = TurnContext({"intent": "TRIAGE_NEW_SYMPTOM"})
    context.called_tools.update(
        {"assess_contextual_emergency", "classify_request"}
    )

    result = await update_intake_phase(context)

    assert result["status"] == "OK"
    assert context.state["unresolved_contradictions"]
    # The planner chose to clarify, and the clarification actually ran.
    assert context.state["selected_action"]["action_type"] == "CLARIFY"
    assert context.state["action_lifecycle"] == "EXECUTED"
    assert context.state["action_execution"]["handler"] == "question_engine"
    assert context.state["response"] == "Vui lòng xác nhận lại thời điểm khởi phát."
    # Nothing was concluded while the contradiction is open.
    assert context.state.get("current_esi_level") is None
    assert result["allowed_next_tools"] == ["verify_clinical_output"]


@pytest.mark.asyncio
async def test_update_intake_requires_confirmation_before_retrieval(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A ready case still asks the patient to confirm before evidence is fetched."""
    async def empty_update(_state: dict) -> dict:
        return {}

    async def ready_update(_state: dict) -> dict:
        return {
            "decision_status": "READY_FOR_EVIDENCE",
            "readiness_outcome": "READY",
            "next_step": "patient_confirmation",
        }

    async def confirmation_update(_state: dict) -> dict:
        return {
            "decision_status": "AWAITING_PATIENT_CONFIRMATION",
            "next_step": "patient_confirmation",
        }

    for target in (
        "validate_answer_node",
        "analyze_patient_intake",
        "detect_contradictions_node",
    ):
        monkeypatch.setattr(
            f"src.agents.deepagent_runtime.tools.{target}",
            empty_update,
        )
    monkeypatch.setattr(
        "src.agents.deepagent_runtime.tools.evaluate_pre_retrieval_readiness_node",
        ready_update,
    )
    monkeypatch.setattr(
        "src.agents.action_execution.request_patient_confirmation_node",
        confirmation_update,
    )

    context = TurnContext(
        {
            "intent": "TRIAGE_NEW_SYMPTOM",
            "patient_confirmed_intake": False,
        }
    )
    context.called_tools.update(
        {"assess_contextual_emergency", "classify_request"}
    )

    result = await update_intake_phase(context)

    assert result["decision_status"] == "AWAITING_PATIENT_CONFIRMATION"
    assert result["next_step"] == "patient_confirmation"
    # END is the action; confirmation is how it is carried out, and retrieval
    # is not authorised until the patient has confirmed.
    assert context.state["selected_action"]["action_type"] == "END"
    assert context.state["action_execution"]["handler"] == "patient_confirmation"
    assert result["allowed_next_tools"] == ["verify_clinical_output"]


def test_confirmed_intake_authorizes_evidence_retrieval_tool() -> None:
    context = TurnContext(
        {
            "intent": "TRIAGE_FOLLOW_UP",
            "patient_confirmed_intake": True,
            "decision_status": "READY_FOR_EVIDENCE",
            "next_step": "retrieve_evidence",
        }
    )
    context.called_tools.update(
        {
            "assess_contextual_emergency",
            "classify_request",
            "update_intake",
        }
    )

    assert context.allowed_next_tools() == ["retrieve_clinical_evidence"]


@pytest.mark.asyncio
async def test_case_support_cannot_authorize_any_esi_reasoner() -> None:
    """MIETIC remains CASE_SUPPORT even if the dormant demo flag is enabled."""
    context = TurnContext(
        {
            "next_step": "demo_case_reasoner",
            "evidence_status": "CASE_EXAMPLE_SUPPORT",
            "evidence_authority_status": "DEMO_ONLY",
        }
    )
    context.called_tools.add("retrieve_clinical_evidence")

    result = await reasoning_phase(context)

    assert result["status"] == "REJECTED"
    assert context.state.get("current_esi_level") is None
    assert context.state.get("sbar_report") is None
