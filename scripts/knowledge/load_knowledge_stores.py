"""Embed both corpora with one model and load them into Postgres.

The two stores previously lived in different vector spaces — BGE-M3 at 1024
dims for ESI, a 768-dim encoder for MIETIC — which made a shared query vector
impossible and produced a hard `different vector dimensions` error at runtime.
Both are rebuilt here with text-embedding-3-large at 1024 dims so one query
embedding serves both.

Subcommands:
    esi      re-embed esi_knowledge_documents in place (content untouched)
    mietic   create and populate mietic_cases from the enriched artifact
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import tiktoken  # noqa: E402
from sqlalchemy import text as sql_text  # noqa: E402
from sqlmodel import Session, SQLModel, select  # noqa: E402

from src.models.db_models import ESIKnowledgeDocument, MieticCase  # noqa: E402
from src.services.db import sync_engine  # noqa: E402
from src.services.embeddings import (  # noqa: E402
    EMBEDDING_DIMENSIONS,
    EMBEDDING_MODEL,
    get_embedding_service,
)

EMBED_PRICE_PER_1M = 0.13
BATCH = 128


def price(texts: list[str]) -> tuple[int, float]:
    enc = tiktoken.get_encoding("cl100k_base")
    tokens = sum(len(enc.encode(t)) for t in texts)
    return tokens, tokens * EMBED_PRICE_PER_1M / 1e6


def guard(texts: list[str], ceiling: float, label: str) -> bool:
    tokens, cost = price(texts)
    print(f"{label}: {len(texts)} texts, {tokens:,} tokens, projected ${cost:.4f} (ceiling ${ceiling:.2f})")
    if cost > ceiling:
        print("REFUSING: projected embedding cost exceeds the ceiling.")
        return False
    return True


def embed_all(texts: list[str]) -> list[list[float]]:
    service = get_embedding_service()
    vectors: list[list[float]] = []
    for start in range(0, len(texts), BATCH):
        chunk = texts[start : start + BATCH]
        vectors.extend(service.embed_documents(chunk))
        print(f"  embedded {min(start + BATCH, len(texts))}/{len(texts)}", flush=True)
    return vectors


def run_esi(args: argparse.Namespace) -> int:
    """Replace every ESI vector. Content, ids and provenance are not touched."""
    with Session(sync_engine) as session:
        rows = session.exec(select(ESIKnowledgeDocument)).all()
        texts = [row.retrieval_text for row in rows]
        if not guard(texts, args.max_api_cost_usd, "ESI re-embed"):
            return 2
        if args.estimate_only:
            return 0
        vectors = embed_all(texts)
        for row, vector in zip(rows, vectors, strict=True):
            row.embedding = vector
            session.add(row)
        session.commit()
    print(f"ESI: re-embedded {len(rows)} documents with {EMBEDDING_MODEL}@{EMBEDDING_DIMENSIONS}")
    return 0


def run_mietic(args: argparse.Namespace) -> int:
    path = Path(args.artifact)
    records = [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    SQLModel.metadata.create_all(sync_engine, tables=[MieticCase.__table__])

    # Reuse the vector of any case whose retrieval text is byte-identical.
    # Corrections to labels or assessments do not change what was embedded, and
    # re-embedding an unchanged corpus is money spent to reproduce the same
    # numbers.
    # Read through the ORM so pgvector hands back a list rather than its text
    # representation.
    existing: dict[str, list[float]] = {}
    with Session(sync_engine) as session:
        for sha, vector in session.exec(
            select(MieticCase.retrieval_text_sha256, MieticCase.embedding)
        ).all():
            if vector is not None:
                existing[sha] = list(vector)

    pending = [r for r in records if r["retrieval_text_sha256"] not in existing]
    print(f"MIETIC: {len(records)} cases, {len(existing)} cached vectors, {len(pending)} to embed")
    if not guard([r["retrieval_text"] for r in pending], args.max_api_cost_usd, "MIETIC embed"):
        return 2
    if args.estimate_only:
        return 0

    if pending:
        fresh = embed_all([r["retrieval_text"] for r in pending])
        for record, vector in zip(pending, fresh, strict=True):
            existing[record["retrieval_text_sha256"]] = vector
    vectors = [existing[r["retrieval_text_sha256"]] for r in records]

    with Session(sync_engine) as session:
        # Staging semantics: a re-run replaces the corpus rather than
        # accumulating a second copy of it.
        session.exec(sql_text("TRUNCATE TABLE mietic_cases"))
        for record, vector in zip(records, vectors, strict=True):
            session.add(
                MieticCase(
                    case_id=record["case_id"],
                    presentation_text=record["presentation_text"],
                    presentation_sha256=record["presentation_sha256"],
                    age_years=record["age_years"],
                    age_band=record["age_band"],
                    sex=record["sex"],
                    vitals=record["vitals"],
                    clinical_features=record.get("clinical_features", []),
                    symptom_concepts=record.get("symptom_concepts", []),
                    assessments=record["assessments"],
                    candidate_esi_levels=record["candidate_esi_levels"],
                    label_status=record["label_status"],
                    validated_esi_level=record["validated_esi_level"],
                    retrieval_text=record["retrieval_text"],
                    retrieval_text_sha256=record["retrieval_text_sha256"],
                    embedding=vector,
                    source_record_ids=record["source_record_ids"],
                    source_record_count=record["source_record_count"],
                    dataset_version=record["dataset_version"],
                    parser_version=record["parser_version"],
                    llm_model=record.get("llm_model"),
                    llm_prompt_version=record.get("llm_prompt_version"),
                    embedding_model=EMBEDDING_MODEL,
                    embedding_dimensions=EMBEDDING_DIMENSIONS,
                )
            )
        session.commit()
    print(f"MIETIC: loaded {len(records)} canonical cases into mietic_cases")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)
    for name in ("esi", "mietic"):
        p = sub.add_parser(name)
        p.add_argument("--max-api-cost-usd", type=float, default=0.50)
        p.add_argument("--estimate-only", action="store_true")
        if name == "mietic":
            p.add_argument(
                "--artifact",
                default="data/knowledge/mietic_v2/canonical_cases.enriched.jsonl",
            )
    args = parser.parse_args()
    return run_esi(args) if args.command == "esi" else run_mietic(args)


if __name__ == "__main__":
    raise SystemExit(main())
