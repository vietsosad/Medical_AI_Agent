"""Nạp và kiểm định danh bạ cơ sở y tế tự biên soạn.

Cùng kiến trúc với @[src/services/health_topics.py]:

    Nguồn công bố -> seed có cấu trúc -> Database -> API

Lớp này chỉ **nạp và đọc** dữ liệu. Không có bước nào ở đây sinh ra thông tin
mới: không gọi LLM, không suy đoán toạ độ, không tự điền số điện thoại còn
trống. Khi có danh bạ chính thức từ Bộ Y tế hoặc Sở Y tế, chỉ cần thay
``load_seed_facilities`` bằng một provider khác trả về cùng cấu trúc
``FacilitySeed``; phần còn lại giữ nguyên.

Việc kiểm định ở đây cố ý chặt: một toạ độ gõ nhầm dấu âm sẽ đẩy người bệnh đi
sai cả nghìn ki-lô-mét, và đó là loại lỗi phải chặn ngay từ lúc nạp seed chứ
không phải lúc có người đang cần chỉ đường.
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field, HttpUrl
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from src.models.db_models import MedicalFacility

SEED_PATH = Path(__file__).resolve().parents[2] / "data" / "facilities" / "vi.json"

FacilityTypeLiteral = Literal["HOSPITAL", "CLINIC", "HEALTH_STATION", "SPECIALIST_CENTER"]


class FacilitySeed(BaseModel):
    """Một cơ sở trong file seed. Validate chặt để seed hỏng không lọt vào CSDL."""

    slug: str = Field(min_length=2, max_length=120)
    name: str = Field(min_length=2, max_length=200)
    facility_type: FacilityTypeLiteral = "HOSPITAL"
    address: str = Field(min_length=5, max_length=400)
    province: str = Field(min_length=2, max_length=120)
    latitude: float = Field(ge=-90.0, le=90.0)
    longitude: float = Field(ge=-180.0, le=180.0)
    # Cố ý cho phép None và cố ý KHÔNG có giá trị mặc định nào khác: seed hiện
    # tại để trống toàn bộ số điện thoại vì chưa gọi kiểm chứng được. Một tổng
    # đài sai trong tình huống cấp cứu nguy hiểm hơn việc không có số nào.
    phone_number: str | None = Field(default=None, max_length=40)
    emergency_capability: Literal["EMERGENCY_DEPARTMENT", "UNKNOWN"] = "UNKNOWN"
    google_place_id: str | None = Field(default=None, max_length=200)
    source: str = Field(min_length=2, max_length=200)
    source_url: HttpUrl
    last_verified: str


def load_seed_facilities(seed_path: Path | None = None) -> list[FacilitySeed]:
    """Đọc và kiểm định file seed. Ném ValueError nếu seed sai cấu trúc."""
    path = seed_path or SEED_PATH
    raw = json.loads(path.read_text(encoding="utf-8"))
    facilities = raw.get("facilities")
    if not isinstance(facilities, list) or not facilities:
        raise ValueError(f"Seed {path} không chứa danh sách 'facilities' hợp lệ.")

    parsed = [FacilitySeed.model_validate(item) for item in facilities]

    slugs = [item.slug for item in parsed]
    duplicates = {slug for slug in slugs if slugs.count(slug) > 1}
    if duplicates:
        raise ValueError(f"Seed {path} có slug trùng nhau: {sorted(duplicates)}")

    return parsed


def _parse_seed_date(value: str) -> datetime:
    try:
        return datetime.strptime(value, "%Y-%m-%d")
    except ValueError as exc:
        raise ValueError(f"last_verified '{value}' phải theo định dạng YYYY-MM-DD.") from exc


async def sync_seed_into_database(
    session: AsyncSession,
    seed_path: Path | None = None,
) -> tuple[int, int]:
    """Upsert seed vào bảng ``medical_facilities``, khớp theo ``slug``.

    Chạy lại lệnh seed là thao tác idempotent: cùng một file cho ra cùng một
    trạng thái bảng. Hàm không xoá bản ghi vắng mặt trong seed -- một cơ sở được
    thêm thủ công vào CSDL không bị lệnh seed thổi bay; muốn gỡ thì đổi
    ``status`` của nó thành ARCHIVED.

    Trả về ``(số bản ghi tạo mới, số bản ghi cập nhật)``.
    """
    seeds = load_seed_facilities(seed_path)
    created = 0
    updated = 0

    for seed in seeds:
        existing = (
            await session.execute(select(MedicalFacility).where(MedicalFacility.slug == seed.slug))
        ).scalars().first()

        if existing is None:
            existing = MedicalFacility(slug=seed.slug)
            session.add(existing)
            created += 1
        else:
            updated += 1

        existing.name = seed.name
        existing.facility_type = seed.facility_type
        existing.address = seed.address
        existing.province = seed.province
        existing.latitude = seed.latitude
        existing.longitude = seed.longitude
        existing.phone_number = seed.phone_number
        existing.emergency_capability = seed.emergency_capability
        existing.google_place_id = seed.google_place_id
        existing.source = seed.source
        existing.source_url = str(seed.source_url)
        existing.last_verified = _parse_seed_date(seed.last_verified)
        existing.status = "PUBLISHED"

    await session.commit()
    return created, updated


async def count_published_facilities(session: AsyncSession) -> int:
    """Số cơ sở đang hiển thị được. 0 nghĩa là chưa ai chạy lệnh seed."""
    rows = (
        await session.execute(
            select(MedicalFacility.id).where(MedicalFacility.status == "PUBLISHED")
        )
    ).scalars().all()
    return len(rows)
