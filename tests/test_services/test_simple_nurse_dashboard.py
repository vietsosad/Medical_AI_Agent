"""Kiểm định phép đếm của bảng số liệu tổng quan trạm điều phối.

Hai chỗ dễ sai nhất và cũng nguy hiểm nhất nếu sai:

1. **Chiều của thang ESI.** Thang chạy ngược -- ESI 1 khẩn hơn ESI 5. Đảo
   nhầm dấu so sánh sẽ biến "điều dưỡng phải nâng mức vì AI đánh giá nhẹ tay"
   thành "điều dưỡng hạ mức", tức là báo cáo ngược hẳn về an toàn lâm sàng.
2. **Ranh giới mốc thời gian chờ.** Đúng 30 và đúng 60 phút phải rơi vào nhóm
   nặng hơn, giống hệt cách bảng ca tô màu.
"""

from __future__ import annotations

from datetime import datetime, timedelta

from src.models.db_models import SimpleAgentChatSession, SimpleAgentNurseReview
from src.services.simple_nurse_dashboard import aggregate_dashboard

NOW = datetime(2026, 9, 14, 12, 0, 0)
NURSE_ID = "nurse-1"


def _chat(
    session_id: str,
    *,
    esi: list[int] | None = None,
    minutes_ago: int = 5,
    final_action: str = "RETURN_MATCH",
) -> SimpleAgentChatSession:
    completed = NOW - timedelta(minutes=minutes_ago)
    return SimpleAgentChatSession(
        session_id=session_id,
        patient_id="patient-1",
        status="COMPLETED",
        initial_message="Đau ngực",
        matched_esi_levels=esi or [],
        final_action=final_action,
        started_at=completed,
        completed_at=completed,
    )


def _review(session_id: str, **fields: object) -> SimpleAgentNurseReview:
    review = SimpleAgentNurseReview(session_id=session_id)
    for key, value in fields.items():
        setattr(review, key, value)
    return review


def _decided(session_id: str, *, esi: list[int], decision: str, final_esi: int | None):
    """Một ca đã đóng, kèm quyết định của điều dưỡng."""
    return (
        _chat(session_id, esi=esi),
        _review(
            session_id,
            review_status="HANDED_OFF",
            decision_type=decision,
            final_esi=final_esi,
            decided_at=NOW,
            decision_reason_code="ADDITIONAL_CLINICAL_JUDGMENT",
        ),
    )


# ---------------------------------------------------------------------------
# Ảnh chụp hàng đợi
# ---------------------------------------------------------------------------


def test_ca_chua_co_dong_review_duoc_tinh_la_dang_cho() -> None:
    """Hàng đợi tạo lười dòng review; bảng số liệu chỉ đọc nên phải tự hiểu."""
    result = aggregate_dashboard([(_chat("a", esi=[3]), None)], NURSE_ID, NOW)

    assert result.waiting == 1
    assert result.assigned_total == 0
    assert result.decided == 0


def test_tach_ca_cua_toi_khoi_ca_cua_ca_kip() -> None:
    rows = [
        (_chat("a", esi=[2]), _review("a", review_status="ASSIGNED", assigned_nurse_id=NURSE_ID)),
        (_chat("b", esi=[2]), _review("b", review_status="ASSIGNED", assigned_nurse_id="nurse-2")),
    ]
    result = aggregate_dashboard(rows, NURSE_ID, NOW)

    assert result.assigned_total == 2
    assert result.assigned_to_me == 1
    assert result.waiting == 0


def test_ca_tam_gac_va_ca_da_dong_khong_nam_trong_phan_bo_dang_mo() -> None:
    """Phân bố mức độ chỉ nói về phần việc còn trên bàn của kíp trực."""
    rows = [
        (_chat("live", esi=[2]), None),
        (_chat("parked", esi=[1]), _review("parked", review_status="PARKED")),
        (_chat("closed", esi=[1]), _review("closed", review_status="HANDED_OFF")),
    ]
    result = aggregate_dashboard(rows, NURSE_ID, NOW)

    assert result.parked == 1
    assert result.decided == 1
    by_level = {bucket.level: bucket.count for bucket in result.esi_distribution}
    assert by_level[2] == 1
    # Ca ESI 1 đang tạm gác và ca ESI 1 đã đóng đều không được đếm vào đây.
    assert by_level[1] == 0


def test_luon_phat_du_sau_vach_esi_ke_ca_khi_bang_khong() -> None:
    """Một mức vắng mặt là thông tin; biểu đồ đổi số vạch thì không so sánh được."""
    result = aggregate_dashboard([(_chat("a", esi=[3]), None)], NURSE_ID, NOW)

    assert [bucket.level for bucket in result.esi_distribution] == [1, 2, 3, 4, 5, None]


def test_ca_agent_khong_ket_luan_duoc_vao_vach_chua_co_va_dem_rieng() -> None:
    rows = [(_chat("a", esi=[], final_action="RETURN_INCOMPLETE"), None)]
    result = aggregate_dashboard(rows, NURSE_ID, NOW)

    assert result.insufficient_live == 1
    by_level = {bucket.level: bucket.count for bucket in result.esi_distribution}
    assert by_level[None] == 1


# ---------------------------------------------------------------------------
# Thời gian chờ
# ---------------------------------------------------------------------------


def test_moc_thoi_gian_cho_cat_dung_o_30_va_60_phut() -> None:
    """Đúng mốc thì rơi vào nhóm nặng hơn, giống hệt cách bảng ca tô màu."""
    rows = [
        (_chat("duoi", esi=[3], minutes_ago=29), None),
        (_chat("dung-30", esi=[3], minutes_ago=30), None),
        (_chat("giua", esi=[3], minutes_ago=59), None),
        (_chat("dung-60", esi=[3], minutes_ago=60), None),
        (_chat("tren", esi=[3], minutes_ago=120), None),
    ]
    result = aggregate_dashboard(rows, NURSE_ID, NOW)

    buckets = {bucket.key: bucket.count for bucket in result.wait_buckets}
    assert buckets["UNDER_WARNING"] == 1
    assert buckets["WARNING"] == 2
    assert buckets["CRITICAL"] == 2
    assert result.longest_wait_minutes == 120


def test_khong_con_ca_nao_dang_mo_thi_khong_bia_ra_thoi_gian_cho() -> None:
    rows = [(_chat("closed", esi=[2]), _review("closed", review_status="HANDED_OFF"))]
    result = aggregate_dashboard(rows, NURSE_ID, NOW)

    assert result.longest_wait_minutes is None


# ---------------------------------------------------------------------------
# Quyết định của điều dưỡng so với đề xuất của AI
# ---------------------------------------------------------------------------


def test_chot_o_muc_so_nho_hon_la_khan_hon_chu_khong_phai_it_khan_hon() -> None:
    """Thang ESI chạy ngược: AI đề xuất 4, điều dưỡng chốt 2 = NÂNG mức khẩn."""
    rows = [_decided("a", esi=[4], decision="ADJUST_ESI", final_esi=2)]
    result = aggregate_dashboard(rows, NURSE_ID, NOW)

    assert result.agreement.escalated == 1
    assert result.agreement.de_escalated == 0


def test_chot_o_muc_so_lon_hon_la_it_khan_hon() -> None:
    rows = [_decided("a", esi=[2], decision="ADJUST_ESI", final_esi=4)]
    result = aggregate_dashboard(rows, NURSE_ID, NOW)

    assert result.agreement.de_escalated == 1
    assert result.agreement.escalated == 0


def test_bam_dieu_chinh_nhung_chot_lai_dung_muc_cu_van_la_giu_nguyen() -> None:
    rows = [_decided("a", esi=[3], decision="ADJUST_ESI", final_esi=3)]
    result = aggregate_dashboard(rows, NURSE_ID, NOW)

    assert result.agreement.confirmed == 1
    assert result.agreement.escalated == 0
    assert result.agreement.de_escalated == 0


def test_dieu_duong_tu_chot_khi_ai_chua_de_xuat_duoc_tach_rieng() -> None:
    """Không có mức nào để so thì không được xếp vào nâng hay hạ."""
    rows = [_decided("a", esi=[], decision="ADJUST_ESI", final_esi=2)]
    result = aggregate_dashboard(rows, NURSE_ID, NOW)

    assert result.agreement.adjusted_without_proposal == 1
    assert result.agreement.escalated == 0
    assert result.agreement.de_escalated == 0


def test_mau_so_bang_tong_so_ca_da_chot() -> None:
    """Mọi tỉ lệ trên giao diện chia cho con số này, nên nó phải khớp tuyệt đối."""
    rows = [
        _decided("a", esi=[3], decision="CONFIRM_ESI", final_esi=3),
        _decided("b", esi=[4], decision="ADJUST_ESI", final_esi=2),
        _decided("c", esi=[2], decision="ADJUST_ESI", final_esi=4),
        (_chat("d", esi=[2]), None),
    ]
    result = aggregate_dashboard(rows, NURSE_ID, NOW)

    agreement = result.agreement
    assert agreement.decided_total == 3
    assert result.decided == 3
    total = (
        agreement.confirmed
        + agreement.escalated
        + agreement.de_escalated
        + agreement.adjusted_without_proposal
    )
    assert total == agreement.decided_total


def test_ly_do_chot_ca_duoc_dem_va_xep_theo_so_luong_giam_dan() -> None:
    rows = [
        _decided("a", esi=[3], decision="ADJUST_ESI", final_esi=2),
        _decided("b", esi=[3], decision="ADJUST_ESI", final_esi=2),
        (
            _chat("c", esi=[3]),
            _review(
                "c",
                review_status="HANDED_OFF",
                decision_type="CONFIRM_ESI",
                final_esi=3,
                decided_at=NOW,
                decision_reason_code="MATCHES_PROTOCOL",
            ),
        ),
    ]
    result = aggregate_dashboard(rows, NURSE_ID, NOW)

    assert [(reason.code, reason.count) for reason in result.reason_codes] == [
        ("ADDITIONAL_CLINICAL_JUDGMENT", 2),
        ("MATCHES_PROTOCOL", 1),
    ]


# ---------------------------------------------------------------------------
# Khối lượng theo ngày
# ---------------------------------------------------------------------------


def test_khoi_luong_luon_tra_du_14_ngay_lien_tuc_ke_ca_ngay_rong() -> None:
    """Bỏ ngày rỗng đi thì trục thời gian co lại và biểu đồ nói dối về nhịp độ."""
    rows = [(_chat("a", esi=[3], minutes_ago=5), None)]
    result = aggregate_dashboard(rows, NURSE_ID, NOW)

    assert len(result.daily_volume) == 14
    assert result.daily_volume[-1].date == "2026-09-14"
    assert result.daily_volume[0].date == "2026-09-01"
    assert result.daily_volume[-1].completed == 1
    assert sum(point.completed for point in result.daily_volume) == 1
