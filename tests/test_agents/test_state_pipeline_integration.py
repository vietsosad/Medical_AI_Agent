"""Canonical state through the real agent turn, not just the model in isolation.

These exercise ``analyze_patient_intake`` as the runtime calls it, so a break in
the wiring between extraction, state and the turn contract fails here.
"""

from __future__ import annotations

from typing import Any

import pytest

from src.agents.canonical_state import CanonicalPatientState
from src.agents.nodes.intake_analyzer import analyze_patient_intake


async def _turn(state: dict[str, Any], message: str, turn: int) -> dict[str, Any]:
    """Run one intake turn the way the tool adapter does."""
    incoming = {
        **state,
        "query": message,
        "current_turn_id": f"turn-{turn}",
        "intent": "TRIAGE_FOLLOW_UP",
    }
    update = await analyze_patient_intake(incoming)
    return {**incoming, **update}


@pytest.mark.asyncio
async def test_intake_turn_produces_canonical_state() -> None:
    state = await _turn({}, "Tôi 67 tuổi, đang đau ngực", 1)

    assert "canonical_state" in state
    canonical = CanonicalPatientState.from_dict(state["canonical_state"])
    assert canonical.value_of("age") == 67
    assert canonical.status_of("symptom.chest_pain") == "KNOWN"
    assert state["canonical_state_version"] == canonical.version > 0


@pytest.mark.asyncio
async def test_state_accumulates_across_turns_without_losing_earlier_facts() -> None:
    state = await _turn({}, "Tôi bị đau ngực", 1)
    for index in range(2, 15):
        state = await _turn(state, f"Tôi vẫn thấy mệt ({index})", index)
    state = await _turn(state, "À tôi còn khó thở nữa", 15)

    canonical = CanonicalPatientState.from_dict(state["canonical_state"])
    assert canonical.status_of("symptom.chest_pain") == "KNOWN"
    assert canonical.status_of("symptom.dyspnea") == "KNOWN"


@pytest.mark.asyncio
async def test_late_correction_supersedes_and_flags_reassessment() -> None:
    state = await _turn({}, "Tôi đau ngực từ 8 giờ", 1)
    state = await _turn(state, "À tôi nhớ nhầm, thực ra là từ 5 giờ", 2)

    canonical = CanonicalPatientState.from_dict(state["canonical_state"])
    history = canonical.history_of("onset_time")
    assert len(history) == 2
    assert any(not item.is_active for item in history)
    assert "onset_time" in state["pending_reassessment_keys"]


@pytest.mark.asyncio
async def test_unknown_is_preserved_through_a_full_turn() -> None:
    state = await _turn({}, "Tôi bị đau đầu", 1)
    canonical = CanonicalPatientState.from_dict(state["canonical_state"])
    assert canonical.status_of("symptom.chest_pain") == "UNKNOWN"
    assert canonical.status_of("symptom.dyspnea") == "UNKNOWN"


@pytest.mark.asyncio
async def test_negation_through_a_full_turn_is_not_a_positive_finding() -> None:
    state = await _turn({}, "Tôi không đau ngực, chỉ đau đầu thôi", 1)
    canonical = CanonicalPatientState.from_dict(state["canonical_state"])
    assert canonical.status_of("symptom.chest_pain") == "NEGATED"
    assert canonical.is_affirmed("symptom.chest_pain") is False


@pytest.mark.asyncio
async def test_temporal_values_survive_the_turn_boundary() -> None:
    state = await _turn({}, "Sáng nay tôi sốt 39 độ, giờ nhiệt độ còn 37.8", 1)
    canonical = CanonicalPatientState.from_dict(state["canonical_state"])
    assert canonical.value_of("vital.temperature_c") == 37.8
    assert [
        item.value for item in canonical.historical_values("vital.temperature_c")
    ] == [39.0]


@pytest.mark.asyncio
async def test_canonical_state_is_json_serializable_for_storage() -> None:
    import json

    state = await _turn({}, "Tôi 67 tuổi, sáng nay sốt 39 độ, giờ còn 37.8", 1)
    encoded = json.dumps(state["canonical_state"], ensure_ascii=False)
    restored = CanonicalPatientState.from_dict(json.loads(encoded))
    assert restored.value_of("age") == 67
    assert restored.value_of("vital.temperature_c") == 37.8


@pytest.mark.asyncio
async def test_the_existing_blueprint_still_populates_for_legacy_consumers() -> None:
    """Readiness, retrieval and reasoning read the blueprint; it must not regress."""
    state = await _turn({}, "Tôi đau ngực từ sáng nay", 1)
    blueprint = state["clinical_blueprint"]
    assert blueprint["chief_complaint"]
    assert blueprint["onset_time"]
    # And severity is still UNKNOWN rather than fabricated.
    assert blueprint["severity_score"] is None


@pytest.mark.asyncio
async def test_state_survives_a_turn_that_says_nothing_clinical() -> None:
    state = await _turn({}, "Tôi đau ngực", 1)
    version_before = state["canonical_state_version"]
    state = await _turn(state, "ok", 2)
    canonical = CanonicalPatientState.from_dict(state["canonical_state"])
    assert canonical.status_of("symptom.chest_pain") == "KNOWN"
    assert state["canonical_state_version"] == version_before
