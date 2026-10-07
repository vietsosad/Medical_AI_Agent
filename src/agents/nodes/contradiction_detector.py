"""Detect conflicting patient-reported facts before retrieval or ESI reasoning."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from src.agents.state import AgentState


@dataclass(frozen=True)
class ContradictionEvaluation:
    contradictions: list[dict[str, Any]]
    has_unresolved: bool


def detect_contradictions(
    pending_fact_updates: list[dict[str, Any]],
    existing_contradictions: list[dict[str, Any]] | None = None,
) -> ContradictionEvaluation:
    """Merge newly disputed facts without losing their turn-level provenance."""
    merged = [
        dict(item)
        for item in (existing_contradictions or [])
        if item.get("status", "UNRESOLVED") == "UNRESOLVED"
    ]
    known = {
        (
            item.get("field"),
            str(item.get("previous_value")),
            str(item.get("conflicting_value")),
            item.get("conflicting_turn_id"),
        )
        for item in merged
    }
    for update in pending_fact_updates:
        if update.get("status") != "DISPUTED":
            continue
        contradiction = {
            "field": str(update.get("field") or "unknown"),
            "previous_value": update.get("previous_value"),
            "conflicting_value": update.get("value"),
            "previous_turn_id": str(
                update.get("previous_turn_id") or "legacy-checkpoint"
            ),
            "conflicting_turn_id": str(
                update.get("source_turn_id") or "unknown-turn"
            ),
            "previous_raw_span": str(update.get("previous_raw_span") or ""),
            "conflicting_raw_span": str(update.get("raw_span") or ""),
            "status": "UNRESOLVED",
        }
        key = (
            contradiction["field"],
            str(contradiction["previous_value"]),
            str(contradiction["conflicting_value"]),
            contradiction["conflicting_turn_id"],
        )
        if key not in known:
            known.add(key)
            merged.append(contradiction)

    return ContradictionEvaluation(
        contradictions=merged,
        has_unresolved=bool(merged),
    )


async def detect_contradictions_node(state: AgentState) -> dict[str, Any]:
    evaluation = detect_contradictions(
        state.get("pending_fact_updates", []),
        state.get("unresolved_contradictions", []),
    )
    if not evaluation.has_unresolved:
        return {
            "unresolved_contradictions": [],
            "next_step": "readiness_evaluator",
        }

    fields = list(
        dict.fromkeys(
            f"contradiction:{item.get('field', 'unknown')}"
            for item in evaluation.contradictions
        )
    )
    return {
        "unresolved_contradictions": evaluation.contradictions,
        "missing_critical_fields": fields,
        "uncertainty_reasons": [
            "Có thông tin người bệnh cung cấp không nhất quán; cần xác nhận trước khi truy xuất phác đồ"
        ],
        "decision_status": "NEEDS_CLARIFICATION",
        "workflow_phase": "CLARIFICATION",
        "current_esi_level": None,
        "sbar_report": None,
        "turn_rag_citations": [],
        "next_step": "question_engine",
    }
