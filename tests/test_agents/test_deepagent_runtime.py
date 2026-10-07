"""Integration tests for the tool-gated DeepAgent runtime."""

import pytest

from src.agents.deepagent_runtime import (
    get_deepagent_runtime,
    reset_deepagent_runtime,
)
from src.services.llm_provider import MockClinicalAI


@pytest.mark.asyncio
async def test_deepagent_runtime_basic_flow(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(
        "src.agents.deepagent_runtime.supervisor.get_deepagent_llm",
        lambda: MockClinicalAI(),
    )
    monkeypatch.setattr(
        "src.agents.nodes.contextual_emergency_detector.get_deepagent_llm",
        lambda: MockClinicalAI(),
    )
    await reset_deepagent_runtime()

    result = await get_deepagent_runtime().run_start(
        {"query": "Hello"},
        session_id="test-basic-flow",
    )

    assert "response" in result
    assert result["intent"] == "GREETING_HELP"
    assert result.get("current_esi_level") is None
    assert result["metadata"]["agent_runtime"] == "deepagents"
    assert result["metadata"]["execution_mode"] == "DETERMINISTIC_DEGRADED"


@pytest.mark.asyncio
async def test_deepagent_runtime_state_structure(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(
        "src.agents.deepagent_runtime.supervisor.get_deepagent_llm",
        lambda: MockClinicalAI(),
    )
    monkeypatch.setattr(
        "src.agents.nodes.contextual_emergency_detector.get_deepagent_llm",
        lambda: MockClinicalAI(),
    )
    await reset_deepagent_runtime()
    runtime = get_deepagent_runtime()

    result = await runtime.run_start(
        {"query": "Test query"},
        session_id="test-state-structure",
    )
    snapshot = await runtime.get_session_state("test-state-structure")

    assert isinstance(result, dict)
    assert result["query"] == "Test query"
    assert snapshot.values["query"] == "Test query"


# A configured reflex match locks before orchestration. Contextual assessment
# still runs as bounded enrichment, but has no authority to weaken that lock.
@pytest.mark.asyncio
async def test_reflex_lock_skips_orchestrator_but_not_contextual_enrichment(
    monkeypatch: pytest.MonkeyPatch,
):
    def fail_if_model_is_requested():
        raise AssertionError("Locked reflex path must not construct the supervisor model")

    validated: dict[str, bool] = {"called": False}

    async def contextual_validator(state: dict) -> dict:
        validated["called"] = True
        assert state["red_flag_status"] == "CONFIRMED"
        assert state["is_red_flag"] is True
        assert state["emergency_detection_source"] == "DETERMINISTIC_REFLEX"
        return {
            "semantic_emergency_status": "ESCALATED",
            "semantic_emergency_confidence": 0.99,
        }

    monkeypatch.setattr(
        "src.agents.deepagent_runtime.supervisor.get_deepagent_llm",
        fail_if_model_is_requested,
    )
    monkeypatch.setattr(
        "src.agents.deepagent_runtime.tools.assess_contextual_emergency_node",
        contextual_validator,
    )
    await reset_deepagent_runtime()

    result = await get_deepagent_runtime().run_start(
        {"query": "Tôi không thở nổi", "patient_name": "Người bệnh"},
        session_id="test-emergency-reflex",
    )

    assert validated["called"] is True, "contextual validation must never be skipped"
    assert result["is_red_flag"] is True
    assert result["red_flag_status"] == "CONFIRMED"
    assert result["current_esi_level"] == 1
    assert result["decision_status"] == "EMERGENCY_ESCALATED"
    assert result["metadata"]["execution_mode"] == "EMERGENCY_CONFIRMED"


@pytest.mark.asyncio
async def test_contextual_clear_observation_cannot_resume_normal_conversation(
    monkeypatch: pytest.MonkeyPatch,
):
    """A semantic clear is metadata, not permission to undo a rule lock."""

    async def records_clear_without_downgrade(state: dict) -> dict:
        assert state["red_flag_status"] == "CONFIRMED"
        assert state["is_red_flag"] is True
        return {
            "semantic_emergency_status": "CLEAR",
            "semantic_emergency_confidence": 0.99,
        }

    monkeypatch.setattr(
        "src.agents.deepagent_runtime.supervisor.get_deepagent_llm",
        lambda: MockClinicalAI(),
    )
    monkeypatch.setattr(
        "src.agents.deepagent_runtime.tools.assess_contextual_emergency_node",
        records_clear_without_downgrade,
    )
    await reset_deepagent_runtime()

    result = await get_deepagent_runtime().run_start(
        {"query": "Tuần trước tôi từng bị đau thắt ngực", "patient_name": "Người bệnh"},
        session_id="test-candidate-cleared",
    )

    assert result["is_red_flag"] is True
    assert result["red_flag_status"] == "CONFIRMED"
    assert result["current_esi_level"] == 2
    assert result["semantic_emergency_status"] == "CLEAR"
    assert result["decision_status"] == "EMERGENCY_ESCALATED"
    assert result["metadata"]["execution_mode"] == "EMERGENCY_CONFIRMED"


@pytest.mark.asyncio
async def test_semantic_emergency_execution_mode_is_persisted(
    monkeypatch: pytest.MonkeyPatch,
):
    async def semantic_emergency(_state: dict) -> dict:
        return {
            "is_red_flag": True,
            "current_esi_level": 2,
            "decision_status": "EMERGENCY_ESCALATED",
            "response_type": "EMERGENCY",
            "workflow_phase": "SAFETY_CHECK",
            "emergency_detection_source": "SEMANTIC_LLM",
            "semantic_emergency_status": "ESCALATED",
            "safety_rule_id": "SEMANTIC_EMERGENCY_CONTEXT_V1",
            "red_flag_reason": "Tổ hợp dấu hiệu nghiêm trọng theo ngữ cảnh",
            "response": "Cần đánh giá khẩn và gọi 115.",
            "messages": [],
            "next_step": "emergency_escalated",
        }

    monkeypatch.setattr(
        "src.agents.deepagent_runtime.supervisor.get_deepagent_llm",
        lambda: MockClinicalAI(),
    )
    monkeypatch.setattr(
        "src.agents.deepagent_runtime.tools.assess_contextual_emergency_node",
        semantic_emergency,
    )
    await reset_deepagent_runtime()

    result = await get_deepagent_runtime().run_start(
        {
            "query": "Tôi bị chấn thương nặng",
            "patient_name": "Người bệnh",
        },
        session_id="test-semantic-emergency-mode",
    )

    assert result["is_red_flag"] is True
    assert result["current_esi_level"] == 2
    assert result["metadata"]["execution_mode"] == "EMERGENCY_SEMANTIC"


@pytest.mark.asyncio
async def test_stream_adapter_preserves_phase_and_final_event_contract(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "src.agents.deepagent_runtime.supervisor.get_deepagent_llm",
        lambda: MockClinicalAI(),
    )
    monkeypatch.setattr(
        "src.agents.nodes.contextual_emergency_detector.get_deepagent_llm",
        lambda: MockClinicalAI(),
    )
    await reset_deepagent_runtime()

    events = [
        event
        async for event in get_deepagent_runtime().stream_turn(
            {"query": "Hello"},
            session_id="test-stream-contract",
        )
    ]

    assert events[0]["event"] == "on_chain_start"
    assert events[0]["name"] == "redflag_detector"
    assert any(
        event["event"] == "on_chain_start"
        and event["name"] == "contextual_emergency_detector"
        for event in events
    )
    assert any(
        event["event"] == "on_chain_start"
        and event["name"] == "intent_classifier"
        for event in events
    )
    assert events[-1]["event"] == "on_chain_end"
    assert events[-1]["name"] == "DeepAgentSupervisor"
    assert events[-1]["data"]["output"]["intent"] == "GREETING_HELP"
