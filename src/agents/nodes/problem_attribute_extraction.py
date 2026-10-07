"""Deterministic extraction for the problem attributes a conversation asks about.

:mod:`fact_extraction` reads the facts a patient volunteers in almost any
message -- symptoms, age, onset, severity, temperature, radiation. It does not
read the *characterisation* of a problem: whether a headache came on suddenly,
where it hurts, what it feels like, whether it is the worst they have ever had.
Those are precisely the answers an adaptive conversation asks for, so without
them every answer would leave its own question still unanswered and the planner
would ask again.

The same rules apply as everywhere else in extraction:

* nothing is recorded without a matched span of the patient's own words;
* a denial is NEGATED, not absent;
* a hedge is UNCERTAIN, not KNOWN;
* nothing is inferred, defaulted or filled in.

Attributes recorded here land on shared canonical keys (``course``,
``character``, ...) and are attributed to the *primary* problem by
:mod:`src.agents.problem_state`. When the agent asked about a specific
problem's attribute, :func:`extract_answer_for_target` instead records the
reply under the entity-scoped key, so the answer belongs to the problem that
was actually asked about.
"""

from __future__ import annotations

import re

from src.agents.nodes.fact_extraction import (
    ExtractedFact,
    _fold_aligned,
    _is_hedged,
    _is_negated,
    _original_span,
)
from src.agents.nodes.temporal_context import read_temporal_context

# Folded surface -> canonical value. Values stay Vietnamese because they are
# shown back to the patient in the confirmation summary and are translated for
# retrieval by the clinical query planner, never by string substitution here.
_COURSE_PATTERNS: tuple[tuple[str, str], ...] = (
    (r"dot ngot|bat ngo|dung mot cai|tu nhien(?:\s+dau)?|nhu bua bo", "đột ngột"),
    (r"tang dan|nang dan|nang len dan|tu tu tang|moi luc mot", "tăng dần"),
    (r"giam dan|do dan|nhe dan|dang do", "giảm dần"),
    (r"tung con|thanh con|luc co luc khong|ngat quang", "từng cơn"),
    (r"lien tuc|khong dut|suot|am i ca ngay", "liên tục"),
)

_CHARACTER_PATTERNS: tuple[tuple[str, str], ...] = (
    (r"am i", "âm ỉ"),
    (r"nhoi|dau nhoi|nhu kim cham|cham kim", "nhói"),
    (r"bop nghet|bop chat|nhu bi bop|de nang|nhu co vat nang", "bóp nghẹt"),
    (r"gian giat|giat giat|theo nhip mach|nhu mach dap", "giật theo nhịp"),
    (r"boi rat|nong rat|rat bong", "bỏng rát"),
    (r"quan that|quan con|co that", "quặn"),
    (r"cang tuc|nang dau|nhu cang ra", "căng tức"),
)

# "The worst headache of my life" is a specific, high-value answer, so it is
# read as its own attribute rather than folded into severity.
_WORST_EVER_PATTERNS = (
    r"dau nhat tu truoc den nay",
    r"dau nhat tu truoc toi nay",
    r"chua bao gio dau (?:nhu|the) (?:vay|nay)",
    r"nang nhat tu truoc den nay",
    r"du doi nhat",
    r"worst (?:headache|pain)",
)

# Body locations patients name. Deliberately coarse: the value is the patient's
# own wording, and this table only decides that a location *was* stated.
_LOCATION_CUES = (
    r"nua dau (?:ben )?(?:trai|phai)",
    r"(?:vung |o )?(?:tran|gay|dinh dau|thai duong|sau gay)",
    r"(?:ben )?(?:trai|phai) (?:dau|nguc|bung|lung)",
    r"(?:vung |o )?(?:thuong vi|ha suon|quanh ron|ho chau|bung duoi|bung tren)",
    r"(?:vung |o )?(?:nguc trai|nguc phai|giua nguc|sau xuong uc)",
    r"(?:vung |o )?(?:that lung|lung duoi|lung tren)",
)

_FREQUENCY_PATTERN = (
    r"(\d{1,2})\s*(?:lan|con)\b"
    r"(?:\s*(?:mot|trong|tren|\/)?\s*(?:ngay|gio|tieng|dem|buoi))?"
)


def _matched(
    clause: str,
    key: str,
    patterns: tuple[tuple[str, str], ...],
) -> ExtractedFact | None:
    """First matching canonical value, with the patient's wording as evidence."""
    folded = _fold_aligned(clause)
    for pattern, value in patterns:
        match = re.search(pattern, folded)
        if not match:
            continue
        if _is_negated(folded, match.start()):
            continue
        reading = read_temporal_context(clause)
        return ExtractedFact(
            key=key,
            value=value,
            status="UNCERTAIN" if _is_hedged(folded, match.start()) else "KNOWN",
            source="PATIENT_REPORTED",
            temporal=reading.context,
            temporal_label=reading.label,
            raw_span=_original_span(clause, folded, *match.span(0)),
        )
    return None


def extract_course(clause: str) -> ExtractedFact | None:
    return _matched(clause, "course", _COURSE_PATTERNS)


def extract_character(clause: str) -> ExtractedFact | None:
    return _matched(clause, "character", _CHARACTER_PATTERNS)


def extract_worst_ever(clause: str) -> ExtractedFact | None:
    folded = _fold_aligned(clause)
    for pattern in _WORST_EVER_PATTERNS:
        match = re.search(pattern, folded)
        if not match:
            continue
        negated = _is_negated(folded, match.start())
        return ExtractedFact(
            key="worst_ever",
            value=not negated,
            status="NEGATED" if negated else "KNOWN",
            source="PATIENT_REPORTED",
            temporal="CURRENT",
            temporal_label=None,
            raw_span=_original_span(clause, folded, *match.span(0)),
        )
    return None


def extract_location(clause: str) -> ExtractedFact | None:
    folded = _fold_aligned(clause)
    for pattern in _LOCATION_CUES:
        match = re.search(pattern, folded)
        if not match:
            continue
        if _is_negated(folded, match.start()):
            continue
        value = _original_span(clause, folded, *match.span(0))
        if not value:
            continue
        return ExtractedFact(
            key="location",
            value=value[:80],
            status="KNOWN",
            source="PATIENT_REPORTED",
            temporal=read_temporal_context(clause).context,
            temporal_label=None,
            raw_span=value,
        )
    return None


def extract_frequency(clause: str) -> ExtractedFact | None:
    folded = _fold_aligned(clause)
    match = re.search(_FREQUENCY_PATTERN, folded)
    if not match:
        return None
    value = _original_span(clause, folded, *match.span(0))
    if not value:
        return None
    return ExtractedFact(
        key="frequency",
        value=value[:40],
        status="KNOWN",
        source="PATIENT_REPORTED",
        temporal=read_temporal_context(clause).context,
        temporal_label=None,
        raw_span=value,
    )


# The extractors that run on every clause of every message, whatever was asked.
PROBLEM_ATTRIBUTE_EXTRACTORS = (
    extract_course,
    extract_character,
    extract_worst_ever,
    extract_location,
    extract_frequency,
)


def extract_problem_attributes(clause: str) -> list[ExtractedFact]:
    """Every problem-characterisation fact this clause supports."""
    facts: list[ExtractedFact] = []
    for extractor in PROBLEM_ATTRIBUTE_EXTRACTORS:
        found = extractor(clause)
        if found is not None:
            facts.append(found)
    return facts


# Replies that answer a question by declining it. They are recorded as answers
# -- the patient responded -- so the planner stops asking, without asserting a
# clinical value the patient never gave.
_NON_ANSWER_MARKERS = (
    "khong biet",
    "khong ro",
    "khong chac",
    "khong nho",
    "khong de y",
    "chua do",
    "khong do",
    "khong co may",
    "chua co so do",
)

_AFFIRMATION_MARKERS = ("co", "dung", "phai", "co a", "dung roi", "co roi", "vang")

# Annotation for "I cannot tell you", which is an answer about what the patient
# knows rather than a hedged clinical report. Both are UNCERTAIN and neither is
# a finding, but only a hedge is worth putting to them a second time -- asking
# again after someone has said they do not know is how software says it was not
# listening.
DECLINED_NOTE = "declined_unknown"

# Longest an utterance may be and still be read as the answer to the question
# we asked. Past this the patient is telling a story, and filing the whole
# thing as one attribute's value would put words in their mouth.
MAX_ANSWER_LENGTH = 160


def _leads_with_negation(folded: str) -> bool:
    """Does the reply open by denying what was asked?

    Only the opening counts. "Không sốt nhưng có buồn nôn" denies the fever;
    "Có sốt, không ho" does not, and reading a negation from anywhere in the
    sentence would flip the answer.
    """
    return bool(re.match(r"^(?:khong|chua|ko|chang)(?![a-z])", folded.strip()))


def _leads_with_affirmation(folded: str) -> bool:
    head = folded.strip().split()
    return bool(head) and head[0] in _AFFIRMATION_MARKERS


# Targets whose only valid answers are yes, no, or "I don't know". A symptom
# probe is the clearest case: recording free text as the *value* of
# ``symptom.vomiting`` asserts the patient is vomiting, whatever the sentence
# actually said. "Tôi không có nhiệt kế" answering "do you also have vomiting?"
# would become a patient-reported vomiting fact, which is a fabricated clinical
# finding and exactly what extraction is not allowed to do.
_BOOLEAN_ATTRIBUTES = frozenset(
    {
        "worst_ever",
        "associated_neuro",
        "exertion",
        "blood",
        "bowel_change",
    }
)


def _is_boolean_target(canonical_key: str) -> bool:
    if canonical_key.startswith("symptom."):
        return True
    attribute = canonical_key.split(".", 1)[1] if "." in canonical_key else canonical_key
    return attribute in _BOOLEAN_ATTRIBUTES


def extract_answer_for_target(
    message: str,
    canonical_key: str,
    *,
    introduced_new_topic: bool = False,
) -> ExtractedFact | None:
    """Record a reply as the answer to the attribute we actually asked about.

    Used only when the runtime knows which attribute was put to the patient,
    and only when the reply is plausibly *about* it. Three things it will not
    do, each of which would fabricate a clinical fact:

    * It declines when the message introduced a new symptom. "Tôi còn hơi
      chóng mặt nữa" is the patient raising something else, not an answer about
      the headache's character, and filing it as one would attach a sentence
      about dizziness to an attribute it says nothing about.
    * It declines a long message, which is a narrative rather than an answer.
    * It never normalises free text into a clinical claim: the stored value is
      the patient's own wording, and "tôi không biết" is recorded as UNCERTAIN
      so the question counts as answered without becoming a finding.
    """
    if introduced_new_topic:
        return None
    text = message.strip()
    if len(text) < 2 or len(text) > MAX_ANSWER_LENGTH:
        return None
    folded = _fold_aligned(text)
    if any(marker in folded for marker in _NON_ANSWER_MARKERS):
        return ExtractedFact(
            key=canonical_key,
            value="không rõ",
            status="UNCERTAIN",
            source="PATIENT_REPORTED",
            temporal="CURRENT",
            temporal_label=None,
            raw_span=text[:120],
            note=DECLINED_NOTE,
        )
    if _leads_with_negation(folded):
        return ExtractedFact(
            key=canonical_key,
            value=text[:120],
            status="NEGATED",
            source="PATIENT_REPORTED",
            temporal="CURRENT",
            temporal_label=None,
            raw_span=text[:120],
        )
    if _leads_with_affirmation(folded):
        return ExtractedFact(
            key=canonical_key,
            value=True,
            status="KNOWN",
            source="PATIENT_REPORTED",
            temporal="CURRENT",
            temporal_label=None,
            raw_span=text[:120],
        )
    if _is_boolean_target(canonical_key):
        # Neither yes, no, nor "I don't know". Whatever the patient said, it is
        # not an answer to this question, and inventing one from their words is
        # how a system reports a symptom nobody described. The question stays
        # open; the repeat limit stops that becoming a loop.
        return None
    return ExtractedFact(
        key=canonical_key,
        value=text[:160],
        status="KNOWN",
        source="PATIENT_REPORTED",
        temporal=read_temporal_context(text).context,
        temporal_label=None,
        raw_span=text[:160],
    )
