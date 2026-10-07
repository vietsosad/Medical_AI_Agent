"use client";

import React, { useState } from "react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { 
  BarChart3, 
  Database, 
  FileCheck, 
  ShieldAlert, 
  ChevronLeft, 
  ChevronRight, 
  Server, 
  ArrowLeft, 
  LogOut, 
  Zap,
  Cpu
} from "lucide-react";
import { cn } from "@/lib/utils";
import { useAuthStore, type UserProfile } from "@/store/useAuthStore";
import { toast } from "sonner";

/**
 * ============================================================================
 * [ADMIN ANALYTICS SIDEBAR] THANH ĐIỀU HƯỚNG DỌC KHỐI QUẢN TRỊ AI OPS
 * ============================================================================
 * Tối giản - Rõ chiết - Phân lập biểu đồ số liệu.
 * - Hỗ trợ tính năng gập gỡ (Collapsible) để giải phóng diện tích màn hình biểu đồ Recharts.
 * - Cam kết không làm việc thay Bác sĩ (Không có nút ra quyết định hay chẩn đoán lâm sàng).
 */
export const AdminSidebar: React.FC = () => {
  const pathname = usePathname() || "/admin";
  const router = useRouter();
  const { user, loginSuccess, logout } = useAuthStore();
  const [isCollapsed, setIsCollapsed] = useState(false);

  // Danh mục chuyên trách của Kỹ Sư AI Ops & Quản Trị Hệ Thống
  const adminNavItems = [
    { 
      label: "Thống Kê Concordance Rate", 
      href: "/admin", 
      icon: BarChart3,
      badge: "KPI",
      badgeColor: "bg-emerald-50 text-emerald-800 border border-emerald-200"
    },
    { 
      label: "Quản Trị Kho Phác Đồ", 
      href: "/admin/rag-database", 
      icon: Database,
      badge: "VECTOR",
      badgeColor: "bg-sky-50 text-sky-800 border border-sky-200"
    },
    { 
      label: "Hồ Sơ Kiểm Cứu (Audit Logs)", 
      href: "/admin/audit-logs", 
      icon: FileCheck,
      badge: "SECURE",
      badgeColor: "bg-amber-50 text-amber-900 border border-amber-300"
    },
    { 
      label: "Cấu Hình AI Guardrails", 
      href: "/admin/guardrails", 
      icon: ShieldAlert,
      badge: null
    }
  ];

  // Kích hoạt nhanh quyền Quản Trị Viên System Admin Demo
  const handleSwitchToAdmin = () => {
    const demoAdmin: UserProfile = {
      id: "sys-admin-demo-01",
      name: "Trưởng Quản Trị Hệ Thống & RAG Ops",
      email: "admin.ops@ai20k.clinical.vn",
      role: "SYSTEM_ADMIN",
      department: "Trung Tâm Kỹ Thuật AI & Hạ Tầng Y Tế",
      phoneNumber: "0988000999"
    };
    loginSuccess(demoAdmin, "demo_access_token_admin_01");
    toast.success("Đã kích hoạt quyền Quản Trị Viên Hệ Thống (AI Ops).");
  };

  return (
    <aside 
      className={cn(
        "relative flex flex-col justify-between bg-slate-900 border-r border-slate-800 text-slate-200 transition-all duration-300 z-40 select-none shadow-xl",
        isCollapsed ? "w-20" : "w-72"
      )}
    >
      {/* NÚT GẬP MỞ SIDEBAR NẰM TRỰC DIỆN SƯỜN BẢ */}
      <button
        type="button"
        onClick={() => setIsCollapsed(!isCollapsed)}
        className="absolute -right-3.5 top-8 w-7 h-7 bg-blue-600 hover:bg-blue-500 text-white rounded-full flex items-center justify-center shadow-md border border-slate-900 transition-transform active:scale-95 z-50 cursor-pointer"
        title={isCollapsed ? "Mở rộng thanh quản trị" : "Thu gọn thanh quản trị"}
      >
        {isCollapsed ? <ChevronRight className="w-4 h-4 stroke-[3]" /> : <ChevronLeft className="w-4 h-4 stroke-[3]" />}
      </button>

      <div className="flex flex-col space-y-6 p-4">
        {/* LOGO & HUY HIỆU AI OPS SERVER */}
        <div className={cn("flex items-center gap-3 py-2", isCollapsed && "justify-center")}>
          <div className="w-11 h-11 rounded-2xl bg-blue-600 text-white flex items-center justify-center shadow-lg shadow-blue-600/25 shrink-0">
            <Server className="w-6 h-6 stroke-[2]" />
          </div>
          {!isCollapsed && (
            <div className="overflow-hidden">
              <div className="flex items-center gap-1.5">
                <span className="text-lg font-bold text-white tracking-tight">AI20K-OPS</span>
              </div>
              <div className="inline-flex items-center gap-1 text-xs text-slate-400 font-medium">
                <Cpu className="w-3.5 h-3.5 text-slate-400 shrink-0" />
                <span>RAG Analytics Engine</span>
              </div>
            </div>
          )}
        </div>

        {/* DANH SÁCH MODULE ĐIỀU HÀNH QUẢN TRỊ */}
        <nav className="space-y-1.5">
          {!isCollapsed && (
            <div className="px-3.5 py-1.5 text-xs font-semibold text-slate-400 tracking-wide">
              Danh mục hệ thống
            </div>
          )}

          {adminNavItems.map((item) => {
            const Icon = item.icon;
            const isActive = pathname === item.href;
            
            return (
              <Link
                key={item.href}
                href={item.href}
                title={isCollapsed ? item.label : undefined}
                className={cn(
                  "group relative flex items-center gap-3 px-3.5 py-2.5 rounded-xl font-medium text-sm transition-all min-h-[40px]",
                  isActive
                    ? "bg-slate-800 text-white font-semibold shadow-md border border-slate-700/80"
                    : "text-slate-400 hover:bg-slate-800/60 hover:text-slate-200"
                )}
              >
                <Icon className={cn("w-4.5 h-4.5 shrink-0 transition-transform group-hover:scale-105", isActive ? "text-white" : "text-slate-400")} />
                {!isCollapsed && (
                  <span className="flex-1 truncate">{item.label}</span>
                )}
                {!isCollapsed && item.badge && (
                  <span className={cn("px-2 py-0.5 rounded-md text-xs font-semibold", item.badgeColor)}>
                    {item.badge}
                  </span>
                )}
              </Link>
            );
          })}
        </nav>
      </div>

      {/* KHỐI TRẠNG THÁI TÀI KHOẢN QUẢN TRỊ & THOÁT HỆ THỐNG */}
      <div className="p-3 border-t border-slate-800 space-y-3 bg-slate-950/70">
        {!isCollapsed && (
          <div className="p-3 rounded-xl bg-slate-900 border border-slate-800 space-y-2 shadow-2xs">
            <div className="flex items-center justify-between text-xs font-semibold text-slate-400">
              <span>Trạng thái server:</span>
              <span className="text-emerald-400 font-semibold">ONLINE</span>
            </div>
            {user ? (
              <div className="text-xs space-y-1">
                <p className="font-semibold text-white leading-tight truncate">{user.name}</p>
                <div className="flex items-center justify-between">
                  <span className="text-xs text-slate-300 font-medium bg-slate-800 px-2 py-0.5 rounded-md border border-slate-700">
                    {user.role}
                  </span>
                  <button
                    type="button"
                    onClick={() => {
                      logout();
                      router.push("/auth/login");
                    }}
                    className="p-1.5 rounded-lg text-slate-400 hover:text-rose-400 hover:bg-rose-950/40 transition-colors"
                    title="Đăng xuất khỏi trạm Ops"
                  >
                    <LogOut className="w-4 h-4" />
                  </button>
                </div>
              </div>
            ) : (
              <button
                type="button"
                onClick={handleSwitchToAdmin}
                className="w-full py-2 px-3 rounded-xl bg-blue-600 text-white font-bold text-xs flex items-center justify-center gap-1.5 min-h-[36px]"
              >
                <Zap className="w-3.5 h-3.5 text-blue-200" />
                <span>Kích Hoạt Quyền Admin</span>
              </button>
            )}
          </div>
        )}

        <Link
          href="/triage"
          title={isCollapsed ? "Trở về Cổng Bệnh nhân Top Bar" : undefined}
          className={cn(
            "w-full py-3 px-3.5 rounded-2xl bg-slate-800 hover:bg-slate-700 text-slate-300 hover:text-white font-extrabold text-xs transition-all flex items-center gap-2.5 border border-slate-700 min-h-[44px] shadow-sm",
            isCollapsed && "justify-center px-0"
          )}
        >
          <ArrowLeft className="w-4.5 h-4.5 text-blue-400 shrink-0 stroke-[2.5]" />
          {!isCollapsed && <span>Về Cổng Bệnh Nhân (Top Bar)</span>}
        </Link>
      </div>
    </aside>
  );
};

export default AdminSidebar;
