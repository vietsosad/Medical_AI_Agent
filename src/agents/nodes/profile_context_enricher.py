"""Build a provenance-labelled EHR context before retrieval and reasoning."""

from __future__ import annotations

from typing import Any

from src.agents.state import AgentState


def build_verified_profile_context(
    clinical_memory: dict[str, Any],
    confirmation_status: str,
    updated_at: str | None,
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Return only EHR facts explicitly confirmed during this triage session."""
    usable = confirmation_status == "CONFIRMED"
    context = {
        "age": clinical_memory.get("age"),
        "gender": clinical_memory.get("gender"),
        "height_cm": clinical_memory.get("height_cm"),
        "weight_kg": clinical_memory.get("weight_kg"),
        "bmi": clinical_memory.get("bmi"),
        "blood_type": clinical_memory.get("blood_type"),
        "chronic_conditions": list(clinical_memory.get("chronic_conditions", [])),
        "daily_medications": list(clinical_memory.get("daily_medications", [])),
        "allergies": list(clinical_memory.get("allergies", [])),
    } if usable else {}
    provenance = {
        "source": "EHR_PROFILE",
        "confirmation_status": confirmation_status,
        "updated_at": updated_at,
        "usable_for_reasoning": usable,
    }
    return context, provenance


async def enrich_profile_context_node(state: AgentState) -> dict[str, Any]:
    """Pure partial update; never mutates the checkpointed clinical memory."""
    context, provenance = build_verified_profile_context(
        state.get("clinical_memory", {}),
        state.get("clinical_memory_confirmation_status", "NOT_REVIEWED"),
        state.get("clinical_memory_updated_at"),
    )
    return {
        "verified_profile_context": context,
        "profile_context_provenance": provenance,
        "workflow_phase": "RETRIEVAL",
        "next_step": "bilingual_query_builder",
    }
