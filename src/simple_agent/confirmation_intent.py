"""Classifies one patient reply sent while a confirmation offer is pending
("anything to add, or should I finalise?") as ready-to-finalise or not.

Replaces a deterministic keyword whitelist that used to live in agent.py
(``_is_confirmation_affirmation``, removed 2026-08-29). That approach had to
be patched three separate times after real misses -- "tôi không muốn bổ
sung", "bạn hãy đánh giá luôn", "tôi đồng ý để bạn đánh giá" each needed a new
filler word or exact phrase added to a whitelist before it could be
recognised -- and still missed a plain "tôi không có bổ sung gì cả" the next
time a patient phrased the same intent slightly differently, leaving them
stuck being re-offered the same confirmation they had already answered. No
finite whitelist of exact phrases can cover open-ended natural language.

This module asks the same narrow question with one small, single-purpose LLM
call instead -- the same idiom as resource_estimate.py's
``estimate_resource_count`` and phrasing.py's ``phrase_*`` calls: a
dedicated call for one job, with a `confident` gate so an unclear reply is
left unresolved (the patient sees the same offer again) rather than guessed
into a wrong answer. That gate matters more in one direction than the other
here: a false "ready" ends the conversation before the patient said
everything they wanted to, while a false "not ready" only costs one extra
turn -- so an unconfident classification always resolves to False, never
True.

This is *not* a wider replacement for Phase A's own `confirmed_ready` field
(see prompts.py's UNDERSTANDING_SYSTEM_PROMPT) -- that stays, and the two are
still ORed together in agent.py. This module exists because that signal is
one flag among many a single deepagents tool-calling loop has to remember to
set correctly on one particular call among several; a call that has no job
except this one classification is structurally more reliable for it, not
because either signal alone is trusted blindly.
"""

from __future__ import annotations

import json
import logging
import os

from openai import OpenAI

from .prompts import CONFIRMATION_INTENT_SYSTEM_PROMPT

logger = logging.getLogger(__name__)


def classify_confirmation_reply(client: OpenAI, message: str, model: str | None = None) -> bool:
    model_name = model or os.getenv("DEEP_TRIAGE_MODEL", "gpt-4.1-mini")
    logger.debug("CONFIRMATION_INTENT input (model=%s) | message=%r", model_name, message)
    response = client.chat.completions.create(
        model=model_name,
        temperature=0,
        response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": CONFIRMATION_INTENT_SYSTEM_PROMPT},
            {"role": "user", "content": json.dumps({"patient_reply": message}, ensure_ascii=False)},
        ],
    )
    text = response.choices[0].message.content or "{}"
    logger.debug("CONFIRMATION_INTENT output | %r", text)
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError:
        return False
    if not isinstance(parsed, dict) or parsed.get("confident") is not True:
        return False
    return parsed.get("ready_to_finalize") is True
