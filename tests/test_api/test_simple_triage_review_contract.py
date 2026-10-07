from datetime import datetime

from src.api.routes_simple_triage import _chat_session_summary
from src.models.db_models import SimpleAgentChatSession


def test_patient_summary_exposes_the_persisted_nurse_decision() -> None:
    chat_session = SimpleAgentChatSession(
        session_id="pilot-case-1",
        patient_id="patient-1",
        status="COMPLETED",
        initial_message="Đau đầu nhiều",
        matched_esi_levels=[4],
    )
    summary = _chat_session_summary(
        chat_session,
        {
            "review_status": "HANDED_OFF",
            "is_overridden": True,
            "final_esi": 2,
            "decision_type": "ADJUST_ESI",
            "decision_reason_code": "ADDITIONAL_CLINICAL_JUDGMENT",
            "decision_note": "Đau tăng nhanh, cần đánh giá ưu tiên.",
            "reviewer_name": "Điều dưỡng Minh Anh",
            "reviewed_at": datetime(2026, 8, 31, 9, 30),
        },
    )

    assert summary["review_display_status"] == "OVERRIDDEN"
    assert summary["final_esi"] == 2
    assert summary["decision_type"] == "ADJUST_ESI"
    assert summary["decision_note"] == "Đau tăng nhanh, cần đánh giá ưu tiên."
    assert summary["reviewer_name"] == "Điều dưỡng Minh Anh"
    assert summary["reviewed_at"] == "2026-08-31T09:30:00Z"
