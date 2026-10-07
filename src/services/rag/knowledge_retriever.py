"""Unified retrieval over the two knowledge stores.

Both corpora now live in one embedding space (text-embedding-3-large @ 1024),
so a turn embeds its query once and searches ESI authority, ESI case support
and MIETIC cases with the same vector.

Authority is decided by the corpus row, never by the ranking: `mietic_cases`
rows are stamped CASE_SUPPORT/NOT_PROTOCOL at ingestion and this module cannot
promote them. `search_esi_authority` filters to CLINICAL_AUTHORITY in SQL, so
an omission in a prompt cannot leak context material into an authority result.

Every call returns a typed RetrievalOutcome. A database or embedding fault is
reported as a technical failure and never as an absence of evidence.
"""

from __future__ import annotations

import logging
from typing import Any

from sqlalchemy import text as sql_text

from src.config import get_settings
from sqlmodel.ext.asyncio.session import AsyncSession

from src.services.db import async_engine
from src.services.embeddings import EmbeddingError, get_embedding_service
from src.services.rag.hybrid_retrieval import CorpusSpec, multi_query_search
from src.services.rag.outcomes import (
    RetrievalOutcome,
    RetrievalStatus,
    RetrievedItem,
    technical_failure,
)

logger = logging.getLogger(__name__)

ESI_TABLE = "esi_knowledge_documents"
MIETIC_TABLE = "mietic_cases"

# Cross-lingual similarity sits well below monolingual, so this floor is about
# discarding noise, not asserting clinical relevance — the evidence gate still
# decides sufficiency.
DEFAULT_MIN_SIMILARITY = 0.25


def _dimension_error(exc: BaseException) -> bool:
    return "different vector dimensions" in str(exc).lower()


class KnowledgeRetriever:
    """Read-only access to the ESI and MIETIC stores."""

    def __init__(self, *, top_k: int | None = None, min_similarity: float | None = None) -> None:
        settings = get_settings()
        self.top_k = top_k or getattr(settings, "rag_retrieval_top_k", 5)
        self.min_similarity = (
            DEFAULT_MIN_SIMILARITY if min_similarity is None else min_similarity
        )

    async def _vector_search(
        self,
        *,
        table: str,
        id_column: str,
        text_column: str,
        vector: list[float],
        where: str,
        params: dict[str, Any],
        extra_columns: str = "",
        top_k: int,
    ) -> list[dict[str, Any]]:
        columns = f"{id_column} AS doc_id, {text_column} AS text"
        if extra_columns:
            columns += f", {extra_columns}"
        statement = sql_text(
            f"SELECT {columns}, 1 - (embedding <=> CAST(:qv AS vector)) AS score "
            f"FROM {table} WHERE {where} "
            f"ORDER BY embedding <=> CAST(:qv AS vector) LIMIT :k"
        )
        payload = {"qv": str(vector), "k": top_k, **params}
        async with AsyncSession(async_engine) as session:
            result = await session.execute(statement, payload)
            return [dict(row) for row in result.mappings().all()]

    async def _run(
        self,
        *,
        query: str,
        query_vector: list[float] | None,
        table: str,
        id_column: str,
        text_column: str,
        where: str,
        params: dict[str, Any],
        extra_columns: str,
        scope: str,
        authority_status: str,
        top_k: int | None,
        filters: dict[str, Any],
        query_vi: str,
        query_en: str,
    ) -> RetrievalOutcome:
        context = {"query_vi": query_vi, "query_en": query_en, "filters": filters}
        vector = query_vector
        if vector is None:
            # Compatibility path for callers that issue an isolated search.
            # Multi-corpus async flows should compute one vector with
            # ``embed_query_async`` and pass it explicitly so they neither
            # block the event loop here nor request the same embedding twice.
            try:
                vector = get_embedding_service().embed_query(query)
            except EmbeddingError as exc:
                logger.error("Embedding failed for retrieval: %s", exc)
                return technical_failure(RetrievalStatus.EMBEDDING_FAILURE, exc, **context)
            except Exception as exc:  # noqa: BLE001 - surfaced, not swallowed
                logger.exception("Unexpected embedding error")
                return technical_failure(RetrievalStatus.EMBEDDING_FAILURE, exc, **context)

        try:
            rows = await self._vector_search(
                table=table,
                id_column=id_column,
                text_column=text_column,
                vector=vector,
                where=where,
                params=params,
                extra_columns=extra_columns,
                top_k=top_k or self.top_k,
            )
        except Exception as exc:  # noqa: BLE001
            status = (
                RetrievalStatus.DIMENSION_MISMATCH
                if _dimension_error(exc)
                else RetrievalStatus.DATABASE_FAILURE
            )
            logger.error("Retrieval against %s failed (%s): %s", table, status.value, exc)
            return technical_failure(status, exc, **context)

        if not rows:
            return RetrievalOutcome(status=RetrievalStatus.NO_RESULTS, channels=("dense",), **context)

        items = tuple(
            RetrievedItem(
                doc_id=str(row["doc_id"]),
                text=str(row["text"]),
                score=float(row["score"]),
                source_table=table,
                retrieval_scope=scope,
                authority_status=authority_status,
                retrieval_channel="dense",
                metadata={
                    k: v for k, v in row.items() if k not in {"doc_id", "text", "score"}
                },
            )
            for row in rows
            if float(row["score"]) >= self.min_similarity
        )
        if not items:
            best = max(float(row["score"]) for row in rows)
            return RetrievalOutcome(
                status=RetrievalStatus.LOW_RELEVANCE,
                channels=("dense",),
                detail=f"best score {best:.3f} below floor {self.min_similarity:.2f}",
                **context,
            )
        return RetrievalOutcome(
            status=RetrievalStatus.SUCCESS, items=items, channels=("dense",), **context
        )

    async def search_esi_authority(
        self,
        query: str,
        *,
        query_vector: list[float] | None = None,
        query_vi: str = "",
        query_en: str = "",
        decision_point: str | None = None,
        facets: list[str] | None = None,
        top_k: int | None = None,
    ) -> RetrievalOutcome:
        """CLINICAL_AUTHORITY only, optionally narrowed to a decision point.

        Filtering on the Pass-5 payload is what turns a broad similarity search
        into "the rules that decide this question": an unfiltered chest-pain
        query ranks gastrointestinal rules first, while the same query scoped to
        Decision Point B surfaces the severe-pain criteria it needs.
        """
        clauses = ["retrieval_scope = 'CLINICAL_AUTHORITY'"]
        params: dict[str, Any] = {}
        filters: dict[str, Any] = {"retrieval_scope": "CLINICAL_AUTHORITY"}
        if decision_point:
            clauses.append("(payload::jsonb)->'decision_points' ? :dp")
            params["dp"] = decision_point
            filters["decision_point"] = decision_point
        if facets:
            clauses.append("(payload::jsonb)->'retrieval_facets' ?| :facets")
            params["facets"] = facets
            filters["facets"] = facets
        return await self._run(
            query=query,
            query_vector=query_vector,
            table=ESI_TABLE,
            id_column="document_id",
            text_column="retrieval_text",
            where=" AND ".join(clauses),
            params=params,
            extra_columns=(
                "atom_type, pass5_version, retrieval_text_sha256, payload"
            ),
            scope="CLINICAL_AUTHORITY",
            authority_status="AUTHORITATIVE",
            top_k=top_k,
            filters=filters,
            query_vi=query_vi or query,
            query_en=query_en,
        )

    async def search_esi_cases(
        self, query: str, *, query_vi: str = "", query_en: str = "", top_k: int | None = None
    ) -> RetrievalOutcome:
        """Curated ESI handbook examples. Support and explanation only."""
        return await self._run(
            query=query,
            query_vector=None,
            table=ESI_TABLE,
            id_column="document_id",
            text_column="retrieval_text",
            where="retrieval_scope = 'CASE_SUPPORT'",
            params={},
            extra_columns=(
                "atom_type, pass5_version, retrieval_text_sha256, payload"
            ),
            scope="CASE_SUPPORT",
            authority_status="NOT_PROTOCOL",
            top_k=top_k,
            filters={"retrieval_scope": "CASE_SUPPORT"},
            query_vi=query_vi or query,
            query_en=query_en,
        )

    async def search_mietic_cases(
        self,
        query: str,
        *,
        query_vector: list[float] | None = None,
        query_vi: str = "",
        query_en: str = "",
        age_band: str | None = None,
        symptom_concepts: list[str] | None = None,
        labelled_only: bool = False,
        top_k: int | None = None,
    ) -> RetrievalOutcome:
        """Similar real presentations. Never protocol authority, by construction."""
        clauses = ["TRUE"]
        params: dict[str, Any] = {}
        filters: dict[str, Any] = {"retrieval_scope": "CASE_SUPPORT"}
        if age_band:
            clauses.append("age_band = :age_band")
            params["age_band"] = age_band
            filters["age_band"] = age_band
        if symptom_concepts:
            clauses.append("symptom_concepts && :concepts")
            params["concepts"] = symptom_concepts
            filters["symptom_concepts"] = symptom_concepts
        if labelled_only:
            clauses.append("validated_esi_level IS NOT NULL")
            filters["labelled_only"] = True
        return await self._run(
            query=query,
            query_vector=query_vector,
            table=MIETIC_TABLE,
            id_column="case_id",
            text_column="retrieval_text",
            where=" AND ".join(clauses),
            params=params,
            extra_columns=(
                "age_years, age_band, sex, validated_esi_level, label_status, "
                "candidate_esi_levels, symptom_concepts"
            ),
            scope="CASE_SUPPORT",
            authority_status="NOT_PROTOCOL",
            top_k=top_k,
            filters=filters,
            query_vi=query_vi or query,
            query_en=query_en,
        )


    # ------------------------------------------------------------------
    # Multi-query hybrid search
    #
    # These sit beside the single-query methods above rather than replacing
    # them: the dense-only path is what the benchmark measures against, and a
    # deployment can fall back to it by configuration without a code change.
    # ------------------------------------------------------------------

    async def search_esi_authority_hybrid(
        self,
        queries: list[tuple[str, str]],
        *,
        decision_point: str | None = None,
        facets: list[str] | None = None,
        top_k: int | None = None,
        use_lexical: bool = True,
        query_vi: str = "",
        query_en: str = "",
    ) -> tuple[RetrievalOutcome, dict[str, Any]]:
        """CLINICAL_AUTHORITY only, several queries, rank-fused.

        The authority boundary is still enforced in SQL. Fusion may only
        reorder rows the ``retrieval_scope`` filter already allowed, so no
        ranking change can promote case material into an authority result.
        """
        clauses = ["retrieval_scope = 'CLINICAL_AUTHORITY'"]
        params: dict[str, Any] = {}
        filters: dict[str, Any] = {"retrieval_scope": "CLINICAL_AUTHORITY"}
        if decision_point:
            clauses.append("(payload::jsonb)->'decision_points' ? :dp")
            params["dp"] = decision_point
            filters["decision_point"] = decision_point
        if facets:
            clauses.append("(payload::jsonb)->'retrieval_facets' ?| :facets")
            params["facets"] = facets
            filters["facets"] = facets

        spec = CorpusSpec(
            table=ESI_TABLE,
            id_column="document_id",
            text_column="retrieval_text",
            extra_columns="atom_type, pass5_version, retrieval_text_sha256, payload",
            where=" AND ".join(clauses),
            params=params,
        )
        return await self._hybrid(
            spec,
            queries,
            scope="CLINICAL_AUTHORITY",
            authority_status="AUTHORITATIVE",
            top_k=top_k or self.top_k,
            filters=filters,
            use_lexical=use_lexical,
            query_vi=query_vi,
            query_en=query_en,
        )

    async def search_mietic_cases_hybrid(
        self,
        queries: list[tuple[str, str]],
        *,
        top_k: int | None = None,
        use_lexical: bool = True,
        query_vi: str = "",
        query_en: str = "",
        symptom_concepts: list[str] | None = None,
    ) -> tuple[RetrievalOutcome, dict[str, Any]]:
        """Similar real presentations. Never protocol authority, by construction."""
        clauses = ["TRUE"]
        params: dict[str, Any] = {}
        filters: dict[str, Any] = {"retrieval_scope": "CASE_SUPPORT"}
        if symptom_concepts:
            filters["symptom_concepts"] = symptom_concepts
        spec = CorpusSpec(
            table=MIETIC_TABLE,
            id_column="case_id",
            text_column="retrieval_text",
            extra_columns=(
                "age_years, age_band, sex, validated_esi_level, label_status, "
                "candidate_esi_levels, symptom_concepts"
            ),
            where=" AND ".join(clauses),
            params=params,
        )
        return await self._hybrid(
            spec,
            queries,
            scope="CASE_SUPPORT",
            authority_status="NOT_PROTOCOL",
            top_k=top_k or self.top_k,
            filters=filters,
            use_lexical=use_lexical,
            query_vi=query_vi,
            query_en=query_en,
        )

    async def _hybrid(
        self,
        spec: CorpusSpec,
        queries: list[tuple[str, str]],
        *,
        scope: str,
        authority_status: str,
        top_k: int,
        filters: dict[str, Any],
        use_lexical: bool,
        query_vi: str,
        query_en: str,
    ) -> tuple[RetrievalOutcome, dict[str, Any]]:
        context = {"query_vi": query_vi, "query_en": query_en, "filters": filters}
        if not queries:
            return (
                RetrievalOutcome(status=RetrievalStatus.NO_RESULTS, **context),
                {},
            )
        settings = get_settings()
        try:
            candidates, audit = await multi_query_search(
                spec,
                queries,
                per_query_limit=max(top_k * 2, 10),
                pool_size=int(settings.retrieval_candidate_pool_size),
                rrf_k=int(settings.retrieval_rrf_k),
                use_lexical=use_lexical,
            )
        except Exception as exc:  # noqa: BLE001 - surfaced, never swallowed
            status = (
                RetrievalStatus.DIMENSION_MISMATCH
                if _dimension_error(exc)
                else RetrievalStatus.DATABASE_FAILURE
            )
            logger.error("Hybrid retrieval against %s failed: %s", spec.table, exc)
            return technical_failure(status, exc, **context), {}

        # An embedding outage is a technical failure even when the keyword
        # channel happened to return rows: reporting a lexical-only result as a
        # normal retrieval would hide the outage behind a plausible answer.
        degraded = audit.get("degraded_modes") or []
        if any(mode.startswith("DENSE_CHANNEL") for mode in degraded):
            return (
                RetrievalOutcome(
                    status=RetrievalStatus.EMBEDDING_FAILURE,
                    error="; ".join(degraded),
                    channels=tuple(audit.get("channels", {})),
                    **context,
                ),
                audit,
            )
        if not candidates:
            return (
                RetrievalOutcome(
                    status=RetrievalStatus.NO_RESULTS,
                    channels=tuple(audit.get("channels", {})),
                    **context,
                ),
                audit,
            )

        items = tuple(
            RetrievedItem(
                doc_id=candidate.doc_id,
                text=candidate.text,
                # The dense similarity where one exists, so downstream
                # consumers keep a comparable number; fusion rank is carried
                # separately in metadata and is what the ordering used.
                score=(
                    candidate.best_dense_score
                    if candidate.best_dense_score is not None
                    else 0.0
                ),
                source_table=spec.table,
                retrieval_scope=scope,
                authority_status=authority_status,
                retrieval_channel="+".join(candidate.channels) or "dense",
                metadata={
                    **candidate.metadata,
                    "fusion_score": candidate.fusion_score,
                    "channel_audit": candidate.audit(),
                },
            )
            for candidate in candidates[:top_k]
        )
        return (
            RetrievalOutcome(
                status=RetrievalStatus.SUCCESS,
                items=items,
                channels=tuple(audit.get("channels", {})),
                **context,
            ),
            {**audit, "candidates": [item.audit() for item in candidates[:top_k]]},
        )


_instance: KnowledgeRetriever | None = None


def get_knowledge_retriever() -> KnowledgeRetriever:
    global _instance
    if _instance is None:
        _instance = KnowledgeRetriever()
    return _instance
