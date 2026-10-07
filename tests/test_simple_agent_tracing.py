"""Privacy and configuration tests for Simple Agent LangSmith tracing."""

from __future__ import annotations

import pytest
from langsmith.utils import tracing_is_enabled

from src.simple_agent import tracing


_TRACE_ENV_VARS = (
    "LANGCHAIN_API_KEY",
    "LANGCHAIN_PROJECT",
    "LANGCHAIN_TRACING_V2",
    "LANGSMITH_API_KEY",
    "LANGSMITH_PROJECT",
    "LANGSMITH_TRACING",
    "LANGSMITH_TRACING_V2",
    "SIMPLE_AGENT_LANGSMITH_ENABLED",
    "SIMPLE_AGENT_LANGSMITH_TRACE_CONTENT",
)


@pytest.fixture(autouse=True)
def _clean_trace_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    for name in _TRACE_ENV_VARS:
        monkeypatch.delenv(name, raising=False)
    tracing.get_trace_client.cache_clear()
    yield
    tracing.get_trace_client.cache_clear()


def test_scoped_flag_takes_precedence_over_global_legacy_flag(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("LANGCHAIN_TRACING_V2", "true")
    monkeypatch.setenv("SIMPLE_AGENT_LANGSMITH_ENABLED", "false")

    assert tracing.tracing_requested() is False

    monkeypatch.setenv("SIMPLE_AGENT_LANGSMITH_ENABLED", "true")
    assert tracing.tracing_requested() is True


def test_tracing_requires_an_explicit_api_key(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("SIMPLE_AGENT_LANGSMITH_ENABLED", "true")
    assert tracing.tracing_ready() is False

    monkeypatch.setenv("LANGSMITH_API_KEY", "ls-test-workspace-key")
    assert tracing.tracing_ready() is True


def test_default_filter_hides_clinical_content_but_keeps_safe_metrics() -> None:
    raw = {"message": "Tôi đau ngực", "session_snapshot": {"facts": {"temperature": 39}}}
    assert tracing._process_trace_payload(raw) == {}

    safe = tracing.safe_trace_payload(
        {
            "route": "TRIAGE",
            "action": "ASK_NEXT",
            "contact": "demo.patient@example.com / 0987654321",
        }
    )
    assert tracing._process_trace_payload(safe) == {
        "route": "TRIAGE",
        "action": "ASK_NEXT",
        "contact": "<redacted-email> / <redacted-phone>",
    }


def test_content_opt_in_still_redacts_common_identifiers(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("SIMPLE_AGENT_LANGSMITH_TRACE_CONTENT", "true")
    payload = {
        "message": "Liên hệ demo.patient@example.com hoặc 0987654321",
        "session_id": "550e8400-e29b-41d4-a716-446655440000",
        "authorization": "Bearer abc.def.ghi",
    }

    assert tracing._process_trace_payload(payload) == {
        "message": "Liên hệ <redacted-email> hoặc <redacted-phone>",
        "session_id": "<redacted-uuid>",
        "authorization": "<redacted-bearer-token>",
    }


def test_metadata_filter_keeps_hash_but_drops_raw_identifiers() -> None:
    filtered = tracing._process_trace_metadata(
        {
            "runtime": "simple_agent",
            "session_hash": "0123456789abcdef",
            "session_id": "raw-session-id",
            "patient_id": "raw-patient-id",
        }
    )

    assert filtered == {
        "runtime": "simple_agent",
        "session_hash": "0123456789abcdef",
        "session_id": "<redacted-metadata>",
        "patient_id": "<redacted-metadata>",
    }


def test_turn_summary_excludes_messages_facts_and_protocol_content() -> None:
    result = {
        "message": "Nội dung trả lời nhạy cảm",
        "decision": {
            "route": "TRIAGE",
            "action": "RETURN_MATCH",
            "concepts": ["concept:chest_pain"],
            "retrieved_protocol_atoms": 7,
            "supported_protocol_atoms": 1,
            "unresolved_protocol_requirements": 0,
            "question_target_id": None,
            "matched_esi_levels": [2],
            "matched_atoms": [{"criteria_text": "sensitive criterion"}],
            "tool_calls": [{"tool": "record_fact"}],
        },
    }

    summary = tracing.summarize_turn_result(result)

    assert summary == {
        "route": "TRIAGE",
        "action": "RETURN_MATCH",
        "response_length": len(result["message"]),
        "retrieved_protocol_atom_count": 7,
        "supported_protocol_atom_count": 1,
        "unresolved_requirement_count": 0,
        "tool_call_count": 1,
        "has_question_target": False,
        "has_esi_match": True,
    }
    assert "message" not in summary
    assert "concepts" not in summary
    assert "matched_atoms" not in summary


def test_missing_key_suppresses_global_tracing_for_simple_turn(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("LANGSMITH_TRACING", "true")
    monkeypatch.setenv("SIMPLE_AGENT_LANGSMITH_ENABLED", "true")

    with tracing.simple_agent_tracing_context("session-123", restored=False):
        assert tracing_is_enabled() is False


def test_openai_client_is_unchanged_when_tracing_is_disabled() -> None:
    client = object()
    assert tracing.wrap_simple_agent_openai(client) is client


def test_identifier_hash_is_stable_and_not_the_raw_value() -> None:
    first = tracing.hash_identifier("session-123")
    second = tracing.hash_identifier("session-123")

    assert first == second
    assert first != "session-123"
    assert len(first) == 16


def test_finish_span_records_usage_as_metadata_without_assigning_sdk_fields() -> None:
    class FakeRun:
        def __init__(self) -> None:
            self.end_kwargs: dict = {}

        def end(self, **kwargs) -> None:
            self.end_kwargs = kwargs

    run = FakeRun()
    tracing.finish_trace_span(
        run,
        {"dimensions": 1536},
        usage_metadata={"input_tokens": 12, "total_tokens": 12},
    )

    assert run.end_kwargs == {
        "outputs": tracing.safe_trace_payload({"dimensions": 1536}),
        "metadata": {
            "usage_metadata": {"input_tokens": 12, "total_tokens": 12},
        },
    }
