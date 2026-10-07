"""Patient API contracts for adaptive evidence and durable SBAR recovery."""

from __future__ import annotations

from datetime import datetime
from types import SimpleNamespace
from typing import Any

import pytest

from src.agents.nodes.question_engine import (
    plan_next_question,
    run_question_engine_node,
)
from src.api.routes_patient import (
    _case_support_dtos,
    _citation_dtos,
    _persisted_evidence_details,
    _persisted_question_payload,
    _structured_payload_dto,
    get_patient_history,
    get_session_messages,
    get_session_replay_detail,
)
from src.models.db_models import ChatMessage, NurseReviewState, TriageCase
from src.models.patient_schemas import PatientChatMessageDTO, StructuredPayloadDTO
from src.services.triage_session_recovery import recover_triage_state


AUTHORITY_CITATION: dict[str, Any] = {
    "id": "ESI-AUTH-001",
    "title": "Emergency Severity Index decision rule",
    "protocolId": "ESI-AUTH-001",
    "excerpt": "Validated authority excerpt",
    "sourceType": "validated_protocol",
    "retrievalChannels": [
        {"channel": "en_dense", "rank": 1, "score": 0.92},
    ],
}

RAW_CASE_SUPPORT: dict[str, Any] = {
    "case_id": "MIETIC-CASE-007",
    "presentation_excerpt": "Comparable presentation without an ESI label.",
    "similarity_score": 0.88,
    "retrieval_scope": "CASE_SUPPORT",
    "authority_status": "NOT_PROTOCOL",
    # These internal labels may be used to audit the corpus, but neither may
    # cross the patient API boundary or be persisted in its replay payload.
    "validated_esi_level": 1,
    "label_status": "CONFLICTING",
}

COMPLETE_SBAR: dict[str, Any] = {
    "situation": "Đau ngực cần đánh giá sớm.",
    "background": "Thông tin nền đã được người bệnh xác nhận.",
    "assessment": "Đề xuất dựa trên phác đồ ESI đã duyệt.",
    "recommendation": "Chuyển điều dưỡng thẩm định.",
    "citations": ["ESI-AUTH-001"],
}


class _ScalarResult:
    def __init__(self, values: list[Any]) -> None:
        self._values = values

    def first(self) -> Any | None:
        return self._values[0] if self._values else None

    def all(self) -> list[Any]:
        return self._values


class _ExecuteResult:
    def __init__(
        self,
        *,
        scalar_values: list[Any] | None = None,
        rows: list[Any] | None = None,
    ) -> None:
        self._scalar_values = scalar_values or []
        self._rows = rows or []

    def scalars(self) -> _ScalarResult:
        return _ScalarResult(self._scalar_values)

    def first(self) -> Any | None:
        return self._rows[0] if self._rows else None

    def all(self) -> list[Any]:
        return self._rows


class _FakeSession:
    def __init__(self, *results: _ExecuteResult) -> None:
        self._results = list(results)

    async def execute(self, _query: object) -> _ExecuteResult:
        if not self._results:
            raise AssertionError("unexpected database query")
        return self._results.pop(0)


class _FakeRuntime:
    def __init__(self, values: object) -> None:
        self._values = values

    async def get_session_state(self, _session_id: str) -> SimpleNamespace:
        return SimpleNamespace(values=self._values)


def _case(**changes: Any) -> TriageCase:
    values: dict[str, Any] = {
        "id": "case-1",
        "patient_id": "patient-1",
        "profile_id": None,
        "session_title": "Đau ngực",
        "status": "IN_PROGRESS",
        "ai_proposed_esi": None,
        "final_clinical_esi": None,
        "is_red_flag_triggered": False,
        "sbar_summary": None,
        "rag_citations": [],
        "rag_citation_details": [],
        "created_at": datetime(2026, 8, 20, 8, 0, 0),
        "updated_at": datetime(2026, 8, 20, 8, 5, 0),
    }
    values.update(changes)
    return TriageCase(**values)


def _agent_message(content: str = "Đã xử lý lượt hiện tại.") -> ChatMessage:
    return ChatMessage(
        id="message-1",
        triage_case_id="case-1",
        sender_type="AI_AGENT",
        content=content,
        created_at=datetime(2026, 8, 20, 8, 4, 0),
    )


def test_generic_options_mark_only_mutually_exclusive_choices() -> None:
    question = plan_next_question(
        {"chief_complaint": ["đau ngực"]},
        ["associated_symptoms"],
        {},
    )

    payload = StructuredPayloadDTO.model_validate(question.structured_payload)
    options = {item.id: item for item in payload.options or []}

    assert options["associated_fever"].isExclusive is False
    assert options["associated_none"].isExclusive is True
    assert options["associated_unsure"].isExclusive is True


def test_case_support_is_sanitized_and_kept_out_of_authority_citations() -> None:
    legacy_case_citation = {
        "id": "CASE-CITATION-007",
        "title": "MIETIC case",
        "protocolId": "MIETIC-CASE-007",
        "excerpt": "Not a protocol.",
        "sourceType": "case_example",
    }
    persisted = _persisted_evidence_details(
        [AUTHORITY_CITATION, legacy_case_citation],
        [RAW_CASE_SUPPORT],
    )

    assert [item.protocolId for item in _citation_dtos(persisted)] == [
        "ESI-AUTH-001"
    ]
    support = _case_support_dtos(persisted)
    assert len(support) == 1
    assert support[0].caseId == "MIETIC-CASE-007"
    assert support[0].retrievalScope == "CASE_SUPPORT"
    assert support[0].authorityStatus == "NOT_PROTOCOL"
    serialized = support[0].model_dump(mode="json")
    assert "validated_esi_level" not in serialized
    assert "label_status" not in serialized
    assert all("validated_esi_level" not in item for item in persisted)
    assert all("label_status" not in item for item in persisted)


def test_message_contract_accepts_case_support_and_retrieval_failure() -> None:
    message = PatientChatMessageDTO.model_validate(
        {
            "id": "message-1",
            "sender": "bot",
            "timestamp": "2026-08-20T08:00:00Z",
            "content": "Không thể truy xuất nguồn ESI lúc này.",
            "decisionStatus": "RETRIEVAL_FAILURE",
            "workflowPhase": "RETRIEVAL",
            "evidenceStatus": "RETRIEVAL_FAILURE",
            "caseSupport": _case_support_dtos([RAW_CASE_SUPPORT]),
            "sbarFinalized": False,
        }
    )

    assert message.decisionStatus == "RETRIEVAL_FAILURE"
    assert message.evidenceStatus == "RETRIEVAL_FAILURE"
    assert message.caseSupport[0].authorityStatus == "NOT_PROTOCOL"
    assert message.ragCitations is None
    assert message.sbarFinalized is False


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("target", "expected_field", "expected_options_type"),
    [
        ("radiation", "radiation", "text_only"),
        ("contradiction_onset_time", "contradiction_onset_time", "text_only"),
        ("symptom.dyspnea", "associated_symptoms", "single"),
    ],
)
async def test_cold_recovery_prefers_validated_question_target_marker(
    target: str,
    expected_field: str,
    expected_options_type: str,
) -> None:
    result = await run_question_engine_node(
        {
            "clinical_blueprint": {"chief_complaint": ["đau ngực"]},
            "missing_critical_fields": [],
        },
        target=target,
    )
    persisted = _persisted_question_payload(result)

    assert persisted is not None
    assert persisted["_activeQuestion"]["field"] == expected_field
    assert persisted["optionsType"] == expected_options_type
    record = _agent_message(result["response"])
    record.structured_options = [persisted]

    recovered = recover_triage_state([record])

    assert recovered.active_question == {
        "field": expected_field,
        "question_id": expected_field,
        "options_type": expected_options_type,
    }
    public_payload = _structured_payload_dto(persisted)
    assert public_payload is not None
    assert "_activeQuestion" not in public_payload.model_dump(mode="json")


def test_cold_recovery_rejects_an_unknown_private_question_target() -> None:
    record = _agent_message("Please provide a hidden identifier")
    record.structured_options = [
        {
            "optionsType": "text_only",
            "_activeQuestion": {
                "field": "patient.secret_identifier",
                "questionId": "patient.secret_identifier",
                "optionsType": "text_only",
            },
        }
    ]

    recovered = recover_triage_state([record])

    assert recovered.active_question is None


@pytest.mark.asyncio
async def test_replayed_free_text_question_keeps_text_response_contract(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    result = await run_question_engine_node(
        {
            "clinical_blueprint": {"chief_complaint": ["đau ngực"]},
            "missing_critical_fields": [],
        },
        target="radiation",
    )
    persisted = _persisted_question_payload(result)
    assert persisted is not None
    record = _agent_message(result["response"])
    record.structured_options = [persisted]
    runtime = _FakeRuntime({})
    monkeypatch.setattr(
        "src.api.routes_patient.get_deepagent_runtime",
        lambda: runtime,
    )
    session = _FakeSession(
        _ExecuteResult(scalar_values=[_case()]),
        _ExecuteResult(rows=[]),
        _ExecuteResult(scalar_values=[record]),
    )

    response = await get_session_messages(
        "case-1",
        SimpleNamespace(id="patient-1"),  # type: ignore[arg-type]
        session,  # type: ignore[arg-type]
    )

    replayed = response.messages[-1]
    assert replayed.responseType == "TEXT"
    assert replayed.structured is not None
    assert replayed.structured.optionsType == "text_only"
    assert "_activeQuestion" not in replayed.structured.model_dump(mode="json")


@pytest.mark.asyncio
async def test_recovery_exposes_hot_retrieval_failure_without_stale_sbar(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    triage_case = _case(
        # A partial JSON value on an active case is not a finalized SBAR.
        ai_proposed_esi=2,
        sbar_summary={"situation": "partial draft"},
    )
    session = _FakeSession(
        _ExecuteResult(scalar_values=[triage_case]),
        _ExecuteResult(rows=[]),
        _ExecuteResult(scalar_values=[_agent_message()]),
        # Ca đang ở HITL_REVIEWING nhưng chưa ai nhận, nên trạng thái đội ngũ
        # chăm sóc phải tra bảng rà soát để phân biệt "chờ người nhận" với
        # "đã chuyển đánh giá chuyên sâu".
        _ExecuteResult(scalar_values=[]),
    )
    runtime = _FakeRuntime(
        {
            "decision_status": "RETRIEVAL_FAILURE",
            "evidence_status": "RETRIEVAL_FAILURE",
            "retrieval_degraded_modes": [
                "AUTHORITY_RETRIEVAL:TIMEOUT",
                "AUTHORITY_RETRIEVAL:TIMEOUT",
            ],
            "workflow_phase": "RETRIEVAL",
            "intake_confirmation_status": "CONFIRMED",
        }
    )
    monkeypatch.setattr(
        "src.api.routes_patient.get_deepagent_runtime",
        lambda: runtime,
    )

    response = await get_session_messages(
        "case-1",
        SimpleNamespace(id="patient-1"),  # type: ignore[arg-type]
        session,  # type: ignore[arg-type]
    )

    assert response.session_status.status == "IN_PROGRESS"
    assert response.session_status.decision_status == "RETRIEVAL_FAILURE"
    assert response.session_status.evidence_status == "RETRIEVAL_FAILURE"
    assert response.session_status.workflow_phase == "RETRIEVAL"
    assert response.session_status.retrieval_degraded_modes == [
        "AUTHORITY_RETRIEVAL:TIMEOUT"
    ]
    assert response.session_status.ai_proposed_esi == 2
    assert response.session_status.final_esi is None
    assert response.session_status.sbar_summary is None
    assert response.session_status.sbar_finalized is False
    assert response.messages[-1].decisionStatus == "RETRIEVAL_FAILURE"
    assert response.messages[-1].evidenceStatus == "RETRIEVAL_FAILURE"
    assert response.messages[-1].esiLevel is None
    assert response.messages[-1].sbarFinalized is False


@pytest.mark.asyncio
async def test_recovery_replays_finalized_authority_and_sanitized_case_support(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    persisted_evidence = _persisted_evidence_details(
        [AUTHORITY_CITATION],
        [RAW_CASE_SUPPORT],
    )
    triage_case = _case(
        status="HITL_REVIEWING",
        ai_proposed_esi=3,
        sbar_summary=COMPLETE_SBAR,
        rag_citations=["ESI-AUTH-001"],
        rag_citation_details=persisted_evidence,
    )
    session = _FakeSession(
        _ExecuteResult(scalar_values=[triage_case]),
        _ExecuteResult(rows=[]),
        _ExecuteResult(scalar_values=[_agent_message("Kết quả đã hoàn tất.")]),
        # Ca HITL_REVIEWING chưa có người nhận: cần một vòng tra bảng rà soát để
        # nói đúng trạng thái đội ngũ chăm sóc cho người bệnh.
        _ExecuteResult(scalar_values=[]),
    )
    runtime = _FakeRuntime({})
    monkeypatch.setattr(
        "src.api.routes_patient.get_deepagent_runtime",
        lambda: runtime,
    )

    response = await get_session_messages(
        "case-1",
        SimpleNamespace(id="patient-1"),  # type: ignore[arg-type]
        session,  # type: ignore[arg-type]
    )

    assert response.session_status.status == "HITL_REVIEWING"
    assert response.session_status.sbar_finalized is True
    assert response.session_status.decision_status == "PROPOSED"
    assert response.session_status.evidence_status == "SUFFICIENT"
    assert response.session_status.workflow_phase == "HANDOFF"
    result = response.messages[-1]
    assert result.responseType == "TRIAGE_PROPOSAL"
    assert result.sbarFinalized is True
    assert [item.protocolId for item in result.ragCitations or []] == [
        "ESI-AUTH-001"
    ]
    assert [item.caseId for item in result.caseSupport] == ["MIETIC-CASE-007"]
    dumped_support = result.caseSupport[0].model_dump(mode="json")
    assert "validated_esi_level" not in dumped_support
    assert "label_status" not in dumped_support


@pytest.mark.asyncio
async def test_history_uses_real_status_and_never_fabricates_draft_sbar(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    triage_case = _case(
        ai_proposed_esi=4,
        sbar_summary={"situation": "unfinished"},
    )
    current_user = SimpleNamespace(id="patient-1")
    history = await get_patient_history(
        current_user,  # type: ignore[arg-type]
        _FakeSession(
            _ExecuteResult(rows=[(triage_case, None)]),
            _ExecuteResult(rows=[]),
        ),  # type: ignore[arg-type]
    )

    assert len(history.items) == 1
    assert history.items[0].status == "IN_PROGRESS"
    assert history.items[0].final_esi is None
    assert history.items[0].sbar_finalized is False
    assert history.items[0].sbar_snippet == ""

    runtime = _FakeRuntime({})
    monkeypatch.setattr(
        "src.api.routes_patient.get_deepagent_runtime",
        lambda: runtime,
    )
    detail_session = _FakeSession(
        _ExecuteResult(rows=[(triage_case, None)]),
        _ExecuteResult(scalar_values=[triage_case]),
        _ExecuteResult(rows=[]),
        _ExecuteResult(scalar_values=[_agent_message()]),
    )
    detail = await get_session_replay_detail(
        "case-1",
        current_user,  # type: ignore[arg-type]
        detail_session,  # type: ignore[arg-type]
    )

    assert detail.status == "IN_PROGRESS"
    assert detail.sbar_finalized is False
    assert detail.sbar_report is None
    assert detail.sbar_snippet == ""


@pytest.mark.asyncio
async def test_history_signature_uses_only_persisted_nurse_decision(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    triage_case = _case(
        status="COMPLETED",
        ai_proposed_esi=3,
        final_clinical_esi=2,
        is_overridden=True,
        assigned_nurse_id="nurse-42",
        reviewed_at=datetime(2026, 8, 20, 9, 0, 0),
        sbar_summary=COMPLETE_SBAR,
        rag_citations=["ESI-AUTH-001"],
        rag_citation_details=_persisted_evidence_details(
            [AUTHORITY_CITATION],
            [],
        ),
    )
    runtime = _FakeRuntime({})
    monkeypatch.setattr(
        "src.api.routes_patient.get_deepagent_runtime",
        lambda: runtime,
    )
    nurse_review = NurseReviewState(
        triage_case_id="case-1",
        review_status="TRIAGE_DECIDED",
        assigned_nurse_id="nurse-42",
        decision_type="ADJUST_ESI",
        decision_reason_code="CLINICAL_FINDING_CHANGED",
        decision_note="Dấu hiệu sinh tồn mới cần ưu tiên đánh giá sớm.",
        decided_at=datetime(2026, 8, 20, 9, 0, 0),
    )
    session = _FakeSession(
        _ExecuteResult(rows=[(triage_case, None)]),
        _ExecuteResult(scalar_values=[triage_case]),
        _ExecuteResult(rows=[(nurse_review, SimpleNamespace(full_name="Điều dưỡng Minh Anh"))]),
        _ExecuteResult(scalar_values=[_agent_message("Đã thẩm định.")]),
    )

    detail = await get_session_replay_detail(
        "case-1",
        SimpleNamespace(id="patient-1"),  # type: ignore[arg-type]
        session,  # type: ignore[arg-type]
    )

    assert detail.status == "COMPLETED"
    assert detail.hitl_signature is not None
    assert detail.hitl_signature.review_timestamp == "2026-08-20T09:00:00Z"
    assert detail.hitl_signature.original_esi == 3
    assert detail.hitl_signature.final_esi == 2
    assert detail.hitl_signature.reviewer_name == "Điều dưỡng Minh Anh"
    assert detail.hitl_signature.justification_note == "Dấu hiệu sinh tồn mới cần ưu tiên đánh giá sớm."
