"""Semantic-evidence-only extraction of the patient-reported 0-10 severity score.

A digit in a patient message is not a severity score. Age, blood pressure,
dosage, duration and similar measurements all contain digits, and reading any of
them as a pain score fabricates a clinical fact the patient never reported.

Severity is therefore recorded only when the utterance carries explicit evidence
that the patient is scoring their symptom, or when the patient is directly
answering the 0-10 scale question the agent asked. Without that evidence the
score stays unset: ``None`` means UNKNOWN and is never defaulted to 0, clamped,
or guessed.

All matching runs on accent-folded text so accented, unaccented and lightly
mistyped Vietnamese behave identically.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from src.agents.nodes.intent_classifier import normalize_vietnamese_text

_SCORE = r"(?:10|[0-9])"

# A number followed by one of these belongs to another measurement, never to a
# pain score. Folded spellings, e.g. "tuổi" -> "tuoi", "ngày" -> "ngay".
_NON_SEVERITY_UNITS = (
    "tuoi", "nam", "thang", "tuan", "ngay", "gio", "tieng", "phut", "giay",
    "vien", "lan", "goi", "ong", "chai", "lo",
    "mg", "ml", "gam", "kg", "cm", "mm", "mmhg", "lit",
    "do", "%", "lit", "nhip", "lomol",
)

# Constructions that identify the number as a symptom score on their own.
_EXPLICIT_SEVERITY_PATTERNS = (
    # "7/10", "10 / 10"
    rf"(?<!\d)({_SCORE})\s*/\s*10(?!\d)",
    # "6 tren 10", "6 tren thang 10"
    rf"(?<!\d)({_SCORE})\s*tren\s*(?:thang\s*)?10(?!\d)",
    # "7 diem", "dau 8 diem"
    rf"(?<!\d)({_SCORE})\s*diem(?!\d)",
    # "muc do 7", "muc dau 6", "thang diem 8", "diem dau 9", "muc 7"
    rf"(?:muc\s*(?:do|dau)?|thang\s*diem|diem\s*dau)\s*(?:la|:|=)?\s*(?<!\d)({_SCORE})(?!\d)",
)

# Verbal intensity, accepted only while the scale question is open because these
# words are far too common in free narrative to be scored on their own.
_DESCRIPTOR_SCORES = (
    ("khong dau", 0),
    ("du doi", 9),
    ("nang", 8),
    ("vua", 5),
    ("nhe", 2),
)

_BARE_SCORE = re.compile(rf"(?<!\d)({_SCORE})(?!\d)")


@dataclass(frozen=True)
class SeverityExtraction:
    """A score plus the evidence that justified recording it."""

    score: int | None
    evidence: str | None


def _fold(text: str) -> str:
    return re.sub(r"\s+", " ", normalize_vietnamese_text(text)).strip()


def _contains_word(text: str, term: str) -> bool:
    return re.search(rf"(?<![a-z0-9]){re.escape(term)}(?![a-z0-9])", text) is not None


def _carries_other_unit(folded: str, end: int) -> bool:
    """True when the digits directly qualify a non-severity measurement."""
    tail = folded[end:].lstrip()
    if tail.startswith("%"):
        return True
    if folded[end:].startswith("/"):
        # "150/90" style readings; a genuine score uses the "/10" form, which
        # the explicit patterns already claimed before we get here.
        return True
    return any(
        _contains_word(tail[: len(unit) + 1], unit) for unit in _NON_SEVERITY_UNITS
    )


def extract_severity_score(
    query: str,
    *,
    severity_question_active: bool = False,
) -> SeverityExtraction:
    """Return a 0-10 score only when the patient actually reported one."""
    folded = _fold(query)
    if not folded:
        return SeverityExtraction(None, None)

    for pattern in _EXPLICIT_SEVERITY_PATTERNS:
        match = re.search(pattern, folded)
        if match:
            return SeverityExtraction(int(match.group(1)), "explicit_pain_score")

    if not severity_question_active:
        # Free narrative without an explicit score: severity stays UNKNOWN.
        return SeverityExtraction(None, None)

    for descriptor, score in _DESCRIPTOR_SCORES:
        if _contains_word(folded, descriptor):
            return SeverityExtraction(score, f"severity_descriptor:{descriptor}")

    for match in _BARE_SCORE.finditer(folded):
        if not _carries_other_unit(folded, match.end()):
            return SeverityExtraction(int(match.group(1)), "answer_to_scale_question")

    return SeverityExtraction(None, None)


def has_severity_evidence(
    query: str,
    *,
    severity_question_active: bool = False,
) -> bool:
    """Whether the utterance answers a severity question at all."""
    return (
        extract_severity_score(
            query,
            severity_question_active=severity_question_active,
        ).score
        is not None
    )
