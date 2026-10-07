"""Rebuild durable intake context from persisted patient chat messages.

Persisted ``chat_messages`` are the durable recovery source for DeepAgent
clinical state. This module replays only facts explicitly present in those
messages and never derives an ESI level.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any

from src.agents.blueprint_projection import ingest_blueprint
from src.agents.canonical_state import CanonicalPatientState
from src.agents.nodes.answer_validator import validate_answer_alignment
from src.agents.nodes.fact_extraction import FIELD_DISPLAY_VI, SYMPTOM_DISPLAY_VI
from src.agents.nodes.intake_analyzer import extract_blueprint_deterministically
from src.agents.nodes.patient_confirmation import build_intake_summary
from src.models.db_models import ChatMessage

# Marks every observation that came from replay rather than a live turn.
LEGACY_RECOVERY_TURN_ID = "legacy-recovered"

INTAKE_REVIEW_MARKER = "kiểm tra bản tóm tắt bên dưới"
INTAKE_CONFIRMATION_TEXT = (
    "Tôi xác nhận thông tin đã thu thập là đúng và đồng ý bắt đầu phân loại."
)
_VAGUE_COMPLAINTS = {"mệt", "met", "không khỏe", "khong khoe", "khó chịu", "kho chiu"}
_ACTIVE_QUESTION_MARKER = "_activeQuestion"
_QUESTION_OPTION_TYPES = frozenset(
    {"single", "multiple", "scale", "text_only", "vitals_form"}
)
_QUESTION_FIELDS = frozenset(
    {
        "chief_complaint",
        "onset_time",
        "recent_procedure",
        "severity_score",
        "associated_symptoms",
        "vital_signs",
        "clinical_memory_update_detail",
        "clinical_memory_confirmation",
        "radiation",
        "red_flag_context",
    }
)


@dataclass(frozen=True)
class RecoveredTriageState:
    """Minimum safe state needed to resume a legacy triage session.

    Replay reconstructs *what was said*, never *how it was originally
    understood*. Turn boundaries, hedging, temporal framing and correction links
    are not recoverable from stored message text, so the canonical state built
    here is explicitly marked ``LEGACY_RECOVERED`` rather than dressed up as
    live patient-reported observations.
    """

    clinical_blueprint: dict[str, Any]
    intake_summary: dict[str, Any]
    canonical_state: dict[str, Any]
    messages: list[dict[str, str]]
    active_question: dict[str, str] | None
    confirmation_was_requested: bool
    awaiting_confirmation: bool
    step: int


def _structured_payload(record: ChatMessage) -> dict[str, Any] | None:
    options = record.structured_options
    if not options or not isinstance(options[0], dict):
        return None
    return options[0]


def _is_supported_fact_key(field: str) -> bool:
    if field in FIELD_DISPLAY_VI:
        return True
    for prefix in ("symptom.", "complaint.", "associated."):
        if field.startswith(prefix):
            return field.removeprefix(prefix) in SYMPTOM_DISPLAY_VI
    return field in SYMPTOM_DISPLAY_VI


def _validated_active_question_marker(value: object) -> dict[str, str] | None:
    """Accept only question-engine fields, never arbitrary persisted strings."""
    if not isinstance(value, dict):
        return None
    field = str(value.get("field") or "").strip()
    options_type = str(
        value.get("optionsType") or value.get("options_type") or ""
    ).strip()
    if not field or len(field) > 120 or options_type not in _QUESTION_OPTION_TYPES:
        return None
    if field.startswith("contradiction_"):
        supported = _is_supported_fact_key(field.removeprefix("contradiction_"))
    else:
        supported = field in _QUESTION_FIELDS
    if not supported:
        return None
    # The identifier is deliberately reconstructed from the validated field;
    # no opaque runtime/planner string is trusted during cold recovery.
    return {
        "field": field,
        "question_id": field,
        "options_type": options_type,
    }


def build_question_recovery_payload(
    structured_payload: object,
    active_question: object,
) -> dict[str, Any] | None:
    """Attach a private, validated recovery marker to an existing JSON payload.

    Free-text questions previously stored no ``structured_options`` value at
    all, so a process restart lost their target. A minimal ``text_only``
    payload keeps that target in the existing JSON column. Pydantic's public
    ``StructuredPayloadDTO`` ignores the private marker on output.
    """
    marker = _validated_active_question_marker(active_question)
    if marker is None:
        return dict(structured_payload) if isinstance(structured_payload, dict) else None
    payload = (
        dict(structured_payload)
        if isinstance(structured_payload, dict)
        else {"optionsType": "text_only", "submitted": False}
    )
    payload[_ACTIVE_QUESTION_MARKER] = {
        "field": marker["field"],
        "questionId": marker["question_id"],
        "optionsType": marker["options_type"],
    }
    return payload


def _infer_active_question(record: ChatMessage) -> dict[str, str] | None:
    """Infer the slot that a persisted AI question was asking about."""
    payload = _structured_payload(record)
    if payload:
        persisted_marker = _validated_active_question_marker(
            payload.get(_ACTIVE_QUESTION_MARKER)
        )
        if persisted_marker is not None:
            return persisted_marker
    option_ids: list[str] = []
    options_type = "text_only"
    if payload:
        options_type = str(payload.get("optionsType") or "single")
        raw_options = payload.get("options")
        if isinstance(raw_options, list):
            option_ids = [
                str(option.get("id", ""))
                for option in raw_options
                if isinstance(option, dict)
            ]

    content = record.content.lower()
    field: str | None = None
    if any(option_id.startswith("onset_") for option_id in option_ids):
        field = "onset_time"
    elif any(option_id.startswith("associated_") for option_id in option_ids):
        field = "associated_symptoms"
    elif any(option_id.startswith("vitals_") for option_id in option_ids):
        field = "vital_signs"
    elif any(option_id.startswith("ehr_") for option_id in option_ids):
        field = "clinical_memory_confirmation"
    elif options_type == "vitals_form":
        field = "vital_signs"
    elif options_type == "scale" or "từ 0 đến 10" in content:
        field = "severity_score"
    elif "bắt đầu từ khoảng thời gian" in content:
        field = "onset_time"
    elif "ngoài triệu chứng chính" in content or "dấu hiệu nào đi kèm" in content:
        field = "associated_symptoms"
    elif "phẫu thuật/thủ thuật" in content or "bạn phẫu thuật gì" in content:
        field = "recent_procedure"
    elif "phần nào đã thay đổi" in content:
        field = "clinical_memory_update_detail"
    elif "số đo gần đây" in content and "sinh hiệu" in content:
        field = "vital_signs"
    elif "hồ sơ ehr hiện ghi" in content:
        field = "clinical_memory_confirmation"
    elif "khó chịu rõ nhất" in content or "triệu chứng nào" in content:
        field = "chief_complaint"

    if field is None:
        return None
    return {
        "field": field,
        "question_id": field,
        "options_type": options_type,
    }


def _preserve_specific_patient_wording(
    content: str,
    blueprint: dict[str, Any],
) -> dict[str, Any]:
    """Keep a detailed patient phrase when a one-word symptom is too vague."""
    complaints = [
        str(item).strip().lower()
        for item in blueprint.get("chief_complaint", [])
        if str(item).strip()
    ]
    if (
        complaints
        and all(item in _VAGUE_COMPLAINTS for item in complaints)
        and blueprint.get("onset_time")
        and len(content.strip()) > max(len(item) for item in complaints) + 4
    ):
        return {**blueprint, "chief_complaint": [content.strip()[:120]]}
    return blueprint


def build_legacy_canonical_state(
    blueprint: dict[str, Any],
) -> CanonicalPatientState:
    """Rebuild canonical state from a replayed blueprint, honestly labelled.

    Provenance is ``LEGACY_RECOVERED``, not ``PATIENT_REPORTED``: the patient did
    say these things, but nothing about when, how certainly, or in which turn
    survives in the stored transcript. Claiming otherwise would fabricate
    provenance that no longer exists.
    """
    state = CanonicalPatientState()
    ingest_blueprint(
        state,
        blueprint,
        turn_id=LEGACY_RECOVERY_TURN_ID,
        source="LEGACY_RECOVERED",
    )
    return state


def recover_triage_state(records: Sequence[ChatMessage]) -> RecoveredTriageState:
    """Replay persisted messages into a conservative, resumable intake state."""
    blueprint: dict[str, Any] = {}
    transcript: list[dict[str, str]] = []
    active_question: dict[str, str] | None = None
    confirmation_was_requested = False
    last_record_is_review_request = False
    last_record_is_orphaned_confirmation = False
    saw_structured_question = False

    for index, record in enumerate(records):
        is_patient = record.sender_type == "PATIENT"
        transcript.append({
            "role": "user" if is_patient else "assistant",
            "content": record.content,
        })

        if is_patient:
            is_confirmation = record.content.strip() == INTAKE_CONFIRMATION_TEXT
            if is_confirmation:
                active_question = None
                last_record_is_review_request = False
                last_record_is_orphaned_confirmation = (
                    confirmation_was_requested and index == len(records) - 1
                )
                continue

            previous_complaints = list(blueprint.get("chief_complaint", []))
            validation = validate_answer_alignment(record.content, active_question)
            blueprint = extract_blueprint_deterministically(
                record.content,
                blueprint,
                active_question,
                validation.alignment,
            )
            if (
                (active_question or {}).get("field") == "associated_symptoms"
                and any(
                    marker in record.content.lower()
                    for marker in ("không có", "không rõ", "không chắc")
                )
            ):
                blueprint["chief_complaint"] = previous_complaints
            blueprint = _preserve_specific_patient_wording(record.content, blueprint)
            active_question = None
            last_record_is_review_request = False
            last_record_is_orphaned_confirmation = False
            continue

        is_review_request = INTAKE_REVIEW_MARKER in record.content.lower()
        if is_review_request:
            confirmation_was_requested = True
            active_question = None
        else:
            inferred_question = _infer_active_question(record)
            if inferred_question:
                active_question = inferred_question
                saw_structured_question = saw_structured_question or bool(
                    _structured_payload(record)
                )
        last_record_is_review_request = (
            is_review_request and index == len(records) - 1
        )
        last_record_is_orphaned_confirmation = False

    step = 3 if confirmation_was_requested else 2 if saw_structured_question else 1
    return RecoveredTriageState(
        clinical_blueprint=blueprint,
        canonical_state=build_legacy_canonical_state(blueprint).to_dict(),
        intake_summary=build_intake_summary(blueprint),
        messages=transcript,
        active_question=active_question,
        confirmation_was_requested=confirmation_was_requested,
        awaiting_confirmation=(
            last_record_is_review_request or last_record_is_orphaned_confirmation
        ),
        step=step,
    )
