"""Opt-in inference step for fact_target:resource_count, run at most once per
session by agent.py, only after every patient-answerable question has been
asked and the patient has confirmed there is nothing else to add.

fact_target:resource_count (how many distinct ED resource types -- labs,
imaging, IV fluids/medication, specialty consult, procedures -- a clinician
would likely order) drives nearly every ESI 3/4/5 atom (see
data/siu/MULTI_TURN_PROBE_FINDINGS.md), but its reporting_style is
CLINICIAN_ONLY: the patient is never asked for it, and nothing else in this
package ever sets it. protocol_atoms.jsonl now marks resource_count
non-required on the D_RESOURCE_PREDICTION atoms that need it, so an
unresolved value no longer blocks a match outright -- but it also can't
narrow an otherwise-complete case down from several adjacent candidate ESI
levels to one. This module supplies that narrowing, from the same structured
facts decision.py already trusts (never from raw patient text), so the
project's existing guarantee holds: the model supplies one more fact value,
and decision.py's ordinary matches() check still decides whether any given
atom is satisfied, contradicted, or missing -- it cannot assert an ESI level
directly. A low-confidence guess is discarded rather than recorded, so a
wrong guess at worst leaves an atom's resource_count requirement unresolved
(same as before this module existed), and never wrongly contradicts a true
match.
"""

from __future__ import annotations

import json
import logging
import os
from typing import Any

from openai import OpenAI

from .prompts import RESOURCE_COUNT_ESTIMATION_SYSTEM_PROMPT

logger = logging.getLogger(__name__)


def estimate_resource_count(
    client: OpenAI,
    *,
    concepts: list[str],
    recorded_facts: list[dict[str, Any]],
    qualitative_observations: list[dict[str, str]],
    model: str | None = None,
) -> int | None:
    payload = {
        "concepts": concepts,
        "recorded_facts": recorded_facts,
        "qualitative_observations": qualitative_observations,
    }
    model_name = model or os.getenv("DEEP_TRIAGE_MODEL", "gpt-4.1-mini")
    logger.debug(
        "RESOURCE_COUNT_ESTIMATE input (model=%s) | %s", model_name, json.dumps(payload, ensure_ascii=False)
    )
    response = client.chat.completions.create(
        model=model_name,
        temperature=0,
        response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": RESOURCE_COUNT_ESTIMATION_SYSTEM_PROMPT},
            {"role": "user", "content": json.dumps(payload, ensure_ascii=False)},
        ],
    )
    text = response.choices[0].message.content or "{}"
    logger.debug("RESOURCE_COUNT_ESTIMATE output | %r", text)
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError:
        return None
    if not isinstance(parsed, dict) or parsed.get("confident") is not True:
        return None
    value = parsed.get("resource_count")
    if isinstance(value, bool) or not isinstance(value, int) or not (0 <= value <= 10):
        return None
    return value
