from eval.simple_runtime.golden_validator import atom_matches, satisfied_esi


def test_independent_validator_honours_optional_discriminator_when_present():
    atom = {"authority_scope": "CLINICAL_AUTHORITY", "atom_type": "DECISION_CRITERION", "requirements": [{"fact_target_id": "resource", "operator": "EQ", "expected_value": 1, "required": False}], "decision_effect": {"impact": "ASSIGN_ESI", "candidate_esi": 4}}
    assert atom_matches(atom, {})
    assert atom_matches(atom, {"resource": 1})
    assert not atom_matches(atom, {"resource": 2})


def test_independent_validator_selects_most_urgent_satisfied_esi():
    atoms = {
        "esi1": {"authority_scope": "CLINICAL_AUTHORITY", "atom_type": "DECISION_CRITERION", "requirements": [{"fact_target_id": "airway", "operator": "EQ", "expected_value": "OBSTRUCTED"}], "decision_effect": {"impact": "ASSIGN_ESI", "candidate_esi": 1}},
        "esi3": {"authority_scope": "CLINICAL_AUTHORITY", "atom_type": "DECISION_CRITERION", "requirements": [{"fact_target_id": "resource", "operator": "GTE", "expected_value": 2}], "decision_effect": {"impact": "ASSIGN_ESI", "candidate_esi": 3}},
    }
    assert satisfied_esi(atoms, {"airway": "OBSTRUCTED", "resource": 2}) == (1, ["esi1"])
