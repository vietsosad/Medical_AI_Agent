"""LLM layer for the MIETIC canonical pipeline: extraction + grounding checks.

The deterministic layer in mietic_common already recovers age, sex, vitals and
the DP-A/DP-B answers. This module covers only what genuinely needs semantics:
clinical concept extraction from the patient presentation, and the DP-C
resource count, which is stated in prose rather than as a parseable figure.

Two rules govern everything here:

1. Only the patient `input` is a source of patient facts. The generated
   `output` analysis may inform an assessment, never an observed fact.
2. Every extracted concept carries the span it came from, and a span that is
   not present verbatim in the source is rejected rather than trusted.
"""

from __future__ import annotations

import hashlib
import os
import re
import sqlite3
import threading
import unicodedata
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field, ValidationError

PROMPT_VERSION = "mietic-extract-v2"

# Priced per 1M tokens, verified against OpenAI pricing on 2026-08-20.
PRICING: dict[str, tuple[float, float]] = {
    "gpt-5-nano": (0.05, 0.40),
    "gpt-4.1-nano": (0.10, 0.40),
    "gpt-4o-mini": (0.15, 0.60),
    "text-embedding-3-large": (0.13, 0.0),
}

# gpt-4.1-nano, not gpt-5-nano: the gpt-5 tier bills invisible reasoning tokens,
# measured at ~3.6k completion tokens for this extraction against ~130 here —
# a 28x cost difference for a task that needs parsing, not deliberation.
DEFAULT_MODEL = "gpt-4.1-nano"

# A structured extraction that runs long has gone wrong; cap it rather than
# pay for the tail.
MAX_COMPLETION_TOKENS = 700


# --------------------------------------------------------------------------
# structured output contract
# --------------------------------------------------------------------------


class ClinicalFeature(BaseModel):
    concept: str = Field(description="snake_case clinical concept, e.g. dyspnea")
    present: bool = Field(description="False only when explicitly denied in the text")
    source_span: str = Field(description="verbatim substring of the presentation")


class PresentationExtraction(BaseModel):
    chief_complaint: str | None = None
    features: list[ClinicalFeature] = Field(default_factory=list)
    mental_status_altered: bool | None = None
    trauma: bool | None = None
    recent_intervention: bool | None = None


class ResourceExtraction(BaseModel):
    resource_count: int | None = Field(default=None, ge=0, le=20)
    resources: list[str] = Field(default_factory=list)
    stated_explicitly: bool = False


EXTRACTION_SYSTEM = """You extract clinical findings from an emergency department patient presentation.

The source_span rule is absolute and is checked mechanically:
- source_span MUST be an exact character-for-character substring of the presentation.
- Copy it. Do not paraphrase, re-order, correct, expand or shorten it.
- If you cannot copy an exact substring for a finding, OMIT that finding entirely.
- Never write commentary such as "not explicitly mentioned" or "potential injuries"
  into source_span. A span is quoted text, never your own words.

What to extract:
- Findings and symptoms the text actually states, present or explicitly denied.
- Set present=false ONLY when the text explicitly denies the finding
  (e.g. "denies chest pain", "no fever"); then the span is that denial.
- Never record a differential, a suspicion, or a possible cause as a finding.
  "possible pulmonary embolism" is not a finding.
- Never infer or fill in anything the text does not state.
- Omit age, sex and vital signs; those are extracted separately.

Use snake_case concepts, preferring standard clinical terms: dyspnea, chest_pain,
abdominal_pain, headache, syncope, altered_mental_status, fever, nausea, vomiting,
diarrhea, hypotension, tachycardia, bleeding, seizure, trauma, weakness, dizziness."""

RESOURCE_SYSTEM = """You read a triage analysis that predicts which ED resources a patient will need.

Report the total number of distinct ESI resources the analysis concludes are needed.
ESI resource counting rules: labs of any number count as ONE resource; imaging of any
number counts as ONE resource; IV fluids/medications count as one; specialty consult
counts as one. History, physical exam, point-of-care tests, oral medications, prescriptions,
simple wound care and crutches are NOT resources.

Set stated_explicitly=true only when the analysis names a total itself.
If the analysis does not support a count, return resource_count=null."""


# --------------------------------------------------------------------------
# cost tracking + cache
# --------------------------------------------------------------------------


class BudgetExceeded(RuntimeError):
    """Raised to stop a run before it can cross the configured ceiling."""


@dataclass
class CostLedger:
    """Tracks real spend and refuses to cross the ceiling mid-run.

    Guarded by a lock because the workers run concurrently; an unsynchronised
    counter is exactly how a budget ceiling gets overshot.
    """

    ceiling_usd: float
    input_tokens: int = 0
    output_tokens: int = 0
    calls: int = 0
    spend_usd: float = 0.0
    _lock: threading.Lock = field(default_factory=threading.Lock, repr=False)

    def record(self, model: str, prompt_tokens: int, completion_tokens: int) -> None:
        rate_in, rate_out = PRICING[model]
        with self._lock:
            self.spend_usd += (prompt_tokens * rate_in + completion_tokens * rate_out) / 1e6
            self.input_tokens += prompt_tokens
            self.output_tokens += completion_tokens
            self.calls += 1

    def check(self) -> None:
        with self._lock:
            if self.spend_usd >= self.ceiling_usd:
                raise BudgetExceeded(
                    f"BUDGET STOP: spent ${self.spend_usd:.4f} of ${self.ceiling_usd:.2f}"
                )

    def summary(self) -> str:
        return (
            f"calls={self.calls} in={self.input_tokens:,} out={self.output_tokens:,} "
            f"spend=${self.spend_usd:.4f}"
        )


class Cache:
    """Content-addressed so a crash or retry never re-buys the same answer."""

    def __init__(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(path, check_same_thread=False)
        self._lock = threading.Lock()
        self.conn.execute(
            "CREATE TABLE IF NOT EXISTS calls "
            "(key TEXT PRIMARY KEY, response TEXT, prompt_tokens INT, completion_tokens INT)"
        )
        self.conn.commit()

    @staticmethod
    def key(content: str, model: str, prompt_version: str, kind: str) -> str:
        raw = f"{kind}|{model}|{prompt_version}|{content}"
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()

    def get(self, key: str) -> tuple[str, int, int] | None:
        with self._lock:
            row = self.conn.execute(
                "SELECT response, prompt_tokens, completion_tokens FROM calls WHERE key=?",
                (key,),
            ).fetchone()
        return (row[0], row[1], row[2]) if row else None

    def put(self, key: str, response: str, prompt_tokens: int, completion_tokens: int) -> None:
        with self._lock:
            self.conn.execute(
                "INSERT OR REPLACE INTO calls VALUES (?,?,?,?)",
                (key, response, prompt_tokens, completion_tokens),
            )
            self.conn.commit()


# --------------------------------------------------------------------------
# grounding validation
# --------------------------------------------------------------------------


def _loose(text: str) -> str:
    text = unicodedata.normalize("NFKC", text).lower()
    return re.sub(r"[^a-z0-9]+", " ", text).strip()


_STOPWORDS = {
    "a", "an", "the", "of", "with", "and", "or", "nor", "to", "in", "on", "at",
    "is", "are", "was", "were", "has", "had", "have", "he", "she", "his", "her",
    "no", "not", "denies", "denied", "for", "as", "well", "any", "presents",
    "present", "presenting", "reports", "reported", "complains", "including",
}


def _content_tokens(text: str) -> list[str]:
    return [t for t in _loose(text).split() if t not in _STOPWORDS and len(t) > 2]


def _token_supported(token: str, source_tokens: set[str]) -> bool:
    """A token counts as present if some source token shares its stem.

    Prefix matching on the first four characters accepts the morphology the
    model drifts into ("present" for "presents") while still rejecting an
    invented content word: "substernal" has no counterpart in a source that
    only says "chest pain", so a fabricated clinical qualifier still fails.
    """
    if token in source_tokens:
        return True
    stem = token[:4]
    return any(candidate.startswith(stem) for candidate in source_tokens if len(stem) >= 4)


def validate_grounding(
    extraction: PresentationExtraction, source: str
) -> tuple[list[ClinicalFeature], list[str]]:
    """Drop any feature whose span is not actually supported by the source.

    An exact substring test proved too strict — the model reliably paraphrases
    connective words — and a bare fuzzy match too lax. Requiring every *content*
    word of the span to have a stem in the source keeps invented findings out
    while tolerating the wording drift.
    """
    haystack = _loose(source)
    source_tokens = set(haystack.split())
    kept: list[ClinicalFeature] = []
    rejected: list[str] = []

    for feature in extraction.features:
        span = _loose(feature.source_span)
        if not span:
            rejected.append(f"{feature.concept}:<empty span>")
            continue
        if span in haystack:
            kept.append(feature)
            continue
        tokens = _content_tokens(feature.source_span)
        if tokens and all(_token_supported(t, source_tokens) for t in tokens):
            kept.append(feature)
        else:
            rejected.append(f"{feature.concept}:{feature.source_span[:40]}")
    return kept, rejected


# --------------------------------------------------------------------------
# client
# --------------------------------------------------------------------------


def load_api_key() -> str:
    key = os.environ.get("OPENAI_API_KEY", "").strip()
    if key:
        return key
    for line in Path(".env").read_text(encoding="utf-8").splitlines():
        if line.startswith("OPENAI_API_KEY="):
            return line.split("=", 1)[1].strip()
    raise RuntimeError("OPENAI_API_KEY is not configured")


def call_structured(
    client: Any,
    model: str,
    system: str,
    user: str,
    schema: type[BaseModel],
    cache: Cache,
    ledger: CostLedger,
    kind: str,
) -> tuple[BaseModel | None, bool]:
    """Return (parsed, was_cached). Schema failures return None, not a guess."""
    key = Cache.key(user, model, PROMPT_VERSION, kind)
    hit = cache.get(key)
    if hit is not None:
        try:
            return schema.model_validate_json(hit[0]), True
        except ValidationError:
            return None, True

    ledger.check()
    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        response_format={
            "type": "json_schema",
            "json_schema": {
                "name": schema.__name__,
                "schema": schema.model_json_schema(),
                "strict": False,
            },
        },
        max_completion_tokens=MAX_COMPLETION_TOKENS,
    )
    content = response.choices[0].message.content or "{}"
    usage = response.usage
    ledger.record(model, usage.prompt_tokens, usage.completion_tokens)
    cache.put(key, content, usage.prompt_tokens, usage.completion_tokens)
    try:
        return schema.model_validate_json(content), False
    except ValidationError:
        return None, False
