"""Hợp đồng HTTP của endpoint tra cứu cơ sở y tế.

Điều được canh chừng gắt nhất ở đây là **endpoint không bao giờ được biến một
sự cố hạ tầng thành một lỗi chắn ngang người bệnh**. Người mở màn hình này ra
thường đang ở mức ESI 1/2/3; một phản hồi 5xx hay 429 lúc đó là một đường thoát
bị đóng lại, chứ không phải một dòng đỏ trong log.

Các test ở đây cũng chốt hai ranh giới còn lại: toạ độ đi trong thân request
(không nằm trong URL), và danh tính đến từ Bearer Token (không nằm trong
payload).
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Any

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlmodel import SQLModel
from sqlmodel.ext.asyncio.session import AsyncSession

from src.api.dependencies import get_current_patient
from src.config import get_settings
from src.main import app
from src.models.db_models import MedicalFacility, User
from src.services.db import POSTGRES_ONLY_TABLES as POSTGRES_ONLY
from src.services.db import get_async_session
from src.services.nearby_facilities import (
    FacilityCandidate,
    reset_external_budget,
    reset_provider_cache,
)

ENDPOINT = "/api/v1/facilities/nearby"
HANOI = {"latitude": 21.0, "longitude": 105.8}


@pytest_asyncio.fixture
async def db_session(tmp_path) -> AsyncIterator[AsyncSession]:
    engine = create_async_engine(f"sqlite+aiosqlite:///{tmp_path / 'facilities_api.db'}")
    tables = [
        table for table in SQLModel.metadata.sorted_tables if table.name not in POSTGRES_ONLY
    ]
    async with engine.begin() as conn:
        await conn.run_sync(lambda sync_conn: SQLModel.metadata.create_all(sync_conn, tables=tables))
    maker = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with maker() as session:
        yield session
    await engine.dispose()


@pytest.fixture(autouse=True)
def clean_process_state():
    reset_provider_cache()
    reset_external_budget()
    get_settings.cache_clear()
    yield
    reset_provider_cache()
    reset_external_budget()
    get_settings.cache_clear()
    app.dependency_overrides.clear()


def _bind_session(session: AsyncSession) -> None:
    async def _session_override() -> AsyncIterator[AsyncSession]:
        yield session

    app.dependency_overrides[get_async_session] = _session_override


def _bind_patient(session: AsyncSession) -> None:
    async def _patient_override() -> User:
        return User(id="patient-1", email="patient@test.local", full_name="Bệnh nhân", role="PATIENT")

    _bind_session(session)
    app.dependency_overrides[get_current_patient] = _patient_override


@pytest_asyncio.fixture
async def client() -> AsyncIterator[AsyncClient]:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as http_client:
        yield http_client


def _facility(slug: str, latitude: float, longitude: float, **overrides: Any) -> MedicalFacility:
    fields: dict[str, Any] = {
        "slug": slug,
        "name": overrides.pop("name", slug),
        "facility_type": "HOSPITAL",
        "address": "địa chỉ kiểm thử",
        "province": "Hà Nội",
        "latitude": latitude,
        "longitude": longitude,
        "source": "Kiểm thử",
        "source_url": "https://example.test",
    }
    fields.update(overrides)
    return MedicalFacility(**fields)


# ---------------------------------------------------------------------------
# Xác thực
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_anonymous_callers_are_rejected(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    _bind_session(db_session)
    response = await client.post(ENDPOINT, json=HANOI)
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_identity_comes_from_the_token_not_the_payload() -> None:
    """Payload chỉ chứa vị trí. Không có trường nào để client tự khai mình là ai."""
    from src.models.facility_schemas import NearbyFacilityRequest

    assert set(NearbyFacilityRequest.model_fields) == {
        "latitude",
        "longitude",
        "radius_meters",
        "accuracy_meters",
    }


# ---------------------------------------------------------------------------
# Hợp đồng dữ liệu
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_returns_facilities_sorted_by_distance(
    client: AsyncClient, db_session: AsyncSession, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("GOOGLE_MAPS_API_KEY", "")
    get_settings.cache_clear()
    db_session.add(_facility("xa", 21.05, 105.8, name="Xa"))
    db_session.add(_facility("gan", 21.001, 105.8, name="Gần"))
    await db_session.commit()
    _bind_patient(db_session)

    response = await client.post(ENDPOINT, json=HANOI)

    assert response.status_code == 200
    body = response.json()
    assert [item["name"] for item in body["facilities"]] == ["Gần", "Xa"]
    assert body["data_source"] == "local_directory"
    assert body["degraded"] is False
    assert body["disclaimer"]
    # Mỗi mục phải tự mang theo đường chỉ đường dùng được ngay, không cần khoá.
    first = body["facilities"][0]
    assert first["directions_url"].startswith("https://www.google.com/maps/dir/?")
    assert "key=" not in first["directions_url"]
    assert first["id"]


@pytest.mark.asyncio
async def test_unverified_phone_number_is_null_not_a_placeholder(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    db_session.add(_facility("chua-co-so", 21.001, 105.8, name="Chưa có số"))
    await db_session.commit()
    _bind_patient(db_session)

    body = (await client.post(ENDPOINT, json=HANOI)).json()
    assert body["facilities"][0]["phone_number"] is None


@pytest.mark.asyncio
async def test_empty_result_is_a_200_with_an_empty_list(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    _bind_patient(db_session)
    response = await client.post(ENDPOINT, json=HANOI)

    assert response.status_code == 200
    assert response.json()["facilities"] == []


# ---------------------------------------------------------------------------
# Kiểm định đầu vào
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
@pytest.mark.parametrize(
    "payload",
    [
        {"latitude": 91.0, "longitude": 105.8},
        {"latitude": 21.0, "longitude": 181.0},
        {"latitude": "không phải số", "longitude": 105.8},
        {"latitude": 21.0},
        {"latitude": 21.0, "longitude": 105.8, "radius_meters": 1},
        {"latitude": 21.0, "longitude": 105.8, "radius_meters": 999_999},
        {"latitude": 21.0, "longitude": 105.8, "ho_ten": "Nguyễn Văn A"},
    ],
)
async def test_malformed_payloads_are_refused(
    client: AsyncClient, db_session: AsyncSession, payload: dict[str, Any]
) -> None:
    _bind_patient(db_session)
    response = await client.post(ENDPOINT, json=payload)
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_coordinates_are_not_accepted_from_the_query_string(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    """Chỉ có POST. Một biến thể GET sẽ đẩy toạ độ vào access log và lịch sử trình duyệt."""
    _bind_patient(db_session)
    response = await client.get(f"{ENDPOINT}?latitude=21.0&longitude=105.8")
    assert response.status_code == 405


# ---------------------------------------------------------------------------
# Suy biến an toàn
# ---------------------------------------------------------------------------

class _BrokenProvider:
    def __call__(self, *_args: Any, **_kwargs: Any) -> _BrokenProvider:
        return self

    async def search(self, **_kwargs: Any) -> list[FacilityCandidate]:
        raise RuntimeError("Places trả 500")


@pytest.mark.asyncio
async def test_provider_outage_is_not_visible_as_an_http_error(
    client: AsyncClient, db_session: AsyncSession, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("GOOGLE_MAPS_API_KEY", "test-key")
    get_settings.cache_clear()
    monkeypatch.setattr(
        "src.services.facility_providers.google_places.GooglePlacesProvider",
        _BrokenProvider(),
    )
    db_session.add(_facility("du-phong", 21.001, 105.8, name="Dự phòng"))
    await db_session.commit()
    _bind_patient(db_session)

    response = await client.post(ENDPOINT, json=HANOI)

    assert response.status_code == 200
    body = response.json()
    assert body["degraded"] is True
    assert body["data_source"] == "local_directory"
    assert [item["name"] for item in body["facilities"]] == ["Dự phòng"]


@pytest.mark.asyncio
async def test_repeated_lookups_are_never_answered_with_429(
    client: AsyncClient, db_session: AsyncSession, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Hạn mức chỉ chặn lời gọi ra dịch vụ tính tiền, không chặn người bệnh."""
    monkeypatch.setenv("GOOGLE_MAPS_API_KEY", "test-key")
    monkeypatch.setenv("FACILITY_LOOKUPS_PER_USER", "1")
    get_settings.cache_clear()
    monkeypatch.setattr(
        "src.services.facility_providers.google_places.GooglePlacesProvider",
        _BrokenProvider(),
    )
    db_session.add(_facility("du-phong", 21.001, 105.8, name="Dự phòng"))
    await db_session.commit()
    _bind_patient(db_session)

    for offset in range(5):
        response = await client.post(
            ENDPOINT,
            json={"latitude": 21.0 + offset / 100, "longitude": 105.8},
        )
        assert response.status_code == 200
