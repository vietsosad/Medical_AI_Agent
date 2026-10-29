import type { CSSProperties } from "react";
import { Phone } from "lucide-react";

import { cn } from "@/lib/utils";

/**
 * Lối thoát cấp cứu luôn có mặt ở mọi màn xác thực: người đang nguy cấp không
 * phải đăng nhập mới gọi được 115. Đây là thông tin tĩnh, không phải cảnh báo
 * vừa phát sinh, nên dùng vùng mốc `aside` thay vì `role="alert"`.
 */
export function AuthEmergencyStrip({ className, style }: { className?: string; style?: CSSProperties }) {
  return (
    <aside
      aria-label="Cấp cứu"
      className={cn(
        "flex items-center justify-between gap-4 rounded-2xl border border-rose-200 bg-rose-50 p-4 dark:border-rose-900/60 dark:bg-rose-950/40",
        className,
      )}
      style={style}
    >
      <p className="text-sm font-semibold leading-snug text-rose-900 dark:text-rose-100">
        Đang cấp cứu? Gọi ngay, không cần đăng nhập.
      </p>
      <a
        href="tel:115"
        aria-label="Gọi cấp cứu 115"
        className="inline-flex min-h-11 shrink-0 items-center gap-2 rounded-xl bg-rose-700 px-4 text-base font-extrabold text-white transition-[background-color,scale] duration-120 hover:bg-rose-800 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-rose-700 motion-safe:active:scale-[0.97] dark:focus-visible:outline-rose-400"
      >
        <Phone className="size-4" aria-hidden="true" />
        115
      </a>
    </aside>
  );
}
