"""Dịch vụ Giao tiếp Xác Thực Ngoại Vi OAuth 2.0 (Google & GitHub Async OAuth Engine).

Tuân thủ quy chuẩn kỹ thuật tại .agents/rules/backend-rules.md:
- An toàn Non-Blocking Loop: Truy cập giao dịch REST HTTP qua httpx.AsyncClient bất đồng bộ.
- Xử lý mượt mà trích xuất địa chỉ Email chính danh và Hồ sơ người dùng từ Google & GitHub.
"""

import urllib.parse
from typing import Any

import httpx
from fastapi import HTTPException

from src.config import get_settings

settings = get_settings()

# Path the frontend serves its OAuth callback page on, for every provider.
_CALLBACK_PATH_TEMPLATE = "/auth/callback/{provider}"


def _allowed_origins() -> set[str]:
    """Origins the frontend is permitted to be served from.

    Reuses the CORS allowlist rather than keeping a second list: the set of
    places this app may legitimately run from is one fact, and two copies of it
    drift apart exactly when it matters.
    """
    return {
        item.strip().rstrip("/")
        for item in settings.cors_origins.split(",")
        if item.strip()
    }


def resolve_oauth_redirect_uri(origin: str | None, provider: str) -> str:
    """The callback URL for the origin the patient is actually browsing.

    ``redirect_uri`` was a fixed setting pointing at ``localhost:3000``. A user
    on ``127.0.0.1:3000`` -- the same app, a different origin as far as every
    browser is concerned -- was sent to Google, authenticated, and returned to
    ``localhost:3000``. The login itself succeeded; the token landed in
    localStorage for an origin they were not looking at, so the tab they came
    from stayed logged out and the feature appeared broken.

    The origin is **validated against the allowlist**, never trusted. An
    attacker-supplied ``Origin`` header must not be able to steer Google into
    delivering an authorization code to a host of their choosing, so anything
    unrecognised falls back to the configured value rather than being honoured.
    """
    candidate = (origin or "").strip().rstrip("/")
    configured = (
        settings.google_redirect_uri
        if provider == "google"
        else settings.github_redirect_uri
    )
    if candidate and candidate in _allowed_origins():
        return f"{candidate}{_CALLBACK_PATH_TEMPLATE.format(provider=provider)}"
    return configured


# =====================================================================
# 1. GOOGLE OAUTH 2.0 ENGINE
# =====================================================================

def get_google_authorization_url(redirect_uri: str | None = None) -> str:
    """Tạo URL điều hướng người dùng tới Cổng đăng nhập hợp lệ của Google."""
    if not settings.google_client_id:
        raise HTTPException(
            status_code=500,
            detail="Cấu hình Google Client ID chưa được thiết lập trong biến môi trường (.env)."
        )

    params = {
        "client_id": settings.google_client_id,
        "redirect_uri": redirect_uri or settings.google_redirect_uri,
        "response_type": "code",
        "scope": "openid email profile",
        "access_type": "offline",
        "prompt": "select_account",
    }
    query_string = urllib.parse.urlencode(params)
    return f"https://accounts.google.com/o/oauth2/v2/auth?{query_string}"


async def authenticate_with_google(
    code: str,
    redirect_uri: str | None = None,
) -> dict[str, Any]:
    """Đổi Authorization Code lấy Access Token và trích xuất hồ sơ định danh từ Google."""
    if not settings.google_client_id or not settings.google_client_secret:
        raise HTTPException(status_code=500, detail="Thiếu cấu hình Secret cho cổng xác thực Google OAuth.")

    token_url = "https://oauth2.googleapis.com/token"
    token_payload = {
        "code": code,
        "client_id": settings.google_client_id,
        "client_secret": settings.google_client_secret,
        "redirect_uri": redirect_uri or settings.google_redirect_uri,
        "grant_type": "authorization_code",
    }

    async with httpx.AsyncClient(timeout=15.0) as client:
        # Bước 1: Tráo đổi mã Code lấy Thẻ Quyền Access Token
        token_res = await client.post(token_url, data=token_payload)
        if token_res.status_code != 200:
            console_msg = f"Lỗi đổi Token Google: {token_res.text}"
            print(f"❌ [OAuth Google] {console_msg}")
            raise HTTPException(status_code=401, detail="Mã xác nhận Google OAuth không hợp lệ hoặc đã hết thời gian thực thi.")

        token_data = token_res.json()
        access_token = token_data.get("access_token")

        # Bước 2: Gọi API truy xuất thông tin định danh Google User Info
        userinfo_url = "https://www.googleapis.com/oauth2/v2/userinfo"
        userinfo_res = await client.get(
            userinfo_url,
            headers={"Authorization": f"Bearer {access_token}"}
        )
        if userinfo_res.status_code != 200:
            raise HTTPException(status_code=401, detail="Không thể truy cứu thông tin hồ sơ y khoa từ Google Server.")

        profile = userinfo_res.json()
        # Chuẩn hóa cấu trúc trả về cho Backend Router
        return {
            "oauth_id": str(profile.get("id")),
            "email": profile.get("email"),
            "name": profile.get("name") or profile.get("email", "").split("@")[0],
            "avatar": profile.get("picture"),
            "provider": "google",
        }


# =====================================================================
# 2. GITHUB OAUTH 2.0 ENGINE
# =====================================================================

def get_github_authorization_url(redirect_uri: str | None = None) -> str:
    """Tạo URL điều hướng người dùng tới Cổng đăng nhập của GitHub."""
    if not settings.github_client_id:
        raise HTTPException(
            status_code=500,
            detail="Cấu hình GitHub Client ID chưa được tích hợp tại máy chủ."
        )

    params = {
        "client_id": settings.github_client_id,
        "redirect_uri": redirect_uri or settings.github_redirect_uri,
        "scope": "read:user user:email",
    }
    query_string = urllib.parse.urlencode(params)
    return f"https://github.com/login/oauth/authorize?{query_string}"


async def authenticate_with_github(
    code: str,
    redirect_uri: str | None = None,
) -> dict[str, Any]:
    """Đổi Code lấy Access Token và quét email định danh chính từ GitHub User Profile."""
    if not settings.github_client_id or not settings.github_client_secret:
        raise HTTPException(status_code=500, detail="Thiếu cấu hình Secret cho GitHub OAuth.")

    token_url = "https://github.com/login/oauth/access_token"
    token_payload = {
        "client_id": settings.github_client_id,
        "client_secret": settings.github_client_secret,
        "code": code,
        "redirect_uri": redirect_uri or settings.github_redirect_uri,
    }

    async with httpx.AsyncClient(timeout=15.0) as client:
        # Bước 1: Tráo đổi thẻ Token (yêu cầu trả về JSON)
        token_res = await client.post(
            token_url,
            data=token_payload,
            headers={"Accept": "application/json"}
        )
        if token_res.status_code != 200:
            raise HTTPException(status_code=401, detail="Mã ủy quyền GitHub OAuth bị từ chối.")

        token_data = token_res.json()
        access_token = token_data.get("access_token")
        if not access_token:
            print(f"❌ [OAuth GitHub Error] Phản hồi không chứa Token: {token_data}")
            raise HTTPException(status_code=401, detail="Không nhận được thẻ quyền hợp lệ từ dịch vụ GitHub.")

        # Bước 2: Truy xuất Thông tin cá nhân cơ bản
        user_res = await client.get(
            "https://api.github.com/user",
            headers={"Authorization": f"Bearer {access_token}", "Accept": "application/vnd.github.v3+json"}
        )
        if user_res.status_code != 200:
            raise HTTPException(status_code=401, detail="Không thể truy cập dữ liệu người dùng từ GitHub.")

        profile = user_res.json()
        primary_email = profile.get("email")

        # Bước 3: Nếu Email bị riêng tư (null), tiếp tục gọi sang endpoint danh sách email
        if not primary_email:
            emails_res = await client.get(
                "https://api.github.com/user/emails",
                headers={"Authorization": f"Bearer {access_token}", "Accept": "application/vnd.github.v3+json"}
            )
            if emails_res.status_code == 200:
                emails_list: list[dict[str, Any]] = emails_res.json()
                # Ưu tiên email chính và đã được xác thực
                for item in emails_list:
                    if item.get("primary") and item.get("verified"):
                        primary_email = item.get("email")
                        break
                if not primary_email and len(emails_list) > 0:
                    primary_email = emails_list[0].get("email")

        if not primary_email:
            raise HTTPException(
                status_code=400,
                detail="Tài khoản GitHub của bạn không công khai hoặc chưa có địa chỉ Email xác thực."
            )

        return {
            "oauth_id": str(profile.get("id")),
            "email": primary_email,
            "name": profile.get("name") or profile.get("login") or primary_email.split("@")[0],
            "avatar": profile.get("avatar_url"),
            "provider": "github",
        }
