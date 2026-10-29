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

import { WAIT_CRITICAL_MINUTES, WAIT_WARNING_MINUTES } from "@/components/clinical/nurse-simple/wait-time";
import type { SimpleAgreementDTO, SimpleWaitBucketDTO, SimpleWaitBucketKey } from "@/types/simple-nurse";

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
 */
export const VIZ_TOKEN_CLASSES = [
  "[--viz-slot-1:#0D9488] [--viz-slot-2:#6250D6] dark:[--viz-slot-2:#8B5CF6]",
  "[--viz-escalated:#C2410C] [--viz-confirmed:#94A3B8] [--viz-deescalated:#0369A1]",
  "[--viz-grid:#E2E8F0] dark:[--viz-grid:#1E293B] [--viz-axis:#CBD5E1] dark:[--viz-axis:#475569]",
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
