"use client";

import React, { useEffect } from "react";
import { Loader2, ShieldCheck } from "lucide-react";
import { usePathname, useRouter } from "next/navigation";

import { getHomeRouteForRole } from "@/lib/auth-routing";
import { useAuthStore } from "@/store/useAuthStore";

interface PatientRoleGuardProps {
  children: React.ReactNode;
}

/**
 * Các tuyến trong nhóm (patient) vẫn mở cho khách chưa đăng nhập.
 *
 * `/triage/guest-session` là một điểm vào xác thực (nút "Bỏ Qua Đăng Nhập" trên
 * màn hình Đăng nhập/Đăng ký): nó gọi `authService.loginAsGuest()` rồi mới đưa
 * người dùng sang `/triage`. Chặn tuyến này sẽ phá luồng khám nhanh khẩn cấp.
 */
const PUBLIC_PATIENT_ROUTES = ["/triage/guest-session"] as const;

const LOGIN_ROUTE = "/auth/login?reason=auth_required";

function isPublicPatientRoute(pathname: string): boolean {
  return PUBLIC_PATIENT_ROUTES.some(
    (route) => pathname === route || pathname.startsWith(`${route}/`),
  );
}

/**
 * ============================================================================
 * [PATIENT ROLE GUARD] CỔNG BỆNH NHÂN: BẮT BUỘC ĐĂNG NHẬP & TÁCH KHỎI CỔNG LÂM SÀNG
 * ============================================================================
 * Cơ chế hoạt động:
 * 1. Chờ khôi phục token trước khi hiển thị nội dung để tránh nháy sai giao diện.
 * 2. Khách chưa đăng nhập được đưa về luồng đăng nhập hiện có (trừ các tuyến công khai).
 * 3. Chỉ Bệnh nhân hoặc Khách khẩn cấp đã có phiên mới được vào luồng bệnh nhân.
 * 4. Nhân viên y tế và quản trị viên được chuyển về đúng không gian theo vai trò.
 */
export const PatientRoleGuard: React.FC<PatientRoleGuardProps> = ({ children }) => {
  const router = useRouter();
  const pathname = usePathname() || "";
  const { user, isAuthenticated, isLoading } = useAuthStore();

  const isPublicRoute = isPublicPatientRoute(pathname);
  const hasPatientRole = user?.role === "PATIENT" || user?.role === "GUEST";
  const deniedUser = !isLoading && isAuthenticated && user && !hasPatientRole ? user : null;

  const requiresLogin = !isLoading && !isAuthenticated && !isPublicRoute;
  const destination = requiresLogin
    ? LOGIN_ROUTE
    : deniedUser
      ? getHomeRouteForRole(deniedUser.role)
      : null;
  const shouldRedirect = destination !== null;

  useEffect(() => {
    if (destination) {
      router.replace(destination);
    }
  }, [destination, router]);

  if (isLoading || (isAuthenticated && !user) || shouldRedirect) {
    return (
      <main
        className="flex min-h-[70vh] items-center justify-center bg-background p-6"
        aria-busy="true"
        aria-label="Đang kiểm tra quyền truy cập cổng bệnh nhân"
      >
        <div className="flex items-center gap-3 rounded-xl border border-border bg-card px-5 py-4 text-sm font-medium text-slate-700 dark:text-slate-200">
          <span className="relative flex size-9 items-center justify-center rounded-lg bg-sky-50 text-sky-700">
            <ShieldCheck className="size-5" aria-hidden="true" />
            <Loader2 className="absolute -right-1 -top-1 size-4 animate-spin text-sky-700" aria-hidden="true" />
          </span>
          {requiresLogin
            ? "Chức năng này cần đăng nhập. Đang chuyển tới trang đăng nhập..."
            : "Đang kiểm tra quyền và chuyển hướng an toàn..."}
        </div>
      </main>
    );
  }

  return (
    <div className="w-full min-h-full flex flex-col font-sans bg-background">
      <div className="flex-1 flex flex-col">
        {children}
      </div>
    </div>
  );
};

export default PatientRoleGuard;
