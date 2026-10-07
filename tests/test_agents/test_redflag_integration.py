"""End-to-end: patient message -> runtime -> resolution -> frontend-facing state.

These run the whole tool-gated turn, not individual nodes, so they catch a
bypass reintroduced anywhere in the pipeline.
"""

from __future__ import annotations

from typing import Any

import pytest

from src.agents.deepagent_runtime import (
    get_deepagent_runtime,
    reset_deepagent_runtime,
)
from src.agents.nodes.contextual_emergency_detector import (
    ContextualEmergencyAssessment,
)
from src.services.llm_provider import MockClinicalAI


class ScriptedValidator:
    def __init__(self, result: ContextualEmergencyAssessment | Exception) -> None:
        self.result = result

    def with_structured_output(self, _schema: Any) -> ScriptedValidator:
        return self

    async def ainvoke(self, _prompt: str) -> ContextualEmergencyAssessment:
        if isinstance(self.result, Exception):
            raise self.result
        return self.result


def _verdict(context_type: str, *, current: bool) -> ContextualEmergencyAssessment:
    return ContextualEmergencyAssessment(
        context_type=context_type,
        is_current_personal_event=current,
        is_time_critical_emergency=current,
        confidence=0.96,
        risk_category="CARDIAC" if current else "NONE",
        observed_signals=["đau thắt ngực"],
        evidence_summary="Kết luận ngữ cảnh.",
    )


async def _run(
    monkeypatch: pytest.MonkeyPatch,
    query: str,
    validator: Any,
    session_id: str,
) -> dict[str, Any]:
    monkeypatch.setattr(
        "src.agents.deepagent_runtime.supervisor.get_deepagent_llm",
        lambda: MockClinicalAI(),
    )
    monkeypatch.setattr(
        "src.agents.nodes.contextual_emergency_detector.get_deepagent_llm",
        lambda: validator,
    )
    await reset_deepagent_runtime()
    return await get_deepagent_runtime().run_start(
        {"query": query, "patient_name": "Người bệnh"},
        session_id=session_id,
    )


@pytest.mark.asyncio
async def test_current_emergency_reaches_the_frontend_lock(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The full contract routes_patient reads to set RED_FLAG_LOCKED."""
    result = await _run(
        monkeypatch,
        "Tôi đang đau thắt ngực dữ dội",
        ScriptedValidator(_verdict("CURRENT_PERSONAL_EVENT", current=True)),
        "itest-confirmed",
    )
    assert result["is_red_flag"] is True
    assert result["red_flag_status"] == "CONFIRMED"
    assert result["decision_status"] == "EMERGENCY_ESCALATED"
    assert result["response_type"] == "EMERGENCY"
    assert result["current_esi_level"] == 2
    assert result["sbar_report"] is not None
    assert result["metadata"]["execution_mode"] == "EMERGENCY_CONFIRMED"


@pytest.mark.asyncio
async def test_historical_raw_rule_match_remains_locked_after_semantic_clear(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Configured deterministic rules remain authoritative after enrichment."""
    result = await _run(
        monkeypatch,
        "Tuần trước tôi từng bị đau thắt ngực",
        ScriptedValidator(_verdict("HISTORICAL_OR_QUOTED", current=False)),
        "itest-historical",
    )
    assert result["is_red_flag"] is True
    assert result["red_flag_status"] == "CONFIRMED"
    assert result["decision_status"] == "EMERGENCY_ESCALATED"
    assert result["response_type"] == "EMERGENCY"
    assert result["current_esi_level"] == 2
    assert result["emergency_detection_source"] == "DETERMINISTIC_REFLEX"
    assert result["semantic_emergency_status"] == "CLEAR"


@pytest.mark.asyncio
async def test_third_person_raw_rule_match_cannot_be_cleared_by_the_model(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    result = await _run(
        monkeypatch,
        "Bố tôi từng bị đau thắt ngực",
        ScriptedValidator(_verdict("HISTORICAL_OR_QUOTED", current=False)),
        "itest-third-person",
    )
    assert result["is_red_flag"] is True
    assert result["red_flag_status"] == "CONFIRMED"
    assert result["current_esi_level"] == 2
    assert result["emergency_detection_source"] == "DETERMINISTIC_REFLEX"
    assert result["semantic_emergency_status"] == "CLEAR"


@pytest.mark.asyncio
async def test_validator_outage_preserves_deterministic_rule_provenance(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    result = await _run(
        monkeypatch,
        "Tôi đang đau thắt ngực dữ dội",
        ScriptedValidator(TimeoutError()),
        "itest-fallback",
    )
    assert result["is_red_flag"] is True
    assert result["red_flag_status"] == "CONFIRMED"
    assert result["emergency_detection_source"] == "DETERMINISTIC_REFLEX"
    assert result["semantic_emergency_status"] == "UNAVAILABLE"
    assert result["metadata"]["execution_mode"] == "EMERGENCY_CONFIRMED"
    context = result["sbar_report"]["clinical_context"]
    assert context["red_flag_status"] == "CONFIRMED"
    assert context["evidence_mode"] == "DETERMINISTIC_REFLEX_RULE"
    assert "QUY TẮC AN TOÀN XÁC ĐỊNH" in result["sbar_report"]["assessment"]


@pytest.mark.asyncio
async def test_deterministic_handoff_is_not_labelled_context_validated_or_fallback(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """confirmed != fallback must survive all the way into the SBAR."""
    result = await _run(
        monkeypatch,
        "Tôi đang đau thắt ngực dữ dội",
        ScriptedValidator(_verdict("CURRENT_PERSONAL_EVENT", current=True)),
        "itest-confirmed-sbar",
    )
    context = result["sbar_report"]["clinical_context"]
    assert context["red_flag_status"] == "CONFIRMED"
    assert context["evidence_mode"] == "DETERMINISTIC_REFLEX_RULE"
    assert "QUY TẮC AN TOÀN XÁC ĐỊNH" in result["sbar_report"]["assessment"]
    assert "ĐÃ ĐƯỢC KIỂM CHỨNG NGỮ CẢNH" not in result["sbar_report"]["assessment"]
    assert "CHƯA ĐƯỢC KIỂM CHỨNG" not in result["sbar_report"]["assessment"]


@pytest.mark.asyncio
async def test_output_firewall_rejects_a_turn_that_skipped_validation() -> None:
    """The gate refuses to emit output if contextual validation never ran."""
    from src.agents.deepagent_runtime.tools import TurnContext, verify_output_phase

    context = TurnContext({"query": "Tôi đang đau thắt ngực", "is_red_flag": True})
    result = await verify_output_phase(context)

    assert result["status"] == "REJECTED"
    assert "assess_contextual_emergency" in result["reason"]


@pytest.mark.asyncio
async def test_evidence_and_reasoning_gates_are_untouched() -> None:
    """Part E: the existing safety gates must still fail closed."""
    from src.agents.deepagent_runtime.tools import (
        TurnContext,
        reasoning_phase,
        retrieve_evidence_phase,
    )

    unconfirmed = TurnContext({"next_step": "question_engine"})
    assert (await retrieve_evidence_phase(unconfirmed))["status"] == "REJECTED"

    no_evidence = TurnContext({"next_step": "triage_reasoner"})
    assert (await reasoning_phase(no_evidence))["status"] == "REJECTED"
