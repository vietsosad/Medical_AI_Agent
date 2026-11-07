"""Mô hình kịch bản (spec) cho bộ ca tổng hợp generated_mock_v2.

Mỗi ``Spec`` là một tình huống người bệnh do người viết soạn tay: hồ sơ giả lập,
lời kể mở đầu, dữ kiện người bệnh khai được (theo đúng ``fact_target`` của
corpus PostgreSQL), câu trả lời tự nhiên cho từng câu hỏi, những điều người
bệnh không biết, và cách người bệnh làm rõ khi được hỏi lại.

Spec KHÔNG mang nhãn phân luồng. ``intended`` chỉ là dự định của người viết;
nhãn thật được ``build_dataset.py`` tính bằng bộ đánh giá độc lập của dự án
(``eval.simple_runtime.golden_validator.satisfied_esi``) trên toàn bộ tiêu chí
``CLINICAL_AUTHORITY`` của corpus. Lệch giữa dự định và nhãn tính được là lỗi
dựng bộ ca, không được tự sửa nhãn cho khớp.

Mọi nhân vật đều là giả lập: không tên, không số điện thoại, không địa chỉ.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

# Nhóm tình huống (Phase 2 của yêu cầu).
COMMON = "COMMON"
MULTI = "MULTI_SYMPTOM"
RED = "RED_FLAG"
MISSING = "MISSING_INFO"
CONFLICT = "CONFLICTING"
COMPLEX = "COMPLEX_DIALOGUE"
GROUPS = (COMMON, MULTI, RED, MISSING, CONFLICT, COMPLEX)

#: Kết cục "agent không đủ căn cứ, chuyển nhân viên y tế" (RETURN_INCOMPLETE).
INCOMPLETE = "INCOMPLETE"

#: Người kể chuyện: chính người bệnh hay người khác kể hộ.
SELF = "SELF"
CAREGIVER = "CAREGIVER"

#: Hành vi mong đợi của bộ lọc khẩn cấp trước LLM trên câu mở đầu.
SCREEN_HIT = "HIT"
SCREEN_QUIET = "QUIET"


def P(
    age: int,
    sex: str,
    rel: str = "SELF",
    *,
    months: int | None = None,
    chronic: tuple[str, ...] | list[str] = (),
    allergies: tuple[str, ...] | list[str] = (),
    meds: tuple[str, ...] | list[str] = (),
) -> dict[str, Any]:
    """Hồ sơ giả lập. ``months`` = tuổi tính bằng tháng cho trẻ dưới 3 tuổi."""
    return {
        "age_years": age,
        "sex": sex,
        "relationship_type": rel,
        "age_months": months,
        "chronic_conditions": list(chronic),
        "allergies": list(allergies),
        "daily_medications": list(meds),
    }


@dataclass(frozen=True)
class Spec:
    case_id: str
    family: str
    group: str
    title: str
    profile: dict[str, Any]
    opening: str
    facts: dict[str, Any]
    intended: int | str
    answers: dict[str, str] = field(default_factory=dict)
    unknown: dict[str, str] = field(default_factory=dict)
    concepts: tuple[str, ...] = ()
    negated: tuple[str, ...] = ()
    clarification: str = ""
    confirmation: str = ""
    resources: int | None = None
    resource_basis: str = ""
    narrator: str = SELF
    style: tuple[str, ...] = ()
    tags: tuple[str, ...] = ()
    test: str = ""
    review_concern: str = ""
    screen: str = ""
    variants: dict[str, tuple[str, ...]] = field(default_factory=dict)
    forbidden_atoms: tuple[str, ...] = ()
    primary_atom: str = ""
    conflict: tuple[str, ...] = ()


#: Câu xác nhận thay phiên, để 200 ca không cùng một câu. Không câu nào có đại
#: từ ngôi thứ nhất: người kể xưng "em" hay "tôi" tuỳ ca, câu xác nhận dùng
#: chung không được đổi cách xưng hô giữa chừng.
CONFIRMATIONS = (
    "Đúng rồi, thông tin như vậy.",
    "Vâng, đúng như thế ạ.",
    "Đúng, bạn tổng hợp chuẩn rồi.",
    "Chuẩn rồi, bạn cứ hoàn tất giúp nhé.",
    "Đúng hết, không còn gì khác.",
    "Vâng ạ, như vậy là đủ.",
)
