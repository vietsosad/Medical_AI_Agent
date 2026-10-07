"""A deterministic emergency reflex is monotonic across semantic assessment."""

from __future__ import annotations

from typing import Any

import pytest

from src.agents.deepagent_runtime import (
    get_deepagent_runtime,
    reset_deepagent_runtime,
)
from src.agents.nodes.contextual_emergency_detector import (
    ContextualEmergencyAssessment,
    assess_contextual_emergency_node,
)
from src.agents.nodes.redflag_detector import detect_redflag_node


class NegativeContextModel:
    """A scripted semantic model that tries to clear the deterministic match."""

    def __init__(self) -> None:
        self.invoked = False

    def with_structured_output(self, _schema: Any) -> NegativeContextModel:
        return self

    async def ainvoke(self, _prompt: str) -> ContextualEmergencyAssessment:
        self.invoked = True
        return ContextualEmergencyAssessment(
            context_type="HISTORICAL_OR_QUOTED",
            is_current_personal_event=False,
            is_time_critical_emergency=False,
            confidence=0.99,
            risk_category="NONE",
            observed_signals=[],
            evidence_summary="Semantic model returned a non-emergency verdict.",
        )


@pytest.mark.asyncio
async def test_positive_deterministic_reflex_locks_before_any_model_call() -> None:
    update = await detect_redflag_node({"query": "Tôi đang đau thắt ngực dữ dội"})

    assert update["is_red_flag"] is True
    assert update["red_flag_status"] == "CONFIRMED"
    assert update["emergency_detection_source"] == "DETERMINISTIC_REFLEX"
    assert update["current_esi_level"] == update["red_flag_candidate_esi"] == 2
    assert update["decision_status"] == "EMERGENCY_ESCALATED"
    assert update["next_step"] == "emergency_escalated"
    assert "115" in update["response"]


@pytest.mark.asyncio
async def test_negative_contextual_llm_cannot_clear_or_lower_reflex_lock(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    state: dict[str, Any] = {"query": "Tôi đang đau thắt ngực dữ dội"}
    state.update(await detect_redflag_node(state))
    locked_esi = state["current_esi_level"]
    locked_rule = state["safety_rule_id"]
    model = NegativeContextModel()
    monkeypatch.setattr(
        "src.agents.nodes.contextual_emergency_detector.get_deepagent_llm",
        lambda: model,
    )

    state.update(await assess_contextual_emergency_node(state))

    assert model.invoked is True
    assert state["semantic_emergency_status"] == "CLEAR"
    assert state["is_red_flag"] is True
    assert state["red_flag_status"] == "CONFIRMED"
    assert state["emergency_detection_source"] == "DETERMINISTIC_REFLEX"
    assert state["current_esi_level"] == locked_esi
    assert state["safety_rule_id"] == locked_rule
    assert state["decision_status"] == "EMERGENCY_ESCALATED"
    assert state["next_step"] == "emergency_escalated"
    assert state["metadata"]["deterministic_reflex_lock"]["locked"] is True


@pytest.mark.asyncio
async def test_later_turn_cannot_clear_and_a_stronger_rule_can_only_escalate() -> None:
    state: dict[str, Any] = {"query": "Tôi đang đau thắt ngực dữ dội"}
    state.update(await detect_redflag_node(state))
    assert state["current_esi_level"] == 2

    state["query"] = "Tôi thấy đỡ hơn"
    state.update(await detect_redflag_node(state))
    assert state["is_red_flag"] is True
    assert state["red_flag_status"] == "CONFIRMED"
    assert state["current_esi_level"] == 2

    state["query"] = "Bây giờ tôi không thở nổi"
    state.update(await detect_redflag_node(state))
    assert state["is_red_flag"] is True
    assert state["red_flag_status"] == "CONFIRMED"
    assert state["current_esi_level"] == 1
    assert state["emergency_detection_source"] == "DETERMINISTIC_REFLEX"


@pytest.mark.asyncio
async def test_runtime_skips_orchestrator_and_preserves_lock_after_negative_llm(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fail_if_supervisor_model_is_requested() -> None:
        raise AssertionError("Locked reflex path must not construct supervisor LLM")

    model = NegativeContextModel()
    monkeypatch.setattr(
        "src.agents.deepagent_runtime.supervisor.get_deepagent_llm",
        fail_if_supervisor_model_is_requested,
    )
    monkeypatch.setattr(
        "src.agents.nodes.contextual_emergency_detector.get_deepagent_llm",
        lambda: model,
    )
    await reset_deepagent_runtime()

    result = await get_deepagent_runtime().run_start(
        {
            "query": "Tôi đang đau thắt ngực dữ dội",
            "patient_name": "Người bệnh",
        },
        session_id="deterministic-reflex-monotonicity",
    )

    assert model.invoked is True
    assert result["is_red_flag"] is True
    assert result["red_flag_status"] == "CONFIRMED"
    assert result["current_esi_level"] == 2
    assert result["emergency_detection_source"] == "DETERMINISTIC_REFLEX"
    assert result["decision_status"] == "EMERGENCY_ESCALATED"
    assert result["sbar_report"] is not None
    assert result["metadata"]["execution_mode"] == "EMERGENCY_CONFIRMED"
