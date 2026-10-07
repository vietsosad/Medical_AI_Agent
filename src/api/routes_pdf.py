"""Authenticated export endpoint for the canonical SBAR handoff PDF."""

import io

from asyncer import asyncify
from fastapi import APIRouter, HTTPException, status
from fastapi.responses import StreamingResponse
from sqlmodel import select

from src.api.dependencies import CurrentUserDep, SessionDep
from src.models.db_models import EHRProfile, NurseReviewState, TriageCase, User
from src.services.clinical_text import normalize_clinical_display_text
from src.services.sbar_pdf import SbarPdfData, build_sbar_pdf

router = APIRouter(prefix="/triage", tags=["Triage PDF Export"])


def _review_status(case_doc: TriageCase, review: NurseReviewState | None = None) -> str:
    if case_doc.status == "RED_FLAG_LOCKED":
        return "EMERGENCY_REJECTED"
    if case_doc.is_overridden:
        return "OVERRIDDEN"
    if case_doc.status == "COMPLETED" or (review is not None and review.review_status in {"TRIAGE_DECIDED", "HANDED_OFF"}):
        return "APPROVED"
    return "PENDING_REVIEW"


@router.get(
    "/session/{session_id}/pdf",
    response_class=StreamingResponse,
    status_code=status.HTTP_200_OK,
)
async def export_triage_pdf(
    session_id: str,
    current_user: CurrentUserDep,
    session: SessionDep,
) -> StreamingResponse:
    """Download one Unicode-safe A4 SBAR handoff generated from persisted data."""

    case_result = await session.execute(
        select(TriageCase).where(
            TriageCase.id == session_id,
            TriageCase.patient_id == current_user.id,
        )
    )
    case_doc = case_result.scalars().first()
    if not case_doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Không tìm thấy phiên khám.",
        )

    if not isinstance(case_doc.sbar_summary, dict):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Phiên khám chưa có bản tóm tắt SBAR hoàn chỉnh.",
        )

    profile = None
    if case_doc.profile_id:
        profile_result = await session.execute(
            select(EHRProfile).where(EHRProfile.id == case_doc.profile_id)
        )
        profile = profile_result.scalars().first()

    review = (
        await session.execute(
            select(NurseReviewState).where(NurseReviewState.triage_case_id == case_doc.id)
        )
    ).scalars().first()

    reviewer = None
    reviewer_id = review.assigned_nurse_id if review and review.assigned_nurse_id else case_doc.assigned_nurse_id
    if reviewer_id:
        reviewer_result = await session.execute(
            select(User).where(User.id == reviewer_id)
        )
        reviewer = reviewer_result.scalars().first()

    sbar = case_doc.sbar_summary
    raw_citations = sbar.get("citations") or case_doc.rag_citations or []
    citation_values = (
        raw_citations
        if isinstance(raw_citations, (list, tuple))
        else [raw_citations]
    )
    citations = tuple(
        str(value).strip()
        for value in citation_values
        if str(value).strip()
    )
    review_status = _review_status(case_doc, review)
    final_esi = case_doc.final_clinical_esi
    esi_level = final_esi if review_status in {"APPROVED", "OVERRIDDEN"} else case_doc.ai_proposed_esi

    pdf_data = SbarPdfData(
        session_id=case_doc.id,
        patient_name=(profile.full_name if profile else current_user.full_name),
        age=profile.age if profile else None,
        gender=profile.gender if profile else None,
        relationship_type=profile.relationship_type if profile else None,
        created_at=case_doc.created_at,
        chief_complaint=case_doc.session_title or "Chưa ghi nhận",
        esi_level=esi_level if esi_level in {1, 2, 3, 4, 5} else None,
        review_status=review_status,
        reviewer_name=reviewer.full_name if reviewer else None,
        reviewed_at=(review.decided_at if review and review.decided_at else case_doc.reviewed_at),
        situation=normalize_clinical_display_text(str(sbar.get("situation") or "Chưa ghi nhận")),
        background=normalize_clinical_display_text(str(sbar.get("background") or "Chưa ghi nhận")),
        assessment=normalize_clinical_display_text(str(sbar.get("assessment") or "Chưa ghi nhận")),
        recommendation=normalize_clinical_display_text(str(sbar.get("recommendation") or "Chưa ghi nhận")),
        citations=citations,
        ai_proposed_esi=(
            case_doc.ai_proposed_esi if case_doc.ai_proposed_esi in {1, 2, 3, 4, 5} else None
        ),
        final_esi=final_esi if final_esi in {1, 2, 3, 4, 5} else None,
        decision_type=review.decision_type if review else None,
        decision_reason_code=review.decision_reason_code if review else None,
        decision_note=review.decision_note if review else None,
    )

    try:
        pdf_bytes = await asyncify(build_sbar_pdf)(pdf_data)
    except RuntimeError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Máy chủ chưa sẵn sàng để xuất PDF Unicode.",
        ) from exc

    filename = f"Phieu_SBAR_{case_doc.id[-8:]}.pdf"
    headers = {
        "Content-Disposition": f'attachment; filename="{filename}"',
        "Content-Length": str(len(pdf_bytes)),
        "Cache-Control": "private, no-store",
        "X-Content-Type-Options": "nosniff",
    }
    return StreamingResponse(
        io.BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers=headers,
    )
