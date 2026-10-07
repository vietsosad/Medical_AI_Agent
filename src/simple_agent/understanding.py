"""Phase A: a bounded OpenAI tool-calling loop that turns one patient message
into session-state mutations via ``AgentToolbox``. No clinical decision is
made here -- only "what did the patient say" (which concepts, values,
negations, corrections). Route/action/ESI matching stays deterministic in
``decision.py``.
"""

from __future__ import annotations

import json
import logging
import os
from typing import Any

from openai import OpenAI

from .prompts import TOOL_SCHEMAS, UNDERSTANDING_SYSTEM_PROMPT
from .tools import AgentToolbox

logger = logging.getLogger(__name__)

MAX_TOOL_CALLS = 8


def _parse_arguments(raw: str) -> dict[str, Any]:
    try:
        parsed = json.loads(raw or "{}")
    except json.JSONDecodeError:
        return {}
    return parsed if isinstance(parsed, dict) else {}


def run_understanding_loop(
    client: OpenAI,
    toolbox: AgentToolbox,
    message: str,
    *,
    model: str | None = None,
) -> dict[str, Any]:
    """Run the tool-calling loop until ``finish_turn`` is called or the call budget runs out.

    The initial user turn is seeded with a session snapshot (recent history,
    known concepts/facts, pending question) so the model has context from its
    very first message this turn, rather than depending on it choosing to
    call get_session_state before acting.
    """
    snapshot = toolbox.get_session_state()
    initial_payload = {"message": message, "session_snapshot": snapshot}
    messages: list[dict[str, Any]] = [
        {"role": "system", "content": UNDERSTANDING_SYSTEM_PROMPT},
        {"role": "user", "content": json.dumps(initial_payload, ensure_ascii=False)},
    ]
    model_name = model or os.getenv("DEEP_TRIAGE_MODEL", "gpt-4.1-mini")
    logger.debug(
        "PHASE A input | message=%r | session_snapshot=%s",
        message, json.dumps(snapshot, ensure_ascii=False),
    )

    for call_num in range(1, MAX_TOOL_CALLS + 1):
        response = client.chat.completions.create(
            model=model_name,
            tools=TOOL_SCHEMAS,
            tool_choice="auto",
            temperature=0,
            messages=messages,
        )
        choice = response.choices[0].message
        messages.append(choice.model_dump(exclude_none=True))
        tool_calls_desc = [
            f"{c.function.name}({c.function.arguments})" for c in (choice.tool_calls or [])
        ]
        logger.debug(
            "PHASE A LLM call %d/%d (model=%s) -> content=%r tool_calls=%s",
            call_num, MAX_TOOL_CALLS, model_name, choice.content, tool_calls_desc,
        )
        if not choice.tool_calls:
            break
        for call in choice.tool_calls:
            result = toolbox.dispatch(call.function.name, _parse_arguments(call.function.arguments))
            messages.append(
                {
                    "role": "tool",
                    "tool_call_id": call.id,
                    "content": json.dumps(result, ensure_ascii=False),
                }
            )
        if toolbox.finished:
            break

    if not toolbox.finished:
        # Ran out of budget without a terminal call -- force one so the turn
        # still produces a usable outcome instead of silently doing nothing.
        logger.debug("PHASE A exhausted %d calls without finish_turn -- forcing one", MAX_TOOL_CALLS)
        toolbox.dispatch("finish_turn", {"intent": "TRIAGE"})
    outcome = toolbox.outcome or {"intent": "TRIAGE"}
    logger.debug("PHASE A outcome | %s", json.dumps(outcome, ensure_ascii=False))
    return outcome
