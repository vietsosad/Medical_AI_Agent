from eval.simple_runtime.deterministic_metrics import compute_metrics


def _observation(expected, predicted):
    return {"case_id": f"case-{expected}", "category": f"esi_{expected}", "kind": "triage", "expected_esi": expected, "predicted_esi": predicted, "terminal": True, "terminal_action": "RETURN_MATCH", "expected_state": {"concept_ids": [], "facts": {}}, "persisted_state": {"concepts": [], "facts": {}}, "expected_retrieval": {"primary_atom_id": "a", "relevant_atom_ids": ["a"]}, "retrieved_atoms": [{"atom_id": "a"}], "citations": [{"atom_id": "a"}], "asked_question_target_ids": []}


def test_critical_undertriage_is_hard_failure():
    metrics = compute_metrics([_observation(1, 2)])
    assert metrics["classification"]["critical_undertriage_count"] == 1
    assert "critical_undertriage" in metrics["hard_fail_reasons"]


def test_retrieval_metrics_are_perfect_for_exact_atom():
    metrics = compute_metrics([_observation(4, 4)])
    assert metrics["retrieval_protocol"]["recall_at_5"] == 1.0
    assert metrics["retrieval_protocol"]["mrr"] == 1.0
