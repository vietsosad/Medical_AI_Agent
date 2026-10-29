"use client";

import { useCallback, useSyncExternalStore } from "react";

function canMatchMedia(): boolean {
  return typeof window !== "undefined" && typeof window.matchMedia === "function";
}

/**
 * Đọc một media query và cập nhật khi khung nhìn đổi. Máy chủ (và jsdom, vốn
 * không có `matchMedia`) luôn trả `false`, nên bố cục hẹp là bố cục mặc định.
 */
export function useMediaQuery(query: string): boolean {
  const subscribe = useCallback(
    (notify: () => void) => {
      if (!canMatchMedia()) return () => {};
      const list = window.matchMedia(query);
      list.addEventListener("change", notify);
      return () => list.removeEventListener("change", notify);
    },
    [query],
  );
  return useSyncExternalStore(
    subscribe,
    () => canMatchMedia() && window.matchMedia(query).matches,
    () => false,
  );
}
