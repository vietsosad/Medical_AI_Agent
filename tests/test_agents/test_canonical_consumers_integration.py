"""Every clinical consumer reads canonical state, through the real turn.

These run the actual nodes the runtime calls, so a consumer quietly reverting to
an independent blueprint fails here.
"""

from __future__ import annotations

from typing import Any

import pytest

from src.agents.clinical_state_view import ClinicalStateView
from src.agents.nodes.bilingual_query_builder import build_bilingual_query_node
from src.agents.nodes.intake_analyzer import analyze_patient_intake
from src.agents.nodes.readiness_evaluator import evaluate_readiness_node


async def _turn(state: dict[str, Any], message: str, turn: int = 1) -> dict[str, Any]:
    incoming = {
        **state,
        "query": message,
        "current_turn_id": f"t{turn}",
        "intent": "TRIAGE_FOLLOW_UP",
        "clinical_memory_confirmation_status": "CONFIRMED",
    }
    merged = {**incoming, **await analyze_patient_intake(incoming)}
    return {**merged, **await evaluate_readiness_node(merged)}


# --------------------------------------------------------------------------
# Readiness
# --------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_readiness_reads_canonical_derived_state() -> None:
    state = await _turn({}, "Tôi đang đau ngực")
    view = ClinicalStateView.from_agent_state(state)
    assert view.is_present("symptom.chest_pain") is True
    assert state["symptom_cluster"] == "chest_pain"


@pytest.mark.asyncio
async def test_readiness_exposes_its_reasoning_vocabulary() -> None:
    state = await _turn({}, "Tôi đang đau ngực")
    assert state["readiness_outcome"] in {
        "READY",
        "NOT_READY",
        "NEEDS_CLARIFICATION",
        "REQUIRES_ESCALATION",
    }
    assert isinstance(state["decision_relevant_unknowns"], list)
    assert isinstance(state["relevant_uncertainties"], list)


# --------------------------------------------------------------------------
# §14 retrieval
# --------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_a_denied_symptom_never_becomes_a_retrieval_query_term() -> None:
    state = await _turn({}, "Tôi đau đầu, tôi không đau ngực")
    state["clinical_blueprint"] = {
        # A stale blueprint that wrongly carries the denied symptom.
        **state["clinical_blueprint"],
        "chief_complaint": [*state["clinical_blueprint"]["chief_complaint"], "đau ngực"],
    }
    result = await build_bilingual_query_node(state)

    assert "đau ngực" not in result["retrieval_query_vi"]
    assert "chest pain" not in result["retrieval_query_en"].lower()


@pytest.mark.asyncio
async def test_an_affirmed_symptom_does_reach_the_retrieval_query() -> None:
    state = await _turn({}, "Tôi đang đau ngực từ sáng nay")
    result = await build_bilingual_query_node(state)
    assert "đau ngực" in result["retrieval_query_vi"]


@pytest.mark.asyncio
async def test_retrieval_query_does_not_carry_a_fabricated_severity() -> None:
    state = await _turn({}, "Tôi 67 tuổi, đang đau ngực")
    result = await build_bilingual_query_node(state)
    assert "mức độ" not in result["retrieval_query_vi"]
    assert "severity" not in result["retrieval_query_en"]


@pytest.mark.asyncio
async def test_retrieval_is_blocked_while_a_contradiction_is_open() -> None:
    """Pre-existing safety behaviour must survive the refactor."""
    state = await _turn({}, "Tôi đau ngực")
    state["unresolved_contradictions"] = [{"field": "onset_time"}]
    result = await build_bilingual_query_node(state)
    assert result["retrieval_degraded_modes"] == ["BLOCKED_BY_CONTRADICTION"]
    assert result["evidence_status"] == "NOT_REQUESTED"


# --------------------------------------------------------------------------
# §12 the blueprint cannot be an independent source of truth
# --------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_the_turn_blueprint_agrees_with_canonical_state() -> None:
    state = await _turn({}, "Tôi 67 tuổi, đau ngực từ 5 giờ sáng")
    view = ClinicalStateView.from_agent_state(state)
    blueprint = state["clinical_blueprint"]

    assert blueprint["onset_time"] == view.current_value("onset_time")
    assert blueprint["severity_score"] == view.current_value("severity_score")
    assert blueprint["radiation"] == view.current_value("radiation")


@pytest.mark.asyncio
async def test_a_denied_symptom_does_not_appear_in_the_projected_blueprint() -> None:
    state = await _turn({}, "Tôi không đau ngực, chỉ đau đầu thôi")
    complaints = " ".join(state["clinical_blueprint"]["chief_complaint"]).lower()
    assert "đau ngực" not in complaints


@pytest.mark.asyncio
async def test_a_correction_reaches_every_consumer_in_one_turn() -> None:
    state = await _turn({}, "Tôi đau ngực từ 8 giờ", 1)
    state = await _turn(state, "À tôi nhớ nhầm, thực ra là từ 5 giờ", 2)

    view = ClinicalStateView.from_agent_state(state)
    assert view.current_value("onset_time") == "5 giờ"
    assert state["clinical_blueprint"]["onset_time"] == "5 giờ"

    retrieval = await build_bilingual_query_node(state)
    assert "5 giờ" in retrieval["retrieval_query_vi"]
    assert "8 giờ" not in retrieval["retrieval_query_vi"]


# --------------------------------------------------------------------------
# §16 the safety architecture is unchanged
# --------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_state_refactor_did_not_touch_the_red_flag_lifecycle() -> None:
    from src.agents.nodes.redflag_detector import detect_redflag_node

    update = await detect_redflag_node({"query": "Tuần trước tôi từng bị đau thắt ngực"})
    assert update["red_flag_status"] == "CONFIRMED"
    assert update["is_red_flag"] is True
    assert update["emergency_detection_source"] == "DETERMINISTIC_REFLEX"


@pytest.mark.asyncio
async def test_evidence_and_reasoning_gates_still_fail_closed() -> None:
    from src.agents.deepagent_runtime.tools import (
        TurnContext,
        reasoning_phase,
        retrieve_evidence_phase,
    )

    assert (
        await retrieve_evidence_phase(TurnContext({"next_step": "question_engine"}))
    )["status"] == "REJECTED"
    assert (
        await reasoning_phase(TurnContext({"next_step": "triage_reasoner"}))
    )["status"] == "REJECTED"
