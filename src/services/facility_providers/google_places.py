"""Nguồn cơ sở y tế từ Google Places API (New) -- ``places:searchNearby``.

Khoá API chỉ tồn tại ở phía máy chủ. Trình duyệt không bao giờ nhận được nó:
giao diện chỉ nhận danh sách đã chuẩn hoá cùng deep link
``google.com/maps/dir/?api=1`` -- một địa chỉ web công khai không cần khoá.

Hai giới hạn phải nói thẳng, vì chúng quyết định cách giao diện được phép mô tả
dữ liệu này:

1. **Places không biết cơ sở đó có khoa cấp cứu đang trực hay không.** Nó trả về
   loại địa điểm ("hospital"), không trả về năng lực điều trị. Vì vậy mọi ứng
   viên từ đây đều mang ``emergency_capability="UNKNOWN"`` -- không suy đoán,
   không nâng cấp, kể cả khi tên cơ sở có chữ "cấp cứu".
2. **Dữ liệu Places không được lưu lại.** Điều khoản Maps Platform chỉ cho phép
   lưu lâu dài trường ``place_id``; phần nội dung còn lại không được cache quá
   30 ngày. Hệ thống này không ghi kết quả Places xuống CSDL, và cache trong
   tiến trình chỉ sống vài phút (xem ``facility_cache_ttl_seconds``).
"""

from __future__ import annotations

from typing import Any

import httpx

from src.models.facility_schemas import FacilityDataSource
from src.services.nearby_facilities import FacilityCandidate

_ENDPOINT = "https://places.googleapis.com/v1/places:searchNearby"

#: Chỉ xin đúng những trường sẽ hiển thị. FieldMask quyết định bậc tính tiền của
#: Places API, nên xin thừa là trả tiền thừa cho dữ liệu không ai đọc.
_FIELD_MASK = ",".join(
    (
        "places.id",
        "places.displayName",
        "places.formattedAddress",
        "places.location",
        "places.nationalPhoneNumber",
        "places.primaryType",
    )
)

#: Tính năng này phục vụ các mức ESI khẩn (1/2/3), nên chỉ tìm bệnh viện. Nhà
#: thuốc hay phòng khám răng cũng là "cơ sở y tế" theo phân loại của Google
#: nhưng không phải nơi nên đến với một ca cần cấp cứu, và đưa chúng vào danh
#: sách sẽ đẩy bệnh viện thật xuống dưới.
_INCLUDED_TYPES = ("hospital",)

#: Trần cứng của Places API cho một lần gọi searchNearby.
_MAX_RESULT_COUNT = 20


class GooglePlacesProvider:
    """Gọi ``places:searchNearby`` và dịch kết quả về ``FacilityCandidate``.

    Provider này cố ý **không bắt ngoại lệ**: timeout, 4xx, 5xx hay JSON méo đều
    được ném lên cho ``find_nearby_facilities`` quyết định rơi về danh bạ nội
    bộ. Nuốt lỗi ở đây sẽ biến một sự cố hạ tầng thành câu trả lời "quanh đây
    không có cơ sở y tế nào" -- đúng kiểu sai lầm nguy hiểm nhất mà tính năng
    này có thể mắc.
    """

    source: FacilityDataSource = "google_places"

    def __init__(self, *, api_key: str, timeout_seconds: float) -> None:
        self._api_key = api_key
        self._timeout_seconds = timeout_seconds

    async def search(
        self,
        *,
        latitude: float,
        longitude: float,
        radius_meters: int,
        limit: int,
    ) -> list[FacilityCandidate]:
        if not self._api_key:
            raise RuntimeError("GOOGLE_MAPS_API_KEY chưa được cấu hình.")

        payload: dict[str, Any] = {
            "includedTypes": list(_INCLUDED_TYPES),
            "maxResultCount": max(1, min(int(limit), _MAX_RESULT_COUNT)),
            "rankPreference": "DISTANCE",
            "locationRestriction": {
                "circle": {
                    "center": {"latitude": latitude, "longitude": longitude},
                    "radius": float(radius_meters),
                }
            },
            # Ngôn ngữ và vùng của người dùng cuối, để tên và địa chỉ trả về
            # đọc được bằng tiếng Việt thay vì phiên âm.
            "languageCode": "vi",
            "regionCode": "VN",
        }
        headers = {
            "Content-Type": "application/json",
            "X-Goog-Api-Key": self._api_key,
            "X-Goog-FieldMask": _FIELD_MASK,
        }

        async with httpx.AsyncClient(timeout=self._timeout_seconds) as client:
            response = await client.post(_ENDPOINT, json=payload, headers=headers)
        # Ném nguyên trạng cho tầng điều phối; thông điệp lỗi của Google có ích
        # khi đọc log, còn toạ độ thì không nằm trong đó.
        response.raise_for_status()

        places = response.json().get("places") or []
        candidates: list[FacilityCandidate] = []
        for place in places:
            candidate = _to_candidate(place)
            if candidate is not None:
                candidates.append(candidate)
        return candidates


def _to_candidate(place: dict[str, Any]) -> FacilityCandidate | None:
    """Dịch một phần tử ``places[]`` sang ứng viên, bỏ qua bản ghi không đủ dùng.

    Một địa điểm thiếu toạ độ thì không tính được khoảng cách và không chỉ đường
    được; thiếu tên thì người bệnh không biết mình đang được dẫn tới đâu. Cả hai
    trường hợp đều bị loại thay vì hiển thị một dòng trống.
    """
    location = place.get("location") or {}
    latitude = location.get("latitude")
    longitude = location.get("longitude")
    name = (place.get("displayName") or {}).get("text")
    if latitude is None or longitude is None or not name:
        return None

    place_id = place.get("id")
    return FacilityCandidate(
        # Places không phát khoá ổn định nào khác ngoài place_id; khi vắng nó,
        # toạ độ là định danh duy nhất còn lại và vẫn đủ ổn định làm React key.
        id=str(place_id or f"{latitude},{longitude}"),
        name=str(name),
        facility_type=str(place.get("primaryType") or "hospital").upper(),
        address=str(place.get("formattedAddress") or ""),
        latitude=float(latitude),
        longitude=float(longitude),
        phone_number=place.get("nationalPhoneNumber"),
        # Xem docstring của module: Places không xác nhận được năng lực cấp cứu.
        emergency_capability="UNKNOWN",
        google_place_id=str(place_id) if place_id else None,
        source="Google Maps",
        source_url=None,
    )
