"""Conservative display-only normalization for persisted clinical text."""

import re


_JOINED_HITL_ACTION = re.compile(r"(?<=[\wÀ-ỹ])(APPROVE|OVERRIDE)\b")


def normalize_clinical_display_text(value: str) -> str:
    """Repair known formatting artifacts without rewriting clinical meaning."""
    return _JOINED_HITL_ACTION.sub(r" \1", value)
