#!/usr/bin/env python3
"""Evaluate VI/EN/sparse/fused protocol retrieval on an approved gold set.

The evaluator refuses pending or incomplete clinical judgments. It never
converts observed similarities into a threshold and never writes to the
clinical database.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import math
import os
import sys
import time
from pathlib import Path
from statistics import mean
from typing import Any

from pydantic import BaseModel, Field, model_validator


REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

os.environ.setdefault("HF_HUB_OFFLINE", "1")
os.environ.setdefault("TRANSFORMERS_OFFLINE", "1")

from src.services.db import dispose_db_engine  # noqa: E402
from src.services.rag.hybrid_retriever import (  # noqa: E402
    ClinicalHybridRetriever,
)


class RelevanceJudgment(BaseModel):
    citation_id: str = Field(min_length=1)
    relevance: int = Field(ge=0, le=2)
    reviewer: str = Field(min_length=3)
    reviewed_at: str = Field(min_length=10)


class BenchmarkCase(BaseModel):
    case_id: str
    symptom_cluster: str
    population: str
    query_vi: str
    query_en: str
    sparse_terms: list[str]
    relevance_judgments: list[RelevanceJudgment]

    @model_validator(mode="after")
    def require_positive_relevance(self) -> BenchmarkCase:
        if not any(item.relevance > 0 for item in self.relevance_judgments):
            raise ValueError(
                f"{self.case_id} has no clinician-approved relevant citation"
            )
        return self


class Benchmark(BaseModel):
    benchmark_version: str
    clinical_review_status: str
    reviewed_by: str | None
    reviewed_at: str | None
    cases: list[BenchmarkCase] = Field(min_length=1)

    @model_validator(mode="after")
    def require_approval(self) -> Benchmark:
        if self.clinical_review_status != "APPROVED":
            raise ValueError("benchmark is not clinically approved")
        if not self.reviewed_by or not self.reviewed_at:
            raise ValueError("approved benchmark requires reviewer and review time")
        return self


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "benchmark_path",
        nargs="?",
        type=Path,
        default=Path("eval/triage_retrieval_benchmark.json"),
    )
    parser.add_argument("--top-k", type=int, default=5)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    if args.top_k < 1 or args.top_k > 50:
        parser.error("--top-k must be in 1..50")
    return args


def ranked_ids(documents: list[Any]) -> list[str]:
    return [
        str(document.metadata.get("citation_id"))
        for document in documents
        if document.metadata.get("citation_id")
    ]


def metric_row(
    ids: list[str],
    judgments: dict[str, int],
    top_k: int,
) -> dict[str, float | int]:
    selected = ids[:top_k]
    relevant = {citation_id for citation_id, score in judgments.items() if score > 0}
    retrieved_relevant = relevant.intersection(selected)
    reciprocal_rank = 0.0
    for rank, citation_id in enumerate(selected, start=1):
        if citation_id in relevant:
            reciprocal_rank = 1.0 / rank
            break
    dcg = sum(
        (2 ** judgments.get(citation_id, 0) - 1) / math.log2(rank + 1)
        for rank, citation_id in enumerate(selected, start=1)
    )
    ideal_scores = sorted(judgments.values(), reverse=True)[:top_k]
    idcg = sum(
        (2 ** score - 1) / math.log2(rank + 1)
        for rank, score in enumerate(ideal_scores, start=1)
    )
    return {
        "recall_at_k": len(retrieved_relevant) / len(relevant),
        "mrr": reciprocal_rank,
        "ndcg_at_k": dcg / idcg if idcg else 0.0,
        "zero_result": int(not selected),
    }


def relevant_rank(ids: list[str], relevant: set[str]) -> int | None:
    for rank, citation_id in enumerate(ids, start=1):
        if citation_id in relevant:
            return rank
    return None


async def evaluate(benchmark: Benchmark, top_k: int) -> dict[str, Any]:
    retriever = ClinicalHybridRetriever(k_results=top_k)
    case_reports: list[dict[str, Any]] = []
    started = time.perf_counter()
    try:
        for case in benchmark.cases:
            case_started = time.perf_counter()
            result = await retriever.ainvoke_channels(
                query_vi=case.query_vi,
                query_en=case.query_en,
                sparse_terms=case.sparse_terms,
                symptom_cluster=case.symptom_cluster,
                population=case.population,
            )
            judgments = {
                item.citation_id: item.relevance
                for item in case.relevance_judgments
            }
            relevant = {
                citation_id
                for citation_id, relevance in judgments.items()
                if relevance > 0
            }
            channel_ids = {
                channel: ranked_ids(documents)
                for channel, documents in result.channel_documents.items()
            }
            channel_ids["fused"] = ranked_ids(result.documents)
            metrics = {
                channel: metric_row(ids, judgments, top_k)
                for channel, ids in channel_ids.items()
            }
            vi_rank = relevant_rank(channel_ids.get("vi_dense", []), relevant)
            en_rank = relevant_rank(channel_ids.get("en_dense", []), relevant)
            case_reports.append({
                "case_id": case.case_id,
                "metrics": metrics,
                "cross_language_rank_delta": (
                    vi_rank - en_rank
                    if vi_rank is not None and en_rank is not None
                    else None
                ),
                "channel_runtime": result.channels,
                "degraded_modes": result.degraded_modes,
                "latency_ms": round(
                    (time.perf_counter() - case_started) * 1000,
                    2,
                ),
            })
    finally:
        await retriever.aclose()
        await dispose_db_engine()

    channel_names = sorted({
        channel
        for report in case_reports
        for channel in report["metrics"]
    })
    aggregate = {
        channel: {
            metric: round(mean([
                float(report["metrics"][channel][metric])
                for report in case_reports
                if channel in report["metrics"]
            ]), 6)
            for metric in ("recall_at_k", "mrr", "ndcg_at_k", "zero_result")
        }
        for channel in channel_names
    }
    return {
        "benchmark_version": benchmark.benchmark_version,
        "top_k": top_k,
        "case_count": len(case_reports),
        "aggregate": aggregate,
        "cases": case_reports,
        "total_latency_ms": round((time.perf_counter() - started) * 1000, 2),
        "threshold_selected": False,
        "database_mutation": False,
    }


def main() -> int:
    args = parse_args()
    path = args.benchmark_path
    if not path.is_absolute():
        path = REPO_ROOT / path
    benchmark = Benchmark.model_validate_json(path.read_text(encoding="utf-8"))
    report = asyncio.run(evaluate(benchmark, args.top_k))
    rendered = json.dumps(report, ensure_ascii=False, indent=2)
    print(rendered)
    if args.output:
        output = args.output
        if not output.is_absolute():
            output = REPO_ROOT / output
        output.write_text(rendered + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(
            f"Retrieval evaluation aborted: {type(exc).__name__}: {exc}",
            file=sys.stderr,
        )
        raise SystemExit(1) from exc
