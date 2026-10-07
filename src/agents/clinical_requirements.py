"""Clinical requirement policy: what each presentation needs before reasoning.

.. warning::
   **These profiles are PROVISIONAL INTERNAL CONFIGURATION, not a validated
   clinical guideline.** Every requirement below carries
   ``review_status=PENDING_CLINICAL_REVIEW`` and ``source=INTERNAL_PROVISIONAL``
   because no clinician has signed them off. They were written by engineers to
   replace a fixed five-question checklist, which they improve on, but that does
   not make them medical policy.

   Nothing here grounds a clinical claim. Protocol grounding remains the job of
   the evidence gate, which accepts only approved, versioned, clinician-reviewed
   documents. These profiles decide *what to ask the patient next*, never what
   is clinically true and never what ESI applies.

Each requirement is classified so an engineering convenience is never mistaken
for medical policy:

``ENGINEERING``
    Structural: the machinery cannot proceed without it.
``CLINICAL_POLICY``
    A judgement about what matters for this presentation. Needs clinician review.
``SAFETY``
    Present to avoid missing a time-critical finding. Needs clinician review.
``WORKFLOW``
    Consent, EHR confirmation and similar process gates.

The profile set is a versioned policy object, so requirements can later be
loaded from a reviewed, dated configuration without touching orchestration code.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

RequirementKind = Literal[
    # The fact must be known before reasoning; its absence blocks.
    "REQUIRED",
    # Absence is acceptable, but a hedged answer must be clarified.
    "CLARIFY_IF_UNCERTAIN",
    # Useful background; never blocks on its own.
    "OPTIONAL",
]

RequirementClass = Literal[
    "ENGINEERING",
    "CLINICAL_POLICY",
    "SAFETY",
    "WORKFLOW",
]

RequirementSource = Literal[
    # Written in-house, unreviewed. The only value currently in use.
    "INTERNAL_PROVISIONAL",
    # Reserved for requirements traced to an approved external document.
    "AHRQ_ESI_HANDBOOK",
    "MOH_VN_PROTOCOL",
    "CLINICIAN_REVIEWED",
]

ReviewStatus = Literal[
    "PENDING_CLINICAL_REVIEW",
    "CLINICIAN_APPROVED",
    "RETIRED",
]

# Bumped whenever a requirement changes, so a decision can be traced to the
# policy version that produced it.
POLICY_VERSION = "0.1.0-provisional"

# No requirement in this file has been reviewed. When that changes, individual
# requirements get their own status and this stops being true.
POLICY_REVIEW_STATUS: ReviewStatus = "PENDING_CLINICAL_REVIEW"


@dataclass(frozen=True)
class RequirementProvenance:
    """Where a requirement came from, and whether anyone qualified approved it."""

    source: RequirementSource = "INTERNAL_PROVISIONAL"
    review_status: ReviewStatus = "PENDING_CLINICAL_REVIEW"
    reviewed_by: str | None = None
    effective_date: str | None = None
    citation: str | None = None

    @property
    def is_clinically_validated(self) -> bool:
        """False for everything currently shipped. Do not present as guidance."""
        return (
            self.review_status == "CLINICIAN_APPROVED"
            and self.source != "INTERNAL_PROVISIONAL"
        )


PROVISIONAL = RequirementProvenance()


@dataclass(frozen=True)
class ClinicalRequirement:
    """One thing we need to know, why it matters, and on whose authority."""

    fact_key: str
    kind: RequirementKind
    # The clarification slot the question engine understands.
    question_field: str
    reason: str
    requirement_class: RequirementClass = "CLINICAL_POLICY"
    provenance: RequirementProvenance = PROVISIONAL
    # When true, a historical observation cannot satisfy it - we need the
    # patient's status now (a fever this morning is not a fever now).
    requires_current: bool = True


@dataclass(frozen=True)
class RequirementProfile:
    """The requirement set for one presentation."""

    cluster: str
    requirements: tuple[ClinicalRequirement, ...] = field(default_factory=tuple)
    version: str = POLICY_VERSION
    review_status: ReviewStatus = POLICY_REVIEW_STATUS

    @property
    def is_clinically_validated(self) -> bool:
        return all(
            requirement.provenance.is_clinically_validated
            for requirement in self.requirements
        )


def _complaint() -> ClinicalRequirement:
    return ClinicalRequirement(
        fact_key="chief_complaint",
        kind="REQUIRED",
        question_field="chief_complaint",
        reason="Chưa có triệu chứng chính đủ cụ thể",
        # Structural: with no complaint there is nothing to triage at all.
        requirement_class="ENGINEERING",
    )


def _onset() -> ClinicalRequirement:
    return ClinicalRequirement(
        fact_key="onset_time",
        kind="REQUIRED",
        question_field="onset_time",
        reason="Chưa rõ thời điểm khởi phát",
        requirement_class="CLINICAL_POLICY",
        requires_current=False,
    )


# Chest pain can be an acute coronary syndrome, so severity now, associated
# features and time-course all move the acuity. PROVISIONAL - not from ESI.
_CHEST_PAIN = RequirementProfile(
    cluster="chest_pain",
    requirements=(
        _complaint(),
        _onset(),
        ClinicalRequirement(
            fact_key="severity_score",
            kind="REQUIRED",
            question_field="severity_score",
            reason="Đau ngực cần mức độ hiện tại trước khi đối chiếu tiêu chí",
            requirement_class="CLINICAL_POLICY",
        ),
        ClinicalRequirement(
            fact_key="associated_symptoms",
            kind="REQUIRED",
            question_field="associated_symptoms",
            reason="Đau ngực cần xác nhận dấu hiệu đi kèm",
            requirement_class="SAFETY",
        ),
        ClinicalRequirement(
            fact_key="symptom.dyspnea",
            kind="CLARIFY_IF_UNCERTAIN",
            question_field="associated_symptoms",
            reason="Khó thở kèm đau ngực làm thay đổi mức ưu tiên",
            requirement_class="SAFETY",
        ),
        ClinicalRequirement(
            fact_key="vital_signs",
            kind="OPTIONAL",
            question_field="vital_signs",
            reason="Sinh hiệu hỗ trợ đối chiếu ngưỡng nhưng không bắt buộc",
            requirement_class="WORKFLOW",
        ),
    ),
)

_DYSPNEA = RequirementProfile(
    cluster="dyspnea",
    requirements=(
        _complaint(),
        _onset(),
        ClinicalRequirement(
            fact_key="severity_score",
            kind="REQUIRED",
            question_field="severity_score",
            reason="Mức độ khó thở hiện tại quyết định mức ưu tiên",
            requirement_class="CLINICAL_POLICY",
        ),
        ClinicalRequirement(
            fact_key="vital_signs",
            kind="OPTIONAL",
            question_field="vital_signs",
            reason="SpO₂ và nhịp thở hỗ trợ đánh giá",
            requirement_class="WORKFLOW",
        ),
    ),
)

_FEVER = RequirementProfile(
    cluster="fever",
    requirements=(
        _complaint(),
        _onset(),
        ClinicalRequirement(
            fact_key="vital.temperature_c",
            kind="REQUIRED",
            question_field="vital_signs",
            reason="Cần nhiệt độ hiện tại, không dùng số đo cũ",
            requirement_class="CLINICAL_POLICY",
            requires_current=True,
        ),
        ClinicalRequirement(
            fact_key="associated_symptoms",
            kind="CLARIFY_IF_UNCERTAIN",
            question_field="associated_symptoms",
            reason="Dấu hiệu kèm giúp phân biệt mức độ",
            requirement_class="CLINICAL_POLICY",
        ),
    ),
)

# Time-critical presentations. Deliberately short: these escalate on presence
# through the red-flag path, they are not questionnaires.
_HIGH_ACUITY = tuple(
    RequirementProfile(
        cluster=cluster,
        requirements=(_complaint(), _onset()),
    )
    for cluster in ("syncope", "neurologic", "bleeding")
)

_STANDARD_CLUSTERS = (
    "abdominal_pain",
    "headache",
    "gastrointestinal",
    "musculoskeletal",
    "ent",
    "dermatologic",
    "other_specific",
)
_STANDARD = tuple(
    RequirementProfile(
        cluster=cluster,
        requirements=(
            _complaint(),
            _onset(),
            ClinicalRequirement(
                fact_key="severity_score",
                kind="CLARIFY_IF_UNCERTAIN",
                question_field="severity_score",
                reason="Mức độ khó chịu giúp phân loại",
                requirement_class="CLINICAL_POLICY",
            ),
        ),
    )
    for cluster in _STANDARD_CLUSTERS
)

# No canonical evidence of a presentation yet. All we need is what is wrong.
_UNDIFFERENTIATED = RequirementProfile(
    cluster="undifferentiated",
    requirements=(_complaint(), _onset()),
)

PROFILES: dict[str, RequirementProfile] = {
    profile.cluster: profile
    for profile in (_CHEST_PAIN, _DYSPNEA, _FEVER, *_HIGH_ACUITY, *_STANDARD)
}


def profile_for(cluster: str | None) -> RequirementProfile:
    """The requirement set for a presentation, or the minimal one.

    ``cluster=None`` means canonical state carries no evidence of a
    presentation, so the minimal profile applies. It never falls back to a
    guess.
    """
    if cluster is None:
        return _UNDIFFERENTIATED
    return PROFILES.get(cluster, _UNDIFFERENTIATED)


def clinical_review_dependencies() -> list[dict[str, str]]:
    """Every requirement awaiting clinician sign-off, for the review backlog."""
    pending: list[dict[str, str]] = []
    for profile in (*PROFILES.values(), _UNDIFFERENTIATED):
        for requirement in profile.requirements:
            if requirement.provenance.is_clinically_validated:
                continue
            if requirement.requirement_class not in {"CLINICAL_POLICY", "SAFETY"}:
                continue
            pending.append(
                {
                    "cluster": profile.cluster,
                    "fact_key": requirement.fact_key,
                    "requirement_class": requirement.requirement_class,
                    "reason": requirement.reason,
                    "source": requirement.provenance.source,
                    "review_status": requirement.provenance.review_status,
                }
            )
    return pending
