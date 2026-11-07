/**
 * Phần thuần (không React) của bảng tổng quan trạm điều phối: nhãn, màu biểu
 * đồ đã kiểm định và vài phép tính nhỏ. Tách khỏi JSX để mỗi con số trên màn
 * hình truy ngược được về đúng một trường của `GET /nurse-simple/dashboard`
 * (xem đầu `src/services/simple_nurse_dashboard.py`).
 *
 * Mọi số ở đây là phép ĐẾM, không phải ước lượng. Khối "đồng thuận" luôn được
 * gọi là điều dưỡng đã làm gì với đề xuất, không bao giờ là độ chính xác.
 */
import { CircleCheck, Clock, TriangleAlert, type LucideIcon } from "lucide-react";

import { esiTheme, ESI_UNKNOWN } from "@/components/clinical/nurse-simple/esi-theme";
import { WAIT_CRITICAL_MINUTES, WAIT_WARNING_MINUTES } from "@/components/clinical/nurse-simple/wait-time";
import type {
  SimpleAgreementDTO,
  SimpleClaimBinDTO,
  SimpleDashboardWindow,
  SimpleHourOfDayDTO,
  SimpleMatrixRowKey,
  SimpleWaitBucketDTO,
  SimpleWaitBucketKey,
  SimpleWeekdayHourDTO,
} from "@/types/simple-nurse";

// ============================================================================
// MÀU BIỂU ĐỒ
// ============================================================================

/**
 * Biến màu của mọi biểu đồ trên màn, đặt một lần ở gốc bảng. Các giá trị đã
 * chạy qua bộ kiểm định bảng màu (độ tách sắc giác, độ tương phản) ở cả hai
 * chế độ sáng/tối -- không thêm màu nào ngoài danh sách này.
 *
 * - slot-1 / slot-2: hai chuỗi của biểu đồ khối lượng; slot-1 cũng là màu duy
 *   nhất của biểu đồ một chuỗi (lý do chốt ca). Bước tối của slot-2 sáng hơn
 *   để vẫn đọc được trên nền thẻ tối.
 * - escalated / confirmed / deescalated: thang phân cực "điều dưỡng so với
 *   AI". Mốc giữa là xám trung tính và luôn đi kèm nhãn chữ; ba giá trị này
 *   giữ nguyên ở chế độ tối (đã kiểm định trên cả hai nền).
 * - grid / axis: lưới mảnh lùi về sau và đường đáy đậm hơn một bậc.
 * - heat-1..5: thang tuần tự MỘT sắc (teal của thương hiệu) cho ma trận mức
 *   khẩn × thời gian chờ, nhạt = ít, đậm = nhiều. Ở chế độ tối thang lật mốc:
 *   bậc ít nằm sát nền tối, bậc nhiều sáng nhất. Đã chạy `validate_palette.js
 *   --ordinal`: đơn điệu, mỗi bậc cách nhau ΔL >= 0.06 ở cả hai chế độ; bậc
 *   nhạt nhất ở chế độ sáng được phép chìm gần nền vì mỗi ô luôn in số.
 * - heat-ink-1..5: màu chữ in trong từng bậc, chọn theo độ tương phản
 *   (>= 4.5:1 ở mọi bậc, kiểm bằng `contrast()` của bộ kiểm định).
 * - spark: xám lùi của đường xu hướng trong ô chỉ số; giờ đang chạy mang slot-1.
 */
export const VIZ_TOKEN_CLASSES = [
  "[--viz-slot-1:#0D9488] [--viz-slot-2:#6250D6] dark:[--viz-slot-2:#8B5CF6]",
  "[--viz-escalated:#C2410C] [--viz-confirmed:#94A3B8] [--viz-deescalated:#0369A1]",
  "[--viz-grid:#E2E8F0] dark:[--viz-grid:#1E293B] [--viz-axis:#CBD5E1] dark:[--viz-axis:#475569]",
  "[--viz-heat-1:#CCFBF1] [--viz-heat-2:#5EEAD4] [--viz-heat-3:#2DD4BF] [--viz-heat-4:#0D9488] [--viz-heat-5:#115E59]",
  "dark:[--viz-heat-1:#115E59] dark:[--viz-heat-2:#0F766E] dark:[--viz-heat-3:#0D9488] dark:[--viz-heat-4:#14B8A6] dark:[--viz-heat-5:#5EEAD4]",
  "[--viz-heat-ink-1:#0F172A] [--viz-heat-ink-2:#0F172A] [--viz-heat-ink-3:#0F172A] [--viz-heat-ink-4:#0F172A] [--viz-heat-ink-5:#FFFFFF]",
  "dark:[--viz-heat-ink-1:#FFFFFF] dark:[--viz-heat-ink-2:#FFFFFF] dark:[--viz-heat-ink-3:#0F172A] dark:[--viz-heat-ink-4:#0F172A] dark:[--viz-heat-ink-5:#0F172A]",
  "[--viz-spark:#64748B]",
].join(" ");

// ============================================================================
// ĐỊNH DẠNG
// ============================================================================

const COUNT_FORMAT = new Intl.NumberFormat("vi-VN");

/** 1284 -> "1.284". Số lớn đứng một mình dùng chữ số tỉ lệ, không tabular. */
export function formatCount(value: number): string {
  return COUNT_FORMAT.format(value);
}

/** Tỉ lệ làm tròn tới phần trăm. Mẫu số bằng 0 thì không có tỉ lệ nào để nói. */
export function percentOf(part: number, whole: number): string {
  if (whole <= 0) return "—";
  return `${Math.round((part / whole) * 100)}%`;
}

/** Phần của tổng, 0..1; mẫu số bằng 0 thì là 0. */
export function shareOf(part: number, whole: number): number {
  return whole > 0 ? part / whole : 0;
}

export function sumCounts(items: ReadonlyArray<{ count: number }>): number {
  return items.reduce((sum, item) => sum + item.count, 0);
}

/**
 * "2026-10-29" -> "29/10". Ngày do backend chia theo giờ UTC; giữ nguyên chuỗi
 * ngày, không quy đổi múi giờ, để mỗi điểm trùng đúng nhóm mà backend đã đếm.
 */
export function formatDay(isoDate: string): string {
  return `${isoDate.slice(8, 10)}/${isoDate.slice(5, 7)}`;
}

/**
 * Thời điểm chụp số liệu. Backend gửi giờ UTC không kèm hậu tố múi giờ
 * (`get_utc_now()` là naive), nên tự gắn "Z"; chuỗi đã có múi giờ thì giữ nguyên.
 */
export function parseSnapshot(iso: string): Date | null {
  const hasZone = /(?:Z|[+-]\d{2}:?\d{2})$/.test(iso);
  const parsed = new Date(hasZone ? iso : `${iso}Z`);
  return Number.isNaN(parsed.getTime()) ? null : parsed;
}

// ============================================================================
// THỜI GIAN CHỜ
// ============================================================================

export interface WaitBucketMeta {
  label: string;
  icon: LucideIcon;
  /** Màu đoạn trong thanh chia. Đặt trên nền tối của ô chính ở CẢ HAI chế độ. */
  bar: string;
  /** Màu biểu tượng trên cùng nền tối đó. */
  iconTone: string;
}

/**
 * Ba nhóm chờ, cắt đúng hai mốc mà bảng ca dùng (`wait-time.ts`, trùng với
 * backend). Phút là số nguyên làm tròn xuống, nên nhóm giữa là 30 - 59 phút.
 * Màu trạng thái luôn đi kèm biểu tượng và nhãn, không bao giờ đứng một mình.
 */
export const WAIT_BUCKET_META: Record<SimpleWaitBucketKey, WaitBucketMeta> = {
  UNDER_WARNING: {
    label: `Dưới ${WAIT_WARNING_MINUTES} phút`,
    icon: CircleCheck,
    bar: "bg-emerald-500",
    iconTone: "text-emerald-400",
  },
  WARNING: {
    label: `${WAIT_WARNING_MINUTES} – ${WAIT_CRITICAL_MINUTES - 1} phút`,
    icon: Clock,
    bar: "bg-amber-400",
    iconTone: "text-amber-400",
  },
  CRITICAL: {
    label: `Từ ${WAIT_CRITICAL_MINUTES} phút`,
    icon: TriangleAlert,
    bar: "bg-rose-500",
    iconTone: "text-rose-400",
  },
};

const WAIT_ORDER: readonly SimpleWaitBucketKey[] = ["UNDER_WARNING", "WARNING", "CRITICAL"];

/** Luôn đủ ba nhóm, theo thứ tự từ chờ ngắn tới chờ lâu. */
export function orderedWaitBuckets(buckets: readonly SimpleWaitBucketDTO[]): SimpleWaitBucketDTO[] {
  return WAIT_ORDER.map((key) => ({
    key,
    count: buckets.find((bucket) => bucket.key === key)?.count ?? 0,
  }));
}

/** Nhóm chờ của một số phút cụ thể -- cùng mốc cắt với backend. */
export function waitBucketOf(minutes: number): SimpleWaitBucketKey {
  if (minutes >= WAIT_CRITICAL_MINUTES) return "CRITICAL";
  if (minutes >= WAIT_WARNING_MINUTES) return "WARNING";
  return "UNDER_WARNING";
}

// ============================================================================
// ĐIỀU DƯỠNG SO VỚI ĐỀ XUẤT CỦA AI
// ============================================================================

export type AgreementKey = "escalated" | "confirmed" | "de_escalated";

export interface AgreementSeries {
  key: AgreementKey;
  /** Nhãn nói rõ chiều của thang ESI, người đọc không phải tự đoán. */
  label: string;
  color: string;
}

/**
 * Thứ tự cố ý: khẩn hơn -- giữ nguyên -- ít khẩn hơn. Đây là một thang phân
 * cực quanh mốc "giữ nguyên", nên mốc giữa mang xám trung tính còn hai đầu
 * mang hai màu đối nhau (ấm/lạnh), không phải ba màu rời rạc.
 */
export const AGREEMENT_SERIES: readonly AgreementSeries[] = [
  { key: "escalated", label: "Chốt khẩn hơn AI", color: "var(--viz-escalated)" },
  { key: "confirmed", label: "Giữ nguyên mức AI", color: "var(--viz-confirmed)" },
  { key: "de_escalated", label: "Chốt ít khẩn hơn AI", color: "var(--viz-deescalated)" },
];

export function agreementCount(agreement: SimpleAgreementDTO, key: AgreementKey): number {
  return agreement[key];
}

/**
 * Số ca có mức AI để so: mẫu số của thanh phân cực. Ca điều dưỡng tự chốt khi
 * AI chưa đề xuất mức không nằm trên thang này, nên được nêu riêng.
 */
export function comparedTotal(agreement: SimpleAgreementDTO): number {
  return agreement.escalated + agreement.confirmed + agreement.de_escalated;
}

// ============================================================================
// LÝ DO CHỐT CA
// ============================================================================

/**
 * Mã lý do do backend kiểm định (`_REASON_CODES` trong routes_nurse_simple.py);
 * nhãn bám đúng chữ trong SimpleDecisionForm.tsx -- điều dưỡng đọc lại đúng câu
 * mình đã chọn.
 */
export const REASON_LABELS: Record<string, string> = {
  MATCHES_PROTOCOL: "Dữ liệu phù hợp với phác đồ đã tham chiếu",
  ADDITIONAL_CLINICAL_JUDGMENT: "Nhận định lâm sàng bổ sung",
  INSUFFICIENT_PATIENT_DATA: "Dữ liệu bệnh nhân cung cấp chưa đủ",
  OTHER: "Lý do khác (ghi rõ trong ghi chú)",
};

export function reasonLabel(code: string): string {
  return REASON_LABELS[code] ?? code;
}

// ============================================================================
// CỬA SỔ LỊCH SỬ
// ============================================================================

/** Bốn cửa sổ backend nhận (`WINDOW_DAYS_CHOICES`); thứ tự này là thứ tự nút. */
export const DASHBOARD_WINDOWS: readonly SimpleDashboardWindow[] = [7, 14, 30, 90];
export const DEFAULT_DASHBOARD_WINDOW: SimpleDashboardWindow = 14;

// ============================================================================
// MA TRẬN MỨC KHẨN × THỜI GIAN CHỜ
// ============================================================================

export const HEAT_STEPS = 5;

/**
 * Bậc màu 1..5 của một ô, so với ô nhiều nhất của chính ma trận; 0 = không
 * tô. Thang tương đối nên chú giải luôn ghi rõ hai đầu (1 và số lớn nhất).
 */
export function heatStep(count: number, max: number): number {
  if (count <= 0 || max <= 0) return 0;
  return Math.min(HEAT_STEPS, Math.max(1, Math.ceil((count / max) * HEAT_STEPS)));
}

export interface MatrixRowMeta {
  /** Tên ngắn đứng đầu hàng ("ESI 2", "Chưa đủ dữ liệu"). */
  name: string;
  /** Phần giải thích đi kèm ("Cấp cứu"), hoặc null. */
  detail: string | null;
  /** Dải màu nhận diện, cùng màu với bảng ca. */
  rail: string;
}

/**
 * Nhãn của một hàng ma trận. Hàng "Đang sàng lọc" mang màu đỏ của cờ "Cần xem
 * ngay" vì nó CHỈ gồm phiên đã bị gắn cờ -- nhưng không bao giờ mang chữ
 * "ESI": phiên chưa xong thì chưa có mức nào.
 */
export function matrixRowMeta(key: SimpleMatrixRowKey): MatrixRowMeta {
  if (key === "IN_PROGRESS") {
    return { name: "Đang sàng lọc", detail: "đã gắn cờ cần xem ngay", rail: "bg-rose-700 dark:bg-rose-500" };
  }
  if (key === "INSUFFICIENT") {
    return { name: ESI_UNKNOWN.label, detail: null, rail: ESI_UNKNOWN.rail };
  }
  const level = Number(key);
  const theme = esiTheme(level);
  return { name: `ESI ${level}`, detail: theme.label, rail: theme.rail };
}

/** "ESI 2 · Cấp cứu" / "Chưa đủ dữ liệu" -- dùng trong nhãn đọc và chú thích. */
export function matrixRowLabel(key: SimpleMatrixRowKey): string {
  const meta = matrixRowMeta(key);
  return meta.detail ? `${meta.name} · ${meta.detail}` : meta.name;
}

// ============================================================================
// GIỜ TRONG NGÀY
// ============================================================================

/** Lệch giờ của máy người xem so với UTC, tính bằng phút (Việt Nam: +420). */
export function localOffsetMinutes(): number {
  return -new Date().getTimezoneOffset();
}

export interface LocalHourPoint {
  hour: number;
  completed: number;
}

/**
 * Xoay 24 giờ UTC của backend sang 24 giờ trên máy người xem. Chỉ đúng với độ
 * lệch tròn giờ và không đổi trong cửa sổ -- đúng với Việt Nam (UTC+7, không
 * có giờ mùa hè). Độ lệch lẻ thì trả null để giao diện giữ nguyên nhãn UTC
 * thay vì gán sai giờ.
 */
export function hourOfDayInLocalTime(
  points: readonly SimpleHourOfDayDTO[],
  offsetMinutes: number,
): LocalHourPoint[] | null {
  if (offsetMinutes % 60 !== 0) return null;
  const shift = offsetMinutes / 60;
  const counts = Array.from({ length: 24 }, () => 0);
  for (const point of points) {
    counts[(((point.hour_utc + shift) % 24) + 24) % 24] += point.completed;
  }
  return counts.map((completed, hour) => ({ hour, completed }));
}

/** 9 -> "09:00 – 09:59". */
export function hourRangeLabel(hour: number): string {
  const hh = String(hour).padStart(2, "0");
  return `${hh}:00 – ${hh}:59`;
}

// ============================================================================
// MỨC AI ĐỀ XUẤT × MỨC ĐIỀU DƯỠNG CHỐT
// ============================================================================

export type DecisionRelation = "kept" | "more_urgent" | "less_urgent" | "no_proposal";

/**
 * Điều dưỡng đã làm gì ở một ô của ma trận. Thang ESI chạy ngược: chốt một số
 * NHỎ hơn mức AI đề xuất là chốt KHẨN HƠN. Trong mỗi hàng, ô bên trái ô đường
 * chéo là khẩn hơn, ô bên phải là ít khẩn hơn.
 */
export function decisionRelation(rowKey: SimpleMatrixRowKey, finalEsi: number): DecisionRelation {
  if (rowKey === "INSUFFICIENT" || rowKey === "IN_PROGRESS") return "no_proposal";
  const proposed = Number(rowKey);
  if (finalEsi === proposed) return "kept";
  return finalEsi < proposed ? "more_urgent" : "less_urgent";
}

const AGREEMENT_LABEL = Object.fromEntries(AGREEMENT_SERIES.map((series) => [series.key, series.label])) as Record<
  AgreementKey,
  string
>;

/** Cùng chữ với khối đối chiếu (`AGREEMENT_SERIES`): một hành động, một cách gọi. */
export const DECISION_RELATION_LABELS: Record<DecisionRelation, string> = {
  kept: AGREEMENT_LABEL.confirmed,
  more_urgent: AGREEMENT_LABEL.escalated,
  less_urgent: AGREEMENT_LABEL.de_escalated,
  no_proposal: "AI chưa đề xuất mức để so",
};

// ============================================================================
// TỪ LÚC GẮN CỜ TỚI KHI CÓ NGƯỜI NHẬN
// ============================================================================

/** "0 – 4 phút" / "Từ 60 phút": phút là số nguyên làm tròn xuống, như bảng ca. */
export function claimBinLabel(bin: SimpleClaimBinDTO): string {
  if (bin.max_minutes === null) return `Từ ${bin.min_minutes} phút`;
  return `${bin.min_minutes} – ${bin.max_minutes - 1} phút`;
}

/** Nhóm chờ của một cột, theo mốc tô màu của bảng ca (để gắn biểu tượng + nhãn). */
export function claimBinBucket(bin: SimpleClaimBinDTO): SimpleWaitBucketKey {
  return waitBucketOf(bin.min_minutes);
}

/** Đủ ca để nêu tỉ lệ / trung vị chưa: dưới ngưỡng thì chỉ nêu số ca. */
export function hasEnoughCases(count: number, minCases: number): boolean {
  return count > 0 && count >= minCases;
}

// ============================================================================
// THỨ × GIỜ THEO GIỜ VIỆT NAM
// ============================================================================

/** Thứ theo ISO (1 = Thứ Hai ... 7 = Chủ nhật), đúng thứ tự backend trả. */
export const WEEKDAY_LABELS: Record<number, string> = {
  1: "Thứ Hai",
  2: "Thứ Ba",
  3: "Thứ Tư",
  4: "Thứ Năm",
  5: "Thứ Sáu",
  6: "Thứ Bảy",
  7: "Chủ nhật",
};

export function weekdayLabel(weekday: number): string {
  return WEEKDAY_LABELS[weekday] ?? `Thứ ${weekday}`;
}

export interface WeekdayHourPeak {
  weekday: number;
  hour: number;
  count: number;
  /** Số khung giờ KHÁC có cùng số phiên lớn nhất. */
  ties: number;
}

/** Khung giờ đông nhất; hòa thì lấy khung đầu tiên theo thứ rồi theo giờ và nói rõ số khung hòa. */
export function weekdayHourPeak(panel: SimpleWeekdayHourDTO): WeekdayHourPeak | null {
  let peak: WeekdayHourPeak | null = null;
  for (const row of panel.rows) {
    for (let hour = 0; hour < row.hours.length; hour += 1) {
      const count = row.hours[hour];
      if (count <= 0) continue;
      if (peak === null || count > peak.count) {
        peak = { weekday: row.weekday, hour, count, ties: 0 };
      } else if (count === peak.count) {
        peak.ties += 1;
      }
    }
  }
  return peak;
}

/**
 * Cửa sổ không chia đều cho 7 thì có thứ được tính nhiều ngày hơn thứ khác:
 * nói rõ để không ai đọc nhầm "Chủ nhật đông hơn" chỉ vì có thêm một Chủ nhật.
 */
export function describeWeekdayDays(panel: SimpleWeekdayHourDTO): string {
  const counts = panel.rows.map((row) => row.days);
  const most = Math.max(...counts);
  const least = Math.min(...counts);
  if (most === least) return `Mỗi thứ có ${most} ngày trong khoảng này.`;
  const longer = panel.rows.filter((row) => row.days === most).map((row) => weekdayLabel(row.weekday));
  const rest = least === most - 1 ? `các thứ khác có ${least} ngày` : "các thứ khác có ít ngày hơn";
  return `${longer.join(", ")} có ${most} ngày trong khoảng này, ${rest}: so tổng giữa các thứ cần tính đến chênh lệch đó.`;
}

// ============================================================================
// TRỤC SỐ
// ============================================================================

const NICE_STEPS = [1, 2, 5, 10, 20, 25, 50, 100, 200, 250, 500, 1000, 2000, 2500, 5000];

/**
 * Trục đếm "tròn": tối đa 5 vạch nguyên (0, 5, 10, 15, 20). Tự tính thay vì để
 * thư viện tự chọn, để biết chắc đỉnh trục khi đặt nhãn cuối đường.
 */
export function niceCountAxis(maxValue: number): { top: number; ticks: number[] } {
  const safeMax = Math.max(1, Math.ceil(maxValue));
  const step =
    NICE_STEPS.find((candidate) => Math.ceil(safeMax / candidate) <= 4) ??
    10 ** Math.ceil(Math.log10(safeMax / 4));
  const top = Math.ceil(safeMax / step) * step;
  const ticks: number[] = [];
  for (let tick = 0; tick <= top; tick += step) ticks.push(tick);
  return { top, ticks };
}
