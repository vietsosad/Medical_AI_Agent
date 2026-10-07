"""ESI derivation from MIETIC decision-point assessments.

The corpus asks Decision Points A, B and C as three separate tasks about the
same patient, so most canonical cases carry only some of them. These tests pin
the rule that an unanswered decision point widens the candidate set instead of
being read as a negative answer — the defect that previously let a bare
resource count label an unscreened patient as mid-acuity.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts" / "knowledge"))

import mietic_common as mc  # noqa: E402

ARTIFACT = Path("data/knowledge/mietic_v2/canonical_cases.enriched.jsonl")


def build_case(**answers: object) -> mc.CanonicalCase:
    assessments = [
        mc.TaskAssessment(point.upper(), f"rec_{point}", 0, value, "regex", "")
        for point, value in answers.items()
        if value is not None
    ]
    return mc.CanonicalCase(
        case_id="c", presentation_text="", presentation_sha256="",
        age_years=None, age_band=None, sex=None, vitals={},
        assessments=assessments,
    )


# --------------------------------------------------------------------------
# decision-point semantics
# --------------------------------------------------------------------------


def test_a_positive_settles_level_one() -> None:
    candidates, status, validated = mc.derive_esi(build_case(a=True))
    assert candidates == [1]
    assert status == "CONSISTENT"
    assert validated == 1


def test_a_negative_alone_asserts_nothing() -> None:
    """Ruling out level 1 does not choose among the rest."""
    candidates, status, validated = mc.derive_esi(build_case(a=False))
    assert candidates == [2, 3, 4, 5]
    assert status == "UNKNOWN"
    assert validated is None


def test_b_is_only_conclusive_once_a_is_answered() -> None:
    unscreened = mc.derive_esi(build_case(b=True))
    assert unscreened[0] == [1, 2], "an unanswered A cannot be assumed negative"
    assert unscreened[2] is None

    screened = mc.derive_esi(build_case(a=False, b=True))
    assert screened == ([2], "CONSISTENT", 2)


def test_resource_count_alone_cannot_label_an_unscreened_patient() -> None:
    """The regression this suite exists for: C is reached only after A and B."""
    candidates, status, validated = mc.derive_esi(build_case(c=0))
    assert 1 in candidates and 2 in candidates
    assert candidates == [1, 2, 5]
    assert status == "UNKNOWN"
    assert validated is None


@pytest.mark.parametrize(
    ("count", "level"), [(0, 5), (1, 4), (2, 3), (5, 3)]
)
def test_resource_count_maps_to_level_once_c_is_reached(count: int, level: int) -> None:
    assert mc.derive_esi(build_case(a=False, b=False, c=count)) == (
        [level], "CONSISTENT", level,
    )


def test_missing_decision_points_stay_unknown_rather_than_guessing() -> None:
    candidates, status, validated = mc.derive_esi(build_case())
    assert candidates == [1, 2, 3, 4, 5]
    assert status == "UNKNOWN"
    assert validated is None


def test_contradictory_answers_assert_no_level() -> None:
    case = mc.CanonicalCase(
        case_id="c", presentation_text="", presentation_sha256="",
        age_years=None, age_band=None, sex=None, vitals={},
        assessments=[
            mc.TaskAssessment("A", "rec_1", 0, True, "regex", ""),
            mc.TaskAssessment("A", "rec_2", 0, False, "regex", ""),
        ],
    )
    _, status, validated = mc.derive_esi(case)
    assert status == "CONFLICTING"
    assert validated is None


def test_analysis_prose_cannot_override_the_structured_answer() -> None:
    """`analysis_text` is provenance; only the parsed answer decides a level.

    The DP-A prompt embeds the ESI-1 knowledge block, so its prose mentions
    "ESI-1" even when the answer is negative.
    """
    case = mc.CanonicalCase(
        case_id="c", presentation_text="", presentation_sha256="",
        age_years=None, age_band=None, sex=None, vitals={},
        assessments=[
            mc.TaskAssessment(
                "A", "rec_1", 0, False, "regex",
                "This patient clearly meets ESI Level 1 criteria.",
            ),
            mc.TaskAssessment("B", "rec_2", 0, False, "regex", "ESI Level 2 applies."),
            mc.TaskAssessment("C", "rec_3", 0, 0, "llm", "Needs ESI Level 3 workup."),
        ],
    )
    assert mc.derive_esi(case) == ([5], "CONSISTENT", 5)


# --------------------------------------------------------------------------
# corpus-wide invariants
# --------------------------------------------------------------------------


def _artifact_records() -> list[dict]:
    if not ARTIFACT.exists():
        pytest.skip("canonical MIETIC artifact has not been built")
    return [
        json.loads(line)
        for line in ARTIFACT.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def test_every_stored_label_equals_its_recomputation() -> None:
    """Stored labels must be a pure function of the stored assessments."""
    mismatched: list[str] = []
    for record in _artifact_records():
        case = mc.CanonicalCase(
            case_id=record["case_id"], presentation_text="", presentation_sha256="",
            age_years=None, age_band=None, sex=None, vitals={},
            assessments=[
                mc.TaskAssessment(
                    a["decision_point"], a["source_record_id"], 0,
                    a["answer"], a["parse_method"], a.get("analysis_text", ""),
                )
                for a in record["assessments"]
            ],
        )
        candidates, status, validated = mc.derive_esi(case)
        if (
            candidates != record["candidate_esi_levels"]
            or status != record["label_status"]
            or validated != record["validated_esi_level"]
        ):
            mismatched.append(record["case_id"])
    assert not mismatched, f"{len(mismatched)} cases disagree, e.g. {mismatched[:3]}"


def test_a_validated_level_never_rests_on_an_unanswered_decision_point() -> None:
    offenders: list[str] = []
    for record in _artifact_records():
        if record["validated_esi_level"] is None:
            continue
        answered = {
            a["decision_point"] for a in record["assessments"] if a["answer"] is not None
        }
        level = record["validated_esi_level"]
        # Level 1 needs only A; every level below it needs A and B settled.
        required = {"A"} if level == 1 else {"A", "B"}
        if not required <= answered:
            offenders.append(f"{record['case_id']}:esi{level}:answered={sorted(answered)}")
    assert not offenders, f"{len(offenders)} unsupported labels, e.g. {offenders[:3]}"


def test_candidates_are_never_empty() -> None:
    """An empty candidate list would read as 'no level is possible'."""
    for record in _artifact_records():
        assert record["candidate_esi_levels"], record["case_id"]


def test_the_build_is_reproducible() -> None:
    """Same input and parser version must yield the same case ids and hashes."""
    records = _artifact_records()
    rebuilt, _ = mc.build_canonical_cases(Path("data/MIETIC_v1.jsonl"))
    assert len(rebuilt) == len(records)
    by_id = {r["case_id"]: r for r in records}
    for case_id, case in rebuilt.items():
        assert case_id in by_id
        assert case.presentation_sha256 == by_id[case_id]["presentation_sha256"]
