"use client";

import type { ReactNode } from "react";
import { AnimatePresence, motion, useReducedMotion } from "framer-motion";

import { DURATION, EASE_IN, enterTransition, popVariants } from "@/lib/motion";
import { cn } from "@/lib/utils";

const TONE_CLASS = {
  success:
    "border-emerald-200 bg-emerald-50 text-emerald-700 dark:border-emerald-900/60 dark:bg-emerald-950/40 dark:text-emerald-300",
  error:
    "border-rose-200 bg-rose-50 text-rose-700 dark:border-rose-900/60 dark:bg-rose-950/40 dark:text-rose-300",
  neutral: "border-border bg-card text-foreground",
} as const;

/** Ô biểu tượng kết quả (thành công / lỗi / đang xử lý), bật vào khi xuất hiện. */
export function AuthStatusIcon({
  tone,
  children,
  className,
}: {
  tone: keyof typeof TONE_CLASS;
  children: ReactNode;
  className?: string;
}) {
  return (
    <motion.span
      aria-hidden="true"
      variants={popVariants}
      initial="hidden"
      animate="visible"
      className={cn(
        "relative grid size-16 shrink-0 place-items-center rounded-2xl border",
        TONE_CLASS[tone],
        className,
      )}
    >
      {children}
    </motion.span>
  );
}

/**
 * Chuyển giữa các bước (nhập email -> nhập mã -> đặt mật khẩu...) bằng cách
 * hòa mờ: bước cũ tách khỏi bố cục và mờ đi thật nhanh, bước mới nổi lên ngay
 * tại chỗ. Bước mới được gắn vào DOM ngay lập tức, nên lệnh focus của trang
 * (ví dụ đưa con trỏ vào ô mã đầu tiên) vẫn chạy đúng lúc.
 */
export function AuthSwap({ stateKey, children }: { stateKey: string; children: ReactNode }) {
  const reduceMotion = useReducedMotion() ?? false;

  return (
    <div className="relative">
      <AnimatePresence mode="popLayout" initial={false}>
        <motion.div
          key={stateKey}
          initial={reduceMotion ? { opacity: 0 } : { opacity: 0, y: 8 }}
          animate={{ opacity: 1, y: 0, transition: reduceMotion ? { duration: 0.12 } : enterTransition }}
          exit={{
            opacity: 0,
            transition: reduceMotion ? { duration: 0.1 } : { duration: DURATION.press, ease: EASE_IN },
          }}
        >
          {children}
        </motion.div>
      </AnimatePresence>
    </div>
  );
}
