"""Diễn giải nội dung sức khỏe bằng LLM - có ràng buộc và có thể từ chối kết quả.

Mô hình ngôn ngữ ở đây KHÔNG phải nguồn dữ liệu y tế. Nó chỉ được phép viết lại
cho dễ đọc phần nội dung đã có sẵn trong seed (đã trích dẫn nguồn). Mọi thứ khác
đều bị chặn:

- không số ca, tỷ lệ, xu hướng dịch, mức độ phổ biến;
- không khẳng định người đọc đang mắc bệnh;
- không kê đơn, không hướng dẫn liều thuốc;
- không tự bịa nguồn.

Đầu ra là JSON có schema, được Pydantic kiểm định, rồi đi qua một bộ lọc từ khóa
cấm. Nếu bất kỳ bước nào thất bại, hệ thống giữ nguyên bản tóm tắt seed - nội dung
hiển thị luôn có đường lui an toàn, không bao giờ phụ thuộc vào việc LLM trả lời đúng.
"""

from __future__ import annotations

import json
import re

from pydantic import BaseModel, Field, ValidationError

from src.models.db_models import HealthTopic
from src.services.llm_provider import get_resilient_llm

MAX_AI_SUMMARY_CHARS = 400

SYSTEM_PROMPT = """Bạn là biên tập viên nội dung y tế cho một ứng dụng sàng lọc lâm sàng tiếng Việt.

Nhiệm vụ DUY NHẤT: viết lại đoạn tóm tắt được cung cấp cho dễ hiểu với người đọc phổ thông.

Quy tắc bắt buộc:
- Chỉ dùng thông tin có trong dữ liệu được cung cấp. Không thêm bất kỳ dữ kiện mới nào.
- TUYỆT ĐỐI KHÔNG nêu số ca mắc, tỷ lệ phần trăm, xu hướng dịch, mức độ phổ biến hay thống kê.
- TUYỆT ĐỐI KHÔNG khẳng định người đọc đang mắc bệnh. Không dùng "bạn đang bị", "bạn mắc".
- TUYỆT ĐỐI KHÔNG kê đơn, không nêu tên thuốc, liều lượng hay phác đồ điều trị.
- Không bịa nguồn tài liệu.
- Giữ giọng văn bình tĩnh, trung tính, không gây hoang mang.
- Độ dài tối đa 60 từ, viết thành 1-2 câu.

Chỉ trả về JSON đúng định dạng sau, không kèm giải thích hay markdown:
{"summary": "..."}"""


class HealthSummaryOutput(BaseModel):
    """Schema đầu ra bắt buộc của LLM."""

    summary: str = Field(min_length=20, max_length=MAX_AI_SUMMARY_CHARS)


# Bộ lọc hậu kiểm áp lên ĐẦU RA CỦA LLM, phòng trường hợp mô hình phớt lờ hướng dẫn.
# Chia theo nhóm vì seed do người biên soạn và đầu ra LLM có mức tin cậy khác nhau:
# nội dung seed đã được trích nguồn và rà soát nên được phép nói tới việc tuân thủ
# điều trị ("uống thuốc đúng theo chỉ định"), còn LLM thì tuyệt đối không.
EPIDEMIOLOGY_PATTERNS: tuple[tuple[str, str], ...] = (
    (r"\d+\s*%", "tỷ lệ phần trăm"),
    # Chỉ chặn việc ĐẾM ca. "Phần lớn ca bệnh nhẹ" là mô tả mức độ nặng nhẹ về mặt
    # lâm sàng, hợp lệ trong nội dung giáo dục và không phải số liệu dịch tễ.
    (r"\d[\d.,]*\s*(?:ca|trường hợp|người mắc)\b", "số ca cụ thể"),
    (r"\bsố\s+(?:ca|trường hợp|người mắc)\b", "số ca"),
    (r"\b(?:ca|trường hợp)\s+(?:mắc|nhiễm)\s+mới\b", "ca mắc mới"),
    (r"\bphổ biến nhất\b|\bnhiều nhất\b|\bhàng đầu\b", "xếp hạng mức độ phổ biến"),
    (r"\bbùng phát\b|\bdịch bùng\b|\bgia tăng\b|\bxu hướng\b|\bthống kê\b", "tuyên bố dịch tễ"),
)

DIAGNOSIS_PATTERNS: tuple[tuple[str, str], ...] = (
    (
        r"\bbạn đang bị\b|\bbạn bị\b|\bbạn mắc\b|\bbạn đã mắc\b|\bchắc chắn mắc\b",
        "khẳng định chẩn đoán",
    ),
)

PRESCRIPTION_PATTERNS: tuple[tuple[str, str], ...] = (
    (r"\bkê đơn\b|\bliều dùng\b|\bliều lượng\b|\bkháng sinh\b|\buống thuốc\b", "hướng dẫn dùng thuốc"),
)

#: Luật áp cho mọi nội dung, kể cả seed do người viết.
CONTENT_SAFETY_PATTERNS: tuple[tuple[str, str], ...] = EPIDEMIOLOGY_PATTERNS + DIAGNOSIS_PATTERNS

#: Luật đầy đủ, chỉ áp cho đầu ra do mô hình sinh ra.
FORBIDDEN_PATTERNS: tuple[tuple[str, str], ...] = CONTENT_SAFETY_PATTERNS + PRESCRIPTION_PATTERNS


def violated_rule(
    text: str,
    patterns: tuple[tuple[str, str], ...] = FORBIDDEN_PATTERNS,
) -> str | None:
    """Tên quy tắc bị vi phạm, hoặc None nếu nội dung sạch."""
    lowered = text.lower()
    for pattern, label in patterns:
        if re.search(pattern, lowered):
            return label
    return None


def _extract_json_object(raw: str) -> dict[str, object] | None:
    """Bóc lấy JSON object đầu tiên, chịu được trường hợp model bọc trong ```json."""
    fenced = re.sub(r"^\s*```(?:json)?|```\s*$", "", raw.strip(), flags=re.MULTILINE)
    start = fenced.find("{")
    end = fenced.rfind("}")
    if start == -1 or end <= start:
        return None
    try:
        parsed = json.loads(fenced[start : end + 1])
    except json.JSONDecodeError:
        return None
    return parsed if isinstance(parsed, dict) else None


def _build_user_prompt(topic: HealthTopic) -> str:
    return json.dumps(
        {
            "ten_chu_de": topic.name,
            "tom_tat_goc": topic.summary,
            "trieu_chung": topic.symptoms,
            "dau_hieu_can_chu_y": topic.warning_signs,
        },
        ensure_ascii=False,
        indent=2,
    )


async def generate_ai_summary(topic: HealthTopic) -> tuple[str, str] | None:
    """Sinh bản diễn giải dễ hiểu cho một chủ đề.

    Trả về ``(summary, model_name)`` khi kết quả vượt qua toàn bộ kiểm định,
    hoặc ``None`` khi cần giữ nguyên bản tóm tắt seed.
    """
    llm = get_resilient_llm(tier="small")
    model_name = getattr(llm, "model_name", None) or getattr(llm, "model", None) or type(llm).__name__

    try:
        response = await llm.ainvoke(
            [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": _build_user_prompt(topic)},
            ]
        )
    except Exception as exc:  # noqa: BLE001 - nội dung seed vẫn hiển thị được
        print(f"[HealthTopic AI] Không gọi được LLM cho '{topic.slug}': {exc}")
        return None

    raw = getattr(response, "content", None)
    if not isinstance(raw, str) or not raw.strip():
        print(f"[HealthTopic AI] Phản hồi rỗng cho '{topic.slug}'")
        return None

    payload = _extract_json_object(raw)
    if payload is None:
        print(f"[HealthTopic AI] Phản hồi cho '{topic.slug}' không phải JSON hợp lệ")
        return None

    try:
        validated = HealthSummaryOutput.model_validate(payload)
    except ValidationError as exc:
        print(f"[HealthTopic AI] Đầu ra cho '{topic.slug}' sai schema: {exc.error_count()} lỗi")
        return None

    summary = validated.summary.strip()
    violation = violated_rule(summary)
    if violation:
        print(f"[HealthTopic AI] Từ chối đầu ra cho '{topic.slug}': chứa {violation}")
        return None

    return summary, str(model_name)
