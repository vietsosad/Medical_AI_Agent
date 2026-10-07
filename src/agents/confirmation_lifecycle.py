"""When the intake review may be shown, and when a confirmation stops holding.

Confirmation used to be re-derived from the request payload on every turn, so
any message after "confirm" silently un-confirmed the case and the review came
straight back. This module gives that decision one owner and one rule.

Two questions, kept separate on purpose:

``has_the_patient_confirmed?``
    A durable property of the conversation. It is raised by the patient and
    lowered only by this module, never by the transport.

``is_that_confirmation_still_about_this_case?``
    A confirmation is a statement about the facts as they stood. Adding a fact
    afterwards does not falsify it -- the patient confirmed a summary and then
    told us more. *Changing* a fact they confirmed does, and so does raising a
    new problem, and so does a contradiction.
"""

from __future__ import annotations

from typing import Any

from src.agents.clinical_state_view import ClinicalStateView

# Statuses that count as an answer the patient stands behind.
_ANSWERED = frozenset({"KNOWN", "NEGATED"})

# Prefixes whose change is a change to the clinical picture. Workflow and
# control keys are deliberately excluded: an EHR review answer is not a
# correction to the symptoms someone confirmed.
_CLINICAL_PREFIXES = ("symptom.", "complaint.", "associated.", "vital.")
_CLINICAL_SCALARS = frozenset(
    {
        "onset_time",
        "severity_score",
        "radiation",
        "course",
        "character",
        "location",
        "worst_ever",
        "frequency",
        "age",
        "sex",
    }
)

StaleReason = str  # NEW_PROBLEM | CONTRADICTION | FACT_SUPERSEDED


def _is_clinical_key(key: str) -> bool:
    return (
        key.startswith(_CLINICAL_PREFIXES)
        or key in _CLINICAL_SCALARS
        or _is_problem_scoped_clinical_key(key)
    )


def _is_problem_scoped_clinical_key(key: str) -> bool:
    """Whether ``<problem>.<attribute>`` is a symptom-specific clinical fact."""
    if "." not in key:
        return False
    problem, attribute = key.split(".", 1)
    return bool(problem) and attribute in _CLINICAL_SCALARS


def fact_snapshot(view: ClinicalStateView) -> dict[str, list[Any]]:
    """The answered clinical facts as they stand, in a form safe to persist."""
    snapshot: dict[str, list[Any]] = {}
    for key in sorted(view.canonical.facts):
        if not _is_clinical_key(key):
            continue
        reading = view.read(key)
        if reading.status not in _ANSWERED:
            continue
        snapshot[key] = [str(reading.status), _plain(reading.value)]
    return snapshot


def _plain(value: Any) -> Any:
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    return str(value)


def superseded_facts(
    confirmed: dict[str, Any] | None,
    current: dict[str, list[Any]],
) -> list[str]:
    """Keys the patient confirmed and has since answered differently."""
    if not isinstance(confirmed, dict) or not confirmed:
        return []
    changed: list[str] = []
    for key, previous in confirmed.items():
        if key not in current:
            continue
        if list(previous) != list(current[key]):
            changed.append(key)
    return sorted(changed)


def evaluate_confirmation(
    state: dict[str, Any],
    view: ClinicalStateView,
    *,
    newly_mentioned: list[str],
    unresolved_contradictions: list[dict[str, Any]],
) -> dict[str, Any]:
    """Decide whether an existing confirmation still stands, and why not.

    Returns the fields the caller should apply. A stale confirmation is lowered
    together with the snapshot that justified it, so the next review is built
    from what the patient actually says now.
    """
    confirmed = bool(state.get("patient_confirmed_intake"))
    current = fact_snapshot(view)
    if not confirmed:
        return {
            "patient_confirmed_intake": False,
            "confirmation_stale_reason": None,
            "current_fact_snapshot": current,
        }

    reasons: list[StaleReason] = []
    if unresolved_contradictions:
        # A conflict the patient has not settled invalidates any summary they
        # confirmed, whether or not we hold the snapshot it was built from.
        reasons.append("CONTRADICTION")

    snapshot = state.get("confirmed_fact_snapshot")
    has_snapshot = isinstance(snapshot, dict) and bool(snapshot)
    changed: list[str] = []
    if has_snapshot:
        # Staleness is measured against what was actually confirmed. Without
        # that record there is no evidence anything changed, and asserting
        # otherwise would invalidate a confirmation that arrives with the very
        # first turn -- a recovered session, or a client that confirms and
        # describes in one request. Both are legitimate and neither is the
        # patient raising something new *after* confirming.
        if newly_mentioned:
            reasons.append("NEW_PROBLEM")
        changed = superseded_facts(snapshot, current)
        if changed:
            reasons.append("FACT_SUPERSEDED")

    if not reasons:
        # Facts may have been *added* since -- the reasoner asks for one more
        # detail and the patient answers it. That strengthens the record the
        # patient confirmed; it does not contradict it, and sending them back
        # to the review would make answering a question look like a mistake.
        return {
            "patient_confirmed_intake": True,
            "confirmation_stale_reason": None,
            "current_fact_snapshot": current,
        }

    return {
        "patient_confirmed_intake": False,
        "confirmation_stale_reason": reasons[0],
        "confirmation_stale_details": {
            "reasons": reasons,
            "superseded_keys": changed,
            "new_problems": list(newly_mentioned),
        },
        "confirmed_fact_snapshot": {},
        "current_fact_snapshot": current,
    }


def review_already_shown_for(state: dict[str, Any]) -> bool:
    """Whether the current facts have already been put to the patient.

    §16: one review per canonical-state version. A refetch, a reconnect or a
    duplicate submit that changes nothing must not produce a second review.
    """
    shown = state.get("intake_review_shown_snapshot")
    if not isinstance(shown, dict):
        return False
    return shown == (state.get("current_fact_snapshot") or {})
