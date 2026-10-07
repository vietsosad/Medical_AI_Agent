"""Vi-Node 0: deterministic emergency reflex and monotonic safety lock.

The recall-oriented matcher runs before every LLM call. A positive match from
the existing deterministic safety rules immediately locks the turn:

    deterministic match -> CONFIRMED / DETERMINISTIC_REFLEX

The contextual model may attach semantic observations afterwards, but it has no
authority to clear the flag, increase the numeric ESI level, or resume intake.
"""

from typing import Any

from src.agents.guardrails import screen_red_flag_candidate
from src.agents.nodes.contextual_emergency_detector import (
    EMERGENCY_GUIDANCE,
    build_emergency_escalation_update,
)
from src.agents.state import AgentState


def _deterministic_reflex_is_locked(state: AgentState) -> bool:
    return bool(
        state.get("is_red_flag")
        and state.get("red_flag_status") == "CONFIRMED"
        and state.get("emergency_detection_source") == "DETERMINISTIC_REFLEX"
    )


def _locked_reflex_update(
    state: AgentState,
    candidate: dict[str, Any] | None,
) -> dict[str, Any]:
    """Create or preserve a deterministic lock; a later rule may only escalate."""
    was_locked = _deterministic_reflex_is_locked(state)
    candidate_esi = int(candidate.get("candidate_esi") or 5) if candidate else 5
    existing_esi = int(
        state.get("current_esi_level")
        or state.get("red_flag_candidate_esi")
        or (candidate_esi if candidate else 2)
    )
    candidate_is_more_urgent = candidate is not None and (
        not was_locked or candidate_esi < existing_esi
    )

    if candidate_is_more_urgent:
        esi_level = candidate_esi
        reason = str(candidate.get("trigger_keyword") or "Dấu hiệu cần đánh giá khẩn")
        safety_rule_id = str(candidate.get("safety_rule_id") or "REFLEX_RULE_V1")
        latency_ms = candidate.get("latency_ms")
    else:
        esi_level = existing_esi
        reason = str(
            state.get("red_flag_candidate_reason")
            or state.get("red_flag_reason")
            or "Dấu hiệu cần đánh giá khẩn"
        )
        safety_rule_id = str(state.get("safety_rule_id") or "REFLEX_RULE_V1")
        latency_ms = state.get("red_flag_latency_ms")

    resolution_reason = str(
        state.get("red_flag_resolution_reason")
        or "Quy tắc an toàn xác định đã kích hoạt khóa cấp cứu."
    )
    metadata = dict(state.get("metadata") or {})
    metadata["deterministic_reflex_lock"] = {
        "locked": True,
        "safety_rule_id": safety_rule_id,
        "esi_level": esi_level,
    }

    return {
        **build_emergency_escalation_update(
            state,
            status="CONFIRMED",
            esi_level=esi_level,
            guidance=EMERGENCY_GUIDANCE,
            reason=reason,
            safety_rule_id=safety_rule_id,
            source="DETERMINISTIC_REFLEX",
            resolution_reason=resolution_reason,
            latency_ms=latency_ms,
            confidence=1.0,
        ),
        "red_flag_candidate_reason": reason,
        "red_flag_candidate_esi": esi_level,
        "semantic_emergency_status": (
            state.get("semantic_emergency_status") if was_locked else "NOT_RUN"
        ),
        "semantic_emergency_confidence": (
            state.get("semantic_emergency_confidence") if was_locked else None
        ),
        "semantic_emergency_category": (
            state.get("semantic_emergency_category") if was_locked else None
        ),
        "semantic_emergency_signals": (
            list(state.get("semantic_emergency_signals") or []) if was_locked else []
        ),
        "semantic_emergency_reason": (
            state.get("semantic_emergency_reason") if was_locked else None
        ),
        "workflow_phase": "SAFETY_CHECK",
        "metadata": metadata,
    }


async def detect_redflag_node(state: AgentState) -> dict:
    """Run the fast rules and lock any positive result before model work."""
    candidate = screen_red_flag_candidate(state.get("query", ""))

    if _deterministic_reflex_is_locked(state):
        print("[Red-Flag Reflex] Preserving deterministic emergency lock")
        return _locked_reflex_update(state, candidate)

    if candidate is None and state.get("red_flag_status") in {
        "UNCERTAIN",
        "MONITORING",
    }:
        # An open concern from a previous turn stays open. The patient is
        # answering our safety clarification, and that answer usually contains no
        # keyword at all ("Đang xảy ra với tôi ngay bây giờ"), so re-screening the
        # reply alone would silently drop the very candidate we asked about.
        #
        # MONITORING is carried the same way and for a stronger reason: nobody
        # asked about it, so the escalating answer will arrive inside an
        # ordinary reply ("đau 9 trên 10") with no keyword in it at all. A watch
        # that forgets between turns is not a watch.
        print(
            "[Red-Flag Screen] Carrying forward unresolved candidate "
            f"'{state.get('red_flag_candidate_reason')}' for re-validation"
        )
        return {
            "is_red_flag": False,
            # Carried at its own level. Promoting a MONITORING concern to
            # CANDIDATE would hand it to the branch that confirms on currency
            # alone, so "khó thở" followed by "đau 3 trên 10" would escalate on
            # the strength of the symptom still being present -- which is the
            # very over-triage this band exists to prevent.
            "red_flag_status": (
                "MONITORING"
                if state.get("red_flag_status") == "MONITORING"
                else "CANDIDATE"
            ),
            "red_flag_candidate_reason": state.get("red_flag_candidate_reason"),
            "red_flag_candidate_esi": state.get("red_flag_candidate_esi"),
            "red_flag_resolution_reason": None,
            "safety_rule_id": state.get("safety_rule_id"),
            "red_flag_latency_ms": state.get("red_flag_latency_ms"),
            "current_esi_level": None,
            "emergency_detection_source": None,
            "semantic_emergency_status": "NOT_RUN",
            "semantic_emergency_confidence": None,
            "semantic_emergency_category": None,
            "semantic_emergency_signals": [],
            "semantic_emergency_reason": None,
            "workflow_phase": "SAFETY_CHECK",
            "turn_rag_citations": [],
            "next_step": "contextual_emergency_detector",
        }

    if candidate:
        print(
            f"[Red-Flag Reflex] Locked '{candidate['trigger_keyword']}' in "
            f"{candidate['latency_ms']}ms"
        )
        return _locked_reflex_update(state, candidate)

    return {
        "is_red_flag": False,
        "red_flag_status": "NO_CANDIDATE",
        "red_flag_candidate_reason": None,
        "red_flag_candidate_esi": None,
        "red_flag_resolution_reason": None,
        "workflow_phase": "SAFETY_CHECK",
        "turn_rag_citations": [],
        "safety_rule_id": None,
        "emergency_detection_source": None,
        "semantic_emergency_status": "NOT_RUN",
        "semantic_emergency_confidence": None,
        "semantic_emergency_category": None,
        "semantic_emergency_signals": [],
        "semantic_emergency_reason": None,
        "next_step": "contextual_emergency_detector",
    }
