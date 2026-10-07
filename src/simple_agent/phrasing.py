"""Phase C: turns a decision already made by ``decision.py`` into natural,
jargon-free Vietnamese. This step cannot introduce clinical facts -- it only
phrases a fact target to ask about, or a final matched/unmatched outcome.
"""

from __future__ import annotations

import json
import logging
import os
from typing import Any

from openai import OpenAI

from .prompts import (
    CONFIRMATION_PHRASING_SYSTEM_PROMPT,
    OUTCOME_PHRASING_SYSTEM_PROMPT,
    QUESTION_PHRASING_SYSTEM_PROMPT,
)

logger = logging.getLogger(__name__)


def _call(client: OpenAI, kind: str, system_prompt: str, payload: dict[str, Any], model: str | None) -> str:
    model_name = model or os.getenv("DEEP_TRIAGE_MODEL", "gpt-4.1-mini")
    logger.debug("PHASE C %s input (model=%s) | %s", kind, model_name, json.dumps(payload, ensure_ascii=False))
    response = client.chat.completions.create(
        model=model_name,
        temperature=0.3,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": json.dumps(payload, ensure_ascii=False)},
        ],
    )
    text = (response.choices[0].message.content or "").strip()
    logger.debug("PHASE C %s output | %r", kind, text)
    return text


def phrase_question(
    client: OpenAI,
    *,
    fact_target: dict[str, Any],
    needs_precision: bool,
    history: list[tuple[str, str]],
    subject: dict[str, Any] | None = None,
    topic_shift: bool = False,
    model: str | None = None,
) -> str:
    payload = {
        "fact_target_id": fact_target["fact_target_id"],
        "name": fact_target["name"],
        "reporting_style": fact_target.get("reporting_style", "CLINICIAN_ONLY"),
        "lay_terms": fact_target.get("lay_terms", ""),
        "severity_anchors": fact_target.get("severity_anchors"),
        "needs_precision": needs_precision,
        "subject": subject or {"type": "SELF"},
        "recent_conversation": [{"speaker": speaker, "text": text} for speaker, text in history[-4:]],
        # See agent.py's topic_shift computation: true when this question is
        # an unrelated red-flag/differential check, not a follow-up to what
        # was just asked -- lets phrase_question add a short transition
        # instead of sounding like a non-sequitur.
        "topic_shift": topic_shift,
    }
    return _call(client, "phrase_question", QUESTION_PHRASING_SYSTEM_PROMPT, payload, model)


def phrase_confirmation(
    client: OpenAI,
    *,
    recorded_concepts: list[str],
    recorded_facts: list[dict[str, Any]],
    subject: dict[str, Any] | None = None,
    model: str | None = None,
) -> str:
    payload = {
        "recorded_concepts": recorded_concepts,
        "recorded_facts": recorded_facts,
        "subject": subject or {"type": "SELF"},
    }
    return _call(client, "phrase_confirmation", CONFIRMATION_PHRASING_SYSTEM_PROMPT, payload, model)


def phrase_outcome(
    client: OpenAI,
    *,
    matched: bool,
    esi_levels: list[str],
    subject: dict[str, Any] | None = None,
    model: str | None = None,
) -> str:
    payload = {"matched": matched, "esi_levels": esi_levels, "subject": subject or {"type": "SELF"}}
    return _call(client, "phrase_outcome", OUTCOME_PHRASING_SYSTEM_PROMPT, payload, model)
