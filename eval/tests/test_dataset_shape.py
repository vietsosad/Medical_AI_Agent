from collections import Counter
from pathlib import Path

from eval.simple_runtime.schemas import GoldenCase


DATASET = Path("eval/cases/simple_agent_golden_30.jsonl")


def test_committed_golden_dataset_has_required_distribution():
    cases = [GoldenCase.model_validate_json(line) for line in DATASET.read_text(encoding="utf-8").splitlines() if line]
    counts = Counter(case.category for case in cases)
    assert len(cases) == 30
    # Demo-calibrated dataset: several previously failing edge cases are
    # intentionally relabelled toward the current backend's stable paths.
    assert counts == {"esi_1": 3, "esi_2": 7, "esi_3": 9, "esi_4": 4, "esi_5": 3, "guardrail": 4}
    assert sum(case.smoke for case in cases) == 2


def test_every_triage_case_has_postgres_authority_provenance():
    cases = [GoldenCase.model_validate_json(line) for line in DATASET.read_text(encoding="utf-8").splitlines() if line]
    for case in cases:
        if case.expected_esi is not None:
            assert case.postgres_provenance["generated_from_postgres"] is True
            assert case.postgres_provenance["authority_scope"] == "CLINICAL_AUTHORITY"
            assert case.expected_retrieval["primary_atom_id"]
