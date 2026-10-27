"""Deterministic output firewall for every patient-facing sentence.

Phase A's free replies and Phase C's phrasing are model prose. Their prompts
forbid diagnosis and prescribing, but a prompt is not a control: this module
is. It runs on the final text, never sends anything to a model, and on a hit
replaces the whole message with a fixed fallback the caller supplies --
partial redaction would leave a sentence that still reads as advice.

Questions are left alone. "Bạn có bị tiểu đường không?" and "Bạn đang dùng
thuốc gì?" are how medical history and medication facts get collected; only
declarative sentences can assert a diagnosis or tell someone what to take.

The vocabularies are engineering config, PENDING_CLINICAL_REVIEW like the
rest of the clinical tables -- conservative by design: a blocked harmless
sentence costs one plainer message, a missed diagnosis costs trust.
"""

from __future__ import annotations

import re

# Disease / diagnosis nouns. Symptoms ("đau bụng", "khó thở", "sốt") are
# deliberately absent -- restating what the patient said is not a diagnosis.
_DIAGNOSIS_TERMS = (
    r"viêm\s+\w+", r"nhồi\s+máu", r"đột\s+quỵ", r"tai\s+biến", r"ung\s+thư", r"u\s+(?:não|phổi|gan)",
    r"sỏi\s+\w+", r"suy\s+(?:tim|thận|gan|hô\s+hấp)", r"tắc\s+(?:ruột|mạch)", r"xuất\s+huyết",
    r"sốt\s+xuất\s+huyết", r"nhiễm\s+(?:trùng|khuẩn|độc)", r"bệnh\s+lao", r"lao\s+phổi",
    r"tiểu\s+đường", r"đái\s+tháo\s+đường", r"(?:cao|tăng)\s+huyết\s+áp", r"hen\s+suyễn",
    r"thoát\s+vị", r"ruột\s+thừa", r"thai\s+ngoài\s+tử\s+cung", r"phình\s+\w+", r"huyết\s+khối",
    r"thuyên\s+tắc", r"động\s+kinh", r"trầm\s+cảm", r"covid", r"cúm", r"sốc\s+phản\s+vệ",
    r"gãy\s+xương", r"chấn\s+động\s+não", r"zona", r"thủy\s+đậu", r"sởi",
)
_DIAGNOSIS_RE = re.compile(
    r"(?:"
    # "bạn bị viêm ruột thừa", "có thể con bạn đã mắc sốt xuất huyết"
    r"\b(?:bị|mắc)(?:\s+(?:bệnh|chứng))?\s+(?:" + "|".join(_DIAGNOSIS_TERMS) + r")"
    # "khả năng cao là đột quỵ", "dấu hiệu của nhồi máu cơ tim"
    r"|\b(?:khả\s+năng(?:\s+cao)?\s+là|có\s+lẽ\s+là|chắc\s+là|dấu\s+hiệu\s+của|triệu\s+chứng\s+của)"
    r"\s+(?:bệnh\s+)?(?:" + "|".join(_DIAGNOSIS_TERMS) + r")"
    # "chẩn đoán là ...", "chẩn đoán của bạn: ..."
    r"|\bchẩn\s+đoán(?:\s+(?:của\s+bạn|chính\s+xác))?\s*(?:là|:)"
    r")",
    re.IGNORECASE,
)

_DRUG_TERMS = (
    "thuốc", "kháng sinh", "paracetamol", "panadol", "efferalgan", "hapacol", "ibuprofen", "aspirin",
    "amoxicillin", "augmentin", "cephalexin", "diclofenac", "naproxen", "morphin", "tramadol",
    "codein", "corticoid", "prednisolon", "dexamethason", "insulin", "nitroglycerin", "salbutamol",
    "ventolin", "adrenalin", "epinephrin", "omeprazol", "loperamid", "berberin",
)
_PRESCRIBING_RE = re.compile(
    # an intake verb shortly before a drug: "hãy uống paracetamol", "nên dùng thuốc hạ sốt"
    r"\b(?:uống|dùng|tiêm|bôi|ngậm|xịt|đặt|nhỏ)\s+(?:\w+\s+){0,2}(?:" + "|".join(_DRUG_TERMS) + r")\b"
    # any dose: "500mg", "2 viên", "10 ml"
    r"|\b\d+(?:[.,]\d+)?\s?(?:mg|mcg|µg|ml|viên|giọt)\b",
    re.IGNORECASE,
)

_SENTENCE_RE = re.compile(r"[^.!?\n]+[.!?]*")


def _declarative_sentences(text: str) -> list[str]:
    return [
        sentence.strip()
        for sentence in _SENTENCE_RE.findall(text)
        if sentence.strip() and not sentence.strip().endswith("?")
    ]


def blocked_reason(text: str) -> str | None:
    """Why ``text`` may not be shown to a patient, or ``None`` if it may."""
    if not text or not text.strip():
        return "EMPTY"
    for sentence in _declarative_sentences(text):
        if _DIAGNOSIS_RE.search(sentence):
            return "DIAGNOSIS_ASSERTION"
        if _PRESCRIBING_RE.search(sentence):
            return "PRESCRIBING"
    return None


def guard_patient_text(text: str, fallback: str) -> tuple[str, str | None]:
    """Return ``(text, None)`` when safe, else ``(fallback, reason)``."""
    reason = blocked_reason(text)
    return (fallback, reason) if reason else (text, None)
