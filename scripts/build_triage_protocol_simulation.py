#!/usr/bin/env python3
"""Build a review-only triage protocol simulation corpus from local PDFs.

The pipeline deliberately stops before embedding or database ingestion:

1. Extract page-addressable text and write an immutable source registry.
2. Prepare OpenAI Batch API requests for structured candidate extraction.
3. Submit/download the extraction batch only when explicitly requested.
4. Deterministically reject candidates that lose provenance or mix triage systems.
5. Prepare a second, selective verification batch for high-risk candidates.
6. Build a package whose final status is always ``pending_human_review``.

No command can mark a protocol clinically approved. ``OPENAI_API_KEY`` is read
from ``.env`` through ``src.config.Settings`` and is never written to output.

Examples (run later, after reviewing this code):

    python scripts/build_triage_protocol_simulation.py extract
    python scripts/build_triage_protocol_simulation.py prepare-extraction
    python scripts/build_triage_protocol_simulation.py submit-extraction
    python scripts/build_triage_protocol_simulation.py download-extraction
    python scripts/build_triage_protocol_simulation.py parse-extraction
    python scripts/build_triage_protocol_simulation.py prepare-verification
    python scripts/build_triage_protocol_simulation.py submit-verification
    python scripts/build_triage_protocol_simulation.py download-verification
    python scripts/build_triage_protocol_simulation.py parse-verification
    python scripts/build_triage_protocol_simulation.py build-review-package
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
import unicodedata
from collections import defaultdict
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Literal, TypeVar

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    ValidationError,
    model_validator,
)


REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from src.config import get_settings  # noqa: E402


PIPELINE_VERSION = "triage-protocol-simulation-v1"
PROMPT_VERSION = "triage-protocol-extract-v1"
VERIFICATION_PROMPT_VERSION = "triage-protocol-verify-v1"
BATCH_ENDPOINT = "/v1/responses"

Population = Literal[
    "adult",
    "pediatric",
    "geriatric",
    "all_populations",
    "age_12_plus",
    "age_under_12",
]
ClinicalUse = Literal[
    "ESI_DECISION_SUPPORT",
    "EMERGENCY_RED_FLAG",
    "ROUTINE_TRIAGE",
    "QUESTION_GUIDANCE",
    "DEFINITION_REFERENCE",
]
TriageSystem = Literal["ESI_V4", "BYT_QD79_2026", "WHO_IITT_3_COLOR"]


@dataclass(frozen=True)
class SourceSpec:
    source_id: str
    relative_pdf: Path
    title: str
    issuing_body: str
    source_family: str
    triage_system: TriageSystem
    allowed_clinical_uses: tuple[ClinicalUse, ...]
    default_populations: tuple[Population, ...]
    license_reference: str
    force_layout_review: bool = False


SOURCE_SPECS: tuple[SourceSpec, ...] = (
    SourceSpec(
        source_id="AHRQ_ESI_V4_2012",
        relative_pdf=Path(
            "ena/AHRQ_ESI_v4_2012_Implementation_Handbook.pdf"
        ),
        title="Emergency Severity Index Version 4 Implementation Handbook",
        issuing_body="Agency for Healthcare Research and Quality",
        source_family="ESI_V4",
        triage_system="ESI_V4",
        allowed_clinical_uses=(
            "ESI_DECISION_SUPPORT",
            "QUESTION_GUIDANCE",
            "DEFINITION_REFERENCE",
        ),
        default_populations=("all_populations",),
        license_reference="Source copyright/license page; legal review required",
    ),
    SourceSpec(
        source_id="BYT_QD79_2026",
        relative_pdf=Path("vn_byt/BYT_QD79_2026_Huong_dan_cap_cuu.pdf"),
        title=(
            "Quyết định 79/QĐ-BYT: Hướng dẫn chỉ định nhập viện đối với "
            "người bệnh trong tình trạng cấp cứu"
        ),
        issuing_body="Bộ Y tế Việt Nam",
        source_family="BYT_QD79_2026",
        triage_system="BYT_QD79_2026",
        allowed_clinical_uses=(
            "EMERGENCY_RED_FLAG",
            "QUESTION_GUIDANCE",
            "DEFINITION_REFERENCE",
        ),
        default_populations=("all_populations",),
        license_reference="Official decision/source reuse review required",
        force_layout_review=True,
    ),
    SourceSpec(
        source_id="WHO_IITT_AGE_12_PLUS",
        relative_pdf=Path("who_iitt/WHO_IITT_Age_12_Plus.pdf"),
        title="WHO Interagency Integrated Triage Tool: Age 12 years and older",
        issuing_body="World Health Organization",
        source_family="WHO_IITT",
        triage_system="WHO_IITT_3_COLOR",
        allowed_clinical_uses=(
            "EMERGENCY_RED_FLAG",
            "ROUTINE_TRIAGE",
            "QUESTION_GUIDANCE",
        ),
        default_populations=("age_12_plus",),
        license_reference="CC BY-NC-SA 3.0 IGO; use-case review required",
        force_layout_review=True,
    ),
    SourceSpec(
        source_id="WHO_IITT_UNDER_12",
        relative_pdf=Path("who_iitt/WHO_IITT_Age_Under_12.pdf"),
        title="WHO Interagency Integrated Triage Tool: Age under 12 years",
        issuing_body="World Health Organization",
        source_family="WHO_IITT",
        triage_system="WHO_IITT_3_COLOR",
        allowed_clinical_uses=(
            "EMERGENCY_RED_FLAG",
            "ROUTINE_TRIAGE",
            "QUESTION_GUIDANCE",
        ),
        default_populations=("age_under_12",),
        license_reference="CC BY-NC-SA 3.0 IGO; use-case review required",
        force_layout_review=True,
    ),
    SourceSpec(
        source_id="WHO_IITT_REFERENCE_CARD",
        relative_pdf=Path("who_iitt/WHO_IITT_Reference_Card.pdf"),
        title="WHO Interagency Integrated Triage Tool Reference Card",
        issuing_body="World Health Organization",
        source_family="WHO_IITT",
        triage_system="WHO_IITT_3_COLOR",
        allowed_clinical_uses=(
            "EMERGENCY_RED_FLAG",
            "QUESTION_GUIDANCE",
            "DEFINITION_REFERENCE",
        ),
        default_populations=("all_populations",),
        license_reference="CC BY-NC-SA 3.0 IGO; use-case review required",
        force_layout_review=True,
    ),
)
SOURCE_BY_ID = {spec.source_id: spec for spec in SOURCE_SPECS}


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class SourceRegistryEntry(StrictModel):
    source_id: str
    title: str
    issuing_body: str
    source_family: str
    triage_system: TriageSystem
    local_path: str
    sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    file_size_bytes: int = Field(ge=1)
    page_count: int = Field(ge=1)
    license_reference: str
    license_review_status: Literal["required"]
    simulation_only: Literal[True]
    extracted_at: datetime


class SourceRegistry(StrictModel):
    registry_version: Literal[PIPELINE_VERSION]
    sources: list[SourceRegistryEntry] = Field(min_length=1)


class ExtractedPage(StrictModel):
    page_id: str
    source_id: str
    source_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    page_number: int = Field(ge=1)
    text: str
    extraction_method: Literal["pdf_text_layer"]
    quality_flags: list[str]
    requires_visual_review: bool


class EvidenceSpan(StrictModel):
    page: int = Field(ge=1)
    quote: str = Field(min_length=3, max_length=8_000)


class DecisionCriterion(StrictModel):
    criterion_original: str = Field(min_length=3, max_length=4_000)
    criterion_vi: str = Field(min_length=3, max_length=4_000)
    outcome: str = Field(min_length=1, max_length=200)
    evidence_page: int = Field(ge=1)
    evidence_quote: str = Field(min_length=3, max_length=8_000)
    numeric_thresholds: list[str] = Field(max_length=20)


class ProtocolCandidate(StrictModel):
    source_id: str
    title: str = Field(min_length=3, max_length=500)
    section: str = Field(min_length=1, max_length=500)
    page_start: int = Field(ge=1)
    page_end: int = Field(ge=1)
    triage_system: TriageSystem
    populations: list[Population] = Field(min_length=1, max_length=4)
    clinical_uses: list[ClinicalUse] = Field(min_length=1, max_length=5)
    esi_level: int | None
    iitt_priority: Literal["RED", "YELLOW", "GREEN"] | None
    summary_original_language: str = Field(min_length=3, max_length=8_000)
    summary_vi: str = Field(min_length=3, max_length=8_000)
    decision_criteria: list[DecisionCriterion] = Field(min_length=1, max_length=50)
    evidence_spans: list[EvidenceSpan] = Field(min_length=1, max_length=50)
    keywords: list[str] = Field(min_length=1, max_length=100)
    review_flags: list[str] = Field(max_length=30)

    @model_validator(mode="after")
    def validate_triage_system_fields(self) -> ProtocolCandidate:
        if self.page_end < self.page_start:
            raise ValueError("page_end must be greater than or equal to page_start")
        if self.esi_level is not None and self.esi_level not in {1, 2, 3, 4, 5}:
            raise ValueError("esi_level must be in 1..5")
        if self.triage_system != "ESI_V4" and self.esi_level is not None:
            raise ValueError("non-ESI sources cannot emit esi_level")
        if self.triage_system == "ESI_V4" and self.iitt_priority is not None:
            raise ValueError("ESI sources cannot emit IITT priority")
        if self.triage_system != "WHO_IITT_3_COLOR" and self.iitt_priority:
            raise ValueError("only WHO IITT may emit IITT priority")
        return self


class ExtractionEnvelope(StrictModel):
    source_id: str
    pages_seen: list[int] = Field(min_length=1)
    candidates: list[ProtocolCandidate] = Field(max_length=30)
    omitted_content_notes: list[str] = Field(max_length=30)


class CandidateRecord(StrictModel):
    candidate_id: str = Field(pattern=r"^[a-z0-9_]{12,160}$")
    citation_id: str
    source_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    pipeline_version: Literal[PIPELINE_VERSION]
    prompt_version: Literal[PROMPT_VERSION]
    extraction_model: str
    extraction_custom_id: str
    candidate: ProtocolCandidate
    deterministic_flags: list[str]
    risk_flags: list[str]
    validation_status: Literal["candidate"]


class VerificationIssue(StrictModel):
    code: str = Field(min_length=2, max_length=100)
    severity: Literal["warning", "error"]
    message: str = Field(min_length=3, max_length=2_000)


class CriterionCheck(StrictModel):
    criterion_index: int = Field(ge=0)
    source_supported: bool
    evidence_quote_exact: bool
    numeric_thresholds_preserved: bool
    notes: str = Field(max_length=2_000)


class VerificationEnvelope(StrictModel):
    candidate_id: str
    decision: Literal["llm_verified", "manual_review", "reject"]
    source_grounding_passed: bool
    triage_system_separation_passed: bool
    criterion_checks: list[CriterionCheck]
    issues: list[VerificationIssue]


class VerificationRecord(StrictModel):
    candidate_id: str
    verification_model: str
    verification_prompt_version: Literal[VERIFICATION_PROMPT_VERSION]
    decision: Literal["llm_verified", "manual_review", "reject"]
    source_grounding_passed: bool
    triage_system_separation_passed: bool
    criterion_checks: list[CriterionCheck]
    issues: list[VerificationIssue]


class ReviewPackageRecord(StrictModel):
    candidate_id: str
    citation_id: str
    source_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    candidate: ProtocolCandidate
    deterministic_flags: list[str]
    risk_flags: list[str]
    llm_verification: VerificationRecord | None
    review_status: Literal["pending_human_review", "blocked"]
    simulation_only: Literal[True]


class DemoAllowlistRecord(StrictModel):
    candidate_id: str
    citation_id: str
    source_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    pipeline_version: Literal[PIPELINE_VERSION]
    generated_at: datetime
    demo_status: Literal["demo_eligible_nonclinical"]
    review_method: Literal[
        "deterministic_and_llm_documentary_gate_without_clinician"
    ]
    simulation_only: Literal[True]
    clinical_approval: Literal[False]
    eligible_for_internal_demo_retrieval: Literal[True]
    public_distribution_allowed: Literal[False]
    license_review_required: Literal[True]
    candidate: ProtocolCandidate
    llm_verification: VerificationRecord
    allowed_uses: list[str]
    prohibited_uses: list[str]


class BatchJobState(StrictModel):
    pipeline_version: Literal[PIPELINE_VERSION]
    stage: Literal[
        "extraction",
        "verification",
        "repair",
        "repair_verification",
    ]
    batch_id: str
    input_file_id: str
    endpoint: Literal[BATCH_ENDPOINT]
    model: str
    input_path: str
    submitted_at: datetime
    output_file_id: str | None
    error_file_id: str | None
    status: str


@dataclass(frozen=True)
class WorkPaths:
    root: Path
    source_registry: Path
    extracted_pages: Path
    extraction_input: Path
    extraction_job: Path
    extraction_output: Path
    extraction_api_errors: Path
    extraction_retry_input: Path
    extraction_retry_job: Path
    extraction_retry_output: Path
    extraction_retry_api_errors: Path
    candidates: Path
    rejected_candidates: Path
    verification_input: Path
    verification_job: Path
    verification_output: Path
    verification_api_errors: Path
    verification_retry_input: Path
    verification_retry_job: Path
    verification_retry_output: Path
    verification_retry_api_errors: Path
    verification_parse_errors: Path
    verifications: Path
    review_package: Path
    review_summary: Path
    demo_allowlist: Path
    demo_review_queue: Path
    demo_excluded: Path
    demo_allowlist_summary: Path


def work_paths(root: Path) -> WorkPaths:
    batches = root / "batches"
    return WorkPaths(
        root=root,
        source_registry=root / "source_registry.json",
        extracted_pages=root / "extracted_pages.jsonl",
        extraction_input=batches / "extraction_input.jsonl",
        extraction_job=batches / "extraction_job.json",
        extraction_output=batches / "extraction_output.jsonl",
        extraction_api_errors=batches / "extraction_api_errors.jsonl",
        extraction_retry_input=batches / "extraction_retry_input.jsonl",
        extraction_retry_job=batches / "extraction_retry_job.json",
        extraction_retry_output=batches / "extraction_retry_output.jsonl",
        extraction_retry_api_errors=batches / "extraction_retry_api_errors.jsonl",
        candidates=root / "protocol_candidates.jsonl",
        rejected_candidates=root / "protocol_rejected.jsonl",
        verification_input=batches / "verification_input.jsonl",
        verification_job=batches / "verification_job.json",
        verification_output=batches / "verification_output.jsonl",
        verification_api_errors=batches / "verification_api_errors.jsonl",
        verification_retry_input=batches / "verification_retry_input.jsonl",
        verification_retry_job=batches / "verification_retry_job.json",
        verification_retry_output=batches / "verification_retry_output.jsonl",
        verification_retry_api_errors=batches / "verification_retry_api_errors.jsonl",
        verification_parse_errors=root / "protocol_verification_rejected.jsonl",
        verifications=root / "protocol_verifications.jsonl",
        review_package=root / "protocol_review_package.jsonl",
        review_summary=root / "protocol_review_summary.json",
        demo_allowlist=root / "protocol_demo_allowlist.jsonl",
        demo_review_queue=root / "protocol_demo_review_queue.jsonl",
        demo_excluded=root / "protocol_demo_excluded.jsonl",
        demo_allowlist_summary=root / "protocol_demo_allowlist_summary.json",
    )


ModelT = TypeVar("ModelT", bound=BaseModel)


def utc_now() -> datetime:
    return datetime.now(UTC)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def normalize_space(value: str) -> str:
    return " ".join(value.split())


def normalize_keyword(value: str) -> str:
    ascii_value = "".join(
        char
        for char in unicodedata.normalize("NFKD", value.lower())
        if not unicodedata.combining(char)
    ).replace("đ", "d")
    normalized = re.sub(r"[^a-z0-9]+", "_", ascii_value).strip("_")
    return normalized[:100]


def numeric_tokens(value: str) -> set[str]:
    tokens = re.findall(r"(?:<=|>=|<|>|≤|≥)?\s*\d+(?:[.,]\d+)?", value)
    return {
        re.sub(r"\s+", "", token).replace("≤", "<=").replace("≥", ">=")
        for token in tokens
    }


def atomic_write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.tmp")
    temporary.write_text(content, encoding="utf-8")
    os.replace(temporary, path)


def write_json(path: Path, payload: Any) -> None:
    atomic_write_text(
        path,
        json.dumps(payload, ensure_ascii=False, indent=2, default=str) + "\n",
    )


def write_jsonl(path: Path, rows: Iterable[Any]) -> int:
    serialized: list[str] = []
    for row in rows:
        if isinstance(row, BaseModel):
            payload = row.model_dump(mode="json")
        else:
            payload = row
        serialized.append(json.dumps(payload, ensure_ascii=False))
    atomic_write_text(path, "\n".join(serialized) + ("\n" if serialized else ""))
    return len(serialized)


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open(encoding="utf-8") as source:
        for line_number, line in enumerate(source, start=1):
            if not line.strip():
                continue
            try:
                payload = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValueError(f"{path}:{line_number}: invalid JSON") from exc
            if not isinstance(payload, dict):
                raise ValueError(f"{path}:{line_number}: JSON object required")
            rows.append(payload)
    return rows


def read_models(path: Path, model: type[ModelT]) -> list[ModelT]:
    return [model.model_validate(row) for row in read_jsonl(path)]


def require_file(path: Path) -> None:
    if not path.is_file():
        raise FileNotFoundError(path)


def extract_sources(raw_root: Path, paths: WorkPaths) -> None:
    try:
        import pdfplumber
    except ImportError as exc:
        raise RuntimeError("pdfplumber is required for PDF extraction") from exc

    extracted_at = utc_now()
    registry_rows: list[SourceRegistryEntry] = []
    pages: list[ExtractedPage] = []
    for spec in SOURCE_SPECS:
        pdf_path = raw_root / spec.relative_pdf
        require_file(pdf_path)
        source_hash = sha256_file(pdf_path)
        with pdfplumber.open(pdf_path) as pdf:
            page_count = len(pdf.pages)
            if page_count < 1:
                raise RuntimeError(f"PDF contains no pages: {pdf_path}")
            registry_rows.append(SourceRegistryEntry(
                source_id=spec.source_id,
                title=spec.title,
                issuing_body=spec.issuing_body,
                source_family=spec.source_family,
                triage_system=spec.triage_system,
                local_path=str(pdf_path.relative_to(REPO_ROOT)),
                sha256=source_hash,
                file_size_bytes=pdf_path.stat().st_size,
                page_count=page_count,
                license_reference=spec.license_reference,
                license_review_status="required",
                simulation_only=True,
                extracted_at=extracted_at,
            ))
            for page_number, page in enumerate(pdf.pages, start=1):
                text = (page.extract_text(layout=True) or "").strip()
                flags: list[str] = []
                if not text:
                    flags.append("empty_text_layer_requires_ocr")
                elif len(normalize_space(text)) < 120:
                    flags.append("low_text_density")
                if spec.force_layout_review:
                    flags.append("layout_requires_visual_review")
                pages.append(ExtractedPage(
                    page_id=f"{spec.source_id}__P{page_number:04d}",
                    source_id=spec.source_id,
                    source_sha256=source_hash,
                    page_number=page_number,
                    text=text,
                    extraction_method="pdf_text_layer",
                    quality_flags=flags,
                    requires_visual_review=bool(flags),
                ))

    registry = SourceRegistry(
        registry_version=PIPELINE_VERSION,
        sources=registry_rows,
    )
    write_json(paths.source_registry, registry.model_dump(mode="json"))
    count = write_jsonl(paths.extracted_pages, pages)
    print(f"extracted_pages={count}")
    print(f"source_registry={paths.source_registry}")
    print("openai_requests=0 database_writes=0 embedding_calls=0")


def extraction_system_prompt() -> str:
    return """You transform clinical guideline source text into review candidates.
Use only SOURCE_PAGES. Do not use outside medical knowledge.
Do not invent, repair, merge, or generalize a threshold, operator, unit, age,
population, outcome, ESI level, or IITT priority.
Every decision criterion must have a verbatim evidence_quote and evidence_page.
Keep ESI, WHO IITT, and Vietnamese Ministry of Health systems separate.
Only ESI_V4 source text may emit esi_level 1..5.
WHO IITT RED/YELLOW/GREEN must never be converted into ESI.
Exclude exercises, answer keys, fictional practice cases, acknowledgements,
history, bibliography, and administrative prose unless they define a decision.
Vietnamese text is a draft translation for human review; preserve clinical meaning,
numbers, comparison operators, units, and population exactly.
If the source is unclear, add a review_flag instead of guessing.
Return only the requested structured object."""


def extraction_retry_system_prompt() -> str:
    return extraction_system_prompt() + """

This is a strict provenance retry after deterministic validation rejected the
first extraction. For evidence_quote and every evidence_spans.quote:
- copy one contiguous substring from exactly one rendered SOURCE_PAGES page;
- preserve every character, word, number, operator, unit, and punctuation;
- never add ellipses (... or …), normalize typography, join separate sentences,
  repair OCR, or quote a heading from a different page;
- set evidence_page to the page that contains that exact copied substring.
Every number/operator/unit in criterion_original and numeric_thresholds must
occur verbatim in that criterion's evidence_quote. If exact evidence cannot be
copied, omit the candidate and explain why in omitted_content_notes. Returning
zero candidates is safer than returning an approximate citation."""


def verification_system_prompt() -> str:
    return """You are a source-grounding verifier, not a guideline author.
Compare CANDIDATE against SOURCE_PAGES only. Do not correct or rewrite it.
Reject any unsupported criterion, missing/mutated threshold, wrong page citation,
or conversion between ESI, WHO IITT, and BYT systems.
Use manual_review for layout/OCR ambiguity or an issue requiring a clinician.
Use llm_verified only when every criterion is directly supported and all numbers,
operators, units, populations, outcomes, and triage-system boundaries are preserved.
Return only the requested structured object."""


def json_schema_format(model: type[BaseModel], name: str) -> dict[str, Any]:
    return {
        "type": "json_schema",
        "name": name,
        "strict": True,
        "schema": model.model_json_schema(),
    }


def response_batch_request(
    *,
    custom_id: str,
    model: str,
    system_prompt: str,
    user_prompt: str,
    output_model: type[BaseModel],
    schema_name: str,
    max_output_tokens: int,
) -> dict[str, Any]:
    return {
        "custom_id": custom_id,
        "method": "POST",
        "url": BATCH_ENDPOINT,
        "body": {
            "model": model,
            "store": False,
            "input": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "text": {
                "format": json_schema_format(output_model, schema_name),
            },
            "max_output_tokens": max_output_tokens,
        },
    }


def grouped_pages(
    pages: Sequence[ExtractedPage],
    pages_per_request: int,
) -> Iterable[list[ExtractedPage]]:
    if pages_per_request < 1:
        raise ValueError("pages_per_request must be positive")
    ordered = sorted(pages, key=lambda item: item.page_number)
    for offset in range(0, len(ordered), pages_per_request):
        yield ordered[offset : offset + pages_per_request]


def render_source_pages(pages: Sequence[ExtractedPage]) -> str:
    sections = []
    for page in pages:
        sections.append(
            f"--- PAGE {page.page_number} [{page.page_id}] ---\n{page.text}"
        )
    return "\n\n".join(sections)


def prepare_extraction_batch(paths: WorkPaths) -> None:
    require_file(paths.extracted_pages)
    settings = get_settings()
    pages = read_models(paths.extracted_pages, ExtractedPage)
    by_source: dict[str, list[ExtractedPage]] = defaultdict(list)
    for page in pages:
        by_source[page.source_id].append(page)

    requests: list[dict[str, Any]] = []
    for spec in SOURCE_SPECS:
        source_pages = by_source.get(spec.source_id, [])
        if not source_pages:
            raise RuntimeError(f"no extracted pages for {spec.source_id}")
        for group in grouped_pages(
            source_pages,
            settings.protocol_openai_pages_per_request,
        ):
            first = group[0].page_number
            last = group[-1].page_number
            custom_id = f"extract__{spec.source_id.lower()}__p{first:04d}_{last:04d}"
            user_prompt = (
                "SOURCE_METADATA:\n"
                + json.dumps(
                    {
                        "source_id": spec.source_id,
                        "title": spec.title,
                        "triage_system": spec.triage_system,
                        "allowed_clinical_uses": spec.allowed_clinical_uses,
                        "default_populations": spec.default_populations,
                        "target_pages": [page.page_number for page in group],
                    },
                    ensure_ascii=False,
                )
                + "\n\nSOURCE_PAGES:\n"
                + render_source_pages(group)
            )
            requests.append(response_batch_request(
                custom_id=custom_id,
                model=settings.protocol_openai_extraction_model,
                system_prompt=extraction_system_prompt(),
                user_prompt=user_prompt,
                output_model=ExtractionEnvelope,
                schema_name="triage_protocol_extraction",
                max_output_tokens=settings.protocol_openai_extraction_max_output_tokens,
            ))

    count = write_jsonl(paths.extraction_input, requests)
    print(f"extraction_requests={count}")
    print(f"batch_input={paths.extraction_input}")
    print("openai_requests=0 database_writes=0 embedding_calls=0")


def prepare_extraction_retry_batch(paths: WorkPaths) -> None:
    require_file(paths.extraction_input)
    require_file(paths.rejected_candidates)
    settings = get_settings()
    rejected = read_jsonl(paths.rejected_candidates)
    retry_errors: dict[str, set[str]] = defaultdict(set)
    for row in rejected:
        custom_id = row.get("custom_id")
        reason = str(row.get("reason") or "")
        if not isinstance(custom_id, str) or not custom_id:
            continue
        if reason in {"duplicate_candidate", "candidate_outside_extraction_scope"}:
            continue
        retry_errors[custom_id].add(reason)
        for error in row.get("errors", []):
            retry_errors[custom_id].add(str(error))
    if not retry_errors:
        raise RuntimeError("no rejected extraction requests require retry")

    requests: list[dict[str, Any]] = []
    for original in read_jsonl(paths.extraction_input):
        custom_id = str(original.get("custom_id") or "")
        if custom_id not in retry_errors:
            continue
        request = json.loads(json.dumps(original, ensure_ascii=False))
        body = request.get("body")
        if not isinstance(body, dict):
            raise RuntimeError(f"invalid original batch body: {custom_id}")
        inputs = body.get("input")
        if not isinstance(inputs, list) or len(inputs) != 2:
            raise RuntimeError(f"invalid original batch input: {custom_id}")
        inputs[0]["content"] = extraction_retry_system_prompt()
        inputs[1]["content"] += (
            "\n\nRETRY_CONTEXT (do not copy as source evidence):\n"
            + json.dumps(
                {"previous_validation_errors": sorted(retry_errors[custom_id])},
                ensure_ascii=False,
            )
        )
        body["model"] = settings.protocol_openai_extraction_model
        body["max_output_tokens"] = (
            settings.protocol_openai_extraction_max_output_tokens
        )
        requests.append(request)

    missing = set(retry_errors) - {row["custom_id"] for row in requests}
    if missing:
        raise RuntimeError(f"retry requests missing original inputs: {sorted(missing)}")
    count = write_jsonl(paths.extraction_retry_input, requests)
    print(f"extraction_retry_requests={count}")
    print(f"batch_input={paths.extraction_retry_input}")
    print("openai_requests=0 database_writes=0 embedding_calls=0")


def require_openai_client() -> Any:
    settings = get_settings()
    api_key = settings.openai_api_key.strip()
    if not api_key or api_key == "sk-your-key-here":
        raise RuntimeError(
            "OPENAI_API_KEY is missing. Put it in .env; never commit the key."
        )
    try:
        from openai import OpenAI
    except ImportError as exc:
        raise RuntimeError("Install the openai package from requirements.txt") from exc
    return OpenAI(
        api_key=api_key,
        timeout=settings.protocol_openai_request_timeout_seconds,
        max_retries=settings.protocol_openai_max_retries,
    )


def validate_batch_input(path: Path, expected_model: str) -> int:
    rows = read_jsonl(path)
    if not rows:
        raise RuntimeError(f"batch input is empty: {path}")
    custom_ids: set[str] = set()
    for line_number, row in enumerate(rows, start=1):
        custom_id = row.get("custom_id")
        body = row.get("body")
        if not isinstance(custom_id, str) or not custom_id:
            raise RuntimeError(f"batch line {line_number} has no custom_id")
        if custom_id in custom_ids:
            raise RuntimeError(f"duplicate batch custom_id: {custom_id}")
        custom_ids.add(custom_id)
        if row.get("method") != "POST" or row.get("url") != BATCH_ENDPOINT:
            raise RuntimeError(f"batch line {line_number} has an invalid endpoint")
        if not isinstance(body, dict) or body.get("model") != expected_model:
            raise RuntimeError(
                f"batch line {line_number} does not use model {expected_model}"
            )
        if body.get("store") is not False:
            raise RuntimeError(f"batch line {line_number} must set store=false")
    return len(rows)


def submit_batch(
    *,
    stage: Literal[
        "extraction",
        "verification",
        "repair",
        "repair_verification",
    ],
    input_path: Path,
    job_path: Path,
    model: str,
) -> None:
    require_file(input_path)
    request_count = validate_batch_input(input_path, model)
    if job_path.exists():
        raise RuntimeError(
            f"job state already exists: {job_path}; remove it only after review"
        )
    client = require_openai_client()
    with input_path.open("rb") as source:
        uploaded = client.files.create(file=source, purpose="batch")
    batch = client.batches.create(
        input_file_id=uploaded.id,
        endpoint=BATCH_ENDPOINT,
        completion_window="24h",
        metadata={
            "pipeline": PIPELINE_VERSION,
            "stage": stage,
        },
    )
    state = BatchJobState(
        pipeline_version=PIPELINE_VERSION,
        stage=stage,
        batch_id=batch.id,
        input_file_id=uploaded.id,
        endpoint=BATCH_ENDPOINT,
        model=model,
        input_path=str(input_path),
        submitted_at=utc_now(),
        output_file_id=getattr(batch, "output_file_id", None),
        error_file_id=getattr(batch, "error_file_id", None),
        status=str(batch.status),
    )
    write_json(job_path, state.model_dump(mode="json"))
    print(f"batch_id={state.batch_id}")
    print(f"status={state.status}")
    print(f"request_count={request_count}")
    print(f"job_state={job_path}")
    print("database_writes=0 embedding_calls=0")


def download_batch(
    *,
    job_path: Path,
    output_path: Path,
    error_path: Path,
) -> int:
    require_file(job_path)
    state = BatchJobState.model_validate_json(job_path.read_text(encoding="utf-8"))
    client = require_openai_client()
    batch = client.batches.retrieve(state.batch_id)
    updated = state.model_copy(update={
        "status": str(batch.status),
        "output_file_id": getattr(batch, "output_file_id", None),
        "error_file_id": getattr(batch, "error_file_id", None),
    })
    write_json(job_path, updated.model_dump(mode="json"))
    print(f"batch_id={updated.batch_id}")
    print(f"status={updated.status}")
    if updated.status != "completed":
        print("output_downloaded=false")
        return 2
    if not updated.output_file_id:
        raise RuntimeError("completed batch has no output_file_id")
    output = client.files.content(updated.output_file_id)
    atomic_write_text(output_path, output.text)
    if updated.error_file_id:
        errors = client.files.content(updated.error_file_id)
        atomic_write_text(error_path, errors.text)
    print(f"output={output_path}")
    print(f"error_output={error_path if updated.error_file_id else 'none'}")
    print("database_writes=0 embedding_calls=0")
    return 0


def response_output_text(body: dict[str, Any]) -> str:
    direct = body.get("output_text")
    if isinstance(direct, str) and direct.strip():
        return direct.strip()
    text_parts: list[str] = []
    for output_item in body.get("output", []):
        if not isinstance(output_item, dict):
            continue
        for content_item in output_item.get("content", []):
            if not isinstance(content_item, dict):
                continue
            if content_item.get("type") == "output_text":
                text = content_item.get("text")
                if isinstance(text, str):
                    text_parts.append(text)
    if not text_parts:
        raise ValueError("Responses API body contains no output_text")
    return "\n".join(text_parts).strip()


def successful_batch_bodies(
    output_path: Path,
) -> tuple[list[tuple[str, dict[str, Any]]], list[dict[str, Any]]]:
    successes: list[tuple[str, dict[str, Any]]] = []
    errors: list[dict[str, Any]] = []
    for row in read_jsonl(output_path):
        custom_id = str(row.get("custom_id") or "")
        response = row.get("response")
        if not custom_id or not isinstance(response, dict):
            errors.append({"custom_id": custom_id, "reason": "missing_response", "row": row})
            continue
        status_code = response.get("status_code")
        body = response.get("body")
        if status_code != 200 or not isinstance(body, dict):
            errors.append({
                "custom_id": custom_id,
                "reason": "api_request_failed",
                "status_code": status_code,
                "error": row.get("error") or body,
            })
            continue
        successes.append((custom_id, body))
    return successes, errors


def page_lookup(pages: Sequence[ExtractedPage]) -> dict[tuple[str, int], ExtractedPage]:
    return {(page.source_id, page.page_number): page for page in pages}


def quote_is_grounded(quote: str, page_text: str) -> bool:
    return normalize_space(quote) in normalize_space(page_text)


def deterministic_candidate_errors(
    candidate: ProtocolCandidate,
    pages: dict[tuple[str, int], ExtractedPage],
) -> list[str]:
    errors: list[str] = []
    spec = SOURCE_BY_ID.get(candidate.source_id)
    if spec is None:
        return ["unknown_source_id"]
    if candidate.triage_system != spec.triage_system:
        errors.append("triage_system_mismatch")
    if not set(candidate.clinical_uses).issubset(spec.allowed_clinical_uses):
        errors.append("clinical_use_not_allowed_for_source")
    if candidate.triage_system != "ESI_V4" and candidate.esi_level is not None:
        errors.append("non_esi_source_emitted_esi_level")

    for evidence in candidate.evidence_spans:
        source_page = pages.get((candidate.source_id, evidence.page))
        if source_page is None:
            errors.append(f"unknown_evidence_page:{evidence.page}")
        elif not quote_is_grounded(evidence.quote, source_page.text):
            errors.append(f"evidence_quote_not_exact:{evidence.page}")

    for index, criterion in enumerate(candidate.decision_criteria):
        source_page = pages.get((candidate.source_id, criterion.evidence_page))
        if source_page is None:
            errors.append(f"criterion_{index}_unknown_page")
            continue
        if not quote_is_grounded(criterion.evidence_quote, source_page.text):
            errors.append(f"criterion_{index}_quote_not_exact")
        evidence_numbers = numeric_tokens(criterion.evidence_quote)
        declared_numbers = {
            token
            for threshold in criterion.numeric_thresholds
            for token in numeric_tokens(threshold)
        }
        criterion_numbers = numeric_tokens(criterion.criterion_original)
        if not declared_numbers.issubset(evidence_numbers):
            errors.append(f"criterion_{index}_declared_number_not_in_evidence")
        if not criterion_numbers.issubset(evidence_numbers):
            errors.append(f"criterion_{index}_number_not_in_evidence")
    return sorted(set(errors))


def extraction_request_scope(custom_id: str) -> tuple[str, set[int]]:
    match = re.fullmatch(
        r"extract__(?P<source>[a-z0-9_]+)__p(?P<start>\d{4})_(?P<end>\d{4})",
        custom_id,
    )
    if match is None:
        raise ValueError(f"invalid extraction custom_id: {custom_id}")
    source_key = match.group("source")
    matching_sources = [
        spec.source_id
        for spec in SOURCE_SPECS
        if spec.source_id.lower() == source_key
    ]
    if len(matching_sources) != 1:
        raise ValueError(f"unknown extraction source in custom_id: {custom_id}")
    start = int(match.group("start"))
    end = int(match.group("end"))
    if start < 1 or end < start:
        raise ValueError(f"invalid extraction page range: {custom_id}")
    return matching_sources[0], set(range(start, end + 1))


def candidate_pages(candidate: ProtocolCandidate) -> set[int]:
    pages = set(range(candidate.page_start, candidate.page_end + 1))
    pages.update(span.page for span in candidate.evidence_spans)
    pages.update(
        criterion.evidence_page for criterion in candidate.decision_criteria
    )
    return pages


def candidate_risk_flags(
    candidate: ProtocolCandidate,
    pages: dict[tuple[str, int], ExtractedPage],
) -> list[str]:
    flags: set[str] = set(candidate.review_flags)
    if candidate.triage_system == "ESI_V4":
        flags.add("esi_decision_support")
    if "pediatric" in candidate.populations:
        flags.add("pediatric_rule")
    if candidate.esi_level is not None:
        flags.add("esi_level_present")
    if any(
        numeric_tokens(criterion.criterion_original)
        for criterion in candidate.decision_criteria
    ):
        flags.add("numeric_threshold")
    for page_number in range(candidate.page_start, candidate.page_end + 1):
        source_page = pages.get((candidate.source_id, page_number))
        if source_page and source_page.requires_visual_review:
            flags.add("source_page_requires_visual_review")
    return sorted(flag for flag in flags if flag)


def stable_candidate_id(candidate: ProtocolCandidate) -> str:
    payload = json.dumps(
        {
            "source_id": candidate.source_id,
            "page_start": candidate.page_start,
            "page_end": candidate.page_end,
            "section": normalize_space(candidate.section),
            "evidence": [
                [span.page, normalize_space(span.quote)]
                for span in candidate.evidence_spans
            ],
        },
        ensure_ascii=False,
        sort_keys=True,
    )
    suffix = hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]
    prefix = normalize_keyword(candidate.source_id)[:80]
    return f"{prefix}_{suffix}"


def sanitize_candidate(candidate: ProtocolCandidate) -> ProtocolCandidate:
    keywords = [normalize_keyword(keyword) for keyword in candidate.keywords]
    keywords = list(dict.fromkeys(keyword for keyword in keywords if keyword))
    populations: list[Population] = list(dict.fromkeys(candidate.populations))
    if candidate.source_id == "WHO_IITT_AGE_12_PLUS":
        populations = ["age_12_plus"]
    elif candidate.source_id == "WHO_IITT_UNDER_12":
        populations = ["age_under_12"]
    return candidate.model_copy(update={
        "keywords": keywords,
        "review_flags": list(dict.fromkeys(candidate.review_flags)),
        "clinical_uses": list(dict.fromkeys(candidate.clinical_uses)),
        "populations": populations,
    })


def parse_extraction_batch(paths: WorkPaths) -> None:
    require_file(paths.extraction_output)
    require_file(paths.extracted_pages)
    settings = get_settings()
    pages_list = read_models(paths.extracted_pages, ExtractedPage)
    pages = page_lookup(pages_list)
    successes, api_errors = successful_batch_bodies(paths.extraction_output)
    if paths.extraction_retry_output.exists():
        retry_successes, retry_api_errors = successful_batch_bodies(
            paths.extraction_retry_output
        )
        successes.extend(retry_successes)
        api_errors.extend(retry_api_errors)
    accepted: list[CandidateRecord] = []
    rejected: list[dict[str, Any]] = list(api_errors)
    seen_ids: set[str] = set()

    for custom_id, body in successes:
        try:
            expected_source, expected_pages = extraction_request_scope(custom_id)
            raw_output = response_output_text(body)
            envelope = ExtractionEnvelope.model_validate_json(raw_output)
        except (ValidationError, ValueError, json.JSONDecodeError) as exc:
            rejected.append({
                "custom_id": custom_id,
                "reason": "invalid_structured_output",
                "error": str(exc),
            })
            continue
        if (
            envelope.source_id != expected_source
            or set(envelope.pages_seen) != expected_pages
        ):
            rejected.append({
                "custom_id": custom_id,
                "reason": "extraction_scope_mismatch",
                "expected_source": expected_source,
                "expected_pages": sorted(expected_pages),
                "actual_source": envelope.source_id,
                "actual_pages": envelope.pages_seen,
            })
            continue
        for candidate_index, raw_candidate in enumerate(envelope.candidates):
            candidate = sanitize_candidate(raw_candidate)
            if (
                candidate.source_id != expected_source
                or not candidate_pages(candidate).issubset(expected_pages)
            ):
                rejected.append({
                    "custom_id": custom_id,
                    "candidate_index": candidate_index,
                    "reason": "candidate_outside_extraction_scope",
                    "candidate_source": candidate.source_id,
                    "candidate_pages": sorted(candidate_pages(candidate)),
                })
                continue
            errors = deterministic_candidate_errors(candidate, pages)
            candidate_id = stable_candidate_id(candidate)
            if candidate_id in seen_ids:
                rejected.append({
                    "custom_id": custom_id,
                    "candidate_index": candidate_index,
                    "candidate_id": candidate_id,
                    "reason": "duplicate_candidate",
                })
                continue
            seen_ids.add(candidate_id)
            if errors:
                rejected.append({
                    "custom_id": custom_id,
                    "candidate_index": candidate_index,
                    "candidate_id": candidate_id,
                    "reason": "deterministic_validation_failed",
                    "errors": errors,
                    "candidate": candidate.model_dump(mode="json"),
                })
                continue
            accepted.append(CandidateRecord(
                candidate_id=candidate_id,
                citation_id=f"SIM:{candidate_id}",
                source_sha256=pages[
                    (candidate.source_id, candidate.page_start)
                ].source_sha256,
                pipeline_version=PIPELINE_VERSION,
                prompt_version=PROMPT_VERSION,
                extraction_model=settings.protocol_openai_extraction_model,
                extraction_custom_id=custom_id,
                candidate=candidate,
                deterministic_flags=[],
                risk_flags=candidate_risk_flags(candidate, pages),
                validation_status="candidate",
            ))

    write_jsonl(paths.candidates, accepted)
    write_jsonl(paths.rejected_candidates, rejected)
    print(f"accepted_candidates={len(accepted)}")
    print(f"rejected_candidates={len(rejected)}")
    print("review_status=pending database_writes=0 embedding_calls=0")


def prepare_verification_batch(
    paths: WorkPaths,
    *,
    output_path: Path | None = None,
) -> None:
    require_file(paths.candidates)
    require_file(paths.extracted_pages)
    settings = get_settings()
    candidates = read_models(paths.candidates, CandidateRecord)
    pages = page_lookup(read_models(paths.extracted_pages, ExtractedPage))
    requests: list[dict[str, Any]] = []
    for record in candidates:
        if not record.risk_flags:
            continue
        candidate = record.candidate
        source_pages = [
            pages[(candidate.source_id, page_number)]
            for page_number in sorted(candidate_pages(candidate))
            if (candidate.source_id, page_number) in pages
        ]
        if not source_pages:
            raise RuntimeError(f"missing source pages for {record.candidate_id}")
        user_prompt = (
            "CANDIDATE:\n"
            + json.dumps(
                {
                    "candidate_id": record.candidate_id,
                    "risk_flags": record.risk_flags,
                    "candidate": candidate.model_dump(mode="json"),
                },
                ensure_ascii=False,
            )
            + "\n\nSOURCE_PAGES:\n"
            + render_source_pages(source_pages)
        )
        requests.append(response_batch_request(
            custom_id=f"verify__{record.candidate_id}",
            model=settings.protocol_openai_verification_model,
            system_prompt=verification_system_prompt(),
            user_prompt=user_prompt,
            output_model=VerificationEnvelope,
            schema_name="triage_protocol_verification",
            max_output_tokens=settings.protocol_openai_verification_max_output_tokens,
        ))

    batch_input = output_path or paths.verification_input
    count = write_jsonl(batch_input, requests)
    print(f"verification_requests={count}")
    print(f"batch_input={batch_input}")
    print("openai_requests=0 database_writes=0 embedding_calls=0")


def normalize_verification_decision(
    envelope: VerificationEnvelope,
    criterion_count: int,
) -> VerificationEnvelope:
    indexes = {check.criterion_index for check in envelope.criterion_checks}
    expected_indexes = set(range(criterion_count))
    all_checks_pass = bool(envelope.criterion_checks) and all(
        check.source_supported
        and check.evidence_quote_exact
        and check.numeric_thresholds_preserved
        for check in envelope.criterion_checks
    )
    hard_error = any(issue.severity == "error" for issue in envelope.issues)
    can_verify = (
        envelope.source_grounding_passed
        and envelope.triage_system_separation_passed
        and indexes == expected_indexes
        and all_checks_pass
        and not hard_error
    )
    if envelope.decision == "llm_verified" and not can_verify:
        return envelope.model_copy(update={"decision": "manual_review"})
    return envelope


def parse_verification_batch(paths: WorkPaths) -> None:
    verification_output = (
        paths.verification_retry_output
        if paths.verification_retry_output.exists()
        else paths.verification_output
    )
    require_file(verification_output)
    require_file(paths.candidates)
    settings = get_settings()
    candidates = {
        item.candidate_id: item
        for item in read_models(paths.candidates, CandidateRecord)
    }
    successes, api_errors = successful_batch_bodies(verification_output)
    records: list[VerificationRecord] = []
    errors: list[dict[str, Any]] = list(api_errors)
    seen: set[str] = set()

    for custom_id, body in successes:
        try:
            envelope = VerificationEnvelope.model_validate_json(
                response_output_text(body)
            )
        except (ValidationError, ValueError, json.JSONDecodeError) as exc:
            errors.append({
                "custom_id": custom_id,
                "reason": "invalid_structured_output",
                "error": str(exc),
            })
            continue
        if custom_id != f"verify__{envelope.candidate_id}":
            errors.append({
                "custom_id": custom_id,
                "reason": "verification_scope_mismatch",
                "candidate_id": envelope.candidate_id,
            })
            continue
        candidate = candidates.get(envelope.candidate_id)
        if candidate is None:
            errors.append({
                "custom_id": custom_id,
                "reason": "unknown_candidate_id",
                "candidate_id": envelope.candidate_id,
            })
            continue
        if envelope.candidate_id in seen:
            errors.append({
                "custom_id": custom_id,
                "reason": "duplicate_verification",
                "candidate_id": envelope.candidate_id,
            })
            continue
        seen.add(envelope.candidate_id)
        envelope = normalize_verification_decision(
            envelope,
            len(candidate.candidate.decision_criteria),
        )
        records.append(VerificationRecord(
            candidate_id=envelope.candidate_id,
            verification_model=settings.protocol_openai_verification_model,
            verification_prompt_version=VERIFICATION_PROMPT_VERSION,
            decision=envelope.decision,
            source_grounding_passed=envelope.source_grounding_passed,
            triage_system_separation_passed=(
                envelope.triage_system_separation_passed
            ),
            criterion_checks=envelope.criterion_checks,
            issues=envelope.issues,
        ))

    write_jsonl(paths.verifications, records)
    write_jsonl(paths.verification_parse_errors, errors)
    print(f"verification_records={len(records)}")
    print(f"verification_errors={len(errors)}")
    print("clinical_approval=false database_writes=0 embedding_calls=0")


def build_review_package(paths: WorkPaths) -> None:
    require_file(paths.candidates)
    candidates = read_models(paths.candidates, CandidateRecord)
    verification_by_id: dict[str, VerificationRecord] = {}
    if paths.verifications.exists():
        verification_by_id = {
            item.candidate_id: item
            for item in read_models(paths.verifications, VerificationRecord)
        }

    package: list[ReviewPackageRecord] = []
    blocked_reasons: dict[str, int] = defaultdict(int)
    for candidate in candidates:
        verification = verification_by_id.get(candidate.candidate_id)
        blocked = False
        if candidate.risk_flags and verification is None:
            blocked = True
            blocked_reasons["missing_required_llm_verification"] += 1
        elif verification and verification.decision != "llm_verified":
            blocked = True
            blocked_reasons[f"verification_{verification.decision}"] += 1
        package.append(ReviewPackageRecord(
            candidate_id=candidate.candidate_id,
            citation_id=candidate.citation_id,
            source_sha256=candidate.source_sha256,
            candidate=candidate.candidate,
            deterministic_flags=candidate.deterministic_flags,
            risk_flags=candidate.risk_flags,
            llm_verification=verification,
            review_status="blocked" if blocked else "pending_human_review",
            simulation_only=True,
        ))

    write_jsonl(paths.review_package, package)
    summary = {
        "pipeline_version": PIPELINE_VERSION,
        "generated_at": utc_now().isoformat(),
        "total_candidates": len(package),
        "pending_human_review": sum(
            row.review_status == "pending_human_review" for row in package
        ),
        "blocked": sum(row.review_status == "blocked" for row in package),
        "blocked_reasons": dict(sorted(blocked_reasons.items())),
        "clinical_approval": False,
        "simulation_only": True,
        "database_writes": 0,
        "embedding_calls": 0,
    }
    write_json(paths.review_summary, summary)
    print(f"review_records={len(package)}")
    print(f"pending_human_review={summary['pending_human_review']}")
    print(f"blocked={summary['blocked']}")
    print("clinical_approval=false database_writes=0 embedding_calls=0")


def demo_eligibility_reasons(
    record: ReviewPackageRecord,
    pages: dict[tuple[str, int], ExtractedPage],
) -> list[str]:
    reasons: set[str] = set()
    verification = record.llm_verification
    if record.review_status != "pending_human_review":
        reasons.add(f"review_status_{record.review_status}")
    if verification is None:
        reasons.add("missing_llm_verification")
    else:
        if verification.decision != "llm_verified":
            reasons.add(f"verification_{verification.decision}")
        if not verification.source_grounding_passed:
            reasons.add("source_grounding_failed")
        if not verification.triage_system_separation_passed:
            reasons.add("triage_system_separation_failed")
        expected_indexes = set(range(len(record.candidate.decision_criteria)))
        actual_indexes = {
            check.criterion_index for check in verification.criterion_checks
        }
        if actual_indexes != expected_indexes:
            reasons.add("incomplete_criterion_checks")
        if any(
            not (
                check.source_supported
                and check.evidence_quote_exact
                and check.numeric_thresholds_preserved
            )
            for check in verification.criterion_checks
        ):
            reasons.add("criterion_check_failed")
        for issue in verification.issues:
            reasons.add(f"verification_issue_{normalize_keyword(issue.code)}")
    if "source_page_requires_visual_review" in record.risk_flags:
        reasons.add("source_page_requires_visual_review")
    for error in deterministic_candidate_errors(record.candidate, pages):
        reasons.add(f"deterministic_{error}")
    return sorted(reasons)


def build_demo_allowlist(paths: WorkPaths) -> None:
    require_file(paths.review_package)
    require_file(paths.extracted_pages)
    require_file(paths.source_registry)
    package = read_models(paths.review_package, ReviewPackageRecord)
    pages = page_lookup(read_models(paths.extracted_pages, ExtractedPage))
    registry = SourceRegistry.model_validate_json(
        paths.source_registry.read_text(encoding="utf-8")
    )
    registry_sources = {source.source_id: source for source in registry.sources}
    generated_at = utc_now()
    allowlist: list[DemoAllowlistRecord] = []
    review_queue: list[dict[str, Any]] = []
    excluded: list[dict[str, Any]] = []
    seen_ids: set[str] = set()

    for record in package:
        if record.candidate_id in seen_ids:
            raise RuntimeError(f"duplicate review candidate: {record.candidate_id}")
        seen_ids.add(record.candidate_id)
        source = registry_sources.get(record.candidate.source_id)
        reasons = demo_eligibility_reasons(record, pages)
        if source is None:
            reasons.append("missing_source_registry_entry")
        elif source.sha256 != record.source_sha256:
            reasons.append("source_hash_mismatch")
        reasons = sorted(set(reasons))
        verification = record.llm_verification
        if not reasons and verification is not None:
            allowlist.append(DemoAllowlistRecord(
                candidate_id=record.candidate_id,
                citation_id=record.citation_id,
                source_sha256=record.source_sha256,
                pipeline_version=PIPELINE_VERSION,
                generated_at=generated_at,
                demo_status="demo_eligible_nonclinical",
                review_method=(
                    "deterministic_and_llm_documentary_gate_without_clinician"
                ),
                simulation_only=True,
                clinical_approval=False,
                eligible_for_internal_demo_retrieval=True,
                public_distribution_allowed=False,
                license_review_required=True,
                candidate=record.candidate,
                llm_verification=verification,
                allowed_uses=[
                    "internal_synthetic_demo",
                    "retrieval_and_citation_demo",
                    "hitl_workflow_demo",
                ],
                prohibited_uses=[
                    "real_patient_triage",
                    "autonomous_esi_assignment",
                    "diagnosis_or_treatment",
                    "public_distribution_before_license_review",
                ],
            ))
            continue

        disposition = {
            "candidate_id": record.candidate_id,
            "source_id": record.candidate.source_id,
            "section": record.candidate.section,
            "pages": [record.candidate.page_start, record.candidate.page_end],
            "verification_decision": (
                verification.decision if verification else None
            ),
            "disposition_reasons": reasons,
            "simulation_only": True,
            "clinical_approval": False,
        }
        if verification and verification.decision == "reject":
            excluded.append(disposition)
        else:
            review_queue.append(disposition)

    if len(allowlist) + len(review_queue) + len(excluded) != len(package):
        raise RuntimeError("demo disposition count does not match review package")
    write_jsonl(paths.demo_allowlist, allowlist)
    write_jsonl(paths.demo_review_queue, review_queue)
    write_jsonl(paths.demo_excluded, excluded)
    summary = {
        "pipeline_version": PIPELINE_VERSION,
        "generated_at": generated_at.isoformat(),
        "source_review_package": str(paths.review_package),
        "total_candidates": len(package),
        "demo_allowlist": len(allowlist),
        "documentary_review_queue": len(review_queue),
        "excluded": len(excluded),
        "simulation_only": True,
        "clinical_approval": False,
        "public_distribution_allowed": False,
        "database_writes": 0,
        "embedding_calls": 0,
    }
    write_json(paths.demo_allowlist_summary, summary)
    print(f"demo_allowlist={len(allowlist)}")
    print(f"documentary_review_queue={len(review_queue)}")
    print(f"excluded={len(excluded)}")
    print("clinical_approval=false database_writes=0 embedding_calls=0")


def resolve_repo_path(value: str) -> Path:
    path = Path(value)
    if not path.is_absolute():
        path = REPO_ROOT / path
    return path.resolve()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build a source-grounded triage protocol simulation corpus."
    )
    parser.add_argument(
        "--raw-dir",
        default="data/protocol_corpus/raw",
        help="Directory containing the five source PDFs.",
    )
    parser.add_argument(
        "--work-dir",
        default="data/protocol_corpus/work/simulation_v1",
        help="Generated staging artifacts; never a production corpus.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)
    for command in (
        "extract",
        "prepare-extraction",
        "submit-extraction",
        "download-extraction",
        "parse-extraction",
        "prepare-extraction-retry",
        "submit-extraction-retry",
        "download-extraction-retry",
        "prepare-verification",
        "submit-verification",
        "download-verification",
        "prepare-verification-retry",
        "submit-verification-retry",
        "download-verification-retry",
        "parse-verification",
        "build-review-package",
        "build-demo-allowlist",
    ):
        subparsers.add_parser(command)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    os.chdir(REPO_ROOT)
    raw_root = resolve_repo_path(args.raw_dir)
    paths = work_paths(resolve_repo_path(args.work_dir))
    settings = get_settings()

    if args.command == "extract":
        extract_sources(raw_root, paths)
    elif args.command == "prepare-extraction":
        prepare_extraction_batch(paths)
    elif args.command == "submit-extraction":
        submit_batch(
            stage="extraction",
            input_path=paths.extraction_input,
            job_path=paths.extraction_job,
            model=settings.protocol_openai_extraction_model,
        )
    elif args.command == "download-extraction":
        return download_batch(
            job_path=paths.extraction_job,
            output_path=paths.extraction_output,
            error_path=paths.extraction_api_errors,
        )
    elif args.command == "parse-extraction":
        parse_extraction_batch(paths)
    elif args.command == "prepare-extraction-retry":
        prepare_extraction_retry_batch(paths)
    elif args.command == "submit-extraction-retry":
        submit_batch(
            stage="extraction",
            input_path=paths.extraction_retry_input,
            job_path=paths.extraction_retry_job,
            model=settings.protocol_openai_extraction_model,
        )
    elif args.command == "download-extraction-retry":
        return download_batch(
            job_path=paths.extraction_retry_job,
            output_path=paths.extraction_retry_output,
            error_path=paths.extraction_retry_api_errors,
        )
    elif args.command == "prepare-verification":
        prepare_verification_batch(paths)
    elif args.command == "submit-verification":
        submit_batch(
            stage="verification",
            input_path=paths.verification_input,
            job_path=paths.verification_job,
            model=settings.protocol_openai_verification_model,
        )
    elif args.command == "download-verification":
        return download_batch(
            job_path=paths.verification_job,
            output_path=paths.verification_output,
            error_path=paths.verification_api_errors,
        )
    elif args.command == "prepare-verification-retry":
        prepare_verification_batch(
            paths,
            output_path=paths.verification_retry_input,
        )
    elif args.command == "submit-verification-retry":
        submit_batch(
            stage="verification",
            input_path=paths.verification_retry_input,
            job_path=paths.verification_retry_job,
            model=settings.protocol_openai_verification_model,
        )
    elif args.command == "download-verification-retry":
        return download_batch(
            job_path=paths.verification_retry_job,
            output_path=paths.verification_retry_output,
            error_path=paths.verification_retry_api_errors,
        )
    elif args.command == "parse-verification":
        parse_verification_batch(paths)
    elif args.command == "build-review-package":
        build_review_package(paths)
    elif args.command == "build-demo-allowlist":
        build_demo_allowlist(paths)
    else:
        raise AssertionError(f"unhandled command: {args.command}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(
            f"Protocol simulation pipeline aborted: {type(exc).__name__}: {exc}",
            file=sys.stderr,
        )
        raise SystemExit(1) from exc
