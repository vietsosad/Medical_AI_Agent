"""Deterministic validation that prevents unrelated answers from filling slots."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

from src.agents.guardrails import extract_patient_reported_vitals
from src.agents.nodes.adaptive_questions import canonical_key_for_field
from src.agents.nodes.intent_classifier import normalize_vietnamese_text
from src.agents.nodes.severity_extraction import has_severity_evidence
from src.agents.state import AgentState, AnswerAlignment

RECENT_PROCEDURE_PATTERNS = (
    "phau thuat",
    "mo xong",
    "mo noi soi",
    "thu thuat",
    "xuat vien sau mo",
    "hau phau",
)
CLEAR_NEGATIVE_PATTERNS = (
    "khong co",
    "khong thay",
    "khong bi",
    "khong ro",
    "khong chac",
)
VITAL_UNAVAILABLE_PATTERNS = (
    "chua do",
    "khong do",
    "khong co may",
    "khong biet chi so",
    "khong ro chi so",
)
# Free-text wordings that genuinely answer the three-option EHR review form.
EHR_CONFIRMATION_ANSWER_PATTERNS = (
    "van dung",
    "khong thay doi",
    "chinh xac",
    "dung roi",
    "van the",
    "van vay",
    "giu nguyen",
    "thay doi",
    "can sua",
    "khong dung",
    "sai",
    "khong chac",
    "khong ro",
    "khong biet",
)
EHR_CONFIRMATION_OPTION_IDS = frozenset({
    "ehr_confirmed",
    "ehr_changed",
    "ehr_unsure",
})


@dataclass(frozen=True)
class AnswerValidation:
    alignment: AnswerAlignment
    reason: str


def _fold(text: str) -> str:
    return re.sub(r"\s+", " ", normalize_vietnamese_text(text)).strip()


def _contains_any(text: str, patterns: tuple[str, ...]) -> bool:
    return any(pattern in text for pattern in patterns)


def validate_answer_alignment(
    query: str,
    active_question: dict[str, Any] | None,
) -> AnswerValidation:
    """Classify whether the latest utterance actually answers the open question."""
    if not active_question:
        return AnswerValidation("NOT_APPLICABLE", "no_active_question")

    compact = _fold(query)
    field = str(active_question.get("field") or "")
    if not compact:
        return AnswerValidation("UNCLEAR_ANSWER", "empty_answer")
    if field.startswith("contradiction_") and len(compact) >= 2:
        return AnswerValidation("DIRECT_ANSWER", "contradiction_resolution")

    # Adaptive targets name a problem and one of its attributes
    # ("headache.course"), or a canonical symptom/vital key. They are asked as
    # open questions on purpose, so any substantive reply answers them --
    # including "tôi không biết", which is an answer about what the patient can
    # tell us and must not leave the same question open to be asked again.
    adaptive_key = canonical_key_for_field(field)
    if adaptive_key is not None:
        if len(compact) < 2:
            return AnswerValidation("UNCLEAR_ANSWER", "empty_answer")
        return AnswerValidation("DIRECT_ANSWER", "adaptive_target_answer")

    has_procedure_update = _contains_any(compact, RECENT_PROCEDURE_PATTERNS)
    has_vitals = bool(extract_patient_reported_vitals(query))
    if has_procedure_update and field != "recent_procedure":
        return AnswerValidation(
            "CLINICAL_CONTEXT_UPDATE",
            "recent_procedure_during_unrelated_question",
        )
    if has_vitals and field != "vital_signs":
        return AnswerValidation(
            "CLINICAL_CONTEXT_UPDATE",
            "patient_reported_vitals_during_unrelated_question",
        )

    if field == "chief_complaint" and len(compact) >= 3:
        return AnswerValidation("DIRECT_ANSWER", "free_text_complaint")
    if field == "onset_time" and (
        _contains_any(compact, CLEAR_NEGATIVE_PATTERNS)
        or re.search(r"\b(phut|gio|tieng|ngay|tuan|thang)\b", compact)
        or _contains_any(
            compact,
            (
                "hom nay",
                "hom qua",
                "sang nay",
                "trua nay",
                "chieu nay",
                "toi nay",
                "toi qua",
                "toi hom qua",
                "dem qua",
                "vua bi",
                "moi bi",
                "vua moi bi",
                "moi dau",
                "vua dau",
            ),
        )
    ):
        return AnswerValidation("DIRECT_ANSWER", "onset_expression")
    if field == "severity_score" and has_severity_evidence(
        query,
        severity_question_active=True,
    ):
        return AnswerValidation("DIRECT_ANSWER", "severity_expression")
    if field == "radiation" and (
        re.search(
            r"\b(?:khong|chua|ko|chang)(?:\s+(?:co|bi|thay))?\s+lan\b",
            compact,
        )
        or re.search(r"\blan(?:\s+\w+){1,4}", compact)
    ):
        return AnswerValidation("DIRECT_ANSWER", "radiation_expression")
    if field == "associated_symptoms" and (
        _contains_any(compact, CLEAR_NEGATIVE_PATTERNS)
        or re.search(
            r"(?<!\w)(?:đau|mỏi|tê|ngứa|sưng|tức|rát|yếu)(?!\w)",
            query.lower(),
            flags=re.UNICODE,
        )
        or _contains_any(
            compact,
            (
                "sot",
                "ret run",
                "buon non",
                "non",
                "chong mat",
                "choang",
                "kho tho",
                "va mo hoi",
                "phat ban",
                "chay mau",
                "tim dap nhanh",
                "danh trong nguc",
            ),
        )
    ):
        return AnswerValidation("DIRECT_ANSWER", "associated_symptom_expression")
    if field == "recent_procedure" and len(compact) >= 3:
        return AnswerValidation("DIRECT_ANSWER", "procedure_clarification")
    if field == "vital_signs" and (
        has_vitals or _contains_any(compact, VITAL_UNAVAILABLE_PATTERNS)
    ):
        return AnswerValidation("DIRECT_ANSWER", "vital_sign_answer")
    if field == "clinical_memory_confirmation":
        # This form has three server-issued options. Free text only settles it
        # when it actually says one of those three things.
        #
        # Accepting *any* two characters meant "38.5 độ" -- a patient reporting
        # their temperature -- was recorded as an EHR review answer, the record
        # was marked UNCERTAIN-but-reviewed, and the clinical content of the
        # message was dropped on the floor. Anything else now leaves the form
        # open and travels on as an ordinary clinical utterance.
        if any(marker in compact for marker in EHR_CONFIRMATION_ANSWER_PATTERNS):
            return AnswerValidation("DIRECT_ANSWER", "ehr_review_answer")
        return AnswerValidation(
            "CLINICAL_CONTEXT_UPDATE",
            "clinical_content_during_ehr_review",
        )
    if field == "clinical_memory_update_detail" and len(compact) >= 3:
        return AnswerValidation("DIRECT_ANSWER", "ehr_correction_detail")

    return AnswerValidation("UNCLEAR_ANSWER", f"does_not_answer_{field or 'unknown'}")


async def validate_answer_node(state: AgentState) -> dict[str, Any]:
    active_question = state.get("active_question")
    active_field = str((active_question or {}).get("field") or "")
    selected_option_id = state.get("selected_option_id")
    if (
        selected_option_id in EHR_CONFIRMATION_OPTION_IDS
        and active_field != "clinical_memory_confirmation"
    ):
        # Structured workflow actions retain their identity even when a
        # clinical question is also open.  Binding the EHR button label to an
        # onset/severity target fabricated a clinical fact from UI text.
        validation = AnswerValidation(
            "CLINICAL_CONTEXT_UPDATE",
            "ehr_review_during_clinical_question",
        )
    else:
        validation = validate_answer_alignment(
            state.get("query", ""),
            active_question,
        )
    return {
        "answer_alignment": validation.alignment,
        "answer_alignment_reason": validation.reason,
        "analysis": (
            f"{state.get('analysis', '')}\n"
            f"[Answer Validator] {validation.alignment}: {validation.reason}"
        ),
    }
