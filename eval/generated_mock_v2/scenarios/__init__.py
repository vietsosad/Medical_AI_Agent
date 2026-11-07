"""Tập hợp mọi kịch bản viết tay của generated_mock_v2, theo đợt và theo nhóm.

Đợt 1 (200 kịch bản, đã khoá trong ``split_lock.json``) nằm ở các tệp không tiền tố.
Đợt 2 (200 kịch bản, đã khoá) nằm ở các tệp ``b2_*.py``; mỗi tệp một nhóm tình huống.
Đợt 3 (190 kịch bản) nằm ở chín tệp ``b3_*.py`` không hậu tố ``_c``/``_d``: phủ các tiêu chí
ESI 2 chưa ca nào chạm tới.

Đợt 4 đang viết dở trong các tệp ``b3_*_c.py``/``b3_*_d.py``: viết theo các lớp lỗi đã biết của
agent và bộ lọc khẩn cấp, cân lại tỉ lệ ESI 1, ESI 3 và ca chưa đủ dữ liệu. Các tệp này **chưa**
được nạp vào ``ALL_SPECS``; chỉ đăng ký khi đã đủ 210 kịch bản và khoá được thành một đợt riêng,
vì ``assign_splits`` tính lại các cụm chưa khoá mỗi lần thêm bản ghi.
"""

from __future__ import annotations

from . import (
    b2_common_a,
    b2_common_b,
    b2_complex,
    b2_conflict,
    b2_missing,
    b2_multi,
    b2_red_flag,
    b3_common_a,
    b3_common_b,
    b3_complex,
    b3_conflict,
    b3_missing,
    b3_multi_a,
    b3_multi_b,
    b3_red_flag_a,
    b3_red_flag_b,
    common,
    complex as complex_dialogue,
    conflict,
    missing,
    multi,
    red_flag,
)

BATCH_1 = [
    *common.SPECS,
    *multi.SPECS,
    *red_flag.SPECS,
    *missing.SPECS,
    *conflict.SPECS,
    *complex_dialogue.SPECS,
]
BATCH_2 = [
    *b2_common_a.SPECS,
    *b2_common_b.SPECS,
    *b2_multi.SPECS,
    *b2_red_flag.SPECS,
    *b2_missing.SPECS,
    *b2_conflict.SPECS,
    *b2_complex.SPECS,
]

BATCH_3 = [
    *b3_common_a.SPECS,
    *b3_common_b.SPECS,
    *b3_multi_a.SPECS,
    *b3_multi_b.SPECS,
    *b3_red_flag_a.SPECS,
    *b3_red_flag_b.SPECS,
    *b3_missing.SPECS,
    *b3_conflict.SPECS,
    *b3_complex.SPECS,
]

ALL_SPECS = [*BATCH_1, *BATCH_2, *BATCH_3]
BATCH_OF = (
    {spec.case_id: 1 for spec in BATCH_1}
    | {spec.case_id: 2 for spec in BATCH_2}
    | {spec.case_id: 3 for spec in BATCH_3}
)
