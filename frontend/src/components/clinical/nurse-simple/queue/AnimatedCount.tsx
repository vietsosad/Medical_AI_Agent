"use client";

import { AnimatePresence, motion } from "framer-motion";

import { DURATION, EASE_OUT } from "@/lib/motion";
import { cn } from "@/lib/utils";

/**
 * Con số đổi giá trị thì số cũ trượt xuống, số mới trượt vào: người trực thấy
 * ngay bộ đếm vừa thay đổi thay vì phải nhớ con số lúc trước. Lần hiện đầu
 * tiên không diễn hoạt.
 */
export function AnimatedCount({ value, className }: { value: number; className?: string }) {
  return (
    <span className={cn("relative inline-flex overflow-hidden tabular-nums", className)}>
      <AnimatePresence initial={false} mode="popLayout">
        <motion.span
          key={value}
          initial={{ y: "-70%", opacity: 0 }}
          animate={{ y: 0, opacity: 1 }}
          exit={{ y: "70%", opacity: 0 }}
          transition={{ duration: DURATION.quick, ease: EASE_OUT }}
        >
          {value}
        </motion.span>
      </AnimatePresence>
    </span>
  );
}
