import type { CSSProperties } from "react";

import { DURATION, staggerDelay } from "@/lib/motion";

/**
 * Lớp dùng chung cho các màn xác thực (đăng nhập, đăng ký, mã xác minh, quên
 * mật khẩu, OAuth callback). Màu lấy từ token nên chế độ tối tự đúng.
 *
 * Viền ô nhập đổi màu theo trạng thái được viết thành từng bộ riêng thay vì
 * dựa vào tailwind-merge gộp lớp: biến thể `dark:` đứng sau `focus-visible:`
 * trong CSS sinh ra, nên bộ tối phải tự mang lớp `dark:focus-visible:`.
 */

export const focusOutlineClass =
  "focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-brand";

/** Khung ô nhập: viền và vòng sáng lớn dần khi focus (180 ms, đường cong "vào"). */
export const fieldBaseClass =
  "h-12 w-full min-w-0 rounded-xl border bg-card px-4 text-base text-foreground caret-brand outline-hidden placeholder:text-muted-foreground transition-[border-color,box-shadow,background-color] duration-180 ease-[cubic-bezier(0.22,1,0.36,1)] disabled:cursor-not-allowed disabled:opacity-60";

export const fieldToneClass =
  "border-slate-300 focus-visible:border-brand focus-visible:inset-ring-1 focus-visible:inset-ring-brand focus-visible:ring-4 focus-visible:ring-brand/20 dark:border-slate-700 dark:focus-visible:border-brand";

export const fieldInvalidToneClass =
  "border-rose-500 focus-visible:border-rose-600 focus-visible:inset-ring-1 focus-visible:inset-ring-rose-600 focus-visible:ring-4 focus-visible:ring-rose-600/20 dark:border-rose-400 dark:focus-visible:border-rose-400 dark:focus-visible:inset-ring-rose-400 dark:focus-visible:ring-rose-400/25";

export const primaryButtonClass =
  "relative inline-flex min-h-14 w-full items-center justify-center gap-2 rounded-xl bg-brand px-6 text-base font-bold text-brand-foreground shadow-[0_10px_24px_-12px_rgb(15_118_110/0.7)] transition-[background-color,box-shadow,opacity] duration-180 hover:bg-brand-strong disabled:cursor-not-allowed disabled:opacity-60 dark:shadow-none " +
  focusOutlineClass;

export const secondaryButtonClass =
  "inline-flex min-h-12 w-full items-center justify-center gap-2 rounded-xl border border-slate-300 bg-card px-4 text-base font-semibold text-foreground transition-[background-color,border-color,opacity] duration-180 hover:border-slate-400 hover:bg-muted disabled:cursor-not-allowed disabled:opacity-60 dark:border-slate-700 dark:hover:border-slate-500 " +
  focusOutlineClass;

export const textLinkClass =
  "rounded-md font-semibold text-brand underline-offset-4 transition-colors duration-180 hover:text-brand-strong hover:underline " +
  focusOutlineClass;

/**
 * Độ trễ cho lớp `.page-enter`: khối nội dung của trang mới nổi lên lần lượt,
 * cách nhau 50 ms (tối đa 6 khối). Lớp CSS chạy ngay từ HTML máy chủ và tự tắt
 * khi người dùng bật "giảm chuyển động".
 */
export function enterDelay(index: number): CSSProperties {
  return { animationDelay: `${Math.round(staggerDelay(index) * 1000)}ms` };
}

/** Như `enterDelay`, nhưng cho cả một thẻ/bảng: quy chuẩn cho thẻ là 420 ms. */
export function cardEnter(index = 0): CSSProperties {
  return { ...enterDelay(index), animationDuration: `${Math.round(DURATION.gentle * 1000)}ms` };
}
