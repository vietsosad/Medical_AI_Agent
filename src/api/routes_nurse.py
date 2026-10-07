"""Nurse Triage API: priority queue, HITL review, audit and handoff.

The router deliberately excludes diagnosis, prescribing, EMS operations and
hospital bed management. Every mutation is nurse-only and version checked.
"""

import uuid
from datetime import datetime, timedelta
from typing import Annotated, Any

from fastapi import APIRouter, HTTPException, Path, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from src.agents.guardrails import filter_output_diagnosis
from src.api.dependencies import NurseUserDep, SessionDep
from src.models.db_models import (
    AuditLog,
    ChatMessage,
    ClinicalObservation,
    EHRProfile,
    NurseReviewState,
    TriageCase,
    User,
    get_utc_now,
)
from src.models.nurse_schemas import (
    AcknowledgeAlertRequestDTO,
    CaseMessagesResponseDTO,
    CitationDTO,
    InboxItemDTO,
    InboxResponseDTO,
    ClaimCaseRequestDTO,
    ClinicalObservationDTO,
    ClinicalTranscriptMessageDTO,
    DataCompletenessDTO,
    EmergencyContactPersonDTO,
    EmergencyContactResponseDTO,
    EscalateCaseRequestDTO,
    HandoffCaseRequestDTO,
    NurseActionResponseDTO,
    NurseCaseDetailDTO,
    NurseIdentityDTO,
    NurseQueueItemDTO,
    NurseQueueResponseDTO,
    NurseQueueSummaryDTO,
    PiiAccessRequestDTO,
    PiiAccessResponseDTO,
    RiskContextDTO,
    SbarSummaryDTO,
    SendCaseMessageRequestDTO,
    SpecialistReviewContextDTO,
    TriageDecisionRequestDTO,
    UpdateIntakeRequestDTO,
    UpdateObservationsRequestDTO,
)

from src.services.event_bus import (
    EVENT_CASE_CLAIMED,
    EVENT_CASE_ESCALATED,
    EVENT_CASE_RELEASED,
    EVENT_MESSAGE_CREATED,
    EVENT_MESSAGE_READ,
    STAFF_QUEUE_TOPIC,
    case_topic,
    get_event_bus,
    patient_topic,
)
from src.services.clinical_text import normalize_clinical_display_text

router = APIRouter(prefix="/nurse", tags=["Nurse Triage and HITL"])

# Các loại tin thuộc về hội thoại lâm sàng mà nhân viên được đọc.
TRANSCRIPT_SENDER_TYPES = frozenset({"PATIENT", "AI_AGENT", "SYSTEM_SHIELD", "NURSE"})

# Kênh trao đổi trực tiếp giữa người bệnh và nhân viên y tế, tách khỏi phần hỏi
# bệnh của AI. Nhân viên vẫn đọc cả hai để có đủ bối cảnh lâm sàng.
CARE_TEAM_CHANNEL = "CARE_TEAM"

# Độ dài trích ngắn hiển thị ở hộp thư. Đủ để nhận ra việc cần làm, không đủ để
# thành một bản sao hồ sơ lâm sàng nằm ngoài lớp kiểm quyền.
INBOX_PREVIEW_LENGTH = 120


def _message_priority(case: TriageCase) -> str:
    """Mức ưu tiên hiển thị của một ca; không phải kết luận lâm sàng mới."""
    if case.is_red_flag_triggered or case.status == "RED_FLAG_LOCKED":
        return "RED_FLAG"
    if case.ai_proposed_esi in {1, 2}:
        return "URGENT"
    return "NORMAL"


def _citation_dtos(case: TriageCase) -> list[CitationDTO]:
    """Join stable citation codes with the provenance saved for the proposal.

    Legacy cases only stored ``rag_citations``. Those codes remain visible but
    deliberately do not acquire guessed titles, excerpts, or source URLs.
    """
    raw_details = case.rag_citation_details or []
    details_by_code = {
        str(detail.get("protocolId") or detail.get("id")): detail
        for detail in raw_details
        if isinstance(detail, dict)
        and detail.get("sourceType") in {None, "validated_protocol"}
        and (detail.get("protocolId") or detail.get("id"))
    }
    citations: list[CitationDTO] = []
    for raw_code in case.rag_citations or []:
        code = str(raw_code).strip()
        if not code:
            continue
        detail = details_by_code.get(code, {})
        citations.append(
            CitationDTO(
                code=code,
                title=str(detail["title"]) if detail.get("title") else None,
                excerpt=str(detail["excerpt"]) if detail.get("excerpt") else None,
                source_uri=str(detail["sourceUri"]) if detail.get("sourceUri") else None,
                section=str(detail["section"]) if detail.get("section") else None,
                version=str(detail["version"]) if detail.get("version") else None,
                content_hash=(str(detail["contentHash"]) if detail.get("contentHash") else None),
            )
        )
    return citations


async def _claim_for_reply(
    session: AsyncSession,
    case: TriageCase,
    review: NurseReviewState,
    nurse: User,
) -> bool:
    """Trả lời người bệnh là đã nhận trách nhiệm với ca đó.

    Nhận ca ngầm khi ca chưa có ai phụ trách, đi đúng đường khoá hàng và ghi
    kiểm toán như thao tác nhận ca thủ công. Ca đã có người khác giữ thì từ chối:
    hai nhân viên cùng tưởng mình độc quyền một ca là tình huống phải chặn.
    """
    if review.assigned_nurse_id == nurse.id:
        return False
    if review.assigned_nurse_id:
        assignee = await _identity(session, review.assigned_nurse_id)
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Ca đang do {assignee.name if assignee else 'nhân viên khác'} phụ trách.",
        )

    before = {
        "assignee": None,
        "review_status": _review_status(review),
        "version": review.version,
    }
    review.assigned_nurse_id = nurse.id
    review.review_status = "IN_REVIEW"
    review.claimed_at = review.claimed_at or get_utc_now()
    review.version += 1
    review.updated_at = get_utc_now()
    case.assigned_nurse_id = nurse.id
    _audit(
        session,
        event_type="NURSE_CASE_CLAIMED",
        case_id=case.id,
        nurse=nurse,
        before=before,
        after={
            "assignee": nurse.id,
            "review_status": review.review_status,
            "version": review.version,
            "trigger": "REPLY_TO_PATIENT",
        },
    )
    return True


ACTIVE_TRIAGE_STATUSES = ("HITL_REVIEWING", "RED_FLAG_LOCKED")

# Hàng đợi chỉ nhận ca đã được AI bàn giao, nhưng hộp thư thì không: người bệnh
# nhắn cho trạm trực ngay trong lúc còn đang hỏi bệnh với AI, và tin đó phải tới
# nơi. Chỉ ca đã đóng sổ mới nằm ngoài hộp thư.
INBOX_TRIAGE_STATUSES = ("IN_PROGRESS", "HITL_REVIEWING", "RED_FLAG_LOCKED")
TERMINAL_REVIEW_STATUSES = ("HANDED_OFF",)
LEGACY_SPECIALIST_REVIEW_STATUS = "ESCALATED_TO_DOCTOR"
SPECIALIST_REVIEW_STATUS = "SPECIALIST_REVIEW_REQUIRED"


def _mask_name(real_name: str) -> str:
    parts = [part for part in real_name.split() if part]
    if not parts:
        return "Bệnh nhân ẩn danh"
    return " ".join(f"{part[0]}{'*' * max(1, len(part) - 1)}" for part in parts)


def _profile_bmi(profile: EHRProfile | None) -> float | None:
    if profile is None or not profile.height_cm or not profile.weight_kg:
        return None
    height_m = profile.height_cm / 100
    return round(profile.weight_kg / (height_m * height_m), 1)


def _missing_fields(case: TriageCase) -> list[str]:
    missing: list[str] = []
    if case.ai_proposed_esi not in {1, 2, 3, 4, 5}:
        missing.append("Đề xuất ESI của AI")
    if not case.session_title or case.session_title == "Triage Consultation":
        missing.append("Triệu chứng chính")
    if not case.is_red_flag_triggered and not case.rag_citations:
        missing.append("Nguồn tham chiếu phân luồng")
    return missing


def _review_status(state: NurseReviewState) -> str:
    if state.review_status == LEGACY_SPECIALIST_REVIEW_STATUS:
        return SPECIALIST_REVIEW_STATUS
    if state.review_status == "WAITING_REVIEW" and state.assigned_nurse_id:
        return "ASSIGNED"
    return state.review_status


async def _get_case(
    session: AsyncSession,
    case_id: str,
    *,
    lock: bool = False,
) -> TriageCase:
    statement = select(TriageCase).where(TriageCase.id == case_id)
    if lock:
        statement = statement.with_for_update()
    result = await session.execute(statement)
    case = result.scalars().first()
    if case is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Không tìm thấy ca phân luồng.")
    return case


async def _get_review_state(
    session: AsyncSession,
    case_id: str,
    *,
    lock: bool = False,
) -> NurseReviewState:
    statement = select(NurseReviewState).where(NurseReviewState.triage_case_id == case_id)
    if lock:
        statement = statement.with_for_update()
    result = await session.execute(statement)
    review = result.scalars().first()
    if review is None:
        review = NurseReviewState(triage_case_id=case_id)
        session.add(review)
        await session.flush()
    return review


def _assert_version(review: NurseReviewState, expected: int) -> None:
    if review.version != expected:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "code": "CASE_VERSION_CONFLICT",
                "message": "Ca đã được cập nhật bởi người khác. Vui lòng tải lại dữ liệu.",
                "current_version": review.version,
            },
        )


def _assert_assignee(review: NurseReviewState, nurse: User) -> None:
    if review.assigned_nurse_id != nurse.id:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Bạn phải nhận ca này trước khi thay đổi dữ liệu hoặc ra quyết định.",
        )


def _audit(
    session: AsyncSession,
    *,
    event_type: str,
    case_id: str,
    nurse: User,
    before: dict[str, Any] | None,
    after: dict[str, Any] | None,
    note: str | None = None,
) -> None:
    session.add(
        AuditLog(
            id=str(uuid.uuid4()),
            event_type=event_type,
            triage_case_id=case_id,
            actor_id=nurse.id,
            actor_role=nurse.role,
            before_state=before,
            after_state=after,
            clinical_justification=note,
        )
    )


async def _identity(session: AsyncSession, user_id: str | None) -> NurseIdentityDTO | None:
    if user_id is None:
        return None
    result = await session.execute(select(User).where(User.id == user_id))
    user = result.scalars().first()
    if user is None:
        return NurseIdentityDTO(id=user_id, name="Nhân viên không còn hoạt động")
    return NurseIdentityDTO(id=user.id, name=user.full_name)


async def _patient_context(
    session: AsyncSession,
    case: TriageCase,
) -> tuple[User | None, EHRProfile | None]:
    user_result = await session.execute(select(User).where(User.id == case.patient_id))
    patient = user_result.scalars().first()
    profile: EHRProfile | None = None
    if case.profile_id:
        profile_result = await session.execute(
            select(EHRProfile).where(
                EHRProfile.id == case.profile_id,
                EHRProfile.user_id == case.patient_id,
            )
        )
        profile = profile_result.scalars().first()
    return patient, profile


async def _conversation_stats(
    session: AsyncSession,
    case_id: str,
) -> tuple[int, datetime | None]:
    """Số tin bệnh nhân gửi mà phía lâm sàng chưa đọc, và mốc tin gần nhất."""
    result = await session.execute(
        select(ChatMessage).where(ChatMessage.triage_case_id == case_id).order_by(ChatMessage.created_at.asc())
    )
    messages = list(result.scalars().all())
    unread = sum(1 for message in messages if message.sender_type == "PATIENT" and message.read_at is None)
    last_at = messages[-1].created_at if messages else None
    return unread, last_at


def _transcript_dto(message: ChatMessage) -> ClinicalTranscriptMessageDTO:
    """Chuyển một dòng tin sang DTO, giữ nguyên nhãn tác giả.

    Chỉ nội dung do máy sinh mới đi qua bộ lọc chống khẳng định chẩn đoán. Lời
    của bệnh nhân và của nhân viên lâm sàng là phát ngôn của con người: sửa lại
    chúng sẽ làm sai lệch hồ sơ giao tiếp y tế.
    """
    machine_authored = message.sender_type in {"AI_AGENT", "SYSTEM_SHIELD"}
    return ClinicalTranscriptMessageDTO(
        id=message.id,
        sender=message.sender_type,
        content=(filter_output_diagnosis(message.content) if machine_authored else message.content),
        created_at=message.created_at,
        sender_name=message.sender_display_name,
        read_at=message.read_at,
    )


async def _publish(topic: str, event: str, payload: dict[str, Any]) -> None:
    """Đánh thức giao diện. Trạng thái đã commit mới là nguồn sự thật."""
    try:
        await get_event_bus().publish(topic, event, payload)
    except Exception:  # noqa: BLE001 - realtime hỏng không được làm hỏng ca bệnh
        pass


async def _queue_item(
    session: AsyncSession,
    case: TriageCase,
    review: NurseReviewState,
) -> NurseQueueItemDTO:
    patient, profile = await _patient_context(session, case)
    unread_count, last_message_at = await _conversation_stats(session, case.id)
    display_name = profile.full_name if profile else patient.full_name if patient else "Bệnh nhân ẩn danh"
    missing = _missing_fields(case)
    wait_seconds = max(0, int((get_utc_now() - case.created_at).total_seconds()))
    red_flags = [case.red_flag_trigger_keyword] if case.red_flag_trigger_keyword else []
    displayed_status = _review_status(review)
    if missing and displayed_status not in {
        *TERMINAL_REVIEW_STATUSES,
        "TRIAGE_DECIDED",
        SPECIALIST_REVIEW_STATUS,
    }:
        displayed_status = "NEEDS_MORE_INFO"
    return NurseQueueItemDTO(
        case_id=case.id,
        patient_name=display_name,
        masked_patient_label=_mask_name(display_name),
        age=profile.age if profile else None,
        sex=profile.gender if profile else None,
        chief_complaint=("" if case.session_title == "Triage Consultation" else case.session_title),
        ai_recommended_esi=case.ai_proposed_esi if case.ai_proposed_esi in {1, 2, 3, 4, 5} else None,
        red_flags=red_flags,
        is_red_flag=case.is_red_flag_triggered,
        red_flag_status=case.red_flag_status,
        red_flag_detection_source=case.red_flag_detection_source,
        red_flag_resolution_reason=case.red_flag_resolution_reason,
        waiting_since=case.created_at,
        wait_time_seconds=wait_seconds,
        review_status=displayed_status,
        assignee=await _identity(session, review.assigned_nurse_id),
        data_completeness=DataCompletenessDTO(is_complete=not missing, missing_fields=missing),
        case_version=review.version,
        alert_acknowledged=review.alert_acknowledged_at is not None,
        unread_count=unread_count,
        last_message_at=last_message_at,
    )


@router.get("/queue", response_model=NurseQueueResponseDTO)
async def get_nurse_queue(
    nurse: NurseUserDep,
    session: SessionDep,
    mine_only: Annotated[bool, Query(description="Chỉ lấy ca do nhân viên hiện tại phụ trách")] = False,
    urgent_only: Annotated[bool, Query(description="Chỉ lấy Red Flag hoặc ESI 1-2")] = False,
    needs_info_only: Annotated[bool, Query(description="Chỉ lấy ca thiếu dữ liệu nền tảng")] = False,
    specialist_only: Annotated[
        bool,
        Query(description="Chỉ lấy ca đang chờ đánh giá chuyên sâu"),
    ] = False,
) -> NurseQueueResponseDTO:
    """Return a fail-closed, clinically prioritized queue."""
    result = await session.execute(
        select(TriageCase).where(TriageCase.status.in_(ACTIVE_TRIAGE_STATUSES)).order_by(TriageCase.created_at.asc())
    )
    cases = list(result.scalars().all())
    all_items: list[NurseQueueItemDTO] = []
    for case in cases:
        review = await _get_review_state(session, case.id)
        if _review_status(review) in TERMINAL_REVIEW_STATUSES:
            continue
        item = await _queue_item(session, case, review)
        all_items.append(item)

    items = [
        item
        for item in all_items
        if (not mine_only or (item.assignee is not None and item.assignee.id == nurse.id))
        and (not urgent_only or item.is_red_flag or item.ai_recommended_esi in {1, 2})
        and (not needs_info_only or not item.data_completeness.is_complete)
        and (not specialist_only or item.review_status == SPECIALIST_REVIEW_STATUS)
    ]

    items.sort(
        key=lambda item: (
            0 if item.is_red_flag else 1,
            item.ai_recommended_esi if item.ai_recommended_esi is not None else 6,
            item.waiting_since,
        )
    )
    await session.commit()
    return NurseQueueResponseDTO(
        items=items,
        summary=NurseQueueSummaryDTO(
            total_waiting=len(all_items),
            urgent_count=sum(1 for item in all_items if item.is_red_flag or item.ai_recommended_esi in {1, 2}),
            mine_count=sum(1 for item in all_items if item.assignee and item.assignee.id == nurse.id),
            specialist_count=sum(1 for item in all_items if item.review_status == SPECIALIST_REVIEW_STATUS),
            longest_wait_seconds=max(
                (item.wait_time_seconds for item in all_items),
                default=0,
            ),
        ),
        sla_target_minutes=None,
    )


@router.get("/cases/{case_id}", response_model=NurseCaseDetailDTO)
async def get_nurse_case(
    case_id: Annotated[str, Path(min_length=1)],
    nurse: NurseUserDep,
    session: SessionDep,
) -> NurseCaseDetailDTO:
    case = await _get_case(session, case_id)
    review = await _get_review_state(session, case_id)
    queue_item = await _queue_item(session, case, review)
    _, profile = await _patient_context(session, case)

    observation_result = await session.execute(
        select(ClinicalObservation)
        .where(ClinicalObservation.triage_case_id == case_id)
        .order_by(ClinicalObservation.created_at.desc())
    )
    latest_by_kind: dict[str, ClinicalObservation] = {}
    for observation in observation_result.scalars().all():
        latest_by_kind.setdefault(observation.kind, observation)

    observation_dtos: list[ClinicalObservationDTO] = []
    for observation in latest_by_kind.values():
        recorder = await _identity(session, observation.recorded_by)
        if recorder is None:
            continue
        observation_dtos.append(
            ClinicalObservationDTO(
                id=observation.id,
                kind=observation.kind,
                value=observation.value,
                unit=observation.unit,
                availability=observation.availability,
                source=observation.source,
                measured_at=observation.measured_at,
                recorded_by=recorder,
                recorded_at=observation.created_at,
            )
        )

    raw_sbar = case.sbar_summary if isinstance(case.sbar_summary, dict) else {}
    clinical_context = raw_sbar.get("clinical_context") if isinstance(raw_sbar.get("clinical_context"), dict) else {}
    ehr_snapshot = (
        clinical_context.get("ehr_snapshot") if isinstance(clinical_context.get("ehr_snapshot"), dict) else {}
    )
    patient_reported_vitals = (
        clinical_context.get("patient_reported_vitals")
        if isinstance(clinical_context.get("patient_reported_vitals"), dict)
        else {}
    )

    def safe_sbar_value(key: str) -> str | None:
        value = raw_sbar.get(key)
        return normalize_clinical_display_text(filter_output_diagnosis(str(value))) if value else None

    safe_assessment = safe_sbar_value("assessment")
    citations = _citation_dtos(case)
    transcript: list[ClinicalTranscriptMessageDTO] = []
    if review.assigned_nurse_id == nurse.id:
        transcript_result = await session.execute(
            select(ChatMessage).where(ChatMessage.triage_case_id == case_id).order_by(ChatMessage.created_at.asc())
        )
        transcript = [
            _transcript_dto(message)
            for message in transcript_result.scalars().all()
            if message.sender_type in TRANSCRIPT_SENDER_TYPES
        ]
    specialist_review_required = review.decision_type in {
        "REQUEST_SPECIALIST_REVIEW",
        "ESCALATE_TO_DOCTOR",
    }
    await session.commit()
    return NurseCaseDetailDTO(
        **queue_item.model_dump(),
        triage_status=case.status,
        final_esi=case.final_clinical_esi if case.final_clinical_esi in {1, 2, 3, 4, 5} else None,
        observations=observation_dtos,
        risk_context=RiskContextDTO(
            age=ehr_snapshot.get("age", profile.age if profile else None),
            gender=ehr_snapshot.get("gender", profile.gender if profile else None),
            height_cm=ehr_snapshot.get("height_cm", profile.height_cm if profile else None),
            weight_kg=ehr_snapshot.get("weight_kg", profile.weight_kg if profile else None),
            bmi=ehr_snapshot.get("bmi", _profile_bmi(profile)),
            blood_type=ehr_snapshot.get("blood_type", profile.blood_type if profile else None),
            chronic_conditions=list(
                ehr_snapshot.get("chronic_conditions", profile.chronic_conditions if profile else []) or []
            ),
            allergies=list(ehr_snapshot.get("allergies", profile.allergies if profile else []) or []),
            active_medications=list(
                ehr_snapshot.get("daily_medications", profile.daily_medications if profile else []) or []
            ),
            pregnancy_status=None,
            patient_reported_vitals=patient_reported_vitals,
            patient_reported_vitals_source=(
                str(clinical_context["patient_reported_vitals_source"])
                if clinical_context.get("patient_reported_vitals_source")
                else None
            ),
            patient_reported_vitals_measured_at=(
                str(clinical_context["patient_reported_vitals_measured_at"])
                if clinical_context.get("patient_reported_vitals_measured_at")
                else None
            ),
            vital_signs_status=str(clinical_context.get("vital_signs_status") or "NOT_REVIEWED"),
            ehr_confirmation_status=str(ehr_snapshot.get("confirmation_status") or "NOT_REVIEWED"),
            ehr_profile_updated_at=(str(ehr_snapshot["updated_at"]) if ehr_snapshot.get("updated_at") else None),
            patient_context_note=(
                str(ehr_snapshot["patient_context_note"]) if ehr_snapshot.get("patient_context_note") else None
            ),
        ),
        sbar=SbarSummaryDTO(
            situation=safe_sbar_value("situation"),
            background=safe_sbar_value("background"),
            assessment=safe_assessment,
            recommendation=(
                f"Đề xuất phân luồng ESI {case.ai_proposed_esi}; cần Điều dưỡng xác nhận."
                if case.ai_proposed_esi in {1, 2, 3, 4, 5}
                else None
            ),
        ),
        citations=citations,
        ai_rationale=safe_assessment,
        transcript=transcript,
        specialist_review=SpecialistReviewContextDTO(
            required=specialist_review_required,
            reason_code=review.decision_reason_code if specialist_review_required else None,
            note=review.decision_note if specialist_review_required else None,
            requested_at=review.decided_at if specialist_review_required else None,
        ),
    )


@router.post("/cases/{case_id}/claim", response_model=NurseActionResponseDTO)
async def claim_or_release_case(
    case_id: Annotated[str, Path(min_length=1)],
    payload: ClaimCaseRequestDTO,
    nurse: NurseUserDep,
    session: SessionDep,
) -> NurseActionResponseDTO:
    case = await _get_case(session, case_id, lock=True)
    review = await _get_review_state(session, case_id, lock=True)
    _assert_version(review, payload.case_version)
    before = {"assignee": review.assigned_nurse_id, "review_status": _review_status(review), "version": review.version}

    if payload.action == "CLAIM":
        if review.assigned_nurse_id and review.assigned_nurse_id != nurse.id:
            assignee = await _identity(session, review.assigned_nurse_id)
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Ca đang do {assignee.name if assignee else 'nhân viên khác'} phụ trách.",
            )
        review.assigned_nurse_id = nurse.id
        review.review_status = "IN_REVIEW"
        review.claimed_at = review.claimed_at or get_utc_now()
        case.assigned_nurse_id = nurse.id
        event_type = "NURSE_CASE_CLAIMED"
        message = "Đã nhận ca. Bạn có thể rà soát và bổ sung dữ liệu."
    else:
        _assert_assignee(review, nurse)
        if _review_status(review) in TERMINAL_REVIEW_STATUSES or review.review_status == "TRIAGE_DECIDED":
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT, detail="Không thể trả ca sau khi đã ra quyết định."
            )
        review.assigned_nurse_id = None
        review.review_status = "WAITING_REVIEW"
        review.claimed_at = None
        case.assigned_nurse_id = None
        event_type = "NURSE_CASE_RELEASED"
        message = "Đã trả ca về hàng đợi."

    review.version += 1
    review.updated_at = get_utc_now()
    _audit(
        session,
        event_type=event_type,
        case_id=case_id,
        nurse=nurse,
        before=before,
        after={"assignee": review.assigned_nurse_id, "review_status": review.review_status, "version": review.version},
        note=payload.reason,
    )
    await session.commit()

    claimed = payload.action == "CLAIM"
    signal = {
        "case_id": case_id,
        "review_status": review.review_status,
        "assignee_name": nurse.full_name if claimed else None,
        "case_version": review.version,
    }
    event = EVENT_CASE_CLAIMED if claimed else EVENT_CASE_RELEASED
    # Hàng đợi cần biết ca đã có người, còn bệnh nhân cần biết có nhân viên thật
    # đang xem hồ sơ của mình.
    await _publish(STAFF_QUEUE_TOPIC, event, signal)
    await _publish(case_topic(case_id), event, signal)

    return NurseActionResponseDTO(
        case_id=case_id,
        review_status=review.review_status,
        case_version=review.version,
        message=message,
    )


@router.patch("/cases/{case_id}/observations", response_model=NurseActionResponseDTO)
async def update_case_observations(
    case_id: Annotated[str, Path(min_length=1)],
    payload: UpdateObservationsRequestDTO,
    nurse: NurseUserDep,
    session: SessionDep,
) -> NurseActionResponseDTO:
    await _get_case(session, case_id, lock=True)
    review = await _get_review_state(session, case_id, lock=True)
    _assert_version(review, payload.case_version)
    _assert_assignee(review, nurse)

    previous_result = await session.execute(
        select(ClinicalObservation)
        .where(ClinicalObservation.triage_case_id == case_id)
        .order_by(ClinicalObservation.created_at.desc())
    )
    previous_by_kind: dict[str, ClinicalObservation] = {}
    for observation in previous_result.scalars().all():
        previous_by_kind.setdefault(observation.kind, observation)

    before: dict[str, Any] = {}
    after: dict[str, Any] = {}
    now = get_utc_now()
    for item in payload.observations:
        previous = previous_by_kind.get(item.kind)
        before[item.kind] = (
            {
                "value": previous.value,
                "unit": previous.unit,
                "availability": previous.availability,
                "source": previous.source,
            }
            if previous
            else None
        )
        measured_at = item.measured_at
        if measured_at and measured_at.tzinfo is not None:
            measured_at = measured_at.replace(tzinfo=None)
        session.add(
            ClinicalObservation(
                triage_case_id=case_id,
                kind=item.kind,
                value=item.value,
                unit=item.unit,
                availability=item.availability,
                source=item.source,
                measured_at=measured_at,
                recorded_by=nurse.id,
            )
        )
        after[item.kind] = {
            "value": item.value,
            "unit": item.unit,
            "availability": item.availability,
            "source": item.source,
            "measured_at": measured_at.isoformat() if measured_at else None,
        }

    review.review_status = "IN_REVIEW"
    review.version += 1
    review.updated_at = now
    _audit(
        session,
        event_type="NURSE_OBSERVATIONS_UPDATED",
        case_id=case_id,
        nurse=nurse,
        before=before,
        after=after,
        note="Cập nhật dữ liệu có nguồn gốc trong bước rà soát Triage.",
    )
    await session.commit()
    return NurseActionResponseDTO(
        case_id=case_id,
        review_status=review.review_status,
        case_version=review.version,
        message="Đã lưu dữ liệu sinh hiệu và nguồn ghi nhận.",
    )


@router.patch("/cases/{case_id}/intake", response_model=NurseActionResponseDTO)
async def update_case_intake(
    case_id: Annotated[str, Path(min_length=1)],
    payload: UpdateIntakeRequestDTO,
    nurse: NurseUserDep,
    session: SessionDep,
) -> NurseActionResponseDTO:
    """Correct the chief complaint with ownership, versioning and audit."""
    case = await _get_case(session, case_id, lock=True)
    review = await _get_review_state(session, case_id, lock=True)
    _assert_version(review, payload.case_version)
    _assert_assignee(review, nurse)

    before = {"chief_complaint": case.session_title}
    case.session_title = payload.chief_complaint
    case.updated_at = get_utc_now()
    review.review_status = "IN_REVIEW"
    review.version += 1
    review.updated_at = get_utc_now()
    _audit(
        session,
        event_type="CLINICAL_INTAKE_UPDATED",
        case_id=case_id,
        nurse=nurse,
        before=before,
        after={
            "chief_complaint": case.session_title,
            "version": review.version,
        },
        note="Bổ sung hoặc hiệu chỉnh triệu chứng chính trong bước rà soát Triage.",
    )
    await session.commit()
    return NurseActionResponseDTO(
        case_id=case_id,
        review_status=review.review_status,
        case_version=review.version,
        message="Đã lưu triệu chứng chính và nhật ký thay đổi.",
    )


@router.post("/cases/{case_id}/decision", response_model=NurseActionResponseDTO)
async def submit_triage_decision(
    case_id: Annotated[str, Path(min_length=1)],
    payload: TriageDecisionRequestDTO,
    nurse: NurseUserDep,
    session: SessionDep,
) -> NurseActionResponseDTO:
    case = await _get_case(session, case_id, lock=True)
    review = await _get_review_state(session, case_id, lock=True)
    _assert_assignee(review, nurse)
    if review.version != payload.case_version:
        is_safe_retry = (
            review.version == payload.case_version + 1
            and review.review_status == "TRIAGE_DECIDED"
            and review.decision_type == payload.decision_type
            and review.decision_reason_code == payload.reason_code
            and review.decision_note == payload.note
            and case.final_clinical_esi == payload.final_esi
        )
        if is_safe_retry:
            return NurseActionResponseDTO(
                case_id=case_id,
                review_status=review.review_status,
                case_version=review.version,
                message="Quyết định này đã được lưu trước đó.",
            )
        _assert_version(review, payload.case_version)
    missing = _missing_fields(case)
    if missing:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={"code": "INCOMPLETE_TRIAGE_DATA", "missing_fields": missing},
        )
    if _review_status(review) in TERMINAL_REVIEW_STATUSES:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Ca đã được bàn giao.")
    if payload.decision_type == "CONFIRM_ESI" and payload.final_esi != case.ai_proposed_esi:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Xác nhận ESI phải giữ nguyên mức AI đề xuất."
        )
    if payload.decision_type == "ADJUST_ESI":
        if payload.final_esi == case.ai_proposed_esi:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Mức điều chỉnh phải khác ESI do AI đề xuất."
            )
        if not payload.note or len(payload.note.strip()) < 10:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Điều chỉnh ESI cần ghi chú lâm sàng ít nhất 10 ký tự.",
            )

    before = {
        "ai_esi": case.ai_proposed_esi,
        "final_esi": case.final_clinical_esi,
        "review_status": review.review_status,
        "version": review.version,
    }
    case.final_clinical_esi = payload.final_esi
    case.is_overridden = payload.decision_type == "ADJUST_ESI"
    case.reviewed_at = get_utc_now()
    review.review_status = "TRIAGE_DECIDED"
    review.decision_type = payload.decision_type
    review.decision_reason_code = payload.reason_code
    review.decision_note = payload.note
    review.decided_at = get_utc_now()
    review.version += 1
    review.updated_at = get_utc_now()
    _audit(
        session,
        event_type="NURSE_ESI_CONFIRMED" if payload.decision_type == "CONFIRM_ESI" else "NURSE_ESI_ADJUSTED",
        case_id=case_id,
        nurse=nurse,
        before=before,
        after={
            "ai_esi": case.ai_proposed_esi,
            "final_esi": payload.final_esi,
            "review_status": review.review_status,
            "reason_code": payload.reason_code,
            "version": review.version,
        },
        note=payload.note,
    )
    await session.commit()
    return NurseActionResponseDTO(
        case_id=case_id,
        review_status=review.review_status,
        case_version=review.version,
        message="Đã lưu quyết định phân luồng trên máy chủ.",
    )


@router.post("/cases/{case_id}/escalate", response_model=NurseActionResponseDTO)
async def request_specialist_review(
    case_id: Annotated[str, Path(min_length=1)],
    payload: EscalateCaseRequestDTO,
    nurse: NurseUserDep,
    session: SessionDep,
) -> NurseActionResponseDTO:
    case = await _get_case(session, case_id, lock=True)
    review = await _get_review_state(session, case_id, lock=True)
    _assert_version(review, payload.case_version)
    _assert_assignee(review, nurse)
    if _review_status(review) in TERMINAL_REVIEW_STATUSES:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Ca đã được bàn giao.")
    before = {
        "assignee": review.assigned_nurse_id,
        "review_status": _review_status(review),
        "version": review.version,
    }
    review.review_status = SPECIALIST_REVIEW_STATUS
    review.decision_type = "REQUEST_SPECIALIST_REVIEW"
    review.decision_reason_code = payload.reason_code
    review.decision_note = payload.note
    review.decided_at = get_utc_now()
    review.assigned_nurse_id = None
    review.version += 1
    review.updated_at = get_utc_now()
    case.assigned_nurse_id = None
    _audit(
        session,
        event_type="CLINICAL_SPECIALIST_REVIEW_REQUESTED",
        case_id=case_id,
        nurse=nurse,
        before=before,
        after={
            "assignee": None,
            "review_status": review.review_status,
            "reason_code": payload.reason_code,
            "version": review.version,
        },
        note=payload.note,
    )
    await session.commit()

    signal = {
        "case_id": case_id,
        "review_status": review.review_status,
        "reason_code": payload.reason_code,
        "case_version": review.version,
    }
    await _publish(STAFF_QUEUE_TOPIC, EVENT_CASE_ESCALATED, signal)
    await _publish(case_topic(case_id), EVENT_CASE_ESCALATED, signal)

    return NurseActionResponseDTO(
        case_id=case_id,
        review_status=review.review_status,
        case_version=review.version,
        message="Đã đưa ca về hàng đợi đánh giá chuyên sâu của đội ngũ lâm sàng.",
    )


@router.post("/cases/{case_id}/handoff", response_model=NurseActionResponseDTO)
async def handoff_case(
    case_id: Annotated[str, Path(min_length=1)],
    payload: HandoffCaseRequestDTO,
    nurse: NurseUserDep,
    session: SessionDep,
) -> NurseActionResponseDTO:
    case = await _get_case(session, case_id, lock=True)
    review = await _get_review_state(session, case_id, lock=True)
    _assert_version(review, payload.case_version)
    _assert_assignee(review, nurse)
    if review.review_status != "TRIAGE_DECIDED":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Cần lưu quyết định phân luồng trước khi bàn giao.",
        )

    before = {"review_status": review.review_status, "version": review.version}
    review.review_status = "HANDED_OFF"
    review.handoff_destination = payload.destination
    review.handoff_note = payload.note
    review.handed_off_at = get_utc_now()
    review.version += 1
    review.updated_at = get_utc_now()
    case.status = "COMPLETED"
    _audit(
        session,
        event_type="NURSE_HANDOFF_COMPLETED",
        case_id=case_id,
        nurse=nurse,
        before=before,
        after={"review_status": review.review_status, "destination": payload.destination, "version": review.version},
        note=payload.note,
    )
    await session.commit()
    return NurseActionResponseDTO(
        case_id=case_id,
        review_status=review.review_status,
        case_version=review.version,
        message="Đã bàn giao và hoàn tất phần việc lâm sàng.",
    )


@router.post("/alerts/{case_id}/acknowledge", response_model=NurseActionResponseDTO)
async def acknowledge_red_flag_alert(
    case_id: Annotated[str, Path(min_length=1)],
    payload: AcknowledgeAlertRequestDTO,
    nurse: NurseUserDep,
    session: SessionDep,
) -> NurseActionResponseDTO:
    case = await _get_case(session, case_id, lock=True)
    if not case.is_red_flag_triggered:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Ca này không có cảnh báo Red Flag."
        )
    review = await _get_review_state(session, case_id, lock=True)
    _assert_version(review, payload.case_version)
    if review.alert_acknowledged_at is None:
        review.alert_acknowledged_by = nurse.id
        review.alert_acknowledged_at = get_utc_now()
        review.version += 1
        review.updated_at = get_utc_now()
        _audit(
            session,
            event_type="NURSE_RED_FLAG_ACKNOWLEDGED",
            case_id=case_id,
            nurse=nurse,
            before={"acknowledged": False, "version": payload.case_version},
            after={"acknowledged": True, "version": review.version},
        )
        await session.commit()
    return NurseActionResponseDTO(
        case_id=case_id,
        review_status=_review_status(review),
        case_version=review.version,
        message="Đã xác nhận nhìn thấy cảnh báo; ca vẫn được ghim trong hàng đợi.",
    )


@router.post("/cases/{case_id}/pii-access", response_model=PiiAccessResponseDTO)
async def access_case_pii(
    case_id: Annotated[str, Path(min_length=1)],
    payload: PiiAccessRequestDTO,
    nurse: NurseUserDep,
    session: SessionDep,
) -> PiiAccessResponseDTO:
    case = await _get_case(session, case_id)
    review = await _get_review_state(session, case_id)
    _assert_assignee(review, nurse)
    patient, profile = await _patient_context(session, case)
    if patient is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Không tìm thấy thông tin liên hệ của bệnh nhân."
        )
    expires_at = get_utc_now() + timedelta(minutes=5)
    _audit(
        session,
        event_type="PII_UNMASKED",
        case_id=case_id,
        nurse=nurse,
        before={"pii_status": "MASKED"},
        after={"pii_status": "TEMPORARILY_VISIBLE", "expires_at": expires_at.isoformat()},
        note=payload.reason,
    )
    await session.commit()
    # Khi ca thuộc về người thân, số của chủ tài khoản là số người giám hộ chứ
    # không phải số bệnh nhân. Trả nhầm ở đây khiến nhân viên gọi sai người vào
    # đúng lúc cần gọi gấp, nên ưu tiên số riêng của hồ sơ đang được khám.
    case_is_account_owner = profile is None or profile.relationship_type == "SELF"
    patient_phone = patient.phone if case_is_account_owner else (profile.phone_number if profile else None)
    return PiiAccessResponseDTO(
        case_id=case_id,
        full_name=profile.full_name if profile else patient.full_name,
        phone=patient_phone,
        emergency_contact_name=profile.emergency_contact_name if profile else None,
        emergency_contact_phone=profile.emergency_contact_phone if profile else None,
        expires_at=expires_at,
    )


# =====================================================================
# HỘI THOẠI TRỰC TIẾP GIỮA NHÂN VIÊN LÂM SÀNG VÀ BỆNH NHÂN
# =====================================================================


@router.get("/cases/{case_id}/messages", response_model=CaseMessagesResponseDTO)
async def list_case_messages(
    case_id: Annotated[str, Path(min_length=1)],
    nurse: NurseUserDep,
    session: SessionDep,
) -> CaseMessagesResponseDTO:
    """Toàn bộ hội thoại của ca, dành cho nhân viên đang phụ trách.

    Đọc được hội thoại là đọc được lời kể bệnh, nên vẫn phải nhận ca trước.
    """
    await _get_case(session, case_id)
    review = await _get_review_state(session, case_id)
    _assert_assignee(review, nurse)

    result = await session.execute(
        select(ChatMessage).where(ChatMessage.triage_case_id == case_id).order_by(ChatMessage.created_at.asc())
    )
    messages = [
        _transcript_dto(message) for message in result.scalars().all() if message.sender_type in TRANSCRIPT_SENDER_TYPES
    ]
    unread_count, _ = await _conversation_stats(session, case_id)
    await session.commit()
    return CaseMessagesResponseDTO(
        case_id=case_id,
        messages=messages,
        unread_count=unread_count,
    )


@router.post(
    "/cases/{case_id}/messages",
    response_model=CaseMessagesResponseDTO,
    status_code=status.HTTP_201_CREATED,
)
async def send_case_message(
    case_id: Annotated[str, Path(min_length=1)],
    payload: SendCaseMessageRequestDTO,
    nurse: NurseUserDep,
    session: SessionDep,
) -> CaseMessagesResponseDTO:
    """Nhân viên lâm sàng nhắn trực tiếp cho bệnh nhân trong ca đang phụ trách.

    Nội dung được lưu nguyên văn: đây là phát ngôn của một người có chuyên môn
    chịu trách nhiệm, không phải văn bản do mô hình sinh ra.
    """
    case = await _get_case(session, case_id, lock=True)
    review = await _get_review_state(session, case_id, lock=True)
    if _review_status(review) in TERMINAL_REVIEW_STATUSES:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Ca đã bàn giao, không nhắn thêm được trong hội thoại này.",
        )
    # Nhắn được thẳng từ hàng đợi, không phải mở toàn bộ hồ sơ trước.
    claimed_now = await _claim_for_reply(session, case, review, nurse)

    # Một lần bấm gửi chỉ được tạo một bản ghi, kể cả khi client thử lại.
    if payload.client_message_id:
        existing = await session.execute(
            select(ChatMessage).where(
                ChatMessage.triage_case_id == case_id,
                ChatMessage.client_message_id == payload.client_message_id,
            )
        )
        if existing.scalars().first() is not None:
            return await list_case_messages(case_id, nurse, session)

    record = ChatMessage(
        triage_case_id=case_id,
        sender_type="NURSE",
        content=payload.content,
        sender_id=nurse.id,
        sender_display_name=nurse.full_name,
        client_message_id=payload.client_message_id,
        channel=CARE_TEAM_CHANNEL,
    )
    session.add(record)
    _audit(
        session,
        event_type="CLINICAL_MESSAGE_SENT",
        case_id=case_id,
        nurse=nurse,
        before={"channel": "CASE_CONVERSATION"},
        after={"message_id": record.id, "length": len(payload.content)},
    )
    await session.commit()

    if claimed_now:
        claim_signal = {
            "case_id": case_id,
            "review_status": review.review_status,
            "assignee_name": nurse.full_name,
            "case_version": review.version,
        }
        await _publish(STAFF_QUEUE_TOPIC, EVENT_CASE_CLAIMED, claim_signal)
        await _publish(case_topic(case_id), EVENT_CASE_CLAIMED, claim_signal)

    signal = {
        "case_id": case_id,
        "message_id": record.id,
        "sender": "NURSE",
        "sender_name": nurse.full_name,
        "priority": _message_priority(case),
        "created_at": record.created_at.isoformat(),
    }
    await _publish(case_topic(case_id), EVENT_MESSAGE_CREATED, signal)
    await _publish(STAFF_QUEUE_TOPIC, EVENT_MESSAGE_CREATED, signal)
    await _publish(patient_topic(case.patient_id), EVENT_MESSAGE_CREATED, signal)
    return await list_case_messages(case_id, nurse, session)


@router.post("/cases/{case_id}/messages/read")
async def mark_case_messages_read(
    case_id: Annotated[str, Path(min_length=1)],
    nurse: NurseUserDep,
    session: SessionDep,
) -> CaseMessagesResponseDTO:
    """Đánh dấu các tin của bệnh nhân là đã được phía lâm sàng đọc."""
    await _get_case(session, case_id)

    result = await session.execute(
        select(ChatMessage).where(
            ChatMessage.triage_case_id == case_id,
            ChatMessage.sender_type == "PATIENT",
            ChatMessage.read_at.is_(None),
        )
    )
    now = get_utc_now()
    changed = 0
    for message in result.scalars().all():
        message.read_at = now
        changed += 1
    await session.commit()

    if changed:
        await _publish(
            case_topic(case_id),
            EVENT_MESSAGE_READ,
            {"case_id": case_id, "read_by": "CLINICAL_STAFF", "count": changed},
        )
    return await list_case_messages(case_id, nurse, session)


@router.get(
    "/cases/{case_id}/emergency-contacts",
    response_model=EmergencyContactResponseDTO,
)
async def get_case_emergency_contacts(
    case_id: Annotated[str, Path(min_length=1)],
    nurse: NurseUserDep,
    session: SessionDep,
) -> EmergencyContactResponseDTO:
    """Danh bạ khẩn cấp của ca, tách rõ bệnh nhân với người liên hệ.

    Một ca có thể thuộc về người thân chứ không phải chủ tài khoản. Khi đó số
    của chủ tài khoản là số **người giám hộ**, không phải số bệnh nhân; gộp hai
    số này lại là một sai sót lâm sàng thật vào đúng lúc cần gọi gấp.
    """
    case = await _get_case(session, case_id)
    review = await _get_review_state(session, case_id)
    _assert_assignee(review, nurse)
    patient, profile = await _patient_context(session, case)
    if patient is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Không tìm thấy thông tin liên hệ của bệnh nhân.",
        )

    # Ca của chính chủ tài khoản: hồ sơ SELF, hoặc ca không gắn hồ sơ nào.
    case_is_account_owner = profile is None or profile.relationship_type == "SELF"
    contacts: list[EmergencyContactPersonDTO] = [
        EmergencyContactPersonDTO(
            label="Bệnh nhân",
            full_name=profile.full_name if profile else patient.full_name,
            relationship=None if case_is_account_owner else profile.relationship_type,
            phone=(patient.phone if case_is_account_owner else (profile.phone_number if profile else None)),
        )
    ]
    if not case_is_account_owner:
        contacts.append(
            EmergencyContactPersonDTO(
                label="Chủ tài khoản / người giám hộ",
                full_name=patient.full_name,
                relationship="Người tạo hồ sơ",
                phone=patient.phone,
            )
        )
    if profile and profile.emergency_contact_name:
        contacts.append(
            EmergencyContactPersonDTO(
                label="Người liên hệ khẩn cấp",
                full_name=profile.emergency_contact_name,
                relationship=None,
                phone=profile.emergency_contact_phone,
            )
        )

    expires_at = get_utc_now() + timedelta(minutes=5)
    _audit(
        session,
        event_type="PII_UNMASKED",
        case_id=case_id,
        nurse=nurse,
        before={"pii_status": "MASKED"},
        after={
            "pii_status": "TEMPORARILY_VISIBLE",
            "channel": "EMERGENCY_CONTACTS",
            "expires_at": expires_at.isoformat(),
        },
    )
    await session.commit()
    return EmergencyContactResponseDTO(
        case_id=case_id,
        contacts=contacts,
        expires_at=expires_at,
    )


# =====================================================================
# HỘP THƯ TRẠM TRỰC — BIẾT CÓ VIỆC MÀ KHÔNG PHẢI MỞ TỪNG HỒ SƠ
# =====================================================================


@router.get("/inbox", response_model=InboxResponseDTO)
async def get_clinical_inbox(
    nurse: NurseUserDep,
    session: SessionDep,
    limit: Annotated[int, Query(ge=1, le=50)] = 20,
) -> InboxResponseDTO:
    """Các ca có tin nhắn của người bệnh mà phía lâm sàng chưa đọc.

    Mở cho mọi nhân viên lâm sàng đang trực, vì đây chính là thứ quyết định nên
    mở ca nào trước. Mỗi dòng chỉ mang một trích ngắn; hồ sơ đầy đủ, sinh hiệu và
    danh bạ liên hệ vẫn nằm sau lớp kiểm quyền của từng ca.
    """
    result = await session.execute(
        select(TriageCase).where(TriageCase.status.in_(INBOX_TRIAGE_STATUSES)).order_by(TriageCase.created_at.desc())
    )
    cases = list(result.scalars().all())

    items: list[InboxItemDTO] = []
    for case in cases:
        messages = (
            (
                await session.execute(
                    select(ChatMessage)
                    .where(
                        ChatMessage.triage_case_id == case.id,
                        ChatMessage.sender_type == "PATIENT",
                        ChatMessage.channel == CARE_TEAM_CHANNEL,
                    )
                    .order_by(ChatMessage.created_at.asc())
                )
            )
            .scalars()
            .all()
        )
        unread = [message for message in messages if message.read_at is None]
        if not unread:
            continue

        review = await _get_review_state(session, case.id)
        if _review_status(review) in TERMINAL_REVIEW_STATUSES:
            continue

        patient, profile = await _patient_context(session, case)
        latest = unread[-1]
        items.append(
            InboxItemDTO(
                case_id=case.id,
                patient_name=(profile.full_name if profile else patient.full_name if patient else "Bệnh nhân ẩn danh"),
                age=profile.age if profile else None,
                sex=profile.gender if profile else None,
                chief_complaint=("" if case.session_title == "Triage Consultation" else case.session_title),
                ai_recommended_esi=(case.ai_proposed_esi if case.ai_proposed_esi in {1, 2, 3, 4, 5} else None),
                is_red_flag=case.is_red_flag_triggered,
                priority=_message_priority(case),
                preview=latest.content[:INBOX_PREVIEW_LENGTH],
                unread_count=len(unread),
                last_message_at=latest.created_at,
                assignee=await _identity(session, review.assigned_nurse_id),
                case_version=review.version,
            )
        )

    # Báo động đỏ lên trước, rồi tới ESI thấp, rồi tin mới nhất.
    priority_rank = {"RED_FLAG": 0, "URGENT": 1, "NORMAL": 2}
    items.sort(
        key=lambda item: (
            priority_rank.get(item.priority, 2),
            item.ai_recommended_esi if item.ai_recommended_esi is not None else 6,
            -(item.last_message_at.timestamp() if item.last_message_at else 0),
        )
    )
    await session.commit()

    return InboxResponseDTO(
        items=items[:limit],
        total_unread=sum(item.unread_count for item in items),
        urgent_unread=sum(item.unread_count for item in items if item.priority in {"RED_FLAG", "URGENT"}),
    )


@router.get("/cases/{case_id}/care-team", response_model=CaseMessagesResponseDTO)
async def get_case_care_team_thread(
    case_id: Annotated[str, Path(min_length=1)],
    nurse: NurseUserDep,
    session: SessionDep,
) -> CaseMessagesResponseDTO:
    """Riêng luồng trao đổi giữa người bệnh và nhân viên, không kèm hội thoại AI.

    Đọc được mà không cần nhận ca: nhân viên đang trực cần trả lời nhanh từ hàng
    đợi. Hội thoại hỏi bệnh với AI, sinh hiệu và danh bạ liên hệ vẫn đòi phải
    nhận ca, vì đó là hồ sơ lâm sàng chứ không phải kênh liên lạc.
    """
    await _get_case(session, case_id)
    result = await session.execute(
        select(ChatMessage)
        .where(
            ChatMessage.triage_case_id == case_id,
            ChatMessage.channel == CARE_TEAM_CHANNEL,
        )
        .order_by(ChatMessage.created_at.asc())
    )
    messages = [_transcript_dto(message) for message in result.scalars().all()]
    unread_count, _ = await _conversation_stats(session, case_id)
    await session.commit()
    return CaseMessagesResponseDTO(
        case_id=case_id,
        messages=messages,
        unread_count=unread_count,
    )
