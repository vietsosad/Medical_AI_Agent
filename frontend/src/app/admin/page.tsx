"use client";

import React from "react";
import { 
  BarChart, 
  Bar, 
  XAxis, 
  YAxis, 
  CartesianGrid, 
  Tooltip, 
  ResponsiveContainer
} from "recharts";
import { 
  Activity, 
  Database, 
  ShieldAlert, 
  CheckCircle2, 
  Clock, 
  Lock, 
  Cpu 
} from "lucide-react";

// Dữ liệu mẫu Concordance Rate (Tỷ lệ Đồng thuận AI vs Bác sĩ HITL)
const concordanceData = [
  { month: "T1", concordance: 92, target: 90, overrides: 8 },
  { month: "T2", concordance: 94, target: 90, overrides: 6 },
  { month: "T3", concordance: 89, target: 90, overrides: 11 },
  { month: "T4", concordance: 96, target: 90, overrides: 4 },
  { month: "T5", concordance: 95, target: 90, overrides: 5 },
  { month: "T6", concordance: 98, target: 90, overrides: 2 },
];

/**
 * ============================================================================
 * [ADMIN ANALYTICS DASHBOARD] TRM GIÁM SÁT RAG & CONCORDANCE RATE
 * ============================================================================
 * Tuân thủ Quy tắc Bảng Màu Trạng Thái (Semantic Colors):
 * - Xanh lá (Success): Tỷ lệ đồng thuận cao (>90%), phác đồ RAG ổn định.
 * - Vàng (Warning): Prompt trễ hoặc có dấu hiệu nghẽn nghẽn cổ chai (>1.5s).
 * - Đỏ (Danger): Cảnh báo rủi ro Hallucination hoặc thao tác xóa dữ liệu PII.
 * - Nhắc nhở ranh giới quyền: Quản trị viên không được đọc PII chưa mã hóa.
 */
export default function AdminDashboardPage() {
  return (
    <div className="space-y-8 animate-in fade-in duration-300 pb-12">
      
      {/* HEADER & THÔNG BÁO CAM KẾT BẢO MẬT PHẨN VAY TRÒ */}
      <div className="bg-card border border-border shadow-sm rounded-3xl p-6 sm:p-8 flex flex-col md:flex-row items-start md:items-center justify-between gap-6">
        <div className="space-y-2">
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-blue-50 text-blue-800 border border-blue-200 text-xs font-black tracking-wider uppercase font-mono">
            <Cpu className="w-4 h-4 text-blue-600 stroke-[2.5]" />
            <span>RAG Telemetry & System Ops</span>
          </div>
          <h1 className="text-2xl sm:text-3xl font-black text-foreground tracking-tight">
            Trạm Giám Sát Hiệu Suất & AI Guardrails
          </h1>
          <p className="text-sm text-slate-600 font-medium max-w-2xl dark:text-slate-300">
            Theo dõi tỷ lệ đồng thuận giữa mức ESI do AI đề xuất và mức điều dưỡng chốt, cùng tình trạng kho tri thức phác đồ.
          </p>
        </div>

        <div className="p-4 rounded-2xl bg-amber-50 border border-amber-200 max-w-sm shrink-0 flex items-start gap-3">
          <Lock className="w-5 h-5 text-amber-700 shrink-0 mt-0.5 stroke-[2.5]" />
          <div className="text-xs text-amber-900 space-y-1">
            <p className="font-extrabold uppercase tracking-wider">Cam Kết Bảo Mật PII:</p>
            <p className="font-semibold leading-relaxed">
              Quản trị viên không có thẩm quyền đọc hội thoại bệnh án chưa mã hóa ẩn danh (PHI) và cấm tuyệt đối ra chỉ định lâm sàng.
            </p>
          </div>
        </div>
      </div>

      {/* LƯỚI THẺ SƠ KHÔNG GIAN BẮT BUỘC SEMANTIC STATUS COLORS */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        
        {/* THẺ SUCCESS - XANH LÁ */}
        <div className="bg-card border border-emerald-200 rounded-3xl p-6 shadow-sm relative overflow-hidden flex flex-col justify-between">
          <div className="absolute top-0 right-0 w-2 h-full bg-emerald-600" />
          <div className="space-y-3">
            <div className="flex items-center justify-between">
              <span className="text-xs font-mono font-black text-emerald-800 uppercase tracking-wider bg-emerald-50 px-3 py-1 rounded-full border border-emerald-200">
                SUCCESS STATUS
              </span>
              <CheckCircle2 className="w-6 h-6 text-emerald-600 stroke-[2.5]" />
            </div>
            <div className="space-y-1">
              <p className="text-xs font-bold text-muted-foreground uppercase">Tỷ Lệ Đồng Thuận HITL</p>
              <h3 className="text-3xl font-black text-foreground tracking-tight">96.4%</h3>
            </div>
          </div>
          <p className="text-xs text-slate-600 font-medium pt-4 mt-4 border-t border-slate-100 flex items-center gap-1.5 dark:text-slate-300">
            <span className="text-emerald-700 font-extrabold">+2.1% so với tháng trước</span> (Vượt KPI 90%)
          </p>
        </div>

        {/* THẺ WARNING - VÀNG CAM */}
        <div className="bg-card border border-amber-300 rounded-3xl p-6 shadow-sm relative overflow-hidden flex flex-col justify-between">
          <div className="absolute top-0 right-0 w-2 h-full bg-amber-500" />
          <div className="space-y-3">
            <div className="flex items-center justify-between">
              <span className="text-xs font-mono font-black text-amber-900 uppercase tracking-wider bg-amber-50 px-3 py-1 rounded-full border border-amber-300">
                WARNING STATUS
              </span>
              <Clock className="w-6 h-6 text-amber-600 stroke-[2.5]" />
            </div>
            <div className="space-y-1">
              <p className="text-xs font-bold text-muted-foreground uppercase">Độ Trễ Phản Hồi RAG</p>
              <h3 className="text-3xl font-black text-foreground tracking-tight">1.48s</h3>
            </div>
          </div>
          <p className="text-xs text-slate-600 font-medium pt-4 mt-4 border-t border-slate-100 flex items-center gap-1.5 dark:text-slate-300">
            <span className="text-amber-700 font-extrabold">Cần theo dõi:</span> Cận ngưỡng nghẽn cổ chai 1.5s
          </p>
        </div>

        {/* THẺ DANGER - ĐỎ ROSE */}
        <div className="bg-card border border-rose-200 rounded-3xl p-6 shadow-sm relative overflow-hidden flex flex-col justify-between">
          <div className="absolute top-0 right-0 w-2 h-full bg-rose-600" />
          <div className="space-y-3">
            <div className="flex items-center justify-between">
              <span className="text-xs font-mono font-black text-rose-800 uppercase tracking-wider bg-rose-50 px-3 py-1 rounded-full border border-rose-200">
                DANGER STATUS
              </span>
              <ShieldAlert className="w-6 h-6 text-rose-600 stroke-[2.5]" />
            </div>
            <div className="space-y-1">
              <p className="text-xs font-bold text-muted-foreground uppercase">Cảnh Báo Hallucination</p>
              <h3 className="text-3xl font-black text-foreground tracking-tight">0.02%</h3>
            </div>
          </div>
          <p className="text-xs text-slate-600 font-medium pt-4 mt-4 border-t border-slate-100 flex items-center gap-1.5 dark:text-slate-300">
            <span className="text-rose-700 font-extrabold">Bảo vệ AI:</span> Đã tự động kích hoạt Tường lửa 2 tầng
          </p>
        </div>

      </div>

      {/* KHỐI BIỂU ĐỒ RECHARTS BẢO ĐẢM NO HYDRO MISMATCH WITH RESPONSIVE CONTAINER */}
      <div className="bg-card border border-border shadow-sm rounded-3xl p-6 sm:p-8 space-y-6">
        <div className="flex items-center justify-between flex-wrap gap-4">
          <div>
            <h3 className="text-lg font-black text-foreground tracking-tight flex items-center gap-2">
              <Activity className="w-5 h-5 text-blue-600 stroke-[2.5]" />
              <span>Biểu Đồ Theo Dõi Tỷ Lệ Đồng Thuận (Concordance Rate KPI)</span>
            </h3>
            <p className="text-xs font-medium text-muted-foreground">
              Dữ liệu đối soát giữa Phác đồ SBAR do AI gợi ý và quyết định cuối cùng của Bác sĩ chuyên khoa HITL.
            </p>
          </div>
          <div className="flex items-center gap-4 text-xs font-bold">
            <span className="flex items-center gap-1.5 text-slate-700 dark:text-slate-200">
              <span className="w-3 h-3 rounded-md bg-blue-600 inline-block"></span>
              Đồng thuận AI (%)
            </span>
            <span className="flex items-center gap-1.5 text-slate-700 dark:text-slate-200">
              <span className="w-3 h-3 rounded-md bg-rose-500 inline-block"></span>
              Bác sĩ can thiệp Override (%)
            </span>
          </div>
        </div>

        <div className="w-full h-[340px] pt-4">
          <ResponsiveContainer width="100%" height={320}>
            <BarChart data={concordanceData} margin={{ top: 10, right: 30, left: 0, bottom: 0 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" vertical={false} />
              <XAxis dataKey="month" stroke="#64748b" fontStyle="bold" fontSize={12} tickLine={false} axisLine={false} />
              <YAxis stroke="#64748b" fontSize={12} tickLine={false} axisLine={false} domain={[0, 100]} />
              <Tooltip 
                contentStyle={{ 
                  backgroundColor: "#0f172a", 
                  borderRadius: "16px", 
                  border: "none", 
                  boxShadow: "0 10px 25px rgba(0,0,0,0.2)",
                  color: "#fff",
                  fontWeight: "bold"
                }} 
              />
              <Bar dataKey="concordance" fill="#2563eb" radius={[8, 8, 0, 0]} name="Đồng thuận AI (%)" barSize={36} />
              <Bar dataKey="overrides" fill="#f43f5e" radius={[8, 8, 0, 0]} name="Can thiệp Override (%)" barSize={36} />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* NÚT THAO TÁC CỰC THÌ MƯỢT MÀ CHUẨN 8PX GRID */}
      <div className="flex items-center justify-end gap-4 pt-2">
        <button
          type="button"
          className="px-6 py-3.5 rounded-2xl bg-blue-600 hover:bg-blue-700 text-white font-black text-sm transition-all shadow-lg shadow-blue-600/25 flex items-center gap-2 min-h-[44px] cursor-pointer active:scale-95"
        >
          <Database className="w-4.5 h-4.5 stroke-[2.5]" />
          <span>Tối Ưu &amp; Re-index Kho Phác Đồ</span>
        </button>
      </div>
    </div>
  );
}
