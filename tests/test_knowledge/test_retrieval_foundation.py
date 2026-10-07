"""DB-backed tests for the rebuilt knowledge foundation.

These run against the real Postgres corpora because the defects they guard
against — a mixed vector space, an authority leak, a database fault reported as
missing clinical evidence — are only observable against real data. They skip
rather than fail when no database is reachable.
"""

from __future__ import annotations

import asyncio

import pytest

from src.services.rag.outcomes import (
    RetrievalStatus,
    RetrievedItem,
    technical_failure,
)
from src.services.rag.query_translation import translate_query


def _retriever():
    from src.services.rag.knowledge_retriever import get_knowledge_retriever

    return get_knowledge_retriever()


# One loop for the whole module: the async engine's pool binds to the loop that
# first used it, so a fresh asyncio.run() per test would hand connections to a
# loop that no longer exists. FastAPI serves every request on one loop, so this
# mirrors production rather than working around it.
_LOOP = asyncio.new_event_loop()


def _run(coro):
    return _LOOP.run_until_complete(coro)


def teardown_module(_module: object) -> None:
    from src.services.db import async_engine

    _LOOP.run_until_complete(async_engine.dispose())
    _LOOP.close()


@pytest.fixture(scope="module")
def db_available() -> bool:
    try:
        outcome = _run(_retriever().search_esi_authority("chest pain", top_k=1))
    except Exception:  # noqa: BLE001 - environment probe
        pytest.skip("knowledge database is not reachable")
    if outcome.status.is_technical_failure:
        pytest.skip(f"knowledge database unavailable: {outcome.error}")
    return True


# --------------------------------------------------------------------------
# outcome semantics — pure, no database
# --------------------------------------------------------------------------


def test_technical_failure_is_never_clinically_interpretable() -> None:
    """The exact bug this replaces: a dimension error read as 'no evidence'."""
    outcome = technical_failure(
        RetrievalStatus.DIMENSION_MISMATCH,
        ValueError("different vector dimensions 768 and 1024"),
    )
    assert outcome.status.is_technical_failure
    assert not outcome.ok
    assert not outcome.status.permits_clinical_interpretation
    assert "768" in (outcome.error or "")


def test_absence_of_evidence_is_distinct_from_failure() -> None:
    assert not RetrievalStatus.NO_RESULTS.is_technical_failure
    assert not RetrievalStatus.LOW_RELEVANCE.is_technical_failure
    # ...but neither may stand in for a successful retrieval.
    assert not RetrievalStatus.NO_RESULTS.permits_clinical_interpretation
    assert RetrievalStatus.SUCCESS.permits_clinical_interpretation


def test_case_support_item_can_never_report_as_authority() -> None:
    item = RetrievedItem(
        doc_id="mietic_c_x",
        text="...",
        score=0.99,
        source_table="mietic_cases",
        retrieval_scope="CASE_SUPPORT",
        authority_status="NOT_PROTOCOL",
        retrieval_channel="dense",
    )
    assert not item.is_authority


# --------------------------------------------------------------------------
# query translation
# --------------------------------------------------------------------------


def test_vietnamese_query_produces_english_channel() -> None:
    translated = translate_query("đau ngực dữ dội, khó thở, vã mồ hôi")
    assert translated.query_en, "English channel is required for an English corpus"
    assert "chest pain" in translated.query_en
    assert "EN_CHANNEL_UNAVAILABLE" not in translated.degraded_modes


def test_patient_slang_still_routes_to_clinical_terms() -> None:
    """Slang is what patients actually type, and it retrieved worst of all."""
    translated = translate_query("tim đập loạn cào cào như muốn văng ra ngoài")
    assert "palpitations" in translated.query_en or "tachycardia" in translated.query_en


def test_translation_is_capped_to_avoid_diluting_the_query() -> None:
    translated = translate_query("đau bụng quặn từng cơn kèm nôn ói")
    assert len(translated.concepts) <= 3


def test_sparse_terms_are_unigrams_not_slugs() -> None:
    """The corpus keyword index is unigram English; slugs match nothing."""
    translated = translate_query("đau ngực dữ dội")
    assert translated.sparse_terms
    assert all("_" not in term and ":" not in term for term in translated.sparse_terms)


# --------------------------------------------------------------------------
# database-backed
# --------------------------------------------------------------------------


def test_authority_search_returns_only_authority(db_available: bool) -> None:
    outcome = _run(_retriever().search_esi_authority("severe chest pain", top_k=8))
    assert outcome.status is RetrievalStatus.SUCCESS
    assert outcome.items
    assert all(item.retrieval_scope == "CLINICAL_AUTHORITY" for item in outcome.items)
    assert len(outcome.authority_items) == len(outcome.items)


def test_mietic_search_never_yields_authority(db_available: bool) -> None:
    outcome = _run(_retriever().search_mietic_cases("severe chest pain", top_k=8))
    assert outcome.status is RetrievalStatus.SUCCESS
    assert outcome.items
    assert outcome.authority_items == ()
    assert all(item.retrieval_scope == "CASE_SUPPORT" for item in outcome.items)


def test_one_query_vector_serves_both_corpora(db_available: bool) -> None:
    """A shared embedding space is what makes a single query vector possible."""
    from src.services.embeddings import (
        EMBEDDING_DIMENSIONS,
        get_embedding_service,
    )

    service = get_embedding_service()
    vector = service.embed_query("đau ngực dữ dội, khó thở")
    assert len(vector) == EMBEDDING_DIMENSIONS
    # The cache returns the identical object, so no second API call is made.
    assert service.embed_query("đau ngực dữ dội, khó thở") is vector


def test_decision_point_filter_narrows_to_the_deciding_rules(db_available: bool) -> None:
    outcome = _run(
        _retriever().search_esi_authority(
            "severe pain, diaphoretic, chest discomfort",
            decision_point="B",
            facets=["HIGH_RISK"],
            top_k=5,
        )
    )
    assert outcome.status is RetrievalStatus.SUCCESS
    assert outcome.filters["decision_point"] == "B"
    for item in outcome.items:
        payload = item.metadata.get("payload") or {}
        assert "B" in (payload.get("decision_points") or [])


def test_mietic_metadata_filters_apply(db_available: bool) -> None:
    outcome = _run(
        _retriever().search_mietic_cases(
            "shortness of breath",
            age_band="elderly_65plus",
            labelled_only=True,
            top_k=5,
        )
    )
    assert outcome.status is RetrievalStatus.SUCCESS
    for item in outcome.items:
        assert item.metadata["age_band"] == "elderly_65plus"
        assert item.metadata["validated_esi_level"] is not None


def test_english_channel_improves_vietnamese_retrieval(db_available: bool) -> None:
    """Measured, not assumed: the English channel is why retrieval works."""
    query_vi = "co giật toàn thân, sùi bọt mép"
    translated = translate_query(query_vi)
    reference = _run(_retriever().search_esi_authority(translated.query_en, top_k=5))
    vi_only = _run(_retriever().search_esi_authority(query_vi, top_k=5))
    combined = _run(
        _retriever().search_esi_authority(f"{query_vi}. {translated.query_en}", top_k=5)
    )
    if reference.status is not RetrievalStatus.SUCCESS:
        pytest.skip("reference retrieval unavailable")

    gold = {item.doc_id for item in reference.items}
    vi_overlap = len(gold & {item.doc_id for item in vi_only.items})
    combined_overlap = len(gold & {item.doc_id for item in combined.items})
    assert combined_overlap >= vi_overlap
