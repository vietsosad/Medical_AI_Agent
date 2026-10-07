"""One embedding space for every corpus and every query.

Both knowledge stores and the runtime query path go through this module, so a
query vector can be computed once and reused against ESI and MIETIC alike.
Mixing spaces is what previously produced a hard `different vector dimensions`
error at query time, surfaced to patients as missing clinical evidence.

The dimension is asserted rather than assumed: a provider silently returning a
different width would corrupt an index that takes hours to rebuild.
"""

from __future__ import annotations

import asyncio
import hashlib
from dataclasses import dataclass
from functools import lru_cache
from typing import Any

from src.config import get_settings

EMBEDDING_MODEL = "text-embedding-3-large"
EMBEDDING_DIMENSIONS = 1024


class EmbeddingError(RuntimeError):
    """Raised when a vector cannot be produced. Never swallowed into an empty
    result — a technical failure must stay distinguishable from 'no evidence'."""


@dataclass(frozen=True)
class EmbeddingResult:
    vector: list[float]
    model: str
    dimensions: int


def _digest(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


class OpenAIEmbeddingService:
    """Thin, dimension-checked wrapper with a small in-process query cache."""

    def __init__(self, *, model: str = EMBEDDING_MODEL, dimensions: int = EMBEDDING_DIMENSIONS) -> None:
        self.model = model
        self.dimensions = dimensions
        self._client: Any | None = None
        self._lock = asyncio.Lock()
        self._cache: dict[str, list[float]] = {}

    def _get_client(self) -> Any:
        if self._client is None:
            settings = get_settings()
            api_key = settings.openai_api_key.strip()
            if not api_key:
                raise EmbeddingError("OPENAI_API_KEY is not configured")
            try:
                from openai import OpenAI
            except ImportError as exc:  # pragma: no cover - dependency guard
                raise EmbeddingError("openai package is not installed") from exc
            self._client = OpenAI(api_key=api_key)
        return self._client

    def _check(self, vectors: list[list[float]]) -> None:
        for vector in vectors:
            if len(vector) != self.dimensions:
                raise EmbeddingError(
                    f"Expected {self.dimensions}-dim vectors, got {len(vector)}"
                )

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        response = self._get_client().embeddings.create(
            model=self.model, input=texts, dimensions=self.dimensions
        )
        vectors = [item.embedding for item in response.data]
        self._check(vectors)
        return vectors

    def embed_query(self, text: str) -> list[float]:
        """Cached: the same turn queries several corpora with one vector."""
        key = _digest(f"{self.model}|{self.dimensions}|{text}")
        cached = self._cache.get(key)
        if cached is not None:
            return cached
        vector = self.embed_documents([text])[0]
        if len(self._cache) > 512:
            self._cache.clear()
        self._cache[key] = vector
        return vector

    async def embed_query_async(self, text: str) -> list[float]:
        async with self._lock:
            return await asyncio.to_thread(self.embed_query, text)


@lru_cache(maxsize=1)
def get_embedding_service() -> OpenAIEmbeddingService:
    return OpenAIEmbeddingService()
