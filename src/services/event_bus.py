"""Bus sự kiện lâm sàng theo chủ đề (topic-scoped clinical event bus).

Vì sao tồn tại lớp này thay vì phát sóng thẳng qua WebSocket:

- **Phân vùng người nhận.** Một ca bệnh chỉ được gửi tới đúng những người có
  quyền với ca đó. Cách phát sóng cho toàn bộ kết nối đang mở là một lỗ hổng
  quyền riêng tư y tế, không phải một chi tiết tối ưu.
- **Thay hạ tầng mà không sửa nơi gọi.** Bản hiện tại chạy trong bộ nhớ của một
  tiến trình. Khi backend chạy nhiều replica, chỉ cần thêm một lớp cài đặt
  `EventBus` dựa trên Redis pub/sub; mọi ``publish``/``subscribe`` giữ nguyên.
- **Sự kiện không bao giờ là nguồn sự thật.** Cơ sở dữ liệu mới là nguồn sự
  thật. Sự kiện chỉ nói "có thay đổi, hãy đọc lại", nên mất một sự kiện làm
  giao diện chậm cập nhật chứ không làm sai dữ liệu lâm sàng.
"""

from __future__ import annotations

import asyncio
import logging
from collections.abc import AsyncIterator, Iterable
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Protocol

from src.models.db_models import get_utc_now

logger = logging.getLogger(__name__)

# Số sự kiện tối đa xếp hàng cho một người nhận đang xử lý chậm. Khi đầy, sự
# kiện cũ nhất bị bỏ: người nhận vẫn được đánh thức và sẽ đọc lại trạng thái
# mới nhất từ cơ sở dữ liệu, nên bỏ sự kiện cũ an toàn hơn là chặn người gửi.
SUBSCRIBER_QUEUE_SIZE = 64

# ---------------------------------------------------------------------------
# Chủ đề
# ---------------------------------------------------------------------------

#: Mọi nhân viên lâm sàng đang trực: thay đổi ở hàng đợi chung.
STAFF_QUEUE_TOPIC = "staff:queue"


def case_topic(case_id: str) -> str:
    """Chủ đề riêng của một ca: chỉ bệnh nhân sở hữu và nhân viên lâm sàng."""
    return f"case:{case_id}"


def patient_topic(patient_id: str) -> str:
    """Chủ đề riêng của một bệnh nhân: nhận thông báo đẩy."""
    return f"patient:{patient_id}"


# ---------------------------------------------------------------------------
# Tên sự kiện — giữ đúng quy ước ``danh_từ.động_từ`` của dự án
# ---------------------------------------------------------------------------

EVENT_CASE_CREATED = "case.created"
EVENT_CASE_RED_FLAG_DETECTED = "case.red_flag_detected"
EVENT_CASE_CLAIMED = "case.claimed"
EVENT_CASE_RELEASED = "case.released"
EVENT_CASE_ESCALATED = "case.escalated"
EVENT_CASE_STATUS_CHANGED = "case.status_changed"
EVENT_MESSAGE_CREATED = "message.created"
EVENT_MESSAGE_READ = "message.read"

#: Các sự kiện hợp lệ. Publish một tên ngoài tập này là lỗi lập trình, không
#: phải dữ liệu người dùng, nên chặn ngay tại chỗ thay vì âm thầm bỏ qua.
KNOWN_EVENTS: frozenset[str] = frozenset(
    {
        EVENT_CASE_CREATED,
        EVENT_CASE_RED_FLAG_DETECTED,
        EVENT_CASE_CLAIMED,
        EVENT_CASE_RELEASED,
        EVENT_CASE_ESCALATED,
        EVENT_CASE_STATUS_CHANGED,
        EVENT_MESSAGE_CREATED,
        EVENT_MESSAGE_READ,
    }
)


@dataclass(frozen=True)
class ClinicalEvent:
    """Một thông báo "có thay đổi", không phải bản sao dữ liệu lâm sàng."""

    event: str
    topic: str
    payload: dict[str, Any] = field(default_factory=dict)
    emitted_at: datetime = field(default_factory=get_utc_now)

    def to_wire(self) -> dict[str, Any]:
        return {
            "event": self.event,
            "topic": self.topic,
            "payload": self.payload,
            "emitted_at": self.emitted_at.isoformat(),
        }


class EventBus(Protocol):
    """Hợp đồng tối thiểu để lớp WebSocket không phụ thuộc vào hạ tầng."""

    async def publish(self, topic: str, event: str, payload: dict[str, Any]) -> int: ...

    def subscribe(self, topics: Iterable[str]) -> Any: ...


class InMemoryEventBus:
    """Cài đặt một tiến trình. Đủ cho triển khai một replica hiện tại."""

    def __init__(self) -> None:
        self._topics: dict[str, set[asyncio.Queue[ClinicalEvent]]] = {}

    # -- phía người nhận ---------------------------------------------------

    @asynccontextmanager
    async def subscribe(
        self, topics: Iterable[str]
    ) -> AsyncIterator[asyncio.Queue[ClinicalEvent]]:
        """Đăng ký nhận sự kiện của các chủ đề, tự huỷ đăng ký khi thoát khối."""
        requested = {topic for topic in topics if topic}
        queue: asyncio.Queue[ClinicalEvent] = asyncio.Queue(maxsize=SUBSCRIBER_QUEUE_SIZE)
        for topic in requested:
            self._topics.setdefault(topic, set()).add(queue)
        try:
            yield queue
        finally:
            for topic in requested:
                subscribers = self._topics.get(topic)
                if subscribers is None:
                    continue
                subscribers.discard(queue)
                if not subscribers:
                    self._topics.pop(topic, None)

    # -- phía người gửi ----------------------------------------------------

    async def publish(self, topic: str, event: str, payload: dict[str, Any]) -> int:
        """Gửi tới mọi người nhận của một chủ đề; trả về số người đã nhận."""
        if event not in KNOWN_EVENTS:
            raise ValueError(f"Sự kiện lâm sàng không được khai báo: {event!r}")

        subscribers = self._topics.get(topic)
        if not subscribers:
            return 0

        message = ClinicalEvent(event=event, topic=topic, payload=payload)
        delivered = 0
        for queue in tuple(subscribers):
            if _offer(queue, message):
                delivered += 1
        return delivered

    def subscriber_count(self, topic: str) -> int:
        """Dùng cho chẩn đoán và kiểm thử; không dùng trong luồng lâm sàng."""
        return len(self._topics.get(topic, ()))


def _offer(queue: asyncio.Queue[ClinicalEvent], message: ClinicalEvent) -> bool:
    """Xếp sự kiện vào hàng đợi, bỏ cái cũ nhất nếu người nhận đang tụt lại."""
    try:
        queue.put_nowait(message)
        return True
    except asyncio.QueueFull:
        try:
            queue.get_nowait()
            queue.task_done()
        except asyncio.QueueEmpty:  # pragma: no cover - chỉ khi có tranh chấp
            pass
        try:
            queue.put_nowait(message)
            logger.warning(
                "Người nhận realtime bị tụt lại, đã bỏ sự kiện cũ nhất của %s", message.topic
            )
            return True
        except asyncio.QueueFull:  # pragma: no cover - chỉ khi có tranh chấp
            logger.warning("Không xếp được sự kiện %s vào hàng đợi", message.event)
            return False


_bus: InMemoryEventBus | None = None


def get_event_bus() -> InMemoryEventBus:
    """Trả về bus dùng chung của tiến trình."""
    global _bus
    if _bus is None:
        _bus = InMemoryEventBus()
    return _bus


def reset_event_bus() -> None:
    """Xoá trạng thái giữa các bài kiểm thử."""
    global _bus
    _bus = None
