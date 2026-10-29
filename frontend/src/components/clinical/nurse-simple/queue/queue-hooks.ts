"use client";

import { useEffect, useState } from "react";

const NO_ARRIVALS: ReadonlySet<string> = new Set();

interface ArrivalState {
  key: string;
  known: ReadonlySet<string>;
  arrivals: ReadonlySet<string>;
}

/**
 * Mã các ca vừa xuất hiện so với lần dữ liệu trước của cùng một danh sách.
 *
 * Lần dữ liệu đầu tiên không có ca nào "vừa tới": đó là cả danh sách hiện lên,
 * và nó nổi lên lần lượt. Từ lần thứ hai, một ca mới chen vào được đánh dấu để
 * hàng của nó trượt vào và sáng lên một nhịp; hàng đã có sẵn thì không diễn
 * hoạt lại khi hàng đợi tự làm mới.
 *
 * Cập nhật state ngay trong lúc render (mẫu "điều chỉnh state khi prop đổi"
 * của React) thay vì trong effect: React dựng lại component trước khi vẽ con,
 * nên hàng mới gắn vào DOM đã biết mình là ca vừa tới.
 */
export function useArrivals(ids: readonly string[]): ReadonlySet<string> {
  const key = ids.join("\n");
  const [state, setState] = useState<ArrivalState>(() => ({
    key,
    known: new Set(ids),
    arrivals: NO_ARRIVALS,
  }));

  if (state.key !== key) {
    const fresh = ids.filter((id) => !state.known.has(id));
    setState({ key, known: new Set(ids), arrivals: fresh.length > 0 ? new Set(fresh) : NO_ARRIVALS });
  }

  return state.arrivals;
}

/** Đồng hồ cho các nhãn "x giây trước"; chỉ component gọi nó vẽ lại mỗi nhịp. */
export function useNow(intervalMs: number): number {
  const [now, setNow] = useState(() => Date.now());
  useEffect(() => {
    const timer = window.setInterval(() => setNow(Date.now()), intervalMs);
    return () => window.clearInterval(timer);
  }, [intervalMs]);
  return now;
}

/**
 * Giá trị chậm lại một nhịp sau khi người dùng ngừng gõ, để ô tìm kiếm không
 * bắn một request (và một lần dựng lại danh sách) cho mỗi phím.
 */
export function useDebouncedValue<T>(value: T, delayMs: number): T {
  const [debounced, setDebounced] = useState(value);
  useEffect(() => {
    const timer = window.setTimeout(() => setDebounced(value), delayMs);
    return () => window.clearTimeout(timer);
  }, [value, delayMs]);
  return debounced;
}
