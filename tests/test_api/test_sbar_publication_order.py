"""SBAR is published only after verification and durable commit."""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any

import pytest

from src.agents.nodes.summary_creator import create_sbar_summary_node
from src.agents.tools.queue_pusher import publish_finalized_sbar
from src.api.routes_patient import (
    _commit_and_publish_finalized_sbar,
    _is_clinical_proposal,
)


def _verified_proposal() -> dict[str, Any]:
    return {
        "metadata": {"deepagent_tool_gated": True},
        "decision_status": "PROPOSED",
        "patient_confirmed_intake": True,
        "evidence_status": "SUFFICIENT",
        "evidence_authority_status": "AUTHORIZED",
        "turn_rag_citations": [{"protocolId": "ESI-AUTH-1"}],
        "current_esi_level": 2,
        "sbar_report": {"situation": "Finalized situation"},
    }


def _committed_case() -> SimpleNamespace:
    return SimpleNamespace(
        id="case-1",
        session_title="Đau ngực",
        ai_proposed_esi=2,
        is_red_flag_triggered=False,
        sbar_summary={"situation": "Finalized situation"},
    )


class _RecordingSession:
    def __init__(self, events: list[str], *, fail_commit: bool = False) -> None:
        self.events = events
        self.fail_commit = fail_commit

    async def commit(self) -> None:
        self.events.append("commit")
        if self.fail_commit:
            raise RuntimeError("commit failed")


@pytest.mark.asyncio
async def test_verified_sbar_is_published_only_after_commit(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    events: list[str] = []
    published: dict[str, Any] = {}

    async def record_publication(**payload: Any) -> bool:
        events.append("publish")
        published.update(payload)
        return True

    monkeypatch.setattr(
        "src.api.routes_patient.publish_finalized_sbar",
        record_publication,
    )
    case = _committed_case()

    delivered = await _commit_and_publish_finalized_sbar(
        _RecordingSession(events),  # type: ignore[arg-type]
        case,  # type: ignore[arg-type]
        _verified_proposal(),
    )

    assert delivered is True
    assert events == ["commit", "publish"]
    assert published["session_id"] == case.id
    assert published["recommended_esi"] == case.ai_proposed_esi
    assert published["sbar_report"] == case.sbar_summary


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "agent_result",
    [
        {
            **_verified_proposal(),
            "metadata": {"deepagent_tool_gated": False},
        },
        {
            **_verified_proposal(),
            "decision_status": "INSUFFICIENT_EVIDENCE",
            "current_esi_level": None,
            "sbar_report": None,
        },
    ],
)
async def test_unverified_or_rejected_output_is_never_published(
    monkeypatch: pytest.MonkeyPatch,
    agent_result: dict[str, Any],
) -> None:
    events: list[str] = []

    async def must_not_publish(**_payload: Any) -> bool:
        raise AssertionError("rejected output reached queue publication")

    monkeypatch.setattr(
        "src.api.routes_patient.publish_finalized_sbar",
        must_not_publish,
    )

    delivered = await _commit_and_publish_finalized_sbar(
        _RecordingSession(events),  # type: ignore[arg-type]
        _committed_case(),  # type: ignore[arg-type]
        agent_result,
    )

    assert delivered is False
    assert events == ["commit"]


@pytest.mark.asyncio
async def test_commit_failure_never_publishes(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    events: list[str] = []

    async def must_not_publish(**_payload: Any) -> bool:
        raise AssertionError("publication ran after failed commit")

    monkeypatch.setattr(
        "src.api.routes_patient.publish_finalized_sbar",
        must_not_publish,
    )

    with pytest.raises(RuntimeError, match="commit failed"):
        await _commit_and_publish_finalized_sbar(
            _RecordingSession(events, fail_commit=True),  # type: ignore[arg-type]
            _committed_case(),  # type: ignore[arg-type]
            _verified_proposal(),
        )

    assert events == ["commit"]


@pytest.mark.asyncio
async def test_post_commit_delivery_failure_preserves_committed_result(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    events: list[str] = []

    async def failed_publication(**_payload: Any) -> bool:
        events.append("publish")
        raise RuntimeError("socket manager failed")

    monkeypatch.setattr(
        "src.api.routes_patient.publish_finalized_sbar",
        failed_publication,
    )

    delivered = await _commit_and_publish_finalized_sbar(
        _RecordingSession(events),  # type: ignore[arg-type]
        _committed_case(),  # type: ignore[arg-type]
        _verified_proposal(),
    )

    assert delivered is False
    assert events == ["commit", "publish"]


@pytest.mark.asyncio
async def test_summary_creation_has_no_queue_side_effect(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def must_not_get_queue_manager() -> None:
        raise AssertionError("summary creator attempted an early broadcast")

    monkeypatch.setattr(
        "src.api.websocket_manager.get_queue_manager",
        must_not_get_queue_manager,
    )

    result = await create_sbar_summary_node(
        {
            "query": "Tôi đang đau ngực",
            "current_esi_level": 2,
            "is_red_flag": True,
            "red_flag_status": "CONFIRMED",
            "clinical_blueprint": {"chief_complaint": ["đau ngực"]},
            "clinical_memory": {},
        }
    )

    assert result["decision_status"] == "EMERGENCY_ESCALATED"
    assert isinstance(result["sbar_report"], dict)
    assert "quyết định APPROVE" in result["sbar_report"]["recommendation"]
    assert "quyết địnhAPPROVE" not in result["sbar_report"]["recommendation"]


@pytest.mark.asyncio
async def test_queue_payload_contains_the_exact_finalized_sbar(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    payloads: list[dict[str, Any]] = []

    class _Manager:
        async def broadcast(self, payload: dict[str, Any]) -> None:
            payloads.append(payload)

    monkeypatch.setattr(
        "src.api.websocket_manager.get_queue_manager",
        lambda: _Manager(),
    )
    sbar = {"situation": "Committed SBAR", "citations": ["ESI-AUTH-1"]}

    delivered = await publish_finalized_sbar(
        session_id="case-1",
        recommended_esi=2,
        chief_complaint="Đau ngực",
        is_red_flag=False,
        sbar_report=sbar,
    )

    assert delivered is True
    assert payloads == [
        {
            "event": "NEW_TRIAGE_CASE",
            "session_id": "case-1",
            "recommended_esi": 2,
            "chief_complaint": "Đau ngực",
            "is_red_flag": False,
            "sbar_snippet": "ESI 2 • Đau ngực...",
            "sbar_report": sbar,
            "publication_stage": "POST_COMMIT_FINALIZED",
        }
    ]


def test_proposal_guard_requires_current_turn_verification() -> None:
    proposal = _verified_proposal()
    assert _is_clinical_proposal(proposal) is True

    proposal["metadata"] = {"deepagent_tool_gated": False}
    assert _is_clinical_proposal(proposal) is False
