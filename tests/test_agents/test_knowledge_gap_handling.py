"""When the knowledge layer cannot support a decision, the system must abstain.

This suite exists because of what the corpus audit found: the production
protocol table ``triage_protocol_documents`` is empty in this environment and
the source whitelist is unset, so *every* authority filter matches nothing.
That is not a hypothetical degraded mode -- it is the current state of the
deployment, which makes "what happens with no evidence" the single most
important behaviour to pin down.

The answer has to be abstention. Not a guess, not a plausible-sounding ESI
derived from the model's own knowledge, and not a silent downgrade to a
lower-authority source that gets presented as though it were a protocol.
"""

from __future__ import annotations

from typing import Any

import pytest

from src.agents.nodes.evidence_gate import (
    build_insufficient_evidence_handoff,
    evaluate_demo_case_support,
    evaluate_evidence,
)


def _protocol_result(**overrides: Any) -> dict[str, Any]:
    """A fully-formed, authority-bearing protocol row."""
    base = {
        "citation_id": "ESI-V5:sec-3",
        "chunk_id": "chunk-3",
        "protocol_code": "ESI-V5",
        "title": "ESI decision point A",
        "issuing_body": "AHRQ",
        "source": "ahrq_esi_v5",
        "source_uri": "https://example.invalid/esi",
        "license_reference": "public-domain",
        "version": "5.0",
        "section": "3",
        "document_type": "validated_protocol",
        "validation_status": "approved",
        "reviewed_by": "clinical-owner",
        "clinical_scope": ["chest_pain", "adult"],
        "similarity_score": 0.82,
        "scope_match": True,
        "matched_protocol_criteria": ["chest pain with diaphoresis"],
        "matched_sparse_terms": ["chest_pain"],
    }
    base.update(overrides)
    return base


# --------------------------------------------------------------------------
# No evidence at all
# --------------------------------------------------------------------------

def test_an_empty_corpus_produces_abstention_not_a_guess() -> None:
    """The current deployment state: nothing retrievable."""
    evaluation = evaluate_evidence([])

    assert evaluation.status == "INSUFFICIENT_EVIDENCE"
    assert evaluation.eligible_for_esi is False
    assert evaluation.citations == []
    assert evaluation.reasons, "abstention must say why"


def test_the_abstention_handoff_carries_no_esi_and_no_citations() -> None:
    handoff = build_insufficient_evidence_handoff("no approved source matched")

    assert handoff["current_esi_level"] is None
    assert handoff["preliminary_esi_reasoning"] is None
    assert handoff["turn_rag_citations"] == []
    assert handoff["decision_status"] == "INSUFFICIENT_EVIDENCE"
    # It terminates the turn rather than falling through to a reasoner.
    assert handoff["next_step"] == "complete"
    assert handoff["response"], "the patient must still be told something"


def test_an_unknown_presentation_does_not_invent_supporting_evidence() -> None:
    """A rare complaint retrieves nothing, and nothing is what it gets."""
    evaluation = evaluate_evidence([])

    assert evaluation.eligible_for_esi is False
    assert evaluation.document_type is None
    assert evaluation.authority_status in {"REJECTED", None}


# --------------------------------------------------------------------------
# Evidence that exists but is not authoritative
# --------------------------------------------------------------------------

@pytest.mark.parametrize(
    "override",
    [
        {"validation_status": "pending"},
        {"validation_status": "draft"},
        {"document_type": "case_example"},
        {"document_type": "blog_post"},
        {"citation_id": ""},
        {"source": ""},
    ],
)
def test_unapproved_or_malformed_evidence_is_refused(override: dict[str, Any]) -> None:
    evaluation = evaluate_evidence([_protocol_result(**override)])

    assert evaluation.eligible_for_esi is False, override
    assert evaluation.status == "INSUFFICIENT_EVIDENCE", override


def test_a_scope_mismatch_is_not_treated_as_support() -> None:
    """A retrieved protocol about the wrong presentation supports nothing."""
    evaluation = evaluate_evidence(
        [_protocol_result(scope_match=False, clinical_scope=["ankle_injury"])]
    )

    assert evaluation.eligible_for_esi is False
    assert evaluation.status == "INSUFFICIENT_EVIDENCE"


# --------------------------------------------------------------------------
# Case examples are never promoted to protocol authority
# --------------------------------------------------------------------------

def test_a_case_example_cannot_pass_the_protocol_gate() -> None:
    """MIETIC rows are demo context. The protocol gate must not accept them."""
    mietic = {
        "citation_id": "MIETIC-DEMO:mietic_00001",
        "case_id": "mietic_00001",
        "source": "MIETIC_v1",
        "document_type": "case_example",
        "validation_status": "demo_only",
        "authority_status": "DEMO_ONLY",
        "case_content": "Symptoms: 64-year-old male with chest pain",
        "similarity_score": 0.91,
    }
    evaluation = evaluate_evidence([mietic])

    assert evaluation.eligible_for_esi is False
    assert evaluation.status == "INSUFFICIENT_EVIDENCE"


def test_demo_support_is_labelled_as_a_case_example_not_a_protocol() -> None:
    """When the demo path does support a decision, it says exactly what it is."""
    mietic = {
        "citation_id": "MIETIC-DEMO:mietic_00001",
        "case_id": "mietic_00001",
        "source": "MIETIC_v1",
        "document_type": "case_example",
        "authority_status": "DEMO_ONLY",
        "case_content": "Symptoms: 64-year-old male with chest pain",
        "metadata_esi_level": 2,
        "similarity_score": 0.91,
    }
    evaluation = evaluate_demo_case_support([mietic])

    assert evaluation.status == "CASE_EXAMPLE_SUPPORT"
    assert evaluation.citations
    assert evaluation.citations[0]["sourceType"] == "case_example"
    # It must never claim protocol authority.
    assert evaluation.document_type != "validated_protocol"


def test_a_forged_authority_label_on_a_mietic_row_is_ignored() -> None:
    """Demo support is granted only to rows that are honestly labelled."""
    forged = {
        "citation_id": "MIETIC-DEMO:mietic_00001",
        "case_id": "mietic_00001",
        "source": "MIETIC_v1",
        "document_type": "validated_protocol",   # lying about itself
        "authority_status": "APPROVED",
        "case_content": "Symptoms: chest pain",
        "metadata_esi_level": 1,
        "similarity_score": 0.99,
    }
    evaluation = evaluate_demo_case_support([forged])

    assert evaluation.status == "INSUFFICIENT_EVIDENCE"
    assert evaluation.eligible_for_esi is False


# --------------------------------------------------------------------------
# Open clinical questions block a conclusion regardless of evidence
# --------------------------------------------------------------------------

def test_unresolved_contradictions_block_esi_even_with_good_support() -> None:
    mietic = {
        "citation_id": "MIETIC-DEMO:mietic_00001",
        "case_id": "mietic_00001",
        "source": "MIETIC_v1",
        "document_type": "case_example",
        "authority_status": "DEMO_ONLY",
        "case_content": "Symptoms: chest pain",
        "metadata_esi_level": 2,
        "similarity_score": 0.95,
    }
    evaluation = evaluate_demo_case_support(
        [mietic],
        unresolved_contradictions=[{"key": "symptom.chest_pain"}],
    )

    assert evaluation.eligible_for_esi is False
    assert evaluation.status == "INSUFFICIENT_EVIDENCE"


def test_missing_critical_fields_block_esi_even_with_good_support() -> None:
    mietic = {
        "citation_id": "MIETIC-DEMO:mietic_00001",
        "case_id": "mietic_00001",
        "source": "MIETIC_v1",
        "document_type": "case_example",
        "authority_status": "DEMO_ONLY",
        "case_content": "Symptoms: chest pain",
        "metadata_esi_level": 2,
        "similarity_score": 0.95,
    }
    evaluation = evaluate_demo_case_support(
        [mietic],
        missing_critical_fields=["severity_score"],
    )

    assert evaluation.eligible_for_esi is False
    assert evaluation.status == "INSUFFICIENT_EVIDENCE"
