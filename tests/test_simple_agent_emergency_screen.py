"""The pre-LLM emergency screen (src/simple_agent/emergency_screen.py).

Both lists are the contract. The first is what must never wait for a model;
the second is what must not raise an alarm -- denials, questions about a
term, events from long ago, and the look-alikes that appear once a patient
types without accents. An alarm that fires on "ngạt mũi" or "đau từ từ" is
one patients learn to ignore.
"""

from __future__ import annotations

import pytest

from src.simple_agent.emergency_screen import emergency_guidance, screen_patient_message


@pytest.mark.parametrize(
    "message",
    [
        "con tôi ngất xỉu",
        "mẹ tôi vừa ngất",
        "lúc nãy em bị ngất",  # recent, not historical (F-E01 class)
        "tôi bị xỉu",
        "bố tôi bất tỉnh",
        "gọi không tỉnh",
        "con tôi co giật",
        "tôi nôn ra máu",
        "nôn ra rất nhiều máu",
        "chảy máu nhiều không cầm",
        "đau ngực lan ra tay trái",
        "đau ngực, vã mồ hôi",
        "môi tím tái",
        "không thở được",
        "khó thở dữ dội",
        "sưng môi rồi khó thở",
        "méo miệng nói ngọng",
        "spo2 78 thở 42",
        # typed without accents
        "toi bi ngat xiu",
        "con toi co giat",
        "non ra mau",
        "con tôi bị ngat xiu",
    ],
)
def test_emergency_phrases_are_caught_before_any_model(message: str) -> None:
    signal = screen_patient_message(message)

    assert signal is not None
    assert signal.kind == "EMERGENCY"


@pytest.mark.parametrize("message", ["tôi muốn tự tử", "toi muon tu sat", "tôi không muốn sống nữa"])
def test_self_harm_is_caught_with_its_own_kind(message: str) -> None:
    signal = screen_patient_message(message)

    assert signal is not None and signal.kind == "SELF_HARM"


@pytest.mark.parametrize(
    "message",
    [
        # denials
        "tôi không bị ngất",
        "không co giật",
        "chưa từng ngất bao giờ",
        "không nôn ra máu",
        "không chảy máu nhiều",
        # a question about the term
        "ngất là gì",
        # long ago, nothing current
        "năm ngoái tôi bị ngất một lần",
        # look-alikes once accents are gone
        "tôi bị ngạt mũi",
        "toi bi ngat mui",
        "đau một xíu thôi",
        "dau mot xiu thoi",
        "dau tu tu tang dan",  # từ từ, not tự tử
        "toi da tim hieu roi",  # đã tìm hiểu, not da tím
        "toi moi tim thay thuoc",  # mới tìm thấy, not môi tím
        "cha toi bi dau bung",  # cha = father, not a negator
        # hyperbole and unqualified symptoms stay conversational
        "đau bụng muốn chết",
        "khó thở nhẹ",
        "đau ngực",
        "tôi đau đầu",
    ],
)
def test_no_alarm_on_denials_questions_history_or_look_alikes(message: str) -> None:
    assert screen_patient_message(message) is None


def test_guidance_is_conditional_and_points_at_115() -> None:
    signal = screen_patient_message("con tôi ngất xỉu")
    assert signal is not None

    text = emergency_guidance(signal)

    assert "115" in text
    assert "Nếu tình trạng này đang hoặc vừa xảy ra" in text
    assert signal.label in text
