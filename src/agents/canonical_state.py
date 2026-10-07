"""Canonical Patient State: the source of truth for clinical conversation.

The governing rule:

    Every turn may change state, but no state value may become a clinical fact
    without evidence and provenance.

Three distinctions this model exists to protect, each of which was previously
impossible to express:

1. ``UNKNOWN`` is not ``NEGATED`` and neither is ``False``. A fact the patient
   never mentioned and a fact the patient explicitly denied are different
   clinical situations. An absent key reads as UNKNOWN, always.
2. A value observed at one time does not overwrite a value observed at another.
   "Sáng nay sốt 39, giờ 37.8" is two true observations, not a contradiction.
3. Where a value came from is part of the value. SYSTEM_INFERENCE and SYNTHETIC
   can never silently become PATIENT_REPORTED.

Observations are append-only. Nothing is ever deleted or mutated in place; a
correction supersedes an earlier observation and records the link, so the full
history stays auditable.

This module is pure data and pure functions. It performs no I/O, holds no
session, and knows nothing about ESI, retrieval or the agent runtime.
"""

from __future__ import annotations

import unicodedata
import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any, Literal

# --------------------------------------------------------------------------
# Vocabulary
# --------------------------------------------------------------------------

FactStatus = Literal[
    # The patient (or a clinician) affirmed it.
    "KNOWN",
    # Nobody has said anything about it. The default for every fact.
    "UNKNOWN",
    # Explicitly denied: "Tôi không đau ngực."
    "NEGATED",
    # Hedged by the speaker: "Hình như tôi hơi khó thở."
    "UNCERTAIN",
    # Derived by the system, never asserted by a person.
    "INFERRED",
]

FactSource = Literal[
    "PATIENT_REPORTED",
    "CLINICAL_OBSERVATION",
    "CLINICIAN_ENTERED",
    "SYSTEM_INFERENCE",
    "RAG_EVIDENCE",
    "SYNTHETIC",
    # Replayed from a case recorded before canonical state existed. The patient
    # did say it, but the turn, timing and certainty are no longer recoverable,
    # so it must not be presented with the confidence of a live observation.
    "LEGACY_RECOVERED",
]

TemporalContext = Literal[
    "CURRENT",
    "HISTORICAL",
    "RELATIVE",
    "BEFORE_MEDICATION",
    "AFTER_MEDICATION",
    "BEFORE_EVENT",
    "AFTER_EVENT",
    "UNKNOWN_TIME",
]

# Keys whose value is the patient's own wording, not an asserted quantity.
#
# "đau bụng" and "đau bụng buồn ỉa" are two descriptions of one complaint, not
# two competing claims about it: the clinical content lives in the *key*
# (`complaint.abdominal_pain`), and the value only records how the patient
# happened to put it. Treating a rephrasing as a contradiction asks the patient
# to "confirm which is correct" when both are, which is baffling to read and
# spends the credibility that a real clarification depends on.
DESCRIPTIVE_KEY_PREFIXES: tuple[str, ...] = ("complaint.",)


def is_descriptive_key(key: str) -> bool:
    """Is this key free-text description rather than a value that can conflict?"""
    return key.startswith(DESCRIPTIVE_KEY_PREFIXES)


def _normalized_text(value: Any) -> str:
    """Accent-insensitive, whitespace-collapsed form for comparing wordings."""
    text = str(value).strip().lower()
    decomposed = unicodedata.normalize("NFD", text)
    stripped = "".join(
        character
        for character in decomposed
        if unicodedata.category(character) != "Mn"
    )
    return " ".join(stripped.replace("đ", "d").split())


def values_corroborate(previous: Any, current: Any) -> bool:
    """Do two observations say the same thing in different words?

    A contradiction is a claim the patient has to be asked to settle, so it has
    to be a real disagreement. "sáng nay" and "sáng" are one answer phrased two
    ways; treating them as a conflict stops the conversation to ask which of
    two identical times is correct, which is baffling to read and spends the
    credibility a genuine clarification depends on.

    Deliberately narrow. Only *textual* values are compared, and only when one
    wording contains the other, so "8 giờ" and "5 giờ" remain the conflict they
    are. Numbers are never merged: 6 and 8 out of 10 are different answers even
    though neither contains the other.
    """
    if isinstance(previous, bool) or isinstance(current, bool):
        return previous is current
    if not isinstance(previous, str) or not isinstance(current, str):
        return previous == current
    first = _normalized_text(previous)
    second = _normalized_text(current)
    if not first or not second:
        return False
    return first in second or second in first


# Sources that represent a real assertion by a person about this patient. Only
# these may satisfy a clinical requirement on their own.
PERSON_ASSERTED_SOURCES: frozenset[str] = frozenset(
    {"PATIENT_REPORTED", "CLINICAL_OBSERVATION", "CLINICIAN_ENTERED"}
)

# Replayed legacy facts are usable context but carry no recoverable provenance,
# so they are tracked separately from anything observed in a live turn.
PROVENANCE_DEGRADED_SOURCES: frozenset[str] = frozenset({"LEGACY_RECOVERED"})

# Statuses that assert presence. UNCERTAIN deliberately does not, and INFERRED
# is a system product rather than a patient statement.
AFFIRMING_STATUSES: frozenset[str] = frozenset({"KNOWN"})

# Temporal contexts describing the patient right now.
CURRENT_CONTEXTS: frozenset[str] = frozenset({"CURRENT", "AFTER_MEDICATION"})


def _now() -> str:
    return datetime.now(UTC).isoformat()


# --------------------------------------------------------------------------
# Observations
# --------------------------------------------------------------------------


@dataclass
class FactObservation:
    """One evidenced statement about one fact at one point in the conversation.

    Immutable in spirit: the only field that changes after creation is
    ``superseded_by``, set when a later correction replaces this observation.
    """

    value: Any
    status: FactStatus = "KNOWN"
    source: FactSource = "PATIENT_REPORTED"
    temporal: TemporalContext = "UNKNOWN_TIME"
    temporal_label: str | None = None
    raw_span: str = ""
    turn_id: str = ""
    confidence: float | None = None
    recorded_at: str = field(default_factory=_now)
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    # Set when a later observation corrects this one.
    superseded_by: str | None = None
    # Set on the correcting observation, pointing back at what it replaced.
    corrects: str | None = None
    note: str | None = None

    @property
    def is_active(self) -> bool:
        return self.superseded_by is None

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "value": self.value,
            "status": self.status,
            "source": self.source,
            "temporal": self.temporal,
            "temporal_label": self.temporal_label,
            "raw_span": self.raw_span,
            "turn_id": self.turn_id,
            "confidence": self.confidence,
            "recorded_at": self.recorded_at,
            "superseded_by": self.superseded_by,
            "corrects": self.corrects,
            "note": self.note,
        }

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> FactObservation:
        """Rebuild defensively: unknown or missing fields must never become
        a confident clinical value."""
        return cls(
            value=payload.get("value"),
            status=payload.get("status") or "UNKNOWN",
            source=payload.get("source") or "SYSTEM_INFERENCE",
            temporal=payload.get("temporal") or "UNKNOWN_TIME",
            temporal_label=payload.get("temporal_label"),
            raw_span=str(payload.get("raw_span") or ""),
            turn_id=str(payload.get("turn_id") or ""),
            confidence=payload.get("confidence"),
            recorded_at=str(payload.get("recorded_at") or _now()),
            id=str(payload.get("id") or uuid.uuid4()),
            superseded_by=payload.get("superseded_by"),
            corrects=payload.get("corrects"),
            note=payload.get("note"),
        )


@dataclass
class ClinicalFact:
    """The append-only observation history for one fact key."""

    key: str
    observations: list[FactObservation] = field(default_factory=list)

    def active(self) -> list[FactObservation]:
        return [item for item in self.observations if item.is_active]

    def current(self) -> FactObservation | None:
        """The observation describing the patient now.

        Prefers an explicitly current observation. Falls back to an untimed one,
        because most conversational statements carry no temporal marker and are
        about the present. A purely historical observation is never returned as
        the current value.
        """
        active = self.active()
        for contexts in (CURRENT_CONTEXTS, {"UNKNOWN_TIME", "RELATIVE"}):
            matches = [item for item in active if item.temporal in contexts]
            if matches:
                return matches[-1]
        return None

    def historical(self) -> list[FactObservation]:
        return [
            item
            for item in self.active()
            if item.temporal not in CURRENT_CONTEXTS
            and item.temporal not in {"UNKNOWN_TIME", "RELATIVE"}
        ]

    def superseded(self) -> list[FactObservation]:
        return [item for item in self.observations if not item.is_active]

    def to_dict(self) -> dict[str, Any]:
        return {
            "key": self.key,
            "observations": [item.to_dict() for item in self.observations],
        }

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> ClinicalFact:
        return cls(
            key=str(payload.get("key") or ""),
            observations=[
                FactObservation.from_dict(item)
                for item in payload.get("observations", [])
                if isinstance(item, dict)
            ],
        )


@dataclass
class SymptomEntity:
    """A symptom the patient has referred to, so later references can link back.

    Keeps entity identity separate from fact keys, so "cơn đau đầu tôi nói lúc
    nãy" attaches to the existing headache rather than creating a second one.
    """

    entity_id: str
    label: str
    normalized: str
    first_turn_id: str = ""
    last_turn_id: str = ""
    mention_count: int = 1

    def to_dict(self) -> dict[str, Any]:
        return {
            "entity_id": self.entity_id,
            "label": self.label,
            "normalized": self.normalized,
            "first_turn_id": self.first_turn_id,
            "last_turn_id": self.last_turn_id,
            "mention_count": self.mention_count,
        }

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> SymptomEntity:
        return cls(
            entity_id=str(payload.get("entity_id") or uuid.uuid4()),
            label=str(payload.get("label") or ""),
            normalized=str(payload.get("normalized") or ""),
            first_turn_id=str(payload.get("first_turn_id") or ""),
            last_turn_id=str(payload.get("last_turn_id") or ""),
            mention_count=int(payload.get("mention_count") or 1),
        )


@dataclass
class Contradiction:
    """Two active observations of the same fact and time that cannot both hold."""

    key: str
    previous_observation_id: str
    conflicting_observation_id: str
    previous_value: Any
    conflicting_value: Any
    temporal: TemporalContext
    status: Literal["UNRESOLVED", "RESOLVED"] = "UNRESOLVED"

    def to_dict(self) -> dict[str, Any]:
        return {
            "key": self.key,
            "previous_observation_id": self.previous_observation_id,
            "conflicting_observation_id": self.conflicting_observation_id,
            "previous_value": self.previous_value,
            "conflicting_value": self.conflicting_value,
            "temporal": self.temporal,
            "status": self.status,
        }

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> Contradiction:
        return cls(
            key=str(payload.get("key") or ""),
            previous_observation_id=str(payload.get("previous_observation_id") or ""),
            conflicting_observation_id=str(
                payload.get("conflicting_observation_id") or ""
            ),
            previous_value=payload.get("previous_value"),
            conflicting_value=payload.get("conflicting_value"),
            temporal=payload.get("temporal") or "UNKNOWN_TIME",
            status=payload.get("status") or "UNRESOLVED",
        )


# --------------------------------------------------------------------------
# The state
# --------------------------------------------------------------------------

# Facts whose change plausibly moves triage acuity, so a correction to one must
# force a reassessment rather than quietly editing a decided case.
REASSESSMENT_TRIGGERING_KEYS: frozenset[str] = frozenset(
    {
        "onset_time",
        "severity_score",
        "age",
        "radiation",
        "duration",
    }
)
REASSESSMENT_TRIGGERING_PREFIXES: tuple[str, ...] = (
    "symptom.",
    "vital.",
    "medication",
)


def triggers_reassessment(key: str) -> bool:
    """Whether changing this fact must invalidate a prior triage conclusion."""
    return key in REASSESSMENT_TRIGGERING_KEYS or key.startswith(
        REASSESSMENT_TRIGGERING_PREFIXES
    )


@dataclass
class ExtractionDisagreement:
    """Two extractors read the same patient words differently.

    This is emphatically **not** a patient contradiction. The patient said one
    thing; two parsers disagreed about what it was. Recording it as a clinical
    contradiction would put words in the patient's mouth and would send them a
    clarification question about something they never said twice.

    Canonical stays authoritative. The disagreement is kept so the divergence is
    auditable and the legacy parser's drift is measurable.
    """

    fact_key: str
    legacy_value: Any
    canonical_value: Any
    turn_id: str = ""
    detected_at: str = field(default_factory=_now)
    resolution: str = "CANONICAL_AUTHORITATIVE"

    def to_dict(self) -> dict[str, Any]:
        return {
            "fact_key": self.fact_key,
            "legacy_value": self.legacy_value,
            "canonical_value": self.canonical_value,
            "turn_id": self.turn_id,
            "detected_at": self.detected_at,
            "resolution": self.resolution,
        }

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> ExtractionDisagreement:
        return cls(
            fact_key=str(payload.get("fact_key") or ""),
            legacy_value=payload.get("legacy_value"),
            canonical_value=payload.get("canonical_value"),
            turn_id=str(payload.get("turn_id") or ""),
            detected_at=str(payload.get("detected_at") or _now()),
            resolution=str(payload.get("resolution") or "CANONICAL_AUTHORITATIVE"),
        )


@dataclass
class CanonicalPatientState:
    """The current, evidenced picture of one patient in one triage session."""

    facts: dict[str, ClinicalFact] = field(default_factory=dict)
    entities: dict[str, SymptomEntity] = field(default_factory=dict)
    contradictions: list[Contradiction] = field(default_factory=list)
    # Parser divergence, kept strictly apart from patient contradictions.
    extraction_disagreements: list[ExtractionDisagreement] = field(
        default_factory=list
    )
    version: int = 0
    # Keys changed since the last triage conclusion, so a reassessment can be
    # justified rather than merely triggered.
    pending_reassessment_keys: list[str] = field(default_factory=list)

    # -- reading ----------------------------------------------------------

    def status_of(self, key: str) -> FactStatus:
        """UNKNOWN unless something was actually observed. Never False."""
        fact = self.facts.get(key)
        if fact is None:
            return "UNKNOWN"
        current = fact.current()
        if current is None:
            # Only historical observations exist; nothing is claimed about now.
            return "UNKNOWN" if not fact.active() else "KNOWN"
        return current.status

    def value_of(self, key: str) -> Any:
        fact = self.facts.get(key)
        if fact is None:
            return None
        current = fact.current()
        return current.value if current else None

    def observation_of(self, key: str) -> FactObservation | None:
        fact = self.facts.get(key)
        return fact.current() if fact else None

    def history_of(self, key: str) -> list[FactObservation]:
        fact = self.facts.get(key)
        return list(fact.observations) if fact else []

    def latest_observation(self, key: str) -> FactObservation | None:
        """The most recent active observation whatever its time.

        Answers "was this ever reported?", which is a different question from
        "is this true now?" - ``value_of`` deliberately answers only the latter,
        so a symptom reported "lúc nãy" is retrievable without being asserted as
        a current finding.
        """
        fact = self.facts.get(key)
        active = fact.active() if fact else []
        return active[-1] if active else None

    def was_ever_reported(self, key: str) -> bool:
        return self.latest_observation(key) is not None

    def historical_values(self, key: str) -> list[FactObservation]:
        fact = self.facts.get(key)
        return fact.historical() if fact else []

    def is_affirmed(self, key: str) -> bool:
        """Presence asserted by a person. UNCERTAIN and INFERRED do not count."""
        observation = self.observation_of(key)
        return bool(
            observation
            and observation.status in AFFIRMING_STATUSES
            and observation.source in PERSON_ASSERTED_SOURCES
        )

    def unresolved_contradictions(self) -> list[Contradiction]:
        return [item for item in self.contradictions if item.status == "UNRESOLVED"]

    def record_disagreement(
        self,
        fact_key: str,
        legacy_value: Any,
        canonical_value: Any,
        *,
        turn_id: str = "",
    ) -> ExtractionDisagreement:
        """Note that two parsers read one utterance differently.

        Deliberately does not touch ``contradictions`` and does not bump the
        version: nothing about the patient changed, only our reading of them.
        """
        disagreement = ExtractionDisagreement(
            fact_key=fact_key,
            legacy_value=legacy_value,
            canonical_value=canonical_value,
            turn_id=turn_id,
        )
        self.extraction_disagreements.append(disagreement)
        return disagreement

    # -- writing ----------------------------------------------------------

    def record(
        self,
        key: str,
        value: Any,
        *,
        status: FactStatus = "KNOWN",
        source: FactSource = "PATIENT_REPORTED",
        temporal: TemporalContext = "UNKNOWN_TIME",
        temporal_label: str | None = None,
        raw_span: str = "",
        turn_id: str = "",
        confidence: float | None = None,
        is_correction: bool = False,
        note: str | None = None,
    ) -> FactObservation:
        """Append one observation, deciding how it relates to what came before.

        Three distinct relationships, which must not collapse into one
        overwrite:

        * **Correction** - the speaker retracted an earlier value. The old
          observation is superseded and linked, so history survives.
        * **Temporal change** - a different point in time. Both stay active.
        * **Contradiction** - same time, different value, no retraction. Both
          stay active and the conflict is recorded for clarification.
        """
        fact = self.facts.setdefault(key, ClinicalFact(key=key))
        observation = FactObservation(
            value=value,
            status=status,
            source=source,
            temporal=temporal,
            temporal_label=temporal_label,
            raw_span=raw_span,
            turn_id=turn_id,
            confidence=confidence,
            note=note,
        )

        same_time = [
            item
            for item in fact.active()
            if item.temporal == temporal and not values_corroborate(item.value, value)
        ]
        if same_time:
            previous = same_time[-1]
            if is_correction:
                previous.superseded_by = observation.id
                observation.corrects = previous.id
                # A retracted value can no longer sustain a contradiction.
                for contradiction in self.contradictions:
                    if previous.id in {
                        contradiction.previous_observation_id,
                        contradiction.conflicting_observation_id,
                    }:
                        contradiction.status = "RESOLVED"
            elif is_descriptive_key(key):
                # Both wordings stay on the record and neither is disputed.
                # They corroborate the same complaint rather than compete.
                pass
            elif turn_id and previous.turn_id == turn_id:
                # One utterance, read two ways. The patient said a single
                # thing; it is our extraction that produced two values, so
                # this is our disagreement to record and not a question to
                # put to them. Asking someone to reconcile a conflict they
                # never made is how a system loses their trust.
                self.record_disagreement(
                    key,
                    previous.value,
                    value,
                    turn_id=turn_id,
                )
            else:
                self.contradictions.append(
                    Contradiction(
                        key=key,
                        previous_observation_id=previous.id,
                        conflicting_observation_id=observation.id,
                        previous_value=previous.value,
                        conflicting_value=value,
                        temporal=temporal,
                    )
                )

        fact.observations.append(observation)
        self.version += 1
        if triggers_reassessment(key) and key not in self.pending_reassessment_keys:
            self.pending_reassessment_keys.append(key)
        return observation

    def resolve_contradiction(
        self,
        key: str,
        chosen_value: Any,
        *,
        turn_id: str = "",
        raw_span: str = "",
    ) -> FactObservation:
        """Settle a conflict by recording the patient's chosen value as canonical."""
        fact = self.facts.get(key)
        if fact is not None:
            for item in fact.active():
                if item.value != chosen_value:
                    item.superseded_by = "resolved-by-patient"
        for contradiction in self.contradictions:
            if contradiction.key == key:
                contradiction.status = "RESOLVED"
        return self.record(
            key,
            chosen_value,
            turn_id=turn_id,
            raw_span=raw_span,
            note="contradiction_resolved_by_patient",
        )

    def clear_reassessment_flags(self) -> None:
        self.pending_reassessment_keys = []

    # -- entities ---------------------------------------------------------

    def upsert_entity(
        self,
        label: str,
        normalized: str,
        *,
        turn_id: str = "",
    ) -> SymptomEntity:
        """Reuse an existing symptom entity rather than duplicating it."""
        for entity in self.entities.values():
            if entity.normalized == normalized:
                entity.last_turn_id = turn_id or entity.last_turn_id
                entity.mention_count += 1
                return entity
        entity = SymptomEntity(
            entity_id=str(uuid.uuid4()),
            label=label,
            normalized=normalized,
            first_turn_id=turn_id,
            last_turn_id=turn_id,
        )
        self.entities[entity.entity_id] = entity
        return entity

    def most_recent_entity(self) -> SymptomEntity | None:
        if not self.entities:
            return None
        return sorted(
            self.entities.values(),
            key=lambda item: item.mention_count,
        )[-1]

    def find_entity(self, normalized: str) -> SymptomEntity | None:
        for entity in self.entities.values():
            if entity.normalized == normalized:
                return entity
        return None

    # -- serialization ----------------------------------------------------

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": 1,
            "version": self.version,
            "facts": {key: fact.to_dict() for key, fact in self.facts.items()},
            "entities": {
                key: entity.to_dict() for key, entity in self.entities.items()
            },
            "contradictions": [item.to_dict() for item in self.contradictions],
            "extraction_disagreements": [
                item.to_dict() for item in self.extraction_disagreements
            ],
            "pending_reassessment_keys": list(self.pending_reassessment_keys),
        }

    @classmethod
    def from_dict(cls, payload: dict[str, Any] | None) -> CanonicalPatientState:
        """Rebuild from storage. A missing or unreadable payload yields an empty
        state, which reads as UNKNOWN everywhere - never as a set of negatives."""
        if not isinstance(payload, dict):
            return cls()
        facts = {
            str(key): ClinicalFact.from_dict(value)
            for key, value in (payload.get("facts") or {}).items()
            if isinstance(value, dict)
        }
        entities = {
            str(key): SymptomEntity.from_dict(value)
            for key, value in (payload.get("entities") or {}).items()
            if isinstance(value, dict)
        }
        return cls(
            facts=facts,
            entities=entities,
            contradictions=[
                Contradiction.from_dict(item)
                for item in (payload.get("contradictions") or [])
                if isinstance(item, dict)
            ],
            extraction_disagreements=[
                ExtractionDisagreement.from_dict(item)
                for item in (payload.get("extraction_disagreements") or [])
                if isinstance(item, dict)
            ],
            version=int(payload.get("version") or 0),
            pending_reassessment_keys=[
                str(item)
                for item in (payload.get("pending_reassessment_keys") or [])
            ],
        )
