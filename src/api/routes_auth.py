"""APIRouter Giao Tiếp Cổng Định Danh, Xác Thực, OAuth & OTP (Auth Router Group 1).

Tuân thủ quy chuẩn kỹ thuật tại .agents/rules/backend-rules.md:
- APIRouter(prefix="/auth", tags=["Identity & Auth (Group 1)"]).
- 100% Non-blocking AsyncSession query execution.
- Strict Pydantic v2 DTOs cho toàn bộ request và response payload.
- Quản trị trọn gói phiên làm việc CSDL và Xoay vòng Refresh Token (Token Rotation + HTTP Cookie injection).
"""

import secrets
import uuid
from datetime import timedelta

from fastapi import APIRouter, Cookie, Header, HTTPException, Request, Response, status
from sqlmodel import select

from src.api.dependencies import CurrentUserDep, OptionalUserDep, SessionDep
from src.config import get_settings
from src.models.auth_schemas import (
    AuthResponseDTO,
    ForgotPasswordRequestDTO,
    LoginRequestDTO,
    OAuthCallbackRequestDTO,
    OAuthUrlResponseDTO,
    RefreshTokenRequestDTO,
    RegisterRequestDTO,
    ResendRegistrationOtpRequestDTO,
    ResetPasswordRequestDTO,
    StandardMessageResponseDTO,
    UpdatePhoneNumberRequestDTO,
    UserProfileDTO,
    VerifyOtpRequestDTO,
)
from src.models.db_models import EHRProfile, OtpCode, User, get_utc_now
from src.services.email_service import send_registration_otp, send_reset_password_otp
from src.services.oauth_service import (
    authenticate_with_github,
    authenticate_with_google,
    get_github_authorization_url,
    get_google_authorization_url,
    resolve_oauth_redirect_uri,
)
from src.services.security import (
    create_session_tokens,
    generate_otp_code,
    hash_password,
    revoke_session_token,
    rotate_refresh_token,
    verify_password,
)
from src.api.dependencies import staff_capabilities
from src.services.log_redaction import mask_email, pseudonym

settings = get_settings()
router = APIRouter(prefix="/auth", tags=["Identity & Auth (Group 1)"])

# Một mã 6 chữ số chỉ an toàn khi số lần đoán bị chặn.
MAX_OTP_ATTEMPTS = 5
_OTP_INVALID_DETAIL = "Mã bảo mật OTP không hợp lệ hoặc không thuộc về tài khoản này."
_OTP_EXPIRED_DETAIL = "Mã PIN bảo mật OTP đã hết chu kỳ sống 15 phút. Vui lòng yêu cầu cấp lại mã mới."


async def _issue_otp(session: SessionDep, *, email: str, purpose: str, valid_minutes: int = 15) -> str:
    """Cấp mã mới cho (email, purpose) và huỷ mọi mã cũ chưa dùng của cặp đó.

    Không huỷ mã cũ thì mỗi lần gọi lại endpoint gửi mã sẽ thêm một mã sống nữa,
    và kẻ đoán mã có thêm một cơ hội trúng cho mỗi lần gọi. Người gọi tự commit.
    """
    stale = await session.execute(
        select(OtpCode).where(
            OtpCode.email == email,
            OtpCode.purpose == purpose,
            OtpCode.is_used == False,  # noqa: E712
        )
    )
    for old_code in stale.scalars().all():
        old_code.is_used = True
        session.add(old_code)

    otp_pin = generate_otp_code(6)
    session.add(OtpCode(
        email=email,
        code=otp_pin,
        purpose=purpose,
        expires_at=get_utc_now() + timedelta(minutes=valid_minutes),
    ))
    return otp_pin


async def _match_otp(session: SessionDep, *, email: str, code: str, purpose: str) -> OtpCode:
    """Trả về mã còn hiệu lực của đúng (email, purpose) nếu ``code`` khớp.

    Mã luôn được tra theo email, không bao giờ chỉ theo 6 chữ số: tra theo mã
    trần sẽ dò cùng lúc trên mọi tài khoản. Mỗi lần sai được đếm, chạm
    MAX_OTP_ATTEMPTS thì mã bị huỷ. Hàm không đánh dấu mã đã dùng -- người gọi
    quyết định việc đó.
    """
    res = await session.execute(
        select(OtpCode)
        .where(
            OtpCode.email == email,
            OtpCode.purpose == purpose,
            OtpCode.is_used == False,  # noqa: E712
        )
        .order_by(OtpCode.created_at.desc())  # type: ignore
    )
    otp_entry = res.scalars().first()
    if not otp_entry:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=_OTP_INVALID_DETAIL)

    expires_at = otp_entry.expires_at
    if expires_at.tzinfo is not None:
        expires_at = expires_at.replace(tzinfo=None)
    if get_utc_now() > expires_at:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=_OTP_EXPIRED_DETAIL)

    if not secrets.compare_digest(otp_entry.code.encode(), code.encode()):
        otp_entry.failed_attempts = (otp_entry.failed_attempts or 0) + 1
        if otp_entry.failed_attempts >= MAX_OTP_ATTEMPTS:
            otp_entry.is_used = True
        session.add(otp_entry)
        await session.commit()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=_OTP_INVALID_DETAIL)
    return otp_entry


def _build_user_profile_dto(user: User) -> UserProfileDTO:
    """Map internal legacy roles to the public frontend role contract."""
    public_role = {
        "DOCTOR": "CLINICAL_NURSE",
        "GUEST_EMERGENCY": "GUEST",
    }.get(user.role, user.role)
    return UserProfileDTO(
        id=user.id,
        name=user.full_name,
        email=user.email or "guest@hospital.vn",
        role=public_role,
        avatar=None,
        department=None,
        phoneNumber=user.phone,
        # Vai trò công khai của tài khoản bác sĩ vẫn là CLINICAL_NURSE để dùng
        # chung console và guard; quyền riêng của bác sĩ đi kèm ở đây.
        capabilities=staff_capabilities(user),
    )


def _set_auth_cookies(response: Response, access_token: str, refresh_token: str) -> None:
    """Đóng dấu cặp thẻ quyền Access & Refresh Token vào HTTP Response Cookies.
    
    Lưu ý kỹ thuật: httponly=False để tương thích trọn vẹn với thư viện js-cookie & Axios Interceptor bên Frontend.
    """
    is_prod = (settings.app_env == "production")
    response.set_cookie(
        key="ai20k_access_token",
        value=access_token,
        max_age=settings.access_token_expire_minutes * 60,
        path="/",
        httponly=False,
        secure=is_prod,
        samesite="lax",
    )
    response.set_cookie(
        key="ai20k_refresh_token",
        value=refresh_token,
        max_age=settings.refresh_token_expire_minutes * 60,
        path="/",
        httponly=False,
        secure=is_prod,
        samesite="lax",
    )


def _clear_auth_cookies(response: Response) -> None:
    """Xóa bỏ sạch sẽ các thẻ quyền tại Cookies khi Đăng xuất hoặc thu hồi phiên."""
    response.delete_cookie(key="ai20k_access_token", path="/")
    response.delete_cookie(key="ai20k_refresh_token", path="/")


# =====================================================================
# 1. ĐĂNG KÝ & XÁC THỰC MÃ OTP (REGISTRATION & OTP ENGINE)
# =====================================================================

@router.post("/register", response_model=StandardMessageResponseDTO, status_code=status.HTTP_201_CREATED)
async def register_clinical_user(payload: RegisterRequestDTO, session: SessionDep) -> StandardMessageResponseDTO:
    """Đăng ký hồ sơ tài khoản y khoa mới.
    
    Hệ thống khởi tạo tài khoản ở trạng thái chưa kích hoạt (is_active=False),
    phát sinh mã OTP bảo mật 6 chữ số và gửi qua máy chủ SMTP Email.
    """
    # 1. Kiểm tra Email đã được đăng ký hay chưa
    query = select(User).where(User.email == payload.email)
    res = await session.execute(query)
    existing_user = res.scalars().first()

    if existing_user:
        if existing_user.is_active:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Địa chỉ Email này đã tồn tại trong hệ thống Bệnh viện. Vui lòng thử đăng nhập hoặc sử dụng chức năng Quên mật khẩu."
            )
        else:
            # Nếu tài khoản cũ chưa kích hoạt OTP, xóa bản ghi cũ hoặc tiếp tục đắp lại hồ sơ mới
            await session.delete(existing_user)
            await session.commit()

    # 2. Mã hóa mật khẩu và tạo bản ghi User mới
    hashed_pwd = hash_password(payload.password)
    new_user = User(
        email=payload.email,
        full_name=payload.name,
        hashed_password=hashed_pwd,
        role="PATIENT",
        phone=payload.phoneNumber,
        is_active=False, # Yêu cầu bước xác thực OTP kế tiếp
    )
    session.add(new_user)
    await session.commit()
    await session.refresh(new_user)

    # 3. Khởi tạo sẵn hồ sơ bệnh án điện tử EHR Lite cho chủ tài khoản (Primary Profile - SELF)
    ehr_profile = EHRProfile(
        user_id=new_user.id,
        full_name=new_user.full_name,
        relationship_type="SELF",
        is_primary=True,
        avatar_color="emerald",
    )
    session.add(ehr_profile)

    # 4. Phát sinh và lưu mã OTP (Hiệu lực 15 phút)
    otp_pin = await _issue_otp(session, email=new_user.email, purpose="REGISTRATION")
    await session.commit()

    # 5. Gửi thư điện tử xác nhận thông qua Async SMTP Engine
    await send_registration_otp(new_user.email, new_user.full_name, otp_pin, valid_minutes=15)

    return StandardMessageResponseDTO(
        success=True,
        message=f"Hồ sơ y khoa của {new_user.full_name} đã được khởi tạo! Vui lòng kiểm tra hòm thư Email để lấy mã PIN OTP 6 chữ số."
    )


@router.post("/resend-registration-otp", response_model=StandardMessageResponseDTO)
async def resend_registration_otp(
    payload: ResendRegistrationOtpRequestDTO, session: SessionDep
) -> StandardMessageResponseDTO:
    """Gửi lại mã xác minh cho tài khoản vừa đăng ký mà chưa kích hoạt.

    Trả cùng một câu cho mọi email, giống forgot-password, để không lộ email nào
    đã có tài khoản. Mã mới huỷ mọi mã cũ (``_issue_otp``), nên sau khi gửi lại
    chỉ mã mới nhất còn dùng được.
    """
    query = select(User).where(User.email == payload.email)
    res = await session.execute(query)
    user = res.scalars().first()

    if user and not user.is_active:
        otp_pin = await _issue_otp(session, email=user.email, purpose="REGISTRATION")  # type: ignore[arg-type]
        await session.commit()
        await send_registration_otp(user.email, user.full_name, otp_pin, valid_minutes=15)  # type: ignore[arg-type]

    return StandardMessageResponseDTO(
        success=True,
        message="Nếu email này đang chờ xác minh, một mã mới đã được gửi tới hòm thư.",
    )


@router.post("/verify-otp", response_model=AuthResponseDTO | StandardMessageResponseDTO)
async def verify_clinical_otp(
    payload: VerifyOtpRequestDTO, session: SessionDep, response: Response
) -> AuthResponseDTO | StandardMessageResponseDTO:
    """Xác nhận mã bảo mật OTP 6 chữ số.

    Khi thành công: Kích hoạt chính thức hồ sơ (is_active=True), tạo bản ghi CSDL Token Session và tráo đổi lấy cặp Tokens Bearer & Cookie.
    Riêng mã PASSWORD_RESET chỉ được kiểm tra ở đây; ``/reset-password`` mới tiêu thụ nó.
    """
    # 1-2. Đối chiếu mã theo đúng email, kiểm chứng hạn dùng và số lần sai
    otp_entry = await _match_otp(session, email=payload.email, code=payload.code, purpose=payload.purpose)

    if payload.purpose == "PASSWORD_RESET":
        # Cấp phiên ở đây biến "quên mật khẩu" thành đăng nhập bằng OTP mà
        # không đổi mật khẩu, và đánh dấu mã đã dùng khiến /reset-password
        # ngay sau đó luôn báo sai mã.
        return StandardMessageResponseDTO(
            success=True,
            message="Mã xác minh hợp lệ. Vui lòng đặt mật khẩu mới.",
        )

    # 3. Đóng đinh cờ is_used = True (Chống Replay Attack)
    otp_entry.is_used = True
    session.add(otp_entry)

    # 4. Tìm kiếm tài khoản liên quan
    user_query = select(User).where(User.email == otp_entry.email)
    user_res = await session.execute(user_query)
    user = user_res.scalars().first()

    if not user:
        raise HTTPException(status_code=404, detail="Không tìm thấy tài khoản gắn với mã xác minh này.")

    if payload.purpose == "REGISTRATION" and not user.is_active:
        user.is_active = True
        session.add(user)

    await session.commit()
    await session.refresh(user)

    # 5. Cấp phát cặp đôi Tokens Bearer và ghi lưu vào CSDL Session Engine
    access_token, refresh_token = await create_session_tokens(session, user)
    _set_auth_cookies(response, access_token, refresh_token)
    user_dto = _build_user_profile_dto(user)

    return AuthResponseDTO(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="Bearer",
        expires_in=settings.access_token_expire_minutes * 60,
        user=user_dto,
    )


# =====================================================================
# 2. ĐĂNG NHẬP & PHỤT HỒI TOKEN (LOGIN & SILENT REFRESH WITH ROTATION)
# =====================================================================

@router.post("/login", response_model=AuthResponseDTO)
async def login_user(payload: LoginRequestDTO, session: SessionDep, response: Response) -> AuthResponseDTO:
    """Xác thực tài khoản bằng Email & Mật khẩu Bcrypt, thiết lập phiên CSDL & HTTP Cookies."""
    query = select(User).where(User.email == payload.email)
    res = await session.execute(query)
    user = res.scalars().first()

    if not user or not user.hashed_password:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Thông tin tài khoản Email hoặc mật khẩu không chính xác."
        )

    if not verify_password(payload.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Thông tin tài khoản Email hoặc mật khẩu không chính xác."
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Tài khoản của bạn chưa hoàn thiện bước xác thực OTP. Vui lòng kiểm tra lại hộp thư Email."
        )

    access_token, refresh_token = await create_session_tokens(session, user)
    _set_auth_cookies(response, access_token, refresh_token)
    user_dto = _build_user_profile_dto(user)

    print(f"🔓 [Auth Server] Bác sĩ/Bệnh nhân {pseudonym(user.id, prefix='user')} ({user.role}) đã đăng nhập thành công. (Token & Cookie injected)")
    return AuthResponseDTO(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="Bearer",
        expires_in=settings.access_token_expire_minutes * 60,
        user=user_dto,
    )


@router.post("/guest", response_model=AuthResponseDTO, status_code=status.HTTP_201_CREATED)
async def create_guest_session(
    session: SessionDep,
    response: Response,
) -> AuthResponseDTO:
    """Create an authenticated, non-PII guest identity for emergency triage."""
    guest = User(
        id=str(uuid.uuid4()),
        email=None,
        phone=None,
        hashed_password=None,
        full_name="Khách Triage Khẩn Cấp",
        role="GUEST_EMERGENCY",
        oauth_provider="none",
        is_guest=True,
        is_active=True,
    )
    session.add(guest)
    await session.commit()
    await session.refresh(guest)

    access_token, refresh_token = await create_session_tokens(session, guest)
    _set_auth_cookies(response, access_token, refresh_token)

    return AuthResponseDTO(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="Bearer",
        expires_in=settings.access_token_expire_minutes * 60,
        user=_build_user_profile_dto(guest),
    )


@router.post("/refresh", response_model=AuthResponseDTO)
async def refresh_access_token(
    session: SessionDep,
    response: Response,
    body: RefreshTokenRequestDTO | None = None,
    ai20k_refresh_token: str | None = Cookie(default=None),
    authorization: str | None = Header(default=None),
) -> AuthResponseDTO:
    """Điểm cuối giải tỏa 401 Silent Refresh cho Axios Interceptors & thực thi Refresh Token Rotation."""
    # 1. Tìm thẻ quyền Refresh Token từ Body JSON -> Cookie -> Header
    token_to_check: str | None = None
    if body and body.refresh_token:
        token_to_check = body.refresh_token
    elif ai20k_refresh_token:
        token_to_check = ai20k_refresh_token
    elif authorization and authorization.startswith("Bearer "):
        token_to_check = authorization.replace("Bearer ", "").strip()

    if not token_to_check:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Không tìm thấy thẻ quyền Refresh Token hợp lệ trong Body, Cookie hoặc Header."
        )

    # 2. Giao phó cho Session Engine thực hiện Xoay vòng Token (Revoke thẻ cũ -> Cấp thẻ mới)
    rotation_result = await rotate_refresh_token(session, token_to_check)
    if not rotation_result:
        _clear_auth_cookies(response)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Thẻ quyền Refresh Token đã bị vô hiệu hóa, hết hạn hoặc bị xả bỏ trong CSDL. Vui lòng đăng nhập lại."
        )

    user, new_access, new_refresh = rotation_result
    _set_auth_cookies(response, new_access, new_refresh)
    user_dto = _build_user_profile_dto(user)

    print(f"🔄 [Auth Refresher] Xoay vòng thẻ quyền thành công cho User [{pseudonym(user.id, prefix='user')}]. (Old revoked -> New active)")
    return AuthResponseDTO(
        access_token=new_access,
        refresh_token=new_refresh,
        token_type="Bearer",
        expires_in=settings.access_token_expire_minutes * 60,
        user=user_dto,
    )


# =====================================================================
# 3. QUÊN MẬT KHẨU & KHÔI PHỤC CREDITIALS (PASSWORD RECOVERY)
# =====================================================================

@router.post("/forgot-password", response_model=StandardMessageResponseDTO)
async def forgot_password_request(payload: ForgotPasswordRequestDTO, session: SessionDep) -> StandardMessageResponseDTO:
    """Tiếp nhận yêu cầu khôi phục mật khẩu và gửi mã PIN OTP 6 chữ số tới Email."""
    query = select(User).where(User.email == payload.email)
    res = await session.execute(query)
    user = res.scalars().first()

    if user and user.is_active:
        otp_pin = await _issue_otp(session, email=user.email, purpose="PASSWORD_RESET")  # type: ignore[arg-type]
        await session.commit()
        await send_reset_password_otp(user.email, otp_pin, valid_minutes=15) # type: ignore

    return StandardMessageResponseDTO(
        success=True,
        message="Nếu địa chỉ Email của bạn tồn tại trong hệ thống, mã xác thực khôi phục OTP đã được gửi tới hòm thư."
    )


@router.post("/reset-password", response_model=StandardMessageResponseDTO)
async def reset_user_password(payload: ResetPasswordRequestDTO, session: SessionDep) -> StandardMessageResponseDTO:
    """Thực thi đổi mật khẩu mới thông qua kiểm chứng Mã bảo mật OTP."""
    target_otp = payload.otp or payload.token
    if not target_otp:
        raise HTTPException(status_code=400, detail="Vui lòng cung cấp mã xác minh OTP khôi phục mật khẩu.")

    otp_entry = await _match_otp(session, email=payload.email, code=target_otp, purpose="PASSWORD_RESET")
    otp_entry.is_used = True
    session.add(otp_entry)

    user_query = select(User).where(User.email == otp_entry.email)
    user_res = await session.execute(user_query)
    user = user_res.scalars().first()
    if not user:
        raise HTTPException(status_code=404, detail="Hồ sơ người dùng không tìm thấy.")

    user.hashed_password = hash_password(payload.newPassword)
    session.add(user)
    await session.commit()

    # Thu hồi toàn bộ phiên đăng nhập của người dùng khi đổi mật khẩu để bảo đảm tuyệt đối an ninh
    await revoke_session_token(session, user_id=user.id)

    return StandardMessageResponseDTO(
        success=True,
        message="🎉 Mật khẩu bảo mật của bạn đã được cập nhật hoàn tất! Các phiên kết nối cũ đã bị thu hồi. Bạn có thể đăng nhập bằng mật khẩu mới."
    )


# =====================================================================
# 4. HỒ SƠ ĐỊNH DANH & NGẮT PHIÊN (ME & LOGOUT)
# =====================================================================

@router.get("/me", response_model=UserProfileDTO)
async def get_current_user_profile(user: CurrentUserDep) -> UserProfileDTO:
    """Truy xuất thông tin Bác sĩ / Bệnh nhân hiện tại từ Bearer Token."""
    return _build_user_profile_dto(user)


@router.patch("/me/phone", response_model=UserProfileDTO)
async def update_own_phone_number(
    payload: UpdatePhoneNumberRequestDTO,
    user: CurrentUserDep,
    session: SessionDep,
) -> UserProfileDTO:
    """Cập nhật số điện thoại liên lạc của chính chủ tài khoản đang đăng nhập.

    Chủ thể bị tác động luôn là ``user`` giải mã từ Bearer Token; payload không mang
    user id nên client không thể sửa hồ sơ của người khác. Số điện thoại đã được
    Pydantic chuẩn hóa và kiểm định định dạng Việt Nam trước khi tới đây.
    """
    if user.is_guest:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Phiên khách khẩn cấp không lưu thông tin liên lạc cá nhân. Vui lòng đăng ký tài khoản.",
        )

    new_phone = payload.phoneNumber

    # Cột users.phone là UNIQUE: kiểm tra trước để trả lỗi nghiệp vụ tường minh
    # thay vì để asyncpg ném IntegrityError thô.
    if new_phone and new_phone != user.phone:
        duplicate = await session.execute(
            select(User).where(User.phone == new_phone, User.id != user.id)
        )
        if duplicate.scalars().first():
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Số điện thoại này đã được liên kết với một tài khoản khác.",
            )

    user.phone = new_phone
    user.updated_at = get_utc_now()
    session.add(user)
    await session.commit()
    await session.refresh(user)

    print(f"📞 [Auth Profile] Đã cập nhật số điện thoại liên lạc cho User [{pseudonym(user.id, prefix='user')}].")

    return _build_user_profile_dto(user)


@router.post("/logout", response_model=StandardMessageResponseDTO)
async def logout_clinical_session(
    response: Response,
    session: SessionDep,
    user: OptionalUserDep,
    ai20k_refresh_token: str | None = Cookie(default=None),
) -> StandardMessageResponseDTO:
    """Chấm dứt phiên làm việc, thu hồi Refresh Token tại CSDL và xóa trắng Cookie."""
    user_id = user.id if user else None
    await revoke_session_token(session, refresh_token=ai20k_refresh_token, user_id=user_id)
    _clear_auth_cookies(response)

    actor_label = pseudonym(user.id, prefix="user") if user else "Khách vãng lai"
    print(f"🔌 [Auth Logout] Đã tiếp nhận tín hiệu kết thúc và thu hồi phiên CSDL từ {actor_label}.")
    return StandardMessageResponseDTO(
        success=True,
        message="Bạn đã ngắt kết nối an toàn khỏi trạm AI Triage. (Token Session Revoked & Cookies Cleared)"
    )


# =====================================================================
# 5. OAUTH 2.0 FEDERATION (GOOGLE & GITHUB)
# =====================================================================

@router.get("/oauth/{provider}/url", response_model=OAuthUrlResponseDTO)
async def get_oauth_login_url(provider: str, request: Request) -> OAuthUrlResponseDTO:
    """Cung cấp đường liên kết truy nhập trạm OAuth 2.0 (Google hoặc GitHub)."""
    clean_provider = provider.lower().strip()
    # The callback must come back to the origin the patient is actually on.
    # Sending them to a different one logs them in somewhere they are not
    # looking, which is indistinguishable from the login having failed.
    origin = request.headers.get("origin")
    if clean_provider == "google":
        url = get_google_authorization_url(
            resolve_oauth_redirect_uri(origin, "google")
        )
        return OAuthUrlResponseDTO(url=url, provider="google")
    elif clean_provider == "github":
        url = get_github_authorization_url(
            resolve_oauth_redirect_uri(origin, "github")
        )
        return OAuthUrlResponseDTO(url=url, provider="github")
    else:
        raise HTTPException(status_code=400, detail=f"Cổng liên thông OAuth '{provider}' hiện chưa được bệnh viện hỗ trợ.")


@router.post("/oauth/{provider}/callback", response_model=AuthResponseDTO)
async def process_oauth_callback(provider: str, payload: OAuthCallbackRequestDTO, session: SessionDep, response: Response, request: Request) -> AuthResponseDTO:
    """Tiếp nhận mã Authorization Code, liên thông đổi dữ liệu hồ sơ và cấp phát thẻ quyền & Cookie."""
    clean_provider = provider.lower().strip()
    oauth_data: dict[str, str] = {}

    # Must be the *same* redirect_uri that was sent when the code was issued,
    # or the provider rejects the exchange. Derived from the origin again, and
    # the callback page runs on the origin the flow started from, so the two
    # agree by construction rather than by a value passed through the browser.
    origin = request.headers.get("origin")

    if clean_provider == "google":
        oauth_data = await authenticate_with_google(
            payload.code,
            resolve_oauth_redirect_uri(origin, "google"),
        )
    elif clean_provider == "github":
        oauth_data = await authenticate_with_github(
            payload.code,
            resolve_oauth_redirect_uri(origin, "github"),
        )
    else:
        raise HTTPException(status_code=400, detail="Nhà cung cấp OAuth không hợp lệ.")

    email = oauth_data.get("email")
    if not email:
        raise HTTPException(status_code=400, detail="Không thể chiết xuất địa chỉ Email từ thẻ quyền OAuth.")

    query = select(User).where(User.email == email)
    res = await session.execute(query)
    user = res.scalars().first()

    if user:
        user.oauth_provider = clean_provider
        user.oauth_id = oauth_data.get("oauth_id")
        user.is_active = True
        session.add(user)
    else:
        user = User(
            email=email,
            full_name=oauth_data.get("name", "Medical Specialist"),
            role="PATIENT",
            oauth_provider=clean_provider,
            oauth_id=oauth_data.get("oauth_id"),
            is_active=True,
        )
        session.add(user)
        await session.commit()
        await session.refresh(user)

        ehr_profile = EHRProfile(
            user_id=user.id,
            full_name=user.full_name,
            relationship_type="SELF",
            is_primary=True,
            avatar_color="emerald",
        )
        session.add(ehr_profile)

    await session.commit()
    await session.refresh(user)

    access_token, refresh_token = await create_session_tokens(session, user)
    _set_auth_cookies(response, access_token, refresh_token)
    user_dto = _build_user_profile_dto(user)
    if oauth_data.get("avatar"):
        user_dto.avatar = oauth_data.get("avatar")

    print(f"🌐 [OAuth Federation] Tài khoản {mask_email(user.email)} đã kết nối thành công qua cổng {clean_provider.upper()}. (Session & Cookies set)")
    return AuthResponseDTO(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="Bearer",
        expires_in=settings.access_token_expire_minutes * 60,
        user=user_dto,
    )
