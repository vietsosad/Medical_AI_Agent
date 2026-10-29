"""Định Danh Các DTO Kháng Chịu Lỗi Bất Biến (Strict Pydantic v2 Auth DTO Schemas).

Tuân thủ tuyệt đối quy tắc tại .agents/rules/backend-rules.md (Mục 3.6 & Pydantic Strict Mode):
- Đóng vách ngăn 100% Request và Response Payload khi giao tiếp với Frontend @[frontend/src/services/auth.service.ts].
- Tuyệt đối nói KHÔNG với việc trả ngược raw ORM hay Dict tự do tại Endpoint Controller.
"""

import re

from pydantic import BaseModel, ConfigDict, Field, field_validator

EMAIL_REGEX = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")

class UserProfileDTO(BaseModel):
    """DTO định danh nhân viên lâm sàng hoặc Bệnh nhân trả về Frontend."""
    model_config = ConfigDict(from_attributes=True)

    id: str = Field(..., description="UUID định danh duy nhất của tài khoản")
    name: str = Field(..., description="Họ tên hiển thị")
    email: str = Field(..., description="Địa chỉ Email chính danh")
    role: str = Field(default="PATIENT", description="Quyền RBAC chuẩn (PATIENT, CLINICAL_NURSE, SYSTEM_ADMIN...)")
    avatar: str | None = Field(default=None, description="URL ảnh đại diện (OAuth avatar)")
    department: str | None = Field(default=None, description="Phụ trách Khoa / Chuyên khoa Y")
    phoneNumber: str | None = Field(default=None, description="Số điện thoại / Liên lạc SMS OTP")
    capabilities: list[str] = Field(
        default_factory=list,
        description="Năng lực bổ sung ngoài quyền nền của vai trò, ví dụ SPECIALIST_REVIEW của bác sĩ",
    )


class AuthResponseDTO(BaseModel):
    """DTO Chuẩn phản hồi khi xác minh Đăng nhập, Đăng ký hoặc đổi OAuth thành công."""
    access_token: str = Field(..., description="Thẻ quyền Bearer Token ngắn ngày")
    refresh_token: str | None = Field(default=None, description="Thẻ quyền Refresh Token dài ngày cho Silent Retry")
    token_type: str = Field(default="Bearer", description="Định dạng Header Authentication")
    expires_in: int = Field(default=86400, description="Thời gian sống của Access Token tính bằng giây")
    user: UserProfileDTO = Field(..., description="Hồ sơ định danh trọn vẹn")


class LoginRequestDTO(BaseModel):
    """DTO Payload xác thực khi người dùng gửi yêu cầu Đăng Nhập."""
    email: str = Field(..., description="Địa chỉ Email hợp lệ")
    password: str = Field(..., min_length=8, description="Mật khẩu tài khoản (tối thiểu 8 ký tự)")

    @field_validator("email")
    @classmethod
    def clean_email(cls, v: str) -> str:
        val = v.strip().lower()
        if not EMAIL_REGEX.match(val):
            raise ValueError("Định dạng địa chỉ Email y khoa không hợp lệ.")
        return val


class RefreshTokenRequestDTO(BaseModel):
    """DTO Payload yêu cầu gia hạn và xoay vòng đôi thẻ quyền Access & Refresh Token (Refresh Token Rotation)."""
    refresh_token: str | None = Field(default=None, description="Thẻ quyền Refresh Token JWT (nếu không tự gắn trong Cookie)")


class RegisterRequestDTO(BaseModel):
    """DTO Payload xin gia nhập hệ thống AI Triage Cấp Cứu."""
    name: str = Field(..., min_length=2, max_length=150, description="Họ và Tên (2 - 150 ký tự)")
    email: str = Field(..., description="Địa chỉ Email y khoa cá nhân")
    password: str = Field(..., min_length=8, description="Mật khẩu bảo mật cá nhân")
    department: str | None = Field(default=None, description="Tên phòng Khoa làm việc (tuỳ ý)")
    phoneNumber: str | None = Field(default=None, description="Số điện thoại di động (tuỳ ý)")

    @field_validator("email")
    @classmethod
    def clean_email(cls, v: str) -> str:
        val = v.strip().lower()
        if not EMAIL_REGEX.match(val):
            raise ValueError("Định dạng địa chỉ Email y khoa không hợp lệ.")
        return val


class VerifyOtpRequestDTO(BaseModel):
    """DTO Thẻ kiểm toán Mã OTP 6 chữ số.

    ``email`` là bắt buộc: thiếu nó, mã chỉ còn là 6 chữ số được dò trên mọi tài
    khoản cùng lúc, và mã của bất kỳ ai khớp trước sẽ mở phiên cho người đó.
    """
    email: str = Field(..., description="Email sở hữu mã xác nhận")
    code: str = Field(..., min_length=6, max_length=6, description="Mã PIN 6 chữ số")
    purpose: str = Field(default="REGISTRATION", description="Mục đích xác thực (REGISTRATION | PASSWORD_RESET)")

    @field_validator("email")
    @classmethod
    def clean_email(cls, v: str) -> str:
        return v.strip().lower()

    @field_validator("code")
    @classmethod
    def only_digits(cls, v: str) -> str:
        clean_v = "".join(filter(str.isdigit, v))
        if len(clean_v) != 6:
            raise ValueError("Mã bảo mật y khoa OTP bắt buộc phải gồm chính xác 6 chữ số nguyên.")
        return clean_v


class ForgotPasswordRequestDTO(BaseModel):
    """DTO xin cấp phát lại liên kết hoặc mã khôi phục mật khẩu."""
    email: str = Field(..., description="Email đăng nhập cần khôi phục")

    @field_validator("email")
    @classmethod
    def clean_email(cls, v: str) -> str:
        val = v.strip().lower()
        if not EMAIL_REGEX.match(val):
            raise ValueError("Định dạng địa chỉ Email y khoa không hợp lệ.")
        return val


class ResendRegistrationOtpRequestDTO(ForgotPasswordRequestDTO):
    """DTO xin gửi lại mã xác minh cho tài khoản vừa đăng ký, chưa kích hoạt."""
    email: str = Field(..., description="Email vừa dùng để đăng ký")


class ResetPasswordRequestDTO(BaseModel):
    """DTO cập nhật mật khẩu mới thông qua OTP / Token thuyên chuyển."""
    email: str = Field(..., description="Email của tài khoản cần đổi Mật khẩu")
    token: str | None = Field(default=None, description="Token ủy thác đổi mật khẩu (hoặc mã OTP)")
    otp: str | None = Field(default=None, description="Mã PIN 6 chữ số OTP")
    newPassword: str = Field(..., min_length=8, description="Mật khẩu mới (tối thiểu 8 ký tự)")

    @field_validator("email")
    @classmethod
    def clean_email(cls, v: str) -> str:
        return v.strip().lower()


class StandardMessageResponseDTO(BaseModel):
    """DTO chuẩn phản hồi các tín hiệu nghiệp vụ thông thường (Success boolean & message)."""
    success: bool = Field(default=True, description="Cờ trạng thái thành công")
    message: str = Field(..., description="Thông điệp tường minh thông báo cho Bác sĩ/Bệnh nhân")


class OAuthUrlResponseDTO(BaseModel):
    """DTO Trả về liên kết cổng Đăng nhập OAuth Ngoại vi."""
    url: str = Field(..., description="URL trạm OAuth Google hoặc GitHub")
    provider: str = Field(..., description="Tên nhà cung cấp (google, github)")


class OAuthCallbackRequestDTO(BaseModel):
    """DTO Nhận Mã xác nhận Authorization Code từ Frontend gửi lên sau khi xác thực OAuth."""
    code: str = Field(..., description="Mã Code hợp lệ do Google/GitHub phát hành")
    provider: str | None = Field(default=None, description="Nhà cung cấp tương ứng")


# =====================================================================
# CẬP NHẬT SỐ ĐIỆN THOẠI LIÊN LẠC CỦA CHÍNH CHỦ TÀI KHOẢN
# =====================================================================

# Di động Việt Nam: 10 chữ số, đầu số 03 / 05 / 07 / 08 / 09.
# Cố định Việt Nam: 11 chữ số, đầu số 02 theo quy hoạch kho số hiện hành.
VN_PHONE_REGEX = re.compile(r"^(0[35789]\d{8}|02\d{9})$")

# Chặn payload rác trước khi chuẩn hóa: "+84 (024) 3936-1414" vẫn nằm dưới ngưỡng này.
MAX_RAW_PHONE_LENGTH = 24


def normalize_vietnam_phone(raw_value: str) -> str:
    """Chuẩn hóa số điện thoại Việt Nam về dạng nội địa bắt đầu bằng số 0.

    Chấp nhận các cách viết thông dụng (khoảng trắng, dấu chấm, gạch nối, dấu ngoặc,
    tiền tố quốc tế +84 hoặc 84) rồi quy về một dạng lưu trữ duy nhất.
    Ném ValueError kèm thông điệp tiếng Việt tường minh khi số không hợp lệ.
    """
    trimmed = raw_value.strip()
    if len(trimmed) > MAX_RAW_PHONE_LENGTH:
        raise ValueError("Số điện thoại quá dài. Vui lòng nhập số điện thoại Việt Nam hợp lệ.")

    digits_only = re.sub(r"[\s.\-()]", "", trimmed)
    if not re.fullmatch(r"\+?\d+", digits_only or ""):
        raise ValueError("Số điện thoại chỉ được chứa chữ số và các ký tự phân cách thông dụng.")

    if digits_only.startswith("+84"):
        national = "0" + digits_only[3:]
    elif digits_only.startswith("84") and len(digits_only) >= 11:
        national = "0" + digits_only[2:]
    else:
        national = digits_only

    if not VN_PHONE_REGEX.match(national):
        raise ValueError(
            "Số điện thoại không đúng định dạng Việt Nam "
            "(ví dụ 0912345678, +84912345678 hoặc số cố định 02439361414)."
        )
    return national


class UpdatePhoneNumberRequestDTO(BaseModel):
    """DTO cập nhật số điện thoại liên lạc của chính chủ tài khoản đang đăng nhập.

    Không nhận user id từ client: danh tính luôn lấy từ Bearer Token phía server.
    """

    phoneNumber: str | None = Field(
        default=None,
        max_length=MAX_RAW_PHONE_LENGTH,
        description="Số điện thoại Việt Nam; để trống hoặc null nghĩa là gỡ bỏ số hiện tại",
    )

    @field_validator("phoneNumber")
    @classmethod
    def clean_phone_number(cls, v: str | None) -> str | None:
        if v is None or not v.strip():
            return None
        return normalize_vietnam_phone(v)
