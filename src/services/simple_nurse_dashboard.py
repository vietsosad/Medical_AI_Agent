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
"""

from __future__ import annotations

from collections import Counter
from collections.abc import Sequence
from datetime import datetime, timedelta
from typing import Literal

from pydantic import BaseModel, Field
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
#: frontend/src/components/clinical/nurse-simple/SimpleNurseQueueWorkspace.tsx
#: -- bảng số liệu và bảng ca phải chia mốc giống hệt nhau.
WAIT_WARNING_MINUTES = 30
WAIT_CRITICAL_MINUTES = 60

#: Bề rộng cửa sổ của biểu đồ khối lượng theo ngày.
DAILY_VOLUME_DAYS = 14


def ai_proposed_esi(chat: SimpleAgentChatSession) -> int | None:
    """Mức ESI mà agent đề xuất: mức khẩn nhất trong các mức atom đã hỗ trợ.

    Nguồn duy nhất cho cả hàng đợi lẫn bảng số liệu -- xem
    ``routes_nurse_simple._ai_proposed_esi`` gọi thẳng vào đây.
    """
    return min(chat.matched_esi_levels) if chat.matched_esi_levels else None


# ---------------------------------------------------------------------------
# DTO
# ---------------------------------------------------------------------------


class EsiBucketDTO(BaseModel):
    level: int | None = Field(
        description="Mức ESI AI đề xuất; null nghĩa là agent kết luận chưa đủ dữ liệu"
    )
    count: int


class WaitBucketDTO(BaseModel):
    key: Literal["UNDER_WARNING", "WARNING", "CRITICAL"] = Field(
        description="Mốc thời gian chờ, chia đúng như bảng ca"
    )
    count: int


class AgreementDTO(BaseModel):
    """Điều dưỡng đã làm gì với mức ESI AI đề xuất, tính trên các ca ĐÃ CHỐT.

    Không phải thước đo độ chính xác -- xem ghi chú đầu module.
    """

    decided_total: int = Field(description="Tổng số ca đã chốt, tức mẫu số của mọi con số bên dưới")
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


class NurseDashboardDTO(BaseModel):
    generated_at: str = Field(description="Thời điểm chụp số liệu, UTC")

    # --- Ảnh chụp hàng đợi ngay tại thời điểm gọi ---
    waiting: int = Field(description="Ca đã sàng lọc xong, chưa ai nhận")
    assigned_total: int = Field(description="Ca đang có người phụ trách")
    assigned_to_me: int = Field(description="Trong số đó, ca của chính người đang xem")
    parked: int
    decided: int
    insufficient_live: int = Field(
        description="Ca chưa đóng mà agent kết luận chưa đủ dữ liệu"
    )
    longest_wait_minutes: int | None = Field(
        description="Thời gian chờ của ca chờ lâu nhất đang còn trong hàng đợi"
    )

    # --- Phân bố ---
    esi_distribution: list[EsiBucketDTO] = Field(
        description="Trên các ca chưa đóng (đang chờ + đang phụ trách)"
    )
    wait_buckets: list[WaitBucketDTO] = Field(description="Trên đúng tập ca của esi_distribution")
    agreement: AgreementDTO
    reason_codes: list[ReasonCountDTO] = Field(description="Lý do đã chọn khi chốt ca")
    daily_volume: list[DailyPointDTO]


# ---------------------------------------------------------------------------
# Tổng hợp
# ---------------------------------------------------------------------------


#: Một ca kèm dòng review của nó; ``None`` nghĩa là chưa ai chạm tới ca này.
DashboardRow = tuple[SimpleAgentChatSession, SimpleAgentNurseReview | None]


async def build_nurse_dashboard(session: AsyncSession, nurse_id: str) -> NurseDashboardDTO:
    """Đọc dữ liệu rồi giao cho ``aggregate_dashboard`` đếm.

    Một truy vấn LEFT JOIN duy nhất thay vì đọc từng dòng review một: ca chưa
    có dòng review trả về ``None`` và được hiểu đúng là đang chờ tiếp nhận.
    """
    rows = (
        await session.execute(
            select(SimpleAgentChatSession, SimpleAgentNurseReview)
            .join(
                SimpleAgentNurseReview,
                SimpleAgentNurseReview.session_id == SimpleAgentChatSession.session_id,
                isouter=True,
            )
            .where(SimpleAgentChatSession.status == "COMPLETED")
        )
    ).all()
    return aggregate_dashboard(list(rows), nurse_id, get_utc_now())


def aggregate_dashboard(
    rows: Sequence[DashboardRow],
    nurse_id: str,
    now: datetime,
) -> NurseDashboardDTO:
    """Đếm một lượt trên toàn bộ ca đã sàng lọc xong.

    Tách khỏi phần truy vấn và nhận ``now`` như một tham số tường minh: phần
    logic dễ sai nhất ở đây -- chiều của thang ESI và cách cắt mốc thời gian
    chờ -- nhờ vậy kiểm thử được mà không cần dựng cơ sở dữ liệu, và không phụ
    thuộc vào đồng hồ lúc chạy test.
    """
    waiting = 0
    assigned_total = 0
    assigned_to_me = 0
    parked = 0
    decided = 0
    insufficient_live = 0
    longest_wait_minutes: int | None = None

    esi_counter: Counter[int | None] = Counter()
    wait_counter: Counter[str] = Counter()
    reason_counter: Counter[str] = Counter()
    completed_by_day: Counter[str] = Counter()
    decided_by_day: Counter[str] = Counter()

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

        if chat.completed_at:
            completed_by_day[chat.completed_at.date().isoformat()] += 1

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
            if chat.final_action == "RETURN_INCOMPLETE":
                insufficient_live += 1

            esi_counter[ai_proposed_esi(chat)] += 1

            # Cùng mốc bắt đầu đếm giờ với bảng ca: thời điểm agent kết thúc
            # phiên, lùi về lúc mở phiên nếu vì lý do nào đó chưa có mốc kết thúc.
            waiting_since = chat.completed_at or chat.started_at
            minutes = max(0, int((now - waiting_since).total_seconds() // 60))
            if longest_wait_minutes is None or minutes > longest_wait_minutes:
                longest_wait_minutes = minutes

            if minutes >= WAIT_CRITICAL_MINUTES:
                wait_counter["CRITICAL"] += 1
            elif minutes >= WAIT_WARNING_MINUTES:
                wait_counter["WARNING"] += 1
            else:
                wait_counter["UNDER_WARNING"] += 1

        if is_closed and review is not None:
            closed_at = review.decided_at or review.handed_off_at
            if closed_at:
                decided_by_day[closed_at.date().isoformat()] += 1
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

    today = now.date()
    daily_volume = []
    for offset in range(DAILY_VOLUME_DAYS - 1, -1, -1):
        key = (today - timedelta(days=offset)).isoformat()
        daily_volume.append(
            DailyPointDTO(
                date=key,
                completed=completed_by_day.get(key, 0),
                decided=decided_by_day.get(key, 0),
            )
        )

    # Luôn phát đủ 6 vạch ESI (1..5 + "chưa đủ dữ liệu") kể cả khi bằng 0: một
    # mức vắng mặt là thông tin, còn một biểu đồ đổi số vạch theo ngày thì
    # không đọc so sánh được.
    esi_distribution = [EsiBucketDTO(level=level, count=esi_counter.get(level, 0)) for level in (1, 2, 3, 4, 5)]
    esi_distribution.append(EsiBucketDTO(level=None, count=esi_counter.get(None, 0)))

    wait_buckets = [
        WaitBucketDTO(key="UNDER_WARNING", count=wait_counter.get("UNDER_WARNING", 0)),
        WaitBucketDTO(key="WARNING", count=wait_counter.get("WARNING", 0)),
        WaitBucketDTO(key="CRITICAL", count=wait_counter.get("CRITICAL", 0)),
    ]

    return NurseDashboardDTO(
        generated_at=now.isoformat(),
        waiting=waiting,
        assigned_total=assigned_total,
        assigned_to_me=assigned_to_me,
        parked=parked,
        decided=decided,
        insufficient_live=insufficient_live,
        longest_wait_minutes=longest_wait_minutes,
        esi_distribution=esi_distribution,
        wait_buckets=wait_buckets,
        agreement=AgreementDTO(
            decided_total=decided,
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
    )
