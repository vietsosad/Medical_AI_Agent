"""What may become authoritative protocol evidence, and what may never.

The protocol table is empty, so these tests do not exercise a corpus -- they
exercise the boundary that decides what would be allowed into one. That
boundary is the only thing standing between "we have no protocol data" and the
much worse "we have data that claims to be protocol data and is not".

Three separate things get confused if the boundary is loose: the AHRQ ESI
source text (real, but not yet clinically reviewed in this repo), the MIETIC
case corpus (real cases, demo authority only), and synthetic fixtures (useful
for tests, never clinical). Each has a different standing, and the gate has to
keep them apart without anyone having to remember to.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from src.agents.nodes.evidence_gate import evaluate_demo_case_support, evaluate_evidence

REPO_ROOT = Path(__file__).resolve().parents[2]
DRAFT_MANIFEST = REPO_ROOT / "data" / "protocols" / "ahrq_esi_v5.draft-manifest.json"


def _manifest_payload() -> dict[str, Any]:
    """The draft manifest, rebuilt from the tracked source if it is absent.

    The generated file is version-controlled, but a fresh checkout that has not
    run the builder must still exercise these guarantees. Rebuilding is exact --
    the builder is a pure function of a tracked source file -- so this never
    skips and never tests something different from what ships.
    """
    if DRAFT_MANIFEST.exists():
        return json.loads(DRAFT_MANIFEST.read_text(encoding="utf-8"))

    from scripts.build_protocol_manifest import (
        MANIFEST_VERSION,
        REQUIRES_HUMAN,
        SOURCE_FILE,
        build_chunk,
        gap_report,
        parse_sections,
    )

    sections = parse_sections(SOURCE_FILE.read_text(encoding="utf-8"))
    chunks = [build_chunk(section, i) for i, section in enumerate(sections, start=1)]
    return {
        "manifest_version": MANIFEST_VERSION,
        "clinical_owner": REQUIRES_HUMAN,
        "export_approved_at": REQUIRES_HUMAN,
        "_draft_status": "NOT_READY_FOR_INGESTION",
        "_blocking_fields": {k: len(v) for k, v in gap_report(chunks).items()},
        "chunks": chunks,
    }


def approved_protocol(**overrides: Any) -> dict[str, Any]:
    """A row carrying every credential the gate requires.

    Written out in full deliberately: the list of fields *is* the contract, and
    a test that built it from a helper would hide which credential each
    negative case is actually removing.
    """
    row = {
        "citation_id": "AHRQ-ESI-V5:decision_point_b",
        "chunk_id": "ahrq_esi_v5-002",
        "protocol_code": "AHRQ-ESI-V5",
        "title": "Decision Point B: high-risk situation",
        "issuing_body": "Agency for Healthcare Research and Quality",
        "source": "ahrq_esi_v5",
        "source_uri": "https://example.invalid/ahrq-esi-v5",
        "license_reference": "US public domain",
        "version": "5",
        "effective_date": "2023-11-01T00:00:00+00:00",
        "section": "decision_point_b",
        "document_type": "validated_protocol",
        "validation_status": "approved",
        "authority_status": "AUTHORIZED",
        "reviewed_by": "clinical-owner",
        "reviewed_at": "2026-01-01T00:00:00+00:00",
        "parser_version": "ahrq-esi-md-parser-1.0.0",
        "content_hash": "a" * 64,
        "clinical_scope": ["chest_pain", "adult"],
        "scope_match": True,
        "matched_protocol_criteria": ["High-risk situation ➔ ESI 2"],
        "similarity_score": 0.83,
        "protocol_content": (
            "Decision Point B: high-risk situation, or confused/lethargic/"
            "disoriented, or severe pain or distress ➔ ESI 2."
        ),
        # Calibration is part of the credential set, not an optimisation: an
        # uncalibrated similarity score is a number without a meaning.
        "symptom_cluster": "chest_pain",
        "population": "adult",
        "calibration_id": "cal-chest-pain-adult-001",
        "calibration_profile": {
            "symptom_cluster": "chest_pain",
            "population": "adult",
            "thresholds": {"vi_dense": 0.55, "en_dense": 0.55},
            "min_passing_dense_channels": 1,
            "approved_by": "clinical-owner",
            "approved_at": "2026-01-01T00:00:00+00:00",
        },
        "retrieval_channels": [
            {"channel": "vi_dense", "score": 0.81},
            {"channel": "en_dense", "score": 0.78},
        ],
    }
    row.update(overrides)
    return row


def mietic_case(**overrides: Any) -> dict[str, Any]:
    row = {
        "citation_id": "MIETIC-DEMO:mietic_00001",
        "case_id": "mietic_00001",
        "source": "MIETIC_v1",
        "document_type": "case_example",
        "validation_status": "demo_only",
        "authority_status": "DEMO_ONLY",
        "case_content": "Symptoms: 64-year-old male with chest pain",
        "metadata_esi_level": 2,
        "similarity_score": 0.91,
    }
    row.update(overrides)
    return row


# --------------------------------------------------------------------------
# A properly credentialed protocol is accepted
# --------------------------------------------------------------------------

def test_a_fully_credentialed_protocol_passes_the_evidence_gate() -> None:
    """The positive case. Without it, the negatives prove only that nothing passes."""
    evaluation = evaluate_evidence([approved_protocol()])

    assert evaluation.status == "SUFFICIENT"
    assert evaluation.eligible_for_esi is True
    assert evaluation.document_type == "validated_protocol"
    assert evaluation.authority_status == "AUTHORIZED"
    assert evaluation.citations


# --------------------------------------------------------------------------
# Each credential is individually load-bearing
# --------------------------------------------------------------------------

@pytest.mark.parametrize(
    ("field_name", "bad_value"),
    [
        ("document_type", "case_example"),
        ("validation_status", "pending"),
        ("authority_status", "DEMO_ONLY"),
        ("scope_match", False),
        ("matched_protocol_criteria", []),
        ("source_uri", ""),
        ("license_reference", ""),
        ("reviewed_by", ""),
        ("reviewed_at", ""),
        ("content_hash", ""),
        ("version", ""),
        ("effective_date", ""),
        ("parser_version", ""),
        ("issuing_body", ""),
        ("protocol_code", ""),
    ],
)
def test_removing_any_single_credential_refuses_the_document(
    field_name: str, bad_value: Any
) -> None:
    evaluation = evaluate_evidence([approved_protocol(**{field_name: bad_value})])

    assert evaluation.eligible_for_esi is False, field_name
    assert evaluation.status == "INSUFFICIENT_EVIDENCE", field_name


# --------------------------------------------------------------------------
# MIETIC quarantine
# --------------------------------------------------------------------------

def test_a_mietic_case_cannot_pass_the_protocol_gate() -> None:
    evaluation = evaluate_evidence([mietic_case()])

    assert evaluation.eligible_for_esi is False
    assert evaluation.status == "INSUFFICIENT_EVIDENCE"


def test_mietic_cannot_be_promoted_by_relabelling_itself() -> None:
    """Source is checked before type, so a forged label changes nothing."""
    forged = mietic_case(
        document_type="validated_protocol",
        validation_status="approved",
        authority_status="AUTHORIZED",
    )
    evaluation = evaluate_evidence([forged])

    assert evaluation.eligible_for_esi is False


def test_mietic_support_is_labelled_demo_and_never_protocol() -> None:
    evaluation = evaluate_demo_case_support([mietic_case()])

    assert evaluation.status == "CASE_EXAMPLE_SUPPORT"
    assert evaluation.document_type != "validated_protocol"
    assert evaluation.citations[0]["sourceType"] == "case_example"


def test_a_protocol_row_does_not_become_demo_case_support() -> None:
    """The two channels are separate in both directions."""
    evaluation = evaluate_demo_case_support([approved_protocol()])

    assert evaluation.status == "INSUFFICIENT_EVIDENCE"


# --------------------------------------------------------------------------
# Synthetic data is for tests, never for clinical authority
# --------------------------------------------------------------------------

def test_a_synthetic_source_cannot_be_authorised_as_protocol() -> None:
    """Synthetic fixtures must not reach the gate wearing real credentials."""
    synthetic = approved_protocol(
        source="SYNTHETIC",
        authority_status="DEMO_ONLY",
    )
    evaluation = evaluate_evidence([synthetic])

    assert evaluation.eligible_for_esi is False


# --------------------------------------------------------------------------
# Scope
# --------------------------------------------------------------------------

@pytest.mark.parametrize(
    "scope_match", [False, None],
)
def test_a_scope_mismatch_or_missing_scope_is_refused(scope_match: Any) -> None:
    """Embedding similarity is not scope. A near neighbour is not applicable."""
    evaluation = evaluate_evidence(
        [approved_protocol(scope_match=scope_match, similarity_score=0.99)]
    )

    assert evaluation.eligible_for_esi is False


def test_a_high_similarity_unrelated_protocol_does_not_become_evidence() -> None:
    """An ankle protocol retrieved for chest pain supports nothing."""
    evaluation = evaluate_evidence(
        [
            approved_protocol(
                citation_id="AHRQ-ESI-V5:ankle",
                clinical_scope=["ankle_injury", "adult"],
                scope_match=False,
                similarity_score=0.97,
            )
        ]
    )

    assert evaluation.eligible_for_esi is False
    assert evaluation.status == "INSUFFICIENT_EVIDENCE"


# --------------------------------------------------------------------------
# Versions
# --------------------------------------------------------------------------

def test_two_versions_of_one_protocol_are_both_surfaced_not_merged() -> None:
    """Conflicting versions must stay visible rather than being silently blended.

    The gate does not currently pick a winner between two live versions of the
    same protocol_code -- it cites both. That is the safe direction (a nurse
    sees the conflict) but it is not version resolution, and this test pins the
    actual behaviour rather than the behaviour one might assume.
    """
    v4 = approved_protocol(
        citation_id="AHRQ-ESI-V4:decision_point_b", version="4"
    )
    v5 = approved_protocol(version="5")

    evaluation = evaluate_evidence([v4, v5])

    assert evaluation.eligible_for_esi is True
    versions = {citation["id"] for citation in evaluation.citations}
    assert len(versions) == 2, "both versions must remain visible"


def test_the_retrieval_path_no_longer_enforces_document_expiry() -> None:
    """Expiry enforcement disappeared together with the legacy protocol corpus.

    ``ClinicalHybridRetriever`` filtered ``effective_date``, ``expires_at`` and
    ``validation_status`` inside the query itself, so an expired protocol could
    not reach the gate.  The Pass-5 corpus that replaced it carries none of
    those columns, and ``KnowledgeRetriever`` filters on ``retrieval_scope``
    alone.

    This pins the loss rather than deleting the question: an expired AHRQ
    revision now has nothing stopping it at the retrieval layer.  Restoring the
    guarantee means putting the metadata back onto the corpus first, at which
    point this test should assert the filter again instead of its absence.
    """
    from src.models.db_models import ESIKnowledgeDocument
    from src.services.rag.knowledge_retriever import KnowledgeRetriever

    columns = set(ESIKnowledgeDocument.model_fields)
    assert not (columns & {"effective_date", "expires_at", "validation_status"})
    assert not hasattr(KnowledgeRetriever, "_authority_filters")


# --------------------------------------------------------------------------
# The draft manifest is a draft, and the gate says so
# --------------------------------------------------------------------------

def test_the_draft_manifest_is_not_ingestible() -> None:
    """The AHRQ draft must fail validation until a clinician signs it off."""
    from scripts.ingest_validated_protocols import ProtocolManifest

    payload = _manifest_payload()

    assert payload["_draft_status"] == "NOT_READY_FOR_INGESTION"
    with pytest.raises(Exception):
        ProtocolManifest.model_validate(payload)


def test_the_draft_manifest_never_claims_approval() -> None:
    payload = _manifest_payload()

    for chunk in payload["chunks"]:
        assert chunk["validation_status"] != "approved"
        assert chunk["reviewed_by"] == "REQUIRES_CLINICAL_OWNER"
        assert chunk["calibration_profile"] == "REQUIRES_CLINICAL_OWNER"


def test_the_draft_chunks_carry_real_derived_content() -> None:
    """The half that could be done honestly must actually have been done."""
    payload = _manifest_payload()
    chunks = payload["chunks"]

    assert len(chunks) >= 5
    hashes = [chunk["content_hash"] for chunk in chunks]
    assert len(hashes) == len(set(hashes)), "no duplicate chunks"
    for chunk in chunks:
        assert len(chunk["page_content"]) >= 80
        assert chunk["keywords"]
        assert chunk["clinical_scope"]
        assert chunk["protocol_code"] == "AHRQ-ESI-V5"
