"""Conversation memory: retrieval support, never a second clinical truth.

Canonical patient state answers *what is known about the patient*. Memory
answers a narrower question: *what was said earlier that helps interpret what
the patient just said*. "Cơn đau đầu tôi nói lúc nãy" needs the earlier turn to
resolve; it does not need a second opinion about whether the headache exists.

Consequences that shape the whole design:

* a retrieved memory is **evidence about the conversation**, not a clinical
  fact. Nothing here writes to canonical state; callers must route anything
  clinical through the normal extraction and validation path;
* when memory and canonical state disagree, **canonical wins**, unless the
  patient's current message is itself the correction;
* memory carries its temporal context with it, so "tuần trước tôi sốt 39" can
  never be retrieved and read as a current fever;
* every retrieval is scoped to one patient and one session **before** relevance
  is considered. Similarity is never the thing that decides who may see what.

There is no embedding model here on purpose. Conversation recall is lexical and
recency-weighted, which is cheap, deterministic, auditable, and adequate for
resolving references within a single triage session. A semantic index can
replace ``_score`` later without changing the isolation guarantees around it.
"""

from __future__ import annotations

import re
import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any, Literal

from src.agents.nodes.intent_classifier import normalize_vietnamese_text

MemoryType = Literal[
    # The last few turns, kept verbatim.
    "RECENT_TURN",
    # A compacted account of everything older.
    "ROLLING_SUMMARY",
    # Something clinically notable that must never be summarised away.
    "IMPORTANT_EVENT",
    # An older conversational statement, searchable by reference.
    "SEMANTIC",
]

MemorySource = Literal["PATIENT", "AGENT", "SYSTEM", "CLINICIAN"]

# Events too important to lose to summarisation.
IMPORTANT_EVENT_KINDS: frozenset[str] = frozenset(
    {
        "NEW_SYMPTOM",
        "RED_FLAG_CANDIDATE",
        "RED_FLAG_CONFIRMED",
        "RED_FLAG_NOT_CONFIRMED",
        "SAFETY_FALLBACK",
        "CORRECTION",
        "TRIAGE_REASSESSMENT",
        "MEDICATION_DISCLOSED",
        "VITAL_REPORTED",
        "CLINICIAN_INTERVENTION",
    }
)

_STOPWORDS: frozenset[str] = frozenset(
    {
        "toi", "minh", "la", "co", "khong", "va", "thi", "o", "cua", "mot",
        "cai", "do", "ay", "nay", "cho", "voi", "duoc", "ma", "nhu", "ve",
        "roi", "cung", "khi", "lam", "bi", "rat", "nhung", "hay", "da",
    }
)


def _now() -> str:
    return datetime.now(UTC).isoformat()


def _tokens(text: str) -> set[str]:
    folded = normalize_vietnamese_text(text)
    return {
        token
        for token in re.findall(r"[a-z0-9]+", folded)
        if len(token) > 1 and token not in _STOPWORDS
    }


@dataclass
class MemoryItem:
    """One remembered thing, with everything needed to trust and scope it."""

    content: str
    memory_type: MemoryType
    # Isolation keys. Both are required; a record missing either is unusable.
    patient_id: str
    session_id: str
    turn_id: str = ""
    source: MemorySource = "PATIENT"
    confidence: float = 1.0
    temporal_context: str = "UNKNOWN_TIME"
    event_kind: str | None = None
    created_at: str = field(default_factory=_now)
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    # Set when a later statement retracts this one.
    superseded_by: str | None = None
    # How many turns have re-asserted this same event, and when it was last
    # seen. Important events are pinned and never summarised away, so an event
    # that recurs every turn would otherwise grow the pinned set without bound
    # and crowd out everything else in the context budget.
    occurrence_count: int = 1
    last_turn_id: str = ""

    @property
    def is_active(self) -> bool:
        return self.superseded_by is None

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "content": self.content,
            "memory_type": self.memory_type,
            "patient_id": self.patient_id,
            "session_id": self.session_id,
            "turn_id": self.turn_id,
            "source": self.source,
            "confidence": self.confidence,
            "temporal_context": self.temporal_context,
            "event_kind": self.event_kind,
            "created_at": self.created_at,
            "superseded_by": self.superseded_by,
            "occurrence_count": self.occurrence_count,
            "last_turn_id": self.last_turn_id,
        }

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> MemoryItem:
        return cls(
            content=str(payload.get("content") or ""),
            memory_type=payload.get("memory_type") or "SEMANTIC",
            patient_id=str(payload.get("patient_id") or ""),
            session_id=str(payload.get("session_id") or ""),
            turn_id=str(payload.get("turn_id") or ""),
            source=payload.get("source") or "PATIENT",
            confidence=float(payload.get("confidence") or 1.0),
            temporal_context=str(payload.get("temporal_context") or "UNKNOWN_TIME"),
            event_kind=payload.get("event_kind"),
            created_at=str(payload.get("created_at") or _now()),
            id=str(payload.get("id") or uuid.uuid4()),
            superseded_by=payload.get("superseded_by"),
            occurrence_count=int(payload.get("occurrence_count") or 1),
            last_turn_id=str(payload.get("last_turn_id") or ""),
        )


@dataclass(frozen=True)
class MemoryScope:
    """Who is allowed to read. Enforced before relevance, never after."""

    patient_id: str
    session_id: str

    def permits(self, item: MemoryItem) -> bool:
        return (
            bool(self.patient_id)
            and bool(self.session_id)
            and item.patient_id == self.patient_id
            and item.session_id == self.session_id
        )


# Only these are worth remembering. Everything else is either already in
# canonical state or is conversational noise.
_ACKNOWLEDGEMENTS: frozenset[str] = frozenset(
    {"vang", "vang a", "ok", "oke", "da", "da vang", "cam on", "hieu roi", "u", "um"}
)


def should_remember(content: str, *, source: MemorySource = "PATIENT") -> bool:
    """Memory write policy: store what could be needed later, nothing else.

    Bare acknowledgements carry no recoverable meaning, and storing every
    message would make retrieval noisier without making it more useful.
    """
    text = content.strip()
    if len(text) < 3:
        return False
    if source == "PATIENT" and normalize_vietnamese_text(text) in _ACKNOWLEDGEMENTS:
        return False
    return True


class ConversationMemory:
    """In-session conversation memory with hard patient/session isolation.

    Held per session and serialised alongside canonical state. The store keeps
    items for more than one scope only so that isolation can be *tested*
    honestly; every read path filters by scope first.
    """

    RECENT_WINDOW = 6
    SUMMARY_TRIGGER = 12

    def __init__(self) -> None:
        self._items: list[MemoryItem] = []
        self._summary: MemoryItem | None = None

    # -- writing ----------------------------------------------------------

    def remember(
        self,
        content: str,
        *,
        patient_id: str,
        session_id: str,
        turn_id: str = "",
        source: MemorySource = "PATIENT",
        memory_type: MemoryType = "RECENT_TURN",
        temporal_context: str = "UNKNOWN_TIME",
        event_kind: str | None = None,
        confidence: float = 1.0,
    ) -> MemoryItem | None:
        """Store one item, or decline under the write policy."""
        if not patient_id or not session_id:
            # Refuse to store anything that cannot be scoped. An unscoped item
            # is one that could later be read by the wrong person.
            return None
        if event_kind is None and not should_remember(content, source=source):
            return None
        item = MemoryItem(
            content=content.strip(),
            memory_type="IMPORTANT_EVENT" if event_kind else memory_type,
            patient_id=patient_id,
            session_id=session_id,
            turn_id=turn_id,
            source=source,
            confidence=confidence,
            temporal_context=temporal_context,
            event_kind=event_kind,
        )
        self._items.append(item)
        return item

    def record_event(
        self,
        event_kind: str,
        content: str,
        *,
        patient_id: str,
        session_id: str,
        turn_id: str = "",
    ) -> MemoryItem | None:
        """Record something that must survive summarisation, at most once.

        Callers re-derive events from turn state, and turn state carries
        forward: an open red-flag candidate or a pending reassessment key is
        still present on the next turn, and the turn after that. Recording each
        one again would pin an unbounded pile of identical events -- and
        because important events are deliberately exempt from summarisation,
        nothing would ever trim them.

        So a repeat of an event already pinned for this scope updates the
        existing record instead of adding another. The recurrence is not
        discarded: the count and the latest turn are kept, which is the part
        that carries information, while the pinned set stays proportional to
        *what happened* rather than to how many turns have elapsed.
        """
        if event_kind not in IMPORTANT_EVENT_KINDS:
            return None
        normalized = content.strip()
        scope = MemoryScope(patient_id=patient_id, session_id=session_id)
        for existing in self._items:
            if (
                existing.is_active
                and existing.event_kind == event_kind
                and existing.content == normalized
                and scope.permits(existing)
            ):
                existing.occurrence_count += 1
                existing.last_turn_id = turn_id or existing.last_turn_id
                return existing
        item = self.remember(
            content,
            patient_id=patient_id,
            session_id=session_id,
            turn_id=turn_id,
            source="SYSTEM",
            event_kind=event_kind,
        )
        if item is not None:
            item.last_turn_id = turn_id
        return item

    def supersede(self, item_id: str, by_turn_id: str) -> bool:
        """Retire an item the patient has since corrected.

        Obsolete statements must stop surfacing as though still true; the record
        is kept, marked, so the history stays auditable.
        """
        for item in self._items:
            if item.id == item_id and item.is_active:
                item.superseded_by = by_turn_id or "superseded"
                return True
        return False

    # -- reading ----------------------------------------------------------

    def _scoped(self, scope: MemoryScope) -> list[MemoryItem]:
        """The only way items are read. Scope is applied before anything else."""
        return [
            item for item in self._items if item.is_active and scope.permits(item)
        ]

    def recent(self, scope: MemoryScope, limit: int | None = None) -> list[MemoryItem]:
        items = self._scoped(scope)
        return items[-(limit or self.RECENT_WINDOW):]

    def important_events(self, scope: MemoryScope) -> list[MemoryItem]:
        return [
            item
            for item in self._scoped(scope)
            if item.memory_type == "IMPORTANT_EVENT"
        ]

    def rolling_summary(self, scope: MemoryScope) -> MemoryItem | None:
        if self._summary is None or not scope.permits(self._summary):
            return None
        return self._summary

    @staticmethod
    def _score(query_tokens: set[str], item: MemoryItem, rank: int, total: int) -> float:
        """Lexical overlap with a mild recency preference."""
        if not query_tokens:
            return 0.0
        item_tokens = _tokens(item.content)
        if not item_tokens:
            return 0.0
        overlap = len(query_tokens & item_tokens)
        if overlap == 0:
            return 0.0
        precision = overlap / len(query_tokens)
        recency = (rank + 1) / max(total, 1)
        return round(precision * 0.8 + recency * 0.2, 4)

    def search(
        self,
        query: str,
        scope: MemoryScope,
        *,
        limit: int = 3,
        min_score: float = 0.15,
    ) -> list[tuple[MemoryItem, float]]:
        """Find earlier statements relevant to the current message.

        Scope is applied first and unconditionally: a highly similar message
        belonging to another patient is not a near-miss, it is invisible.
        """
        candidates = self._scoped(scope)
        query_tokens = _tokens(query)
        total = len(candidates)
        scored = [
            (item, self._score(query_tokens, item, rank, total))
            for rank, item in enumerate(candidates)
        ]
        relevant = [pair for pair in scored if pair[1] >= min_score]
        relevant.sort(key=lambda pair: pair[1], reverse=True)
        return relevant[:limit]

    # -- summarisation ----------------------------------------------------

    def needs_summary(self, scope: MemoryScope) -> bool:
        return len(self._scoped(scope)) > self.SUMMARY_TRIGGER

    def build_rolling_summary(self, scope: MemoryScope) -> MemoryItem | None:
        """Compact older turns, keeping every important event verbatim.

        Summarisation is deterministic and lossy by design, so anything that
        could matter clinically is excluded from compaction rather than trusted
        to survive it.
        """
        items = self._scoped(scope)
        if len(items) <= self.RECENT_WINDOW:
            return None
        older = items[: -self.RECENT_WINDOW]
        compactable = [
            item
            for item in older
            if item.memory_type != "IMPORTANT_EVENT" and item.source == "PATIENT"
        ]
        if not compactable:
            return None
        joined = " | ".join(item.content[:120] for item in compactable[-20:])
        self._summary = MemoryItem(
            content=f"Người bệnh đã kể trước đó: {joined}",
            memory_type="ROLLING_SUMMARY",
            patient_id=scope.patient_id,
            session_id=scope.session_id,
            source="SYSTEM",
            confidence=0.6,
        )
        return self._summary

    # -- serialization ----------------------------------------------------

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": 1,
            "items": [item.to_dict() for item in self._items],
            "summary": self._summary.to_dict() if self._summary else None,
        }

    @classmethod
    def from_dict(cls, payload: dict[str, Any] | None) -> ConversationMemory:
        memory = cls()
        if not isinstance(payload, dict):
            return memory
        memory._items = [
            MemoryItem.from_dict(item)
            for item in (payload.get("items") or [])
            if isinstance(item, dict)
        ]
        raw_summary = payload.get("summary")
        memory._summary = (
            MemoryItem.from_dict(raw_summary) if isinstance(raw_summary, dict) else None
        )
        return memory
