"""Kiểm định bốn khối chất lượng và xu hướng của bảng số liệu trạm điều phối.

Những chỗ sai thì báo cáo ngược hẳn về an toàn lâm sàng:

1. **Chiều của thang ESI trong ma trận.** AI đề xuất 4, điều dưỡng chốt 2 là
   điều dưỡng chốt KHẨN HƠN. Đảo dấu là biến "AI đánh giá nhẹ tay" thành "AI
   đánh giá quá tay".
2. **Giờ Việt Nam.** Mốc trong cơ sở dữ liệu là UTC naive; đọc thẳng là xếp
   một phiên lúc 3 giờ sáng Thứ Hai vào 20 giờ tối Chủ nhật.
3. **Thời gian chờ không bao giờ âm hoặc bịa ra.** Ca chưa ai nhận không được
   tính như ca nhận sau 0 phút.
4. **Truy vấn chặn theo cửa sổ không được bỏ sót ca** -- kiểm trên SQLite thật.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from datetime import datetime, timedelta

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlmodel import SQLModel
from sqlmodel.ext.asyncio.session import AsyncSession

import src.services.simple_nurse_dashboard as dashboard_module
from src.models.db_models import SimpleAgentChatSession, SimpleAgentNurseReview, User
from src.services.db import POSTGRES_ONLY_TABLES
from src.services.simple_nurse_dashboard import (
    CLAIM_BIN_MINUTES,
    MIN_CASES_FOR_SUMMARY,
    WAIT_CRITICAL_MINUTES,
    WAIT_WARNING_MINUTES,
    aggregate_dashboard,
    aggregate_history_panels,
    build_nurse_dashboard,
    history_row_of,
    load_history_rows,
)

# Thứ Hai 14/09/2026, 12:00 UTC = 19:00 giờ Việt Nam cùng ngày.
NOW = datetime(2026, 9, 14, 12, 0, 0)
NURSE_ID = "nurse-1"


def _chat(
    session_id: str,
    *,
    esi: list[int] | None = None,
    completed_at: datetime | None = None,
    minutes_ago: int = 120,
    status: str = "COMPLETED",
    final_action: str = "RETURN_MATCH",
    flagged_at: datetime | None = None,
) -> SimpleAgentChatSession:
    if status == "COMPLETED" and completed_at is None:
        completed_at = NOW - timedelta(minutes=minutes_ago)
    started = (completed_at or flagged_at or NOW) - timedelta(minutes=10)
    return SimpleAgentChatSession(
        session_id=session_id,
        patient_id="patient-1",
        status=status,
        initial_message="Đau ngực",
        matched_esi_levels=esi or [],
        final_action=final_action if status == "COMPLETED" else None,
        started_at=started,
        completed_at=completed_at if status == "COMPLETED" else None,
        attention_required=flagged_at is not None,
        attention_raised_at=flagged_at,
    )


def _review(session_id: str, **fields: object) -> SimpleAgentNurseReview:
    review = SimpleAgentNurseReview(session_id=session_id)
    for key, value in fields.items():
        setattr(review, key, value)
    return review


def _decided(
    session_id: str,
    *,
    esi: list[int],
    final_esi: int | None,
    decided_at: datetime = NOW,
    completed_at: datetime | None = None,
    decision: str = "ADJUST_ESI",
):
    chat = _chat(session_id, esi=esi, completed_at=completed_at or decided_at - timedelta(minutes=20))
    review = _review(
        session_id,
        review_status="HANDED_OFF",
        decision_type=decision,
        final_esi=final_esi,
        decided_at=decided_at,
        handed_off_at=decided_at,
        claimed_at=decided_at - timedelta(minutes=5),
        assigned_nurse_id=NURSE_ID,
    )
    return chat, review


def _panels(pairs, window_days: int = 14):
    return aggregate_history_panels([history_row_of(chat, review) for chat, review in pairs], NOW, window_days)


def _cell(matrix, row_key: str, final_esi: int) -> int:
    row = next(row for row in matrix.rows if row.key == row_key)
    return next(cell.count for cell in row.counts if cell.final_esi == final_esi)


# ---------------------------------------------------------------------------
# Ma trận mức AI đề xuất × mức điều dưỡng chốt
# ---------------------------------------------------------------------------


def test_ma_tran_chot_so_nho_hon_la_khan_hon_va_nam_ben_trai_duong_cheo() -> None:
    """AI đề xuất 4, điều dưỡng chốt 2: ô (hàng 4, cột 2) và là KHẨN HƠN."""
    matrix = _panels([_decided("a", esi=[4], final_esi=2)]).decision_matrix

    assert _cell(matrix, "4", 2) == 1
    assert matrix.more_urgent == 1
    assert matrix.less_urgent == 0
    assert matrix.kept == 0


def test_ma_tran_chot_so_lon_hon_la_it_khan_hon() -> None:
    matrix = _panels([_decided("a", esi=[2], final_esi=4)]).decision_matrix

    assert _cell(matrix, "2", 4) == 1
    assert matrix.less_urgent == 1
    assert matrix.more_urgent == 0


def test_duong_cheo_la_giu_nguyen_va_muc_ai_la_muc_khan_nhat_cua_atom() -> None:
    """Mức AI đề xuất là min(matched_esi_levels), như hàng đợi."""
    matrix = _panels([_decided("a", esi=[3, 2], final_esi=2, decision="CONFIRM_ESI")]).decision_matrix

    assert _cell(matrix, "2", 2) == 1
    assert matrix.kept == 1


def test_ca_khong_co_muc_ai_vao_dung_hang_rieng() -> None:
    insufficient_chat, insufficient_review = _decided("thieu", esi=[], final_esi=3)
    insufficient_chat.final_action = "RETURN_INCOMPLETE"
    flagged_at = NOW - timedelta(minutes=50)
    still_screening = (
        _chat("dang-khai", status="ACTIVE", flagged_at=flagged_at),
        _review("dang-khai", review_status="HANDED_OFF", final_esi=1, decided_at=NOW - timedelta(minutes=30)),
    )
    matrix = _panels([(insufficient_chat, insufficient_review), still_screening]).decision_matrix

    assert _cell(matrix, "INSUFFICIENT", 3) == 1
    assert _cell(matrix, "IN_PROGRESS", 1) == 1
    assert matrix.without_proposal == 2
    assert matrix.kept == matrix.more_urgent == matrix.less_urgent == 0


def test_ma_tran_luon_du_bay_hang_nam_cot_va_tong_khop_khoi_doi_chieu() -> None:
    """Hai khối đếm cùng một tập ca: lệch nhau một ca là mất lòng tin vào cả hai."""
    old = NOW - timedelta(days=20)
    pairs = [
        _decided("giu", esi=[3], final_esi=3, decision="CONFIRM_ESI"),
        _decided("khan-hon", esi=[4], final_esi=2),
        _decided("it-khan", esi=[2], final_esi=4),
        _decided("khong-muc", esi=[], final_esi=2),
        _decided("ngoai-cua-so", esi=[3], final_esi=1, decided_at=old),
        (_chat("chua-chot", esi=[2]), None),
    ]
    result = aggregate_dashboard(pairs, NURSE_ID, NOW)
    matrix = result.decision_matrix

    assert [row.key for row in matrix.rows] == ["1", "2", "3", "4", "5", "INSUFFICIENT", "IN_PROGRESS"]
    assert all([cell.final_esi for cell in row.counts] == [1, 2, 3, 4, 5] for row in matrix.rows)
    assert matrix.decided_total == result.agreement.decided_total == 4
    assert matrix.kept == result.agreement.confirmed
    assert matrix.more_urgent == result.agreement.escalated
    assert matrix.less_urgent == result.agreement.de_escalated
    assert matrix.without_proposal == result.agreement.adjusted_without_proposal
    assert sum(cell.count for row in matrix.rows for cell in row.counts) == matrix.decided_total


def test_ca_chot_khong_ghi_muc_khong_nam_o_nao_nhung_van_trong_tong() -> None:
    matrix = _panels([_decided("cu", esi=[3], final_esi=None)]).decision_matrix

    assert matrix.without_final_esi == 1
    assert matrix.decided_total == 1
    assert sum(cell.count for row in matrix.rows for cell in row.counts) == 0


# ---------------------------------------------------------------------------
# Từ lúc gắn cờ tới khi có người nhận
# ---------------------------------------------------------------------------


def _flagged(session_id: str, *, flagged_minutes_ago: int, claimed_after: int | None = None, **review: object):
    flagged_at = NOW - timedelta(minutes=flagged_minutes_ago)
    fields = dict(review)
    if claimed_after is not None:
        fields.setdefault("claimed_at", flagged_at + timedelta(minutes=claimed_after))
        fields.setdefault("assigned_nurse_id", NURSE_ID)
        fields.setdefault("review_status", "ASSIGNED")
    return (
        _chat(session_id, completed_at=flagged_at + timedelta(seconds=30), flagged_at=flagged_at),
        _review(session_id, **fields) if fields else None,
    )


def test_cot_nam_phut_cat_dung_hai_moc_cua_bang_ca() -> None:
    """29 phút là trước mốc cảnh báo; đúng 30 phút thì không còn 'trước mốc'."""
    claim = _panels(
        [
            _flagged("ngay", flagged_minutes_ago=300, claimed_after=0),
            _flagged("bon", flagged_minutes_ago=300, claimed_after=4),
            _flagged("nam", flagged_minutes_ago=300, claimed_after=5),
            _flagged("hai-chin", flagged_minutes_ago=300, claimed_after=29),
            _flagged("ba-muoi", flagged_minutes_ago=300, claimed_after=30),
            _flagged("sau-muoi", flagged_minutes_ago=300, claimed_after=60),
            _flagged("hai-gio", flagged_minutes_ago=300, claimed_after=120),
        ]
    ).flagged_claim

    counts = {(item.min_minutes, item.max_minutes): item.count for item in claim.bins}
    assert counts[(0, 5)] == 2
    assert counts[(5, 10)] == 1
    assert counts[(25, 30)] == 1
    assert counts[(30, 35)] == 1
    assert counts[(60, None)] == 2
    assert claim.claimed == 7
    assert claim.claimed_under_warning == 4


def test_ranh_gioi_cot_trung_hai_moc_va_cot_cuoi_khong_co_can_tren() -> None:
    bins = _panels([]).flagged_claim.bins

    edges = [item.min_minutes for item in bins]
    assert WAIT_WARNING_MINUTES in edges
    assert edges[-1] == WAIT_CRITICAL_MINUTES
    assert bins[-1].max_minutes is None
    assert all(item.max_minutes - item.min_minutes == CLAIM_BIN_MINUTES for item in bins[:-1])


def test_ca_chot_thang_khong_ai_nhan_truoc_thi_tinh_toi_luc_chot() -> None:
    flagged_at = NOW - timedelta(minutes=90)
    pair = (
        _chat("chot-thang", completed_at=flagged_at, flagged_at=flagged_at),
        _review("chot-thang", review_status="HANDED_OFF", final_esi=2, decided_at=flagged_at + timedelta(minutes=12)),
    )
    claim = _panels([pair]).flagged_claim

    assert claim.claimed == 1
    assert next(item.count for item in claim.bins if item.min_minutes == 10) == 1


def test_ca_chua_ai_nhan_khong_bi_tinh_nhu_nhan_sau_khong_phut() -> None:
    claim = _panels(
        [
            _flagged("chua-dong-toi", flagged_minutes_ago=40),
            _flagged("tra-lai", flagged_minutes_ago=40, review_status="WAITING_REVIEW"),
            _flagged("giu-khong-ghi-gio", flagged_minutes_ago=40, assigned_nurse_id=NURSE_ID, review_status="ASSIGNED"),
            _flagged("da-nhan", flagged_minutes_ago=40, claimed_after=3),
        ]
    ).flagged_claim

    assert claim.flagged_total == 4
    assert claim.unclaimed == 2
    assert claim.untimed == 1
    assert claim.claimed == 1
    assert sum(item.count for item in claim.bins) == claim.claimed
    assert claim.flagged_total == claim.claimed + claim.unclaimed + claim.untimed


def test_chi_dem_ca_co_co_gan_trong_cua_so() -> None:
    claim = _panels(
        [
            _flagged("cu", flagged_minutes_ago=20 * 24 * 60, claimed_after=5),
            _flagged("moi", flagged_minutes_ago=60, claimed_after=5),
            (_chat("khong-co", esi=[3]), _review("khong-co", claimed_at=NOW, assigned_nurse_id=NURSE_ID)),
        ]
    ).flagged_claim

    assert claim.flagged_total == 1
    assert _panels([_flagged("cu", flagged_minutes_ago=20 * 24 * 60, claimed_after=5)], window_days=30).flagged_claim.claimed == 1


def test_nhan_truoc_luc_gan_co_thi_khong_ra_so_phut_am() -> None:
    claim = _panels([_flagged("lech-gio", flagged_minutes_ago=60, claimed_after=-3)]).flagged_claim

    assert claim.bins[0].count == 1
    assert claim.min_cases == MIN_CASES_FOR_SUMMARY


# ---------------------------------------------------------------------------
# Thời gian chờ tới khi được chốt
# ---------------------------------------------------------------------------


def test_trung_vi_cho_theo_muc_va_chi_neu_khi_du_ca() -> None:
    waits = [5, 12, 40, 41, 90]
    pairs = [
        _decided(f"esi2-{index}", esi=[2], final_esi=2, completed_at=NOW - timedelta(minutes=wait))
        for index, wait in enumerate(waits)
    ]
    pairs += [_decided(f"esi3-{index}", esi=[3], final_esi=3, completed_at=NOW - timedelta(minutes=8)) for index in range(2)]
    wait = _panels(pairs).decision_wait
    by_key = {row.key: row for row in wait.rows}

    assert [row.key for row in wait.rows] == ["1", "2", "3", "4", "5", "INSUFFICIENT", "IN_PROGRESS"]
    assert by_key["2"].count == 5
    assert by_key["2"].median_minutes == 40
    # Hai ca: nêu số ca, không nêu trung vị.
    assert by_key["3"].count == 2
    assert by_key["3"].median_minutes is None
    assert by_key["1"].count == 0
    assert wait.decided_total == 7


def test_trung_vi_so_ca_chan_lay_trung_binh_hai_ca_giua_roi_lam_tron_xuong() -> None:
    waits = [10, 20, 31, 40, 50, 60]
    pairs = [
        _decided(f"a{index}", esi=[2], final_esi=2, completed_at=NOW - timedelta(minutes=wait))
        for index, wait in enumerate(waits)
    ]
    by_key = {row.key: row for row in _panels(pairs).decision_wait.rows}

    # (31 + 40) / 2 = 35,5 phút -> 35 phút.
    assert by_key["2"].median_minutes == 35


def test_ca_co_co_chot_khi_con_dang_khai_tinh_cho_tu_luc_gan_co() -> None:
    """Phiên kết thúc SAU lúc chốt: đọc thẳng công thức của bảng ca sẽ ra chờ âm."""
    flagged_at = NOW - timedelta(minutes=60)
    decided_at = NOW - timedelta(minutes=20)
    pairs = []
    for index in range(MIN_CASES_FOR_SUMMARY):
        chat = _chat(f"co-{index}", completed_at=NOW - timedelta(minutes=5), flagged_at=flagged_at)
        pairs.append((chat, _review(chat.session_id, review_status="HANDED_OFF", final_esi=1, decided_at=decided_at)))
    by_key = {row.key: row for row in _panels(pairs).decision_wait.rows}

    assert by_key["INSUFFICIENT"].median_minutes == 40


# ---------------------------------------------------------------------------
# Thứ × giờ theo giờ Việt Nam
# ---------------------------------------------------------------------------


def _weekday_cell(panel, weekday: int, hour: int) -> int:
    return next(row for row in panel.rows if row.weekday == weekday).hours[hour]


def test_gio_utc_doi_sang_gio_viet_nam_ke_ca_khi_qua_ngay() -> None:
    """20:30 UTC Chủ nhật là 03:30 sáng Thứ Hai ở Việt Nam."""
    panel = _panels(
        [
            (_chat("dem", completed_at=datetime(2026, 9, 13, 20, 30)), None),
            (_chat("sang", completed_at=datetime(2026, 9, 14, 1, 15)), None),
        ]
    ).weekday_hour

    assert panel.utc_offset_hours == 7
    assert _weekday_cell(panel, 1, 3) == 1
    assert _weekday_cell(panel, 7, 20) == 0
    assert _weekday_cell(panel, 1, 8) == 1
    assert panel.total == 2


def test_cua_so_theo_lich_viet_nam_khong_theo_ngay_utc() -> None:
    """Cửa sổ 7 ngày theo lịch Việt Nam bắt đầu 0:00 Thứ Ba 08/09 giờ Việt Nam."""
    pairs = [
        # 18:00 UTC 07/09 = 01:00 ngày 08/09 giờ Việt Nam: thuộc cửa sổ dù ngày UTC thì không.
        (_chat("vao", completed_at=datetime(2026, 9, 7, 18, 0)), None),
        # 16:00 UTC 07/09 = 23:00 ngày 07/09 giờ Việt Nam: ngoài cửa sổ.
        (_chat("ra", completed_at=datetime(2026, 9, 7, 16, 0)), None),
    ]
    result = aggregate_dashboard(pairs, NURSE_ID, NOW, window_days=7)
    panel = result.weekday_hour

    assert panel.first_day == "2026-09-08"
    assert panel.last_day == "2026-09-14"
    assert panel.total == 1
    assert _weekday_cell(panel, 2, 1) == 1
    # Các biểu đồ theo ngày UTC không tính phiên nào trong hai phiên này.
    assert result.completed_in_window == 0


def test_so_ngay_cua_moi_thu_trong_cua_so() -> None:
    by_window = {days: _panels([], window_days=days).weekday_hour for days in (7, 14, 30, 90)}

    assert {row.days for row in by_window[7].rows} == {1}
    assert {row.days for row in by_window[14].rows} == {2}
    # 30 ngày từ Chủ nhật 16/08 tới Thứ Hai 14/09: Chủ nhật và Thứ Hai có 5 ngày.
    thirty = {row.weekday: row.days for row in by_window[30].rows}
    assert thirty == {1: 5, 2: 4, 3: 4, 4: 4, 5: 4, 6: 4, 7: 5}
    assert sum(row.days for row in by_window[90].rows) == 90


def test_tong_cac_o_bang_tong_va_luon_du_bay_hang_hai_tu_gio() -> None:
    pairs = [(_chat(f"p{index}", minutes_ago=index * 97), None) for index in range(12)]
    panel = _panels(pairs).weekday_hour

    assert [row.weekday for row in panel.rows] == [1, 2, 3, 4, 5, 6, 7]
    assert all(len(row.hours) == 24 for row in panel.rows)
    assert sum(sum(row.hours) for row in panel.rows) == panel.total == 12


# ---------------------------------------------------------------------------
# Cửa sổ rỗng
# ---------------------------------------------------------------------------


def test_cua_so_rong_tra_khung_day_du_toan_so_khong() -> None:
    result = aggregate_dashboard([], NURSE_ID, NOW)

    assert result.decision_matrix.decided_total == 0
    assert len(result.decision_matrix.rows) == 7
    assert all(cell.count == 0 for row in result.decision_matrix.rows for cell in row.counts)
    assert result.flagged_claim.flagged_total == 0
    assert len(result.flagged_claim.bins) == WAIT_CRITICAL_MINUTES // CLAIM_BIN_MINUTES + 1
    assert all(row.count == 0 and row.median_minutes is None for row in result.decision_wait.rows)
    assert result.weekday_hour.total == 0
    assert all(sum(row.hours) == 0 for row in result.weekday_hour.rows)


# ---------------------------------------------------------------------------
# Truy vấn chặn theo cửa sổ, chạy thật trên SQLite
# ---------------------------------------------------------------------------


@pytest_asyncio.fixture
async def db_session(tmp_path) -> AsyncIterator[AsyncSession]:
    engine = create_async_engine(f"sqlite+aiosqlite:///{tmp_path / 'dashboard_quality.db'}")
    tables = [table for table in SQLModel.metadata.sorted_tables if table.name not in POSTGRES_ONLY_TABLES]
    async with engine.begin() as conn:
        await conn.run_sync(lambda sync_conn: SQLModel.metadata.create_all(sync_conn, tables=tables))
    maker = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with maker() as session:
        session.add(User(id="patient-1", email="patient@test.local", full_name="Người bệnh", role="PATIENT"))
        await session.commit()
        yield session
    await engine.dispose()


def _seed_pairs():
    long_ago = NOW - timedelta(days=40)
    return [
        _decided("moi", esi=[3], final_esi=2),
        # Phiên kết thúc từ lâu nhưng được chốt trong cửa sổ: phải được đọc lên.
        _decided("chot-muon", esi=[4], final_esi=4, completed_at=long_ago, decided_at=NOW - timedelta(hours=3)),
        _decided("chot-cu", esi=[2], final_esi=1, completed_at=long_ago, decided_at=long_ago + timedelta(hours=1)),
        (_chat("cu-chua-chot", completed_at=long_ago), None),
        # 18:00 UTC 31/08 = 01:00 ngày 01/09 giờ Việt Nam: chỉ thuộc cửa sổ theo lịch Việt Nam.
        (_chat("bien-viet-nam", completed_at=datetime(2026, 8, 31, 18, 0)), None),
        (_chat("truoc-bien", completed_at=datetime(2026, 8, 31, 16, 0)), None),
        _flagged("co", flagged_minutes_ago=45, claimed_after=7),
        (_chat("dang-khai-khong-co", status="ACTIVE"), None),
        (_chat("dang-khai-co", status="ACTIVE", flagged_at=NOW - timedelta(minutes=15)), None),
    ]


async def _seed(session: AsyncSession) -> None:
    for chat, review in _seed_pairs():
        session.add(chat)
        if review is not None:
            session.add(review)
    await session.commit()


@pytest.mark.asyncio
async def test_truy_van_chan_cua_so_khong_bo_sot_ca_nao_can_dem(db_session: AsyncSession) -> None:
    await _seed(db_session)

    loaded = await load_history_rows(db_session, NOW, 14)
    loaded_at = {(row.completed_at, row.decided_at, row.attention_raised_at) for row in loaded}

    # Chặn trong SQL: ca cũ không còn mốc nào trong cửa sổ không được đọc lên.
    assert len(loaded) == 5
    assert (datetime(2026, 8, 31, 16, 0), None, None) not in loaded_at
    # Kết quả trùng khớp với việc đếm trên toàn bộ ca xem xét được.
    every_reviewable = [
        history_row_of(chat, review)
        for chat, review in _seed_pairs()
        if chat.status == "COMPLETED" or chat.attention_required
    ]
    for window_days in (7, 14, 30, 90):
        rows = await load_history_rows(db_session, NOW, window_days)
        assert aggregate_history_panels(rows, NOW, window_days) == aggregate_history_panels(
            every_reviewable, NOW, window_days
        )


@pytest.mark.asyncio
async def test_bang_so_lieu_day_du_doc_tu_co_so_du_lieu(db_session: AsyncSession, monkeypatch) -> None:
    await _seed(db_session)
    monkeypatch.setattr(dashboard_module, "get_utc_now", lambda: NOW)

    result = await build_nurse_dashboard(db_session, NURSE_ID, window_days=14)

    assert result.decision_matrix.decided_total == result.agreement.decided_total == 2
    assert result.decision_matrix.more_urgent == 1
    assert result.decision_matrix.kept == 1
    assert result.flagged_claim.flagged_total == 2
    assert result.flagged_claim.claimed == 1
    assert result.flagged_claim.unclaimed == 1
    assert result.weekday_hour.total == 3
    # Khối JSON trả cho giao diện có đủ bốn khối mới.
    payload = result.model_dump(mode="json")
    assert {"decision_matrix", "flagged_claim", "decision_wait", "weekday_hour"} <= payload.keys()
