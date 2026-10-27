"""The patient-facing output firewall (src/simple_agent/output_guard.py).

Two directions matter equally: what must never reach a patient, and what the
interview itself needs to say -- a guard that also blocks "Bạn có bị tiểu
đường không?" would break history-taking instead of protecting anyone.
"""

from __future__ import annotations

import pytest

from src.simple_agent.output_guard import blocked_reason, guard_patient_text
from src.simple_agent.phrasing import emergency_outcome_message


@pytest.mark.parametrize(
    ("text", "reason"),
    [
        ("Bạn bị nhồi máu cơ tim, cần uống aspirin ngay.", "DIAGNOSIS_ASSERTION"),
        ("Bạn bị viêm ruột thừa.", "DIAGNOSIS_ASSERTION"),
        ("Có thể con bạn đã mắc sốt xuất huyết.", "DIAGNOSIS_ASSERTION"),
        ("Khả năng cao là đột quỵ.", "DIAGNOSIS_ASSERTION"),
        ("Đây là dấu hiệu của nhồi máu cơ tim.", "DIAGNOSIS_ASSERTION"),
        ("Chẩn đoán của bạn là viêm phổi.", "DIAGNOSIS_ASSERTION"),
        ("Bạn nên uống paracetamol mỗi 6 giờ.", "PRESCRIBING"),
        ("Hãy dùng thuốc hạ sốt.", "PRESCRIBING"),
        ("Uống 2 viên trước khi ngủ.", "PRESCRIBING"),
        ("", "EMPTY"),
        ("   ", "EMPTY"),
    ],
)
def test_diagnosis_prescribing_and_empty_text_are_blocked(text: str, reason: str) -> None:
    assert blocked_reason(text) == reason


@pytest.mark.parametrize(
    "text",
    [
        # History-taking questions about conditions and medication.
        "Bạn có bị tiểu đường không?",
        "Bạn đang dùng thuốc gì không?",
        "Bạn bị đau bụng từ khi nào?",
        "Bạn sốt 38,5 độ phải không?",
        # Restating a symptom is not a diagnosis.
        "Bạn bị đau bụng đã hai ngày, mình cần hỏi thêm một chút.",
        # General care advice that names no drug.
        "Hãy uống nhiều nước và nghỉ ngơi.",
        # The outcome wording itself mentions "chẩn đoán" only to disclaim it.
        "Dữ liệu mô phỏng khớp với mức ESI 3, đây không phải chẩn đoán.",
        "Chào bạn! Bạn đang gặp vấn đề sức khỏe gì?",
    ],
)
def test_interview_language_passes(text: str) -> None:
    assert blocked_reason(text) is None


@pytest.mark.parametrize("level", [1, 2])
@pytest.mark.parametrize("subject", [None, {"type": "OTHER_PERSON", "label": "con của bạn"}])
def test_the_fixed_emergency_messages_pass_the_guard(level: int, subject: dict | None) -> None:
    assert blocked_reason(emergency_outcome_message(level, subject)) is None


def test_a_blocked_message_is_replaced_whole_not_redacted() -> None:
    text, reason = guard_patient_text("Bạn bị viêm phổi. Mình hỏi thêm nhé.", "FALLBACK")

    assert (text, reason) == ("FALLBACK", "DIAGNOSIS_ASSERTION")
