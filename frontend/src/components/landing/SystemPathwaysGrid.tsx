"use client";

import React from "react";
import Link from "next/link";
import { patientEntryHref } from "@/lib/auth-routing";
import { 
  MessageSquare, 
  FileText, 
  History, 
  ArrowRight, 
  CheckCircle2, 
  KeyRound,
  Sliders
} from "lucide-react";
import { useAuthStore } from "@/store/useAuthStore";
import { toast } from "sonner";

/**
 * Ba lối vào dành cho người bệnh. Tách thành dữ liệu thay vì ba khối JSX chép
 * tay: mọi thẻ chắc chắn dùng chung một hình dáng, một trạng thái hover và một
 * viền sáng -- sai lệch giữa chúng là thứ người đọc nhận ra trước cả nội dung.
 */
const PATHWAYS = [
  {
    label: "Triage AI",
    icon: MessageSquare,
    href: (isAuthenticated: boolean) => patientEntryHref("/triage", isAuthenticated),
    title: "Khám Triage AI",
    description:
      "Mô tả triệu chứng bằng lời tự nhiên. Trợ lý sẽ hỏi thêm từng bước để làm rõ thông tin.",
    cta: "Vào phòng chat Triage",
  },
  {
    label: "EHR Lite",
    icon: FileText,
    href: () => "/profile/ehr",
    title: "Hồ Sơ Y Khoa & SOS",
    description:
      "Lưu thông tin về cơ thể, bệnh nền, dị ứng, thuốc đang dùng và người liên hệ khẩn cấp.",
    cta: "Cập nhật hồ sơ sức khỏe",
  },
  {
    label: "Lịch sử khám",
    icon: History,
    href: (isAuthenticated: boolean) => patientEntryHref("/history", isAuthenticated),
    title: "Lịch sử trao đổi",
    description: "Xem lại các cuộc trao đổi trước đó khi bạn cần tham khảo.",
    cta: "Xem lịch sử",
  },
] as const;

export const SystemPathwaysGrid: React.FC = () => {
  const { user, isAuthenticated, logout } = useAuthStore();

  const handleLogout = async () => {
    await logout(false);
    toast.success("Bạn đã ngắt kết nối khỏi phiên làm việc y khoa an toàn.");
  };

  return (
    <section
      id="danh-ba-chuc-nang"
      className="scroll-mt-20 py-20 bg-slate-50 dark:bg-slate-900/80 border-b border-slate-200 dark:border-slate-800"
    >
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        
        {/* SECTION HEADER */}
        <div className="text-center max-w-3xl mx-auto mb-16">
          <div className="inline-flex items-center gap-2 px-3.5 py-1.5 rounded-full bg-slate-200/80 dark:bg-slate-800 text-slate-800 dark:text-slate-200 font-mono font-bold text-sm mb-4">
            <Sliders className="w-4 h-4 text-sky-600 dark:text-sky-400 stroke-[2.2]" />
            <span>DANH BẠ CHỨC NĂNG DÀNH CHO NGƯỜI BỆNH</span>
          </div>
          <h2 className="font-heading text-3xl sm:text-4xl font-extrabold text-slate-900 dark:text-white tracking-tight">
            Các tính năng hỗ trợ <br />
            <span className="text-sky-600 dark:text-sky-400">trao đổi và lưu thông tin sức khỏe</span>
          </h2>
          <p className="mt-3 text-base sm:text-lg font-medium text-slate-600 dark:text-slate-300">
            Truy cập nhanh phần trao đổi triệu chứng, hồ sơ sức khỏe và lịch sử của bạn.
          </p>

          {/* AUTHENTICATION ACTION STATUS BAR */}
          <div className="mt-6 flex flex-col sm:flex-row items-center justify-center gap-4">
            {isAuthenticated && user ? (
              <div className="flex items-center gap-3 bg-white dark:bg-slate-950 px-5 py-3 rounded-xl border border-slate-300 dark:border-slate-700 shadow-sm text-sm font-bold text-slate-800 dark:text-slate-200">
                <span className="live-dot w-2.5 h-2.5 rounded-full bg-emerald-500 shrink-0" />
                <span>Đang kết nối: {user.name || user.email || "Bác sĩ / Điều phối viên"}</span>
                <Link
                  href={patientEntryHref("/profile/ehr", isAuthenticated)}
                  className="ml-2 underline text-sky-600 dark:text-sky-400 hover:text-sky-700"
                >
                  Hồ Sơ EHR
                </Link>
                <button
                  type="button"
                  onClick={handleLogout}
                  className="glow-soft glow-rose ml-3 px-3 py-1.5 rounded-lg border border-rose-200 dark:border-rose-900 bg-rose-100 dark:bg-rose-950/80 text-rose-800 dark:text-rose-300 hover:bg-rose-200 dark:hover:bg-rose-900 font-bold min-h-[44px] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-rose-600 focus-visible:ring-offset-2"
                >
                  Đăng Xuất
                </button>
              </div>
            ) : (
              <Link
                href="/auth/login"
                className="group/login glow-soft glow-sky inline-flex items-center justify-center min-h-[48px] px-6 py-3 text-base font-bold text-slate-800 dark:text-slate-200 bg-white dark:bg-slate-800 hover:bg-slate-100 dark:hover:bg-slate-700 border border-slate-300 dark:border-slate-600 rounded-xl shadow-xs focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-sky-600 focus-visible:ring-offset-2"
              >
                <KeyRound className="w-5 h-5 mr-2.5 text-sky-600 dark:text-sky-400 stroke-[2.2]" />
                <span>Đăng Nhập / Đăng Ký Cổng Bác Sĩ &amp; Người Bệnh</span>
                <ArrowRight className="ml-2 w-5 h-5 text-slate-400 transition-transform duration-300 group-hover/login:translate-x-1 motion-reduce:group-hover/login:translate-x-0" />
              </Link>
            )}
          </div>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 text-left">
          {PATHWAYS.map((pathway, index) => {
            const Icon = pathway.icon;
            return (
              <Link
                key={pathway.label}
                href={pathway.href(isAuthenticated)}
                style={{ "--rise-delay": `${index * 90}ms` } as React.CSSProperties}
                className="group glow-frame glow-sky rise-in bg-white dark:bg-slate-950 border border-slate-200 dark:border-slate-800 rounded-2xl p-6 shadow-sm hover:shadow-lg hover:border-sky-500/50 hover:-translate-y-1 motion-reduce:hover:translate-y-0 transition-[transform,box-shadow,border-color] duration-300 ease-out flex flex-col justify-between focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-sky-600 focus-visible:ring-offset-2"
              >
                <div className="relative z-10">
                  <div className="flex items-center justify-between mb-4">
                    <div className="w-12 h-12 rounded-xl bg-sky-50 dark:bg-sky-950 text-sky-600 dark:text-sky-400 flex items-center justify-center group-hover:bg-sky-600 group-hover:text-white group-hover:scale-105 motion-reduce:group-hover:scale-100 transition-[background-color,color,transform] duration-300 border border-sky-200 dark:border-sky-800">
                      <Icon className="w-6 h-6 stroke-[2.2]" />
                    </div>
                    <span className="text-sm font-semibold text-slate-600 dark:text-slate-300">{pathway.label}</span>
                  </div>
                  <h3 className="text-xl font-bold text-slate-900 dark:text-white group-hover:text-sky-600 dark:group-hover:text-sky-400 transition-colors flex items-center justify-between">
                    <span>{pathway.title}</span>
                    <ArrowRight className="w-5 h-5 text-slate-400 group-hover:translate-x-1 group-hover:text-sky-500 transition-[transform,color] duration-300 motion-reduce:group-hover:translate-x-0" />
                  </h3>
                  <p className="mt-3 text-sm font-medium text-slate-600 dark:text-slate-400 leading-relaxed">
                    {pathway.description}
                  </p>
                </div>
                <div className="relative z-10 mt-6 pt-4 border-t border-slate-100 dark:border-slate-800 flex items-center gap-2 text-sm font-bold text-sky-600 dark:text-sky-400">
                  <CheckCircle2 className="w-4 h-4 shrink-0 stroke-[2.5]" />
                  <span>{pathway.cta}</span>
                </div>
              </Link>
            );
          })}
        </div>

      </div>
    </section>
  );
};
