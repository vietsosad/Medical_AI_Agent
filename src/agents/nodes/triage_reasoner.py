"""Evidence-gated ESI reasoning with fail-closed clinical output."""

from __future__ import annotations

import asyncio
import json
import uuid
from datetime import UTC, datetime
from typing import Any, Literal, get_args

from pydantic import BaseModel, Field, model_validator

from src.agents.clinical_state_view import ClinicalStateView
from src.agents.guardrails import filter_output_diagnosis
from src.agents.nodes.evidence_gate import build_insufficient_evidence_handoff
from src.agents.nodes.resource_estimator import (
    build_resource_count_proposal,
    estimate_resource_count_esi,
)
from src.agents.prompt_safety import PROMPT_INJECTION_GUARD
from src.agents.state import AgentState
from src.config import get_rag_refinement_attempt_limit, get_settings
from src.services.llm_provider import get_resilient_llm


DecisionFactTarget = Literal[
    "chief_complaint",
    "onset_time",
    "severity_score",
    "radiation",
    "associated_symptoms",
    "vital_signs",
    "symptom.chest_pain",
    "symptom.dyspnea",
    "symptom.headache",
    "symptom.abdominal_pain",
    "symptom.back_pain",
    "symptom.sore_throat",
    "symptom.nausea",
    "symptom.vomiting",
    "symptom.fever",
    "symptom.cough",
    "symptom.dizziness",
    "symptom.lightheadedness",
    "symptom.diarrhea",
    "symptom.rash",
    "symptom.bleeding",
    "symptom.syncope",
    "symptom.seizure",
    "symptom.diaphoresis",
    "symptom.palpitations",
    "vital.temperature_c",
    "vital.spo2",
    "vital.heart_rate",
    "vital.systolic_bp",
    "recent_procedure_context",
    "clinical_memory_confirmation",
]


class TriageEvaluation(BaseModel):
    """One bounded clinical decision over patient facts and authority evidence."""

    decision: Literal[
        "PROPOSE",
        "NEED_MORE_PATIENT_INFO",
        "NEED_MORE_EVIDENCE",
        "CONTRADICTORY_DATA",
        "ABSTAIN",
    ]
    esi_level: int | None = Field(
        default=None,
        ge=1,
        le=5,
        description="Mức ESI đề xuất từ 1 đến 5; null khi ABSTAIN",
    )
    reasoning: str = Field(
        min_length=20,
        description=(
            "Nhận định nguy cơ ngắn BẰNG TIẾNG VIỆT, nói trực tiếp với người "
            "bệnh (xưng 'bạn'), không chẩn đoán và không kê đơn"
        ),
    )
    matched_criteria: list[str] = Field(default_factory=list)
    citation_ids: list[str] = Field(default_factory=list)
    uncertainty_reasons: list[str] = Field(default_factory=list)
    requested_fact: DecisionFactTarget | None = None
    contradiction_field: str | None = Field(default=None, max_length=120)
    refined_query: str | None = Field(default=None, max_length=500)
    decision_point: Literal["A", "B", "C"] | None = None
    retrieval_facets: list[str] = Field(default_factory=list, max_length=8)

    @model_validator(mode="after")
    def validate_decision(self) -> TriageEvaluation:
        if self.decision == "PROPOSE" and self.esi_level is None:
            raise ValueError("PROPOSE requires esi_level")
        if self.decision != "PROPOSE" and self.esi_level is not None:
            raise ValueError(f"{self.decision} requires esi_level=null")
        if self.decision == "NEED_MORE_PATIENT_INFO" and not self.requested_fact:
            raise ValueError("NEED_MORE_PATIENT_INFO requires requested_fact")
        if self.decision == "NEED_MORE_EVIDENCE" and not (
            self.refined_query or self.decision_point or self.retrieval_facets
        ):
            raise ValueError(
                "NEED_MORE_EVIDENCE requires a bounded query or metadata filter"
            )
        if self.decision == "CONTRADICTORY_DATA" and not self.contradiction_field:
            raise ValueError("CONTRADICTORY_DATA requires contradiction_field")
        return self


# Appended to the prompt on the single retry. It restates the contract that
# was broken; it does not relax it or ask the model to reveal its reasoning.
_REGROUNDING_REMINDER = (
    "LƯU Ý: câu trả lời trước không hợp lệ vì citation_ids không nằm trong "
    "danh sách bằng chứng được cung cấp. Hãy trả lời lại và sao chép chính xác "
    "ít nhất một citation_id từ khối 'Bằng chứng có provenance' ở trên. Không "
    "thay đổi kết luận lâm sàng chỉ để vượt qua kiểm tra này."
)

_MISSING_TEXT_VALUES = {
    "khong ro",
    "chua ro",
    "chua co",
    "khong co so do",
    "unknown",
    "not available",
    "n/a",
}


def _insufficient_result(
    reason: str,
    *,
    handoff_reason: str = "UNSPECIFIED",
) -> dict[str, Any]:
    return build_insufficient_evidence_handoff(
        reason,
        handoff_reason=handoff_reason,
    )


def _contradiction_result(state: AgentState) -> dict[str, Any]:
    contradictions = [
        item
        for item in state.get("unresolved_contradictions", [])
        if isinstance(item, dict)
    ]
    field = str(
        (contradictions[0].get("field") or contradictions[0].get("key") or "unknown")
        if contradictions
        else "unknown"
    )
    return {
        "evidence_sufficiency_outcome": "CONTRADICTORY_DATA",
        "decision_status": "NEEDS_CLARIFICATION",
        "current_esi_level": None,
        "sbar_report": None,
        "turn_rag_citations": [],
        "missing_critical_fields": [f"contradiction:{field}"],
        "readiness_outcome": "NOT_READY",
        "evidence_status": "NOT_REQUESTED",
        "evidence_authority_status": "NOT_EVALUATED",
        "patient_confirmed_intake": False,
        "next_step": "question_engine",
        "workflow_phase": "CLARIFICATION",
    }


def _target_is_unresolved(
    target: DecisionFactTarget,
    state: AgentState,
) -> bool:
    """Reject a model-requested question when authoritative state answered it."""
    accepted_unknown = set(
        (state.get("action_loop_state") or {}).get("accepted_unknown_targets") or []
    )
    asked_targets = dict(
        (state.get("action_loop_state") or {}).get("asked_targets") or {}
    )
    if target in accepted_unknown or int(asked_targets.get(target, 0)) >= 2:
        return False
    view = ClinicalStateView.from_agent_state(state)
    blueprint = state.get("clinical_blueprint", {})
    if target.startswith("symptom."):
        reading = view.read(target)
        return reading.is_unknown or reading.is_uncertain
    if target.startswith("vital."):
        vital_key = target.removeprefix("vital.")
        if view.current_value(target) is not None:
            return False
        if (blueprint.get("vital_signs") or {}).get(vital_key) is not None:
            return False
        return state.get("vital_signs_status") != "UNAVAILABLE_CONFIRMED"
    if target == "chief_complaint":
        return not bool(blueprint.get("chief_complaint"))
    if target in {"onset_time", "severity_score", "radiation"}:
        if _primary_problem_answered(view, target):
            return False
        return _is_missing_value(blueprint.get(target))
    if target == "associated_symptoms":
        # An empty list is not the same as an explicit denial. This question
        # offers "none" and therefore resolves that semantic distinction.
        return not bool(blueprint.get("associated_symptoms"))
    if target == "vital_signs":
        return not bool(blueprint.get("vital_signs")) and state.get(
            "vital_signs_status"
        ) not in {"PATIENT_REPORTED", "UNAVAILABLE_CONFIRMED"}
    if target == "recent_procedure_context":
        return bool(state.get("clinical_context_update_pending"))
    if target == "clinical_memory_confirmation":
        return state.get("clinical_memory_confirmation_status") not in {
            "CONFIRMED",
            "UPDATED_BY_PATIENT",
            "UNCERTAIN",
        }
    return False


def _is_missing_value(value: Any) -> bool:
    if value is None:
        return True
    if isinstance(value, str):
        text = _fold_missing_marker(value)
        return not text or text in _MISSING_TEXT_VALUES
    return False


def _fold_missing_marker(value: str) -> str:
    import unicodedata

    normalized = unicodedata.normalize("NFD", value.lower().replace("đ", "d"))
    return " ".join(
        "".join(
            character
            for character in normalized
            if unicodedata.category(character) != "Mn"
        ).split()
    )


def _primary_problem_answered(
    view: ClinicalStateView,
    attribute: str,
) -> bool:
    """True when the primary symptom already answered a generic target.

    The reasoner speaks in legacy generic targets while adaptive questions may
    store answers under the primary problem, e.g. ``headache.onset_time``.  This
    guard prevents a structured model from re-asking a question just because it
    used the generic target name.
    """
    from src.agents.problem_state import build_problem_state

    primary = build_problem_state(view).primary
    if primary is None:
        return False
    fact = primary.facts.get(attribute)
    return bool(
        fact
        and fact.is_answered
        and fact.value is not None
        and not _is_missing_value(fact.value)
    )


def _patient_info_result(
    target: DecisionFactTarget,
    reason: str,
    *,
    citation_ids: list[str],
) -> dict[str, Any]:
    return {
        "evidence_sufficiency_outcome": "NEED_MORE_PATIENT_INFO",
        # The retrieval snapshot is invalidated: it was built without the fact
        # about to arrive, so it must be fetched again once the answer exists.
        "evidence_status": "NOT_REQUESTED",
        "evidence_authority_status": "NOT_EVALUATED",
        "decision_status": "NEEDS_CLARIFICATION",
        # The patient's confirmation is deliberately left standing. Asking for
        # one more detail is not new information -- no answer has arrived yet --
        # and clearing the confirmation here produced the loop the live audit
        # found in every non-emergency conversation: confirm, get asked one
        # question, answer it, and be shown the same review again, forever.
        # Genuine invalidation (a corrected fact, a new problem, a
        # contradiction) is owned by ``confirmation_lifecycle`` and still
        # applies to the answer when it arrives.
        "missing_critical_fields": [target],
        "decision_relevant_unknowns": [target],
        "readiness_outcome": "NOT_READY",
        "current_esi_level": None,
        "preliminary_esi_reasoning": None,
        "sbar_report": None,
        "turn_rag_citations": [],
        "uncertainty_reasons": [reason],
        "evidence_gap_citation_ids": citation_ids,
        "evidence_requested_fact": target,
        "workflow_phase": "CLARIFICATION",
        "next_step": "question_engine",
    }


def _evidence_refinement_result(result: TriageEvaluation) -> dict[str, Any]:
    reason = "; ".join(result.uncertainty_reasons) or result.reasoning
    return {
        "evidence_sufficiency_outcome": "NEED_MORE_EVIDENCE",
        "evidence_status": "RETRIEVED",
        "decision_status": "READY_FOR_REASONING",
        "retrieval_refined_query": str(result.refined_query or "").strip()[:500],
        "retrieval_decision_point": result.decision_point,
        "retrieval_facets": [
            str(item).strip()[:80]
            for item in result.retrieval_facets
            if str(item).strip()
        ][:8],
        "uncertainty_reasons": [reason],
        "current_esi_level": None,
        "sbar_report": None,
        "next_step": "refine_evidence",
    }


async def run_triage_reasoner_node(state: AgentState) -> dict[str, Any]:
    evidence = state.get("retrieved_evidence", [])
    citations = state.get("turn_rag_citations", [])
    if state.get("unresolved_contradictions"):
        return _contradiction_result(state)
    if state.get("patient_confirmed_intake") is not True:
        return _insufficient_result(
            "Intake chưa được người bệnh xác nhận",
            handoff_reason="INTAKE_NOT_CONFIRMED",
        )
    if state.get("evidence_status") not in {
        "RETRIEVED",
        "SUFFICIENT",
    } or not evidence or not citations:
        return _insufficient_result(
            "Bằng chứng truy xuất không đạt cổng kiểm định",
            handoff_reason="NO_AUTHORITY_EVIDENCE_RETRIEVED",
        )
    if state.get("evidence_authority_status") != "AUTHORIZED":
        return _insufficient_result(
            "Nguồn bằng chứng chưa được xác nhận thẩm quyền",
            handoff_reason="EVIDENCE_AUTHORITY_REJECTED",
        )

    # Semantics are resolved before the reasoner sees anything, so the model
    # never decides for itself what UNKNOWN, NEGATED or HISTORICAL mean.
    clinical_view = ClinicalStateView.from_agent_state(state)
    blueprint = state.get("clinical_blueprint", {})
    memory = state.get("clinical_memory", {})
    verified_profile_context = state.get("verified_profile_context", {})
    memory_status = state.get("clinical_memory_confirmation_status", "NOT_REVIEWED")
    resource_estimate = estimate_resource_count_esi(state)
    if resource_estimate is not None:
        deterministic_proposal = build_resource_count_proposal(
            state,
            resource_estimate,
        )
        if deterministic_proposal is not None:
            return deterministic_proposal
    if memory_status == "CONFIRMED":
        verified_memory = verified_profile_context or memory
        memory_note = "EHR đã được người bệnh xác nhận lại trong phiên."
    elif memory_status == "UPDATED_BY_PATIENT":
        verified_memory = {}
        memory_note = (
            "EHR có thay đổi; chỉ dùng phần đính chính của người bệnh cho ca này: "
            f"{blueprint.get('clinical_context_note') or 'không có chi tiết'}"
        )
    else:
        verified_memory = {}
        memory_note = "EHR không chắc còn đúng; không dùng để hạ mức ưu tiên."
    rag_context = "\n".join(
        (
            f"- [{item.get('citation_id')} | {item.get('protocol_code')} | "
            f"section {item.get('section')} | "
            f"criteria={json.dumps(item.get('protocol_criteria', []), ensure_ascii=False)} | "
            f"decision_points={json.dumps(item.get('decision_points', []), ensure_ascii=False)} | "
            f"facets={json.dumps(item.get('retrieval_facets', []), ensure_ascii=False)}]: "
            f"{item.get('protocol_content')}"
        )
        for item in evidence
    )
    allowed_targets = list(get_args(DecisionFactTarget))
    refinement_limit = get_rag_refinement_attempt_limit()
    # What has already been put to this patient. Without it the reasoner
    # re-requests a fact the conversation has already asked about (or already
    # settled), the deterministic guard rejects the repeat, and the turn dies
    # in a handoff -- so a model that cannot see its own history is a model
    # that cannot ask a *next* question.
    loop_state = state.get("action_loop_state") or {}
    asked_targets = dict(loop_state.get("asked_targets") or {})
    resolved_targets = sorted(
        {
            target
            for target in allowed_targets
            if not _target_is_unresolved(target, state)  # type: ignore[arg-type]
        }
    )
    open_targets = [
        target for target in allowed_targets if target not in resolved_targets
    ]
    # The evidence-driven question budget. Each accepted request costs one; when
    # it is spent the reasoner has to conclude from what it has, because
    # "sufficient" is a judgement the conversation already made and this phase
    # exists to check the evidence, not to restart the history-taking.
    evidence_questions_asked = int(loop_state.get("evidence_questions") or 0)
    evidence_question_budget = int(get_settings().evidence_question_budget)
    question_budget_spent = evidence_questions_asked >= evidence_question_budget
    if question_budget_spent:
        open_targets = []
    prompt = (
        "Bạn là trợ lý phân loại mức độ khẩn cấp lâm sàng. Không chẩn đoán bệnh, không kê đơn.\n"
        # The authority corpus is in English and the model answered in English,
        # in third-person clinical prose, straight to a Vietnamese patient:
        # "The patient reports a headache with a severity score of 5...". The
        # evidence language is not the patient's language.
        "TRƯỜNG `reasoning` LÀ CÂU NÓI VỚI NGƯỜI BỆNH: viết bằng TIẾNG VIỆT, "
        "xưng hô 'bạn', 2-3 câu, không dùng ngôi thứ ba ('bệnh nhân'), "
        "không dùng thuật ngữ tiếng Anh. Bằng chứng có thể bằng tiếng Anh; "
        "câu trả lời thì không.\n"
        + PROMPT_INJECTION_GUARD +
        "Chọn đúng một outcome có cấu trúc:\n"
        "- PROPOSE chỉ khi patient facts và ESI authority trực tiếp hỗ trợ một mức ESI.\n"
        "- NEED_MORE_PATIENT_INFO khi đúng một fact chưa biết có thể đổi decision branch; "
        f"requested_fact BẮT BUỘC thuộc danh sách còn mở: {open_targets}.\n"
        + (
            "ĐÃ HẾT lượt hỏi thêm dữ kiện cho ca này. TUYỆT ĐỐI không chọn "
            "NEED_MORE_PATIENT_INFO. Hãy PROPOSE nếu dữ kiện và authority đủ, "
            "hoặc ABSTAIN nếu không đủ.\n"
            if question_budget_spent
            else f"Số lượt hỏi thêm đã dùng: "
            f"{evidence_questions_asked}/{evidence_question_budget}.\n"
        ) +
        "- NEED_MORE_EVIDENCE khi patient facts đã đủ nhưng authority candidates chưa phủ "
        "decision point; cung cấp refined_query ngắn và/hoặc decision_point A/B/C, facets.\n"
        "- CONTRADICTORY_DATA chỉ khi canonical state bên dưới có contradiction thật.\n"
        "- ABSTAIN khi không thể đề xuất, hỏi một fact, hay refine an toàn.\n"
        "Mỗi NEED_MORE_PATIENT_INFO/NEED_MORE_EVIDENCE phải trích ít nhất một citation_id "
        "từ authority cho thấy gap đó; không tạo clinical rule mới. "
        "MIETIC CASE_SUPPORT và nhãn ca tương tự không được cung cấp cho bạn và không bao giờ "
        "được dùng để suy ESI. "
        "Mọi matched_criteria và citation_ids phải sao chép từ bằng chứng được cung cấp, "
        "không tự tạo mã mới. Hồ sơ EHR chỉ là bối cảnh nguy cơ; không được dùng BMI, "
        "nhóm máu hoặc bệnh nền đơn lẻ để hạ mức ưu tiên hay thay thế triệu chứng/sinh hiệu hiện tại.\n\n"
        f"Trạng thái lâm sàng đã phân giải ngữ nghĩa: "
        f"{json.dumps(clinical_view.to_reasoner_payload(), ensure_ascii=False, default=str)}\n"
        "Diễn giải bắt buộc: not_asked_or_unknown nghĩa là CHƯA CÓ THÔNG TIN, "
        "không phải là không có triệu chứng. explicitly_denied_symptoms là do "
        "người bệnh phủ định, không phải chưa hỏi. historical_only_symptoms "
        "thuộc về quá khứ và không được coi là tình trạng hiện tại.\n"
        f"Blueprint (read-model tương thích): {json.dumps(blueprint, ensure_ascii=False)}\n"
        f"Bệnh nền đã xác minh: {json.dumps(verified_memory.get('chronic_conditions', []), ensure_ascii=False)}\n"
        f"Dị ứng đã xác minh: {json.dumps(verified_memory.get('allergies', []), ensure_ascii=False)}\n"
        f"Thuốc đã xác minh: {json.dumps(verified_memory.get('daily_medications', []), ensure_ascii=False)}\n"
        f"Nhân khẩu học và thể chất đã xác minh: {json.dumps({key: verified_memory.get(key) for key in ('age', 'gender', 'height_cm', 'weight_kg', 'bmi', 'blood_type')}, ensure_ascii=False)}\n"
        f"Trạng thái EHR: {memory_note}\n"
        f"Sinh hiệu do người bệnh khai: {json.dumps(blueprint.get('vital_signs', {}), ensure_ascii=False)}\n"
        f"Trạng thái sinh hiệu: {state.get('vital_signs_status', 'NOT_REVIEWED')}. "
        "Không được xem sinh hiệu thiếu là bình thường.\n"
        f"Số lượt refinement đã dùng: "
        f"{int(state.get('retrieval_refinement_count') or 0)}/{refinement_limit}.\n"
        f"Mâu thuẫn chưa giải quyết trong canonical state: "
        f"{json.dumps(state.get('unresolved_contradictions') or [], ensure_ascii=False, default=str)}\n"
        f"Fact đã hỏi và số lần đã hỏi: "
        f"{json.dumps(asked_targets, ensure_ascii=False)}\n"
        f"Fact ĐÃ có câu trả lời hoặc đã hỏi đủ số lần - TUYỆT ĐỐI không hỏi lại: "
        f"{json.dumps(resolved_targets, ensure_ascii=False)}\n"
        f"Bằng chứng có provenance:\n{rag_context}"
    )

    llm = get_resilient_llm(tier="large")
    if not hasattr(llm, "with_structured_output"):
        return _insufficient_result(
            "Không có mô hình structured-output khả dụng",
            handoff_reason="REASONER_MODEL_UNAVAILABLE",
        )

    public_citation_ids_precheck = {
        str(item.get("id")) for item in citations if item.get("id")
    }
    result: TriageEvaluation | None = None
    # One bounded retry, and only for a gap outcome whose citations did not
    # ground. A model that asks a sensible question but attaches the wrong
    # citation id has made a formatting mistake, not a clinical finding, and
    # ending the patient's conversation at a nurse queue over it is exactly the
    # reflex this phase exists to remove. Every gate below is re-applied to the
    # retry unchanged; nothing is waived, and a second bad answer still fails
    # closed.
    for attempt in range(2):
        try:
            async with asyncio.timeout(
                get_settings().llm_request_timeout_seconds
            ):
                candidate = await llm.with_structured_output(
                    TriageEvaluation
                ).ainvoke(
                    prompt
                    if attempt == 0
                    else f"{prompt}\n\n{_REGROUNDING_REMINDER}"
                )
            if not isinstance(candidate, TriageEvaluation):
                candidate = TriageEvaluation.model_validate(candidate)
        except Exception as exc:
            print(f"[Triage Reasoner] Structured reasoning failed closed: {exc}")
            return _insufficient_result(
                "Bộ suy luận không trả về kết quả hợp lệ",
                handoff_reason="REASONER_INVALID_OUTPUT",
            )
        result = candidate
        is_gap = candidate.decision in {
            "NEED_MORE_PATIENT_INFO",
            "NEED_MORE_EVIDENCE",
        }
        citations_ground = bool(candidate.citation_ids) and set(
            candidate.citation_ids
        ).issubset(public_citation_ids_precheck)
        if not is_gap or citations_ground:
            break

    assert result is not None  # the loop either breaks with one or returns

    public_citation_ids = {
        str(item.get("id")) for item in citations if item.get("id")
    }
    criteria_by_citation: dict[str, set[str]] = {}
    for item in evidence:
        citation_id = str(item.get("citation_id") or "").strip()
        if not citation_id:
            continue
        criteria_by_citation.setdefault(citation_id, set()).update(
            str(criterion).strip()
            for criterion in item.get("protocol_criteria", [])
            if str(criterion).strip()
        )
    # A citation is usable only when both the patient-facing citation DTO and
    # the private evidence atom exist. Criteria are then checked against the
    # exact cited atoms, not against a turn-wide union that could accidentally
    # pair a citation from document A with a criterion from document B.
    allowed_citation_ids = public_citation_ids.intersection(criteria_by_citation)
    citations_are_grounded = bool(result.citation_ids) and set(
        result.citation_ids
    ).issubset(allowed_citation_ids)
    cited_criteria: set[str] = set()
    for citation_id in result.citation_ids:
        cited_criteria.update(criteria_by_citation.get(citation_id, set()))
    # Two different questions, deliberately kept apart.
    #
    # ``criteria_are_grounded`` asks "did the model prove the patient meets a
    # criterion?" -- the right bar for a PROPOSE, which asserts an ESI level.
    #
    # ``criteria_are_not_fabricated`` asks only "is everything it named real?".
    # That is the right bar for a *gap*: NEED_MORE_PATIENT_INFO and
    # NEED_MORE_EVIDENCE exist precisely because no criterion has been matched
    # yet, so demanding a matched criterion to justify asking a question is a
    # contradiction in terms. It was also the single reason ordinary
    # conversations could never adapt: the reasoner would correctly ask for the
    # missing fact, the empty ``matched_criteria`` would fail this check, and
    # the question was rewritten into a nurse handoff.
    criteria_are_grounded = bool(result.matched_criteria) and set(
        result.matched_criteria
    ).issubset(cited_criteria)
    criteria_are_not_fabricated = set(result.matched_criteria).issubset(
        cited_criteria
    )

    if result.decision == "ABSTAIN":
        reason = "; ".join(result.uncertainty_reasons) or result.reasoning
        return _insufficient_result(
            f"Bộ suy luận chủ động ABSTAIN: {reason}",
            handoff_reason="REASONER_ABSTAINED",
        )

    if result.decision == "CONTRADICTORY_DATA":
        # The model cannot create a contradiction. Canonical state is the only
        # authority, and a real one was handled before the model was invoked.
        return _insufficient_result(
            "Bộ suy luận báo contradiction không tồn tại trong canonical state",
            handoff_reason="CONTRADICTION_NOT_IN_CANONICAL_STATE",
        )

    if result.decision == "NEED_MORE_PATIENT_INFO":
        target = result.requested_fact
        # A gap must still be anchored to authority the gate accepted, and it
        # may not name a criterion that does not exist. It simply does not have
        # to match one.
        if (
            target is None
            or not citations_are_grounded
            or not criteria_are_not_fabricated
        ):
            return _insufficient_result(
                "Yêu cầu hỏi thêm không gắn với authority đã kiểm định",
                handoff_reason="QUESTION_NOT_GROUNDED_IN_AUTHORITY",
            )
        if question_budget_spent:
            # The model was told the budget was spent and asked anyway. Failing
            # closed is right, but it must be recorded as a budget stop rather
            # than as "the evidence was insufficient", which is a different
            # finding about a different thing.
            return _insufficient_result(
                "Đã dùng hết số lượt hỏi thêm dữ kiện cho ca này",
                handoff_reason="EVIDENCE_QUESTION_BUDGET_EXHAUSTED",
            )
        if not _target_is_unresolved(target, state):
            # The question space for this target is closed: it is already
            # answered, or it has been asked as often as policy allows.
            return _insufficient_result(
                f"Fact '{target}' đã được biết hoặc đã hỏi đủ số lần cho phép",
                handoff_reason="QUESTION_TARGET_ALREADY_RESOLVED",
            )
        reason = "; ".join(result.uncertainty_reasons) or result.reasoning
        return _patient_info_result(
            target,
            reason,
            citation_ids=result.citation_ids,
        )

    if result.decision == "NEED_MORE_EVIDENCE":
        if int(state.get("retrieval_refinement_count") or 0) >= refinement_limit:
            update = _insufficient_result(
                "Evidence vẫn chưa đủ sau lượt refinement được phép",
                handoff_reason="REFINEMENT_BUDGET_EXHAUSTED",
            )
            update["retrieval_refinement_stop_reason"] = "MAX_ATTEMPTS"
            return update
        if not citations_are_grounded or not criteria_are_not_fabricated:
            return _insufficient_result(
                "Yêu cầu refinement không liên kết với authority đã kiểm định",
                handoff_reason="REFINEMENT_NOT_GROUNDED_IN_AUTHORITY",
            )
        return _evidence_refinement_result(result)

    # PROPOSE keeps the strict bar. Asserting an ESI level requires the model
    # to name the criterion it matched, inside the document it cited.
    if (
        not citations_are_grounded
        or not result.matched_criteria
        or not criteria_are_grounded
    ):
        return _insufficient_result(
            "Bộ suy luận không liên kết được proposal với citation/criterion đã kiểm định",
            handoff_reason="PROPOSAL_NOT_GROUNDED",
        )

    safe_response = filter_output_diagnosis(result.reasoning)
    used_citation_ids = set(result.citation_ids)
    used_citations = [
        citation
        for citation in citations
        if str(citation.get("id")) in used_citation_ids
    ]
    message = {
        "id": str(uuid.uuid4()),
        "sender": "bot",
        "timestamp": datetime.now(UTC).isoformat(),
        "content": safe_response,
        "step": 3,
        "ragCitations": used_citations,
    }
    return {
        "step": 3,
        "current_esi_level": result.esi_level,
        "preliminary_esi_reasoning": safe_response,
        "rag_citations": used_citations,
        "turn_rag_citations": used_citations,
        "messages": [message],
        "response": safe_response,
        "response_type": "TRIAGE_PROPOSAL",
        "workflow_phase": "REASONING",
        "decision_status": "PROPOSED",
        "evidence_status": "SUFFICIENT",
        "evidence_sufficiency_outcome": "READY_FOR_REASONING",
        "uncertainty_reasons": [],
        "matched_protocol_criteria": result.matched_criteria,
        "next_step": "summary_creator",
    }
