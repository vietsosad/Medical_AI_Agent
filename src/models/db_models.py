"""Mô hình dữ liệu ORM cơ cấu theo chuẩn SQLModel over SQLAlchemy.

Phân chia theo 5 thực thể chính ánh xạ 100% sang 6 Nhóm Màn hình Chức năng (UI_UX_FUNCTIONAL_GROUPS_AND_ROADMAP.md)
Tuân thủ tuyệt đối quy tắc tại .agents/rules/backend-rules.md (Pydantic DTO strictness, UUID primary keys, JSON columns).
"""

import uuid
from datetime import UTC, datetime
from typing import Any

from pgvector.sqlalchemy import Vector
from sqlalchemy import JSON, Column, Index
from sqlalchemy.dialects.postgresql import ARRAY, TEXT
from sqlmodel import Field, Relationship, SQLModel


def get_utc_now() -> datetime:
    """Trả về thời gian UTC hiện tại cho các trường timestamp (offset-naive để tương thích asyncpg PostgreSQL)."""
    return datetime.now(UTC).replace(tzinfo=None)


# =====================================================================
# 1. NHÓM DANH TÍNH, XÁC THỰC & BẢO MẬT (UI GROUP 1: IDENTITY & AUTH)
# =====================================================================
class User(SQLModel, table=True):
    """Bảng lưu trữ thông tin định danh và quyền hạn RBAC của người dùng.

    Phục vụ cho Màn hình Đăng ký/Đăng nhập, Đổi mật khẩu, OAuth (Google/GitHub)
    và chế độ đặc quyền Khách Khẩn Cấp (Guest Emergency Bypass <100ms).
    """

    __tablename__ = "users"

    id: str = Field(
        default_factory=lambda: str(uuid.uuid4()),
        primary_key=True,
        index=True,
        description="UUID định danh định dạng văn bản duy nhất",
    )
    email: str | None = Field(
        default=None, index=True, unique=True, description="Email cho tài khoản chính danh hoặc OAuth"
    )
    phone: str | None = Field(
        default=None, index=True, unique=True, description="Số điện thoại cá nhân / SMS OTP"
    )
    hashed_password: str | None = Field(
        default=None, description="Mật khẩu mã hóa bcrypt (None cho Guest hoặc OAuth)"
    )
    full_name: str = Field(default="Guest Emergency Patient", description="Họ tên hiển thị")

    # RBAC Role: GUEST_EMERGENCY | PATIENT | CLINICAL_NURSE | SYSTEM_ADMIN.
    # DOCTOR is accepted only as a legacy alias for CLINICAL_NURSE.
    role: str = Field(default="PATIENT", index=True, description="Quyền hạn RBAC trong hệ thống")

    # OAuth providers info
    oauth_provider: str = Field(default="none", description="Cổng cung cấp OAuth (none, google, github)")
    oauth_id: str | None = Field(default=None, index=True, description="ID định danh từ cổng OAuth")

    is_guest: bool = Field(default=False, description="Cờ đánh dấu tài khoản Khách Khẩn Cấp không cần đăng ký")
    is_active: bool = Field(default=True, description="Cờ trạng thái hoạt động của tài khoản")

    created_at: datetime = Field(default_factory=get_utc_now, description="Thời điểm tạo tài khoản")
    updated_at: datetime = Field(default_factory=get_utc_now, description="Thời điểm cập nhật gần nhất")

    # Relationships - Chuyển sang 1:N để cho phép 1 Chủ tài khoản sở hữu danh sách hồ sơ gia đình
    ehr_profiles: list["EHRProfile"] = Relationship(back_populates="user", sa_relationship_kwargs={"cascade": "all, delete-orphan"})
    triage_cases: list["TriageCase"] = Relationship(back_populates="patient", sa_relationship_kwargs={"foreign_keys": "TriageCase.patient_id"})


# =====================================================================
# 2. NHÓM HỒ SƠ Y KHOA & TIỀN SỬ BỆNH NỀN (UI GROUP 2: EHR LITE PROFILE)
# =====================================================================
class EHRProfile(SQLModel, table=True):
    """Bảng lưu trữ tiền sử lâm sàng, dị ứng và người liên hệ khẩn cấp cho từng thành viên gia đình.

    Dữ liệu từ bảng này sẽ được hệ thống tự động tiêm (Memory Injection) vào
    Clinical state bên trong DeepAgent runtime khi bệnh nhân khởi xướng phiên Triage mới.
    """

    __tablename__ = "ehr_profiles"

    id: str = Field(
        default_factory=lambda: str(uuid.uuid4()),
        primary_key=True,
        index=True,
    )
    user_id: str = Field(
        foreign_key="users.id",
        index=True,
        description="ID Chủ tài khoản sở hữu hồ sơ (Account Owner)",
    )

    # Định danh tường minh từng hồ sơ trong gia đình (Multi-Profile Dependent Care)
    full_name: str = Field(default="Guest Emergency Patient", description="Họ tên thành viên hồ sơ")
    relationship_type: str = Field(default="SELF", index=True, description="Mối quan hệ: SELF | CHILD | SPOUSE | PARENT | SIBLING | OTHER")
    is_primary: bool = Field(default=False, index=True, description="Cờ đánh dấu hồ sơ gốc của chính chủ tài khoản")
    dob: datetime | None = Field(default=None, description="Ngày tháng năm sinh chuẩn xác để AI tính tuổi lâm sàng/nhi khoa")
    avatar_color: str = Field(default="emerald", description="Token màu nhận diện trên giao diện UI Redesign")

    # Số liên lạc của CHÍNH thành viên này. Khác hoàn toàn với
    # ``emergency_contact_phone`` bên dưới - đó là số của người hỗ trợ khi nguy cấp.
    phone_number: str | None = Field(
        default=None, description="Số điện thoại liên lạc của thành viên hồ sơ"
    )

    age: int | None = Field(default=None, description="Tuổi bệnh nhân")
    gender: str | None = Field(default=None, description="Giới tính (Male / Female / Other)")
    blood_type: str | None = Field(default=None, description="Nhóm máu (A+, B+, O+, AB-...)")
    height_cm: float | None = Field(default=None, description="Chiều cao (cm)")
    weight_kg: float | None = Field(default=None, description="Cân nặng (kg) - Phục vụ tính BMI")

    # Lưu trữ dưới dạng cột JSON: ["Đặt Stent Mạch Vành 2024", "Huyết Áp Cao", "Hen Suyễn Mạn Tính"]
    chronic_conditions: list[str] | None = Field(
        default=None, sa_column=Column("chronic_conditions", JSON, nullable=True), description="Danh sách bệnh nền"
    )
    daily_medications: list[str] | None = Field(
        default=None, sa_column=Column("daily_medications", JSON, nullable=True), description="Thuốc dùng hàng ngày (Plavix, Insulin...)"
    )
    allergies: list[str] | None = Field(
        default=None, sa_column=Column("allergies", JSON, nullable=True), description="Dị ứng kháng sinh/thuốc (Penicillin, NSAID...)"
    )

    emergency_contact_name: str | None = Field(default=None, description="Họ tên người liên hệ khẩn cấp ưu tiên 1 (derived từ emergency_contacts_json)")
    emergency_contact_phone: str | None = Field(default=None, description="SĐT liên lạc khẩn cấp ưu tiên 1 (derived từ emergency_contacts_json)")

    # Lưu toàn bộ danh sách người liên hệ khẩn cấp dưới dạng JSON array
    # Format: [{"id": "...", "full_name": "...", "relationship": "SPOUSE", "phone_number": "...", "is_primary": true, "address": null}]
    emergency_contacts_json: list[dict] | None = Field(
        default=None,
        sa_column=Column("emergency_contacts_json", JSON, nullable=True),
        description="Danh sách người liên hệ khẩn cấp đầy đủ (JSON array) cho Multi-SOS Architecture"
    )

    updated_at: datetime = Field(default_factory=get_utc_now, description="Thời điểm cập nhật hồ sơ")

    # Relationships
    user: User | None = Relationship(back_populates="ehr_profiles")
    triage_cases: list["TriageCase"] = Relationship(back_populates="target_profile", sa_relationship_kwargs={"cascade": "all, delete-orphan"})


# =====================================================================
# 3 & 4. NHÓM TRỢ LÝ HỎI-ĐÁP CẤU TRÚC, BÁO ĐỘNG ĐỎ & LỊCH SỬ KÝ ỨC
# (UI GROUP 3 & 4: TRIAGE ENGINE, RED-FLAG OVERLAY & HISTORICAL ARCHIVES)
# =====================================================================
class TriageCase(SQLModel, table=True):
    """Bảng lưu trữ phiên Triage lâm sàng và Bản tóm tắt y khoa SBAR.

    Làm trung tâm quản lý luồng trạng thái, tra cứu RAG gốc, kết quả đề xuất ESI,
    và minh chứng ký thác phê duyệt HITL từ Điều Dưỡng/Bác Sĩ trực chiến.
    """

    __tablename__ = "triage_cases"

    id: str = Field(
        default_factory=lambda: str(uuid.uuid4()),
        primary_key=True,
        index=True,
        description="Mã định danh phiên Triage Case ID",
    )
    patient_id: str = Field(foreign_key="users.id", index=True, description="ID Bệnh nhân / Chủ tài khoản thiết bị")
    profile_id: str | None = Field(default=None, foreign_key="ehr_profiles.id", index=True, description="ID Hồ sơ y khoa cụ thể của ca chẩn đoán")
    session_title: str = Field(default="Triage Consultation", description="Tiêu đề phiên tư vấn (Tạo tự động từ triệu chứng chính)")

    # Trạng thái: IN_PROGRESS | RED_FLAG_LOCKED | HITL_REVIEWING | COMPLETED | CANCELLED
    status: str = Field(default="IN_PROGRESS", index=True, description="Trạng thái luồng khám")

    ai_proposed_esi: int | None = Field(default=None, description="Cấp độ ESI do DeepAgent đề xuất (1 ➔ 5)")
    final_clinical_esi: int | None = Field(default=None, description="Cấp độ ESI sau cùng do nhân viên lâm sàng phê duyệt")

    # Derived, confirmed-only flag kept for backward compatibility. It is true
    # only for CONFIRMED and SAFETY_FALLBACK; read ``red_flag_status`` to tell
    # a validated emergency from a precaution.
    is_red_flag_triggered: bool = Field(default=False, index=True, description="Cờ đánh dấu Báo Động Đỏ được xác nhận")
    red_flag_trigger_keyword: str | None = Field(default=None, description="Từ khóa nguy hiểm gây nhấp ngắt luồng (vd: Đau ngực, FAST)")
    red_flag_latency_ms: float | None = Field(default=None, description="Thời gian phản xạ ngắt luồng (ms - chứng minh tiêu chuẩn <50ms)")

    # Red-flag lifecycle, persisted so an alert stays answerable after the
    # conversation: when it was raised, why, what it resolved to, and by what.
    # NULL on legacy rows written before the lifecycle existed.
    red_flag_status: str | None = Field(
        default=None,
        index=True,
        description="NO_CANDIDATE | CANDIDATE | CONFIRMED | NOT_CONFIRMED | UNCERTAIN | SAFETY_FALLBACK",
    )
    red_flag_candidate_esi: int | None = Field(
        default=None,
        description="Cấp ESI thận trọng do luật an toàn đề xuất nếu ứng viên được xác nhận",
    )
    red_flag_detection_source: str | None = Field(
        default=None,
        description="DETERMINISTIC_REFLEX | CONTEXTUAL_VALIDATION | SEMANTIC_LLM | SAFETY_FALLBACK",
    )
    red_flag_resolution_reason: str | None = Field(
        default=None,
        description="Lý do bộ kiểm chứng ngữ cảnh kết luận như vậy",
    )
    red_flag_raised_at: datetime | None = Field(
        default=None,
        description="Thời điểm ứng viên báo động đỏ được nêu lần đầu",
    )
    red_flag_resolved_at: datetime | None = Field(
        default=None,
        description="Thời điểm ứng viên được kết luận (confirm/clear/fallback)",
    )

    # Phiếu SBAR tóm tắt lâm sàng: {"situation": "...", "background": "...", "assessment": "...", "recommendation": "..."}
    sbar_summary: dict[str, Any] | None = Field(
        default=None, sa_column=Column("sbar_summary", JSON, nullable=True), description="Cấu trúc phiếu SBAR"
    )
    # Trích dẫn phác đồ RAG: ["PRO_CP_001", "PRO_DYS_002"]
    rag_citations: list[str] | None = Field(
        default=None, sa_column=Column("rag_citations", JSON, nullable=True), description="Các mã trích dẫn phác đồ RAG ESI V5 gốc"
    )
    rag_citation_details: list[dict[str, Any]] | None = Field(
        default=None,
        sa_column=Column("rag_citation_details", JSON, nullable=True),
        description="Citation authority/version/section/hash used by the final proposal",
    )

    # Canonical Patient State, serialized. NULL on legacy rows, which then fall
    # back to replaying chat_messages; that fallback cannot reconstruct
    # provenance, temporal context or corrections.
    canonical_state: dict[str, Any] | None = Field(
        default=None,
        sa_column=Column("canonical_state", JSON, nullable=True),
        description="Canonical Patient State đã tuần tự hóa (facts, provenance, temporal, corrections)",
    )
    canonical_state_version: int | None = Field(
        default=None,
        description="Số phiên bản tăng dần theo mỗi lần ghi nhận fact",
    )
    # Conversation memory. Retrieval support only; canonical_state remains the
    # clinical source of truth. Scoped to this case, which is scoped to a patient.
    conversation_memory: dict[str, Any] | None = Field(
        default=None,
        sa_column=Column("conversation_memory", JSON, nullable=True),
        description="Bộ nhớ hội thoại (recent/summary/events/semantic) của riêng ca này",
    )

    # Durable conversation control: which questions have already been put to
    # this patient, which targets were accepted as unknown, and whether the
    # intake review has been confirmed.
    #
    # These used to live only in process memory, which made them three-way
    # contested: the request payload, the hot runtime state and message replay
    # each had an opinion, and the payload won every turn. That is what made a
    # confirmed intake un-confirm itself the moment the patient sent another
    # message. One durable owner, written every turn.
    conversation_control: dict[str, Any] | None = Field(
        default=None,
        sa_column=Column("conversation_control", JSON, nullable=True),
        description="Trạng thái điều phối hội thoại bền vững (xác nhận, câu đã hỏi)",
    )

    assigned_nurse_id: str | None = Field(default=None, foreign_key="users.id", description="ID nhân viên lâm sàng thẩm định")
    is_overridden: bool = Field(default=False, index=True, description="Cờ đánh dấu nhân viên lâm sàng đã điều chỉnh ESI của AI")

    reviewed_at: datetime | None = Field(default=None, description="Thời điểm hoàn tất thẩm định HITL")
    created_at: datetime = Field(default_factory=get_utc_now, index=True, description="Thời điểm mở phiên Triage")
    updated_at: datetime = Field(default_factory=get_utc_now, description="Thời điểm cập nhật phiên")

    # Relationships
    patient: User | None = Relationship(back_populates="triage_cases", sa_relationship_kwargs={"foreign_keys": "TriageCase.patient_id"})
    target_profile: EHRProfile | None = Relationship(back_populates="triage_cases", sa_relationship_kwargs={"foreign_keys": "TriageCase.profile_id"})
    messages: list["ChatMessage"] = Relationship(back_populates="triage_case", sa_relationship_kwargs={"cascade": "all, delete-orphan"})
    audit_logs: list["AuditLog"] = Relationship(back_populates="triage_case", sa_relationship_kwargs={"cascade": "all, delete-orphan"})


class NurseReviewState(SQLModel, table=True):
    """Trạng thái công việc Điều dưỡng, tách biệt khỏi trạng thái AI Triage.

    Bảng một-một này giữ quyền sở hữu ca và số phiên bản để chống hai Điều
    dưỡng cùng ghi đè một quyết định. Tạo bảng mới giúp triển khai an toàn trên
    cơ sở dữ liệu hiện hữu mà không làm thay đổi ý nghĩa ``TriageCase.status``.
    """

    __tablename__ = "nurse_review_states"

    triage_case_id: str = Field(
        foreign_key="triage_cases.id",
        primary_key=True,
        description="ID ca Triage được Điều dưỡng rà soát",
    )
    review_status: str = Field(default="WAITING_REVIEW", index=True)
    assigned_nurse_id: str | None = Field(default=None, foreign_key="users.id", index=True)
    version: int = Field(default=1, ge=1, description="Phiên bản optimistic concurrency")
    claimed_at: datetime | None = Field(default=None)
    decision_type: str | None = Field(default=None)
    decision_reason_code: str | None = Field(default=None)
    decision_note: str | None = Field(default=None)
    decided_at: datetime | None = Field(default=None)
    handoff_destination: str | None = Field(default=None)
    handoff_note: str | None = Field(default=None)
    handed_off_at: datetime | None = Field(default=None)
    alert_acknowledged_by: str | None = Field(default=None, foreign_key="users.id")
    alert_acknowledged_at: datetime | None = Field(default=None)
    created_at: datetime = Field(default_factory=get_utc_now)
    updated_at: datetime = Field(default_factory=get_utc_now)


class ClinicalObservation(SQLModel, table=True):
    """Bản ghi lâm sàng có nguồn gốc; không suy diễn giá trị từ mức ESI.

    Mỗi lần sửa tạo một bản ghi mới. Bản ghi mới nhất theo ``kind`` là giá trị
    hiện hành, còn lịch sử trước/sau được giữ trong AuditLog.
    """

    __tablename__ = "clinical_observations"

    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    triage_case_id: str = Field(foreign_key="triage_cases.id", index=True)
    kind: str = Field(index=True, description="HEART_RATE | BLOOD_PRESSURE | RESPIRATORY_RATE | SPO2 | TEMPERATURE | CONSCIOUSNESS")
    value: str | None = Field(default=None, description="Giá trị nguyên bản đã được ghi nhận")
    unit: str | None = Field(default=None)
    availability: str = Field(default="MEASURED", description="MEASURED | UNKNOWN | NOT_MEASURED | NOT_APPLICABLE")
    source: str = Field(default="UNKNOWN", description="PATIENT_REPORTED | NURSE_MEASURED | DEVICE | UNKNOWN")
    measured_at: datetime | None = Field(default=None)
    recorded_by: str = Field(foreign_key="users.id", index=True)
    created_at: datetime = Field(default_factory=get_utc_now, index=True)


class ChatMessage(SQLModel, table=True):
    """Bảng lưu trữ diễn biến các dòng thông điệp và kịch bản hỏi-đáp cấu trúc.

    Phục vụ giao diện Khai báo trắc nghiệm có cấu trúc [SCR-TRIAGE-02] và phát lại
    diễn biến hội thoại cũ trong trung tâm lưu trữ [SCR-HIST-02].
    """

    __tablename__ = "chat_messages"

    id: str = Field(
        default_factory=lambda: str(uuid.uuid4()),
        primary_key=True,
        index=True,
    )
    triage_case_id: str = Field(foreign_key="triage_cases.id", index=True, description="ID Phiên Triage")

    # Loại người gửi: PATIENT | AI_AGENT | NURSE | SYSTEM_ALERT
    sender_type: str = Field(default="PATIENT", index=True, description="Định danh tác giả dòng tin")
    content: str = Field(description="Nội dung văn bản hội thoại hoặc thông điệp cảnh báo")

    # Thẻ câu hỏi trắc nghiệm có cấu trúc do AI sinh ra (Options for quick selection)
    # Ví dụ: [{"id": "opt_1", "label": "Có, vã mồ hôi hột"}, {"id": "opt_2", "label": "Không, chỉ nhói nhẹ"}]
    structured_options: list[dict[str, Any]] | None = Field(
        default=None, sa_column=Column("structured_options", JSON, nullable=True), description="Danh sách nút chọn nhanh trắc nghiệm"
    )
    selected_option: str | None = Field(default=None, description="Lựa chọn trắc nghiệm mà bệnh nhân đã ấn chọn")

    # Ai thực sự viết dòng này. NULL trên dòng cũ và trên tin do AI/hệ thống sinh
    # ra; với tin của nhân viên lâm sàng thì luôn có, để hồ sơ giao tiếp y tế
    # quy được trách nhiệm về một con người cụ thể.
    sender_id: str | None = Field(
        default=None,
        foreign_key="users.id",
        index=True,
        description="ID người thật đã gửi tin (nhân viên lâm sàng hoặc bệnh nhân)",
    )
    sender_display_name: str | None = Field(
        default=None,
        description="Tên hiển thị tại thời điểm gửi, giữ nguyên kể cả khi hồ sơ đổi tên sau này",
    )
    read_at: datetime | None = Field(
        default=None,
        description="Thời điểm phía nhận đã đọc; NULL nghĩa là chưa đọc",
    )
    # Do client sinh ra, dùng để một lần bấm gửi không tạo hai bản ghi khi mạng
    # chập chờn và người dùng thử lại.
    client_message_id: str | None = Field(
        default=None,
        index=True,
        description="Khoá chống trùng do client sinh cho mỗi lần gửi",
    )
    # Cùng một người bệnh nói với hai đối tượng khác nhau. Không tách ra thì
    # kênh trao đổi với nhân viên y tế sẽ phát lại cả cuộc hỏi bệnh của AI.
    # NULL trên dòng cũ, đọc là TRIAGE.
    channel: str | None = Field(
        default=None,
        index=True,
        description="TRIAGE (hỏi bệnh với AI) | CARE_TEAM (trao đổi với nhân viên y tế)",
    )

    created_at: datetime = Field(default_factory=get_utc_now, index=True, description="Thời điểm gửi tin")

    # Relationships
    triage_case: TriageCase | None = Relationship(back_populates="messages")


# =====================================================================
# 5 & 6. NHÓM ĐIỀU PHỐI LÂM SÀNG HITL & QUẢN TRỊ DEV/OPS (AUDIT & TELEMETRY)
# (UI GROUP 5 & 6: CLINICAL NURSE KANBAN, ACID LEDGER & KPI CONCORDANCE RATE)
# =====================================================================
class AuditLog(SQLModel, table=True):
    """Bảng Kiểm Toán Bất Biến (Immutable ACID Audit Ledger).

    Lưu lại 100% các sự kiện quan trọng trong hệ thống:
    - Quyết định Phê Duyệt / Can Thiệp Override của Bác sĩ (Kèm Clinical Justification).
    - Thời gian trễ RAG (RAG Latency) và các lần ngắt luồng <50ms Reflex.
    - Lịch sử mở khóa thông tin cá nhân bảo mật (PII Unmasked events).
    Phục vụ trực tiếp cho việc tính toán Đồng Hồ KPI Đồng Thuận Concordance Rate > 85%.
    """

    __tablename__ = "audit_logs"

    id: str = Field(
        default_factory=lambda: str(uuid.uuid4()),
        primary_key=True,
        index=True,
    )
    # Sự kiện: HITL_APPROVE | HITL_OVERRIDE | REFLEX_50MS_TRIGGER | RAG_LATENCY_LOG | PII_UNMASKED | AUTH_LOGIN | PASSWORD_CHANGE
    event_type: str = Field(default="HITL_APPROVE", index=True, description="Phân loại sự kiện kiểm toán")

    triage_case_id: str | None = Field(default=None, foreign_key="triage_cases.id", index=True, description="ID Ca Triage liên đới")
    actor_id: str | None = Field(default=None, foreign_key="users.id", index=True, description="ID Người thực hiện hành động")
    actor_role: str = Field(default="SYSTEM", description="Vai trò của tác nhân (SYSTEM_AI, CLINICAL_NURSE...)")

    # Lưu vết trạng thái trước và sau khi thay đổi (Before vs After State)
    before_state: dict[str, Any] | None = Field(
        default=None, sa_column=Column("before_state", JSON, nullable=True), description="Trạng thái trước thay đổi (vd: AI ESI = 3)"
    )
    after_state: dict[str, Any] | None = Field(
        default=None, sa_column=Column("after_state", JSON, nullable=True), description="Trạng thái sau thay đổi (vd: Nurse ESI = 2)"
    )

    # Lý do chuyên khoa bắt buộc khi Bác sĩ/Điều Dưỡng thiếp lập Override
    clinical_justification: str | None = Field(
        default=None, description="Văn phong giải thích lý do lâm sàng của nhân viên y tế khi can thiệp đổi cấp ESI"
    )

    latency_ms: float | None = Field(default=None, description="Thời gian xử lý của sự kiện (RAG latency / Reflex latency)")
    timestamp: datetime = Field(default_factory=get_utc_now, index=True, description="Thời gian xảy ra sự kiện")

    # Relationships
    triage_case: TriageCase | None = Relationship(back_populates="audit_logs")


# =====================================================================
# 6. BẢNG XÁC NHẬN MÃ OTP (REGISTER, PASSWORD RECOVERY & 2FA)
# =====================================================================
class OtpCode(SQLModel, table=True):
    """Bảng lưu trữ Mã xác thực OTP lâm sàng 6 chữ số cho các nghiệp vụ Y khoa.

    Cơ chế bảo mật 3 tầng:
    - Kiểm soát thời gian hiệu lực tuyệt đối qua cột expires_at (thực thi UTC).
    - Cờ is_used loại bỏ hoàn toàn nguy cơ tấn công phát lại (Replay Attacks).
    - Phân chia mục đích rõ ràng (REGISTRATION vs PASSWORD_RESET vs TWO_FACTOR).
    """

    __tablename__ = "otp_codes"

    id: str = Field(
        default_factory=lambda: str(uuid.uuid4()),
        primary_key=True,
        index=True,
    )
    email: str = Field(index=True, description="Email Bác sĩ/Bệnh nhân nhận mã OTP")
    code: str = Field(index=True, description="Mã PIN bảo mật 6 chữ số (000000 - 999999)")

    # Mục đích: REGISTRATION | PASSWORD_RESET | TWO_FACTOR
    purpose: str = Field(default="REGISTRATION", index=True, description="Mục đích sử dụng mã")
    is_used: bool = Field(default=False, index=True, description="Cờ đánh dấu mã đã được kích hoạt hay chưa")

    expires_at: datetime = Field(index=True, description="Thời điểm hết hạn hiệu lực của mã OTP")
    created_at: datetime = Field(default_factory=get_utc_now, index=True, description="Thời điểm phát sinh mã OTP")


# =====================================================================
# 7. BẢNG QUẢN TRỊ PHIÊN LÀM VIỆC & XOAY VÒNG REFRESH TOKEN (SESSION ROTATION)
# =====================================================================
class RefreshTokenSession(SQLModel, table=True):
    """Bảng quản lý phiên Đăng nhập và Thẻ quyền Refresh Token (Refresh Token Rotation & Revocation).

    Cơ chế bảo mật y tế an toàn kép:
    - Lưu trữ danh sách Refresh Token hợp lệ của từng Bác sĩ / Bệnh nhân.
    - Cho phép thu hồi thẻ (Revocation) ngay lập tức khi Đăng xuất (Logout) hoặc nghi ngờ có rò rỉ.
    - Thực thi Xoay Vòng Thẻ Quyền (Refresh Token Rotation): Mỗi khi dùng Refresh Token để gia hạn, thẻ cũ lập tức bị đánh dấu vô hiệu hóa (is_revoked=True) và một cặp Access + Refresh Token mới được phát hành.
    """

    __tablename__ = "refresh_token_sessions"

    id: str = Field(
        default_factory=lambda: str(uuid.uuid4()),
        primary_key=True,
        index=True,
    )
    user_id: str = Field(foreign_key="users.id", index=True, description="ID Tài khoản Bác sĩ / Bệnh nhân sở hữu phiên")
    refresh_token: str = Field(index=True, unique=True, description="Chuỗi thẻ quyền Refresh Token JWT hợp lệ")
    is_revoked: bool = Field(default=False, index=True, description="Cờ đánh dấu token đã bị thu hồi / đăng xuất hay chưa")
    expires_at: datetime = Field(index=True, description="Thời điểm hết hạn của Refresh Token (mặc định 7 ngày)")
    created_at: datetime = Field(default_factory=get_utc_now, description="Thời điểm khởi tạo phiên làm việc")

# =====================================================================
# 8. RAG KNOWLEDGE BASE MODELS (MIETIC)
# =====================================================================

class ESIKnowledgeDocument(SQLModel, table=True):
    """Pass 5 AHRQ ESI corpus: the only source eligible as protocol authority.

    ``retrieval_scope`` is the authority boundary and is enforced at the query
    layer, not by prompt convention: CLINICAL_AUTHORITY may justify an ESI
    decision, CASE_SUPPORT and CONTEXT_ONLY may only support or explain one.

    ``payload`` keeps the full Pass-5 metadata — decision_points, esi_level,
    population, retrieval_facets, numeric_expressions — so the retriever can
    filter on a decision point instead of hoping semantic similarity lands on
    the right rule.
    """

    __tablename__ = "esi_knowledge_documents"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    document_id: str = Field(index=True, unique=True, description="Stable Pass 5 retrieval ID")
    pass5_version: str = Field(index=True, description="Corpus version for idempotent updates")
    document_kind: str = Field(index=True)
    retrieval_scope: str = Field(index=True, description="CLINICAL_AUTHORITY | CASE_SUPPORT | CONTEXT_ONLY")
    atom_type: str = Field(index=True)
    retrieval_text: str
    retrieval_text_sha256: str = Field(index=True)

    payload: dict = Field(default_factory=dict, sa_column=Column(JSON))

    embedding: list[float] = Field(sa_column=Column(Vector(1024)))
    keywords: list[str] = Field(default_factory=list, sa_column=Column(ARRAY(TEXT)))

    indexed_at: datetime = Field(default_factory=get_utc_now)

    __table_args__ = (
        Index(
            "ix_esi_knowledge_docs_embedding_hnsw",
            "embedding",
            postgresql_using="hnsw",
            postgresql_with={"m": 16, "ef_construction": 64},
            postgresql_ops={"embedding": "vector_cosine_ops"},
        ),
        Index(
            "ix_esi_knowledge_docs_keywords_gin",
            "keywords",
            postgresql_using="gin",
        ),
    )


class MieticCase(SQLModel, table=True):
    """Canonical MIETIC patient case — case support only, never protocol authority.

    One row is one *patient*, not one task record. The raw corpus asks up to
    three separate ESI questions about the same presentation (life-saving
    intervention, ESI-2 criteria, resource count), so 9,627 task rows collapse
    to 5,590 cases whose assessments are held together here.

    The columns are deliberately split by trust level:

    - ``presentation_text`` and everything derived from it are patient facts,
      extracted only from the raw patient description.
    - ``assessments`` holds generated clinical analysis. It is provenance, and
      is never promoted into a patient fact.
    - ``validated_esi_level`` is populated only when the decision-point answers
      agree; ``label_status`` says why when it is NULL. The task prompt is
      never treated as a label.
    """

    __tablename__ = "mietic_cases"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    case_id: str = Field(index=True, unique=True, description="Stable id derived from the presentation")

    # --- patient facts (source: raw `input` only) ---
    presentation_text: str
    presentation_sha256: str = Field(index=True)
    age_years: float | None = Field(default=None)
    age_band: str | None = Field(default=None, index=True, description="ESI danger-zone vital band")
    sex: str | None = Field(default=None, index=True)
    vitals: dict[str, Any] = Field(default_factory=dict, sa_column=Column("vitals", JSON))
    clinical_features: list[Any] = Field(
        default_factory=list,
        sa_column=Column("clinical_features", JSON),
        description="Source-grounded features, each carrying the span it came from",
    )
    symptom_concepts: list[str] = Field(default_factory=list, sa_column=Column(ARRAY(TEXT)))

    # --- generated analysis (source: raw `output`; provenance, not fact) ---
    assessments: list[Any] = Field(
        default_factory=list,
        sa_column=Column("assessments", JSON),
        description="Per-decision-point analyses (A/B/C) with their source record ids",
    )

    # --- labels, only where the answers support one ---
    candidate_esi_levels: list[int] = Field(default_factory=list, sa_column=Column("candidate_esi_levels", JSON))
    label_status: str = Field(index=True, description="CONSISTENT | CONFLICTING | UNKNOWN")
    validated_esi_level: int | None = Field(default=None, index=True)

    # --- retrieval ---
    retrieval_text: str
    retrieval_text_sha256: str = Field(index=True)
    embedding: list[float] = Field(sa_column=Column(Vector(1024)))

    # --- provenance ---
    source_record_ids: list[str] = Field(default_factory=list, sa_column=Column(ARRAY(TEXT)))
    source_record_count: int = Field(default=0)
    dataset_version: str
    parser_version: str
    llm_model: str | None = Field(default=None)
    llm_prompt_version: str | None = Field(default=None)
    embedding_model: str
    embedding_dimensions: int

    # --- authority, fixed by construction ---
    document_type: str = Field(default="case_example", index=True)
    retrieval_scope: str = Field(default="CASE_SUPPORT", index=True)
    authority_status: str = Field(default="NOT_PROTOCOL", index=True)

    indexed_at: datetime = Field(default_factory=get_utc_now)

    __table_args__ = (
        Index(
            "ix_mietic_cases_embedding_hnsw",
            "embedding",
            postgresql_using="hnsw",
            postgresql_with={"m": 16, "ef_construction": 64},
            postgresql_ops={"embedding": "vector_cosine_ops"},
        ),
        Index(
            "ix_mietic_cases_symptom_concepts_gin",
            "symptom_concepts",
            postgresql_using="gin",
        ),
    )


# =====================================================================
# 6. NHÓM THÔNG TIN SỨC KHỎE GIÁO DỤC CỘNG ĐỒNG (HEALTH EDUCATION)
# =====================================================================
class HealthTopic(SQLModel, table=True):
    """Chủ đề sức khỏe hiển thị ở mục "Thông tin sức khỏe đáng chú ý" trên trang chủ.

    Đây là nội dung GIÁO DỤC SỨC KHỎE, không phải công cụ tự chẩn đoán và không
    phải dữ liệu dịch tễ. Mọi nội dung lâm sàng (triệu chứng, dấu hiệu cần chú ý,
    cách phòng ngừa) đều đến từ nguồn y tế được trích dẫn trong ``source`` /
    ``source_url`` và được nạp từ seed có cấu trúc.

    ``summary`` là phần DUY NHẤT mô hình ngôn ngữ được phép chạm vào: nó chỉ diễn
    giải lại nội dung đã có cho dễ đọc. LLM không được thêm số ca, xu hướng dịch,
    mức độ phổ biến, nguồn hay khuyến cáo điều trị mới - xem
    ``src/services/health_topic_summary.py``.
    """

    __tablename__ = "health_topics"

    id: str = Field(
        default_factory=lambda: str(uuid.uuid4()),
        primary_key=True,
        index=True,
    )
    slug: str = Field(index=True, unique=True, description="Định danh URL, ví dụ 'sot-xuat-huyet'")
    name: str = Field(description="Tên chủ đề sức khỏe hiển thị cho người dùng")

    # Bản tóm tắt seed luôn tồn tại; bản do LLM diễn giải là tuỳ chọn và có thể vắng.
    summary: str = Field(description="Tóm tắt ngắn lấy từ seed đã biên soạn")
    ai_summary: str | None = Field(
        default=None, description="Bản diễn giải dễ hiểu do LLM viết lại từ chính nội dung seed"
    )
    ai_summary_model: str | None = Field(
        default=None, description="Tên model đã tạo ai_summary, phục vụ truy vết"
    )
    ai_summary_generated_at: datetime | None = Field(
        default=None, description="Thời điểm sinh ai_summary (dùng để cache, không gọi LLM mỗi request)"
    )

    symptoms: list[str] = Field(
        default_factory=list, sa_column=Column("symptoms", JSON, nullable=False), description="Triệu chứng thường gặp"
    )
    warning_signs: list[str] = Field(
        default_factory=list, sa_column=Column("warning_signs", JSON, nullable=False), description="Dấu hiệu cần chú ý"
    )
    prevention: list[str] = Field(
        default_factory=list, sa_column=Column("prevention", JSON, nullable=False), description="Cách phòng ngừa"
    )
    when_to_seek_care: str = Field(default="", description="Khi nào nên đi khám")

    source: str = Field(description="Tên tổ chức y tế phát hành nội dung")
    source_url: str = Field(description="Đường dẫn tới tài liệu gốc")
    last_updated: datetime = Field(default_factory=get_utc_now, description="Ngày cập nhật nội dung")

    status: str = Field(default="PUBLISHED", index=True, description="PUBLISHED | DRAFT | ARCHIVED")
    display_order: int = Field(default=0, index=True, description="Thứ tự hiển thị trên trang chủ")


# =====================================================================
# 7. NHÓM PHIÊN SIMPLE_AGENT (PILOT, SONG SONG VỚI DEEPAGENT_RUNTIME)
# =====================================================================
class SimpleAgentSessionRecord(SQLModel, table=True):
    """Persisted ``src.simple_agent.session.Session`` for one simple_agent conversation.

    Đây là bảng mới, độc lập với ``triage_cases``/``chat_messages`` của luồng
    deepagent_runtime hiện có -- không sửa, không dùng chung bảng cũ. Mọi cột
    ánh xạ 1:1 field của ``Session`` (xem ``src/simple_agent/persistence.py``
    cho logic (de)serialize set<->list). Chỉ dùng cột JSON/scalar, không
    Vector/ARRAY, nên chạy được trên cả SQLite lẫn PostgreSQL.
    """

    __tablename__ = "simple_agent_sessions"

    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    session_id: str = Field(index=True, unique=True, description="Khóa hội thoại simple_agent")
    patient_id: str | None = Field(
        default=None, foreign_key="users.id", index=True, description="Chủ sở hữu phiên, kiểm tra quyền ở tầng route"
    )

    subject_type: str = Field(default="SELF")
    subject_label: str = Field(default="")
    parked_subjects: dict[str, Any] = Field(default_factory=dict, sa_column=Column("parked_subjects", JSON))

    concepts: list[str] = Field(default_factory=list, sa_column=Column("concepts", JSON))
    concept_order: list[str] = Field(default_factory=list, sa_column=Column("concept_order", JSON))
    facts: dict[str, Any] = Field(default_factory=dict, sa_column=Column("facts", JSON))
    qualitative_observations: dict[str, str] = Field(
        default_factory=dict, sa_column=Column("qualitative_observations", JSON)
    )
    unknown_facts: list[str] = Field(default_factory=list, sa_column=Column("unknown_facts", JSON))
    needs_precision: list[str] = Field(default_factory=list, sa_column=Column("needs_precision", JSON))
    seen_atom_ids: list[str] = Field(default_factory=list, sa_column=Column("seen_atom_ids", JSON))
    # Added later (see src/simple_agent/decision.py's
    # MIN_ATOM_RELEVANCE_SCORE_FOR_PROACTIVE_ASK): best cosine relevance score
    # ever seen for each atom_id in seen_atom_ids. Nullable/defaulted via
    # _ADDITIVE_COLUMNS_BY_TABLE in src/services/db.py since this table
    # already has real pilot rows on Postgres.
    atom_relevance_score: dict[str, float] = Field(
        default_factory=dict, sa_column=Column("atom_relevance_score", JSON)
    )
    # Added later: last non-null retrieval_query Phase A produced (see
    # src/simple_agent/tools.py's finish_turn) -- English clinical-register
    # text used as decision.py's retrieve_atoms_scored query, replacing the
    # old "concept labels + raw Vietnamese message" join. Nullable/defaulted
    # via _ADDITIVE_COLUMNS_BY_TABLE in src/services/db.py, same as
    # atom_relevance_score above.
    retrieval_query: str | None = Field(default=None)
    # Added later (see src/simple_agent/session.py's Session.card_gender/
    # card_relationship): the EHR profile card picked at /start, if any --
    # None for an anonymous session. Nullable/defaulted via
    # _ADDITIVE_COLUMNS_BY_TABLE in src/services/db.py, same as
    # atom_relevance_score/retrieval_query above.
    card_gender: str | None = Field(default=None)
    card_relationship: str | None = Field(default=None)

    last_question: str | None = Field(default=None)
    stale_question_streak: int = Field(default=0)
    confirmation_offered: bool = Field(default=False)
    resource_count_estimated: bool = Field(default=False)

    history: list[list[str]] = Field(default_factory=list, sa_column=Column("history", JSON))
    tool_log_tail: list[dict[str, Any]] = Field(default_factory=list, sa_column=Column("tool_log_tail", JSON))

    created_at: datetime = Field(default_factory=get_utc_now, index=True)
    updated_at: datetime = Field(default_factory=get_utc_now)


class SimpleAgentChatSession(SQLModel, table=True):
    """Domain-level control record for one simple_agent conversation ("phiên làm việc").

    Distinct from ``SimpleAgentSessionRecord`` above, which persists the raw
    engine state (``Session`` dataclass fields) needed to resume Phase
    A/B/C mid-conversation. This table answers a different question: is this
    session still open, and -- once it isn't -- what did it conclude with.
    One row per ``session_id``, created on ``/simple-triage/start`` and
    updated on every ``/simple-triage/chat/{session_id}`` turn.

    ``status`` is the session lifecycle:

    - ``ACTIVE``: still accepting messages.
    - ``COMPLETED``: the agent reached a terminal turn (``RETURN_MATCH`` or
      ``RETURN_INCOMPLETE``) -- the route rejects further chat turns on this
      session_id once set, mirroring how ``routes_patient.py`` locks a
      ``TriageCase`` once ``status == "COMPLETED"``.
    - ``ABANDONED``: reserved for future use (e.g. a cleanup job marking long
      idle sessions); nothing in this pilot sets it yet.
    """

    __tablename__ = "simple_agent_chat_sessions"

    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    session_id: str = Field(index=True, unique=True, description="Cùng khóa với simple_agent_sessions.session_id")
    patient_id: str = Field(foreign_key="users.id", index=True, description="Chủ sở hữu phiên")

    status: str = Field(default="ACTIVE", index=True, description="ACTIVE | COMPLETED | ABANDONED")
    turn_count: int = Field(default=0, description="Số lượt bệnh nhân đã gửi trong phiên này")

    initial_message: str = Field(default="", description="Tin nhắn mở đầu phiên, để hiển thị danh sách phiên nhanh")
    # Added later (see src/simple_agent/session.py's Session.card_gender):
    # the EHR profile card chosen at /start, if any -- None for an anonymous
    # session. No foreign_key= (same reasoning as card_gender/card_relationship
    # on SimpleAgentSessionRecord): ownership was already checked once at
    # /start time, this is just carried through so the UI can keep showing
    # "đang khám cho ai" throughout the conversation without re-deriving it.
    # Nullable/defaulted via _ADDITIVE_COLUMNS_BY_TABLE in src/services/db.py
    # since this table already has real pilot rows on Postgres.
    profile_id: str | None = Field(default=None)

    # Kết quả cuối cùng -- chỉ có giá trị khi status == COMPLETED.
    final_route: str | None = Field(default=None, description="route của lượt kết thúc, vd TRIAGE | NON_CLINICAL")
    final_action: str | None = Field(default=None, description="action của lượt kết thúc, vd RETURN_MATCH | RETURN_INCOMPLETE")
    matched_esi_levels: list[int] = Field(
        default_factory=list, sa_column=Column("matched_esi_levels", JSON), description="Các mức ESI được atom hỗ trợ khi kết luận"
    )
    final_message: str | None = Field(default=None, description="Câu trả lời cuối cùng của agent cho lượt kết thúc")
    final_concepts: list[str] = Field(
        default_factory=list, sa_column=Column("final_concepts", JSON), description="Snapshot concept lúc kết thúc, tra cứu nhanh không cần join"
    )

    started_at: datetime = Field(default_factory=get_utc_now, index=True)
    last_activity_at: datetime = Field(default_factory=get_utc_now, index=True)
    completed_at: datetime | None = Field(default=None)


class SimpleAgentChatMessage(SQLModel, table=True):
    """One row per message in a simple_agent conversation -- full history, never truncated.

    ``Session.history`` (inside ``SimpleAgentSessionRecord``) is a capped
    last-10-turns window kept only to give the LLM recent context; this
    table is the durable, queryable record of the whole conversation, the
    simple_agent analogue of ``ChatMessage`` for the deepagent_runtime flow.

    ``channel``/``read_at``/``client_message_id`` were added later (see
    ``src/api/routes_nurse_simple.py``'s care-team endpoints) to let this same
    table also carry patient<->nurse messages, mirroring how the real
    ``ChatMessage`` disambiguates by ``channel`` instead of a separate thread
    table. Existing rows default to ``channel="TRIAGE"`` -- added via
    ``_ADDITIVE_COLUMNS_BY_TABLE`` in ``src/services/db.py`` since this table
    already has real pilot rows on Postgres.
    """

    __tablename__ = "simple_agent_chat_messages"

    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    session_id: str = Field(index=True, description="simple_agent_chat_sessions.session_id, không dùng FK cứng để giữ bảng độc lập, dễ test")
    turn_index: int = Field(index=True, description="Thứ tự lượt bệnh nhân trong phiên, bắt đầu từ 0")

    sender: str = Field(index=True, description="PATIENT | AGENT | NURSE")
    content: str = Field(description="Nội dung tin nhắn")

    # Chỉ có ý nghĩa với sender=AGENT -- snapshot quyết định Phase B tại đúng
    # lượt này, phục vụ audit mà không cần suy luận lại từ engine state.
    route: str | None = Field(default=None)
    action: str | None = Field(default=None)
    question_target_id: str | None = Field(default=None)
    decision_snapshot: dict[str, Any] = Field(default_factory=dict, sa_column=Column("decision_snapshot", JSON))

    # TRIAGE (hội thoại với AI) | CARE_TEAM (nhắn với y tá). Nullable vì cột
    # được thêm bằng ALTER TABLE sau khi bảng đã có dữ liệu -- dòng cũ NULL,
    # đọc là TRIAGE giống hệt quy ước của ChatMessage.channel thật. Dòng mới
    # tạo qua ORM luôn có giá trị tường minh nhờ default="TRIAGE" ở Python.
    channel: str | None = Field(default="TRIAGE", index=True)
    read_at: datetime | None = Field(default=None, description="Chỉ có ý nghĩa với channel=CARE_TEAM")
    client_message_id: str | None = Field(
        default=None, index=True, description="Khóa idempotency phía người gửi, tránh tạo tin đôi khi retry"
    )

    created_at: datetime = Field(default_factory=get_utc_now, index=True)


class SimpleAgentNurseReview(SQLModel, table=True):
    """Nurse/HITL review state for one simple_agent session -- pilot equivalent
    of ``NurseReviewState``, but 1:1 with ``SimpleAgentChatSession`` instead of
    ``TriageCase``. Deliberately a separate table, never written by
    ``routes_simple_triage.py`` -- rows are created lazily on first read by
    ``routes_nurse_simple.py`` (same pattern as ``NurseReviewState``'s
    ``_get_review_state`` in ``routes_nurse.py``), so the patient-facing pilot
    route stays untouched by this feature.

    No escalate/specialist-review/handoff-destination fields here (see
    ``.claude/plans/sunny-launching-mitten.md``): this pilot's "decision" step
    closes the case directly (``review_status`` goes straight to
    ``HANDED_OFF``), collapsing the two-step decide/handoff flow the real
    ``NurseReviewState`` supports.
    """

    __tablename__ = "simple_agent_nurse_reviews"

    session_id: str = Field(foreign_key="simple_agent_chat_sessions.session_id", primary_key=True)
    review_status: str = Field(
        default="WAITING_REVIEW",
        index=True,
        description="WAITING_REVIEW | ASSIGNED | TRIAGE_DECIDED | HANDED_OFF | PARKED",
    )
    assigned_nurse_id: str | None = Field(default=None, foreign_key="users.id", index=True)
    version: int = Field(default=0, description="Optimistic concurrency, như NurseReviewState.version")

    claimed_at: datetime | None = Field(default=None)
    decision_type: str | None = Field(default=None, description="CONFIRM_ESI | ADJUST_ESI")
    decision_reason_code: str | None = Field(default=None)
    decision_note: str | None = Field(default=None)
    final_esi: int | None = Field(default=None, description="Mức ESI do y tá chốt, có thể khác ai_proposed_esi")
    is_overridden: bool = Field(default=False)
    decided_at: datetime | None = Field(default=None)
    handed_off_at: datetime | None = Field(default=None)

    # "Tạm gác lại" -- một điều dưỡng đặt ca này sang một bên (dữ liệu vô giá
    # trị, cần liên hệ thêm bệnh nhân, v.v.) để nó không chiếm chỗ trong hàng
    # đợi chính, nhưng vẫn xem/khôi phục lại được (RESTORE). Không phải trạng
    # thái đóng ca -- khác hẳn HANDED_OFF, ai cũng đẩy lại được vào hàng đợi.
    parked_at: datetime | None = Field(default=None)
    parked_by_nurse_id: str | None = Field(default=None, foreign_key="users.id")
    parked_reason: str | None = Field(default=None)

    created_at: datetime = Field(default_factory=get_utc_now)
    updated_at: datetime = Field(default_factory=get_utc_now)


# =====================================================================
# 8. CORPUS SIMPLE_AGENT (data/siu + data/indexes_siu, migrated vào Postgres)
# =====================================================================
# Bốn bảng dưới đây là bản migrate 1:1 của data/siu/*.jsonl +
# data/indexes_siu/*.npy -- xem scripts/migrate_simple_agent_corpus_to_pg.py.
# File cục bộ KHÔNG bị xoá (vẫn là input cho script migrate và cho
# tests/test_simple_agent.py, vốn cố tình chạy offline không cần Postgres);
# nhưng runtime thật (src/agents/simple_agent_runtime/) giờ nạp corpus hoàn
# toàn từ các bảng này qua src/simple_agent/pg_corpus.py, không đọc file nữa.
class SimpleAgentClinicalConcept(SQLModel, table=True):
    """1:1 với data/siu/clinical_concepts.jsonl, cộng thêm embedding từ concept_embeddings.npy."""

    __tablename__ = "simple_agent_clinical_concepts"

    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    concept_id: str = Field(index=True, unique=True)
    canonical_name: str
    aliases: list[str] = Field(default_factory=list, sa_column=Column("aliases", JSON))
    semantic_type: str = Field(index=True)

    # text-embedding-3-small, 1536-dim -- KHÔNG cùng không gian embedding với
    # esi_knowledge_documents/mietic_cases (text-embedding-3-large, 1024-dim).
    # Không dùng chung, không convert qua lại.
    embedding: list[float] = Field(sa_column=Column(Vector(1536)))

    __table_args__ = (
        Index(
            "ix_simple_agent_concepts_embedding_hnsw",
            "embedding",
            postgresql_using="hnsw",
            postgresql_with={"m": 16, "ef_construction": 64},
            postgresql_ops={"embedding": "vector_cosine_ops"},
        ),
    )


class SimpleAgentConceptRelation(SQLModel, table=True):
    """1:1 với data/siu/concept_relations.jsonl. Không embedding.

    ``target_id`` có thể là fact_target_id (REQUIRES_ASSESSMENT_OF) hoặc
    concept_id khác (DISTINGUISHES_FROM) tuỳ ``relation_type`` -- không đặt
    FK cứng, giữ đúng cách corpus.py parse hiện tại (bỏ qua relation_type lạ
    thay vì raise lỗi).
    """

    __tablename__ = "simple_agent_concept_relations"

    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    source_concept_id: str = Field(index=True)
    relation_type: str = Field(index=True)
    target_id: str = Field(index=True)


class SimpleAgentProtocolAtom(SQLModel, table=True):
    """1:1 với data/siu/protocol_atoms.jsonl, cộng thêm embedding từ protocol_embeddings.npy."""

    __tablename__ = "simple_agent_protocol_atoms"

    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    atom_id: str = Field(index=True, unique=True)
    authority_scope: str = Field(index=True)
    source_document_id: str
    atom_type: str = Field(index=True)
    decision_point: str | None = Field(default=None, index=True)
    requirements: list[Any] = Field(default_factory=list, sa_column=Column("requirements", JSON))
    decision_effect: dict[str, Any] = Field(default_factory=dict, sa_column=Column("decision_effect", JSON))
    retrieval_text: str
    retrieval_embedding_model: str = Field(default="text-embedding-3-small")

    embedding: list[float] = Field(sa_column=Column(Vector(1536)))

    __table_args__ = (
        Index(
            "ix_simple_agent_atoms_embedding_hnsw",
            "embedding",
            postgresql_using="hnsw",
            postgresql_with={"m": 16, "ef_construction": 64},
            postgresql_ops={"embedding": "vector_cosine_ops"},
        ),
    )


class SimpleAgentFactTarget(SQLModel, table=True):
    """1:1 với data/siu/fact_targets.jsonl. Không embedding."""

    __tablename__ = "simple_agent_fact_targets"

    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    fact_target_id: str = Field(index=True, unique=True)
    name: str
    description: str = Field(default="")
    value_schema: dict[str, Any] = Field(default_factory=dict, sa_column=Column("value_schema", JSON))
    reporting_style: str = Field(index=True)
    lay_terms: str = Field(default="")
    severity_anchors: dict[str, Any] | None = Field(default=None, sa_column=Column("severity_anchors", JSON))
    # Added later (see decision.py's askable-gating logic): optional
    # {"fact_target_id": ..., "expected_value": ...} -- when set, this fact
    # is only proactively askable once the named gate fact already holds
    # that value in the session (e.g. don't ask the circumstances of a
    # fainting spell before confirming one happened at all). Nullable via
    # _ADDITIVE_COLUMNS_BY_TABLE in src/services/db.py since this table
    # already has real corpus rows on Postgres; NULL means "not gated".
    gated_by: dict[str, Any] | None = Field(default=None, sa_column=Column("gated_by", JSON))
    # Added later (see agent.py's _sex_compatible): "FEMALE" or "MALE" when
    # this fact only makes sense for one sex (e.g. pregnancy_status) --
    # None means asked regardless of sex, same as today. Nullable/defaulted
    # via _ADDITIVE_COLUMNS_BY_TABLE in src/services/db.py, same as
    # gated_by above.
    requires_sex: str | None = Field(default=None)


class SimpleAgentFactTargetEmbedding(SQLModel, table=True):
    """Patient-phrased (name + lay_terms) embedding of each fact_target, one row
    per fact_target_id -- see scripts/audit_fact_target_duplicates.py's
    ``patient_text``. A separate table, not a column added to
    SimpleAgentFactTarget (which predates pgvector and stays SQLite-friendly,
    see that class's own docstring): keeps this purely-additive index from
    forcing that already-populated table onto the Postgres-only list, so
    nothing about its existing schema or SQLite compatibility changes.
    Backs tools.py's search_fact_targets_for_text via
    decision.py's retrieve_fact_targets_scored / corpus.py's
    fact_target_embeddings -- see Corpus._read_index_files("fact_target_patient")
    for the file-based equivalent (data/indexes_siu/fact_target_patient_*)."""

    __tablename__ = "simple_agent_fact_target_embeddings"

    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    fact_target_id: str = Field(index=True, unique=True)
    embedding_model: str = Field(default="text-embedding-3-small")
    embedding: list[float] = Field(sa_column=Column(Vector(1536)))

    __table_args__ = (
        Index(
            "ix_simple_agent_fact_target_embeddings_hnsw",
            "embedding",
            postgresql_using="hnsw",
            postgresql_with={"m": 16, "ef_construction": 64},
            postgresql_ops={"embedding": "vector_cosine_ops"},
        ),
    )


# =====================================================================
# 8. NHÓM CƠ SỞ Y TẾ THAM CHIẾU (NEARBY FACILITY DIRECTORY)
# =====================================================================
class MedicalFacility(SQLModel, table=True):
    """Danh bạ cơ sở y tế do dự án tự biên soạn, dùng để tìm cơ sở gần người bệnh.

    Đây là dữ liệu HÀNH CHÍNH (tên, địa chỉ, toạ độ, số điện thoại), KHÔNG phải
    dữ liệu lâm sàng và không tham gia vào bất kỳ suy luận ESI nào. Bảng này
    hoàn toàn độc lập với ``triage_cases`` và toàn bộ nhóm bảng
    ``simple_agent_*``; không có khoá ngoại nào trỏ sang chúng.

    **Chỉ chứa dữ liệu tự biên soạn có trích dẫn nguồn.** Kết quả trả về từ
    Google Places KHÔNG bao giờ được ghi xuống bảng này: điều khoản Google Maps
    Platform không cho lưu nội dung Places quá 30 ngày, và trộn hai nguồn vào
    một bảng sẽ làm mất dấu vết xuất xứ của từng bản ghi.

    ``emergency_capability`` cố ý có trạng thái ``UNKNOWN`` và mặc định rơi vào
    đó: theo đúng nguyên tắc ``UNKNOWN != NEGATIVE`` của hệ thống, "chưa xác
    minh được cơ sở này có khoa cấp cứu" không được phép hiển thị thành "không
    có khoa cấp cứu", và cũng không được phép hiển thị thành "có".
    """

    __tablename__ = "medical_facilities"

    id: str = Field(
        default_factory=lambda: str(uuid.uuid4()),
        primary_key=True,
        index=True,
    )
    slug: str = Field(index=True, unique=True, description="Định danh ổn định trong file seed")
    name: str = Field(description="Tên cơ sở y tế hiển thị cho người dùng")
    facility_type: str = Field(
        default="HOSPITAL",
        description="HOSPITAL | CLINIC | HEALTH_STATION | SPECIALIST_CENTER",
    )
    address: str = Field(description="Địa chỉ đầy đủ để đọc cho tổng đài 115 hoặc tài xế")
    province: str = Field(index=True, description="Tỉnh/thành phố, dùng để lọc và soát seed")
    latitude: float = Field(description="Vĩ độ, hệ WGS84")
    longitude: float = Field(description="Kinh độ, hệ WGS84")
    phone_number: str | None = Field(
        default=None, description="Số điện thoại công bố; None nghĩa là chưa xác minh được"
    )
    emergency_capability: str = Field(
        default="UNKNOWN",
        description="EMERGENCY_DEPARTMENT khi nguồn trích dẫn nói rõ có khoa cấp cứu, ngược lại UNKNOWN",
    )
    # ``place_id`` là trường DUY NHẤT của Google được phép lưu lâu dài theo điều
    # khoản Maps Platform. Ở đây nó chỉ giúp deep link chỉ đường trỏ đúng địa
    # điểm; None thì deep link rơi về toạ độ, vẫn hoạt động bình thường.
    google_place_id: str | None = Field(default=None, description="Place ID của Google Maps, nếu đã tra được")
    source: str = Field(description="Tổ chức công bố thông tin cơ sở này")
    source_url: str = Field(description="Đường dẫn tới nguồn công bố")
    last_verified: datetime = Field(default_factory=get_utc_now, description="Lần rà soát thủ công gần nhất")
    status: str = Field(default="PUBLISHED", index=True, description="PUBLISHED | DRAFT | ARCHIVED")
