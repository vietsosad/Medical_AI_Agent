"""Severity is a reported score, never a digit harvested from another fact."""

from __future__ import annotations

import pytest

from src.agents.nodes.answer_validator import validate_answer_alignment
from src.agents.nodes.intake_analyzer import extract_blueprint_deterministically
from src.agents.nodes.severity_extraction import extract_severity_score

SEVERITY_QUESTION = {"field": "severity_score", "question_id": "severity_score"}


def _blueprint(query: str, active_question: dict | None = None) -> dict:
    return extract_blueprint_deterministically(query, {}, active_question, "NOT_APPLICABLE")


# --- Fabrication: digits belonging to another measurement -------------------

@pytest.mark.parametrize(
    "query",
    [
        "Tôi 67 tuổi, đau ngực từ sáng",
        "Tôi 45 tuổi bị đau đầu",
        "Tôi đau ngực, huyết áp 150/90",
        "Đau bụng 3 ngày nay",
        "Tôi uống 2 viên thuốc",
        "Đau đầu từ 8 giờ sáng",
        "Tôi nặng 70 kg và đang đau lưng",
        "Sốt 39 độ kèm đau người",
        "Mạch 110 lần/phút, tôi thấy đau ngực",
    ],
)
def test_unrelated_numbers_never_become_severity(query: str) -> None:
    assert extract_severity_score(query).score is None
    assert _blueprint(query)["severity_score"] is None


def test_unrelated_number_stays_unknown_even_while_scale_question_is_open() -> None:
    """An off-topic reply must not be scored just because the slider is showing."""
    assert _blueprint("Đau bụng 3 ngày nay", SEVERITY_QUESTION)["severity_score"] is None
    assert _blueprint("Tôi 67 tuổi", SEVERITY_QUESTION)["severity_score"] is None


# --- Genuine patient-reported scores ---------------------------------------

@pytest.mark.parametrize(
    ("query", "expected"),
    [
        ("Tôi đau 7/10", 7),
        ("Đau 10/10", 10),
        ("Mức độ đau khoảng 6 trên 10", 6),
        ("Cơn đau 8 điểm", 8),
        ("Mức độ 5", 5),
        ("Thang điểm 9", 9),
        ("toi dau 7/10", 7),
        ("muc do dau khoang 4 tren 10", 4),
    ],
)
def test_explicit_pain_scores_are_extracted(query: str, expected: int) -> None:
    assert extract_severity_score(query).score == expected
    assert _blueprint(query)["severity_score"] == expected


@pytest.mark.parametrize(("query", "expected"), [("7", 7), ("10", 10), ("0", 0)])
def test_scale_widget_answer_still_works(query: str, expected: int) -> None:
    """The 0-10 slider submits a bare number; that path must not regress."""
    assert _blueprint(query, SEVERITY_QUESTION)["severity_score"] == expected


@pytest.mark.parametrize(
    ("query", "expected"),
    [("Đau nhẹ thôi", 2), ("Đau vừa", 5), ("Đau nặng", 8), ("Đau dữ dội", 9), ("Không đau", 0)],
)
def test_verbal_intensity_answers_the_open_scale_question(query: str, expected: int) -> None:
    assert _blueprint(query, SEVERITY_QUESTION)["severity_score"] == expected


def test_verbal_intensity_alone_is_not_scored_in_free_narrative() -> None:
    """"đau nặng" in a story is not a reported 0-10 score."""
    assert extract_severity_score("Tôi bị đau nặng ở lưng").score is None


# --- UNKNOWN is preserved, never defaulted ---------------------------------

def test_zero_is_a_real_answer_and_is_distinct_from_unknown() -> None:
    scored = _blueprint("0", SEVERITY_QUESTION)["severity_score"]
    unknown = _blueprint("Tôi đau ngực")["severity_score"]
    assert scored == 0
    assert unknown is None
    assert scored is not None  # 0 must never be read as "not collected"


def test_missing_severity_is_none_not_zero() -> None:
    assert _blueprint("Tôi khó thở từ hôm qua")["severity_score"] is None


# --- Downstream contract ----------------------------------------------------

def test_extraction_records_the_evidence_that_justified_the_score() -> None:
    assert extract_severity_score("Tôi đau 7/10").evidence == "explicit_pain_score"
    assert extract_severity_score("7", severity_question_active=True).evidence == (
        "answer_to_scale_question"
    )


def test_answer_validator_agrees_with_the_extractor() -> None:
    """Alignment and extraction must not drift apart."""
    assert validate_answer_alignment("7", SEVERITY_QUESTION).alignment == "DIRECT_ANSWER"
    assert validate_answer_alignment("Đau 8/10", SEVERITY_QUESTION).alignment == "DIRECT_ANSWER"
    assert validate_answer_alignment("Đau bụng 3 ngày nay", SEVERITY_QUESTION).alignment != (
        "DIRECT_ANSWER"
    )


def test_readiness_still_asks_for_severity_when_it_is_unknown() -> None:
    """The fix must not silently satisfy the readiness gate.

    EXPECTATION UPDATED: readiness now selects its requirement profile from
    canonical state alone, so the case has to carry canonical evidence of chest
    pain before the chest-pain requirements apply. The original intent - a
    fabricated-then-removed severity must leave the gate open - is unchanged.
    """
    from src.agents.canonical_state import CanonicalPatientState
    from src.agents.clinical_state_view import ClinicalStateView
    from src.agents.nodes.fact_extraction import apply_message_to_state
    from src.agents.nodes.readiness_evaluator import evaluate_readiness

    message = "Tôi 67 tuổi, đang đau ngực từ sáng nay"
    canonical = CanonicalPatientState()
    apply_message_to_state(canonical, message, turn_id="t1")

    evaluation = evaluate_readiness(
        _blueprint(message),
        view=ClinicalStateView(canonical),
        vital_signs_status="UNAVAILABLE_CONFIRMED",
    )
    assert evaluation.symptom_cluster == "chest_pain"
    assert "severity_score" in evaluation.missing_critical_fields


def test_readiness_will_not_classify_a_presentation_without_canonical_evidence() -> None:
    """A blueprint alone must not select a clinical requirement profile."""
    from src.agents.nodes.readiness_evaluator import evaluate_readiness

    evaluation = evaluate_readiness(_blueprint("Tôi 67 tuổi, đau ngực từ sáng nay"))
    assert evaluation.symptom_cluster is None
    assert evaluation.ready is False


def test_rag_query_omits_severity_when_unknown() -> None:
    """A fabricated score used to poison the retrieval query."""
    from src.agents.nodes.bilingual_query_builder import build_retrieval_queries

    bundle = build_retrieval_queries(_blueprint("Tôi 67 tuổi, đau ngực"))
    assert "mức độ" not in bundle.query_vi
    assert "severity" not in bundle.query_en
