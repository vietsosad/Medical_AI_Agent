"use client";

import React, { createContext, useCallback, useContext, useEffect, useMemo, useSyncExternalStore } from "react";

import {
  type ResolvedTheme,
  type ThemePreference,
  applyTheme,
  readStoredPreference,
  resolveTheme,
  setThemePreference,
  subscribeToTheme,
  systemPrefersDark,
} from "@/lib/theme";

interface ThemeContextValue {
  /** Lựa chọn của người dùng, kể cả "system". */
  preference: ThemePreference;
  /** Chế độ đang thực sự hiển thị. */
  resolved: ResolvedTheme;
  setPreference: (next: ThemePreference) => void;
}

const ThemeContext = createContext<ThemeContextValue | null>(null);

/** Máy chủ không có localStorage lẫn matchMedia, nên nó luôn dựng ở "system"/sáng. */
const serverPreference = (): ThemePreference => "system";
const serverPrefersDark = (): boolean => false;

/**
 * Nguồn sự thật duy nhất cho chế độ sáng/tối.
 *
 * Chế độ hiển thị không phải state của React: nó nằm ở localStorage và ở cài
 * đặt hệ điều hành. Vì vậy nó được **đọc** qua `useSyncExternalStore` thay vì
 * sao chép vào state rồi đồng bộ ngược bằng effect — cách đó vừa gây render dây
 * chuyền, vừa bỏ sót trường hợp người dùng đổi chế độ ở một tab khác.
 *
 * Thứ tự khởi tạo có chủ đích: đoạn mã nội tuyến trong `layout.tsx` đã gắn class
 * `.dark` lên `<html>` **trước khi** React chạy, nên provider này không vẽ lại
 * giao diện lúc khởi động — nó chỉ tiếp quản trạng thái đã có. Nhờ vậy không có
 * cú chớp trắng ở lần tải đầu.
 */
export function ThemeProvider({ children }: { children: React.ReactNode }) {
  const preference = useSyncExternalStore(
    subscribeToTheme,
    readStoredPreference,
    serverPreference,
  );
  const prefersDark = useSyncExternalStore(
    subscribeToTheme,
    systemPrefersDark,
    serverPrefersDark,
  );

  const resolved = resolveTheme(preference, prefersDark);

  // Effect duy nhất, và nó làm đúng việc effect sinh ra để làm: đẩy trạng thái
  // của React ra một hệ thống bên ngoài (thẻ <html>), không đặt state nào cả.
  useEffect(() => {
    applyTheme(resolved);
  }, [resolved]);

  const setPreference = useCallback((next: ThemePreference) => {
    setThemePreference(next);
  }, []);

  const value = useMemo<ThemeContextValue>(
    () => ({ preference, resolved, setPreference }),
    [preference, resolved, setPreference],
  );

  return <ThemeContext.Provider value={value}>{children}</ThemeContext.Provider>;
}

/**
 * Trả về `null` khi được gọi ngoài provider, thay vì ném lỗi.
 *
 * Nút chuyển chế độ nằm trên thanh điều hướng, mà thanh này cũng được dựng
 * trong các bài kiểm thử lẻ không bọc provider. Một component điều khiển giao
 * diện không đáng để làm sập cả trang chỉ vì thiếu context.
 */
export function useTheme(): ThemeContextValue | null {
  return useContext(ThemeContext);
}
