"""Canonical Patient State: fact semantics, temporal model, corrections.

The governing rule under test: every turn may change state, but no state value
may become a clinical fact without evidence and provenance.
"""

from __future__ import annotations

import pytest

from src.agents.canonical_state import CanonicalPatientState
from src.agents.nodes.fact_extraction import apply_message_to_state, extract_facts
from src.agents.nodes.temporal_context import (
    has_anaphoric_reference,
    is_correction,
    read_temporal_context,
)


def _state(*messages: str) -> CanonicalPatientState:
    state = CanonicalPatientState()
    for index, message in enumerate(messages):
        apply_message_to_state(state, message, turn_id=f"turn-{index + 1}")
    return state


# --------------------------------------------------------------------------
# §16 Unknown / Negation / Current / Historical
# --------------------------------------------------------------------------

def test_a_fact_never_mentioned_is_unknown() -> None:
    state = _state("Tôi bị đau đầu")
    assert state.status_of("symptom.chest_pain") == "UNKNOWN"
    # The decisive point: absence must not read as a negative finding.
    assert state.status_of("symptom.chest_pain") != "NEGATED"
    assert state.value_of("symptom.chest_pain") is None


def test_explicit_denial_is_negated_not_unknown() -> None:
    state = _state("Tôi không đau ngực")
    assert state.status_of("symptom.chest_pain") == "NEGATED"


def test_denial_and_silence_are_distinguishable() -> None:
    denied = _state("Tôi không đau ngực")
    silent = _state("Tôi bị đau đầu")
    assert denied.status_of("symptom.chest_pain") == "NEGATED"
    assert silent.status_of("symptom.chest_pain") == "UNKNOWN"
    assert denied.status_of("symptom.chest_pain") != silent.status_of(
        "symptom.chest_pain"
    )


def test_current_symptom_is_known_and_affirmed() -> None:
    state = _state("Tôi đang đau ngực")
    assert state.status_of("symptom.chest_pain") == "KNOWN"
    assert state.is_affirmed("symptom.chest_pain") is True


def test_historical_symptom_does_not_become_a_current_finding() -> None:
    state = _state("Tuần trước tôi bị đau ngực")
    observation = state.observation_of("symptom.chest_pain")
    history = state.historical_values("symptom.chest_pain")
    assert history and history[0].temporal == "HISTORICAL"
    # Nothing is claimed about the present.
    assert observation is None or observation.temporal != "CURRENT"


def test_hedged_statement_is_uncertain_not_known() -> None:
    state = _state("Hình như tôi hơi khó thở")
    # "hình như" is the hedge here. "hơi" only grades it as mild.
    assert state.status_of("symptom.dyspnea") == "UNCERTAIN"
    # UNCERTAIN must not satisfy a requirement for an affirmed finding.
    assert state.is_affirmed("symptom.dyspnea") is False


def test_resolved_symptom_is_not_active(  ) -> None:
    state = _state("Lúc nãy khó thở, giờ đã hết rồi")
    assert state.status_of("symptom.dyspnea") != "KNOWN" or not state.is_affirmed(
        "symptom.dyspnea"
    )


# --------------------------------------------------------------------------
# §5 Temporal values
# --------------------------------------------------------------------------

def test_two_temperatures_coexist_without_overwriting() -> None:
    state = _state("Sáng nay tôi sốt 39 độ, giờ nhiệt độ còn 37.8")
    key = "vital.temperature_c"
    assert state.value_of(key) == 37.8
    historical = state.historical_values(key)
    assert [item.value for item in historical] == [39.0]
    assert historical[0].temporal_label == "sang nay"
    assert len(state.history_of(key)) == 2


def test_a_decimal_point_is_not_a_clause_boundary() -> None:
    """37.8 must not be truncated to 37 by sentence splitting."""
    state = _state("giờ nhiệt độ còn 37.8")
    assert state.value_of("vital.temperature_c") == 37.8


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("hiện tại tôi đau", "CURRENT"),
        ("bây giờ tôi đau", "CURRENT"),
        ("sáng nay tôi sốt", "HISTORICAL"),
        ("hôm qua tôi đau", "HISTORICAL"),
        ("tuần trước tôi đau", "HISTORICAL"),
        ("lúc nãy tôi đau", "HISTORICAL"),
        ("vừa rồi tôi đau", "HISTORICAL"),
        ("trước khi uống thuốc tôi đau", "BEFORE_MEDICATION"),
        ("sau khi uống thuốc tôi đỡ", "AFTER_MEDICATION"),
        ("sau khi vận động tôi khó thở", "AFTER_EVENT"),
        ("cách đây 3 ngày tôi đau", "RELATIVE"),
        ("tôi bị đau", "UNKNOWN_TIME"),
    ],
)
def test_vietnamese_temporal_expressions(text: str, expected: str) -> None:
    assert read_temporal_context(text).context == expected


def test_clock_time_is_not_read_as_now() -> None:
    """'8 giờ' is a time of day; only a bare 'giờ' means the present."""
    assert read_temporal_context("tôi đau từ 8 giờ").context != "CURRENT"
    assert read_temporal_context("giờ tôi còn đau").context == "CURRENT"


def test_temporal_markers_work_without_diacritics() -> None:
    assert read_temporal_context("sang nay toi sot").context == "HISTORICAL"
    assert read_temporal_context("hien tai toi dau").context == "CURRENT"


# --------------------------------------------------------------------------
# §6 Corrections
# --------------------------------------------------------------------------

def test_correction_replaces_canonical_but_preserves_history() -> None:
    state = CanonicalPatientState()
    state.record("onset_time", "8 giờ", turn_id="t1", raw_span="từ 8 giờ")
    state.record(
        "onset_time",
        "5 giờ",
        turn_id="t2",
        raw_span="thực ra là 5 giờ",
        is_correction=True,
    )
    assert state.value_of("onset_time") == "5 giờ"
    superseded = [item for item in state.history_of("onset_time") if not item.is_active]
    assert [item.value for item in superseded] == ["8 giờ"]
    # The correction links back to what it replaced.
    current = state.observation_of("onset_time")
    assert current is not None and current.corrects == superseded[0].id
    # Exactly one active canonical value.
    assert len(state.facts["onset_time"].active()) == 1


@pytest.mark.parametrize(
    "text",
    [
        "À tôi nhớ nhầm, thực ra là 5 giờ",
        "Không phải vậy, tôi nhầm rồi",
        "Cho tôi sửa lại",
        "Ý tôi là 7 giờ",
    ],
)
def test_correction_markers_are_recognised(text: str) -> None:
    assert is_correction(text) is True


def test_ordinary_statements_are_not_corrections() -> None:
    assert is_correction("Tôi đau ngực từ sáng nay") is False


@pytest.mark.parametrize(
    "key",
    ["severity_score", "onset_time", "age", "medication", "symptom.chest_pain"],
)
def test_correction_applies_to_every_clinical_field_not_just_onset(key: str) -> None:
    state = CanonicalPatientState()
    state.record(key, "first", turn_id="t1")
    state.record(key, "second", turn_id="t2", is_correction=True)
    assert state.value_of(key) == "second"
    assert len(state.facts[key].active()) == 1
    assert len(state.facts[key].superseded()) == 1


def test_correction_of_a_clinically_relevant_fact_flags_reassessment() -> None:
    state = CanonicalPatientState()
    state.record("onset_time", "8 giờ", turn_id="t1")
    state.clear_reassessment_flags()
    state.record("onset_time", "5 giờ", turn_id="t2", is_correction=True)
    assert "onset_time" in state.pending_reassessment_keys


# --------------------------------------------------------------------------
# §7 Contradiction is not a temporal change and not a correction
# --------------------------------------------------------------------------

def test_same_time_conflict_without_retraction_is_a_contradiction() -> None:
    state = CanonicalPatientState()
    state.record("onset_time", "8 giờ", temporal="CURRENT", turn_id="t1")
    state.record("onset_time", "5 giờ", temporal="CURRENT", turn_id="t2")
    assert len(state.unresolved_contradictions()) == 1


def test_a_different_time_is_not_a_contradiction() -> None:
    state = _state("Sáng nay tôi sốt 39 độ, giờ nhiệt độ còn 37.8")
    assert state.unresolved_contradictions() == []


def test_a_retraction_is_not_a_contradiction() -> None:
    state = CanonicalPatientState()
    state.record("onset_time", "8 giờ", temporal="CURRENT", turn_id="t1")
    state.record("onset_time", "5 giờ", temporal="CURRENT", turn_id="t2",
                 is_correction=True)
    assert state.unresolved_contradictions() == []


def test_patient_can_resolve_a_contradiction() -> None:
    state = CanonicalPatientState()
    state.record("onset_time", "8 giờ", temporal="CURRENT", turn_id="t1")
    state.record("onset_time", "5 giờ", temporal="CURRENT", turn_id="t2")
    state.resolve_contradiction("onset_time", "5 giờ", turn_id="t3")
    assert state.unresolved_contradictions() == []
    assert state.value_of("onset_time") == "5 giờ"


# --------------------------------------------------------------------------
# §8 Multi-fact extraction, independent of the open question
# --------------------------------------------------------------------------

def test_one_message_updates_many_fields() -> None:
    state = _state(
        "Tôi 67 tuổi, đau ngực từ sáng, lúc nãy đau lan xuống tay trái, "
        "hơi khó thở và đang uống thuốc huyết áp."
    )
    assert state.value_of("age") == 67
    assert state.status_of("symptom.chest_pain") == "KNOWN"
    assert state.value_of("onset_time")
    # "hơi khó thở" grades the breathlessness as mild; it does not doubt it.
    # Recording it UNCERTAIN made a stated symptom unconfirmable and, in the
    # live audit, unanswerable: the patient was asked what their symptom was
    # three times and then handed off. Genuine hedging is covered below.
    assert state.status_of("symptom.dyspnea") == "KNOWN"
    assert state.value_of("medication")
    # Reported as "lúc nãy", so it is captured but not asserted as current.
    # The stored value keeps the patient's own wording, diacritics included -
    # it reaches the RAG query and the patient-facing summary.
    radiation = state.latest_observation("radiation")
    assert radiation is not None and radiation.value == "tay trái"
    assert state.value_of("radiation") is None


def test_a_genuine_hedge_is_still_uncertain() -> None:
    """Doubt about *whether* a symptom is there stays UNCERTAIN."""
    state = _state("Hình như tôi bị sốt, mà tôi không chắc")
    assert state.status_of("symptom.fever") == "UNCERTAIN"


def test_extraction_does_not_depend_on_the_active_question() -> None:
    """Facts outside the asked slot must still be captured."""
    facts = extract_facts("Tôi 67 tuổi và đang khó thở")
    keys = {fact.key for fact in facts}
    assert "age" in keys
    assert "symptom.dyspnea" in keys


def test_late_information_updates_the_same_state() -> None:
    state = _state(
        "Tôi bị đau ngực",
        *[f"Tôi vẫn thấy khó chịu ({index})" for index in range(13)],
        "À tôi còn khó thở nữa",
    )
    assert state.status_of("symptom.chest_pain") == "KNOWN"
    assert state.status_of("symptom.dyspnea") == "KNOWN"


# --------------------------------------------------------------------------
# §9 Entity linking
# --------------------------------------------------------------------------

def test_repeating_a_symptom_does_not_create_a_duplicate_entity() -> None:
    state = _state("Tôi bị đau đầu", "Đau đầu vẫn còn")
    headaches = [
        entity for entity in state.entities.values() if entity.normalized == "headache"
    ]
    assert len(headaches) == 1
    assert headaches[0].mention_count == 2


def test_anaphoric_reference_attaches_to_the_existing_symptom() -> None:
    state = _state("Tôi bị đau đầu")
    entity = state.find_entity("headache")
    assert entity is not None
    apply_message_to_state(
        state,
        "Cơn đau đó bắt đầu từ tối qua",
        turn_id="turn-10",
    )
    # Linked onto the existing headache rather than starting a second symptom.
    assert state.value_of("headache.onset_time") is not None
    assert len([e for e in state.entities.values() if e.normalized == "headache"]) == 1


@pytest.mark.parametrize(
    "text",
    ["Cơn đau đó bắt đầu tối qua", "Triệu chứng đó vẫn còn", "Cái đó tôi nói lúc nãy"],
)
def test_conversational_references_are_detected(text: str) -> None:
    assert has_anaphoric_reference(text) is True


def test_an_ambiguous_reference_with_no_prior_entity_links_nothing() -> None:
    """Entity linking must not force a match when there is nothing to match."""
    state = CanonicalPatientState()
    apply_message_to_state(state, "Cái đó bắt đầu từ tối qua", turn_id="t1")
    assert state.entities == {}


# --------------------------------------------------------------------------
# §17 Safety invariants
# --------------------------------------------------------------------------

def test_unknown_never_becomes_negated_without_evidence() -> None:
    state = _state("Tôi bị đau đầu", "Tôi mệt", "Không biết nữa")
    assert state.status_of("symptom.chest_pain") == "UNKNOWN"


def test_unknown_never_becomes_known_without_evidence() -> None:
    state = CanonicalPatientState()
    for key in ("age", "severity_score", "onset_time", "medication"):
        assert state.status_of(key) == "UNKNOWN"
        assert state.value_of(key) is None


def test_inference_is_not_patient_reported() -> None:
    state = CanonicalPatientState()
    state.record(
        "symptom.chest_pain", True, status="INFERRED", source="SYSTEM_INFERENCE",
        turn_id="t1",
    )
    observation = state.observation_of("symptom.chest_pain")
    assert observation is not None
    assert observation.source == "SYSTEM_INFERENCE"
    # An inference must not satisfy a check for a patient-asserted finding.
    assert state.is_affirmed("symptom.chest_pain") is False


def test_synthetic_is_not_patient_reported() -> None:
    state = CanonicalPatientState()
    state.record("age", 55, source="SYNTHETIC", turn_id="seed")
    observation = state.observation_of("age")
    assert observation is not None and observation.source == "SYNTHETIC"
    assert state.is_affirmed("age") is False
    # Survives a storage round-trip without being laundered.
    restored = CanonicalPatientState.from_dict(state.to_dict())
    assert restored.observation_of("age").source == "SYNTHETIC"


def test_provenance_survives_a_round_trip_for_every_source() -> None:
    state = CanonicalPatientState()
    for index, source in enumerate(
        [
            "PATIENT_REPORTED",
            "CLINICAL_OBSERVATION",
            "CLINICIAN_ENTERED",
            "SYSTEM_INFERENCE",
            "RAG_EVIDENCE",
            "SYNTHETIC",
        ]
    ):
        state.record(f"fact_{index}", index, source=source, turn_id="t1")
    restored = CanonicalPatientState.from_dict(state.to_dict())
    for index, source in enumerate(
        [
            "PATIENT_REPORTED",
            "CLINICAL_OBSERVATION",
            "CLINICIAN_ENTERED",
            "SYSTEM_INFERENCE",
            "RAG_EVIDENCE",
            "SYNTHETIC",
        ]
    ):
        assert restored.observation_of(f"fact_{index}").source == source


def test_historical_facts_do_not_overwrite_current_facts() -> None:
    state = CanonicalPatientState()
    state.record("vital.temperature_c", 37.0, temporal="CURRENT", turn_id="t1")
    state.record("vital.temperature_c", 39.5, temporal="HISTORICAL", turn_id="t2")
    assert state.value_of("vital.temperature_c") == 37.0


def test_new_clinically_relevant_facts_trigger_reassessment() -> None:
    state = CanonicalPatientState()
    state.record("symptom.dyspnea", True, turn_id="t1")
    assert "symptom.dyspnea" in state.pending_reassessment_keys
    state.clear_reassessment_flags()
    assert state.pending_reassessment_keys == []


def test_observations_are_append_only() -> None:
    state = CanonicalPatientState()
    state.record("onset_time", "8 giờ", turn_id="t1")
    state.record("onset_time", "5 giờ", turn_id="t2", is_correction=True)
    state.record("onset_time", "6 giờ", turn_id="t3", is_correction=True)
    assert len(state.history_of("onset_time")) == 3


# --------------------------------------------------------------------------
# §11 / §18 Versioning and serialization
# --------------------------------------------------------------------------

def test_version_increments_on_every_meaningful_mutation() -> None:
    state = CanonicalPatientState()
    assert state.version == 0
    state.record("age", 67, turn_id="t1")
    assert state.version == 1
    state.record("severity_score", 7, turn_id="t1")
    assert state.version == 2


def test_round_trip_preserves_the_whole_model() -> None:
    original = _state(
        "Tôi 67 tuổi, đau ngực từ sáng",
        "Sáng nay sốt 39 độ, giờ còn 37.8",
    )
    restored = CanonicalPatientState.from_dict(original.to_dict())
    assert restored.version == original.version
    assert restored.value_of("age") == 67
    assert restored.value_of("vital.temperature_c") == 37.8
    assert len(restored.historical_values("vital.temperature_c")) == 1
    assert restored.entities.keys() == original.entities.keys()


@pytest.mark.parametrize("payload", [None, {}, {"facts": None}, {"garbage": 1}, []])
def test_legacy_or_corrupt_payloads_deserialize_to_unknown_not_to_values(
    payload: object,
) -> None:
    """Old rows must not crash, and must not resolve to clinical negatives."""
    state = CanonicalPatientState.from_dict(payload)  # type: ignore[arg-type]
    assert state.status_of("symptom.chest_pain") == "UNKNOWN"
    assert state.value_of("severity_score") is None
    assert state.version == 0


def test_unreadable_observation_defaults_to_the_safe_source() -> None:
    """A stored observation missing its provenance must not claim the patient."""
    state = CanonicalPatientState.from_dict(
        {"facts": {"age": {"key": "age", "observations": [{"value": 40}]}}}
    )
    observation = state.observation_of("age")
    assert observation is not None
    assert observation.source != "PATIENT_REPORTED"
    assert state.is_affirmed("age") is False
