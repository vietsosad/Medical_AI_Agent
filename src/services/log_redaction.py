"""Redaction helpers for operational console logs.

These helpers exist for the *diagnostic* log stream only. The structured
clinical audit trail (``audit_logs``) is a separate, deliberate record and is
never routed through here: it is supposed to hold identifiers, before/after
state and clinical justification, because that is what makes a clinical
decision reviewable afterwards.

Operational logs are different. They are read by whoever is watching a
terminal, shipped to wherever stdout goes, and kept for far longer than anyone
intends. A patient's name, an email address or a one-time passcode in that
stream is a disclosure with no matching benefit, because the thing an operator
actually needs is *which* user or session an event belongs to, not *who* they
are.

So identifiers are replaced by a stable pseudonym. The same user yields the
same token for the lifetime of a deployment, which keeps a log readable and
correlatable across lines, while the token itself does not reveal the person.
The salt is the deployment's JWT secret, so pseudonyms are not comparable
across deployments and cannot be reversed with a dictionary of common emails.
"""

from __future__ import annotations

import hashlib
import logging
import re
from collections.abc import Mapping
from typing import Any

_MASK = "***"
_SENSITIVE_QUERY_KEYS = frozenset(
    {"access_token", "id_token", "refresh_token", "token"}
)
_SENSITIVE_QUERY_RE = re.compile(
    r"(^|[?&])(?P<key>access_token|id_token|refresh_token|token)="
    r"(?P<value>[^&#\s\"']+)",
    re.IGNORECASE,
)


def _salt() -> str:
    # Imported lazily: config reads the environment, and log redaction must not
    # force settings to resolve at module-import time.
    from src.config import get_settings

    return get_settings().jwt_secret_key


def pseudonym(value: Any, *, prefix: str = "id") -> str:
    """A stable, non-reversible token standing in for one identifier.

    Correlation is the whole point: two log lines about the same user must be
    recognisably about the same user, without either line naming them.
    """
    text = str(value or "").strip()
    if not text:
        return f"{prefix}:anon"
    digest = hashlib.sha256(f"{_salt()}|{text}".encode()).hexdigest()[:12]
    return f"{prefix}:{digest}"


def mask_email(email: Any) -> str:
    """Keep the domain, drop the person.

    The domain is often the operationally interesting part -- a bounce or a
    delivery failure is usually a property of the provider, not the mailbox --
    while the local part is the identifying half.
    """
    text = str(email or "").strip()
    if not text:
        return _MASK
    if "@" not in text:
        return pseudonym(text, prefix="addr")
    local, _, domain = text.partition("@")
    head = local[:1] if local else ""
    return f"{head}{_MASK}@{domain}"


def mask_name(name: Any) -> str:
    """Reduce a personal name to a non-identifying initial."""
    text = str(name or "").strip()
    if not text:
        return _MASK
    return f"{text[:1]}{_MASK}"


def coarse_location(latitude: Any, longitude: Any) -> str:
    """Reduce a precise fix to a grid cell far too coarse to identify anyone.

    The nearby-facility lookup receives a live GPS position. An operator
    debugging that endpoint needs to know roughly *where* traffic is coming
    from -- whether a provider outage is regional, whether a result set is
    empty because the caller is outside the seeded directory's coverage. They
    never need the street the patient is standing on.

    One decimal place is about 11km at Vietnamese latitudes: enough to tell
    Ha Noi from Da Nang, not enough to tell a house from its neighbourhood.
    Anything that cannot be parsed as a coordinate is masked outright rather
    than echoed, so a malformed payload cannot smuggle a precise fix through.
    """
    try:
        return f"grid:{float(latitude):.1f},{float(longitude):.1f}"
    except (TypeError, ValueError):
        return _MASK


def redact_secret(_value: Any = None) -> str:
    """For anything that authenticates: never partially revealed."""
    return _MASK


def redact_url_query_secrets(value: str) -> str:
    """Mask authentication values embedded in a URL query string.

    Browser WebSocket clients cannot set an ``Authorization`` header, so a
    query-token fallback is sometimes unavoidable. Uvicorn includes the full
    WebSocket target in its access/error logs; sanitize that target before it
    reaches stdout, a log shipper, or long-term storage.
    """

    return _SENSITIVE_QUERY_RE.sub(
        lambda match: f"{match.group(1)}{match.group('key')}={_MASK}",
        value,
    )


def _redact_log_value(value: Any) -> Any:
    if isinstance(value, str):
        return redact_url_query_secrets(value)
    if isinstance(value, Mapping):
        return {
            key: (
                _MASK
                if str(key).casefold() in _SENSITIVE_QUERY_KEYS
                else _redact_log_value(item)
            )
            for key, item in value.items()
        }
    if isinstance(value, tuple):
        return tuple(_redact_log_value(item) for item in value)
    if isinstance(value, list):
        return [_redact_log_value(item) for item in value]
    return value


class SensitiveQueryRedactionFilter(logging.Filter):
    """Remove query-string credentials from structured and formatted logs."""

    _medtriage_sensitive_query_filter = True

    def filter(self, record: logging.LogRecord) -> bool:
        record.msg = _redact_log_value(record.msg)
        record.args = _redact_log_value(record.args)
        return True


def install_uvicorn_log_redaction() -> None:
    """Install the token filter once on Uvicorn loggers and handlers.

    ``uvicorn.error`` owns WebSocket handshake messages while
    ``uvicorn.access`` owns normal HTTP request lines. Handler installation
    also covers child loggers, since logger filters are not inherited.
    """

    for logger_name in ("uvicorn.access", "uvicorn.error"):
        logger = logging.getLogger(logger_name)
        targets: list[logging.Filterer] = [logger, *logger.handlers]
        for target in targets:
            if any(
                getattr(existing, "_medtriage_sensitive_query_filter", False)
                for existing in target.filters
            ):
                continue
            target.addFilter(SensitiveQueryRedactionFilter())
