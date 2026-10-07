import asyncio
from datetime import datetime

import pytest
from fastapi import HTTPException
from pydantic import ValidationError

from src.api.dependencies import get_current_nurse, get_current_patient
from src.api.routes_auth import _build_user_profile_dto
from src.api.routes_nurse import (
    _assert_assignee,
    _assert_version,
    _citation_dtos,
    _missing_fields,
    _review_status,
)
from src.models.db_models import NurseReviewState, TriageCase, User
from src.models.nurse_schemas import (
    ClinicalObservationInputDTO,
    HandoffCaseRequestDTO,
    NurseQueueSummaryDTO,
    UpdateIntakeRequestDTO,
)


def test_measured_observation_requires_value_unit_and_timestamp():
    with pytest.raises(ValueError):
        ClinicalObservationInputDTO(
            kind="HEART_RATE",
            value="88",
            unit=None,
            availability="MEASURED",
            source="NURSE_MEASURED",
            measured_at=None,
        )

    valid = ClinicalObservationInputDTO(
        kind="HEART_RATE",
        value="88",
        unit="lần/phút",
        availability="MEASURED",
        source="NURSE_MEASURED",
        measured_at=datetime(2026, 8, 12, 10, 30),
    )
    assert valid.source == "NURSE_MEASURED"


def test_case_completeness_never_invents_missing_esi_or_citation():
    incomplete = TriageCase(
        id="case-1",
        patient_id="patient-1",
        session_title="Đau ngực",
        status="HITL_REVIEWING",
    )
    assert _missing_fields(incomplete) == ["Đề xuất ESI của AI", "Nguồn tham chiếu phân luồng"]

    red_flag = TriageCase(
        id="case-2",
        patient_id="patient-1",
        session_title="Khó thở dữ dội",
        status="RED_FLAG_LOCKED",
        ai_proposed_esi=1,
        is_red_flag_triggered=True,
    )
    assert _missing_fields(red_flag) == []


def test_nurse_citations_preserve_saved_source_provenance_without_guessing_urls():
    case = TriageCase(
        id="case-with-source",
        patient_id="patient-1",
        session_title="Đau đầu",
        status="HITL_REVIEWING",
        rag_citations=["p5doc_d63c62370ba3c9b87de2", "legacy-code"],
        rag_citation_details=[
            {
                "id": "p5doc_d63c62370ba3c9b87de2",
                "protocolId": "p5doc_d63c62370ba3c9b87de2",
                "title": "Is the Patient in Severe Pain or Distress?",
                "excerpt": "Retrieved ESI passage",
                "sourceUri": "https://example.org/esi.pdf",
                "section": "Decision Point B",
                "version": "v5",
                "contentHash": "hash-1",
                "sourceType": "validated_protocol",
            }
        ],
    )

    citations = _citation_dtos(case)

    assert citations[0].source_uri == "https://example.org/esi.pdf"
    assert citations[0].excerpt == "Retrieved ESI passage"
    assert citations[1].code == "legacy-code"
    assert citations[1].source_uri is None


def test_version_and_assignment_guards_reject_stale_or_foreign_updates():
    nurse = User(id="nurse-1", full_name="Điều dưỡng Một", role="CLINICAL_NURSE")
    review = NurseReviewState(
        triage_case_id="case-1",
        assigned_nurse_id="nurse-2",
        review_status="IN_REVIEW",
        version=4,
    )

    with pytest.raises(HTTPException) as stale_error:
        _assert_version(review, 3)
    assert stale_error.value.status_code == 409

    with pytest.raises(HTTPException) as owner_error:
        _assert_assignee(review, nurse)
    assert owner_error.value.status_code == 409


def test_unified_clinical_role_accepts_legacy_doctor_and_nurse():
    doctor = User(id="doctor-1", full_name="Bác sĩ Một", role="DOCTOR")
    nurse = User(id="nurse-1", full_name="Điều dưỡng Một", role="CLINICAL_NURSE")

    assert asyncio.run(get_current_nurse(doctor)) is doctor
    assert asyncio.run(get_current_nurse(nurse)) is nurse
    assert _build_user_profile_dto(doctor).role == "CLINICAL_NURSE"


def test_legacy_doctor_review_status_is_normalized_for_the_unified_queue():
    review = NurseReviewState(
        triage_case_id="case-legacy",
        review_status="ESCALATED_TO_DOCTOR",
    )

    assert _review_status(review) == "SPECIALIST_REVIEW_REQUIRED"


def test_unified_queue_exposes_specialist_review_count():
    summary = NurseQueueSummaryDTO(
        total_waiting=7,
        urgent_count=2,
        mine_count=1,
        specialist_count=3,
        longest_wait_seconds=900,
    )

    assert summary.specialist_count == 3


def test_intake_update_strips_and_validates_chief_complaint():
    payload = UpdateIntakeRequestDTO(
        case_version=2,
        chief_complaint="  Đau ngực khi gắng sức  ",
    )

    assert payload.chief_complaint == "Đau ngực khi gắng sức"

    with pytest.raises(ValidationError):
        UpdateIntakeRequestDTO(case_version=2, chief_complaint=" ")


def test_handoff_no_longer_has_a_separate_doctor_destination():
    with pytest.raises(ValidationError):
        HandoffCaseRequestDTO(
            case_version=1,
            destination="DOCTOR_REVIEW",
            note="Bàn giao sang vai trò đã được hợp nhất.",
        )


def test_patient_api_role_boundary_rejects_nurse():
    nurse = User(id="nurse-1", full_name="Điều dưỡng Một", role="CLINICAL_NURSE")
    with pytest.raises(HTTPException) as role_error:
        asyncio.run(get_current_patient(nurse))
    assert role_error.value.status_code == 403

    patient = User(id="patient-1", full_name="Bệnh nhân Một", role="PATIENT")
    assert asyncio.run(get_current_patient(patient)) is patient
