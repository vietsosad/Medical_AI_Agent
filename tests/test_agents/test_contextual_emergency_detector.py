from __future__ import annotations

from typing import Any

import pytest

from src.agents.nodes.contextual_emergency_detector import (
    ContextualEmergencyAssessment,
    assess_contextual_emergency_node,
)


class StructuredAssessmentModel:
    def __init__(self, result: ContextualEmergencyAssessment | Exception) -> None:
        self.result = result

    def with_structured_output(self, schema: Any) -> StructuredAssessmentModel:
        assert schema is ContextualEmergencyAssessment
        return self

    async def ainvoke(self, prompt: str) -> ContextualEmergencyAssessment:
        assert "xương lòi ra" in prompt
        if isinstance(self.result, Exception):
            raise self.result
        return self.result


@pytest.mark.asyncio
async def test_contextual_model_escalates_open_fracture_with_heavy_bleeding(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    assessment = ContextualEmergencyAssessment(
        context_type="CURRENT_PERSONAL_EVENT",
        is_current_personal_event=True,
        is_time_critical_emergency=True,
        confidence=0.98,
        risk_category="MAJOR_TRAUMA_OR_BLEEDING",
        observed_signals=["gãy chân", "chảy nhiều máu", "xương lòi ra"],
        evidence_summary="Chấn thương hở kèm chảy máu nhiều đang xảy ra.",
    )
    monkeypatch.setattr(
        "src.agents.nodes.contextual_emergency_detector.get_deepagent_llm",
        lambda: StructuredAssessmentModel(assessment),
    )

    result = await assess_contextual_emergency_node(
        {"query": "tôi bị gãy chân, chảy nhiều máu, xương lòi ra"}
    )

    assert result["is_red_flag"] is True
    assert result["current_esi_level"] == 2
    assert result["decision_status"] == "EMERGENCY_ESCALATED"
    assert result["emergency_detection_source"] == "SEMANTIC_LLM"
    assert result["semantic_emergency_status"] == "ESCALATED"
    assert result["safety_rule_id"] == "SEMANTIC_EMERGENCY_CONTEXT_V1"
    assert result["turn_rag_citations"] == []
    assert "Gọi cấp cứu 115" in result["response"]


@pytest.mark.asyncio
async def test_contextual_model_does_not_escalate_negated_educational_context(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class FailIfInvoked:
        def with_structured_output(self, _schema: Any) -> FailIfInvoked:
            raise AssertionError("Explicit educational queries must bypass the model")

    monkeypatch.setattr(
        "src.agents.nodes.contextual_emergency_detector.get_deepagent_llm",
        lambda: FailIfInvoked(),
    )

    result = await assess_contextual_emergency_node(
        {"query": "Không thở nổi nghĩa là gì?"}
    )

    assert result.get("is_red_flag") is None
    assert result["semantic_emergency_status"] == "CLEAR"
    assert result["metadata"]["semantic_emergency_assessment"]["context_type"] == (
        "EDUCATIONAL_OR_HYPOTHETICAL"
    )
    assert result["next_step"] == "intent_classifier"


@pytest.mark.asyncio
async def test_contextual_model_cannot_escalate_a_non_current_event(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    assessment = ContextualEmergencyAssessment(
        context_type="HISTORICAL_OR_QUOTED",
        is_current_personal_event=False,
        is_time_critical_emergency=True,
        confidence=0.99,
        risk_category="MAJOR_TRAUMA_OR_BLEEDING",
        observed_signals=["xương lòi ra"],
        evidence_summary="Cụm từ nghiêm trọng xuất hiện trong lời kể lịch sử.",
    )
    monkeypatch.setattr(
        "src.agents.nodes.contextual_emergency_detector.get_deepagent_llm",
        lambda: StructuredAssessmentModel(assessment),
    )

    result = await assess_contextual_emergency_node(
        {"query": "Hôm qua người khác kể rằng họ bị xương lòi ra"}
    )

    assert result.get("is_red_flag") is None
    assert result["semantic_emergency_status"] == "INCONCLUSIVE"
    assert result["next_step"] == "intent_classifier"


@pytest.mark.asyncio
async def test_contextual_model_failure_degrades_without_fabricating_emergency(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "src.agents.nodes.contextual_emergency_detector.get_deepagent_llm",
        lambda: StructuredAssessmentModel(TimeoutError()),
    )

    result = await assess_contextual_emergency_node(
        {"query": "tôi bị gãy chân, chảy nhiều máu, xương lòi ra"}
    )

    assert result.get("is_red_flag") is None
    assert result.get("current_esi_level") is None
    assert result["semantic_emergency_status"] == "UNAVAILABLE"
    assert result["next_step"] == "intent_classifier"
