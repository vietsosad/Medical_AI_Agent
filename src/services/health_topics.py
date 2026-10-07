"""Nguồn nội dung cho mục "Thông tin sức khỏe đáng chú ý".

Kiến trúc theo đúng thứ tự yêu cầu:

    Nguồn y tế đáng tin cậy -> seed có cấu trúc -> Database -> (LLM diễn giải) -> Homepage

Lớp này chỉ lo phần **nạp và đọc dữ liệu**. Toàn bộ nội dung lâm sàng đến từ file
seed đã biên soạn kèm trích dẫn nguồn; không có bước nào ở đây sinh ra nội dung y
khoa mới. Khi có API dịch tễ thật, chỉ cần thay ``load_seed_topics`` bằng một
provider khác trả về cùng cấu trúc ``HealthTopicSeed`` - phần còn lại giữ nguyên.
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

from pydantic import BaseModel, Field, HttpUrl
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from src.models.db_models import HealthTopic, get_utc_now

SEED_PATH = Path(__file__).resolve().parents[2] / "data" / "health_topics" / "vi.json"


class HealthTopicSeed(BaseModel):
    """Một chủ đề trong file seed. Validate chặt để seed hỏng không lọt vào CSDL."""

    slug: str = Field(min_length=2, max_length=120)
    name: str = Field(min_length=2, max_length=200)
    summary: str = Field(min_length=10, max_length=1000)
    symptoms: list[str] = Field(min_length=1)
    warning_signs: list[str] = Field(min_length=1)
    prevention: list[str] = Field(min_length=1)
    when_to_seek_care: str = Field(min_length=10, max_length=1000)
    source: str = Field(min_length=2, max_length=200)
    source_url: HttpUrl
    last_updated: str
    display_order: int = 0


def load_seed_topics(seed_path: Path | None = None) -> list[HealthTopicSeed]:
    """Đọc và kiểm định file seed. Ném ValueError nếu seed sai cấu trúc."""
    path = seed_path or SEED_PATH
    raw = json.loads(path.read_text(encoding="utf-8"))
    topics = raw.get("topics")
    if not isinstance(topics, list) or not topics:
        raise ValueError(f"Seed {path} không chứa danh sách 'topics' hợp lệ.")
    return [HealthTopicSeed.model_validate(item) for item in topics]


def _parse_seed_date(value: str) -> datetime:
    try:
        return datetime.strptime(value, "%Y-%m-%d")
    except ValueError as exc:
        raise ValueError(f"last_updated '{value}' phải theo định dạng YYYY-MM-DD.") from exc


async def sync_seed_into_database(
    session: AsyncSession,
    seed_path: Path | None = None,
) -> tuple[int, int]:
    """Upsert seed vào bảng ``health_topics``, khớp theo ``slug``.

    Giữ nguyên ``ai_summary`` đã sinh trước đó khi nội dung seed không đổi, để
    việc chạy lại lệnh seed không kéo theo một loạt lời gọi LLM không cần thiết.

    Trả về ``(số bản ghi tạo mới, số bản ghi cập nhật)``.
    """
    seeds = load_seed_topics(seed_path)
    created = 0
    updated = 0

    for seed in seeds:
        existing = (
            await session.execute(select(HealthTopic).where(HealthTopic.slug == seed.slug))
        ).scalars().first()

        content_changed = existing is not None and (
            existing.summary != seed.summary
            or existing.symptoms != seed.symptoms
            or existing.warning_signs != seed.warning_signs
            or existing.prevention != seed.prevention
            or existing.when_to_seek_care != seed.when_to_seek_care
        )

        if existing is None:
            existing = HealthTopic(slug=seed.slug)
            session.add(existing)
            created += 1
        else:
            updated += 1

        existing.name = seed.name
        existing.summary = seed.summary
        existing.symptoms = list(seed.symptoms)
        existing.warning_signs = list(seed.warning_signs)
        existing.prevention = list(seed.prevention)
        existing.when_to_seek_care = seed.when_to_seek_care
        existing.source = seed.source
        existing.source_url = str(seed.source_url)
        existing.last_updated = _parse_seed_date(seed.last_updated)
        existing.display_order = seed.display_order
        existing.status = "PUBLISHED"

        # Nội dung gốc đổi thì bản diễn giải cũ không còn mô tả đúng nó nữa.
        if content_changed:
            existing.ai_summary = None
            existing.ai_summary_model = None
            existing.ai_summary_generated_at = None

    await session.commit()
    return created, updated


async def list_published_topics(session: AsyncSession, limit: int = 24) -> list[HealthTopic]:
    """Các chủ đề hiển thị trên trang chủ, theo đúng thứ tự biên tập."""
    result = await session.execute(
        select(HealthTopic)
        .where(HealthTopic.status == "PUBLISHED")
        .order_by(HealthTopic.display_order, HealthTopic.name)
        .limit(limit)
    )
    return list(result.scalars().all())


async def get_topic_by_slug(session: AsyncSession, slug: str) -> HealthTopic | None:
    """Một chủ đề đã xuất bản; bản nháp và bản lưu trữ không lộ ra ngoài."""
    result = await session.execute(
        select(HealthTopic).where(
            HealthTopic.slug == slug,
            HealthTopic.status == "PUBLISHED",
        )
    )
    return result.scalars().first()


def touch_updated(topic: HealthTopic) -> HealthTopic:
    """Đóng dấu thời điểm sinh ai_summary cho mục đích cache."""
    topic.ai_summary_generated_at = get_utc_now()
    return topic
