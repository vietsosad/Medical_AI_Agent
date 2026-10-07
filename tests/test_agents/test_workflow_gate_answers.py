"""Answering a question must close it.

Reported from a live session: the patient was asked what had changed in their
record, answered "Tôi bị viêm phổi, không dị ứng thuốc", and was asked the
identical question again on the next turn.

The gate only closed when ``active_question`` could still be identified. That
identification is fragile by construction: the persisted AI message stores a
short title ("Xác nhận hồ sơ sức khỏe hiện tại") rather than the question text,
so recovering the open slot depends on a structured payload that a free-text
question does not carry. When it failed, the patient was re-asked something they
had just answered -- which is the clearest way software has of announcing that
it was not listening.

The gate now closes on the substantive answer itself. What it must not do is
close on silence or a shrug, which is asserted here too.
"""

from __future__ import annotations

from typing import Any

import pytest

from src.agents.nodes.intake_analyzer import analyze_patient_intake

BASE: dict[str, Any] = {
    "intent": "TRIAGE_NEW_SYMPTOM",
    "patient_id": "p",
    "session_id": "s",
    "clinical_memory_confirmation_status": "NOT_REVIEWED",
    "clinical_memory_update_pending": True,
}


async def _intake(query: str, **overrides: Any) -> dict[str, Any]:
    state = {**BASE, **overrides, "query": query, "current_turn_id": "t2"}
    return await analyze_patient_intake(state)


# --------------------------------------------------------------------------
# The reported case
# --------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_an_answer_closes_the_record_update_gate() -> None:
    result = await _intake("Tôi bị viêm phổi, không dị ứng thuốc")

    assert result["clinical_memory_update_pending"] is False
    assert result["clinical_memory_confirmation_status"] == "UPDATED_BY_PATIENT"


@pytest.mark.asyncio
async def test_it_closes_even_when_the_open_question_was_lost() -> None:
    """The whole point: no dependency on active_question surviving."""
    result = await _intake(
        "Tôi bị viêm phổi, không dị ứng thuốc",
        active_question=None,
    )

    assert result["clinical_memory_update_pending"] is False


@pytest.mark.asyncio
async def test_it_still_closes_when_the_question_is_known() -> None:
    """The original path must keep working."""
    result = await _intake(
        "Tôi bị hen suyễn",
        active_question={
            "field": "clinical_memory_update_detail",
            "question_id": "clinical_memory_update_detail",
            "options_type": "text_only",
        },
        answer_alignment="DIRECT_ANSWER",
    )

    assert result["clinical_memory_update_pending"] is False


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "answer",
    [
        "Tôi bị viêm phổi",
        "dị ứng penicillin",
        "đang uống thuốc huyết áp",
        "không có gì thay đổi cả",
        "tôi bị tiểu đường type 2",
    ],
)
async def test_any_substantive_answer_closes_it(answer: str) -> None:
    result = await _intake(answer)

    assert result["clinical_memory_update_pending"] is False, answer


# --------------------------------------------------------------------------
# It must not close on nothing
# --------------------------------------------------------------------------

@pytest.mark.asyncio
@pytest.mark.parametrize("answer", ["", "  ", "a", "ok"])
async def test_an_empty_or_trivial_reply_does_not_close_it(answer: str) -> None:
    """A shrug is not a medical history."""
    result = await _intake(answer)

    assert result["clinical_memory_update_pending"] is True, repr(answer)


@pytest.mark.asyncio
async def test_the_gate_is_untouched_when_nothing_was_pending() -> None:
    """A normal turn must not be interpreted as answering a question we never asked."""
    result = await _intake(
        "tôi bị đau họng từ hôm qua",
        clinical_memory_update_pending=False,
        clinical_memory_confirmation_status="CONFIRMED",
    )

    assert result["clinical_memory_update_pending"] is False
    assert result["clinical_memory_confirmation_status"] == "CONFIRMED"


@pytest.mark.asyncio
async def test_the_answer_does_not_silently_overwrite_the_ehr() -> None:
    """The question promises the answer is attached to the case only."""
    result = await _intake("Tôi bị viêm phổi, không dị ứng thuốc")

    # Recorded as the patient's own statement for this case, never written back
    # as a confirmed EHR record.
    assert result["clinical_memory_confirmation_status"] == "UPDATED_BY_PATIENT"
    assert "clinical_memory" not in result
