"""LangSmith observability for the active ``simple_agent`` runtime.

Tracing is deliberately scoped to simple-agent turns instead of being enabled
globally for every LangChain call in the process.  Clinical message content is
hidden by default; operators may explicitly opt in to redacted content for a
controlled development workspace.

LangSmith is observability only.  A tracing setup or delivery failure must
never change the patient-visible result, session state, or database audit
trail.
"""

from __future__ import annotations

import hashlib
import logging
import os
import re
from collections.abc import Iterator, Mapping
from contextlib import contextmanager
from functools import lru_cache
from typing import Any

from langsmith import Client, tracing_context
from langsmith.run_helpers import trace
from langsmith.run_trees import RunTree
from langsmith.wrappers import wrap_openai

logger = logging.getLogger(__name__)

_SAFE_PAYLOAD_MARKER = "__simple_agent_trace_safe__"
_TRUE_VALUES = {"1", "true", "yes", "on"}

_EMAIL_RE = re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.IGNORECASE)
_PHONE_RE = re.compile(r"(?<!\d)(?:\+?84|0)(?:[ .-]?\d){9,10}(?!\d)")
_SESSION_HASH_RE = re.compile(r"[0-9a-f]{16}", re.IGNORECASE)
_UUID_RE = re.compile(
    r"\b[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}\b",
    re.IGNORECASE,
)
_SECRET_RE = re.compile(r"\b(?:sk|lsv2|ls)-[A-Za-z0-9_-]{12,}\b")
_BEARER_RE = re.compile(r"\bBearer\s+[A-Za-z0-9._~+/=-]+", re.IGNORECASE)
_SENSITIVE_METADATA_PARTS = (
    "authorization",
    "email",
    "patient_id",
    "phone",
    "session_id",
    "token",
    "user_id",
)


def _is_true(value: str | None) -> bool:
    return str(value or "").strip().casefold() in _TRUE_VALUES


def tracing_requested() -> bool:
    """Whether simple-agent tracing was explicitly requested.

    The simple-agent flag takes precedence and permits selective tracing while
    ``LANGSMITH_TRACING`` remains false for legacy runtimes in the same process.
    Legacy ``LANGCHAIN_*`` names remain readable for existing deployments.
    """

    scoped = os.getenv("SIMPLE_AGENT_LANGSMITH_ENABLED")
    if scoped is not None:
        return _is_true(scoped)
    return _is_true(
        os.getenv("LANGSMITH_TRACING")
        or os.getenv("LANGSMITH_TRACING_V2")
        or os.getenv("LANGCHAIN_TRACING_V2")
    )


def trace_content_enabled() -> bool:
    """Return true only for the explicit, development-only content opt-in."""

    return _is_true(os.getenv("SIMPLE_AGENT_LANGSMITH_TRACE_CONTENT"))


def _api_key() -> str:
    return (
        os.getenv("LANGSMITH_API_KEY")
        or os.getenv("LANGCHAIN_API_KEY")
        or ""
    ).strip()


def _project_name() -> str:
    return (
        os.getenv("LANGSMITH_PROJECT")
        or os.getenv("LANGCHAIN_PROJECT")
        or "medtriage-simple-agent"
    ).strip()


def tracing_ready() -> bool:
    """Tracing must never activate accidentally without an explicit API key."""

    return tracing_requested() and bool(_api_key())


def hash_identifier(value: str) -> str:
    """Stable pseudonym for trace correlation without sending a raw identifier."""

    return hashlib.sha256(value.encode("utf-8")).hexdigest()[:16]


def _redact_text(value: str) -> str:
    redacted = _BEARER_RE.sub("<redacted-bearer-token>", value)
    redacted = _SECRET_RE.sub("<redacted-secret>", redacted)
    redacted = _EMAIL_RE.sub("<redacted-email>", redacted)
    redacted = _PHONE_RE.sub("<redacted-phone>", redacted)
    return _UUID_RE.sub("<redacted-uuid>", redacted)


def _redact_nested(value: Any, *, depth: int = 0) -> Any:
    if depth >= 12:
        return "<redacted-max-depth>"
    if isinstance(value, str):
        return _redact_text(value)
    if isinstance(value, Mapping):
        return {
            str(key): _redact_nested(item, depth=depth + 1)
            for key, item in value.items()
        }
    if isinstance(value, tuple):
        return [_redact_nested(item, depth=depth + 1) for item in value]
    if isinstance(value, list):
        return [_redact_nested(item, depth=depth + 1) for item in value]
    return value


def safe_trace_payload(payload: Mapping[str, Any]) -> dict[str, Any]:
    """Mark an operational, non-free-text payload as safe for the trace UI."""

    return {_SAFE_PAYLOAD_MARKER: True, **dict(payload)}


def _process_trace_payload(payload: dict[str, Any]) -> dict[str, Any]:
    """Hide nested clinical content unless an operator explicitly opted in."""

    if not isinstance(payload, dict):
        return {}
    is_safe = payload.get(_SAFE_PAYLOAD_MARKER) is True
    if not is_safe and not trace_content_enabled():
        return {}
    visible = {key: value for key, value in payload.items() if key != _SAFE_PAYLOAD_MARKER}
    return _redact_nested(visible)


def _process_trace_metadata(metadata: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(metadata, dict):
        return {}
    filtered: dict[str, Any] = {}
    for key, value in metadata.items():
        normalized_key = str(key).casefold()
        if normalized_key == "session_hash" and isinstance(value, str):
            filtered[str(key)] = (
                value if _SESSION_HASH_RE.fullmatch(value) else "<redacted-metadata>"
            )
        elif any(part in normalized_key for part in _SENSITIVE_METADATA_PARTS):
            filtered[str(key)] = "<redacted-metadata>"
        else:
            filtered[str(key)] = _redact_nested(value)
    return filtered


@lru_cache(maxsize=1)
def get_trace_client() -> Client | None:
    """Build the privacy-filtering client lazily when tracing is usable."""

    if not tracing_ready():
        return None
    try:
        return Client(
            api_key=_api_key(),
            hide_inputs=_process_trace_payload,
            hide_outputs=_process_trace_payload,
            hide_metadata=_process_trace_metadata,
        )
    except Exception as exc:  # pragma: no cover - defensive SDK setup boundary
        logger.warning("LangSmith tracing disabled after client setup failed: %s", type(exc).__name__)
        return None


@contextmanager
def simple_agent_tracing_context(
    session_id: str,
    *,
    restored: bool,
) -> Iterator[None]:
    """Scope native LangGraph and wrapped-OpenAI traces to one simple turn."""

    client = get_trace_client()
    if client is None:
        # Explicitly suppress a globally enabled tracer when the simple-agent
        # integration has no usable credentials or was scoped off.
        with tracing_context(enabled=False):
            yield
        return

    metadata = {
        "runtime": "simple_agent",
        "session_hash": hash_identifier(session_id),
        "restored_from_postgres": restored,
        "model": os.getenv("DEEP_TRIAGE_MODEL", "gpt-4.1-mini"),
        "clinical_content_enabled": trace_content_enabled(),
    }
    with tracing_context(
        enabled=True,
        client=client,
        project_name=_project_name(),
        tags=["simple-agent", "clinical-triage"],
        metadata=metadata,
    ):
        yield


@contextmanager
def trace_span(
    name: str,
    *,
    inputs: Mapping[str, Any],
    run_type: str = "chain",
    metadata: Mapping[str, Any] | None = None,
) -> Iterator[RunTree | None]:
    """Create a child span without letting SDK setup failures affect care."""

    client = get_trace_client()
    if client is None:
        yield None
        return

    manager = trace(
        name,
        run_type=run_type,
        inputs=safe_trace_payload(inputs),
        metadata=dict(metadata or {}),
        client=client,
    )
    try:
        run = manager.__enter__()
    except Exception as exc:  # pragma: no cover - defensive SDK setup boundary
        logger.warning("LangSmith span %s was skipped: %s", name, type(exc).__name__)
        yield None
        return

    try:
        yield run
    except BaseException as exc:
        try:
            manager.__exit__(type(exc), exc, exc.__traceback__)
        except Exception as trace_exc:  # pragma: no cover - background SDK boundary
            logger.warning("LangSmith span %s failed to close: %s", name, type(trace_exc).__name__)
        raise
    else:
        try:
            manager.__exit__(None, None, None)
        except Exception as exc:  # pragma: no cover - background SDK boundary
            logger.warning("LangSmith span %s failed to close: %s", name, type(exc).__name__)


def finish_trace_span(
    run: RunTree | None,
    outputs: Mapping[str, Any],
    *,
    usage_metadata: Mapping[str, Any] | None = None,
) -> None:
    if run is None:
        return
    try:
        metadata = (
            {"usage_metadata": dict(usage_metadata)}
            if usage_metadata
            else None
        )
        run.end(
            outputs=safe_trace_payload(outputs),
            metadata=metadata,
        )
    except Exception as exc:  # pragma: no cover - background SDK boundary
        logger.warning("LangSmith span output was dropped: %s", type(exc).__name__)


def wrap_simple_agent_openai(client: Any) -> Any:
    """Trace raw OpenAI SDK calls as children of the current turn."""

    trace_client = get_trace_client()
    if trace_client is None:
        return client
    try:
        return wrap_openai(
            client,
            tracing_extra={
                "client": trace_client,
                "tags": ["simple-agent", "openai"],
                "metadata": {"runtime": "simple_agent"},
            },
        )
    except Exception as exc:  # pragma: no cover - defensive SDK setup boundary
        logger.warning("OpenAI LangSmith wrapper disabled: %s", type(exc).__name__)
        return client


def summarize_turn_result(result: Mapping[str, Any]) -> dict[str, Any]:
    """Operational output safe enough to retain when clinical content is hidden."""

    decision = result.get("decision") if isinstance(result, Mapping) else None
    decision = decision if isinstance(decision, Mapping) else {}
    tool_calls = decision.get("tool_calls")
    return {
        "route": decision.get("route"),
        "action": decision.get("action"),
        "response_length": len(str(result.get("message") or "")),
        "retrieved_protocol_atom_count": int(decision.get("retrieved_protocol_atoms") or 0),
        "supported_protocol_atom_count": int(decision.get("supported_protocol_atoms") or 0),
        "unresolved_requirement_count": int(decision.get("unresolved_protocol_requirements") or 0),
        "tool_call_count": len(tool_calls) if isinstance(tool_calls, list) else 0,
        "has_question_target": bool(decision.get("question_target_id")),
        "has_esi_match": bool(decision.get("matched_esi_levels")),
    }
