"""Offline tests for rejected-candidate repair and demo gating."""

from scripts.build_triage_protocol_simulation import (
    CriterionCheck,
    VerificationIssue,
    VerificationRecord,
)
from scripts.repair_triage_protocol_demo_candidates import (
    _repair_numeric_errors,
    documentary_gate_passes,
)
from tests.test_scripts.test_build_triage_protocol_simulation import (
    _esi_candidate,
)


def _verification(
    *,
    decision: str = "llm_verified",
    issue_severity: str | None = None,
) -> VerificationRecord:
    issues = []
    if issue_severity:
        issues.append(VerificationIssue(
            code="layout_review",
            severity=issue_severity,
            message="Source layout needs review.",
        ))
    return VerificationRecord(
        candidate_id="ahrq_esi_v4_2012_repair_0_1234567890abcdef",
        verification_model="gpt-5-mini",
        verification_prompt_version="triage-protocol-verify-v1",
        decision=decision,
        source_grounding_passed=True,
        triage_system_separation_passed=True,
        criterion_checks=[CriterionCheck(
            criterion_index=0,
            source_supported=True,
            evidence_quote_exact=True,
            numeric_thresholds_preserved=True,
            notes="",
        )],
        issues=issues,
    )


def test_repair_requires_structured_numeric_thresholds() -> None:
    candidate = _esi_candidate()
    criterion = candidate.decision_criteria[0].model_copy(
        update={"numeric_thresholds": []}
    )
    candidate = candidate.model_copy(update={"decision_criteria": [criterion]})

    errors = _repair_numeric_errors(candidate)

    assert "criterion_0_missing_numeric_thresholds" in errors


def test_repair_accepts_complete_structured_numeric_thresholds() -> None:
    candidate = _esi_candidate()

    assert _repair_numeric_errors(candidate) == []


def test_documentary_gate_accepts_warning_only_manual_review() -> None:
    verification = _verification(
        decision="manual_review",
        issue_severity="warning",
    )

    assert documentary_gate_passes(verification) is True


def test_documentary_gate_rejects_any_error_issue() -> None:
    verification = _verification(
        decision="reject",
        issue_severity="error",
    )

    assert documentary_gate_passes(verification) is False
