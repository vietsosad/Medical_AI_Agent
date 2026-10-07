"""Nothing provisional may present itself as validated clinical guidance."""

from __future__ import annotations

from src.agents.clinical_governance import (
    GOVERNED_ARTIFACTS,
    is_any_artifact_claiming_validation,
    pending_clinical_review,
)


def test_no_shipped_clinical_artifact_claims_validation() -> None:
    assert is_any_artifact_claiming_validation() is False


def test_every_governed_artifact_is_pending_review() -> None:
    for artifact in GOVERNED_ARTIFACTS:
        assert artifact.review_status == "PENDING_CLINICAL_REVIEW"
        assert artifact.reviewed_by is None
        assert artifact.is_clinically_validated is False


def test_the_review_backlog_covers_every_clinical_table() -> None:
    """A new unreviewed clinical table must be registered, not left invisible."""
    kinds = {artifact.kind for artifact in pending_clinical_review()}
    assert kinds >= {
        "SYMPTOM_LEXICON",
        "TEMPORAL_MARKERS",
        "RED_FLAG_SCREEN",
        "VITAL_THRESHOLDS",
        "SEVERITY_SCALE",
        "REQUIREMENT_PROFILE",
        "PATIENT_FACING_WORDING",
    }


def test_each_artifact_states_what_it_decides_and_the_risk() -> None:
    for artifact in GOVERNED_ARTIFACTS:
        assert artifact.what_it_decides.strip()
        assert artifact.risk_if_wrong.strip()
        assert artifact.module.strip()


def test_the_registry_and_the_requirement_module_agree() -> None:
    from src.agents.clinical_requirements import PROFILES

    assert not any(profile.is_clinically_validated for profile in PROFILES.values())
