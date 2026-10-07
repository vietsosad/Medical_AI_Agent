"""Process-local runtime wrapping ``SimpleTriageAgent`` for the additive
``/simple-triage/*`` pilot routes (``src/api/routes_simple_triage.py``).

This class knows nothing about SQLModel/Postgres for *session* persistence --
loading a persisted ``Session`` and saving it back is the caller's (the
route's) job. It only owns the in-process ``SimpleTriageAgent`` instance, a
per-``session_id`` async lock (mirrors
``DeepAgentSessionStore.serialize_turn`` in
``src/agents/deepagent_runtime/state_store.py``), and the sync-to-thread
boundary: ``SimpleTriageAgent.process_turn`` -- and every OpenAI call inside
it -- is a plain blocking call, never ``async def``.

The *corpus* (clinical concepts/protocol atoms/fact targets/relations +
their embeddings), however, is loaded from Postgres via ``create()`` --
see ``src/simple_agent/pg_corpus.py``. ``data/siu``/``data/indexes_siu`` are
not read here at all; ``scripts/migrate_simple_agent_corpus_to_pg.py`` must
have populated the ``simple_agent_*`` corpus tables first.
"""

from __future__ import annotations

import asyncio
from typing import Any

from src.services.db import sync_engine
from src.simple_agent.agent import SimpleTriageAgent
from src.simple_agent.pg_corpus import load_corpus_from_postgres
from src.simple_agent.session import Session
from src.simple_agent.tracing import (
    finish_trace_span,
    simple_agent_tracing_context,
    summarize_turn_result,
    trace_span,
)


class SimpleAgentRuntime:
    def __init__(self, agent: SimpleTriageAgent) -> None:
        self._agent = agent
        self._lock = asyncio.Lock()
        self._turn_locks: dict[str, asyncio.Lock] = {}

    @classmethod
    async def create(cls) -> SimpleAgentRuntime:
        """Build the runtime, loading the corpus from Postgres off the event loop."""
        corpus = await asyncio.to_thread(load_corpus_from_postgres, sync_engine)
        return cls(SimpleTriageAgent(corpus=corpus, enable_preask_check=True))

    async def _turn_lock(self, session_id: str) -> asyncio.Lock:
        async with self._lock:
            return self._turn_locks.setdefault(session_id, asyncio.Lock())

    async def process_turn(
        self,
        session_id: str,
        message: str,
        *,
        restore: Session | None = None,
    ) -> dict[str, Any]:
        """Run one turn for ``session_id``.

        ``restore``, when given, seeds this worker's in-memory state before
        the turn runs -- used when this worker has no hot session yet (e.g.
        just after a restart) and the caller reloaded it from Postgres.
        """
        turn_lock = await self._turn_lock(session_id)
        async with turn_lock:
            if restore is not None:
                self._agent.sessions[session_id] = restore
            with simple_agent_tracing_context(
                session_id,
                restored=restore is not None,
            ):
                with trace_span(
                    "simple_triage.turn",
                    inputs={
                        "message_length": len(message),
                        "restored_from_postgres": restore is not None,
                    },
                    metadata={"entrypoint": "SimpleAgentRuntime.process_turn"},
                ) as turn_span:
                    result = await asyncio.to_thread(
                        self._agent.process_turn,
                        session_id,
                        message,
                    )
                    finish_trace_span(turn_span, summarize_turn_result(result))
                    return result

    @property
    def corpus(self) -> Any:
        """The hydrated ``Corpus`` this runtime's agent was built with.

        Read-only accessor for callers that need corpus lookups (concept/fact
        display names) without running a turn -- e.g. ``routes_nurse_simple.py``
        building an SBAR summary (see ``src/simple_agent/sbar.py``). Exposes
        already-held data only; does not add any new corpus-loading path.
        """
        return self._agent.corpus

    def has_hot_session(self, session_id: str) -> bool:
        return session_id in self._agent.sessions

    def export_session(self, session_id: str) -> Session:
        return self._agent.sessions[session_id]

    async def reset(self) -> None:
        async with self._lock:
            self._agent.sessions.clear()
            self._turn_locks.clear()
