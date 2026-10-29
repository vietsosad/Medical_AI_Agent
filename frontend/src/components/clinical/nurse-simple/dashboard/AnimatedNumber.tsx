"use client";

import { animate, motion, useMotionValue, useReducedMotion, useTransform } from "framer-motion";
import { useEffect, useRef } from "react";

import { DURATION, EASE_OUT } from "@/lib/motion";
import { cn } from "@/lib/utils";

import { formatCount } from "./dashboard-model";

/** Vệt sáng báo "con số này vừa đổi": cùng nhịp với `.fact-flash` (900 ms). */
const CHANGE_FLASH_SECONDS = 0.9;

interface AnimatedNumberProps {
  value: number;
  /**
   * Đếm lên từ 0 ở lần hiện đầu tiên. Chỉ dành cho con số chính của màn: một
   * màn mà mọi ô cùng nhảy số thì không ô nào còn được chú ý.
   */
  countUp?: boolean;
  className?: string;
  /** Sắc của vệt sáng khi số đổi; mặc định là sắc thương hiệu. */
  flashClassName?: string;
}

/**
 * Một con số đếm được trên bảng tổng quan.
 *
 * - Lần đầu: hiện ngay giá trị (hoặc đếm lên một lần nếu `countUp`).
 * - Lần làm mới sau đó: nếu giá trị đổi, số trượt từ cũ sang mới và một vệt
 *   sáng mờ dần -- trả lời câu "cái gì vừa thay đổi". Giá trị không đổi thì
 *   không có gì chuyển động, nên vòng làm mới 30 giây không làm màn nhấp nháy.
 * - Người dùng bật giảm chuyển động: luôn hiện thẳng giá trị cuối.
 *
 * Trình đọc màn hình chỉ đọc giá trị cuối (bản sao `sr-only`), không bao giờ
 * đọc các số trung gian của hiệu ứng.
 */
export function AnimatedNumber({ value, countUp = false, className, flashClassName }: AnimatedNumberProps) {
  const reduceMotion = useReducedMotion() ?? false;
  const motionValue = useMotionValue(countUp && !reduceMotion ? 0 : value);
  const display = useTransform(motionValue, (latest) => formatCount(Math.round(latest)));
  const flashRef = useRef<HTMLSpanElement>(null);
  // Đã hiện xong lần đầu chưa: phân biệt "đếm lên lần đầu" với "vừa đổi giá trị".
  const settledRef = useRef(false);

  useEffect(() => {
    if (reduceMotion) {
      motionValue.set(value);
      settledRef.current = true;
      return;
    }
    if (motionValue.get() === value) {
      settledRef.current = true;
      return;
    }

    const isIntro = countUp && !settledRef.current;
    const controls = animate(motionValue, value, {
      duration: isIntro ? DURATION.slow : DURATION.gentle,
      ease: EASE_OUT,
      onComplete: () => {
        settledRef.current = true;
      },
    });
    const flash =
      !isIntro && flashRef.current
        ? animate(flashRef.current, { opacity: [0.85, 0] }, { duration: CHANGE_FLASH_SECONDS, ease: EASE_OUT })
        : null;

    return () => {
      controls.stop();
      flash?.stop();
    };
  }, [value, countUp, reduceMotion, motionValue]);

  return (
    <span className={cn("relative inline-block", className)}>
      <span
        ref={flashRef}
        aria-hidden="true"
        className={cn("pointer-events-none absolute -inset-2 rounded-xl bg-brand-edge opacity-0", flashClassName)}
      />
      <span className="sr-only">{formatCount(value)}</span>
      <motion.span aria-hidden="true" className="relative">
        {display}
      </motion.span>
    </span>
  );
}
