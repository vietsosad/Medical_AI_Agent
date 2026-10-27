"""Ranh giới của thẻ quyền JWT: loại thẻ và khoá ký.

- Refresh token sống 7 ngày và chỉ được dùng để xin cặp thẻ mới; cổng API và
  WebSocket chỉ nhận access token.
- Ở production, tiến trình phải từ chối khởi động với một khoá ký đã công khai
  trong repo, vì ai đọc được khoá đó đều ký được thẻ cho mọi tài khoản.
"""

from __future__ import annotations

from collections.abc import AsyncIterator

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from pydantic import ValidationError
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlmodel import SQLModel
from sqlmodel.ext.asyncio.session import AsyncSession

from src.config import DEFAULT_JWT_SECRET_KEY, Settings
from src.main import app
from src.models.db_models import User
from src.services.db import POSTGRES_ONLY_TABLES, get_async_session
from src.services.security import create_access_token, create_refresh_token, decode_access_token


@pytest_asyncio.fixture
async def db_session(tmp_path) -> AsyncIterator[AsyncSession]:
    engine = create_async_engine(f"sqlite+aiosqlite:///{tmp_path / 'auth_tokens.db'}")
    tables = [table for table in SQLModel.metadata.sorted_tables if table.name not in POSTGRES_ONLY_TABLES]
    async with engine.begin() as conn:
        await conn.run_sync(lambda sync_conn: SQLModel.metadata.create_all(sync_conn, tables=tables))
    maker = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with maker() as session:
        yield session
    await engine.dispose()


@pytest_asyncio.fixture
async def client(db_session: AsyncSession) -> AsyncIterator[AsyncClient]:
    async def _session_override() -> AsyncIterator[AsyncSession]:
        yield db_session

    app.dependency_overrides[get_async_session] = _session_override
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as http_client:
        yield http_client
    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_a_refresh_token_is_not_accepted_as_an_access_token(client: AsyncClient, db_session) -> None:
    user = User(email="nurse@test.local", full_name="Điều dưỡng", role="CLINICAL_NURSE")
    user.is_active = True
    db_session.add(user)
    await db_session.commit()

    as_refresh = await client.get(
        "/api/v1/auth/me", headers={"Authorization": f"Bearer {create_refresh_token(user.id)}"}
    )
    as_access = await client.get(
        "/api/v1/auth/me", headers={"Authorization": f"Bearer {create_access_token(user.id)}"}
    )

    assert as_refresh.status_code == 401
    assert as_access.status_code == 200


def test_the_socket_and_api_decoder_rejects_refresh_tokens() -> None:
    assert decode_access_token(create_refresh_token("user-1")) is None
    assert decode_access_token(create_access_token("user-1"))["sub"] == "user-1"


@pytest.mark.parametrize(
    "secret",
    [DEFAULT_JWT_SECRET_KEY, "your-production-jwt-secret", "doi-thanh-mot-chuoi-ngau-nhien-that-dai", "short"],
)
def test_production_refuses_a_published_or_short_jwt_secret(secret: str) -> None:
    with pytest.raises(ValidationError):
        Settings(_env_file=None, app_env="production", jwt_secret_key=secret)


def test_production_starts_with_a_private_secret_and_development_keeps_its_default() -> None:
    assert Settings(_env_file=None, app_env="production", jwt_secret_key="x" * 64).app_env == "production"
    assert Settings(_env_file=None, app_env="development").jwt_secret_key == DEFAULT_JWT_SECRET_KEY
