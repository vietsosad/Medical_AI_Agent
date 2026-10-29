/**
 * Bảng màu thang ESI 5 cấp, dùng chung cho bảng điều phối và màn thẩm định ca
 * để hai màn hình không bao giờ hiển thị cùng một mức độ bằng hai màu khác
 * nhau -- điều dưỡng chuyển qua lại giữa chúng liên tục trong ca trực.
 *
 * Quy ước màu bám đúng thang phân loại cấp cứu:
 * 1 đỏ (hồi sức) · 2 cam (cấp cứu) · 3 vàng (khẩn trương) ·
 * 4 lục (ít khẩn) · 5 lam (không khẩn).
 *
 * Chip có sẵn biến thể tối: nền đậm, chữ sáng, cùng sắc độ với bản sáng.
 *
 * Màu LUÔN đi kèm chữ ở mọi nơi sử dụng ("ESI 2", "Cấp cứu"), không bao giờ là
 * kênh truyền tin duy nhất -- người rối loạn sắc giác vẫn phải đọc được.
 */

export interface EsiTheme {
  /** Nền + viền cho thẻ mức độ. */
  chip: string;
  /** Dải màu đặc, dùng cho mép trái hàng ca và chấm chỉ dẫn. */
  rail: string;
  /** Tên mức độ theo ngôn ngữ phân loại cấp cứu. */
  label: string;
}

export const ESI_THEME: Record<number, EsiTheme> = {
  1: { chip: "border-rose-300 bg-rose-100 text-rose-900 dark:border-rose-800 dark:bg-rose-950/60 dark:text-rose-100", rail: "bg-rose-600", label: "Hồi sức" },
  2: { chip: "border-orange-300 bg-orange-100 text-orange-900 dark:border-orange-800 dark:bg-orange-950/60 dark:text-orange-100", rail: "bg-orange-500", label: "Cấp cứu" },
  3: { chip: "border-amber-300 bg-amber-100 text-amber-900 dark:border-amber-800 dark:bg-amber-950/60 dark:text-amber-100", rail: "bg-amber-400", label: "Khẩn trương" },
  4: { chip: "border-emerald-300 bg-emerald-100 text-emerald-900 dark:border-emerald-800 dark:bg-emerald-950/60 dark:text-emerald-100", rail: "bg-emerald-500", label: "Ít khẩn cấp" },
  5: { chip: "border-sky-300 bg-sky-100 text-sky-900 dark:border-sky-800 dark:bg-sky-950/60 dark:text-sky-100", rail: "bg-sky-500", label: "Không khẩn cấp" },
};

export const ESI_UNKNOWN: EsiTheme = {
  chip: "border-slate-300 bg-slate-100 text-slate-700 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-200",
  rail: "bg-slate-300 dark:bg-slate-600",
  label: "Chưa đủ dữ liệu",
};

export function esiTheme(esi: number | null | undefined): EsiTheme {
  return esi !== null && esi !== undefined && ESI_THEME[esi] ? ESI_THEME[esi] : ESI_UNKNOWN;
}
