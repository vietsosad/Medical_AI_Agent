"""Patient verification gate before any non-emergency ESI reasoning."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from src.agents.clinical_state_view import ClinicalStateView
from src.agents.confirmation_lifecycle import fact_snapshot
from src.agents.nodes.fact_extraction import describe_fact_key
from src.agents.state import AgentState


def _acknowledged_facts(state: AgentState) -> list[str]:
    """Name, in the patient's language, what this turn actually recorded."""
    described: list[str] = []
    for record in state.get("pending_fact_updates") or []:
        if not isinstance(record, dict):
            continue
        field = str(record.get("field") or "")
        value = record.get("value")
        if not field or value is None or value == "":
            continue
        label = describe_fact_key(field.replace("vital_signs.", "vital."))
        text = f"{label}: {value}"
        if text not in described:
            described.append(text)
    return described[:4]


def build_intake_summary(
    blueprint: dict[str, Any],
    clinical_memory: dict[str, Any] | None = None,
    *,
    clinical_memory_confirmation_status: str = "NOT_REVIEWED",
    clinical_memory_updated_at: str | None = None,
    vital_signs_status: str = "NOT_REVIEWED",
    uncertain_symptoms: list[str] | None = None,
) -> dict[str, Any]:
    """Return only patient-facing facts collected during intake.

    ``uncertain_symptoms`` are things the patient hedged -- "hơi chóng mặt".
    They are deliberately not promoted into ``chief_complaint``, because a
    hedge is not an affirmation and the projection is right to exclude them.
    But the review is the one place the patient can correct our reading of what
    they said, so a symptom they mentioned and we recorded as uncertain has to
    be visible there. Omitting it means they cannot confirm it, cannot deny it,
    and cannot tell that it was heard at all.
    """
    return {
        "uncertain_symptoms": [
            str(item).strip()
            for item in (uncertain_symptoms or [])
            if str(item).strip()
        ],
        "chief_complaint": [
            str(item).strip()
            for item in blueprint.get("chief_complaint", [])
            if str(item).strip()
        ],
        "onset_time": str(blueprint.get("onset_time") or "").strip() or None,
        "severity_score": blueprint.get("severity_score"),
        "radiation": str(blueprint.get("radiation") or "").strip() or None,
        "associated_symptoms": [
            str(item).strip()
            for item in blueprint.get("associated_symptoms", [])
            if str(item).strip()
        ],
        "current_medication": [
            str(item).strip()
            for item in blueprint.get("current_medication", [])
            if str(item).strip()
        ],
        "recent_procedure": str(blueprint.get("recent_procedure") or "").strip() or None,
        "vital_signs": dict(blueprint.get("vital_signs", {})),
        "vital_signs_status": vital_signs_status,
        "vital_signs_source": blueprint.get("vital_signs_source"),
        "vital_signs_measured_at": blueprint.get("vital_signs_measured_at"),
        "ehr_snapshot": {
            "age": (clinical_memory or {}).get("age"),
            "gender": (clinical_memory or {}).get("gender"),
            "height_cm": (clinical_memory or {}).get("height_cm"),
            "weight_kg": (clinical_memory or {}).get("weight_kg"),
            "bmi": (clinical_memory or {}).get("bmi"),
            "blood_type": (clinical_memory or {}).get("blood_type"),
            "chronic_conditions": list(
                (clinical_memory or {}).get("chronic_conditions", [])
            ),
            "allergies": list((clinical_memory or {}).get("allergies", [])),
            "daily_medications": list(
                (clinical_memory or {}).get("daily_medications", [])
            ),
            "updated_at": clinical_memory_updated_at,
            "confirmation_status": clinical_memory_confirmation_status,
            "patient_context_note": (
                str(blueprint.get("clinical_context_note") or "").strip() or None
            ),
        },
    }


async def request_patient_confirmation_node(state: AgentState) -> dict[str, Any]:
    """Pause normal triage until the patient verifies the collected facts."""
    view = ClinicalStateView.from_agent_state(state)
    intake_summary = build_intake_summary(
        state.get("clinical_blueprint", {}),
        state.get("clinical_memory", {}),
        clinical_memory_confirmation_status=state.get(
            "clinical_memory_confirmation_status",
            "NOT_REVIEWED",
        ),
        clinical_memory_updated_at=state.get("clinical_memory_updated_at"),
        vital_signs_status=state.get("vital_signs_status", "NOT_REVIEWED"),
        uncertain_symptoms=[
            describe_fact_key(f"symptom.{concept}")
            for concept in view.uncertain_symptoms()
        ],
    )
    # How many times this patient has already been shown the review. Repeating
    # a message word for word after someone answers it is the clearest way for
    # software to say it was not listening: the patient cannot tell whether
    # their reply was recorded, rejected, or lost, so they answer again and the
    # exchange stalls. The second and later prompts therefore say explicitly
    # what was taken in and what "confirm" means here.
    prompt_count = int(state.get("intake_confirmation_prompt_count") or 0)
    if prompt_count == 0:
        response = (
            "Mình đã thu thập đủ thông tin ban đầu. Vui lòng kiểm tra bản tóm tắt bên dưới, "
            "sửa hoặc bổ sung nếu cần, rồi xác nhận để AI mới bắt đầu phân loại mức độ ưu tiên."
        )
    else:
        recorded = _acknowledged_facts(state)
        acknowledgement = (
            "Mình đã ghi nhận thêm — " + "; ".join(recorded) + ". "
            if recorded
            else "Bản tóm tắt bên dưới vẫn giữ nguyên vì chưa có dữ kiện mới. "
        )
        response = (
            f"{acknowledgement}"
            "Mình vẫn chưa nhận được xác nhận của bạn cho bản tóm tắt này, nên "
            "chưa thể bắt đầu phân loại mức độ ưu tiên. Bạn hãy bấm nút xác nhận "
            "bên dưới; nếu còn chi tiết chưa đúng hoặc còn thiếu, cứ nhắn thêm "
            "trước khi xác nhận."
        )
    message = {
        "id": str(uuid.uuid4()),
        "sender": "bot",
        "timestamp": datetime.now(UTC).isoformat(),
        "content": response,
        "step": 3,
        "intakeSummary": intake_summary,
    }
    return {
        "step": 3,
        "response": response,
        "messages": [message],
        "structured_question": None,
        "active_question": None,
        "intake_summary": intake_summary,
        "intake_confirmation_prompt_count": prompt_count + 1,
        # Which facts this review was built for. A reconnect, a refetch or a
        # duplicate submit that changes nothing produces the same snapshot, and
        # the readiness gate uses that to tell a genuinely new review from the
        # same one arriving again.
        "intake_review_shown_snapshot": fact_snapshot(view),
        "patient_confirmed_intake": False,
        "intake_confirmation_status": "AWAITING_CONFIRMATION",
        "response_type": "INTAKE_REVIEW",
        "workflow_phase": "PATIENT_CONFIRMATION",
        "decision_status": "AWAITING_PATIENT_CONFIRMATION",
        "current_esi_level": None,
        "sbar_report": None,
        "turn_rag_citations": [],
        "next_step": "wait_for_patient_confirmation",
    }
