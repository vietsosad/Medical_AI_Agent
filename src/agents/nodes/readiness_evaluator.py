"""Risk-aware readiness: what *this* presentation still needs, not a fixed form.

Readiness used to run one checklist against every patient, so a possible
myocardial infarction and a sprained ankle produced the same residual question
list. It also read a flat blueprint, where a fact nobody asked about and a fact
the patient denied were indistinguishable.

Both are fixed here. Requirements come from the presentation's profile in
``clinical_requirements``, and every requirement is evaluated against the
ClinicalStateView, so:

* an UNKNOWN only blocks when its answer could change this case's triage;
* a NEGATED fact is answered, not missing;
* an UNCERTAIN answer produces clarification rather than being read as KNOWN;
* a value observed this morning does not satisfy a requirement for now.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from src.agents.canonical_state import CanonicalPatientState
from src.agents.confirmation_lifecycle import (
    evaluate_confirmation,
    fact_snapshot,
)
from src.agents.clinical_requirements import (
    POLICY_REVIEW_STATUS,
    POLICY_VERSION,
    profile_for,
)
from src.agents.clinical_state_view import ClinicalStateView
from src.agents.problem_state import build_problem_state_from_agent_state
from src.agents.question_planning import plan_from_agent_state
from src.agents.state import AgentState, DecisionStatus

VAGUE_COMPLAINTS = {"không khỏe", "khong khoe", "khó chịu", "kho chiu", "mệt", "met"}

# Session-level gates that are not clinical facts about the patient's body.
# They stay in the evaluator because they come from the EHR/consent workflow
# rather than from anything the patient said this turn.
_WORKFLOW_REASONS = {
    "recent_procedure_context": (
        "Thông tin phẫu thuật/thủ thuật gần đây chưa được làm rõ"
    ),
    "clinical_memory_update_detail": (
        "Người bệnh báo EHR đã thay đổi nhưng chưa nêu nội dung"
    ),
    "clinical_memory_confirmation": (
        "Bệnh nền, dị ứng và thuốc từ EHR chưa được xác nhận lại"
    ),
}

# Gates that come from the EHR/consent workflow rather than from the patient's
# body. They still have to be satisfied before reasoning, but they must never
# be the *first* thing the conversation asks about and must never stand in for
# clinical characterisation -- see the ordering in
# ``evaluate_pre_retrieval_readiness_node``.
WORKFLOW_GATE_FIELDS: frozenset[str] = frozenset(_WORKFLOW_REASONS)

ReadinessOutcome = str  # READY | NOT_READY | NEEDS_CLARIFICATION | REQUIRES_ESCALATION


def _adaptive_enabled() -> bool:
    try:
        from src.config import get_settings

        return bool(get_settings().adaptive_questioning_enabled)
    except Exception:  # noqa: BLE001 - configuration must never break the gate
        return True


def _questions_per_turn() -> int:
    try:
        from src.config import get_settings

        return int(get_settings().adaptive_max_questions_per_turn)
    except Exception:  # noqa: BLE001
        return 1


@dataclass(frozen=True)
class ReadinessEvaluation:
    ready: bool
    decision_status: DecisionStatus
    missing_critical_fields: list[str]
    confidence: float
    uncertainty_reasons: list[str]
    symptom_cluster: str | None
    outcome: ReadinessOutcome = "NOT_READY"
    # Unknowns that could change triage for this presentation, as opposed to
    # everything that merely happens to be absent.
    decision_relevant_unknowns: list[str] = None  # type: ignore[assignment]
    relevant_uncertainties: list[str] = None  # type: ignore[assignment]

    def __post_init__(self) -> None:
        if self.decision_relevant_unknowns is None:
            object.__setattr__(self, "decision_relevant_unknowns", [])
        if self.relevant_uncertainties is None:
            object.__setattr__(self, "relevant_uncertainties", [])


def infer_symptom_cluster(blueprint: dict[str, Any]) -> str | None:
    """PRESENTATION ONLY. Lexical cluster guess from blueprint wording.

    .. warning::
       Not for clinical decisions. This classifies by string matching, with no
       notion of negation, tense or certainty, so it will happily label a case
       "chest_pain" from "tôi không đau ngực" or from a symptom last reported a
       week ago.

       ``symptom_cluster`` selects the readiness requirement profile, filters
       which protocols are in scope during retrieval, and must match the
       calibration profile at the evidence gate. Every one of those reads
       ``ClinicalStateView.symptom_cluster()``, which is canonical-only.

       Kept for display grouping and for legacy callers holding nothing but a
       blueprint. ``test_source_of_truth_invariants`` fails if a decision path
       calls it again.
    """
    complaints = " ".join(
        str(item).strip().lower()
        for item in blueprint.get("chief_complaint", [])
        if str(item).strip()
    )
    cluster_terms = (
        ("chest_pain", ("đau ngực", "chest pain", "tức ngực")),
        ("dyspnea", ("khó thở", "dyspnea", "shortness of breath")),
        ("abdominal_pain", ("đau bụng", "abdominal pain")),
        ("headache", ("đau đầu", "headache")),
        ("fever", ("sốt", "fever")),
        ("gastrointestinal", ("tiêu chảy", "nôn", "buồn nôn")),
    )
    for cluster, terms in cluster_terms:
        if any(term in complaints for term in terms):
            return cluster
    return "other_specific" if complaints else None


def _requirement_is_satisfied(
    view: ClinicalStateView,
    blueprint: dict[str, Any],
    fact_key: str,
    requires_current: bool,
    vital_signs_status: str = "NOT_REVIEWED",
) -> bool:
    """Whether we already know enough to stop asking about this requirement.

    Every clinical fact is read from canonical state. ``blueprint`` is consulted
    only for the structured vitals form, which is a workflow artefact rather
    than a fact the canonical model owns; that exception is asserted by
    ``test_source_of_truth_invariants``.
    """
    if fact_key == "chief_complaint":
        complaints = view.current_complaints()
        specific = [
            item
            for item in complaints
            if item.strip().lower() not in VAGUE_COMPLAINTS
        ]
        return bool(specific) or bool(view.present_symptoms())
    if fact_key == "associated_symptoms":
        return bool(view.current_associated()) or len(view.present_symptoms()) > 1
    if fact_key == "vital_signs":
        # Workflow slot, not a canonical clinical fact. "I have no way to
        # measure" is an answer, not a gap.
        return bool(blueprint.get("vital_signs")) or vital_signs_status in {
            "PATIENT_REPORTED",
            "UNAVAILABLE_CONFIRMED",
        }

    reading = view.read(fact_key)
    if reading.is_present or reading.is_negated:
        # A denial is an answer. Asking again would be asking a question the
        # patient already answered.
        if requires_current and reading.temporal not in {
            "CURRENT",
            "AFTER_MEDICATION",
            "UNKNOWN_TIME",
            "RELATIVE",
            None,
        }:
            return False
        return True
    return False


def evaluate_readiness(
    blueprint: dict[str, Any],
    *,
    clinical_memory_confirmation_status: str = "CONFIRMED",
    vital_signs_status: str = "UNAVAILABLE_CONFIRMED",
    clinical_context_update_pending: bool = False,
    clinical_memory_update_pending: bool = False,
    unresolved_contradictions: list[dict[str, Any]] | None = None,
    view: ClinicalStateView | None = None,
) -> ReadinessEvaluation:
    """Decide what this presentation still needs before reasoning may run."""
    state_view = view or ClinicalStateView(CanonicalPatientState())
    # Canonical only. A cluster with no canonical evidence behind it would pick
    # the requirement profile, the retrieval scope filter and the evidence-gate
    # calibration from lexical guesswork.
    cluster = state_view.symptom_cluster()
    profile = profile_for(cluster)

    missing: list[str] = []
    reasons: list[str] = []
    decision_relevant_unknowns: list[str] = []
    relevant_uncertainties: list[str] = []

    if unresolved_contradictions:
        for contradiction in unresolved_contradictions:
            field = str(contradiction.get("field") or contradiction.get("key") or "unknown")
            missing.append(f"contradiction:{field}")
        reasons.append("Còn thông tin mâu thuẫn chưa được người bệnh xác nhận")

    for requirement in profile.requirements:
        satisfied = _requirement_is_satisfied(
            state_view,
            blueprint,
            requirement.fact_key,
            requirement.requires_current,
            vital_signs_status,
        )
        reading = state_view.read(requirement.fact_key)

        # Hedged answers are never promoted to known. When the ambiguity could
        # change this presentation's triage, it becomes a clarification.
        if reading.is_uncertain and requirement.kind in {
            "REQUIRED",
            "CLARIFY_IF_UNCERTAIN",
        }:
            relevant_uncertainties.append(requirement.fact_key)
            if requirement.question_field not in missing:
                missing.append(requirement.question_field)
                reasons.append(requirement.reason)
            continue

        if satisfied:
            continue
        if requirement.kind == "OPTIONAL":
            # Absent, but not something that changes the decision here.
            continue
        if requirement.kind == "CLARIFY_IF_UNCERTAIN":
            # Only an ambiguous answer blocks; plain absence does not.
            continue

        decision_relevant_unknowns.append(requirement.fact_key)
        if requirement.question_field not in missing:
            missing.append(requirement.question_field)
            reasons.append(requirement.reason)

    # Workflow gates, independent of the clinical presentation.
    if clinical_context_update_pending:
        missing.append("recent_procedure_context")
        reasons.append(_WORKFLOW_REASONS["recent_procedure_context"])
    if clinical_memory_update_pending:
        missing.append("clinical_memory_update_detail")
        reasons.append(_WORKFLOW_REASONS["clinical_memory_update_detail"])
    elif clinical_memory_confirmation_status == "NOT_REVIEWED":
        missing.append("clinical_memory_confirmation")
        reasons.append(_WORKFLOW_REASONS["clinical_memory_confirmation"])

    total = max(1, len(profile.requirements))
    confidence = max(0.0, min(1.0, (total - len(decision_relevant_unknowns)) / total))

    if missing:
        outcome = "NEEDS_CLARIFICATION" if relevant_uncertainties else "NOT_READY"
    else:
        outcome = "READY"

    return ReadinessEvaluation(
        ready=not missing,
        decision_status="READY_FOR_EVIDENCE" if not missing else "NEEDS_CLARIFICATION",
        missing_critical_fields=missing,
        confidence=confidence,
        uncertainty_reasons=reasons,
        symptom_cluster=cluster,
        outcome=outcome,
        decision_relevant_unknowns=decision_relevant_unknowns,
        relevant_uncertainties=relevant_uncertainties,
    )


async def evaluate_readiness_node(state: AgentState) -> dict[str, Any]:
    view = ClinicalStateView.from_agent_state(state)
    evaluation = evaluate_readiness(
        state.get("clinical_blueprint", {}),
        clinical_memory_confirmation_status=state.get(
            "clinical_memory_confirmation_status",
            "NOT_REVIEWED",
        ),
        vital_signs_status=state.get("vital_signs_status", "NOT_REVIEWED"),
        clinical_context_update_pending=state.get(
            "clinical_context_update_pending",
            False,
        ),
        clinical_memory_update_pending=state.get(
            "clinical_memory_update_pending",
            False,
        ),
        unresolved_contradictions=(
            state.get("unresolved_contradictions", [])
            or view.unresolved_contradictions()
        ),
        view=view,
    )
    is_confirmed = evaluation.ready and state.get("patient_confirmed_intake") is True
    return {
        "missing_critical_fields": evaluation.missing_critical_fields,
        "extraction_confidence": evaluation.confidence,
        "uncertainty_reasons": evaluation.uncertainty_reasons,
        "symptom_cluster": evaluation.symptom_cluster,
        "decision_status": evaluation.decision_status,
        "readiness_outcome": evaluation.outcome,
        "decision_relevant_unknowns": evaluation.decision_relevant_unknowns,
        "relevant_uncertainties": evaluation.relevant_uncertainties,
        "intake_confirmation_status": (
            "CONFIRMED"
            if is_confirmed
            else "AWAITING_CONFIRMATION"
            if evaluation.ready
            else "NOT_READY"
        ),
        "workflow_phase": (
            "REASONING"
            if is_confirmed
            else "PATIENT_CONFIRMATION"
            if evaluation.ready
            else "CLARIFICATION"
        ),
        "next_step": (
            "retrieve_evidence"
            if is_confirmed
            else "patient_confirmation"
            if evaluation.ready
            else "question_engine"
        ),
    }


def evaluate_pre_retrieval_readiness(
    blueprint: dict[str, Any],
    *,
    clinical_memory_confirmation_status: str = "CONFIRMED",
    clinical_context_update_pending: bool = False,
    clinical_memory_update_pending: bool = False,
    unresolved_contradictions: list[dict[str, Any]] | None = None,
    view: ClinicalStateView | None = None,
    accepted_unknown_targets: frozenset[str] | set[str] | None = None,
) -> ReadinessEvaluation:
    """Apply only deterministic gates required before authority retrieval.

    Presentation profiles in :mod:`clinical_requirements` are explicitly
    provisional and therefore cannot decide which clinical fact must be asked
    before the ESI authority has even been retrieved.  The active DeepAgent
    path uses this narrower gate: it requires an attributable current
    complaint, resolves canonical contradictions, and completes EHR workflow
    checks.  Clinical completeness is decided later by the authority-grounded
    structured reasoner.

    The full profile evaluator remains available as a non-blocking audit hint
    and deterministic degraded fallback via :func:`evaluate_readiness`.
    """
    state_view = view or ClinicalStateView(CanonicalPatientState())
    cluster = state_view.symptom_cluster()
    missing: list[str] = []
    reasons: list[str] = []
    relevant_uncertainties: list[str] = []

    if unresolved_contradictions:
        for contradiction in unresolved_contradictions:
            field = str(
                contradiction.get("field")
                or contradiction.get("key")
                or "unknown"
            )
            missing.append(f"contradiction:{field}")
        reasons.append("Còn thông tin mâu thuẫn chưa được người bệnh xác nhận")

    # Retrieval needs a canonical presentation to scope the authority query.
    # This is an engineering/integrity prerequisite, not a clinical claim
    # about which symptom detail changes an ESI decision point.
    exhausted = set(accepted_unknown_targets or ())
    if not _requirement_is_satisfied(
        state_view,
        blueprint,
        "chief_complaint",
        False,
    ):
        hedged_symptoms = state_view.uncertain_symptoms()
        if "chief_complaint" in exhausted and hedged_symptoms:
            # The patient has been asked twice and each time described the same
            # symptom in hedged wording. That is an answer -- it names a
            # presentation retrieval can scope against -- and continuing to
            # treat it as "no complaint given" ended the consultation in a
            # clinician handoff for "question space exhausted", which is not a
            # clinical finding and not what happened.
            relevant_uncertainties.append("chief_complaint")
        else:
            missing.append("chief_complaint")
            reasons.append("Chưa có triệu chứng hoặc lý do đến khám cụ thể")
            if hedged_symptoms:
                relevant_uncertainties.append("chief_complaint")

    # A workflow gate the patient has been asked about as often as policy
    # allows is recorded as unanswered and stops blocking. It must not become a
    # clinician handoff: "we asked twice about your EHR record and you talked
    # about your symptoms instead" is not a clinical finding, and the reasoner
    # already treats an unconfirmed record conservatively -- it may not be used
    # to lower priority. The chief complaint is deliberately excluded, because
    # retrieval genuinely cannot build a query without one.
    if clinical_context_update_pending and (
        "recent_procedure_context" not in exhausted
    ):
        missing.append("recent_procedure_context")
        reasons.append(_WORKFLOW_REASONS["recent_procedure_context"])
    if clinical_memory_update_pending and (
        "clinical_memory_update_detail" not in exhausted
    ):
        missing.append("clinical_memory_update_detail")
        reasons.append(_WORKFLOW_REASONS["clinical_memory_update_detail"])
    elif (
        not clinical_memory_update_pending
        and clinical_memory_confirmation_status == "NOT_REVIEWED"
        and "clinical_memory_confirmation" not in exhausted
    ):
        missing.append("clinical_memory_confirmation")
        reasons.append(_WORKFLOW_REASONS["clinical_memory_confirmation"])

    missing = list(dict.fromkeys(missing))
    outcome = (
        "NEEDS_CLARIFICATION"
        if relevant_uncertainties
        else "NOT_READY"
        if missing
        else "READY"
    )
    # This confidence describes structural preconditions only. Clinical
    # sufficiency is deliberately left pending until authority evaluation.
    structural_gate_count = 1 + int(clinical_context_update_pending) + int(
        clinical_memory_update_pending
        or clinical_memory_confirmation_status == "NOT_REVIEWED"
    )
    confidence = max(
        0.0,
        min(1.0, (structural_gate_count - len(missing)) / structural_gate_count),
    )
    return ReadinessEvaluation(
        ready=not missing,
        decision_status="READY_FOR_EVIDENCE" if not missing else "NEEDS_CLARIFICATION",
        missing_critical_fields=missing,
        confidence=confidence,
        uncertainty_reasons=reasons,
        symptom_cluster=cluster,
        outcome=outcome,
        # Only the complaint is a patient fact at this boundary. The remaining
        # gaps are workflow or contradiction lifecycle targets.
        decision_relevant_unknowns=(
            ["chief_complaint"] if "chief_complaint" in missing else []
        ),
        relevant_uncertainties=relevant_uncertainties,
    )


async def evaluate_pre_retrieval_readiness_node(
    state: AgentState,
) -> dict[str, Any]:
    """DeepAgent pre-retrieval gate, adaptive question plan, and hints.

    The structural gates are unchanged: retrieval still needs an attributable
    complaint, resolved contradictions and completed EHR workflow. Three things
    changed after the live audit:

    * **Workflow gates no longer outrank clinical characterisation.** The EHR
      review used to be the only thing in ``missing`` on the first two turns, so
      it was the only thing the planner could ask -- the conversation opened by
      asking a patient with a headache to confirm their medication list, and the
      no-information-gain circuit breaker then read those two workflow turns as
      two failed questions and declared the case ready for confirmation without
      having asked a single clinical one.
    * **Confirmation has an owner.** Whether a confirmation still holds is
      decided by :mod:`confirmation_lifecycle` from what changed, not by
      whatever the transport happened to put in this turn's state.
    * **The review is emitted once per fact snapshot.** A reconnect, a refetch
      or a duplicate submit that changes nothing does not produce a second one.
    """
    view = ClinicalStateView.from_agent_state(state)
    contradictions = (
        state.get("unresolved_contradictions", [])
        or view.unresolved_contradictions()
    )
    common = {
        "clinical_memory_confirmation_status": state.get(
            "clinical_memory_confirmation_status",
            "NOT_REVIEWED",
        ),
        "clinical_context_update_pending": state.get(
            "clinical_context_update_pending",
            False,
        ),
        "clinical_memory_update_pending": state.get(
            "clinical_memory_update_pending",
            False,
        ),
        "unresolved_contradictions": contradictions,
        "view": view,
    }
    accepted_unknown = set(
        (state.get("action_loop_state") or {}).get("accepted_unknown_targets") or []
    )
    evaluation = evaluate_pre_retrieval_readiness(
        state.get("clinical_blueprint", {}),
        accepted_unknown_targets=accepted_unknown,
        **common,
    )
    provisional = evaluate_readiness(
        state.get("clinical_blueprint", {}),
        vital_signs_status=state.get("vital_signs_status", "NOT_REVIEWED"),
        **common,
    )
    problem_state = build_problem_state_from_agent_state(state)

    # -- confirmation lifecycle ------------------------------------------
    confirmation = evaluate_confirmation(
        dict(state),
        view,
        newly_mentioned=list(problem_state.newly_mentioned),
        unresolved_contradictions=list(contradictions),
    )
    confirmed = bool(confirmation["patient_confirmed_intake"])
    current_snapshot = confirmation["current_fact_snapshot"]
    stale_reason = confirmation.get("confirmation_stale_reason")

    plan = plan_from_agent_state(state) if _adaptive_enabled() else None
    if not _adaptive_enabled():
        problem_state = None  # type: ignore[assignment]

    # Once the agent has judged the case sufficient and put the summary up, the
    # checkpoint is sticky: a confirmation turn carries no new facts, and
    # without this the planner re-derives the question it had already decided to
    # stop asking, so pressing confirm looks like it did nothing.
    #
    # It reopens for exactly the reasons a confirmation goes stale.
    agent_closed_questioning = bool(state.get("adaptive_questioning_complete"))
    questioning_closed = agent_closed_questioning or confirmed
    reopened = bool(stale_reason) or bool(
        contradictions
        or (
            agent_closed_questioning
            and (problem_state.newly_mentioned if problem_state else [])
        )
    )
    if questioning_closed and not reopened and plan is not None:
        plan.candidates = []
        plan.stop_reason = "SEMANTIC_SUFFICIENT"
        plan.sufficiency = "SUFFICIENT_FOR_CONFIRMATION"

    # -- gate ordering ----------------------------------------------------
    # Structural gates block everything; clinical characterisation comes next;
    # workflow gates are satisfied last, on the way to the review.
    all_missing = list(evaluation.missing_critical_fields)
    structural_missing = [
        field for field in all_missing if field not in WORKFLOW_GATE_FIELDS
    ]
    workflow_missing = [
        field for field in all_missing if field in WORKFLOW_GATE_FIELDS
    ]
    decision_relevant = list(evaluation.decision_relevant_unknowns)
    reasons = list(evaluation.uncertainty_reasons)
    outcome = evaluation.outcome
    target_gain: dict[str, float] = {}
    clinical_missing: list[str] = []

    if plan is not None and plan.should_ask and not structural_missing:
        # Structural gates are clear, but the presentation is not yet
        # characterised. These targets are what the agent wants to know; the
        # action validator still decides whether asking is permitted.
        limit = _questions_per_turn()
        for candidate in plan.candidates[:limit]:
            clinical_missing.append(candidate.target)
            decision_relevant.append(candidate.canonical_key)
            reasons.append(f"Chưa rõ {candidate.reason_vi}")
            target_gain[candidate.target] = candidate.expected_information_gain
        outcome = "NOT_READY"

    missing = [*structural_missing, *clinical_missing, *workflow_missing]
    ready = not missing
    is_confirmed = ready and confirmed

    # -- one review per fact snapshot -------------------------------------
    shown_snapshot = state.get("intake_review_shown_snapshot")
    review_is_new = shown_snapshot != current_snapshot

    update: dict[str, Any] = {
        "missing_critical_fields": missing,
        "extraction_confidence": evaluation.confidence,
        "uncertainty_reasons": reasons,
        "symptom_cluster": evaluation.symptom_cluster,
        "decision_status": (
            "READY_FOR_EVIDENCE" if ready else "NEEDS_CLARIFICATION"
        ),
        "readiness_outcome": "READY" if ready else outcome,
        "decision_relevant_unknowns": decision_relevant,
        "relevant_uncertainties": evaluation.relevant_uncertainties,
        "target_information_gain": target_gain,
        "problem_state": problem_state.to_dict() if problem_state else {},
        "patient_confirmed_intake": confirmed,
        "confirmation_stale_reason": stale_reason,
        "current_fact_snapshot": current_snapshot,
        "intake_review_is_new": review_is_new,
        "adaptive_questioning_complete": bool(
            plan is not None and not plan.should_ask and not missing
        ),
        "question_plan": plan.to_dict() if plan is not None else {},
        "clinical_sufficiency": (
            plan.sufficiency if plan is not None else "SUFFICIENT_FOR_CONFIRMATION"
        ),
        "provisional_readiness_hints": {
            "policy_version": POLICY_VERSION,
            "review_status": POLICY_REVIEW_STATUS,
            "non_blocking": True,
            "symptom_cluster": provisional.symptom_cluster,
            "missing_fields": provisional.missing_critical_fields,
            "decision_relevant_unknowns": provisional.decision_relevant_unknowns,
            "relevant_uncertainties": provisional.relevant_uncertainties,
        },
        "intake_confirmation_status": (
            "CONFIRMED"
            if is_confirmed
            else "AWAITING_CONFIRMATION"
            if ready
            else "NOT_READY"
        ),
        "workflow_phase": (
            "REASONING"
            if is_confirmed
            else "PATIENT_CONFIRMATION"
            if ready
            else "CLARIFICATION"
        ),
        "next_step": (
            "retrieve_evidence"
            if is_confirmed
            else "patient_confirmation"
            if ready
            else "question_engine"
        ),
    }
    if "confirmed_fact_snapshot" in confirmation:
        update["confirmed_fact_snapshot"] = confirmation["confirmed_fact_snapshot"]
    if "confirmation_stale_details" in confirmation:
        update["confirmation_stale_details"] = confirmation[
            "confirmation_stale_details"
        ]
    if is_confirmed and not state.get("confirmed_fact_snapshot"):
        # Record what the patient actually confirmed, so a later change can be
        # told apart from a later addition.
        update["confirmed_fact_snapshot"] = fact_snapshot(view)
    return update
