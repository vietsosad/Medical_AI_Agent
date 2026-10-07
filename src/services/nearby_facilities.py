"""Tìm cơ sở y tế gần vị trí người bệnh.

Lớp này thuần tuý là **tra cứu dữ liệu địa điểm**. Nó không đọc, không ghi và
không suy diễn bất cứ thứ gì thuộc về trạng thái lâm sàng: không chạm vào
``triage_cases``, không chạm vào nhóm bảng ``simple_agent_*``, không tham gia
vào việc quyết định mức ESI. Việc "người bệnh này có nên thấy danh sách cơ sở y
tế hay không" là quyết định của tầng hiển thị, dựa trên mức ESI mà backend đã
chốt từ trước -- xem @[frontend/src/components/chat/NearbyFacilitiesCard.tsx].

Nguyên tắc chi phối toàn bộ file này: **tính năng chỉ được cộng thêm, không bao
giờ được trừ đi.** Một người đang trong tình huống khẩn cấp mở màn hình này ra
thì mọi nhánh -- thiếu khoá API, Google sập, quá hạn mức, dữ liệu rỗng -- đều
phải trả về một câu trả lời dùng được, không bao giờ là một lỗi chắn ngang. Do
đó:

- Provider ngoài hỏng  -> rơi về danh bạ nội bộ, gắn cờ ``degraded``.
- Vượt hạn mức gọi API -> rơi về danh bạ nội bộ, KHÔNG trả 429.
- Danh bạ nội bộ rỗng  -> trả danh sách rỗng kèm ``disclaimer``, để giao diện
  hiện lối đi khác (gọi 115, tự tìm trên Google Maps), chứ không phải một màn
  hình lỗi.
"""

from __future__ import annotations

import logging
import math
import time
from collections import deque
from dataclasses import dataclass
from typing import Protocol
from urllib.parse import urlencode

from sqlalchemy.ext.asyncio import AsyncSession

from src.config import get_settings
from src.models.facility_schemas import (
    EmergencyCapability,
    FacilityDataSource,
    NearbyFacilitiesResponse,
    NearbyFacilityDTO,
)

logger = logging.getLogger(__name__)

#: Bán kính Trái Đất trung bình (mét), giá trị thường dùng cho công thức haversine.
EARTH_RADIUS_METERS = 6_371_000.0

#: Một độ vĩ tuyến xấp xỉ 111.32 km ở mọi vĩ độ. Dùng để dựng hộp bao trước khi
#: tính haversine, giúp truy vấn không phải quét toàn bảng.
METERS_PER_DEGREE_LATITUDE = 111_320.0


def haversine_meters(
    latitude_a: float,
    longitude_a: float,
    latitude_b: float,
    longitude_b: float,
) -> float:
    """Khoảng cách đường chim bay giữa hai điểm, tính bằng mét.

    Đây KHÔNG phải quãng đường đi thực tế. Mọi chỗ hiển thị con số này ra cho
    người dùng đều phải nói rõ điều đó: ở đô thị, quãng đường đi có thể dài gấp
    rưỡi đường chim bay, và một người đang cấp cứu không nên tự ước lượng thời
    gian tới nơi dựa trên nó.
    """
    lat_a = math.radians(latitude_a)
    lat_b = math.radians(latitude_b)
    delta_lat = lat_b - lat_a
    delta_lon = math.radians(longitude_b - longitude_a)

    inner = (
        math.sin(delta_lat / 2) ** 2
        + math.cos(lat_a) * math.cos(lat_b) * math.sin(delta_lon / 2) ** 2
    )
    return 2 * EARTH_RADIUS_METERS * math.asin(min(1.0, math.sqrt(inner)))


def bounding_box(
    latitude: float,
    longitude: float,
    radius_meters: float,
) -> tuple[float, float, float, float]:
    """Hộp bao ``(min_lat, max_lat, min_lon, max_lon)`` chứa trọn hình tròn bán kính đã cho.

    Hộp bao luôn rộng hơn hình tròn, nên nó chỉ dùng để loại bớt ứng viên ở tầng
    SQL; phép lọc đúng vẫn là haversine ở tầng Python. Gần hai cực, ``cos(lat)``
    tiến về 0 và độ kinh tuyến co lại vô hạn -- khi đó hộp bao được mở ra toàn bộ
    dải kinh độ thay vì chia cho một số gần 0.
    """
    delta_lat = radius_meters / METERS_PER_DEGREE_LATITUDE
    cos_lat = math.cos(math.radians(latitude))
    if abs(cos_lat) < 1e-6:
        min_lon, max_lon = -180.0, 180.0
    else:
        delta_lon = radius_meters / (METERS_PER_DEGREE_LATITUDE * abs(cos_lat))
        min_lon = max(-180.0, longitude - delta_lon)
        max_lon = min(180.0, longitude + delta_lon)
    return (
        max(-90.0, latitude - delta_lat),
        min(90.0, latitude + delta_lat),
        min_lon,
        max_lon,
    )


def build_directions_url(
    latitude: float,
    longitude: float,
    place_id: str | None = None,
) -> str:
    """Deep link chỉ đường của Google Maps.

    Dùng Google Maps URLs (``/maps/dir/?api=1``): đây là địa chỉ web công khai,
    **không cần API key**, nên không có mẩu khoá nào phải đi xuống trình duyệt.
    Trên điện thoại, đường dẫn này mở thẳng ứng dụng Google Maps.

    ``place_id`` giúp Maps trỏ đúng địa điểm thay vì một toạ độ trần; khi không
    có, toạ độ vẫn là điểm đến hợp lệ.
    """
    params: dict[str, str] = {
        "api": "1",
        "destination": f"{latitude},{longitude}",
        "travelmode": "driving",
    }
    if place_id:
        params["destination_place_id"] = place_id
    # ``safe=","`` giữ dấu phẩy giữa vĩ độ và kinh độ ở dạng nguyên bản,
    # đúng như ví dụ trong tài liệu Google Maps URLs. Dạng mã hoá %2C cũng
    # hợp lệ trên web, nhưng bộ lọc intent của ứng dụng Maps trên di động
    # nhận dạng dạng nguyên bản chắc chắn hơn.
    return f"https://www.google.com/maps/dir/?{urlencode(params, safe=',')}"


@dataclass(frozen=True)
class FacilityCandidate:
    """Một cơ sở y tế đã chuẩn hoá, chưa gắn khoảng cách.

    Kiểu trung gian giữa provider và DTO: mỗi provider chỉ cần dịch định dạng
    riêng của nó về đây, còn việc tính khoảng cách, sắp xếp, cắt danh sách và
    dựng deep link được làm đúng một lần ở hàm điều phối bên dưới.
    """

    id: str
    name: str
    facility_type: str
    address: str
    latitude: float
    longitude: float
    phone_number: str | None = None
    emergency_capability: EmergencyCapability = "UNKNOWN"
    google_place_id: str | None = None
    source: str | None = None
    source_url: str | None = None


class FacilityProvider(Protocol):
    """Hợp đồng cho một nguồn dữ liệu cơ sở y tế.

    Provider chỉ có một việc: trả về ứng viên trong bán kính. Nó không sắp xếp,
    không tự cắt danh sách theo ý mình và **không được nuốt lỗi**: hỏng thì ném
    ngoại lệ để hàm điều phối quyết định rơi về nguồn nào, thay vì lặng lẽ trả
    danh sách rỗng khiến một sự cố hạ tầng trông giống như "quanh đây không có
    cơ sở y tế nào".
    """

    source: FacilityDataSource

    async def search(
        self,
        *,
        latitude: float,
        longitude: float,
        radius_meters: int,
        limit: int,
    ) -> list[FacilityCandidate]:
        ...


# ---------------------------------------------------------------------------
# Hạn mức gọi provider trả phí, theo từng tài khoản
# ---------------------------------------------------------------------------
# Cố ý KHÔNG phải là rate limit của endpoint. Vượt hạn mức chỉ có nghĩa là lần
# tra cứu này không được gọi ra dịch vụ tính tiền nữa; người bệnh vẫn nhận được
# danh bạ nội bộ. Không có đường nào từ đây dẫn tới một phản hồi 429.
_external_call_log: dict[str, deque[float]] = {}


def _external_budget_available(user_key: str | None) -> bool:
    """True khi tài khoản này còn suất gọi provider trả phí trong cửa sổ hiện tại."""
    if not user_key:
        return True
    settings = get_settings()
    window = float(settings.facility_rate_limit_window_seconds)
    budget = int(settings.facility_lookups_per_user)
    now = time.monotonic()

    calls = _external_call_log.setdefault(user_key, deque())
    while calls and now - calls[0] > window:
        calls.popleft()
    if len(calls) >= budget:
        return False
    calls.append(now)
    return True


def reset_external_budget() -> None:
    """Xoá sổ hạn mức. Chỉ dùng cho kiểm thử."""
    _external_call_log.clear()


# ---------------------------------------------------------------------------
# Cache ngắn hạn cho provider ngoài
# ---------------------------------------------------------------------------
# Chỉ cache provider trả phí. Danh bạ nội bộ là một truy vấn DB rẻ; cache nó chỉ
# đổi lấy dữ liệu cũ mà không tiết kiệm được gì.
#
# Khoá cache làm tròn toạ độ tới 3 chữ số thập phân (~110m): đủ để hai lần bấm
# liên tiếp của cùng một người dùng chung một kết quả, và cũng có nghĩa là bản
# thân cache không giữ vị trí chính xác của ai. TTL tính bằng phút, nằm rất xa
# trần 30 ngày mà điều khoản Google Maps Platform cho phép lưu nội dung Places.
_CACHE_COORDINATE_PRECISION = 3

_CacheKey = tuple[str, float, float, int, int]
_provider_cache: dict[_CacheKey, tuple[float, list[FacilityCandidate]]] = {}


def _cache_key(
    source: str,
    latitude: float,
    longitude: float,
    radius_meters: int,
    limit: int,
) -> _CacheKey:
    return (
        source,
        round(latitude, _CACHE_COORDINATE_PRECISION),
        round(longitude, _CACHE_COORDINATE_PRECISION),
        radius_meters,
        limit,
    )


def _cache_get(key: _CacheKey) -> list[FacilityCandidate] | None:
    entry = _provider_cache.get(key)
    if entry is None:
        return None
    expires_at, candidates = entry
    if time.monotonic() >= expires_at:
        _provider_cache.pop(key, None)
        return None
    return candidates


def _cache_put(key: _CacheKey, candidates: list[FacilityCandidate]) -> None:
    ttl = int(get_settings().facility_cache_ttl_seconds)
    if ttl <= 0:
        return
    _provider_cache[key] = (time.monotonic() + ttl, candidates)


def reset_provider_cache() -> None:
    """Xoá cache. Chỉ dùng cho kiểm thử."""
    _provider_cache.clear()


# ---------------------------------------------------------------------------
# Điều phối
# ---------------------------------------------------------------------------
def _to_dto(candidate: FacilityCandidate, distance_meters: float) -> NearbyFacilityDTO:
    return NearbyFacilityDTO(
        id=candidate.id,
        name=candidate.name,
        facility_type=candidate.facility_type,
        address=candidate.address,
        latitude=candidate.latitude,
        longitude=candidate.longitude,
        distance_meters=int(round(distance_meters)),
        phone_number=candidate.phone_number,
        emergency_capability=candidate.emergency_capability,
        directions_url=build_directions_url(
            candidate.latitude,
            candidate.longitude,
            candidate.google_place_id,
        ),
        source=candidate.source,
        source_url=candidate.source_url,
    )


def rank_candidates(
    candidates: list[FacilityCandidate],
    *,
    latitude: float,
    longitude: float,
    radius_meters: int,
    limit: int,
) -> list[NearbyFacilityDTO]:
    """Lọc theo bán kính, sắp xếp theo khoảng cách tăng dần, cắt còn ``limit`` mục.

    Đây là nơi duy nhất quyết định thứ tự danh sách, nên mọi provider đều cho ra
    cùng một cách sắp xếp -- người bệnh không gặp hai thứ tự khác nhau chỉ vì
    hôm nay hệ thống rơi sang nguồn dự phòng.
    """
    scored: list[tuple[float, FacilityCandidate]] = []
    for candidate in candidates:
        distance = haversine_meters(latitude, longitude, candidate.latitude, candidate.longitude)
        if distance <= radius_meters:
            scored.append((distance, candidate))

    # Khoá phụ là tên cơ sở: hai cơ sở cách đều nhau vẫn phải ra cùng một thứ tự
    # giữa các lần gọi, nếu không danh sách sẽ nhảy chỗ mỗi lần giao diện tải lại.
    scored.sort(key=lambda item: (item[0], item[1].name))
    return [_to_dto(candidate, distance) for distance, candidate in scored[:limit]]


def _response(
    candidates: list[FacilityCandidate],
    *,
    latitude: float,
    longitude: float,
    radius_meters: int,
    limit: int,
    data_source: FacilityDataSource,
    degraded: bool,
    accuracy_meters: float | None,
) -> NearbyFacilitiesResponse:
    return NearbyFacilitiesResponse(
        facilities=rank_candidates(
            candidates,
            latitude=latitude,
            longitude=longitude,
            radius_meters=radius_meters,
            limit=limit,
        ),
        data_source=data_source,
        degraded=degraded,
        search_radius_meters=radius_meters,
        accuracy_meters=accuracy_meters,
    )


async def find_nearby_facilities(
    session: AsyncSession,
    *,
    latitude: float,
    longitude: float,
    radius_meters: int | None = None,
    accuracy_meters: float | None = None,
    user_key: str | None = None,
) -> NearbyFacilitiesResponse:
    """Danh sách cơ sở y tế gần một toạ độ, đã sắp xếp theo khoảng cách.

    ``user_key`` là định danh đã giả danh hoá của người gọi, chỉ dùng cho hạn
    mức gọi provider trả phí; truyền ``None`` thì không áp hạn mức.

    Hàm này không ném ngoại lệ vì lý do hạ tầng: sự cố của provider ngoài được
    nuốt lại thành cờ ``degraded`` trên phản hồi.
    """
    # Import cục bộ: giữ cho module lõi không kéo theo httpx ngay ở thời điểm
    # import, đồng thời cắt vòng phụ thuộc giữa provider và file này.
    from src.services.facility_providers.google_places import GooglePlacesProvider
    from src.services.facility_providers.local_directory import LocalDirectoryProvider

    settings = get_settings()
    radius = int(radius_meters or settings.facility_search_radius_meters)
    limit = int(settings.facility_max_results)

    prefers_google = settings.facility_provider in {"auto", "google"} and bool(
        settings.google_maps_api_key
    )
    degraded = False

    if prefers_google:
        if not _external_budget_available(user_key):
            # Hết suất gọi API trong cửa sổ hiện tại. Đây là quyết định về chi
            # phí, không phải về quyền truy cập: người bệnh vẫn có danh sách.
            logger.info("[Facilities] Hạn mức gọi Places đã hết, dùng danh bạ nội bộ.")
            degraded = True
        else:
            key = _cache_key("google_places", latitude, longitude, radius, limit)
            cached = _cache_get(key)
            if cached is not None:
                return _response(
                    cached,
                    latitude=latitude,
                    longitude=longitude,
                    radius_meters=radius,
                    limit=limit,
                    data_source="google_places",
                    degraded=False,
                    accuracy_meters=accuracy_meters,
                )
            try:
                candidates = await GooglePlacesProvider(
                    api_key=settings.google_maps_api_key,
                    timeout_seconds=settings.facility_provider_timeout_seconds,
                ).search(
                    latitude=latitude,
                    longitude=longitude,
                    radius_meters=radius,
                    limit=limit,
                )
            except Exception as exc:  # provider ngoài: mọi sự cố đều là sự cố hạ tầng
                # Cố ý không ghi toạ độ vào log -- xem src/services/log_redaction.py.
                logger.warning(
                    "[Facilities] Google Places không phục vụ được (%s), dùng danh bạ nội bộ.",
                    exc,
                )
                degraded = True
            else:
                if candidates:
                    _cache_put(key, candidates)
                    return _response(
                        candidates,
                        latitude=latitude,
                        longitude=longitude,
                        radius_meters=radius,
                        limit=limit,
                        data_source="google_places",
                        degraded=False,
                        accuracy_meters=accuracy_meters,
                    )
                # Google không thấy gì trong bán kính này. Danh bạ nội bộ có thể
                # vẫn có -- thử nốt, và nói thật rằng kết quả không đến từ nguồn
                # đã định.
                degraded = True

    local_candidates = await LocalDirectoryProvider(session).search(
        latitude=latitude,
        longitude=longitude,
        radius_meters=radius,
        limit=limit,
    )
    return _response(
        local_candidates,
        latitude=latitude,
        longitude=longitude,
        radius_meters=radius,
        limit=limit,
        data_source="local_directory",
        degraded=degraded,
        accuracy_meters=accuracy_meters,
    )
