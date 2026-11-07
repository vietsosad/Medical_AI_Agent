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


@pytest.mark.parametrize(
    "message",
    [
        # chest pain or pressure spreading, not only "đau ngực ... lan"
        "từ sáng ngực em cứ thắt lại, lan ra sau lưng",
        "ông kêu nặng ngực, nặng lan xuống cả hai cánh tay",
        # breathlessness described by its effect on speech or at rest
        "anh ấy nói vài chữ lại phải ngừng lấy hơi",
        "ngồi yên cũng khó thở, nói không hết câu",
        # stroke signs in everyday words
        "thấy miệng mẹ hơi xệ một bên",
        "miệng ông lệch hẳn sang một bên",
        "tự nhiên chị ấy ôm đầu rồi nói lộn xộn",
        # GI bleeding without the words "nôn ra máu"
        "bà nôn ra mấy lần cái gì nâu nâu như bã cà phê",
        "chú ấy vừa ói ra cả vũng máu",
        "đi cầu ra toàn máu tươi, đỏ lòm cả bồn cầu",
        "đi ngoài phân đen như hắc ín",
        # heavy bleeding
        "máu vẫn ra ồ ạt",
        "cứ một tiếng là ướt sũng một miếng băng",
        "chảy máu ko cầm",
        # unresponsive, cyanosis, cold numb limb
        "nó nằm bất động, gọi không trả lời",
        "môi bé hơi tím",
        "cánh tay đột ngột lạnh ngắt, trắng bệch, tê bì",
    ],
)
def test_v2_emergency_wordings_are_caught(message: str) -> None:
    signal = screen_patient_message(message)

    assert signal is not None
    assert signal.kind == "EMERGENCY"


@pytest.mark.parametrize(
    "message",
    [
        "nhiều đêm tôi nghĩ giá mà ngủ một giấc rồi không dậy nữa",
        "anh nhắn là đã uống thuốc để không phải sống nữa",
        "em nghĩ hay là làm đau mình cho xong",
        "dạo này em chán sống lắm",
    ],
)
def test_indirect_self_harm_wordings_are_caught(message: str) -> None:
    signal = screen_patient_message(message)

    assert signal is not None and signal.kind == "SELF_HARM"


@pytest.mark.parametrize(
    "message",
    [
        # typed WITH accents, these only collide once folded
        "bé buồn nên mặt xìu xuống",
        "từ sáng cháu mới đi tiểu một lần, ít xíu",
        "lần đó chỉ ra mấy viên nhỏ xíu",
        "tay lạnh ngắt vì trời rét quá",
        "bàn tay đổi màu tái lạnh",
        # no word boundary used to make "doi mau" read as "oi mau"
        "ban tay doi mau tai lanh",
        # the legacy reflex used to ignore the denial or read across a clause
        "ho khan, sổ mũi. Không sốt, không khó thở, máy đo oxy ở nhà 98%.",
        "chỗ bỏng cỡ đồng xu, đỏ, rát. Không bị ở mặt, không hít khói.",
        "quên uống thuốc hai hôm. Không đau đầu, không đau ngực, không khó thở.",
        "Hiện tôi không khó thở, không khò khè. Máy đo báo SpO2 98%.",
        # a denial inside a wide pattern
        "đau ngực nhưng không lan ra tay",
        "sưng môi nhưng không khó thở",
        "môi không tím",
        "khi ngồi yên thì không khó thở",
    ],
)
def test_no_v2_alarm_on_accented_look_alikes_or_denials(message: str) -> None:
    assert screen_patient_message(message) is None


def test_guidance_is_conditional_and_points_at_115() -> None:
    signal = screen_patient_message("con tôi ngất xỉu")
    assert signal is not None

    text = emergency_guidance(signal)

    assert "115" in text
    assert "Nếu tình trạng này đang hoặc vừa xảy ra" in text
    assert signal.label in text
