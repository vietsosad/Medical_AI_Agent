"""Deterministic pre-Phase-A routing.

A "skill" here is a named situation-handling bundle, not a framework: a
classifier rule plus whether the message even reaches the LLM. This module
only holds the one skill that can be caught *deterministically* -- an attempt
to extract the system prompt, tool schemas, or internal instructions. Caught
here, it never spends an LLM call and can't be talked around by clever
phrasing, the same defense-in-depth spirit as ``agent.py``'s existing
``_is_unknown_answer`` short-circuit.

Off-topic chit-chat is a *different* skill (see ``UNDERSTANDING_SYSTEM_PROMPT``
in ``prompts.py``) that stays inside Phase A on purpose: telling "off-topic"
apart from a real health message needs understanding, not just keyword
matching, so it can't be caught here.
"""

from __future__ import annotations

import re

from .corpus import fold

# Non-exhaustive by design -- this is one layer of defense, not the only one.
# Subtler extraction attempts are still covered by the hardened rules in
# UNDERSTANDING_SYSTEM_PROMPT.
_PROBE_PATTERNS = (
    r"\bsystem prompt\b",
    r"\bprompt he thong\b",
    r"huong dan he thong",
    r"chi thi he thong",
    r"in ra (toan bo )?(huong dan|chi thi|prompt)",
    r"doc lai (huong dan|chi thi|prompt)",
    r"bo qua (tat ca )?huong dan (truoc|ban dau)",
    r"bo qua chi thi",
    r"ignore (all |previous )?instructions",
    r"reveal your (system )?prompt",
    r"what (is|are) your (system )?(prompt|instructions)",
    r"ban duoc lap trinh (nhu the nao|the nao|ra sao)",
    r"ban duoc train (nhu the nao|the nao)",
    r"developer mode",
    r"che do (nha phat trien|dev)",
    r"cac tool (ban|cua ban) co",
    r"function (ban|cua ban) co the goi",
    r"internal id",
    r"act as (a |an )?(dan|jailbreak|unrestricted)",
)
_PROBE_REGEX = re.compile("|".join(_PROBE_PATTERNS))

PROBE_REFUSAL_MESSAGE = (
    "Mình là trợ lý mô phỏng hỗ trợ hỏi về sức khoẻ, nên mình không chia sẻ cách mình được thiết lập hay vận hành "
    "nhé. Bạn có đang gặp vấn đề sức khoẻ nào mình có thể hỗ trợ không?"
)


def is_prompt_probe(message: str) -> bool:
    """True if ``message`` is a clear attempt to extract system instructions."""
    return bool(_PROBE_REGEX.search(fold(message)))
