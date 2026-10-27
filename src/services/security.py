"""Dịch vụ Bảo Mật, Mã Hóa & Quản lý Thẻ Quyền JWT / OTP (Security & Token Service).

Tuân thủ quy chuẩn kỹ thuật tại .agents/rules/backend-rules.md:
- Mã hóa mật khẩu an toàn theo chuẩn bcrypt.
- Khởi tạo và xác nhận Token Bearer JWT cho phiên định danh lâm sàng (RBAC).
- Phát sinh Mã OTP 6 chữ số ngẫu nhiên an toàn bằng thư viện cryptographically secure (secrets).
"""

import secrets
import string
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

import bcrypt
import jwt
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from src.config import get_settings
from src.models.db_models import RefreshTokenSession, User, get_utc_now
from src.services.log_redaction import pseudonym

settings = get_settings()


# =====================================================================
# 1. HỆ THỐNG MÃ HÓA & KIỂM CHỨNG MẬT KHẨU (BCRYPT HASHING ENGINE)
# =====================================================================

def hash_password(password: str) -> str:
    """Mã hóa mật khẩu bằng thuật toán bcrypt với salt tự do.

    An toàn tuyệt đối trước mọi hình thức dịch ngược tấn công Rainbow Table.
    """
    salt = bcrypt.gensalt(rounds=12)
    hashed = bcrypt.hashpw(password.encode("utf-8"), salt)
    return hashed.decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Đối chiếu mật khẩu người dùng nhập vào với chuỗi băm lưu trữ trong CSDL."""
    if not hashed_password or not plain_password:
        return False
    try:
        return bcrypt.checkpw(
            plain_password.encode("utf-8"),
            hashed_password.encode("utf-8")
        )
    except Exception as e:
        print(f"⚠️ [Security Service Exception] Lỗi đối chiếu chuỗi băm bcrypt: {e}")
        return False


# =====================================================================
# 2. HỆ THỐNG PHÁT HÀNH & KIỂM VỰC THẺ JWT BEARER (STATELESS AUTHENTICATION)
# =====================================================================

def create_access_token(subject: str, additional_claims: dict[str, Any] | None = None) -> str:
    """Phát hành Access Token cho phiên làm việc lâm sàng."""
    now = datetime.now(UTC)
    expire = now + timedelta(minutes=settings.access_token_expire_minutes)

    payload: dict[str, Any] = {
        "sub": str(subject),  # User ID hoặc Email UUID
        "iat": now,
        "exp": expire,
        "type": "access",
        "jti": str(uuid.uuid4()),
    }
    if additional_claims:
        payload.update(additional_claims)

    encoded_jwt = jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)
    return encoded_jwt


def create_refresh_token(subject: str) -> str:
    """Phát hành Refresh Token có hiệu lực dài ngày (7 ngày mặc định)."""
    now = datetime.now(UTC)
    expire = now + timedelta(minutes=settings.refresh_token_expire_minutes)

    payload = {
        "sub": str(subject),
        "iat": now,
        "exp": expire,
        "type": "refresh",
        "jti": str(uuid.uuid4()),
    }

    encoded_jwt = jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)
    return encoded_jwt


def decode_jwt_token(token: str) -> dict[str, Any] | None:
    """Giải mã và thẩm định hiệu lực chữ ký của JWT Token.

    Trả về Dict dữ liệu payload hoặc None nếu token sai chữ ký / đã hết hạn.
    """
    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret_key,
            algorithms=[settings.jwt_algorithm]
        )
        return payload
    except jwt.ExpiredSignatureError:
        # Token đã vượt quá thời hạn exp
        return None
    except jwt.InvalidTokenError:
        # Chữ ký bất hợp pháp hoặc dữ liệu bị can thiệp
        return None


def decode_access_token(token: str) -> dict[str, Any] | None:
    """Như ``decode_jwt_token`` nhưng chỉ nhận thẻ ``type == "access"``.

    Refresh token cùng chữ ký và sống 7 ngày; nếu cổng API nhận nó như access
    token thì vòng xoay refresh không còn giới hạn được gì.
    """
    payload = decode_jwt_token(token)
    if not payload or payload.get("type") != "access":
        return None
    return payload


# =====================================================================
# 3. QUẢN TRỊ PHIÊN LÀM VIỆC CSDL & XOAY VÒNG REFRESH TOKEN (SESSION ENGINE)
# =====================================================================

async def create_session_tokens(db: AsyncSession, user: User) -> tuple[str, str]:
    """Phát hành cặp đôi Access & Refresh Token mới, ghi nhận hồ sơ vào CSDL PostgreSQL.
    
    Trả về tuple: (access_token, refresh_token).
    """
    access_token = create_access_token(
        subject=user.id,
        additional_claims={"role": user.role, "email": user.email}
    )
    refresh_token = create_refresh_token(subject=user.id)

    now_utc = get_utc_now()
    expires_at = now_utc + timedelta(minutes=settings.refresh_token_expire_minutes)

    # Khởi tạo bản ghi phiên làm việc trong CSDL
    session_record = RefreshTokenSession(
        user_id=user.id,
        refresh_token=refresh_token,
        is_revoked=False,
        expires_at=expires_at,
        created_at=now_utc,
    )
    db.add(session_record)
    await db.commit()
    await db.refresh(session_record)

    print(f"🔐 [Session Engine] Cấp mới thẻ quyền cho hồ sơ y khoa [{pseudonym(user.id, prefix='user')}] - Hết hạn Refresh Token lúc: {expires_at.strftime('%Y-%m-%d %H:%M:%S')} UTC")
    return access_token, refresh_token


async def rotate_refresh_token(db: AsyncSession, old_refresh_token: str) -> tuple[User, str, str] | None:
    """Thực hiện Xoay Vòng Thẻ Quyền (Refresh Token Rotation).
    
    Kiểm chứng chữ ký JWT và tình trạng hồ sơ CSDL của thẻ cũ:
    - Nếu hợp lệ: Đánh dấu thu hồi thẻ cũ (is_revoked=True), cấp cặp thẻ mới và trả về (user, new_access_token, new_refresh_token).
    - Nếu hết hạn/bị thu hồi/rách chữ ký: Trả về None.
    """
    payload = decode_jwt_token(old_refresh_token)
    if not payload or payload.get("type") != "refresh":
        print("⚠️ [Session Engine] Thẻ Refresh Token gửi lên có chữ ký sai lệch hoặc không hợp pháp.")
        return None

    user_id = payload.get("sub")
    if not user_id:
        return None

    # Đối chiếu hồ sơ thẻ quyền trong CSDL
    stmt = select(RefreshTokenSession).where(
        RefreshTokenSession.refresh_token == old_refresh_token,
        RefreshTokenSession.is_revoked == False
    )
    result = await db.execute(stmt)
    session_record = result.scalar_one_or_none()

    now_utc = get_utc_now()
    if not session_record or session_record.expires_at <= now_utc:
        print(f"❌ [Session Engine] Thẻ quyền của User [{pseudonym(user_id, prefix='user')}] đã bị thu hồi trong CSDL hoặc hết hạn.")
        return None

    # Đánh dấu vô hiệu hóa lập tức thẻ cũ để ngăn chặn việc sử dụng lại (Replay Attack Protection)
    session_record.is_revoked = True
    db.add(session_record)

    # Lấy thông tin tài khoản người dùng
    user = await db.get(User, str(user_id))
    if not user or not user.is_active:
        await db.commit()
        return None

    # Phát hành cặp thẻ quyền hoàn toàn mới
    new_access, new_refresh = await create_session_tokens(db, user)
    return user, new_access, new_refresh


async def revoke_session_token(db: AsyncSession, refresh_token: str | None = None, user_id: str | None = None) -> None:
    """Thu hồi và xả hủy hiệu lực của Refresh Token khi người dùng Đăng xuất (Logout)."""
    if refresh_token:
        stmt = select(RefreshTokenSession).where(RefreshTokenSession.refresh_token == refresh_token)
        result = await db.execute(stmt)
        session_record = result.scalar_one_or_none()
        if session_record:
            session_record.is_revoked = True
            db.add(session_record)
            await db.commit()
            print("🔴 [Session Engine] Đã thu hồi chính xác thẻ quyền Refresh Token của phiên đăng xuất.")
    elif user_id:
        # Trong trường hợp đăng xuất khẩn cấp không mang kèm refresh_token cụ thể -> vô hiệu hóa tất cả token của user
        stmt = select(RefreshTokenSession).where(
            RefreshTokenSession.user_id == user_id,
            RefreshTokenSession.is_revoked == False
        )
        result = await db.execute(stmt)
        active_sessions = result.scalars().all()
        for s in active_sessions:
            s.is_revoked = True
            db.add(s)
        if active_sessions:
            await db.commit()
            print(f"🔴 [Session Engine] Đã dọn dẹp và thu hồi trọn bộ ({len(active_sessions)}) phiên làm việc của User [{pseudonym(user_id, prefix='user')}].")


# =====================================================================
# 4. MÁY PHÁT SINH MÁ PIN OTP AN TOÀN (CRYPTOGRAPHIC OTP GENERATOR)
# =====================================================================

def generate_otp_code(length: int = 6) -> str:
    """Phát sinh mã bảo mật PIN gồm `length` chữ số nguyên ngẫu nhiên (chuẩn y tế).

    Sử dụng `secrets.choice()` thay vì `random` để đảm bảo tiêu chuẩn an ninh mật mã NIST.
    """
    digits = string.digits
    otp = "".join(secrets.choice(digits) for _ in range(length))
    return otp
