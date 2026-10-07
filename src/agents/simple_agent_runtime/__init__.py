"""Public entry points for the simple_agent pilot runtime.

Mirrors the three-function shape of ``src/agents/deepagent_runtime``, but the
underlying agent is built lazily in ``configure_simple_agent_runtime()``
(called from ``src/main.py``'s lifespan only when
``settings.simple_agent_enabled`` is set), not eagerly at import time --
building it queries Postgres for the whole corpus (see
``src/simple_agent/pg_corpus.py``), a cost this pilot path should not pay
when the flag is off.
"""

from __future__ import annotations

from src.agents.simple_agent_runtime.runtime import SimpleAgentRuntime

__all__ = [
    "configure_simple_agent_runtime",
    "get_simple_agent_runtime",
    "reset_simple_agent_runtime",
]

_runtime: SimpleAgentRuntime | None = None


async def configure_simple_agent_runtime() -> SimpleAgentRuntime:
    global _runtime
    _runtime = await SimpleAgentRuntime.create()
    return _runtime


def get_simple_agent_runtime() -> SimpleAgentRuntime:
    if _runtime is None:
        raise RuntimeError(
            "simple_agent runtime is not configured -- set SIMPLE_AGENT_ENABLED=true "
            "so src.main's lifespan calls configure_simple_agent_runtime()."
        )
    return _runtime


async def reset_simple_agent_runtime() -> None:
    global _runtime
    if _runtime is not None:
        await _runtime.reset()
    _runtime = None
