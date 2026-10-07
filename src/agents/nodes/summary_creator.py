"""Vi-Node 4: Kiến tạo Báo Cáo SBAR & Ký Thác Thẩm Định HITL (SBAR Summary Creator Node).

Tuân thủ giải pháp lâm sàng:
- Tổng hợp trọn bộ 4 khối văn phác đồ SBAR:
  + S (Situation): Hiện trạng bệnh tình & sinh hiệu.
  + B (Background): Tiền sử hồ sơ gia đình & dị ứng.
  + A (Assessment): Nhận định mức ưu tiên ESI của DeepAgent clinical tools.
  + R (Recommendation): Chỉ định điều hướng sang Trạm Kíp trực thẩm định.
- Chỉ tạo dữ liệu SBAR; API phát hành sau verify và database commit.
"""

from src.agents.guardrails import (
    extract_patient_reported_vital_context,
    extract_patient_reported_vitals,
)
from src.agents.nodes.evidence_gate import build_insufficient_evidence_handoff
from src.agents.state import AgentState


async def create_sbar_summary_node(state: AgentState) -> dict:
    """Nút chấp bút Báo cáo SBAR 4 khối chuẩn bị bàn giao cho Điều dưỡng / Bác sĩ thẩm định."""
    query = state.get("query", "")
    esi = state.get("current_esi_level")
    is_red_flag = state.get("is_red_flag", False)
    name = state.get("patient_name", "Bệnh nhân ẩn danh")
    relationship = state.get("relationship_type", "SELF")
    age = state.get("patient_age", "N/A")
    memory = state.get("clinical_memory", {})
    blueprint = state.get("clinical_blueprint", {})
    memory_status = state.get("clinical_memory_confirmation_status", "NOT_REVIEWED")
    is_demo_case_support = (
        state.get("evidence_status") == "CASE_EXAMPLE_SUPPORT"
        and state.get("evidence_authority_status") == "DEMO_ONLY"
    )
    if memory_status == "CONFIRMED":
        chronic = ", ".join(memory.get("chronic_conditions", [])) or "Người bệnh xác nhận chưa ghi nhận"
        allergies = ", ".join(memory.get("allergies", [])) or "Người bệnh xác nhận chưa ghi nhận"
        meds = ", ".join(memory.get("daily_medications", [])) or "Người bệnh xác nhận chưa ghi nhận"
        memory_provenance = "EHR đã được xác nhận lại trong phiên"
    elif memory_status == "UPDATED_BY_PATIENT":
        chronic = allergies = meds = "Không dùng bản EHR cũ cho suy luận"
        memory_provenance = (
            "Người bệnh báo thay đổi: "
            f"{blueprint.get('clinical_context_note') or 'chưa có chi tiết'}"
        )
    else:
        chronic = allergies = meds = "Chưa xác minh lại"
        memory_provenance = "EHR không chắc còn đúng"
    
    citations = state.get("turn_rag_citations", [])
    citation_codes = [
        str(c.get("protocolId"))
        for c in citations
        if isinstance(c, dict) and c.get("protocolId")
    ]
    if esi is None or (not is_red_flag and not citation_codes):
        return build_insufficient_evidence_handoff(
            "Không thể tạo SBAR vì ESI hoặc citation hợp lệ bị thiếu",
            step=int(state.get("step") or 3),
            handoff_reason="SBAR_MISSING_ESI_OR_CITATION",
        )

    # 1. Soạn 4 khối SBAR chuẩn mục
    complaints = ", ".join(blueprint.get("chief_complaint", [])) or query
    onset = blueprint.get("onset_time") or "chưa rõ thời điểm"
    associated = ", ".join(blueprint.get("associated_symptoms", [])) or "chưa ghi nhận"
    vital_signs = blueprint.get("vital_signs", {}) or extract_patient_reported_vitals(query)
    vital_form_context = extract_patient_reported_vital_context(query)
    vital_source = blueprint.get("vital_signs_source") or vital_form_context.get("source")
    vital_measured_at = (
        blueprint.get("vital_signs_measured_at")
        or vital_form_context.get("measured_at")
    )
    vital_context = (
        f"Sinh hiệu do người bệnh khai: {vital_signs}; "
        f"nguồn {vital_source or 'chưa rõ'}; "
        f"thời điểm {vital_measured_at or 'chưa rõ'}"
        if vital_signs
        else f"Sinh hiệu: {state.get('vital_signs_status', 'chưa xác minh')}"
    )
    procedure = blueprint.get("recent_procedure")
    situation_str = (
        f"Bệnh nhân {name} ({relationship}, {age} tuổi) khai triệu chứng: "
        f"'{complaints}', khởi phát {onset}; dấu hiệu kèm: {associated}. {vital_context}."
    )
    background_str = (
        f"Bệnh nền: [{chronic}]. Dị ứng: [{allergies}]. Thuốc đang dùng: [{meds}]. "
        f"Nguồn bối cảnh: {memory_provenance}."
        + (f" Phẫu thuật/thủ thuật gần đây: {procedure}." if procedure else "")
    )
    red_flag_status = str(state.get("red_flag_status") or "")
    if is_red_flag and red_flag_status == "SAFETY_FALLBACK":
        # A precaution, not a finding. The nurse must be able to tell them apart.
        assessment_detail = (
            "THẬN TRỌNG TỰ ĐỘNG, CHƯA ĐƯỢC KIỂM CHỨNG NGỮ CẢNH: lớp sàng lọc "
            "nhanh phát hiện dấu hiệu cần đánh giá khẩn nhưng bộ kiểm tra ngữ "
            "cảnh không chạy được, nên hệ thống chọn phương án an toàn. Chưa xác "
            f"định được đây có phải tình trạng hiện tại của người bệnh hay không. "
            f"Dấu hiệu sàng lọc: '{state.get('red_flag_candidate_reason') or 'không rõ'}'. "
            "Cần nhân viên y tế đánh giá trực tiếp."
        )
    elif is_red_flag:
        emergency_source = state.get("emergency_detection_source")
        if emergency_source == "SEMANTIC_LLM":
            assessment_detail = (
                "Cảnh báo khẩn từ đánh giá ngữ cảnh bằng mô hình; cần nhân viên y tế "
                "xác nhận."
            )
        elif emergency_source == "DETERMINISTIC_REFLEX":
            assessment_detail = (
                "BÁO ĐỘNG TỪ QUY TẮC AN TOÀN XÁC ĐỊNH: quy tắc sàng lọc khẩn "
                "đã kích hoạt trực tiếp; kết quả này không được mô tả là đã kiểm "
                "chứng ngữ cảnh. Cần nhân viên y tế đánh giá và xác nhận."
            )
        else:
            assessment_detail = (
                "Báo động đỏ đã được kiểm chứng ngữ cảnh (chủ thể, thì, phủ định, "
                "tình trạng hiện tại); cần nhân viên y tế xác nhận."
            )
    elif is_demo_case_support:
        assessment_detail = (
            "Đề xuất sơ bộ dựa trên metadata ESI của các ca MIETIC tương tự. "
            f"Lý giải: {state.get('preliminary_esi_reasoning') or 'chưa có chi tiết'}. "
            "Nhân viên y tế phải xác nhận hoặc điều chỉnh."
        )
    else:
        assessment_detail = (
            "Đây là đề xuất từ lời khai và phác đồ; nhân viên y tế phải xác "
            "minh lại sinh hiệu."
        )
    assessment_str = (
        f"Trợ lý AI DeepAgent đánh giá mức độ khẩn cấp là ESI Level {esi}. "
        f"{assessment_detail}"
    )
    recommendation_str = (
        "Chuyển ngay thẻ bệnh nhân vào Bảng Hàng Đợi Kanban Lâm Sàng cho Bác sĩ trực/Điều dưỡng thẩm định. "
        "Yêu cầu kíp trực mở khóa hồ sơ Break-Glass (nếu cần thiết) để quyết định APPROVE hoặc OVERRIDE cấp ESI."
    )

    sbar_doc = {
        "situation": situation_str,
        "background": background_str,
        "assessment": assessment_str,
        "recommendation": recommendation_str,
        "citations": citation_codes,
        "clinical_context": {
            "safety_rule_id": state.get("safety_rule_id") if is_red_flag else None,
            "red_flag_status": red_flag_status or None,
            "red_flag_candidate_reason": state.get("red_flag_candidate_reason"),
            "red_flag_resolution_reason": state.get("red_flag_resolution_reason"),
            "patient_reported_vitals": vital_signs,
            "patient_reported_vitals_source": vital_source,
            "patient_reported_vitals_measured_at": vital_measured_at,
            "vital_signs_status": (
                "PATIENT_REPORTED"
                if vital_signs
                else state.get("vital_signs_status", "NOT_REVIEWED")
            ),
            "recent_procedure": procedure,
            "evidence_mode": (
                "MIETIC_CASE_EXAMPLE_DEMO"
                if is_demo_case_support
                else (
                    "UNVALIDATED_SAFETY_FALLBACK"
                    if red_flag_status == "SAFETY_FALLBACK"
                    else "SEMANTIC_EMERGENCY_LLM"
                    if state.get("emergency_detection_source") == "SEMANTIC_LLM"
                    else "DETERMINISTIC_REFLEX_RULE"
                    if state.get("emergency_detection_source")
                    == "DETERMINISTIC_REFLEX"
                    else "CONTEXT_VALIDATED_RED_FLAG_RULE"
                )
                if is_red_flag
                else "VALIDATED_PROTOCOL"
            ),
            "ehr_snapshot": {
                "age": memory.get("age"),
                "gender": memory.get("gender"),
                "height_cm": memory.get("height_cm"),
                "weight_kg": memory.get("weight_kg"),
                "bmi": memory.get("bmi"),
                "blood_type": memory.get("blood_type"),
                "chronic_conditions": list(memory.get("chronic_conditions", [])),
                "allergies": list(memory.get("allergies", [])),
                "daily_medications": list(memory.get("daily_medications", [])),
                "updated_at": state.get("clinical_memory_updated_at"),
                "confirmation_status": memory_status,
                "patient_context_note": blueprint.get("clinical_context_note"),
            },
        },
    }

    return {
        "sbar_report": sbar_doc,
        "workflow_phase": "HANDOFF",
        "decision_status": "EMERGENCY_ESCALATED" if is_red_flag else "PROPOSED",
        "response_type": "EMERGENCY" if is_red_flag else "TRIAGE_PROPOSAL",
        "next_step": "hitl_checkpoint"
    }
