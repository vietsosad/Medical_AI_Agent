"use client";

import { MotionConfig } from "framer-motion";

import { enterTransition } from "@/lib/motion";

/**
 * Một chỗ duy nhất quyết định chuyển động cho toàn ứng dụng: người dùng bật
 * "giảm chuyển động" ở hệ điều hành thì mọi motion component tự bỏ dịch
 * chuyển và chỉ giữ độ mờ, không component nào phải tự kiểm tra lại.
 */
export function MotionProvider({ children }: { children: React.ReactNode }) {
  return (
    <MotionConfig reducedMotion="user" transition={enterTransition}>
      {children}
    </MotionConfig>
  );
}
