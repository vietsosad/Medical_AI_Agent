"""Shared clinical state contract for the tool-gated DeepAgent runtime.

Clinical capabilities return partial updates. The runtime tool adapter is the
only layer allowed to merge those updates into turn-local state.
"""

from __future__ import annotations

import operator
from typing import Annotated, Any, Literal, TypedDict

IntentType = Literal[
    "TRIAGE_NEW_SYMPTOM",
    "TRIAGE_FOLLOW_UP",
    "GREETING_HELP",
    "OUT_OF_SCOPE",
    "UNCLEAR",
    "EMERGENCY_SIGNAL",
    # Safety-relevant, but not an ESI presentation. A patient in crisis must
    # not be routed into symptom slot-filling, and must not fall through to
    # the generic "I did not understand you" reply either.
    "SAFETY_CRISIS_SUPPORT",
]
DecisionStatus = Literal[
    "NOT_APPLICABLE",
    "COLLECTING",
    "NEEDS_CLARIFICATION",
    "READY_FOR_EVIDENCE",
    "READY_FOR_REASONING",
    "AWAITING_PATIENT_CONFIRMATION",
    "INSUFFICIENT_EVIDENCE",
    "RETRIEVAL_FAILURE",
    "PROPOSED",
    "EMERGENCY_ESCALATED",
]
ResponseType = Literal[
    "TEXT",
    "STRUCTURED_QUESTION",
    "INTAKE_REVIEW",
    "EMERGENCY",
    "TRIAGE_PROPOSAL",
    # Safety guidance that is explicitly not a triage conclusion.
    "SAFETY_GUIDANCE",
]
WorkflowPhase = Literal[
    "SAFETY_CHECK",
    "INTENT_CLASSIFICATION",
    "INTAKE_EXTRACTION",
    "CLARIFICATION",
    "PATIENT_CONFIRMATION",
    "RETRIEVAL",
    "REASONING",
    "REASSESSMENT",
    "HANDOFF",
    "COMPLETE",
]
AnswerAlignment = Literal[
    "NOT_APPLICABLE",
    "DIRECT_ANSWER",
    "CLINICAL_CONTEXT_UPDATE",
    "UNCLEAR_ANSWER",
]
ConversationMode = Literal[
    "NEW_INTAKE",
    "FOLLOW_UP",
    "SCOPE_HELP",
    "EMERGENCY",
]
EvidenceStatus = Literal[
    "NOT_REQUESTED",
    "RETRIEVED",
    "INSUFFICIENT_EVIDENCE",
    "RETRIEVAL_FAILURE",
    "CASE_EXAMPLE_SUPPORT",
    "SUFFICIENT",
]
EvidenceSufficiencyOutcome = Literal[
    "NOT_EVALUATED",
    "PENDING_EVALUATION",
    "NEED_MORE_PATIENT_INFO",
    "NEED_MORE_EVIDENCE",
    "CONTRADICTORY_DATA",
    "READY_FOR_REASONING",
    "RETRIEVAL_FAILURE",
    "ABSTAIN",
]
EvidenceAuthorityStatus = Literal[
    "NOT_EVALUATED",
    "REJECTED",
    "DEMO_ONLY",
    "AUTHORIZED",
]
SemanticEmergencyStatus = Literal[
    "NOT_RUN",
    "CLEAR",
    "INCONCLUSIVE",
    "ESCALATED",
    "UNAVAILABLE",
]
RedFlagStatus = Literal[
    # The fast screen found nothing to look at.
    "NO_CANDIDATE",
    # An unresolved legacy/carried safety clarification. Fresh configured-rule
    # matches are locked directly as CONFIRMED by the deterministic reflex.
    "CANDIDATE",
    # A deterministic reflex lock or a semantic/contextual escalation.
    "CONFIRMED",
    # The validator established the mention was historical, negated, third-person,
    # hypothetical or already resolved. The conversation continues normally.
    "NOT_CONFIRMED",
    # A concern worth holding in mind, but not worth interrupting the
    # consultation over. This is what a clinician does with "khó thở" said
    # without qualifiers: they do not stop and call an ambulance, and they do
    # not forget it either -- they carry it while taking the history, and act
    # the moment severity, onset or a second sign makes it real.
    #
    # Not terminal: the conversation continues normally. Re-evaluated on every
    # turn against everything known so far, so it escalates as soon as the
    # evidence arrives rather than only when a keyword does.
    "MONITORING",
    # The validator ran but could not decide. We ask instead of guessing.
    "UNCERTAIN",
    # The validator could not run at all. Escalated as a precaution, never as a
    # clinical finding.
    "SAFETY_FALLBACK",
]

# Only these resolutions may set the derived ``is_red_flag`` flag that locks the
# session, pages the nurse queue and drives the frontend overlay. A CANDIDATE
# must never reach them.
ESCALATING_RED_FLAG_STATUSES: frozenset[str] = frozenset(
    {"CONFIRMED", "SAFETY_FALLBACK"}
)


class ClinicalFactProvenance(TypedDict, total=False):
    """Trace one extracted fact back to the exact patient turn."""

    field: str
    value: Any
    source_turn_id: str
    raw_span: str
    status: Literal["CONFIRMED", "DISPUTED", "SUPERSEDED"]
    previous_value: Any
    previous_turn_id: str
    previous_raw_span: str


class ClinicalContradiction(TypedDict, total=False):
    """A conflict that must be resolved before retrieval is allowed."""

    field: str
    previous_value: Any
    conflicting_value: Any
    previous_turn_id: str
    conflicting_turn_id: str
    previous_raw_span: str
    conflicting_raw_span: str
    status: Literal["UNRESOLVED", "RESOLVED"]


class RetrievalChannelResult(TypedDict, total=False):
    """Auditable per-channel retrieval metrics, without patient raw text."""

    channel: Literal["vi_dense", "en_dense", "sparse", "demo_dense"]
    result_count: int
    latency_ms: float
    top_score: float | None
    degraded: bool


class ClinicalBlueprint(TypedDict, total=False):
    """Bản đồ triệu chứng JSON (Slot-filling) định hướng truy xuất RAG."""
    chief_complaint: list[str]          # Mảng từ khóa triệu chứng chính (không dùng câu văn dài)
    clinical_keywords_en: list[str]     # Dịch chuẩn y khoa sang EN (vd: "chest pain") tối ưu cho Pgvector BM25
    onset_time: str | None              # Thời điểm khởi phát
    severity_score: int | None          # Mức độ nghiêm trọng (1-10)
    radiation: str | None               # Hướng lan
    associated_symptoms: list[str]      # Các triệu chứng kèm theo
    current_medication: list[str]       # Thuốc đang sử dụng
    recent_procedure: str | None        # Thủ thuật/phẫu thuật gần đây do người bệnh khai
    clinical_context_note: str | None   # Đính chính EHR dạng nguyên văn, không tự ghi đè hồ sơ
    vital_signs: dict[str, Any]          # Chỉ số có nhãn do người bệnh cung cấp
    vital_signs_source: str | None       # Nguồn do người bệnh chọn trong biểu mẫu
    vital_signs_measured_at: str | None  # Thời điểm đo do người bệnh nhập
    confidence_score: float             # Độ tự tin của dữ liệu thu thập (0.0 - 1.0)


class VerifiedProfileContext(TypedDict, total=False):
    """EHR facts permitted for retrieval/reasoning after patient confirmation."""

    age: int | None
    gender: str | None
    height_cm: float | None
    weight_kg: float | None
    bmi: float | None
    blood_type: str | None
    chronic_conditions: list[str]
    daily_medications: list[str]
    allergies: list[str]


class ProfileContextProvenance(TypedDict, total=False):
    source: Literal["EHR_PROFILE"]
    confirmation_status: str
    updated_at: str | None
    usable_for_reasoning: bool


class AgentState(TypedDict, total=False):
    """State schema toàn diện cho bộ clinical tools của DeepAgent supervisor.

    Mỗi node (Red-Flag, Intake, Question Engine, Reasoner, Summary) đọc và ghi dữ liệu lâm sàng
    tuần tự vào state này qua cơ chế immitation & partial update dicts.
    """

    # 1. Định danh và Cổng Vào (Session & Target Family Profile)
    session_id: str
    current_turn_id: str
    query: str  # Tin nhắn/triệu chứng mới nhất từ bệnh nhân
    selected_option_id: str | None  # Mã lựa chọn cấu trúc của lượt hiện tại
    step: int   # Bước hiện tại trong luồng hỏi bệnh (1: Tiếp nhận | 2: Làm rõ | 3: Suy luận | 4: Chốt SBAR)

    profile_id: str
    patient_name: str
    relationship_type: str  # SELF | CHILD | SPOUSE | PARENT | SIBLING | OTHER
    patient_age: int | None
    patient_gender: str | None

    # 2. Ký ức Lâm sàng Tiêm Tự Động từ EHRProfile (Memory Injection)
    clinical_memory: dict[str, Any]  # {"chronic_conditions": [], "daily_medications": [], "allergies": []}
    clinical_memory_updated_at: str | None
    clinical_memory_confirmation_status: Literal[
        "NOT_REVIEWED",
        "CONFIRMED",
        "UPDATED_BY_PATIENT",
        "UNCERTAIN",
    ]
    confirmed_clinical_memory_updated_at: str | None
    clinical_context_update_pending: bool
    clinical_memory_update_pending: bool
    verified_profile_context: VerifiedProfileContext
    profile_context_provenance: ProfileContextProvenance
    vital_signs_status: Literal[
        "NOT_REVIEWED",
        "PATIENT_REPORTED",
        "UNAVAILABLE_CONFIRMED",
        "UNCERTAIN",
    ]
    special_instructions: list[str]  # e.g., "Pediatric guidelines applies", "Geriatric assessment mode"

    # 3. Lịch sử Cuộc Vời & Nguồn Bằng Chứng (Accumulative Reducers)
    messages: Annotated[list[dict[str, Any]], operator.add]      # Diễn biến chuỗi tin nhắn giữa User & Agent
    rag_citations: Annotated[list[dict[str, Any]], operator.add] # Mảng minh chứng RAG chống bịa đặt (Provenance)
    turn_rag_citations: list[dict[str, Any]]

    # 4. Biểu Mẫu Trắc Nghiệm Cấu Trúc (Structured Question Engine) & Blueprint
    structured_question: dict[str, Any] | None # Form trắc nghiệm chèn vào chat (Single, Multiple, Scale)
    active_question: dict[str, Any] | None
    answer_alignment: AnswerAlignment
    answer_alignment_reason: str
    clinical_blueprint: ClinicalBlueprint      # JSON lưu trạng thái slot-filling
    # Canonical Patient State, serialized. This is the source of truth for
    # clinical facts; ``clinical_blueprint`` above is a derived read-model kept
    # for the readiness, retrieval and reasoning consumers that predate it.
    canonical_state: dict[str, Any]
    canonical_state_version: int
    # Keys whose change could move triage. Set by the state layer; the decision
    # layer uses them to know a prior conclusion is stale.
    pending_reassessment_keys: list[str]
    requires_triage_reassessment: bool
    # Two extractors read one utterance differently. Auditable, and explicitly
    # NOT a patient contradiction.
    extraction_disagreements: list[dict[str, Any]]

    # Adaptive loop. The planner proposes; the validator decides; both are
    # recorded so a turn's action is explainable after the fact.
    conversation_memory: dict[str, Any]
    action_loop_state: dict[str, Any]
    selected_action: dict[str, Any] | None
    action_validation: dict[str, Any] | None
    context_assembly_audit: dict[str, Any] | None
    has_unresolved_reference: bool
    readiness_outcome: str
    # Problem-oriented projection of canonical state, plus the adaptive
    # question plan built from it. Both are derived read-models: they hold no
    # fact canonical state does not already own.
    problem_state: dict[str, Any]
    question_plan: dict[str, Any]
    clinical_sufficiency: str
    # Per-target expected information gain for this turn's open questions.
    target_information_gain: dict[str, float]
    # Whether the last patient message produced any new canonical observation.
    information_gained_last_turn: bool
    # Whether the agent has already read its understanding of the problem list
    # back to the patient, so it is not repeated before every question.
    adaptive_opening_sent: bool
    # Whether the agent has judged the case sufficiently characterised. Sticky:
    # confirming a summary must not send the patient back into questioning. It
    # reopens only when a new problem or a contradiction appears.
    adaptive_questioning_complete: bool
    # Non-blocking output of the provisional presentation profiles. The active
    # DeepAgent may audit or use it as degraded fallback, but it cannot prevent
    # authority retrieval or choose the normal-path clinical question.
    provisional_readiness_hints: dict[str, Any]
    decision_relevant_unknowns: list[str]
    relevant_uncertainties: list[str]
    clinical_fact_provenance: dict[str, list[ClinicalFactProvenance]]
    pending_fact_updates: list[ClinicalFactProvenance]
    unresolved_contradictions: list[ClinicalContradiction]
    missing_critical_fields: list[str]
    extraction_confidence: float
    retrieved_evidence: list[dict[str, Any]]
    evidence_status: EvidenceStatus
    evidence_sufficiency_outcome: EvidenceSufficiencyOutcome
    evidence_document_type: str | None
    evidence_authority_status: EvidenceAuthorityStatus
    available_protocol_criteria: list[str]
    matched_protocol_criteria: list[str]
    uncertainty_reasons: list[str]
    evidence_requested_fact: str | None
    evidence_gap_citation_ids: list[str]
    # Short structured code for why a turn ended in a clinician handoff. The
    # patient-facing wording is identical in every case; this is what an audit
    # reads to tell "no authority evidence" apart from "the patient stopped
    # answering" apart from "the output firewall rejected a proposal".
    handoff_reason: str | None
    intake_summary: dict[str, Any]
    patient_confirmed_intake: bool
    intake_confirmation_status: Literal[
        "NOT_READY",
        "AWAITING_CONFIRMATION",
        "CONFIRMED",
    ]
    # How many times the intake review has been put to the patient. Used only
    # to stop the same wording repeating verbatim after they answer it.
    intake_confirmation_prompt_count: int

    # 5. Kết quả Phán Quyết Lâm Sàng & Phiếu SBAR
    current_esi_level: int | None # Cấp độ ESI do AI ước lượng (1 -> 5)
    preliminary_esi_reasoning: str | None
    # Derived, confirmed-only. True only when red_flag_status is CONFIRMED or
    # SAFETY_FALLBACK. Never set directly from a keyword match.
    is_red_flag: bool
    red_flag_status: RedFlagStatus
    red_flag_candidate_reason: str | None   # What the fast screen matched on
    red_flag_candidate_esi: int | None      # Rule-owned acuity for a match/lock
    red_flag_resolution_reason: str | None  # Why the validator resolved as it did
    red_flag_reason: str | None   # Lý do kích hoạt báo động đỏ
    safety_rule_id: str | None
    red_flag_latency_ms: float | None
    emergency_detection_source: Literal[
        "DETERMINISTIC_REFLEX",
        "SEMANTIC_LLM",
        "CONTEXTUAL_VALIDATION",
        "SAFETY_FALLBACK",
    ] | None
    semantic_emergency_status: SemanticEmergencyStatus
    semantic_emergency_confidence: float | None
    semantic_emergency_category: str | None
    semantic_emergency_signals: list[str]
    semantic_emergency_reason: str | None
    sbar_report: dict[str, Any] | None # {"situation": "...", "background": "...", "assessment": "...", "recommendation": "..."}

    # 6. Nhật Ký Phân Tích Kỹ Thuật & Điều hướng
    context: str
    analysis: str
    response: str
    error: str
    next_step: str
    metadata: dict[str, Any]
    intent: IntentType
    intent_confidence: float
    conversation_mode: ConversationMode
    response_type: ResponseType
    workflow_phase: WorkflowPhase
    decision_status: DecisionStatus
    symptom_cluster: str | None
    retrieval_population: str
    retrieval_query_vi: str
    retrieval_query_en: str
    retrieval_sparse_terms: list[str]
    retrieval_channels: list[RetrievalChannelResult]
    retrieval_degraded_modes: list[str]
    retrieval_error: str | None
    retrieval_audit: dict[str, Any]
    case_support_evidence: list[dict[str, Any]]
    retrieval_refinement_count: int
    retrieval_refined_query: str
    retrieval_decision_point: str | None
    retrieval_facets: list[str]
    # Bounded refinement progress contains only hashes and authority candidate
    # identifiers.  It is turn-local audit/control state, never patient prose.
    retrieval_refinement_signatures: list[str]
    retrieval_candidate_fingerprints: list[str]
    retrieval_seen_candidate_keys: list[str]
    retrieval_refinement_stop_reason: str | None
