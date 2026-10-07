"""Typed contracts for the Nurse Triage and mandatory HITL workflow."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

EsiLevel = Literal[1, 2, 3, 4, 5]
ReviewStatus = Literal[
    "WAITING_REVIEW",
    "ASSIGNED",
    "IN_REVIEW",
    "NEEDS_MORE_INFO",
    "SPECIALIST_REVIEW_REQUIRED",
    "TRIAGE_DECIDED",
    "HANDED_OFF",
]
ObservationKind = Literal[
    "HEART_RATE",
    "BLOOD_PRESSURE",
    "RESPIRATORY_RATE",
    "SPO2",
    "TEMPERATURE",
    "CONSCIOUSNESS",
]
ObservationAvailability = Literal["MEASURED", "UNKNOWN", "NOT_MEASURED", "NOT_APPLICABLE"]
ObservationSource = Literal["PATIENT_REPORTED", "NURSE_MEASURED", "DEVICE", "UNKNOWN"]


class NurseIdentityDTO(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str = Field(description="ID nhân viên đang phụ trách")
    name: str = Field(description="Tên hiển thị của Điều dưỡng")


class DataCompletenessDTO(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    is_complete: bool = Field(description="Đủ dữ liệu nền tảng để chốt phân luồng")
    missing_fields: list[str] = Field(default_factory=list)


class NurseQueueItemDTO(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    case_id: str = Field(description="ID ca Triage")
    patient_name: str = Field(description="Họ tên đầy đủ, chỉ trả qua API dành cho nhân viên lâm sàng")
    masked_patient_label: str = Field(description="Tên bệnh nhân đã che mờ")
    age: int | None = Field(default=None, ge=0, le=130)
    sex: str | None = Field(default=None)
    chief_complaint: str = Field(description="Triệu chứng chính, không phải chẩn đoán")
    ai_recommended_esi: EsiLevel | None = Field(
        default=None,
        description="Mức ESI do AI đề xuất; null nếu dữ liệu chưa đủ, tuyệt đối không suy diễn",
    )
    red_flags: list[str] = Field(default_factory=list)
    is_red_flag: bool = Field(default=False)
    # Lifecycle, so a nurse can tell a context-validated emergency from a
    # precaution taken when the validator could not run. None on legacy cases
    # recorded before the lifecycle was persisted.
    red_flag_status: str | None = Field(
        default=None,
        description="CANDIDATE | CONFIRMED | NOT_CONFIRMED | UNCERTAIN | SAFETY_FALLBACK",
    )
    red_flag_detection_source: str | None = Field(default=None)
    red_flag_resolution_reason: str | None = Field(default=None)
    waiting_since: datetime = Field(description="Mốc server bắt đầu chờ")
    wait_time_seconds: int = Field(default=0, ge=0)
    review_status: ReviewStatus = Field(description="Trạng thái công việc Điều dưỡng")
    assignee: NurseIdentityDTO | None = Field(default=None)
    data_completeness: DataCompletenessDTO = Field(description="Tình trạng đầy đủ dữ liệu")
    case_version: int = Field(ge=1, description="Phiên bản chống ghi đè")
    alert_acknowledged: bool = Field(default=False)
    unread_count: int = Field(
        default=0,
        ge=0,
        description="Số tin bệnh nhân đã gửi mà phía lâm sàng chưa đọc",
    )
    last_message_at: datetime | None = Field(
        default=None,
        description="Thời điểm dòng tin gần nhất của ca, để sắp xếp hội thoại đang sống",
    )


class NurseQueueSummaryDTO(BaseModel):
    total_waiting: int = Field(default=0, ge=0)
    urgent_count: int = Field(default=0, ge=0)
    mine_count: int = Field(default=0, ge=0)
    specialist_count: int = Field(default=0, ge=0)
    longest_wait_seconds: int = Field(default=0, ge=0)


class NurseQueueResponseDTO(BaseModel):
    items: list[NurseQueueItemDTO] = Field(default_factory=list)
    summary: NurseQueueSummaryDTO = Field(default_factory=NurseQueueSummaryDTO)
    sla_target_minutes: int | None = Field(
        default=None,
        ge=1,
        description="Chỉ có khi cơ sở y tế đã cấu hình; không hard-code theo ESI",
    )


class ClinicalObservationInputDTO(BaseModel):
    kind: ObservationKind = Field(description="Loại sinh hiệu")
    value: str | None = Field(default=None, max_length=40)
    unit: str | None = Field(default=None, max_length=20)
    availability: ObservationAvailability = Field(default="MEASURED")
    source: ObservationSource = Field(default="NURSE_MEASURED")
    measured_at: datetime | None = Field(default=None)

    @model_validator(mode="after")
    def validate_measurement(self) -> "ClinicalObservationInputDTO":
        if self.availability == "MEASURED":
            if not self.value or not self.unit or self.measured_at is None:
                raise ValueError("Giá trị đã đo phải có value, unit và measured_at")
        elif self.value is not None or self.unit is not None:
            raise ValueError("Không gửi value/unit khi sinh hiệu chưa có dữ liệu")
        return self


class ClinicalObservationDTO(ClinicalObservationInputDTO):
    id: str = Field(description="ID bản ghi bất biến")
    recorded_by: NurseIdentityDTO = Field(description="Người ghi nhận")
    recorded_at: datetime = Field(description="Thời điểm lưu trên server")


class RiskContextDTO(BaseModel):
    age: int | None = Field(default=None)
    gender: str | None = Field(default=None)
    height_cm: float | None = Field(default=None)
    weight_kg: float | None = Field(default=None)
    bmi: float | None = Field(default=None)
    blood_type: str | None = Field(default=None)
    chronic_conditions: list[str] = Field(default_factory=list)
    allergies: list[str] = Field(default_factory=list)
    active_medications: list[str] = Field(default_factory=list)
    pregnancy_status: str | None = Field(default=None)
    patient_reported_vitals: dict[str, str | int | float] = Field(default_factory=dict)
    patient_reported_vitals_source: str | None = Field(default=None)
    patient_reported_vitals_measured_at: str | None = Field(default=None)
    vital_signs_status: str = Field(default="NOT_REVIEWED")
    ehr_confirmation_status: str = Field(default="NOT_REVIEWED")
    ehr_profile_updated_at: str | None = Field(default=None)
    patient_context_note: str | None = Field(default=None)


class SbarSummaryDTO(BaseModel):
    situation: str | None = Field(default=None)
    background: str | None = Field(default=None)
    assessment: str | None = Field(default=None)
    recommendation: str | None = Field(default=None)


class CitationDTO(BaseModel):
    code: str = Field(description="Mã nguồn từ RAG; không tạo nội dung nguồn giả")
    title: str | None = Field(default=None, description="Tiêu đề nguồn đã truy xuất")
    excerpt: str | None = Field(default=None, description="Đoạn nguồn thực tế đã hỗ trợ proposal")
    source_uri: str | None = Field(default=None, description="URL tài liệu gốc nếu corpus đã lưu")
    section: str | None = Field(default=None, description="Mục trong tài liệu nguồn")
    version: str | None = Field(default=None, description="Phiên bản tài liệu hoặc pipeline ingest")
    content_hash: str | None = Field(default=None, description="Hash kiểm chứng nội dung đã truy xuất")


class ClinicalTranscriptMessageDTO(BaseModel):
    id: str
    # NURSE là tin do một nhân viên lâm sàng thật gõ. Trộn nó vào AI_AGENT sẽ
    # khiến hồ sơ giao tiếp y tế không quy được trách nhiệm về ai.
    sender: Literal["PATIENT", "AI_AGENT", "SYSTEM_SHIELD", "NURSE"]
    content: str
    created_at: datetime
    sender_name: str | None = Field(
        default=None,
        description="Tên nhân viên đã gửi, giữ theo thời điểm gửi",
    )
    read_at: datetime | None = Field(default=None)


class SpecialistReviewContextDTO(BaseModel):
    required: bool = Field(default=False)
    reason_code: str | None = Field(default=None)
    note: str | None = Field(default=None)
    requested_at: datetime | None = Field(default=None)


class NurseCaseDetailDTO(NurseQueueItemDTO):
    triage_status: str = Field(description="Trạng thái riêng của AI Triage")
    final_esi: EsiLevel | None = Field(default=None, description="ESI đã được Điều dưỡng chốt")
    observations: list[ClinicalObservationDTO] = Field(default_factory=list)
    risk_context: RiskContextDTO = Field(default_factory=RiskContextDTO)
    sbar: SbarSummaryDTO = Field(default_factory=SbarSummaryDTO)
    citations: list[CitationDTO] = Field(default_factory=list)
    ai_rationale: str | None = Field(default=None)
    transcript: list[ClinicalTranscriptMessageDTO] = Field(
        default_factory=list,
        description="Chỉ trả cho nhân viên đang phụ trách ca",
    )
    specialist_review: SpecialistReviewContextDTO = Field(
        default_factory=SpecialistReviewContextDTO,
    )


class InboxItemDTO(BaseModel):
    """Một dòng trong hộp thư trạm trực.

    Chỉ mang đủ thông tin để nhân viên quyết định mở ca nào trước. Nội dung lâm
    sàng đầy đủ vẫn phải tải qua API có kiểm quyền.
    """

    case_id: str
    patient_name: str
    age: int | None = Field(default=None)
    sex: str | None = Field(default=None)
    chief_complaint: str = Field(default="")
    ai_recommended_esi: EsiLevel | None = Field(default=None)
    is_red_flag: bool = Field(default=False)
    priority: Literal["RED_FLAG", "URGENT", "NORMAL"] = Field(default="NORMAL")
    preview: str = Field(
        default="",
        description="Trích ngắn tin gần nhất của người bệnh, đã cắt độ dài",
    )
    unread_count: int = Field(default=0, ge=0)
    last_message_at: datetime | None = Field(default=None)
    assignee: NurseIdentityDTO | None = Field(default=None)
    case_version: int = Field(ge=1)


class InboxResponseDTO(BaseModel):
    items: list[InboxItemDTO] = Field(default_factory=list)
    total_unread: int = Field(default=0, ge=0)
    urgent_unread: int = Field(default=0, ge=0)


class SendCaseMessageRequestDTO(BaseModel):
    """Tin nhắn do nhân viên lâm sàng gửi cho bệnh nhân trong một ca."""

    model_config = ConfigDict(str_strip_whitespace=True)

    content: str = Field(min_length=1, max_length=2000)
    # Do client sinh: một lần bấm gửi chỉ tạo đúng một bản ghi kể cả khi mạng
    # chập chờn và người dùng bấm lại.
    client_message_id: str | None = Field(default=None, max_length=64)


class CaseMessagesResponseDTO(BaseModel):
    """Toàn bộ hội thoại của ca kèm số tin phía lâm sàng chưa đọc."""

    case_id: str
    messages: list[ClinicalTranscriptMessageDTO] = Field(default_factory=list)
    unread_count: int = Field(default=0, ge=0)


class EmergencyContactPersonDTO(BaseModel):
    """Một đầu mối liên hệ, luôn nói rõ đây là ai so với ca bệnh."""

    label: str = Field(description="Vai trò so với ca bệnh, ví dụ 'Bệnh nhân' hoặc 'Người liên hệ'")
    full_name: str | None = Field(default=None)
    relationship: str | None = Field(default=None)
    phone: str | None = Field(
        default=None,
        description="None nghĩa là chưa khai báo; giao diện phải hiện 'Chưa cập nhật', không được bịa số",
    )


class EmergencyContactResponseDTO(BaseModel):
    """Danh bạ khẩn cấp của một ca.

    Tách bạch ba đầu mối vì một ca có thể thuộc về người thân chứ không phải chủ
    tài khoản: gọi nhầm số chủ tài khoản khi bệnh nhân là trẻ nhỏ là một sai sót
    lâm sàng thật, không phải chi tiết trình bày.
    """

    case_id: str
    contacts: list[EmergencyContactPersonDTO] = Field(default_factory=list)
    expires_at: datetime


class ClaimCaseRequestDTO(BaseModel):
    case_version: int = Field(ge=1)
    action: Literal["CLAIM", "RELEASE"] = Field(default="CLAIM")
    reason: str | None = Field(default=None, min_length=5, max_length=300)

    @model_validator(mode="after")
    def require_release_reason(self) -> "ClaimCaseRequestDTO":
        if self.action == "RELEASE" and not self.reason:
            raise ValueError("Trả ca về hàng đợi phải có lý do")
        return self


class UpdateObservationsRequestDTO(BaseModel):
    case_version: int = Field(ge=1)
    observations: list[ClinicalObservationInputDTO] = Field(min_length=1, max_length=6)


class UpdateIntakeRequestDTO(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    case_version: int = Field(ge=1)
    chief_complaint: str = Field(
        min_length=2,
        max_length=160,
        description="Triệu chứng chính theo ghi nhận lâm sàng; không phải chẩn đoán",
    )


class TriageDecisionRequestDTO(BaseModel):
    case_version: int = Field(ge=1)
    decision_type: Literal["CONFIRM_ESI", "ADJUST_ESI"] = Field(description="Loại quyết định phân luồng")
    final_esi: EsiLevel = Field(description="ESI cuối do Điều dưỡng chốt")
    reason_code: str = Field(min_length=2, max_length=80)
    note: str | None = Field(default=None, max_length=500)


class EscalateCaseRequestDTO(BaseModel):
    case_version: int = Field(ge=1)
    reason_code: str = Field(min_length=2, max_length=80)
    note: str = Field(min_length=10, max_length=500)


class HandoffCaseRequestDTO(BaseModel):
    case_version: int = Field(ge=1)
    destination: Literal["IMMEDIATE_CARE", "PRIORITY_IN_PERSON", "ROUTINE_QUEUE"]
    note: str = Field(min_length=5, max_length=800)


class AcknowledgeAlertRequestDTO(BaseModel):
    case_version: int = Field(ge=1)


class PiiAccessRequestDTO(BaseModel):
    reason: str = Field(min_length=10, max_length=300)


class PiiAccessResponseDTO(BaseModel):
    case_id: str
    full_name: str
    phone: str | None = None
    emergency_contact_name: str | None = None
    emergency_contact_phone: str | None = None
    expires_at: datetime


class NurseActionResponseDTO(BaseModel):
    success: bool = Field(default=True)
    case_id: str
    review_status: ReviewStatus
    case_version: int = Field(ge=1)
    message: str
