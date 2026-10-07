"use client";

import React, { useEffect } from "react";
import { useRouter, usePathname } from "next/navigation";
import { useAuthStore } from "@/store/useAuthStore";
import { Loader2, ShieldCheck } from "lucide-react";
import { getHomeRouteForRole } from "@/lib/auth-routing";

export interface GuestGuardProps {
  children: React.ReactNode;
}

/**
 * ============================================================================
 * CLIENT ROUTING FIREWALL - GUEST ONLY GUARD FOR AUTH SCREENS
 * ============================================================================
 * Lớp rào chắn tự động ngắt truy cập vào các trang Đăng nhập / Đăng ký
 * khi hệ thống phát hiện Bác sĩ / Điều dưỡng / Bệnh nhân ĐÃ ĐĂNG NHẬP (isAuthenticated).
 * Tránh hoàn toàn sạn UX (user đã đăng nhập nhưng vẫn thấy form login/register).
 */
export const GuestGuard: React.FC<GuestGuardProps> = ({ children }) => {
  const { isAuthenticated, isLoading, user } = useAuthStore();
  const router = useRouter();
  const pathname = usePathname();

  useEffect(() => {
    // Không cản trở luồng callback của OAuth2 / SSO lúc đang xử lý token
    if (pathname && pathname.includes("/auth/callback")) {
      return;
    }

    // Nếu người dùng đã đăng nhập hợp lệ và không trong trạng thái tải trang
    if (!isLoading && isAuthenticated && user) {
      router.replace(getHomeRouteForRole(user.role));
    }
  }, [isAuthenticated, isLoading, router, user, pathname]);

  // Cho phép đi qua nếu là luồng callback của OAuth2 / SSO
  if (pathname && pathname.includes("/auth/callback")) {
    return <>{children}</>;
  }

  // Nếu đang kiểm tra phiên hoặc đang chuẩn bị điều hướng vì phát hiện đã log in
  if (isLoading || isAuthenticated) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[350px] p-6 text-center space-y-5 bg-background/80 border border-border/80 rounded-2xl backdrop-blur-xl animate-pulse">
        <div className="w-14 h-14 rounded-2xl bg-sky-500/15 border border-sky-500/30 flex items-center justify-center text-sky-600 shadow-md">
          <Loader2 className="w-7 h-7 animate-spin" />
        </div>

        <div className="space-y-1.5 max-w-sm">
          <div className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-emerald-100 text-emerald-800 font-mono text-[11px] font-extrabold mb-1">
            <ShieldCheck className="w-3.5 h-3.5 text-emerald-600" />
            <span>PHIÊN LÀM VIỆC AN TOÀN ĐANG HOẠT ĐỘNG</span>
          </div>
          <h3 className="text-base font-extrabold text-foreground">
            Đang đồng bộ điều hướng lâm sàng...
          </h3>
          <p className="text-xs text-slate-600 leading-relaxed font-normal dark:text-slate-300">
            Hệ thống phát hiện tài khoản <strong className="text-sky-700 font-bold">{user?.name || user?.email || "của bạn"}</strong> đã đăng nhập. Đang chuyển tới không gian làm việc phù hợp với vai trò.
          </p>
        </div>
      </div>
    );
  }

  // Trường hợp khách (Guest / Chưa đăng nhập) -> Mở khóa hiển thị form Login/Register
  return <>{children}</>;
};
