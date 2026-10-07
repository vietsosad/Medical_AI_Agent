"""Phase B pre-ask check: right before the system turns a chosen
``question_target`` into an actual question, ask one small, single-purpose
LLM call -- given the WHOLE conversation so far, has the patient already,
explicitly stated an answer for this ONE specific fact somewhere? If so,
skip asking it and record the value directly.

Replaces extraction_backfill.py (removed 2026-08-29, judged not effective
enough): that module scanned a WIDE candidate pool once per turn (up to 20
fact_targets via embedding retrieval, or a whole concept's facts_for_concept
list) against the raw message in one shot. Live testing found two real
downsides to that shape specifically: (1) with many candidates in view at
once, the model repeatedly bridged an unrelated quote to the wrong
candidate (e.g. inferring mucosal_involvement_present=NO from "no facial
burn" -- two related-but-distinct topics) -- needed two rounds of
prompt/code hardening to suppress, and even then recall of the intended
target facts was inconsistent run to run; (2) it only ever checked once,
at the end of a turn, against a candidate list built by embedding rank --
a fact genuinely relevant to what's about to be asked next could still
rank too low to appear as a candidate at all.

This design removes both: one candidate at a time (the literal question the
system is about to ask, chosen by decision.py's own deterministic ranking,
never by embedding score) makes a wrong-topic bridging inference far less
likely (there's nothing else to bridge to), and it runs at the one point
that actually matters -- immediately before a question would be posed --
walked down the already-ranked askable list (agent.py's
PREASK_CHECK_LIMIT caps how many fact_targets get checked in one turn, so a
very information-dense message doesn't turn into an unbounded chain of
calls).

Keeps the same two-layer grounding this package already found necessary for
this class of check (see _quote_is_grounded/_quote_supports_candidate
below, carried over from extraction_backfill.py unchanged): a claimed value
must both (a) trace back to a real, verbatim quote from the conversation,
and (b) that quote must share real vocabulary with the specific fact_target
being checked -- not just exist anywhere in the transcript. Each accepted
value still goes through AgentToolbox.record_fact's ordinary schema
validation, so a wrong or hallucinated value still can't silently corrupt
session state.
"""

from __future__ import annotations

import json
import logging
import os
import re
from typing import Any

from openai import OpenAI

from .prompts import PREASK_CHECK_SYSTEM_PROMPT

logger = logging.getLogger(__name__)


def _normalize_for_match(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip().casefold()


def _quote_is_grounded(quote: Any, conversation: list[dict[str, str]]) -> bool:
    """Same backstop as extraction_backfill.py's version, generalised to the
    whole conversation (patient turns only) instead of one message plus a
    short recent window -- this check is allowed to look at anything the
    patient has ever said in the session, not just the last few turns."""
    if not isinstance(quote, str) or not quote.strip():
        return False
    needle = _normalize_for_match(quote)
    haystacks = [turn.get("text", "") for turn in conversation if turn.get("speaker") == "patient"]
    return any(needle in _normalize_for_match(haystack) for haystack in haystacks if haystack)


# Vietnamese function words, WITH diacritics kept -- see content_words'
# own comment (carried over verbatim from extraction_backfill.py) for why
# folding them away would be wrong here specifically ("mắt"/"mặt",
# "bỏng"/"bóng" collide once diacritics are stripped).
_VN_STOPWORDS = frozenset({
    "không", "có", "là", "và", "của", "bị", "rất", "tôi", "bạn", "mình", "em", "với",
    "cho", "đang", "đã", "sẽ", "còn", "tại", "trong", "ngoài", "này", "đó", "các",
    "khi", "lúc", "từ", "đến", "thì", "như", "mà", "rồi", "được", "bằng", "vậy",
    "qua", "vào", "hay", "hoặc", "cũng", "vẫn", "một", "những", "gì", "nào",
})


def content_words(text: str) -> set[str]:
    """Public so agent.py can reuse the exact same tokenizer when building
    the corpus-wide frequency table _quote_supports_candidate weighs
    overlap against (see that function's own docstring)."""
    words = re.findall(r"[^\W\d_]+", text, flags=re.UNICODE)
    return {w.casefold() for w in words if len(w) >= 3 and w.casefold() not in _VN_STOPWORDS}


# How common a shared word may be across the corpus's *other* fact_targets
# before it stops counting as real topical evidence -- see
# _quote_supports_candidate's own docstring for the real incident this
# threshold exists to catch. 20 fact_targets is ~8% of this corpus (238
# fact_targets total as of 2026-08-29); a word that common is a generic
# medical term, not something specific to one topic.
MAX_SHARED_WORD_CORPUS_FREQUENCY = 20


def _quote_supports_candidate(
    quote: str, fact_target: dict[str, Any], word_frequency: dict[str, int] | None = None
) -> bool:
    """Whether ``quote`` shares a real, sufficiently SPECIFIC content word
    with this fact_target's own name/lay_terms -- see
    extraction_backfill.py's retired version for the first incident (a
    burn/mucosa bridging inference) this check exists to catch. Kept even
    with a single candidate: nothing here stops the model from inventing a
    real, grounded quote that is actually about a DIFFERENT topic than the
    one fact it was asked to check.

    ``word_frequency`` (built once from the whole corpus by agent.py's
    ``_preask_word_frequency_table``, not recomputed per call) matters
    because plain "any shared word" wasn't specific enough on its own.
    Second real incident (2026-08-29, same day as the first, different
    words): given the same burn message, the model reported
    symptom_trend=CONSTANT quoting "đau rát nhẹ 1/10" ("pain described
    without mention of intermittence, implying constant" -- silence framed
    as a stated value again, the exact class of failure the grounding check
    exists to catch) -- and it passed the plain-overlap check because
    symptom_trend's own lay_terms happens to start with "đau/triệu
    chứng..." ("pain/symptom..."), and "đau" (pain) is such a generic word
    it appears in 47 of this corpus's 238 fact_targets (~20%) -- it carries
    almost no information about which *specific* topic a quote is about.
    Requiring at least one shared word below MAX_SHARED_WORD_CORPUS_FREQUENCY
    rejects this without hand-listing "đau" (or the next generic word this
    class of failure finds) as a one-off exception -- the same
    whack-a-mole pattern already found not to scale elsewhere in this
    package (see agent.py's retired confirmation-loop whitelist).
    """
    quote_words = content_words(quote)
    if not quote_words:
        return False
    candidate_text = f"{fact_target.get('name', '')} {fact_target.get('lay_terms', '')}"
    shared = quote_words & content_words(candidate_text)
    if not shared:
        return False
    if word_frequency is None:
        return True
    return any(word_frequency.get(word, 0) <= MAX_SHARED_WORD_CORPUS_FREQUENCY for word in shared)


def check_already_answered(
    client: OpenAI,
    *,
    fact_target: dict[str, Any],
    conversation: list[dict[str, str]],
    word_frequency: dict[str, int] | None = None,
    model: str | None = None,
) -> Any | None:
    """Returns the value to record if the conversation already, explicitly
    answers ``fact_target``, else ``None``. Never raises on a malformed
    model response -- ``None`` (ask the question normally) is the safe,
    common result.

    ``fact_target`` is the already-flat ``{fact_target_id, name, lay_terms,
    allowed_values}`` shape agent.py's ``_run_preask_checks`` builds once
    (not the raw corpus record, which nests allowed_values under
    value_schema) -- built there rather than here so an injected
    ``preask_checker`` stub sees the exact same shape a real call does.

    ``word_frequency``, when given, is passed straight through to
    ``_quote_supports_candidate`` -- see that function's own docstring.
    """
    if not conversation:
        return None
    payload = {"fact_target": fact_target, "conversation": conversation}
    model_name = model or os.getenv("DEEP_TRIAGE_MODEL", "gpt-4.1-mini")
    logger.debug("PREASK_CHECK input (model=%s) | %s", model_name, json.dumps(payload, ensure_ascii=False))
    response = client.chat.completions.create(
        model=model_name,
        temperature=0,
        response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": PREASK_CHECK_SYSTEM_PROMPT},
            {"role": "user", "content": json.dumps(payload, ensure_ascii=False)},
        ],
    )
    text = response.choices[0].message.content or "{}"
    logger.debug("PREASK_CHECK output | %r", text)
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError:
        return None
    if not isinstance(parsed, dict) or parsed.get("already_answered") is not True or parsed.get("confident") is not True:
        return None
    if "value" not in parsed:
        return None
    if not _quote_is_grounded(parsed.get("quote"), conversation):
        logger.debug("PREASK_CHECK discarded ungrounded value | %s", parsed)
        return None
    if not _quote_supports_candidate(parsed.get("quote"), fact_target, word_frequency):
        logger.debug("PREASK_CHECK discarded off-topic quote | %s", parsed)
        return None
    return parsed["value"]
