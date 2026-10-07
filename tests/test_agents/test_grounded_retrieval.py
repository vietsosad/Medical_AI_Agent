"""Retrieval asks the corpus about this patient, in the corpus's own language.

The observed failure: cases labelled "55% tương đồng" that were visibly about
something else. Three causes, each pinned down here:

* the query was a Vietnamese summary the English corpora could not match well;
* one averaged vector stood in for the whole case, so it was moderately close
  to everything and specific to nothing;
* a retriever asked for five results returned five whatever it found, and the
  UI rendered a cosine distance as though it were a confidence.

The measured effect of fixing the first two is in
``eval/results/retrieval_report.md``. What is asserted here is the behaviour
that must hold regardless of how the numbers move.
"""

from __future__ import annotations

from typing import Any

import pytest

from src.agents.canonical_state import CanonicalPatientState
from src.agents.clinical_state_view import ClinicalStateView
from src.agents.nodes.fact_extraction import apply_message_to_state
from src.agents.problem_state import build_problem_state
from src.services.rag.clinical_query_planner import (
    build_deterministic_queries,
    validate_grounding,
)
from src.services.rag.hybrid_retrieval import (
    ChannelHit,
    FusedCandidate,
    apply_relevance_floor,
    deterministic_relevance,
    fuse,
)


def _plan(*messages: str):
    state = CanonicalPatientState()
    for index, message in enumerate(messages):
        apply_message_to_state(state, message, turn_id=f"t{index + 1}")
    return build_deterministic_queries(
        build_problem_state(ClinicalStateView(state))
    )


# ---------------------------------------------------------------------------
# Query generation
# ---------------------------------------------------------------------------


def test_the_query_is_clinical_english_not_the_vietnamese_message() -> None:
    plan = _plan("Tôi bị đau đầu và buồn nôn", "Đau từ sáng nay, khoảng 6/10")

    assert "headache" in plan.primary
    assert "nausea" in plan.associated
    assert "moderate" in plan.overall
    assert "since this morning" in plan.overall
    # Nothing Vietnamese survives into the query the corpus is searched with.
    for _, query in plan.queries():
        assert "đau" not in query
        assert "buồn nôn" not in query


def test_slang_and_unaccented_typing_still_produce_a_clinical_query() -> None:
    """"nhuc dau qua, chong mat" is how a lot of patients actually type."""
    plan = _plan("nhuc dau qua, chong mat")

    assert "headache" in plan.primary
    assert "dizziness" in plan.associated


def test_one_case_produces_several_scoped_queries() -> None:
    plan = _plan("Tôi đau ngực dữ dội từ 30 phút trước, vã mồ hôi")
    names = {name for name, _ in plan.queries()}

    assert {"overall", "primary", "associated"} <= names
    # Each asks a different question of the corpus rather than repeating one.
    texts = [query for _, query in plan.queries()]
    assert len(set(texts)) == len(texts)


def test_a_denied_symptom_is_recorded_as_denied_not_searched_for() -> None:
    plan = _plan("Tôi bị khó thở, không đau ngực")

    assert "denies chest pain" in plan.overall
    # The keyword channel has no notion of negation, so a denial must never
    # reach it: "denies chest pain" as keywords retrieves chest-pain cases.
    assert "chest" not in plan.lexical_terms
    assert "pain" not in plan.lexical_terms


def test_a_query_naming_something_the_patient_never_said_is_rejected() -> None:
    """The grounding check is deterministic and reads no justification."""
    facts = {
        "age_band": "adult",
        "concepts": ["headache"],
        "denied_concepts": [],
        "vitals": {},
        "severity": 6,
        "onset": "since this morning",
        "course": "",
        "character": "",
    }

    grounded = validate_grounding(
        "adult patient with moderate headache since this morning", facts
    )
    invented_symptom = validate_grounding(
        "adult patient with moderate headache and chest pain", facts
    )
    invented_number = validate_grounding(
        "adult patient with headache temperature 39", facts
    )
    diagnosis = validate_grounding(
        "adult patient with headache suggesting subarachnoid bleed", facts
    )

    assert grounded == []
    assert any(item.startswith("ungrounded_term:chest") for item in invented_symptom)
    assert any(item.startswith("ungrounded_number:39") for item in invented_number)
    assert any(item.startswith("diagnosis_term:") for item in diagnosis)


def test_a_case_with_no_canonical_complaint_produces_no_query() -> None:
    """Retrieval declines to guess rather than searching for nothing."""
    plan = _plan("chào bạn")

    assert plan.primary == ""
    assert plan.queries() == []
    assert "NO_GROUNDED_PRIMARY_CONCEPT" in plan.degraded_modes


# ---------------------------------------------------------------------------
# Fusion
# ---------------------------------------------------------------------------


def test_fusion_combines_ranks_not_incomparable_scores() -> None:
    """A cosine similarity and a ts_rank are not on the same scale."""
    fused = fuse(
        {
            "dense:overall": [
                {"doc_id": "a", "text": "a", "score": 0.61},
                {"doc_id": "b", "text": "b", "score": 0.59},
            ],
            "lexical:overall": [
                {"doc_id": "b", "text": "b", "score": 0.004},
                {"doc_id": "c", "text": "c", "score": 0.001},
            ],
        }
    )
    by_id = {item.doc_id: item for item in fused}

    # b is the only document both channels returned, so it leads despite
    # having the lower raw dense score and a tiny lexical one.
    assert fused[0].doc_id == "b"
    assert by_id["b"].channels == ["dense:overall", "lexical:overall"]
    assert by_id["c"].best_dense_score is None


def test_the_overall_query_outweighs_a_bare_symptom_query() -> None:
    """A bare "headache" matches every headache; the presentation does not."""
    fused = fuse(
        {
            "dense:overall": [{"doc_id": "specific", "text": "", "score": 0.6}],
            "dense:primary": [{"doc_id": "generic", "text": "", "score": 0.9}],
        }
    )

    assert fused[0].doc_id == "specific"


# ---------------------------------------------------------------------------
# Relevance and suppression
# ---------------------------------------------------------------------------


def _candidate(doc_id: str, text: str, **metadata: Any) -> FusedCandidate:
    return FusedCandidate(doc_id=doc_id, text=text, metadata=metadata)


def test_a_case_sharing_the_presentation_scores_above_one_that_does_not() -> None:
    matching = _candidate(
        "match",
        "A 44-year-old with headache and nausea since this morning.",
        symptom_concepts=["headache", "nausea"],
    )
    unrelated = _candidate(
        "unrelated",
        "A 61-year-old presenting for a routine dressing change.",
        symptom_concepts=["wound"],
    )

    matched_score, _ = deterministic_relevance(
        matching, grounded_concepts=("headache", "nausea")
    )
    unrelated_score, _ = deterministic_relevance(
        unrelated, grounded_concepts=("headache", "nausea")
    )

    assert matched_score > unrelated_score
    assert unrelated_score < 0.3


def test_an_unlabelled_case_is_scored_from_its_text_not_written_off() -> None:
    """1,347 corpus rows carry no concept list. That is not "nothing in common"."""
    candidate = _candidate(
        "no-concepts",
        "A 30-year-old male with severe headache and nausea after a fall.",
    )

    score, _ = deterministic_relevance(
        candidate, grounded_concepts=("headache", "nausea")
    )

    assert score > 0.5


def test_agreement_between_channels_counts_as_evidence() -> None:
    text = "A 44-year-old with headache and nausea."
    dense_only = _candidate("dense", text, symptom_concepts=["headache", "nausea"])
    dense_only.hits = [ChannelHit("dense:overall", 1, 0.6)]
    both = _candidate("both", text, symptom_concepts=["headache", "nausea"])
    both.hits = [ChannelHit("dense:overall", 1, 0.6), ChannelHit("lexical:overall", 1, 0.01)]

    dense_score, _ = deterministic_relevance(
        dense_only, grounded_concepts=("headache", "nausea")
    )
    both_score, _ = deterministic_relevance(
        both, grounded_concepts=("headache", "nausea")
    )

    assert both_score > dense_score


def test_showing_no_case_is_preferred_to_showing_an_unrelated_one() -> None:
    """Top-K is not relevance. A retriever asked for five always finds five."""
    candidates = [
        _candidate(f"weak-{index}", "unrelated presentation") for index in range(5)
    ]
    for candidate in candidates:
        candidate.relevance = 0.1

    kept = apply_relevance_floor(candidates, minimum=0.3, max_shown=3)

    assert kept == []


def test_the_shown_list_is_capped_and_ordered_by_relevance() -> None:
    candidates = []
    for index, relevance in enumerate((0.4, 0.9, 0.7, 0.6, 0.5)):
        candidate = _candidate(f"case-{index}", "text")
        candidate.relevance = relevance
        candidates.append(candidate)

    kept = apply_relevance_floor(candidates, minimum=0.3, max_shown=3)

    assert [item.relevance for item in kept] == [0.9, 0.7, 0.6]


# ---------------------------------------------------------------------------
# Presentation contract
# ---------------------------------------------------------------------------


def test_case_support_carries_its_own_esi_label_and_never_the_patients() -> None:
    from src.api.routes_patient import _case_support_dtos

    dtos = _case_support_dtos(
        [
            {
                "case_id": "mietic_c_1",
                "presentation_excerpt": "headache with nausea",
                "excerpt": "headache with nausea",
                "retrieval_relevance": 0.82,
                "relevance_band": "HIGH",
                "validated_esi_level": 3,
                "candidate_esi_levels": [3],
                "label_status": "CONSISTENT",
                "age_band": "adult",
                "sex": "female",
                "symptom_concepts": ["headache", "nausea"],
                "retrieval_scope": "CASE_SUPPORT",
                "authority_status": "NOT_PROTOCOL",
            }
        ]
    )

    assert len(dtos) == 1
    case = dtos[0]
    assert case.validatedEsiLevel == 3
    assert case.labelStatus == "CONSISTENT"
    assert case.relevanceBand == "HIGH"
    # The authority boundary is a property of the DTO's type, not of a prompt.
    assert case.authorityStatus == "NOT_PROTOCOL"
    assert case.retrievalScope == "CASE_SUPPORT"


def test_an_unknown_case_label_stays_unknown() -> None:
    """Candidate levels are competing answers, never resolved into one."""
    from src.api.routes_patient import _case_support_dtos

    dtos = _case_support_dtos(
        [
            {
                "case_id": "mietic_c_2",
                "excerpt": "abdominal pain",
                "validated_esi_level": None,
                "candidate_esi_levels": [1, 2, 5],
                "label_status": "UNKNOWN",
                "retrieval_scope": "CASE_SUPPORT",
                "authority_status": "NOT_PROTOCOL",
            }
        ]
    )

    assert dtos[0].validatedEsiLevel is None
    assert dtos[0].labelStatus == "UNKNOWN"
    assert dtos[0].candidateEsiLevels == [1, 2, 5]


@pytest.mark.parametrize(
    ("score", "band"),
    [(0.9, "HIGH"), (0.6, "MODERATE"), (0.2, "LOW"), (None, "UNKNOWN")],
)
def test_relevance_is_banded_rather_than_shown_as_a_percentage(
    score: float | None,
    band: str,
) -> None:
    """A cosine similarity is not a confidence and must not read like one."""
    from src.agents.nodes.evidence_gate import _relevance_band

    assert _relevance_band(score) == band
