"use client";

import React from "react";
import { Moon, Sun } from "lucide-react";

import { useTheme } from "@/components/providers/theme-provider";
import { cn } from "@/lib/utils";
import type { ThemePreference } from "@/lib/theme";

/**
 * ============================================================================
 * [THEME TOGGLE] CHUYỂN CHẾ ĐỘ SÁNG / TỐI
 * ============================================================================
 *
 * Hai lựa chọn, hiện hết ra thay vì một nút bấm xoay vòng: người dùng thấy
 * ngay đang ở chế độ nào và chuyển được chỉ bằng một cú bấm.
 *
 * Không có nút "theo hệ thống" trên thanh điều hướng. Cài đặt của máy vẫn được
 * tôn trọng — lần đầu vào, ai để máy ở chế độ tối sẽ thấy giao diện tối ngay —
 * nhưng đó là điểm khởi đầu chứ không phải một nút bấm thứ ba. Thêm một biểu
 * tượng màn hình vào cạnh mặt trời và mặt trăng chỉ làm người dùng phải dừng
 * lại đoán nó là gì.
 *
 * Tuân thủ quy tắc 3.3 của .agents/rules/frontend-rules.md: 100% icon vector
 * Lucide, cấm emoji.
 */

const OPTIONS: ReadonlyArray<{
  value: Exclude<ThemePreference, "system">;
  label: string;
  Icon: typeof Sun;
}> = [
  { value: "light", label: "Sáng", Icon: Sun },
  { value: "dark", label: "Tối", Icon: Moon },
];

interface ThemeToggleProps {
  /** `compact` chỉ hiện icon (thanh điều hướng); `full` kèm chữ (menu di động). */
  variant?: "compact" | "full";
  className?: string;
}

export function ThemeToggle({ variant = "compact", className }: ThemeToggleProps) {
  const theme = useTheme();

  // Ngoài provider thì không có gì để điều khiển; ẩn hẳn còn hơn hiện một nút
  // bấm không làm gì.
  if (!theme) return null;

  // Bám theo chế độ ĐANG hiển thị, không bám theo lựa chọn đã lưu. Người chưa
  // bấm bao giờ vẫn đang xem một trong hai chế độ, và nút phải nói đúng chế độ
  // đó thay vì để cả hai cùng tắt.
  const { resolved, setPreference } = theme;
  const isCompact = variant === "compact";

  return (
    <div
      role="group"
      aria-label="Chế độ hiển thị"
      className={cn(
        "inline-flex items-center gap-0.5 rounded-xl border border-slate-200 bg-slate-100 p-1",
        "dark:border-slate-700 dark:bg-slate-800",
        isCompact ? "" : "w-full justify-between",
        className,
      )}
    >
      {OPTIONS.map(({ value, label, Icon }) => {
        const active = resolved === value;
        return (
          <button
            key={value}
            type="button"
            onClick={() => setPreference(value)}
            aria-pressed={active}
            title={label}
            className={cn(
              "flex items-center justify-center gap-2 rounded-lg font-semibold transition-colors",
              "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-sky-600 focus-visible:ring-offset-1",
              "dark:focus-visible:ring-sky-400 dark:focus-visible:ring-offset-slate-800",
              isCompact ? "size-9" : "min-h-11 flex-1 px-3 text-sm",
              active
                ? "bg-white text-slate-900 shadow-2xs dark:bg-slate-950 dark:text-white"
                : "text-slate-500 hover:text-slate-900 dark:text-slate-400 dark:hover:text-white",
            )}
          >
            <Icon className="size-4 shrink-0" aria-hidden="true" />
            {isCompact ? <span className="sr-only">{label}</span> : <span>{label}</span>}
          </button>
        );
      })}
    </div>
  );
}

export default ThemeToggle;
