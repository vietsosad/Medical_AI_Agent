"""Wording for the questions the adaptive planner selects.

The planner decides *what* is worth asking; this module decides how to say it.
They are separate because the planner reasons over canonical keys
(``headache.course``) and a patient must never see one.

Three things distinguish this from the fixed question engine it sits beside:

* Questions name the problem they are about. With two active problems, "triệu
  chứng này bắt đầu khi nào?" is ambiguous and the answer cannot be attributed;
  "cơn đau đầu bắt đầu khi nào?" can.
* The first question of a multi-problem case opens by saying what was
  understood, so the patient can correct the agent's reading of their own
  message before answering anything.
* An objective measurement is asked for as something the patient may not have.
  Not having a thermometer is an answer, never a failure to comply.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from src.agents.nodes.fact_extraction import SYMPTOM_DISPLAY_VI, describe_fact_key
from src.agents.problem_state import ProblemState

# One template per attribute. ``{label}`` is the problem in the patient's own
# clinical vocabulary ("đau đầu"), never a canonical key.
_ATTRIBUTE_QUESTIONS: dict[str, str] = {
    "onset_time": "Tình trạng {label} bắt đầu từ khi nào?",
    "course": (
        "{label_cap} xuất hiện đột ngột hay tăng dần lên? "
        "Hiện đang nặng thêm, giữ nguyên hay đỡ hơn?"
    ),
    "location": "{label_cap} tập trung rõ nhất ở vùng nào?",
    "character": (
        "Bạn mô tả giúp cảm giác {label}: âm ỉ, nhói, bóp nghẹt hay kiểu khác?"
    ),
    "severity_score": (
        "Nếu chấm mức độ {label} từ 0 đến 10, hiện tại bạn ở mức nào?"
    ),
    "radiation": (
        "{label_cap} có lan sang vị trí nào khác không? "
        "Nếu không lan, bạn nói rõ giúp là không lan."
    ),
    "frequency": "Tình trạng {label} xuất hiện khoảng bao nhiêu lần?",
    "worst_ever": (
        "Đây có phải cơn {label} dữ dội nhất bạn từng gặp không?"
    ),
    "associated_neuro": (
        "Kèm theo {label}, bạn có thấy yếu hoặc tê một bên người, "
        "nói khó, hay nhìn mờ/nhìn đôi không?"
    ),
    "exertion": (
        "{label_cap} có tăng lên khi bạn gắng sức hoặc đi lại không?"
    ),
    "rest_or_exertion": (
        "Bạn thấy {label} cả khi đang nghỉ ngơi, hay chỉ khi gắng sức?"
    ),
    "bowel_change": (
        "Kèm theo {label}, việc đi ngoài của bạn có gì thay đổi không?"
    ),
    "blood": "Bạn có thấy máu khi {label} không?",
    "volume": "Lượng máu chảy khoảng bao nhiêu, và đã cầm được chưa?",
    "relation_to_primary": (
        "Tình trạng {label} xuất hiện cùng lúc với triệu chứng chính "
        "hay ở thời điểm khác?"
    ),
}

# Objective measurements. Phrased so that "tôi không có máy đo" is a complete,
# acceptable answer.
_VITAL_QUESTIONS: dict[str, str] = {
    "vital.temperature_c": (
        "Nếu bạn có nhiệt kế, bạn đo giúp nhiệt độ hiện tại được không? "
        "Nếu không có, bạn cứ nói là chưa đo được."
    ),
    "vital.spo2": (
        "Nếu bạn có máy đo SpO₂ ở nhà, chỉ số hiện tại là bao nhiêu? "
        "Nếu không có máy, bạn cứ nói là chưa đo được."
    ),
    "vital.heart_rate": (
        "Nếu bạn đo được mạch hoặc có đồng hồ/máy đo, nhịp tim hiện tại "
        "khoảng bao nhiêu lần một phút? Nếu chưa đo được thì không sao."
    ),
    "vital.systolic_bp": (
        "Nếu bạn có máy đo huyết áp, số đo gần nhất là bao nhiêu? "
        "Nếu chưa đo được, bạn cứ nói là chưa có số đo."
    ),
    "vital.respiratory_rate": (
        "Nếu đếm được, nhịp thở của bạn khoảng bao nhiêu lần một phút? "
        "Nếu chưa đếm được thì không sao."
    ),
}


@dataclass(frozen=True)
class AdaptiveQuestion:
    """One rendered question plus the slot its answer is recorded under."""

    field: str
    text: str
    structured_payload: dict[str, Any] | None = None


def _capitalize(text: str) -> str:
    return text[:1].upper() + text[1:] if text else text


def _join_vi(labels: list[str]) -> str:
    if len(labels) <= 1:
        return "".join(labels)
    return f"{', '.join(labels[:-1])} và {labels[-1]}"


def opening_acknowledgement(problem_state: ProblemState) -> str:
    """Say what was understood before asking anything.

    Only produced once a case has more than one active problem, or a new
    problem has just been raised. A single-symptom opener does not need the
    agent to read the message back.
    """
    active = problem_state.active_problems
    newly = [
        problem_state.problem(concept)
        for concept in problem_state.newly_mentioned
        if problem_state.problem(concept) is not None
    ]
    if newly and len(active) > len(newly):
        labels = _join_vi([item.label_vi for item in newly if item])
        return (
            f"Mình đã ghi nhận thêm {labels} vào phần triệu chứng đang theo dõi, "
            "cùng với những gì bạn kể trước đó."
        )
    if len(active) > 1:
        labels = _join_vi([item.label_vi for item in active])
        count = "hai" if len(active) == 2 else "các"
        return (
            f"Hiện mình ghi nhận {count} triệu chứng chính là {labels}."
        )
    return ""


def _severity_payload() -> dict[str, Any]:
    return {
        "type": "scale",
        "optionsType": "scale",
        "minScale": 0,
        "maxScale": 10,
        "submitted": False,
    }


def render_question(
    target: str,
    attribute: str,
    problem_label: str,
    *,
    lead_in: str = "",
) -> AdaptiveQuestion | None:
    """Render one planner target as a patient-facing question.

    ``None`` means this module has no wording for the target. The caller must
    then fall back to the existing question engine rather than putting a raw
    identifier in front of a patient.
    """
    if target.startswith("vital."):
        text = _VITAL_QUESTIONS.get(target)
        if not text:
            return None
        return AdaptiveQuestion(field=target, text=_with_lead(lead_in, text))

    if target.startswith("symptom."):
        concept = target.removeprefix("symptom.")
        label = SYMPTOM_DISPLAY_VI.get(concept)
        if not label:
            return None
        text = f"Bạn có thấy {label} kèm theo không?"
        return AdaptiveQuestion(field=target, text=_with_lead(lead_in, text))

    template = _ATTRIBUTE_QUESTIONS.get(attribute)
    if not template:
        return None
    text = template.format(
        label=problem_label,
        label_cap=_capitalize(problem_label),
    )
    payload = _severity_payload() if attribute == "severity_score" else None
    return AdaptiveQuestion(
        field=target,
        text=_with_lead(lead_in, text),
        structured_payload=payload,
    )


def _with_lead(lead_in: str, text: str) -> str:
    if not lead_in:
        return text
    return f"{lead_in.rstrip()} {text}"


def canonical_key_for_field(field: str) -> str | None:
    """The canonical key an answer to this adaptive slot is recorded under.

    Returns ``None`` for anything that is not an adaptive target, so the legacy
    slot-filling path keeps its existing fields untouched.
    """
    name = str(field or "").strip()
    if not name:
        return None
    if name.startswith(("symptom.", "vital.")):
        return name
    if "." in name:
        concept, attribute = name.split(".", 1)
        if attribute in _ATTRIBUTE_QUESTIONS and concept in _known_concepts():
            return name
    return None


def _known_concepts() -> frozenset[str]:
    from src.agents.problem_state import PROBLEM_PROFILES

    return frozenset(PROBLEM_PROFILES) | frozenset(SYMPTOM_DISPLAY_VI)


def describe_target(field: str) -> str:
    """Patient-facing wording for an adaptive target, for summaries and audit."""
    name = str(field or "")
    if name.startswith(("symptom.", "vital.")):
        return describe_fact_key(name)
    if "." in name:
        concept, attribute = name.split(".", 1)
        label = SYMPTOM_DISPLAY_VI.get(concept, concept)
        attribute_label = {
            "onset_time": "thời điểm bắt đầu",
            "course": "diễn tiến",
            "location": "vị trí",
            "character": "tính chất",
            "severity_score": "mức độ",
            "radiation": "hướng lan",
            "frequency": "tần suất",
            "worst_ever": "mức dữ dội nhất từng gặp",
            "associated_neuro": "dấu hiệu thần kinh kèm theo",
            "exertion": "liên quan gắng sức",
            "rest_or_exertion": "khi nghỉ hay khi gắng sức",
            "bowel_change": "thay đổi đại tiện",
            "blood": "có máu hay không",
            "volume": "lượng máu",
            "relation_to_primary": "liên quan tới triệu chứng chính",
        }.get(attribute, attribute)
        return f"{attribute_label} của {label}"
    return describe_fact_key(name)
