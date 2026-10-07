"""Nurse/HITL review pilot routes for `src.simple_agent` sessions.

Deliberately parallel to `src/api/routes_nurse.py`, not an extension of it:
this router reads/writes only the new `SimpleAgentNurseReview` table (see
`src/models/db_models.py`) plus the existing `SimpleAgentChatSession`/
`SimpleAgentChatMessage`/`SimpleAgentSessionRecord` tables from the patient
pilot -- it never touches `TriageCase`/`NurseReviewState`/`AuditLog`/
`ChatMessage`, so a real nurse's `/clinical/queue` never shows a
simple_agent-originated case. See `.claude/plans/sunny-launching-mitten.md`
for the full design and the deliberate simplifications versus
`routes_nurse.py` (no escalate/specialist-review/PII-access, decision closes
the case directly instead of a separate handoff step, no red-flag concept).

Auth reuses `NurseUserDep` unchanged (`src/api/dependencies.py`) -- that
dependency was already engine-agnostic.
"""

from __future__ import annotations

from typing import Any, Literal

from fastapi import APIRouter, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy import or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from src.agents.simple_agent_runtime import get_simple_agent_runtime
from src.api.dependencies import NurseUserDep, SessionDep
from src.config import get_settings
from src.models.db_models import (
    EHRProfile,
    SimpleAgentChatMessage,
    SimpleAgentChatSession,
    SimpleAgentNurseReview,
    SimpleAgentSessionRecord,
    User,
    get_utc_now,
)
from src.services.simple_nurse_dashboard import (
    NurseDashboardDTO,
    ai_proposed_esi,
    build_nurse_dashboard,
)
from src.simple_agent.persistence import deserialize_session
from src.simple_agent.realtime import (
    EVENT_CASE_STATUS_CHANGED,
    EVENT_MESSAGE_CREATED,
    SIMPLE_STAFF_QUEUE_TOPIC,
    get_event_bus,
    simple_case_topic,
    simple_patient_topic,
)
from src.simple_agent.sbar import build_simple_agent_sbar

router = APIRouter(prefix="/nurse-simple", tags=["Nurse Simple-Agent Pilot"])

_TERMINAL_REVIEW_STATUS = "HANDED_OFF"
# "Tạm gác lại" -- set aside by a nurse, hidden from the main QUEUE bucket
# but never a closed/decided case; restorable by anyone. See plan.
_PARKED_STATUS = "PARKED"
_MIN_PARK_REASON_LENGTH = 10
_REASON_CODES = frozenset(
    {"MATCHES_PROTOCOL", "ADDITIONAL_CLINICAL_JUDGMENT", "INSUFFICIENT_PATIENT_DATA", "OTHER"}
)
_QUEUE_PAGE_SIZE_MAX = 100


_CARE_TEAM_CHANNEL = "CARE_TEAM"


class SimpleClaimRequest(BaseModel):
    version: int
    action: str  # "CLAIM" | "RELEASE" | "PARK" | "RESTORE"
    # Only meaningful (and required, >= _MIN_PARK_REASON_LENGTH chars) for PARK
    # -- why this case is being set aside, so a later reviewer (possibly a
    # different nurse) knows what to fix before pushing it back to the queue.
    reason: str | None = None


class SendCaseMessageRequest(BaseModel):
    content: str
    client_message_id: str | None = None


class SimpleDecisionRequest(BaseModel):
    version: int
    decision_type: str  # "CONFIRM_ESI" | "ADJUST_ESI"
    final_esi: int
    reason_code: str
    note: str | None = None


def _require_enabled() -> None:
    if not get_settings().simple_agent_enabled:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="simple_agent pilot is disabled (set SIMPLE_AGENT_ENABLED=true to enable it locally).",
        )


def _ai_proposed_esi(chat: SimpleAgentChatSession) -> int | None:
    # Định nghĩa nằm ở src/services/simple_nurse_dashboard.py để hàng đợi và
    # bảng số liệu không thể trôi khỏi nhau. Giữ tên cũ ở đây cho các lời gọi
    # sẵn có trong file này.
    return ai_proposed_esi(chat)


def _record_to_session_dict(record: SimpleAgentSessionRecord) -> dict[str, Any]:
    """Local copy of routes_simple_triage.py's helper -- kept independent on
    purpose (see module docstring) rather than importing a private helper
    across router modules."""
    return {
        "subject_type": record.subject_type,
        "subject_label": record.subject_label,
        "parked_subjects": record.parked_subjects,
        "concepts": record.concepts,
        "concept_order": record.concept_order,
        "facts": record.facts,
        "qualitative_observations": record.qualitative_observations,
        "unknown_facts": record.unknown_facts,
        "needs_precision": record.needs_precision,
        "seen_atom_ids": record.seen_atom_ids,
        "last_question": record.last_question,
        "stale_question_streak": record.stale_question_streak,
        "confirmation_offered": record.confirmation_offered,
        "resource_count_estimated": record.resource_count_estimated,
        "history": record.history,
        "tool_log_tail": record.tool_log_tail,
    }


async def _patient_contact_block(session: AsyncSession, chat: SimpleAgentChatSession) -> dict[str, Any]:
    """Danh tính và đường liên lạc của người bệnh trong một ca đã hoàn tất.

    Thuần đọc, và chỉ phục vụ endpoint đã đứng sau ``NurseUserDep`` -- cùng
    mô hình phân quyền mà hàng đợi production đang dùng (xem
    ``NurseQueueItemDTO.patient_name``: "Họ tên đầy đủ, chỉ trả qua API dành
    cho nhân viên lâm sàng"). Không có đường nào khác để lấy dữ liệu này:
    ``/profiles/{id}`` đứng sau ``PatientUserDep`` và còn lọc theo
    ``user_id == current_user.id``, nên điều dưỡng gọi vào sẽ 404.

    ``profile`` là thẻ hồ sơ EHR đã chọn lúc ``/start``. Nó có thể là hồ sơ
    người thân chứ không phải chủ tài khoản -- đúng tình huống "gọi cho ai"
    mà điều dưỡng cần phân biệt, nên hai khối tài khoản và thẻ hồ sơ được
    trả riêng thay vì trộn làm một.
    """
    user = (
        await session.execute(select(User).where(User.id == chat.patient_id))
    ).scalars().first()

    profile: EHRProfile | None = None
    if chat.profile_id:
        profile = (
            await session.execute(select(EHRProfile).where(EHRProfile.id == chat.profile_id))
        ).scalars().first()

    return {
        "account": {
            "full_name": user.full_name if user else None,
            "email": user.email if user else None,
            "phone": user.phone if user else None,
        },
        # None = phiên ẩn danh: bệnh nhân không gắn thẻ hồ sơ nào lúc bắt đầu.
        "profile": None
        if profile is None
        else {
            "full_name": profile.full_name,
            "relationship_type": profile.relationship_type,
            "is_primary": profile.is_primary,
            "age": profile.age,
            "gender": profile.gender,
            "phone_number": profile.phone_number,
            "blood_type": profile.blood_type,
            "chronic_conditions": profile.chronic_conditions or [],
            "allergies": profile.allergies or [],
            "emergency_contact_name": profile.emergency_contact_name,
            "emergency_contact_phone": profile.emergency_contact_phone,
        },
    }


async def _get_chat_session_or_404(session: AsyncSession, session_id: str) -> SimpleAgentChatSession:
    chat = (
        await session.execute(
            select(SimpleAgentChatSession).where(SimpleAgentChatSession.session_id == session_id)
        )
    ).scalars().first()
    if chat is None or chat.status != "COMPLETED":
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Không tìm thấy ca simple_agent đã hoàn tất để thẩm định.",
        )
    return chat


async def _get_or_create_review(session: AsyncSession, session_id: str) -> SimpleAgentNurseReview:
    """Lazy row creation -- same pattern as `_get_review_state` in
    `routes_nurse.py`. Keeps `routes_simple_triage.py` at zero diff: nothing
    on the patient-facing path ever needs to know a review row exists."""
    review = (
        await session.execute(
            select(SimpleAgentNurseReview).where(SimpleAgentNurseReview.session_id == session_id)
        )
    ).scalars().first()
    if review is None:
        review = SimpleAgentNurseReview(session_id=session_id)
        session.add(review)
        await session.flush()
    return review


def _assert_version(review: SimpleAgentNurseReview, expected: int) -> None:
    if review.version != expected:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "code": "CASE_VERSION_CONFLICT",
                "message": "Ca đã được cập nhật bởi người khác. Vui lòng tải lại dữ liệu.",
                "current_version": review.version,
            },
        )


def _assert_assignee(review: SimpleAgentNurseReview, nurse: User) -> None:
    if review.assigned_nurse_id != nurse.id:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Bạn phải nhận ca này trước khi ra quyết định.",
        )


async def _unread_from_patient(session: AsyncSession, session_id: str) -> int:
    """Care-team messages from the patient the clinical side hasn't read yet."""
    rows = (
        await session.execute(
            select(SimpleAgentChatMessage).where(
                SimpleAgentChatMessage.session_id == session_id,
                SimpleAgentChatMessage.channel == _CARE_TEAM_CHANNEL,
                SimpleAgentChatMessage.sender == "PATIENT",
                SimpleAgentChatMessage.read_at.is_(None),
            )
        )
    ).scalars().all()
    return len(rows)


def _queue_item(
    chat: SimpleAgentChatSession,
    review: SimpleAgentNurseReview,
    unread_count: int,
    patient_email: str | None,
    patient_name: str | None,
) -> dict[str, Any]:
    ai_esi = _ai_proposed_esi(chat)
    waiting_since = chat.completed_at or chat.started_at
    decided_at = review.decided_at or review.handed_off_at
    return {
        "session_id": chat.session_id,
        "initial_message": chat.initial_message,
        "final_action": chat.final_action,
        "ai_proposed_esi": ai_esi,
        "is_insufficient": chat.final_action == "RETURN_INCOMPLETE",
        "turn_count": chat.turn_count,
        "waiting_since": waiting_since.isoformat(),
        "review_status": review.review_status,
        "assigned_nurse_id": review.assigned_nurse_id,
        "case_version": review.version,
        "unread_count": unread_count,
        "patient_email": patient_email,
        "patient_name": patient_name,
        # DECIDED-tab display -- already available on `review`, no extra
        # fetch needed once a case is HANDED_OFF.
        "final_esi": review.final_esi,
        "decision_type": review.decision_type,
        "decision_note": review.decision_note,
        "decided_at": decided_at.isoformat() if decided_at else None,
        # PARKED-tab display.
        "parked_at": review.parked_at.isoformat() if review.parked_at else None,
        "parked_by_nurse_id": review.parked_by_nurse_id,
        "parked_reason": review.parked_reason,
    }


@router.get("/queue", status_code=status.HTTP_200_OK)
async def get_simple_nurse_queue(
    nurse: NurseUserDep,
    session: SessionDep,
    bucket: Literal["QUEUE", "PARKED", "DECIDED"] = Query(
        "QUEUE", description="QUEUE = đang chờ; PARKED = tạm gác lại; DECIDED = đã xác nhận/điều chỉnh"
    ),
    mine_only: bool = Query(False, description="Chỉ lấy ca do điều dưỡng hiện tại phụ trách"),
    q: str | None = Query(None, description="Lọc theo mã ca hoặc mô tả triệu chứng"),
    patient_email: str | None = Query(None, description="Lọc theo email bệnh nhân"),
    esi_levels: str | None = Query(
        None, description="Lọc theo mức ESI AI đề xuất, phân cách bằng dấu phẩy (vd '2,3') -- tránh mọi khác biệt "
        "cách các client HTTP tự nối tham số dạng danh sách vào URL."
    ),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=_QUEUE_PAGE_SIZE_MAX),
) -> dict[str, Any]:
    """Prioritized, filterable, paginated view over completed simple_agent
    sessions -- 3 buckets sharing this one endpoint (see plan) rather than 3
    separate routes, since they only ever differ by `review_status` WHERE
    clause + default sort:

    - QUEUE: awaiting review (not yet decided, not parked) -- default view,
      mirrors `GET /nurse/queue`'s shape (`items` + `summary`), trimmed: no
      red-flag/urgent split (simple_agent has no red-flag concept), sorted by
      AI-proposed ESI (lowest/most urgent first, no-proposal last) then wait
      time -- unchanged from before this endpoint grew buckets/filters. Once
      claimed by anyone, a case only appears here for its assignee (via
      `mine_only`, see below) -- not in the shared, un-mine_only'd view, so
      multiple nurses working the same queue don't keep seeing cases another
      nurse already picked up (2026-08-29).
    - PARKED: set aside by a nurse ("tạm gác lại"), hidden from QUEUE but
      restorable by any nurse -- same sort as QUEUE.
    - DECIDED: already HANDED_OFF, review-only -- sorted by most-recently
      decided first, since browsing history cares about recency, not
      severity/wait time.

    `mine_only`/`q`/`patient_email`/`esi_levels` are plain Python filters over
    the already-fetched, already-bucketed list (mirrors production's own
    `mine_only` on `GET /nurse/queue` -- pilot data volumes don't need this
    pushed into SQL). `page`/`page_size` slice the filtered+sorted list;
    `summary` reflects the bucket+search+email+esi-filtered set *before*
    `mine_only`/pagination, so "mine_count" stays meaningful even when not
    on the "mine" tab.
    """
    _require_enabled()
    rows = (
        await session.execute(
            select(SimpleAgentChatSession, User.email, User.full_name)
            .join(User, User.id == SimpleAgentChatSession.patient_id)
            .where(SimpleAgentChatSession.status == "COMPLETED")
        )
    ).all()

    items: list[dict[str, Any]] = []
    for chat, email, full_name in rows:
        review = await _get_or_create_review(session, chat.session_id)
        if bucket == "QUEUE" and review.review_status in {_TERMINAL_REVIEW_STATUS, _PARKED_STATUS}:
            continue
        if bucket == "PARKED" and review.review_status != _PARKED_STATUS:
            continue
        if bucket == "DECIDED" and review.review_status != _TERMINAL_REVIEW_STATUS:
            continue
        unread_count = await _unread_from_patient(session, chat.session_id)
        items.append(_queue_item(chat, review, unread_count, email, full_name))
    await session.commit()

    if q:
        needle = q.strip().lower()
        items = [
            item
            for item in items
            if needle in item["session_id"].lower() or needle in item["initial_message"].lower()
        ]
    if patient_email:
        needle_email = patient_email.strip().lower()
        items = [
            item for item in items if item["patient_email"] and needle_email in item["patient_email"].lower()
        ]
    if esi_levels:
        try:
            allowed_levels = {int(token) for token in esi_levels.split(",") if token.strip()}
        except ValueError:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="esi_levels phải là danh sách số nguyên phân cách bằng dấu phẩy.") from None
        if allowed_levels:
            items = [item for item in items if item["ai_proposed_esi"] in allowed_levels]

    summary = {
        "total_waiting": len(items),
        "mine_count": sum(1 for item in items if item["assigned_nurse_id"] == nurse.id),
        "insufficient_count": sum(1 for item in items if item["is_insufficient"]),
    }

    if mine_only:
        items = [item for item in items if item["assigned_nurse_id"] == nurse.id]
    elif bucket == "QUEUE":
        # Real feedback (2026-08-29): with more than one nurse able to work
        # this queue, a case someone already claimed (ASSIGNED) shouldn't
        # keep cluttering everyone else's shared "Hàng đợi" view -- it now
        # only shows up for its assignee, via the "Ca của tôi" (mine_only)
        # tab above. `summary` was already computed from the pre-filter set
        # just above, so `mine_count` stays accurate even though these items
        # disappear from `items` here.
        items = [item for item in items if item["assigned_nurse_id"] is None]

    if bucket == "DECIDED":
        items.sort(key=lambda item: item["decided_at"] or "", reverse=True)
    else:
        items.sort(
            key=lambda item: (item["ai_proposed_esi"] if item["ai_proposed_esi"] is not None else 6, item["waiting_since"])
        )

    total_items = len(items)
    total_pages = max(1, -(-total_items // page_size))
    current_page = min(page, total_pages)
    start = (current_page - 1) * page_size
    page_items = items[start : start + page_size]

    return {
        "items": page_items,
        "summary": summary,
        "pagination": {
            "page": current_page,
            "page_size": page_size,
            "total_items": total_items,
            "total_pages": total_pages,
        },
    }


@router.get("/dashboard", response_model=NurseDashboardDTO, status_code=status.HTTP_200_OK)
async def get_simple_nurse_dashboard(nurse: NurseUserDep, session: SessionDep) -> NurseDashboardDTO:
    """Số liệu tổng quan của trạm điều phối, đọc từ đúng tập ca mà hàng đợi dùng.

    Chỉ đọc, không tạo dòng review lười như `GET /queue` -- xem ghi chú đầu
    `src/services/simple_nurse_dashboard.py`. `nurse.id` chỉ dùng để tách ra
    phần "ca của tôi"; mọi con số còn lại là của cả kíp trực.
    """
    _require_enabled()
    return await build_nurse_dashboard(session, nurse.id)


@router.get("/cases/{session_id}", status_code=status.HTTP_200_OK)
async def get_simple_nurse_case(session_id: str, nurse: NurseUserDep, session: SessionDep) -> dict[str, Any]:
    """Full case detail: transcript, synthesized SBAR, and review state."""
    _require_enabled()
    chat = await _get_chat_session_or_404(session, session_id)
    review = await _get_or_create_review(session, session_id)
    await session.commit()

    record = (
        await session.execute(
            select(SimpleAgentSessionRecord).where(SimpleAgentSessionRecord.session_id == session_id)
        )
    ).scalars().first()
    messages = (
        await session.execute(
            select(SimpleAgentChatMessage)
            .where(
                SimpleAgentChatMessage.session_id == session_id,
                # Same exclusion as routes_simple_triage.py's session detail --
                # care-team messages are a separate conversation, shown via
                # GET .../care-team instead.
                or_(SimpleAgentChatMessage.channel == "TRIAGE", SimpleAgentChatMessage.channel.is_(None)),
            )
            .order_by(SimpleAgentChatMessage.turn_index, SimpleAgentChatMessage.created_at)
        )
    ).scalars().all()

    sbar: dict[str, Any] | None = None
    if record is not None:
        runtime = get_simple_agent_runtime()
        engine_session = deserialize_session(_record_to_session_dict(record))
        sbar = build_simple_agent_sbar(
            corpus=runtime.corpus,
            session=engine_session,
            initial_message=chat.initial_message,
            final_message=chat.final_message or "",
            matched_esi_levels=chat.matched_esi_levels,
        )

    return {
        "session_id": session_id,
        "patient": await _patient_contact_block(session, chat),
        "initial_message": chat.initial_message,
        "final_action": chat.final_action,
        "final_message": chat.final_message,
        "ai_proposed_esi": _ai_proposed_esi(chat),
        "matched_esi_levels": chat.matched_esi_levels,
        "final_concepts": chat.final_concepts,
        "review_status": review.review_status,
        "assigned_nurse_id": review.assigned_nurse_id,
        "case_version": review.version,
        "final_esi": review.final_esi,
        "decision_type": review.decision_type,
        "decision_reason_code": review.decision_reason_code,
        "decision_note": review.decision_note,
        "sbar": sbar,
        "messages": [
            {
                "turn_index": m.turn_index,
                "sender": m.sender,
                "content": m.content,
                "created_at": m.created_at.isoformat(),
            }
            for m in messages
        ],
    }


@router.post("/cases/{session_id}/claim", status_code=status.HTTP_200_OK)
async def claim_simple_case(
    session_id: str,
    payload: SimpleClaimRequest,
    nurse: NurseUserDep,
    session: SessionDep,
) -> dict[str, Any]:
    _require_enabled()
    await _get_chat_session_or_404(session, session_id)
    review = await _get_or_create_review(session, session_id)
    _assert_version(review, payload.version)

    if payload.action == "CLAIM":
        if review.assigned_nurse_id and review.assigned_nurse_id != nurse.id:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Ca này đã có người khác nhận.")
        review.assigned_nurse_id = nurse.id
        review.claimed_at = get_utc_now()
        review.review_status = "ASSIGNED"
    elif payload.action == "RELEASE":
        _assert_assignee(review, nurse)
        review.assigned_nurse_id = None
        review.claimed_at = None
        review.review_status = "WAITING_REVIEW"
    elif payload.action == "PARK":
        if review.review_status == _TERMINAL_REVIEW_STATUS:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Ca đã đóng, không thể tạm gác lại.")
        if review.assigned_nurse_id and review.assigned_nurse_id != nurse.id:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Ca này đang được y tá khác phụ trách.")
        if not payload.reason or len(payload.reason.strip()) < _MIN_PARK_REASON_LENGTH:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Tạm gác lại cần ghi lý do ít nhất {_MIN_PARK_REASON_LENGTH} ký tự.",
            )
        # Auto-claim if nobody has it yet -- same idea as send_case_message's
        # auto-claim-on-reply, a nurse setting a case aside shouldn't need a
        # separate claim step first.
        if review.assigned_nurse_id is None:
            review.assigned_nurse_id = nurse.id
            review.claimed_at = get_utc_now()
        review.review_status = _PARKED_STATUS
        review.parked_at = get_utc_now()
        review.parked_by_nurse_id = nurse.id
        review.parked_reason = payload.reason.strip()
    elif payload.action == "RESTORE":
        if review.review_status != _PARKED_STATUS:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Ca này hiện không ở trạng thái tạm gác lại.")
        # Any nurse may restore -- the point is to make it visible again for
        # whoever picks it up next, not necessarily the one who parked it.
        review.assigned_nurse_id = None
        review.claimed_at = None
        review.parked_at = None
        review.parked_by_nurse_id = None
        review.parked_reason = None
        review.review_status = "WAITING_REVIEW"
    else:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="action phải là CLAIM, RELEASE, PARK hoặc RESTORE."
        )

    review.version += 1
    review.updated_at = get_utc_now()
    await session.commit()
    return {"session_id": session_id, "review_status": review.review_status, "case_version": review.version}


@router.post("/cases/{session_id}/decision", status_code=status.HTTP_200_OK)
async def submit_simple_decision(
    session_id: str,
    payload: SimpleDecisionRequest,
    nurse: NurseUserDep,
    session: SessionDep,
) -> dict[str, Any]:
    """Confirm or adjust the AI's ESI, and close the case in the same step
    (see module docstring: the two-step decide/handoff flow is collapsed for
    this pilot)."""
    _require_enabled()
    chat = await _get_chat_session_or_404(session, session_id)
    review = await _get_or_create_review(session, session_id)
    _assert_assignee(review, nurse)
    _assert_version(review, payload.version)

    if review.review_status == _TERMINAL_REVIEW_STATUS:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Ca đã được đóng.")
    if payload.decision_type not in {"CONFIRM_ESI", "ADJUST_ESI"}:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="decision_type phải là CONFIRM_ESI hoặc ADJUST_ESI.")
    if payload.reason_code not in _REASON_CODES:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="reason_code không hợp lệ.")
    if not (1 <= payload.final_esi <= 5):
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="final_esi phải trong khoảng 1-5.")

    ai_esi = _ai_proposed_esi(chat)
    if payload.decision_type == "CONFIRM_ESI":
        if ai_esi is None:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Không có mức ESI do AI đề xuất để xác nhận -- dùng ADJUST_ESI.",
            )
        if payload.final_esi != ai_esi:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Xác nhận ESI phải giữ nguyên mức AI đề xuất.")
    else:  # ADJUST_ESI
        if ai_esi is not None and payload.final_esi == ai_esi:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Mức điều chỉnh phải khác ESI do AI đề xuất.")
        if not payload.note or len(payload.note.strip()) < 10:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Điều chỉnh ESI cần ghi chú lâm sàng ít nhất 10 ký tự.")

    review.final_esi = payload.final_esi
    review.is_overridden = payload.decision_type == "ADJUST_ESI"
    review.decision_type = payload.decision_type
    review.decision_reason_code = payload.reason_code
    review.decision_note = payload.note
    review.decided_at = get_utc_now()
    review.review_status = _TERMINAL_REVIEW_STATUS
    review.handed_off_at = get_utc_now()
    review.version += 1
    review.updated_at = get_utc_now()
    await session.commit()
    # The decision is already committed before this best-effort notification.
    # Patient UI treats the event only as a prompt to re-read the persisted
    # decision, so a dropped socket message cannot show a fabricated result.
    bus = get_event_bus()
    decision_event = {
        "session_id": session_id,
        "decision_type": review.decision_type,
        "final_esi": review.final_esi,
    }
    await bus.publish(simple_case_topic(session_id), EVENT_CASE_STATUS_CHANGED, decision_event)
    await bus.publish(simple_patient_topic(chat.patient_id), EVENT_CASE_STATUS_CHANGED, decision_event)
    await bus.publish(SIMPLE_STAFF_QUEUE_TOPIC, EVENT_CASE_STATUS_CHANGED, decision_event)
    return {
        "session_id": session_id,
        "review_status": review.review_status,
        "case_version": review.version,
        "final_esi": review.final_esi,
    }


# -- care-team chat (nurse side) ---------------------------------------------
#
# Mirrors routes_nurse.py's send_case_message/mark_case_messages_read/
# get_case_care_team_thread, but on SimpleAgentChatMessage/SimpleAgentNurseReview.
# See routes_simple_triage.py for the patient-side counterpart.


async def _find_by_client_message_id(
    session: AsyncSession, session_id: str, client_message_id: str | None
) -> SimpleAgentChatMessage | None:
    if not client_message_id:
        return None
    return (
        await session.execute(
            select(SimpleAgentChatMessage).where(
                SimpleAgentChatMessage.session_id == session_id,
                SimpleAgentChatMessage.client_message_id == client_message_id,
            )
        )
    ).scalars().first()


async def _case_care_team_thread(session: AsyncSession, session_id: str) -> dict[str, Any]:
    rows = (
        await session.execute(
            select(SimpleAgentChatMessage)
            .where(
                SimpleAgentChatMessage.session_id == session_id,
                SimpleAgentChatMessage.channel == _CARE_TEAM_CHANNEL,
            )
            .order_by(SimpleAgentChatMessage.created_at)
        )
    ).scalars().all()
    unread_count = sum(1 for row in rows if row.sender == "PATIENT" and row.read_at is None)
    return {
        "session_id": session_id,
        "unread_count": unread_count,
        "messages": [
            {
                "id": row.id,
                "sender": "patient" if row.sender == "PATIENT" else "staff",
                "content": row.content,
                "created_at": row.created_at.isoformat(),
                "read_at": row.read_at.isoformat() if row.read_at else None,
            }
            for row in rows
        ],
    }


@router.post("/cases/{session_id}/messages", status_code=status.HTTP_201_CREATED)
async def send_case_message(
    session_id: str,
    payload: SendCaseMessageRequest,
    nurse: NurseUserDep,
    session: SessionDep,
) -> dict[str, Any]:
    """Reply to the patient. Auto-claims the case if nobody has yet -- same
    idea as the real `_claim_for_reply`: a nurse skimming unread messages
    shouldn't need a separate claim step before answering."""
    _require_enabled()
    chat = await _get_chat_session_or_404(session, session_id)
    review = await _get_or_create_review(session, session_id)
    if review.review_status == _TERMINAL_REVIEW_STATUS:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Ca đã được đóng, không thể nhắn thêm.")
    if review.assigned_nurse_id is None:
        review.assigned_nurse_id = nurse.id
        review.claimed_at = get_utc_now()
        review.review_status = "ASSIGNED"
        review.version += 1
        review.updated_at = get_utc_now()
    elif review.assigned_nurse_id != nurse.id:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Ca này đang được y tá khác phụ trách.")

    existing = await _find_by_client_message_id(session, session_id, payload.client_message_id)
    if existing is not None:
        await session.commit()
        return await _case_care_team_thread(session, session_id)

    session.add(
        SimpleAgentChatMessage(
            session_id=session_id,
            turn_index=chat.turn_count,
            sender="NURSE",
            content=payload.content,
            channel=_CARE_TEAM_CHANNEL,
            client_message_id=payload.client_message_id,
        )
    )
    await session.commit()
    # Chỉ báo "có thay đổi" -- nội dung thật luôn đọc lại qua REST ở trên, nên
    # mất sự kiện này chỉ làm giao diện chậm cập nhật, không sai dữ liệu.
    bus = get_event_bus()
    await bus.publish(
        simple_case_topic(session_id), EVENT_MESSAGE_CREATED, {"session_id": session_id, "sender": "NURSE"}
    )
    await bus.publish(
        simple_patient_topic(chat.patient_id), EVENT_MESSAGE_CREATED, {"session_id": session_id, "sender": "NURSE"}
    )
    # Việc tự nhận ca ở trên (nếu có) cũng đổi thứ tự/nhãn hàng đợi, nên báo
    # luôn cho các y tá khác đang xem hàng đợi.
    await bus.publish(
        SIMPLE_STAFF_QUEUE_TOPIC, EVENT_MESSAGE_CREATED, {"session_id": session_id, "sender": "NURSE"}
    )
    return await _case_care_team_thread(session, session_id)


@router.post("/cases/{session_id}/messages/read", status_code=status.HTTP_200_OK)
async def mark_case_messages_read(
    session_id: str,
    nurse: NurseUserDep,
    session: SessionDep,
) -> dict[str, Any]:
    _require_enabled()
    await _get_chat_session_or_404(session, session_id)
    unread = (
        await session.execute(
            select(SimpleAgentChatMessage).where(
                SimpleAgentChatMessage.session_id == session_id,
                SimpleAgentChatMessage.channel == _CARE_TEAM_CHANNEL,
                SimpleAgentChatMessage.sender == "PATIENT",
                SimpleAgentChatMessage.read_at.is_(None),
            )
        )
    ).scalars().all()
    now = get_utc_now()
    for row in unread:
        row.read_at = now
    await session.commit()
    return await _case_care_team_thread(session, session_id)


@router.get("/cases/{session_id}/care-team", status_code=status.HTTP_200_OK)
async def get_case_care_team_thread(
    session_id: str,
    nurse: NurseUserDep,
    session: SessionDep,
) -> dict[str, Any]:
    """Readable without claiming the case -- a nurse can see what a patient
    said before deciding whether to pick the case up."""
    _require_enabled()
    await _get_chat_session_or_404(session, session_id)
    return await _case_care_team_thread(session, session_id)
