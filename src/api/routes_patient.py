"""Cổng API Giao thiệp Bệnh Nhân: Trò Chuyện Trắc Nghiệm Triage & Lịch Sử Replay Chỉ Độc.

Tuân thủ nghiêm ngặt chuẩn backend-rules.md:
- Kiến trúc modular async router với FastAPI & SQLModel.
- Quản trị TriageCase, ChatMessage và bộ não DeepAgent có clinical tool gates.
- Hỗ trợ xem lại Lịch sử khám (Read-Only Replay) kèm theo chữ ký thẩm định từ Điều dưỡng / Bác sĩ.
"""

import asyncio
import json
import logging
import time
import uuid
from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter, HTTPException, status
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select, func

from src.agents.deepagent_runtime import get_deepagent_runtime
from src.agents.tools.queue_pusher import publish_finalized_sbar
from src.services.health_topics import get_topic_by_slug
from src.services.clinical_state_persistence import persist_turn_state
from src.agents.nodes.intake_analyzer import (
    EHR_CONFIRMATION_OPTION_IDS,
    resolve_ehr_confirmation_choice,
)
from src.api.dependencies import PatientUserDep, SessionDep
from src.models.db_models import ChatMessage, EHRProfile, NurseReviewState, TriageCase, User, get_utc_now
from src.services.event_bus import (
    EVENT_MESSAGE_CREATED,
    EVENT_MESSAGE_READ,
    STAFF_QUEUE_TOPIC,
    case_topic,
    get_event_bus,
)
from src.models.patient_schemas import (
    CareTeamMessageDTO,
    CareTeamThreadResponse,
    SendStaffMessageRequestDTO,
    StaffConversationResponse,
    AgentStreamEventDTO,
    CaseSupportDTO,
    HistoryListResponse,
    HitlSignatureDTO,
    PatientChatInputDTO,
    PatientChatMessageDTO,
    RagCitationDTO,
    SbarReportDTO,
    SessionMessagesResponse,
    SessionStatusDTO,
    StartTriageRequest,
    StartTriageResponse,
    StructuredPayloadDTO,
    TriageHistoryListItemDTO,
    TriageSessionDetailDTO,
)
from src.services.triage_session_recovery import (
    INTAKE_CONFIRMATION_TEXT,
    build_question_recovery_payload,
    recover_triage_state,
)

router = APIRouter(prefix="/triage", tags=["Patient Triage Engine & History Replay"])

# Trao đổi trực tiếp với nhân viên y tế là một luồng riêng, không phải một lượt
# hỏi bệnh. Trộn chung sẽ khiến phần phục hồi phiên hiểu nhầm đó là câu trả lời
# cho câu hỏi của AI.
CARE_TEAM_CHANNEL = "CARE_TEAM"

# Ca đã đóng sổ thì kênh trao đổi cũng đóng theo.
CLOSED_CASE_STATUSES = frozenset({"COMPLETED", "CANCELLED"})


def case_message_priority(case: TriageCase) -> str:
    """Mức ưu tiên của một tin mới, suy từ chính bản ghi ca.

    Chỉ dùng để sắp xếp và làm nổi bật ở trạm trực. Không phải một kết luận lâm
    sàng mới và không bao giờ ghi đè ESI.
    """
    if case.is_red_flag_triggered or case.status == "RED_FLAG_LOCKED":
        return "RED_FLAG"
    if case.ai_proposed_esi in {1, 2}:
        return "URGENT"
    return "NORMAL"
logger = logging.getLogger(__name__)

_PUBLIC_DECISION_STATUSES = frozenset(
    {
        "NOT_APPLICABLE",
        "COLLECTING",
        "NEEDS_CLARIFICATION",
        "READY_FOR_EVIDENCE",
        "READY_FOR_REASONING",
        "AWAITING_PATIENT_CONFIRMATION",
        "INSUFFICIENT_EVIDENCE",
        "RETRIEVAL_FAILURE",
        "PROPOSED",
        "EMERGENCY_ESCALATED",
    }
)
_PUBLIC_EVIDENCE_STATUSES = frozenset(
    {
        "NOT_REQUESTED",
        "RETRIEVED",
        "INSUFFICIENT_EVIDENCE",
        "RETRIEVAL_FAILURE",
        "CASE_EXAMPLE_SUPPORT",
        "SUFFICIENT",
    }
)
_PUBLIC_WORKFLOW_PHASES = frozenset(
    {
        "SAFETY_CHECK",
        "INTENT_CLASSIFICATION",
        "INTAKE_EXTRACTION",
        "CLARIFICATION",
        "PATIENT_CONFIRMATION",
        "RETRIEVAL",
        "REASONING",
        "REASSESSMENT",
        "HANDOFF",
        "COMPLETE",
    }
)


def _log_agent_metric(event: str, **values: object) -> None:
    """Emit aggregate-safe telemetry without query text, names or record IDs."""
    logger.info(
        "triage_agent_metric %s",
        json.dumps({"event": event, **values}, ensure_ascii=True, default=str),
    )


def _is_clinical_proposal(ai_result: dict) -> bool:
    metadata = ai_result.get("metadata")
    passed_final_verification = (
        isinstance(metadata, dict)
        and metadata.get("deepagent_tool_gated") is True
    )
    decision_status = ai_result.get("decision_status")
    is_emergency = decision_status == "EMERGENCY_ESCALATED"
    citations = ai_result.get("turn_rag_citations")
    is_confirmed_proposal = (
        decision_status == "PROPOSED"
        and ai_result.get("patient_confirmed_intake") is True
        and ai_result.get("evidence_status") == "SUFFICIENT"
        and ai_result.get("evidence_authority_status") == "AUTHORIZED"
        and bool(citations)
    )
    return (
        passed_final_verification
        and (is_emergency or is_confirmed_proposal)
        and ai_result.get("current_esi_level") in {1, 2, 3, 4, 5}
        and isinstance(ai_result.get("sbar_report"), dict)
    )


def _requires_nurse_review(ai_result: dict) -> bool:
    """Queue every fail-closed clinical handoff without inventing an ESI."""
    # An exhausted structural intake may be impossible for the patient to
    # confirm precisely because the decisive fact remains unknown. The safe
    # response explicitly promises nurse review, so confirmation cannot be a
    # precondition for creating that review artifact. Proposals remain subject
    # to the stricter confirmation/evidence checks in ``_is_clinical_proposal``.
    return _is_clinical_proposal(ai_result) or ai_result.get(
        "decision_status"
    ) == "INSUFFICIENT_EVIDENCE"


async def _commit_and_publish_finalized_sbar(
    session: AsyncSession,
    case_doc: TriageCase,
    ai_result: dict[str, Any],
) -> bool:
    """Commit authoritative state before any best-effort queue publication.

    The API resets ``deepagent_tool_gated`` before every runtime invocation.
    Therefore a proposal can satisfy ``_is_clinical_proposal`` only when the
    final verifier completed during this turn. A commit exception propagates
    and publication is never attempted.
    """
    await session.commit()
    if not _is_clinical_proposal(ai_result):
        return False

    sbar_report = case_doc.sbar_summary
    recommended_esi = case_doc.ai_proposed_esi
    if not isinstance(sbar_report, dict) or recommended_esi not in {1, 2, 3, 4, 5}:
        logger.error("Committed proposal is missing its finalized ESI/SBAR")
        return False
    try:
        return await publish_finalized_sbar(
            session_id=case_doc.id,
            recommended_esi=recommended_esi,
            chief_complaint=case_doc.session_title,
            is_red_flag=bool(case_doc.is_red_flag_triggered),
            sbar_report=sbar_report,
        )
    except Exception:  # noqa: BLE001 - the authoritative result is already durable
        logger.exception("Committed SBAR could not be published")
        return False


def _visible_case_esi(case_doc: TriageCase) -> int | None:
    """Hide legacy/default AI scores from sessions that never reached a proposal state."""
    if case_doc.final_clinical_esi is not None:
        return case_doc.final_clinical_esi
    if case_doc.status in {"HITL_REVIEWING", "RED_FLAG_LOCKED", "COMPLETED"}:
        return case_doc.ai_proposed_esi
    return None


def _patient_hitl_status(
    case_doc: TriageCase,
    review: NurseReviewState | None = None,
) -> str:
    """Return the persisted nurse-decision state visible to the patient.

    A nurse decision is a durable HITL event at ``TRIAGE_DECIDED``; it must
    not be shown as "waiting" merely because the subsequent handoff has not
    happened yet.  This only reads persisted fields and never infers an ESI.
    """

    if case_doc.status == "RED_FLAG_LOCKED":
        return "EMERGENCY_REJECTED"
    if case_doc.is_overridden:
        return "OVERRIDDEN"
    if case_doc.status == "COMPLETED" or (review is not None and review.review_status in {"TRIAGE_DECIDED", "HANDED_OFF"}):
        return "APPROVED"
    return "PENDING_REVIEW"


async def _nurse_decision_context(
    session: AsyncSession,
    case_id: str,
) -> tuple[NurseReviewState | None, str | None]:
    """Read the persisted decision and reviewer display name for one case."""

    result = await session.execute(
        select(NurseReviewState, User)
        .outerjoin(User, NurseReviewState.assigned_nurse_id == User.id)
        .where(NurseReviewState.triage_case_id == case_id)
    )
    row = result.first()
    if row is None:
        return None, None
    review, reviewer = row
    return review, reviewer.full_name if reviewer else None


def _finalized_sbar_dto(case_doc: TriageCase) -> SbarReportDTO | None:
    """Return only a durable, complete SBAR; never manufacture a draft."""
    if case_doc.status not in {"HITL_REVIEWING", "RED_FLAG_LOCKED", "COMPLETED"}:
        return None
    if _visible_case_esi(case_doc) not in {1, 2, 3, 4, 5}:
        return None
    if not isinstance(case_doc.sbar_summary, dict):
        return None
    if (
        not case_doc.is_red_flag_triggered
        and not _citation_dtos(case_doc.rag_citation_details)
    ):
        return None
    payload = dict(case_doc.sbar_summary)
    payload.setdefault("citations", case_doc.rag_citations or [])
    try:
        return SbarReportDTO.model_validate(payload)
    except ValueError:
        # Pydantic's error text can echo the invalid SBAR input. Keep clinical
        # content out of logs while treating an incomplete legacy row as draft.
        logger.warning("Persisted SBAR is incomplete and remains non-final")
        return None


def _safe_enum(value: object, allowed: frozenset[str]) -> str | None:
    normalized = str(value or "").strip()
    return normalized if normalized in allowed else None


def _safe_degraded_modes(value: object) -> list[str]:
    if not isinstance(value, list):
        return []
    return list(
        dict.fromkeys(
            str(item).strip()[:120]
            for item in value[:20]
            if str(item).strip()
        )
    )


def _dump_sse_event(event: AgentStreamEventDTO) -> str:
    return f"data: {json.dumps(event.model_dump(mode='json'), ensure_ascii=False)}\n\n"


def _session_title(value: str) -> str:
    """Build the short, patient-provided complaint label used by clinical queues."""
    normalized = value.strip()
    return f"{normalized[:45]}..." if len(normalized) > 45 else normalized


def _session_title_from_agent_result(ai_result: dict) -> str:
    """Read an extracted complaint without inventing one from an AI assessment."""
    for source_name in ("clinical_blueprint", "intake_summary"):
        source = ai_result.get(source_name)
        if not isinstance(source, dict):
            continue
        complaints = source.get("chief_complaint")
        if not isinstance(complaints, list):
            continue
        title = ", ".join(
            str(complaint).strip()
            for complaint in complaints
            if str(complaint).strip()
        )
        if title:
            return _session_title(title)
    return ""


_PUBLIC_RETRIEVAL_CHANNELS = {"vi_dense", "en_dense", "sparse", "demo_dense", "hybrid"}


def _public_retrieval_channels(raw_channels: object) -> list[dict[str, object]]:
    """Normalize persisted retrieval channel audit rows for the public DTO.

    Some internal retrieval paths carry a suffix such as
    ``hybrid:resource_fallback``. That suffix is useful in server provenance but
    is outside the frontend's stable channel enum, so replaying a single such
    citation caused the whole chat history payload to fail client validation.
    """
    if not isinstance(raw_channels, list):
        return []

    channels: list[dict[str, object]] = []
    for raw_channel in raw_channels:
        if not isinstance(raw_channel, dict):
            continue
        channel_name = str(raw_channel.get("channel") or "").strip()
        public_channel = channel_name.split(":", 1)[0]
        if public_channel not in _PUBLIC_RETRIEVAL_CHANNELS:
            continue

        row: dict[str, object] = {"channel": public_channel}
        try:
            rank = int(raw_channel.get("rank") or 1)
        except (TypeError, ValueError):
            rank = 1
        row["rank"] = max(rank, 1)

        raw_score = raw_channel.get("score")
        if raw_score is not None:
            try:
                row["score"] = float(raw_score)
            except (TypeError, ValueError):
                pass
        channels.append(row)
    return channels


def _citation_dtos(raw_citations: object) -> list[RagCitationDTO]:
    if not isinstance(raw_citations, list):
        return []
    return [
        RagCitationDTO(
            id=str(c["id"]),
            title=str(c["title"]),
            protocolId=str(c["protocolId"]),
            excerpt=str(c["excerpt"]),
            relevanceScore=c.get("relevanceScore"),
            issuingBody=c.get("issuingBody"),
            sourceUri=c.get("sourceUri"),
            version=c.get("version"),
            section=c.get("section"),
            effectiveDate=c.get("effectiveDate"),
            validationStatus=c.get("validationStatus"),
            contentHash=c.get("contentHash"),
            reviewedBy=c.get("reviewedBy"),
            reviewedAt=c.get("reviewedAt"),
            calibrationId=c.get("calibrationId"),
            sourceType=c.get("sourceType"),
            retrievalChannels=_public_retrieval_channels(
                c.get("retrievalChannels", [])
            ),
        )
        for c in raw_citations
        if isinstance(c, dict)
        # ``None`` keeps legacy protocol rows readable. Every new authority
        # citation is explicitly tagged ``validated_protocol``; CASE_SUPPORT
        # and unknown source kinds never enter the authority channel.
        and c.get("sourceType") in {None, "validated_protocol"}
        and c.get("retrievalScope") != "CASE_SUPPORT"
        and c.get("retrieval_scope") != "CASE_SUPPORT"
        and c.get("authorityStatus") != "NOT_PROTOCOL"
        and c.get("authority_status") != "NOT_PROTOCOL"
        and all(c.get(field) for field in ("id", "title", "protocolId", "excerpt"))
    ]


_LABEL_STATUSES = {"CONSISTENT", "CONFLICTING", "UNKNOWN"}
_RELEVANCE_BANDS = {"HIGH", "MODERATE", "LOW", "UNKNOWN"}


def _esi_level(value: object) -> int | None:
    """A case's own recorded level, or None. Never coerced into a number."""
    try:
        level = int(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return None
    return level if 1 <= level <= 5 else None


def _case_support_dtos(raw_support: object) -> list[CaseSupportDTO]:
    """Whitelist the display-safe CASE_SUPPORT fields.

    The retrieved case's own ESI metadata is now included, because a similar
    case with no level shown at all was unreadable: a nurse could see that the
    system found something and not what it found. It is carried as the case's
    label, with its ``labelStatus`` attached, and an ``UNKNOWN`` label stays
    UNKNOWN -- it is never filled in from ``candidateEsiLevels``, which are
    competing answers rather than an agreed one. None of this reaches the ESI
    decision, which is made from the authority corpus alone.
    """
    if not isinstance(raw_support, list):
        return []
    support: list[CaseSupportDTO] = []
    for item in raw_support:
        if not isinstance(item, dict):
            continue
        retrieval_scope = str(
            item.get("retrievalScope") or item.get("retrieval_scope") or ""
        ).strip()
        authority_status = str(
            item.get("authorityStatus") or item.get("authority_status") or ""
        ).strip()
        if retrieval_scope != "CASE_SUPPORT" or authority_status != "NOT_PROTOCOL":
            continue
        case_id = str(item.get("caseId") or item.get("case_id") or "").strip()
        excerpt = str(
            item.get("excerpt") or item.get("presentation_excerpt") or ""
        ).strip()
        if not case_id or not excerpt:
            continue
        label_status = str(
            item.get("labelStatus") or item.get("label_status") or "UNKNOWN"
        ).upper()
        band = str(
            item.get("relevanceBand") or item.get("relevance_band") or "UNKNOWN"
        ).upper()
        candidates = item.get("candidateEsiLevels")
        if candidates is None:
            candidates = item.get("candidate_esi_levels")
        try:
            support.append(
                CaseSupportDTO(
                    caseId=case_id[:160],
                    excerpt=excerpt[:240],
                    similarityScore=(
                        item.get("similarityScore")
                        if item.get("similarityScore") is not None
                        else item.get("similarity_score")
                    ),
                    retrievalRelevance=(
                        item.get("retrievalRelevance")
                        if item.get("retrievalRelevance") is not None
                        else item.get("retrieval_relevance")
                    ),
                    relevanceBand=band if band in _RELEVANCE_BANDS else "UNKNOWN",
                    validatedEsiLevel=_esi_level(
                        item.get("validatedEsiLevel")
                        if item.get("validatedEsiLevel") is not None
                        else item.get("validated_esi_level")
                    ),
                    candidateEsiLevels=[
                        level
                        for level in (
                            _esi_level(entry)
                            for entry in (candidates or [])
                        )
                        if level is not None
                    ],
                    labelStatus=(
                        label_status if label_status in _LABEL_STATUSES else "UNKNOWN"
                    ),
                    ageBand=(
                        str(item.get("ageBand") or item.get("age_band") or "")[:40]
                        or None
                    ),
                    sex=str(item.get("sex") or "")[:20] or None,
                    symptomConcepts=[
                        str(concept)[:40]
                        for concept in (
                            item.get("symptomConcepts")
                            or item.get("symptom_concepts")
                            or []
                        )
                    ][:12],
                )
            )
        except ValueError:
            # One malformed similarity score must not break recovery of the
            # authoritative conversation state.
            continue
    return support


def _persisted_evidence_details(
    citations: object,
    case_support: object,
) -> list[dict[str, Any]]:
    """Use the existing citation JSON column for two explicitly tagged channels."""
    authority = [
        item.model_dump(mode="json", exclude_none=True)
        for item in _citation_dtos(citations)
    ]
    similar_cases = [
        item.model_dump(mode="json", exclude_none=True)
        for item in _case_support_dtos(case_support)
    ]
    return [*authority, *similar_cases]


def _structured_payload_dto(
    raw_payload: object,
    *,
    selected_answer: str | None = None,
) -> StructuredPayloadDTO | None:
    """Validate persisted/runtime question payloads without dropping form metadata."""
    if not isinstance(raw_payload, dict):
        return None
    payload = dict(raw_payload)
    payload["submitted"] = selected_answer is not None
    if selected_answer is not None:
        payload["selectedAnswer"] = selected_answer
    try:
        return StructuredPayloadDTO.model_validate(payload)
    except ValueError as exc:
        logger.warning("Invalid structured triage payload omitted: %s", exc)
        return None


def _persisted_question_payload(ai_result: dict[str, Any]) -> dict[str, Any] | None:
    """Keep the validated active target in the existing message JSON column."""
    structured_question = ai_result.get("structured_question")
    active_question = ai_result.get("active_question")
    if active_question:
        return build_question_recovery_payload(
            structured_question,
            active_question,
        )
    if ai_result.get("response_type") not in {"TEXT", "STRUCTURED_QUESTION"}:
        return (
            dict(structured_question)
            if isinstance(structured_question, dict)
            else None
        )
    return build_question_recovery_payload(
        structured_question,
        active_question,
    )


def _structured_option_ids(record: ChatMessage | None) -> set[str]:
    """Return option IDs from one persisted form without trusting client text."""
    if record is None or not record.structured_options:
        return set()
    raw_payload = record.structured_options[0]
    if not isinstance(raw_payload, dict):
        return set()
    raw_options = raw_payload.get("options")
    if not isinstance(raw_options, list):
        return set()
    return {
        str(option["id"])
        for option in raw_options
        if isinstance(option, dict) and option.get("id")
    }


def _build_clinical_memory(profile: EHRProfile | None) -> dict[str, object]:
    """Create one consistent EHR snapshot for every DeepAgent turn."""
    if profile is None:
        return {}
    bmi: float | None = None
    if profile.height_cm and profile.weight_kg:
        height_m = profile.height_cm / 100
        bmi = round(profile.weight_kg / (height_m * height_m), 1)
    return {
        "age": profile.age,
        "gender": profile.gender,
        "height_cm": profile.height_cm,
        "weight_kg": profile.weight_kg,
        "bmi": bmi,
        "blood_type": profile.blood_type,
        "chronic_conditions": list(profile.chronic_conditions or []),
        "daily_medications": list(profile.daily_medications or []),
        "allergies": list(profile.allergies or []),
    }


DEFAULT_TRIAGE_GREETING = (
    "Chào bạn! Cảm ơn bạn đã liên hệ. Tôi là Trợ lý AI Triage. "
    "Xin vui lòng mô tả triệu chứng khởi phát của bạn để tôi có thể hỗ trợ phân loại lâm sàng."
)


async def _greeting_for_health_topic(session: AsyncSession, health_topic: str | None) -> str:
    """Lời chào mở đầu phiên khám, có thể nhắc lại chủ đề người dùng vừa tìm hiểu.

    Chỉ đổi cách hỏi, không đổi điều được hỏi: câu mở vẫn là một câu hỏi mở về
    triệu chứng hiện tại, và câu chào nói thẳng rằng quan tâm một chủ đề không
    đồng nghĩa với mắc tình trạng đó. Tên chủ đề lấy từ bảng ``health_topics`` nên
    một slug bịa ra sẽ rơi về lời chào mặc định.
    """
    if not health_topic:
        return DEFAULT_TRIAGE_GREETING

    topic = await get_topic_by_slug(session, health_topic.strip().lower())
    if topic is None:
        return DEFAULT_TRIAGE_GREETING

    return (
        f"Chào bạn! Tôi hiểu bạn đang muốn tìm hiểu các triệu chứng liên quan đến {topic.name}. "
        "Việc quan tâm tới một chủ đề sức khỏe không có nghĩa là bạn đang mắc tình trạng đó. "
        "Hiện tại bạn có triệu chứng nào không, và bắt đầu từ khi nào?"
    )


@router.post("/start", response_model=StartTriageResponse, status_code=status.HTTP_201_CREATED)
async def start_triage_session(
    payload: StartTriageRequest,
    current_user: PatientUserDep,
    session: SessionDep,
) -> StartTriageResponse:
    """Khởi tạo một ca khám Triage mới (Tự động tiêm tiền sử từ EHR Profile vào AI Agent)."""
    # 1. Xác định Hồ sơ lâm sàng mục tiêu
    target_profile: EHRProfile | None = None
    if payload.profile_id:
        query_profile = select(EHRProfile).where(EHRProfile.id == payload.profile_id, EHRProfile.user_id == current_user.id)
        res_profile = await session.execute(query_profile)
        target_profile = res_profile.scalars().first()
        if not target_profile:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Không tìm thấy Hồ sơ gia đình tương thích.")
    else:
        # Nếu không truyền, ưu tiên dùng hồ sơ gốc (SELF)
        query_default = select(EHRProfile).where(EHRProfile.user_id == current_user.id, EHRProfile.is_primary == True)
        res_default = await session.execute(query_default)
        target_profile = res_default.scalars().first()

    # 2. Khởi tạo bản ghi TriageCase trong CSDL
    session_id = str(uuid.uuid4())
    session_title = _session_title(payload.initial_symptom)

    triage_case = TriageCase(
        id=session_id,
        patient_id=current_user.id,
        profile_id=target_profile.id if target_profile else None,
        session_title=session_title,
        status="IN_PROGRESS"
    )
    session.add(triage_case)
    await session.commit()
    await session.refresh(triage_case)

    # 3. Đóng gói ký ức lâm sàng và gọi DeepAgent runtime.
    is_red_flag = False
    ai_response_text = "Hệ thống đã tiếp nhận yêu cầu khám bệnh."

    if not payload.initial_symptom.strip():
        # User wants to start a session but hasn't provided a symptom yet (greeting flow)
        # A health_topic only personalises this greeting. It is never written to the
        # clinical state, never becomes a patient-reported fact, and never implies the
        # person has that condition - so the safety pass still starts from zero.
        ai_response_text = await _greeting_for_health_topic(session, payload.health_topic)

        
        bot_msg_record = ChatMessage(
            id=str(uuid.uuid4()),
            triage_case_id=session_id,
            sender_type="AI_AGENT",
            content=ai_response_text
        )
        session.add(bot_msg_record)
        await session.commit()
        
        return StartTriageResponse(
            session_id=session_id,
            status="IN_PROGRESS",
            message=ai_response_text,
            is_red_flag=False
        )

    # Nếu có initial_symptom, chạy luồng Triage Agent
    memory_dict: dict[str, object] = {}
    clinical_memory_updated_at = None
    if target_profile:
        memory_dict = _build_clinical_memory(target_profile)
        clinical_memory_updated_at = target_profile.updated_at.isoformat()

    initial_turn_id = str(uuid.uuid4())
    ai_state = {
        "session_id": session_id,
        "current_turn_id": initial_turn_id,
        "query": payload.initial_symptom,
        "step": 1,
        "profile_id": target_profile.id if target_profile else "",
        "patient_name": target_profile.full_name if target_profile else current_user.full_name,
        "relationship_type": target_profile.relationship_type if target_profile else "SELF",
        "patient_age": target_profile.age if target_profile else None,
        "patient_gender": target_profile.gender if target_profile else None,
        "clinical_memory": memory_dict,
        "clinical_memory_updated_at": clinical_memory_updated_at,
        "clinical_memory_confirmation_status": "NOT_REVIEWED",
        "confirmed_clinical_memory_updated_at": None,
        "clinical_context_update_pending": False,
        "clinical_memory_update_pending": False,
        "vital_signs_status": "NOT_REVIEWED",
        "patient_confirmed_intake": False,
        # A verification marker is turn-scoped. Never inherit a successful
        # gate from an earlier hot-state snapshot.
        "metadata": {"deepagent_tool_gated": False},
    }

    ai_result = await get_deepagent_runtime().run_start(
        ai_state,
        session_id=session_id,
    )
    is_red_flag = ai_result.get("is_red_flag", False)
    ai_response_text = ai_result.get("response", "Hệ thống đã tiếp nhận yêu cầu khám bệnh.")

    # 4. Lưu lại tin nhắn của Bệnh nhân và Phản hồi từ Trợ lý AI vào ChatMessage
    user_msg_record = ChatMessage(
        id=initial_turn_id,
        triage_case_id=session_id,
        sender_type="PATIENT",
        content=payload.initial_symptom
    )
    
    bot_sender = "SYSTEM_SHIELD" if is_red_flag else "AI_AGENT"
    persisted_question = _persisted_question_payload(ai_result)
    bot_msg_record = ChatMessage(
        id=str(uuid.uuid4()),
        triage_case_id=session_id,
        sender_type=bot_sender,
        content=ai_response_text,
        structured_options=[persisted_question] if persisted_question else None
    )
    
    session.add(user_msg_record)
    session.add(bot_msg_record)

    # Canonical state and the red-flag lifecycle are persisted on every turn,
    # not only on turns that reach a proposal, so facts and alerts stay
    # auditable regardless of how the turn ended.
    persist_turn_state(session, triage_case, ai_result)

    # Chỉ lưu ESI/SBAR khi kết quả đã vượt qua cổng an toàn và có proposal hoàn chỉnh.
    if _is_clinical_proposal(ai_result):
        authority_citations = _citation_dtos(ai_result.get("turn_rag_citations"))
        triage_case.status = "RED_FLAG_LOCKED" if is_red_flag else "HITL_REVIEWING"
        triage_case.is_red_flag_triggered = is_red_flag
        triage_case.ai_proposed_esi = ai_result["current_esi_level"]
        triage_case.sbar_summary = ai_result["sbar_report"]
        triage_case.rag_citations = [
            citation.protocolId for citation in authority_citations
        ]
        triage_case.rag_citation_details = _persisted_evidence_details(
            ai_result.get("turn_rag_citations"),
            ai_result.get("case_support_evidence"),
        )
        if is_red_flag:
            triage_case.red_flag_trigger_keyword = ai_result.get("red_flag_reason", "Khẩn cấp")
            triage_case.red_flag_latency_ms = ai_result.get("red_flag_latency_ms")
        session.add(triage_case)
        session.add(NurseReviewState(triage_case_id=session_id, review_status="WAITING_REVIEW"))

    await _commit_and_publish_finalized_sbar(session, triage_case, ai_result)

    return StartTriageResponse(
        session_id=session_id,
        status=triage_case.status,
        message=ai_response_text,
        is_red_flag=is_red_flag
    )


@router.post("/chat/{session_id}", status_code=status.HTTP_200_OK)
async def submit_chat_turn(
    session_id: str,
    payload: PatientChatInputDTO,
    current_user: PatientUserDep,
    session: SessionDep,
):
    """Gửi tin nhắn trả lời câu hỏi trắc nghiệm hoặc bổ sung triệu chứng trong ca Triage."""
    # 1. Kiểm tra thẩm quyền sở hữu phiên
    query_case = select(TriageCase).where(TriageCase.id == session_id, TriageCase.patient_id == current_user.id)
    res = await session.execute(query_case)
    case_doc = res.scalars().first()
    if not case_doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Phiên Triage không hợp lệ hoặc đã kết thúc.")
        
    if case_doc.status == "RED_FLAG_LOCKED":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Phiên đã bị khóa an toàn vì tình trạng khẩn cấp. Vui lòng gọi ngay tel:115!")

    if case_doc.status == "COMPLETED":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Phiên khám này đã hoàn tất. Mỗi phiên khám chỉ được thực hiện 1 lần. Vui lòng bắt đầu phiên khám mới nếu cần tư vấn thêm.")

    # 2. Xử lý câu trả lời từ người dùng
    input_text = (
        INTAKE_CONFIRMATION_TEXT
        if payload.confirm_intake
        else payload.selected_option
        if payload.selected_option
        else payload.message
    )
    if not input_text:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Bạn cần cung cấp nội dung trả lời hoặc nhấn chọn phương án.")

    selected_ehr_confirmation = False
    if payload.selected_option_id:
        latest_ai_result = await session.execute(
            select(ChatMessage)
            .where(
                ChatMessage.triage_case_id == session_id,
                ChatMessage.sender_type == "AI_AGENT",
            )
            .order_by(ChatMessage.created_at.desc())
            .limit(1)
        )
        latest_ai_message = latest_ai_result.scalars().first()
        offered_option_ids = _structured_option_ids(latest_ai_message)
        if payload.selected_option_id not in offered_option_ids:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=(
                    "Biểu mẫu này không còn là câu hỏi hiện tại. "
                    "Vui lòng trả lời biểu mẫu mới nhất."
                ),
            )
        selected_ehr_confirmation = (
            payload.selected_option_id in EHR_CONFIRMATION_OPTION_IDS
        )

    is_retrying_interrupted_confirmation = False
    if payload.confirm_intake:
        last_message_result = await session.execute(
            select(ChatMessage)
            .where(ChatMessage.triage_case_id == session_id)
            .order_by(ChatMessage.created_at.desc())
            .limit(1)
        )
        last_message = last_message_result.scalars().first()
        is_retrying_interrupted_confirmation = bool(
            last_message
            and last_message.sender_type == "PATIENT"
            and last_message.content.strip() == INTAKE_CONFIRMATION_TEXT
        )

    current_turn_id = str(uuid.uuid4())
    if not is_retrying_interrupted_confirmation:
        user_turn = ChatMessage(
            id=current_turn_id,
            triage_case_id=session_id,
            sender_type="PATIENT",
            content=str(input_text),
            selected_option=payload.selected_option
        )
        session.add(user_turn)
        await session.commit()

    # 3. Khôi phục trạng thái hiện tại và tăng bước (Dynamic Step Routing)
    triage_agent = get_deepagent_runtime()
    current_agent_state = await triage_agent.get_session_state(session_id)
    
    # Nếu agent chưa từng được gọi (trạng thái empty) -> Lần tương tác thực sự đầu tiên của User
    is_first_interaction = not current_agent_state or not current_agent_state.values

    recovered_state = None
    if is_first_interaction:
        history_result = await session.execute(
            select(ChatMessage)
            .where(ChatMessage.triage_case_id == session_id)
            .order_by(ChatMessage.created_at.asc())
        )
        recovered_state = recover_triage_state(history_result.scalars().all())
        # Prefer the persisted canonical state when the case has one. Message
        # replay stays the fallback for rows written before it existed, and it
        # cannot reconstruct provenance, temporal context or corrections.
        persisted_canonical = case_doc.canonical_state
    
    current_step = (
        recovered_state.step
        if recovered_state is not None
        else current_agent_state.values.get("step", 2)
    )
    next_step = current_step + 1

    # Luôn đọc lại hồ sơ ở mỗi lượt. Hồ sơ có thể thay đổi sau khi phiên bắt đầu,
    # nên checkpoint không được xem là nguồn EHR hiện hành.
    memory_dict: dict[str, object] = {}
    profile_info = {}
    clinical_memory_updated_at = None
    if case_doc.profile_id:
        query_profile = select(EHRProfile).where(
            EHRProfile.id == case_doc.profile_id,
            EHRProfile.user_id == current_user.id,
        )
        res_profile = await session.execute(query_profile)
        target_profile = res_profile.scalars().first()
        if target_profile:
            memory_dict = _build_clinical_memory(target_profile)
            profile_info = {
                "profile_id": target_profile.id,
                "patient_name": target_profile.full_name,
                "relationship_type": target_profile.relationship_type,
                "patient_age": target_profile.age,
                "patient_gender": target_profile.gender,
            }
            clinical_memory_updated_at = target_profile.updated_at.isoformat()

    # Durable conversation control is the baseline; hot runtime state, when the
    # process still has it, is the same data more recently written. The request
    # payload is neither -- it is one patient action, and it may only *add* to
    # this, never silently reset it.
    durable_control = (
        dict(case_doc.conversation_control)
        if isinstance(case_doc.conversation_control, dict)
        else {}
    )
    state_values = {
        **durable_control,
        **(
            current_agent_state.values
            if current_agent_state and current_agent_state.values
            else {}
        ),
    }
    turn_metadata = dict(state_values.get("metadata") or {})
    # The verifier sets this back to True only after this turn's final gate.
    turn_metadata["deepagent_tool_gated"] = False
    memory_confirmation_status = state_values.get(
        "clinical_memory_confirmation_status",
        "NOT_REVIEWED",
    )
    confirmed_memory_updated_at = state_values.get(
        "confirmed_clinical_memory_updated_at"
    )
    active_question = state_values.get("active_question")
    if active_question is None and recovered_state is not None:
        active_question = recovered_state.active_question
    if selected_ehr_confirmation:
        # The latest persisted server form is the durable authority when a
        # checkpoint was lost or came from a backend process that restarted.
        active_question = {
            "field": "clinical_memory_confirmation",
            "question_id": "clinical_memory_confirmation",
            "options_type": "single",
        }
    if (
        memory_confirmation_status in {"CONFIRMED", "UPDATED_BY_PATIENT", "UNCERTAIN"}
        and confirmed_memory_updated_at != clinical_memory_updated_at
    ):
        # EHR changed after the patient's review. Require a fresh review and never
        # silently carry the old confirmation into clinical reasoning.
        memory_confirmation_status = "NOT_REVIEWED"
        confirmed_memory_updated_at = None

    # Structured EHR controls are workflow commands, not free text for the
    # language parser to guess. Apply the server-issued option ID before the
    # graph runs so a valid click cannot re-open the same confirmation form.
    if (
        selected_ehr_confirmation
        and payload.selected_option_id in EHR_CONFIRMATION_OPTION_IDS
    ):
        (
            memory_confirmation_status,
            memory_update_pending,
            confirmed_memory_updated_at,
        ) = resolve_ehr_confirmation_choice(
            payload.selected_option_id,
            clinical_memory_updated_at=clinical_memory_updated_at,
        )
    else:
        memory_update_pending = state_values.get(
            "clinical_memory_update_pending",
            False,
        )

    ai_state = {
        "query": str(input_text),
        "selected_option_id": payload.selected_option_id,
        "current_turn_id": current_turn_id,
        "step": next_step,
        "session_id": session_id,
        "messages": (
            recovered_state.messages
            if recovered_state is not None
            else [{"role": "user", "content": str(input_text)}]
        ),
        # Confirmation is durable conversation state, not a request field.
        # Writing the payload value here unconditionally meant every ordinary
        # message after "confirm" cleared the confirmation, so the review came
        # straight back and the conversation could never leave the checkpoint.
        # The payload may raise it; only ``confirmation_lifecycle`` lowers it.
        "patient_confirmed_intake": bool(
            payload.confirm_intake or state_values.get("patient_confirmed_intake")
        ),
        "confirmed_fact_snapshot": state_values.get("confirmed_fact_snapshot") or {},
        "intake_review_shown_snapshot": state_values.get(
            "intake_review_shown_snapshot"
        )
        or {},
        "action_loop_state": state_values.get("action_loop_state") or {},
        "adaptive_questioning_complete": bool(
            state_values.get("adaptive_questioning_complete")
        ),
        "adaptive_opening_sent": bool(state_values.get("adaptive_opening_sent")),
        "intake_confirmation_prompt_count": int(
            state_values.get("intake_confirmation_prompt_count") or 0
        ),
        "clinical_memory": memory_dict,
        "clinical_memory_updated_at": clinical_memory_updated_at,
        "clinical_memory_confirmation_status": memory_confirmation_status,
        "confirmed_clinical_memory_updated_at": confirmed_memory_updated_at,
        "clinical_context_update_pending": state_values.get(
            "clinical_context_update_pending",
            False,
        ),
        "clinical_memory_update_pending": memory_update_pending,
        "vital_signs_status": state_values.get(
            "vital_signs_status",
            "NOT_REVIEWED",
        ),
        # Gửi tường minh câu hỏi đang mở thay vì chỉ trông chờ
        # checkpointer merge ngầm. Structured option phải được áp dụng
        # cho đúng câu hỏi đã sinh ra nó.
        "active_question": active_question,
        "metadata": turn_metadata,
    }

    ai_state.update(profile_info)
    if is_first_interaction:
        if not profile_info: # Fallback if no profile ID
            ai_state.update({
                "patient_name": current_user.full_name,
                "relationship_type": "SELF"
            })
        if recovered_state is not None:
            if isinstance(persisted_canonical, dict) and persisted_canonical:
                ai_state["canonical_state"] = persisted_canonical
                if isinstance(case_doc.conversation_memory, dict):
                    ai_state["conversation_memory"] = case_doc.conversation_memory
                ai_state["canonical_state_version"] = (
                    case_doc.canonical_state_version or 0
                )
            else:
                # Pre-canonical case. Replay gives us the facts but not their
                # original provenance, so they arrive marked LEGACY_RECOVERED.
                ai_state["canonical_state"] = recovered_state.canonical_state
            ai_state.update({
                "clinical_blueprint": recovered_state.clinical_blueprint,
                "active_question": recovered_state.active_question,
                "intake_summary": recovered_state.intake_summary,
                "intake_confirmation_status": (
                    "CONFIRMED"
                    if payload.confirm_intake
                    else "AWAITING_CONFIRMATION"
                    if recovered_state.awaiting_confirmation
                    else "NOT_READY"
                ),
                # The transcript already shows the review was put to this
                # patient, so a restarted backend must not open with the
                # first-time wording as though nothing had been asked. Durable
                # control, when present, is the better answer and wins.
                "intake_confirmation_prompt_count": int(
                    durable_control.get("intake_confirmation_prompt_count")
                    or (1 if recovered_state.awaiting_confirmation else 0)
                ),
            })
            if durable_control:
                # Message replay cannot reconstruct which questions were asked
                # or which targets were accepted as unknown, so a restart
                # re-asked them. The durable record can.
                ai_state.update(
                    {
                        "action_loop_state": durable_control.get(
                            "action_loop_state"
                        )
                        or {},
                        "patient_confirmed_intake": bool(
                            payload.confirm_intake
                            or durable_control.get("patient_confirmed_intake")
                        ),
                        "confirmed_fact_snapshot": durable_control.get(
                            "confirmed_fact_snapshot"
                        )
                        or {},
                        "adaptive_questioning_complete": bool(
                            durable_control.get("adaptive_questioning_complete")
                        ),
                        "adaptive_opening_sent": bool(
                            durable_control.get("adaptive_opening_sent")
                        ),
                        "vital_signs_status": durable_control.get(
                            "vital_signs_status"
                        )
                        or ai_state.get("vital_signs_status", "NOT_REVIEWED"),
                        # Durable beats replay: replay cannot rebuild a
                        # free-text adaptive question at all.
                        "active_question": durable_control.get("active_question")
                        or recovered_state.active_question,
                    }
                )
    
    async def event_generator():
        started_at = time.perf_counter()
        sequence = 0
        ai_result = None
        current_phase = "SAFETY_CHECK"
        current_intent = None
        phase_messages = {
            "redflag_detector": (
                "SAFETY_CHECK", "Đang kiểm tra an toàn",
                "Kiểm tra dấu hiệu cần cấp cứu ngay.", 5,
            ),
            "contextual_emergency_detector": (
                "SAFETY_CHECK", "Đang đánh giá ngữ cảnh khẩn cấp",
                "Kiểm tra tổ hợp dấu hiệu nghiêm trọng sau lớp phản xạ nhanh.", 10,
            ),
            "intent_classifier": (
                "INTENT_CLASSIFICATION", "Đang hiểu yêu cầu của bạn",
                "Xác định đây có phải là mô tả triệu chứng cần sàng lọc.", 15,
            ),
            "answer_validator": (
                "INTAKE_EXTRACTION", "Đang kiểm tra câu trả lời",
                "Đối chiếu với câu hỏi đang được làm rõ.", 25,
            ),
            "intake_analyzer": (
                "INTAKE_EXTRACTION", "Đang ghi nhận thông tin",
                "Trích xuất dữ kiện và lưu nguồn lượt nói.", 35,
            ),
            "contradiction_detector": (
                "INTAKE_EXTRACTION", "Đang kiểm tra tính nhất quán",
                "Phát hiện thông tin cần bạn xác nhận lại.", 45,
            ),
            "readiness_evaluator": (
                "INTAKE_EXTRACTION", "Đang kiểm tra độ đầy đủ",
                "Xác định dữ kiện quan trọng còn thiếu theo nhóm triệu chứng.", 55,
            ),
            "action_planner": (
                "INTAKE_EXTRACTION", "Đang chọn bước phù hợp",
                "Chọn một hành động được phép từ dữ kiện hiện có.", 60,
            ),
            "action_execution": (
                "INTAKE_EXTRACTION", "Đang thực hiện bước tiếp theo",
                "Thực thi hành động đã qua cổng an toàn.", 62,
            ),
            "question_engine": (
                "CLARIFICATION", "Đang chuẩn bị câu hỏi tiếp theo",
                "Chọn một câu hỏi làm rõ có giá trị cao nhất.", 65,
            ),
            "evidence_question_execution": (
                "CLARIFICATION", "Đang chuẩn bị câu hỏi bổ sung",
                "Bằng chứng cho thấy cần thêm một dữ kiện cụ thể.", 92,
            ),
            "patient_confirmation": (
                "PATIENT_CONFIRMATION", "Đang chuẩn bị bản tóm tắt",
                "Cho phép bạn kiểm tra dữ kiện trước khi đối chiếu phác đồ.", 68,
            ),
            "bilingual_query_builder": (
                "RETRIEVAL", "Đang chuẩn hóa truy vấn",
                "Tạo riêng kênh tiếng Việt, tiếng Anh và từ khóa kiểm soát.", 72,
            ),
            "profile_context_enricher": (
                "RETRIEVAL", "Đang kiểm tra phạm vi phác đồ",
                "Dùng bối cảnh hồ sơ đã xác nhận để giới hạn tìm kiếm.", 70,
            ),
            "retrieve_evidence": (
                "RETRIEVAL", "Đang tìm bằng chứng",
                "Chỉ tìm phác đồ đã duyệt và đúng phạm vi lâm sàng.", 80,
            ),
            "refine_evidence": (
                "RETRIEVAL", "Đang tinh chỉnh tìm kiếm",
                "Thử một truy vấn giới hạn khác để tìm bằng chứng mới.", 84,
            ),
            "triage_reasoner": (
                "REASONING", "Đang đối chiếu tiêu chí",
                "Kiểm tra dữ kiện với tiêu chí có citation truy vết được.", 90,
            ),
            "triage_reasoner_after_refinement": (
                "REASONING", "Đang đánh giá bằng chứng bổ sung",
                "Đối chiếu lại tiêu chí sau lần tìm kiếm giới hạn.", 91,
            ),
            "insufficient_evidence_responder": (
                "HANDOFF", "Đang chuẩn bị chuyển thẩm định",
                "Không tạo ESI khi bằng chứng đã duyệt chưa đủ.", 94,
            ),
            "summary_creator": (
                "HANDOFF", "Đang chuẩn bị bàn giao",
                "Tạo hồ sơ để điều dưỡng thẩm định.", 96,
            ),
        }

        yield _dump_sse_event(AgentStreamEventDTO(
            type="accepted",
            message="Đã nhận thông tin của bạn",
            sequence=sequence,
            elapsedMs=0,
            phase="SAFETY_CHECK",
            label="Đã nhận thông tin",
            detail="Hệ thống bắt đầu kiểm tra an toàn.",
            progress=0,
        ))

        event_iterator = triage_agent.stream_turn(
            ai_state,
            session_id=session_id,
        ).__aiter__()
        pending_event: asyncio.Task | None = asyncio.create_task(anext(event_iterator))
        try:
            while pending_event is not None:
                done, _ = await asyncio.wait({pending_event}, timeout=2.0)
                elapsed_ms = int((time.perf_counter() - started_at) * 1000)
                if not done:
                    sequence += 1
                    yield _dump_sse_event(AgentStreamEventDTO(
                        type="heartbeat",
                        message="Hệ thống vẫn đang xử lý an toàn",
                        sequence=sequence,
                        elapsedMs=elapsed_ms,
                        phase=current_phase,
                        intent=current_intent,
                        label="Hệ thống vẫn đang xử lý",
                        detail="Các hàng rào an toàn vẫn đang hoạt động.",
                    ))
                    continue

                try:
                    event = pending_event.result()
                except StopAsyncIteration:
                    pending_event = None
                    break
                pending_event = asyncio.create_task(anext(event_iterator))

                kind = event.get("event")
                node_name = event.get("name")
                if kind == "on_chain_start" and node_name in phase_messages:
                    phase, label, detail, progress = phase_messages[node_name]
                    current_phase = phase
                    _log_agent_metric(
                        "phase_started",
                        phase=phase,
                        elapsed_ms=elapsed_ms,
                    )
                    sequence += 1
                    yield _dump_sse_event(AgentStreamEventDTO(
                        type="progress",
                        message=label,
                        sequence=sequence,
                        elapsedMs=elapsed_ms,
                        phase=phase,
                        intent=current_intent,
                        label=label,
                        detail=detail,
                        progress=progress,
                    ))
                elif kind == "on_chain_end" and node_name == "intent_classifier":
                    output = event.get("data", {}).get("output", {})
                    if isinstance(output, dict) and output.get("intent"):
                        current_intent = output["intent"]
                        sequence += 1
                        yield _dump_sse_event(AgentStreamEventDTO(
                            type="intent",
                            message="Đã xác định hướng hỗ trợ phù hợp",
                            sequence=sequence,
                            elapsedMs=elapsed_ms,
                            phase="INTENT_CLASSIFICATION",
                            intent=output["intent"],
                            label="Đã xác định hướng hỗ trợ",
                            detail="Luồng xử lý tiếp theo đã được chọn.",
                            progress=20,
                        ))
                elif kind == "on_chain_end" and node_name == "DeepAgentSupervisor":
                    ai_result = event.get("data", {}).get("output")
        except Exception as exc:
            logger.exception("Triage agent stream failed")
            _log_agent_metric(
                "agent_error",
                phase=current_phase,
                error_type=type(exc).__name__,
                elapsed_ms=int((time.perf_counter() - started_at) * 1000),
            )
            sequence += 1
            yield _dump_sse_event(AgentStreamEventDTO(
                type="error",
                message="Không thể hoàn tất xử lý lúc này. Vui lòng thử lại.",
                sequence=sequence,
                elapsedMs=int((time.perf_counter() - started_at) * 1000),
                phase=current_phase,
                intent=current_intent,
                label="Xử lý bị gián đoạn",
                detail="Không có kết quả lâm sàng nào được lưu từ lượt lỗi này.",
                retryable=True,
                errorCode="AGENT_EXECUTION_FAILED",
            ))
            return
        finally:
            if pending_event is not None and not pending_event.done():
                pending_event.cancel()

        if not isinstance(ai_result, dict):
            _log_agent_metric(
                "invalid_agent_result",
                phase=current_phase,
                elapsed_ms=int((time.perf_counter() - started_at) * 1000),
            )
            sequence += 1
            yield _dump_sse_event(AgentStreamEventDTO(
                type="error",
                message="Không thể hoàn tất xử lý lúc này. Vui lòng thử lại.",
                sequence=sequence,
                elapsedMs=int((time.perf_counter() - started_at) * 1000),
                phase=current_phase,
                intent=current_intent,
                label="Không nhận được kết quả hợp lệ",
                detail="Không có đề xuất ESI nào được tạo.",
                retryable=True,
                errorCode="INVALID_AGENT_RESULT",
            ))
            return

        if not case_doc.session_title or case_doc.session_title == "Triage Consultation":
            extracted_title = _session_title_from_agent_result(ai_result)
            if extracted_title:
                case_doc.session_title = extracted_title

        ai_msg_text = ai_result.get("response") or "Hệ thống đã ghi nhận thông tin."
        citations_data = ai_result.get("turn_rag_citations", [])
        case_support_data = ai_result.get("case_support_evidence", [])
        esi_level = ai_result.get("current_esi_level")
        sbar_report = ai_result.get("sbar_report")
        structured_question = ai_result.get("structured_question")
        persisted_question = _persisted_question_payload(ai_result)
        intake_summary = ai_result.get("intake_summary")
        is_red_flag = ai_result.get("decision_status") == "EMERGENCY_ESCALATED"

        bot_turn_id = str(uuid.uuid4())
        session.add(ChatMessage(
            id=bot_turn_id,
            triage_case_id=session_id,
            sender_type="SYSTEM_SHIELD" if is_red_flag else "AI_AGENT",
            content=ai_msg_text,
            structured_options=[persisted_question] if persisted_question else None,
        ))

        persist_turn_state(session, case_doc, ai_result)

        is_clinical_proposal = _is_clinical_proposal(ai_result)
        if _requires_nurse_review(ai_result):
            case_doc.status = "RED_FLAG_LOCKED" if is_red_flag else "HITL_REVIEWING"
            case_doc.is_red_flag_triggered = is_red_flag
            if is_clinical_proposal:
                authority_citations = _citation_dtos(citations_data)
                case_doc.ai_proposed_esi = esi_level
                case_doc.sbar_summary = sbar_report
                case_doc.rag_citations = [
                    citation.protocolId for citation in authority_citations
                ]
                case_doc.rag_citation_details = _persisted_evidence_details(
                    citations_data,
                    case_support_data,
                )
            else:
                case_doc.ai_proposed_esi = None
                case_doc.sbar_summary = None
                case_doc.rag_citations = []
                case_doc.rag_citation_details = []
            if is_red_flag:
                case_doc.red_flag_trigger_keyword = ai_result.get("red_flag_reason", "Khẩn cấp")
                case_doc.red_flag_latency_ms = ai_result.get("red_flag_latency_ms")
            review_result = await session.execute(
                select(NurseReviewState).where(NurseReviewState.triage_case_id == session_id)
            )
            if review_result.scalars().first() is None:
                session.add(NurseReviewState(
                    triage_case_id=session_id,
                    review_status="WAITING_REVIEW",
                ))
        session.add(case_doc)
        await _commit_and_publish_finalized_sbar(session, case_doc, ai_result)

        dto_citations = _citation_dtos(citations_data)
        dto_case_support = _case_support_dtos(case_support_data)

        struct_payload = _structured_payload_dto(structured_question)

        final_dto = PatientChatMessageDTO(
            id=bot_turn_id,
            sender="system_shield" if is_red_flag else "bot",
            timestamp=datetime.now(UTC).isoformat(),
            content=ai_msg_text,
            step=ai_result.get("step", next_step),
            structured=struct_payload,
            ragCitations=dto_citations or None,
            caseSupport=dto_case_support,
            intent=ai_result.get("intent"),
            responseType=ai_result.get("response_type"),
            decisionStatus=ai_result.get("decision_status"),
            workflowPhase=ai_result.get("workflow_phase", "COMPLETE"),
            esiLevel=esi_level,
            evidenceStatus=ai_result.get("evidence_status"),
            retrievalDegradedModes=ai_result.get("retrieval_degraded_modes", []),
            intakeSummary=intake_summary if isinstance(intake_summary, dict) else None,
            requiresPatientConfirmation=(
                ai_result.get("decision_status") == "AWAITING_PATIENT_CONFIRMATION"
            ),
            sbarFinalized=is_clinical_proposal,
        )
        sequence += 1
        _log_agent_metric(
            "turn_completed",
            intent=ai_result.get("intent"),
            decision_status=ai_result.get("decision_status"),
            evidence_status=ai_result.get("evidence_status"),
            retrieval_result_count=len(ai_result.get("retrieved_evidence", [])),
            retrieval_degraded_mode_count=len(
                ai_result.get("retrieval_degraded_modes", [])
            ),
            elapsed_ms=int((time.perf_counter() - started_at) * 1000),
        )
        yield _dump_sse_event(AgentStreamEventDTO(
            type="result",
            message="Đã hoàn tất lượt xử lý",
            sequence=sequence,
            elapsedMs=int((time.perf_counter() - started_at) * 1000),
            phase=ai_result.get("workflow_phase", "COMPLETE"),
            intent=ai_result.get("intent"),
            result=final_dto,
            label="Đã hoàn tất lượt xử lý",
            detail="Kết quả hiển thị không bao gồm suy luận nội bộ của mô hình.",
            progress=100,
        ))

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.get("/chat/{session_id}/messages", response_model=SessionMessagesResponse, status_code=status.HTTP_200_OK)
async def get_session_messages(
    session_id: str,
    current_user: PatientUserDep,
    session: SessionDep,
) -> SessionMessagesResponse:
    """Lấy trạng thái phiên khám + danh sách trọn bộ tin nhắn để phục hồi UI."""
    # Lấy thông tin phiên
    query_case = select(TriageCase).where(TriageCase.id == session_id, TriageCase.patient_id == current_user.id)
    res_case = await session.execute(query_case)
    triage_case = res_case.scalars().first()
    if not triage_case:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Phiên Triage không tồn tại hoặc không thuộc quyền sở hữu của bạn.")

    nurse_review, reviewer_name = await _nurse_decision_context(session, triage_case.id)
    hitl_status = _patient_hitl_status(triage_case, nurse_review)

    query_msg = (
        select(ChatMessage)
        .where(ChatMessage.triage_case_id == session_id)
        .order_by(ChatMessage.created_at.asc())
    )
    res = await session.execute(query_msg)
    all_records = list(res.scalars().all())
    # Kênh trao đổi với nhân viên y tế có màn hình riêng; giữ nó ở đây sẽ vừa
    # lặp nội dung vừa làm bộ phục hồi phiên tưởng đó là câu trả lời hỏi bệnh.
    records = [
        record for record in all_records if record.channel != CARE_TEAM_CHANNEL
    ]
    unread_from_staff = sum(
        1
        for record in all_records
        if record.sender_type == "NURSE" and record.read_at is None
    )

    intake_confirmation_status = "NOT_READY"
    intake_summary = None
    workflow_phase = None
    state_values: dict[str, Any] = {}
    try:
        runtime_state = await get_deepagent_runtime().get_session_state(session_id)
        raw_state_values = runtime_state.values if runtime_state else {}
        state_values = raw_state_values if isinstance(raw_state_values, dict) else {}
        intake_confirmation_status = state_values.get(
            "intake_confirmation_status",
            "NOT_READY",
        )
        state_summary = state_values.get("intake_summary")
        intake_summary = state_summary if isinstance(state_summary, dict) else None
        workflow_phase = _safe_enum(
            state_values.get("workflow_phase"),
            _PUBLIC_WORKFLOW_PHASES,
        )
    except Exception as exc:
        logger.warning(
            "Could not read hot triage session state: %s",
            type(exc).__name__,
        )

    hot_decision_status = _safe_enum(
        state_values.get("decision_status"),
        _PUBLIC_DECISION_STATUSES,
    )
    hot_evidence_status = _safe_enum(
        state_values.get("evidence_status"),
        _PUBLIC_EVIDENCE_STATUSES,
    )
    hot_degraded_modes = _safe_degraded_modes(
        state_values.get("retrieval_degraded_modes")
    )
    hot_case_support = _case_support_dtos(
        state_values.get("case_support_evidence")
    )

    recovered_state = recover_triage_state(records)
    if (
        triage_case.status == "IN_PROGRESS"
        and recovered_state.awaiting_confirmation
        and (
            intake_confirmation_status != "AWAITING_CONFIRMATION"
            or intake_summary is None
        )
    ):
        intake_confirmation_status = "AWAITING_CONFIRMATION"
        intake_summary = recovered_state.intake_summary
        workflow_phase = "PATIENT_CONFIRMATION"

    dtos: list[PatientChatMessageDTO] = []
    replay_citations = _citation_dtos(triage_case.rag_citation_details)
    replay_case_support = _case_support_dtos(triage_case.rag_citation_details)
    finalized_sbar = _finalized_sbar_dto(triage_case)
    sbar_finalized = finalized_sbar is not None
    session_decision_status = (
        "EMERGENCY_ESCALATED"
        if sbar_finalized and triage_case.is_red_flag_triggered
        else "PROPOSED"
        if sbar_finalized
        else hot_decision_status
    )
    session_evidence_status = (
        "NOT_REQUESTED"
        if sbar_finalized and triage_case.is_red_flag_triggered
        else "SUFFICIENT"
        if sbar_finalized
        else hot_evidence_status
    )
    session_workflow_phase = (
        "COMPLETE"
        if sbar_finalized and triage_case.status == "COMPLETED"
        else "HANDOFF"
        if sbar_finalized
        else workflow_phase
    )
    last_agent_index = max(
        (
            index
            for index, record in enumerate(records)
            if record.sender_type in {"AI_AGENT", "SYSTEM_SHIELD"}
        ),
        default=-1,
    )
    for idx, r in enumerate(records):
        sender_val = (
            "user"
            if r.sender_type == "PATIENT"
            else "system_shield"
            if r.sender_type == "SYSTEM_SHIELD"
            else "nurse"
            if r.sender_type == "NURSE"
            else "bot"
        )
        # Tin của nhân viên lâm sàng là lời một con người, không mang theo bất kỳ
        # kết luận nào của mô hình, nên không được gắn ESI/trích dẫn/SBAR vào.
        is_staff_message = sender_val == "nurse"
        struct_payload = None
        selected_answer = r.selected_option
        if (
            selected_answer is None
            and idx + 1 < len(records)
            and records[idx + 1].sender_type == "PATIENT"
        ):
            selected_answer = records[idx + 1].selected_option
        if r.structured_options and len(r.structured_options) > 0:
            struct_payload = _structured_payload_dto(
                r.structured_options[0],
                selected_answer=selected_answer,
            )
        is_intake_review = (
            recovered_state.awaiting_confirmation
            and idx == len(records) - 1
            and r.sender_type == "AI_AGENT"
        )
        is_last_agent = idx == last_agent_index and not is_staff_message
        is_emergency_result = bool(
            is_last_agent
            and sbar_finalized
            and triage_case.is_red_flag_triggered
        )
        is_grounded_proposal = bool(
            is_last_agent
            and sbar_finalized
            and replay_citations
            and not triage_case.is_red_flag_triggered
            and triage_case.ai_proposed_esi in {1, 2, 3, 4, 5}
        )
        dtos.append(PatientChatMessageDTO(
            id=r.id,
            sender=sender_val,
            senderName=r.sender_display_name if is_staff_message else None,
            timestamp=r.created_at.isoformat() + "Z",
            content=r.content,
            step=3 if is_intake_review else 2 if struct_payload else 1,
            structured=struct_payload,
            ragCitations=replay_citations if is_grounded_proposal else None,
            caseSupport=(
                (replay_case_support or hot_case_support)
                if is_grounded_proposal
                else []
            ),
            responseType=(
                "EMERGENCY"
                if is_emergency_result
                else "TRIAGE_PROPOSAL"
                if is_grounded_proposal
                else "INTAKE_REVIEW"
                if is_intake_review
                else "TEXT"
                if struct_payload and struct_payload.optionsType == "text_only"
                else "STRUCTURED_QUESTION"
                if struct_payload
                else None
            ),
            decisionStatus=(
                "EMERGENCY_ESCALATED"
                if is_emergency_result
                else "PROPOSED"
                if is_grounded_proposal
                else "AWAITING_PATIENT_CONFIRMATION"
                if is_intake_review
                else hot_decision_status
                if is_last_agent
                else None
            ),
            workflowPhase=(
                "HANDOFF"
                if is_grounded_proposal or is_emergency_result
                else "PATIENT_CONFIRMATION"
                if is_intake_review
                else workflow_phase
                if is_last_agent
                else None
            ),
            esiLevel=(
                triage_case.ai_proposed_esi
                if is_grounded_proposal or is_emergency_result
                else None
            ),
            evidenceStatus=(
                "SUFFICIENT"
                if is_grounded_proposal
                else "NOT_REQUESTED"
                if is_emergency_result
                else hot_evidence_status
                if is_last_agent
                else None
            ),
            retrievalDegradedModes=(
                hot_degraded_modes if is_last_agent else []
            ),
            intakeSummary=intake_summary if is_intake_review else None,
            requiresPatientConfirmation=is_intake_review,
            sbarFinalized=(
                sbar_finalized and (is_grounded_proposal or is_emergency_result)
            ),
        ))
    care_team_name, care_team_status = await _care_team_view(session, triage_case)
    return SessionMessagesResponse(
        session_status=SessionStatusDTO(
            session_id=triage_case.id,
            status=triage_case.status,
            profile_id=triage_case.profile_id,
            ai_proposed_esi=triage_case.ai_proposed_esi,
            final_esi=_visible_case_esi(triage_case),
            hitl_status=hitl_status,
            reviewer_name=reviewer_name,
            reviewed_at=(
                f'{(nurse_review.decided_at or nurse_review.handed_off_at).isoformat()}Z'
                if nurse_review and (nurse_review.decided_at or nurse_review.handed_off_at)
                else f"{triage_case.reviewed_at.isoformat()}Z" if triage_case.reviewed_at else None
            ),
            decision_type=nurse_review.decision_type if nurse_review else None,
            decision_note=nurse_review.decision_note if nurse_review else None,
            is_red_flag_triggered=triage_case.is_red_flag_triggered,
            created_at=triage_case.created_at.isoformat() + "Z",
            updated_at=triage_case.updated_at.isoformat() + "Z" if triage_case.updated_at else None,
            sbar_summary=(triage_case.sbar_summary if sbar_finalized else None),
            sbar_finalized=sbar_finalized,
            decision_status=session_decision_status,
            evidence_status=session_evidence_status,
            retrieval_degraded_modes=hot_degraded_modes,
            intake_confirmation_status=intake_confirmation_status,
            intake_summary=intake_summary,
            care_team_name=care_team_name,
            care_team_status=care_team_status,
            unread_from_staff=unread_from_staff,
            workflow_phase=session_workflow_phase,
        ),
        messages=dtos
    )


# =====================================================================
# MODULE TRA CỨU LỊCH SỬ & REPLAY CHỈ ĐỌC (UI GROUP 4 - SCR-HIST-01 & 02)
# =====================================================================
@router.get("/history", response_model=HistoryListResponse, status_code=status.HTTP_200_OK)
async def get_patient_history(
    current_user: PatientUserDep,
    session: SessionDep,
) -> HistoryListResponse:
    """Tra cứu danh sách lịch sử các phiên Triage trong quá khứ của người dùng."""
    query_history = (
        select(TriageCase, EHRProfile)
        .outerjoin(EHRProfile, TriageCase.profile_id == EHRProfile.id)
        .where(TriageCase.patient_id == current_user.id)
        .order_by(TriageCase.created_at.desc())
    )
    res = await session.execute(query_history)
    cases_with_profiles = res.all()

    # Để tối ưu, ta thực hiện một query gộp đếm số lượng tin chưa đọc cho TẤT CẢ các ca của bệnh nhân này
    unread_subq = await session.execute(
        select(ChatMessage.triage_case_id, func.count(ChatMessage.id))
        .where(
            ChatMessage.sender_type == "NURSE",
            ChatMessage.read_at.is_(None)
        )
        .group_by(ChatMessage.triage_case_id)
    )
    unread_counts = {case_id: count for case_id, count in unread_subq.all()}

    items: list[TriageHistoryListItemDTO] = []
    for c, p in cases_with_profiles:
        esi = _visible_case_esi(c)
        sbar_doc = _finalized_sbar_dto(c)
        sbar_finalized = sbar_doc is not None
        hitl = "APPROVED" if c.status == "COMPLETED" and not c.is_overridden else "OVERRIDDEN" if c.is_overridden else "EMERGENCY_REJECTED" if c.status == "RED_FLAG_LOCKED" else "PENDING_REVIEW"
        snippet = sbar_doc.situation[:80] if sbar_doc is not None else ""

        profile_name = p.full_name if p else "Khám Nhanh"
        relationship_type = p.relationship_type if p else "GUEST"
        
        unread_count = unread_counts.get(c.id, 0)

        items.append(TriageHistoryListItemDTO(
            session_id=c.id,
            status=c.status,
            profile_name=profile_name,
            relationship_type=relationship_type,
            chief_complaint=c.session_title,
            created_at=c.created_at.isoformat() + "Z",
            final_esi=esi,
            hitl_status=hitl,
            sbar_snippet=snippet,
            sbar_finalized=sbar_finalized,
            unread_from_staff=unread_count,
        ))

    return HistoryListResponse(items=items)


@router.get("/history/{session_id}", response_model=TriageSessionDetailDTO, status_code=status.HTTP_200_OK)
async def get_session_replay_detail(
    session_id: str,
    current_user: PatientUserDep,
    session: SessionDep,
) -> TriageSessionDetailDTO:
    """Tra cứu chi tiết một ca bệnh quá khứ phục vụ Read-Only Replay, toàn văn SBAR và Chữ ký thẩm định."""
    query_case = (
        select(TriageCase, EHRProfile)
        .outerjoin(EHRProfile, TriageCase.profile_id == EHRProfile.id)
        .where(TriageCase.id == session_id, TriageCase.patient_id == current_user.id)
    )
    res = await session.execute(query_case)
    row = res.first()
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Không tìm thấy lịch sử ca Triage.")
    c, p = row

    # Lấy chuỗi hội thoại
    messages = await get_session_messages(session_id, current_user, session)
    
    esi = _visible_case_esi(c)
    hitl_status = messages.session_status.hitl_status

    # Không dựng placeholder mang hình dáng SBAR cho ca chưa finalized.
    sbar_doc = _finalized_sbar_dto(c)
    sbar_finalized = sbar_doc is not None

    # Chữ ký Bác sĩ thẩm định (nếu đã xong)
    sig_doc = None
    if (
        messages.session_status.reviewed_at
        and messages.session_status.decision_type in {"CONFIRM_ESI", "ADJUST_ESI"}
        and c.ai_proposed_esi is not None
        and c.final_clinical_esi is not None
    ):
        sig_doc = HitlSignatureDTO(
            reviewer_name=messages.session_status.reviewer_name,
            review_timestamp=messages.session_status.reviewed_at,
            status=hitl_status,
            original_esi=c.ai_proposed_esi,
            final_esi=c.final_clinical_esi,
            justification_note=messages.session_status.decision_note,
        )

    profile_name = p.full_name if p else "Khám Nhanh"
    relationship_type = p.relationship_type if p else "GUEST"

    return TriageSessionDetailDTO(
        session_id=c.id,
        status=c.status,
        profile_name=profile_name,
        relationship_type=relationship_type,
        chief_complaint=c.session_title,
        created_at=c.created_at.isoformat() + "Z",
        final_esi=esi,
        hitl_status=hitl_status,
        sbar_snippet=(sbar_doc.situation[:60] + "...") if sbar_doc else "",
        sbar_finalized=sbar_finalized,
        messages=messages.messages,
        sbar_report=sbar_doc,
        hitl_signature=sig_doc
    )


async def _publish_clinical(topic: str, event: str, payload: dict[str, Any]) -> None:
    """Đánh thức giao diện phía kia. Bản ghi đã commit mới là nguồn sự thật."""
    try:
        await get_event_bus().publish(topic, event, payload)
    except Exception:  # noqa: BLE001 - realtime hỏng không được làm hỏng ca bệnh
        logger.warning("Không phát được sự kiện realtime %s", event)


# =====================================================================
# KÊNH NHẮN TIN GIỮA NGƯỜI BỆNH VÀ NHÂN VIÊN LÂM SÀNG ĐANG PHỤ TRÁCH
# =====================================================================
# Kênh này cố ý tách khỏi endpoint hội thoại với AI: ở đây không có mô hình nào
# chạy, không suy luận ESI, không sinh SBAR. Đó chỉ là hai con người nhắn cho
# nhau bên trong một ca đã được nhân viên y tế tiếp nhận.


async def _care_team_view(
    session: AsyncSession,
    case: TriageCase,
) -> tuple[str | None, str]:
    """Diễn đạt trạng thái ca theo ngôn ngữ người bệnh hiểu được.

    Trả về (tên nhân viên đang phụ trách, trạng thái). Không lộ vai trò nội bộ
    hay mã trạng thái kỹ thuật của hàng đợi.
    """
    if case.status == "COMPLETED":
        return None, "COMPLETED"

    # ``assigned_nurse_id`` trên chính bản ghi ca được giữ đồng bộ ở mọi bước
    # nhận/trả/chuyển ca, nên đọc nó rẻ hơn một vòng truy vấn bảng rà soát.
    if case.assigned_nurse_id:
        staff = await session.execute(
            select(User).where(User.id == case.assigned_nurse_id)
        )
        assignee = staff.scalars().first()
        return (assignee.full_name if assignee else None), "STAFF_REVIEWING"

    if case.status not in {"HITL_REVIEWING", "RED_FLAG_LOCKED"}:
        return None, "AI_SCREENING"

    # Chỉ lúc này mới cần phân biệt "đang chờ người nhận" với "đã chuyển đánh
    # giá chuyên sâu" - hai tình huống mà người bệnh nhìn thấy khác hẳn nhau.
    result = await session.execute(
        select(NurseReviewState).where(NurseReviewState.triage_case_id == case.id)
    )
    review = result.scalars().first()
    if review is not None and review.review_status == "SPECIALIST_REVIEW_REQUIRED":
        return None, "SPECIALIST_REVIEW"
    return None, "WAITING_REVIEW"


async def _owned_case_or_404(
    session: AsyncSession,
    session_id: str,
    current_user: User,
) -> TriageCase:
    """Chỉ chủ sở hữu ca mới thao tác được; ID do client gửi không được tin."""
    result = await session.execute(
        select(TriageCase).where(
            TriageCase.id == session_id,
            TriageCase.patient_id == current_user.id,
        )
    )
    case = result.scalars().first()
    if case is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Không tìm thấy phiên khám này trong tài khoản của bạn.",
        )
    return case


@router.post(
    "/chat/{session_id}/message-to-staff",
    response_model=StaffConversationResponse,
    status_code=status.HTTP_201_CREATED,
)
async def send_message_to_staff(
    session_id: str,
    payload: SendStaffMessageRequestDTO,
    current_user: PatientUserDep,
    session: SessionDep,
) -> StaffConversationResponse:
    """Người bệnh nhắn cho đội ngũ lâm sàng của ca mình.

    Tin gửi được ngay cả khi chưa ai nhận ca: nó vào thẳng hộp thư của trạm trực.
    Bản trước chặn ở đây cho tới lúc có người nhận ca, và vì việc nhận ca lại xảy
    ra bằng cách mở hồ sơ, hệ quả là không một tin nào của người bệnh tới được
    trạm trực trước khi có người chủ động mở hồ sơ ra — đúng thứ tự ngược với mô
    hình HITL, và nguy hiểm khi người bệnh đang trở nặng.
    """
    case = await _owned_case_or_404(session, session_id, current_user)
    if case.status in CLOSED_CASE_STATUSES:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Phiên khám này đã kết thúc. Hãy mở một phiên khám mới nếu bạn cần hỗ trợ tiếp.",
        )

    if payload.clientMessageId:
        existing = await session.execute(
            select(ChatMessage).where(
                ChatMessage.triage_case_id == session_id,
                ChatMessage.client_message_id == payload.clientMessageId,
            )
        )
        if existing.scalars().first() is not None:
            return await _staff_conversation(session, case, current_user)

    record = ChatMessage(
        triage_case_id=session_id,
        sender_type="PATIENT",
        content=payload.content,
        sender_id=current_user.id,
        sender_display_name=current_user.full_name,
        client_message_id=payload.clientMessageId,
        channel=CARE_TEAM_CHANNEL,
    )
    session.add(record)
    await session.commit()

    # Payload tối thiểu: đủ để trạm trực biết có việc và mở đúng ca, không mang
    # theo dữ liệu lâm sàng. Nội dung đầy đủ chỉ tải được qua API có kiểm quyền.
    signal = {
        "case_id": session_id,
        "message_id": record.id,
        "sender": "PATIENT",
        "priority": case_message_priority(case),
        "created_at": record.created_at.isoformat(),
    }
    # Trạm trực nhận ngay dù chưa ai mở hồ sơ; ai đang mở đúng ca thì thấy tin luôn.
    await _publish_clinical(case_topic(session_id), EVENT_MESSAGE_CREATED, signal)
    await _publish_clinical(STAFF_QUEUE_TOPIC, EVENT_MESSAGE_CREATED, signal)

    return await _staff_conversation(session, case, current_user)


@router.post(
    "/chat/{session_id}/mark-staff-read",
    response_model=StaffConversationResponse,
)
async def mark_staff_messages_read(
    session_id: str,
    current_user: PatientUserDep,
    session: SessionDep,
) -> StaffConversationResponse:
    """Đánh dấu các tin của nhân viên lâm sàng là người bệnh đã đọc."""
    case = await _owned_case_or_404(session, session_id, current_user)
    result = await session.execute(
        select(ChatMessage).where(
            ChatMessage.triage_case_id == session_id,
            ChatMessage.sender_type == "NURSE",
            ChatMessage.read_at.is_(None),
        )
    )
    # get_utc_now() trả về UTC offset-naive, đúng kiểu cột TIMESTAMP của asyncpg.
    # Dùng datetime.now(UTC) ở đây sẽ ném DataError ngay lúc ghi.
    now = get_utc_now()
    changed = 0
    for message in result.scalars().all():
        message.read_at = now
        changed += 1
    await session.commit()

    if changed:
        await _publish_clinical(
            case_topic(session_id),
            EVENT_MESSAGE_READ,
            {"case_id": session_id, "read_by": "PATIENT", "count": changed},
        )
    return await _staff_conversation(session, case, current_user)


async def _staff_conversation(
    session: AsyncSession,
    case: TriageCase,
    current_user: User,
) -> StaffConversationResponse:
    """Trạng thái đội ngũ chăm sóc kèm số tin người bệnh chưa đọc."""
    care_team_name, care_team_status = await _care_team_view(session, case)
    return StaffConversationResponse(
        session_id=case.id,
        care_team_name=care_team_name,
        care_team_status=care_team_status,
        unread_from_staff=await _unread_from_staff(session, case.id),
    )


async def _unread_from_staff(session: AsyncSession, session_id: str) -> int:
    """Số tin nhân viên y tế đã gửi mà người bệnh chưa đọc."""
    result = await session.execute(
        select(ChatMessage).where(
            ChatMessage.triage_case_id == session_id,
            ChatMessage.sender_type == "NURSE",
            ChatMessage.read_at.is_(None),
        )
    )
    return len(list(result.scalars().all()))


@router.get("/chat/{session_id}/care-team", response_model=CareTeamThreadResponse)
async def get_care_team_thread(
    session_id: str,
    current_user: PatientUserDep,
    session: SessionDep,
) -> CareTeamThreadResponse:
    """Luồng trao đổi giữa người bệnh và nhân viên y tế của một ca.

    Tách khỏi hội thoại hỏi bệnh của AI: đây là nơi người bệnh nói chuyện với
    một con người, nên nội dung không đi qua bất kỳ lớp sinh văn bản nào và
    không mang theo ESI, trích dẫn hay SBAR.
    """
    case = await _owned_case_or_404(session, session_id, current_user)
    care_team_name, care_team_status = await _care_team_view(session, case)

    result = await session.execute(
        select(ChatMessage)
        .where(
            ChatMessage.triage_case_id == session_id,
            ChatMessage.channel == CARE_TEAM_CHANNEL,
        )
        .order_by(ChatMessage.created_at.asc())
    )
    messages = [
        CareTeamMessageDTO(
            id=record.id,
            sender="staff" if record.sender_type == "NURSE" else "patient",
            senderName=record.sender_display_name,
            content=record.content,
            createdAt=record.created_at.isoformat() + "Z",
            readAt=(record.read_at.isoformat() + "Z") if record.read_at else None,
        )
        for record in result.scalars().all()
    ]

    return CareTeamThreadResponse(
        session_id=session_id,
        care_team_name=care_team_name,
        care_team_status=care_team_status,
        unread_from_staff=sum(
            1 for message in messages if message.sender == "staff" and message.readAt is None
        ),
        messages=messages,
    )
