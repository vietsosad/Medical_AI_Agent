import asyncio

import pytest

from eval.simple_runtime.corpus_reader import CorpusSnapshot
from eval.simple_runtime.ragas_evaluator import (
    RagasConfig,
    RagasMetricBundle,
    _score_case,
    evaluate_observations,
    prepare_ragas_input,
)
from eval.simple_runtime.report import verdict
from eval.simple_runtime.schemas import RagasCaseInput, RagasResult


def _corpus() -> CorpusSnapshot:
    return CorpusSnapshot(
        concepts={},
        relations=[],
        atoms={
            "atom:expected": {
                "atom_id": "atom:expected",
                "authority_scope": "CLINICAL_AUTHORITY",
                "decision_point": "D_RESOURCE_PREDICTION",
                "retrieval_text": "Stable presentation needing one resource.",
                "requirements": [],
                "decision_effect": {"candidate_esi": 4},
            },
            "atom:other": {
                "atom_id": "atom:other",
                "authority_scope": "CLINICAL_AUTHORITY",
                "decision_point": "D_RESOURCE_PREDICTION",
                "retrieval_text": "Other stable resource rule.",
                "requirements": [],
                "decision_effect": {"candidate_esi": 4},
            },
            "atom:mock": {
                "atom_id": "atom:mock",
                "authority_scope": "MOCK_SIMULATION_ONLY",
                "decision_point": "D_RESOURCE_PREDICTION",
                "retrieval_text": "Mock rule.",
                "requirements": [],
                "decision_effect": {"candidate_esi": 5},
            },
        },
        facts={},
        fact_embedding_dimensions={},
        table_fingerprints={},
        table_counts={},
    )


def _observation(**overrides):
    observation = {
        "case_id": "case-1",
        "expected_esi": 4,
        "predicted_esi": 4,
        "final_response": "Tình trạng phù hợp mức độ nghiêm trọng 4.",
        "presentation": {"initial_message": "Tôi bị vết cắt nhỏ ở tay."},
        "profile": {"age_years": 30, "sex": "female"},
        "persisted_state": {"facts": {"fact_target:resource_count": 1}},
        "expected_state": {"facts": {"fact_target:resource_count": 1}},
        "expected_decision": {"resource_count": 1},
        "expected_retrieval": {
            "primary_atom_id": "atom:expected",
            "decision_points": ["D_RESOURCE_PREDICTION"],
        },
        "decision_snapshots": [
            {
                "action": "RETURN_MATCH",
                "retrieved_atoms_this_turn": [
                    {"atom_id": "atom:expected"},
                    {"atom_id": "atom:expected"},
                    {"atom_id": "atom:other"},
                    {"atom_id": "atom:mock"},
                ],
            }
        ],
        "citations": [{"atom_id": "atom:expected"}],
        "matched_atoms": [{"atom_id": "atom:other"}],
    }
    observation.update(overrides)
    return observation


def test_prepare_uses_final_turn_deduplicates_and_keeps_authority_grounding():
    sample, preliminary = prepare_ragas_input(_observation(), _corpus())
    assert preliminary is None
    assert sample is not None
    assert len(sample.retrieved_contexts) == 3
    assert "atom:expected" in sample.retrieved_contexts[0]
    assert len(sample.grounding_contexts) == 1
    assert "CLINICAL_AUTHORITY" in sample.grounding_contexts[0]
    assert "Expected ESI: 4" in sample.reference
    assert '"predicted_esi": 4' in sample.response
    assert "Final response:" not in sample.response


def test_prompt_probe_without_expected_esi_is_not_applicable():
    sample, result = prepare_ragas_input(_observation(expected_esi=None), _corpus())
    assert sample is None
    assert result is not None
    assert result.ragas_applicable is False
    assert result.verdict == "skipped"


def test_missing_prediction_is_incomplete_before_model_call():
    sample, result = prepare_ragas_input(_observation(predicted_esi=None), _corpus())
    assert sample is None
    assert result is not None
    assert result.metric_errors["input"] == "Backend returned no final ESI prediction."


def test_ragas_schema_rejects_score_outside_unit_interval():
    with pytest.raises(Exception):
        RagasResult(case_id="bad", faithfulness_score=1.1, verdict="fail")


class _Result:
    def __init__(self, value, reason=None):
        self.value = value
        self.reason = reason


class _Metric:
    async def ascore(self, **_kwargs):
        return _Result(0.8, "ok")


def test_score_case_averages_all_five_metrics():
    bundle = RagasMetricBundle(
        faithfulness=_Metric(),
        context_precision=_Metric(),
        context_recall=_Metric(),
        context_relevance=_Metric(),
        answer_relevancy=_Metric(),
    )
    sample = RagasCaseInput(
        case_id="case-1",
        user_input="question",
        response="answer",
        reference="reference",
        retrieved_contexts=["context"],
        grounding_contexts=["grounding"],
    )
    result = asyncio.run(_score_case(sample, bundle))
    assert result.ragas_score == 0.8
    assert result.verdict == "pass"


def test_evaluate_does_not_initialize_model_for_non_applicable_case():
    results, errors = asyncio.run(
        evaluate_observations(
            [_observation(expected_esi=None)],
            RagasConfig.from_env(),
            corpus=_corpus(),
            metric_bundle=RagasMetricBundle(None, None, None, None, None),
        )
    )
    assert errors == []
    assert results[0]["ragas_applicable"] is False


def test_deterministic_only_mode_is_not_penalized_by_missing_ragas():
    final_verdict, score = verdict(
        {"deterministic_score": 0.8, "hard_fail_reasons": []},
        [],
        "COMPLETED",
        "DETERMINISTIC_ONLY",
    )
    assert final_verdict == "PASS"
    assert score == 0.8


def test_incomplete_applicable_ragas_result_keeps_score_unavailable():
    final_verdict, score = verdict(
        {"deterministic_score": 0.9, "hard_fail_reasons": []},
        [{"ragas_applicable": True, "verdict": "incomplete", "ragas_score": None}],
        "COMPLETED",
        "RAGAS",
    )
    assert final_verdict == "EVALUATION_INCOMPLETE"
    assert score is None
