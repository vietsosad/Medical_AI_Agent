"""Kênh thời gian thực cho hàng đợi lâm sàng và hội thoại của từng ca.

Nguyên tắc bảo mật của module này:

1. **Xác thực trước khi chấp nhận socket.** Không có thẻ quyền hợp lệ thì
   handshake bị từ chối, không phải chấp nhận rồi mới đóng.
2. **Quyền quyết định chủ đề được nghe**, không phải client. Client không gửi
   lên danh sách chủ đề nào cả.
3. **Kênh chỉ đi một chiều.** Mọi hành động lâm sàng vẫn phải đi qua REST để
   được kiểm tra phiên bản, kiểm tra quyền sở hữu ca và ghi nhật ký kiểm toán.
"""

from __future__ import annotations

import asyncio
import logging

from fastapi import APIRouter, Query, WebSocket, WebSocketDisconnect
from sqlmodel import select

from src.api.dependencies import CLINICAL_STAFF_ROLES
from src.models.db_models import TriageCase, User
from src.services.db import get_async_session
from src.services.event_bus import STAFF_QUEUE_TOPIC, case_topic, patient_topic, get_event_bus
from src.services.security import decode_access_token
from src.api.websocket_manager import drain_client_frames, pump_events_to_socket

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/ws", tags=["Realtime Clinical Channel"])

# Mã đóng chuẩn WebSocket cho "vi phạm chính sách"; dùng cho cả trường hợp
# thiếu thẻ quyền lẫn không đủ quyền, để không lộ ra ca nào có thật.
POLICY_VIOLATION = 1008

# Tên cookie chứa access token, khớp với thứ backend đặt lúc đăng nhập.
ACCESS_TOKEN_COOKIE = "ai20k_access_token"


async def _resolve_socket_user(websocket: WebSocket, token: str | None) -> User | None:
    """Đọc thẻ quyền từ query hoặc cookie rồi truy hồi tài khoản tương ứng.

    Trình duyệt không cho phép đặt header ``Authorization`` khi mở WebSocket,
    nên phải chấp nhận thẻ quyền qua query. Cookie được ưu tiên khi có vì nó
    không lọt vào access log của proxy.
    """
    raw_token = websocket.cookies.get(ACCESS_TOKEN_COOKIE) or token
    if not raw_token:
        return None

    payload = decode_access_token(raw_token)
    if not payload:
        return None

    subject = str(payload.get("sub", ""))
    if not subject:
        return None

    async for session in get_async_session():
        result = await session.execute(select(User).where(User.id == subject))
        user = result.scalars().first()
        if user is None and "@" in subject:
            result = await session.execute(select(User).where(User.email == subject))
            user = result.scalars().first()
        if user is None:
            return None
        if not user.is_active and not user.is_guest:
            return None
        return user
    return None


async def _may_watch_case(user: User, case_id: str) -> bool:
    """Chỉ bệnh nhân sở hữu ca và nhân viên lâm sàng mới được nghe ca đó."""
    if user.role in CLINICAL_STAFF_ROLES:
        return True

    async for session in get_async_session():
        result = await session.execute(select(TriageCase).where(TriageCase.id == case_id))
        case = result.scalars().first()
        return case is not None and case.patient_id == user.id
    return False


async def _serve(websocket: WebSocket, topics: list[str]) -> None:
    """Chấp nhận socket rồi chạy song song bơm sự kiện và phát hiện ngắt kết nối."""
    try:
        await websocket.accept()
        bus = get_event_bus()
        async with bus.subscribe(topics) as queue:
            await websocket.send_json({"event": "subscribed", "topics": topics})
            pump = asyncio.create_task(pump_events_to_socket(websocket, queue))
            drain = asyncio.create_task(drain_client_frames(websocket))
            try:
                done, pending = await asyncio.wait(
                    {pump, drain}, return_when=asyncio.FIRST_COMPLETED
                )
                for task in pending:
                    task.cancel()
                for task in done:
                    exception = task.exception()
                    if exception is not None and not isinstance(
                        exception, (WebSocketDisconnect, asyncio.CancelledError)
                    ):
                        raise exception
            finally:
                for task in (pump, drain):
                    if not task.done():
                        task.cancel()
    except OSError as exc:
        # Uvicorn raises ClientDisconnected (an OSError) when the browser
        # closes during accept/send. Normalize that transport race so route
        # handlers treat it like every other ordinary WebSocket disconnect.
        raise WebSocketDisconnect(code=1006) from exc


@router.websocket("/clinical")
async def clinical_queue_channel(
    websocket: WebSocket,
    token: str | None = Query(default=None),
) -> None:
    """Hàng đợi trực chiến: ca mới, báo động đỏ, nhận ca, chuyển ca."""
    user = await _resolve_socket_user(websocket, token)
    if user is None or user.role not in CLINICAL_STAFF_ROLES:
        await websocket.close(code=POLICY_VIOLATION)
        return

    try:
        await _serve(websocket, [STAFF_QUEUE_TOPIC])
    except WebSocketDisconnect:
        pass
    except Exception:  # noqa: BLE001 - một socket hỏng không được hạ cả kênh
        logger.exception("Kênh hàng đợi lâm sàng gặp lỗi")


@router.websocket("/case/{case_id}")
async def case_channel(
    websocket: WebSocket,
    case_id: str,
    token: str | None = Query(default=None),
) -> None:
    """Hội thoại của một ca: tin nhắn mới, trạng thái ca, đánh dấu đã đọc."""
    user = await _resolve_socket_user(websocket, token)
    if user is None or not await _may_watch_case(user, case_id):
        await websocket.close(code=POLICY_VIOLATION)
        return

    try:
        await _serve(websocket, [case_topic(case_id)])
    except WebSocketDisconnect:
        pass
    except Exception:  # noqa: BLE001 - một socket hỏng không được hạ cả kênh
        logger.exception("Kênh hội thoại của ca %s gặp lỗi", case_id)


@router.websocket("/patient")
async def patient_channel(
    websocket: WebSocket,
    token: str | None = Query(default=None),
) -> None:
    """Kênh thời gian thực dành riêng cho một bệnh nhân: nhận thông báo chung."""
    user = await _resolve_socket_user(websocket, token)
    if user is None:
        await websocket.close(code=POLICY_VIOLATION)
        return

    try:
        await _serve(websocket, [patient_topic(user.id)])
    except WebSocketDisconnect:
        pass
    except Exception:  # noqa: BLE001
        logger.exception("Kênh realtime của bệnh nhân %s gặp lỗi", user.id)
