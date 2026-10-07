"""A symptom name is a question. An emergency claim needs evidence.

Reported from a live session: typing the two words "khó thở" produced a red
emergency banner and a locked session. A clinician hearing "khó thở" asks how
bad, since when, at rest or walking, can you finish a sentence. They do not
stop the consultation on the word alone.

The cause was a gap between two layers, not a bug in either. The deterministic
screen decides *does a dangerous phrase appear* -- and it was well calibrated,
matching "khó thở dữ dội" but not "khó thở". The contextual model decides *is
this happening to this patient now*, and its prompt explicitly forbids it from
judging severity. So nothing decided **is there enough here to declare an
emergency**, and any current mention of a worrying symptom became one.

The fix adds that missing judgement and routes the insufficient case to the
clarification state the architecture already had. Escalation is delayed by one
turn for a bare mention, and that turn's question leads with "gọi 115 ngay".
An alarm that fires on two words is an alarm patients learn to ignore.
"""

from __future__ import annotations

import pytest

from src.agents.guardrails import screen_red_flag_candidate
from src.agents.nodes.contextual_emergency_detector import (
    emergency_evidence_is_sufficient,
)


# --------------------------------------------------------------------------
# A bare symptom is not an emergency claim
# --------------------------------------------------------------------------

@pytest.mark.parametrize(
    "message",
    [
        "khó thở",
        "đau ngực",
        "đau đầu",
        "chóng mặt",
        "đau bụng",
        "tôi bị sốt",
        "hơi mệt",
        "buồn nôn",
    ],
)
def test_a_bare_symptom_is_not_sufficient_evidence(message: str) -> None:
    assert emergency_evidence_is_sufficient(message, []) is False


@pytest.mark.parametrize(
    "message",
    ["khó thở", "đau ngực", "đau đầu", "chóng mặt", "đau bụng"],
)
def test_the_deterministic_screen_also_leaves_these_alone(message: str) -> None:
    """The screen was never the trigger-happy layer; this pins that."""
    assert screen_red_flag_candidate(message) is None


# --------------------------------------------------------------------------
# The patient's own words can establish it
# --------------------------------------------------------------------------

@pytest.mark.parametrize(
    "message",
    [
        "khó thở dữ dội",
        "không thở được",
        "tôi tím tái",
        "tôi sắp chết",
        "chảy máu không cầm",
        "tôi thấy đau đầu đột ngột",
        "đau ngực không chịu nổi",
        "tôi bất tỉnh",
    ],
)
def test_an_urgency_qualifier_is_sufficient(message: str) -> None:
    assert emergency_evidence_is_sufficient(message, []) is True


@pytest.mark.parametrize(
    "message",
    [
        "đau ngực và khó thở",
        "đau ngực, vã mồ hôi, buồn nôn",
        "khó thở kèm chóng mặt",
    ],
)
def test_two_reinforcing_symptoms_are_sufficient(message: str) -> None:
    """What the model prompt already called stronger evidence."""
    assert emergency_evidence_is_sufficient(message, []) is True


def test_several_observed_signals_are_sufficient_even_outside_the_lexicon() -> None:
    """Recall must not depend on our Vietnamese lexicon being complete."""
    assert emergency_evidence_is_sufficient(
        "người tôi lạnh toát và mắt mờ đi",
        ["da lạnh ẩm", "nhìn mờ"],
    ) is True


def test_a_single_observed_signal_is_not_sufficient() -> None:
    assert emergency_evidence_is_sufficient("khó thở", ["khó thở"]) is False


def test_an_empty_message_is_never_sufficient() -> None:
    assert emergency_evidence_is_sufficient("", ["bất kỳ"]) is False
    assert emergency_evidence_is_sufficient("   ", []) is False


# --------------------------------------------------------------------------
# The high-specificity screen path is untouched
# --------------------------------------------------------------------------

@pytest.mark.parametrize(
    "message",
    [
        "khó thở dữ dội",
        "không thở nổi",
        "bất tỉnh",
        "co giật liên hồi",
        "chảy máu không cầm",
        "đau thắt ngực",
        "tôi sắp chết",
    ],
)
def test_high_specificity_phrases_still_raise_a_candidate(message: str) -> None:
    """These never reach the evidence check; the screen confirms them directly."""
    candidate = screen_red_flag_candidate(message)

    assert candidate is not None, message
    assert candidate["status"] == "CANDIDATE"
    assert candidate["candidate_esi"] in {1, 2}


def test_the_screen_still_proposes_rather_than_confirms() -> None:
    """A candidate is not a red flag. Contextual validation still owns that."""
    candidate = screen_red_flag_candidate("khó thở dữ dội")

    assert candidate is not None
    assert candidate["status"] == "CANDIDATE"
    assert "is_red_flag" not in candidate
    assert "esi_level" not in candidate


# --------------------------------------------------------------------------
# Nothing is dropped -- the concern stays open
# --------------------------------------------------------------------------

def test_the_qualifier_table_is_accent_insensitive() -> None:
    """Patients type Vietnamese with and without diacritics."""
    assert emergency_evidence_is_sufficient("kho tho du doi", []) is True
    assert emergency_evidence_is_sufficient("khó thở dữ dội", []) is True


def test_severity_wording_inside_a_longer_sentence_still_counts() -> None:
    assert emergency_evidence_is_sufficient(
        "Chào bác sĩ, từ sáng nay tôi thấy khó thở dữ dội lắm ạ", []
    ) is True
