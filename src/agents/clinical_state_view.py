"""The one place canonical state is interpreted for clinical decisions.

Readiness, retrieval and reasoning previously each read a flat blueprint and
each applied their own idea of what a missing value meant. That is how a fact
nobody asked about and a fact the patient explicitly denied ended up looking the
same to every consumer.

This layer resolves the semantics once, so every decision component reads the
same truth:

* ``UNKNOWN`` is not ``NEGATED`` and neither is ``False``;
* a symptom reported last week is not a symptom now;
* a hedged report is not an affirmed finding;
* an inference or a synthetic seed is not something the patient said.

It is read-only. Nothing here mutates state, and nothing here talks to the
database, an LLM, or the agent runtime.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from src.agents.canonical_state import (
    PROVENANCE_DEGRADED_SOURCES,
    CanonicalPatientState,
    FactObservation,
)

# Symptom keys that name a clinical presentation, used to pick the requirement
# profile a case should be judged against.
SYMPTOM_CLUSTER_KEYS: tuple[tuple[str, str], ...] = (
    ("symptom.chest_pain", "chest_pain"),
    ("symptom.dyspnea", "dyspnea"),
    ("symptom.syncope", "syncope"),
    ("symptom.seizure", "neurologic"),
    ("symptom.bleeding", "bleeding"),
    ("symptom.abdominal_pain", "abdominal_pain"),
    ("symptom.headache", "headache"),
    ("symptom.fever", "fever"),
    ("symptom.diarrhea", "gastrointestinal"),
    ("symptom.vomiting", "gastrointestinal"),
    ("symptom.nausea", "gastrointestinal"),
    ("symptom.back_pain", "musculoskeletal"),
    ("symptom.sore_throat", "ent"),
    ("symptom.rash", "dermatologic"),
)


@dataclass(frozen=True)
class FactReading:
    """A resolved answer about one fact, with the evidence behind it."""

    key: str
    status: str
    value: Any
    temporal: str | None
    source: str | None
    raw_span: str = ""

    @property
    def is_present(self) -> bool:
        return self.status == "KNOWN"

    @property
    def is_negated(self) -> bool:
        return self.status == "NEGATED"

    @property
    def is_unknown(self) -> bool:
        return self.status == "UNKNOWN"

    @property
    def is_uncertain(self) -> bool:
        return self.status == "UNCERTAIN"

    @property
    def is_inferred(self) -> bool:
        return self.status == "INFERRED"


class ClinicalStateView:
    """Read-only semantic access to one patient's canonical state."""

    def __init__(self, state: CanonicalPatientState) -> None:
        self._state = state

    @classmethod
    def from_agent_state(cls, agent_state: dict[str, Any]) -> ClinicalStateView:
        """Build from a turn's serialized state, tolerating legacy/empty rows."""
        return cls(CanonicalPatientState.from_dict(agent_state.get("canonical_state")))

    @property
    def canonical(self) -> CanonicalPatientState:
        return self._state

    # -- single-fact queries ---------------------------------------------

    def read(self, key: str) -> FactReading:
        """Resolve one fact as it stands *now*.

        A fact whose only observations are historical reads UNKNOWN, because
        nothing has been claimed about the present.
        """
        observation = self._state.observation_of(key)
        if observation is None:
            return FactReading(
                key=key, status="UNKNOWN", value=None, temporal=None, source=None
            )
        return FactReading(
            key=key,
            status=observation.status,
            value=observation.value,
            temporal=observation.temporal,
            source=observation.source,
            raw_span=observation.raw_span,
        )

    def is_present(self, key: str) -> bool:
        return self.read(key).is_present

    def is_negated(self, key: str) -> bool:
        return self.read(key).is_negated

    def is_unknown(self, key: str) -> bool:
        return self.read(key).is_unknown

    def is_uncertain(self, key: str) -> bool:
        return self.read(key).is_uncertain

    def is_inferred(self, key: str) -> bool:
        return self.read(key).is_inferred

    def current_value(self, key: str) -> Any:
        return self._state.value_of(key)

    def latest_observation(self, key: str) -> FactObservation | None:
        return self._state.latest_observation(key)

    def historical_values(self, key: str) -> list[FactObservation]:
        return self._state.historical_values(key)

    def was_ever_reported(self, key: str) -> bool:
        return self._state.was_ever_reported(key)

    def is_patient_asserted(self, key: str) -> bool:
        """True only for a person's affirmation, never an inference or seed."""
        return self._state.is_affirmed(key)

    # -- collections -------------------------------------------------------

    def present_symptoms(self) -> list[str]:
        """Symptoms affirmed as current. Negated, hedged and historical excluded."""
        return [
            key.removeprefix("symptom.")
            for key in self._symptom_keys()
            if self.is_present(key)
        ]

    def negated_symptoms(self) -> list[str]:
        return [
            key.removeprefix("symptom.")
            for key in self._symptom_keys()
            if self.is_negated(key)
        ]

    def uncertain_symptoms(self) -> list[str]:
        return [
            key.removeprefix("symptom.")
            for key in self._symptom_keys()
            if self.is_uncertain(key)
        ]

    def historical_symptoms(self) -> list[str]:
        """Reported in the past with nothing claimed about now."""
        return [
            key.removeprefix("symptom.")
            for key in self._symptom_keys()
            if not self.is_present(key)
            and not self.is_negated(key)
            and self._state.historical_values(key)
        ]

    def _symptom_keys(self) -> list[str]:
        return sorted(
            key for key in self._state.facts if key.startswith("symptom.")
        )

    def observations_for(self, entity_normalized: str) -> list[FactObservation]:
        """Everything recorded about one symptom entity, newest last."""
        collected: list[FactObservation] = []
        for key, fact in self._state.facts.items():
            if key == f"symptom.{entity_normalized}" or key.startswith(
                f"{entity_normalized}."
            ):
                collected.extend(fact.active())
        return sorted(collected, key=lambda item: item.recorded_at)

    def recent_events(self, limit: int = 10) -> list[FactObservation]:
        """The most recent active observations across every fact."""
        every: list[FactObservation] = []
        for fact in self._state.facts.values():
            every.extend(fact.active())
        return sorted(every, key=lambda item: item.recorded_at)[-limit:]

    def current_complaints(self) -> list[str]:
        """Complaint phrases that stand as current. Denied and historical excluded."""
        return self._active_phrases("complaint.")

    def current_associated(self) -> list[str]:
        return self._active_phrases("associated.")

    def _active_phrases(self, prefix: str) -> list[str]:
        phrases: list[str] = []
        for key in sorted(self._state.facts):
            if not key.startswith(prefix):
                continue
            reading = self.read(key)
            # Only an affirmed, current phrase survives. NEGATED, UNCERTAIN and
            # historical-only complaints are excluded by their canonical status,
            # not by matching their wording against a table.
            if reading.is_present and reading.value:
                phrases.append(str(reading.value))
        return phrases

    def symptom_cluster(self) -> str | None:
        """The presentation this case should be judged as, from canonical only.

        Decision-critical: the cluster selects the readiness requirement profile,
        filters which protocols are in scope during retrieval, and must match the
        calibration profile at the evidence gate. It therefore never consults the
        legacy blueprint - a classification with no canonical evidence behind it
        would let lexical guesswork choose a clinical protocol.

        Historical-only, negated and unknown all yield None, which downstream
        means "insufficient context to classify", not "no presentation".
        """
        for key, cluster in SYMPTOM_CLUSTER_KEYS:
            if self.is_present(key):
                return cluster
        for key, cluster in SYMPTOM_CLUSTER_KEYS:
            if self.is_uncertain(key):
                return cluster
        # A complaint the patient stated in their own words, recorded canonically.
        for key in sorted(self._state.facts):
            if not key.startswith("complaint."):
                continue
            if not self.read(key).is_present:
                continue
            slug = key.removeprefix("complaint.")
            for symptom_key, cluster in SYMPTOM_CLUSTER_KEYS:
                if symptom_key.removeprefix("symptom.") == slug:
                    return cluster
            return "other_specific"
        return None

    # -- reasoner input ----------------------------------------------------

    def to_reasoner_payload(self) -> dict[str, Any]:
        """State for the reasoner with the semantics already resolved.

        The reasoner used to receive a raw blueprint dump and was left to work
        out for itself what an absent key meant. It no longer interprets state:
        present, denied, uncertain, historical and unknown arrive as separate,
        labelled lists, so the model cannot quietly read silence as a negative
        or a last-week symptom as a current one.
        """
        historical: dict[str, Any] = {}
        for key in sorted(self._state.facts):
            values = self._state.historical_values(key)
            if values:
                historical[key] = [
                    {
                        "value": item.value,
                        "when": item.temporal_label or item.temporal,
                    }
                    for item in values
                ]

        return {
            "current_symptoms": self.present_symptoms(),
            "explicitly_denied_symptoms": self.negated_symptoms(),
            "uncertain_symptoms": self.uncertain_symptoms(),
            "historical_only_symptoms": self.historical_symptoms(),
            "current_values": {
                key: self.current_value(key)
                for key in ("onset_time", "severity_score", "radiation", "age")
                if self.current_value(key) is not None
            },
            "current_vitals": {
                key.removeprefix("vital."): self.current_value(key)
                for key in sorted(self._state.facts)
                if key.startswith("vital.") and self.current_value(key) is not None
            },
            "historical_observations": historical,
            "not_asked_or_unknown": self.decision_relevant_unknown_keys(),
            "provenance_note": (
                "current_symptoms are patient-affirmed. explicitly_denied_symptoms "
                "were denied by the patient and must not be treated as unknown. "
                "not_asked_or_unknown means no information exists; it does NOT "
                "mean the finding is absent. historical_only_symptoms describe "
                "the past and must not be read as the patient's current state."
            ),
        }

    def decision_relevant_unknown_keys(self) -> list[str]:
        """Facts with no observation at all, listed so the reasoner cannot
        mistake silence for a negative."""
        candidates = (
            "onset_time",
            "severity_score",
            "symptom.chest_pain",
            "symptom.dyspnea",
            "vital.temperature_c",
        )
        return [key for key in candidates if self.is_unknown(key)]

    def unresolved_contradictions(self) -> list[dict[str, Any]]:
        return [item.to_dict() for item in self._state.unresolved_contradictions()]

    def pending_reassessment_keys(self) -> list[str]:
        return list(self._state.pending_reassessment_keys)

    def extraction_disagreements(self) -> list[dict[str, Any]]:
        """Parser divergences, kept separate from patient contradictions."""
        return [item.to_dict() for item in self._state.extraction_disagreements]

    def has_degraded_provenance(self) -> bool:
        """True when any active fact was replayed from a pre-canonical case."""
        return any(
            observation.source in PROVENANCE_DEGRADED_SOURCES
            for fact in self._state.facts.values()
            for observation in fact.active()
        )
