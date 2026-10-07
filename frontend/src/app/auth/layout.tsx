import React from "react";
import { 
  Activity, 
  ShieldAlert, 
  Stethoscope, 
  Lock, 
  Sparkles, 
  ShieldCheck 
} from "lucide-react";
import { GuestGuard } from "@/components/auth/guest-guard";

interface AuthLayoutProps {
  children: React.ReactNode;
}

export default function AuthLayout({ children }: AuthLayoutProps) {
  return (
    <main className="min-h-screen w-full bg-background text-slate-800 flex items-center justify-center p-4 sm:p-6 lg:p-10 relative overflow-hidden font-sans selection:bg-blue-500/20 selection:text-blue-700 dark:text-slate-100">
      {/* 🌌 AMBIENT MINIMALIST LIGHT SPHERES (COHESIVE BLUE PALETTE) */}
      <div className="absolute -top-48 -left-48 w-[600px] h-[600px] bg-blue-400/10 rounded-full blur-[120px] pointer-events-none animate-pulse duration-[8000ms]" />
      <div className="absolute -bottom-32 -right-32 w-[500px] h-[500px] bg-teal-400/10 rounded-full blur-[140px] pointer-events-none" />
      <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[700px] h-[400px] bg-sky-300/10 rounded-full blur-[160px] pointer-events-none" />
      
      {/* Subtle Medical Cybernetic Grid Overlay */}
      <div 
        className="absolute inset-0 bg-[linear-gradient(to_right,#cbd5e120_1px,transparent_1px),linear-gradient(to_bottom,#cbd5e120_1px,transparent_1px)] bg-[size:4rem_4rem] [mask-image:radial-gradient(ellipse_75%_65%_at_50%_50%,#000_70%,transparent_100%)] pointer-events-none" 
        aria-hidden="true"
      />

      {/* 🔮 CENTERED MASTER MINIMALIST NAVY & WHITE CARD */}
      <div className="w-full max-w-5xl bg-card border border-border shadow-[0_20px_70px_-15px_rgba(0,0,0,0.05),0_0_2px_1px_rgba(37,99,235,0.08)] rounded-3xl overflow-hidden grid grid-cols-1 lg:grid-cols-12 relative z-10 transition-all duration-300">
        
        {/* 🧬 LEFT COLUMN: CLINICAL AI BRANDING (Deep Navy Accent - 5 Cols) */}
        <section className="lg:col-span-5 bg-slate-900 p-8 sm:p-10 flex flex-col justify-between text-white border-b lg:border-b-0 lg:border-r border-slate-800 relative overflow-hidden">
          
          {/* Subtle Inner Blue Accent Line */}
          <div className="absolute top-0 left-0 right-0 h-1.5 bg-gradient-to-r from-blue-500 via-sky-400 to-teal-400" />
          <div className="absolute bottom-0 right-0 w-64 h-64 bg-blue-600/10 rounded-full blur-3xl pointer-events-none" />

          {/* Brand Logo & Title */}
          <div className="relative z-10">
            <div className="flex items-center gap-3.5 mb-8">
              <div className="flex h-12 w-12 items-center justify-center rounded-2xl bg-blue-600 shadow-md shadow-blue-600/40 text-white">
                <Activity className="w-6 h-6 animate-pulse" />
              </div>
              <div className="flex flex-col">
                <span className="font-black text-xl tracking-tight text-white leading-none">
                  AI20K <span className="text-blue-400 font-semibold">Triage</span>
                </span>
                <span className="text-[10px] uppercase tracking-widest font-mono text-slate-400 mt-1.5 font-bold">
                  Clinical Intelligence
                </span>
              </div>
            </div>

            {/* AI Platform Badge */}
            <div className="inline-flex items-center gap-2 rounded-full border border-blue-400/30 bg-blue-500/15 px-3.5 py-1 text-xs font-bold text-blue-300 mb-6 shadow-inner">
              <Sparkles className="w-3.5 h-3.5 animate-pulse text-blue-400" />
              <span>Hệ thống sàng lọc lâm sàng theo thang ESI</span>
            </div>

            {/* Hero Headline */}
            <h1 className="text-2xl sm:text-3xl font-extrabold tracking-tight text-white leading-tight">
              Sàng Lọc Lâm Sàng &amp; <br />
              <span className="text-blue-400 font-black underline decoration-white/20 decoration-2">
                Thẩm Định Bởi Nhân Viên Y Tế
              </span>
            </h1>

            {/* Feature Bullet Points (Zero Red/Yellow Policy) */}
            <div className="mt-8 space-y-6">
              <div className="flex items-start gap-4 group transition-all duration-200">
                <div className="p-2.5 rounded-2xl bg-blue-500/20 border border-blue-400/40 text-blue-300 mt-0.5 shadow-xs transition-transform group-hover:scale-105">
                  <ShieldAlert className="w-5 h-5 stroke-[2.3]" />
                </div>
                <div>
                  <h3 className="text-sm font-black text-white tracking-wide">
                    Kết Luận Luôn Kèm Căn Cứ
                  </h3>
                  <p className="text-xs font-medium text-slate-400 mt-1 leading-relaxed">
                    Mỗi mức ESI đề xuất đều đi kèm tiêu chí phác đồ đã thỏa; không truy xuất được căn cứ thì hệ thống báo rõ là chưa đủ dữ liệu.
                  </p>
                </div>
              </div>

              <div className="flex items-start gap-4 group transition-all duration-200">
                <div className="p-2.5 rounded-2xl bg-sky-500/20 border border-sky-400/40 text-sky-300 mt-0.5 shadow-xs transition-transform group-hover:scale-105">
                  <Stethoscope className="w-5 h-5 stroke-[2.3]" />
                </div>
                <div>
                  <h3 className="text-sm font-black text-white tracking-wide">
                    Điều Dưỡng Thẩm Định Cuối
                  </h3>
                  <p className="text-xs font-medium text-slate-400 mt-1 leading-relaxed">
                    Mỗi ca đều sinh phiếu bàn giao SBAR để điều dưỡng rà soát và chốt mức ESI chính thức.
                  </p>
                </div>
              </div>

              <div className="flex items-start gap-4 group transition-all duration-200">
                <div className="p-2.5 rounded-2xl bg-teal-500/20 border border-teal-400/40 text-teal-300 mt-0.5 shadow-xs transition-transform group-hover:scale-105">
                  <Lock className="w-5 h-5 stroke-[2.3]" />
                </div>
                <div>
                  <h3 className="text-sm font-black text-white tracking-wide">
                    Che Dữ Liệu Định Danh Trong Log
                  </h3>
                  <p className="text-xs font-medium text-slate-400 mt-1 leading-relaxed">
                    Thông tin định danh được che trong nhật ký hệ thống, và toàn bộ hội thoại được lưu lại để nhân viên y tế rà soát.
                  </p>
                </div>
              </div>
            </div>
          </div>

          {/* Footer Security Badge */}
          <div className="pt-6 mt-10 border-t border-slate-800 flex items-center justify-between text-[11px] font-mono text-slate-400 relative z-10">
            <div className="flex items-center gap-2">
              <ShieldCheck className="w-4 h-4 text-teal-400 stroke-[2.5]" />
              <span className="tracking-wider font-bold">Hỗ trợ sàng lọc &#183; Không thay thế chẩn đoán</span>
            </div>
            <span className="bg-slate-800 text-slate-300 px-3 py-0.5 rounded-xl text-[10px] font-black border border-slate-700">
              ESI 5 CẤP
            </span>
          </div>
        </section>

        {/* 🌞 RIGHT COLUMN: PRISTINE MINIMALIST AUTH FLOW (7 Cols) */}
        <section className="lg:col-span-7 p-6 sm:p-10 lg:p-14 flex flex-col justify-center bg-card relative">
          {/* Main Form Content Injection Point */}
          <div className="w-full max-w-md mx-auto space-y-6">
            <GuestGuard>
              {children}
            </GuestGuard>
          </div>

          {/* Clinical Legal Disclaimer Notice */}
          <footer className="mt-12 pt-6 border-t border-slate-100 text-center">
            <p className="text-xs font-medium text-slate-400 leading-relaxed max-w-sm mx-auto">
              Bằng việc thao tác, bạn xác nhận tuân thủ{" "}
              <span className="text-blue-600 underline font-bold transition-colors cursor-pointer hover:text-blue-800">
                Cam Kết Y Đức &amp; Quyền Riêng Tư
              </span>{" "}
              của hệ thống AI Trợ lý Lâm sàng AI20K.
            </p>
          </footer>
        </section>

      </div>
    </main>
  );
}
