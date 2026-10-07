"""Regression tests for credentials that can appear in operational logs."""

from __future__ import annotations

import logging

from src.services.log_redaction import (
    SensitiveQueryRedactionFilter,
    redact_url_query_secrets,
)


def test_redact_url_query_secrets_preserves_non_secret_parameters() -> None:
    url = "/api/v1/ws/case/123?topic=triage&token=header.payload.signature&lang=vi"

    assert redact_url_query_secrets(url) == (
        "/api/v1/ws/case/123?topic=triage&token=***&lang=vi"
    )


def test_uvicorn_websocket_tuple_arguments_are_redacted() -> None:
    record = logging.LogRecord(
        name="uvicorn.error",
        level=logging.INFO,
        pathname=__file__,
        lineno=1,
        msg='%s - "WebSocket %s" [accepted]',
        args=(
            "127.0.0.1:12345",
            "/api/v1/ws/simple-patient?token=secret-jwt&channel=patient",
        ),
        exc_info=None,
    )

    assert SensitiveQueryRedactionFilter().filter(record) is True
    rendered = record.getMessage()
    assert "secret-jwt" not in rendered
    assert "token=***" in rendered
    assert "channel=patient" in rendered


def test_mapping_arguments_mask_direct_token_values_and_urls() -> None:
    record = logging.LogRecord(
        name="app.audit",
        level=logging.INFO,
        pathname=__file__,
        lineno=1,
        msg="request=%(url)s token=%(token)s",
        args={
            "url": "/socket?id_token=id-secret&topic=queue",
            "token": "direct-secret",
        },
        exc_info=None,
    )

    SensitiveQueryRedactionFilter().filter(record)
    rendered = record.getMessage()
    assert "id-secret" not in rendered
    assert "direct-secret" not in rendered
    assert "id_token=***" in rendered
    assert "token=***" in rendered
