"""Chủ đề realtime cho pilot ``simple_agent``.

Tái dùng nguyên bộ máy bus sự kiện theo chủ đề của
``src.services.event_bus`` (``EventBus``/``ClinicalEvent``/``get_event_bus``)
-- lớp đó vốn không hề gắn với bất kỳ bảng cụ thể nào, chỉ nói chuyện bằng
chuỗi chủ đề và dict payload, nên dùng lại 100% an toàn thay vì viết lại một
bus riêng cho pilot.

Điều duy nhất module này thêm là một **không gian tên chủ đề tách biệt**
(tiền tố ``simple:``) để traffic của pilot không bao giờ lẫn với 3 chủ đề của
production (``staff:queue``, ``case:{id}``, ``patient:{id}``) dù cả hai dùng
chung một instance bus trong cùng tiến trình -- đúng tinh thần "song song
hoàn toàn" đã áp dụng cho mọi bảng/route khác của pilot.

Không sửa ``src/services/event_bus.py`` hay ``src/api/routes_ws.py`` -- xem
``.claude/plans/sunny-launching-mitten.md``'s bổ sung về realtime.
"""

from __future__ import annotations

from src.services.event_bus import EVENT_CASE_STATUS_CHANGED, EVENT_MESSAGE_CREATED, get_event_bus

__all__ = [
    "EVENT_MESSAGE_CREATED",
    "EVENT_CASE_STATUS_CHANGED",
    "get_event_bus",
    "SIMPLE_STAFF_QUEUE_TOPIC",
    "simple_case_topic",
    "simple_patient_topic",
]

#: Mọi y tá đang xem hàng đợi pilot (`/clinical/queue-pilot`).
SIMPLE_STAFF_QUEUE_TOPIC = "simple:staff:queue"


def simple_case_topic(session_id: str) -> str:
    """Chủ đề riêng của một phiên pilot: bệnh nhân sở hữu phiên + y tá đang xem ca đó."""
    return f"simple:case:{session_id}"


def simple_patient_topic(patient_id: str) -> str:
    """Chủ đề riêng của một bệnh nhân: đẩy tin dù họ đang ở phiên pilot nào."""
    return f"simple:patient:{patient_id}"
