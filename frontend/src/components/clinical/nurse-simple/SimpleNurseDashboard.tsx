"use client";

import { motion } from "framer-motion";
import { CloudOff, FileQuestion, RefreshCw, ShieldAlert, Stethoscope, Timer } from "lucide-react";
import { useState, type CSSProperties, type ReactNode } from "react";

import { AgreementPanel } from "@/components/clinical/nurse-simple/dashboard/AgreementPanel";
import { CaseFlowPanel } from "@/components/clinical/nurse-simple/dashboard/CaseFlowPanel";
import { ClaimTimePanel } from "@/components/clinical/nurse-simple/dashboard/ClaimTimePanel";
import { DecisionMatrixPanel } from "@/components/clinical/nurse-simple/dashboard/DecisionMatrixPanel";
import { DecisionWaitPanel } from "@/components/clinical/nurse-simple/dashboard/DecisionWaitPanel";
import {
  DASHBOARD_WINDOWS,
  DEFAULT_DASHBOARD_WINDOW,
  formatCount,
  parseSnapshot,
  VIZ_TOKEN_CLASSES,
} from "@/components/clinical/nurse-simple/dashboard/dashboard-model";
import { EsiWaitMatrix } from "@/components/clinical/nurse-simple/dashboard/EsiWaitMatrix";
import { HourProfilePanel } from "@/components/clinical/nurse-simple/dashboard/HourProfilePanel";
import { KpiTile } from "@/components/clinical/nurse-simple/dashboard/KpiTile";
import { PriorityCasesPanel } from "@/components/clinical/nurse-simple/dashboard/PriorityCasesPanel";
import { SectionHeading, SegmentedSwitch } from "@/components/clinical/nurse-simple/dashboard/primitives";
import { QueueHeroTile } from "@/components/clinical/nurse-simple/dashboard/QueueHeroTile";
import { ReasonsPanel } from "@/components/clinical/nurse-simple/dashboard/ReasonsPanel";
import { VolumePanel } from "@/components/clinical/nurse-simple/dashboard/VolumePanel";
import { WeekdayHourPanel } from "@/components/clinical/nurse-simple/dashboard/WeekdayHourPanel";
import { dropVariants, staggerDelay } from "@/lib/motion";
import { cn } from "@/lib/utils";
import { useSimpleNurseDashboard } from "@/queries/useSimpleNurseQueries";
import type { SimpleDashboardWindow, SimpleHourPointDTO, SimpleNurseDashboardDTO } from "@/types/simple-nurse";

/**
 * ============================================================================
 * [TỔNG QUAN TRẠM ĐIỀU PHỐI] BẢNG SỐ LIỆU TRIAGE AGENT
 * ============================================================================
 *
 * Màn đầu tiên điều dưỡng thấy sau khi đăng nhập (xem `nurseHomeHref`).
 *
 * QUY TẮC NỘI DUNG. Mọi con số trên màn này là phép ĐẾM trực tiếp trên dữ liệu
 * ca thật, lấy từ `GET /nurse-simple/dashboard` (xem đầu
 * `src/services/simple_nurse_dashboard.py`) và, riêng danh sách ca ưu tiên,
 * từ chính `GET /nurse-simple/queue`. Không có chỉ số hiệu năng nào được ước
 * lượng ở đây, và tuyệt đối không đặt thêm nhãn kiểu "độ chính xác của AI":
 * hệ thống không có nhãn chuẩn để đối chiếu, chỉ có quyết định của điều dưỡng.
 *
 * BỐ CỤC. Hai khu vực, đọc từ trên xuống theo thứ tự ra quyết định:
 * 1. "Ngay lúc này" -- ảnh chụp hàng đợi: con số chính, ma trận mức khẩn ×
 *    thời gian chờ, ca cần người nhận trước, bốn ô chỉ số, luồng xử lý ca.
 *    Không phụ thuộc khoảng thời gian.
 * 2. "Diễn biến N ngày qua" -- MỘT hàng chọn khoảng thời gian nằm ngay trên
 *    mọi biểu đồ mà nó áp dụng: khối lượng theo ngày, giờ trong ngày, quyết
 *    định của điều dưỡng, lý do chốt ca; rồi bốn khối chất lượng và xu hướng:
 *    ma trận mức AI × mức điều dưỡng chốt, thời gian từ lúc gắn cờ tới khi có
 *    người nhận, trung vị chờ tới khi được chốt theo mức, và thứ × giờ (giờ
 *    Việt Nam). Mốc 30/60 phút trên các khối đó là mốc tô màu của bảng ca,
 *    không phải chỉ tiêu: hệ thống chưa có chỉ tiêu thời gian nào.
 *
 * CHUYỂN ĐỘNG. Thẻ nổi lên lần lượt, con số chính đếm lên, ô ma trận hiện dần
 * theo đường chéo từ góc khẩn nhất, cột mọc từ đáy, đường vẽ ra -- tất cả chỉ
 * một lần khi bảng hiện. Vòng làm mới 30 giây giữ nguyên phần tử nên chỉ số
 * thật sự đổi mới trượt sang giá trị mới và sáng lên; bước nào trong luồng ca
 * vừa có thêm ca thì một chấm chạy vào bước đó. Đổi khoảng thời gian thì phần
 * lịch sử mờ đi trong lúc chờ số mới, không khung chờ, không nhảy bố cục.
 */

/** Nhịp làm mới ghi trên màn; phải khớp `DASHBOARD_POLL_MS` trong useSimpleNurseQueries.ts. */
const POLL_SECONDS = 30;

export function SimpleNurseDashboard() {
  const [days, setDays] = useState<SimpleDashboardWindow>(DEFAULT_DASHBOARD_WINDOW);
  const { data, isLoading, isError, error, refetch, isFetching, isPlaceholderData } = useSimpleNurseDashboard({
    days,
  });
  const ready = !isLoading && !isError && data !== undefined;

  let body: ReactNode;
  if (isLoading) {
    body = <DashboardSkeleton />;
  } else if (isError || !data) {
    // Cố ý không hiện số cũ khi lần tải gần nhất hỏng: một con số lỗi thời
    // trên bảng lâm sàng nguy hiểm hơn là không có số.
    body = (
      <DashboardError
        message={error instanceof Error ? error.message : "Vui lòng thử lại."}
        isFetching={isFetching}
        onRetry={() => void refetch()}
      />
    );
  } else {
    body = (
      <DashboardBody
        data={data}
        days={days}
        onDaysChange={setDays}
        historyPending={Boolean(isPlaceholderData)}
      />
    );
  }

  return (
    // `data-wide-layout`: khung trang lâm sàng nới rộng cho riêng bảng này
    // (xem app/clinical/layout.tsx) -- nhiều biểu đồ cần chiều ngang màn rộng.
    <div data-wide-layout className={cn("flex flex-col gap-8", VIZ_TOKEN_CLASSES)}>
      <header className="page-enter flex flex-wrap items-end justify-between gap-4">
        <div className="min-w-0">
          <h1 className="text-2xl font-extrabold tracking-tight text-foreground sm:text-3xl">Tổng quan trạm điều phối</h1>
          <p className="mt-2 max-w-2xl text-sm leading-6 text-muted-foreground sm:text-base">
            Mọi con số là phép đếm trực tiếp trên ca, cùng tập dữ liệu với bảng hàng đợi, không phải ước lượng.
          </p>
        </div>
        {ready ? (
          <div className="flex flex-wrap items-center gap-4">
            <p className="flex items-center gap-2 text-sm font-medium leading-6 text-muted-foreground">
              <span aria-hidden="true" className="live-dot size-2 shrink-0 rounded-full bg-emerald-500" />
              <span>
                Cập nhật <SnapshotTime iso={data.generated_at} /> · tự làm mới mỗi {POLL_SECONDS} giây
              </span>
            </p>
            <motion.button
              type="button"
              whileTap={{ scale: 0.97 }}
              onClick={() => void refetch()}
              disabled={isFetching}
              className="inline-flex min-h-11 items-center gap-2 rounded-xl border border-border bg-card px-4 text-sm font-semibold text-foreground shadow-xs outline-hidden transition-colors duration-200 hover:bg-muted focus-visible:ring-2 focus-visible:ring-brand focus-visible:ring-offset-2 focus-visible:ring-offset-background disabled:cursor-wait disabled:opacity-60"
            >
              <RefreshCw
                className={cn("size-4", isFetching && "animate-spin motion-reduce:animate-none")}
                aria-hidden="true"
              />
              Tải lại
            </motion.button>
          </div>
        ) : null}
      </header>

      {body}
    </div>
  );
}

/**
 * Giờ chụp số liệu theo giờ máy người xem; ngày kèm theo để không nhầm bảng cũ.
 * Tự ghép "dd/mm" thay vì nhờ Intl: bản vi-VN của trình duyệt có nơi in "29-10".
 */
function SnapshotTime({ iso }: { iso: string }) {
  const parsed = parseSnapshot(iso);
  if (!parsed) return <span>—</span>;
  const pad = (value: number) => String(value).padStart(2, "0");
  const time = `${pad(parsed.getHours())}:${pad(parsed.getMinutes())}`;
  const day = `${pad(parsed.getDate())}/${pad(parsed.getMonth() + 1)}`;
  return (
    <time dateTime={parsed.toISOString()} className="font-semibold text-foreground">
      {time} ngày {day}
    </time>
  );
}

// ============================================================================
// NỘI DUNG
// ============================================================================

function sumRecent(points: readonly SimpleHourPointDTO[], key: "completed" | "decided"): number {
  return points.reduce((sum, point) => sum + point[key], 0);
}

const WINDOW_OPTIONS = DASHBOARD_WINDOWS.map((value) => ({ value, label: `${value} ngày` }));

function DashboardBody({
  data,
  days,
  onDaysChange,
  historyPending,
}: {
  data: SimpleNurseDashboardDTO;
  days: SimpleDashboardWindow;
  onDaysChange: (next: SimpleDashboardWindow) => void;
  /** Đang chờ số của khoảng thời gian vừa chọn; phần lịch sử còn là số của khoảng cũ. */
  historyPending: boolean;
}) {
  const completed24h = sumRecent(data.recent_hours, "completed");
  const decided24h = sumRecent(data.recent_hours, "decided");
  const inProgress = data.in_progress_live;

  return (
    <>
      <section aria-labelledby="dashboard-now-title" className="flex flex-col gap-4">
        <SectionHeading
          id="dashboard-now-title"
          title="Ngay lúc này"
          description="Ảnh chụp hàng đợi lúc cập nhật, không phụ thuộc khoảng thời gian ở phần dưới."
        />

        <div className="grid gap-4 xl:grid-cols-[minmax(0,5fr)_minmax(0,7fr)]">
          <QueueHeroTile dashboard={data} />
          <EsiWaitMatrix dashboard={data} order={1} />
        </div>

        <div className="grid gap-4 xl:grid-cols-[minmax(0,7fr)_minmax(0,5fr)]">
          <PriorityCasesPanel order={2} />
          <div className="grid grid-cols-2 content-start gap-4">
            <KpiTile
              id="kpi-attention"
              order={3}
              label="Cần xem ngay"
              value={data.attention_live}
              tone="critical"
              icon={ShieldAlert}
              hint={
                data.attention_live === 0
                  ? "Bộ lọc khẩn cấp chưa gắn cờ ca nào đang mở"
                  : inProgress > 0
                    ? `Bộ lọc khẩn cấp đã gắn cờ; ${formatCount(inProgress)} phiên còn đang sàng lọc`
                    : "Bộ lọc khẩn cấp đã gắn cờ trước khi AI trả lời"
              }
            />
            <KpiTile
              id="kpi-insufficient"
              order={4}
              label="Thiếu dữ liệu kết luận"
              value={data.insufficient_live}
              icon={FileQuestion}
              hint="Ca đang mở mà agent dừng lại thay vì đoán một mức ESI"
            />
            <KpiTile
              id="kpi-completed"
              order={5}
              label="Phiên kết thúc trong 24 giờ"
              value={completed24h}
              icon={Timer}
              hint="Người bệnh hoàn tất sàng lọc"
              trend={{ points: data.recent_hours, series: "completed", unit: "phiên" }}
            />
            <KpiTile
              id="kpi-decided"
              order={6}
              label="Ca được chốt trong 24 giờ"
              value={decided24h}
              icon={Stethoscope}
              hint="Điều dưỡng đã ra quyết định phân luồng"
              trend={{ points: data.recent_hours, series: "decided", unit: "ca" }}
            />
          </div>
        </div>

        <CaseFlowPanel dashboard={data} decidedLast24h={decided24h} order={6} />
      </section>

      <section aria-labelledby="dashboard-history-title" aria-busy={historyPending} className="flex flex-col gap-4">
        <SectionHeading
          id="dashboard-history-title"
          title={`Diễn biến ${data.window_days} ngày qua`}
          description={`${formatCount(data.completed_in_window)} phiên sàng lọc kết thúc, ${formatCount(data.decided_in_window)} ca được chốt. Khoảng thời gian áp dụng cho mọi biểu đồ bên dưới.`}
        />
        <SegmentedSwitch id="history-window" label="Khoảng thời gian" value={days} options={WINDOW_OPTIONS} onChange={onDaysChange} />

        <div
          className={cn(
            "flex flex-col gap-4 transition-opacity duration-200 motion-reduce:transition-none",
            historyPending && "opacity-60",
          )}
        >
          <div className="grid gap-4 xl:grid-cols-[minmax(0,7fr)_minmax(0,5fr)]">
            <VolumePanel points={data.daily_volume} order={6} />
            <HourProfilePanel points={data.hour_of_day} windowDays={data.window_days} order={6} />
          </div>
          <div className="grid gap-4 xl:grid-cols-2">
            <AgreementPanel agreement={data.agreement} windowDays={data.window_days} order={6} />
            <ReasonsPanel reasons={data.reason_codes} windowDays={data.window_days} order={6} />
          </div>
          {/* Bốn khối chất lượng và xu hướng là trường cộng thêm: máy chủ chưa có thì bỏ khung đó. */}
          {data.decision_matrix || data.flagged_claim ? (
            <div className="grid gap-4 xl:grid-cols-[minmax(0,7fr)_minmax(0,5fr)]">
              {data.decision_matrix ? (
                <DecisionMatrixPanel matrix={data.decision_matrix} windowDays={data.window_days} order={6} />
              ) : null}
              {data.flagged_claim ? (
                <ClaimTimePanel claim={data.flagged_claim} windowDays={data.window_days} order={6} />
              ) : null}
            </div>
          ) : null}
          {data.decision_wait || data.weekday_hour ? (
            <div className="grid gap-4 xl:grid-cols-[minmax(0,5fr)_minmax(0,7fr)]">
              {data.decision_wait ? (
                <DecisionWaitPanel wait={data.decision_wait} windowDays={data.window_days} order={6} />
              ) : null}
              {data.weekday_hour ? (
                <WeekdayHourPanel panel={data.weekday_hour} windowDays={data.window_days} order={6} />
              ) : null}
            </div>
          ) : null}
        </div>
      </section>
    </>
  );
}

// ============================================================================
// ĐANG TẢI / LỖI
// ============================================================================

/** Khung chờ cùng hình dạng với bảng thật, để lúc số liệu về không có cú nhảy bố cục. */
function DashboardSkeleton() {
  return (
    <div className="flex flex-col gap-8" aria-busy="true">
      <span role="status" className="sr-only">
        Đang tải số liệu tổng quan
      </span>
      <div className="flex flex-col gap-4">
        <SkeletonBlock order={0} className="h-12 w-64 max-w-full" />
        <div className="grid gap-4 xl:grid-cols-[minmax(0,5fr)_minmax(0,7fr)]">
          <SkeletonBlock order={0} className="h-80" />
          <SkeletonBlock order={1} className="h-80" />
        </div>
        <div className="grid gap-4 xl:grid-cols-[minmax(0,7fr)_minmax(0,5fr)]">
          <SkeletonBlock order={2} className="h-96" />
          <div className="grid grid-cols-2 gap-4">
            {["attention", "insufficient", "completed", "decided"].map((id, index) => (
              <SkeletonBlock key={id} order={index + 3} className="h-44" />
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}

function SkeletonBlock({ order, className }: { order: number; className?: string }) {
  return (
    <div
      aria-hidden="true"
      style={{ "--rise-delay": `${Math.round(staggerDelay(order) * 1000)}ms` } as CSSProperties}
      className={cn("rise-in skeleton-sweep relative overflow-hidden rounded-2xl border border-border bg-card", className)}
    />
  );
}

function DashboardError({
  message,
  isFetching,
  onRetry,
}: {
  message: string;
  isFetching: boolean;
  onRetry: () => void;
}) {
  return (
    <motion.div
      role="alert"
      variants={dropVariants}
      initial="hidden"
      animate="visible"
      className="mx-auto w-full max-w-xl rounded-2xl border border-rose-200 bg-rose-50 p-6 text-center dark:border-rose-900/60 dark:bg-rose-950/40"
    >
      <span className="mx-auto flex size-12 items-center justify-center rounded-2xl bg-rose-100 text-rose-700 dark:bg-rose-900/50 dark:text-rose-300">
        <CloudOff className="size-6" aria-hidden="true" />
      </span>
      <h2 className="mt-4 text-base font-bold leading-6 text-rose-900 dark:text-rose-100">
        Không tải được số liệu tổng quan.
      </h2>
      <p className="mt-2 text-sm leading-6 text-rose-800 dark:text-rose-200">{message}</p>
      <p className="mt-2 text-sm leading-6 text-rose-800 dark:text-rose-200">
        Số liệu cũ được ẩn đi để không ai đọc nhầm một con số đã lỗi thời.
      </p>
      <motion.button
        type="button"
        whileTap={{ scale: 0.97 }}
        onClick={onRetry}
        disabled={isFetching}
        className="mt-6 inline-flex min-h-11 items-center gap-2 rounded-xl border border-rose-300 bg-card px-4 text-sm font-semibold text-rose-900 shadow-xs outline-hidden transition-colors duration-200 hover:bg-rose-100 focus-visible:ring-2 focus-visible:ring-rose-600 focus-visible:ring-offset-2 focus-visible:ring-offset-rose-50 disabled:cursor-wait disabled:opacity-60 dark:border-rose-800 dark:text-rose-100 dark:hover:bg-rose-900/40 dark:focus-visible:ring-offset-rose-950"
      >
        <RefreshCw
          className={cn("size-4", isFetching && "animate-spin motion-reduce:animate-none")}
          aria-hidden="true"
        />
        Thử tải lại
      </motion.button>
    </motion.div>
  );
}

export default SimpleNurseDashboard;
