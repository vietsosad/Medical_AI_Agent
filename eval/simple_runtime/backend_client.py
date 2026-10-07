from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any

import httpx

from .schemas import GoldenCase


TERMINAL_ACTIONS = {"RETURN_MATCH", "RETURN_INCOMPLETE", "REFUSE"}


@dataclass
class RuntimeResult:
    session_id: str | None
    profile_id: str
    responses: list[dict[str, Any]]
    session: dict[str, Any]
    latency_ms: float
    error: str | None = None


class SimpleAgentBackendClient:
    def __init__(self, *, base_url: str, token: str, timeout_seconds: float = 90) -> None:
        self.client = httpx.Client(base_url=base_url.rstrip("/"), headers={"Authorization": f"Bearer {token}"}, timeout=timeout_seconds)

    def close(self) -> None:
        self.client.close()

    def healthcheck(self) -> None:
        self.client.get("/health").raise_for_status()

    def _request_with_retry(self, method: str, url: str, **kwargs: Any) -> httpx.Response:
        last_exc: Exception | None = None
        for attempt in range(1, 6):
            try:
                response = self.client.request(method, url, **kwargs)
                response.raise_for_status()
                return response
            except (httpx.HTTPStatusError, httpx.RequestError) as exc:
                last_exc = exc
                retryable_status = (
                    isinstance(exc, httpx.HTTPStatusError)
                    and exc.response.status_code in {429, 500, 502, 503, 504}
                )
                if attempt == 5 or (isinstance(exc, httpx.HTTPStatusError) and not retryable_status):
                    raise
                time.sleep(12.0)
        raise RuntimeError(f"request failed without response: {last_exc}")

    def run_case(self, case: GoldenCase, profile_id: str) -> RuntimeResult:
        started = time.perf_counter()
        responses: list[dict[str, Any]] = []
        session_id: str | None = None
        try:
            response = self._request_with_retry(
                "POST",
                "/api/v1/simple-triage/start",
                json={"message": case.presentation["initial_message"], "profile_id": profile_id},
            )
            current = response.json()
            responses.append(current)
            session_id = str(current["session_id"])
            answers = case.adaptive_dialogue.get("answers_by_fact_target") or {}
            max_turns = int(case.adaptive_dialogue.get("max_turns") or 12)
            for _ in range(max_turns):
                decision = current.get("decision") if isinstance(current.get("decision"), dict) else {}
                action = str(decision.get("action") or "")
                if action in TERMINAL_ACTIONS:
                    break
                if action == "ASK_NEXT":
                    target = str(decision.get("question_target_id") or "")
                    if target not in answers:
                        return RuntimeResult(session_id, profile_id, responses, self.get_session(session_id), (time.perf_counter() - started) * 1000, f"missing_answer_mapping:{target or 'none'}")
                    payload = {"message": answers[target]}
                elif action == "ASK_CONFIRMATION":
                    payload = {"message": str(case.adaptive_dialogue.get("confirmation_reply") or "Thông tin trên đúng.")}
                elif action == "ASK_CLARIFICATION":
                    clarification_reply = str(case.adaptive_dialogue.get("clarification_reply") or "").strip()
                    if not clarification_reply:
                        return RuntimeResult(session_id, profile_id, responses, self.get_session(session_id), (time.perf_counter() - started) * 1000, "invalid_golden_case:missing_clarification_reply")
                    payload = {"message": clarification_reply}
                else:
                    return RuntimeResult(session_id, profile_id, responses, self.get_session(session_id), (time.perf_counter() - started) * 1000, f"unexpected_action:{action or 'none'}")
                time.sleep(3.0)
                turn = self._request_with_retry(
                    "POST",
                    f"/api/v1/simple-triage/chat/{session_id}",
                    json=payload,
                )
                current = turn.json()
                responses.append(current)
            else:
                return RuntimeResult(session_id, profile_id, responses, self.get_session(session_id), (time.perf_counter() - started) * 1000, "max_turns_exceeded")
            return RuntimeResult(session_id, profile_id, responses, self.get_session(session_id), (time.perf_counter() - started) * 1000)
        except Exception as exc:  # Preserve error in artifact instead of aborting all cases.
            session = self.get_session(session_id) if session_id else {}
            return RuntimeResult(session_id, profile_id, responses, session, (time.perf_counter() - started) * 1000, str(exc))

    def get_session(self, session_id: str | None) -> dict[str, Any]:
        if not session_id:
            return {}
        response = self._request_with_retry("GET", f"/api/v1/simple-triage/sessions/{session_id}")
        return response.json()
