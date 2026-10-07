#!/usr/bin/env python3
"""Validate and quarantine MIETIC as case examples, using LLM for extraction.

The command is dry-run by default. Use ``--apply`` only after reviewing the
audit summary and confirming a database snapshot exists. Embedding/model
failures abort the migration; dummy vectors are prohibited.

This version uses LLM for robust extraction of ESI levels and keywords,
and OpenAI's cost-effective embeddings (text-embedding-3-small).
"""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import os
import sys
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlmodel import Session, SQLModel

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from src.config import get_settings
from src.models.db_models import TriageCaseExample
from src.services.db import sync_engine
from src.services.llm_provider import get_resilient_llm

PARSER_VERSION = "mietic-llm-v1"
DATASET_VERSION = "MIETIC_v1"

class ClinicalExtraction(BaseModel):
    esi_level: int = Field(description="The Emergency Severity Index (ESI) level from 1 to 5 based on the case. 1 is most urgent, 5 is least urgent.")
    keywords: list[str] = Field(description="List of key clinical symptoms, conditions, or keywords (e.g., 'chest pain', 'fever', 'dyspnea'). Max 5 keywords.")

@dataclass(frozen=True)
class ValidatedCase:
    source_record_id: str
    page_content: str
    content_hash: str
    esi_level: int
    keywords: list[str]
    metadata: dict[str, Any]

@dataclass
class AuditReport:
    total: int = 0
    accepted: int = 0
    rejected_missing_fields: int = 0
    rejected_llm_failure: int = 0
    duplicate_content: int = 0
    existing_rows: int = 0
    inserted: int = 0
    esi_distribution: Counter[int] | None = None
    keyword_distribution: Counter[str] | None = None

    def __post_init__(self) -> None:
        self.esi_distribution = Counter()
        self.keyword_distribution = Counter()

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("jsonl_path", nargs="?", default="data/MIETIC_v1.jsonl")
    parser.add_argument("--batch-size", type=int, default=50) # Smaller batch size for LLM API limits
    parser.add_argument("--apply", action="store_true", help="Write validated rows to database.")
    args = parser.parse_args()
    if args.batch_size < 1:
        parser.error("--batch-size must be positive")
    return args

async def extract_with_llm(instruction: str, patient_input: str, output: str) -> ClinicalExtraction | None:
    try:
        # Sử dụng tier="small" (ví dụ: gpt-4o-mini hoặc gemini-flash) để tối ưu chi phí
        llm = get_resilient_llm(tier="small")
        
        # Đảm bảo LLM hiện tại hỗ trợ structured output (Mock AI sẽ không hỗ trợ)
        if hasattr(llm, "with_structured_output"):
            structured_llm = llm.with_structured_output(ClinicalExtraction)
            prompt = (
                "Extract the ESI level and key medical symptoms/conditions from this clinical case.\n\n"
                f"Instruction: {instruction}\n"
                f"Patient Input: {patient_input}\n"
                f"Analysis: {output}"
            )
            result = await structured_llm.ainvoke(prompt)
            return result
        else:
            print("Warning: Configured LLM does not support structured output. Make sure you set an API Key.")
            return None
    except Exception as e:
        print(f"LLM extraction error: {e}")
        return None

async def validate_record(data: dict[str, Any], line_number: int) -> ValidatedCase | None:
    required = ("instruction", "input", "output")
    if not all(isinstance(data.get(key), str) and data[key].strip() for key in required):
        return None
        
    patient_input = data["input"].strip()
    output = data["output"].strip()
    
    extracted = await extract_with_llm(data["instruction"], patient_input, output)
    if not extracted or extracted.esi_level not in [1, 2, 3, 4, 5]:
        return None

    page_content = f"Symptoms: {patient_input}\nAnalysis: {output}"
    content_hash = hashlib.sha256(page_content.encode("utf-8")).hexdigest()
    source_record_id = f"mietic_{line_number:05d}"
    
    # Chuẩn hóa keywords về chữ thường
    keywords = [k.lower() for k in extracted.keywords]

    return ValidatedCase(
        source_record_id=source_record_id,
        page_content=page_content,
        content_hash=content_hash,
        esi_level=extracted.esi_level,
        keywords=keywords,
        metadata={
            "source_record_id": source_record_id,
            "source": DATASET_VERSION,
            "dataset_version": DATASET_VERSION,
            "parser_version": PARSER_VERSION,
            "document_type": "case_example",
            "validation_status": "not_protocol",
            "esi_level": extracted.esi_level,
            "provenance": f"MIETIC source record {source_record_id} (LLM Extracted)",
        },
    )

async def process_cases_async(path: Path, report: AuditReport) -> list[ValidatedCase]:
    seen_hashes: set[str] = set()
    valid_cases = []
    lines_data = []
    
    with path.open(encoding="utf-8") as source:
        for line_number, line in enumerate(source, start=1):
            if not line.strip():
                continue
            report.total += 1
            try:
                data = json.loads(line)
                lines_data.append((line_number, data))
            except json.JSONDecodeError:
                report.rejected_missing_fields += 1

    print(f"Starting LLM extraction for {len(lines_data)} records...")
    
    # Sử dụng Semaphore để giới hạn số lượng gọi API LLM đồng thời tránh rate limit
    sem = asyncio.Semaphore(10)
    
    async def bounded_validate(data, line_num):
        async with sem:
            return await validate_record(data, line_num)
            
    tasks = [bounded_validate(data, line_num) for line_num, data in lines_data]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    
    for res in results:
        if isinstance(res, Exception):
            print(f"Error during validation: {res}")
            report.rejected_llm_failure += 1
            continue
            
        if res is None:
            report.rejected_llm_failure += 1
            continue
            
        if res.content_hash in seen_hashes:
            report.duplicate_content += 1
            continue
            
        seen_hashes.add(res.content_hash)
        report.accepted += 1
        
        assert report.esi_distribution is not None
        assert report.keyword_distribution is not None
        report.esi_distribution[res.esi_level] += 1
        report.keyword_distribution.update(res.keywords)
        
        valid_cases.append(res)
            
    return valid_cases

def load_embedder() -> tuple[Any, str, str]:
    """Load OpenAI Embeddings (text-embedding-3-small) with reduced dimensions (1024)."""
    try:
        from langchain_openai import OpenAIEmbeddings
    except ImportError as exc:
        raise RuntimeError("langchain_openai is required for OpenAI embeddings.") from exc

    settings = get_settings()
    if not settings.openai_api_key:
        raise RuntimeError("OPENAI_API_KEY is missing in settings. Cannot use OpenAI embeddings.")

    model_name = "text-embedding-3-small"
    revision = "v1"
    
    embedder = OpenAIEmbeddings(
        model=model_name,
        api_key=settings.openai_api_key,
        dimensions=1024  # Rất quan trọng: truncate về 1024 để khớp với Schema của TriageCaseExample
    )
    
    probe = embedder.embed_query("embedding dimension validation")
    if len(probe) != 1024 or len(set(round(value, 8) for value in probe)) <= 1:
        raise RuntimeError(f"Embedding probe invalid or wrong dimension: {len(probe)}")
        
    return embedder, model_name, revision

def migrate(cases: list[ValidatedCase], report: AuditReport, batch_size: int) -> None:
    embedder, model_name, revision = load_embedder()
    SQLModel.metadata.create_all(sync_engine, tables=[TriageCaseExample.__table__])
    
    print("\nStarting OpenAI embeddings generation and DB insertion...")
    for batch_start in range(0, len(cases), batch_size):
        batch = cases[batch_start : batch_start + batch_size]
        hashes = [case.content_hash for case in batch]
        
        with Session(sync_engine) as session:
            existing = set(
                session.exec(
                    select(TriageCaseExample.content_hash).where(
                        TriageCaseExample.content_hash.in_(hashes)
                    )
                ).all()
            )
            report.existing_rows += len(existing)
            pending = [case for case in batch if case.content_hash not in existing]
            if not pending:
                continue
                
            vectors = embedder.embed_documents([case.page_content for case in pending])
            if any(len(vector) != 1024 for vector in vectors):
                raise RuntimeError("Embedding dimension mismatch; transaction aborted")
                
            session.add_all([
                TriageCaseExample(
                    source_record_id=case.source_record_id,
                    source=DATASET_VERSION,
                    dataset_version=DATASET_VERSION,
                    parser_version=PARSER_VERSION,
                    embedding_model=model_name,
                    embedding_revision=revision,
                    content_hash=case.content_hash,
                    page_content=case.page_content,
                    embedding=vector,
                    metadata_json={
                        **case.metadata,
                        "embedding_model": model_name,
                        "embedding_revision": revision,
                        "content_hash": case.content_hash,
                    },
                    keywords=case.keywords,
                    document_type="case_example",
                    validation_status="not_protocol",
                )
                for case, vector in zip(pending, vectors, strict=True)
            ])
            session.commit()
            report.inserted += len(pending)

def print_report(report: AuditReport, *, apply: bool) -> None:
    print("\nMIETIC LLM-powered quarantine audit")
    print(f"  mode: {'APPLY' if apply else 'DRY_RUN'}")
    print(f"  total_records: {report.total}")
    print(f"  accepted_unique: {report.accepted}")
    print(f"  rejected_missing_fields: {report.rejected_missing_fields}")
    print(f"  rejected_llm_failure: {report.rejected_llm_failure}")
    print(f"  duplicate_content: {report.duplicate_content}")
    print(f"  esi_distribution: {dict(sorted((report.esi_distribution or {}).items()))}")
    
    top_keywords = dict((report.keyword_distribution or {}).most_common(20))
    print(f"  top_keywords: {top_keywords}")
    print(f"  existing_rows: {report.existing_rows}")
    print(f"  inserted_rows: {report.inserted}")
    print("  evidence_eligible: false (document_type=case_example)")

async def async_main(args: argparse.Namespace, report: AuditReport, path: Path):
    cases = await process_cases_async(path, report)
    if args.apply:
        migrate(cases, report, args.batch_size)
    print_report(report, apply=args.apply)

def main() -> int:
    args = parse_args()
    os.chdir(REPO_ROOT)
    path = Path(args.jsonl_path)
    if not path.is_absolute():
        path = REPO_ROOT / path
    if not path.exists():
        raise FileNotFoundError(path)

    report = AuditReport()
    asyncio.run(async_main(args, report, path))
    return 0

if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"Migration aborted: {type(exc).__name__}: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc
