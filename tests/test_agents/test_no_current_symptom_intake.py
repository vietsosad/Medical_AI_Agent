from __future__ import annotations

from src.agents.blueprint_projection import ingest_blueprint, project_blueprint
from src.agents.canonical_state import CanonicalPatientState
from src.agents.nodes.intake_analyzer import extract_blueprint_deterministically


def test_no_current_symptom_answer_is_not_promoted_to_chief_complaint() -> None:
    blueprint = extract_blueprint_deterministically(
        "tôi không bị khó chịu gì hết",
        {"chief_complaint": []},
        {"field": "chief_complaint"},
        "DIRECT_ANSWER",
    )

    assert blueprint["chief_complaint"] == []


def test_no_pain_or_symptom_answer_is_not_promoted_to_chief_complaint() -> None:
    blueprint = extract_blueprint_deterministically(
        "tôi không bị đau đớn hay triệu chứng gì hết mà",
        {"chief_complaint": []},
        {"field": "chief_complaint"},
        "DIRECT_ANSWER",
    )

    assert blueprint["chief_complaint"] == []


def test_no_current_symptom_legacy_phrase_is_not_projected_as_complaint() -> None:
    canonical = CanonicalPatientState()
    legacy = {"chief_complaint": ["tôi không bị khó chịu gì hết"]}

    ingest_blueprint(canonical, legacy, turn_id="t-no-symptom")
    projected = project_blueprint(canonical, legacy)

    assert projected["chief_complaint"] == []


def test_legacy_cut_no_pain_phrase_is_not_projected_as_complaint() -> None:
    canonical = CanonicalPatientState()
    legacy = {"chief_complaint": ["đau đớn gì hết"]}

    ingest_blueprint(canonical, legacy, turn_id="t-no-pain")
    projected = project_blueprint(canonical, legacy)

    assert projected["chief_complaint"] == []
