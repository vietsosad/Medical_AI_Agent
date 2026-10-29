"use client";

import { motion } from "framer-motion";
import { CloudOff, RefreshCw } from "lucide-react";
import type { CSSProperties, ReactNode } from "react";

import { AgreementPanel } from "@/components/clinical/nurse-simple/dashboard/AgreementPanel";
import { parseSnapshot, VIZ_TOKEN_CLASSES } from "@/components/clinical/nurse-simple/dashboard/dashboard-model";
import { EsiDistributionPanel } from "@/components/clinical/nurse-simple/dashboard/EsiDistributionPanel";
import { StatTile } from "@/components/clinical/nurse-simple/dashboard/primitives";
import { QueueHeroTile } from "@/components/clinical/nurse-simple/dashboard/QueueHeroTile";
import { ReasonsPanel } from "@/components/clinical/nurse-simple/dashboard/ReasonsPanel";
import { VolumePanel } from "@/components/clinical/nurse-simple/dashboard/VolumePanel";
import { dropVariants, staggerDelay } from "@/lib/motion";
import { cn } from "@/lib/utils";
import { useSimpleNurseDashboard } from "@/queries/useSimpleNurseQueries";
import type { SimpleNurseDashboardDTO } from "@/types/simple-nurse";

/**
 * ============================================================================
 * [TỔNG QUAN TRẠM ĐIỀU PHỐI] BẢNG SỐ LIỆU TRIAGE AGENT
 * ============================================================================
 *
 * QUY TẮC NỘI DUNG. Mọi con số trên màn này là phép ĐẾM trực tiếp trên dữ liệu
 * ca thật, lấy từ `GET /nurse-simple/dashboard` (xem đầu
 * `src/services/simple_nurse_dashboard.py`). Không có chỉ số hiệu năng nào
 * được ước lượng ở đây, và tuyệt đối không đặt thêm nhãn kiểu "độ chính xác
 * của AI": hệ thống không có nhãn chuẩn để đối chiếu, chỉ có quyết định của
 * điều dưỡng. Khối "đồng thuận" vì thế luôn được gọi đúng tên là điều dưỡng
 * đã làm gì với đề xuất, kèm mẫu số đi cùng mọi tỉ lệ.
 *
 * BỐ CỤC. Một con số chính (ca trong hàng đợi, kèm thời gian chờ) dẫn đầu,
 * bốn ô chỉ số, rồi bốn biểu đồ. Phần biểu đồ nằm trong `./dashboard/`.
 *
 * CHUYỂN ĐỘNG. Ô và thẻ nổi lên lần lượt, con số chính đếm lên, vạch mọc từ
 * trục, đường vẽ ra -- tất cả CHỈ một lần khi bảng hiện. Vòng làm mới 30 giây
 * giữ nguyên phần tử (khóa ổn định), nên chỉ những số thật sự đổi mới trượt
 * sang giá trị mới và sáng lên trong chốc lát.
 */

/** Nhịp làm mới ghi trên màn; phải khớp `DASHBOARD_POLL_MS` trong useSimpleNurseQueries.ts. */
const POLL_SECONDS = 30;

export function SimpleNurseDashboard() {
  const { data, isLoading, isError, error, refetch, isFetching } = useSimpleNurseDashboard();
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
    body = <DashboardBody data={data} />;
  }

  return (
    <div className={cn("flex flex-col gap-6", VIZ_TOKEN_CLASSES)}>
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

function DashboardBody({ data }: { data: SimpleNurseDashboardDTO }) {
  const tiles = [
    {
      id: "mine",
      label: "Bạn phụ trách",
      value: data.assigned_to_me,
      hint: `Cả kíp đang giữ ${data.assigned_total} ca`,
    },
    {
      id: "parked",
      label: "Tạm gác",
      value: data.parked,
      hint: "Chờ bổ sung thông tin trước khi xử lý tiếp",
    },
    {
      id: "decided",
      label: "Đã chốt",
      value: data.decided,
      hint: "Tổng số ca đã có quyết định phân luồng cuối cùng",
    },
    {
      id: "insufficient",
      label: "Thiếu dữ liệu kết luận",
      value: data.insufficient_live,
      hint: "Ca đang mở mà agent dừng lại thay vì đoán một mức ESI",
    },
  ];

  return (
    <>
      <div className="grid grid-cols-2 gap-4 md:grid-cols-4 lg:grid-cols-2 xl:grid-cols-[minmax(0,1.25fr)_minmax(0,1fr)_minmax(0,1fr)]">
        <QueueHeroTile dashboard={data} />
        {tiles.map(({ id, ...tile }, index) => (
          <StatTile key={id} id={`tile-${id}`} order={index + 1} {...tile} />
        ))}
      </div>

      <div className="grid gap-4 xl:grid-cols-2">
        <EsiDistributionPanel buckets={data.esi_distribution} order={5} />
        <AgreementPanel agreement={data.agreement} order={6} />
      </div>

      <div className="grid gap-4 xl:grid-cols-[minmax(0,1.4fr)_minmax(0,1fr)]">
        <VolumePanel points={data.daily_volume} order={6} />
        <ReasonsPanel reasons={data.reason_codes} order={6} />
      </div>
    </>
  );
}

// ============================================================================
// ĐANG TẢI / LỖI
// ============================================================================

/** Khung chờ cùng hình dạng với bảng thật, để lúc số liệu về không có cú nhảy bố cục. */
function DashboardSkeleton() {
  return (
    <div className="flex flex-col gap-6" aria-busy="true">
      <span role="status" className="sr-only">
        Đang tải số liệu tổng quan
      </span>
      <div className="grid grid-cols-2 gap-4 md:grid-cols-4 lg:grid-cols-2 xl:grid-cols-[minmax(0,1.25fr)_minmax(0,1fr)_minmax(0,1fr)]">
        <SkeletonBlock
          order={0}
          className="col-span-2 h-64 md:col-span-4 lg:col-span-2 xl:col-span-1 xl:row-span-2 xl:h-auto"
        />
        {["mine", "parked", "decided", "insufficient"].map((id, index) => (
          <SkeletonBlock key={id} order={index + 1} className="h-36" />
        ))}
      </div>
      <div className="grid gap-4 xl:grid-cols-2">
        <SkeletonBlock order={5} className="h-80" />
        <SkeletonBlock order={6} className="h-80" />
      </div>
      <div className="grid gap-4 xl:grid-cols-[minmax(0,1.4fr)_minmax(0,1fr)]">
        <SkeletonBlock order={6} className="h-96" />
        <SkeletonBlock order={6} className="h-96" />
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
