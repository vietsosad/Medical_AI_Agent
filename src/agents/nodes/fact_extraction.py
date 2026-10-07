"""Turn one patient message into evidenced canonical facts.

Every message is a chance to learn anything, not only an answer to the question
we happen to have asked. "Tôi 67 tuổi, đau ngực từ sáng, lúc nãy đau lan xuống
tay trái, hơi khó thở và đang uống thuốc huyết áp" carries six facts, each with
its own certainty and its own time.

Extraction here is deterministic and conservative by design:

* nothing is recorded without a matched span of the patient's own words;
* hedged phrasing ("hình như", "hơi") becomes UNCERTAIN, not KNOWN;
* denial ("không đau ngực") becomes NEGATED, which is not the same as never
  having been asked;
* anything the system worked out rather than heard is SYSTEM_INFERENCE.

It never fills a gap with a default. A fact that was not stated stays absent,
and an absent fact reads as UNKNOWN.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from typing import Any

from src.agents.canonical_state import (
    CanonicalPatientState,
    FactSource,
    FactStatus,
)
from src.agents.nodes.intent_classifier import normalize_vietnamese_text
from src.agents.nodes.severity_extraction import extract_severity_score
from src.agents.nodes.temporal_context import (
    has_anaphoric_reference,
    is_correction,
    read_temporal_context,
    split_temporal_clauses,
)

# Symptoms we can name confidently. Each maps to a stable fact key so the same
# complaint always lands on the same entity across turns.
SYMPTOM_LEXICON: tuple[tuple[str, str], ...] = (
    ("dau nguc", "chest_pain"),
    ("tuc nguc", "chest_pain"),
    ("dau that nguc", "chest_pain"),
    ("kho tho", "dyspnea"),
    ("kho tho", "dyspnea"),
    ("dau dau", "headache"),
    ("dau bung", "abdominal_pain"),
    ("dau lung", "back_pain"),
    ("dau hong", "sore_throat"),
    ("buon non", "nausea"),
    ("non", "vomiting"),
    ("sot", "fever"),
    ("ho", "cough"),
    ("chong mat", "dizziness"),
    ("choang", "lightheadedness"),
    ("tieu chay", "diarrhea"),
    ("phat ban", "rash"),
    ("chay mau", "bleeding"),
    ("ngat", "syncope"),
    ("co giat", "seizure"),
    ("va mo hoi", "diaphoresis"),
    ("tim dap nhanh", "palpitations"),
    ("danh trong nguc", "palpitations"),
    # -- Everyday wording -------------------------------------------------
    # Patients do not use clinical vocabulary. Someone typing "buồn ỉa" or
    # "đau bao tử" was previously extracted as *nothing at all*, which left the
    # case undifferentiated and the conversation with no clinical content to
    # work from. These are additional wordings for symptoms the lexicon already
    # recognises, not new clinical categories.
    #
    # Still PENDING_CLINICAL_REVIEW, like every other entry in this table: the
    # mapping from colloquial phrasing to a canonical symptom is a clinical
    # judgement that no clinician here has signed off on. In particular the
    # urgency terms below ("buồn ỉa", "mót ỉa") describe an urge to defecate,
    # which is not identical to diarrhoea and is grouped with it provisionally.
    ("buon ia", "diarrhea"),
    ("mot ia", "diarrhea"),
    ("di ngoai long", "diarrhea"),
    ("di ngoai nhieu lan", "diarrhea"),
    ("di cau long", "diarrhea"),
    ("di ngoai", "diarrhea"),
    ("dau bao tu", "abdominal_pain"),
    ("dau da day", "abdominal_pain"),
    ("dau quan bung", "abdominal_pain"),
    ("quan bung", "abdominal_pain"),
    ("nhuc dau", "headache"),
    ("dau nua dau", "headache"),
    ("xay xam", "lightheadedness"),
    ("buon oi", "nausea"),
    ("non oi", "vomiting"),
    ("rat hong", "sore_throat"),
    ("ngua hong", "sore_throat"),
    ("dau rat hong", "sore_throat"),
    ("hut hoi", "dyspnea"),
    ("tho doc", "dyspnea"),
    ("tho gap", "dyspnea"),
    ("len con co giat", "seizure"),
    ("xiu", "syncope"),
    ("ngat xiu", "syncope"),
)

# Longest first, so "đau thắt ngực" wins over "đau ngực".
_ORDERED_SYMPTOMS = tuple(
    sorted(SYMPTOM_LEXICON, key=lambda item: len(item[0]), reverse=True)
)

# What a patient should actually read for each canonical symptom.
#
# The lexicon above is accent-folded so it can match what people type; folded
# text is unreadable ("dau bung") and the canonical key is English
# ("abdominal_pain"). Neither belongs in a sentence shown to a Vietnamese
# patient, so the display wording is kept separately and deliberately.
SYMPTOM_DISPLAY_VI: dict[str, str] = {
    "chest_pain": "đau ngực",
    "dyspnea": "khó thở",
    "headache": "đau đầu",
    "abdominal_pain": "đau bụng",
    "back_pain": "đau lưng",
    "sore_throat": "đau họng",
    "nausea": "buồn nôn",
    "vomiting": "nôn",
    "fever": "sốt",
    "cough": "ho",
    "dizziness": "chóng mặt",
    "lightheadedness": "choáng váng",
    "diarrhea": "tiêu chảy",
    "rash": "phát ban",
    "bleeding": "chảy máu",
    "syncope": "ngất",
    "seizure": "co giật",
    "diaphoresis": "vã mồ hôi",
    "palpitations": "tim đập nhanh",
}

# Non-symptom fields the conversation asks about, in the patient's language.
FIELD_DISPLAY_VI: dict[str, str] = {
    "chief_complaint": "triệu chứng chính",
    "onset_time": "thời điểm bắt đầu",
    "severity_score": "mức độ đau",
    "radiation": "hướng lan của cơn đau",
    "medication": "thuốc đang dùng",
    "associated_symptoms": "các triệu chứng đi kèm",
    "vital.temperature_c": "nhiệt độ cơ thể",
    "vital.spo2": "nồng độ oxy trong máu",
    "vital.heart_rate": "nhịp tim",
    "vital.systolic_bp": "huyết áp",
    "age": "tuổi",
    "recent_procedure_context": "thủ thuật gần đây",
    "clinical_memory_confirmation": "thông tin bệnh sử",
    "clinical_memory_update_detail": "thay đổi trong bệnh sử",
}

# Used when a key has no wording of its own. Vague on purpose: a generic phrase
# reads as a normal question, whereas a leaked identifier reads as a bug and
# tells the patient nothing.
_UNNAMED_FIELD_VI = "triệu chứng bạn vừa mô tả"

# Wordings that mean something else entirely once a particular word follows.
# "đi ngoài" is a bowel movement; "đi ngoài đường" is walking down the street.
# Without this, "Tôi đi ngoài đường bị ngã" records diarrhoea -- a symptom the
# patient never reported, attached to their record as a patient-reported fact.
_DISQUALIFYING_FOLLOWERS: dict[str, tuple[str, ...]] = {
    "di ngoai": ("duong", "pho", "san", "bien", "cong", "ngo", "hem"),
}


# Symptom surfaces that are only a symptom when the patient's own tone marks
# say so.
#
# Accent folding is what lets the lexicon match "kho tho" from someone typing
# without diacritics. It is also what turns "hồ sơ" into "ho so", so a patient
# answering "xác nhận hồ sơ sức khỏe" was recorded as reporting a **cough** --
# a fabricated clinical finding, added to the problem list, characterised, and
# carried into the confirmation summary. "một xíu" (a little) folds onto "xỉu"
# (fainting), which is worse.
#
# The rule: when the patient's original wording carries tone marks, they are
# read, and a spelling that is not this symptom's own is not this symptom.
# Wholly unaccented text is still accepted, because a great many people type
# that way and rejecting it would lose real reports.
_TONE_SENSITIVE_SURFACES: dict[str, frozenset[str]] = {
    "ho": frozenset({"ho"}),
    "non": frozenset({"non", "nôn"}),
    "sot": frozenset({"sot", "sốt"}),
    "ngat": frozenset({"ngat", "ngất"}),
    "xiu": frozenset({"xiu", "xỉu"}),
    "choang": frozenset({"choang", "choáng"}),
    "non oi": frozenset({"non oi", "nôn ói"}),
    "ngat xiu": frozenset({"ngat xiu", "ngất xỉu"}),
}


def _aligned_pair(clause: str) -> tuple[str, str]:
    """The patient's wording and its index-aligned accent fold.

    Whitespace is normalised on the original *before* folding, so the two
    strings share indices and a match found on the fold can be checked against
    what the patient actually wrote.
    """
    original = re.sub(r"\s+", " ", clause).strip().lower()
    return original, _fold_aligned(original)


def _tone_conflicts(original: str, start: int, end: int, term: str) -> bool:
    """Whether the patient's own spelling says this is a different word."""
    accepted = _TONE_SENSITIVE_SURFACES.get(term)
    if accepted is None:
        return False
    if len(original) < end:
        return False
    return original[start:end] not in accepted


def _has_disqualifying_follower(folded: str, term: str, end: int) -> bool:
    followers = _DISQUALIFYING_FOLLOWERS.get(term)
    if not followers:
        return False
    tail = folded[end:end + 12].strip()
    return any(
        re.match(rf"{re.escape(word)}(?![a-z0-9])", tail) for word in followers
    )


def describe_fact_key(key: str) -> str:
    """Patient-facing Vietnamese for a canonical fact key.

    Never returns an internal identifier. Anything unrecognised falls back to a
    neutral phrase, because showing a patient ``complaint.abdominal_pain`` is
    worse than showing them slightly less detail.
    """
    field = str(key or "").strip()
    if not field:
        return _UNNAMED_FIELD_VI
    if field in FIELD_DISPLAY_VI:
        return FIELD_DISPLAY_VI[field]
    for prefix in ("symptom.", "complaint.", "associated."):
        if field.startswith(prefix):
            canonical = field[len(prefix):]
            return SYMPTOM_DISPLAY_VI.get(canonical, _UNNAMED_FIELD_VI)
    return SYMPTOM_DISPLAY_VI.get(field, _UNNAMED_FIELD_VI)

_NEGATION_MARKERS = ("khong", "chua", "ko", "chang", "khong he", "khong bi")
# Epistemic hedging: the patient is unsure *whether* the symptom is there.
#
# "hơi" was here and is not one of these. It is an intensity qualifier -- "hơi
# chóng mặt" asserts dizziness and grades it as mild -- and reading it as
# uncertainty made a stated complaint permanently unconfirmable: the live audit
# shows a patient saying "hơi khó thở" being asked what their symptom was three
# times and then handed to a clinician for "question space exhausted". Mildness
# is recorded on the observation, never as doubt about the fact.
_HEDGE_MARKERS = (
    "hinh nhu",
    "co ve",
    "co le",
    "khong chac",
    "chac la",
    "dai loai",
    "kieu nhu",
    "khong ro",
    "may may",
)

# Intensity qualifiers. They modify how bad a symptom is, not whether it is
# real, so they never downgrade a fact to UNCERTAIN.
_MILD_INTENSITY_MARKERS = ("hoi", "nhe nhe", "it thoi", "chut it")
_RESOLVED_MARKERS = ("het roi", "da het", "khoi roi", "da khoi", "do roi", "het han")

# Verbs that say a *named* symptom has ended: "hết sốt", "khỏi đau", "dứt cơn
# ho". These matter because the resolution sits immediately before the symptom
# word, so the phrase-level markers above cannot see it -- "het roi" never
# matches "het sot roi" -- and the symptom would otherwise be recorded as
# currently present on the strength of the patient saying it had stopped.
#
# Kept deliberately narrow. "đỡ" folds to "do", which collides with "độ"
# (degree) and "đó" (that), and "bớt" means reduced rather than gone; treating
# either as a denial would erase a symptom the patient still has.
_RESOLUTION_VERBS = ("het", "khoi", "dut")


@dataclass(frozen=True)
class ExtractedFact:
    """One candidate fact plus the evidence that produced it."""

    key: str
    value: Any
    status: FactStatus
    source: FactSource
    temporal: str
    temporal_label: str | None
    raw_span: str
    confidence: float | None = None
    entity_label: str | None = None
    # Short structured annotation carried through to the canonical observation.
    # Used to tell "the patient hedged" apart from "the patient told us they
    # cannot answer" -- both are UNCERTAIN, but only one is worth asking again.
    note: str | None = None


def _fold(text: str) -> str:
    return re.sub(r"\s+", " ", normalize_vietnamese_text(text)).strip()


def _fold_aligned(text: str) -> str:
    """Fold accents without changing length or trimming.

    Every Vietnamese precomposed letter decomposes to exactly one base letter,
    so the folded string stays index-aligned with the original. That lets a
    match found on folded text be sliced back out of the patient's own wording,
    instead of storing "5 gio" where they wrote "5 giờ".
    """
    decomposed = unicodedata.normalize("NFD", text.lower())
    folded = "".join(
        character
        for character in decomposed
        if unicodedata.category(character) != "Mn"
    )
    return folded.replace("đ", "d")


def _original_span(text: str, folded: str, start: int, end: int) -> str:
    """Slice the patient's original wording for a match found on folded text."""
    if len(folded) == len(text):
        return text[start:end].strip()
    return folded[start:end].strip()


def _window_before(folded: str, start: int, width: int = 28) -> str:
    return folded[max(0, start - width) : start]


def _is_negated(folded: str, start: int) -> bool:
    window = _window_before(folded, start)
    return bool(re.search(r"(?:khong|chua|ko|chang)(?:\s+\w+){0,2}\s*$", window))


def _is_hedged(folded: str, start: int) -> bool:
    """Whether the patient hedged about *this* symptom, not merely nearby.

    Matched on word boundaries. A bare substring test read "vã mồ hôi" as a
    hedge for whatever followed it, because "hoi" appears inside "mo hoi".
    """
    window = _window_before(folded, start)
    return any(
        re.search(rf"(?<![a-z0-9]){re.escape(marker)}(?![a-z0-9])", window)
        for marker in _HEDGE_MARKERS
    )


def has_mild_intensity(folded: str, start: int) -> bool:
    """Whether the symptom was reported as mild. Not doubt; a grading."""
    window = _window_before(folded, start, width=16)
    return any(
        re.search(rf"(?<![a-z0-9]){re.escape(marker)}(?![a-z0-9])\s*$", window)
        for marker in _MILD_INTENSITY_MARKERS
    )


def _is_resolved_symptom(folded: str, start: int) -> bool:
    """Does a resolution verb sit immediately before this symptom word?

    Adjacency is the whole test. "hết sốt" is a denial about now; "đau hết cả
    người" -- pain across the whole body -- puts the same syllable *after* the
    symptom and means the opposite, so only what precedes the symptom counts.
    """
    window = _window_before(folded, start, width=20)
    pattern = "|".join(_RESOLUTION_VERBS)
    return bool(re.search(rf"(?:{pattern})(?:\s+\w+)?\s*$", window))


def _status_for(folded: str, start: int) -> FactStatus:
    """Denial and hedging are different clinical states, and neither is KNOWN."""
    if _is_negated(folded, start):
        return "NEGATED"
    if _is_resolved_symptom(folded, start):
        # "Giờ tôi hết sốt rồi" is the patient stating the symptom is not
        # present, which is a denial -- not a report that they have a fever.
        return "NEGATED"
    if _is_hedged(folded, start):
        return "UNCERTAIN"
    return "KNOWN"


def extract_symptom_facts(clause: str) -> list[ExtractedFact]:
    original, folded = _aligned_pair(clause)
    reading = read_temporal_context(clause)
    resolved = any(marker in folded for marker in _RESOLVED_MARKERS)
    found: list[tuple[int, ExtractedFact]] = []
    claimed: list[tuple[int, int]] = []

    for term, key in _ORDERED_SYMPTOMS:
        for match in re.finditer(rf"(?<![a-z0-9]){re.escape(term)}(?![a-z0-9])", folded):
            if any(start <= match.start() < end for start, end in claimed):
                continue
            if _has_disqualifying_follower(folded, term, match.end()):
                continue
            if _tone_conflicts(original, match.start(), match.end(), term):
                continue
            claimed.append((match.start(), match.end()))
            status = _status_for(folded, match.start())
            temporal = reading.context
            if resolved and temporal == "UNKNOWN_TIME":
                # "lúc nãy khó thở, giờ đã hết" is a symptom that changed state,
                # not a symptom that is currently present.
                temporal = "HISTORICAL"
            found.append(
                (
                    match.start(),
                    ExtractedFact(
                        key=f"symptom.{key}",
                        value=True if status != "NEGATED" else False,
                        status=status,
                        source="PATIENT_REPORTED",
                        temporal=temporal,
                        temporal_label=reading.label,
                        raw_span=term,
                        entity_label=term,
                    ),
                )
            )
            break
    # Mention order, not lexicon order. The table is scanned longest-surface
    # first so "đau thắt ngực" beats "đau ngực", but that scan order has
    # nothing to do with what the patient led with -- and "đau đầu và buồn
    # nôn" must record the headache first, because the problem the patient
    # named first is the one the conversation treats as primary.
    return [fact for _, fact in sorted(found, key=lambda item: item[0])]


def symptom_key_for_phrase(phrase: str) -> str | None:
    """Map a complaint phrase to its canonical symptom key, or None.

    The single place a Vietnamese symptom wording is turned into a canonical
    key. The projection and the cluster classifier both use it, so no consumer
    needs its own private table of symptom names.
    """
    original, folded = _aligned_pair(phrase)
    if not folded:
        return None
    for term, key in _ORDERED_SYMPTOMS:
        match = re.search(rf"(?<![a-z0-9]){re.escape(term)}(?![a-z0-9])", folded)
        if not match:
            continue
        if _has_disqualifying_follower(folded, term, match.end()):
            continue
        if _tone_conflicts(original, match.start(), match.end(), term):
            continue
        return key
    return None


def complaint_slug(phrase: str) -> str:
    """A stable canonical key for one complaint phrase."""
    folded = _fold(phrase)
    mapped = symptom_key_for_phrase(phrase)
    if mapped:
        return mapped
    return re.sub(r"[^a-z0-9]+", "_", folded).strip("_")[:60] or "unspecified"


def extract_age(clause: str) -> ExtractedFact | None:
    folded = _fold(clause)
    match = re.search(r"(?<!\d)(\d{1,3})\s*tuoi(?![a-z0-9])", folded)
    if not match:
        return None
    age = int(match.group(1))
    if not 0 < age < 130:
        return None
    return ExtractedFact(
        key="age",
        value=age,
        status="KNOWN",
        source="PATIENT_REPORTED",
        temporal="CURRENT",
        temporal_label=None,
        raw_span=match.group(0),
    )


def extract_radiation(clause: str) -> ExtractedFact | None:
    folded = _fold_aligned(clause)
    negative = re.search(
        r"\b(?:khong|chua|ko|chang)(?:\s+(?:co|bi|thay))?\s+lan\b",
        folded,
    )
    if negative:
        reading = read_temporal_context(clause)
        return ExtractedFact(
            key="radiation",
            value="không lan",
            status="KNOWN",
            source="PATIENT_REPORTED",
            temporal=reading.context,
            temporal_label=reading.label,
            raw_span=_original_span(clause, folded, *negative.span(0)),
        )
    match = re.search(
        r"(?<![a-z0-9])lan\s+(?:xuong|len|ra|sang|toi|den)?\s*"
        r"([a-z]+(?:\s+[a-z]+){0,3})",
        folded,
    )
    if not match:
        return None
    # "lan" (to spread) and "lần" (a count) fold to the same ASCII token, and
    # folding is index-aligned, so the patient's own spelling settles it.
    # Without this, "chưa nôn lần nào" records a radiation of "nào": a claim
    # about pain spreading, invented from a sentence about how often someone
    # vomited.
    if clause[match.start() : match.start() + 3].lower() != "lan":
        return None
    # Trim trailing conjunctions so "tay trai va hoi kho tho" stops at "tay trai".
    trimmed = re.split(r"\b(?:va|roi|nhung|kem|con)\b", match.group(1))[0]
    start = match.start(1)
    target = _original_span(clause, folded, start, start + len(trimmed))
    if not target:
        return None
    return ExtractedFact(
        key="radiation",
        value=target,
        status="KNOWN",
        source="PATIENT_REPORTED",
        temporal=read_temporal_context(clause).context,
        temporal_label=None,
        raw_span=_original_span(clause, folded, *match.span(0)),
    )


def extract_medications(clause: str) -> list[ExtractedFact]:
    folded = _fold_aligned(clause)
    facts: list[ExtractedFact] = []
    for match in re.finditer(
        r"(?:dang\s+)?(?:uong|dung|su dung|tiem)\s+thuoc\s+"
        r"([a-z0-9]+(?:\s+[a-z0-9]+){0,3})",
        folded,
    ):
        trimmed = re.split(r"\b(?:va|roi|nhung|tu|duoc|moi)\b", match.group(1))[0]
        start = match.start(1)
        name = _original_span(clause, folded, start, start + len(trimmed))
        if not name:
            continue
        facts.append(
            ExtractedFact(
                key="medication",
                value=name,
                status="NEGATED" if _is_negated(folded, match.start()) else "KNOWN",
                source="PATIENT_REPORTED",
                temporal=read_temporal_context(clause).context,
                temporal_label=None,
                raw_span=_original_span(clause, folded, *match.span(0)),
            )
        )
    return facts


def extract_temperature(clause: str) -> ExtractedFact | None:
    folded = _fold(clause)
    # Allow the filler patients actually use: "sốt 39 độ", "nhiệt độ còn 37.8",
    # "nhiệt độ khoảng 38".
    match = re.search(
        r"(?:sot|nhiet do)\s*"
        r"(?:la|:|=|con|chi con|khoang|chi|do)?\s*"
        r"(\d{2}(?:[.,]\d)?)\s*(?:do|c)?(?![a-z0-9])",
        folded,
    )
    if not match:
        match = re.search(r"(?<!\d)(\d{2}[.,]\d)\s*(?:do|c)?(?![a-z0-9])", folded)
    if not match:
        return None
    value = float(match.group(1).replace(",", "."))
    if not 30.0 <= value <= 45.0:
        return None
    reading = read_temporal_context(clause)
    return ExtractedFact(
        key="vital.temperature_c",
        value=value,
        status="KNOWN",
        source="PATIENT_REPORTED",
        temporal=reading.context,
        temporal_label=reading.label,
        raw_span=match.group(0),
    )


def extract_onset(clause: str) -> ExtractedFact | None:
    folded = _fold_aligned(clause)
    matches = re.finditer(
        r"(?:tu|khoang|bat dau tu|duoc)?\s*"
        r"((?:\d+\s*(?:phut|gio|tieng|ngay|tuan|thang))"
        r"|(?:vai|may)\s+(?:phut|gio|tieng|ngay|tuan|thang)"
        r"|(?:sang|trua|chieu|dem)(?:\s+(?:nay|qua|hom qua))?"
        r"|toi\s+(?:nay|qua|hom qua)"
        r"|hom nay|hom qua|tuan truoc"
        r"|vua\s+(?:moi\s+)?bi|moi\s+bi|vua\s+dau|moi\s+dau)",
        folded,
    )
    for match in matches:
        # In a correction such as "tối qua, không phải sáng nay", the
        # retracted time is evidence about what is false, not a second onset.
        # Recording both as corrections made the negated value win merely
        # because it appeared last in the sentence.
        if _is_negated(folded, match.start(1)):
            continue
        value = _original_span(clause, folded, *match.span(1))
        return ExtractedFact(
            key="onset_time",
            value=value,
            status="KNOWN",
            source="PATIENT_REPORTED",
            temporal="RELATIVE",
            temporal_label=value,
            raw_span=_original_span(clause, folded, *match.span(0)),
        )
    return None


def extract_facts(
    message: str,
    *,
    severity_question_active: bool = False,
) -> list[ExtractedFact]:
    """Read every fact the message supports, independent of the open question."""
    if not message or not message.strip():
        return []

    # Imported here rather than at module scope: the attribute extractors reuse
    # this module's folding and negation helpers, so a top-level import would
    # be circular.
    from src.agents.nodes.problem_attribute_extraction import (
        extract_problem_attributes,
    )

    facts: list[ExtractedFact] = []
    for clause in split_temporal_clauses(message):
        facts.extend(extract_symptom_facts(clause))
        for extractor in (
            extract_age,
            extract_radiation,
            extract_temperature,
            extract_onset,
        ):
            found = extractor(clause)
            if found is not None:
                facts.append(found)
        facts.extend(extract_medications(clause))
        # Problem characterisation -- how it started, where, what it feels
        # like. Read from every message, not only from an answer to the
        # question that happened to be open.
        facts.extend(extract_problem_attributes(clause))

    severity = extract_severity_score(
        message,
        severity_question_active=severity_question_active,
    )
    if severity.score is not None:
        facts.append(
            ExtractedFact(
                key="severity_score",
                value=severity.score,
                status="KNOWN",
                source="PATIENT_REPORTED",
                temporal="CURRENT",
                temporal_label=None,
                raw_span=message.strip()[:120],
                confidence=1.0 if severity.evidence == "explicit_pain_score" else 0.8,
            )
        )

    # Drop exact duplicates produced by overlapping clauses, keeping the first.
    unique: list[ExtractedFact] = []
    seen: set[tuple[str, Any, str]] = set()
    for fact in facts:
        signature = (fact.key, str(fact.value), fact.temporal)
        if signature in seen:
            continue
        seen.add(signature)
        unique.append(fact)
    return unique


def apply_message_to_state(
    state: CanonicalPatientState,
    message: str,
    *,
    turn_id: str = "",
    severity_question_active: bool = False,
) -> list[ExtractedFact]:
    """Run the state update pipeline for one patient message.

    normalize -> extract -> entity link -> temporal -> provenance ->
    correction/contradiction -> canonical update.
    """
    correction = is_correction(message)
    facts = extract_facts(
        message,
        severity_question_active=severity_question_active,
    )

    # An anaphoric reference with no new symptom named attaches to the symptom
    # already under discussion, instead of starting a second one.
    if has_anaphoric_reference(message) and not any(
        fact.key.startswith("symptom.") for fact in facts
    ):
        entity = state.most_recent_entity()
        if entity is not None:
            for index, fact in enumerate(facts):
                if fact.key in {"onset_time", "severity_score"}:
                    facts[index] = ExtractedFact(
                        key=f"{entity.normalized}.{fact.key}",
                        value=fact.value,
                        status=fact.status,
                        source=fact.source,
                        temporal=fact.temporal,
                        temporal_label=fact.temporal_label,
                        raw_span=fact.raw_span,
                        confidence=fact.confidence,
                        entity_label=entity.label,
                    )

    for fact in facts:
        if fact.entity_label and fact.key.startswith("symptom."):
            state.upsert_entity(
                fact.entity_label,
                fact.key.removeprefix("symptom."),
                turn_id=turn_id,
            )
        state.record(
            fact.key,
            fact.value,
            status=fact.status,
            source=fact.source,
            temporal=fact.temporal,
            temporal_label=fact.temporal_label,
            raw_span=fact.raw_span,
            turn_id=turn_id,
            confidence=fact.confidence,
            is_correction=correction,
            note=fact.note,
        )
    return facts
