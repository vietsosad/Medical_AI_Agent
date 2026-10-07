"""The OAuth callback must return to the origin the patient started from.

Reported as "Google login is broken". The backend was fine -- it reached Google
and got a well-formed response. The failure was quieter: ``redirect_uri`` was a
fixed setting pointing at ``localhost:3000``, so a patient browsing
``127.0.0.1:3000`` was sent to Google, authenticated successfully, and returned
to a *different origin*. The token landed in localStorage for an origin they
were not looking at, and the tab they came from stayed logged out.

The origin now follows the request -- but only after being checked against the
allowlist. ``redirect_uri`` is where an authorization code gets delivered, so an
attacker who could set it would be redirecting other people's codes to
themselves. That check is the security-critical half of this change and most of
what is asserted below.
"""

from __future__ import annotations

import pytest

from src.config import get_settings
from src.services.oauth_service import resolve_oauth_redirect_uri

ALLOWED = "http://127.0.0.1:3000"
ALSO_ALLOWED = "http://localhost:3000"


@pytest.fixture(autouse=True)
def allowlist(monkeypatch: pytest.MonkeyPatch):
    """Pin the allowlist these tests reason about, instead of reading the machine's ``.env``.

    ``oauth_service`` resolves ``get_settings()`` once at import time and keeps
    the result in a module-level ``settings``, so the allowlist a test sees is
    whatever ``CORS_ORIGINS`` happened to say on the developer's box. That made
    four of these tests fail on any checkout whose ``.env`` omits the loopback
    origin -- a red suite that says nothing about the code under test.

    What is being verified here is the *resolution rule*: a listed origin is
    honoured, anything else falls back. That rule has to hold for whatever the
    allowlist contains, so the allowlist belongs to the test.
    """
    from src.services import oauth_service

    pinned = get_settings().model_copy(
        update={"cors_origins": f"{ALSO_ALLOWED},{ALLOWED}"}
    )
    monkeypatch.setattr(oauth_service, "settings", pinned)
    return pinned


def _configured(provider: str) -> str:
    settings = get_settings()
    return (
        settings.google_redirect_uri
        if provider == "google"
        else settings.github_redirect_uri
    )


# --------------------------------------------------------------------------
# An allowed origin is honoured
# --------------------------------------------------------------------------

@pytest.mark.parametrize("provider", ["google", "github"])
def test_an_allowed_origin_gets_its_own_callback(provider: str) -> None:
    resolved = resolve_oauth_redirect_uri(ALLOWED, provider)

    assert resolved == f"{ALLOWED}/auth/callback/{provider}"


def test_the_two_local_origins_are_kept_distinct() -> None:
    """127.0.0.1 and localhost are different origins to every browser."""
    loopback = resolve_oauth_redirect_uri(ALLOWED, "google")
    named = resolve_oauth_redirect_uri(ALSO_ALLOWED, "google")

    assert loopback != named
    assert loopback.startswith(ALLOWED)
    assert named.startswith(ALSO_ALLOWED)


def test_a_trailing_slash_does_not_produce_a_double_slash() -> None:
    resolved = resolve_oauth_redirect_uri(f"{ALLOWED}/", "google")

    assert resolved == f"{ALLOWED}/auth/callback/google"
    assert "//auth" not in resolved


# --------------------------------------------------------------------------
# Anything else falls back -- this is the security control
# --------------------------------------------------------------------------

@pytest.mark.parametrize(
    "hostile",
    [
        "https://evil.example",
        "http://127.0.0.1:3000.evil.example",
        "http://localhost:3000@evil.example",
        "http://127.0.0.1:9999",
        "http://127.0.0.1",
        "javascript:alert(1)",
        "//evil.example",
        "",
        "   ",
    ],
)
def test_an_unlisted_origin_is_refused(hostile: str) -> None:
    """An authorization code must never be steered to an unlisted host."""
    resolved = resolve_oauth_redirect_uri(hostile, "google")

    assert resolved == _configured("google")
    assert "evil" not in resolved
    assert "javascript" not in resolved


def test_a_missing_origin_falls_back() -> None:
    assert resolve_oauth_redirect_uri(None, "google") == _configured("google")


@pytest.mark.parametrize("provider", ["google", "github"])
def test_the_fallback_is_the_configured_value(provider: str) -> None:
    assert resolve_oauth_redirect_uri("https://evil.example", provider) == _configured(
        provider
    )


def test_the_allowlist_is_the_cors_allowlist(allowlist) -> None:
    """One list of legitimate origins, not two that can drift apart.

    Reads ``cors_origins`` off the same settings object the module itself uses,
    so the assertion stays about "these two lists are the same list" rather
    than about what one machine's environment happens to hold.
    """
    from src.services.oauth_service import _allowed_origins

    configured = {
        item.strip().rstrip("/")
        for item in allowlist.cors_origins.split(",")
        if item.strip()
    }
    assert _allowed_origins() == configured


# --------------------------------------------------------------------------
# The same URI must be used at both steps
# --------------------------------------------------------------------------

def test_both_oauth_steps_accept_the_same_redirect_uri() -> None:
    """Google rejects the exchange if the two differ, so both must take it."""
    import inspect

    from src.services import oauth_service

    for name in (
        "get_google_authorization_url",
        "authenticate_with_google",
        "get_github_authorization_url",
        "authenticate_with_github",
    ):
        signature = inspect.signature(getattr(oauth_service, name))
        assert "redirect_uri" in signature.parameters, name


def test_the_authorization_url_carries_the_resolved_uri() -> None:
    import urllib.parse

    from src.services.oauth_service import get_google_authorization_url

    resolved = resolve_oauth_redirect_uri(ALLOWED, "google")
    url = get_google_authorization_url(resolved)
    query = urllib.parse.parse_qs(urllib.parse.urlparse(url).query)

    assert query["redirect_uri"] == [resolved]
    assert query["client_id"], "client id must still be sent"


def test_omitting_the_uri_keeps_the_configured_default() -> None:
    """Callers that do not care must behave exactly as before."""
    import urllib.parse

    from src.services.oauth_service import get_google_authorization_url

    url = get_google_authorization_url()
    query = urllib.parse.parse_qs(urllib.parse.urlparse(url).query)

    assert query["redirect_uri"] == [_configured("google")]
