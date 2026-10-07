"""DTO cho tính năng "tìm cơ sở y tế gần nhất" (Pydantic v2, strict).

Đóng vách ngăn giữa lớp dịch vụ @[src/services/nearby_facilities.py] và
Frontend @[frontend/src/services/facilities.service.ts].

Hai quyết định đáng ghi lại ở đây:

1. **Toạ độ đi trong thân request (POST), không đi trong query string.** Vị trí
   của một người đang cấp cứu là dữ liệu cá nhân nhạy cảm; nằm trong URL thì nó
   sẽ đọng lại ở access log của web server, ở lịch sử trình duyệt và ở header
   ``Referer`` gửi sang bên thứ ba.

2. **Server tự dựng sẵn ``directions_url``.** Định dạng deep link Google Maps
   chỉ được viết đúng một chỗ, và quan trọng hơn: deep link
   ``google.com/maps/dir/?api=1`` là URL công khai, KHÔNG cần API key, nên
   không có mẩu khoá nào phải đi xuống trình duyệt.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

#: Lời nhắc bắt buộc đi kèm mọi phản hồi. Giao diện không tự chế câu này, và
#: cũng không được phép bỏ nó đi: danh bạ cơ sở y tế là dữ liệu hành chính, nó
#: không nói được cơ sở đó lúc này có còn chỗ hay có đúng chuyên khoa hay không.
FACILITY_DISCLAIMER = (
    "Danh sách dựa trên dữ liệu địa điểm, không phải dữ liệu năng lực điều trị theo "
    "thời gian thực. Hệ thống không xác minh được cơ sở còn chỗ, còn kíp trực hay "
    "đúng chuyên khoa cho tình trạng của bạn. Trường hợp nguy kịch, hãy gọi 115 trước."
)

#: Nguồn dữ liệu của một lần tra cứu, phát kèm phản hồi để giao diện ghi nguồn
#: đúng sự thật thay vì mặc định gán cho Google.
FacilityDataSource = Literal["google_places", "local_directory"]

#: ``UNKNOWN`` không đồng nghĩa với "không có khoa cấp cứu" -- xem docstring của
#: ``MedicalFacility``. Giao diện phải phân biệt được hai điều đó.
EmergencyCapability = Literal["EMERGENCY_DEPARTMENT", "UNKNOWN"]


class NearbyFacilityRequest(BaseModel):
    """Vị trí người bệnh vừa cho phép trình duyệt chia sẻ."""

    model_config = ConfigDict(extra="forbid")

    latitude: float = Field(ge=-90.0, le=90.0, description="Vĩ độ WGS84 từ navigator.geolocation")
    longitude: float = Field(ge=-180.0, le=180.0, description="Kinh độ WGS84 từ navigator.geolocation")
    radius_meters: int | None = Field(
        default=None,
        ge=500,
        le=50_000,
        description="Bán kính tìm kiếm; bỏ trống thì dùng mặc định của hệ thống",
    )
    accuracy_meters: float | None = Field(
        default=None,
        ge=0.0,
        le=100_000.0,
        description="Sai số định vị do trình duyệt báo, chỉ để hiển thị lại cho người dùng",
    )


class NearbyFacilityDTO(BaseModel):
    """Một cơ sở y tế trong danh sách trả về."""

    model_config = ConfigDict(from_attributes=True)

    id: str = Field(description="Định danh ổn định, dùng làm React key")
    name: str
    facility_type: str = Field(description="HOSPITAL | CLINIC | HEALTH_STATION | SPECIALIST_CENTER")
    address: str
    latitude: float
    longitude: float
    distance_meters: int = Field(ge=0, description="Khoảng cách đường chim bay, KHÔNG phải quãng đường đi thực tế")
    phone_number: str | None = Field(default=None, description="None nghĩa là chưa xác minh được số")
    emergency_capability: EmergencyCapability = Field(default="UNKNOWN")
    directions_url: str = Field(description="Deep link Google Maps chỉ đường, không cần API key")
    source: str | None = Field(default=None, description="Tổ chức công bố thông tin, nếu có")
    source_url: str | None = Field(default=None)


class NearbyFacilitiesResponse(BaseModel):
    """Kết quả một lần tra cứu."""

    model_config = ConfigDict(from_attributes=True)

    facilities: list[NearbyFacilityDTO] = Field(default_factory=list)
    data_source: FacilityDataSource = Field(description="Nguồn thực tế đã phục vụ lần tra cứu này")
    # True khi provider ưu tiên hỏng và hệ thống đã tự rơi về danh bạ nội bộ.
    # Giao diện dùng cờ này để nói thật rằng danh sách có thể chưa đầy đủ, thay
    # vì im lặng trình bày một kết quả hẹp như thể đó là toàn bộ sự thật.
    degraded: bool = Field(default=False)
    search_radius_meters: int = Field(description="Bán kính đã dùng cho lần tra cứu này")
    accuracy_meters: float | None = Field(default=None, description="Sai số định vị do trình duyệt báo lại")
    disclaimer: str = Field(default=FACILITY_DISCLAIMER)
