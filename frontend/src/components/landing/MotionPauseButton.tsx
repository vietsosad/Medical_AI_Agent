"use client";

import { useReducedMotion } from "framer-motion";
import { Pause, Play } from "lucide-react";

import { cn } from "@/lib/utils";

/**
 * Nút dừng / cho chạy tiếp một khối hình động tự chạy trên trang chủ. Hình động
 * tự chạy quá 5 giây phải dừng được (WCAG 2.2.2). Người đã tắt hiệu ứng chuyển
 * động không thấy nút: với họ không có gì chạy.
 */
export function MotionPauseButton({
  paused,
  onToggle,
  subject,
  className,
}: {
  paused: boolean;
  onToggle: () => void;
  /** Thứ đang chuyển động, để tên nút nói rõ nó dừng gì: "Dừng {subject}". */
  subject: string;
  className?: string;
}) {
  const reduced = Boolean(useReducedMotion());
  if (reduced) return null;

  return (
    <button
      type="button"
      onClick={onToggle}
      aria-pressed={paused}
      aria-label={paused ? `Cho ${subject} chạy tiếp` : `Dừng ${subject}`}
      className={cn(
        "flex size-12 items-center justify-center rounded-full border border-border bg-card text-foreground shadow-[0_10px_24px_-16px_rgba(15,23,42,0.6)] transition-colors hover:border-brand-edge hover:text-brand focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand",
        className,
      )}
    >
      {paused ? <Play className="size-5" aria-hidden="true" /> : <Pause className="size-5" aria-hidden="true" />}
    </button>
  );
}
