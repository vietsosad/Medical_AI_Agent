"""Pure tests for turn-scoped query-vector reuse across knowledge stores."""

from __future__ import annotations

from typing import Any

import pytest

from src.services.embeddings import EMBEDDING_DIMENSIONS
from src.services.rag import knowledge_retriever as retriever_module
from src.services.rag.knowledge_retriever import (
    ESI_TABLE,
    MIETIC_TABLE,
    KnowledgeRetriever,
)
from src.services.rag.outcomes import RetrievalStatus


@pytest.mark.asyncio
async def test_precomputed_vector_is_reused_for_authority_and_mietic(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Supplying a turn vector must bypass both per-search embedding calls."""
    retriever = KnowledgeRetriever(top_k=1, min_similarity=0.0)
    shared_vector = [0.125] * EMBEDDING_DIMENSIONS
    searches: list[tuple[str, list[float]]] = []

    def unexpected_embedding_service() -> None:
        raise AssertionError("a supplied query_vector must bypass embedding")

    async def capture_search(**kwargs: Any) -> list[dict[str, Any]]:
        searches.append((str(kwargs["table"]), kwargs["vector"]))
        return [{"doc_id": f"{kwargs['table']}-1", "text": "evidence", "score": 0.9}]

    monkeypatch.setattr(retriever_module, "get_embedding_service", unexpected_embedding_service)
    monkeypatch.setattr(retriever, "_vector_search", capture_search)

    authority = await retriever.search_esi_authority("shared bilingual query", query_vector=shared_vector)
    mietic = await retriever.search_mietic_cases("shared bilingual query", query_vector=shared_vector)

    assert authority.status is RetrievalStatus.SUCCESS
    assert mietic.status is RetrievalStatus.SUCCESS
    assert [table for table, _vector in searches] == [ESI_TABLE, MIETIC_TABLE]
    assert all(vector is shared_vector for _table, vector in searches)


@pytest.mark.asyncio
async def test_omitted_vector_keeps_single_search_compatibility(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Legacy isolated searches still embed their own query when needed."""
    retriever = KnowledgeRetriever(top_k=1, min_similarity=0.0)
    generated_vector = [0.25] * EMBEDDING_DIMENSIONS

    class StubEmbeddingService:
        def __init__(self) -> None:
            self.queries: list[str] = []

        def embed_query(self, query: str) -> list[float]:
            self.queries.append(query)
            return generated_vector

    service = StubEmbeddingService()
    captured_vectors: list[list[float]] = []

    async def capture_search(**kwargs: Any) -> list[dict[str, Any]]:
        captured_vectors.append(kwargs["vector"])
        return [{"doc_id": "esi-1", "text": "evidence", "score": 0.9}]

    monkeypatch.setattr(retriever_module, "get_embedding_service", lambda: service)
    monkeypatch.setattr(retriever, "_vector_search", capture_search)

    outcome = await retriever.search_esi_authority("isolated query")

    assert outcome.status is RetrievalStatus.SUCCESS
    assert service.queries == ["isolated query"]
    assert captured_vectors == [generated_vector]
