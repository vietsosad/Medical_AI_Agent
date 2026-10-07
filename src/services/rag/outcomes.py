"""Typed retrieval outcomes.

The failure this exists to prevent is concrete and was live in production: the
MIETIC retriever raised a pgvector dimension error, the exception was swallowed
into an empty result list, the empty list was read as "no supporting evidence",
and the patient was told there was not enough evidence to assign a triage
level. A database fault was delivered as a clinical finding.

So a retrieval call reports what actually happened, and only ``SUCCESS`` may be
interpreted clinically. Everything else is an operational signal: a technical
failure must reach logs and operators, never a patient as a triage conclusion.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any


class RetrievalStatus(StrEnum):
    # The query ran and returned usable candidates.
    SUCCESS = "SUCCESS"

    # The query ran correctly; the corpus simply holds nothing matching.
    NO_RESULTS = "NO_RESULTS"
    # Candidates came back but none cleared the relevance floor.
    LOW_RELEVANCE = "LOW_RELEVANCE"

    # Technical faults. None of these say anything about the patient.
    EMBEDDING_FAILURE = "EMBEDDING_FAILURE"
    DIMENSION_MISMATCH = "DIMENSION_MISMATCH"
    DATABASE_FAILURE = "DATABASE_FAILURE"
    RETRIEVAL_FAILURE = "RETRIEVAL_FAILURE"

    @property
    def is_technical_failure(self) -> bool:
        return self in {
            RetrievalStatus.EMBEDDING_FAILURE,
            RetrievalStatus.DIMENSION_MISMATCH,
            RetrievalStatus.DATABASE_FAILURE,
            RetrievalStatus.RETRIEVAL_FAILURE,
        }

    @property
    def permits_clinical_interpretation(self) -> bool:
        """Only a successful retrieval may be reasoned about clinically."""
        return self is RetrievalStatus.SUCCESS


@dataclass(frozen=True)
class RetrievedItem:
    """One candidate, carrying enough provenance to be audited or rejected."""

    doc_id: str
    text: str
    score: float
    source_table: str
    retrieval_scope: str
    authority_status: str
    retrieval_channel: str
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def is_authority(self) -> bool:
        """Authority is a property of the corpus row, never of the ranking."""
        return (
            self.retrieval_scope == "CLINICAL_AUTHORITY"
            and self.authority_status == "AUTHORITATIVE"
        )


@dataclass(frozen=True)
class RetrievalOutcome:
    status: RetrievalStatus
    items: tuple[RetrievedItem, ...] = ()
    query_vi: str = ""
    query_en: str = ""
    channels: tuple[str, ...] = ()
    filters: dict[str, Any] = field(default_factory=dict)
    error: str | None = None
    detail: str | None = None

    @property
    def ok(self) -> bool:
        return self.status.permits_clinical_interpretation

    @property
    def authority_items(self) -> tuple[RetrievedItem, ...]:
        return tuple(item for item in self.items if item.is_authority)

    def audit(self) -> dict[str, Any]:
        return {
            "status": self.status.value,
            "technical_failure": self.status.is_technical_failure,
            "item_count": len(self.items),
            "authority_count": len(self.authority_items),
            "query_vi": self.query_vi,
            "query_en": self.query_en,
            "channels": list(self.channels),
            "filters": self.filters,
            "doc_ids": [item.doc_id for item in self.items],
            "error": self.error,
        }


def technical_failure(
    status: RetrievalStatus, error: BaseException, **context: Any
) -> RetrievalOutcome:
    """Build a failure outcome that keeps the cause instead of erasing it."""
    if not status.is_technical_failure:
        raise ValueError(f"{status} is not a technical failure")
    return RetrievalOutcome(
        status=status,
        error=f"{type(error).__name__}: {error}",
        **context,
    )
