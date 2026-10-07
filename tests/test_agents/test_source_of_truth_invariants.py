"""One canonical clinical truth, many read models.

These are the guard rails for the foundation: they fail if a decision-critical
path starts deriving a clinical fact from the legacy blueprint again, or if a
classification appears without canonical evidence behind it.
"""

from __future__ import annotations

import ast
import inspect
from pathlib import Path

import pytest

from src.agents.blueprint_projection import ingest_blueprint, project_blueprint
from src.agents.canonical_state import CanonicalPatientState
from src.agents.clinical_state_view import ClinicalStateView
from src.agents.nodes.fact_extraction import apply_message_to_state
from src.agents.nodes.readiness_evaluator import evaluate_readiness

SRC = Path(__file__).resolve().parents[2] / "src"

# Modules whose job is to make a clinical decision. None of them may classify a
# presentation from blueprint wording.
DECISION_CRITICAL_MODULES = (
    "agents/nodes/readiness_evaluator.py",
    "agents/nodes/bilingual_query_builder.py",
    "agents/nodes/triage_reasoner.py",
    "agents/nodes/evidence_gate.py",
    "agents/clinical_state_view.py",
)


def _state(*messages: str) -> CanonicalPatientState:
    state = CanonicalPatientState()
    for index, message in enumerate(messages):
        apply_message_to_state(state, message, turn_id=f"t{index + 1}")
    return state


def _view(*messages: str) -> ClinicalStateView:
    return ClinicalStateView(_state(*messages))


# --------------------------------------------------------------------------
# The legacy lexical classifier must not return to a decision path
# --------------------------------------------------------------------------

def test_no_decision_path_calls_the_legacy_cluster_inference() -> None:
    """`infer_symptom_cluster` is presentation-only; guard against reuse."""
    offenders: list[str] = []
    for relative in DECISION_CRITICAL_MODULES:
        source = (SRC / relative).read_text(encoding="utf-8")
        tree = ast.parse(source)
        for node in ast.walk(tree):
            if (
                isinstance(node, ast.Call)
                and isinstance(node.func, ast.Name)
                and node.func.id == "infer_symptom_cluster"
            ):
                # Its own definition module may still expose it.
                if relative != "agents/nodes/readiness_evaluator.py":
                    offenders.append(f"{relative}:{node.lineno}")
                elif _is_inside_function(tree, node, "evaluate_readiness"):
                    offenders.append(f"{relative}:{node.lineno}")
    assert offenders == [], (
        "Legacy lexical cluster inference reached a decision path: "
        f"{offenders}. Use ClinicalStateView.symptom_cluster()."
    )


def _is_inside_function(tree: ast.Module, target: ast.AST, name: str) -> bool:
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef) and node.name == name:
            for child in ast.walk(node):
                if child is target:
                    return True
    return False


def test_the_legacy_inference_is_documented_as_non_clinical() -> None:
    from src.agents.nodes.readiness_evaluator import infer_symptom_cluster

    doc = inspect.getdoc(infer_symptom_cluster) or ""
    assert "PRESENTATION ONLY" in doc
    assert "Not for clinical decisions" in doc


# --------------------------------------------------------------------------
# §17 A/B/C - classification requires canonical evidence
# --------------------------------------------------------------------------

def test_historical_only_chest_pain_is_not_a_current_presentation() -> None:
    view = _view("Tuần trước tôi bị đau ngực")
    assert view.symptom_cluster() != "chest_pain"
    assert view.is_present("symptom.chest_pain") is False


def test_negated_chest_pain_is_not_a_current_presentation() -> None:
    view = _view("Tôi không đau ngực")
    assert view.symptom_cluster() != "chest_pain"


def test_a_blueprint_cannot_override_a_canonical_negation() -> None:
    """§17-C: canonical NEGATED beats a positive legacy value."""
    state = _state("Tôi không đau ngực")
    ingest_blueprint(state, {"chief_complaint": ["đau ngực"]}, turn_id="t2")
    view = ClinicalStateView(state)

    assert view.is_negated("symptom.chest_pain") is True
    assert view.symptom_cluster() != "chest_pain"
    assert "đau ngực" not in project_blueprint(state, {})["chief_complaint"]


def test_a_blueprint_cannot_override_canonical_unknown() -> None:
    """A scalar present only in the blueprint never becomes a canonical fact."""
    state = CanonicalPatientState()
    projected = project_blueprint(state, {"severity_score": 9, "onset_time": "8 giờ"})
    assert projected["severity_score"] is None
    assert projected["onset_time"] is None
    assert ClinicalStateView(state).is_unknown("severity_score") is True


def test_readiness_cannot_classify_without_canonical_evidence() -> None:
    evaluation = evaluate_readiness(
        {"chief_complaint": ["đau ngực"], "onset_time": "1 giờ", "severity_score": 9}
    )
    assert evaluation.symptom_cluster is None
    assert evaluation.ready is False


def test_readiness_classifies_once_canonical_evidence_exists() -> None:
    evaluation = evaluate_readiness(
        {}, view=_view("Bây giờ tôi đau ngực"), clinical_memory_confirmation_status="CONFIRMED"
    )
    assert evaluation.symptom_cluster == "chest_pain"


# --------------------------------------------------------------------------
# §17 D - extractor disagreement is not patient contradiction
# --------------------------------------------------------------------------

def test_extractor_disagreement_is_recorded_and_canonical_wins() -> None:
    state = CanonicalPatientState()
    state.record("onset_time", "5 giờ", turn_id="t1")
    ingest_blueprint(state, {"onset_time": "8 giờ"}, turn_id="t1")

    assert state.value_of("onset_time") == "5 giờ"
    assert len(state.extraction_disagreements) == 1
    disagreement = state.extraction_disagreements[0]
    assert disagreement.legacy_value == "8 giờ"
    assert disagreement.canonical_value == "5 giờ"
    assert disagreement.resolution == "CANONICAL_AUTHORITATIVE"


def test_extractor_disagreement_never_becomes_a_patient_contradiction() -> None:
    """The patient said one thing. Two parsers disagreed. Do not ask them again."""
    state = CanonicalPatientState()
    state.record("onset_time", "5 giờ", turn_id="t1")
    ingest_blueprint(state, {"onset_time": "8 giờ"}, turn_id="t1")

    assert state.unresolved_contradictions() == []
    evaluation = evaluate_readiness(
        {}, view=ClinicalStateView(state), clinical_memory_confirmation_status="CONFIRMED"
    )
    assert not any(
        field.startswith("contradiction:")
        for field in evaluation.missing_critical_fields
    )


def test_a_real_patient_contradiction_still_registers() -> None:
    """The distinction must cut both ways."""
    state = CanonicalPatientState()
    state.record("onset_time", "8 giờ", temporal="CURRENT", turn_id="t1")
    state.record("onset_time", "5 giờ", temporal="CURRENT", turn_id="t2")
    assert len(state.unresolved_contradictions()) == 1
    assert state.extraction_disagreements == []


def test_disagreements_survive_serialization_separately_from_contradictions() -> None:
    state = CanonicalPatientState()
    state.record("onset_time", "5 giờ", turn_id="t1")
    state.record_disagreement("onset_time", "8 giờ", "5 giờ", turn_id="t1")
    restored = CanonicalPatientState.from_dict(state.to_dict())
    assert len(restored.extraction_disagreements) == 1
    assert restored.unresolved_contradictions() == []


# --------------------------------------------------------------------------
# §17 E - requirement provenance
# --------------------------------------------------------------------------

def test_every_shipped_requirement_is_marked_provisional() -> None:
    from src.agents.clinical_requirements import PROFILES

    for profile in PROFILES.values():
        for requirement in profile.requirements:
            assert requirement.provenance.review_status == "PENDING_CLINICAL_REVIEW"
            assert requirement.provenance.source == "INTERNAL_PROVISIONAL"
            assert requirement.provenance.is_clinically_validated is False


def test_no_profile_claims_clinical_validation() -> None:
    from src.agents.clinical_requirements import PROFILES

    assert not any(profile.is_clinically_validated for profile in PROFILES.values())


def test_requirements_are_classified_not_uniformly_clinical() -> None:
    from src.agents.clinical_requirements import PROFILES

    classes = {
        requirement.requirement_class
        for profile in PROFILES.values()
        for requirement in profile.requirements
    }
    # Engineering structure must be distinguishable from clinical judgement.
    assert "ENGINEERING" in classes
    assert "CLINICAL_POLICY" in classes
    assert "SAFETY" in classes


def test_the_clinical_review_backlog_is_enumerable() -> None:
    from src.agents.clinical_requirements import clinical_review_dependencies

    pending = clinical_review_dependencies()
    assert pending
    assert all(item["review_status"] == "PENDING_CLINICAL_REVIEW" for item in pending)
    assert {item["cluster"] for item in pending} >= {"chest_pain", "fever"}


def test_the_policy_set_is_versioned() -> None:
    from src.agents.clinical_requirements import POLICY_VERSION, profile_for

    assert "provisional" in POLICY_VERSION
    assert profile_for("chest_pain").version == POLICY_VERSION


def test_requirement_profiles_do_not_ground_clinical_claims() -> None:
    """Protocol grounding stays with the evidence gate, not these profiles."""
    from src.agents import clinical_requirements

    source = Path(clinical_requirements.__file__).read_text(encoding="utf-8")
    # No ESI level or protocol code may be asserted from a requirement profile.
    assert "esi_level" not in source.lower()
    assert "protocol_code" not in source


# --------------------------------------------------------------------------
# §17 F - legacy recovery is marked, not fabricated
# --------------------------------------------------------------------------

def test_replayed_legacy_facts_are_not_labelled_patient_reported() -> None:
    from src.services.triage_session_recovery import build_legacy_canonical_state

    state = build_legacy_canonical_state(
        {"chief_complaint": ["đau ngực"], "onset_time": "5 giờ"}
    )
    view = ClinicalStateView(state)
    assert view.read("onset_time").source == "LEGACY_RECOVERED"
    assert view.is_patient_asserted("onset_time") is False
    assert view.has_degraded_provenance() is True


def test_a_live_turn_is_not_flagged_as_degraded_provenance() -> None:
    assert _view("Tôi đang đau ngực").has_degraded_provenance() is False


def test_legacy_recovery_marks_its_turn_id() -> None:
    from src.services.triage_session_recovery import (
        LEGACY_RECOVERY_TURN_ID,
        build_legacy_canonical_state,
    )

    state = build_legacy_canonical_state({"onset_time": "5 giờ"})
    assert state.observation_of("onset_time").turn_id == LEGACY_RECOVERY_TURN_ID


# --------------------------------------------------------------------------
# §17 G - persistence preserves meaning
# --------------------------------------------------------------------------

@pytest.mark.parametrize(
    ("message", "key", "expected_status"),
    [
        ("Bây giờ tôi đau ngực", "symptom.chest_pain", "KNOWN"),
        ("Tôi không đau ngực", "symptom.chest_pain", "NEGATED"),
        ("Hình như tôi hơi khó thở", "symptom.dyspnea", "UNCERTAIN"),
        ("Tôi bị đau đầu", "symptom.chest_pain", "UNKNOWN"),
    ],
)
def test_semantic_status_survives_persist_and_reload(
    message: str, key: str, expected_status: str
) -> None:
    original = _state(message)
    restored = CanonicalPatientState.from_dict(original.to_dict())
    assert ClinicalStateView(restored).read(key).status == expected_status


def test_temporal_and_correction_survive_persist_and_reload() -> None:
    state = _state("Sáng nay tôi sốt 39 độ, giờ nhiệt độ còn 37.8")
    state.record("onset_time", "8 giờ", turn_id="t2")
    state.record("onset_time", "5 giờ", turn_id="t3", is_correction=True)

    restored = CanonicalPatientState.from_dict(state.to_dict())
    view = ClinicalStateView(restored)

    assert view.current_value("vital.temperature_c") == 37.8
    assert [o.value for o in view.historical_values("vital.temperature_c")] == [39.0]
    assert view.current_value("onset_time") == "5 giờ"
    superseded = [o for o in restored.history_of("onset_time") if not o.is_active]
    assert [o.value for o in superseded] == ["8 giờ"]


def test_inferred_and_synthetic_survive_reload_without_promotion() -> None:
    state = CanonicalPatientState()
    state.record("age", 55, source="SYNTHETIC", turn_id="seed")
    state.record(
        "symptom.dyspnea", True, status="INFERRED", source="SYSTEM_INFERENCE",
        turn_id="t1",
    )
    view = ClinicalStateView(CanonicalPatientState.from_dict(state.to_dict()))
    assert view.read("age").source == "SYNTHETIC"
    assert view.read("symptom.dyspnea").status == "INFERRED"
    assert view.is_patient_asserted("age") is False
    assert view.is_patient_asserted("symptom.dyspnea") is False
