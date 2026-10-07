"""Registry of clinical configuration that no clinician has reviewed.

Several tables in this codebase encode clinical judgement: which Vietnamese
words name which symptom, which phrases mean "now" versus "last week", which
keywords deserve an emergency screen, which vital thresholds are critical. They
were written by engineers. They work, and they are better than what preceded
them, but none of them is a validated medical guideline.

The risk this module exists to prevent is silent promotion: a provisional table
being treated, six months later, as though it had been approved. Everything
listed here reports ``PENDING_CLINICAL_REVIEW`` until a named reviewer and a
date replace that.

Nothing here grounds a clinical claim. Protocol grounding remains the job of the
evidence gate, which accepts only approved, versioned, clinician-reviewed
documents.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

ReviewStatus = Literal["PENDING_CLINICAL_REVIEW", "CLINICIAN_APPROVED", "RETIRED"]

GovernedArtifactKind = Literal[
    "SYMPTOM_LEXICON",
    "TEMPORAL_MARKERS",
    "RED_FLAG_SCREEN",
    "VITAL_THRESHOLDS",
    "SEVERITY_SCALE",
    "REQUIREMENT_PROFILE",
    "PATIENT_FACING_WORDING",
    "CONVERSATION_POLICY",
]


@dataclass(frozen=True)
class GovernedArtifact:
    """One piece of clinical configuration and its review standing."""

    name: str
    kind: GovernedArtifactKind
    module: str
    what_it_decides: str
    risk_if_wrong: str
    review_status: ReviewStatus = "PENDING_CLINICAL_REVIEW"
    reviewed_by: str | None = None
    reviewed_at: str | None = None

    @property
    def is_clinically_validated(self) -> bool:
        return self.review_status == "CLINICIAN_APPROVED" and bool(self.reviewed_by)


GOVERNED_ARTIFACTS: tuple[GovernedArtifact, ...] = (
    GovernedArtifact(
        name="SYMPTOM_LEXICON",
        kind="SYMPTOM_LEXICON",
        module="src/agents/nodes/fact_extraction.py",
        what_it_decides=(
            "Which Vietnamese wordings become which canonical symptom, and "
            "therefore which presentation profile a case is judged under."
        ),
        risk_if_wrong=(
            "A symptom outside the lexicon yields no canonical fact, so the case "
            "falls to the undifferentiated profile and usually fails the protocol "
            "scope match. Fail-closed to nurse handoff, but coverage is limited."
        ),
    ),
    GovernedArtifact(
        name="TEMPORAL_MARKERS",
        kind="TEMPORAL_MARKERS",
        module="src/agents/nodes/temporal_context.py",
        what_it_decides=(
            "Whether a statement describes the patient now, in the past, or "
            "relative to medication or an event."
        ),
        risk_if_wrong=(
            "A current symptom misread as historical drops out of the "
            "presentation entirely; the reverse asserts a finding that has "
            "resolved."
        ),
    ),
    GovernedArtifact(
        name="RED_FLAG_SCREEN_KEYWORDS",
        kind="RED_FLAG_SCREEN",
        module="src/agents/guardrails.py",
        what_it_decides=(
            "Which phrases raise a RED_FLAG_CANDIDATE for contextual validation."
        ),
        risk_if_wrong=(
            "A missing keyword means no candidate is raised at all, and the "
            "contextual validator never gets the chance to escalate. Recall here "
            "matters more than precision."
        ),
    ),
    GovernedArtifact(
        name="PATIENT_REPORTED_VITAL_THRESHOLDS",
        kind="VITAL_THRESHOLDS",
        module="src/agents/guardrails.py::_vital_redflag",
        what_it_decides=(
            "Which patient-reported vital values raise an emergency candidate "
            "(SpO2, heart rate, systolic BP, GCS)."
        ),
        risk_if_wrong=(
            "Thresholds set too high miss a deteriorating patient; too low "
            "floods the nurse queue and erodes trust in the alert."
        ),
    ),
    GovernedArtifact(
        name="SEVERITY_DESCRIPTOR_SCALE",
        kind="SEVERITY_SCALE",
        module="src/agents/nodes/severity_extraction.py",
        what_it_decides=(
            "The 0-10 score assigned to verbal intensity (nhẹ/vừa/nặng/dữ dội)."
        ),
        risk_if_wrong=(
            "A mapped score enters the reasoner prompt and the retrieval query as "
            "though the patient had named a number."
        ),
    ),
    GovernedArtifact(
        name="REQUIREMENT_PROFILES",
        kind="REQUIREMENT_PROFILE",
        module="src/agents/clinical_requirements.py",
        what_it_decides=(
            "What each presentation must establish before triage reasoning runs."
        ),
        risk_if_wrong=(
            "An omitted requirement lets a case reach reasoning under-informed; "
            "an excessive one asks a distressed patient unnecessary questions."
        ),
    ),
    GovernedArtifact(
        name="EMERGENCY_AND_FALLBACK_WORDING",
        kind="PATIENT_FACING_WORDING",
        module="src/agents/nodes/contextual_emergency_detector.py",
        what_it_decides=(
            "The exact Vietnamese instructions a patient receives when the "
            "system escalates or takes a precaution."
        ),
        risk_if_wrong=(
            "Wording that under-conveys urgency, or that reads as a diagnosis, "
            "changes what a frightened patient actually does next."
        ),
    ),
    GovernedArtifact(
        name="QUESTION_PRIORITY_ORDERING",
        kind="CONVERSATION_POLICY",
        module="src/agents/next_best_action.py::_gain",
        what_it_decides=(
            "Which unknown is asked about first when several are missing -- "
            "chief complaint before severity, severity before associated "
            "symptoms, and so on."
        ),
        risk_if_wrong=(
            "Ordering is why a patient in distress is asked one thing rather "
            "than another. A poor order does not make triage unsafe on its own, "
            "because readiness still requires every field, but it lengthens the "
            "conversation before the decisive fact is obtained, and a patient "
            "who abandons the conversation early is triaged on less."
        ),
    ),
    GovernedArtifact(
        name="REPEAT_QUESTION_POLICY",
        kind="CONVERSATION_POLICY",
        module="src/agents/next_best_action.py::MAX_REPEATS_PER_TARGET",
        what_it_decides=(
            "How many times one fact may be asked about before the system "
            "accepts it as UNKNOWN and moves on. Currently two."
        ),
        risk_if_wrong=(
            "Too few attempts and a recoverable fact is written off as unknown, "
            "narrowing what the nurse receives. Too many and a distressed or "
            "confused patient is pressed repeatedly for something they cannot "
            "give. The value is an engineering judgement about conversation, "
            "but it decides what a real patient experiences."
        ),
    ),
)


def pending_clinical_review() -> list[GovernedArtifact]:
    """Everything still awaiting clinician sign-off."""
    return [
        artifact
        for artifact in GOVERNED_ARTIFACTS
        if not artifact.is_clinically_validated
    ]


def is_any_artifact_claiming_validation() -> bool:
    """Guard: nothing shipped may claim clinical validation."""
    return any(artifact.is_clinically_validated for artifact in GOVERNED_ARTIFACTS)
