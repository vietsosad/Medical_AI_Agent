"""Số liệu tổng quan cho trạm điều phối Triage Agent (HITL).

QUY TẮC NỘI DUNG CỦA MODULE NÀY
-------------------------------
Mọi con số trả ra ở đây đều là phép ĐẾM trực tiếp trên hai bảng
``simple_agent_chat_sessions`` và ``simple_agent_nurse_reviews``. Không có chỉ
số nào được ước lượng, ngoại suy, quy đổi hay lấy trung bình có trọng số. Đây
là bảng điều khiển lâm sàng: một con số không chỉ thẳng ra được nguồn gốc thì
nguy hiểm hơn là không có con số nào.

Đặc biệt, khối ``AgreementDTO`` KHÔNG phải thước đo độ chính xác của AI. Hệ
thống không có nhãn chuẩn để đối chiếu, chỉ có quyết định của điều dưỡng. Tên
từng trường vì thế nói đúng điều đếm được ("điều dưỡng giữ nguyên", "điều
dưỡng chốt ở mức khẩn hơn"), và giao diện có nghĩa vụ giữ nguyên cách gọi đó.

ĐỒNG BỘ VỚI HÀNG ĐỢI
--------------------
Điều kiện lọc ca, cách suy ra mức ESI do AI đề xuất và mốc bắt đầu tính thời
gian chờ được giữ TRÙNG KHÍT với ``GET /nurse-simple/queue``
(``src/api/routes_nurse_simple.py``). Hai màn hình đếm lệch nhau một ca là mất
lòng tin vào cả hai.

Khác một điểm có chủ đích: hàng đợi tạo lười một dòng review khi đọc tới ca
chưa có (``_get_or_create_review``), còn module này KHÔNG BAO GIỜ ghi. Một
bảng số liệu chỉ được đọc; ca chưa có dòng review thì đọc theo đúng mặc định
của bảng, tức là đang chờ tiếp nhận.

Tập ca là ``REVIEWABLE_CLAUSE`` -- định nghĩa đúng một lần ở đây và hàng đợi
import về. Nó gồm cả phiên CÒN ĐANG sàng lọc mà bộ lọc khẩn cấp trước LLM đã
gắn cờ "Cần xem ngay": hàng đợi đưa chúng lên đầu, nên bảng số liệu phải đếm
chúng, không thì con số "ca đang mở" thiếu đúng những ca gấp nhất.

HAI LOẠI SỐ
-----------
- **Ảnh chụp** (``waiting``, ``esi_wait_matrix``, ``attention_live``...): trạng
  thái của hàng đợi tại đúng lúc gọi, không phụ thuộc cửa sổ thời gian.
- **Lịch sử** (``daily_volume``, ``hour_of_day``, ``agreement``,
  ``reason_codes``, ``*_in_window``): chỉ tính sự kiện rơi vào cửa sổ
  ``window_days`` ngày gần nhất (theo ngày UTC, gồm cả hôm nay). ``decided``
  vẫn là tổng mọi thời điểm, vì nó là con số của tab "Đã quyết định".

BỐN KHỐI CHẤT LƯỢNG VÀ XU HƯỚNG
-------------------------------
``decision_matrix``, ``flagged_claim``, ``decision_wait`` và ``weekday_hour``
thêm sau, chỉ cộng thêm trường (client cũ bỏ qua được). Chúng đọc một truy vấn
RIÊNG đã chặn theo cửa sổ ngay trong SQL (``load_history_rows``) và chỉ lấy các
cột cần dùng; phần đếm vẫn là hàm thuần (``aggregate_history_panels``). Không
đẩy phép nhóm xuống SQL vì hàng của ba khối đầu là mức AI đề xuất, tức
``min(matched_esi_levels)`` trên một cột JSON: viết lại trong SQL là có hai định
nghĩa cho cùng một mức, đúng điều đầu module này cấm.

- ``decision_matrix``: mức AI đề xuất × mức điều dưỡng chốt, cùng tập ca với
  ``agreement``. Vẫn là "điều dưỡng đã làm gì với đề xuất", không phải độ chính
  xác.
- ``flagged_claim``: ca bị bộ lọc khẩn cấp gắn cờ trong cửa sổ, từ
  ``attention_raised_at`` tới lúc có người nhận. Hàng đợi xóa ``claimed_at`` khi
  trả ca hay khôi phục ca tạm gác, nên đây là lần nhận ĐANG GHI trên ca (lần sau
  cùng), không phải lần đầu. Hệ thống không có chỉ tiêu thời gian nhận ca
  (``sla_target_minutes`` của hàng đợi production cố ý để trống tới khi cơ sở cấu
  hình), nên khối này chỉ đặt hai mốc tô màu sẵn có của bảng ca làm vạch tham
  chiếu, không tự đặt chỉ tiêu lâm sàng nào.
- ``decision_wait``: từ ``waiting_since`` của bảng ca tới lúc chốt, trung vị
  theo mức AI đề xuất. Dưới ``MIN_CASES_FOR_SUMMARY`` ca thì không nêu trung vị.
- ``weekday_hour``: phiên kết thúc theo thứ × giờ GIỜ VIỆT NAM. Backend ghi giờ
  UTC dạng naive (``get_utc_now()``), nên mọi mốc được cộng tường minh
  ``VIETNAM_UTC_OFFSET`` trước khi lấy thứ và giờ. Khối này dùng ``window_days``
  ngày theo LỊCH VIỆT NAM (0:00 - 24:00 giờ Việt Nam, gồm cả hôm nay): một hàng
  "Thứ Hai" phải là trọn những ngày Thứ Hai. Vì vậy tổng của nó có thể lệch vài
  phiên so với ``completed_in_window``, vốn chia ngày theo UTC.
"""

from __future__ import annotations

import statistics
from collections import Counter
from collections.abc import Sequence
from datetime import datetime, time, timedelta
from typing import Literal, NamedTuple

from pydantic import BaseModel, Field
from sqlalchemy import or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from src.models.db_models import (
    SimpleAgentChatSession,
    SimpleAgentNurseReview,
    get_utc_now,
)

#: Trạng thái review của một ca đã đóng và của một ca đang tạm gác.
TERMINAL_REVIEW_STATUS = "HANDED_OFF"
PARKED_STATUS = "PARKED"

#: Hai mốc tô cảnh báo thời gian chờ. Trùng với hằng số cùng tên ở
#: frontend/src/components/clinical/nurse-simple/wait-time.ts -- bảng số liệu
#: và bảng ca phải chia mốc giống hệt nhau.
WAIT_WARNING_MINUTES = 30
WAIT_CRITICAL_MINUTES = 60

#: Các cửa sổ lịch sử được nhận, tính bằng ngày. Danh sách ngắn và cố định:
#: giao diện vẽ đúng bấy nhiêu nút, mỗi cửa sổ là một khóa bộ nhớ đệm riêng.
WINDOW_DAYS_CHOICES: tuple[int, ...] = (7, 14, 30, 90)
DEFAULT_WINDOW_DAYS = 14

#: Số giờ tròn của dải "24 giờ qua", tính cả giờ đang chạy.
RECENT_HOURS = 24

#: Tập ca mà điều dưỡng xem xét được: phiên đã sàng lọc xong, hoặc phiên còn
#: đang chạy nhưng đã bị bộ lọc khẩn cấp gắn cờ. Hàng đợi
#: (``routes_nurse_simple``) dùng chính biểu thức này.
REVIEWABLE_CLAUSE = or_(
    SimpleAgentChatSession.status == "COMPLETED",
    (SimpleAgentChatSession.status == "ACTIVE") & (SimpleAgentChatSession.attention_required == True),  # noqa: E712
)

#: Hàng của ma trận mức khẩn × thời gian chờ. "INSUFFICIENT" = agent đã
#: kết luận chưa đủ dữ liệu; "IN_PROGRESS" = phiên đã gắn cờ nhưng chưa sàng
#: lọc xong, nên chưa có mức nào để xếp -- không được trộn vào "chưa đủ dữ liệu".
MatrixRowKey = Literal["1", "2", "3", "4", "5", "INSUFFICIENT", "IN_PROGRESS"]
MATRIX_ROW_KEYS: tuple[MatrixRowKey, ...] = ("1", "2", "3", "4", "5", "INSUFFICIENT", "IN_PROGRESS")

WaitBucketKey = Literal["UNDER_WARNING", "WARNING", "CRITICAL"]
WAIT_BUCKET_KEYS: tuple[WaitBucketKey, ...] = ("UNDER_WARNING", "WARNING", "CRITICAL")

#: Giờ Việt Nam (Asia/Ho_Chi_Minh): UTC+7 cố định, không có giờ mùa hè. Mốc
#: giờ trong cơ sở dữ liệu là UTC naive, nên mọi phép chia theo thứ/giờ địa
#: phương phải cộng hằng số này một cách tường minh.
VIETNAM_UTC_OFFSET = timedelta(hours=7)

#: Bề rộng một cột của phân bố "từ lúc gắn cờ tới khi có người nhận", tính bằng
#: phút. Các cột chạy từ 0 tới ``WAIT_CRITICAL_MINUTES``, cột cuối gom mọi ca từ
#: mốc đó trở lên. 5 chia hết cả 30 lẫn 60, nên ranh giới cột trùng đúng hai mốc
#: tô màu của bảng ca -- hai vạch tham chiếu trên biểu đồ không bao giờ cắt
#: ngang giữa một cột.
CLAIM_BIN_MINUTES = 5
CLAIM_BIN_STARTS: tuple[int, ...] = tuple(range(0, WAIT_CRITICAL_MINUTES, CLAIM_BIN_MINUTES))

#: Ít hơn số ca này thì không nêu trung vị hay tỉ lệ, chỉ nêu số ca. Đây là quy
#: tắc trình bày thống kê (một "trung vị" của hai ca chỉ là hai ca), KHÔNG phải
#: một ngưỡng lâm sàng.
MIN_CASES_FOR_SUMMARY = 5


def esi_from_matched_levels(levels: Sequence[int] | None) -> int | None:
    """Mức khẩn nhất trong các mức atom đã hỗ trợ -- định nghĩa của "mức AI đề xuất"."""
    return min(levels) if levels else None


def ai_proposed_esi(chat: SimpleAgentChatSession) -> int | None:
    """Mức ESI mà agent đề xuất: mức khẩn nhất trong các mức atom đã hỗ trợ.

    Nguồn duy nhất cho cả hàng đợi lẫn bảng số liệu -- xem
    ``routes_nurse_simple._ai_proposed_esi`` gọi thẳng vào đây.
    """
    return esi_from_matched_levels(chat.matched_esi_levels)


# ---------------------------------------------------------------------------
# DTO
# ---------------------------------------------------------------------------


class EsiBucketDTO(BaseModel):
    level: int | None = Field(
        description="Mức ESI AI đề xuất; null nghĩa là agent kết luận chưa đủ dữ liệu"
    )
    count: int


class WaitBucketDTO(BaseModel):
    key: WaitBucketKey = Field(description="Mốc thời gian chờ, chia đúng như bảng ca")
    count: int


class MatrixRowDTO(BaseModel):
    """Một hàng của ma trận: các ca đang mở cùng một mức, chia theo thời gian chờ."""

    key: MatrixRowKey = Field(
        description="Mức ESI AI đề xuất ('1'..'5'), 'INSUFFICIENT' hoặc 'IN_PROGRESS'"
    )
    counts: list[WaitBucketDTO] = Field(description="Luôn đủ ba mốc chờ, theo thứ tự ngắn tới lâu")


class HourPointDTO(BaseModel):
    hour_start: str = Field(description="Đầu giờ tròn theo UTC, dạng YYYY-MM-DDTHH:00:00")
    completed: int = Field(description="Phiên sàng lọc kết thúc trong giờ này")
    decided: int = Field(description="Ca được điều dưỡng chốt trong giờ này")


class HourOfDayDTO(BaseModel):
    hour_utc: int = Field(ge=0, le=23, description="Giờ trong ngày theo UTC")
    completed: int = Field(description="Phiên kết thúc vào giờ này, cộng dồn trong cửa sổ")


class AgreementDTO(BaseModel):
    """Điều dưỡng đã làm gì với mức ESI AI đề xuất, tính trên các ca ĐÃ CHỐT
    trong cửa sổ thời gian đang xem.

    Không phải thước đo độ chính xác -- xem ghi chú đầu module.
    """

    decided_total: int = Field(
        description="Số ca đã chốt trong cửa sổ, tức mẫu số của mọi con số bên dưới"
    )
    confirmed: int = Field(description="Điều dưỡng giữ nguyên mức AI đề xuất")
    escalated: int = Field(description="Điều dưỡng chốt ở mức KHẨN HƠN (final_esi < mức AI đề xuất)")
    de_escalated: int = Field(description="Điều dưỡng chốt ở mức ÍT KHẨN HƠN (final_esi > mức AI đề xuất)")
    adjusted_without_proposal: int = Field(
        description="Điều dưỡng tự chốt mức trong khi AI chưa đề xuất được mức nào"
    )


class ReasonCountDTO(BaseModel):
    code: str
    count: int


class DailyPointDTO(BaseModel):
    date: str = Field(description="Ngày theo UTC, dạng YYYY-MM-DD")
    completed: int = Field(description="Phiên sàng lọc kết thúc trong ngày")
    decided: int = Field(description="Ca được điều dưỡng chốt trong ngày")


class DecisionCellDTO(BaseModel):
    final_esi: int = Field(ge=1, le=5, description="Mức điều dưỡng chốt")
    count: int


class DecisionMatrixRowDTO(BaseModel):
    """Các ca đã chốt có cùng một mức AI đề xuất, chia theo mức điều dưỡng chốt."""

    key: MatrixRowKey = Field(
        description="Mức AI đề xuất ('1'..'5'); 'INSUFFICIENT' = agent kết luận chưa đủ dữ liệu; "
        "'IN_PROGRESS' = phiên chưa sàng lọc xong nên chưa có đề xuất nào"
    )
    counts: list[DecisionCellDTO] = Field(description="Luôn đủ năm cột, ESI 1 tới ESI 5")


class DecisionMatrixDTO(BaseModel):
    """Mức AI đề xuất × mức điều dưỡng chốt, trên đúng tập ca của ``AgreementDTO``.

    Vẫn là "điều dưỡng đã làm gì với đề xuất của AI", không phải độ chính xác:
    không có kết luận chuẩn nào để đối chiếu. Ô trên đường chéo = giữ nguyên.
    """

    decided_total: int = Field(description="Ca đã chốt trong cửa sổ; trùng agreement.decided_total")
    kept: int = Field(description="Đường chéo: điều dưỡng chốt đúng mức AI đề xuất")
    more_urgent: int = Field(description="Điều dưỡng chốt KHẨN HƠN: final_esi nhỏ hơn mức AI đề xuất")
    less_urgent: int = Field(description="Điều dưỡng chốt ÍT KHẨN HƠN: final_esi lớn hơn mức AI đề xuất")
    without_proposal: int = Field(description="Ca ở hàng 'INSUFFICIENT' hoặc 'IN_PROGRESS': không có mức AI để so")
    without_final_esi: int = Field(
        description="Ca đã chốt mà không ghi mức 1..5 nào (dữ liệu cũ), nên không nằm trong ô nào"
    )
    rows: list[DecisionMatrixRowDTO] = Field(description="Luôn đủ 7 hàng, cùng thứ tự với esi_wait_matrix")


class ClaimBinDTO(BaseModel):
    min_minutes: int = Field(description="Cận dưới, tính cả mốc này")
    max_minutes: int | None = Field(description="Cận trên, không tính mốc này; null = cột cuối, không có cận trên")
    count: int


class FlaggedClaimDTO(BaseModel):
    """Ca bộ lọc khẩn cấp gắn cờ trong cửa sổ: từ lúc gắn cờ tới khi có người nhận.

    "Nhận" là ``claimed_at`` đang ghi trên ca, không có thì là lúc chốt ca. Khi ca
    bị trả lại hoặc tạm gác rồi khôi phục, hàng đợi xóa ``claimed_at``: với những
    ca đó đây là lần nhận sau cùng, không phải lần đầu. Không có chỉ tiêu nào ở
    đây -- xem ghi chú đầu module.
    """

    min_cases: int = Field(description="Dưới số ca đã nhận này thì không nêu tỉ lệ, không vẽ phân bố")
    flagged_total: int = Field(description="Ca có cờ trong cửa sổ, xếp theo attention_raised_at")
    claimed: int = Field(description="Ca đã có người nhận hoặc đã được chốt; bằng tổng của bins")
    unclaimed: int = Field(description="Ca hiện không ai giữ và chưa được chốt")
    untimed: int = Field(description="Ca có người giữ nhưng không ghi thời điểm nhận (dữ liệu cũ)")
    claimed_under_warning: int = Field(
        description="Trong số đã nhận: nhận trước mốc tô cảnh báo của bảng ca (WAIT_WARNING_MINUTES)"
    )
    bins: list[ClaimBinDTO] = Field(
        description="Cột CLAIM_BIN_MINUTES phút từ 0 tới WAIT_CRITICAL_MINUTES, rồi một cột không có cận trên"
    )


class DecisionWaitRowDTO(BaseModel):
    key: MatrixRowKey = Field(description="Mức AI đề xuất, cùng khóa với esi_wait_matrix")
    count: int = Field(description="Số ca đã chốt trong cửa sổ ở hàng này")
    median_minutes: int | None = Field(
        description="Trung vị số phút chờ, làm tròn xuống như bảng ca; null khi count < min_cases"
    )


class DecisionWaitDTO(BaseModel):
    """Từ lúc ca vào hàng đợi (``waiting_since`` của bảng ca) tới lúc điều dưỡng chốt."""

    min_cases: int = Field(description="Dưới số ca này thì không nêu trung vị")
    decided_total: int = Field(description="Ca đã chốt trong cửa sổ; trùng agreement.decided_total")
    rows: list[DecisionWaitRowDTO] = Field(description="Luôn đủ 7 hàng, cùng thứ tự với esi_wait_matrix")


class WeekdayHourRowDTO(BaseModel):
    weekday: int = Field(ge=1, le=7, description="Thứ theo ISO, giờ Việt Nam: 1 = Thứ Hai ... 7 = Chủ nhật")
    days: int = Field(description="Số ngày của thứ này nằm trong cửa sổ theo lịch Việt Nam, kể cả hôm nay")
    hours: list[int] = Field(description="Đủ 24 giờ 0..23 giờ Việt Nam: số phiên kết thúc trong giờ đó")


class WeekdayHourDTO(BaseModel):
    utc_offset_hours: int = Field(description="Giờ Việt Nam lệch UTC bao nhiêu giờ; mọi ô đã đổi theo độ lệch này")
    first_day: str = Field(description="Ngày đầu cửa sổ theo lịch Việt Nam, YYYY-MM-DD")
    last_day: str = Field(description="Hôm nay theo lịch Việt Nam, YYYY-MM-DD; ngày này tính tới lúc cập nhật")
    total: int = Field(description="Tổng mọi ô")
    rows: list[WeekdayHourRowDTO] = Field(description="Luôn đủ 7 hàng, Thứ Hai tới Chủ nhật")


class NurseDashboardDTO(BaseModel):
    generated_at: str = Field(description="Thời điểm chụp số liệu, UTC")
    window_days: int = Field(description="Bề rộng cửa sổ của phần lịch sử, tính bằng ngày")

    # --- Ảnh chụp hàng đợi ngay tại thời điểm gọi ---
    waiting: int = Field(description="Ca đang mở, chưa ai nhận")
    assigned_total: int = Field(description="Ca đang có người phụ trách")
    assigned_to_me: int = Field(description="Trong số đó, ca của chính người đang xem")
    parked: int
    decided: int = Field(description="Tổng số ca đã chốt, mọi thời điểm")
    insufficient_live: int = Field(
        description="Ca chưa đóng mà agent kết luận chưa đủ dữ liệu"
    )
    attention_live: int = Field(
        description="Ca chưa đóng mà bộ lọc khẩn cấp đã gắn cờ 'Cần xem ngay'"
    )
    in_progress_live: int = Field(
        description="Trong số đó, phiên còn đang sàng lọc nên chưa có mức AI đề xuất"
    )
    longest_wait_minutes: int | None = Field(
        description="Thời gian chờ của ca chờ lâu nhất đang còn trong hàng đợi"
    )

    # --- Phân bố ---
    esi_distribution: list[EsiBucketDTO] = Field(
        description="Ca chưa đóng đã sàng lọc xong, theo mức AI đề xuất (không gồm IN_PROGRESS)"
    )
    wait_buckets: list[WaitBucketDTO] = Field(description="Trên mọi ca chưa đóng, kể cả IN_PROGRESS")
    esi_wait_matrix: list[MatrixRowDTO] = Field(
        description="Mức × thời gian chờ trên mọi ca chưa đóng; luôn đủ 7 hàng"
    )

    # --- Lịch sử trong cửa sổ ---
    completed_in_window: int = Field(description="Phiên sàng lọc kết thúc trong cửa sổ")
    decided_in_window: int = Field(description="Ca được chốt trong cửa sổ")
    agreement: AgreementDTO
    reason_codes: list[ReasonCountDTO] = Field(description="Lý do đã chọn khi chốt ca, trong cửa sổ")
    daily_volume: list[DailyPointDTO] = Field(description="Đủ window_days ngày liên tục, kể cả ngày rỗng")
    hour_of_day: list[HourOfDayDTO] = Field(description="Đủ 24 giờ UTC, cộng dồn trong cửa sổ")
    recent_hours: list[HourPointDTO] = Field(
        description="24 giờ tròn gần nhất, cũ tới mới; giờ cuối đang chạy"
    )

    # --- Chất lượng và xu hướng trong cửa sổ (thêm sau, chỉ cộng thêm trường) ---
    decision_matrix: DecisionMatrixDTO
    flagged_claim: FlaggedClaimDTO
    decision_wait: DecisionWaitDTO
    weekday_hour: WeekdayHourDTO


# ---------------------------------------------------------------------------
# Tổng hợp
# ---------------------------------------------------------------------------


#: Một ca kèm dòng review của nó; ``None`` nghĩa là chưa ai chạm tới ca này.
DashboardRow = tuple[SimpleAgentChatSession, SimpleAgentNurseReview | None]


async def build_nurse_dashboard(
    session: AsyncSession,
    nurse_id: str,
    window_days: int = DEFAULT_WINDOW_DAYS,
) -> NurseDashboardDTO:
    """Đọc dữ liệu rồi giao cho ``aggregate_dashboard`` đếm.

    Một truy vấn LEFT JOIN duy nhất thay vì đọc từng dòng review một: ca chưa
    có dòng review trả về ``None`` và được hiểu đúng là đang chờ tiếp nhận.
    Bốn khối chất lượng và xu hướng đọc thêm một truy vấn hẹp, đã chặn theo cửa
    sổ (``load_history_rows``).
    """
    now = get_utc_now()
    rows = (
        await session.execute(
            select(SimpleAgentChatSession, SimpleAgentNurseReview)
            .join(
                SimpleAgentNurseReview,
                SimpleAgentNurseReview.session_id == SimpleAgentChatSession.session_id,
                isouter=True,
            )
            .where(REVIEWABLE_CLAUSE)
        )
    ).all()
    history_rows = await load_history_rows(session, now, window_days)
    return aggregate_dashboard(list(rows), nurse_id, now, window_days=window_days, history_rows=history_rows)


class HistoryRow(NamedTuple):
    """Đúng những cột mà bốn khối chất lượng và xu hướng cần, của một ca xem xét được.

    Các trường của review là ``None`` khi ca chưa có dòng review (chưa ai chạm tới).
    Thứ tự trường trùng ``_HISTORY_COLUMNS``.
    """

    session_status: str
    matched_esi_levels: list[int] | None
    started_at: datetime
    completed_at: datetime | None
    attention_required: bool | None
    attention_raised_at: datetime | None
    review_status: str | None
    assigned_nurse_id: str | None
    final_esi: int | None
    claimed_at: datetime | None
    decided_at: datetime | None
    handed_off_at: datetime | None


_HISTORY_COLUMNS = (
    SimpleAgentChatSession.status,
    SimpleAgentChatSession.matched_esi_levels,
    SimpleAgentChatSession.started_at,
    SimpleAgentChatSession.completed_at,
    SimpleAgentChatSession.attention_required,
    SimpleAgentChatSession.attention_raised_at,
    SimpleAgentNurseReview.review_status,
    SimpleAgentNurseReview.assigned_nurse_id,
    SimpleAgentNurseReview.final_esi,
    SimpleAgentNurseReview.claimed_at,
    SimpleAgentNurseReview.decided_at,
    SimpleAgentNurseReview.handed_off_at,
)


def history_row_of(chat: SimpleAgentChatSession, review: SimpleAgentNurseReview | None) -> HistoryRow:
    """Cùng một ca, đọc từ cặp ORM của truy vấn ảnh chụp thay vì từ truy vấn hẹp."""
    return HistoryRow(
        session_status=chat.status,
        matched_esi_levels=chat.matched_esi_levels,
        started_at=chat.started_at,
        completed_at=chat.completed_at,
        attention_required=chat.attention_required,
        attention_raised_at=chat.attention_raised_at,
        review_status=review.review_status if review else None,
        assigned_nurse_id=review.assigned_nurse_id if review else None,
        final_esi=review.final_esi if review else None,
        claimed_at=review.claimed_at if review else None,
        decided_at=review.decided_at if review else None,
        handed_off_at=review.handed_off_at if review else None,
    )


def history_lower_bound(now: datetime, window_days: int) -> datetime:
    """Mốc UTC sớm nhất mà một sự kiện còn có thể thuộc một trong bốn khối mới.

    Cửa sổ theo ngày UTC bắt đầu lúc 0:00 UTC của ngày đầu; cửa sổ theo lịch
    Việt Nam (``weekday_hour``) bắt đầu lúc 0:00 giờ Việt Nam, tức 17:00 UTC hôm
    trước. Lấy mốc sớm hơn trong hai: truy vấn chỉ được lấy dư, không được thiếu
    -- phép lọc chính xác vẫn do ``aggregate_history_panels`` làm.
    """
    utc_first_day = now.date() - timedelta(days=window_days - 1)
    vietnam_first_day = (now + VIETNAM_UTC_OFFSET).date() - timedelta(days=window_days - 1)
    return min(
        datetime.combine(utc_first_day, time.min),
        datetime.combine(vietnam_first_day, time.min) - VIETNAM_UTC_OFFSET,
    )


async def load_history_rows(session: AsyncSession, now: datetime, window_days: int) -> list[HistoryRow]:
    """Ca xem xét được (``REVIEWABLE_CLAUSE``) có ít nhất một mốc rơi vào cửa sổ.

    Chặn trong SQL bằng các phép so sánh thời gian thuần, chạy như nhau trên
    PostgreSQL và SQLite; chỉ đọc 12 cột, không đọc nội dung hội thoại.
    """
    since = history_lower_bound(now, window_days)
    result = await session.execute(
        select(*_HISTORY_COLUMNS)
        .select_from(SimpleAgentChatSession)
        .join(
            SimpleAgentNurseReview,
            SimpleAgentNurseReview.session_id == SimpleAgentChatSession.session_id,
            isouter=True,
        )
        .where(REVIEWABLE_CLAUSE)
        .where(
            or_(
                SimpleAgentChatSession.completed_at >= since,
                SimpleAgentChatSession.attention_raised_at >= since,
                SimpleAgentNurseReview.decided_at >= since,
                SimpleAgentNurseReview.handed_off_at >= since,
            )
        )
    )
    return [HistoryRow(*row) for row in result.all()]


def wait_bucket_of(minutes: int) -> WaitBucketKey:
    """Mốc chờ của một số phút. Đúng mốc thì rơi vào nhóm nặng hơn, như bảng ca."""
    if minutes >= WAIT_CRITICAL_MINUTES:
        return "CRITICAL"
    if minutes >= WAIT_WARNING_MINUTES:
        return "WARNING"
    return "UNDER_WARNING"


def _floor_hour(moment: datetime) -> datetime:
    return moment.replace(minute=0, second=0, microsecond=0)


def aggregate_dashboard(
    rows: Sequence[DashboardRow],
    nurse_id: str,
    now: datetime,
    window_days: int = DEFAULT_WINDOW_DAYS,
    *,
    history_rows: Sequence[HistoryRow] | None = None,
) -> NurseDashboardDTO:
    """Đếm một lượt trên toàn bộ ca mà điều dưỡng xem xét được.

    Tách khỏi phần truy vấn và nhận ``now`` như một tham số tường minh: phần
    logic dễ sai nhất ở đây -- chiều của thang ESI, cách cắt mốc thời gian
    chờ và ranh giới của cửa sổ -- nhờ vậy kiểm thử được mà không cần dựng cơ
    sở dữ liệu, và không phụ thuộc vào đồng hồ lúc chạy test.

    ``history_rows`` là kết quả của ``load_history_rows``. Bỏ trống thì bốn khối
    chất lượng và xu hướng được đếm trên chính ``rows``: cùng kết quả, vì
    ``aggregate_history_panels`` tự lọc chính xác theo cửa sổ.
    """
    if window_days not in WINDOW_DAYS_CHOICES:
        raise ValueError(f"window_days phải là một trong {WINDOW_DAYS_CHOICES}, nhận {window_days}")

    panels = aggregate_history_panels(
        history_rows if history_rows is not None else [history_row_of(chat, review) for chat, review in rows],
        now,
        window_days,
    )

    today = now.date()
    window_start = today - timedelta(days=window_days - 1)
    current_hour = _floor_hour(now)
    first_recent_hour = current_hour - timedelta(hours=RECENT_HOURS - 1)

    def in_window(moment: datetime | None) -> bool:
        return moment is not None and window_start <= moment.date() <= today

    def recent_hour(moment: datetime | None) -> datetime | None:
        """Giờ tròn của sự kiện nếu nó nằm trong dải 24 giờ qua, không thì None."""
        if moment is None or moment > now:
            return None
        hour = _floor_hour(moment)
        return hour if hour >= first_recent_hour else None

    waiting = 0
    assigned_total = 0
    assigned_to_me = 0
    parked = 0
    decided = 0
    insufficient_live = 0
    attention_live = 0
    in_progress_live = 0
    longest_wait_minutes: int | None = None
    completed_in_window = 0
    decided_in_window = 0

    esi_counter: Counter[int | None] = Counter()
    wait_counter: Counter[str] = Counter()
    matrix_counter: Counter[tuple[str, str]] = Counter()
    reason_counter: Counter[str] = Counter()
    completed_by_day: Counter[str] = Counter()
    decided_by_day: Counter[str] = Counter()
    completed_by_hour_of_day: Counter[int] = Counter()
    recent_completed: Counter[datetime] = Counter()
    recent_decided: Counter[datetime] = Counter()

    agreement_confirmed = 0
    agreement_escalated = 0
    agreement_de_escalated = 0
    agreement_without_proposal = 0

    for chat, review in rows:
        status = review.review_status if review else "WAITING_REVIEW"
        is_closed = status == TERMINAL_REVIEW_STATUS
        is_parked = status == PARKED_STATUS
        # "Còn sống" = chưa đóng và chưa tạm gác, tức đúng phần việc đang nằm
        # trên bàn của kíp trực. Mọi phân bố bên dưới đều tính trên tập này.
        is_live = not is_closed and not is_parked
        # Câu truy vấn chỉ để lọt một loại phiên chưa xong: phiên đã gắn cờ.
        # Phiên đó chưa có kết luận nào của agent, nên không có mức để xếp.
        in_progress = chat.status != "COMPLETED"

        if chat.completed_at:
            completed_by_day[chat.completed_at.date().isoformat()] += 1
            if in_window(chat.completed_at):
                completed_in_window += 1
                completed_by_hour_of_day[chat.completed_at.hour] += 1
            completed_hour = recent_hour(chat.completed_at)
            if completed_hour is not None:
                recent_completed[completed_hour] += 1

        if is_parked:
            parked += 1
        elif is_closed:
            decided += 1
        else:
            assignee = review.assigned_nurse_id if review else None
            if assignee is None:
                waiting += 1
            else:
                assigned_total += 1
                if assignee == nurse_id:
                    assigned_to_me += 1

        if is_live:
            if chat.attention_required:
                attention_live += 1

            # Cùng mốc bắt đầu đếm giờ với bảng ca (`_queue_item`): lúc agent
            # kết thúc phiên; phiên chưa xong thì lúc bị gắn cờ; không có cả
            # hai mốc thì lúc mở phiên.
            waiting_since = chat.completed_at or chat.attention_raised_at or chat.started_at
            minutes = max(0, int((now - waiting_since).total_seconds() // 60))
            if longest_wait_minutes is None or minutes > longest_wait_minutes:
                longest_wait_minutes = minutes
            bucket = wait_bucket_of(minutes)
            wait_counter[bucket] += 1

            if in_progress:
                in_progress_live += 1
                matrix_counter[("IN_PROGRESS", bucket)] += 1
            else:
                if chat.final_action == "RETURN_INCOMPLETE":
                    insufficient_live += 1
                level = ai_proposed_esi(chat)
                esi_counter[level] += 1
                matrix_counter[(str(level) if level is not None else "INSUFFICIENT", bucket)] += 1

        if is_closed and review is not None:
            closed_at = review.decided_at or review.handed_off_at
            if closed_at:
                decided_by_day[closed_at.date().isoformat()] += 1
            decided_hour = recent_hour(closed_at)
            if decided_hour is not None:
                recent_decided[decided_hour] += 1
            # Ca không đặt được vào một ngày nào thì không thuộc cửa sổ nào.
            if not in_window(closed_at):
                continue

            decided_in_window += 1
            if review.decision_reason_code:
                reason_counter[review.decision_reason_code] += 1

            proposed = ai_proposed_esi(chat)
            if review.decision_type == "CONFIRM_ESI":
                agreement_confirmed += 1
            elif proposed is None or review.final_esi is None:
                agreement_without_proposal += 1
            elif review.final_esi < proposed:
                # Thang ESI chạy ngược: số nhỏ hơn nghĩa là khẩn hơn.
                agreement_escalated += 1
            elif review.final_esi > proposed:
                agreement_de_escalated += 1
            else:
                # Bấm "điều chỉnh" nhưng chốt lại đúng mức cũ -- vẫn là giữ nguyên.
                agreement_confirmed += 1

    daily_volume = []
    for offset in range(window_days - 1, -1, -1):
        key = (today - timedelta(days=offset)).isoformat()
        daily_volume.append(
            DailyPointDTO(
                date=key,
                completed=completed_by_day.get(key, 0),
                decided=decided_by_day.get(key, 0),
            )
        )

    recent_hours = []
    for offset in range(RECENT_HOURS):
        hour = first_recent_hour + timedelta(hours=offset)
        recent_hours.append(
            HourPointDTO(
                hour_start=hour.isoformat(),
                completed=recent_completed.get(hour, 0),
                decided=recent_decided.get(hour, 0),
            )
        )

    # Luôn phát đủ 6 vạch ESI (1..5 + "chưa đủ dữ liệu") kể cả khi bằng 0: một
    # mức vắng mặt là thông tin, còn một biểu đồ đổi số vạch theo ngày thì
    # không đọc so sánh được. Ma trận cũng vậy: đủ 7 hàng × 3 mốc chờ.
    esi_distribution = [EsiBucketDTO(level=level, count=esi_counter.get(level, 0)) for level in (1, 2, 3, 4, 5)]
    esi_distribution.append(EsiBucketDTO(level=None, count=esi_counter.get(None, 0)))

    wait_buckets = [WaitBucketDTO(key=key, count=wait_counter.get(key, 0)) for key in WAIT_BUCKET_KEYS]

    esi_wait_matrix = [
        MatrixRowDTO(
            key=row,
            counts=[WaitBucketDTO(key=key, count=matrix_counter.get((row, key), 0)) for key in WAIT_BUCKET_KEYS],
        )
        for row in MATRIX_ROW_KEYS
    ]

    return NurseDashboardDTO(
        generated_at=now.isoformat(),
        window_days=window_days,
        waiting=waiting,
        assigned_total=assigned_total,
        assigned_to_me=assigned_to_me,
        parked=parked,
        decided=decided,
        insufficient_live=insufficient_live,
        attention_live=attention_live,
        in_progress_live=in_progress_live,
        longest_wait_minutes=longest_wait_minutes,
        esi_distribution=esi_distribution,
        wait_buckets=wait_buckets,
        esi_wait_matrix=esi_wait_matrix,
        completed_in_window=completed_in_window,
        decided_in_window=decided_in_window,
        agreement=AgreementDTO(
            decided_total=decided_in_window,
            confirmed=agreement_confirmed,
            escalated=agreement_escalated,
            de_escalated=agreement_de_escalated,
            adjusted_without_proposal=agreement_without_proposal,
        ),
        reason_codes=[
            ReasonCountDTO(code=code, count=count)
            for code, count in sorted(reason_counter.items(), key=lambda pair: (-pair[1], pair[0]))
        ],
        daily_volume=daily_volume,
        hour_of_day=[HourOfDayDTO(hour_utc=hour, completed=completed_by_hour_of_day.get(hour, 0)) for hour in range(24)],
        recent_hours=recent_hours,
        decision_matrix=panels.decision_matrix,
        flagged_claim=panels.flagged_claim,
        decision_wait=panels.decision_wait,
        weekday_hour=panels.weekday_hour,
    )


# ---------------------------------------------------------------------------
# Chất lượng và xu hướng
# ---------------------------------------------------------------------------


class HistoryPanels(NamedTuple):
    decision_matrix: DecisionMatrixDTO
    flagged_claim: FlaggedClaimDTO
    decision_wait: DecisionWaitDTO
    weekday_hour: WeekdayHourDTO


#: Hai hàng không có mức AI để so với mức điều dưỡng chốt.
_NO_PROPOSAL_KEYS: frozenset[str] = frozenset({"INSUFFICIENT", "IN_PROGRESS"})


def proposal_row_key(row: HistoryRow) -> MatrixRowKey:
    """Hàng của một ca theo mức AI đề xuất -- cùng cách xếp với ``esi_wait_matrix``.

    Phiên chưa sàng lọc xong thì chưa có kết luận nào của agent: hàng riêng,
    không trộn vào "chưa đủ dữ liệu".
    """
    if row.session_status != "COMPLETED":
        return "IN_PROGRESS"
    level = esi_from_matched_levels(row.matched_esi_levels)
    if level is None:
        return "INSUFFICIENT"
    return MATRIX_ROW_KEYS[level - 1]


def queue_waiting_since(row: HistoryRow, moment: datetime) -> datetime:
    """``waiting_since`` của bảng ca (``_queue_item``) đúng như nó hiện ở thời điểm ``moment``.

    Bảng ca tính ``completed_at or attention_raised_at or started_at`` trên giá
    trị HIỆN TẠI. Một phiên bị gắn cờ, được chốt khi người bệnh còn đang khai rồi
    mới kết thúc sau đó, sẽ có ``completed_at`` muộn hơn lúc chốt: đọc thẳng công
    thức sẽ ra thời gian chờ âm. Mốc nào chưa xảy ra ở ``moment`` thì bỏ qua.
    """
    if row.completed_at is not None and row.completed_at <= moment:
        return row.completed_at
    if row.attention_raised_at is not None and row.attention_raised_at <= moment:
        return row.attention_raised_at
    return row.started_at


def _whole_minutes(delta: timedelta) -> int:
    """Số phút làm tròn xuống, không âm -- cùng cách bảng ca đọc thời gian chờ."""
    return max(0, int(delta.total_seconds() // 60))


def _claim_bin_index(minutes: int) -> int:
    if minutes >= WAIT_CRITICAL_MINUTES:
        return len(CLAIM_BIN_STARTS)
    return minutes // CLAIM_BIN_MINUTES


def _median_minutes(wait_seconds: Sequence[float]) -> int | None:
    if len(wait_seconds) < MIN_CASES_FOR_SUMMARY:
        return None
    return int(statistics.median(wait_seconds) // 60)


def aggregate_history_panels(rows: Sequence[HistoryRow], now: datetime, window_days: int) -> HistoryPanels:
    """Đếm bốn khối chất lượng và xu hướng trong một lượt.

    - Ca đã chốt: ``review_status == HANDED_OFF`` và mốc chốt
      (``decided_at or handed_off_at``) thuộc cửa sổ ngày UTC -- đúng tập của
      ``AgreementDTO``, nên ``decided_total`` của hai khối luôn bằng nhau.
    - Ca có cờ: ``attention_required`` và ``attention_raised_at`` thuộc cửa sổ.
    - Phiên kết thúc: ``completed_at`` đổi sang giờ Việt Nam rồi mới so với cửa
      sổ theo lịch Việt Nam và lấy thứ, giờ.
    """
    today = now.date()
    window_start = today - timedelta(days=window_days - 1)

    def in_window(moment: datetime | None) -> bool:
        return moment is not None and window_start <= moment.date() <= today

    vietnam_today = (now + VIETNAM_UTC_OFFSET).date()
    vietnam_first_day = vietnam_today - timedelta(days=window_days - 1)

    decision_counter: Counter[tuple[str, int]] = Counter()
    without_final_esi = 0
    wait_seconds: dict[str, list[float]] = {key: [] for key in MATRIX_ROW_KEYS}

    claim_bins = [0] * (len(CLAIM_BIN_STARTS) + 1)
    flagged_total = 0
    unclaimed = 0
    untimed = 0
    claimed_under_warning = 0

    weekday_hours = [[0] * 24 for _ in range(7)]

    for row in rows:
        if row.completed_at is not None:
            local = row.completed_at + VIETNAM_UTC_OFFSET
            if vietnam_first_day <= local.date() <= vietnam_today:
                weekday_hours[local.isoweekday() - 1][local.hour] += 1

        if row.attention_required and row.attention_raised_at is not None and in_window(row.attention_raised_at):
            flagged_total += 1
            # Lúc có người nhận; ca được chốt thẳng mà không ai nhận trước thì là lúc chốt.
            reached_at = row.claimed_at or row.decided_at or row.handed_off_at
            if reached_at is None:
                if row.assigned_nurse_id is None:
                    unclaimed += 1
                else:
                    untimed += 1
            else:
                minutes = _whole_minutes(reached_at - row.attention_raised_at)
                claim_bins[_claim_bin_index(minutes)] += 1
                if minutes < WAIT_WARNING_MINUTES:
                    claimed_under_warning += 1

        if row.review_status != TERMINAL_REVIEW_STATUS:
            continue
        closed_at = row.decided_at or row.handed_off_at
        if closed_at is None or not in_window(closed_at):
            continue
        key = proposal_row_key(row)
        if row.final_esi is not None and 1 <= row.final_esi <= 5:
            decision_counter[(key, row.final_esi)] += 1
        else:
            without_final_esi += 1
        waited = closed_at - queue_waiting_since(row, closed_at)
        wait_seconds[key].append(max(0.0, waited.total_seconds()))

    kept = more_urgent = less_urgent = without_proposal = 0
    for (key, final_esi), count in decision_counter.items():
        if key in _NO_PROPOSAL_KEYS:
            without_proposal += count
            continue
        proposed = int(key)
        if final_esi == proposed:
            kept += count
        elif final_esi < proposed:
            # Thang ESI chạy ngược: số nhỏ hơn nghĩa là khẩn hơn.
            more_urgent += count
        else:
            less_urgent += count
    decided_total = kept + more_urgent + less_urgent + without_proposal + without_final_esi

    decision_matrix = DecisionMatrixDTO(
        decided_total=decided_total,
        kept=kept,
        more_urgent=more_urgent,
        less_urgent=less_urgent,
        without_proposal=without_proposal,
        without_final_esi=without_final_esi,
        rows=[
            DecisionMatrixRowDTO(
                key=key,
                counts=[
                    DecisionCellDTO(final_esi=level, count=decision_counter.get((key, level), 0))
                    for level in (1, 2, 3, 4, 5)
                ],
            )
            for key in MATRIX_ROW_KEYS
        ],
    )

    bins = [
        ClaimBinDTO(min_minutes=start, max_minutes=start + CLAIM_BIN_MINUTES, count=claim_bins[index])
        for index, start in enumerate(CLAIM_BIN_STARTS)
    ]
    bins.append(ClaimBinDTO(min_minutes=WAIT_CRITICAL_MINUTES, max_minutes=None, count=claim_bins[-1]))
    flagged_claim = FlaggedClaimDTO(
        min_cases=MIN_CASES_FOR_SUMMARY,
        flagged_total=flagged_total,
        claimed=sum(claim_bins),
        unclaimed=unclaimed,
        untimed=untimed,
        claimed_under_warning=claimed_under_warning,
        bins=bins,
    )

    decision_wait = DecisionWaitDTO(
        min_cases=MIN_CASES_FOR_SUMMARY,
        decided_total=decided_total,
        rows=[
            DecisionWaitRowDTO(
                key=key,
                count=len(wait_seconds[key]),
                median_minutes=_median_minutes(wait_seconds[key]),
            )
            for key in MATRIX_ROW_KEYS
        ],
    )

    days_per_weekday = Counter(
        (vietnam_first_day + timedelta(days=offset)).isoweekday() for offset in range(window_days)
    )
    weekday_hour = WeekdayHourDTO(
        utc_offset_hours=int(VIETNAM_UTC_OFFSET.total_seconds() // 3600),
        first_day=vietnam_first_day.isoformat(),
        last_day=vietnam_today.isoformat(),
        total=sum(sum(hours) for hours in weekday_hours),
        rows=[
            WeekdayHourRowDTO(weekday=weekday, days=days_per_weekday.get(weekday, 0), hours=weekday_hours[weekday - 1])
            for weekday in range(1, 8)
        ],
    )

    return HistoryPanels(
        decision_matrix=decision_matrix,
        flagged_claim=flagged_claim,
        decision_wait=decision_wait,
        weekday_hour=weekday_hour,
    )
