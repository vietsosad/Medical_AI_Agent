"""Read Vietnamese conversational time expressions into temporal context.

Patients do not date their symptoms. They say "sáng nay", "lúc nãy", "sau khi
uống thuốc". Those phrases carry the clinical difference between a fever that
has broken and one that has not, so they belong in state rather than being
flattened into a single overwritten value.

Everything matches on accent-folded text, so "sáng nay" and "sang nay" behave
identically. Longer, more specific phrases are tested before shorter ones, so
"trước khi uống thuốc" is never mistaken for a bare "trước".
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from src.agents.canonical_state import TemporalContext
from src.agents.nodes.intent_classifier import normalize_vietnamese_text


@dataclass(frozen=True)
class TemporalReading:
    context: TemporalContext
    label: str | None
    matched: str | None


# Checked before everything else, because they change what a following time
# word means. "sáng nay tôi sốt 39" reports a past reading, but "đau ngực từ
# sáng nay" reports a symptom that started then and is still going. Reading the
# second as historical would drop a current chest pain out of the presentation.
_PRIORITY_REGEX_MARKERS: tuple[tuple[str, TemporalContext], ...] = (
    (r"(?<![a-z0-9])dang(?![a-z0-9])", "CURRENT"),
    (
        r"(?<![a-z0-9])tu\s+(?:sang|trua|chieu|toi|dem|hom|tuan|thang|nam|\d)",
        "RELATIVE",
    ),
)

# Ordered most specific first. Medication and event framing outrank plain tense,
# because "sau khi uống thuốc" is clinically richer than "sau đó".
_TEMPORAL_MARKERS: tuple[tuple[str, TemporalContext], ...] = (
    # Medication-relative
    ("truoc khi uong thuoc", "BEFORE_MEDICATION"),
    ("truoc luc uong thuoc", "BEFORE_MEDICATION"),
    ("truoc khi dung thuoc", "BEFORE_MEDICATION"),
    ("chua uong thuoc", "BEFORE_MEDICATION"),
    ("sau khi uong thuoc", "AFTER_MEDICATION"),
    ("sau luc uong thuoc", "AFTER_MEDICATION"),
    ("sau khi dung thuoc", "AFTER_MEDICATION"),
    ("uong thuoc xong", "AFTER_MEDICATION"),
    ("sau uong thuoc", "AFTER_MEDICATION"),
    # Event-relative
    ("truoc khi an", "BEFORE_EVENT"),
    ("truoc khi ngu", "BEFORE_EVENT"),
    ("truoc khi van dong", "BEFORE_EVENT"),
    ("truoc khi", "BEFORE_EVENT"),
    ("truoc luc", "BEFORE_EVENT"),
    ("sau khi an", "AFTER_EVENT"),
    ("sau khi van dong", "AFTER_EVENT"),
    ("sau khi gang suc", "AFTER_EVENT"),
    ("sau khi ngu day", "AFTER_EVENT"),
    ("sau khi", "AFTER_EVENT"),
    ("sau luc", "AFTER_EVENT"),
    ("sau van dong", "AFTER_EVENT"),
    # Explicitly now
    ("ngay luc nay", "CURRENT"),
    ("ngay bay gio", "CURRENT"),
    ("hien tai", "CURRENT"),
    ("hien nay", "CURRENT"),
    ("bay gio", "CURRENT"),
    ("luc nay day", "CURRENT"),
    ("dang con", "CURRENT"),
    ("van con", "CURRENT"),
    ("gio con", "CURRENT"),
    ("gio van", "CURRENT"),
    ("gio thi", "CURRENT"),
    ("hom nay", "CURRENT"),
    # Earlier than now. "lúc nãy" and "vừa rồi" are recent but finished, and a
    # symptom reported there is not evidence about the present.
    ("luc nay", "HISTORICAL"),
    ("hoi nay", "HISTORICAL"),
    ("vua roi", "HISTORICAL"),
    ("vua xong", "HISTORICAL"),
    ("khi nay", "HISTORICAL"),
    ("sang nay", "HISTORICAL"),
    ("trua nay", "HISTORICAL"),
    ("chieu nay", "HISTORICAL"),
    ("toi qua", "HISTORICAL"),
    ("dem qua", "HISTORICAL"),
    ("hom qua", "HISTORICAL"),
    ("hom kia", "HISTORICAL"),
    ("tuan truoc", "HISTORICAL"),
    ("thang truoc", "HISTORICAL"),
    ("nam ngoai", "HISTORICAL"),
    ("truoc day", "HISTORICAL"),
    ("truoc kia", "HISTORICAL"),
    ("da tung", "HISTORICAL"),
    ("tung bi", "HISTORICAL"),
    ("hoi truoc", "HISTORICAL"),
)

# "giờ" alone means "now", but after a number it is a clock time or a duration
# ("8 giờ", "3 giờ trước") and claims nothing about the present. A literal
# substring cannot tell those apart, so this marker needs a guarded pattern.
_TEMPORAL_REGEX_MARKERS: tuple[tuple[str, TemporalContext], ...] = (
    # The digit lookbehind already removes clock times ("8 giờ") and durations.
    # Only "giờ trước"/"giờ nữa" still need excluding. Do not filter on the
    # following word beyond that: folding maps "tối" (evening) and "tôi" (I) to
    # the same token, so "giờ tôi còn đau" would be lost as a clock time.
    (r"(?<!\d)(?<!\d )\bgio\b(?!\s*(?:truoc|nua))", "CURRENT"),
)

# Durations: "cách đây 3 ngày", "3 tiếng trước", "được 2 hôm rồi".
_RELATIVE_PATTERNS: tuple[str, ...] = (
    r"cach day\s+\d+\s*(?:phut|gio|tieng|ngay|tuan|thang|nam)",
    r"\d+\s*(?:phut|gio|tieng|ngay|tuan|thang|nam)\s+truoc",
    r"duoc\s+\d+\s*(?:phut|gio|tieng|ngay|tuan|thang|hom)\s*(?:roi)?",
    r"tu\s+\d+\s*(?:phut|gio|tieng|ngay|tuan|thang)\s*(?:truoc|nay)",
)

# The patient retracting something they said earlier.
_CORRECTION_MARKERS: tuple[str, ...] = (
    "nho nham",
    "nham roi",
    "toi nham",
    "minh nham",
    "thuc ra",
    "thuc te la",
    "dinh chinh",
    "noi lai",
    "khong phai vay",
    "khong phai la",
    "y toi la",
    "sua lai",
    "cho toi sua",
    "khong dung, ",
    "a khong",
)

# References back to something already discussed.
_ANAPHORIC_MARKERS: tuple[str, ...] = (
    "toi noi luc nay",
    "toi noi hoi nay",
    "toi noi luc dau",
    "toi noi ban dau",
    "noi luc nay",
    "noi hoi nay",
    "da noi",
    "vua noi",
    "con dau do",
    "con dau ay",
    "trieu chung do",
    "trieu chung ay",
    "cai do",
    "cai ay",
    "van de do",
    "van de toi noi",
    "chuyen do",
)


def _fold(text: str) -> str:
    return re.sub(r"\s+", " ", normalize_vietnamese_text(text)).strip()


def read_temporal_context(text: str) -> TemporalReading:
    """Classify when the statement is about. Defaults to UNKNOWN_TIME.

    Unmarked speech is deliberately not assumed to be CURRENT here; callers that
    know the conversational frame decide that. Guessing "now" from silence would
    be inventing a temporal claim the patient never made.
    """
    folded = _fold(text)
    if not folded:
        return TemporalReading("UNKNOWN_TIME", None, None)

    for pattern, context in _PRIORITY_REGEX_MARKERS:
        match = re.search(pattern, folded)
        if match:
            return TemporalReading(context, match.group(0).strip(), match.group(0))

    for marker, context in _TEMPORAL_MARKERS:
        if marker in folded:
            return TemporalReading(context, marker, marker)

    for pattern, context in _TEMPORAL_REGEX_MARKERS:
        match = re.search(pattern, folded)
        if match:
            return TemporalReading(context, match.group(0).strip(), match.group(0))

    for pattern in _RELATIVE_PATTERNS:
        match = re.search(pattern, folded)
        if match:
            return TemporalReading("RELATIVE", match.group(0), match.group(0))

    return TemporalReading("UNKNOWN_TIME", None, None)


def split_temporal_clauses(text: str) -> list[str]:
    """Split a sentence carrying several times into separately readable clauses.

    "Sáng nay tôi sốt 39 độ, giờ còn 37.8" holds two observations. Reading the
    sentence as a whole would keep only one of them and silently overwrite the
    other.
    """
    parts = [
        part.strip()
        # A full stop between digits is a decimal point ("37.8"), not a clause
        # boundary. Splitting there silently truncated the reading to 37.
        for part in re.split(
            r"[,;]|(?<!\d)\.(?!\d)|\bnhưng\b|\bnhung\b|\bcòn\s+giờ\b",
            text,
            flags=re.IGNORECASE,
        )
        if part and part.strip()
    ]
    return parts or [text.strip()]


def is_correction(text: str) -> bool:
    """Whether the patient is retracting an earlier statement."""
    folded = _fold(text)
    return any(marker in folded for marker in _CORRECTION_MARKERS)


def has_anaphoric_reference(text: str) -> bool:
    """Whether the message points back at something already discussed."""
    folded = _fold(text)
    return any(marker in folded for marker in _ANAPHORIC_MARKERS)
