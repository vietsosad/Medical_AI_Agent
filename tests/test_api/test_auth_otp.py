"""Hợp đồng HTTP của mã OTP: đăng ký và khôi phục mật khẩu.

Mã OTP là 6 chữ số, tức một triệu khả năng. Nó chỉ an toàn khi ba điều cùng
đúng, và mỗi test dưới đây chốt một điều:

- mã luôn được tra theo đúng email, không bao giờ dò trên mọi tài khoản;
- số lần đoán sai bị chặn, và chỉ mã mới nhất của một email còn sống;
- bước kiểm tra mã khôi phục không mở phiên đăng nhập -- chỉ đổi mật khẩu mới
  là việc tiêu thụ mã.
"""

from __future__ import annotations

from collections.abc import AsyncIterator

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlmodel import SQLModel, select
from sqlmodel.ext.asyncio.session import AsyncSession

import src.api.routes_auth as routes_auth
from src.main import app
from src.models.db_models import User
from src.services.db import POSTGRES_ONLY_TABLES, get_async_session
from src.services.security import hash_password

PASSWORD = "mat-khau-cu-123"
NEW_PASSWORD = "mat-khau-moi-456"


@pytest_asyncio.fixture
async def db_session(tmp_path) -> AsyncIterator[AsyncSession]:
    engine = create_async_engine(f"sqlite+aiosqlite:///{tmp_path / 'auth_otp.db'}")
    tables = [table for table in SQLModel.metadata.sorted_tables if table.name not in POSTGRES_ONLY_TABLES]
    async with engine.begin() as conn:
        await conn.run_sync(lambda sync_conn: SQLModel.metadata.create_all(sync_conn, tables=tables))
    maker = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with maker() as session:
        yield session
    await engine.dispose()


@pytest.fixture
def mailbox(monkeypatch: pytest.MonkeyPatch) -> dict[str, list[str]]:
    """Thay hộp thư thật: ghi lại mã đã gửi cho từng email."""
    sent: dict[str, list[str]] = {}

    async def fake_registration(email: str, _full_name: str, otp_code: str, valid_minutes: int = 15) -> bool:
        sent.setdefault(email, []).append(otp_code)
        return True

    async def fake_reset(email: str, otp_code: str, valid_minutes: int = 15) -> bool:
        sent.setdefault(email, []).append(otp_code)
        return True

    monkeypatch.setattr(routes_auth, "send_registration_otp", fake_registration)
    monkeypatch.setattr(routes_auth, "send_reset_password_otp", fake_reset)
    return sent


@pytest_asyncio.fixture
async def client(db_session: AsyncSession) -> AsyncIterator[AsyncClient]:
    async def _session_override() -> AsyncIterator[AsyncSession]:
        yield db_session

    app.dependency_overrides[get_async_session] = _session_override
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as http_client:
        yield http_client
    app.dependency_overrides.clear()


async def _active_user(session: AsyncSession, email: str) -> User:
    user = User(email=email, full_name="Điều dưỡng", role="CLINICAL_NURSE", hashed_password=hash_password(PASSWORD))
    user.is_active = True
    session.add(user)
    await session.commit()
    return user


async def _request_reset(client: AsyncClient, email: str) -> None:
    response = await client.post("/api/v1/auth/forgot-password", json={"email": email})
    assert response.status_code == 200


def _wrong(code: str) -> str:
    return f"{(int(code) + 1) % 1_000_000:06d}"


@pytest.mark.asyncio
async def test_a_code_is_never_accepted_without_its_email(client: AsyncClient, db_session, mailbox) -> None:
    await _active_user(db_session, "victim@test.local")
    await _request_reset(client, "victim@test.local")
    code = mailbox["victim@test.local"][-1]

    response = await client.post("/api/v1/auth/verify-otp", json={"code": code, "purpose": "PASSWORD_RESET"})

    assert response.status_code == 422


@pytest.mark.asyncio
async def test_a_valid_code_does_not_open_another_account(client: AsyncClient, db_session, mailbox) -> None:
    await _active_user(db_session, "victim@test.local")
    await _active_user(db_session, "attacker@test.local")
    await _request_reset(client, "attacker@test.local")
    attacker_code = mailbox["attacker@test.local"][-1]

    response = await client.post(
        "/api/v1/auth/reset-password",
        json={"email": "victim@test.local", "otp": attacker_code, "newPassword": NEW_PASSWORD},
    )

    assert response.status_code == 400


@pytest.mark.asyncio
async def test_wrong_guesses_burn_the_code(client: AsyncClient, db_session, mailbox) -> None:
    await _active_user(db_session, "victim@test.local")
    await _request_reset(client, "victim@test.local")
    code = mailbox["victim@test.local"][-1]

    for _ in range(routes_auth.MAX_OTP_ATTEMPTS):
        response = await client.post(
            "/api/v1/auth/verify-otp",
            json={"email": "victim@test.local", "code": _wrong(code), "purpose": "PASSWORD_RESET"},
        )
        assert response.status_code == 400

    # The right code no longer works once the guesses are used up.
    response = await client.post(
        "/api/v1/auth/verify-otp",
        json={"email": "victim@test.local", "code": code, "purpose": "PASSWORD_RESET"},
    )
    assert response.status_code == 400


@pytest.mark.asyncio
async def test_requesting_a_new_code_retires_the_previous_one(client: AsyncClient, db_session, mailbox) -> None:
    await _active_user(db_session, "victim@test.local")
    await _request_reset(client, "victim@test.local")
    await _request_reset(client, "victim@test.local")
    first, latest = mailbox["victim@test.local"]
    if first == latest:  # one-in-a-million collision would make the check meaningless
        pytest.skip("both generated codes are identical")

    stale = await client.post(
        "/api/v1/auth/verify-otp",
        json={"email": "victim@test.local", "code": first, "purpose": "PASSWORD_RESET"},
    )
    current = await client.post(
        "/api/v1/auth/verify-otp",
        json={"email": "victim@test.local", "code": latest, "purpose": "PASSWORD_RESET"},
    )

    assert stale.status_code == 400
    assert current.status_code == 200


@pytest.mark.asyncio
async def test_password_reset_checks_the_code_then_changes_the_password(
    client: AsyncClient, db_session, mailbox
) -> None:
    await _active_user(db_session, "nurse@test.local")
    await _request_reset(client, "nurse@test.local")
    code = mailbox["nurse@test.local"][-1]

    check = await client.post(
        "/api/v1/auth/verify-otp",
        json={"email": "nurse@test.local", "code": code, "purpose": "PASSWORD_RESET"},
    )
    # Checking a reset code must not log anyone in.
    assert check.status_code == 200
    assert "access_token" not in check.json()
    assert "access_token" not in check.cookies

    reset = await client.post(
        "/api/v1/auth/reset-password",
        json={"email": "nurse@test.local", "otp": code, "newPassword": NEW_PASSWORD},
    )
    assert reset.status_code == 200

    login = await client.post("/api/v1/auth/login", json={"email": "nurse@test.local", "password": NEW_PASSWORD})
    assert login.status_code == 200

    # A used code cannot reset the password a second time.
    replay = await client.post(
        "/api/v1/auth/reset-password",
        json={"email": "nurse@test.local", "otp": code, "newPassword": "lan-thu-hai-789"},
    )
    assert replay.status_code == 400


@pytest.mark.asyncio
async def test_registration_code_activates_the_account_and_signs_in(
    client: AsyncClient, db_session, mailbox
) -> None:
    registered = await client.post(
        "/api/v1/auth/register",
        json={"name": "Người bệnh", "email": "Patient@Test.local", "password": PASSWORD},
    )
    assert registered.status_code == 201
    code = mailbox["patient@test.local"][-1]

    response = await client.post(
        "/api/v1/auth/verify-otp",
        json={"email": " patient@test.local ", "code": code, "purpose": "REGISTRATION"},
    )

    assert response.status_code == 200
    assert response.json()["access_token"]
    user = (await db_session.exec(select(User).where(User.email == "patient@test.local"))).first()
    assert user is not None and user.is_active


@pytest.mark.asyncio
async def test_resending_a_registration_code_retires_the_previous_one(
    client: AsyncClient, db_session, mailbox
) -> None:
    await client.post(
        "/api/v1/auth/register",
        json={"name": "Người bệnh", "email": "new@test.local", "password": PASSWORD},
    )
    resent = await client.post("/api/v1/auth/resend-registration-otp", json={"email": "New@Test.local"})
    assert resent.status_code == 200
    first, latest = mailbox["new@test.local"]
    if first == latest:  # one-in-a-million collision would make the check meaningless
        pytest.skip("both generated codes are identical")

    stale = await client.post(
        "/api/v1/auth/verify-otp",
        json={"email": "new@test.local", "code": first, "purpose": "REGISTRATION"},
    )
    current = await client.post(
        "/api/v1/auth/verify-otp",
        json={"email": "new@test.local", "code": latest, "purpose": "REGISTRATION"},
    )

    assert stale.status_code == 400
    assert current.status_code == 200


@pytest.mark.asyncio
async def test_resend_reveals_nothing_about_other_emails(client: AsyncClient, db_session, mailbox) -> None:
    await _active_user(db_session, "active@test.local")

    unknown = await client.post("/api/v1/auth/resend-registration-otp", json={"email": "nobody@test.local"})
    active = await client.post("/api/v1/auth/resend-registration-otp", json={"email": "active@test.local"})

    assert unknown.status_code == active.status_code == 200
    assert unknown.json()["message"] == active.json()["message"]
    assert mailbox == {}
