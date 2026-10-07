"""Internal contracts for the DeepAgent supervisor and its safety tools."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any, Literal

from pydantic import BaseModel, Field


class DeepAgentToolCallAudit(BaseModel):
    tool_name: str
    status: Literal["SUCCEEDED", "REJECTED", "FAILED"]
    started_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    elapsed_ms: float = Field(ge=0.0)
    detail: str = ""


class DeepAgentSessionState(BaseModel):
    session_id: str
    clinical_state: dict[str, Any] = Field(default_factory=dict)
    tool_audit: list[DeepAgentToolCallAudit] = Field(default_factory=list)
    execution_mode: Literal[
        "DEEPAGENT",
        "DETERMINISTIC_DEGRADED",
        # Compatibility mode for a carried/open candidate awaiting resolution.
        # Fresh configured-rule matches now use EMERGENCY_CONFIRMED directly.
        "REFLEX_CANDIDATE",
        # Confirmed by deterministic reflex or contextual/semantic escalation.
        "EMERGENCY_CONFIRMED",
        # Emergency the screen had no rule for, found by the model.
        "EMERGENCY_SEMANTIC",
        # Candidate escalated as a precaution because validation could not run.
        "EMERGENCY_SAFETY_FALLBACK",
        # Context was ambiguous, so we asked instead of guessing.
        "SAFETY_CLARIFICATION",
    ] = "DEEPAGENT"
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class DeepAgentStateSnapshot(BaseModel):
    """Small compatibility wrapper used by API recovery paths."""

    values: dict[str, Any] = Field(default_factory=dict)


class DeepAgentTurnResult(BaseModel):
    session_id: str
    state: dict[str, Any]
    execution_mode: str
    tool_audit: list[DeepAgentToolCallAudit] = Field(default_factory=list)


class ClinicalReasoningDecision(BaseModel):
    decision_status: str
    esi_level: int | None = Field(default=None, ge=1, le=5)
    evidence_status: str
    evidence_authority_status: str
    citation_ids: list[str] = Field(default_factory=list)
