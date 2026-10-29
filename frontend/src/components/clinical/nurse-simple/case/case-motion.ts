"use client";

import { useState } from "react";
import type { MotionProps } from "framer-motion";

import { enterTransition } from "@/lib/motion";

/**
 * Nổi lên 8 px theo token chung, có độ trễ để các khối của hồ sơ ca hiện lên
 * theo đúng thứ tự đọc. Chỉ chạy khi phần tử được gắn vào cây: nhịp làm mới
 * 5 giây của ca không làm khối nào diễn hoạt lại.
 */
export function riseIn(delay = 0): Pick<MotionProps, "initial" | "animate" | "transition"> {
  return {
    initial: { opacity: 0, y: 8 },
    animate: { opacity: 1, y: 0 },
    transition: { ...enterTransition, delay },
  };
}

/**
 * Tập id có mặt ở lần dựng đầu tiên. Mục có sẵn thì vào lần lượt; mục đến sau
 * (một lượt hội thoại mới trong ca còn đang trò chuyện) vào ngay, không phải
 * chờ đến lượt của mình trong một chuỗi đã chạy xong từ lâu.
 */
export function useInitialIds(ids: readonly string[]): ReadonlySet<string> {
  const [initial] = useState(() => new Set(ids));
  return initial;
}
