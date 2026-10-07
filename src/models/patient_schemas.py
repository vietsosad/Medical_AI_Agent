"""Pydantic v2 DTO schemas cho cổng Giao tiếp Bệnh nhân (Patient Triage Engine & History Replay).

Tuân thủ nghiêm ngặt chuẩn fastapi-production & backend-rules.md:
- Tuyệt đối KHÔNG dùng dấu chấm lửng (...) hoặc RootModel trong khai báo trường bắt buộc.
- Đảm bảo ánh xạ 100% về mặt định nghĩa trường với các TypeScript contracts (triage-chat.ts, clinical-history.d.ts).
"""

from datetime import UTC, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from src.services.clinical_text import normalize_clinical_display_text


class StartTriageRequest(BaseModel):
    """Payload khởi xướng phiên Triage mới từ Bệnh nhân."""
    model_config = ConfigDict(from_attributes=True)

    profile_id: str | None = Field(default=None, description="UUID của hồ sơ thành viên gia đình đang khám (Nếu trống sẽ dùng hồ sơ gốc)")
    initial_symptom: str = Field(default="", max_length=2000, description="Triệu chứng khởi phát (nếu trống sẽ chỉ tạo phiên)")
    health_topic: str | None = Field(
        default=None,
        max_length=120,
        description=(
            "Slug chủ đề sức khỏe người dùng vừa đọc trên trang chủ. Đây CHỈ là mối quan "
            "tâm, KHÔNG phải triệu chứng người bệnh khai và không bao giờ được coi là chẩn đoán."
        ),
    )


class StartTriageResponse(BaseModel):
    """Phản hồi tức thì ngay sau khi khởi tạo ca khám."""
    model_config = ConfigDict(from_attributes=True)

    session_id: str = Field(description="UUID phiên Triage mới tạo")
    status: str = Field(default="IN_PROGRESS", description="Trạng thái luồng (IN_PROGRESS hoặc RED_FLAG_LOCKED)")
    message: str = Field(description="Thông điệp chào mừng hoặc lời khuyên đầu tiên từ AI Agent")
    is_red_flag: bool = Field(default=False, description="Cờ cảnh báo nếu phản xạ thính chấn <50ms ngắt luồng ngay lập tức")


# ==========================================================
# TRIAGE CHAT & STRUCTURED QUESTION ENGINE (triage-chat.ts)
# ==========================================================
class OptionItemDTO(BaseModel):
    """Một ý trắc nghiệm trong câu hỏi lâm sàng từ AI."""
    model_config = ConfigDict(from_attributes=True)

    id: str = Field(description="Mã định danh lựa chọn (vd: opt_1)")
    label: str = Field(description="Nhãn hiển thị câu trả lời cho người bệnh")
    value: str | int = Field(description="Giá trị thực gửi lên Backend")
    description: str | None = Field(default=None, description="Mô tả bổ sung chi tiết (nếu có)")
    isRisk: bool = Field(default=False, description="Cờ báo hiệu triệu chứng mang yếu tố nguy cơ khẩn cấp (Red-flag candidate)")
    isExclusive: bool = Field(
        default=False,
        description="Lựa chọn loại trừ các lựa chọn khác trong biểu mẫu multiple",
    )


class VitalFormFieldDTO(BaseModel):
    """Một trường sinh hiệu do người bệnh chủ động nhập trong hội thoại."""
    model_config = ConfigDict(from_attributes=True)

    id: Literal[
        "heart_rate",
        "blood_pressure",
        "respiratory_rate",
        "spo2",
        "temperature_c",
        "gcs",
    ] = Field(description="Khóa sinh hiệu ổn định dùng xuyên suốt frontend và DeepAgent")
    label: str = Field(description="Nhãn tiếng Việt hiển thị trong biểu mẫu")
    unit: str = Field(description="Đơn vị lâm sàng đi kèm giá trị")
    placeholder: str = Field(description="Ví dụ định dạng, không phải dữ liệu mặc định")
    inputMode: Literal["numeric", "decimal", "text"] = Field(default="numeric")
    min: float | None = Field(default=None)
    max: float | None = Field(default=None)
    step: float | None = Field(default=None)


class EHRConfirmationSnapshotDTO(BaseModel):
    """Ảnh chụp EHR chỉ đọc để người bệnh xác nhận trong hội thoại."""
    model_config = ConfigDict(from_attributes=True)

    age: int | None = Field(default=None, ge=0, le=130)
    gender: str | None = Field(default=None)
    height_cm: float | None = Field(default=None, gt=0)
    weight_kg: float | None = Field(default=None, gt=0)
    bmi: float | None = Field(default=None, gt=0)
    blood_type: str | None = Field(default=None)
    chronic_conditions: list[str] = Field(default_factory=list)
    allergies: list[str] = Field(default_factory=list)
    daily_medications: list[str] = Field(default_factory=list)


class StructuredPayloadDTO(BaseModel):
    """Cấu trúc biểu mẫu trắc nghiệm đính kèm từ AI Node."""
    model_config = ConfigDict(from_attributes=True)

    optionsType: Literal["single", "multiple", "scale", "text_only", "vitals_form"] = Field(default="single", description="Loại form câu hỏi")
    options: list[OptionItemDTO] | None = Field(default=None, description="Danh sách lựa chọn cho single hoặc multiple")
    fields: list[VitalFormFieldDTO] | None = Field(
        default=None,
        description="Danh sách trường khi optionsType=vitals_form",
    )
    ehrSnapshot: EHRConfirmationSnapshotDTO | None = Field(
        default=None,
        description="Ảnh chụp EHR chỉ đọc khi yêu cầu người bệnh xác nhận",
    )
    minScale: int | None = Field(default=0, description="Giá trị nhỏ nhất nếu là thang điểm scale")
    maxScale: int | None = Field(default=10, description="Giá trị lớn nhất nếu là thang điểm scale")
    submitted: bool = Field(default=False, description="Cờ đánh dấu câu hỏi đã được người bệnh bấm chọn hay chưa")
    selectedAnswer: str | list[str] | int | None = Field(default=None, description="Giá trị câu trả lời chốt của bệnh nhân")


class RagCitationDTO(BaseModel):
    """Tham chiếu trích dẫn nguồn RAG chuẩn y khoa."""
    model_config = ConfigDict(from_attributes=True)

    id: str = Field(description="UUID hoặc mã định danh của trích dẫn")
    title: str = Field(description="Tiêu đề nguồn phác đồ hoặc ca tham khảo")
    protocolId: str = Field(description="Mã nguồn phác đồ hoặc mã ca tham khảo")
    excerpt: str = Field(description="Trích đoạn nguồn hỗ trợ lập luận AI")
    relevanceScore: float | None = Field(default=None, description="Điểm độ tương đồng RAG (0.0 đến 1.0)")
    issuingBody: str | None = None
    sourceUri: str | None = None
    version: str | None = None
    section: str | None = None
    effectiveDate: str | None = None
    validationStatus: Literal["approved"] | None = None
    contentHash: str | None = None
    reviewedBy: str | None = None
    reviewedAt: str | None = None
    calibrationId: str | None = None
    sourceType: Literal["validated_protocol", "case_example"] | None = None
    retrievalChannels: list[dict] = Field(default_factory=list)


class CaseSupportDTO(BaseModel):
    """Ca tương tự chỉ để tham khảo; không có thẩm quyền xác lập ESI.

    The ESI metadata below is the *retrieved case's own* label, carried so a
    reader can see what the corpus recorded about a similar presentation. It is
    display context and nothing else: the patient's ESI comes from the ESI
    authority corpus through the evidence gate, and a case label can never set,
    raise or lower it. ``labelStatus`` says how much the label is worth, and
    ``UNKNOWN`` is rendered as unknown rather than resolved into a level.
    """

    model_config = ConfigDict(from_attributes=True)

    caseId: str = Field(description="Mã ca tham khảo ổn định")
    excerpt: str = Field(description="Trích đoạn biểu hiện đã giới hạn độ dài")
    # Raw cosine similarity from the dense channel. Kept for audit and for
    # stored-state compatibility; it is NOT a confidence and is not what the
    # ranking used, so the UI shows the band below instead.
    similarityScore: float | None = Field(default=None)
    # Post-rerank retrieval relevance in [0, 1]. Also not a probability: it
    # measures how much this case's presentation overlaps the patient's.
    retrievalRelevance: float | None = Field(default=None)
    relevanceBand: Literal["HIGH", "MODERATE", "LOW", "UNKNOWN"] = "UNKNOWN"
    # The retrieved case's recorded ESI, where the corpus has one.
    validatedEsiLevel: int | None = Field(default=None, ge=1, le=5)
    candidateEsiLevels: list[int] = Field(default_factory=list)
    labelStatus: Literal["CONSISTENT", "CONFLICTING", "UNKNOWN"] = "UNKNOWN"
    ageBand: str | None = Field(default=None)
    sex: str | None = Field(default=None)
    symptomConcepts: list[str] = Field(default_factory=list)
    retrievalScope: Literal["CASE_SUPPORT"] = "CASE_SUPPORT"
    authorityStatus: Literal["NOT_PROTOCOL"] = "NOT_PROTOCOL"
    sourceType: Literal["case_example"] = "case_example"


class PatientChatMessageDTO(BaseModel):
    """Một tin nhắn hoàn chỉnh trong phiên hỏi bệnh Triage Chat."""
    model_config = ConfigDict(from_attributes=True)

    id: str = Field(description="UUID tin nhắn")
    sender: Literal["user", "bot", "system_shield", "nurse"] = Field(
        default="bot",
        description="Đại diện gửi tin: bệnh nhân, AI, lớp chắn an toàn, hoặc nhân viên lâm sàng thật",
    )
    senderName: str | None = Field(
        default=None,
        description="Tên nhân viên lâm sàng đã gửi; None với tin do máy sinh",
    )
    timestamp: str = Field(description="Thời gian gửi tin định dạng ISO")
    content: str = Field(description="Nội dung văn bản hội thoại")
    step: int = Field(default=1, description="Bước hiện tại trong kịch bản Triage (1 | 2 | 3 | 4)")
    structured: StructuredPayloadDTO | None = Field(default=None, description="Biểu mẫu câu hỏi trắc nghiệm đính kèm từ AI")
    ragCitations: list[RagCitationDTO] | None = Field(default=None, description="Danh sách nguồn trích dẫn RAG (nếu là tin nhắn của bot/AI)")
    caseSupport: list[CaseSupportDTO] = Field(
        default_factory=list,
        description="Ca tương tự chỉ để tham khảo; không có thẩm quyền ESI",
    )
    intent: Literal[
        "TRIAGE_NEW_SYMPTOM",
        "TRIAGE_FOLLOW_UP",
        "GREETING_HELP",
        "OUT_OF_SCOPE",
        "UNCLEAR",
        "EMERGENCY_SIGNAL",
        "SAFETY_CRISIS_SUPPORT",
    ] | None = Field(default=None)
    responseType: Literal[
        "TEXT",
        "STRUCTURED_QUESTION",
        "INTAKE_REVIEW",
        "EMERGENCY",
        "TRIAGE_PROPOSAL",
        "SAFETY_GUIDANCE",
    ] | None = Field(default=None)
    decisionStatus: Literal[
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
    ] | None = Field(default=None)
    workflowPhase: Literal[
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
    ] | None = Field(default=None)
    esiLevel: int | None = Field(default=None, ge=1, le=5)
    evidenceStatus: Literal[
        "NOT_REQUESTED",
        "RETRIEVED",
        "INSUFFICIENT_EVIDENCE",
        "RETRIEVAL_FAILURE",
        "CASE_EXAMPLE_SUPPORT",
        "SUFFICIENT",
    ] | None = None
    retrievalDegradedModes: list[str] = Field(default_factory=list)
    intakeSummary: dict | None = Field(
        default=None,
        description="Bản tóm tắt dữ liệu để người bệnh kiểm tra trước khi AI phân loại",
    )
    requiresPatientConfirmation: bool = Field(default=False)
    sbarFinalized: bool = Field(
        default=False,
        description="True chỉ sau final verifier và durable database commit",
    )


class AgentStreamEventDTO(BaseModel):
    """Public SSE activity event; contains no hidden reasoning or medical history."""
    model_config = ConfigDict(from_attributes=True)

    type: Literal["accepted", "progress", "intent", "heartbeat", "result", "error"]
    message: str
    sequence: int = Field(ge=0)
    elapsedMs: int = Field(default=0, ge=0)
    phase: Literal[
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
    ] | None = None
    intent: Literal[
        "TRIAGE_NEW_SYMPTOM",
        "TRIAGE_FOLLOW_UP",
        "GREETING_HELP",
        "OUT_OF_SCOPE",
        "UNCLEAR",
        "EMERGENCY_SIGNAL",
        "SAFETY_CRISIS_SUPPORT",
    ] | None = None
    label: str | None = None
    detail: str | None = None
    progress: int | None = Field(default=None, ge=0, le=100)
    timestamp: str = Field(default_factory=lambda: datetime.now(UTC).isoformat())
    retryable: bool | None = None
    errorCode: str | None = None
    result: PatientChatMessageDTO | None = None

    @model_validator(mode="after")
    def validate_terminal_payload(self) -> "AgentStreamEventDTO":
        if self.type == "result" and self.result is None:
            raise ValueError("result event requires a validated chat result")
        if self.type == "error" and (
            self.retryable is None or not self.errorCode
        ):
            raise ValueError("error event requires retryable and errorCode")
        return self


class PatientChatInputDTO(BaseModel):
    """Gói dữ liệu Bệnh nhân phản hồi tin nhắn hoặc chọn trắc nghiệm trong phiên khám."""
    model_config = ConfigDict(from_attributes=True)

    message: str | None = Field(default=None, description="Nội dung tin nhắn văn bản (nếu người dùng gõ tay)")
    selected_option: str | None = Field(default=None, description="ID hoặc nhãn trắc nghiệm được nhấn chọn (nếu là biểu mẫu bấm)")
    selected_option_id: str | None = Field(
        default=None,
        max_length=100,
        description="Mã lựa chọn ổn định do biểu mẫu cung cấp; không dùng nhãn hiển thị để điều khiển workflow",
    )
    step: int = Field(default=1, description="Bước tiến hành trong quy trình")
    confirm_intake: bool = Field(
        default=False,
        description="Người bệnh xác nhận bản tóm tắt để cho phép bắt đầu suy luận ESI",
    )


# =================================================================
# CLINICAL HISTORY & SBAR ARCHIVE MODULE (clinical-history.d.ts)
# =================================================================
class HitlSignatureDTO(BaseModel):
    """Chữ ký thẩm định từ Bác sĩ hoặc Điều dưỡng trưởng."""
    model_config = ConfigDict(from_attributes=True)

    reviewer_name: str | None = Field(
        default=None,
        description="Tên người thẩm định khi backend có dữ liệu định danh đã lưu",
    )
    review_timestamp: str = Field(description="Thời gian ký duyệt chuẩn ISO 8601 string")
    status: Literal["APPROVED", "OVERRIDDEN", "PENDING_REVIEW", "EMERGENCY_REJECTED"] = Field(description="Trạng thái phán quyết lâm sàng")
    original_esi: int = Field(description="Chỉ số ESI ban đầu do DeepAgent đề xuất")
    final_esi: int = Field(description="Chỉ số ESI chính thức sau quyết định thẩm định")
    justification_note: str | None = Field(default=None, description="Lý do lâm sàng của bác sĩ khi can thiệp override")


class SbarReportDTO(BaseModel):
    """Phiếu Báo Cáo SBAR Quá Khứ (Situation - Background - Assessment - Recommendation)."""
    model_config = ConfigDict(from_attributes=True)

    situation: str = Field(description="Tóm tắt tình trạng hiện tại và triệu chứng chính")
    background: str = Field(description="Nền tảng tiền sử, bệnh mãn tính, thuốc đang dùng từ Hồ sơ Lâm sàng")
    assessment: str = Field(description="Nhận định đánh giá và nguy cơ theo phác đồ AI & RAG")
    recommendation: str = Field(description="Khuyến nghị hành động tức thì và hướng chỉ định tiếp theo")
    citations: list[str] = Field(default_factory=list, description="Mảng mã phác đồ RAG đã sử dụng (vd: ['PRO_CARD_001', 'PRO_CP_002'])")

    @field_validator("situation", "background", "assessment", "recommendation")
    @classmethod
    def normalize_display_spacing(cls, value: str) -> str:
        return normalize_clinical_display_text(value)


class TriageHistoryListItemDTO(BaseModel):
    """Thẻ thông tin tóm tắt ca bệnh hiển thị trên danh sách tra cứu / Sidebar."""
    model_config = ConfigDict(from_attributes=True)

    session_id: str = Field(description="UUID duy nhất của phiên khám")
    status: Literal[
        "IN_PROGRESS",
        "RED_FLAG_LOCKED",
        "HITL_REVIEWING",
        "COMPLETED",
        "CANCELLED",
    ] = Field(description="Trạng thái ca khám bền vững từ backend")
    profile_name: str | None = Field(default=None, description="Tên hồ sơ bệnh nhân (hoặc Khám Nhanh)")
    relationship_type: str | None = Field(default=None, description="Mối quan hệ (SELF, CHILD, vv)")
    chief_complaint: str = Field(description="Triệu chứng chính / Lý do tiếp nhận lâm sàng")
    created_at: str = Field(description="Thời gian tạo (ISO timestamp)")
    final_esi: int | None = Field(default=None, description="ESI chỉ có khi AI đề xuất có căn cứ hoặc HITL đã chốt")
    hitl_status: Literal["APPROVED", "OVERRIDDEN", "PENDING_REVIEW", "EMERGENCY_REJECTED"] = Field(default="PENDING_REVIEW", description="Trạng thái thẩm định con người (HITL)")
    sbar_snippet: str = Field(default="", description="Trích đoạn tóm lược SBAR nhanh")
    sbar_finalized: bool = Field(
        default=False,
        description="Cho phép hiển thị/tải SBAR đã commit",
    )
    unread_from_staff: int = Field(
        default=0,
        description="Số lượng tin nhắn chưa đọc từ nhân viên y tế",
    )


class TriageSessionDetailDTO(TriageHistoryListItemDTO):
    """Hồ sơ chi tiết ca bệnh quá khứ hoàn chỉnh phục vụ Read-Only Replay."""
    model_config = ConfigDict(from_attributes=True)

    messages: list[PatientChatMessageDTO] = Field(default_factory=list, description="Lịch sử tin nhắn hội thoại AI (Read-Only Replay)")
    sbar_report: SbarReportDTO | None = Field(
        default=None,
        description="Toàn bộ SBAR đã finalized; null khi ca chưa đủ điều kiện",
    )
    hitl_signature: HitlSignatureDTO | None = Field(default=None, description="Chữ ký thẩm định (có thể null nếu đang chờ duyệt)")


class HistoryListResponse(BaseModel):
    """Danh sách lịch sử các phiên khám của bệnh nhân."""
    model_config = ConfigDict(from_attributes=True)

    items: list[TriageHistoryListItemDTO] = Field(default_factory=list, description="Danh sách ca Triage")


class SessionStatusDTO(BaseModel):
    """Trạng thái tổng quan của một phiên khám Triage."""
    model_config = ConfigDict(from_attributes=True)

    session_id: str = Field(description="UUID phiên khám")
    status: str = Field(description="Trạng thái: IN_PROGRESS | COMPLETED | RED_FLAG_LOCKED | HITL_REVIEWING")
    profile_id: str | None = Field(default=None, description="UUID hồ sơ y khoa gắn với phiên này")
    ai_proposed_esi: int | None = Field(default=None, description="ESI Level đề xuất bởi AI")
    final_esi: int | None = Field(
        default=None,
        description="ESI hiển thị cho người bệnh sau khi ưu tiên kết luận thẩm định",
    )
    hitl_status: Literal[
        "APPROVED",
        "OVERRIDDEN",
        "PENDING_REVIEW",
        "EMERGENCY_REJECTED",
    ] = Field(
        default="PENDING_REVIEW",
        description="Trạng thái thẩm định được suy ra từ bản ghi ca khám",
    )
    reviewer_name: str | None = Field(
        default=None,
        description="Tên điều dưỡng đã lưu quyết định, nếu đã có",
    )
    reviewed_at: str | None = Field(
        default=None,
        description="Thời điểm điều dưỡng lưu quyết định phân luồng",
    )
    decision_type: Literal["CONFIRM_ESI", "ADJUST_ESI"] | None = Field(
        default=None,
        description="Quyết định ESI đã được điều dưỡng lưu",
    )
    decision_note: str | None = Field(
        default=None,
        description="Ghi chú điều dưỡng đã lưu cùng quyết định ESI",
    )
    is_red_flag_triggered: bool = Field(default=False)
    created_at: str = Field(description="Thời gian tạo")
    updated_at: str | None = Field(default=None)
    sbar_summary: dict | None = Field(
        default=None,
        description="SBAR đã lưu trong bản ghi ca khám, nếu đã hoàn tất",
    )
    sbar_finalized: bool = Field(
        default=False,
        description="True khi SBAR đã qua cổng và được commit bền vững",
    )
    decision_status: Literal[
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
    ] | None = Field(default=None)
    evidence_status: Literal[
        "NOT_REQUESTED",
        "RETRIEVED",
        "INSUFFICIENT_EVIDENCE",
        "RETRIEVAL_FAILURE",
        "CASE_EXAMPLE_SUPPORT",
        "SUFFICIENT",
    ] | None = Field(default=None)
    retrieval_degraded_modes: list[str] = Field(default_factory=list)
    intake_confirmation_status: Literal[
        "NOT_READY",
        "AWAITING_CONFIRMATION",
        "CONFIRMED",
    ] = Field(default="NOT_READY")
    intake_summary: dict | None = Field(default=None)
    # Ai đang thực sự xem hồ sơ này. Người bệnh có quyền biết mình đang nói
    # chuyện với máy hay với một nhân viên y tế.
    care_team_name: str | None = Field(
        default=None,
        description="Tên nhân viên lâm sàng đang phụ trách ca; None khi chưa ai nhận",
    )
    care_team_status: Literal[
        "AI_SCREENING",
        "WAITING_REVIEW",
        "STAFF_REVIEWING",
        "SPECIALIST_REVIEW",
        "COMPLETED",
    ] = Field(
        default="AI_SCREENING",
        description="Trạng thái ca diễn đạt theo ngôn ngữ người bệnh hiểu được",
    )
    unread_from_staff: int = Field(
        default=0,
        ge=0,
        description="Số tin nhân viên đã gửi mà người bệnh chưa đọc",
    )
    workflow_phase: Literal[
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
    ] | None = Field(default=None)


class SendStaffMessageRequestDTO(BaseModel):
    """Người bệnh nhắn cho nhân viên lâm sàng đang phụ trách ca."""
    model_config = ConfigDict(str_strip_whitespace=True)

    content: str = Field(min_length=1, max_length=2000, description="Nội dung tin nhắn")
    clientMessageId: str | None = Field(
        default=None,
        max_length=64,
        description="Khoá chống trùng do client sinh, để bấm lại không tạo hai bản ghi",
    )


class CareTeamMessageDTO(BaseModel):
    """Một dòng trong luồng trao đổi giữa người bệnh và nhân viên y tế."""

    id: str
    sender: Literal["patient", "staff"] = Field(
        description="Không có 'bot': kênh này chỉ có hai con người",
    )
    senderName: str | None = Field(default=None)
    content: str
    createdAt: str
    readAt: str | None = Field(default=None)


class CareTeamThreadResponse(BaseModel):
    """Toàn bộ luồng trao đổi với nhân viên y tế kèm trạng thái đội ngũ."""

    session_id: str
    care_team_name: str | None = Field(default=None)
    care_team_status: Literal[
        "AI_SCREENING",
        "WAITING_REVIEW",
        "STAFF_REVIEWING",
        "SPECIALIST_REVIEW",
        "COMPLETED",
    ] = Field(default="AI_SCREENING")
    unread_from_staff: int = Field(default=0, ge=0)
    messages: list[CareTeamMessageDTO] = Field(default_factory=list)


class StaffConversationResponse(BaseModel):
    """Trạng thái kênh liên lạc giữa người bệnh và đội ngũ lâm sàng."""

    session_id: str
    care_team_name: str | None = Field(default=None)
    care_team_status: Literal[
        "AI_SCREENING",
        "WAITING_REVIEW",
        "STAFF_REVIEWING",
        "SPECIALIST_REVIEW",
        "COMPLETED",
    ] = Field(default="AI_SCREENING")
    unread_from_staff: int = Field(default=0, ge=0)


class SessionMessagesResponse(BaseModel):
    """Lịch sử tin nhắn kèm trạng thái phiên khám (dùng khi phục hồi session)."""
    model_config = ConfigDict(from_attributes=True)

    session_status: SessionStatusDTO = Field(description="Trạng thái phiên khám hiện tại")
    messages: list[PatientChatMessageDTO] = Field(default_factory=list, description="Danh sách tin nhắn")
