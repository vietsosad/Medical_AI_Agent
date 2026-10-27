"""Hồ Sơ Cung Cấp Dependency Injection Cho FastAPI (Authentication & SQLModel Sessions).

Tuân thủ quy chuẩn kỹ thuật tại .agents/rules/backend-rules.md:
- Bắt buộc dùng cú pháp Annotated[..., Depends(...)] từ quy ước hiện đại của FastAPI.
- Truy vấn dữ liệu bất đồng bộ 100% qua AsyncSession non-blocking.
- Xác thực và thẩm định thẻ quyền Bearer Token cho mọi endpoint an ninh y tế.
"""

from typing import Annotated

from fastapi import Depends, HTTPException, Security, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from src.models.db_models import User
from src.services.db import get_async_session
from src.services.security import decode_access_token

# Khai báo chuẩn giao thức HTTP Bearer Token của FastAPI
security_bearer = HTTPBearer(auto_error=False)

# 1. Dependency tiêm AsyncSession cho toàn bộ các Router
SessionDep = Annotated[AsyncSession, Depends(get_async_session)]
TokenDep = Annotated[HTTPAuthorizationCredentials | None, Security(security_bearer)]


async def get_current_user(
    session: SessionDep,
    token_credentials: TokenDep,
) -> User:
    """Dependency trích xuất Bearer Token, kiểm định chữ ký JWT và truy hồi Hồ sơ người dùng từ CSDL."""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Thẻ quyền định danh y khoa không hợp lệ, bị mất, hoặc đã hết chu kỳ sống.",
        headers={"WWW-Authenticate": "Bearer"},
    )

    if not token_credentials or not token_credentials.credentials:
        raise credentials_exception

    token = token_credentials.credentials
    payload = decode_access_token(token)
    if not payload:
        raise credentials_exception

    subject: str = str(payload.get("sub", ""))
    if not subject:
        raise credentials_exception

    # Truy vấn Hồ sơ User trong CSDL (ưu tiên tìm theo UUID id trước, fallback email)
    query = select(User).where(User.id == subject)
    result = await session.execute(query)
    user = result.scalars().first()

    if not user and "@" in subject:
        query_email = select(User).where(User.email == subject)
        result_email = await session.execute(query_email)
        user = result_email.scalars().first()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Tài khoản gắn liền với token này đã bị bãi miễn hoặc không tồn tại."
        )

    if not user.is_active and not user.is_guest:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Tài khoản này đã bị khóa hoặc chưa hoàn tất bước xác minh OTP lâm sàng."
        )

    return user


# 2. Dependency tiêm User hiện tại cho các endpoint đòi hỏi đặc quyền đăng nhập
CurrentUserDep = Annotated[User, Depends(get_current_user)]


async def get_current_patient(current_user: CurrentUserDep) -> User:
    """Authorize patient-owned Triage and EHR operations at the API boundary."""
    if current_user.role not in {"PATIENT", "GUEST", "GUEST_EMERGENCY"}:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Chức năng này chỉ dành cho Bệnh nhân hoặc Khách được xác thực.",
        )
    return current_user


PatientUserDep = Annotated[User, Depends(get_current_patient)]


CLINICAL_STAFF_ROLES = frozenset({"CLINICAL_NURSE", "DOCTOR"})

# Bác sĩ dùng chung toàn bộ console với điều dưỡng; khác biệt duy nhất là được
# nhận những ca đã chuyển lên đánh giá chuyên sâu. Mô hình hoá bằng năng lực
# (capability) thay vì tách hẳn vai trò, để một tài khoản DOCTOR vẫn đi qua đúng
# guard và đúng tuyến điều hướng mà điều dưỡng đang dùng.
CAPABILITY_SPECIALIST_REVIEW = "SPECIALIST_REVIEW"


def staff_capabilities(user: User) -> list[str]:
    """Các năng lực bổ sung của một tài khoản lâm sàng, ngoài quyền nền."""
    if user.role == "DOCTOR":
        return [CAPABILITY_SPECIALIST_REVIEW]
    return []


async def get_current_nurse(current_user: CurrentUserDep) -> User:
    """Authorize the unified clinical role, including legacy Doctor accounts."""
    if current_user.role not in CLINICAL_STAFF_ROLES:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Chức năng này chỉ dành cho nhân viên lâm sàng phân luồng.",
        )
    return current_user


NurseUserDep = Annotated[User, Depends(get_current_nurse)]


async def get_specialist_reviewer(current_user: CurrentUserDep) -> User:
    """Chỉ tài khoản bác sĩ mới nhận được ca đang chờ đánh giá chuyên sâu."""
    if CAPABILITY_SPECIALIST_REVIEW not in staff_capabilities(current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Chỉ bác sĩ mới tiếp nhận được ca đang chờ đánh giá chuyên sâu.",
        )
    return current_user


SpecialistUserDep = Annotated[User, Depends(get_specialist_reviewer)]


async def get_optional_user(
    session: SessionDep,
    token_credentials: TokenDep,
) -> User | None:
    """Dependency tiêm User (tự động fallback null nếu là Guest hoặc không gửi token)."""
    if not token_credentials or not token_credentials.credentials:
        return None
    try:
        return await get_current_user(session, token_credentials)
    except HTTPException:
        return None


OptionalUserDep = Annotated[User | None, Depends(get_optional_user)]
