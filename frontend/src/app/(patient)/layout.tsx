import React, { Suspense } from "react";
import { PatientRoleGuard } from "@/components/auth/patient-role-guard";
import { PatientRealtimeNotification } from "@/components/chat/PatientRealtimeNotification";
import { PatientBottomNav } from "@/components/shared/PatientBottomNav";

interface PatientLayoutProps {
  children: React.ReactNode;
}

/**
 * ============================================================================
 * [PATIENT PORTAL LAYOUT & RBAC SHIELD]
 * ============================================================================
 * Sử dụng thanh điều hướng chung ClinicalNavbar trên RootLayout để đảm bảo
 * sự thống nhất 100% khi chuyển tab và bảo đảm quyền riêng tư qua PatientRoleGuard.
 *
 * Trên điện thoại có thêm thanh điều hướng đáy (Sàng lọc / Lịch sử / Hồ sơ),
 * nằm trong PatientRoleGuard để chỉ hiện khi đã qua kiểm tra quyền. Thanh tự
 * ẩn trên màn hội thoại và tự chèn khoảng đệm để không che nội dung cuối trang.
 */
export default function PatientLayout({ children }: PatientLayoutProps) {
  return (
    <PatientRoleGuard>
      <Suspense fallback={null}>
        <PatientRealtimeNotification />
      </Suspense>
      <main className="flex-1 w-full max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6 sm:py-8 font-sans">
        {children}
      </main>
      <PatientBottomNav />
    </PatientRoleGuard>
  );
}
