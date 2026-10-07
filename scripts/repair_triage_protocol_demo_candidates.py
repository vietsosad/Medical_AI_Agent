#!/usr/bin/env python3
"""Repair rejected protocol candidates for a non-clinical internal demo.

This pipeline is deliberately separate from the strict corpus allowlist. It:

1. repairs only the five candidates already rejected by the documentary gate;
2. emits one atomic candidate per original criterion;
3. verifies each repair with a second model and exact source pages;
4. combines strict, project-owner-accepted, and repaired records in a v2 demo
   allowlist without claiming clinical approval.

No command writes to the application database or creates embeddings.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

from pydantic import Field, ValidationError


REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.build_triage_protocol_simulation import (  # noqa: E402
    PIPELINE_VERSION,
    SOURCE_BY_ID,
    EvidenceSpan,
    ExtractedPage,
    ProtocolCandidate,
    ReviewPackageRecord,
    StrictModel,
    VerificationEnvelope,
    VerificationRecord,
    candidate_pages,
    candidate_risk_flags,
    deterministic_candidate_errors,
    download_batch,
    normalize_keyword,
    normalize_verification_decision,
    page_lookup,
    read_jsonl,
    read_models,
    render_source_pages,
    require_file,
    response_batch_request,
    response_output_text,
    sanitize_candidate,
    submit_batch,
    successful_batch_bodies,
    utc_now,
    write_json,
    write_jsonl,
)
from src.config import get_settings  # noqa: E402


REPAIR_PROMPT_VERSION = "triage-protocol-repair-v1"
REPAIR_VERIFICATION_PROMPT_VERSION = "triage-protocol-verify-v1"
EXPECTED_OWNER_ACCEPTED_COUNT = 9
EXPECTED_REJECTED_GROUP_COUNT = 5


class DroppedCriterion(StrictModel):
    original_criterion_index: int = Field(ge=0)
    reason_code: str = Field(min_length=2, max_length=100)
    reason: str = Field(min_length=3, max_length=2_000)


class RepairedCandidateItem(StrictModel):
    original_criterion_index: int = Field(ge=0)
    candidate: ProtocolCandidate


class RepairEnvelope(StrictModel):
    original_candidate_id: str
    source_id: str
    pages_seen: list[int] = Field(min_length=1)
    repaired_candidates: list[RepairedCandidateItem] = Field(max_length=50)
    dropped_criteria: list[DroppedCriterion] = Field(max_length=50)


class SingleRepairEnvelope(StrictModel):
    original_candidate_id: str
    original_criterion_index: int = Field(ge=0)
    source_id: str
    pages_seen: list[int] = Field(min_length=1)
    repaired_candidate: ProtocolCandidate | None
    drop_reason: str | None


class RepairCandidateRecord(StrictModel):
    candidate_id: str = Field(pattern=r"^[a-z0-9_]{12,160}$")
    original_candidate_id: str
    original_criterion_index: int = Field(ge=0)
    citation_id: str
    source_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    pipeline_version: Literal[PIPELINE_VERSION]
    repair_prompt_version: Literal[REPAIR_PROMPT_VERSION]
    repair_model: str
    candidate: ProtocolCandidate
    deterministic_flags: list[str]
    risk_flags: list[str]
    validation_status: Literal["repaired_candidate"]


@dataclass(frozen=True)
class RepairPaths:
    root: Path
    extracted_pages: Path
    review_package: Path
    strict_allowlist: Path
    original_review_queue: Path
    original_excluded: Path
    repair_input: Path
    repair_job: Path
    repair_output: Path
    repair_api_errors: Path
    repair_retry_input: Path
    repair_retry_job: Path
    repair_retry_output: Path
    repair_retry_api_errors: Path
    repaired_candidates: Path
    repair_rejected: Path
    repair_verification_input: Path
    repair_verification_job: Path
    repair_verification_output: Path
    repair_verification_api_errors: Path
    repair_verifications: Path
    repair_verification_parse_errors: Path
    owner_acceptance: Path
    allowlist_v2: Path
    repair_review_queue: Path
    allowlist_v2_summary: Path
    cost_estimate: Path


def repair_paths(root: Path) -> RepairPaths:
    batches = root / "batches"
    return RepairPaths(
        root=root,
        extracted_pages=root / "extracted_pages.jsonl",
        review_package=root / "protocol_review_package.jsonl",
        strict_allowlist=root / "protocol_demo_allowlist.jsonl",
        original_review_queue=root / "protocol_demo_review_queue.jsonl",
        original_excluded=root / "protocol_demo_excluded.jsonl",
        repair_input=batches / "repair_input.jsonl",
        repair_job=batches / "repair_job.json",
        repair_output=batches / "repair_output.jsonl",
        repair_api_errors=batches / "repair_api_errors.jsonl",
        repair_retry_input=batches / "repair_retry_input.jsonl",
        repair_retry_job=batches / "repair_retry_job.json",
        repair_retry_output=batches / "repair_retry_output.jsonl",
        repair_retry_api_errors=batches / "repair_retry_api_errors.jsonl",
        repaired_candidates=root / "protocol_repaired_candidates.jsonl",
        repair_rejected=root / "protocol_repair_rejected.jsonl",
        repair_verification_input=batches / "repair_verification_input.jsonl",
        repair_verification_job=batches / "repair_verification_job.json",
        repair_verification_output=batches / "repair_verification_output.jsonl",
        repair_verification_api_errors=(
            batches / "repair_verification_api_errors.jsonl"
        ),
        repair_verifications=root / "protocol_repair_verifications.jsonl",
        repair_verification_parse_errors=(
            root / "protocol_repair_verification_rejected.jsonl"
        ),
        owner_acceptance=root / "protocol_demo_owner_acceptance.json",
        allowlist_v2=root / "protocol_demo_allowlist_v2.jsonl",
        repair_review_queue=root / "protocol_demo_repair_review_queue.jsonl",
        allowlist_v2_summary=root / "protocol_demo_allowlist_v2_summary.json",
        cost_estimate=root / "protocol_repair_cost_estimate.json",
    )


def repair_system_prompt() -> str:
    return """You repair rejected clinical-guideline extraction candidates.
Use only SOURCE_PAGES. Do not use outside medical knowledge.

Hard rules:
- Emit exactly one decision criterion per repaired candidate.
- Map every original criterion index exactly once: either repaired or dropped.
- Copy evidence_quote as one exact contiguous substring from its evidence page.
- Preserve every number, comparison operator, unit, age, population, and triage
  category exactly. Put every numeric clinical threshold in numeric_thresholds.
- Keep ESI, WHO IITT, and BYT systems separate. Never convert WHO colors to ESI.
- Set WHO IITT RED/YELLOW/GREEN only from the criterion's actual source column.
- clinical_uses must be allowed by SOURCE_METADATA and directly supported.
- Do not invent an admission, treatment, diagnosis, urgency, or outcome.
- A heading with no clinical action may be retained only as
  DEFINITION_REFERENCE with a neutral documentary outcome.
- Use adult for BYT sections explicitly limited to adults.
- If a criterion cannot be repaired from these pages, put it in
  dropped_criteria with a precise reason. Zero repairs is valid.

Vietnamese summaries are documentary translations for later review. Return only
the requested structured object."""


def repair_verification_system_prompt() -> str:
    return """You independently verify one repaired guideline record.
Use only SOURCE_PAGES; do not use outside medical knowledge and do not rewrite.
Check the exact quote, meaning, numbers/operators/units, population, outcome,
clinical use, and triage-system category. A neutral DEFINITION_REFERENCE may
describe a heading but must not imply a clinical action. Reject invented claims
or category conversions. Use llm_verified only when every field is supported.
Return only the requested structured object."""


def repaired_candidate_id(
    original_candidate_id: str,
    original_criterion_index: int,
    candidate: ProtocolCandidate,
) -> str:
    payload = json.dumps(
        {
            "original_candidate_id": original_candidate_id,
            "original_criterion_index": original_criterion_index,
            "candidate": candidate.model_dump(mode="json"),
        },
        ensure_ascii=False,
        sort_keys=True,
    )
    suffix = hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]
    prefix = normalize_keyword(candidate.source_id)[:80]
    return f"{prefix}_repair_{original_criterion_index}_{suffix}"


def _package_by_id(paths: RepairPaths) -> dict[str, ReviewPackageRecord]:
    return {
        row.candidate_id: row
        for row in read_models(paths.review_package, ReviewPackageRecord)
    }


def _source_pages(
    candidate: ProtocolCandidate,
    pages: dict[tuple[str, int], ExtractedPage],
) -> list[ExtractedPage]:
    result = [
        pages[(candidate.source_id, number)]
        for number in sorted(candidate_pages(candidate))
        if (candidate.source_id, number) in pages
    ]
    if not result:
        raise RuntimeError(f"missing source pages for {candidate.source_id}")
    return result


def _estimate_tokens(requests: list[dict[str, Any]]) -> int:
    characters = sum(
        len(json.dumps(row["body"]["input"], ensure_ascii=False))
        for row in requests
    )
    return max(1, (characters + 3) // 4)


def _write_cost_estimate(
    paths: RepairPaths,
    *,
    stage: Literal["repair", "repair_retry", "repair_verification"],
    model: str,
    requests: list[dict[str, Any]],
    max_output_tokens: int,
) -> None:
    # Standard token prices from the official model pages on 2026-08-14.
    # Batch is estimated at 50% of synchronous cost per the Batch API guide.
    standard_prices = {
        "gpt-4o-mini": (0.15, 0.60),
        "gpt-5-mini": (0.25, 2.00),
    }
    input_tokens = _estimate_tokens(requests)
    output_upper_bound = len(requests) * max_output_tokens
    price = standard_prices.get(model)
    estimate: dict[str, Any] = {
        "generated_at": utc_now().isoformat(),
        "stage": stage,
        "model": model,
        "request_count": len(requests),
        "estimated_input_tokens": input_tokens,
        "configured_output_token_upper_bound": output_upper_bound,
        "method": "character_count_divided_by_4; not tokenizer-exact",
        "batch_discount_assumption": "50_percent_vs_synchronous",
    }
    if price:
        batch_input_per_million = price[0] / 2
        batch_output_per_million = price[1] / 2
        estimate.update({
            "batch_input_usd_per_1m_tokens": batch_input_per_million,
            "batch_output_usd_per_1m_tokens": batch_output_per_million,
            "estimated_input_cost_usd": round(
                input_tokens / 1_000_000 * batch_input_per_million,
                6,
            ),
            "configured_worst_case_total_usd": round(
                input_tokens / 1_000_000 * batch_input_per_million
                + output_upper_bound / 1_000_000 * batch_output_per_million,
                6,
            ),
        })
    existing: dict[str, Any] = {}
    if paths.cost_estimate.exists():
        existing = json.loads(paths.cost_estimate.read_text(encoding="utf-8"))
    existing[stage] = estimate
    write_json(paths.cost_estimate, existing)


def prepare_repair(paths: RepairPaths) -> None:
    for required in (
        paths.extracted_pages,
        paths.review_package,
        paths.original_excluded,
    ):
        require_file(required)
    settings = get_settings()
    package = _package_by_id(paths)
    pages = page_lookup(read_models(paths.extracted_pages, ExtractedPage))
    excluded = read_jsonl(paths.original_excluded)
    if len(excluded) != EXPECTED_REJECTED_GROUP_COUNT:
        raise RuntimeError(
            "expected exactly 5 rejected groups from the reviewed baseline; "
            f"found {len(excluded)}"
        )

    requests: list[dict[str, Any]] = []
    for disposition in excluded:
        original_id = str(disposition["candidate_id"])
        record = package.get(original_id)
        if record is None or record.llm_verification is None:
            raise RuntimeError(f"missing rejected review record: {original_id}")
        candidate = record.candidate
        source_spec = SOURCE_BY_ID[candidate.source_id]
        source_pages = _source_pages(candidate, pages)
        page_numbers = [page.page_number for page in source_pages]
        prompt_payload = {
            "original_candidate_id": original_id,
            "source_metadata": {
                "source_id": source_spec.source_id,
                "triage_system": source_spec.triage_system,
                "allowed_clinical_uses": source_spec.allowed_clinical_uses,
                "default_populations": source_spec.default_populations,
                "pages_seen": page_numbers,
            },
            "original_candidate": candidate.model_dump(mode="json"),
            "previous_verification": record.llm_verification.model_dump(
                mode="json"
            ),
            "previous_disposition_reasons": disposition.get(
                "disposition_reasons",
                [],
            ),
        }
        user_prompt = (
            "REPAIR_CONTEXT (not source evidence):\n"
            + json.dumps(prompt_payload, ensure_ascii=False)
            + "\n\nSOURCE_PAGES:\n"
            + render_source_pages(source_pages)
        )
        requests.append(response_batch_request(
            custom_id=f"repair__{original_id}",
            model=settings.protocol_openai_extraction_model,
            system_prompt=repair_system_prompt(),
            user_prompt=user_prompt,
            output_model=RepairEnvelope,
            schema_name="triage_protocol_atomic_repair",
            max_output_tokens=(
                settings.protocol_openai_extraction_max_output_tokens
            ),
        ))

    write_jsonl(paths.repair_input, requests)
    _write_cost_estimate(
        paths,
        stage="repair",
        model=settings.protocol_openai_extraction_model,
        requests=requests,
        max_output_tokens=settings.protocol_openai_extraction_max_output_tokens,
    )
    print(f"repair_requests={len(requests)}")
    print(f"batch_input={paths.repair_input}")
    print(f"cost_estimate={paths.cost_estimate}")
    print("openai_requests=0 database_writes=0 embedding_calls=0")


def _repair_numeric_errors(candidate: ProtocolCandidate) -> list[str]:
    errors: list[str] = []
    for index, criterion in enumerate(candidate.decision_criteria):
        criterion_numbers = _threshold_numeric_tokens(
            criterion.criterion_original
        )
        declared_numbers = {
            token
            for value in criterion.numeric_thresholds
            for token in _threshold_numeric_tokens(value)
        }
        if criterion_numbers and not criterion.numeric_thresholds:
            errors.append(f"criterion_{index}_missing_numeric_thresholds")
        elif not criterion_numbers.issubset(declared_numbers):
            errors.append(f"criterion_{index}_incomplete_numeric_thresholds")
    return errors


def _populate_missing_numeric_thresholds(
    candidate: ProtocolCandidate,
) -> ProtocolCandidate:
    criteria = []
    for criterion in candidate.decision_criteria:
        if criterion.numeric_thresholds:
            criteria.append(criterion)
            continue
        tokens = _threshold_numeric_token_list(criterion.criterion_original)
        criteria.append(criterion.model_copy(update={
            "numeric_thresholds": tokens,
        }))
    return candidate.model_copy(update={"decision_criteria": criteria})


def _threshold_numeric_token_list(value: str) -> list[str]:
    tokens = re.findall(
        r"(?<![A-Za-z])(?:<=|>=|<|>|≤|≥)?\s*\d+(?:[.,]\d+)?"
        r"(?:\s*(?:days? old|months?|°C|mmHg|điểm))?",
        value,
        flags=re.IGNORECASE,
    )
    return list(dict.fromkeys(token.strip() for token in tokens))


def _threshold_numeric_tokens(value: str) -> set[str]:
    """Return numeric tokens while ignoring digits embedded in labels (SpO2)."""
    tokens = re.findall(
        r"(?<![A-Za-z])(?:<=|>=|<|>|≤|≥)?\s*\d+(?:[.,]\d+)?",
        value,
    )
    return {
        re.sub(r"\s+", "", token).replace("≤", "<=").replace("≥", ">=")
        for token in tokens
    }


def _repair_content_errors(
    candidate: ProtocolCandidate,
    pages: dict[tuple[str, int], ExtractedPage],
) -> list[str]:
    relevant = [
        pages.get((candidate.source_id, page_number))
        for page_number in candidate_pages(candidate)
    ]
    if relevant and all(
        page is not None and "MỤC   LỤC" in page.text for page in relevant
    ):
        return ["table_of_contents_not_protocol_content"]
    return []


def _normalize_atomic_candidate(candidate: ProtocolCandidate) -> ProtocolCandidate:
    if len(candidate.decision_criteria) != 1:
        return candidate
    criterion = candidate.decision_criteria[0]
    return candidate.model_copy(update={
        "page_start": criterion.evidence_page,
        "page_end": criterion.evidence_page,
        "evidence_spans": [EvidenceSpan(
            page=criterion.evidence_page,
            quote=criterion.evidence_quote,
        )],
    })


def _atomicize_retry_candidate(
    candidate: ProtocolCandidate,
    original_criterion_index: int,
    original: ProtocolCandidate,
) -> ProtocolCandidate:
    target = original.decision_criteria[original_criterion_index]
    matches = [
        criterion
        for criterion in candidate.decision_criteria
        if (
            normalize_keyword(criterion.criterion_original)
            == normalize_keyword(target.criterion_original)
            or normalize_keyword(criterion.evidence_quote)
            == normalize_keyword(target.evidence_quote)
        )
    ]
    if len(matches) != 1:
        return candidate
    criterion = matches[0]
    return _normalize_atomic_candidate(candidate.model_copy(update={
        "decision_criteria": [criterion],
    }))


def _match_original_criterion_index(
    item: RepairedCandidateItem,
    original: ProtocolCandidate,
) -> int | None:
    repaired = item.candidate.decision_criteria[0]
    original_criteria = original.decision_criteria
    if item.original_criterion_index < len(original_criteria):
        claimed = original_criteria[item.original_criterion_index]
        if (
            normalize_keyword(claimed.criterion_original)
            == normalize_keyword(repaired.criterion_original)
            or normalize_keyword(claimed.evidence_quote)
            == normalize_keyword(repaired.evidence_quote)
        ):
            return item.original_criterion_index
    matches = [
        index
        for index, criterion in enumerate(original_criteria)
        if (
            normalize_keyword(criterion.criterion_original)
            == normalize_keyword(repaired.criterion_original)
            or normalize_keyword(criterion.evidence_quote)
            == normalize_keyword(repaired.evidence_quote)
        )
    ]
    return matches[0] if len(matches) == 1 else None


def parse_repair(paths: RepairPaths) -> None:
    for required in (
        paths.repair_output,
        paths.extracted_pages,
        paths.review_package,
        paths.original_excluded,
    ):
        require_file(required)
    settings = get_settings()
    package = _package_by_id(paths)
    excluded_ids = {
        str(row["candidate_id"]) for row in read_jsonl(paths.original_excluded)
    }
    pages = page_lookup(read_models(paths.extracted_pages, ExtractedPage))
    successes, api_errors = successful_batch_bodies(paths.repair_output)
    accepted: list[RepairCandidateRecord] = []
    rejected: list[dict[str, Any]] = list(api_errors)
    seen_ids: set[str] = set()

    for custom_id, body in successes:
        try:
            envelope = RepairEnvelope.model_validate_json(
                response_output_text(body)
            )
        except (ValidationError, ValueError, json.JSONDecodeError) as exc:
            rejected.append({
                "custom_id": custom_id,
                "reason": "invalid_structured_output",
                "error": str(exc),
            })
            continue
        original_id = envelope.original_candidate_id
        original = package.get(original_id)
        if (
            custom_id != f"repair__{original_id}"
            or original_id not in excluded_ids
            or original is None
            or envelope.source_id != original.candidate.source_id
        ):
            rejected.append({
                "custom_id": custom_id,
                "reason": "repair_scope_mismatch",
                "original_candidate_id": original_id,
            })
            continue
        expected_pages = candidate_pages(original.candidate)
        expected_indexes = set(range(len(original.candidate.decision_criteria)))
        if set(envelope.pages_seen) != expected_pages:
            rejected.append({
                "custom_id": custom_id,
                "reason": "repair_page_scope_mismatch",
                "expected_pages": sorted(expected_pages),
                "actual_pages": envelope.pages_seen,
            })
            continue
        emitted_indexes: set[int] = set()
        for item in envelope.repaired_candidates:
            candidate = _populate_missing_numeric_thresholds(
                _normalize_atomic_candidate(sanitize_candidate(item.candidate))
            )
            errors: list[str] = []
            if len(candidate.decision_criteria) != 1:
                errors.append("repair_not_atomic")
                mapped_index = None
            else:
                mapped_index = _match_original_criterion_index(
                    item,
                    original.candidate,
                )
                if mapped_index is None:
                    errors.append("original_criterion_mapping_failed")
                elif mapped_index in emitted_indexes:
                    errors.append("duplicate_original_criterion_mapping")
            if candidate.source_id != original.candidate.source_id:
                errors.append("source_id_changed")
            if not candidate_pages(candidate).issubset(expected_pages):
                errors.append("candidate_outside_source_pages")
            errors.extend(deterministic_candidate_errors(candidate, pages))
            errors.extend(_repair_numeric_errors(candidate))
            errors.extend(_repair_content_errors(candidate, pages))
            errors = sorted(set(errors))
            candidate_id = repaired_candidate_id(
                original_id,
                mapped_index if mapped_index is not None else 999,
                candidate,
            )
            if candidate_id in seen_ids:
                errors.append("duplicate_repaired_candidate")
            seen_ids.add(candidate_id)
            if errors:
                rejected.append({
                    "custom_id": custom_id,
                    "candidate_id": candidate_id,
                    "original_candidate_id": original_id,
                    "original_criterion_index": mapped_index,
                    "reason": "repair_deterministic_validation_failed",
                    "errors": sorted(set(errors)),
                    "candidate": candidate.model_dump(mode="json"),
                })
                continue
            assert mapped_index is not None
            emitted_indexes.add(mapped_index)
            source_page = pages[(candidate.source_id, candidate.page_start)]
            accepted.append(RepairCandidateRecord(
                candidate_id=candidate_id,
                original_candidate_id=original_id,
                original_criterion_index=mapped_index,
                citation_id=f"SIM-REPAIR:{candidate_id}",
                source_sha256=source_page.source_sha256,
                pipeline_version=PIPELINE_VERSION,
                repair_prompt_version=REPAIR_PROMPT_VERSION,
                repair_model=settings.protocol_openai_extraction_model,
                candidate=candidate,
                deterministic_flags=[],
                risk_flags=candidate_risk_flags(candidate, pages),
                validation_status="repaired_candidate",
            ))
        for missing_index in sorted(expected_indexes - emitted_indexes):
            rejected.append({
                "custom_id": custom_id,
                "original_candidate_id": original_id,
                "original_criterion_index": missing_index,
                "reason": "criterion_not_emitted_or_valid",
                "model_drop_notes": [
                    dropped.model_dump(mode="json")
                    for dropped in envelope.dropped_criteria
                ],
            })

    write_jsonl(paths.repaired_candidates, accepted)
    write_jsonl(paths.repair_rejected, rejected)
    print(f"repaired_candidates={len(accepted)}")
    print(f"repair_rejected_or_dropped={len(rejected)}")
    print("clinical_approval=false database_writes=0 embedding_calls=0")


def prepare_repair_retry(paths: RepairPaths) -> None:
    for required in (
        paths.repaired_candidates,
        paths.review_package,
        paths.original_excluded,
        paths.extracted_pages,
    ):
        require_file(required)
    settings = get_settings()
    package = _package_by_id(paths)
    excluded_ids = {
        str(row["candidate_id"]) for row in read_jsonl(paths.original_excluded)
    }
    repaired = read_models(paths.repaired_candidates, RepairCandidateRecord)
    emitted_by_group: dict[str, set[int]] = {}
    for row in repaired:
        emitted_by_group.setdefault(row.original_candidate_id, set()).add(
            row.original_criterion_index
        )
    pages = page_lookup(read_models(paths.extracted_pages, ExtractedPage))
    requests: list[dict[str, Any]] = []
    for original_id in sorted(excluded_ids):
        original = package[original_id]
        source_pages = _source_pages(original.candidate, pages)
        expected = set(range(len(original.candidate.decision_criteria)))
        missing = expected - emitted_by_group.get(original_id, set())
        for criterion_index in sorted(missing):
            criterion = original.candidate.decision_criteria[criterion_index]
            prompt = {
                "original_candidate_id": original_id,
                "original_criterion_index": criterion_index,
                "source_id": original.candidate.source_id,
                "triage_system": original.candidate.triage_system,
                "allowed_clinical_uses": SOURCE_BY_ID[
                    original.candidate.source_id
                ].allowed_clinical_uses,
                "required_pages_seen": [
                    page.page_number for page in source_pages
                ],
                "original_candidate_context": original.candidate.model_dump(
                    mode="json"
                ),
                "criterion_to_repair": criterion.model_dump(mode="json"),
            }
            user_prompt = (
                "SINGLE_CRITERION_RETRY (not source evidence):\n"
                + json.dumps(prompt, ensure_ascii=False)
                + "\n\nSOURCE_PAGES:\n"
                + render_source_pages(source_pages)
            )
            requests.append(response_batch_request(
                custom_id=f"repair_retry__{original_id}__c{criterion_index}",
                model=settings.protocol_openai_extraction_model,
                system_prompt=(
                    repair_system_prompt()
                    + "\nThis retry contains exactly one criterion. Keep the exact "
                    "original_criterion_index. Return repaired_candidate when "
                    "the source supports any safe documentary representation; "
                    "otherwise return null and explain drop_reason."
                ),
                user_prompt=user_prompt,
                output_model=SingleRepairEnvelope,
                schema_name="triage_protocol_single_atomic_repair",
                max_output_tokens=4_000,
            ))
    if not requests:
        raise RuntimeError("all rejected criteria already have atomic repairs")
    write_jsonl(paths.repair_retry_input, requests)
    _write_cost_estimate(
        paths,
        stage="repair_retry",
        model=settings.protocol_openai_extraction_model,
        requests=requests,
        max_output_tokens=4_000,
    )
    print(f"repair_retry_requests={len(requests)}")
    print(f"batch_input={paths.repair_retry_input}")
    print("openai_requests=0 database_writes=0 embedding_calls=0")


def parse_repair_retry(paths: RepairPaths) -> None:
    for required in (
        paths.repair_retry_output,
        paths.repaired_candidates,
        paths.review_package,
        paths.extracted_pages,
    ):
        require_file(required)
    settings = get_settings()
    package = _package_by_id(paths)
    pages = page_lookup(read_models(paths.extracted_pages, ExtractedPage))
    accepted = read_models(paths.repaired_candidates, RepairCandidateRecord)
    rejected = read_jsonl(paths.repair_rejected)
    existing_keys = {
        (row.original_candidate_id, row.original_criterion_index)
        for row in accepted
    }
    successes, api_errors = successful_batch_bodies(paths.repair_retry_output)
    rejected.extend(api_errors)
    for custom_id, body in successes:
        try:
            envelope = SingleRepairEnvelope.model_validate_json(
                response_output_text(body)
            )
        except (ValidationError, ValueError, json.JSONDecodeError) as exc:
            rejected.append({
                "custom_id": custom_id,
                "reason": "invalid_retry_structured_output",
                "error": str(exc),
            })
            continue
        key = (
            envelope.original_candidate_id,
            envelope.original_criterion_index,
        )
        original = package.get(envelope.original_candidate_id)
        expected_custom_id = (
            f"repair_retry__{envelope.original_candidate_id}"
            f"__c{envelope.original_criterion_index}"
        )
        if key in existing_keys:
            continue
        if (
            custom_id != expected_custom_id
            or original is None
            or envelope.source_id != original.candidate.source_id
            or not set(envelope.pages_seen)
            or not set(envelope.pages_seen).issubset(
                candidate_pages(original.candidate)
            )
        ):
            rejected.append({
                "custom_id": custom_id,
                "reason": "repair_retry_scope_mismatch",
            })
            continue
        candidate = envelope.repaired_candidate
        if candidate is None:
            rejected.append({
                "custom_id": custom_id,
                "original_candidate_id": key[0],
                "original_criterion_index": key[1],
                "reason": "criterion_dropped_after_retry",
                "detail": envelope.drop_reason,
            })
            continue
        candidate = _atomicize_retry_candidate(
            candidate,
            envelope.original_criterion_index,
            original.candidate,
        )
        candidate = _populate_missing_numeric_thresholds(
            sanitize_candidate(candidate)
        )
        errors: list[str] = []
        if len(candidate.decision_criteria) != 1:
            errors.append("repair_not_atomic")
        if candidate.source_id != original.candidate.source_id:
            errors.append("source_id_changed")
        if not candidate_pages(candidate).issubset(candidate_pages(original.candidate)):
            errors.append("candidate_outside_source_pages")
        if not candidate_pages(candidate).issubset(set(envelope.pages_seen)):
            errors.append("candidate_pages_not_reported_as_seen")
        errors.extend(deterministic_candidate_errors(candidate, pages))
        errors.extend(_repair_numeric_errors(candidate))
        errors.extend(_repair_content_errors(candidate, pages))
        candidate_id = repaired_candidate_id(key[0], key[1], candidate)
        if errors:
            rejected.append({
                "custom_id": custom_id,
                "candidate_id": candidate_id,
                "original_candidate_id": key[0],
                "original_criterion_index": key[1],
                "reason": "repair_retry_deterministic_validation_failed",
                "errors": sorted(set(errors)),
                "candidate": candidate.model_dump(mode="json"),
            })
            continue
        source_page = pages[(candidate.source_id, candidate.page_start)]
        accepted.append(RepairCandidateRecord(
            candidate_id=candidate_id,
            original_candidate_id=key[0],
            original_criterion_index=key[1],
            citation_id=f"SIM-REPAIR:{candidate_id}",
            source_sha256=source_page.source_sha256,
            pipeline_version=PIPELINE_VERSION,
            repair_prompt_version=REPAIR_PROMPT_VERSION,
            repair_model=settings.protocol_openai_extraction_model,
            candidate=candidate,
            deterministic_flags=[],
            risk_flags=candidate_risk_flags(candidate, pages),
            validation_status="repaired_candidate",
        ))
        existing_keys.add(key)
    write_jsonl(paths.repaired_candidates, accepted)
    write_jsonl(paths.repair_rejected, rejected)
    print(f"repaired_candidates_total={len(accepted)}")
    print(f"repair_audit_records={len(rejected)}")
    print("clinical_approval=false database_writes=0 embedding_calls=0")


def prepare_repair_verification(paths: RepairPaths) -> None:
    require_file(paths.repaired_candidates)
    require_file(paths.extracted_pages)
    settings = get_settings()
    repaired = read_models(paths.repaired_candidates, RepairCandidateRecord)
    if not repaired:
        raise RuntimeError("no repaired candidates to verify")
    pages = page_lookup(read_models(paths.extracted_pages, ExtractedPage))
    requests: list[dict[str, Any]] = []
    for record in repaired:
        source_pages = _source_pages(record.candidate, pages)
        user_prompt = (
            "REPAIRED_CANDIDATE:\n"
            + json.dumps(
                {
                    "candidate_id": record.candidate_id,
                    "original_candidate_id": record.original_candidate_id,
                    "original_criterion_index": record.original_criterion_index,
                    "candidate": record.candidate.model_dump(mode="json"),
                },
                ensure_ascii=False,
            )
            + "\n\nSOURCE_PAGES:\n"
            + render_source_pages(source_pages)
        )
        requests.append(response_batch_request(
            custom_id=f"repair_verify__{record.candidate_id}",
            model=settings.protocol_openai_verification_model,
            system_prompt=repair_verification_system_prompt(),
            user_prompt=user_prompt,
            output_model=VerificationEnvelope,
            schema_name="triage_protocol_repair_verification",
            max_output_tokens=(
                settings.protocol_openai_verification_max_output_tokens
            ),
        ))
    write_jsonl(paths.repair_verification_input, requests)
    _write_cost_estimate(
        paths,
        stage="repair_verification",
        model=settings.protocol_openai_verification_model,
        requests=requests,
        max_output_tokens=(
            settings.protocol_openai_verification_max_output_tokens
        ),
    )
    print(f"repair_verification_requests={len(requests)}")
    print(f"batch_input={paths.repair_verification_input}")
    print(f"cost_estimate={paths.cost_estimate}")
    print("openai_requests=0 database_writes=0 embedding_calls=0")


def parse_repair_verification(paths: RepairPaths) -> None:
    require_file(paths.repair_verification_output)
    require_file(paths.repaired_candidates)
    settings = get_settings()
    candidates = {
        row.candidate_id: row
        for row in read_models(paths.repaired_candidates, RepairCandidateRecord)
    }
    successes, api_errors = successful_batch_bodies(
        paths.repair_verification_output
    )
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
        candidate = candidates.get(envelope.candidate_id)
        if (
            custom_id != f"repair_verify__{envelope.candidate_id}"
            or candidate is None
        ):
            errors.append({
                "custom_id": custom_id,
                "reason": "repair_verification_scope_mismatch",
                "candidate_id": envelope.candidate_id,
            })
            continue
        if envelope.candidate_id in seen:
            errors.append({
                "custom_id": custom_id,
                "reason": "duplicate_repair_verification",
                "candidate_id": envelope.candidate_id,
            })
            continue
        seen.add(envelope.candidate_id)
        envelope = normalize_verification_decision(envelope, criterion_count=1)
        records.append(VerificationRecord(
            candidate_id=envelope.candidate_id,
            verification_model=settings.protocol_openai_verification_model,
            verification_prompt_version=REPAIR_VERIFICATION_PROMPT_VERSION,
            decision=envelope.decision,
            source_grounding_passed=envelope.source_grounding_passed,
            triage_system_separation_passed=(
                envelope.triage_system_separation_passed
            ),
            criterion_checks=envelope.criterion_checks,
            issues=envelope.issues,
        ))
    write_jsonl(paths.repair_verifications, records)
    write_jsonl(paths.repair_verification_parse_errors, errors)
    print(f"repair_verification_records={len(records)}")
    print(f"repair_verification_errors={len(errors)}")
    print("clinical_approval=false database_writes=0 embedding_calls=0")


def documentary_gate_passes(verification: VerificationRecord) -> bool:
    if not verification.source_grounding_passed:
        return False
    if not verification.triage_system_separation_passed:
        return False
    if {check.criterion_index for check in verification.criterion_checks} != {0}:
        return False
    if not all(
        check.source_supported
        and check.evidence_quote_exact
        and check.numeric_thresholds_preserved
        for check in verification.criterion_checks
    ):
        return False
    return not any(issue.severity == "error" for issue in verification.issues)


def _common_demo_fields() -> dict[str, Any]:
    return {
        "simulation_only": True,
        "clinical_approval": False,
        "eligible_for_internal_demo_retrieval": True,
        "public_distribution_allowed": False,
        "license_review_required": True,
        "requires_clinician_review_before_real_use": True,
        "allowed_uses": [
            "internal_synthetic_demo",
            "retrieval_and_citation_demo",
            "hitl_workflow_demo",
        ],
        "prohibited_uses": [
            "real_patient_triage",
            "autonomous_esi_assignment",
            "diagnosis_or_treatment",
            "public_distribution_before_license_review",
        ],
    }


def build_owner_allowlist(paths: RepairPaths) -> None:
    for required in (
        paths.strict_allowlist,
        paths.original_review_queue,
        paths.review_package,
        paths.repaired_candidates,
        paths.repair_verifications,
    ):
        require_file(required)
    generated_at = utc_now()
    package = _package_by_id(paths)
    strict_rows = read_jsonl(paths.strict_allowlist)
    owner_queue = read_jsonl(paths.original_review_queue)
    if len(owner_queue) != EXPECTED_OWNER_ACCEPTED_COUNT:
        raise RuntimeError(
            "expected exactly 9 owner-reviewed candidates; "
            f"found {len(owner_queue)}"
        )
    accepted_ids = [str(row["candidate_id"]) for row in owner_queue]
    write_json(paths.owner_acceptance, {
        "accepted_at": generated_at.isoformat(),
        "accepted_via": "explicit_project_owner_instruction",
        "scope": "internal_synthetic_demo_only",
        "candidate_ids": accepted_ids,
        "candidate_count": len(accepted_ids),
        "clinical_approval": False,
        "requires_clinician_review_before_real_use": True,
    })

    allowlist: list[dict[str, Any]] = []
    common = _common_demo_fields()
    for row in strict_rows:
        allowlist.append({
            **common,
            "candidate_id": row["candidate_id"],
            "citation_id": row["citation_id"],
            "source_sha256": row["source_sha256"],
            "pipeline_version": PIPELINE_VERSION,
            "generated_at": generated_at.isoformat(),
            "origin": "strict_documentary_gate",
            "demo_status": "demo_eligible_nonclinical",
            "project_owner_override": False,
            "documentary_limitations": [],
            "candidate": row["candidate"],
            "llm_verification": row["llm_verification"],
        })
    for disposition in owner_queue:
        candidate_id = str(disposition["candidate_id"])
        record = package.get(candidate_id)
        if record is None or record.llm_verification is None:
            raise RuntimeError(f"missing owner-accepted candidate: {candidate_id}")
        allowlist.append({
            **common,
            "candidate_id": candidate_id,
            "citation_id": record.citation_id,
            "source_sha256": record.source_sha256,
            "pipeline_version": PIPELINE_VERSION,
            "generated_at": generated_at.isoformat(),
            "origin": "project_owner_accepted_existing_candidate",
            "demo_status": "project_owner_accepted_nonclinical",
            "project_owner_override": True,
            "documentary_limitations": disposition.get(
                "disposition_reasons",
                [],
            ),
            "candidate": record.candidate.model_dump(mode="json"),
            "llm_verification": record.llm_verification.model_dump(mode="json"),
        })

    repaired = read_models(paths.repaired_candidates, RepairCandidateRecord)
    verification_by_id = {
        row.candidate_id: row
        for row in read_models(paths.repair_verifications, VerificationRecord)
    }
    repair_review_queue: list[dict[str, Any]] = []
    recovered_groups: set[str] = set()
    for record in repaired:
        verification = verification_by_id.get(record.candidate_id)
        if verification is None or not documentary_gate_passes(verification):
            repair_review_queue.append({
                "candidate_id": record.candidate_id,
                "original_candidate_id": record.original_candidate_id,
                "original_criterion_index": record.original_criterion_index,
                "reason": "repair_failed_independent_documentary_gate",
                "verification": (
                    verification.model_dump(mode="json")
                    if verification
                    else None
                ),
                "clinical_approval": False,
            })
            continue
        recovered_groups.add(record.original_candidate_id)
        owner_override = verification.decision != "llm_verified"
        allowlist.append({
            **common,
            "candidate_id": record.candidate_id,
            "citation_id": record.citation_id,
            "source_sha256": record.source_sha256,
            "pipeline_version": PIPELINE_VERSION,
            "generated_at": generated_at.isoformat(),
            "origin": "atomic_repair_from_rejected_candidate",
            "original_candidate_id": record.original_candidate_id,
            "original_criterion_index": record.original_criterion_index,
            "demo_status": (
                "repaired_documentary_verified_nonclinical"
                if not owner_override
                else "repaired_project_owner_accepted_nonclinical"
            ),
            "project_owner_override": owner_override,
            "documentary_limitations": [
                issue.code for issue in verification.issues
            ],
            "candidate": record.candidate.model_dump(mode="json"),
            "llm_verification": verification.model_dump(mode="json"),
        })

    candidate_ids = [str(row["candidate_id"]) for row in allowlist]
    if len(candidate_ids) != len(set(candidate_ids)):
        raise RuntimeError("duplicate candidate in v2 demo allowlist")
    write_jsonl(paths.allowlist_v2, allowlist)
    write_jsonl(paths.repair_review_queue, repair_review_queue)
    repair_audit = read_jsonl(paths.repair_rejected)
    dropped_count = sum(
        row.get("reason") == "criterion_dropped_by_repair"
        for row in repair_audit
    )
    summary = {
        "pipeline_version": PIPELINE_VERSION,
        "generated_at": generated_at.isoformat(),
        "strict_documentary_records": len(strict_rows),
        "project_owner_accepted_existing_records": len(owner_queue),
        "repaired_records_in_allowlist": sum(
            row.get("origin") == "atomic_repair_from_rejected_candidate"
            for row in allowlist
        ),
        "total_demo_allowlist_v2": len(allowlist),
        "rejected_groups_targeted": EXPECTED_REJECTED_GROUP_COUNT,
        "rejected_groups_with_at_least_one_recovered_record": len(
            recovered_groups
        ),
        "recovered_original_candidate_ids": sorted(recovered_groups),
        "repair_review_queue": len(repair_review_queue),
        "criteria_dropped_with_audit_reason": dropped_count,
        "simulation_only": True,
        "clinical_approval": False,
        "requires_clinician_review_before_real_use": True,
        "database_writes": 0,
        "embedding_calls": 0,
    }
    write_json(paths.allowlist_v2_summary, summary)
    print(f"demo_allowlist_v2={len(allowlist)}")
    print(f"repaired_records_in_allowlist={summary['repaired_records_in_allowlist']}")
    print(f"recovered_rejected_groups={len(recovered_groups)}")
    print(f"repair_review_queue={len(repair_review_queue)}")
    print("clinical_approval=false database_writes=0 embedding_calls=0")


def resolve_repo_path(value: str) -> Path:
    path = Path(value)
    if not path.is_absolute():
        path = REPO_ROOT / path
    return path.resolve()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Repair rejected protocol candidates for internal demo use."
    )
    parser.add_argument(
        "--work-dir",
        default="data/protocol_corpus/work/simulation_v1",
    )
    parser.add_argument(
        "command",
        choices=(
            "prepare-repair",
            "submit-repair",
            "download-repair",
            "parse-repair",
            "prepare-repair-retry",
            "submit-repair-retry",
            "download-repair-retry",
            "parse-repair-retry",
            "prepare-repair-verification",
            "submit-repair-verification",
            "download-repair-verification",
            "parse-repair-verification",
            "build-owner-allowlist",
        ),
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    os.chdir(REPO_ROOT)
    paths = repair_paths(resolve_repo_path(args.work_dir))
    settings = get_settings()
    if args.command == "prepare-repair":
        prepare_repair(paths)
    elif args.command == "submit-repair":
        submit_batch(
            stage="repair",
            input_path=paths.repair_input,
            job_path=paths.repair_job,
            model=settings.protocol_openai_extraction_model,
        )
    elif args.command == "download-repair":
        return download_batch(
            job_path=paths.repair_job,
            output_path=paths.repair_output,
            error_path=paths.repair_api_errors,
        )
    elif args.command == "parse-repair":
        parse_repair(paths)
    elif args.command == "prepare-repair-retry":
        prepare_repair_retry(paths)
    elif args.command == "submit-repair-retry":
        submit_batch(
            stage="repair",
            input_path=paths.repair_retry_input,
            job_path=paths.repair_retry_job,
            model=settings.protocol_openai_extraction_model,
        )
    elif args.command == "download-repair-retry":
        return download_batch(
            job_path=paths.repair_retry_job,
            output_path=paths.repair_retry_output,
            error_path=paths.repair_retry_api_errors,
        )
    elif args.command == "parse-repair-retry":
        parse_repair_retry(paths)
    elif args.command == "prepare-repair-verification":
        prepare_repair_verification(paths)
    elif args.command == "submit-repair-verification":
        submit_batch(
            stage="repair_verification",
            input_path=paths.repair_verification_input,
            job_path=paths.repair_verification_job,
            model=settings.protocol_openai_verification_model,
        )
    elif args.command == "download-repair-verification":
        return download_batch(
            job_path=paths.repair_verification_job,
            output_path=paths.repair_verification_output,
            error_path=paths.repair_verification_api_errors,
        )
    elif args.command == "parse-repair-verification":
        parse_repair_verification(paths)
    elif args.command == "build-owner-allowlist":
        build_owner_allowlist(paths)
    else:
        raise AssertionError(f"unhandled command: {args.command}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(
            f"Protocol repair pipeline aborted: {type(exc).__name__}: {exc}",
            file=sys.stderr,
        )
        raise SystemExit(1) from exc
