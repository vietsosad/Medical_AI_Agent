"""Adaptive question planning: free text by default, choices only when useful."""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from src.agents.nodes.adaptive_questions import (
    opening_acknowledgement,
    render_question,
)
from src.agents.nodes.fact_extraction import (
    FIELD_DISPLAY_VI,
    SYMPTOM_DISPLAY_VI,
    describe_fact_key,
)
from src.agents.problem_state import (
    ProblemState,
    build_problem_state_from_agent_state,
)
from src.agents.state import AgentState


@dataclass(frozen=True)
class PlannedQuestion:
    field: str
    text: str
    structured_payload: dict[str, Any] | None


def _option(
    option_id: str,
    label: str,
    value: str,
    *,
    is_risk: bool = False,
    is_exclusive: bool = False,
) -> dict[str, Any]:
    return {
        "id": option_id,
        "label": label,
        "value": value,
        "isRisk": is_risk,
        "isExclusive": is_exclusive,
    }


def _contradiction_question(field: str) -> PlannedQuestion:
    """Ask the patient to settle one named conflict without leaking its key."""
    label = describe_fact_key(field)
    return PlannedQuestion(
        field=f"contradiction_{field}",
        text=(
            f"Mình nhận được hai thông tin khác nhau về {label}. "
            "Bạn vui lòng xác nhận thông tin nào đúng với triệu chứng chính đang được sàng lọc?"
        ),
        structured_payload=None,
    )


def _symptom_question(target: str) -> PlannedQuestion:
    """Turn a canonical symptom uncertainty into one bounded patient question."""
    label = describe_fact_key(target)
    option_suffix = target.removeprefix("symptom.").replace(".", "_")
    return PlannedQuestion(
        # The answer validator and deterministic extractor already understand
        # this public slot. The planner target remains canonical in
        # ``selected_action``; no internal key is exposed to the patient.
        field="associated_symptoms",
        text=f"Bạn có thấy {label} kèm theo không?",
        structured_payload={
            "type": "single_choice",
            "optionsType": "single",
            "options": [
                _option(
                    f"{option_suffix}_yes",
                    f"Có {label}",
                    f"Có {label}",
                ),
                _option(
                    f"{option_suffix}_no",
                    f"Không có {label}",
                    f"Không có {label}",
                ),
                _option(
                    f"{option_suffix}_unsure",
                    "Tôi không chắc",
                    f"Tôi không chắc có {label}",
                ),
            ],
            "submitted": False,
        },
    )


def _adaptive_question(
    target: str,
    problem_state: ProblemState | None,
) -> PlannedQuestion | None:
    """Render an adaptive planner target, or None if it is not one."""
    attribute = target.split(".", 1)[1] if "." in target else ""
    label = ""
    if problem_state is not None and "." in target:
        concept = target.split(".", 1)[0]
        problem = problem_state.problem(concept)
        if problem is not None:
            label = problem.label_vi
    if target.startswith(("symptom.", "vital.")):
        # A symptom probe and a vitals request already have bounded slots that
        # the answer validator, the deterministic extractor and cold session
        # recovery all understand. Rewording them as free text would gain a
        # slightly more natural sentence and lose the structured payload a
        # question needs to survive a checkpoint, so they keep their slot and
        # only their wording is improved below.
        return None
    if not label:
        return None

    rendered = render_question(target, attribute, label)
    if rendered is None:
        return None
    return PlannedQuestion(
        field=rendered.field,
        text=rendered.text,
        structured_payload=rendered.structured_payload,
    )


# Legacy workflow slots that describe an attribute of a specific problem. The
# adaptive renderer already has patient-facing wording for each.
_GLOBAL_SLOT_ATTRIBUTES: dict[str, str] = {
    "onset_time": "onset_time",
    "severity_score": "severity_score",
    "radiation": "radiation",
}


def _named_global_question(
    target: str,
    problem_state: ProblemState | None,
) -> PlannedQuestion | None:
    """Render a global slot as a question about the primary problem."""
    attribute = _GLOBAL_SLOT_ATTRIBUTES.get(target)
    if attribute is None or problem_state is None:
        return None
    primary = problem_state.primary
    if primary is None or len(problem_state.active_problems) < 2:
        # One problem needs no disambiguation, and the existing wording for a
        # single complaint reads better than a templated one.
        return None
    rendered = render_question(target, attribute, primary.label_vi)
    if rendered is None:
        return None
    return PlannedQuestion(
        field=target,
        text=rendered.text,
        structured_payload=rendered.structured_payload,
    )


def _is_supported_fact_key(field: str) -> bool:
    if field in FIELD_DISPLAY_VI:
        return True
    for prefix in ("symptom.", "complaint.", "associated."):
        if field.startswith(prefix):
            return field.removeprefix(prefix) in SYMPTOM_DISPLAY_VI
    return field in SYMPTOM_DISPLAY_VI


def build_targeted_question(
    target: str,
    blueprint: dict[str, Any],
    clinical_memory: dict[str, Any] | None = None,
    *,
    problem_state: ProblemState | None = None,
    lead_in: str = "",
) -> PlannedQuestion | None:
    """Build one question for an explicitly selected, bounded target.

    ``None`` means the target is not part of the question engine's authorised
    vocabulary. Callers must then use the ordinary missing-field fallback; an
    arbitrary planner string must never become patient-facing text.
    """
    normalized = str(target or "").strip()
    if not normalized:
        return None

    # Adaptive targets first. These name a problem and one of its attributes
    # ("headache.course"), which the fixed slot vocabulary below has no way to
    # express -- it only knows the six workflow slots the old fixed sequence
    # walked.
    adaptive = _adaptive_question(normalized, problem_state)
    if adaptive is not None:
        return adaptive

    if normalized.startswith("contradiction_"):
        field = normalized.removeprefix("contradiction_")
        return _contradiction_question(field) if _is_supported_fact_key(field) else None
    if normalized.startswith("contradiction:"):
        field = normalized.split(":", 1)[1]
        return _contradiction_question(field) if _is_supported_fact_key(field) else None

    # These are the bounded workflow slots already understood by the answer
    # validator. Supplying only the selected target prevents the legacy fixed
    # ordering inside ``plan_next_question`` from overriding the planner.
    direct_targets = {
        "chief_complaint",
        "onset_time",
        "severity_score",
        "associated_symptoms",
        "vital_signs",
        "clinical_detail",
        "recent_procedure_context",
        "clinical_memory_update_detail",
        "clinical_memory_confirmation",
    }
    if normalized in direct_targets:
        # A global slot still names one problem when the case has one. With two
        # or three active problems "triệu chứng này bắt đầu khi nào?" is a
        # question the patient cannot answer unambiguously and whose answer
        # cannot be attributed. The slot -- and therefore the answer binding --
        # is unchanged; only the wording names what is being asked about.
        named = _named_global_question(normalized, problem_state)
        if named is not None:
            return named
        return plan_next_question(
            blueprint,
            [normalized],
            clinical_memory,
        )
    if normalized == "recent_procedure":
        return plan_next_question(
            blueprint,
            ["recent_procedure_context"],
            clinical_memory,
        )
    if normalized == "radiation":
        return PlannedQuestion(
            field="radiation",
            text=(
                "Cảm giác khó chịu hoặc cơn đau có lan sang vị trí nào khác không? "
                "Nếu không lan, bạn hãy nói rõ là không lan."
            ),
            structured_payload=None,
        )

    if normalized.startswith(("symptom.", "associated.")) and _is_supported_fact_key(
        normalized
    ):
        return _symptom_question(normalized)

    if normalized.startswith("vital.") and normalized in FIELD_DISPLAY_VI:
        label = describe_fact_key(normalized)
        return PlannedQuestion(
            field="vital_signs",
            text=(
                f"Bạn vui lòng cho biết số đo {label} hiện tại. "
                "Nếu chưa đo được, hãy nói rõ là chưa có số đo."
            ),
            structured_payload=None,
        )

    if normalized == "red_flag_context":
        return PlannedQuestion(
            field="red_flag_context",
            text=(
                "Bạn vui lòng mô tả rõ dấu hiệu đáng lo đang có ngay lúc này, "
                "dấu hiệu bắt đầu khi nào và đang tăng lên hay giảm đi."
            ),
            structured_payload=None,
        )

    if normalized == "entity_reference":
        return PlannedQuestion(
            field="chief_complaint",
            text=(
                "Bạn đang nhắc đến triệu chứng nào trong các triệu chứng đã kể? "
                "Hãy nêu tên triệu chứng để mình ghi nhận đúng."
            ),
            structured_payload=None,
        )

    return None


def plan_next_question(
    blueprint: dict[str, Any],
    missing_fields: list[str],
    clinical_memory: dict[str, Any] | None = None,
    *,
    preferred_target: str | None = None,
    problem_state: ProblemState | None = None,
    lead_in: str = "",
) -> PlannedQuestion:
    """Pick one highest-value clarification and avoid invented multiple choice."""
    if preferred_target:
        targeted = build_targeted_question(
            preferred_target,
            blueprint,
            clinical_memory,
            problem_state=problem_state,
            lead_in=lead_in,
        )
        if targeted is not None:
            return targeted

    missing = set(missing_fields)
    contradiction_fields = [
        item.split(":", 1)[1]
        for item in missing_fields
        if item.startswith("contradiction:") and ":" in item
    ]
    if contradiction_fields:
        # Always resolved through the shared Vietnamese vocabulary. The old
        # fallback printed the raw key with underscores swapped for spaces,
        # which put "complaint.abdominal pain" in front of a Vietnamese
        # patient -- an internal identifier, in English, in a clinical
        # question. No patient-facing string is built from a key again.
        return _contradiction_question(contradiction_fields[0])
    if "chief_complaint" in missing:
        return PlannedQuestion(
            field="chief_complaint",
            text=(
                "Bạn đang khó chịu rõ nhất ở triệu chứng nào? Hãy mô tả bằng lời của bạn, "
                "ví dụ vị trí khó chịu và cảm giác đang gặp."
            ),
            structured_payload=None,
        )

    if "onset_time" in missing:
        return PlannedQuestion(
            field="onset_time",
            text="Triệu chứng này bắt đầu từ khoảng thời gian nào?",
            structured_payload={
                "type": "single_choice",
                "optionsType": "single",
                "options": [
                    _option("onset_hours", "Trong vài giờ gần đây", "Trong vài giờ gần đây"),
                    _option("onset_today", "Từ hôm nay", "Từ hôm nay"),
                    _option("onset_yesterday", "Từ hôm qua", "Từ hôm qua"),
                    _option("onset_days", "Đã vài ngày hoặc lâu hơn", "Đã vài ngày hoặc lâu hơn"),
                    _option("onset_unsure", "Tôi không chắc", "Không rõ thời điểm"),
                ],
                "submitted": False,
            },
        )

    if "recent_procedure_context" in missing:
        return PlannedQuestion(
            field="recent_procedure",
            text=(
                "Mình đã ghi nhận bạn vừa phẫu thuật/thủ thuật; thông tin này không "
                "được xem là câu trả lời ‘không có dấu hiệu kèm’. Bạn phẫu thuật gì, "
                "vào khi nào, và hiện có đau tăng, sốt, chảy dịch/chảy máu hoặc khó thở không?"
            ),
            structured_payload=None,
        )

    complaints = " ".join(str(item).lower() for item in blueprint.get("chief_complaint", []))
    if (
        "severity_score" in missing
        or (
            "clinical_detail" in missing
            and "đau" in complaints
            and blueprint.get("severity_score") is None
        )
    ):
        severity_label = "mức đau" if "đau" in complaints else "mức độ khó chịu"
        return PlannedQuestion(
            field="severity_score",
            text=(
                f"Nếu chấm {severity_label} của triệu chứng chính từ 0 đến 10, "
                "hiện tại bạn ở mức nào?"
            ),
            structured_payload={
                "type": "scale",
                "optionsType": "scale",
                "minScale": 0,
                "maxScale": 10,
                "submitted": False,
            },
        )

    if "associated_symptoms" in missing or "clinical_detail" in missing:
        return PlannedQuestion(
            field="associated_symptoms",
            text=(
                "Ngoài triệu chứng chính, bạn có dấu hiệu nào đi kèm không? "
                "Bạn có thể chọn nhanh hoặc mô tả dấu hiệu khác bằng ô nhập bên dưới."
            ),
            structured_payload={
                "type": "multi_choice",
                "optionsType": "multiple",
                "options": [
                    _option("associated_fever", "Sốt hoặc rét run", "Sốt hoặc rét run"),
                    _option("associated_nausea", "Buồn nôn hoặc nôn", "Buồn nôn hoặc nôn"),
                    _option("associated_dizzy", "Chóng mặt hoặc choáng", "Chóng mặt hoặc choáng"),
                    _option(
                        "associated_none",
                        "Không có dấu hiệu khác",
                        "Không có dấu hiệu khác",
                        is_exclusive=True,
                    ),
                    _option(
                        "associated_unsure",
                        "Tôi không chắc",
                        "Không rõ triệu chứng đi kèm",
                        is_exclusive=True,
                    ),
                ],
                "submitted": False,
            },
        )

    if "vital_signs" in missing:
        return PlannedQuestion(
            field="vital_signs",
            text=(
                "Bạn đã có số đo sinh hiệu gần đây chưa? Chọn ‘Đã có số đo’ để mở "
                "biểu mẫu huyết áp, mạch, SpO₂, nhiệt độ, nhịp thở và tri giác; "
                "nếu chưa đo, chọn ‘Chưa có số đo’. AI sẽ không tự điền giá trị."
            ),
            structured_payload={
                "type": "vitals_form",
                "optionsType": "vitals_form",
                "fields": [
                    {
                        "id": "heart_rate",
                        "label": "Mạch",
                        "unit": "lần/phút",
                        "placeholder": "Ví dụ: 82",
                        "inputMode": "numeric",
                        "min": 20,
                        "max": 250,
                        "step": 1,
                    },
                    {
                        "id": "blood_pressure",
                        "label": "Huyết áp",
                        "unit": "mmHg",
                        "placeholder": "Ví dụ: 118/76",
                        "inputMode": "text",
                    },
                    {
                        "id": "respiratory_rate",
                        "label": "Nhịp thở",
                        "unit": "lần/phút",
                        "placeholder": "Ví dụ: 18",
                        "inputMode": "numeric",
                        "min": 5,
                        "max": 80,
                        "step": 1,
                    },
                    {
                        "id": "spo2",
                        "label": "SpO₂",
                        "unit": "%",
                        "placeholder": "Ví dụ: 97",
                        "inputMode": "numeric",
                        "min": 50,
                        "max": 100,
                        "step": 1,
                    },
                    {
                        "id": "temperature_c",
                        "label": "Nhiệt độ",
                        "unit": "°C",
                        "placeholder": "Ví dụ: 37.2",
                        "inputMode": "decimal",
                        "min": 30,
                        "max": 45,
                        "step": 0.1,
                    },
                    {
                        "id": "gcs",
                        "label": "Tri giác (GCS)",
                        "unit": "điểm",
                        "placeholder": "Từ 3 đến 15",
                        "inputMode": "numeric",
                        "min": 3,
                        "max": 15,
                        "step": 1,
                    },
                ],
                "submitted": False,
            },
        )

    if "clinical_memory_update_detail" in missing:
        return PlannedQuestion(
            field="clinical_memory_update_detail",
            text=(
                "Bạn cho biết phần nào đã thay đổi: bệnh nền, dị ứng hay thuốc đang dùng? "
                "Hãy ghi tên thông tin hiện tại; lượt khai này chỉ được gắn vào ca và không tự ghi đè EHR."
            ),
            structured_payload=None,
        )

    if "clinical_memory_confirmation" in missing:
        memory = clinical_memory or {}
        return PlannedQuestion(
            field="clinical_memory_confirmation",
            text="Xác nhận hồ sơ sức khỏe hiện tại",
            structured_payload={
                "type": "single_choice",
                "optionsType": "single",
                "ehrSnapshot": {
                    "age": memory.get("age"),
                    "gender": memory.get("gender"),
                    "height_cm": memory.get("height_cm"),
                    "weight_kg": memory.get("weight_kg"),
                    "bmi": memory.get("bmi"),
                    "blood_type": memory.get("blood_type"),
                    "chronic_conditions": list(
                        memory.get("chronic_conditions", [])
                    ),
                    "allergies": list(memory.get("allergies", [])),
                    "daily_medications": list(
                        memory.get("daily_medications", [])
                    ),
                },
                "options": [
                    _option("ehr_confirmed", "Vẫn đúng, không thay đổi", "Thông tin EHR hiện tại vẫn đúng"),
                    _option("ehr_changed", "Có thông tin đã thay đổi", "Thông tin EHR đã thay đổi"),
                    _option("ehr_unsure", "Tôi không chắc", "Tôi không chắc thông tin EHR còn đúng"),
                ],
                "submitted": False,
            },
        )

    # This should be unreachable for the current readiness contract. Never
    # reopen EHR as a generic fallback because it creates an infinite loop
    # after the profile has already been confirmed.
    return PlannedQuestion(
        field="associated_symptoms",
        text=(
            "Mình cần thêm một chi tiết lâm sàng để tiếp tục. "
            "Bạn hãy mô tả dấu hiệu khó chịu khác đang có, hoặc cho biết nếu không có."
        ),
        structured_payload=None,
    )


async def run_question_engine_node(
    state: AgentState,
    *,
    target: str | None = None,
) -> dict[str, Any]:
    """Render one question, honoring an explicit or selected planner target."""
    selected_target = target
    if selected_target is None:
        selected_target = str(
            (state.get("selected_action") or {}).get("target") or ""
        ) or None
    problem_state = build_problem_state_from_agent_state(state)
    # Said once, before the first question about a newly-understood picture:
    # the patient gets to correct our reading of their message before they
    # answer anything based on it.
    lead_in = ""
    if not state.get("adaptive_opening_sent") or problem_state.newly_mentioned:
        lead_in = opening_acknowledgement(problem_state)
    planned = plan_next_question(
        state.get("clinical_blueprint", {}),
        state.get("missing_critical_fields", []),
        state.get("clinical_memory", {}),
        preferred_target=selected_target,
        problem_state=problem_state,
        lead_in=lead_in,
    )

    # A target that has already been put to this patient is being asked again
    # because their reply did not settle it -- not because the planner forgot.
    # Repeating the sentence word for word is how software says it was not
    # listening, so the repeat says why it is being asked again and is recorded
    # as a clarification rather than a fresh question.
    asked_before = int(
        ((state.get("action_loop_state") or {}).get("asked_targets") or {}).get(
            str(selected_target or ""), 0
        )
    )
    question_type = "CLARIFICATION" if asked_before > 1 else "QUESTION"
    if question_type == "CLARIFICATION":
        lead_in = (
            f"{lead_in.rstrip()} Mình chưa rõ ý này nên hỏi lại một chút."
            if lead_in
            else "Mình chưa rõ ý này nên hỏi lại một chút."
        )
    # The acknowledgement is prepended here rather than inside each builder, so
    # the bounded slot questions (symptom probes, the vitals form) get it too
    # without giving up the structured payload they depend on.
    text = planned.text
    if lead_in and not text.startswith(lead_in):
        text = f"{lead_in.rstrip()} {text}"
    message: dict[str, Any] = {
        "id": str(uuid.uuid4()),
        "sender": "bot",
        "timestamp": datetime.now(UTC).isoformat(),
        "content": text,
        "step": 2,
    }
    if planned.structured_payload:
        message["structured"] = planned.structured_payload

    return {
        "step": 2,
        "structured_question": planned.structured_payload,
        "active_question": {
            "field": planned.field,
            "question_id": planned.field,
            "question_type": question_type,
            "semantic_target": selected_target,
            "options_type": (
                planned.structured_payload.get("optionsType")
                if planned.structured_payload
                else "text_only"
            ),
        },
        "messages": [message],
        "response": text,
        "response_type": "STRUCTURED_QUESTION" if planned.structured_payload else "TEXT",
        "workflow_phase": "CLARIFICATION",
        "decision_status": "NEEDS_CLARIFICATION",
        "adaptive_opening_sent": bool(
            state.get("adaptive_opening_sent") or lead_in
        ),
        "current_esi_level": None,
        "sbar_report": None,
        "turn_rag_citations": [],
        "next_step": "wait_for_patient",
    }
