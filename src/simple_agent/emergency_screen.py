"""Deterministic emergency screen, run on the raw patient message before any LLM.

Without it the live path only noticed "con tôi ngất xỉu" or "nôn ra máu" if
Phase A happened to extract the right fact -- and noticed nothing at all
while OpenAI was down, because then no turn ran.

What a hit does, and does not do (decided 27/10/2026, plan Q3):
- it DOES put a fixed, conditional "call 115" instruction in front of the
  patient and flag the case so it reaches the nurse queue at once, still
  ACTIVE, ahead of everything else;
- it does NOT assign an ESI, lock the chat, or end the interview. A phrase is
  a reason for a human to look now, not a triage level -- the engineering
  contract forbids ``keyword -> ESI``, and an alarm that ends the
  conversation on two words is one patients learn to ignore.

Matching is built to stay quiet on look-alikes: accented patterns run on the
text as typed; folded (diacritic-free) patterns run too, for patients who type
without accents, with explicit exclusions where folding collides ("ngạt mũi"
vs "ngất", "một xíu" vs "xỉu", "từ từ" vs "tự tử", "đã tìm" vs "da tím").
Denied mentions, questions about a term, and events placed long ago are
skipped. The vocabulary is engineering config, PENDING_CLINICAL_REVIEW.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import asdict, dataclass

from src.agents.guardrails import screen_red_flag_candidate

from .corpus import fold


@dataclass(frozen=True)
class EmergencySignal:
    rule_id: str
    kind: str  # "EMERGENCY" | "SELF_HARM"
    label: str  # Vietnamese description, shown to patient and nurse
    trigger: str  # the matched text, as screened

    def as_dict(self) -> dict[str, str]:
        return asdict(self)


@dataclass(frozen=True)
class _Rule:
    rule_id: str
    kind: str
    label: str
    accented: str
    folded: str | None = None  # explicit override where fold(accented) collides


_RULES = (
    _Rule(
        "SA_SCREEN_SYNCOPE_V1", "EMERGENCY", "ngất hoặc bất tỉnh",
        r"(?<!thơm )ngất(?! mũi)|(?<!một )(?<!chút )(?<!tí )xỉu|bất tỉnh|lịm đi|mất ý thức"
        r"|(?:gọi|lay) (?:mãi )?không tỉnh|không tỉnh lại",
    ),
    _Rule(
        "SA_SCREEN_SEIZURE_V1", "EMERGENCY", "co giật",
        r"co giật|lên cơn giật|lên cơn động kinh|sùi bọt mép|giật toàn thân",
    ),
    _Rule(
        "SA_SCREEN_BLEEDING_GI_V1", "EMERGENCY", "nôn hoặc ho ra máu",
        r"(?:nôn|ói|mửa) (?:ra )?(?:rất )?(?:nhiều )?máu|thổ huyết|ho ra (?:rất )?(?:nhiều )?máu"
        r"|đi (?:ngoài|cầu) ra (?:rất )?nhiều máu|phân đen như bã cà phê",
    ),
    _Rule(
        "SA_SCREEN_HEAVY_BLEEDING_V1", "EMERGENCY", "chảy máu nhiều",
        r"chảy (?:rất )?nhiều máu|chảy máu (?:rất )?nhiều|máu chảy (?:rất )?nhiều"
        r"|chảy máu không (?:cầm|ngừng|dừng)|máu (?:chảy )?không (?:cầm|ngừng|dừng)|mất nhiều máu"
        r"|máu phun|băng huyết",
    ),
    _Rule(
        "SA_SCREEN_CHEST_PAIN_V1", "EMERGENCY", "đau ngực lan ra tay, vai, hàm hoặc kèm vã mồ hôi",
        r"đau (?:tức |thắt |bóp |nhói )?ngực[^.?!]{0,40}(?:lan|lên|xuống|sang|ra)[^.?!]{0,15}"
        r"(?:tay|vai|hàm|cằm|lưng)|đau (?:tức |thắt |bóp )?ngực[^.?!]{0,40}vã mồ hôi",
    ),
    _Rule(
        "SA_SCREEN_CYANOSIS_V1", "EMERGENCY", "tím tái",
        r"tím tái|tái tím|tím ngắt|môi (?:bị )?tím|tím môi",
        folded=r"tim tai|tai tim|tim ngat|moi (?:bi )?tim(?! (?:hieu|thay|ra|kiem|duoc|cach|vien|nha))|tim moi",
    ),
    _Rule(
        "SA_SCREEN_RESPIRATORY_V1", "EMERGENCY", "khó thở nặng",
        r"ngạt thở|thở hổn hển|thở không ra hơi|không thở (?:được|nổi)|thở rít"
        r"|khó thở (?:dữ dội|nặng|không nói được|không nằm được)|không nói (?:được|hết) (?:thành )?câu",
    ),
    _Rule(
        "SA_SCREEN_STROKE_V1", "EMERGENCY", "dấu hiệu đột quỵ (méo miệng, yếu hoặc tê nửa người)",
        r"méo miệng|liệt nửa người|yếu nửa người|tê nửa người|mặt (?:bị )?lệch"
        r"|(?:đột ngột )?nói ngọng đột ngột|đột ngột nói ngọng",
    ),
    _Rule(
        "SA_SCREEN_ANAPHYLAXIS_V1", "EMERGENCY", "sưng môi, lưỡi hoặc họng kèm khó thở",
        r"sưng (?:môi|lưỡi|họng|mặt)[^.?!]{0,30}khó thở|khó thở[^.?!]{0,30}sưng (?:môi|lưỡi|họng|mặt)"
        r"|sốc phản vệ",
    ),
    _Rule(
        "SA_SCREEN_SELF_HARM_V1", "SELF_HARM", "ý định tự làm hại bản thân",
        r"tự tử|tự sát|không muốn sống nữa|tự làm hại (?:bản thân|mình)|kết thúc cuộc (?:đời|sống)",
        # "tu tu" is also "từ từ" (slowly) once accents are gone.
        folded=r"tu sat|khong muon song nua|tu lam hai (?:ban than|minh)|ket thuc cuoc (?:doi|song)",
    ),
)

_ACCENTED_NEGATORS = frozenset({"không", "chưa", "chẳng", "chả", "ko", "hông"})
# Folded "cha"/"chang" are also "cha" (father) and "chàng": left out on purpose.
_FOLDED_NEGATORS = frozenset({"khong", "chua", "ko", "hong"})
_NEGATION_WINDOW = 3

_EDUCATIONAL = (
    "là gì", "nghĩa là gì", "có nghĩa gì", "giải thích", "tìm hiểu", "dấu hiệu của",
    "triệu chứng của", "làm sao biết", "phòng tránh", "phòng ngừa",
)
_LONG_AGO = (
    "năm ngoái", "năm trước", "mấy năm", "hồi nhỏ", "từ nhỏ", "ngày xưa", "tiền sử",
    "hồi trước", "trước đây", "đã từng", "từng bị",
)
_RECENT = (
    "vừa", "lúc nãy", "hồi nãy", "ban nãy", "hôm nay", "đang", "bây giờ", "mới", "sáng nay",
    "trưa nay", "chiều nay", "tối nay", "đêm nay", "giờ",
)


def _lower(text: str) -> str:
    return re.sub(r"\s+", " ", unicodedata.normalize("NFC", text).lower()).strip()


def _has_any(markers: tuple[str, ...], accented_text: str, folded_text: str) -> bool:
    return any(
        re.search(rf"\b{re.escape(marker)}\b", accented_text)
        or re.search(rf"\b{re.escape(fold(marker))}\b", folded_text)
        for marker in markers
    )


def _is_negated(text: str, start: int, negators: frozenset[str]) -> bool:
    # Only the words right before the match, and never across a clause break.
    clause = re.split(r"[,;.!?]", text[:start])[-1]
    return any(word in negators for word in clause.split()[-_NEGATION_WINDOW:])


def _compile(pattern: str) -> re.Pattern[str]:
    return re.compile(rf"(?:{pattern})")


_COMPILED = tuple(
    (rule, _compile(rule.accented), _compile(rule.folded or fold(rule.accented)))
    for rule in _RULES
)


def _match_rules(accented_text: str, folded_text: str, skip_events: bool) -> EmergencySignal | None:
    for rule, accented_re, folded_re in _COMPILED:
        if skip_events and rule.kind != "SELF_HARM":
            continue
        for text, pattern, negators in (
            (accented_text, accented_re, _ACCENTED_NEGATORS),
            (folded_text, folded_re, _FOLDED_NEGATORS),
        ):
            for match in pattern.finditer(text):
                if not _is_negated(text, match.start(), negators):
                    return EmergencySignal(rule.rule_id, rule.kind, rule.label, match.group(0))
    return None


def screen_patient_message(message: str) -> EmergencySignal | None:
    """The first emergency signal in ``message``, or ``None``."""
    accented_text = _lower(message)
    if not accented_text:
        return None
    folded_text = fold(message)
    if _has_any(_EDUCATIONAL, accented_text, folded_text):
        return None
    # "năm ngoái tôi bị ngất một lần" is history, not an emergency now --
    # unless the same message also places something in the present.
    long_ago_only = _has_any(_LONG_AGO, accented_text, folded_text) and not _has_any(
        _RECENT, accented_text, folded_text
    )

    signal = _match_rules(accented_text, folded_text, skip_events=long_ago_only)
    if signal or long_ago_only:
        return signal

    # The legacy reflex adds its own vocabulary and patient-reported vitals
    # ("spo2 78, thở 42"); only its match is used, never its ESI.
    legacy = screen_red_flag_candidate(message)
    if legacy:
        rule_id = str(legacy.get("safety_rule_id") or "LEGACY_REFLEX")
        label = (
            "chỉ số sinh hiệu ở ngưỡng nguy hiểm"
            if "VITALS" in rule_id
            else str(legacy.get("trigger_keyword") or "dấu hiệu nguy kịch")
        )
        return EmergencySignal(rule_id, "EMERGENCY", label, str(legacy.get("trigger_keyword") or ""))
    return None


def emergency_guidance(signal: EmergencySignal) -> str:
    """Fixed patient-facing text for a screen hit -- never sent to a model."""
    if signal.kind == "SELF_HARM":
        return (
            "Mình rất tiếc vì bạn đang phải trải qua điều này. Nếu bạn đang nghĩ tới việc làm hại bản thân, "
            "hãy gọi 115 ngay hoặc nói với một người đang ở gần bạn. "
            "Ca của bạn đã được đánh dấu để nhân viên y tế xem trước."
        )
    return (
        f"Lưu ý an toàn: bạn có nhắc tới {signal.label}. Nếu tình trạng này đang hoặc vừa xảy ra, "
        "hãy gọi cấp cứu 115 ngay, đừng chờ trả lời hết các câu hỏi. "
        "Ca của bạn đã được đánh dấu để nhân viên y tế xem trước."
    )
