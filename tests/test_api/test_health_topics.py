"""Kiểm định lớp nội dung sức khỏe: seed hợp lệ và LLM bị ràng buộc chặt."""

from __future__ import annotations

import json

import pytest

from src.models.db_models import HealthTopic
from src.models.health_schemas import HealthTopicDetailDTO, HealthTopicSummaryDTO
from src.services import health_topic_summary
from src.services.health_topic_summary import (
    CONTENT_SAFETY_PATTERNS,
    generate_ai_summary,
    violated_rule,
)
from src.services.health_topics import load_seed_topics


class _StubResponse:
    def __init__(self, content: str) -> None:
        self.content = content


class _StubLLM:
    """Đứng thay LLM thật để kiểm định luồng parse -> validate -> chặn nội dung."""

    model_name = "stub-model"

    def __init__(self, content: str) -> None:
        self._content = content
        self.calls = 0

    async def ainvoke(self, _messages: object) -> _StubResponse:
        self.calls += 1
        return _StubResponse(self._content)


class _ExplodingLLM:
    model_name = "stub-exploding"

    async def ainvoke(self, _messages: object) -> _StubResponse:
        raise RuntimeError("upstream unavailable")


def _topic() -> HealthTopic:
    return HealthTopic(
        slug="cum-mua",
        name="Cúm mùa",
        summary="Nhiễm trùng đường hô hấp do virus cúm, lây qua giọt bắn.",
        symptoms=["Sốt và ớn lạnh", "Ho khan"],
        warning_signs=["Khó thở"],
        prevention=["Rửa tay thường xuyên"],
        when_to_seek_care="Đi khám sớm nếu thuộc nhóm nguy cơ cao.",
        source="WHO",
        source_url="https://www.who.int/",
    )


def _install(monkeypatch: pytest.MonkeyPatch, llm: object) -> None:
    monkeypatch.setattr(health_topic_summary, "get_resilient_llm", lambda tier="small": llm)


# ---------------------------------------------------------------------------
# Seed
# ---------------------------------------------------------------------------

def test_seed_file_parses_and_carries_a_citable_source() -> None:
    topics = load_seed_topics()
    assert len(topics) >= 3
    for topic in topics:
        assert topic.symptoms and topic.warning_signs and topic.prevention
        assert str(topic.source_url).startswith("https://")
        assert topic.when_to_seek_care.strip()


def test_seed_slugs_are_unique() -> None:
    slugs = [topic.slug for topic in load_seed_topics()]
    assert len(slugs) == len(set(slugs))


def test_seed_content_states_no_epidemiological_claims() -> None:
    """Seed là nội dung giáo dục, không phải số liệu dịch tễ.

    Seed do người biên soạn và có trích nguồn nên được phép nhắc tới việc tuân thủ
    điều trị ("uống thuốc đúng theo chỉ định"); luật cấm kê đơn chỉ áp cho đầu ra
    do mô hình sinh ra. Ở đây kiểm tra nhóm luật dành cho mọi nội dung.
    """
    for topic in load_seed_topics():
        blob = " ".join([topic.summary, *topic.symptoms, *topic.warning_signs, *topic.prevention])
        assert violated_rule(blob, CONTENT_SAFETY_PATTERNS) is None, (
            f"{topic.slug} chứa tuyên bố dịch tễ hoặc khẳng định chẩn đoán"
        )


def test_seed_prevention_advice_is_not_treated_as_prescribing() -> None:
    """Luật cấm kê đơn vẫn phải chặn đầu ra LLM, kể cả khi seed được miễn."""
    assert violated_rule("Hãy uống thuốc kháng sinh khi bị sốt") == "hướng dẫn dùng thuốc"
    assert violated_rule("Uống thuốc đúng theo chỉ định", CONTENT_SAFETY_PATTERNS) is None


# ---------------------------------------------------------------------------
# LLM: chấp nhận
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_valid_json_summary_is_accepted(monkeypatch: pytest.MonkeyPatch) -> None:
    _install(monkeypatch, _StubLLM(json.dumps({"summary": "Cúm là bệnh hô hấp do virus, lây qua giọt bắn khi ho."})))
    result = await generate_ai_summary(_topic())
    assert result is not None
    text, model = result
    assert "giọt bắn" in text
    assert model == "stub-model"


@pytest.mark.asyncio
async def test_json_wrapped_in_a_markdown_fence_is_still_accepted(monkeypatch: pytest.MonkeyPatch) -> None:
    fenced = '```json\n{"summary": "Cúm là bệnh hô hấp do virus, lây qua giọt bắn khi ho."}\n```'
    _install(monkeypatch, _StubLLM(fenced))
    assert await generate_ai_summary(_topic()) is not None


# ---------------------------------------------------------------------------
# LLM: từ chối (đây mới là phần an toàn)
# ---------------------------------------------------------------------------

@pytest.mark.parametrize(
    ("bad_summary", "reason"),
    [
        ("Năm nay ghi nhận 12000 ca mắc cúm trên cả nước.", "số ca"),
        ("Khoảng 35% dân số sẽ mắc cúm mỗi mùa.", "tỷ lệ phần trăm"),
        ("Đây là bệnh phổ biến nhất hiện nay tại Việt Nam.", "xếp hạng"),
        ("Số ca đang gia tăng nhanh theo xu hướng năm nay.", "tuyên bố dịch tễ"),
        ("Nếu bạn ho và sốt thì bạn đang bị cúm mùa.", "khẳng định chẩn đoán"),
        ("Hãy uống thuốc kháng sinh với liều lượng phù hợp.", "hướng dẫn dùng thuốc"),
    ],
)
@pytest.mark.asyncio
async def test_forbidden_content_is_refused(
    monkeypatch: pytest.MonkeyPatch, bad_summary: str, reason: str
) -> None:
    _install(monkeypatch, _StubLLM(json.dumps({"summary": bad_summary})))
    assert await generate_ai_summary(_topic()) is None, f"phải chặn: {reason}"


@pytest.mark.asyncio
async def test_non_json_output_is_refused(monkeypatch: pytest.MonkeyPatch) -> None:
    _install(monkeypatch, _StubLLM("Cúm mùa là một bệnh hô hấp thường gặp."))
    assert await generate_ai_summary(_topic()) is None


@pytest.mark.asyncio
async def test_output_missing_the_schema_key_is_refused(monkeypatch: pytest.MonkeyPatch) -> None:
    _install(monkeypatch, _StubLLM(json.dumps({"tom_tat": "Cúm là bệnh hô hấp do virus lây qua giọt bắn."})))
    assert await generate_ai_summary(_topic()) is None


@pytest.mark.asyncio
async def test_an_overlong_summary_is_refused(monkeypatch: pytest.MonkeyPatch) -> None:
    _install(monkeypatch, _StubLLM(json.dumps({"summary": "Cúm mùa. " * 200})))
    assert await generate_ai_summary(_topic()) is None


@pytest.mark.asyncio
async def test_an_llm_outage_leaves_the_seed_summary_in_place(monkeypatch: pytest.MonkeyPatch) -> None:
    _install(monkeypatch, _ExplodingLLM())
    topic = _topic()
    assert await generate_ai_summary(topic) is None
    # Thẻ trên trang chủ vẫn hiển thị được bằng nội dung seed.
    assert HealthTopicSummaryDTO.from_model(topic).summary == topic.summary


# ---------------------------------------------------------------------------
# DTO
# ---------------------------------------------------------------------------

def test_dto_prefers_the_ai_summary_and_flags_that_it_is_ai_assisted() -> None:
    topic = _topic()
    topic.ai_summary = "Bản diễn giải dễ hiểu hơn cho người đọc phổ thông."

    card = HealthTopicSummaryDTO.from_model(topic)
    assert card.summary == topic.ai_summary
    assert card.ai_assisted is True


def test_dto_falls_back_to_the_seed_summary_when_no_ai_summary_exists() -> None:
    card = HealthTopicSummaryDTO.from_model(_topic())
    assert card.summary == _topic().summary
    assert card.ai_assisted is False


def test_detail_dto_always_carries_the_disclaimer_and_warning_signs() -> None:
    detail = HealthTopicDetailDTO.from_model(_topic())
    assert "không thay thế" in detail.disclaimer
    assert detail.warning_signs == ["Khó thở"]
    assert detail.when_to_seek_care.strip()


def test_card_dto_does_not_leak_warning_signs_to_the_homepage() -> None:
    """Trang chủ chỉ hiển thị tóm tắt; dấu hiệu cảnh báo thuộc màn hình chi tiết."""
    assert "warning_signs" not in HealthTopicSummaryDTO.model_fields
