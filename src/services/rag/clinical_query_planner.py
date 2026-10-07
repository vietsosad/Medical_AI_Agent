"""Canonical patient state -> grounded English clinical retrieval queries.

Both corpora are English; patients speak Vietnamese. The previous retrieval
path embedded the Vietnamese summary, a handful of controlled English terms and
a bag of sparse slugs as *one* string, then hoped one dense vector would find
the right protocol rule and the right similar case at once. It usually found
neither: an averaged vector over "everything about this patient" is close to a
great many cases and specific to none.

This module produces several short, specific English queries instead:

* an overall presentation query, for cases that look like this patient;
* a primary-symptom query, for the leading complaint on its own;
* an associated-symptom query, for the combination;
* an optional decision-point query, when a decision-relevant fact is known.

Grounding is enforced structurally rather than by asking a model to behave.
The vocabulary a query may use is *derived from canonical fact keys*, which are
English concept slugs already (``symptom.headache``), so a term can only appear
in a query if an observation put it in the patient's state. A language model
may then be used to compose a more fluent sentence out of that closed
vocabulary, and its output is rejected if it introduces anything the vocabulary
did not contain -- a symptom, a number, a vital sign, or a diagnosis.

Nothing here decides an ESI level, and nothing here reads a corpus.
"""

from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass, field
from typing import Any

from src.agents.problem_state import ProblemState

logger = logging.getLogger(__name__)

# Canonical symptom slug -> the English a clinician would write. Most slugs are
# already English; this table exists for the ones whose natural clinical
# wording differs, and it is the *only* vocabulary a query may draw on.
CONCEPT_EN: dict[str, str] = {
    "chest_pain": "chest pain",
    "abdominal_pain": "abdominal pain",
    "back_pain": "back pain",
    "sore_throat": "sore throat",
    "headache": "headache",
    "dyspnea": "shortness of breath",
    "nausea": "nausea",
    "vomiting": "vomiting",
    "fever": "fever",
    "cough": "cough",
    "dizziness": "dizziness",
    "lightheadedness": "lightheadedness",
    "diarrhea": "diarrhea",
    "rash": "rash",
    "bleeding": "bleeding",
    "syncope": "syncope",
    "seizure": "seizure",
    "diaphoresis": "diaphoresis",
    "palpitations": "palpitations",
}

# Vietnamese course wording -> English. Closed set: the extractor only ever
# records one of these five values.
COURSE_EN: dict[str, str] = {
    "đột ngột": "sudden onset",
    "tăng dần": "gradually worsening",
    "giảm dần": "gradually improving",
    "từng cơn": "intermittent",
    "liên tục": "constant",
}

CHARACTER_EN: dict[str, str] = {
    "âm ỉ": "dull",
    "nhói": "sharp",
    "bóp nghẹt": "crushing",
    "giật theo nhịp": "throbbing",
    "bỏng rát": "burning",
    "quặn": "cramping",
    "căng tức": "pressure-like",
}

# Onset wording -> English. Anything not matched here is dropped rather than
# guessed: a mistranslated duration changes what the query is asking for.
_ONSET_PHRASES: tuple[tuple[str, str], ...] = (
    ("sang nay", "since this morning"),
    ("trua nay", "since midday"),
    ("chieu nay", "since this afternoon"),
    ("toi nay", "since this evening"),
    ("toi qua", "since last night"),
    ("dem qua", "since last night"),
    ("hom nay", "today"),
    ("hom qua", "since yesterday"),
    ("tuan truoc", "for one week"),
    ("vai ngay", "for several days"),
    ("vai gio", "for several hours"),
    ("vai phut", "for several minutes"),
)

_ONSET_UNITS: dict[str, str] = {
    "phut": "minutes",
    "gio": "hours",
    "tieng": "hours",
    "ngay": "days",
    "tuan": "weeks",
    "thang": "months",
}

_VITAL_EN: dict[str, str] = {
    "temperature_c": "temperature {value}C",
    "heart_rate": "heart rate {value}",
    "respiratory_rate": "respiratory rate {value}",
    "spo2": "SpO2 {value}%",
    "systolic_bp": "systolic blood pressure {value}",
    "blood_pressure": "blood pressure {value}",
}

# Terms a retrieval query must never contain, whoever produced them. These name
# a disease rather than a finding, and a query that asks for a diagnosis
# retrieves the protocol for a condition nobody has established.
_DIAGNOSIS_TERMS: tuple[str, ...] = (
    "acute coronary syndrome",
    "myocardial",
    "infarction",
    "stroke",
    "subarachnoid",
    "meningitis",
    "sepsis",
    "appendicitis",
    "embolism",
    "aneurysm",
    "ischemia",
    "hemorrhage",
    "pneumonia",
    "dissection",
    "encephalopathy",
)


def _fold(text: str) -> str:
    import unicodedata

    decomposed = unicodedata.normalize("NFD", str(text).lower())
    stripped = "".join(
        character
        for character in decomposed
        if unicodedata.category(character) != "Mn"
    )
    return " ".join(stripped.replace("đ", "d").split())


def translate_onset(value: Any) -> str:
    """English for a patient-reported onset, or '' when it cannot be read."""
    folded = _fold(value)
    if not folded:
        return ""
    for surface, english in _ONSET_PHRASES:
        if surface in folded:
            return english
    match = re.search(r"(\d+)\s*(phut|gio|tieng|ngay|tuan|thang)", folded)
    if match:
        unit = _ONSET_UNITS[match.group(2)]
        return f"for {match.group(1)} {unit}"
    return ""


def _age_band(demographics: dict[str, Any]) -> str:
    age = demographics.get("age")
    try:
        age = float(age)
    except (TypeError, ValueError):
        return "adult"
    if age < 16:
        return "pediatric"
    if age >= 65:
        return "elderly"
    return "adult"


@dataclass
class ClinicalQuerySet:
    """The grounded English queries one confirmed presentation produces."""

    overall: str = ""
    primary: str = ""
    associated: str = ""
    decision_point: str = ""
    # English concept slugs the queries are allowed to mention. This is the
    # grounding vocabulary and the validation target in one.
    grounded_concepts: tuple[str, ...] = ()
    lexical_terms: tuple[str, ...] = ()
    source: str = "DETERMINISTIC"
    degraded_modes: tuple[str, ...] = ()
    audit: dict[str, Any] = field(default_factory=dict)

    def queries(self) -> list[tuple[str, str]]:
        """Named, non-empty queries, best-scoped first."""
        named = (
            ("primary", self.primary),
            ("associated", self.associated),
            ("overall", self.overall),
            ("decision_point", self.decision_point),
        )
        seen: set[str] = set()
        result: list[tuple[str, str]] = []
        for name, query in named:
            text = query.strip()
            if not text or text.casefold() in seen:
                continue
            seen.add(text.casefold())
            result.append((name, text))
        return result

    def to_dict(self) -> dict[str, Any]:
        return {
            "source": self.source,
            "overall": self.overall,
            "primary": self.primary,
            "associated": self.associated,
            "decision_point": self.decision_point,
            "grounded_concepts": list(self.grounded_concepts),
            "lexical_terms": list(self.lexical_terms),
            "degraded_modes": list(self.degraded_modes),
            **self.audit,
        }


def _grounded_facts(problem_state: ProblemState) -> dict[str, Any]:
    """Everything a query may mention, extracted from canonical state only."""
    active = problem_state.active_problems
    primary = problem_state.primary
    concepts = [
        problem.concept for problem in active if problem.concept in CONCEPT_EN
    ]
    denied = [
        concept
        for concept in problem_state.denied_concepts
        if concept in CONCEPT_EN
    ]

    facts: dict[str, Any] = {
        "age_band": _age_band(problem_state.demographics),
        "primary_concept": primary.concept if primary else None,
        "concepts": concepts,
        "denied_concepts": denied,
        "vitals": {
            key: value
            for key, value in problem_state.vitals.items()
            if key in _VITAL_EN and value is not None
        },
    }
    if primary is not None:
        known = primary.known_facts
        facts["onset"] = translate_onset(known.get("onset_time"))
        facts["course"] = COURSE_EN.get(str(known.get("course") or ""), "")
        facts["character"] = CHARACTER_EN.get(str(known.get("character") or ""), "")
        severity = known.get("severity_score")
        facts["severity"] = severity if isinstance(severity, int | float) else None
        radiation = known.get("radiation")
        facts["radiates"] = bool(radiation) and _fold(radiation) != "khong lan"
        facts["worst_ever"] = known.get("worst_ever") is True
    return facts


def _severity_phrase(severity: Any) -> str:
    if not isinstance(severity, int | float):
        return ""
    if severity >= 7:
        return "severe"
    if severity >= 4:
        return "moderate"
    return "mild"


def build_deterministic_queries(problem_state: ProblemState) -> ClinicalQuerySet:
    """Compose the English queries from grounded facts, with no model involved.

    This is both the fallback and the reference: whatever a model later
    produces is checked against the same vocabulary this function draws on.
    """
    facts = _grounded_facts(problem_state)
    primary_concept = facts.get("primary_concept")
    if not primary_concept or primary_concept not in CONCEPT_EN:
        return ClinicalQuerySet(
            degraded_modes=("NO_GROUNDED_PRIMARY_CONCEPT",),
            grounded_concepts=tuple(facts.get("concepts") or ()),
        )

    primary_en = CONCEPT_EN[primary_concept]
    others = [
        CONCEPT_EN[concept]
        for concept in facts["concepts"]
        if concept != primary_concept
    ]
    severity_word = _severity_phrase(facts.get("severity"))
    course = facts.get("course") or ""
    character = facts.get("character") or ""
    onset = facts.get("onset") or ""

    primary_parts = [
        part
        for part in (severity_word, character, course.replace(" onset", ""), primary_en)
        if part
    ]
    primary_query = " ".join(dict.fromkeys(primary_parts))
    if onset:
        primary_query = f"{primary_query} {onset}"

    associated_query = ""
    if others:
        associated_query = f"{primary_en} with {_join_en(others)}"

    overall_bits = [f"{facts['age_band']} patient with"]
    overall_bits.append(primary_query)
    if others:
        overall_bits.append(f"associated {_join_en(others)}")
    if facts.get("radiates"):
        overall_bits.append("with radiation")
    if facts.get("worst_ever"):
        overall_bits.append("described as the worst ever experienced")
    if facts.get("denied_concepts"):
        denied_en = [CONCEPT_EN[item] for item in facts["denied_concepts"]]
        overall_bits.append(f"denies {_join_en(denied_en)}")
    vitals = [
        _VITAL_EN[key].format(value=value)
        for key, value in facts["vitals"].items()
    ]
    if vitals:
        overall_bits.append(f"vital signs {', '.join(vitals)}")
    overall = " ".join(part for part in overall_bits if part).strip()

    decision_query = ""
    if severity_word == "severe" or facts.get("worst_ever"):
        decision_query = (
            f"emergency severity index high risk criteria severe {primary_en}"
        )
    elif vitals:
        decision_query = (
            f"emergency severity index danger zone vital signs {primary_en}"
        )

    lexical = _lexical_terms(facts, primary_concept)
    return ClinicalQuerySet(
        overall=overall,
        primary=primary_query.strip(),
        associated=associated_query,
        decision_point=decision_query,
        grounded_concepts=tuple(facts["concepts"]),
        lexical_terms=lexical,
        source="DETERMINISTIC",
        audit={"grounded_facts": facts},
    )


def _join_en(items: list[str]) -> str:
    unique = list(dict.fromkeys(items))
    if len(unique) <= 1:
        return "".join(unique)
    return f"{', '.join(unique[:-1])} and {unique[-1]}"


def _lexical_terms(facts: dict[str, Any], primary_concept: str) -> tuple[str, ...]:
    """Words for the keyword channel. Concepts only, never numbers or negations.

    A denied symptom is deliberately excluded: lexical search has no notion of
    negation, so "denies chest pain" as keywords retrieves chest-pain cases.
    """
    terms: list[str] = []
    for concept in facts["concepts"]:
        terms.extend(CONCEPT_EN[concept].split())
    severity = _severity_phrase(facts.get("severity"))
    if severity:
        terms.append(severity)
    if facts.get("course"):
        terms.extend(str(facts["course"]).split())
    return tuple(dict.fromkeys(term for term in terms if len(term) > 2))


# ---------------------------------------------------------------------------
# Optional model-composed phrasing, structurally constrained
# ---------------------------------------------------------------------------

_PLANNER_PROMPT = """You rewrite structured clinical facts as short English \
retrieval queries for an emergency-triage knowledge base.

RULES, all mandatory:
- Use ONLY the facts given. Never add a symptom, sign, vital sign, number, \
duration or diagnosis that is not in them.
- Never name a disease or a suspected diagnosis. Describe findings only.
- Never state or imply an acuity or ESI level.
- Keep each query under 30 words, clinical register, no patient pronouns.

Return JSON with exactly these keys: overall, primary, associated.
"""


def _allowed_vocabulary(facts: dict[str, Any]) -> set[str]:
    """Every word a generated query may use, lower-cased."""
    allowed: set[str] = {
        "patient",
        "with",
        "and",
        "associated",
        "denies",
        "vital",
        "signs",
        "onset",
        "since",
        "for",
        "the",
        "a",
        "of",
        "no",
        "worst",
        "ever",
        "experienced",
        "described",
        "as",
        "radiation",
        "presenting",
        "presents",
        "reports",
        "reported",
        "emergency",
        "severity",
        "index",
        "criteria",
        "risk",
        "high",
        "danger",
        "zone",
    }
    allowed.update(str(facts.get("age_band") or "").split())
    for concept in [*facts.get("concepts", []), *facts.get("denied_concepts", [])]:
        allowed.update(CONCEPT_EN[concept].split())
    for key in ("onset", "course", "character"):
        allowed.update(str(facts.get(key) or "").lower().split())
    severity = _severity_phrase(facts.get("severity"))
    if severity:
        allowed.add(severity)
    for key, value in (facts.get("vitals") or {}).items():
        allowed.update(_VITAL_EN[key].format(value=value).lower().split())
    return {word.strip(",.;:%") for word in allowed if word}


def validate_grounding(query: str, facts: dict[str, Any]) -> list[str]:
    """Every reason this generated query is not grounded in canonical state.

    Deterministic and total: the query is tokenised and each token must appear
    in the vocabulary the patient's own facts produced. A model cannot talk its
    way past this, because the check never reads the model's justification.
    """
    problems: list[str] = []
    lowered = query.lower()
    for term in _DIAGNOSIS_TERMS:
        if term in lowered:
            problems.append(f"diagnosis_term:{term}")
    allowed = _allowed_vocabulary(facts)
    for token in re.findall(r"[a-z0-9]+(?:\.[0-9]+)?", lowered):
        if token in allowed:
            continue
        if token.isdigit() or re.fullmatch(r"[0-9.]+", token):
            problems.append(f"ungrounded_number:{token}")
            continue
        problems.append(f"ungrounded_term:{token}")
    return sorted(set(problems))


async def build_llm_queries(
    problem_state: ProblemState,
    baseline: ClinicalQuerySet,
) -> ClinicalQuerySet:
    """Ask a small model to phrase the same grounded facts more naturally.

    Returns the deterministic baseline unchanged on any failure, any timeout,
    or any grounding violation. The model can therefore improve the wording and
    can never change what the query asks for.
    """
    facts = baseline.audit.get("grounded_facts") or {}
    if not facts:
        return baseline
    try:
        import asyncio

        from src.config import get_settings
        from src.services.llm_provider import get_resilient_llm

        model = get_resilient_llm("small")
        payload = json.dumps(facts, ensure_ascii=False, sort_keys=True)
        response = await asyncio.wait_for(
            model.ainvoke(
                [
                    {"role": "system", "content": _PLANNER_PROMPT},
                    {"role": "user", "content": payload},
                ]
            ),
            timeout=get_settings().llm_request_timeout_seconds,
        )
    except Exception as exc:  # noqa: BLE001 - optional refinement boundary
        logger.info("Query planner LLM unavailable: %s", type(exc).__name__)
        return _degraded(baseline, "QUERY_PLANNER_LLM_UNAVAILABLE")

    text = getattr(response, "content", "") or ""
    if isinstance(text, list):
        text = " ".join(str(part) for part in text)
    match = re.search(r"\{.*\}", str(text), flags=re.S)
    if not match:
        return _degraded(baseline, "QUERY_PLANNER_UNPARSEABLE")
    try:
        parsed = json.loads(match.group(0))
    except json.JSONDecodeError:
        return _degraded(baseline, "QUERY_PLANNER_UNPARSEABLE")

    candidate = {
        key: str(parsed.get(key) or "").strip()
        for key in ("overall", "primary", "associated")
    }
    violations: list[str] = []
    for key, value in candidate.items():
        if value:
            violations.extend(f"{key}:{item}" for item in validate_grounding(value, facts))
    if violations:
        logger.info("Query planner output rejected: %s", violations[:5])
        return _degraded(
            baseline,
            "QUERY_PLANNER_UNGROUNDED",
            audit={"grounding_violations": violations[:20]},
        )

    return ClinicalQuerySet(
        overall=candidate["overall"] or baseline.overall,
        primary=candidate["primary"] or baseline.primary,
        associated=candidate["associated"] or baseline.associated,
        decision_point=baseline.decision_point,
        grounded_concepts=baseline.grounded_concepts,
        lexical_terms=baseline.lexical_terms,
        source="LLM_GROUNDED",
        degraded_modes=baseline.degraded_modes,
        audit={**baseline.audit, "llm_accepted": True},
    )


def _degraded(
    baseline: ClinicalQuerySet,
    mode: str,
    *,
    audit: dict[str, Any] | None = None,
) -> ClinicalQuerySet:
    return ClinicalQuerySet(
        overall=baseline.overall,
        primary=baseline.primary,
        associated=baseline.associated,
        decision_point=baseline.decision_point,
        grounded_concepts=baseline.grounded_concepts,
        lexical_terms=baseline.lexical_terms,
        source=baseline.source,
        degraded_modes=(*baseline.degraded_modes, mode),
        audit={**baseline.audit, **(audit or {})},
    )


async def plan_clinical_queries(
    problem_state: ProblemState,
    *,
    use_llm: bool | None = None,
) -> ClinicalQuerySet:
    """The public entry point: grounded English queries for one presentation."""
    baseline = build_deterministic_queries(problem_state)
    if not baseline.primary:
        return baseline
    if use_llm is None:
        try:
            from src.config import get_settings

            use_llm = bool(get_settings().retrieval_english_normalization_enabled)
        except Exception:  # noqa: BLE001
            use_llm = False
    if not use_llm:
        return baseline
    return await build_llm_queries(problem_state, baseline)
