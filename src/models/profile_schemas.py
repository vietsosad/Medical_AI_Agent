"""Định Danh Các DTO Kháng Chịu Lỗi Bất Biến Cho Hồ Sơ Gia Đình (Strict Pydantic v2 Profile DTOs).

Tuân thủ tuyệt đối quy tắc tại .agents/rules/backend-rules.md:
- An toàn chuẩn Pydantic v2 Strict Mode.
- Đóng vách ngăn 100% Request và Response Payload khi giao tiếp với Frontend @[frontend/src/services/profile.service.ts].
"""

import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from src.models.auth_schemas import MAX_RAW_PHONE_LENGTH, normalize_vietnam_phone

# ============================================================================
# 1. SHARED ENUMS & CONSTANTS
# ============================================================================

RELATIONSHIP_TYPES = Literal["CHILD", "SPOUSE", "PARENT", "SIBLING", "OTHER", "SELF"]
EMERGENCY_RELATIONSHIP_TYPES = Literal["SPOUSE", "PARENT", "CHILD", "SIBLING", "FRIEND", "OTHER"]
GENDER_TYPES = Literal["MALE", "FEMALE", "OTHER"]
BLOOD_TYPES = Literal["A+", "A-", "B+", "B-", "O+", "O-", "AB+", "AB-", "UNKNOWN"]
ALLERGY_TYPES = Literal["MEDICATION", "FOOD", "ENVIRONMENT", "OTHER"]
SEVERITY_TYPES = Literal["HIGH", "MEDIUM", "LOW"]


def _normalize_gender(raw: str | None) -> str | None:
    """Normalize gender string từ 'Male/Female/Other' → 'MALE/FEMALE/OTHER' để khớp với Frontend Zod schema."""
    if raw is None:
        return None
    return raw.strip().upper()


# ============================================================================
# 2. PROFILE RESPONSE & REQUEST DTOs
# ============================================================================

class ProfileResponseDTO(BaseModel):
    """DTO Phụ trách thông tin chi tiết từng hồ sơ trong gia đình (Multi-Profile Dependent Care)."""
    model_config = ConfigDict(from_attributes=True)

    id: str = Field(..., description="UUID định danh hồ sơ thành viên")
    user_id: str = Field(..., description="UUID tài khoản sở hữu hồ sơ")

    full_name: str = Field(..., description="Họ và tên thành viên")
    relationship_type: str = Field(..., description="Mối quan hệ: SELF | CHILD | SPOUSE | PARENT | SIBLING | OTHER")
    is_primary: bool = Field(default=False, description="Cờ đánh dấu hồ sơ gốc của chủ tài khoản")
    dob: str | None = Field(default=None, description="Ngày sinh ISO string")
    avatar_color: str = Field(default="emerald", description="Token màu nhận diện trên UI (emerald, blue, rose, zinc, slate)")

    age: int | None = Field(default=None, description="Tuổi bệnh nhân")
    gender: str | None = Field(default=None, description="Giới tính (MALE / FEMALE / OTHER)")
    blood_type: str | None = Field(default=None, description="Nhóm máu (A+, B+, O+, AB-...)")
    height_cm: float | None = Field(default=None, description="Chiều cao (cm)")
    weight_kg: float | None = Field(default=None, description="Cân nặng (kg)")

    chronic_conditions: list[str] | None = Field(default=None, description="Danh sách bệnh nền mạn tính")
    daily_medications: list[str] | None = Field(default=None, description="Danh sách thuốc dùng hàng ngày")
    allergies: list[str] | None = Field(default=None, description="Danh sách dị ứng thuốc/kháng sinh")

    emergency_contact_name: str | None = Field(default=None, description="Tên người liên hệ khẩn cấp ưu tiên 1")
    phone_number: str | None = Field(default=None, description="Số điện thoại liên lạc của thành viên")
    emergency_contact_phone: str | None = Field(default=None, description="SĐT liên hệ khẩn cấp ưu tiên 1")
    updated_at: str | None = Field(default=None, description="Thời điểm cập nhật hồ sơ gần nhất (ISO string)")

    @field_validator("gender", mode="before")
    @classmethod
    def normalize_gender_field(cls, v: object) -> str | None:
        if v is None:
            return None
        return str(v).strip().upper()

    @field_validator("dob", "updated_at", mode="before")
    @classmethod
    def serialize_datetime_fields(cls, v: object) -> str | None:
        """Convert datetime objects → ISO string trước khi Pydantic validate type."""
        if v is None:
            return None
        if hasattr(v, "isoformat"):
            return v.isoformat()  # type: ignore[union-attr]
        return str(v)

    @field_validator("chronic_conditions", "daily_medications", "allergies", mode="before")
    @classmethod
    def extract_names_from_dicts(cls, v: object) -> list[str] | None:
        """Extract 'name' from dicts if stored as structured JSONB in db."""
        if v is None:
            return None
        if isinstance(v, list):
            result = []
            for item in v:
                if isinstance(item, dict) and "name" in item:
                    result.append(item["name"])
                elif isinstance(item, str):
                    result.append(item)
                else:
                    result.append(str(item))
            return result
        return v


class CreateProfileRequestDTO(BaseModel):
    """DTO Payload tạo nhanh hồ sơ người thân phụ thuộc (< 15 giây Agile Onboarding)."""
    full_name: str = Field(..., min_length=2, max_length=150, description="Họ và Tên thành viên gia đình")
    relationship_type: str = Field(..., description="Mối quan hệ: CHILD | SPOUSE | PARENT | SIBLING | OTHER | SELF")
    dob: datetime | None = Field(default=None, description="Ngày sinh hợp lệ")
    age: int | None = Field(default=None, ge=0, le=125, description="Tuổi bệnh nhân (0 - 125 tuổi)")
    gender: str | None = Field(default=None, description="Giới tính (Male / Female / Other hoặc MALE / FEMALE / OTHER)")
    avatar_color: str = Field(default="emerald", description="Token màu: emerald | blue | purple | rose | amber")

    phone_number: str | None = Field(
        default=None,
        max_length=MAX_RAW_PHONE_LENGTH,
        description="Số điện thoại liên lạc của chính thành viên này",
    )

    blood_type: str | None = Field(default=None, description="Nhóm máu (A+, B+, O+, AB-...)")
    height_cm: float | None = Field(default=None, gt=0, lt=300, description="Chiều cao (cm)")
    weight_kg: float | None = Field(default=None, gt=0, lt=500, description="Cân nặng (kg)")

    chronic_conditions: list[str] | None = Field(default=None, description="Danh sách bệnh nền (tuỳ chọn)")
    daily_medications: list[str] | None = Field(default=None, description="Danh sách thuốc dùng hàng ngày (tuỳ chọn)")
    allergies: list[str] | None = Field(default=None, description="Danh sách dị ứng thuốc (tuỳ chọn)")
    emergency_contact_name: str | None = Field(default=None, description="Người liên hệ khẩn cấp")
    emergency_contact_phone: str | None = Field(default=None, description="SĐT liên hệ khẩn cấp")

    @field_validator("relationship_type")
    @classmethod
    def validate_relationship(cls, v: str) -> str:
        allowed = {"CHILD", "SPOUSE", "PARENT", "SIBLING", "OTHER", "SELF"}
        upper_val = v.upper().strip()
        if upper_val not in allowed:
            raise ValueError(f"Mối quan hệ '{v}' không nằm trong danh sách hỗ trợ ({allowed}).")
        return upper_val

    @field_validator("phone_number")
    @classmethod
    def clean_member_phone(cls, v: str | None) -> str | None:
        """Cùng một luật số điện thoại Việt Nam với số của chủ tài khoản."""
        if v is None or not v.strip():
            return None
        return normalize_vietnam_phone(v)



class UpdateProfileRequestDTO(BaseModel):
    """DTO Payload cập nhật chi tiết hoặc chèn ký ức hội thoại (Progressive Disclosure) cho hồ sơ."""
    full_name: str | None = Field(default=None, min_length=2, max_length=150)
    relationship_type: str | None = Field(default=None)
    dob: datetime | None = Field(default=None)
    age: int | None = Field(default=None, ge=0, le=125)
    gender: str | None = Field(default=None)
    avatar_color: str | None = Field(default=None)

    phone_number: str | None = Field(
        default=None,
        max_length=MAX_RAW_PHONE_LENGTH,
        description="Số điện thoại liên lạc của chính thành viên này",
    )

    blood_type: str | None = Field(default=None)
    height_cm: float | None = Field(default=None, gt=0, lt=300)
    weight_kg: float | None = Field(default=None, gt=0, lt=500)

    chronic_conditions: list[str] | None = Field(default=None)
    daily_medications: list[str] | None = Field(default=None)
    allergies: list[str] | None = Field(default=None)

    emergency_contact_name: str | None = Field(default=None)
    emergency_contact_phone: str | None = Field(default=None)

    @field_validator("relationship_type")
    @classmethod
    def validate_relationship(cls, v: str | None) -> str | None:
        if v is None:
            return None
        allowed = {"CHILD", "SPOUSE", "PARENT", "SIBLING", "OTHER", "SELF"}
        upper_val = v.upper().strip()
        if upper_val not in allowed:
            raise ValueError(f"Mối quan hệ '{v}' không hợp lệ.")
        return upper_val

    @field_validator("phone_number")
    @classmethod
    def clean_member_phone(cls, v: str | None) -> str | None:
        """Cùng một luật số điện thoại Việt Nam với số của chủ tài khoản."""
        if v is None or not v.strip():
            return None
        return normalize_vietnam_phone(v)


# ============================================================================
# 3. EHR LITE & EMERGENCY CONTACT DTOs
# ============================================================================

class AllergyDTO(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    type: str
    severity: str


class MedicationDTO(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    dosage: str
    frequency: str


class EhrLiteDTO(BaseModel):
    """DTO cho Hồ Sơ Lâm Sàng Rút Gọn (EHR Lite). last_updated trả về ISO string để khớp Frontend Zod schema."""
    patient_id: str
    age: int | None = None
    gender: str | None = None
    height_cm: float | None = None
    weight_kg: float | None = None
    blood_type: str | None = None
    chronic_conditions: list[str] = []
    allergies: list[AllergyDTO] = []
    current_medications: list[MedicationDTO] = []
    last_updated: str | None = None  # Trả về ISO string, không phải datetime object

    @field_validator("last_updated", mode="before")
    @classmethod
    def serialize_last_updated(cls, v: object) -> str | None:
        """Convert datetime → ISO string trước khi Pydantic validate type."""
        if v is None:
            return None
        if hasattr(v, "isoformat"):
            return v.isoformat()  # type: ignore[union-attr]
        return str(v)

    @field_validator("gender", mode="before")
    @classmethod
    def normalize_gender(cls, v: object) -> str | None:
        if v is None:
            return None
        return str(v).strip().upper()


class EmergencyContactDTO(BaseModel):
    """DTO một thẻ người liên hệ khẩn cấp SOS."""
    id: str | None = Field(default=None)
    full_name: str = Field(..., min_length=2, description="Họ tên người liên hệ")
    relationship: str = Field(..., description="Mối quan hệ: SPOUSE | PARENT | CHILD | SIBLING | FRIEND | OTHER")
    phone_number: str = Field(..., description="Số điện thoại liên hệ")
    is_primary: bool = Field(default=False, description="Cờ liên hệ ưu tiên số 1")
    address: str | None = Field(default=None, description="Địa chỉ (tuỳ chọn)")

    @field_validator("relationship")
    @classmethod
    def validate_emergency_relationship(cls, v: str) -> str:
        allowed = {"SPOUSE", "PARENT", "CHILD", "SIBLING", "FRIEND", "OTHER"}
        upper_val = v.upper().strip()
        if upper_val not in allowed:
            raise ValueError(f"Mối quan hệ khẩn cấp '{v}' không hợp lệ.")
        return upper_val
