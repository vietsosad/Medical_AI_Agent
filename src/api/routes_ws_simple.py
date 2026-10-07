"""Kênh WebSocket realtime cho pilot ``simple_agent``.

Deliberately song song với ``routes_ws.py`` (production), không sửa file đó:
tái dùng các hàm generic của nó (``_resolve_socket_user`` để xác thực từ
cookie/query token, ``_serve``/``POLICY_VIOLATION`` để bơm sự kiện ra socket)
vì các hàm này không hề gắn với bảng cụ thể nào -- chỉ khác ở đây là chủ đề
đăng ký (``src.simple_agent.realtime``, tiền tố ``simple:``) và điều kiện
quyền truy cập từng kênh dùng ``SimpleAgentChatSession`` thay vì
``TriageCase``. Xem ``.claude/plans/sunny-launching-mitten.md``'s bổ sung về
realtime cho lý do và phạm vi.
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, Query, WebSocket, WebSocketDisconnect
from sqlmodel import select

from src.api.dependencies import CLINICAL_STAFF_ROLES
from src.api.routes_ws import POLICY_VIOLATION, _resolve_socket_user, _serve
from src.models.db_models import SimpleAgentChatSession, User
from src.services.db import get_async_session
from src.simple_agent.realtime import (
    SIMPLE_STAFF_QUEUE_TOPIC,
    simple_case_topic,
    simple_patient_topic,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/ws", tags=["Realtime Clinical Channel (simple_agent pilot)"])


async def _may_watch_simple_case(user: User, session_id: str) -> bool:
    """Chỉ bệnh nhân sở hữu phiên pilot và nhân viên lâm sàng mới được nghe."""
    if user.role in CLINICAL_STAFF_ROLES:
        return True

    async for session in get_async_session():
        result = await session.execute(
            select(SimpleAgentChatSession).where(SimpleAgentChatSession.session_id == session_id)
        )
        chat_session = result.scalars().first()
        return chat_session is not None and chat_session.patient_id == user.id
    return False


@router.websocket("/simple-clinical")
async def simple_clinical_queue_channel(
    websocket: WebSocket,
    token: str | None = Query(default=None),
) -> None:
    """Hàng đợi pilot: tin nhắn mới, đổi trạng thái ca -- xem
    `SimpleNurseQueueWorkspace.tsx`."""
    user = await _resolve_socket_user(websocket, token)
    if user is None or user.role not in CLINICAL_STAFF_ROLES:
        await websocket.close(code=POLICY_VIOLATION)
        return

    try:
        await _serve(websocket, [SIMPLE_STAFF_QUEUE_TOPIC])
    except WebSocketDisconnect:
        pass
    except Exception:  # noqa: BLE001 - một socket hỏng không được hạ cả kênh
        logger.exception("Kênh hàng đợi pilot simple_agent gặp lỗi")


@router.websocket("/simple-case/{session_id}")
async def simple_case_channel(
    websocket: WebSocket,
    session_id: str,
    token: str | None = Query(default=None),
) -> None:
    """Hội thoại (care-team) của một phiên pilot cụ thể -- dùng cho cả khung
    chat nổi phía y tá lẫn phía bệnh nhân."""
    user = await _resolve_socket_user(websocket, token)
    if user is None or not await _may_watch_simple_case(user, session_id):
        await websocket.close(code=POLICY_VIOLATION)
        return

    try:
        await _serve(websocket, [simple_case_topic(session_id)])
    except WebSocketDisconnect:
        pass
    except Exception:  # noqa: BLE001
        logger.exception("Kênh hội thoại pilot của phiên %s gặp lỗi", session_id)


@router.websocket("/simple-patient")
async def simple_patient_channel(
    websocket: WebSocket,
    token: str | None = Query(default=None),
) -> None:
    """Kênh riêng của một bệnh nhân: biết có tin mới dù đang xem phiên pilot
    nào hoặc đang ở danh sách lịch sử -- dùng cho `SimplePilotSidebar.tsx`."""
    user = await _resolve_socket_user(websocket, token)
    if user is None:
        await websocket.close(code=POLICY_VIOLATION)
        return

    try:
        await _serve(websocket, [simple_patient_topic(user.id)])
    except WebSocketDisconnect:
        pass
    except Exception:  # noqa: BLE001
        logger.exception("Kênh realtime pilot của bệnh nhân %s gặp lỗi", user.id)
