"""(De)serialize a ``Session`` to/from plain JSON-safe dicts.

``Session`` (see ``session.py``) holds ``set`` fields (not JSON-serializable)
both at its top level and inside every ``parked_subjects`` snapshot. This
module is the only place that conversion happens, so a caller persisting a
session (e.g. a Postgres row) never has to know ``Session``'s internal shape.

No FastAPI/SQLModel/LLM imports here -- this is a pure data-shape adapter,
reusable by any storage backend.
"""

from __future__ import annotations

from typing import Any

from .session import Session

# Reset at the start of every process_turn() call (see Session.start_turn) --
# pure per-turn reporting, never meaningful to restore into a new turn.
_TRANSIENT_FIELDS = (
    "turn_accepted_facts",
    "turn_observations",
    "turn_asserted_concepts",
    "turn_negated_concepts",
    "turn_tool_log",
    "turn_retrieved_atoms",
)

# How many of the most recent tool_log entries to keep when persisting.
# tool_log grows without bound for the lifetime of an in-memory session; a
# persisted row keeping only the tail avoids an ever-growing JSON column
# while still being useful for local debugging.
TOOL_LOG_TAIL_LENGTH = 20


def _snapshot_to_dict(snapshot: dict[str, Any]) -> dict[str, Any]:
    return {
        **snapshot,
        "concepts": sorted(snapshot["concepts"]),
        "unknown_facts": sorted(snapshot["unknown_facts"]),
        "needs_precision": sorted(snapshot["needs_precision"]),
    }


def _dict_to_snapshot(data: dict[str, Any]) -> dict[str, Any]:
    return {
        **data,
        "concepts": set(data["concepts"]),
        "unknown_facts": set(data["unknown_facts"]),
        "needs_precision": set(data["needs_precision"]),
    }


def serialize_session(session: Session) -> dict[str, Any]:
    """Convert ``session`` into a JSON-safe dict of plain lists/dicts/scalars."""
    return {
        "subject_type": session.subject_type,
        "subject_label": session.subject_label,
        "parked_subjects": {key: _snapshot_to_dict(value) for key, value in session.parked_subjects.items()},
        "concepts": sorted(session.concepts),
        "concept_order": list(session.concept_order),
        "facts": dict(session.facts),
        "qualitative_observations": dict(session.qualitative_observations),
        "unknown_facts": sorted(session.unknown_facts),
        "needs_precision": sorted(session.needs_precision),
        "seen_atom_ids": list(session.seen_atom_ids),
        "atom_relevance_score": dict(session.atom_relevance_score),
        "retrieval_query": session.retrieval_query,
        "last_question": session.last_question,
        "stale_question_streak": session.stale_question_streak,
        "confirmation_offered": session.confirmation_offered,
        "resource_count_estimated": session.resource_count_estimated,
        "history": [[speaker, text] for speaker, text in session.history],
        "tool_log_tail": session.tool_log[-TOOL_LOG_TAIL_LENGTH:],
        "card_gender": session.card_gender,
        "card_relationship": session.card_relationship,
    }


def deserialize_session(data: dict[str, Any]) -> Session:
    """Reconstruct a ``Session`` from a dict produced by ``serialize_session``.

    ``tool_log`` is restored from the persisted tail only -- history before
    the cutoff is not recoverable, which is acceptable: it is a debug trail,
    never read by decision.py/tools.py logic.
    """
    session = Session(
        subject_type=data["subject_type"],
        subject_label=data["subject_label"],
        parked_subjects={key: _dict_to_snapshot(value) for key, value in data["parked_subjects"].items()},
        concepts=set(data["concepts"]),
        concept_order=list(data["concept_order"]),
        facts=dict(data["facts"]),
        qualitative_observations=dict(data["qualitative_observations"]),
        unknown_facts=set(data["unknown_facts"]),
        needs_precision=set(data["needs_precision"]),
        seen_atom_ids=list(data["seen_atom_ids"]),
        # .get(): rows persisted before this field existed (already-live pilot
        # sessions) won't have it -- treat as "no confidence data yet" rather
        # than a hard KeyError on every pre-existing session.
        atom_relevance_score=dict(data.get("atom_relevance_score") or {}),
        retrieval_query=data.get("retrieval_query"),
        last_question=data["last_question"],
        stale_question_streak=data["stale_question_streak"],
        confirmation_offered=data["confirmation_offered"],
        resource_count_estimated=data["resource_count_estimated"],
        history=[(speaker, text) for speaker, text in data["history"]],
        card_gender=data.get("card_gender"),
        card_relationship=data.get("card_relationship"),
    )
    session.tool_log = list(data.get("tool_log_tail") or [])
    for field_name in _TRANSIENT_FIELDS:
        setattr(session, field_name, [])
    return session
