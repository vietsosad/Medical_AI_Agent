"""Additive pilot routes for src/simple_agent -- local-test surface only.

Deliberately separate from routes_patient.py's live `/triage/*` endpoints:
this router adds new paths, reuses the existing patient auth dependency
unchanged (no touch to login/registration), and returns SimpleTriageAgent's
native `{"session_id", "message", "decision"}` shape rather than the
DeepAgent DTOs -- there is no ESI/SBAR/nurse-review wiring here, this is a
standalone path for proving the deepagents-based Phase A locally before any
decision is made about the live triage flow.

Persistence here is split across three concerns, on purpose:

- ``SimpleAgentSessionRecord`` -- raw engine state (the ``Session`` dataclass),
  needed only so a worker restart can resume Phase A/B/C mid-conversation.
- ``SimpleAgentChatSession`` -- the domain-level "working session": is it
  still open, and what did it conclude with. This is what session control
  (reject further turns once closed) and the saved final result live on.
- ``SimpleAgentChatMessage`` -- the full, untruncated message history, one
  row per patient/agent message, with a decision snapshot on agent turns.
"""

from __future__ import annotations

import io
import logging
import uuid
from typing import Any

from asyncer import asyncify
from fastapi import APIRouter, HTTPException, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy import func, or_
from sqlmodel import select

from src.agents.simple_agent_runtime import get_simple_agent_runtime
from src.api.dependencies import PatientUserDep, SessionDep
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
from src.services.sbar_pdf import SbarPdfData, build_sbar_pdf
from src.simple_agent.persistence import deserialize_session, serialize_session
from src.simple_agent.realtime import (
    EVENT_MESSAGE_CREATED,
    SIMPLE_STAFF_QUEUE_TOPIC,
    get_event_bus,
    simple_case_topic,
)
from src.simple_agent.sbar import build_simple_agent_sbar
from src.simple_agent.session import Session

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/simple-triage", tags=["Simple Agent Pilot"])

_TURN_FAILED_DETAIL = (
    "Không thể xử lý lượt hội thoại này do lỗi kết nối tới dịch vụ AI. Vui lòng thử gửi lại."
)

# The only two decision.py actions that end a conversation -- everything else
# (ASK_NEXT, ASK_CONFIRMATION, ASK_CLARIFICATION, RESPOND, REFUSE) keeps the
# session open for another turn. See src/simple_agent/agent.py's process_turn.
_TERMINAL_ACTIONS = {"RETURN_MATCH", "RETURN_INCOMPLETE"}
_CARE_TEAM_CHANNEL = "CARE_TEAM"
# Same terminal value as SimpleAgentNurseReview.review_status in
# routes_nurse_simple.py -- duplicated as a literal, not imported, to keep
# the two routers independent (see that module's docstring).
_REVIEW_HANDED_OFF = "HANDED_OFF"


class SimpleTriageMessageRequest(BaseModel):
    message: str


class StartSimpleTriageRequest(SimpleTriageMessageRequest):
    # Which EHR profile card this conversation is about -- "chọn thẻ của
    # tôi" or "chọn thẻ người thân" in the patient-facing picker. None means
    # the patient picked "ẩn danh / người mới" (anonymous): no demographics
    # are known, and requires_sex-gated fact targets (see agent.py's
    # _sex_compatible) stay askable exactly as before this field existed.
    profile_id: str | None = None


class SendStaffMessageRequest(BaseModel):
    content: str
    client_message_id: str | None = None


def _require_enabled() -> None:
    if not get_settings().simple_agent_enabled:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="simple_agent pilot is disabled (set SIMPLE_AGENT_ENABLED=true to enable it locally).",
        )


# -- engine-state (SimpleAgentSessionRecord) (de)serialization --------------


def _record_to_session_dict(record: SimpleAgentSessionRecord) -> dict[str, Any]:
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
        # `or {}`: rows written before this column existed (real pilot rows
        # predate MIN_ATOM_RELEVANCE_SCORE_FOR_PROACTIVE_ASK) read it back as
        # NULL via the additive-column migration -- treat as "no confidence
        # data yet", same default deserialize_session already falls back to.
        "atom_relevance_score": record.atom_relevance_score or {},
        "retrieval_query": record.retrieval_query,
        "card_gender": record.card_gender,
        "card_relationship": record.card_relationship,
        "last_question": record.last_question,
        "stale_question_streak": record.stale_question_streak,
        "confirmation_offered": record.confirmation_offered,
        "resource_count_estimated": record.resource_count_estimated,
        "history": record.history,
        "tool_log_tail": record.tool_log_tail,
    }


def _apply_session_dict_to_record(record: SimpleAgentSessionRecord, data: dict[str, Any]) -> None:
    record.subject_type = data["subject_type"]
    record.subject_label = data["subject_label"]
    record.parked_subjects = data["parked_subjects"]
    record.concepts = data["concepts"]
    record.concept_order = data["concept_order"]
    record.facts = data["facts"]
    record.qualitative_observations = data["qualitative_observations"]
    record.unknown_facts = data["unknown_facts"]
    record.needs_precision = data["needs_precision"]
    record.seen_atom_ids = data["seen_atom_ids"]
    record.atom_relevance_score = data["atom_relevance_score"]
    record.retrieval_query = data.get("retrieval_query")
    record.card_gender = data.get("card_gender")
    record.card_relationship = data.get("card_relationship")
    record.last_question = data["last_question"]
    record.stale_question_streak = data["stale_question_streak"]
    record.confirmation_offered = data["confirmation_offered"]
    record.resource_count_estimated = data["resource_count_estimated"]
    record.history = data["history"]
    record.tool_log_tail = data["tool_log_tail"]
    record.updated_at = get_utc_now()


# -- domain session control + message history --------------------------------


def _record_turn_messages(
    *, session_id: str, turn_index: int, patient_message: str, result: dict[str, Any]
) -> tuple[SimpleAgentChatMessage, SimpleAgentChatMessage]:
    decision = result["decision"]
    patient_row = SimpleAgentChatMessage(
        session_id=session_id, turn_index=turn_index, sender="PATIENT", content=patient_message,
    )
    agent_row = SimpleAgentChatMessage(
        session_id=session_id, turn_index=turn_index, sender="AGENT", content=result["message"],
        route=decision.get("route"), action=decision.get("action"),
        question_target_id=decision.get("question_target_id"), decision_snapshot=decision,
    )
    return patient_row, agent_row


def _apply_turn_outcome_to_chat_session(chat_session: SimpleAgentChatSession, result: dict[str, Any]) -> None:
    decision = result["decision"]
    now = get_utc_now()
    chat_session.turn_count += 1
    chat_session.last_activity_at = now
    if decision.get("action") in _TERMINAL_ACTIONS:
        chat_session.status = "COMPLETED"
        chat_session.final_route = decision.get("route")
        chat_session.final_action = decision.get("action")
        chat_session.matched_esi_levels = decision.get("matched_esi_levels") or []
        chat_session.final_message = result["message"]
        chat_session.final_concepts = decision.get("concepts") or []
        chat_session.completed_at = now


async def _review_info_by_session(session: SessionDep, session_ids: list[str]) -> dict[str, dict[str, Any]]:
    """Batch-fetch `SimpleAgentNurseReview` + reviewer display name for a set
    of sessions, one query -- used by the list endpoint (all of a patient's
    sessions at once), the detail endpoint, and the PDF endpoint (a single
    session), so review status/reviewer-name logic lives in exactly one
    place instead of being re-derived per call site (see history-page plan).
    """
    if not session_ids:
        return {}
    rows = (
        await session.execute(
            select(SimpleAgentNurseReview, User)
            .outerjoin(User, SimpleAgentNurseReview.assigned_nurse_id == User.id)
            .where(SimpleAgentNurseReview.session_id.in_(session_ids))
        )
    ).all()
    return {
        review.session_id: {
            "review_status": review.review_status,
            "is_overridden": review.is_overridden,
            "final_esi": review.final_esi,
            "decision_type": review.decision_type,
            "decision_reason_code": review.decision_reason_code,
            "decision_note": review.decision_note,
            "reviewer_name": user.full_name if user else None,
            "reviewed_at": review.decided_at or review.handed_off_at,
        }
        for review, user in rows
    }


async def _unread_from_staff_by_session(session: SessionDep, session_ids: list[str]) -> dict[str, int]:
    """Batch-count unread NURSE care-team messages per session, one query --
    used so the patient's own session list/sidebar can show "có tin mới"
    without needing to be on that exact session's page (see
    SimpleCareTeamDock, which already shows this but only while mounted;
    this closes the "no cross-page signal" gap flagged in the plan)."""
    if not session_ids:
        return {}
    rows = (
        await session.execute(
            select(SimpleAgentChatMessage.session_id, func.count())
            .where(
                SimpleAgentChatMessage.session_id.in_(session_ids),
                SimpleAgentChatMessage.channel == _CARE_TEAM_CHANNEL,
                SimpleAgentChatMessage.sender == "NURSE",
                SimpleAgentChatMessage.read_at.is_(None),
            )
            .group_by(SimpleAgentChatMessage.session_id)
        )
    ).all()
    return dict(rows)


def _map_pilot_review_status(review_info: dict[str, Any] | None) -> str:
    """Collapse the pilot's 3-state `SimpleAgentNurseReview.review_status`
    (WAITING_REVIEW/ASSIGNED/HANDED_OFF) + `is_overridden` flag into the same
    3-value vocabulary `services/sbar_pdf.py`'s `SbarPdfData.review_status`
    already understands (a subset of production's 4-value `HitlReviewStatus`
    -- the pilot has no equivalent of a red-flag-locked/EMERGENCY_REJECTED
    case). Used for the history-page filter/badge *and* the PDF export, so
    "pending" vs "reviewed" is defined exactly once.
    """
    if not review_info or review_info["review_status"] != _REVIEW_HANDED_OFF:
        return "PENDING_REVIEW"
    return "OVERRIDDEN" if review_info["is_overridden"] else "APPROVED"


def _chat_session_summary(
    chat_session: SimpleAgentChatSession,
    review_info: dict[str, Any] | None = None,
    unread_from_staff: int = 0,
) -> dict[str, Any]:
    return {
        "session_id": chat_session.session_id,
        "status": chat_session.status,
        "profile_id": chat_session.profile_id,
        "initial_message": chat_session.initial_message,
        "turn_count": chat_session.turn_count,
        "started_at": chat_session.started_at.isoformat(),
        "last_activity_at": chat_session.last_activity_at.isoformat(),
        "completed_at": chat_session.completed_at.isoformat() if chat_session.completed_at else None,
        "final_route": chat_session.final_route,
        "final_action": chat_session.final_action,
        "matched_esi_levels": chat_session.matched_esi_levels,
        "final_message": chat_session.final_message,
        "final_concepts": chat_session.final_concepts,
        # Nurse-review info, never written by this router -- read-only join
        # against SimpleAgentNurseReview (see routes_nurse_simple.py for the
        # writer side). `review_status` here is the raw
        # WAITING_REVIEW/ASSIGNED/HANDED_OFF value; `review_display_status`
        # is the pre-collapsed 3-value form the frontend filters/badges on.
        "review_status": review_info["review_status"] if review_info else None,
        "is_overridden": review_info["is_overridden"] if review_info else False,
        "final_esi": review_info["final_esi"] if review_info else None,
        "decision_type": review_info["decision_type"] if review_info else None,
        "decision_reason_code": review_info["decision_reason_code"] if review_info else None,
        "decision_note": review_info["decision_note"] if review_info else None,
        "reviewer_name": review_info["reviewer_name"] if review_info else None,
        "reviewed_at": (
            f'{review_info["reviewed_at"].isoformat()}Z'
            if review_info and review_info["reviewed_at"]
            else None
        ),
        "review_display_status": _map_pilot_review_status(review_info),
        # Unread NURSE care-team replies -- lets the patient's session list/
        # sidebar show "có tin mới" without needing that exact session open.
        "unread_from_staff": unread_from_staff,
    }


@router.post("/start", status_code=status.HTTP_200_OK)
async def start_simple_triage(
    payload: StartSimpleTriageRequest,
    current_user: PatientUserDep,
    session: SessionDep,
) -> dict[str, Any]:
    _require_enabled()
    session_id = str(uuid.uuid4())
    runtime = get_simple_agent_runtime()

    # "Chọn thẻ của tôi" / "chọn thẻ người thân" vs "ẩn danh/người mới": read-
    # only lookup into the same EHRProfile table production's own /triage/start
    # already uses (no write, no auth/registration surface touched). Ownership
    # is enforced the same way: profile_id must belong to current_user, or
    # this 404s exactly like the production route does for a foreign id.
    initial_session: Session | None = None
    if payload.profile_id:
        profile_result = await session.execute(
            select(EHRProfile).where(EHRProfile.id == payload.profile_id, EHRProfile.user_id == current_user.id)
        )
        profile = profile_result.scalars().first()
        if profile is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Không tìm thấy hồ sơ y tế tương thích.")
        initial_session = Session(card_gender=profile.gender, card_relationship=profile.relationship_type)

    # A raw exception here (observed live: openai.APIConnectionError from a
    # transient network blip reaching OpenAI from inside the container) would
    # otherwise surface to the frontend as a bare 500 with no JSON body --
    # axios then has nothing usable in response.data.detail, so the patient
    # sees only a generic fallback toast and nothing in the transcript at
    # all. Converting it to a clean 503 with an actionable message here lets
    # the chat UI show a real, retryable error card instead of silence. No
    # partial state is persisted either way: every session.add()/commit()
    # below only runs once process_turn has actually returned.
    try:
        result = await runtime.process_turn(session_id, payload.message, restore=initial_session)
    except Exception:
        logger.exception("simple_agent /start turn failed | session=%s", session_id)
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=_TURN_FAILED_DETAIL) from None

    record = SimpleAgentSessionRecord(session_id=session_id, patient_id=current_user.id)
    _apply_session_dict_to_record(record, serialize_session(runtime.export_session(session_id)))

    chat_session = SimpleAgentChatSession(
        session_id=session_id, patient_id=current_user.id, initial_message=payload.message,
        profile_id=payload.profile_id,
    )
    _apply_turn_outcome_to_chat_session(chat_session, result)
    patient_row, agent_row = _record_turn_messages(
        session_id=session_id, turn_index=0, patient_message=payload.message, result=result,
    )

    session.add(record)
    session.add(chat_session)
    session.add(patient_row)
    session.add(agent_row)
    await session.commit()

    return {"session_id": session_id, **result}


@router.post("/chat/{session_id}", status_code=status.HTTP_200_OK)
async def continue_simple_triage(
    session_id: str,
    payload: SimpleTriageMessageRequest,
    current_user: PatientUserDep,
    session: SessionDep,
) -> dict[str, Any]:
    _require_enabled()
    chat_session = (
        await session.execute(
            select(SimpleAgentChatSession).where(
                SimpleAgentChatSession.session_id == session_id,
                SimpleAgentChatSession.patient_id == current_user.id,
            )
        )
    ).scalars().first()
    if chat_session is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Phiên simple-triage không hợp lệ hoặc không thuộc về bạn.",
        )
    if chat_session.status == "COMPLETED":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Phiên này đã kết thúc. Vui lòng bắt đầu phiên mới nếu cần hỏi thêm.",
        )

    record = (
        await session.execute(select(SimpleAgentSessionRecord).where(SimpleAgentSessionRecord.session_id == session_id))
    ).scalars().first()
    if record is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Thiếu bản ghi trạng thái engine cho phiên này -- dữ liệu không nhất quán.",
        )

    runtime = get_simple_agent_runtime()
    restore = None if runtime.has_hot_session(session_id) else deserialize_session(_record_to_session_dict(record))

    # See the matching try/except in start_simple_triage above for why.
    try:
        result = await runtime.process_turn(session_id, payload.message, restore=restore)
    except Exception:
        logger.exception("simple_agent /chat turn failed | session=%s", session_id)
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=_TURN_FAILED_DETAIL) from None

    _apply_session_dict_to_record(record, serialize_session(runtime.export_session(session_id)))
    turn_index = chat_session.turn_count
    _apply_turn_outcome_to_chat_session(chat_session, result)
    patient_row, agent_row = _record_turn_messages(
        session_id=session_id, turn_index=turn_index, patient_message=payload.message, result=result,
    )

    session.add(record)
    session.add(chat_session)
    session.add(patient_row)
    session.add(agent_row)
    await session.commit()

    return {"session_id": session_id, **result}


@router.get("/sessions", status_code=status.HTTP_200_OK)
async def list_simple_triage_sessions(
    current_user: PatientUserDep,
    session: SessionDep,
) -> list[dict[str, Any]]:
    """List the current user's simple-triage sessions, most recent first."""
    _require_enabled()
    rows = (
        await session.execute(
            select(SimpleAgentChatSession)
            .where(SimpleAgentChatSession.patient_id == current_user.id)
            .order_by(SimpleAgentChatSession.last_activity_at.desc())
        )
    ).scalars().all()
    session_ids = [row.session_id for row in rows]
    review_map = await _review_info_by_session(session, session_ids)
    unread_map = await _unread_from_staff_by_session(session, session_ids)
    return [
        _chat_session_summary(row, review_map.get(row.session_id), unread_map.get(row.session_id, 0))
        for row in rows
    ]


@router.get("/sessions/{session_id}", status_code=status.HTTP_200_OK)
async def get_simple_triage_session(
    session_id: str,
    current_user: PatientUserDep,
    session: SessionDep,
) -> dict[str, Any]:
    """Session control/status plus its full message history, for inspection."""
    _require_enabled()
    chat_session = (
        await session.execute(
            select(SimpleAgentChatSession).where(
                SimpleAgentChatSession.session_id == session_id,
                SimpleAgentChatSession.patient_id == current_user.id,
            )
        )
    ).scalars().first()
    if chat_session is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Phiên simple-triage không hợp lệ hoặc không thuộc về bạn.",
        )
    messages = (
        await session.execute(
            select(SimpleAgentChatMessage)
            .where(
                SimpleAgentChatMessage.session_id == session_id,
                # Care-team messages (added later, see care-team section below)
                # live in this same table but are a separate conversation --
                # excluded here exactly like get_session_messages() excludes
                # CARE_TEAM_CHANNEL for the real ChatMessage table.
                or_(SimpleAgentChatMessage.channel == "TRIAGE", SimpleAgentChatMessage.channel.is_(None)),
            )
            .order_by(SimpleAgentChatMessage.turn_index, SimpleAgentChatMessage.created_at)
        )
    ).scalars().all()

    # Patient-facing SBAR, mirroring routes_nurse_simple.py's own build --
    # only once the session is actually finalised (never a mid-conversation
    # guess), computed at read-time only from already-persisted state, same
    # as the nurse route. None while still ACTIVE/ABANDONED.
    sbar: dict[str, Any] | None = None
    if chat_session.status == "COMPLETED":
        record = (
            await session.execute(
                select(SimpleAgentSessionRecord).where(SimpleAgentSessionRecord.session_id == session_id)
            )
        ).scalars().first()
        if record is not None:
            runtime = get_simple_agent_runtime()
            engine_session = deserialize_session(_record_to_session_dict(record))
            sbar = build_simple_agent_sbar(
                corpus=runtime.corpus,
                session=engine_session,
                initial_message=chat_session.initial_message,
                final_message=chat_session.final_message or "",
                matched_esi_levels=chat_session.matched_esi_levels,
            )

    review_info = (await _review_info_by_session(session, [session_id])).get(session_id)
    unread_map = await _unread_from_staff_by_session(session, [session_id])
    return {
        **_chat_session_summary(chat_session, review_info, unread_map.get(session_id, 0)),
        "sbar": sbar,
        "messages": [
            {
                "turn_index": m.turn_index,
                "sender": m.sender,
                "content": m.content,
                "route": m.route,
                "action": m.action,
                "question_target_id": m.question_target_id,
                # Full Phase B decision snapshot, already durably stored per
                # AGENT turn (see the write side in start/chat above) but
                # never surfaced until now -- exposing it lets the pilot UI
                # show *why* a given question was asked (matched concepts,
                # which protocol atom drove it, etc.) without re-running the
                # engine. `{}` for PATIENT rows (nothing snapshotted there).
                "decision_snapshot": m.decision_snapshot,
                "created_at": m.created_at.isoformat(),
            }
            for m in messages
        ],
    }


# Mirrors SimplePilotSbarAccordion.tsx's OPERATOR_SYMBOLS (frontend) --
# kept in sync manually since the PDF is rendered server-side, not via that
# component.
_CITATION_OPERATOR_SYMBOLS = {"EQ": "=", "NEQ": "≠", "GT": ">", "GTE": "≥", "LT": "<", "LTE": "≤"}


def _citation_to_pdf_text(citation: dict[str, Any]) -> str:
    """One ``sbar["citations"]`` entry (see sbar.py's ``_citation_entries`` --
    a dict, not a bare string) rendered as one readable line for the PDF.

    Real bug found and fixed here (2026-08-29): this route used to pass
    ``sbar.get("citations")`` straight into ``SbarPdfData.citations: tuple[str, ...]``
    with no conversion at all -- harmless while citations were bare atom-id
    strings, but citations became ``list[dict]`` on 2026-08-28 (status +
    satisfied_requirements, see sbar.py) and nothing here was updated to
    match. Every pilot PDF export with at least one citation (i.e. almost
    every completed session) has been crashing with
    ``TypeError: unhashable type: 'dict'`` inside ``build_sbar_pdf``'s
    ``dict.fromkeys(data.citations)`` ever since -- confirmed live. Unlike
    ``routes_pdf.py``'s production equivalent (a plain ``str(value)`` on an
    already-string citation), this shape needs real formatting, not just a
    cast.
    """
    text = citation.get("criteria_text") or citation.get("atom_id") or ""
    requirements = citation.get("satisfied_requirements") or []
    if requirements:
        detail = "; ".join(
            f"{req.get('name')} {_CITATION_OPERATOR_SYMBOLS.get(req.get('operator'), req.get('operator'))} "
            f"{req.get('expected_value')} (báo cáo: {req.get('actual_value')})"
            for req in requirements
        )
        text = f"{text} — {detail}" if text else detail
    return text.strip()


@router.get("/sessions/{session_id}/pdf", response_class=StreamingResponse, status_code=status.HTTP_200_OK)
async def export_simple_triage_pdf(
    session_id: str,
    current_user: PatientUserDep,
    session: SessionDep,
) -> StreamingResponse:
    """Download the pilot's own SBAR handoff PDF, reusing production's exact
    PDF engine (`services/sbar_pdf.SbarPdfData`/`build_sbar_pdf` -- a pure,
    stateless function, safe to call directly without touching that file or
    `routes_pdf.py`).

    Deliberately downloadable as soon as the session is COMPLETED (a real
    SBAR exists), *regardless* of nurse-review progress -- the patient asked
    to be able to get this before a nurse has looked at it. What changes is
    only the content: `_map_pilot_review_status`/`reviewer_name` feed
    straight into the PDF's own "TRẠNG THÁI HỒ SƠ" box
    (`services/sbar_pdf.py`'s `_review_label`), so an unreviewed case prints
    "Đang chờ thẩm định" / "Chưa ghi nhận người thẩm định" honestly instead
    of implying a review that hasn't happened.
    """
    _require_enabled()
    chat_session = await _get_owned_chat_session(session_id, current_user.id, session)
    if chat_session.status != "COMPLETED":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Ca khám chưa hoàn tất, chưa có bản tóm tắt SBAR để xuất.",
        )
    record = (
        await session.execute(select(SimpleAgentSessionRecord).where(SimpleAgentSessionRecord.session_id == session_id))
    ).scalars().first()
    if record is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Thiếu bản ghi trạng thái engine cho phiên này -- dữ liệu không nhất quán.",
        )
    runtime = get_simple_agent_runtime()
    engine_session = deserialize_session(_record_to_session_dict(record))
    sbar = build_simple_agent_sbar(
        corpus=runtime.corpus,
        session=engine_session,
        initial_message=chat_session.initial_message,
        final_message=chat_session.final_message or "",
        matched_esi_levels=chat_session.matched_esi_levels,
    )

    profile = None
    if chat_session.profile_id:
        profile = (
            await session.execute(select(EHRProfile).where(EHRProfile.id == chat_session.profile_id))
        ).scalars().first()

    review_info = (await _review_info_by_session(session, [session_id])).get(session_id)
    ai_proposed_esi = min(chat_session.matched_esi_levels) if chat_session.matched_esi_levels else None
    final_esi = review_info["final_esi"] if review_info else None
    review_status = _map_pilot_review_status(review_info)
    # Once the review is terminal, the persisted nurse decision is the
    # authoritative result.  Keep the AI proposal in separate PDF fields so
    # the export proves the transition instead of silently replacing it.
    esi_level = final_esi if review_status in {"APPROVED", "OVERRIDDEN"} else ai_proposed_esi

    pdf_data = SbarPdfData(
        session_id=chat_session.session_id,
        patient_name=profile.full_name if profile else current_user.full_name,
        age=profile.age if profile else None,
        gender=profile.gender if profile else None,
        relationship_type=profile.relationship_type if profile else None,
        created_at=chat_session.started_at,
        chief_complaint=chat_session.initial_message,
        esi_level=esi_level if esi_level in {1, 2, 3, 4, 5} else None,
        review_status=review_status,
        reviewer_name=review_info["reviewer_name"] if review_info else None,
        reviewed_at=review_info["reviewed_at"] if review_info else None,
        situation=str(sbar.get("situation") or "Chưa ghi nhận"),
        background=str(sbar.get("background") or "Chưa ghi nhận"),
        assessment=str(sbar.get("assessment") or "Chưa ghi nhận"),
        recommendation=str(sbar.get("recommendation") or "Chưa ghi nhận"),
        citations=tuple(
            text for citation in (sbar.get("citations") or []) if (text := _citation_to_pdf_text(citation))
        ),
        ai_proposed_esi=ai_proposed_esi if ai_proposed_esi in {1, 2, 3, 4, 5} else None,
        final_esi=final_esi if final_esi in {1, 2, 3, 4, 5} else None,
        decision_type=review_info["decision_type"] if review_info else None,
        decision_reason_code=review_info["decision_reason_code"] if review_info else None,
        decision_note=review_info["decision_note"] if review_info else None,
    )

    try:
        pdf_bytes = await asyncify(build_sbar_pdf)(pdf_data)
    except RuntimeError:
        # NOT 503: handlePilotApiError (frontend) already hardcodes 503 to
        # mean "SIMPLE_AGENT_ENABLED=false" (see _require_enabled above) --
        # reusing it here would silently mislabel a real PDF-engine failure
        # as "pilot disabled" (same class of collision fixed in the turn-
        # processing try/except blocks above this route).
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Máy chủ chưa sẵn sàng để xuất PDF Unicode.",
        ) from None

    return StreamingResponse(
        io.BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="Phieu_SBAR_Pilot_{chat_session.session_id[-8:]}.pdf"',
            "Content-Length": str(len(pdf_bytes)),
            "Cache-Control": "private, no-store",
            "X-Content-Type-Options": "nosniff",
        },
    )


# -- care-team chat (patient <-> nurse), added on top of the same table -----
#
# Mirrors routes_patient.py's message-to-staff/mark-staff-read/care-team
# triad, but on SimpleAgentChatMessage (channel=CARE_TEAM) instead of the
# real ChatMessage table -- see routes_nurse_simple.py for the nurse-side
# counterpart and .claude/plans/sunny-launching-mitten.md for the full design.


async def _get_owned_chat_session(
    session_id: str, current_user_id: str, session: SessionDep
) -> SimpleAgentChatSession:
    chat_session = (
        await session.execute(
            select(SimpleAgentChatSession).where(
                SimpleAgentChatSession.session_id == session_id,
                SimpleAgentChatSession.patient_id == current_user_id,
            )
        )
    ).scalars().first()
    if chat_session is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Phiên simple-triage không hợp lệ hoặc không thuộc về bạn.",
        )
    return chat_session


async def _review_status(session_id: str, session: SessionDep) -> str | None:
    review = (
        await session.execute(
            select(SimpleAgentNurseReview).where(SimpleAgentNurseReview.session_id == session_id)
        )
    ).scalars().first()
    return review.review_status if review else None


async def _find_by_client_message_id(
    session_id: str, client_message_id: str | None, session: SessionDep
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


async def _staff_conversation(session_id: str, session: SessionDep) -> dict[str, Any]:
    unread = (
        await session.execute(
            select(SimpleAgentChatMessage).where(
                SimpleAgentChatMessage.session_id == session_id,
                SimpleAgentChatMessage.channel == _CARE_TEAM_CHANNEL,
                SimpleAgentChatMessage.sender == "NURSE",
                SimpleAgentChatMessage.read_at.is_(None),
            )
        )
    ).scalars().all()
    return {"session_id": session_id, "unread_from_staff": len(unread)}


@router.post("/chat/{session_id}/message-to-staff", status_code=status.HTTP_201_CREATED)
async def send_message_to_staff(
    session_id: str,
    payload: SendStaffMessageRequest,
    current_user: PatientUserDep,
    session: SessionDep,
) -> dict[str, Any]:
    _require_enabled()
    chat_session = await _get_owned_chat_session(session_id, current_user.id, session)
    if chat_session.status != "COMPLETED":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Chỉ có thể nhắn cho nhân viên y tế sau khi phiên đã kết thúc và đang chờ thẩm định.",
        )
    if await _review_status(session_id, session) == _REVIEW_HANDED_OFF:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Ca đã được đóng, không thể nhắn thêm.")

    existing = await _find_by_client_message_id(session_id, payload.client_message_id, session)
    if existing is not None:
        return await _staff_conversation(session_id, session)

    session.add(
        SimpleAgentChatMessage(
            session_id=session_id,
            turn_index=chat_session.turn_count,
            sender="PATIENT",
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
        simple_case_topic(session_id), EVENT_MESSAGE_CREATED, {"session_id": session_id, "sender": "PATIENT"}
    )
    await bus.publish(
        SIMPLE_STAFF_QUEUE_TOPIC, EVENT_MESSAGE_CREATED, {"session_id": session_id, "sender": "PATIENT"}
    )
    return await _staff_conversation(session_id, session)


@router.post("/chat/{session_id}/mark-staff-read", status_code=status.HTTP_200_OK)
async def mark_staff_messages_read(
    session_id: str,
    current_user: PatientUserDep,
    session: SessionDep,
) -> dict[str, Any]:
    _require_enabled()
    await _get_owned_chat_session(session_id, current_user.id, session)
    unread = (
        await session.execute(
            select(SimpleAgentChatMessage).where(
                SimpleAgentChatMessage.session_id == session_id,
                SimpleAgentChatMessage.channel == _CARE_TEAM_CHANNEL,
                SimpleAgentChatMessage.sender == "NURSE",
                SimpleAgentChatMessage.read_at.is_(None),
            )
        )
    ).scalars().all()
    now = get_utc_now()
    for row in unread:
        row.read_at = now
    await session.commit()
    return await _staff_conversation(session_id, session)


@router.get("/chat/{session_id}/care-team", status_code=status.HTTP_200_OK)
async def get_care_team_thread(
    session_id: str,
    current_user: PatientUserDep,
    session: SessionDep,
) -> dict[str, Any]:
    _require_enabled()
    await _get_owned_chat_session(session_id, current_user.id, session)
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
    unread = sum(1 for row in rows if row.sender == "NURSE" and row.read_at is None)
    return {
        "session_id": session_id,
        "unread_from_staff": unread,
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
