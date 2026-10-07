"""Shared deterministic layer for the MIETIC canonical pipeline.

Everything in this module is local and free: parsing, grouping, hashing,
demographic/vital extraction, and decision-point answer parsing. The LLM is
reserved for the parts where semantics genuinely matter (see mietic_extract).

One JSONL row is a *task*, not a patient. The three instruction templates in
MIETIC_v1 are the three ESI decision points asked about the same patients:

    A  "does the patient require immediate life-saving intervention?"
    B  "does the patient meet the criteria for ESI level 2?"
    C  "predict the exact number of resources"

so a canonical case is keyed on the normalized presentation and carries up to
three assessments. ESI is *derived* from those answers, never parsed out of the
free-text analysis.
"""

from __future__ import annotations

import hashlib
import json
import re
import unicodedata
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterator

DATASET_VERSION = "MIETIC_v1"
PARSER_VERSION = "mietic-canonical-v3"

# --------------------------------------------------------------------------
# normalization / identity
# --------------------------------------------------------------------------


def normalize(text: str) -> str:
    return re.sub(r"\s+", " ", unicodedata.normalize("NFKC", text).lower()).strip()


def sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def case_id_for(presentation: str) -> str:
    return f"mietic_c_{sha256(normalize(presentation))[:20]}"


# --------------------------------------------------------------------------
# decision-point classification
# --------------------------------------------------------------------------


def decision_point_of(instruction: str) -> str:
    """Classify a task row by which ESI decision point it asks about.

    Order matters: the DP-B prompt also contains the words "life-saving" inside
    its background knowledge, so the more specific test has to run first.
    """
    n = normalize(instruction)
    if "number of resources" in n:
        return "C"
    if "criteria for esi level 2" in n:
        return "B"
    if "immediate life-saving intervention" in n:
        return "A"
    return "UNKNOWN"


# --------------------------------------------------------------------------
# deterministic answer parsing (92-97% coverage for A and B)
# --------------------------------------------------------------------------

_A_NEG = re.compile(
    r"(?:does\s+not|do\s+not|not|no)\s+(?:appear\s+to\s+|seem\s+to\s+)?"
    r"requir\w*\s+(?:an?\s+)?immediate\s+life[-\s]?saving",
    re.I,
)
_A_POS = re.compile(
    r"(?:requires?|required|needs?|warrants?)\s+(?:an?\s+)?immediate\s+life[-\s]?saving",
    re.I,
)
_B_NEG = re.compile(
    r"(?:does\s+not|do\s+not|not)\s+(?:appear\s+to\s+|seem\s+to\s+)?"
    r"meet\s+the\s+criteria\s+for\s+esi\s+level\s+2",
    re.I,
)
_B_POS = re.compile(r"meets?\s+the\s+criteria\s+for\s+esi\s+level\s+2", re.I)

_C_COUNT = re.compile(
    r"(?:total|number)\s+(?:of\s+)?(?:anticipated\s+|expected\s+)?resources?"
    r"\s*(?:needed|required|anticipated)?\s*(?:is|=|:)\s*(\d+)",
    re.I,
)


def parse_yes_no(output: str, positive: re.Pattern, negative: re.Pattern) -> bool | None:
    """A negation anywhere wins: these analyses state the conclusion once."""
    if negative.search(output):
        return False
    if positive.search(output):
        return True
    return None


def parse_dp_a(output: str) -> bool | None:
    return parse_yes_no(output, _A_POS, _A_NEG)


def parse_dp_b(output: str) -> bool | None:
    return parse_yes_no(output, _B_POS, _B_NEG)


def parse_dp_c(output: str) -> int | None:
    match = _C_COUNT.search(output)
    return int(match.group(1)) if match else None


# --------------------------------------------------------------------------
# deterministic patient facts — from `input` only, never from `output`
# --------------------------------------------------------------------------

_AGE = re.compile(
    r"\b(\d{1,3})[-\s]?(year|yr|y/?o|month|week|day)[-\s]?s?[-\s]?old\b", re.I
)
_SEX = re.compile(r"\b(male|female|man|woman|boy|girl|gentleman|lady)\b", re.I)
_BP = re.compile(r"\b(?:blood pressure|bp)\D{0,12}(\d{2,3})\s*/\s*(\d{2,3})", re.I)
_HR = re.compile(r"\b(?:heart rate|hr|pulse|p)\D{0,8}(\d{2,3})\b", re.I)
_RR = re.compile(r"\b(?:respiratory rate|rr|resp)\D{0,8}(\d{1,2})\b", re.I)
_SPO2 = re.compile(r"\b(?:spo2|o2 sat\w*|oxygen saturation|sat\w*)\D{0,12}(\d{2,3})\s*%?", re.I)
_TEMP = re.compile(r"\b(?:temp\w*|fever of)\D{0,10}(\d{2,3}(?:\.\d)?)\s*°?\s*([CF])?", re.I)

_FEMALE = {"female", "woman", "girl", "lady"}


def extract_age_years(text: str) -> float | None:
    match = _AGE.search(text)
    if not match:
        return None
    value, unit = float(match.group(1)), match.group(2).lower()
    if unit.startswith("month"):
        return round(value / 12, 3)
    if unit.startswith("week"):
        return round(value / 52, 3)
    if unit.startswith("day"):
        return round(value / 365, 3)
    return value


def age_band_for(age_years: float | None) -> str | None:
    """Bands mirror the ESI danger-zone vital-sign table, not generic buckets."""
    if age_years is None:
        return None
    if age_years < 0.25:
        return "infant_lt_3mo"
    if age_years < 3:
        return "toddler_3mo_3y"
    if age_years < 8:
        return "child_3_8y"
    if age_years < 18:
        return "adolescent_8_18y"
    if age_years < 65:
        return "adult"
    return "elderly_65plus"


def extract_sex(text: str) -> str | None:
    match = _SEX.search(text)
    if not match:
        return None
    return "female" if match.group(1).lower() in _FEMALE else "male"


def extract_vitals(text: str) -> dict[str, Any]:
    """Absent stays absent. A missing vital is never inferred or defaulted."""
    vitals: dict[str, Any] = {}
    if (m := _BP.search(text)) is not None:
        vitals["sbp"], vitals["dbp"] = int(m.group(1)), int(m.group(2))
    if (m := _HR.search(text)) is not None:
        vitals["hr"] = int(m.group(1))
    if (m := _RR.search(text)) is not None:
        vitals["rr"] = int(m.group(1))
    if (m := _SPO2.search(text)) is not None:
        value = int(m.group(1))
        if 50 <= value <= 100:
            vitals["spo2"] = value
    if (m := _TEMP.search(text)) is not None:
        value, unit = float(m.group(1)), (m.group(2) or "").upper()
        if unit == "F" or (not unit and value > 45):
            value = round((value - 32) * 5 / 9, 1)
        if 30 <= value <= 45:
            vitals["temp_c"] = value
    return vitals


# --------------------------------------------------------------------------
# canonical case assembly
# --------------------------------------------------------------------------


@dataclass
class TaskAssessment:
    decision_point: str
    source_record_id: str
    source_line: int
    answer: Any | None
    parse_method: str
    analysis_text: str


@dataclass
class CanonicalCase:
    case_id: str
    presentation_text: str
    presentation_sha256: str
    age_years: float | None
    age_band: str | None
    sex: str | None
    vitals: dict[str, Any]
    assessments: list[TaskAssessment] = field(default_factory=list)
    source_record_ids: list[str] = field(default_factory=list)

    @property
    def decision_points(self) -> set[str]:
        return {a.decision_point for a in self.assessments}


def iter_raw_records(path: Path) -> Iterator[tuple[int, dict[str, Any]]]:
    with path.open(encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            line = line.strip()
            if not line:
                continue
            try:
                record = json.loads(line)
            except json.JSONDecodeError:
                continue
            fields = ("instruction", "input", "output")
            if not all(isinstance(record.get(k), str) and record[k].strip() for k in fields):
                continue
            yield line_number, record


def build_canonical_cases(path: Path) -> tuple[dict[str, CanonicalCase], dict[str, int]]:
    cases: dict[str, CanonicalCase] = {}
    stats = {"raw_rows": 0, "malformed": 0, "dp_unknown": 0}
    seen_lines = 0

    for line_number, record in iter_raw_records(path):
        seen_lines += 1
        stats["raw_rows"] += 1
        presentation = record["input"].strip()
        case_id = case_id_for(presentation)

        if case_id not in cases:
            cases[case_id] = CanonicalCase(
                case_id=case_id,
                presentation_text=presentation,
                presentation_sha256=sha256(normalize(presentation)),
                age_years=extract_age_years(presentation),
                age_band=age_band_for(extract_age_years(presentation)),
                sex=extract_sex(presentation),
                vitals=extract_vitals(presentation),
            )

        case = cases[case_id]
        dp = decision_point_of(record["instruction"])
        if dp == "UNKNOWN":
            stats["dp_unknown"] += 1

        output = record["output"].strip()
        if dp == "A":
            answer, method = parse_dp_a(output), "regex"
        elif dp == "B":
            answer, method = parse_dp_b(output), "regex"
        elif dp == "C":
            answer, method = parse_dp_c(output), "regex"
        else:
            answer, method = None, "none"

        source_record_id = f"mietic_{line_number:05d}"
        case.assessments.append(
            TaskAssessment(
                decision_point=dp,
                source_record_id=source_record_id,
                source_line=line_number,
                answer=answer,
                parse_method=method if answer is not None else "unparsed",
                analysis_text=output,
            )
        )
        case.source_record_ids.append(source_record_id)

    total_lines = sum(1 for _ in path.open(encoding="utf-8") if _.strip())
    stats["malformed"] = total_lines - seen_lines
    return cases, stats


# --------------------------------------------------------------------------
# ESI derivation — the real algorithm, applied to the parsed answers
# --------------------------------------------------------------------------


def level_for_resource_count(count: int) -> int:
    """ESI Decision Point C: no resources -> 5, one -> 4, two or more -> 3."""
    return 5 if count == 0 else 4 if count == 1 else 3


def derive_esi(case: CanonicalCase) -> tuple[list[int], str, int | None]:
    """Narrow the possible ESI levels using only the answers actually present.

    Each decision point eliminates levels rather than naming one, and a level is
    asserted only when a single possibility survives. This matters because the
    corpus asks A, B and C as *separate* tasks and most cases carry only some of
    them: a resource count says a patient would be level 3 *if they reach
    Decision Point C*, which is true only once A and B are both known to be
    negative. Reading that count as a label on its own silently promotes an
    unscreened patient — one who was never assessed for a life-saving
    intervention — to a mid-acuity level.

    So an unanswered decision point widens the candidate set instead of being
    treated as a negative answer, and `validated_esi_level` stays NULL unless
    the answers determine exactly one level.
    """
    answers: dict[str, list[Any]] = {}
    for assessment in case.assessments:
        if assessment.answer is None:
            continue
        # Conflicting answers for the same decision point are kept, not merged.
        answers.setdefault(assessment.decision_point, []).append(assessment.answer)

    def single(point: str) -> Any | None:
        values = answers.get(point)
        if not values or len({str(v) for v in values}) > 1:
            return None
        return values[0]

    # Two answers to one decision point that disagree: the case is contradictory
    # and no level may be asserted from it.
    conflicting = any(len({str(v) for v in values}) > 1 for values in answers.values())

    a, b, c = single("A"), single("B"), single("C")
    possible = {1, 2, 3, 4, 5}

    if a is True:
        # A life-saving intervention settles the level outright.
        possible &= {1}
    elif a is False:
        possible -= {1}

    if b is True:
        possible &= {1, 2}
    elif b is False:
        possible -= {2}

    if c is not None and isinstance(c, int):
        # The count only speaks to the 3/4/5 branch; it can neither create nor
        # exclude the high-acuity levels that come before it.
        possible &= {1, 2, level_for_resource_count(c)}

    candidates = sorted(possible)
    if conflicting:
        return candidates, "CONFLICTING", None
    if len(candidates) == 1:
        return candidates, "CONSISTENT", candidates[0]
    return candidates, "UNKNOWN", None
