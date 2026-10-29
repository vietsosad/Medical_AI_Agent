"use client";

import React, { useEffect } from "react";
import { useRouter, usePathname } from "next/navigation";
import { useAuthStore } from "@/store/useAuthStore";
import { Loader2 } from "lucide-react";
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

  // Đang kiểm tra phiên (mọi lần mở trang, kể cả khách chưa đăng nhập) hoặc đã
  // biết là đã đăng nhập và đang chuyển trang. Hai trường hợp nói hai câu khác
  // nhau: lúc đang kiểm tra thì chưa thể nói ai đã đăng nhập.
  if (isLoading || isAuthenticated) {
    const redirecting = isAuthenticated && !isLoading;
    return (
      <div
        role="status"
        aria-live="polite"
        className="flex min-h-80 flex-col items-center justify-center gap-4 p-6 text-center"
      >
        <span className="flex size-12 items-center justify-center rounded-2xl bg-brand-soft text-brand" aria-hidden="true">
          <Loader2 className="size-6 motion-safe:animate-spin" />
        </span>
        <p className="max-w-sm text-base leading-7 text-muted-foreground">
          {redirecting ? (
            <>
              Bạn đã đăng nhập
              {user?.name || user?.email ? (
                <>
                  {" "}với tài khoản <strong className="font-semibold text-foreground">{user?.name || user?.email}</strong>
                </>
              ) : null}
              . Đang chuyển tới trang của bạn…
            </>
          ) : (
            "Đang kiểm tra phiên đăng nhập…"
          )}
        </p>
      </div>
    );
  }

  // Trường hợp khách (Guest / Chưa đăng nhập) -> Mở khóa hiển thị form Login/Register
  return <>{children}</>;
};
