"""Offline safety tests for the protocol simulation corpus builder.

These tests do not read PDFs, call OpenAI, create embeddings, or write a DB.
"""

from pydantic import ValidationError

from scripts.build_triage_protocol_simulation import (
    CriterionCheck,
    DecisionCriterion,
    EvidenceSpan,
    ExtractedPage,
    ExtractionEnvelope,
    ProtocolCandidate,
    ReviewPackageRecord,
    VerificationEnvelope,
    VerificationRecord,
    candidate_pages,
    demo_eligibility_reasons,
    deterministic_candidate_errors,
    normalize_verification_decision,
    response_batch_request,
    sanitize_candidate,
)


def _esi_candidate(*, criterion_text: str = "SpO2 < 90%") -> ProtocolCandidate:
    evidence = "High risk vital sign: SpO2 < 90% on room air."
    return ProtocolCandidate(
        source_id="AHRQ_ESI_V4_2012",
        title="High-risk vital signs",
        section="Decision point B",
        page_start=10,
        page_end=10,
        triage_system="ESI_V4",
        populations=["adult"],
        clinical_uses=["ESI_DECISION_SUPPORT"],
        esi_level=2,
        iitt_priority=None,
        summary_original_language=evidence,
        summary_vi="Dấu hiệu sinh tồn nguy cơ cao: SpO2 < 90% khi thở khí phòng.",
        decision_criteria=[DecisionCriterion(
            criterion_original=criterion_text,
            criterion_vi="SpO2 < 90%",
            outcome="ESI 2 candidate",
            evidence_page=10,
            evidence_quote=evidence,
            numeric_thresholds=["<90"],
        )],
        evidence_spans=[EvidenceSpan(page=10, quote=evidence)],
        keywords=["spo2", "high risk"],
        review_flags=[],
    )


def _page() -> ExtractedPage:
    return ExtractedPage(
        page_id="AHRQ_ESI_V4_2012__P0010",
        source_id="AHRQ_ESI_V4_2012",
        source_sha256="a" * 64,
        page_number=10,
        text="High risk vital sign: SpO2 < 90% on room air.",
        extraction_method="pdf_text_layer",
        quality_flags=[],
        requires_visual_review=False,
    )


def _review_record(
    *,
    decision: str = "llm_verified",
    review_status: str = "pending_human_review",
    risk_flags: list[str] | None = None,
) -> ReviewPackageRecord:
    candidate = _esi_candidate()
    verification = VerificationRecord(
        candidate_id="ahrq_esi_v4_2012_1234567890abcdef",
        verification_model="gpt-5-mini",
        verification_prompt_version="triage-protocol-verify-v1",
        decision=decision,
        source_grounding_passed=True,
        triage_system_separation_passed=True,
        criterion_checks=[CriterionCheck(
            criterion_index=0,
            source_supported=True,
            evidence_quote_exact=True,
            numeric_thresholds_preserved=True,
            notes="",
        )],
        issues=[],
    )
    return ReviewPackageRecord(
        candidate_id=verification.candidate_id,
        citation_id=f"SIM:{verification.candidate_id}",
        source_sha256="a" * 64,
        candidate=candidate,
        deterministic_flags=[],
        risk_flags=risk_flags or [],
        llm_verification=verification,
        review_status=review_status,
        simulation_only=True,
    )


def test_non_esi_source_cannot_emit_esi_level() -> None:
    payload = _esi_candidate().model_dump()
    payload.update({
        "source_id": "WHO_IITT_AGE_12_PLUS",
        "triage_system": "WHO_IITT_3_COLOR",
    })

    try:
        ProtocolCandidate.model_validate(payload)
    except ValidationError:
        pass
    else:
        raise AssertionError("WHO IITT candidate was allowed to emit an ESI level")


def test_who_age_scope_is_not_collapsed_to_adult_or_pediatric() -> None:
    payload = _esi_candidate().model_dump()
    payload.update({
        "source_id": "WHO_IITT_AGE_12_PLUS",
        "triage_system": "WHO_IITT_3_COLOR",
        "esi_level": None,
        "iitt_priority": "RED",
        "populations": ["adult"],
        "clinical_uses": ["EMERGENCY_RED_FLAG"],
    })

    candidate = sanitize_candidate(ProtocolCandidate.model_validate(payload))

    assert candidate.populations == ["age_12_plus"]


def test_candidate_pages_include_all_evidence_pages() -> None:
    candidate = _esi_candidate()
    criterion = candidate.decision_criteria[0].model_copy(
        update={"evidence_page": 11}
    )
    candidate = candidate.model_copy(update={"decision_criteria": [criterion]})

    assert candidate_pages(candidate) == {10, 11}


def test_exact_evidence_and_numeric_threshold_pass_validation() -> None:
    candidate = _esi_candidate()
    page = _page()

    errors = deterministic_candidate_errors(
        candidate,
        {(page.source_id, page.page_number): page},
    )

    assert errors == []


def test_numeric_threshold_with_label_and_unit_passes_validation() -> None:
    candidate = _esi_candidate()
    criterion = candidate.decision_criteria[0].model_copy(
        update={"numeric_thresholds": ["SpO2 < 90%"]}
    )
    candidate = candidate.model_copy(update={"decision_criteria": [criterion]})
    page = _page()

    errors = deterministic_candidate_errors(
        candidate,
        {(page.source_id, page.page_number): page},
    )

    assert errors == []


def test_invented_numeric_threshold_is_rejected() -> None:
    candidate = _esi_candidate(criterion_text="SpO2 < 85%")
    page = _page()

    errors = deterministic_candidate_errors(
        candidate,
        {(page.source_id, page.page_number): page},
    )

    assert "criterion_0_number_not_in_evidence" in errors


def test_batch_request_uses_responses_structured_output_without_storage() -> None:
    request = response_batch_request(
        custom_id="extract__test",
        model="gpt-4o-mini",
        system_prompt="extract",
        user_prompt="source",
        output_model=ExtractionEnvelope,
        schema_name="triage_protocol_extraction",
        max_output_tokens=4_000,
    )

    assert request["url"] == "/v1/responses"
    assert request["body"]["store"] is False
    output_format = request["body"]["text"]["format"]
    assert output_format["type"] == "json_schema"
    assert output_format["strict"] is True


def test_verifier_cannot_approve_without_all_criterion_checks() -> None:
    result = VerificationEnvelope(
        candidate_id="ahrq_esi_v4_2012_1234567890abcdef",
        decision="llm_verified",
        source_grounding_passed=True,
        triage_system_separation_passed=True,
        criterion_checks=[],
        issues=[],
    )

    normalized = normalize_verification_decision(result, criterion_count=1)

    assert normalized.decision == "manual_review"


def test_demo_allowlist_requires_all_documentary_gates() -> None:
    record = _review_record()
    page = _page()

    reasons = demo_eligibility_reasons(
        record,
        {(page.source_id, page.page_number): page},
    )

    assert reasons == []


def test_manual_review_remains_outside_demo_allowlist() -> None:
    record = _review_record(
        decision="manual_review",
        review_status="blocked",
    )
    page = _page()

    reasons = demo_eligibility_reasons(
        record,
        {(page.source_id, page.page_number): page},
    )

    assert "verification_manual_review" in reasons
    assert "review_status_blocked" in reasons


def test_visual_review_requirement_blocks_demo_allowlist() -> None:
    record = _review_record(
        risk_flags=["source_page_requires_visual_review"],
    )
    page = _page()

    reasons = demo_eligibility_reasons(
        record,
        {(page.source_id, page.page_number): page},
    )

    assert "source_page_requires_visual_review" in reasons
