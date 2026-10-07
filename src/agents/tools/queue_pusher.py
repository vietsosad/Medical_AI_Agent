"""Publish a committed, verified SBAR to the real-time clinical queue.

This module deliberately exposes no DeepAgent/LangChain tool. Publication is an
API persistence concern: callers must first pass final clinical verification
and commit the authoritative case record. Keeping the publisher async also
avoids scheduling a broadcast from inside SBAR construction, before the
transaction outcome is known.
"""

from __future__ import annotations

import logging
from typing import Any


logger = logging.getLogger(__name__)


async def publish_finalized_sbar(
    *,
    session_id: str,
    recommended_esi: int,
    chief_complaint: str,
    is_red_flag: bool,
    sbar_report: dict[str, Any],
) -> bool:
    """Best-effort publication of an already committed clinical proposal.

    ``True`` means the in-process queue manager accepted the broadcast attempt;
    it is not an acknowledgement from every connected client. The committed
    database row remains the durable source if no WebSocket listener is online
    or delivery to an individual socket fails.
    """
    if recommended_esi not in {1, 2, 3, 4, 5} or not sbar_report:
        logger.error("Refused to publish an incomplete finalized SBAR")
        return False

    try:
        from src.api.websocket_manager import get_queue_manager

        ws_manager = get_queue_manager()
        payload = {
            "event": "NEW_TRIAGE_CASE" if not is_red_flag else "RED_FLAG_ALERT",
            "session_id": session_id,
            "recommended_esi": recommended_esi,
            "chief_complaint": chief_complaint[:120],
            "is_red_flag": is_red_flag,
            "sbar_snippet": f"ESI {recommended_esi} • {chief_complaint[:60]}...",
            "sbar_report": sbar_report,
            "publication_stage": "POST_COMMIT_FINALIZED",
        }
        await ws_manager.broadcast(payload)
    except Exception:  # noqa: BLE001 - committed DB state is the durable fallback
        logger.exception("Post-commit SBAR publication failed")
        return False

    return True
