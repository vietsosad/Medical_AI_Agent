"""Kiểm định lớp tìm cơ sở y tế gần người bệnh.

Chạy trên một CSDL SQLite thật dựng từ chính các model đang chạy, nên một lỗi
schema hay một giá trị mặc định thiếu an toàn sẽ hỏng ở đây chứ không phải trên
môi trường thật.

Trọng tâm của file này không phải là "hàm trả về đúng danh sách chưa", mà là ba
thứ dễ sai và nguy hiểm nếu sai:

1. **Khoảng cách và hộp bao.** Đảo nhầm vĩ độ với kinh độ, hay chia nhầm cho
   ``cos(lat)``, sẽ đẩy người bệnh đi sai hàng trăm ki-lô-mét mà giao diện vẫn
   trông bình thường.
2. **Mọi nhánh hỏng đều phải còn dữ liệu.** Provider ngoài sập, hết hạn mức,
   thiếu khoá -- không nhánh nào được biến thành lỗi hay danh sách rỗng giả
   trong khi danh bạ nội bộ vẫn còn dùng được.
3. **Không tự nâng cấp thông tin.** ``UNKNOWN`` phải ở nguyên là ``UNKNOWN``;
   không có đường nào biến "chưa xác minh" thành "có khoa cấp cứu".
"""

from __future__ import annotations

from typing import Any

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlmodel import SQLModel
from sqlmodel.ext.asyncio.session import AsyncSession

from src.config import get_settings
from src.models.db_models import MedicalFacility
from src.models.facility_schemas import NearbyFacilityRequest
from src.services.db import POSTGRES_ONLY_TABLES as POSTGRES_ONLY
from src.services.facility_directory import load_seed_facilities, sync_seed_into_database
from src.services.nearby_facilities import (
    FacilityCandidate,
    bounding_box,
    build_directions_url,
    find_nearby_facilities,
    haversine_meters,
    rank_candidates,
    reset_external_budget,
    reset_provider_cache,
)

# Bạch Mai và Chợ Rẫy: hai điểm cách nhau khoảng 1.140 km đường chim bay, dùng
# làm mốc đối chiếu cho haversine.
BACH_MAI = (21.0005, 105.8410)
CHO_RAY = (10.7570, 106.6590)


@pytest_asyncio.fixture
async def db_session(tmp_path):
    engine = create_async_engine(f"sqlite+aiosqlite:///{tmp_path / 'facilities.db'}")
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
    """Cache và bộ đếm hạn mức sống trong tiến trình -- không được rò giữa các test."""
    reset_provider_cache()
    reset_external_budget()
    get_settings.cache_clear()
    yield
    reset_provider_cache()
    reset_external_budget()
    get_settings.cache_clear()


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


def _candidate(name: str, latitude: float, longitude: float, **overrides: Any) -> FacilityCandidate:
    fields: dict[str, Any] = {
        "id": name,
        "name": name,
        "facility_type": "HOSPITAL",
        "address": "địa chỉ kiểm thử",
        "latitude": latitude,
        "longitude": longitude,
    }
    fields.update(overrides)
    return FacilityCandidate(**fields)


# ---------------------------------------------------------------------------
# Hình học
# ---------------------------------------------------------------------------

def test_haversine_matches_a_known_distance() -> None:
    distance_km = haversine_meters(*BACH_MAI, *CHO_RAY) / 1000
    assert 1130 < distance_km < 1155


def test_haversine_is_zero_for_the_same_point_and_symmetric() -> None:
    assert haversine_meters(*BACH_MAI, *BACH_MAI) == pytest.approx(0.0, abs=1e-6)
    assert haversine_meters(*BACH_MAI, *CHO_RAY) == pytest.approx(
        haversine_meters(*CHO_RAY, *BACH_MAI)
    )


def test_haversine_does_not_confuse_latitude_with_longitude() -> None:
    """Một độ vĩ tuyến luôn ~111km; một độ kinh tuyến co lại theo vĩ độ.

    Nếu hai tham số bị hoán vị ở đâu đó, hai con số này sẽ bằng nhau.
    """
    north = haversine_meters(21.0, 105.8, 22.0, 105.8)
    east = haversine_meters(21.0, 105.8, 21.0, 106.8)
    assert north == pytest.approx(111_195, rel=0.01)
    assert east < north


def test_bounding_box_encloses_the_requested_circle() -> None:
    latitude, longitude, radius = 21.0, 105.8, 10_000.0
    min_lat, max_lat, min_lon, max_lon = bounding_box(latitude, longitude, radius)

    # Điểm nằm đúng trên biên hình tròn theo bốn hướng đều phải nằm trong hộp.
    assert min_lat < latitude - radius / 111_320 + 1e-9
    assert max_lat > latitude + radius / 111_320 - 1e-9
    assert min_lon < longitude
    assert max_lon > longitude
    # Ở vĩ độ 21, hộp phải rộng hơn theo kinh độ so với theo vĩ độ.
    assert (max_lon - min_lon) > (max_lat - min_lat)


def test_bounding_box_opens_all_longitudes_near_the_pole() -> None:
    """Gần cực, cos(lat) tiến về 0 -- không được chia cho nó."""
    _, _, min_lon, max_lon = bounding_box(90.0, 105.8, 10_000.0)
    assert (min_lon, max_lon) == (-180.0, 180.0)


# ---------------------------------------------------------------------------
# Deep link
# ---------------------------------------------------------------------------

def test_directions_url_needs_no_api_key_and_keeps_the_coordinate_readable() -> None:
    url = build_directions_url(10.757, 106.659)
    assert url.startswith("https://www.google.com/maps/dir/?")
    assert "destination=10.757,106.659" in url
    assert "travelmode=driving" in url
    # Không được có mẩu khoá nào trong đường dẫn gửi xuống trình duyệt.
    assert "key=" not in url
    assert "api_key" not in url.lower()


def test_directions_url_prefers_a_place_id_when_known() -> None:
    url = build_directions_url(10.757, 106.659, "ChIJ_test_place")
    assert "destination_place_id=ChIJ_test_place" in url


# ---------------------------------------------------------------------------
# Xếp hạng
# ---------------------------------------------------------------------------

def test_rank_orders_by_distance_filters_radius_and_caps_the_list() -> None:
    ranked = rank_candidates(
        [
            _candidate("xa", 21.05, 105.8),      # ~5.5km
            _candidate("gan", 21.001, 105.8),    # ~0.1km
            _candidate("ngoai-ban-kinh", 22.0, 105.8),  # ~111km
            _candidate("trung-binh", 21.02, 105.8),     # ~2.2km
        ],
        latitude=21.0,
        longitude=105.8,
        radius_meters=10_000,
        limit=2,
    )

    assert [item.name for item in ranked] == ["gan", "trung-binh"]
    assert ranked[0].distance_meters < ranked[1].distance_meters


def test_rank_breaks_distance_ties_by_name_so_the_list_does_not_shuffle() -> None:
    first = rank_candidates(
        [_candidate("B", 21.01, 105.8), _candidate("A", 21.01, 105.8)],
        latitude=21.0,
        longitude=105.8,
        radius_meters=10_000,
        limit=5,
    )
    second = rank_candidates(
        [_candidate("A", 21.01, 105.8), _candidate("B", 21.01, 105.8)],
        latitude=21.0,
        longitude=105.8,
        radius_meters=10_000,
        limit=5,
    )
    assert [item.name for item in first] == [item.name for item in second] == ["A", "B"]


def test_rank_returns_empty_instead_of_reaching_for_something_far_away() -> None:
    """Không có cơ sở nào trong bán kính thì trả rỗng, không nới bán kính ngầm."""
    ranked = rank_candidates(
        [_candidate("rat-xa", 10.757, 106.659)],
        latitude=21.0,
        longitude=105.8,
        radius_meters=10_000,
        limit=5,
    )
    assert ranked == []


# ---------------------------------------------------------------------------
# DTO
# ---------------------------------------------------------------------------

@pytest.mark.parametrize(
    "latitude,longitude",
    [(91.0, 105.8), (-91.0, 105.8), (21.0, 181.0), (21.0, -181.0)],
)
def test_request_rejects_impossible_coordinates(latitude: float, longitude: float) -> None:
    with pytest.raises(ValueError):
        NearbyFacilityRequest(latitude=latitude, longitude=longitude)


def test_request_rejects_unknown_fields() -> None:
    """``extra="forbid"``: một trường lạ là dấu hiệu hợp đồng đã lệch, không phải thứ để bỏ qua."""
    with pytest.raises(ValueError):
        NearbyFacilityRequest(latitude=21.0, longitude=105.8, patient_name="Nguyễn Văn A")


# ---------------------------------------------------------------------------
# Seed
# ---------------------------------------------------------------------------

def test_seed_file_parses_and_never_invents_a_phone_number() -> None:
    seeds = load_seed_facilities()
    assert len(seeds) >= 10
    # Seed hiện tại cố ý để trống toàn bộ số điện thoại; nếu ai đó điền vào thì
    # phải là số đã gọi kiểm chứng, và test này buộc họ đọc lại ghi chú đó.
    assert all(seed.phone_number is None for seed in seeds)


def test_seed_marks_emergency_capability_only_with_an_explicit_value() -> None:
    seeds = load_seed_facilities()
    assert {seed.emergency_capability for seed in seeds} <= {"EMERGENCY_DEPARTMENT", "UNKNOWN"}
    # Phải có ít nhất một cơ sở còn ở trạng thái chưa xác minh -- nếu tất cả đều
    # được đánh dấu có khoa cấp cứu thì gần như chắc chắn ai đó đã đánh dấu bừa.
    assert any(seed.emergency_capability == "UNKNOWN" for seed in seeds)


@pytest.mark.asyncio
async def test_seed_sync_is_idempotent(db_session: AsyncSession) -> None:
    created, updated = await sync_seed_into_database(db_session)
    assert created > 0 and updated == 0

    created_again, updated_again = await sync_seed_into_database(db_session)
    assert created_again == 0 and updated_again == created


# ---------------------------------------------------------------------------
# Điều phối: danh bạ nội bộ
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_local_directory_serves_when_no_api_key_is_configured(
    db_session: AsyncSession, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("GOOGLE_MAPS_API_KEY", "")
    get_settings.cache_clear()

    db_session.add(_facility("gan", 21.001, 105.8, name="Gần"))
    db_session.add(_facility("xa", 21.05, 105.8, name="Xa"))
    await db_session.commit()

    result = await find_nearby_facilities(db_session, latitude=21.0, longitude=105.8)

    assert result.data_source == "local_directory"
    # Thiếu khoá API là cấu hình bình thường, không phải sự cố -- không gắn cờ.
    assert result.degraded is False
    assert [item.name for item in result.facilities] == ["Gần", "Xa"]
    assert result.disclaimer


@pytest.mark.asyncio
async def test_archived_facilities_never_reach_a_patient(db_session: AsyncSession) -> None:
    db_session.add(_facility("da-dong-cua", 21.001, 105.8, name="Đã đóng", status="ARCHIVED"))
    await db_session.commit()

    result = await find_nearby_facilities(db_session, latitude=21.0, longitude=105.8)
    assert result.facilities == []


@pytest.mark.asyncio
async def test_unverified_emergency_capability_is_not_upgraded(db_session: AsyncSession) -> None:
    db_session.add(_facility("chua-ro", 21.001, 105.8, name="Chưa rõ"))
    db_session.add(
        _facility("co-cap-cuu", 21.002, 105.8, name="Có cấp cứu", emergency_capability="EMERGENCY_DEPARTMENT")
    )
    # Một giá trị rác trong CSDL phải quy về UNKNOWN, không phải được tin.
    db_session.add(_facility("rac", 21.003, 105.8, name="Giá trị rác", emergency_capability="CO_LE_CO"))
    await db_session.commit()

    result = await find_nearby_facilities(db_session, latitude=21.0, longitude=105.8)
    by_name = {item.name: item.emergency_capability for item in result.facilities}

    assert by_name["Chưa rõ"] == "UNKNOWN"
    assert by_name["Có cấp cứu"] == "EMERGENCY_DEPARTMENT"
    assert by_name["Giá trị rác"] == "UNKNOWN"


@pytest.mark.asyncio
async def test_empty_directory_returns_an_empty_list_not_an_error(
    db_session: AsyncSession,
) -> None:
    result = await find_nearby_facilities(db_session, latitude=21.0, longitude=105.8)
    assert result.facilities == []
    assert result.data_source == "local_directory"
    # Danh sách rỗng vẫn phải mang theo lời nhắc, vì đó là lúc giao diện cần nó nhất.
    assert "115" in result.disclaimer


# ---------------------------------------------------------------------------
# Điều phối: provider ngoài
# ---------------------------------------------------------------------------

class _StubProvider:
    """Đứng thay GooglePlacesProvider, đếm số lần thực sự bị gọi ra ngoài."""

    def __init__(self, candidates: list[FacilityCandidate] | None = None, error: Exception | None = None) -> None:
        self._candidates = candidates or []
        self._error = error
        self.calls = 0

    def __call__(self, *_args: Any, **_kwargs: Any) -> _StubProvider:
        return self

    async def search(self, **_kwargs: Any) -> list[FacilityCandidate]:
        self.calls += 1
        if self._error is not None:
            raise self._error
        return self._candidates


def _install_google(monkeypatch: pytest.MonkeyPatch, stub: _StubProvider) -> None:
    monkeypatch.setenv("GOOGLE_MAPS_API_KEY", "test-key")
    get_settings.cache_clear()
    monkeypatch.setattr(
        "src.services.facility_providers.google_places.GooglePlacesProvider",
        stub,
    )


@pytest.mark.asyncio
async def test_google_results_are_served_when_the_provider_answers(
    db_session: AsyncSession, monkeypatch: pytest.MonkeyPatch
) -> None:
    stub = _StubProvider([_candidate("Bệnh viện từ Places", 21.001, 105.8)])
    _install_google(monkeypatch, stub)

    result = await find_nearby_facilities(db_session, latitude=21.0, longitude=105.8)

    assert result.data_source == "google_places"
    assert result.degraded is False
    assert [item.name for item in result.facilities] == ["Bệnh viện từ Places"]


@pytest.mark.asyncio
async def test_provider_outage_falls_back_to_the_local_directory(
    db_session: AsyncSession, monkeypatch: pytest.MonkeyPatch
) -> None:
    _install_google(monkeypatch, _StubProvider(error=TimeoutError("hết giờ")))
    db_session.add(_facility("du-phong", 21.001, 105.8, name="Dự phòng"))
    await db_session.commit()

    result = await find_nearby_facilities(db_session, latitude=21.0, longitude=105.8)

    # Sự cố hạ tầng không bao giờ được nổi lên thành lỗi cho người bệnh.
    assert result.data_source == "local_directory"
    assert result.degraded is True
    assert [item.name for item in result.facilities] == ["Dự phòng"]


@pytest.mark.asyncio
async def test_empty_provider_answer_still_tries_the_local_directory(
    db_session: AsyncSession, monkeypatch: pytest.MonkeyPatch
) -> None:
    _install_google(monkeypatch, _StubProvider([]))
    db_session.add(_facility("du-phong", 21.001, 105.8, name="Dự phòng"))
    await db_session.commit()

    result = await find_nearby_facilities(db_session, latitude=21.0, longitude=105.8)

    assert result.data_source == "local_directory"
    assert result.degraded is True
    assert len(result.facilities) == 1


@pytest.mark.asyncio
async def test_a_second_lookup_nearby_reuses_the_cached_provider_answer(
    db_session: AsyncSession, monkeypatch: pytest.MonkeyPatch
) -> None:
    stub = _StubProvider([_candidate("Từ cache", 21.001, 105.8)])
    _install_google(monkeypatch, stub)

    await find_nearby_facilities(db_session, latitude=21.0, longitude=105.8)
    # Lệch 10m -- cùng ô cache vì khoá làm tròn tới 3 chữ số thập phân (~110m).
    result = await find_nearby_facilities(db_session, latitude=21.00005, longitude=105.8)

    assert stub.calls == 1
    assert result.data_source == "google_places"


@pytest.mark.asyncio
async def test_a_lookup_far_away_does_not_reuse_the_cache(
    db_session: AsyncSession, monkeypatch: pytest.MonkeyPatch
) -> None:
    stub = _StubProvider([_candidate("Bất kỳ", 21.001, 105.8)])
    _install_google(monkeypatch, stub)

    await find_nearby_facilities(db_session, latitude=21.0, longitude=105.8)
    await find_nearby_facilities(db_session, latitude=10.757, longitude=106.659)

    assert stub.calls == 2


@pytest.mark.asyncio
async def test_exhausted_budget_degrades_instead_of_refusing(
    db_session: AsyncSession, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Hết hạn mức gọi API là chuyện chi phí, không phải chuyện quyền truy cập."""
    monkeypatch.setenv("FACILITY_LOOKUPS_PER_USER", "1")
    stub = _StubProvider([_candidate("Từ Places", 21.001, 105.8)])
    _install_google(monkeypatch, stub)

    db_session.add(_facility("du-phong", 21.002, 105.8, name="Dự phòng"))
    await db_session.commit()

    first = await find_nearby_facilities(
        db_session, latitude=21.0, longitude=105.8, user_key="nguoi-dung-1"
    )
    # Toạ độ khác hẳn để không rơi vào cache của lần trước.
    second = await find_nearby_facilities(
        db_session, latitude=21.002, longitude=105.802, user_key="nguoi-dung-1"
    )

    assert first.data_source == "google_places"
    assert second.data_source == "local_directory"
    assert second.degraded is True
    # Quan trọng nhất: vẫn còn dữ liệu để người bệnh dùng.
    assert len(second.facilities) == 1


@pytest.mark.asyncio
async def test_budget_is_counted_per_user(
    db_session: AsyncSession, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("FACILITY_LOOKUPS_PER_USER", "1")
    stub = _StubProvider([_candidate("Từ Places", 21.001, 105.8)])
    _install_google(monkeypatch, stub)

    await find_nearby_facilities(db_session, latitude=21.0, longitude=105.8, user_key="nguoi-dung-1")
    other = await find_nearby_facilities(
        db_session, latitude=21.002, longitude=105.802, user_key="nguoi-dung-2"
    )

    assert other.data_source == "google_places"


@pytest.mark.asyncio
async def test_local_mode_never_calls_the_paid_provider(
    db_session: AsyncSession, monkeypatch: pytest.MonkeyPatch
) -> None:
    stub = _StubProvider([_candidate("Không được gọi", 21.001, 105.8)])
    _install_google(monkeypatch, stub)
    monkeypatch.setenv("FACILITY_PROVIDER", "local")
    get_settings.cache_clear()

    result = await find_nearby_facilities(db_session, latitude=21.0, longitude=105.8)

    assert stub.calls == 0
    assert result.data_source == "local_directory"
    assert result.degraded is False
