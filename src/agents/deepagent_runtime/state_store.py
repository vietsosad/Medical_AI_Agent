"""Application-scoped clinical state cache backed by durable chat recovery."""

from __future__ import annotations

import asyncio
from copy import deepcopy
from contextlib import asynccontextmanager
from collections.abc import AsyncIterator
from datetime import UTC, datetime
from typing import Any

from src.agents.deepagent_runtime.schemas import DeepAgentSessionState


class DeepAgentSessionStore:
    """Keep hot session state; patient messages remain the durable source."""

    def __init__(self) -> None:
        self._states: dict[str, DeepAgentSessionState] = {}
        self._lock = asyncio.Lock()
        self._turn_locks: dict[str, asyncio.Lock] = {}

    @asynccontextmanager
    async def serialize_turn(self, session_id: str) -> AsyncIterator[None]:
        """Prevent two concurrent turns from overwriting one clinical session."""
        async with self._lock:
            turn_lock = self._turn_locks.setdefault(session_id, asyncio.Lock())
        async with turn_lock:
            yield

    async def get(self, session_id: str) -> DeepAgentSessionState | None:
        async with self._lock:
            state = self._states.get(session_id)
            return state.model_copy(deep=True) if state else None

    async def prepare_turn(
        self,
        session_id: str,
        incoming: dict[str, Any],
    ) -> dict[str, Any]:
        async with self._lock:
            existing = self._states.get(session_id)
            state = deepcopy(existing.clinical_state) if existing else {}
            for key, value in incoming.items():
                if key in {"messages", "rag_citations"} and existing and not value:
                    continue
                state[key] = deepcopy(value)
            state["session_id"] = session_id
            return state

    async def save(
        self,
        session_id: str,
        clinical_state: dict[str, Any],
        *,
        execution_mode: str,
        tool_audit: list[Any],
    ) -> None:
        async with self._lock:
            self._states[session_id] = DeepAgentSessionState(
                session_id=session_id,
                clinical_state=deepcopy(clinical_state),
                tool_audit=deepcopy(tool_audit),
                execution_mode=execution_mode,
                updated_at=datetime.now(UTC),
            )

    async def clear(self) -> None:
        async with self._lock:
            self._states.clear()
            self._turn_locks.clear()
