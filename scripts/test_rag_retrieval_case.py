#!/usr/bin/env python3
"""Read-only diagnostic for production protocol RAG and quarantined legacy data.

Production mode executes the actual VI dense, EN dense, controlled sparse and
RRF path over ``triage_protocol_documents``. Legacy-audit mode preserves the
earlier MIETIC comparison, but labels it explicitly as a non-production corpus.

Run from the repository root:
    python scripts/test_rag_retrieval_case.py
    python scripts/test_rag_retrieval_case.py --mode legacy-audit --top-k 10
"""

from __future__ import annotations

import argparse
import asyncio
import os
import sys
import textwrap
import time
from collections import Counter
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from statistics import mean
from typing import Any, Protocol

from sqlalchemy import Engine, create_engine, text


REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

# This diagnostic must use an already-cached model. It must not silently
# download a different model or substitute dummy embeddings.
os.environ.setdefault("HF_HUB_OFFLINE", "1")
os.environ.setdefault("TRANSFORMERS_OFFLINE", "1")

from src.config import get_settings  # noqa: E402


TABLE_NAME = "triageknowledgebase"
DEFAULT_MODEL = "BAAI/bge-m3"
DEFAULT_TOP_K = 5
DEFAULT_SCORE_THRESHOLD = 0.55
EXPECTED_EMBEDDING_DIMENSION = 1024


@dataclass(frozen=True)
class QueryChannel:
    """One representation of the same synthetic patient case."""

    name: str
    description: str
    query: str


@dataclass
class RetrievalRun:
    """Measured output of one dense retrieval query."""

    channel: QueryChannel
    results: list[dict[str, Any]]
    embedding_ms: float
    database_ms: float


class Embedder(Protocol):
    backend_name: str
    dimension: int

    def embed_query(self, query: str) -> list[float]: ...


class SentenceTransformerEmbedder:
    """Local fallback matching HuggingFaceEmbeddings' core model behavior."""

    def __init__(self, model_name: str) -> None:
        from sentence_transformers import SentenceTransformer

        self._model = SentenceTransformer(model_name, local_files_only=True)
        self.backend_name = "sentence-transformers (local fallback)"
        get_dimension = getattr(
            self._model,
            "get_embedding_dimension",
            self._model.get_sentence_embedding_dimension,
        )
        dimension = get_dimension()
        if dimension is None:
            raise RuntimeError("Không xác định được số chiều embedding của model.")
        self.dimension = int(dimension)

    def embed_query(self, query: str) -> list[float]:
        vector = self._model.encode(
            query,
            convert_to_numpy=True,
            normalize_embeddings=False,
            show_progress_bar=False,
        )
        return vector.astype(float).tolist()


class LangChainEmbedder:
    """Production embedding wrapper when the production package is installed."""

    def __init__(self, model_name: str) -> None:
        from langchain_huggingface import HuggingFaceEmbeddings

        self._model = HuggingFaceEmbeddings(
            model_name=model_name,
            model_kwargs={"local_files_only": True},
        )
        self.backend_name = "langchain-huggingface (production wrapper)"
        probe = self._model.embed_query("embedding dimension probe")
        self.dimension = len(probe)

    def embed_query(self, query: str) -> list[float]:
        return list(self._model.embed_query(query))


def build_query_channels() -> list[QueryChannel]:
    """Build faithful variants of one invented, non-diagnostic case."""

    vietnamese_case = (
        "Nữ 32 tuổi, đau bụng dưới bên phải tăng dần trong 8 giờ, đau 8/10, "
        "sốt 38,7°C, buồn nôn, nôn 2 lần, mạch 112 lần/phút, huyết áp "
        "98/64 mmHg, SpO2 98%."
    )
    english_case = (
        "32-year-old female with progressively worsening right lower abdominal "
        "pain for 8 hours, pain score 8/10, fever 38.7 C, nausea, two episodes "
        "of vomiting, heart rate 112 bpm, blood pressure 98/64 mmHg, SpO2 98%."
    )

    return [
        QueryChannel(
            name="production_like",
            description=(
                "Mô phỏng query builder hiện tại: chief complaint tiếng Việt + "
                "clinical keywords tiếng Anh, chưa giữ toàn bộ dấu hiệu sinh tồn."
            ),
            query=(
                "đau bụng dưới bên phải tăng dần, sốt, buồn nôn, nôn "
                "abdominal pain right lower quadrant fever nausea vomiting"
            ),
        ),
        QueryChannel(
            name="full_vietnamese",
            description="Toàn bộ lời khai và dấu hiệu sinh tồn bằng tiếng Việt.",
            query=vietnamese_case,
        ),
        QueryChannel(
            name="structured_english",
            description="Bản tiếng Anh có cấu trúc, cùng ngôn ngữ với MIETIC.",
            query=english_case,
        ),
        QueryChannel(
            name="bilingual_full",
            description="Ghép đủ dữ kiện tiếng Việt và tiếng Anh.",
            query=f"{vietnamese_case} {english_case}",
        ),
    ]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="In kết quả retrieval của một ca triage giả lập từ PostgreSQL RAG."
    )
    parser.add_argument(
        "--mode",
        choices=("production", "legacy-audit"),
        default="production",
        help="production dùng đúng protocol retriever; legacy-audit chỉ đọc MIETIC.",
    )
    parser.add_argument(
        "--top-k",
        type=int,
        default=DEFAULT_TOP_K,
        help=f"Số kết quả dense retrieval (mặc định: {DEFAULT_TOP_K}).",
    )
    parser.add_argument(
        "--threshold",
        type=float,
        default=DEFAULT_SCORE_THRESHOLD,
        help=(
            "Ngưỡng similarity để mô phỏng evidence gate hiện tại "
            f"(mặc định: {DEFAULT_SCORE_THRESHOLD})."
        ),
    )
    parser.add_argument(
        "--model",
        default=os.getenv("EMBEDDING_MODEL_NAME", DEFAULT_MODEL),
        help=f"Embedding model đã có trong local cache (mặc định: {DEFAULT_MODEL}).",
    )
    args = parser.parse_args()
    if args.top_k < 1 or args.top_k > 100:
        parser.error("--top-k phải nằm trong khoảng 1..100")
    if not 0.0 <= args.threshold <= 1.0:
        parser.error("--threshold phải nằm trong khoảng 0..1")
    return args


def load_embedder(model_name: str) -> Embedder:
    """Prefer the production wrapper; fail loudly instead of using fake vectors."""

    try:
        return LangChainEmbedder(model_name)
    except ModuleNotFoundError as exc:
        if exc.name != "langchain_huggingface":
            raise
        return SentenceTransformerEmbedder(model_name)


def build_read_only_engine() -> Engine:
    """Create a sync PostgreSQL engine without exposing its connection URL."""

    settings = get_settings()
    database_url = settings.sync_database_url or settings.database_url
    database_url = database_url.replace("postgresql+asyncpg://", "postgresql+psycopg://")
    database_url = database_url.replace("postgresql+psycopg2://", "postgresql+psycopg://")
    database_url = database_url.replace("postgres://", "postgresql+psycopg://")
    if not database_url.startswith("postgresql"):
        raise RuntimeError(
            "Diagnostic này yêu cầu PostgreSQL/pgvector nhưng cấu hình hiện tại "
            "không phải PostgreSQL."
        )
    return create_engine(database_url, future=True, pool_pre_ping=True)


def vector_literal(vector: Sequence[float]) -> str:
    """Serialize a vector for an explicit PostgreSQL vector cast."""

    return "[" + ",".join(format(value, ".10g") for value in vector) + "]"


def print_title(title: str, marker: str = "=") -> None:
    print(f"\n{marker * 110}\n{title}\n{marker * 110}")


def print_wrapped(label: str, value: Any, indent: int = 4) -> None:
    prefix = f"{' ' * indent}{label}: "
    subsequent = " " * len(prefix)
    normalized = " ".join(str(value).split())
    print(
        textwrap.fill(
            normalized,
            width=110,
            initial_indent=prefix,
            subsequent_indent=subsequent,
        )
    )


def compact_text(value: Any, limit: int = 700) -> str:
    normalized = " ".join(str(value or "").split())
    if len(normalized) <= limit:
        return normalized
    return normalized[: limit - 1].rstrip() + "…"


def fetch_database_profile(engine: Engine) -> dict[str, Any]:
    profile_sql = text(
        f"""
        SELECT
            COUNT(*)::int AS total_rows,
            COUNT(DISTINCT metadata_json ->> 'source')::int AS source_count,
            COUNT(*) FILTER (WHERE COALESCE(array_length(keywords, 1), 0) = 0)::int
                AS rows_without_keywords,
            COUNT(*) FILTER (WHERE metadata_json ->> 'document_type' IS NOT NULL)::int
                AS rows_with_document_type,
            COUNT(*) FILTER (WHERE metadata_json ->> 'validation_status' IS NOT NULL)::int
                AS rows_with_validation_status
        FROM {TABLE_NAME}
        """
    )
    source_sql = text(
        f"""
        SELECT COALESCE(metadata_json ->> 'source', '<missing>') AS source,
               COUNT(*)::int AS row_count
        FROM {TABLE_NAME}
        GROUP BY 1
        ORDER BY row_count DESC, source
        """
    )
    keyword_sql = text(
        f"""
        SELECT keyword, COUNT(*)::int AS row_count
        FROM {TABLE_NAME}
        CROSS JOIN LATERAL unnest(keywords) AS keyword
        GROUP BY keyword
        ORDER BY row_count DESC, keyword
        """
    )
    with engine.connect() as connection:
        profile = dict(connection.execute(profile_sql).mappings().one())
        profile["sources"] = [dict(row) for row in connection.execute(source_sql).mappings()]
        profile["keyword_vocabulary"] = [
            dict(row) for row in connection.execute(keyword_sql).mappings()
        ]
    return profile


def run_dense_retrieval(
    engine: Engine,
    embedder: Embedder,
    channel: QueryChannel,
    top_k: int,
) -> RetrievalRun:
    embedding_started = time.perf_counter()
    vector = embedder.embed_query(channel.query)
    embedding_ms = (time.perf_counter() - embedding_started) * 1000
    if len(vector) != EXPECTED_EMBEDDING_DIMENSION:
        raise RuntimeError(
            f"Embedding query có {len(vector)} chiều; cột pgvector yêu cầu "
            f"{EXPECTED_EMBEDDING_DIMENSION} chiều."
        )

    sql = text(
        f"""
        SELECT
            case_id,
            page_content,
            keywords,
            metadata_json ->> 'esi_level' AS metadata_esi,
            metadata_json ->> 'source' AS source,
            metadata_json ->> 'provenance' AS provenance,
            metadata_json ->> 'document_type' AS document_type,
            metadata_json ->> 'validation_status' AS validation_status,
            embedding <=> CAST(:query_embedding AS vector) AS cosine_distance,
            1 - (embedding <=> CAST(:query_embedding AS vector)) AS raw_similarity
        FROM {TABLE_NAME}
        ORDER BY embedding <=> CAST(:query_embedding AS vector)
        LIMIT :top_k
        """
    )
    database_started = time.perf_counter()
    with engine.connect() as connection:
        rows = connection.execute(
            sql,
            {"query_embedding": vector_literal(vector), "top_k": top_k},
        ).mappings()
        results = [dict(row) for row in rows]
    database_ms = (time.perf_counter() - database_started) * 1000
    return RetrievalRun(channel, results, embedding_ms, database_ms)


def run_sparse_keyword_diagnostic(
    engine: Engine,
    sparse_terms: list[str],
    top_k: int,
) -> list[dict[str, Any]]:
    """Probe the existing GIN keyword column; this is not used by production."""

    sql = text(
        f"""
        SELECT
            case_id,
            keywords,
            metadata_json ->> 'esi_level' AS metadata_esi,
            metadata_json ->> 'source' AS source,
            (
                SELECT COUNT(*)
                FROM unnest(keywords) AS stored_keyword
                WHERE stored_keyword = ANY(CAST(:sparse_terms AS text[]))
            )::int AS overlap_count
        FROM {TABLE_NAME}
        WHERE keywords && CAST(:sparse_terms AS text[])
        ORDER BY overlap_count DESC, case_id
        LIMIT :top_k
        """
    )
    postgres_array = "{" + ",".join(sparse_terms) + "}"
    with engine.connect() as connection:
        return [
            dict(row)
            for row in connection.execute(
                sql,
                {"sparse_terms": postgres_array, "top_k": top_k},
            ).mappings()
        ]


def print_database_profile(profile: dict[str, Any]) -> None:
    print_title("1. HỒ SƠ DỮ LIỆU RAG ĐANG ĐƯỢC TRUY VẤN")
    print_wrapped("table", TABLE_NAME)
    print_wrapped("total_rows", profile["total_rows"])
    print_wrapped("sources", profile["sources"])
    print_wrapped("rows_without_keywords", profile["rows_without_keywords"])
    print_wrapped("rows_with_document_type", profile["rows_with_document_type"])
    print_wrapped("rows_with_validation_status", profile["rows_with_validation_status"])
    print_wrapped("keyword_vocabulary", profile["keyword_vocabulary"])
    print(
        "\n    Ghi chú: document_type/validation_status là metadata cần thiết để phân biệt "
        "case tham khảo với phác đồ đã kiểm định."
    )


def is_validated_protocol(result: dict[str, Any]) -> bool:
    return (
        result.get("document_type") == "validated_protocol"
        and result.get("validation_status") == "approved"
    )


def print_dense_run(run: RetrievalRun, threshold: float) -> None:
    print_title(
        f"DENSE CHANNEL: {run.channel.name}",
        marker="-",
    )
    print_wrapped("mục đích", run.channel.description)
    print_wrapped("query", run.channel.query)
    print_wrapped("embedding_latency_ms", f"{run.embedding_ms:.1f}")
    print_wrapped("database_latency_ms", f"{run.database_ms:.1f}")
    print_wrapped("total_retrieval_latency_ms", f"{run.embedding_ms + run.database_ms:.1f}")

    if not run.results:
        print("\n    Không có kết quả retrieval.")
        return

    for rank, result in enumerate(run.results, start=1):
        raw_similarity = float(result["raw_similarity"])
        production_similarity = max(0.0, min(1.0, raw_similarity))
        current_gate = "PASS" if production_similarity >= threshold else "FAIL"
        validated_gate = "PASS" if is_validated_protocol(result) else "FAIL"
        print(f"\n    [{rank}] case_id={result['case_id']}")
        print_wrapped("cosine_distance", f"{float(result['cosine_distance']):.6f}", indent=8)
        print_wrapped("raw_similarity", f"{raw_similarity:.6f}", indent=8)
        print_wrapped("production_similarity", f"{production_similarity:.6f}", indent=8)
        print_wrapped(
            f"current_score_gate@{threshold:.2f}",
            current_gate,
            indent=8,
        )
        print_wrapped("validated_protocol_gate", validated_gate, indent=8)
        print_wrapped("metadata_esi", result.get("metadata_esi") or "<missing>", indent=8)
        print_wrapped("source", result.get("source") or "<missing>", indent=8)
        print_wrapped("keywords", result.get("keywords") or [], indent=8)
        print_wrapped("document_type", result.get("document_type") or "<missing>", indent=8)
        print_wrapped(
            "validation_status",
            result.get("validation_status") or "<missing>",
            indent=8,
        )
        print_wrapped(
            "provenance",
            compact_text(result.get("provenance"), limit=300) or "<missing>",
            indent=8,
        )
        print_wrapped(
            "page_content_excerpt",
            compact_text(result.get("page_content")),
            indent=8,
        )

    similarities = [
        max(0.0, min(1.0, float(result["raw_similarity"])))
        for result in run.results
    ]
    esi_distribution = Counter(
        result.get("metadata_esi") or "<missing>" for result in run.results
    )
    passing = sum(score >= threshold for score in similarities)
    print("\n    SUMMARY")
    print_wrapped("top_case_ids", [row["case_id"] for row in run.results], indent=8)
    print_wrapped("top1_similarity", f"{similarities[0]:.6f}", indent=8)
    print_wrapped("mean_top_k_similarity", f"{mean(similarities):.6f}", indent=8)
    print_wrapped("score_gate_pass_count", f"{passing}/{len(similarities)}", indent=8)
    print_wrapped("metadata_esi_distribution", dict(esi_distribution), indent=8)
    print_wrapped(
        "validated_protocol_count",
        f"{sum(is_validated_protocol(row) for row in run.results)}/{len(run.results)}",
        indent=8,
    )


def print_sparse_diagnostic(
    sparse_terms: list[str],
    results: list[dict[str, Any]],
) -> None:
    print_title("3. SPARSE KEYWORD DIAGNOSTIC (GIN ARRAY OVERLAP)")
    print_wrapped("status_in_current_production_retriever", "NOT USED")
    print_wrapped("test_terms", sparse_terms)
    print_wrapped("matched_rows_shown", len(results))
    if not results:
        print(
            "\n    Không có row nào match các clinical term của ca giả lập. Chỉ mục GIN tồn tại, "
            "nhưng vocabulary hiện tại không hỗ trợ query này."
        )
        return
    for rank, result in enumerate(results, start=1):
        print(
            f"    [{rank}] case_id={result['case_id']} "
            f"overlap={result['overlap_count']} "
            f"ESI={result.get('metadata_esi')} "
            f"keywords={result.get('keywords')}"
        )


def print_cross_channel_comparison(runs: list[RetrievalRun]) -> None:
    print_title("4. SO SÁNH ĐỘ ỔN ĐỊNH GIỮA CÁC QUERY CHANNEL")
    for left_index, left in enumerate(runs):
        left_ids = {row["case_id"] for row in left.results}
        for right in runs[left_index + 1 :]:
            right_ids = {row["case_id"] for row in right.results}
            union = left_ids | right_ids
            intersection = left_ids & right_ids
            jaccard = len(intersection) / len(union) if union else 1.0
            print(
                f"    {left.channel.name:<20} vs {right.channel.name:<20} "
                f"overlap={len(intersection)}/{len(union)} jaccard={jaccard:.3f} "
                f"common={sorted(intersection)}"
            )

    all_id_sets = [{row["case_id"] for row in run.results} for run in runs]
    common_to_all = set.intersection(*all_id_sets) if all_id_sets else set()
    print_wrapped("common_to_all_channels", sorted(common_to_all))


def print_interpretation(runs: list[RetrievalRun], threshold: float) -> None:
    print_title("5. CÁCH ĐỌC KẾT QUẢ")
    passing_documents = sum(
        max(0.0, min(1.0, float(row["raw_similarity"]))) >= threshold
        for run in runs
        for row in run.results
    )
    validated_documents = sum(
        is_validated_protocol(row) for run in runs for row in run.results
    )
    print_wrapped(
        "current_score_gate",
        f"{passing_documents}/{sum(len(run.results) for run in runs)} kết quả đạt ngưỡng {threshold:.2f}",
    )
    print_wrapped(
        "validated_protocol_gate",
        f"{validated_documents}/{sum(len(run.results) for run in runs)} kết quả có metadata phác đồ đã duyệt",
    )
    print(
        "\n    PASS ở current_score_gate chỉ có nghĩa là cosine similarity vượt ngưỡng. "
        "Nó không chứng minh tài liệu là guideline/phác đồ đã được kiểm định, không chứng minh "
        "ESI đúng, và không được dùng như kết luận chẩn đoán cho ca giả lập."
    )


async def run_production_diagnostic(args: argparse.Namespace) -> int:
    """Execute the current authority-filtered retriever without database writes."""
    from src.agents.nodes.bilingual_query_builder import build_retrieval_queries
    from src.agents.nodes.evidence_gate import evaluate_evidence
    from src.services.db import dispose_db_engine
    from src.services.rag.hybrid_retriever import ClinicalHybridRetriever, RRF_K

    blueprint = {
        "chief_complaint": ["đau bụng dưới bên phải"],
        "onset_time": "8 giờ",
        "severity_score": 8,
        "associated_symptoms": ["sốt", "buồn nôn", "nôn"],
        "vital_signs": {
            "temperature_c": 38.7,
            "heart_rate": 112,
            "blood_pressure": "98/64",
            "spo2": 98,
        },
    }
    bundle = build_retrieval_queries(blueprint)
    settings = get_settings()

    print_title("PRODUCTION RAG RETRIEVAL DIAGNOSTIC — SYNTHETIC CASE")
    print_wrapped("database_backend", "PostgreSQL + pgvector (read-only SELECT)")
    print_wrapped("production_table", "triage_protocol_documents")
    print_wrapped("legacy_table_queried", "false")
    print_wrapped("case_example_corpus_eligible", "false")
    print_wrapped("query_vi", bundle.query_vi)
    print_wrapped("query_en", bundle.query_en or "<unavailable>")
    print_wrapped("sparse_terms", bundle.sparse_terms)
    print_wrapped("symptom_cluster", bundle.symptom_cluster)
    print_wrapped("population", "adult")
    print_wrapped("query_builder_degraded_modes", bundle.degraded_modes)
    print_wrapped("embedding_model", settings.embedding_model_name)
    print_wrapped(
        "embedding_revision",
        settings.embedding_model_revision or "<UNPINNED: retriever fails closed>",
    )
    print_wrapped("source_whitelist", [
        value.strip()
        for value in settings.rag_protocol_source_whitelist.split(",")
        if value.strip()
    ])
    print_wrapped("top_k", args.top_k)
    print_wrapped("fusion", f"Reciprocal Rank Fusion, k={RRF_K}")
    print_wrapped(
        "evidence_threshold",
        "approved calibration_profile thresholds per channel/cluster/population; no global 0.55 gate",
    )
    print_wrapped("database_mutation", "none")

    retriever = ClinicalHybridRetriever(k_results=args.top_k)
    try:
        retrieval = await retriever.ainvoke_channels(
            query_vi=bundle.query_vi,
            query_en=bundle.query_en,
            sparse_terms=bundle.sparse_terms,
            symptom_cluster=bundle.symptom_cluster,
            population="adult",
        )
        print_title("CHANNEL METRICS")
        print_wrapped("channels", retrieval.channels)
        print_wrapped("retriever_degraded_modes", retrieval.degraded_modes)

        evidence_rows: list[dict[str, Any]] = []
        print_title("FUSED AUTHORITY-FILTERED RESULTS")
        for rank, document in enumerate(retrieval.documents, start=1):
            metadata = dict(document.metadata)
            evidence_row = {
                **metadata,
                "citation_id": metadata.get("citation_id"),
                "protocol_content": document.page_content,
            }
            evidence_rows.append(evidence_row)
            print(f"\n    [{rank}] citation_id={metadata.get('citation_id')}")
            for key in (
                "protocol_code",
                "title",
                "issuing_body",
                "version",
                "section",
                "validation_status",
                "scope_match",
                "similarity_score",
                "fusion_score",
                "calibration_id",
                "calibration_profile",
                "matched_protocol_criteria",
                "retrieval_channels",
                "content_hash",
            ):
                print_wrapped(key, metadata.get(key), indent=8)
            print_wrapped(
                "page_content_excerpt",
                compact_text(document.page_content),
                indent=8,
            )

        evaluation = evaluate_evidence(evidence_rows)
        print_title("EVIDENCE GATE")
        print_wrapped("status", evaluation.status)
        print_wrapped("authority_status", evaluation.authority_status)
        print_wrapped("eligible_for_esi", evaluation.eligible_for_esi)
        print_wrapped("citation_count", len(evaluation.citations))
        print_wrapped("matched_protocol_criteria", evaluation.matched_protocol_criteria)
        print_wrapped("reasons", evaluation.reasons)
    finally:
        await retriever.aclose()
        await dispose_db_engine()
    return 0


def main() -> int:
    args = parse_args()
    os.chdir(REPO_ROOT)

    if args.mode == "production":
        return asyncio.run(run_production_diagnostic(args))

    print_title("LEGACY MIETIC AUDIT — NON-PRODUCTION SYNTHETIC CASE")
    print_wrapped("database_backend", "PostgreSQL + pgvector (read-only SELECT)")
    print_wrapped("table", TABLE_NAME)
    print_wrapped("production_retriever_uses_this_table", "false")
    print_wrapped("dense_metric", "cosine distance; similarity = clamp(1 - distance, 0, 1)")
    print_wrapped("embedding_model", args.model)
    print_wrapped("expected_embedding_dimension", EXPECTED_EMBEDDING_DIMENSION)
    print_wrapped("top_k", args.top_k)
    print_wrapped("current_score_threshold", f"{args.threshold:.2f}")
    print_wrapped("production_sparse_keyword_retrieval", "disabled / not called")
    print_wrapped("database_mutation", "none")

    model_started = time.perf_counter()
    embedder = load_embedder(args.model)
    model_load_ms = (time.perf_counter() - model_started) * 1000
    if embedder.dimension != EXPECTED_EMBEDDING_DIMENSION:
        raise RuntimeError(
            f"Model trả về {embedder.dimension} chiều nhưng database yêu cầu "
            f"{EXPECTED_EMBEDDING_DIMENSION}."
        )
    print_wrapped("embedding_backend", embedder.backend_name)
    print_wrapped("actual_embedding_dimension", embedder.dimension)
    print_wrapped("model_load_latency_ms", f"{model_load_ms:.1f}")

    engine = build_read_only_engine()
    try:
        profile = fetch_database_profile(engine)
        print_database_profile(profile)

        print_title("2. DENSE PGVECTOR RETRIEVAL RESULTS")
        channels = build_query_channels()
        runs = [
            run_dense_retrieval(engine, embedder, channel, args.top_k)
            for channel in channels
        ]
        for run in runs:
            print_dense_run(run, args.threshold)

        sparse_terms = [
            "abdominal_pain",
            "right_lower_quadrant_pain",
            "fever",
            "nausea",
            "vomiting",
            "tachycardia",
            "hypotension",
        ]
        sparse_results = run_sparse_keyword_diagnostic(engine, sparse_terms, args.top_k)
        print_sparse_diagnostic(sparse_terms, sparse_results)
        print_cross_channel_comparison(runs)
        print_interpretation(runs, args.threshold)
    finally:
        engine.dispose()
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except KeyboardInterrupt:
        print("\nĐã dừng theo yêu cầu người dùng.", file=sys.stderr)
        raise SystemExit(130) from None
    except Exception as exc:
        print(f"\nRAG diagnostic thất bại: {type(exc).__name__}: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc
