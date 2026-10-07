"""Tool-gated clinical workflow exposed to the DeepAgent supervisor."""

from __future__ import annotations

import asyncio
import hashlib
import json
import time
from collections.abc import Awaitable, Callable
from contextvars import ContextVar
from typing import Any

from langchain_core.tools import BaseTool, tool

from src.agents.action_validator import validate_action
from src.agents.clinical_state_view import ClinicalStateView
from src.agents.deepagent_runtime.events import phase_completed, phase_started
from src.agents.deepagent_runtime.schemas import DeepAgentToolCallAudit
from src.agents.guardrails import filter_output_diagnosis
from src.agents.nodes.action_planner import (
    execute_selected_action_node,
    plan_next_action_node,
    update_conversation_memory_node,
)
from src.agents.nodes.answer_validator import validate_answer_node
from src.agents.nodes.bilingual_query_builder import build_bilingual_query_node
from src.agents.nodes.contradiction_detector import detect_contradictions_node
from src.agents.nodes.contextual_emergency_detector import (
    assess_contextual_emergency_node,
    reassess_monitored_concern,
)
from src.agents.nodes.evidence_gate import (
    build_insufficient_evidence_handoff,
    build_retrieval_failure_response,
    respond_to_insufficient_evidence_node,
    retrieve_evidence_node,
)
from src.agents.nodes.intake_analyzer import analyze_patient_intake
from src.agents.nodes.intent_classifier import (
    classify_intent_node,
    respond_to_non_triage_intent_node,
)
from src.agents.nodes.profile_context_enricher import enrich_profile_context_node
from src.agents.nodes.readiness_evaluator import (
    evaluate_pre_retrieval_readiness_node,
)
from src.agents.nodes.redflag_detector import detect_redflag_node
from src.agents.nodes.summary_creator import create_sbar_summary_node
from src.agents.nodes.triage_reasoner import run_triage_reasoner_node
from src.agents.next_best_action import ActionContext, NextBestAction
from src.config import get_rag_refinement_attempt_limit

NodeCallable = Callable[[dict[str, Any]], Awaitable[dict[str, Any]]]
_ACCUMULATING_FIELDS = {"messages", "rag_citations"}
_TRIAGE_INTENTS = {"TRIAGE_NEW_SYMPTOM", "TRIAGE_FOLLOW_UP"}


def _normalized_refinement_signature(state: dict[str, Any]) -> str:
    """Hash the meaningful retrieval controls, ignoring cosmetic variation."""

    def normalized(value: object) -> str:
        return " ".join(str(value or "").casefold().split())

    payload = {
        "query": normalized(state.get("retrieval_refined_query")),
        "decision_point": normalized(state.get("retrieval_decision_point")),
        "facets": sorted(
            {
                normalized(item)
                for item in (state.get("retrieval_facets") or [])
                if normalized(item)
            }
        ),
    }
    if not payload["query"] and not payload["decision_point"] and not payload["facets"]:
        return ""
    encoded = json.dumps(payload, ensure_ascii=True, sort_keys=True).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _candidate_keys(state: dict[str, Any]) -> list[str]:
    """Stable authority-candidate identities, independent of ranking scores."""
    keys: set[str] = set()
    for item in state.get("retrieved_evidence") or []:
        if not isinstance(item, dict):
            continue
        citation_id = str(
            item.get("citation_id") or item.get("protocol_code") or ""
        ).strip()
        if not citation_id:
            continue
        provenance = item.get("provenance") or {}
        content_hash = (
            str(provenance.get("retrieval_text_sha256") or "").strip()
            if isinstance(provenance, dict)
            else ""
        )
        keys.add(f"{citation_id}:{content_hash}" if content_hash else citation_id)
    return sorted(keys)


def _candidate_fingerprint(keys: list[str]) -> str:
    if not keys:
        return ""
    return hashlib.sha256("\n".join(keys).encode("utf-8")).hexdigest()


def _initialize_refinement_progress(context: TurnContext) -> None:
    """Seed progress tracking from the initial authority candidate set."""
    keys = _candidate_keys(context.state)
    fingerprint = _candidate_fingerprint(keys)
    signatures = list(context.state.get("retrieval_refinement_signatures") or [])
    fingerprints = list(context.state.get("retrieval_candidate_fingerprints") or [])
    seen_keys = set(context.state.get("retrieval_seen_candidate_keys") or [])
    seen_keys.update(keys)
    if fingerprint and fingerprint not in fingerprints:
        fingerprints.append(fingerprint)
    context.apply_update(
        {
            "retrieval_refinement_signatures": signatures,
            "retrieval_candidate_fingerprints": fingerprints,
            "retrieval_seen_candidate_keys": sorted(seen_keys),
            "retrieval_refinement_stop_reason": None,
        }
    )


def _stop_refinement(
    context: TurnContext,
    *,
    code: str,
    reason: str,
) -> None:
    """Record the bounded-loop stop condition and fail closed."""
    context.apply_update({"retrieval_refinement_stop_reason": code})
    _fail_closed_output(context, reason, handoff_reason=f"REFINEMENT_{code}")


class TurnContext:
    """Mutable turn-local state; only deterministic tools may update it."""

    def __init__(
        self,
        state: dict[str, Any],
        event_queue: asyncio.Queue[dict[str, Any]] | None = None,
    ) -> None:
        self.state = state
        self.event_queue = event_queue
        self.audit: list[DeepAgentToolCallAudit] = []
        self.called_tools: set[str] = set()

    async def emit(self, event: dict[str, Any]) -> None:
        if self.event_queue is not None:
            await self.event_queue.put(event)

    def apply_update(self, update: dict[str, Any]) -> None:
        for key, value in update.items():
            if key in _ACCUMULATING_FIELDS and isinstance(value, list):
                previous = self.state.get(key, [])
                self.state[key] = [*previous, *value]
            else:
                self.state[key] = value

    async def run_node(self, name: str, node: NodeCallable) -> dict[str, Any]:
        await self.emit(phase_started(name).as_dict())
        started = time.perf_counter()
        try:
            update = await node(self.state)
            self.apply_update(update)
            self.audit.append(
                DeepAgentToolCallAudit(
                    tool_name=name,
                    status="SUCCEEDED",
                    elapsed_ms=(time.perf_counter() - started) * 1000,
                )
            )
            await self.emit(phase_completed(name, update).as_dict())
            return update
        except Exception as exc:
            self.audit.append(
                DeepAgentToolCallAudit(
                    tool_name=name,
                    status="FAILED",
                    elapsed_ms=(time.perf_counter() - started) * 1000,
                    detail=type(exc).__name__,
                )
            )
            raise

    def reject_tool(self, name: str, reason: str) -> dict[str, Any]:
        self.audit.append(
            DeepAgentToolCallAudit(
                tool_name=name,
                status="REJECTED",
                elapsed_ms=0.0,
                detail=reason,
            )
        )
        return {
            "status": "REJECTED",
            "reason": reason,
            "allowed_next_tools": self.allowed_next_tools(),
        }

    def allowed_next_tools(self) -> list[str]:
        if turn_is_terminal(self.state):
            return ["verify_clinical_output"]
        if "assess_contextual_emergency" not in self.called_tools:
            return ["assess_contextual_emergency"]
        if "classify_request" not in self.called_tools:
            return ["classify_request"]
        if self.state.get("intent") not in _TRIAGE_INTENTS:
            return ["verify_clinical_output"]
        if "update_intake" not in self.called_tools:
            return ["update_intake"]
        if self.state.get("next_step") != "retrieve_evidence":
            return ["verify_clinical_output"]
        if "retrieve_clinical_evidence" not in self.called_tools:
            return ["retrieve_clinical_evidence"]
        if self.state.get("next_step") == "triage_reasoner":
            return ["reason_and_prepare_handoff"]
        return ["verify_clinical_output"]

    def tool_result(self) -> dict[str, Any]:
        return {
            "status": "OK",
            "decision_status": self.state.get("decision_status"),
            "workflow_phase": self.state.get("workflow_phase"),
            "next_step": self.state.get("next_step"),
            "allowed_next_tools": self.allowed_next_tools(),
        }


_turn_context: ContextVar[TurnContext | None] = ContextVar(
    "medtriage_deepagent_turn_context",
    default=None,
)


def bind_turn_context(context: TurnContext):
    return _turn_context.set(context)


def reset_turn_context(token: Any) -> None:
    _turn_context.reset(token)


def current_turn_context() -> TurnContext:
    context = _turn_context.get()
    if context is None:
        raise RuntimeError("Clinical tool called without an active turn context")
    return context


def turn_is_terminal(state: dict[str, Any]) -> bool:
    """A turn that must stop and answer the patient before any intake work.

    Covers a confirmed emergency, a precautionary safety fallback, and the
    safety clarification we ask when context is genuinely ambiguous.
    """
    return bool(state.get("is_red_flag")) or state.get("red_flag_status") == (
        "UNCERTAIN"
    )


async def run_reflex_screen(context: TurnContext) -> bool:
    """Run the deterministic reflex before any model call.

    Fresh configured-rule matches are locked by ``detect_redflag_node``.  The
    boolean return remains the legacy/open-candidate signal; the supervisor
    reads the state separately for a newly locked deterministic emergency.
    """
    await context.run_node("redflag_detector", detect_redflag_node)
    return context.state.get("red_flag_status") == "CANDIDATE"


async def classify_request_phase(context: TurnContext) -> dict[str, Any]:
    name = "classify_request"
    if "assess_contextual_emergency" not in context.called_tools:
        return context.reject_tool(
            name,
            "assess_contextual_emergency must run first",
        )
    if turn_is_terminal(context.state):
        return context.reject_tool(
            name,
            "Safety resolution stops intent routing for this turn",
        )
    if name in context.called_tools:
        return context.reject_tool(name, "Tool already completed for this turn")
    context.called_tools.add(name)
    await context.run_node("intent_classifier", classify_intent_node)
    if context.state.get("intent") not in _TRIAGE_INTENTS:
        await context.run_node(
            "scope_responder",
            respond_to_non_triage_intent_node,
        )
    return context.tool_result()


async def assess_contextual_emergency_phase(
    context: TurnContext,
) -> dict[str, Any]:
    """Run bounded semantic assessment without weakening reflex authority."""
    name = "assess_contextual_emergency"
    if name in context.called_tools:
        return context.reject_tool(name, "Tool already completed for this turn")
    # Deliberately no is_red_flag guard here.  A locked reflex may be enriched,
    # but the node preserves its rule, ESI and terminal emergency state on every
    # semantic result (including CLEAR, invalid output and provider failure).
    context.called_tools.add(name)
    await context.run_node(
        "contextual_emergency_detector",
        assess_contextual_emergency_node,
    )
    if context.state.get("is_red_flag"):
        await context.run_node("summary_creator", create_sbar_summary_node)
    return context.tool_result()


async def update_intake_phase(context: TurnContext) -> dict[str, Any]:
    name = "update_intake"
    if "classify_request" not in context.called_tools:
        return context.reject_tool(name, "classify_request must run first")
    if context.state.get("intent") not in _TRIAGE_INTENTS:
        return context.reject_tool(name, "Request is outside the triage intake flow")
    if name in context.called_tools:
        return context.reject_tool(name, "Tool already completed for this turn")
    context.called_tools.add(name)

    await context.run_node("answer_validator", validate_answer_node)
    await context.run_node("intake_analyzer", analyze_patient_intake)

    # An open watch is re-tested now that this turn's facts exist. The safety
    # pass ran before extraction and could only judge the sentence; the fact
    # that settles it ("đau khoảng 9 trên 10") is only canonical by this point.
    escalation = reassess_monitored_concern(context.state)
    if escalation is not None:
        context.apply_update(escalation)
        await context.run_node("summary_creator", create_sbar_summary_node)
        return context.tool_result()

    await context.run_node("contradiction_detector", detect_contradictions_node)

    await context.run_node(
        "readiness_evaluator",
        evaluate_pre_retrieval_readiness_node,
    )
    # Safety and readiness have both concluded; only now is an action chosen,
    # and from here the chosen action -- not a status code -- decides what runs.
    # A contradiction no longer short-circuits to the question engine directly:
    # it reaches the planner, which selects CLARIFY for it, so there is one
    # routing authority rather than two that must be kept in agreement.
    await context.run_node("action_planner", plan_next_action_node)
    await context.run_node("action_execution", execute_selected_action_node)
    return context.tool_result()


async def retrieve_evidence_phase(context: TurnContext) -> dict[str, Any]:
    name = "retrieve_clinical_evidence"
    if context.state.get("next_step") != "retrieve_evidence":
        return context.reject_tool(
            name,
            "Intake is not confirmed and ready for evidence retrieval",
        )
    if name in context.called_tools:
        return context.reject_tool(name, "Tool already completed for this turn")
    context.called_tools.add(name)
    # Progress belongs to this confirmed retrieval cycle.  A prior turn's
    # fingerprints must not make the first query of a new cycle look stale.
    context.apply_update(
        {
            "retrieval_refinement_count": 0,
            "retrieval_refinement_signatures": [],
            "retrieval_candidate_fingerprints": [],
            "retrieval_seen_candidate_keys": [],
            "retrieval_refinement_stop_reason": None,
        }
    )

    try:
        await context.run_node("profile_context_enricher", enrich_profile_context_node)
        await context.run_node("bilingual_query_builder", build_bilingual_query_node)
        await context.run_node("retrieve_evidence", retrieve_evidence_node)
    except Exception as exc:  # noqa: BLE001 - operational fail-safe boundary
        context.apply_update(
            build_retrieval_failure_response(
                f"{type(exc).__name__}: {exc}",
                step=int(context.state.get("step") or 3),
            )
        )
    # A failure to look is already a complete, patient-safe operational
    # response. Never send it through the clinical insufficiency responder.
    if context.state.get("decision_status") == "RETRIEVAL_FAILURE":
        return context.tool_result()
    if context.state.get("evidence_status") != "RETRIEVED":
        await context.run_node(
            "insufficient_evidence_responder",
            respond_to_insufficient_evidence_node,
        )
    return context.tool_result()


async def _execute_reasoner_question(context: TurnContext) -> None:
    """Validate and execute the one bounded question selected by the reasoner."""
    state = context.state
    outcome = state.get("evidence_sufficiency_outcome")
    if outcome == "CONTRADICTORY_DATA":
        contradiction = next(
            (
                item
                for item in state.get("unresolved_contradictions", [])
                if isinstance(item, dict)
            ),
            {},
        )
        field = str(
            contradiction.get("field") or contradiction.get("key") or "unknown"
        )
        action = NextBestAction(
            action_type="CLARIFY",
            rationale_code="PATIENT_CONTRADICTION_OPEN",
            target=f"contradiction_{field}",
            priority=85,
            expected_information_gain=1.0,
            policy_dependencies=("contradiction_resolution",),
        )
    else:
        target = str(state.get("evidence_requested_fact") or "")
        action = NextBestAction(
            action_type="ASK",
            rationale_code="DECISION_RELEVANT_UNKNOWN",
            target=target or None,
            priority=80,
            expected_information_gain=1.0,
            policy_dependencies=("esi_authority_evidence",),
            audit_metadata={"selected_by": "structured_evidence_reasoner"},
        )

    action_context = ActionContext.from_agent_state(state)
    validated = validate_action(
        action,
        action_context,
        ClinicalStateView.from_agent_state(state),
        authorized_patient_id=state.get("patient_id") or state.get("profile_id"),
        action_patient_id=state.get("patient_id") or state.get("profile_id"),
        authorized_session_id=state.get("session_id"),
        action_session_id=state.get("session_id"),
    )
    if not validated.may_execute or validated.action is None:
        # The reasoner asked something policy will not allow. That is a real
        # terminal condition, but it must be recorded as one -- not as
        # "evidence was insufficient", which is a different finding entirely.
        _fail_closed_output(
            context,
            validated.detail or "Evidence-driven question was rejected by policy",
            handoff_reason=(
                f"QUESTION_BLOCKED_{validated.block_reason}"
                if validated.block_reason
                else "QUESTION_BLOCKED_BY_POLICY"
            ),
        )
        return

    selected = validated.action.to_dict()
    loop = dict(state.get("action_loop_state") or {})
    asked = dict(loop.get("asked_targets") or {})
    if validated.action.target:
        asked[validated.action.target] = int(
            asked.get(validated.action.target, 0)
        ) + 1
    loop["asked_targets"] = asked
    # Spend one unit of the evidence-question budget. Counted here rather than
    # in the reasoner so a request the validator rejected costs nothing.
    loop["evidence_questions"] = int(loop.get("evidence_questions") or 0) + 1
    context.apply_update(
        {
            "action_loop_state": loop,
            "selected_action": selected,
            "action_validation": {
                **validated.to_dict(),
                "proposed_action": action.action_type,
                "proposed_target": action.target,
                "rationale_code": action.rationale_code,
                "safety_state": action_context.safety_state,
                "readiness_outcome": action_context.readiness_outcome,
                "red_flag_status": action_context.red_flag_status,
                "planner_available": True,
            },
        }
    )
    await context.run_node("evidence_question_execution", execute_selected_action_node)


async def reasoning_phase(context: TurnContext) -> dict[str, Any]:
    name = "reason_and_prepare_handoff"
    if "retrieve_clinical_evidence" not in context.called_tools:
        return context.reject_tool(name, "Evidence retrieval must run first")
    if context.state.get("next_step") != "triage_reasoner":
        return context.reject_tool(name, "Evidence gate did not authorize reasoning")
    if name in context.called_tools:
        return context.reject_tool(name, "Tool already completed for this turn")
    context.called_tools.add(name)

    try:
        _initialize_refinement_progress(context)
        await context.run_node("triage_reasoner", run_triage_reasoner_node)

        while context.state.get("next_step") == "refine_evidence":
            # The loop is bounded twice: Settings has a code-owned hard cap,
            # and this counter is incremented before every retrieval attempt.
            # Progress checks can stop it earlier without asking the model to
            # judge whether its own retry is meaningfully different.
            refinement_limit = get_rag_refinement_attempt_limit()
            refinement_count = int(
                context.state.get("retrieval_refinement_count") or 0
            )
            if refinement_count >= refinement_limit:
                _stop_refinement(
                    context,
                    code="MAX_ATTEMPTS",
                    reason="Evidence remained insufficient after the bounded refinement budget",
                )
                break

            signature = _normalized_refinement_signature(context.state)
            prior_signatures = list(
                context.state.get("retrieval_refinement_signatures") or []
            )
            if not signature or signature in prior_signatures:
                _stop_refinement(
                    context,
                    code="NO_MEANINGFUL_QUERY_CHANGE",
                    reason="Evidence refinement did not provide a meaningfully new bounded query",
                )
                break

            prior_keys = set(
                context.state.get("retrieval_seen_candidate_keys") or []
            )
            prior_fingerprints = list(
                context.state.get("retrieval_candidate_fingerprints") or []
            )
            context.apply_update(
                {
                    "retrieval_refinement_count": refinement_count + 1,
                    "retrieval_refinement_signatures": [
                        *prior_signatures,
                        signature,
                    ],
                }
            )
            try:
                await context.run_node("refine_evidence", retrieve_evidence_node)
            except Exception as exc:  # noqa: BLE001 - operational fail-safe boundary
                context.apply_update(
                    build_retrieval_failure_response(
                        f"{type(exc).__name__}: {exc}",
                        step=int(context.state.get("step") or 3),
                    )
                )
            if context.state.get("decision_status") == "RETRIEVAL_FAILURE":
                context.apply_update(
                    {"retrieval_refinement_stop_reason": "RETRIEVAL_FAILURE"}
                )
                return context.tool_result()
            if context.state.get("evidence_status") != "RETRIEVED":
                context.apply_update(
                    {"retrieval_refinement_stop_reason": "NO_RETRIEVED_CANDIDATES"}
                )
                await context.run_node(
                    "insufficient_evidence_responder",
                    respond_to_insufficient_evidence_node,
                )
                break

            current_keys = _candidate_keys(context.state)
            current_fingerprint = _candidate_fingerprint(current_keys)
            new_keys = set(current_keys).difference(prior_keys)
            if (
                not current_fingerprint
                or current_fingerprint in prior_fingerprints
                or not new_keys
            ):
                _stop_refinement(
                    context,
                    code="NO_NEW_EVIDENCE",
                    reason="Evidence refinement returned no new authority candidates",
                )
                break

            context.apply_update(
                {
                    "retrieval_candidate_fingerprints": [
                        *prior_fingerprints,
                        current_fingerprint,
                    ],
                    "retrieval_seen_candidate_keys": sorted(
                        prior_keys.union(current_keys)
                    ),
                }
            )
            await context.run_node(
                "triage_reasoner_after_refinement",
                run_triage_reasoner_node,
            )

        if context.state.get("evidence_sufficiency_outcome") in {
            "NEED_MORE_PATIENT_INFO",
            "CONTRADICTORY_DATA",
        }:
            await _execute_reasoner_question(context)
        if (
            context.state.get("decision_status") == "PROPOSED"
            and context.state.get("current_esi_level")
        ):
            await context.run_node("summary_creator", create_sbar_summary_node)
    except Exception as exc:  # noqa: BLE001 - clinical fail-safe boundary
        _fail_closed_output(
            context,
            f"Reasoning phase failed safely: {type(exc).__name__}",
            handoff_reason="REASONING_PHASE_ERROR",
        )
    return context.tool_result()


def _fail_closed_output(
    context: TurnContext,
    reason: str,
    *,
    handoff_reason: str = "UNSPECIFIED",
) -> None:
    context.apply_update(
        build_insufficient_evidence_handoff(
            reason,
            step=int(context.state.get("step") or 3),
            handoff_reason=handoff_reason,
        )
    )


async def verify_output_phase(context: TurnContext) -> dict[str, Any]:
    name = "verify_clinical_output"
    if name in context.called_tools:
        return context.reject_tool(name, "Tool already completed for this turn")
    # Unconditional: no turn may produce output without contextual validation,
    # whichever way the fast screen went.
    if "assess_contextual_emergency" not in context.called_tools:
        return context.reject_tool(
            name,
            "assess_contextual_emergency must run first",
        )
    if not turn_is_terminal(context.state):
        if "classify_request" not in context.called_tools:
            return context.reject_tool(name, "classify_request must run first")
        if (
            context.state.get("intent") in _TRIAGE_INTENTS
            and "update_intake" not in context.called_tools
        ):
            return context.reject_tool(name, "update_intake must run first")
        if (
            context.state.get("next_step") == "retrieve_evidence"
            and "retrieve_clinical_evidence" not in context.called_tools
        ):
            return context.reject_tool(
                name,
                "retrieve_clinical_evidence must run first",
            )
        if (
            context.state.get("next_step") == "triage_reasoner"
            and "reason_and_prepare_handoff" not in context.called_tools
        ):
            return context.reject_tool(
                name,
                "reason_and_prepare_handoff must run first",
            )
    context.called_tools.add(name)
    started = time.perf_counter()

    state = context.state
    if state.get("decision_status") == "PROPOSED":
        citations = state.get("turn_rag_citations", [])
        cited_ids = {
            str(item.get("id")) for item in citations if isinstance(item, dict)
        }
        linked_criteria: set[str] = set()
        linked_evidence_ids: set[str] = set()
        for item in state.get("retrieved_evidence", []):
            if not isinstance(item, dict):
                continue
            citation_id = str(item.get("citation_id") or "").strip()
            if citation_id not in cited_ids:
                continue
            linked_evidence_ids.add(citation_id)
            linked_criteria.update(
                str(criterion).strip()
                for criterion in item.get("protocol_criteria", [])
                if str(criterion).strip()
            )
        selected_criteria = {
            str(criterion).strip()
            for criterion in state.get("matched_protocol_criteria", [])
            if str(criterion).strip()
        }
        criterion_link_is_grounded = (
            bool(cited_ids)
            and cited_ids.issubset(linked_evidence_ids)
            and bool(selected_criteria)
            and selected_criteria.issubset(linked_criteria)
        )
        production_authorized = (
            state.get("evidence_status") == "SUFFICIENT"
            and state.get("evidence_authority_status") == "AUTHORIZED"
        )
        if (
            state.get("patient_confirmed_intake") is not True
            or not citations
            or not production_authorized
            or not criterion_link_is_grounded
            or not state.get("sbar_report")
        ):
            _fail_closed_output(
                context,
                "Final clinical output did not satisfy evidence and confirmation gates",
                handoff_reason="OUTPUT_FIREWALL_REJECTED_PROPOSAL",
            )

    await context.run_node(
        "conversation_memory",
        update_conversation_memory_node,
    )

    response = str(state.get("response") or "")
    if response:
        state["response"] = filter_output_diagnosis(response)
    metadata = dict(state.get("metadata") or {})
    metadata["deepagent_tool_gated"] = True
    state["metadata"] = metadata
    context.audit.append(
        DeepAgentToolCallAudit(
            tool_name=name,
            status="SUCCEEDED",
            elapsed_ms=(time.perf_counter() - started) * 1000,
        )
    )
    return context.tool_result()


async def run_remaining_required_tools(context: TurnContext) -> None:
    """Complete a turn safely when the model skips, repeats, or misorders tools."""
    if "assess_contextual_emergency" not in context.called_tools:
        await assess_contextual_emergency_phase(context)
    if turn_is_terminal(context.state):
        await verify_output_phase(context)
        return
    if "classify_request" not in context.called_tools:
        await classify_request_phase(context)
    if context.state.get("intent") in _TRIAGE_INTENTS:
        if "update_intake" not in context.called_tools:
            await update_intake_phase(context)
        if (
            context.state.get("next_step") == "retrieve_evidence"
            and "retrieve_clinical_evidence" not in context.called_tools
        ):
            await retrieve_evidence_phase(context)
        # Checked independently of the retrieval branch above. Nesting it there
        # meant that when the *model* called retrieve_clinical_evidence itself
        # and then stopped -- which is what a provider timeout looks like --
        # the completion path could never reach reasoning, because retrieval
        # had already moved next_step past the condition guarding the branch.
        # The live audit saw those turns end with no reasoning, no answer and
        # the previous message repeated back to the patient.
        if (
            context.state.get("next_step") == "triage_reasoner"
            and "reason_and_prepare_handoff" not in context.called_tools
        ):
            await reasoning_phase(context)
    if "verify_clinical_output" not in context.called_tools:
        await verify_output_phase(context)


def build_clinical_tools() -> list[BaseTool]:
    """Create context-bound tools with small, non-sensitive return payloads."""

    @tool
    async def assess_contextual_emergency() -> dict[str, Any]:
        """Assess contextual emergency risk after reflex preflight; call first."""
        return await assess_contextual_emergency_phase(current_turn_context())

    @tool
    async def classify_request() -> dict[str, Any]:
        """Classify the request after contextual emergency assessment."""
        return await classify_request_phase(current_turn_context())

    @tool
    async def update_intake() -> dict[str, Any]:
        """Validate answers, update intake facts, and choose clarification or confirmation."""
        return await update_intake_phase(current_turn_context())

    @tool
    async def retrieve_clinical_evidence() -> dict[str, Any]:
        """Retrieve and gate approved protocols or explicitly enabled demo cases."""
        return await retrieve_evidence_phase(current_turn_context())

    @tool
    async def reason_and_prepare_handoff() -> dict[str, Any]:
        """Create an evidence-bound ESI proposal and SBAR only after authorization."""
        return await reasoning_phase(current_turn_context())

    @tool
    async def verify_clinical_output() -> dict[str, Any]:
        """Run the mandatory citation, confirmation, and diagnosis-suppression firewall."""
        return await verify_output_phase(current_turn_context())

    return [
        assess_contextual_emergency,
        classify_request,
        update_intake,
        retrieve_clinical_evidence,
        reason_and_prepare_handoff,
        verify_clinical_output,
    ]
