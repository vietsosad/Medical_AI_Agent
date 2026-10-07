"""Danh bạ cơ sở y tế tự biên soạn, đọc từ bảng ``medical_facilities``.

Đây là nguồn **luôn có mặt**: không cần khoá API, không phát sinh chi phí, chạy
được ngoại tuyến, và là chỗ hệ thống rơi về khi provider ngoài hỏng. Nội dung do
dự án biên soạn từ nguồn công bố có trích dẫn (xem ``data/facilities/vi.json``),
nên mỗi bản ghi mang theo ``source``/``source_url`` của chính nó.
"""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from src.models.db_models import MedicalFacility
from src.models.facility_schemas import FacilityDataSource
from src.services.nearby_facilities import FacilityCandidate, bounding_box

#: Trần số bản ghi kéo từ DB cho một lần tra cứu. Hộp bao đã lọc phần lớn rồi;
#: trần này chỉ để một bán kính rộng bất thường không kéo cả bảng vào bộ nhớ.
#: Nó KHÔNG phải số mục hiển thị -- việc cắt danh sách nằm ở ``rank_candidates``.
_MAX_ROWS_SCANNED = 200


class LocalDirectoryProvider:
    """Đọc ứng viên từ danh bạ nội bộ, lọc thô bằng hộp bao ở tầng SQL."""

    source: FacilityDataSource = "local_directory"

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def search(
        self,
        *,
        latitude: float,
        longitude: float,
        radius_meters: int,
        limit: int,
    ) -> list[FacilityCandidate]:
        """Các cơ sở đã xuất bản nằm trong hộp bao quanh toạ độ đã cho.

        Trả về ứng viên trong *hộp bao*, rộng hơn hình tròn bán kính yêu cầu.
        Phép lọc tròn chính xác do ``rank_candidates`` làm bằng haversine --
        provider cố ý không tự quyết định phần đó (xem ``FacilityProvider``).

        ``limit`` không được dùng để cắt ở đây vì lý do tương tự: cắt trước khi
        tính khoảng cách sẽ loại nhầm cơ sở gần nhất chỉ vì nó đứng sau trong
        thứ tự của bảng.
        """
        min_lat, max_lat, min_lon, max_lon = bounding_box(latitude, longitude, float(radius_meters))

        statement = (
            select(MedicalFacility)
            .where(
                MedicalFacility.status == "PUBLISHED",
                MedicalFacility.latitude >= min_lat,
                MedicalFacility.latitude <= max_lat,
                MedicalFacility.longitude >= min_lon,
                MedicalFacility.longitude <= max_lon,
            )
            .limit(_MAX_ROWS_SCANNED)
        )
        rows = (await self._session.execute(statement)).scalars().all()

        return [
            FacilityCandidate(
                id=row.id,
                name=row.name,
                facility_type=row.facility_type,
                address=row.address,
                latitude=row.latitude,
                longitude=row.longitude,
                phone_number=row.phone_number,
                # Chỉ "EMERGENCY_DEPARTMENT" khi nguồn trích dẫn nói rõ; mọi
                # giá trị lạ trong DB đều quy về UNKNOWN chứ không suy đoán.
                emergency_capability=(
                    "EMERGENCY_DEPARTMENT"
                    if row.emergency_capability == "EMERGENCY_DEPARTMENT"
                    else "UNKNOWN"
                ),
                google_place_id=row.google_place_id,
                source=row.source,
                source_url=row.source_url,
            )
            for row in rows
        ]
