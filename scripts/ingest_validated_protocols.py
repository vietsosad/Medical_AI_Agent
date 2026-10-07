#!/usr/bin/env python3
"""Validate and ingest clinician-approved protocol sections.

The command is validation-only by default. ``--apply`` is deliberately gated
by an authoritative-source whitelist, a clinical review record, a licensing
reference, an approved calibration profile and a pinned embedding revision.
No network fallback, dummy vector, inferred criterion or inferred keyword is
allowed.

Example:
    python scripts/ingest_validated_protocols.py path/to/manifest.json
    python scripts/ingest_validated_protocols.py path/to/manifest.json --apply
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, Field, HttpUrl, field_validator, model_validator
from sqlalchemy import select
from sqlmodel import SQLModel, Session


REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from src.config import get_settings  # noqa: E402
from src.services.db import sync_engine  # noqa: E402


MANIFEST_VERSION = "validated-protocol-manifest-v1"
EXPECTED_EMBEDDING_DIMENSION = 1024
CONTROLLED_TERM = re.compile(r"^[a-z0-9]+(?:[_:.\-/][a-z0-9]+)*$")
POPULATION_SCOPES = {
    "adult",
    "pediatric",
    "geriatric",
    "all_populations",
}


class CalibrationProfile(BaseModel):
    symptom_cluster: str = Field(min_length=2, max_length=120)
    population: Literal[
        "adult",
        "pediatric",
        "geriatric",
        "all_populations",
    ]
    thresholds: dict[Literal["vi_dense", "en_dense"], float]
    min_passing_dense_channels: int = Field(default=1, ge=1, le=2)
    approved_by: str = Field(min_length=3, max_length=300)
    approved_at: datetime

    @field_validator("thresholds")
    @classmethod
    def validate_thresholds(
        cls,
        value: dict[str, float],
    ) -> dict[str, float]:
        if not value:
            raise ValueError("at least one calibrated dense channel is required")
        if any(score < -1.0 or score > 1.0 for score in value.values()):
            raise ValueError("channel thresholds must be in -1..1")
        return value


class ProtocolChunk(BaseModel):
    """One clinician-reviewed decision section; never an arbitrary text slice."""

    citation_id: str = Field(min_length=8, max_length=240)
    chunk_id: str = Field(min_length=1, max_length=120)
    protocol_code: str = Field(min_length=2, max_length=120)
    title: str = Field(min_length=3, max_length=500)
    issuing_body: str = Field(min_length=2, max_length=300)
    source: str = Field(min_length=2, max_length=160)
    source_uri: HttpUrl
    license_reference: str = Field(min_length=3, max_length=500)
    version: str = Field(min_length=1, max_length=120)
    effective_date: datetime
    expires_at: datetime | None = None
    section: str = Field(min_length=1, max_length=240)
    document_type: Literal["validated_protocol"]
    clinical_scope: list[str] = Field(min_length=1, max_length=30)
    validation_status: Literal["approved"]
    reviewed_by: str = Field(min_length=3, max_length=300)
    reviewed_at: datetime
    parser_version: str = Field(min_length=1, max_length=120)
    page_content: str = Field(min_length=80, max_length=50_000)
    decision_criteria: list[str] = Field(min_length=1, max_length=50)
    keywords: list[str] = Field(min_length=1, max_length=100)
    calibration_id: str = Field(min_length=3, max_length=160)
    calibration_profile: CalibrationProfile
    content_hash: str | None = Field(default=None, pattern=r"^[a-f0-9]{64}$")

    @model_validator(mode="after")
    def validate_authority_and_integrity(self) -> ProtocolChunk:
        for field_name, value in (
            ("effective_date", self.effective_date),
            ("expires_at", self.expires_at),
            ("reviewed_at", self.reviewed_at),
        ):
            if value is not None and value.tzinfo is None:
                raise ValueError(f"{field_name} must include an explicit timezone")
        if self.expires_at is not None and self.expires_at <= self.effective_date:
            raise ValueError("expires_at must be later than effective_date")
        if self.reviewed_at > datetime.now(UTC):
            raise ValueError("reviewed_at cannot be in the future")
        if self.calibration_profile.approved_at.tzinfo is None:
            raise ValueError("calibration approved_at must include a timezone")
        if self.calibration_profile.approved_at > datetime.now(UTC):
            raise ValueError("calibration approved_at cannot be in the future")
        if self.calibration_profile.symptom_cluster not in self.clinical_scope:
            raise ValueError("calibration symptom_cluster must be in clinical_scope")
        if self.calibration_profile.population not in self.clinical_scope:
            if "all_populations" not in self.clinical_scope:
                raise ValueError("calibration population must be in clinical_scope")
        if (
            self.calibration_profile.min_passing_dense_channels
            > len(self.calibration_profile.thresholds)
        ):
            raise ValueError("min_passing_dense_channels exceeds calibrated channels")
        invalid_terms = [
            term
            for term in [*self.clinical_scope, *self.keywords]
            if not CONTROLLED_TERM.fullmatch(term)
        ]
        if invalid_terms:
            raise ValueError(
                f"clinical_scope/keywords must be controlled terms: {invalid_terms}"
            )
        if not POPULATION_SCOPES.intersection(self.clinical_scope):
            raise ValueError(
                "clinical_scope must include an explicit population scope"
            )
        expected_hash = content_hash(self.page_content)
        if self.content_hash is not None and self.content_hash != expected_hash:
            raise ValueError("content_hash does not match page_content")
        return self


class ProtocolManifest(BaseModel):
    manifest_version: Literal[MANIFEST_VERSION]
    clinical_owner: str = Field(min_length=3, max_length=300)
    export_approved_at: datetime
    chunks: list[ProtocolChunk] = Field(min_length=1)

    @model_validator(mode="after")
    def validate_unique_ids(self) -> ProtocolManifest:
        citation_ids = [chunk.citation_id for chunk in self.chunks]
        if len(citation_ids) != len(set(citation_ids)):
            raise ValueError("citation_id must be unique within the manifest")
        return self


def content_hash(page_content: str) -> str:
    normalized = "\n".join(
        line.rstrip() for line in page_content.strip().splitlines()
    )
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("manifest_path", type=Path)
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Create the protocol table and insert verified, embedded sections.",
    )
    parser.add_argument("--batch-size", type=int, default=32)
    args = parser.parse_args()
    if args.batch_size < 1 or args.batch_size > 256:
        parser.error("--batch-size must be in 1..256")
    return args


def parse_whitelist(raw_value: str) -> set[str]:
    return {item.strip() for item in raw_value.split(",") if item.strip()}


def load_manifest(path: Path) -> ProtocolManifest:
    payload = json.loads(path.read_text(encoding="utf-8"))
    return ProtocolManifest.model_validate(payload)


def validate_deployment_configuration(manifest: ProtocolManifest) -> None:
    settings = get_settings()
    whitelist = parse_whitelist(settings.rag_protocol_source_whitelist)
    if not whitelist:
        raise RuntimeError("RAG_PROTOCOL_SOURCE_WHITELIST is empty")
    unexpected = sorted({chunk.source for chunk in manifest.chunks} - whitelist)
    if unexpected:
        raise RuntimeError(f"manifest contains non-whitelisted sources: {unexpected}")
    if not settings.embedding_model_revision.strip():
        raise RuntimeError("EMBEDDING_MODEL_REVISION must be an immutable revision")


def load_embedder() -> tuple[Any, str, str]:
    try:
        from langchain_huggingface import HuggingFaceEmbeddings
    except ImportError as exc:
        raise RuntimeError(
            "langchain_huggingface is required; dummy embeddings are prohibited"
        ) from exc

    settings = get_settings()
    revision = settings.embedding_model_revision.strip()
    embedder = HuggingFaceEmbeddings(
        model_name=settings.embedding_model_name,
        model_kwargs={"revision": revision},
    )
    probe = embedder.embed_query("validated embedding dimension probe")
    if (
        len(probe) != EXPECTED_EMBEDDING_DIMENSION
        or len({round(value, 8) for value in probe}) <= 1
    ):
        raise RuntimeError("embedding probe is invalid or dimension is not 1024")
    return embedder, settings.embedding_model_name, revision


def _naive_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value
    return value.astimezone(UTC).replace(tzinfo=None)


def ingest(manifest: ProtocolManifest, batch_size: int) -> tuple[int, int]:
    # ``TriageProtocolDocument`` went away with the legacy RAG tables.  The
    # manifest validation in this module is still what stops a draft being
    # ingested, so the dead write path fails here, at call time, rather than
    # breaking the import for every caller of ``ProtocolManifest``.
    try:
        from src.models.db_models import TriageProtocolDocument
    except ImportError as exc:  # pragma: no cover - retired ingest path
        raise RuntimeError(
            "protocol ingest is retired: triage_protocol_documents was dropped "
            "in the deployment cleanup. Load the Pass-5 corpus into "
            "esi_knowledge_documents instead."
        ) from exc

    if sync_engine.dialect.name != "postgresql":
        raise RuntimeError("protocol ingest requires PostgreSQL with pgvector")
    validate_deployment_configuration(manifest)
    embedder, model_name, model_revision = load_embedder()
    SQLModel.metadata.create_all(
        sync_engine,
        tables=[TriageProtocolDocument.__table__],
    )

    inserted = 0
    already_present = 0
    for offset in range(0, len(manifest.chunks), batch_size):
        batch = manifest.chunks[offset : offset + batch_size]
        citation_ids = [chunk.citation_id for chunk in batch]
        with Session(sync_engine) as session:
            existing_rows = session.exec(
                select(TriageProtocolDocument).where(
                    TriageProtocolDocument.citation_id.in_(citation_ids)
                )
            ).all()
            existing = {row.citation_id: row for row in existing_rows}
            pending: list[ProtocolChunk] = []
            for chunk in batch:
                old = existing.get(chunk.citation_id)
                if old is None:
                    pending.append(chunk)
                    continue
                if old.content_hash != content_hash(chunk.page_content):
                    raise RuntimeError(
                        f"citation {chunk.citation_id} already exists with different content; "
                        "publish a new version/chunk ID instead of overwriting"
                    )
                already_present += 1
            if not pending:
                continue

            vectors = embedder.embed_documents(
                [chunk.page_content for chunk in pending]
            )
            if any(
                len(vector) != EXPECTED_EMBEDDING_DIMENSION
                or len({round(value, 8) for value in vector}) <= 1
                for vector in vectors
            ):
                raise RuntimeError("invalid embedding batch; transaction aborted")
            session.add_all([
                TriageProtocolDocument(
                    citation_id=chunk.citation_id,
                    chunk_id=chunk.chunk_id,
                    protocol_code=chunk.protocol_code,
                    title=chunk.title,
                    issuing_body=chunk.issuing_body,
                    source=chunk.source,
                    source_uri=str(chunk.source_uri),
                    license_reference=chunk.license_reference,
                    version=chunk.version,
                    effective_date=_naive_utc(chunk.effective_date),
                    expires_at=(
                        _naive_utc(chunk.expires_at)
                        if chunk.expires_at is not None
                        else None
                    ),
                    section=chunk.section,
                    document_type="validated_protocol",
                    clinical_scope=list(dict.fromkeys(chunk.clinical_scope)),
                    validation_status="approved",
                    reviewed_by=chunk.reviewed_by,
                    reviewed_at=_naive_utc(chunk.reviewed_at),
                    parser_version=chunk.parser_version,
                    content_hash=content_hash(chunk.page_content),
                    page_content=chunk.page_content.strip(),
                    decision_criteria=list(dict.fromkeys(chunk.decision_criteria)),
                    embedding=vector,
                    keywords=list(dict.fromkeys(chunk.keywords)),
                    embedding_model=model_name,
                    embedding_revision=model_revision,
                    calibration_id=chunk.calibration_id,
                    calibration_profile=chunk.calibration_profile.model_dump(
                        mode="json"
                    ),
                    calibrated_min_score=None,
                )
                for chunk, vector in zip(pending, vectors, strict=True)
            ])
            session.commit()
            inserted += len(pending)
    return inserted, already_present


def main() -> int:
    args = parse_args()
    os.chdir(REPO_ROOT)
    manifest_path = args.manifest_path
    if not manifest_path.is_absolute():
        manifest_path = REPO_ROOT / manifest_path
    manifest = load_manifest(manifest_path)

    print("Validated protocol manifest")
    print(f"  mode: {'APPLY' if args.apply else 'VALIDATE_ONLY'}")
    print(f"  manifest_version: {manifest.manifest_version}")
    print(f"  clinical_owner: {manifest.clinical_owner}")
    print(f"  chunk_count: {len(manifest.chunks)}")
    print(f"  sources: {sorted({chunk.source for chunk in manifest.chunks})}")
    print(
        "  calibration_profiles: "
        f"{sorted({chunk.calibration_id for chunk in manifest.chunks})}"
    )
    print("  inferred_clinical_metadata: none")
    print("  database_mutation: none" if not args.apply else "  database_mutation: requested")
    if not args.apply:
        print("  status: manifest valid; deployment configuration/model not invoked")
        return 0

    inserted, already_present = ingest(manifest, args.batch_size)
    print(f"  inserted_rows: {inserted}")
    print(f"  idempotent_existing_rows: {already_present}")
    print("  status: applied")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(
            f"Protocol ingest aborted: {type(exc).__name__}: {exc}",
            file=sys.stderr,
        )
        raise SystemExit(1) from exc
