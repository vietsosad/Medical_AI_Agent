"use client";

import { useSyncExternalStore } from "react";

const subscribe = () => () => {};
const getSnapshot = () => window.location.search;
const getServerSnapshot = () => null;

/**
 * Chuỗi truy vấn hiện tại của URL, chỉ để hiển thị.
 *
 * Không dùng `useSearchParams` vì ở trang tĩnh hook đó bắt phải bọc Suspense
 * khi build. `null` nghĩa là chưa biết (đang render ở máy chủ hoặc đang
 * hydrate); chuỗi rỗng nghĩa là URL không có tham số nào.
 */
export function useLocationSearch(): string | null {
  return useSyncExternalStore<string | null>(subscribe, getSnapshot, getServerSnapshot);
}
