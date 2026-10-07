"""Every clinical decision must read the same canonical truth.

These tests cover the query layer and the invariants of §19: what readiness,
retrieval and the reasoner are allowed to conclude from canonical state.
"""

from __future__ import annotations

import pytest

from src.agents.blueprint_projection import ingest_blueprint, project_blueprint
from src.agents.canonical_state import CanonicalPatientState
from src.agents.clinical_state_view import ClinicalStateView
from src.agents.confirmation_lifecycle import fact_snapshot
from src.agents.nodes.fact_extraction import apply_message_to_state


def _view(*messages: str) -> ClinicalStateView:
    state = CanonicalPatientState()
    for index, message in enumerate(messages):
        apply_message_to_state(state, message, turn_id=f"turn-{index + 1}")
    return ClinicalStateView(state)


# --------------------------------------------------------------------------
# §4 semantic rules, read through the view every consumer uses
# --------------------------------------------------------------------------

def test_unknown_and_negated_are_different_answers() -> None:
    silent = _view("Tôi bị đau đầu")
    denied = _view("Tôi không đau ngực")

    assert silent.is_unknown("symptom.chest_pain") is True
    assert silent.is_negated("symptom.chest_pain") is False
    assert denied.is_negated("symptom.chest_pain") is True
    assert denied.is_unknown("symptom.chest_pain") is False


def test_negated_is_not_absent_by_default() -> None:
    view = _view("Tôi không đau ngực")
    # It was answered, so it is not an open question.
    assert view.is_unknown("symptom.chest_pain") is False
    assert "chest_pain" in view.negated_symptoms()
    assert "chest_pain" not in view.present_symptoms()


def test_historical_is_not_current() -> None:
    view = _view("Tuần trước tôi bị đau ngực")
    assert view.is_present("symptom.chest_pain") is False
    assert view.is_unknown("symptom.chest_pain") is True
    assert "chest_pain" in view.historical_symptoms()
    assert "chest_pain" not in view.present_symptoms()


def test_current_symptom_is_present() -> None:
    view = _view("Bây giờ tôi đau ngực")
    assert view.is_present("symptom.chest_pain") is True
    assert "chest_pain" in view.present_symptoms()


def test_uncertain_is_not_known() -> None:
    view = _view("Hình như tôi hơi khó thở")
    assert view.is_uncertain("symptom.dyspnea") is True
    assert view.is_present("symptom.dyspnea") is False
    assert "dyspnea" not in view.present_symptoms()
    assert "dyspnea" in view.uncertain_symptoms()


def test_inferred_is_not_patient_reported() -> None:
    state = CanonicalPatientState()
    state.record(
        "symptom.chest_pain", True, status="INFERRED", source="SYSTEM_INFERENCE",
        turn_id="t1",
    )
    view = ClinicalStateView(state)
    assert view.is_inferred("symptom.chest_pain") is True
    assert view.is_present("symptom.chest_pain") is False
    assert view.is_patient_asserted("symptom.chest_pain") is False


def test_synthetic_is_not_patient_reported() -> None:
    state = CanonicalPatientState()
    state.record("age", 55, source="SYNTHETIC", turn_id="seed")
    view = ClinicalStateView(state)
    assert view.is_patient_asserted("age") is False
    assert view.read("age").source == "SYNTHETIC"


def test_a_case_is_not_clustered_by_a_historical_symptom() -> None:
    """Chest pain last week must not put the case on the chest-pain profile."""
    assert _view("Tuần trước tôi đau ngực").symptom_cluster() != "chest_pain"
    assert _view("Bây giờ tôi đau ngực").symptom_cluster() == "chest_pain"


def test_temporal_vital_reads_the_current_value() -> None:
    view = _view("Sáng nay tôi sốt 39 độ, giờ nhiệt độ còn 37.8")
    assert view.current_value("vital.temperature_c") == 37.8
    assert [item.value for item in view.historical_values("vital.temperature_c")] == [
        39.0
    ]


# --------------------------------------------------------------------------
# §3 query surface
# --------------------------------------------------------------------------

def test_observations_for_an_entity_are_retrievable() -> None:
    view = _view("Tôi bị đau đầu", "Cơn đau đó bắt đầu từ tối qua")
    observations = view.observations_for("headache")
    assert observations


def test_recent_events_are_ordered_and_bounded() -> None:
    view = _view("Tôi đau ngực", "Tôi khó thở", "Tôi buồn nôn")
    events = view.recent_events(limit=2)
    assert len(events) == 2


# --------------------------------------------------------------------------
# §12 / §19 blueprint may not become an independent source of truth
# --------------------------------------------------------------------------

def test_denied_symptom_never_survives_the_projection_as_a_complaint() -> None:
    """The invariant: NEGATED must not appear as a positive current symptom."""
    state = CanonicalPatientState()
    apply_message_to_state(state, "Tôi không đau ngực", turn_id="t1")
    # A stale/legacy blueprint wrongly listing it as a complaint.
    stale = {"chief_complaint": ["đau ngực"], "associated_symptoms": ["đau ngực"]}

    projected = project_blueprint(state, stale)

    assert "đau ngực" not in projected["chief_complaint"]
    assert "đau ngực" not in projected["associated_symptoms"]


def test_projection_keeps_an_affirmed_symptom() -> None:
    """Complaints reach the projection only by being ingested into canonical.

    EXPECTATION UPDATED: the projection no longer reads complaints out of the
    legacy dict at all. Passing a phrase in through ``legacy`` is not enough;
    it has to become a canonical fact first. That is the boundary that stops a
    stale blueprint from feeding clinical output.
    """
    state = CanonicalPatientState()
    apply_message_to_state(state, "Tôi đang đau ngực", turn_id="t1")
    ingest_blueprint(state, {"chief_complaint": ["đau ngực"]}, turn_id="t1")
    projected = project_blueprint(state, {})
    assert "đau ngực" in projected["chief_complaint"]


def test_an_uningested_legacy_complaint_cannot_reach_the_projection() -> None:
    """The same boundary, stated as the invariant it protects."""
    state = CanonicalPatientState()
    projected = project_blueprint(state, {"chief_complaint": ["đau ngực"]})
    assert projected["chief_complaint"] == []


def test_projected_scalars_come_from_canonical_not_from_the_legacy_dict() -> None:
    state = CanonicalPatientState()
    state.record("onset_time", "5 giờ", turn_id="t1")
    state.record("severity_score", 8, turn_id="t1")
    # Legacy values disagree; canonical must win.
    projected = project_blueprint(
        state, {"onset_time": "8 giờ", "severity_score": 2}
    )
    assert projected["onset_time"] == "5 giờ"
    assert projected["severity_score"] == 8


def test_primary_problem_scoped_scalars_project_to_generic_blueprint() -> None:
    """Adaptive headache answers must not be re-asked as generic slots.

    The adaptive planner records attributed answers such as
    ``headache.onset_time``.  The evidence reasoner still asks about generic
    targets such as ``onset_time``.  For the primary complaint those names refer
    to the same patient answer, so the read-model has to bridge them.
    """
    state = CanonicalPatientState()
    state.record("symptom.headache", True, turn_id="t1")
    state.record(
        "headache.onset_time",
        "vừa mới bị đau",
        turn_id="t2",
        note="answer_to_adaptive_question",
    )
    state.record(
        "headache.severity_score",
        4,
        turn_id="t3",
        note="answer_to_adaptive_question",
    )

    projected = project_blueprint(state, {})

    assert projected["onset_time"] == "vừa mới bị đau"
    assert projected["severity_score"] == 4


def test_confirmation_snapshot_includes_problem_scoped_clinical_facts() -> None:
    state = CanonicalPatientState()
    state.record("symptom.headache", True, turn_id="t1")
    state.record("headache.onset_time", "vừa mới bị đau", turn_id="t2")
    state.record("headache.severity_score", 4, turn_id="t3")
    snapshot = fact_snapshot(ClinicalStateView(state))

    assert snapshot["headache.onset_time"] == ["KNOWN", "vừa mới bị đau"]
    assert snapshot["headache.severity_score"] == ["KNOWN", 4]


def test_a_correction_propagates_into_the_projection() -> None:
    state = CanonicalPatientState()
    state.record("onset_time", "8 giờ", turn_id="t1")
    state.record("onset_time", "5 giờ", turn_id="t2", is_correction=True)
    assert project_blueprint(state, {"onset_time": "8 giờ"})["onset_time"] == "5 giờ"


def test_projection_preserves_fields_canonical_does_not_own() -> None:
    state = CanonicalPatientState()
    legacy = {
        "vital_signs": {"spo2": 97},
        "recent_procedure": "mổ ruột thừa",
        "clinical_keywords_en": ["chest pain"],
        "vital_signs_source": "máy đo tại nhà",
    }
    projected = project_blueprint(state, legacy)
    assert projected["vital_signs"] == {"spo2": 97}
    assert projected["recent_procedure"] == "mổ ruột thừa"
    assert projected["clinical_keywords_en"] == ["chest pain"]
    assert projected["vital_signs_source"] == "máy đo tại nhà"


def test_unknown_projects_to_none_never_to_a_value() -> None:
    projected = project_blueprint(CanonicalPatientState(), {})
    assert projected["onset_time"] is None
    assert projected["severity_score"] is None
    assert projected["chief_complaint"] == []


# --------------------------------------------------------------------------
# §13 reasoner input carries explicit semantics
# --------------------------------------------------------------------------

def test_reasoner_payload_separates_the_five_semantic_categories() -> None:
    view = _view(
        "Bây giờ tôi đau ngực",
        "Tôi không khó thở",
        "Hình như tôi hơi chóng mặt",
        "Tuần trước tôi bị đau đầu",
    )
    payload = view.to_reasoner_payload()

    assert "chest_pain" in payload["current_symptoms"]
    assert "dyspnea" in payload["explicitly_denied_symptoms"]
    assert "dizziness" in payload["uncertain_symptoms"]
    assert "headache" in payload["historical_only_symptoms"]
    assert isinstance(payload["not_asked_or_unknown"], list)


def test_reasoner_payload_never_lists_a_denied_symptom_as_current() -> None:
    payload = _view("Tôi không đau ngực").to_reasoner_payload()
    assert "chest_pain" not in payload["current_symptoms"]
    assert "chest_pain" in payload["explicitly_denied_symptoms"]


def test_reasoner_payload_never_lists_a_historical_symptom_as_current() -> None:
    payload = _view("Tuần trước tôi đau ngực").to_reasoner_payload()
    assert "chest_pain" not in payload["current_symptoms"]
    assert "chest_pain" in payload["historical_only_symptoms"]


def test_reasoner_payload_states_that_unknown_is_not_absence() -> None:
    """The model must be told explicitly, not left to infer it."""
    payload = _view("Tôi đau ngực").to_reasoner_payload()
    note = payload["provenance_note"]
    assert "does NOT" in note
    assert "unknown" in note.lower()


def test_reasoner_payload_uses_current_vitals_not_historical() -> None:
    payload = _view("Sáng nay tôi sốt 39 độ, giờ nhiệt độ còn 37.8").to_reasoner_payload()
    assert payload["current_vitals"]["temperature_c"] == 37.8
    assert payload["historical_observations"]["vital.temperature_c"][0]["value"] == 39.0


@pytest.mark.parametrize("payload", [None, {}, {"canonical_state": None}])
def test_view_tolerates_legacy_agent_state(payload: object) -> None:
    view = ClinicalStateView.from_agent_state(payload or {})  # type: ignore[arg-type]
    assert view.is_unknown("symptom.chest_pain") is True
    assert view.present_symptoms() == []
    assert view.to_reasoner_payload()["current_symptoms"] == []
