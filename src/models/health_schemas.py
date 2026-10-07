"""DTO cho nội dung giáo dục sức khỏe (Health Education).

Đóng vách ngăn giữa bảng ``health_topics`` và Frontend
@[frontend/src/services/health.service.ts]. Trường ``disclaimer`` được server phát
kèm mọi phản hồi để giao diện không tự chế lời miễn trừ trách nhiệm của riêng nó.
"""

from datetime import datetime
from typing import Self

from pydantic import BaseModel, ConfigDict, Field

from src.models.db_models import HealthTopic

HEALTH_CONTENT_DISCLAIMER = (
    "Đây là thông tin sức khỏe mang tính tham khảo, không thay thế cho thăm khám "
    "và đánh giá trực tiếp của nhân viên y tế."
)


def _display_summary(topic: HealthTopic) -> str:
    """Bản do LLM diễn giải nếu đã qua kiểm định, nếu không thì bản seed gốc."""
    return topic.ai_summary or topic.summary


class HealthTopicSummaryDTO(BaseModel):
    """Dữ liệu vừa đủ cho một thẻ trên trang chủ."""

    model_config = ConfigDict(from_attributes=True)

    slug: str = Field(description="Định danh URL của chủ đề")
    name: str = Field(description="Tên chủ đề")
    summary: str = Field(description="Tóm tắt ngắn hiển thị trên thẻ")
    symptoms: list[str] = Field(default_factory=list, description="Triệu chứng thường gặp")
    prevention: list[str] = Field(default_factory=list, description="Cách phòng ngừa")
    source: str = Field(description="Tổ chức y tế phát hành nội dung")
    source_url: str = Field(description="Đường dẫn tài liệu gốc")
    last_updated: datetime = Field(description="Ngày cập nhật nội dung")
    ai_assisted: bool = Field(
        default=False,
        description="True khi phần tóm tắt đã được mô hình ngôn ngữ diễn giải lại",
    )

    @classmethod
    def from_model(cls, topic: HealthTopic) -> Self:
        return cls(
            slug=topic.slug,
            name=topic.name,
            summary=_display_summary(topic),
            symptoms=list(topic.symptoms or []),
            prevention=list(topic.prevention or []),
            source=topic.source,
            source_url=topic.source_url,
            last_updated=topic.last_updated,
            ai_assisted=bool(topic.ai_summary),
        )


class HealthTopicDetailDTO(BaseModel):
    """Nội dung đầy đủ cho màn hình chi tiết."""

    model_config = ConfigDict(from_attributes=True)

    slug: str
    name: str
    summary: str
    symptoms: list[str] = Field(default_factory=list)
    warning_signs: list[str] = Field(default_factory=list, description="Dấu hiệu cần chú ý")
    prevention: list[str] = Field(default_factory=list)
    when_to_seek_care: str = Field(default="", description="Khi nào nên đi khám")
    source: str
    source_url: str
    last_updated: datetime
    ai_assisted: bool = False
    disclaimer: str = Field(default=HEALTH_CONTENT_DISCLAIMER)

    @classmethod
    def from_model(cls, topic: HealthTopic) -> Self:
        return cls(
            slug=topic.slug,
            name=topic.name,
            summary=_display_summary(topic),
            symptoms=list(topic.symptoms or []),
            warning_signs=list(topic.warning_signs or []),
            prevention=list(topic.prevention or []),
            when_to_seek_care=topic.when_to_seek_care,
            source=topic.source,
            source_url=topic.source_url,
            last_updated=topic.last_updated,
            ai_assisted=bool(topic.ai_summary),
            disclaimer=HEALTH_CONTENT_DISCLAIMER,
        )
