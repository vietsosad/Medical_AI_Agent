"""Cầu nối giữa bus sự kiện lâm sàng và các kết nối WebSocket đang mở.

Bản trước phát sóng mọi thông điệp tới **mọi** kết nối và không hề xác thực ai
đang lắng nghe. Bản này chuyển sang mô hình chủ đề của :mod:`src.services.event_bus`:
mỗi kết nối chỉ nhận đúng những chủ đề mà quyền của họ cho phép, và việc kiểm
tra quyền xảy ra ở tầng route **trước khi** socket được chấp nhận.

``ClinicalQueueManager.broadcast`` được giữ nguyên chữ ký vì
:func:`src.agents.tools.queue_pusher.publish_finalized_sbar` đã gọi nó sau khi
ca bệnh được commit; giờ nó đẩy vào bus thay vì tự giữ danh sách socket.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any

from fastapi import WebSocket
from starlette.websockets import WebSocketState

from src.services.event_bus import (
    EVENT_CASE_CREATED,
    EVENT_CASE_RED_FLAG_DETECTED,
    STAFF_QUEUE_TOPIC,
    ClinicalEvent,
    get_event_bus,
)

logger = logging.getLogger(__name__)

# Nhịp giữ kết nối. Proxy và cân bằng tải thường đóng socket im lặng sau
# khoảng 60 giây, nên phải có tín hiệu sống ngắn hơn ngưỡng đó.
HEARTBEAT_SECONDS = 25.0

# Tên sự kiện cũ mà bộ đẩy hàng đợi đang dùng, ánh xạ sang từ vựng của bus.
_LEGACY_EVENT_NAMES: dict[str, str] = {
    "NEW_TRIAGE_CASE": EVENT_CASE_CREATED,
    "RED_FLAG_ALERT": EVENT_CASE_RED_FLAG_DETECTED,
}


class ClinicalQueueManager:
    """Đưa thông điệp hàng đợi lâm sàng vào bus sự kiện theo chủ đề."""

    async def broadcast(self, message: dict[str, Any]) -> None:
        """Phát một thay đổi hàng đợi tới các trạm lâm sàng đang trực.

        Không ném lỗi ra ngoài: bản ghi trong cơ sở dữ liệu đã commit mới là
        nguồn sự thật, còn đây chỉ là tín hiệu đánh thức giao diện.
        """
        legacy_name = str(message.get("event", ""))
        event = _LEGACY_EVENT_NAMES.get(legacy_name)
        if event is None:
            logger.warning("Bỏ qua thông điệp hàng đợi không rõ loại: %r", legacy_name)
            return

        payload = {key: value for key, value in message.items() if key != "event"}
        payload.setdefault("case_id", message.get("session_id"))
        try:
            await get_event_bus().publish(STAFF_QUEUE_TOPIC, event, payload)
        except Exception:  # noqa: BLE001 - trạng thái đã commit là chỗ dựa bền vững
            logger.exception("Không phát được sự kiện hàng đợi lâm sàng")


_manager: ClinicalQueueManager | None = None


def get_queue_manager() -> ClinicalQueueManager:
    """Trả về bộ điều phối hàng đợi dùng chung của tiến trình."""
    global _manager
    if _manager is None:
        _manager = ClinicalQueueManager()
    return _manager


async def pump_events_to_socket(
    websocket: WebSocket,
    queue: asyncio.Queue[ClinicalEvent],
) -> None:
    """Đẩy sự kiện từ hàng đợi người nhận ra socket cho tới khi socket đóng.

    Xen kẽ nhịp ``heartbeat`` để phía trình duyệt phân biệt được "đường truyền
    đứt" với "hiện chưa có gì mới" — hai tình huống trông giống hệt nhau nếu chỉ
    nhìn vào việc không có dữ liệu tới.
    """
    while True:
        try:
            event = await asyncio.wait_for(queue.get(), timeout=HEARTBEAT_SECONDS)
        except TimeoutError:
            if websocket.client_state is not WebSocketState.CONNECTED:
                return
            await websocket.send_json({"event": "heartbeat"})
            continue

        if websocket.client_state is not WebSocketState.CONNECTED:
            return
        await websocket.send_json(event.to_wire())


async def drain_client_frames(websocket: WebSocket) -> None:
    """Đọc và bỏ qua dữ liệu do client gửi lên.

    Kênh này chỉ đi một chiều: mọi hành động lâm sàng đều phải qua REST để được
    kiểm tra quyền, kiểm tra phiên bản và ghi nhật ký kiểm toán. Vẫn phải đọc
    frame để phát hiện lúc client ngắt kết nối.
    """
    while True:
        await websocket.receive_text()
