/**
 * Cách đọc thời gian chờ của một ca, dùng chung cho bảng điều phối và bảng số
 * liệu tổng quan.
 *
 * Hai màn hình này nằm cạnh nhau trong cùng một ca trực. Nếu bảng ca gọi một
 * ca là "Chờ 45 phút" còn bảng số liệu xếp nó vào nhóm khác, hoặc hai nơi cắt
 * mốc cảnh báo ở hai con số khác nhau, thì người trực mất lòng tin vào cả hai.
 * Vì vậy mốc và cách diễn đạt chỉ được định nghĩa đúng một lần, ở đây.
 *
 * Hai mốc dưới đây phải trùng với `WAIT_WARNING_MINUTES` / `WAIT_CRITICAL_MINUTES`
 * trong `src/services/simple_nurse_dashboard.py` -- backend chia nhóm, frontend
 * tô màu, cả hai phải cắt ở cùng một chỗ.
 */

/** Quá mốc này thì thời gian chờ được tô cảnh báo. */
export const WAIT_WARNING_MINUTES = 30;
export const WAIT_CRITICAL_MINUTES = 60;

/**
 * Mốc giờ từ backend, theo mili giây. Backend ghi giờ UTC không kèm hậu tố múi
 * giờ (`get_utc_now()` là naive, ví dụ "2026-11-03T08:00:00"), mà trình duyệt
 * đọc một chuỗi như vậy là giờ ĐỊA PHƯƠNG: ở Việt Nam mọi thời gian chờ sẽ dư
 * đúng 7 tiếng, một ca vừa tới 10 phút hiện thành "7 giờ 10 phút". Vì vậy tự
 * gắn "Z" khi chuỗi chưa có múi giờ -- cùng quy tắc với `parseSnapshot`.
 */
export function serverTimeMs(iso: string): number {
  const hasZone = /(?:Z|[+-]\d{2}:?\d{2})$/i.test(iso);
  return new Date(hasZone ? iso : `${iso}Z`).getTime();
}

/** Số phút đã trôi qua kể từ mốc ca sẵn sàng cho điều dưỡng. */
export function waitingMinutes(iso: string): number {
  return Math.max(0, Math.floor((Date.now() - serverTimeMs(iso)) / 60000));
}

const MINUTES_PER_DAY = 24 * 60;

/** "Dưới 1 phút" / "45 phút" / "2 giờ 10 phút" / "3 ngày 4 giờ" -- cách nói
 * của người trực. Từ một ngày trở lên, số phút không còn ý nghĩa nên bỏ đi. */
export function formatWait(minutes: number): string {
  if (minutes < 1) return "Dưới 1 phút";
  if (minutes < 60) return `${minutes} phút`;
  if (minutes >= MINUTES_PER_DAY) {
    const days = Math.floor(minutes / MINUTES_PER_DAY);
    const hours = Math.floor((minutes % MINUTES_PER_DAY) / 60);
    return hours === 0 ? `${days} ngày` : `${days} ngày ${hours} giờ`;
  }
  const hours = Math.floor(minutes / 60);
  const rest = minutes % 60;
  return rest === 0 ? `${hours} giờ` : `${hours} giờ ${rest} phút`;
}

/** Nền + viền cho nhãn thời gian chờ trên bảng ca. */
export function waitClasses(minutes: number): string {
  if (minutes >= WAIT_CRITICAL_MINUTES) {
    return "border-rose-200 bg-rose-50 text-rose-800 dark:border-rose-900 dark:bg-rose-950/50 dark:text-rose-200";
  }
  if (minutes >= WAIT_WARNING_MINUTES) {
    return "border-amber-200 bg-amber-50 text-amber-800 dark:border-amber-900 dark:bg-amber-950/50 dark:text-amber-200";
  }
  return "border-slate-200 bg-slate-50 text-slate-600 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-300";
}
