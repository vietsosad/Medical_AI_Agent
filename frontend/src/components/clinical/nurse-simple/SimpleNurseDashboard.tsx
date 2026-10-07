"use client";

import {
  AlertCircle,
  Archive,
  CheckCircle2,
  ClipboardList,
  Clock3,
  Inbox,
  RefreshCw,
  TrendingUp,
  UserRoundCheck,
} from "lucide-react";

import { ESI_THEME, ESI_UNKNOWN } from "@/components/clinical/nurse-simple/esi-theme";
import { formatWait } from "@/components/clinical/nurse-simple/wait-time";
import { useSimpleNurseDashboard } from "@/queries/useSimpleNurseQueries";
import { cn } from "@/lib/utils";
import type {
  SimpleAgreementDTO,
  SimpleDailyPointDTO,
  SimpleEsiBucketDTO,
  SimpleNurseDashboardDTO,
  SimpleWaitBucketKey,
} from "@/types/simple-nurse";

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
 * NGÔN NGỮ THỊ GIÁC. Chiều dài cột đã mang thông tin số lượng, nên các cột
 * dùng CHUNG MỘT MÀU: màu không được phép gánh thêm việc phân biệt mức ESI ở
 * kích thước này (bước đậm của cam ESI 2 và hổ phách ESI 3 gần như không tách
 * được với người rối loạn sắc giác). Mức độ vẫn đọc bằng đúng con chip màu mà
 * bảng ca đang dùng, và chip luôn đi kèm chữ.
 */

// Mã lý do do backend kiểm định (`_REASON_CODES` trong routes_nurse_simple.py);
// nhãn hiển thị bám theo đúng chữ trong SimpleDecisionForm.tsx.
const REASON_LABELS: Record<string, string> = {
  MATCHES_PROTOCOL: "Dữ liệu phù hợp với phác đồ đã tham chiếu",
  ADDITIONAL_CLINICAL_JUDGMENT: "Nhận định lâm sàng bổ sung",
  INSUFFICIENT_PATIENT_DATA: "Dữ liệu bệnh nhân cung cấp chưa đủ",
  OTHER: "Lý do khác (ghi rõ trong ghi chú)",
};

const WAIT_BUCKET_META: Record<
  SimpleWaitBucketKey,
  { label: string; fill: string; swatch: string }
> = {
  UNDER_WARNING: { label: "Dưới 30 phút", fill: "bg-slate-500", swatch: "bg-slate-500" },
  WARNING: { label: "30 – 60 phút", fill: "bg-amber-600", swatch: "bg-amber-600" },
  CRITICAL: { label: "Trên 60 phút", fill: "bg-rose-600", swatch: "bg-rose-600" },
};

function formatTimestamp(iso: string): string {
  const parsed = new Date(`${iso}Z`);
  if (Number.isNaN(parsed.getTime())) return "—";
  return parsed.toLocaleString("vi-VN", { day: "2-digit", month: "2-digit", hour: "2-digit", minute: "2-digit" });
}

function percent(part: number, whole: number): string {
  if (whole <= 0) return "—";
  return `${Math.round((part / whole) * 100)}%`;
}

// ============================================================================
// MẢNH GHÉP
// ============================================================================

/** Ô chỉ số. Một con số hiện tại thì đọc bằng chữ số, không cần vẽ biểu đồ. */
function StatTile({
  icon: Icon,
  label,
  value,
  hint,
  tone = "neutral",
}: {
  icon: React.ComponentType<{ className?: string }>;
  label: string;
  value: string | number;
  hint?: string;
  tone?: "neutral" | "active" | "warning" | "critical";
}) {
  const tones = {
    neutral: { box: "border-border bg-card glow-sky", icon: "bg-muted text-slate-600 dark:text-slate-300", value: "text-slate-950 dark:text-slate-50" },
    active: { box: "border-sky-200 bg-sky-50/60 glow-sky", icon: "bg-sky-100 text-sky-700", value: "text-sky-900" },
    warning: { box: "border-amber-200 bg-amber-50/70 glow-rose", icon: "bg-amber-100 text-amber-700", value: "text-amber-900" },
    critical: { box: "border-rose-200 bg-rose-50/70 glow-rose", icon: "bg-rose-100 text-rose-700", value: "text-rose-900" },
  }[tone];

  return (
    <div className={cn("group/tile glow-soft rounded-xl border p-4", tones.box)}>
      <div className="flex items-start gap-3.5">
        <span
          className={cn(
            "flex size-11 shrink-0 items-center justify-center rounded-xl transition-transform duration-300 ease-out group-hover/tile:scale-105 motion-reduce:group-hover/tile:scale-100",
            tones.icon,
          )}
        >
          <Icon className="size-5" aria-hidden="true" />
        </span>
        <div className="min-w-0">
          <p className="text-xs font-bold uppercase tracking-wide text-muted-foreground">{label}</p>
          <p className={cn("mt-1 text-3xl font-black leading-none tabular-nums", tones.value)}>{value}</p>
          {hint && <p className="mt-1.5 text-xs font-medium leading-5 text-muted-foreground">{hint}</p>}
        </div>
      </div>
    </div>
  );
}

/** Khối nội dung có tiêu đề, dùng chung ngôn ngữ với màn thẩm định ca. */
function Panel({
  icon: Icon,
  title,
  subtitle,
  order = 0,
  children,
}: {
  icon: React.ComponentType<{ className?: string }>;
  title: string;
  subtitle?: string;
  order?: number;
  children: React.ReactNode;
}) {
  return (
    <section
      style={{ "--rise-delay": `${order * 80}ms` } as React.CSSProperties}
      className="group/panel glow-soft glow-sky rise-in overflow-hidden rounded-2xl border border-border bg-card shadow-xs"
    >
      <header className="flex items-start gap-3 border-b border-slate-100 bg-background/70 px-4 py-3.5 sm:px-5">
        <span className="flex size-9 shrink-0 items-center justify-center rounded-xl bg-card text-sky-700 shadow-xs transition-[background-color,color] duration-300 group-hover/panel:bg-sky-700 group-hover/panel:text-white">
          <Icon className="size-4.5" aria-hidden="true" />
        </span>
        <div className="min-w-0">
          <h2 className="text-base font-bold text-slate-950 dark:text-slate-50">{title}</h2>
          {subtitle && <p className="mt-0.5 text-sm leading-5 text-slate-600 dark:text-slate-300">{subtitle}</p>}
        </div>
      </header>
      <div className="p-4 sm:p-5">{children}</div>
    </section>
  );
}

/**
 * Một vạch trong biểu đồ cột ngang. Đầu cột bo 4px và luôn neo vào mép trái,
 * nên mắt so sánh được độ dài mà không bị đầu bo đánh lừa.
 */
function BarRow({
  chip,
  chipLabel,
  name,
  count,
  max,
  total,
}: {
  chip: string;
  chipLabel: string;
  name: string;
  count: number;
  max: number;
  total: number;
}) {
  const width = max > 0 ? Math.max(count > 0 ? 2 : 0, (count / max) * 100) : 0;
  return (
    <div
      className="group/bar grid grid-cols-[7.5rem_minmax(0,1fr)_4.5rem] items-center gap-3 rounded-lg px-1 py-1.5 transition-colors hover:bg-sky-50/60"
      title={`${chipLabel} · ${name}: ${count} ca trên tổng ${total}`}
    >
      <span
        className={cn(
          "inline-flex min-h-7 w-fit items-center rounded-lg border px-2 text-xs font-black tabular-nums tracking-tight",
          chip,
        )}
      >
        {chipLabel}
      </span>
      <div className="flex min-w-0 items-center gap-2.5">
        <div className="h-5 min-w-0 flex-1 overflow-hidden rounded-[4px] bg-muted">
          <div
            className="h-full rounded-[4px] bg-sky-700 transition-[width] duration-500 ease-out motion-reduce:transition-none"
            style={{ width: `${width}%` }}
          />
        </div>
      </div>
      <div className="flex items-baseline justify-end gap-1.5">
        <span className="text-sm font-black tabular-nums text-slate-950 dark:text-slate-50">{count}</span>
        <span className="text-xs font-medium tabular-nums text-muted-foreground">{percent(count, total)}</span>
      </div>
    </div>
  );
}

/** Thanh phần-trên-tổng: các đoạn cách nhau 2px để mắt tách được ranh giới. */
function SegmentedBar({
  segments,
  total,
}: {
  segments: { key: string; label: string; count: number; fill: string }[];
  total: number;
}) {
  const shown = segments.filter((segment) => segment.count > 0);
  return (
    <div>
      <div className="flex h-7 w-full gap-0.5 overflow-hidden rounded-[4px] bg-muted">
        {shown.map((segment) => (
          <div
            key={segment.key}
            title={`${segment.label}: ${segment.count} / ${total}`}
            style={{ width: `${(segment.count / total) * 100}%` }}
            className={cn("h-full first:rounded-l-[4px] last:rounded-r-[4px]", segment.fill)}
          />
        ))}
      </div>
      <ul className="mt-3 flex flex-wrap gap-x-5 gap-y-2">
        {segments.map((segment) => (
          <li key={segment.key} className="flex items-center gap-2 text-sm">
            <span className={cn("size-2.5 shrink-0 rounded-[3px]", segment.fill)} aria-hidden="true" />
            <span className="font-medium text-slate-700 dark:text-slate-200">{segment.label}</span>
            <span className="font-black tabular-nums text-slate-950 dark:text-slate-50">{segment.count}</span>
            <span className="text-xs font-medium tabular-nums text-muted-foreground">
              {percent(segment.count, total)}
            </span>
          </li>
        ))}
      </ul>
    </div>
  );
}

function EmptyNote({ children }: { children: React.ReactNode }) {
  return (
    <p className="rounded-xl border border-dashed border-slate-300 bg-background/70 p-4 text-sm leading-6 text-slate-600 dark:text-slate-300 dark:border-slate-700">
      {children}
    </p>
  );
}

// ============================================================================
// CÁC KHỐI SỐ LIỆU
// ============================================================================

function EsiPanel({ buckets }: { buckets: SimpleEsiBucketDTO[] }) {
  const total = buckets.reduce((sum, bucket) => sum + bucket.count, 0);
  const max = buckets.reduce((peak, bucket) => Math.max(peak, bucket.count), 0);

  return (
    <Panel
      icon={ClipboardList}
      order={1}
      title="Mức độ AI đề xuất"
      subtitle={`Trên ${total} ca chưa đóng — đang chờ và đang có người phụ trách`}
    >
      {total === 0 ? (
        <EmptyNote>Không có ca nào đang mở. Bảng này sẽ có số ngay khi kíp trực nhận ca mới.</EmptyNote>
      ) : (
        <div className="space-y-0.5">
          {buckets.map((bucket) => {
            const theme = bucket.level === null ? ESI_UNKNOWN : ESI_THEME[bucket.level];
            return (
              <BarRow
                key={bucket.level ?? "unknown"}
                chip={theme.chip}
                chipLabel={bucket.level === null ? "Chưa có" : `ESI ${bucket.level}`}
                name={theme.label}
                count={bucket.count}
                max={max}
                total={total}
              />
            );
          })}
        </div>
      )}
    </Panel>
  );
}

function WaitPanel({ dashboard }: { dashboard: SimpleNurseDashboardDTO }) {
  const total = dashboard.wait_buckets.reduce((sum, bucket) => sum + bucket.count, 0);
  const segments = dashboard.wait_buckets.map((bucket) => ({
    key: bucket.key,
    label: WAIT_BUCKET_META[bucket.key].label,
    count: bucket.count,
    fill: WAIT_BUCKET_META[bucket.key].fill,
  }));

  return (
    <Panel
      icon={Clock3}
      order={2}
      title="Thời gian chờ tiếp nhận"
      subtitle="Chia đúng hai mốc cảnh báo mà bảng ca đang dùng"
    >
      {total === 0 ? (
        <EmptyNote>Chưa có ca nào đang mở để tính thời gian chờ.</EmptyNote>
      ) : (
        <SegmentedBar segments={segments} total={total} />
      )}
    </Panel>
  );
}

function AgreementPanel({ agreement }: { agreement: SimpleAgreementDTO }) {
  const total = agreement.decided_total;
  // Thứ tự cố ý: khẩn hơn — giữ nguyên — ít khẩn hơn. Đây là một thang phân
  // cực quanh mốc "giữ nguyên", nên mốc giữa mang màu xám trung tính còn hai
  // đầu mang hai màu đối nhau, không phải ba màu rời rạc.
  const segments = [
    { key: "escalated", label: "Chốt khẩn hơn AI", count: agreement.escalated, fill: "bg-rose-600" },
    { key: "confirmed", label: "Giữ nguyên mức AI", count: agreement.confirmed, fill: "bg-slate-500" },
    { key: "de_escalated", label: "Chốt ít khẩn hơn AI", count: agreement.de_escalated, fill: "bg-sky-600" },
    {
      key: "without",
      label: "Tự chốt khi AI chưa đề xuất",
      count: agreement.adjusted_without_proposal,
      fill: "bg-slate-300",
    },
  ];

  return (
    <Panel
      icon={CheckCircle2}
      order={3}
      title="Điều dưỡng đã làm gì với đề xuất của AI"
      subtitle={`Trên ${total} ca đã chốt`}
    >
      {total === 0 ? (
        <EmptyNote>
          Chưa có ca nào được chốt, nên chưa có gì để đối chiếu. Con số ở đây chỉ ghi lại quyết định
          của điều dưỡng — nó không phải thước đo độ chính xác của AI, vì hệ thống không có kết luận
          chuẩn nào để so.
        </EmptyNote>
      ) : (
        <>
          <SegmentedBar segments={segments} total={total} />
          <p className="mt-4 border-t border-slate-100 pt-3 text-xs leading-5 text-muted-foreground">
            Đây là thống kê quyết định của điều dưỡng, không phải độ chính xác của AI: hệ thống
            không có kết luận chuẩn nào để đối chiếu. Mọi tỉ lệ đều tính trên {total} ca đã chốt.
          </p>
        </>
      )}
    </Panel>
  );
}

function ReasonPanel({ reasons, total }: { reasons: { code: string; count: number }[]; total: number }) {
  return (
    <Panel
      icon={AlertCircle}
      order={4}
      title="Lý do đã chọn khi chốt ca"
      subtitle="Ghi nhận trực tiếp từ biểu mẫu quyết định"
    >
      {reasons.length === 0 ? (
        <EmptyNote>Chưa có ca nào được chốt nên chưa ghi nhận lý do nào.</EmptyNote>
      ) : (
        <table className="w-full text-left text-sm">
          <thead>
            <tr className="border-b border-border">
              <th scope="col" className="pb-2 text-xs font-bold uppercase tracking-wide text-muted-foreground">
                Lý do
              </th>
              <th scope="col" className="pb-2 text-right text-xs font-bold uppercase tracking-wide text-muted-foreground">
                Số ca
              </th>
              <th scope="col" className="pb-2 text-right text-xs font-bold uppercase tracking-wide text-muted-foreground">
                Tỉ lệ
              </th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100">
            {reasons.map((reason) => (
              <tr key={reason.code} className="transition-colors hover:bg-sky-50/60">
                <td className="py-2.5 pr-3 leading-6 text-slate-800 dark:text-slate-100">
                  {REASON_LABELS[reason.code] ?? reason.code}
                </td>
                <td className="py-2.5 text-right font-black tabular-nums text-slate-950 dark:text-slate-50">{reason.count}</td>
                <td className="py-2.5 text-right tabular-nums text-muted-foreground">
                  {percent(reason.count, total)}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </Panel>
  );
}

/**
 * Khối lượng 14 ngày. Hai chuỗi cùng đơn vị ("số ca") nên nằm chung một trục —
 * không bao giờ dựng hai trục tung cho hai thang khác nhau.
 */
function VolumePanel({ points }: { points: SimpleDailyPointDTO[] }) {
  const max = points.reduce((peak, point) => Math.max(peak, point.completed, point.decided), 0);
  const totalCompleted = points.reduce((sum, point) => sum + point.completed, 0);
  const totalDecided = points.reduce((sum, point) => sum + point.decided, 0);
  const first = points[0]?.date;
  const last = points[points.length - 1]?.date;

  const range =
    first && last
      ? `${first.slice(8, 10)}/${first.slice(5, 7)} – ${last.slice(8, 10)}/${last.slice(5, 7)}`
      : "";

  return (
    <Panel
      icon={TrendingUp}
      order={5}
      title="Khối lượng 14 ngày gần nhất"
      subtitle={`${range} · ${totalCompleted} phiên sàng lọc kết thúc, ${totalDecided} ca được chốt`}
    >
      {max === 0 ? (
        <EmptyNote>Chưa có phiên nào kết thúc trong 14 ngày qua.</EmptyNote>
      ) : (
        <>
          <div className="flex h-40 items-end gap-1.5" role="img" aria-label={`Khối lượng theo ngày, ${range}`}>
            {points.map((point) => (
              <div key={point.date} className="flex h-full min-w-0 flex-1 flex-col justify-end">
                <div
                  className="flex h-full items-end justify-center gap-0.5"
                  title={`${point.date}: ${point.completed} phiên kết thúc, ${point.decided} ca chốt`}
                >
                  <span
                    className="w-1/2 max-w-2.5 rounded-t-[4px] bg-sky-700 transition-[height] duration-500 ease-out motion-reduce:transition-none"
                    style={{ height: `${point.completed > 0 ? Math.max(3, (point.completed / max) * 100) : 0}%` }}
                  />
                  <span
                    className="w-1/2 max-w-2.5 rounded-t-[4px] bg-emerald-600 transition-[height] duration-500 ease-out motion-reduce:transition-none"
                    style={{ height: `${point.decided > 0 ? Math.max(3, (point.decided / max) * 100) : 0}%` }}
                  />
                </div>
                <span className="mt-1.5 text-center text-[10px] font-medium tabular-nums text-slate-400">
                  {point.date.slice(8, 10)}
                </span>
              </div>
            ))}
          </div>
          <ul className="mt-3 flex flex-wrap gap-x-5 gap-y-2 border-t border-slate-100 pt-3">
            <li className="flex items-center gap-2 text-sm">
              <span className="size-2.5 shrink-0 rounded-[3px] bg-sky-700" aria-hidden="true" />
              <span className="font-medium text-slate-700 dark:text-slate-200">Phiên sàng lọc kết thúc</span>
            </li>
            <li className="flex items-center gap-2 text-sm">
              <span className="size-2.5 shrink-0 rounded-[3px] bg-emerald-600" aria-hidden="true" />
              <span className="font-medium text-slate-700 dark:text-slate-200">Ca được điều dưỡng chốt</span>
            </li>
          </ul>
        </>
      )}
    </Panel>
  );
}

// ============================================================================
// MÀN HÌNH
// ============================================================================

function DashboardSkeleton() {
  return (
    <div className="mx-auto max-w-6xl space-y-5 p-4 sm:p-6">
      <span className="sr-only" role="status">
        Đang tải số liệu tổng quan
      </span>
      <div className="skeleton-sweep relative h-24 overflow-hidden rounded-2xl border border-border bg-card shadow-xs" />
      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
        {[0, 1, 2, 3].map((key) => (
          <div
            key={key}
            style={{ "--rise-delay": `${key * 70}ms` } as React.CSSProperties}
            className="rise-in skeleton-sweep relative h-24 overflow-hidden rounded-xl border border-border bg-card"
          />
        ))}
      </div>
      <div className="grid gap-5 lg:grid-cols-2">
        {[0, 1].map((key) => (
          <div
            key={key}
            style={{ "--rise-delay": `${key * 90}ms` } as React.CSSProperties}
            className="rise-in skeleton-sweep relative h-60 overflow-hidden rounded-2xl border border-border bg-card"
          />
        ))}
      </div>
    </div>
  );
}

export function SimpleNurseDashboard() {
  const { data, isLoading, isError, error, refetch, isFetching } = useSimpleNurseDashboard();

  if (isLoading) return <DashboardSkeleton />;

  if (isError || !data) {
    return (
      <div
        role="alert"
        className="rise-in mx-auto mt-8 max-w-xl rounded-2xl border border-rose-200 bg-rose-50 p-6 text-center"
      >
        <p className="text-sm font-bold text-rose-900">Không tải được số liệu tổng quan.</p>
        <p className="mt-2 text-sm leading-6 text-rose-800">
          {error instanceof Error ? error.message : "Vui lòng thử lại."}
        </p>
        <button
          type="button"
          onClick={() => void refetch()}
          className="glow-soft glow-sky mt-4 inline-flex min-h-11 items-center gap-2 rounded-xl border border-slate-300 bg-card px-4 text-sm font-bold text-slate-800 hover:bg-muted focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-sky-600 focus-visible:ring-offset-2 dark:text-slate-100 dark:border-slate-700"
        >
          <RefreshCw className={cn("size-4", isFetching && "animate-spin")} aria-hidden="true" />
          Thử tải lại
        </button>
      </div>
    );
  }

  const liveTotal = data.waiting + data.assigned_total;

  return (
    <div className="mx-auto max-w-6xl space-y-5 p-4 sm:p-6">
      {/* ------------------------------------------------------ ĐẦU BẢNG */}
      <header className="glow-soft glow-sky rise-in overflow-hidden rounded-2xl border border-border bg-card shadow-xs">
        <div className="flex flex-wrap items-center justify-between gap-4 border-b border-slate-100 bg-gradient-to-r from-slate-50 to-white p-5">
          <div className="flex min-w-0 items-center gap-2.5">
            <span className="flex size-10 shrink-0 items-center justify-center rounded-xl bg-sky-700 text-white">
              <TrendingUp className="size-5" aria-hidden="true" />
            </span>
            <div className="min-w-0">
              <h1 className="truncate text-xl font-bold tracking-tight text-slate-950 dark:text-slate-50">
                Tổng quan trạm điều phối
              </h1>
              <p className="mt-0.5 text-sm text-slate-600 dark:text-slate-300">
                Số liệu chụp lúc {formatTimestamp(data.generated_at)}
              </p>
            </div>
          </div>

          <button
            type="button"
            onClick={() => void refetch()}
            disabled={isFetching}
            className="glow-soft glow-sky flex min-h-11 shrink-0 items-center gap-2 rounded-xl border border-slate-300 bg-card px-4 text-sm font-semibold text-slate-800 hover:bg-muted disabled:opacity-60 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-sky-600 focus-visible:ring-offset-2 dark:text-slate-100 dark:border-slate-700"
          >
            <RefreshCw className={cn("size-4", isFetching && "animate-spin")} aria-hidden="true" />
            Tải lại
          </button>
        </div>

        <p className="px-5 py-2.5 text-sm font-medium leading-6 text-slate-600 dark:text-slate-300">
          Mọi con số ở đây đếm trực tiếp trên các ca chạy qua Triage Agent, cùng một tập dữ liệu với
          bảng hàng đợi.
        </p>
      </header>

      {/* ------------------------------------------------------ Ô CHỈ SỐ */}
      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
        <StatTile
          icon={Inbox}
          label="Chưa ai nhận"
          value={data.waiting}
          hint={`${liveTotal} ca đang mở, gồm cả ca đã có người phụ trách`}
          tone={data.waiting > 0 ? "active" : "neutral"}
        />
        <StatTile
          icon={UserRoundCheck}
          label="Bạn phụ trách"
          value={data.assigned_to_me}
          hint={`Cả kíp đang giữ ${data.assigned_total} ca`}
          tone="neutral"
        />
        <StatTile
          icon={Clock3}
          label="Chờ lâu nhất"
          value={data.longest_wait_minutes === null ? "—" : formatWait(data.longest_wait_minutes)}
          hint="Tính từ lúc agent kết thúc phiên sàng lọc"
          tone={
            data.longest_wait_minutes !== null && data.longest_wait_minutes >= 60
              ? "critical"
              : data.longest_wait_minutes !== null && data.longest_wait_minutes >= 30
                ? "warning"
                : "neutral"
          }
        />
        <StatTile
          icon={AlertCircle}
          label="Thiếu dữ liệu kết luận"
          value={data.insufficient_live}
          hint="Agent dừng lại thay vì đoán một mức ESI"
          tone={data.insufficient_live > 0 ? "warning" : "neutral"}
        />
      </div>

      <div className="grid gap-3 sm:grid-cols-2">
        <StatTile
          icon={Archive}
          label="Đang tạm gác"
          value={data.parked}
          hint="Chờ bổ sung thông tin trước khi xử lý tiếp"
        />
        <StatTile
          icon={CheckCircle2}
          label="Đã chốt"
          value={data.decided}
          hint="Tổng số ca đã có quyết định phân luồng cuối cùng"
        />
      </div>

      {/* ------------------------------------------------------ BIỂU ĐỒ */}
      <div className="grid gap-5 lg:grid-cols-2 lg:items-start">
        <EsiPanel buckets={data.esi_distribution} />
        <WaitPanel dashboard={data} />
      </div>

      <AgreementPanel agreement={data.agreement} />

      <div className="grid gap-5 lg:grid-cols-2 lg:items-start">
        <ReasonPanel
          reasons={data.reason_codes}
          total={data.reason_codes.reduce((sum, reason) => sum + reason.count, 0)}
        />
        <VolumePanel points={data.daily_volume} />
      </div>
    </div>
  );
}

export default SimpleNurseDashboard;
