"""Ràng buộc hình dạng và chất lượng của bộ ca vàng mở rộng (300 ca).

Tách hẳn khỏi ``test_dataset_shape.py``: file đó khoá bộ 30 ca đã công bố và
không được đụng tới. File này khoá bộ mở rộng, với một ràng buộc mà bộ 30 ca
không cần — **lời kể của người bệnh phải là tiếng Việt hoàn toàn**.

Lý do ràng buộc đó tồn tại: ở bộ 30 ca, phần lớn lời kể được biên tập tay nên
lỗi không lộ ra. Ở quy mô 300 ca, lời kể được sinh tự động từ giá trị enum của
kho dữ liệu, và mọi giá trị thiếu bản dịch sẽ rơi vào nhánh dự phòng
``value.replace("_", " ").lower()`` — tức tiếng Anh lọt thẳng vào câu nói của
một người bệnh Việt Nam. Lần dựng đầu tiên dính lỗi này ở 97/300 ca. Test dưới
đây làm cho lỗi đó không thể quay lại mà không ai biết.
"""

from collections import Counter
from pathlib import Path

import pytest

from eval.simple_runtime.golden_builder import _VALUE_TEXT
from eval.simple_runtime.schemas import GoldenCase

DATASET = Path("eval/cases/simple_agent_golden_300.jsonl")
CANONICAL = Path("eval/cases/simple_agent_golden_30.jsonl")

pytestmark = pytest.mark.skipif(
    not DATASET.exists(),
    reason="Chưa dựng bộ mở rộng; chạy python -m eval.build_golden_expanded.",
)


def _cases() -> list[GoldenCase]:
    return [
        GoldenCase.model_validate_json(line)
        for line in DATASET.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def test_expanded_dataset_has_its_intended_distribution() -> None:
    cases = _cases()
    assert len(cases) == 300
    assert Counter(case.category for case in cases) == {
        "esi_1": 20,
        "esi_2": 150,
        "esi_3": 50,
        "esi_4": 35,
        "esi_5": 35,
        "guardrail": 10,
    }
    # Cổng khói phải tồn tại: nó là thứ chặn một backend hỏng đốt cả lượt chạy.
    assert sum(case.smoke for case in cases) >= 1


def test_every_triage_case_carries_postgres_authority_provenance() -> None:
    for case in _cases():
        if case.expected_esi is None:
            continue
        assert case.postgres_provenance["generated_from_postgres"] is True
        assert case.postgres_provenance["authority_scope"] == "CLINICAL_AUTHORITY"
        assert case.expected_retrieval["primary_atom_id"]


def test_patient_utterances_contain_no_untranslated_enum_values() -> None:
    """Không một giá trị enum nào được rơi vào nhánh dự phòng tiếng Anh."""
    untranslated: set[str] = set()
    for case in _cases():
        for value in (case.expected_state.get("facts") or {}).values():
            if isinstance(value, str) and value not in _VALUE_TEXT:
                untranslated.add(value)
    assert not untranslated, (
        "Các giá trị sau chưa có bản dịch tiếng Việt và sẽ lọt vào lời kể của "
        f"người bệnh dưới dạng tiếng Anh: {sorted(untranslated)}. "
        "Bổ sung vào _VALUE_TEXT_VI_EXTRA trong eval/simple_runtime/golden_builder.py."
    )


def test_opening_messages_are_never_bare_fragments() -> None:
    """Câu mở đầu phải bắt đầu bằng một câu hoàn chỉnh, không phải mảnh cụt."""
    for case in _cases():
        message = case.presentation["initial_message"].strip()
        assert message
        assert message[0].isupper() or message[0].isdigit(), case.case_id


def test_expanded_dataset_covers_a_wide_slice_of_the_corpus() -> None:
    """Bộ ca phải phủ rộng, nếu không thì mở rộng chỉ là nhân bản một vùng hẹp."""
    cases = _cases()
    atom_ids = {
        case.postgres_provenance.get("protocol_atom_id")
        for case in cases
    } - {None}
    fact_ids = {
        fact_id
        for case in cases
        for fact_id in (case.expected_state.get("facts") or {})
    }
    # 300 ca dựng trên ít nhất 280 tiêu chí phác đồ khác nhau: gần như mỗi ca
    # một tiêu chí, chỉ vài ca guardrail dùng lại tiêu chí của ca lâm sàng.
    assert len(atom_ids) >= 280
    assert len(fact_ids) >= 100


def test_canonical_thirty_case_dataset_is_left_alone() -> None:
    """Bộ 30 ca đã công bố không được thay đổi bởi việc dựng bộ mở rộng."""
    canonical = [line for line in CANONICAL.read_text(encoding="utf-8").splitlines() if line.strip()]
    assert len(canonical) == 30
