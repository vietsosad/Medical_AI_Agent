import React from "react";
import { AdminRoleGuard } from "@/components/auth/admin-role-guard";
import { AdminSidebar } from "@/components/admin/AdminSidebar";

interface AdminLayoutProps {
  children: React.ReactNode;
}

/**
 * ============================================================================
 * [ADMIN ANALYTICS WORKSTATION LAYOUT & RBAC SHIELD]
 * ============================================================================
 * Bao bọc phân khu /admin bởi tường lửa AdminRoleGuard và thanh Điều hướng dọc
 * AdminSidebar. Thiết lập không gian phân tích số liệu chuẩn mực, dễ nhìn,
 * không chồng chéo với quyền Bác Sĩ hay Bệnh Nhân.
 */
export default function AdminLayout({ children }: AdminLayoutProps) {
  return (
    <AdminRoleGuard>
      <div className="flex h-[calc(100vh)] w-full overflow-hidden bg-background font-sans text-foreground">
        {/* THANH ĐIỀU HƯỚNG DỌC QUẢN TRỊ VIÊN HỆ THỐNG */}
        <AdminSidebar />
        
        {/* VÙNG HIỆN THỊ BIỂU ĐỒ TRANG THỂ TÍCH TRM AN OVERVIEW */}
        <main className="flex-1 overflow-y-auto bg-background p-4 sm:p-6 lg:p-8 font-sans">
          <div className="max-w-7xl mx-auto h-full w-full">
            {children}
          </div>
        </main>
      </div>
    </AdminRoleGuard>
  );
}
