"""Phase A, rebuilt on ``deepagents``/LangGraph instead of a raw OpenAI loop.

Same contract as ``understanding.py``'s ``run_understanding_loop``: read one
patient message, call tools on ``AgentToolbox`` to mutate session state, and
return the ``finish_turn`` outcome. Phase B (``decision.py``) and Phase C
(``phrasing.py``) are untouched by this module and never see an LLM call from
here.

The tools are generated straight from ``TOOL_SCHEMAS`` in ``prompts.py`` --
each tool's OpenAI-style JSON schema is passed as ``args_schema`` verbatim, so
the model sees exactly the same tuned parameter shapes as the raw loop, with
no risk of a hand-transcribed schema drifting from the original. Execution
for every tool is one line: ``AgentToolbox.dispatch(name, kwargs)``, so no
validation logic is duplicated here.

A deep agent's internal tool loop runs inside a single ``.invoke()`` call, so
there is no external per-round-trip checkpoint the way the raw loop's
``for call_num in range(1, MAX_TOOL_CALLS + 1)`` has. The same *outcome* --
bounded, always ending in a ``finish_turn`` -- is preserved by (a) counting
real tool dispatches per turn and refusing once the budget is exhausted, and
(b) a ``recursion_limit`` on the graph as a backstop, with a forced
``finish_turn`` if either bound is hit without one.

(a) used to be a ``ContextVar`` incremented inside ``_run`` below, but that
never actually worked: LangGraph executes each tool call in its own
task/context copy, so a ``ContextVar.set()`` made inside one dispatch is
invisible to the next one. Confirmed live by tracing it -- the counter read
back as 1 on every one of 12 real dispatches in a single turn, so the budget
was silently a no-op for as long as this module has existed. Fixed by
counting on the ``AgentToolbox`` instance instead (``real_dispatch_count``,
see ``tools.py``): that object is retrieved via ``_toolbox_ctx.get()`` fresh
on every call, but it is the *same instance* each time, and mutating a
plain attribute on a shared object (unlike a ``ContextVar``) works correctly
across whatever task LangGraph happens to run each call in.
"""

from __future__ import annotations

import json
import logging
import os
from contextvars import ContextVar
from typing import Any

from deepagents import create_deep_agent
from langchain_core.tools import BaseTool, tool
from langchain_openai import ChatOpenAI
from langgraph.errors import GraphRecursionError

from .prompts import TOOL_SCHEMAS, UNDERSTANDING_SYSTEM_PROMPT
from .tools import AgentToolbox
from .understanding import MAX_TOOL_CALLS

logger = logging.getLogger(__name__)

# Bound to the AgentToolbox for the turn currently in flight. Tool functions
# read this instead of closing over a toolbox instance, so one compiled agent
# (cached per model name) is reusable across every session/turn.
_toolbox_ctx: ContextVar[AgentToolbox | None] = ContextVar("simple_agent_toolbox", default=None)


def _current_toolbox() -> AgentToolbox:
    toolbox = _toolbox_ctx.get()
    if toolbox is None:
        raise RuntimeError("No AgentToolbox bound for the current turn.")
    return toolbox


def _make_tool(schema: dict[str, Any]) -> BaseTool:
    function_spec = schema["function"]
    name = function_spec["name"]

    def _run(**kwargs: Any) -> dict[str, Any]:
        toolbox = _current_toolbox()
        if name != "finish_turn":
            toolbox.real_dispatch_count += 1
            if toolbox.real_dispatch_count > MAX_TOOL_CALLS:
                return {
                    "ok": False,
                    "error": "Tool-call budget exhausted for this turn -- call finish_turn now.",
                }
        return toolbox.dispatch(name, kwargs)

    _run.__name__ = name
    return tool(name, description=function_spec["description"], args_schema=function_spec["parameters"])(_run)


def _build_tools() -> list[BaseTool]:
    return [_make_tool(schema) for schema in TOOL_SCHEMAS]


# Compiled agents are stateless graphs (all per-turn state lives in the
# contextvars above), so one per model name is safely reused across every
# session and turn -- mirrors how understanding.py reuses one OpenAI client.
_agents_cache: dict[str, Any] = {}

# Without an explicit timeout a stalled network call hangs the OpenAI SDK's
# own multi-minute default instead of failing fast. Confirmed the hard way: a
# turn hung for 10+ minutes during manual E2E testing. agent.py's shared
# client (phrasing, confirmation intent, pre-ask, resource estimate,
# embeddings) uses these same two values.
LLM_REQUEST_TIMEOUT_SECONDS = 30.0
LLM_MAX_RETRIES = 1


def _get_agent(model_name: str) -> Any:
    agent = _agents_cache.get(model_name)
    if agent is None:
        llm = ChatOpenAI(
            model=model_name, temperature=0,
            timeout=LLM_REQUEST_TIMEOUT_SECONDS, max_retries=LLM_MAX_RETRIES,
        )
        agent = create_deep_agent(
            model=llm,
            tools=_build_tools(),
            system_prompt=UNDERSTANDING_SYSTEM_PROMPT,
        )
        _agents_cache[model_name] = agent
    return agent


def run_deepagent_understanding_loop(
    toolbox: AgentToolbox,
    message: str,
    *,
    model: str | None = None,
) -> dict[str, Any]:
    """``deepagents``-backed replacement for ``run_understanding_loop`` with the same contract."""
    # Before anything else this turn: surface concepts/fact_targets relevant
    # to the conversation so far directly in the snapshot below -- see
    # AgentToolbox.prime_proactive_candidates's own docstring for why this
    # replaced relying on the model to call search_fact_targets_for_text
    # itself (it measurably never did, across repeated live runs).
    toolbox.prime_proactive_candidates()
    snapshot = toolbox.get_session_state()
    initial_payload = {"message": message, "session_snapshot": snapshot}
    model_name = model or os.getenv("DEEP_TRIAGE_MODEL", "gpt-4.1-mini")
    logger.debug(
        "PHASE A (deepagents) input | message=%r | session_snapshot=%s",
        message, json.dumps(snapshot, ensure_ascii=False),
    )

    agent = _get_agent(model_name)
    recursion_limit = MAX_TOOL_CALLS * 2 + 4
    toolbox_token = _toolbox_ctx.set(toolbox)
    try:
        try:
            agent.invoke(
                {"messages": [{"role": "user", "content": json.dumps(initial_payload, ensure_ascii=False)}]},
                config={"recursion_limit": recursion_limit},
            )
        except GraphRecursionError:
            logger.debug(
                "PHASE A (deepagents) hit recursion_limit=%d without finish_turn", recursion_limit
            )
    finally:
        _toolbox_ctx.reset(toolbox_token)

    if not toolbox.finished:
        # Same fallback as the raw loop: never leave a turn with no outcome.
        logger.debug("PHASE A (deepagents) exhausted without finish_turn -- forcing one")
        toolbox.dispatch("finish_turn", {"intent": "TRIAGE"})
    outcome = toolbox.outcome or {"intent": "TRIAGE"}
    logger.debug("PHASE A (deepagents) outcome | %s", json.dumps(outcome, ensure_ascii=False))
    return outcome
