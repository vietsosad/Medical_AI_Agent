"use client";

import { useEffect, useState, type RefObject } from "react";
import { useReducedMotion } from "framer-motion";

interface DemoTimelineOptions {
  /** Khung dừng lại khi người xem đã tắt hiệu ứng chuyển động: khung kể trọn câu chuyện. */
  finalStep: number;
  /** Người xem đang rê chuột vào để đọc: giữ nguyên khung hiện tại. */
  hold?: boolean;
}

export interface DemoTimeline {
  step: number;
  /** Số vòng đã chạy xong. Đổi giá trị này làm khóa để dựng lại cảnh từ đầu mỗi vòng. */
  cycle: number;
  running: boolean;
}

function useInViewport(ref: RefObject<Element | null>): boolean {
  // Không có IntersectionObserver (môi trường kiểm thử, trình duyệt rất cũ): coi như đang hiện.
  const [inView, setInView] = useState(() => typeof IntersectionObserver !== "function");

  useEffect(() => {
    const element = ref.current;
    if (!element || typeof IntersectionObserver !== "function") return;
    const observer = new IntersectionObserver(([entry]) => setInView(entry.isIntersecting), { threshold: 0.25 });
    observer.observe(element);
    return () => observer.disconnect();
  }, [ref]);

  return inView;
}

function useDocumentVisible(): boolean {
  const [visible, setVisible] = useState(
    () => typeof document === "undefined" || document.visibilityState === "visible",
  );

  useEffect(() => {
    const sync = () => setVisible(document.visibilityState === "visible");
    document.addEventListener("visibilitychange", sync);
    return () => document.removeEventListener("visibilitychange", sync);
  }, []);

  return visible;
}

/**
 * Đồng hồ của các phiên mẫu trên trang chủ: đi lần lượt qua các mốc thời gian
 * (`stepStartsMs`, mốc đầu là 0) rồi quay lại từ đầu sau `cycleMs`.
 *
 * Chỉ đếm khi khối đang nằm trên màn hình, tab đang mở và không ai rê chuột vào
 * đọc; ra khỏi màn hình là đứng yên, không tốn một khung hình nào. Người đã tắt
 * hiệu ứng chuyển động thấy ngay `finalStep` và cảnh không lặp lại.
 */
export function useDemoTimeline(
  ref: RefObject<Element | null>,
  stepStartsMs: readonly number[],
  cycleMs: number,
  { finalStep, hold = false }: DemoTimelineOptions,
): DemoTimeline {
  const reduced = Boolean(useReducedMotion());
  const inView = useInViewport(ref);
  const documentVisible = useDocumentVisible();
  const [position, setPosition] = useState({ step: 0, cycle: 0 });

  const running = !reduced && inView && documentVisible && !hold;
  const lastStep = stepStartsMs.length - 1;

  useEffect(() => {
    if (!running) return;
    const { step } = position;
    const wraps = step >= lastStep;
    const delay = wraps ? cycleMs - stepStartsMs[lastStep] : stepStartsMs[step + 1] - stepStartsMs[step];
    const timer = window.setTimeout(() => {
      setPosition((current) =>
        wraps ? { step: 0, cycle: current.cycle + 1 } : { step: current.step + 1, cycle: current.cycle },
      );
    }, Math.max(delay, 16));
    return () => window.clearTimeout(timer);
  }, [running, position, lastStep, cycleMs, stepStartsMs]);

  return reduced
    ? { step: finalStep, cycle: 0, running: false }
    : { step: position.step, cycle: position.cycle, running };
}
