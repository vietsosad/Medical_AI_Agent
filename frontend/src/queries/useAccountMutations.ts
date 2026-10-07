"use client";

import { useMutation } from "@tanstack/react-query";

import { authService } from "@/services/auth.service";
import { useAuthStore, type UserProfile } from "@/store/useAuthStore";

/**
 * Cập nhật số điện thoại liên lạc của chính chủ tài khoản đang đăng nhập.
 *
 * Máy chủ trả về hồ sơ định danh mới, được ghi thẳng vào Zustand auth store nên
 * giao diện hiển thị số mới ngay lập tức; lần tải trang sau, `hydrate()` đọc lại
 * từ `/api/v1/auth/me` nên dữ liệu vẫn khớp với cơ sở dữ liệu.
 */
export function useUpdatePhoneNumber() {
  const setUser = useAuthStore((state) => state.setUser);

  return useMutation<UserProfile, Error, string | null>({
    mutationFn: (phoneNumber) => authService.updatePhoneNumber(phoneNumber),
    onSuccess: (updatedUser) => {
      setUser(updatedUser);
    },
  });
}
