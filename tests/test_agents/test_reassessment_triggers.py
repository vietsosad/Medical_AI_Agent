"""Which state mutations invalidate a triage conclusion, and which do not.

A conclusion already drawn must not survive a clinically relevant change; but a
turn that only says "vâng ạ" must not force the whole assessment to be redone.
This is mutation classification only - no reasoning runs here.
"""

from __future__ import annotations

from typing import Any

import pytest

from src.agents.canonical_state import CanonicalPatientState, triggers_reassessment
from src.agents.nodes.intake_analyzer import analyze_patient_intake

DECIDED_CASE: dict[str, Any] = {
    "current_esi_level": 4,
    "sbar_report": {"situation": "..."},
}


async def _turn(state: dict[str, Any], message: str, turn: int = 2) -> dict[str, Any]:
    incoming = {
        **state,
        "query": message,
        "current_turn_id": f"t{turn}",
        "intent": "TRIAGE_FOLLOW_UP",
    }
    return {**incoming, **await analyze_patient_intake(incoming)}


def _decided() -> dict[str, Any]:
    return {**DECIDED_CASE, "canonical_state": CanonicalPatientState().to_dict()}


# --------------------------------------------------------------------------
# Should trigger
# --------------------------------------------------------------------------

@pytest.mark.parametrize(
    "message",
    [
        "À tôi còn khó thở nữa",
        "Tôi vừa bị ngất",
        "Giờ tôi thấy đau ngực",
        "Tôi bị co giật",
        "Tôi đang chảy máu",
        "Nhiệt độ hiện tại 39.5 độ",
    ],
)
@pytest.mark.asyncio
async def test_clinically_relevant_facts_invalidate_a_conclusion(message: str) -> None:
    state = await _turn(_decided(), message)
    assert state["requires_triage_reassessment"] is True
    assert state["pending_reassessment_keys"]


@pytest.mark.asyncio
async def test_a_severity_correction_invalidates_a_conclusion() -> None:
    state = await _turn({"canonical_state": CanonicalPatientState().to_dict()},
                        "Mức độ đau 3 trên 10", 1)
    state.update(DECIDED_CASE)
    state = await _turn(state, "À tôi nhớ nhầm, thực ra mức độ đau 9 trên 10", 2)
    assert state["requires_triage_reassessment"] is True
    assert "severity_score" in state["pending_reassessment_keys"]


@pytest.mark.asyncio
async def test_an_onset_correction_invalidates_a_conclusion() -> None:
    state = await _turn({"canonical_state": CanonicalPatientState().to_dict()},
                        "Tôi đau ngực từ 8 giờ", 1)
    state.update(DECIDED_CASE)
    state = await _turn(state, "À tôi nhớ nhầm, thực ra là từ 5 giờ", 2)
    assert state["requires_triage_reassessment"] is True
    assert "onset_time" in state["pending_reassessment_keys"]


@pytest.mark.asyncio
async def test_a_new_medication_invalidates_a_conclusion() -> None:
    state = await _turn(_decided(), "Tôi đang uống thuốc huyết áp")
    assert state["requires_triage_reassessment"] is True


# --------------------------------------------------------------------------
# Should not trigger on their own
# --------------------------------------------------------------------------

@pytest.mark.parametrize(
    "message",
    [
        "vâng ạ",
        "ok",
        "cảm ơn bác sĩ",
        "tôi hiểu rồi",
        "",
    ],
)
@pytest.mark.asyncio
async def test_conversational_filler_does_not_invalidate_a_conclusion(
    message: str,
) -> None:
    state = await _turn(_decided(), message)
    assert state["requires_triage_reassessment"] is False


@pytest.mark.asyncio
async def test_reassessment_is_not_demanded_before_any_conclusion_exists() -> None:
    """A first turn has nothing to invalidate, however relevant the fact."""
    state = await _turn({"canonical_state": CanonicalPatientState().to_dict()},
                        "Tôi đang đau ngực", 1)
    assert state["requires_triage_reassessment"] is False
    # The mutation is still tracked for when a conclusion does exist.
    assert "symptom.chest_pain" in state["pending_reassessment_keys"]


# --------------------------------------------------------------------------
# The classification itself
# --------------------------------------------------------------------------

@pytest.mark.parametrize(
    "key",
    [
        "symptom.chest_pain",
        "symptom.dyspnea",
        "symptom.syncope",
        "vital.temperature_c",
        "severity_score",
        "onset_time",
        "age",
        "medication",
        "radiation",
    ],
)
def test_clinically_relevant_keys_are_classified_as_such(key: str) -> None:
    assert triggers_reassessment(key) is True


@pytest.mark.parametrize(
    "key",
    [
        "patient_name",
        "ui_theme",
        "session_title",
        "clinical_context_note",
        "vital_signs_source",
    ],
)
def test_non_clinical_keys_do_not_trigger_reassessment(key: str) -> None:
    assert triggers_reassessment(key) is False


def test_reassessment_flags_can_be_cleared_after_a_reassessment() -> None:
    state = CanonicalPatientState()
    state.record("symptom.dyspnea", True, turn_id="t1")
    assert state.pending_reassessment_keys
    state.clear_reassessment_flags()
    assert state.pending_reassessment_keys == []
