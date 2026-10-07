"""Derive the legacy ClinicalBlueprint from canonical state.

The blueprint predates the canonical model and is still read by the patient-facing
intake summary, the SBAR and the session title. It is not a second source of
truth; it is a **read-model projected from canonical state**:

    CanonicalPatientState -> projection -> ClinicalBlueprint

Ingestion runs first, so anything the legacy slot-filling extractor found -
free-text complaints, structured-form answers - becomes a canonical fact with
honest provenance before the projection reads it back out. Where the two
extractors disagree about the same utterance, canonical stays authoritative and
the divergence is recorded as an ``ExtractionDisagreement``: a parser problem,
never a patient contradiction.

Complaint filtering is semantic. A complaint whose canonical symptom is NEGATED
or historical-only cannot appear as a current complaint, because its canonical
status says so - not because its wording matched a table.
"""

from __future__ import annotations

import re
import unicodedata
from typing import Any

from src.agents.canonical_state import CanonicalPatientState
from src.agents.clinical_state_view import ClinicalStateView
from src.agents.nodes.fact_extraction import (
    SYMPTOM_DISPLAY_VI,
    complaint_slug,
    symptom_key_for_phrase,
)

# Blueprint slots the canonical model does not model yet. They pass through the
# projection untouched, and are the documented remainder of the migration.
#
# ``vital_signs`` is *not* one of them any more. Canonical state records vitals
# as ``vital.*`` facts, and leaving the blueprint slot as pure passthrough meant
# a value the extractor understood ("38.5 độ" -> vital.temperature_c) reached
# canonical state and then vanished: it never appeared in the intake summary the
# patient reviews, never entered the retrieval query, and never flipped
# ``vital_signs_status`` off NOT_REVIEWED.
PASSTHROUGH_FIELDS: tuple[str, ...] = (
    "clinical_keywords_en",
    "recent_procedure",
    "clinical_context_note",
    "vital_signs_source",
    "vital_signs_measured_at",
)

# Canonical vital keys and the blueprint slot each fills. Blood pressure is
# handled separately because the blueprint carries the combined display string
# alongside the two numbers.
_VITAL_PROJECTIONS: tuple[str, ...] = (
    "temperature_c",
    "spo2",
    "heart_rate",
    "respiratory_rate",
    "systolic_bp",
    "diastolic_bp",
    "gcs",
)

# Canonical keys the projection owns, and the blueprint slot each maps to.
_SCALAR_PROJECTIONS: tuple[tuple[str, str], ...] = (
    ("onset_time", "onset_time"),
    ("severity_score", "severity_score"),
    ("radiation", "radiation"),
)

COMPLAINT_PREFIX = "complaint."
ASSOCIATED_PREFIX = "associated."

NO_CURRENT_SYMPTOM_PATTERNS = (
    r"\b(?:toi\s+)?khong\s+(?:bi|co|thay|cam thay)?\s*(?:kho chiu|dau|dau don|trieu chung)(?:\s+gi|\s+gi het|\s+nao)?\b",
    r"\bkhong\s+co\s+trieu\s+chung(?:\s+cap|\s+gi|\s+nao)?\b",
    r"\b(?:hien tai\s+)?(?:toi\s+)?binh thuong\b",
    r"\bkhong\s+bi\s+kho\s+chiu\s+gi\s+het\b",
    r"\bdau\s+don\s+(?:hay\s+trieu\s+chung\s+)?gi\s+het\b",
)


def ingest_blueprint(
    state: CanonicalPatientState,
    blueprint: dict[str, Any],
    *,
    turn_id: str = "",
    source: str = "PATIENT_REPORTED",
) -> None:
    """Move everything the legacy extractor found into canonical state.

    Scalars are only ingested when canonical has no value, and a differing value
    is recorded as an extraction disagreement rather than overwriting canonical
    or manufacturing a patient contradiction.

    Complaints are ingested with the status their canonical symptom already has,
    so a denied symptom cannot re-enter as a positive complaint.
    """
    for canonical_key, blueprint_key in _SCALAR_PROJECTIONS:
        value = blueprint.get(blueprint_key)
        if value is None:
            continue
        existing = state.value_of(canonical_key)
        if existing is None:
            state.record(
                canonical_key,
                value,
                source=source,  # type: ignore[arg-type]
                temporal="UNKNOWN_TIME",
                raw_span=str(value)[:120],
                turn_id=turn_id,
            )
        elif existing != value:
            # Two parsers, one utterance, two readings. Canonical wins, and the
            # divergence becomes observable instead of vanishing.
            state.record_disagreement(
                canonical_key,
                legacy_value=value,
                canonical_value=existing,
                turn_id=turn_id,
            )

    _ingest_phrases(
        state,
        blueprint.get("chief_complaint", []) or [],
        prefix=COMPLAINT_PREFIX,
        turn_id=turn_id,
        source=source,
    )
    _ingest_phrases(
        state,
        blueprint.get("associated_symptoms", []) or [],
        prefix=ASSOCIATED_PREFIX,
        turn_id=turn_id,
        source=source,
    )

    for item in blueprint.get("current_medication", []) or []:
        name = str(item).strip()
        if name and state.value_of("medication") is None:
            state.record(
                "medication",
                name,
                source=source,  # type: ignore[arg-type]
                temporal="UNKNOWN_TIME",
                raw_span=name[:120],
                turn_id=turn_id,
            )


def _ingest_phrases(
    state: CanonicalPatientState,
    phrases: list[Any],
    *,
    prefix: str,
    turn_id: str,
    source: str,
) -> None:
    view = ClinicalStateView(state)
    for item in phrases:
        phrase = str(item).strip()
        if not phrase:
            continue
        if prefix == COMPLAINT_PREFIX and _is_no_current_symptom_phrase(phrase):
            continue
        key = f"{prefix}{complaint_slug(phrase)}"
        if state.value_of(key) == phrase:
            continue

        # Inherit the canonical status of the symptom this phrase names, so a
        # denial recorded from the patient's own words governs the complaint.
        symptom_key = symptom_key_for_phrase(phrase)
        status = "KNOWN"
        temporal = "UNKNOWN_TIME"
        if symptom_key:
            reading = view.read(f"symptom.{symptom_key}")
            if reading.is_negated:
                status = "NEGATED"
            elif reading.is_uncertain:
                status = "UNCERTAIN"
            if reading.temporal:
                temporal = reading.temporal
        state.record(
            key,
            phrase,
            status=status,  # type: ignore[arg-type]
            source=source,  # type: ignore[arg-type]
            temporal=temporal,  # type: ignore[arg-type]
            raw_span=phrase[:120],
            turn_id=turn_id,
        )


def _is_no_current_symptom_phrase(phrase: str) -> bool:
    folded = _fold_vi(phrase)
    return any(re.search(pattern, folded) for pattern in NO_CURRENT_SYMPTOM_PATTERNS)


def _fold_vi(text: str) -> str:
    normalized = unicodedata.normalize("NFD", text.lower().replace("đ", "d"))
    return " ".join(
        "".join(
            character
            for character in normalized
            if unicodedata.category(character) != "Mn"
        ).split()
    )


def project_blueprint(
    state: CanonicalPatientState,
    legacy: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build the blueprint read-model from canonical state.

    Every clinically decisive field comes from canonical. ``legacy`` supplies
    only the structured-form slots canonical does not own yet.
    """
    legacy = legacy or {}
    view = ClinicalStateView(state)

    projected: dict[str, Any] = {
        "chief_complaint": _current_complaints(view),
        "associated_symptoms": view.current_associated(),
        "current_medication": _medications(state),
        "confidence_score": float(legacy.get("confidence_score", 0.0) or 0.0),
    }
    for canonical_key, blueprint_key in _SCALAR_PROJECTIONS:
        reading = view.read(canonical_key)
        value = reading.value if reading.is_present else None
        if value is None:
            value = _primary_problem_scalar(view, canonical_key)
        projected[blueprint_key] = value

    for field in PASSTHROUGH_FIELDS:
        if field in legacy:
            projected[field] = legacy[field]
    projected.setdefault("clinical_keywords_en", [])
    projected["vital_signs"] = _project_vitals(view, legacy)

    return projected


def _primary_problem_scalar(
    view: ClinicalStateView,
    attribute: str,
) -> Any:
    """Read a generic blueprint scalar from the primary problem if needed.

    Adaptive questioning records attributed answers under the active problem
    (for example ``headache.onset_time`` and ``headache.severity_score``).
    The legacy blueprint still exposes generic slots (``onset_time`` and
    ``severity_score``) for retrieval, SBAR and the reasoner.  For the primary
    complaint these are the same patient answer, so the projection must bridge
    the namespaces instead of letting later phases ask the same question again.
    """
    from src.agents.problem_state import build_problem_state

    primary = build_problem_state(view).primary
    if primary is None:
        return None
    fact = primary.facts.get(attribute)
    # An explicit "I don't know" settles the conversational question but is
    # still an UNCERTAIN clinical fact.  It must not be projected as a scalar
    # value: doing so turns "không rõ" into a KNOWN severity/onset the next
    # time the legacy blueprint is ingested.
    if fact is None or fact.status != "KNOWN":
        return None
    return fact.value


def _current_complaints(view: ClinicalStateView) -> list[str]:
    """Complaint phrases, falling back to the symptoms the patient affirmed.

    ``complaint.*`` facts come from the legacy slot-filling extractor, whose
    vocabulary is narrower than the canonical symptom lexicon. When a patient
    wrote something the canonical extractor understood and the legacy one did
    not -- "đi ngoài phân đen", "hụt hơi khi leo cầu thang" -- the symptom was
    recorded canonically while the complaint list stayed empty. Downstream that
    empty list meant an empty retrieval query, a blank intake summary, and a
    turn that ended in a clinician handoff with no search ever performed.

    The fallback names the symptom canonical state already holds, in the
    Vietnamese the rest of the system uses for it, so the patient reads
    "tiêu chảy" rather than the accent-folded fragment the matcher happened to
    align on. Nothing is invented: every entry corresponds to a symptom fact
    the patient affirmed, and a symptom with no display wording falls back to
    their own matched span rather than to an internal identifier.
    """
    complaints = view.current_complaints()
    if complaints:
        return complaints
    derived: list[str] = []
    for symptom in view.present_symptoms():
        phrase = SYMPTOM_DISPLAY_VI.get(symptom, "")
        if not phrase:
            phrase = (view.read(f"symptom.{symptom}").raw_span or "").strip()
        if phrase and phrase not in derived:
            derived.append(phrase)
    return derived


def _project_vitals(
    view: ClinicalStateView,
    legacy: dict[str, Any],
) -> dict[str, Any]:
    """Merge structured-form vitals with the ones canonical state holds.

    The structured vitals form writes straight into the legacy slot and has no
    canonical key, so it is kept. Anything canonical knows is layered on top,
    because canonical is where free-text vitals land.
    """
    vitals: dict[str, Any] = dict(legacy.get("vital_signs") or {})
    for key in _VITAL_PROJECTIONS:
        value = view.current_value(f"vital.{key}")
        if value is not None:
            vitals[key] = value
    systolic = vitals.get("systolic_bp")
    diastolic = vitals.get("diastolic_bp")
    if systolic is not None and diastolic is not None:
        vitals.setdefault("blood_pressure", f"{systolic}/{diastolic}")
    return vitals


def _medications(state: CanonicalPatientState) -> list[str]:
    """Only medications the patient actually affirmed."""
    observation = state.observation_of("medication")
    if observation is None or observation.status == "NEGATED":
        return []
    return [str(observation.value)]
