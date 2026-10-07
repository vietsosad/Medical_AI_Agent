#!/usr/bin/env python3
"""Validate and quarantine MIETIC as case examples, never protocol evidence.

The command is dry-run by default. Use ``--apply`` only after reviewing the
audit summary and confirming a database snapshot exists. Embedding/model
failures abort the migration; dummy vectors are prohibited.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
from collections import Counter
from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from sqlalchemy import select
from sqlmodel import Session, SQLModel


REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from src.config import get_settings  # noqa: E402
from src.models.db_models import TriageCaseExample  # noqa: E402
from src.services.db import sync_engine  # noqa: E402


PARSER_VERSION = "mietic-quarantine-v2"
DATASET_VERSION = "MIETIC_v1"
ESI_PATTERN = re.compile(
    r"(?i)\bESI(?:\s+Level\s+|\s*[-:]\s*|\s+)([1-5])\b"
)
CONTROLLED_KEYWORDS: dict[str, tuple[str, ...]] = {
    "myocardial_infarction": (
        r"\bmyocardial\s+infarction\b",
        r"\bacute\s+coronary\s+syndrome\b",
    ),
    "dyspnea": (
        r"\bdyspnea\b",
        r"\bshortness\s+of\s+breath\b",
        r"\brespiratory\s+distress\b",
    ),
    "cardiac_arrest": (
        r"\bcardiac\s+arrest\b",
        r"\bventricular\s+fibrillation\s+arrest\b",
    ),
    "abdominal_pain": (r"\babdominal\s+pain\b",),
    "chest_pain": (r"\bchest\s+pain\b",),
    "fever": (r"\bfever\b", r"\bfebrile\b"),
    "nausea": (r"\bnausea\b",),
    "vomiting": (r"\bvomit(?:ing|ed|s)?\b",),
    "diarrhea": (r"\bdiarrhea\b",),
}


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
    rejected_ambiguous_esi: int = 0
    rejected_missing_esi: int = 0
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
    parser.add_argument(
        "jsonl_path",
        nargs="?",
        default="data/MIETIC_v1.jsonl",
    )
    parser.add_argument("--batch-size", type=int, default=100)
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Write validated rows to triage_case_examples.",
    )
    args = parser.parse_args()
    if args.batch_size < 1:
        parser.error("--batch-size must be positive")
    return args


def parse_unique_esi(instruction: str, output: str) -> int | None:
    """Parse ESI 1-5 from structured task text; reject unresolved conflicts."""
    instruction_levels = {int(value) for value in ESI_PATTERN.findall(instruction)}
    output_levels = {int(value) for value in ESI_PATTERN.findall(output)}
    if len(output_levels) == 1:
        output_level = next(iter(output_levels))
        if len(instruction_levels) == 1 and output_level not in instruction_levels:
            return None
        return output_level
    if len(output_levels) > 1:
        return None

    # Some ESI-1 tasks phrase the decision as a life-saving-intervention
    # boolean instead of spelling out the label. Accept only an explicit
    # positive conclusion; the task prompt alone is never treated as a label.
    if instruction_levels == {1}:
        lowered = output.lower()
        negative = re.search(
            r"(?:does\s+not|do\s+not|not)\s+require\s+immediate\s+life[- ]saving",
            lowered,
        )
        positive = re.search(
            r"(?:requires?|required|need(?:s|ed)?)\s+(?:an?\s+)?immediate\s+life[- ]saving",
            lowered,
        )
        if positive and not negative:
            return 1
    return None


def extract_controlled_keywords(text: str) -> list[str]:
    """Use phrase/word-boundary matchers; never test unsafe substrings like 'mi'."""
    lowered = text.lower()
    return [
        keyword
        for keyword, patterns in CONTROLLED_KEYWORDS.items()
        if any(re.search(pattern, lowered) for pattern in patterns)
    ]


def validate_record(data: dict[str, Any], line_number: int) -> ValidatedCase | None:
    required = ("instruction", "input", "output")
    if not all(isinstance(data.get(key), str) and data[key].strip() for key in required):
        return None
    esi_level = parse_unique_esi(data["instruction"], data["output"])
    if esi_level is None:
        return None
    patient_input = data["input"].strip()
    output = data["output"].strip()
    page_content = f"Symptoms: {patient_input}\nAnalysis: {output}"
    content_hash = hashlib.sha256(page_content.encode("utf-8")).hexdigest()
    source_record_id = f"mietic_{line_number:05d}"
    keywords = extract_controlled_keywords(patient_input)
    return ValidatedCase(
        source_record_id=source_record_id,
        page_content=page_content,
        content_hash=content_hash,
        esi_level=esi_level,
        keywords=keywords,
        metadata={
            "source_record_id": source_record_id,
            "source": DATASET_VERSION,
            "dataset_version": DATASET_VERSION,
            "parser_version": PARSER_VERSION,
            "document_type": "case_example",
            "validation_status": "not_protocol",
            "esi_level": esi_level,
            "provenance": f"MIETIC source record {source_record_id}",
        },
    )


def iter_validated_cases(path: Path, report: AuditReport) -> Iterator[ValidatedCase]:
    seen_hashes: set[str] = set()
    with path.open(encoding="utf-8") as source:
        for line_number, line in enumerate(source, start=1):
            if not line.strip():
                continue
            report.total += 1
            try:
                data = json.loads(line)
            except json.JSONDecodeError:
                report.rejected_missing_fields += 1
                continue
            if not all(data.get(key) for key in ("instruction", "input", "output")):
                report.rejected_missing_fields += 1
                continue
            instruction_levels = set(ESI_PATTERN.findall(str(data["instruction"])))
            output_levels = set(ESI_PATTERN.findall(str(data["output"])))
            validated = validate_record(data, line_number)
            if validated is None:
                if len(instruction_levels) > 1 or len(output_levels) > 1:
                    report.rejected_ambiguous_esi += 1
                else:
                    report.rejected_missing_esi += 1
                continue
            if validated.content_hash in seen_hashes:
                report.duplicate_content += 1
                continue
            seen_hashes.add(validated.content_hash)
            report.accepted += 1
            assert report.esi_distribution is not None
            assert report.keyword_distribution is not None
            report.esi_distribution[validated.esi_level] += 1
            report.keyword_distribution.update(validated.keywords)
            yield validated


def load_embedder() -> tuple[Any, str, str]:
    """Load a pinned, real embedder or fail before opening a write transaction."""
    try:
        from langchain_huggingface import HuggingFaceEmbeddings
    except ImportError as exc:
        raise RuntimeError(
            "langchain_huggingface is required; dummy embeddings are prohibited"
        ) from exc

    settings = get_settings()
    model_name = settings.embedding_model_name
    revision = settings.embedding_model_revision.strip()
    if not revision:
        raise RuntimeError(
            "EMBEDDING_MODEL_REVISION must be pinned before --apply"
        )
    embedder = HuggingFaceEmbeddings(
        model_name=model_name,
        model_kwargs={"revision": revision},
    )
    probe = embedder.embed_query("embedding dimension validation")
    if len(probe) != 1024 or len(set(round(value, 8) for value in probe)) <= 1:
        raise RuntimeError("Embedding probe is invalid or has the wrong dimension")
    return embedder, model_name, revision


def migrate(
    cases: list[ValidatedCase],
    report: AuditReport,
    batch_size: int,
) -> None:
    embedder, model_name, revision = load_embedder()
    SQLModel.metadata.create_all(
        sync_engine,
        tables=[TriageCaseExample.__table__],
    )
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
            vectors = embedder.embed_documents(
                [case.page_content for case in pending]
            )
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
    print("MIETIC quarantine audit")
    print(f"  mode: {'APPLY' if apply else 'DRY_RUN'}")
    print(f"  total_records: {report.total}")
    print(f"  accepted_unique: {report.accepted}")
    print(f"  rejected_missing_fields: {report.rejected_missing_fields}")
    print(f"  rejected_ambiguous_esi: {report.rejected_ambiguous_esi}")
    print(f"  rejected_missing_esi: {report.rejected_missing_esi}")
    print(f"  duplicate_content: {report.duplicate_content}")
    print(f"  esi_distribution: {dict(sorted((report.esi_distribution or {}).items()))}")
    print(f"  keyword_distribution: {dict((report.keyword_distribution or {}).most_common())}")
    print(f"  existing_rows: {report.existing_rows}")
    print(f"  inserted_rows: {report.inserted}")
    print("  evidence_eligible: false (document_type=case_example)")


def main() -> int:
    args = parse_args()
    os.chdir(REPO_ROOT)
    path = Path(args.jsonl_path)
    if not path.is_absolute():
        path = REPO_ROOT / path
    if not path.exists():
        raise FileNotFoundError(path)

    report = AuditReport()
    cases = list(iter_validated_cases(path, report))
    if args.apply:
        migrate(cases, report, args.batch_size)
    print_report(report, apply=args.apply)
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"Migration aborted: {type(exc).__name__}: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc
