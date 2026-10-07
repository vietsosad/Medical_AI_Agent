from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class Seed(BaseModel):
    case_id: str
    selected_atom_id: str | None = None
    selected_concept_id: str | None = None
    category: str
    smoke: bool = False
    adversarial_kind: str | None = None
    surface_form: str | None = None
    supplemental_facts: dict[str, Any] = Field(default_factory=dict)
    clinical_review_status: Literal["PENDING_CLINICAL_REVIEW", "CLINICIAN_REVIEWED"] = "PENDING_CLINICAL_REVIEW"


class GoldenCase(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: str = "simple-agent-golden-v1"
    case_id: str
    category: str
    kind: Literal["triage", "guardrail"] = "triage"
    smoke: bool = False
    clinical_review_status: str = "PENDING_CLINICAL_REVIEW"
    profile: dict[str, Any] = Field(default_factory=dict)
    presentation: dict[str, Any]
    expected_state: dict[str, Any] = Field(default_factory=dict)
    adaptive_dialogue: dict[str, Any] = Field(default_factory=dict)
    expected_retrieval: dict[str, Any] = Field(default_factory=dict)
    expected_decision: dict[str, Any] = Field(default_factory=dict)
    expected_safety: dict[str, Any] = Field(default_factory=dict)
    postgres_provenance: dict[str, Any] = Field(default_factory=dict)

    @property
    def expected_esi(self) -> int | None:
        value = self.expected_decision.get("esi")
        return value if isinstance(value, int) and 1 <= value <= 5 else None


class RagasCaseInput(BaseModel):
    """Database-grounded input passed to the five RAGAS metrics."""

    case_id: str
    user_input: str
    response: str
    reference: str
    retrieved_contexts: list[str] = Field(min_length=1, max_length=5)
    grounding_contexts: list[str] = Field(min_length=1)


class RagasResult(BaseModel):
    """Serializable per-case RAGAS result.

    Scores stay nullable so an unavailable metric cannot be confused with a
    genuine zero.  Any applicable case with a missing score is incomplete.
    """

    case_id: str
    ragas_applicable: bool = True
    faithfulness_score: float | None = Field(default=None, ge=0, le=1)
    context_precision_score: float | None = Field(default=None, ge=0, le=1)
    context_recall_score: float | None = Field(default=None, ge=0, le=1)
    context_relevance_score: float | None = Field(default=None, ge=0, le=1)
    answer_relevancy_score: float | None = Field(default=None, ge=0, le=1)
    ragas_score: float | None = Field(default=None, ge=0, le=1)
    metric_reasons: dict[str, str] = Field(default_factory=dict)
    metric_errors: dict[str, str] = Field(default_factory=dict)
    verdict: Literal["pass", "warning", "fail", "incomplete", "skipped"]


class Observation(BaseModel):
    model_config = ConfigDict(extra="allow")

    case_id: str
    category: str
    expected_esi: int | None = None
    predicted_esi: int | None = None
    expected_action: str | None = None
    final_action: str | None = None
    final_route: str | None = None
    passed: bool = False
    undertriage: bool = False
    overtriage: bool = False
    terminal: bool = False
    failure_reason: str | None = None
    session_id: str | None = None
    profile_id: str | None = None
    transcript: list[dict[str, Any]] = Field(default_factory=list)
    question_targets: list[str] = Field(default_factory=list)
    decision_snapshots: list[dict[str, Any]] = Field(default_factory=list)
    persisted_state: dict[str, Any] = Field(default_factory=dict)
    retrieved_atoms: list[dict[str, Any]] = Field(default_factory=list)
    matched_atoms: list[dict[str, Any]] = Field(default_factory=list)
    citations: list[dict[str, Any]] = Field(default_factory=list)
    final_response: str = ""
    case_latency_ms: float | None = None
    backend_error: str | None = None
    safety_violations: list[str] = Field(default_factory=list)
