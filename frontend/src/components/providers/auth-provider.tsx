"use client";

import React, { useEffect } from "react";
import { useAuthStore } from "@/store/useAuthStore";

interface AuthProviderProps {
  children: React.ReactNode;
}

/**
 * ============================================================================
 * GLOBAL CLIENT PROVIDER FOR ZUSTAND AUTH HYDRATION
 * ============================================================================
 * Quản lý khôi phục (Hydration) toàn vẹn phiên định danh y khoa lúc tải trang.
 * Tự động kiểm tra Cookie và truy vết về máy chủ FastAPI (/api/v1/auth/me) để nạp lại
 * Global State nếu người dùng đã đăng nhập từ trước, chống mất mát trạng thái khi Refresh/F5.
 */
export function AuthProvider({ children }: AuthProviderProps) {
  const hydrate = useAuthStore((state) => state.hydrate);

  useEffect(() => {
    // Khởi động chu trình khôi phục phiên làm việc khi app mounted
    hydrate();
  }, [hydrate]);

  return <>{children}</>;
}
