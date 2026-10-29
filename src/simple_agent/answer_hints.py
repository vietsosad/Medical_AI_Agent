"""Patient-UI hints derived from the corpus: how the pending question can be
answered, and what the session has recorded so far.

Display-only. Nothing here feeds ``decision.py`` or Phase A. A quick-reply tap
sends exactly the text the patient could have typed ("Có", "Không",
"Không rõ", "7"), so the agent interprets it like any typed reply and the
matching engine never sees these hints.
"""

from __future__ import annotations

from typing import Any

from .corpus import Corpus
from .session import Session

_YES_NO_VALUE_SETS = (
    frozenset({"YES", "NO", "UNKNOWN"}),
    frozenset({"PRESENT", "ABSENT", "UNKNOWN"}),
)
_QUESTION_ACTIONS = frozenset({"ASK_NEXT", "ASK_CLARIFICATION"})


def question_input(corpus: Corpus, action: str, question_target: str | None) -> dict[str, Any] | None:
    """The answer shape the UI may offer shortcuts for, or ``None`` for free text.

    Only shapes whose every answer has an unambiguous Vietnamese wording get
    a hint. Other enums (``LEFT``/``RIGHT``, onset bands, ...) stay free text:
    their codes have no reviewed patient-facing labels yet.
    """
    if action == "ASK_CONFIRMATION":
        return {"kind": "CONFIRM"}
    if action not in _QUESTION_ACTIONS or question_target is None:
        return None
    fact = corpus.fact_by_id.get(question_target)
    if fact is None:
        return None
    schema = fact.get("value_schema") or {}
    if schema.get("type") == "enum":
        allowed = frozenset(str(value).upper() for value in schema.get("allowed_values") or [])
        return {"kind": "YES_NO"} if allowed in _YES_NO_VALUE_SETS else None
    if schema.get("type") == "integer" and schema.get("minimum") == 0 and schema.get("maximum") == 10:
        return {"kind": "SCALE_0_10"}
    return None


def recorded_facts(corpus: Corpus, session: Session) -> list[dict[str, Any]]:
    """Every fact recorded for the current subject, in the order it was given.

    Clinician-only targets (the resource estimate) are the agent's own
    working numbers, not something the patient said, so they stay out.
    """
    recorded: list[dict[str, Any]] = []
    for fact_id, value in session.facts.items():
        fact = corpus.fact_by_id.get(fact_id)
        if fact is None or fact.get("reporting_style") == "CLINICIAN_ONLY":
            continue
        recorded.append({"fact_target_id": fact_id, "name": fact["name"], "value": value})
    return recorded


def recorded_symptoms(corpus: Corpus, session: Session) -> list[dict[str, str]]:
    """Concepts the patient asserted (never the negated ones), first mention first.

    The label is the concept's first Vietnamese alias -- the corpus's own
    patient-register wording -- falling back to its English canonical name.
    """
    symptoms: list[dict[str, str]] = []
    seen: set[str] = set()
    for concept_id in session.concept_order:
        if concept_id in seen or concept_id not in session.concepts:
            continue
        seen.add(concept_id)
        concept = corpus.concept_by_id.get(concept_id)
        if concept is None:
            continue
        aliases = concept.get("aliases") or []
        label = str(aliases[0]) if aliases else str(concept.get("canonical_name") or concept_id)
        symptoms.append({"concept_id": concept_id, "label": label[:1].upper() + label[1:]})
    return symptoms
