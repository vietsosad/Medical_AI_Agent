"""Patient-UI answer hints (src/simple_agent/answer_hints.py).

Display-only data: these tests pin the shape the chat's quick replies and
"Mình đã ghi nhận" panel read, against the real corpus bundle.
"""

from __future__ import annotations

import pytest

from src.simple_agent.answer_hints import question_input, recorded_facts, recorded_symptoms
from src.simple_agent.session import Session
from src.simple_agent.sql_bundle_corpus import load_corpus_from_sql_bundle


@pytest.fixture(scope="module")
def corpus():
    return load_corpus_from_sql_bundle()


def _yes_no_target(corpus) -> str:
    return next(
        fact["fact_target_id"]
        for fact in corpus.fact_targets
        if fact["value_schema"].get("type") == "enum"
        and set(fact["value_schema"].get("allowed_values") or []) == {"YES", "NO", "UNKNOWN"}
    )


def test_yes_no_question_offers_yes_no(corpus):
    assert question_input(corpus, "ASK_NEXT", _yes_no_target(corpus)) == {"kind": "YES_NO"}


def test_pain_scale_question_offers_zero_to_ten(corpus):
    assert question_input(corpus, "ASK_NEXT", "fact_target:pain_severity") == {"kind": "SCALE_0_10"}


def test_measurement_and_unlabelled_enum_stay_free_text(corpus):
    assert question_input(corpus, "ASK_NEXT", "fact_target:temperature") is None
    side_target = next(
        fact["fact_target_id"]
        for fact in corpus.fact_targets
        if "LEFT" in (fact["value_schema"].get("allowed_values") or [])
    )
    assert question_input(corpus, "ASK_NEXT", side_target) is None


def test_confirmation_offers_confirm_and_outcomes_offer_nothing(corpus):
    assert question_input(corpus, "ASK_CONFIRMATION", None) == {"kind": "CONFIRM"}
    assert question_input(corpus, "RETURN_MATCH", "fact_target:pain_severity") is None
    assert question_input(corpus, "ASK_NEXT", None) is None
    assert question_input(corpus, "ASK_NEXT", "fact_target:does_not_exist") is None


def test_recorded_facts_keep_order_and_hide_clinician_only(corpus):
    session = Session()
    session.facts = {
        "fact_target:pain_severity": 7,
        "fact_target:resource_count": 2,
        "fact_target:temperature": 38.2,
    }
    assert recorded_facts(corpus, session) == [
        {"fact_target_id": "fact_target:pain_severity", "name": "Mức độ đau", "value": 7},
        {"fact_target_id": "fact_target:temperature", "name": "Nhiệt độ cơ thể", "value": 38.2},
    ]


def test_recorded_symptoms_skip_negated_and_duplicates(corpus):
    session = Session()
    session.concepts = {"concept:spinal_pain"}
    session.concept_order = ["concept:spinal_pain", "concept:spinal_pain", "concept:not_asserted"]
    assert recorded_symptoms(corpus, session) == [
        {"concept_id": "concept:spinal_pain", "label": "Đau cột sống"},
    ]
