from __future__ import annotations

from typing import Any


def _compare(actual: Any, operator: str, expected: Any) -> bool:
    if operator == "EQ":
        return actual == expected
    if operator == "NEQ":
        return actual != expected
    try:
        left, right = float(actual), float(expected)
    except (TypeError, ValueError):
        return False
    return {"GT": left > right, "GTE": left >= right, "LT": left < right, "LTE": left <= right}.get(operator, False)


def _resource_count_is_required(atom: dict[str, Any]) -> bool:
    effect = atom.get("decision_effect") or {}
    return (
        str(atom.get("decision_point") or "").startswith("D_")
        and effect.get("impact") == "ASSIGN_ESI"
        and effect.get("candidate_esi") in {3, 4, 5}
    )


def _condition_matches(
    condition: dict[str, Any],
    facts: dict[str, Any],
    *,
    require_resource_count: bool = False,
) -> bool:
    key = condition.get("fact_target_id")
    required = condition.get("required", True) or (
        require_resource_count and key == "fact_target:resource_count"
    )
    if key not in facts:
        return not required
    return _compare(facts[key], str(condition.get("operator", "EQ")), condition.get("expected_value"))


def atom_matches(atom: dict[str, Any], facts: dict[str, Any]) -> bool:
    """Independent evaluator for the corpus's list-of-AND-branches format."""
    requirements = atom.get("requirements") or []
    require_resource_count = _resource_count_is_required(atom)
    if not requirements:
        return False
    if isinstance(requirements[0], dict):
        return all(_condition_matches(item, facts, require_resource_count=require_resource_count) for item in requirements)
    return any(
        all(_condition_matches(item, facts, require_resource_count=require_resource_count) for item in branch)
        for branch in requirements
        if isinstance(branch, list)
    )


def required_conditions(atom: dict[str, Any], branch_index: int = 0) -> list[dict[str, Any]]:
    requirements = atom.get("requirements") or []
    if not requirements:
        return []
    if isinstance(requirements[0], dict):
        return [item for item in requirements if item.get("required", True)]
    branch = requirements[min(branch_index, len(requirements) - 1)]
    return [item for item in branch if item.get("required", True)] if isinstance(branch, list) else []


def branch_conditions(atom: dict[str, Any], branch_index: int = 0) -> list[dict[str, Any]]:
    """All conditions for the selected branch, including optional discriminators."""
    requirements = atom.get("requirements") or []
    if not requirements:
        return []
    if isinstance(requirements[0], dict):
        return list(requirements)
    branch = requirements[min(branch_index, len(requirements) - 1)]
    return list(branch) if isinstance(branch, list) else []


def satisfied_esi(atoms: dict[str, dict[str, Any]], facts: dict[str, Any]) -> tuple[int | None, list[str]]:
    hits: list[tuple[int, str]] = []
    for atom_id, atom in atoms.items():
        effect = atom.get("decision_effect") or {}
        level = effect.get("candidate_esi")
        if atom.get("authority_scope") != "CLINICAL_AUTHORITY" or atom.get("atom_type") != "DECISION_CRITERION":
            continue
        if effect.get("impact") != "ASSIGN_ESI" or not isinstance(level, int):
            continue
        if atom_matches(atom, facts):
            hits.append((level, atom_id))
    if not hits:
        return None, []
    level = min(item[0] for item in hits)
    return level, [atom_id for atom_level, atom_id in hits if atom_level == level]
