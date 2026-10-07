"use client";

import React from "react";
import Link from "next/link";
import { useAuthStore, type UserProfile } from "@/store/useAuthStore";
import { 
  ShieldAlert, 
  ArrowLeft, 
  KeyRound, 
  Server, 
  UserCheck,
  Zap
} from "lucide-react";
import { toast } from "sonner";

interface AdminRoleGuardProps {
  children: React.ReactNode;
}

/**
 * ============================================================================
 * [ADMIN ROLE GUARD] TƯỜNG LỬA BẢO ĐẢM QUYỀN HẠN QUẢN TRỊ HỆ THỐNG & AI OPS
 * ============================================================================
 * Tuân thủ tuyệt đối Ma trận phân quyền RBAC:
 * - Chỉ cho phép tài khoản SYSTEM_ADMIN hoặc AI_OPS truy cập khu vực /admin.
 * - Bác sĩ, Điều dưỡng và Bệnh nhân KHÔNG ĐƯỢC thâm nhập vào hạ tầng chỉ mục RAG hay cấu hình máy chủ.
 * - Ngôn ngữ thị giác Xanh Navy tinh nhã, không dùng emoji thô sương, nút bấm lớn >= 44px.
 */
export const AdminRoleGuard: React.FC<AdminRoleGuardProps> = ({ children }) => {
  const { user, isAuthenticated, loginSuccess } = useAuthStore();

  // Chỉ danh sách quyền Hệ thống & Quản trị trung tâm được cấp phép
  const isSystemAdmin = isAuthenticated && user && [
    "SYSTEM_ADMIN",
    "AI_OPS"
  ].includes(user.role);

  // Nút chuyển nhanh tài khoản sang Admin Demo để thuận tiện kiểm thử
  const handleQuickSwitchToAdmin = () => {
    const demoAdmin: UserProfile = {
      id: "sys-admin-demo-01",
      name: "Trưởng Quản Trị Hệ Thống & RAG Ops",
      email: "admin.ops@ai20k.clinical.vn",
      role: "SYSTEM_ADMIN",
      department: "Trung Tâm Kỹ Thuật AI & Hạ Tầng Y Tế",
      phoneNumber: "0988000999"
    };

    loginSuccess(demoAdmin, "demo_access_token_admin_01");
    toast.success("Đã kích hoạt quyền Quản Trị Viên Hệ Thống. Sẵn sàng vào trạm phân tích số liệu.");
  };

  if (isSystemAdmin) {
    return <>{children}</>;
  }

  return (
    <div className="min-h-[85vh] w-full bg-background flex items-center justify-center p-4 sm:p-8 font-sans">
      <div className="max-w-xl w-full bg-card border border-border shadow-xl rounded-3xl p-8 text-center space-y-7 animate-in fade-in zoom-in-95 duration-200">
        {/* ICON KHÓA QUẢN TRỊ - TÔNG SLATE-900 & TRUST BLUE */}
        <div className="w-20 h-20 bg-slate-900 text-white rounded-3xl flex items-center justify-center mx-auto shadow-md shadow-slate-900/20">
          <Server className="w-10 h-10 stroke-[2.2] text-blue-400" />
        </div>

        {/* TIÊU ĐỀ & TRÍCH LỤC QUY TẮC PHÂN VÀO */}
        <div className="space-y-2.5">
          <div className="inline-flex items-center gap-2 px-3.5 py-1 rounded-full bg-muted text-slate-800 border border-slate-300 text-xs font-black tracking-wider uppercase font-mono dark:text-slate-100 dark:border-slate-700">
            <ShieldAlert className="w-4 h-4 text-blue-600 stroke-[2.5]" />
            <span>Khu Vực Quản Trị Trung Tâm • System Admin Only</span>
          </div>
          <h2 className="text-2xl sm:text-3xl font-black text-foreground tracking-tight">
            Trạm Phân Tích & Quản Trị AI Ops
          </h2>
          <p className="text-sm sm:text-base text-slate-600 font-medium leading-relaxed max-w-md mx-auto dark:text-slate-300">
            Không gian kiểm kê dữ liệu RAG, Concordance Rate và tham số an toàn y khoa chỉ cho phép <strong className="text-blue-700 font-extrabold">Quản trị viên Hệ thống (System Admin)</strong> hoặc <strong className="text-blue-700 font-extrabold">Kỹ sư AI Ops</strong> thao tác.
          </p>
        </div>

        {/* THÔNG TIN TÀI KHOẢN HIỆN TẠI */}
        <div className="p-4 rounded-2xl bg-background border border-border text-left text-xs space-y-2 font-mono">
          <div className="flex items-center justify-between text-muted-foreground font-bold">
            <span>Vai trò đang kích hoạt:</span>
            <span className={isAuthenticated ? "text-blue-700 font-extrabold" : "text-muted-foreground"}>
              {isAuthenticated ? `Quyền ${user?.role}` : "Chưa đăng ký quyền quản trị"}
            </span>
          </div>
          {user && (
            <div className="text-slate-800 font-extrabold flex items-center gap-2 font-sans pt-2 border-t border-border dark:text-slate-100">
              <UserCheck className="w-4.5 h-4.5 text-blue-600 shrink-0" />
              <span>Tài khoản: {user.name} ({user.email})</span>
            </div>
          )}
        </div>

        {/* CÁC PHÍM CHUYỂN HOÁN CỘNG THỜI GIAN NHANH CHÓNG */}
        <div className="space-y-4 pt-1">
          <button
            type="button"
            onClick={handleQuickSwitchToAdmin}
            className="w-full py-4 px-6 rounded-2xl bg-blue-600 hover:bg-blue-700 text-white font-black text-sm uppercase tracking-wider transition-all shadow-md shadow-blue-600/25 flex items-center justify-center gap-2.5 cursor-pointer active:scale-95 group"
          >
            <Zap className="w-5 h-5 text-blue-200 animate-pulse shrink-0 transition-transform group-hover:scale-110" />
            <span>Kích Hoạt Quyền Demo: Quản Trị Viên System Admin</span>
          </button>
          <p className="text-[11px] text-muted-foreground font-semibold italic">
            Nhấn phím xanh dương bên trên để đăng nhập nhanh với vai trò Quản Trị Viên và tiếp cận khu vực giám sát AI ngay.
          </p>

          <div className="flex items-center justify-between gap-3.5 pt-4 border-t border-border/80">
            <Link
              href="/triage"
              className="flex-1 py-3.5 px-4 rounded-xl bg-muted hover:bg-slate-200 text-slate-700 font-extrabold text-xs sm:text-sm transition-all flex items-center justify-center gap-2 min-h-[44px] dark:text-slate-200 dark:hover:bg-slate-700"
            >
              <ArrowLeft className="w-4 h-4 stroke-[2.5]" />
              <span>Cổng Bệnh Nhân</span>
            </Link>

            <Link
              href="/clinical/queue"
              className="flex-1 py-3.5 px-4 rounded-xl bg-card hover:bg-background text-blue-700 font-extrabold text-xs sm:text-sm border-2 border-blue-200 hover:border-blue-500 transition-all flex items-center justify-center gap-2 min-h-[44px]"
            >
              <KeyRound className="w-4 h-4 text-blue-600 stroke-[2.5]" />
              <span>Trạm Bác Sĩ</span>
            </Link>
          </div>
        </div>
      </div>
    </div>
  );
};

export default AdminRoleGuard;
