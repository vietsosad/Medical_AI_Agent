"use client";

import React, { useState } from "react";
import { AlertTriangle, CheckCircle2, Flame, Lock, ShieldCheck, Sliders } from "lucide-react";
import { cn } from "@/lib/utils";

/**
 * Trang Cấu Hình AI Guardrails (Dual-Layer Emergency Reflex & Diagnosis Suppression Firewalls)
 * - Giao diện phẳng Sáng (Pristine Neutral Ops), độ tinh gọn tối đa.
 * - Quản trị viên tùy chỉnh độ nhạy lớp lọc tất định và kiểm sát ngăn AI tự ý kết luận chẩn đoán.
 */
export default function AdminGuardrailsPage() {
  const [reflexEnabled, setReflexEnabled] = useState<boolean>(true);
  const [suppressionEnabled, setSuppressionEnabled] = useState<boolean>(true);
  const [justificationMinLength, setJustificationMinLength] = useState<number>(15);

  return (
    <div className="p-6 sm:p-8 space-y-8 max-w-6xl mx-auto font-sans text-foreground">
      {/* HEADER AI GUARDRAILS */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 bg-card p-6 rounded-2xl border border-border shadow-2xs">
        <div className="flex items-center gap-4">
          <div className="w-12 h-12 rounded-xl bg-slate-900 text-rose-500 flex items-center justify-center shrink-0">
            <Sliders className="w-6 h-6 stroke-[2.2]" />
          </div>
          <div>
            <h1 className="text-xl sm:text-2xl font-bold text-foreground tracking-tight font-mono uppercase">
              Cấu Hình AI Guardrails &amp; Tường Lửa Bảo Vệ Y Khoa
            </h1>
            <p className="text-sm text-muted-foreground mt-0.5">
              Điều phối lớp lọc tất định và chính sách ngăn AI kết luận khi chưa đủ căn cứ
            </p>
          </div>
        </div>

        <button
          type="button"
          onClick={() => alert("Đã ghi nhận cấu hình Guardrails mới cho DeepAgent runtime.")}
          className="min-h-[44px] inline-flex items-center justify-center gap-2 px-6 py-2.5 rounded-xl bg-sky-600 hover:bg-sky-700 text-white font-semibold text-sm shadow-sm transition-all cursor-pointer"
        >
          <CheckCircle2 className="w-4.5 h-4.5 stroke-[2.2]" />
          <span>Lưu thi hành cấu hình mới</span>
        </button>
      </div>

      {/* FIREWALL SETTINGS CARDS (FLAT DESIGN, HIGH CONTRAST) */}
      <div className="space-y-6">
        
        {/* CARD 1: DUAL-LAYER EMERGENCY REFLEX */}
        <div className="p-6 rounded-2xl bg-card border border-border shadow-2xs space-y-6">
          <div className="flex flex-wrap items-center justify-between gap-4 border-b border-slate-100 pb-4">
            <div className="space-y-1">
              <span className="text-xs font-mono font-bold text-rose-600 uppercase bg-rose-50 px-2.5 py-1 rounded border border-rose-200 flex items-center gap-1.5 w-fit">
                <Flame className="w-3.5 h-3.5 stroke-[2.2]" />
                <span>Lớp 1: Lọc tất định (Deterministic Reflex Shield)</span>
              </span>
              <h2 className="text-lg sm:text-xl font-bold text-foreground tracking-tight pt-1">
                Tường Lửa Bắt Sóng Cứu Hộ Ngoại Lệ (Red-Flag Reflex Overlay)
              </h2>
            </div>

            <div className="flex items-center gap-3">
              <span className="text-sm font-semibold text-slate-600 dark:text-slate-300">Trạng thái:</span>
              <button
                type="button"
                onClick={() => setReflexEnabled(!reflexEnabled)}
                className={cn(
                  "min-h-[38px] px-4 py-1.5 rounded-full text-xs sm:text-sm font-mono font-bold transition-all cursor-pointer",
                  reflexEnabled 
                    ? "bg-emerald-600 text-white shadow-sm" 
                    : "bg-slate-200 text-slate-600 dark:text-slate-300 dark:bg-slate-700"
                )}
              >
                {reflexEnabled ? "ON — ACTIVE INTERCEPTION" : "OFF — DISABLED"}
              </button>
            </div>
          </div>

          <p className="text-sm text-slate-600 leading-relaxed dark:text-slate-300">
            Sử dụng tập lệnh chính quy (Regex) và từ khóa tối khẩn y tế (như <strong className="text-foreground">đau ngực, bất tỉnh, khó thở nghẹt thở, co giật, chảy máu phun dào</strong>) để cản phá dòng hỏi đáp thông thường ngay lập tức dưới 50 mili-giây, ép buộc hiển thị màn hình báo động cấp cứu 115 mà không cần đợi mô hình LLM phân tích.
          </p>
        </div>

        {/* CARD 2: DIAGNOSIS SUPPRESSION FIREWALL */}
        <div className="p-6 rounded-2xl bg-card border border-border shadow-2xs space-y-6">
          <div className="flex flex-wrap items-center justify-between gap-4 border-b border-slate-100 pb-4">
            <div className="space-y-1">
              <span className="text-xs font-mono font-bold text-amber-700 uppercase bg-amber-50 px-2.5 py-1 rounded border border-amber-200 flex items-center gap-1.5 w-fit">
                <AlertTriangle className="w-3.5 h-3.5 stroke-[2.2]" />
                <span>Layer 2: Diagnosis Suppression Firewall</span>
              </span>
              <h2 className="text-lg sm:text-xl font-bold text-foreground tracking-tight pt-1">
                Cấm AI Ra Phán Quyết Chẩn Đoán Chính Thức (Hallucination &amp; Liability Shield)
              </h2>
            </div>

            <div className="flex items-center gap-3">
              <span className="text-sm font-semibold text-slate-600 dark:text-slate-300">Trạng thái:</span>
              <button
                type="button"
                onClick={() => setSuppressionEnabled(!suppressionEnabled)}
                className={cn(
                  "min-h-[38px] px-4 py-1.5 rounded-full text-xs sm:text-sm font-mono font-bold transition-all cursor-pointer",
                  suppressionEnabled 
                    ? "bg-emerald-600 text-white shadow-sm" 
                    : "bg-slate-200 text-slate-600 dark:text-slate-300 dark:bg-slate-700"
                )}
              >
                {suppressionEnabled ? "ON — SUPPRESSION ENABLED" : "OFF — BYPASSED"}
              </button>
            </div>
          </div>

          <p className="text-sm text-slate-600 leading-relaxed dark:text-slate-300">
            Kiểm soát đầu ra của LLM qua Pydantic Parser. Nếu phát hiện các câu văn mang tính khẳng định bệnh lý kết luận thay cho Bác sĩ (ví dụ: &quot;Bạn chắc chắn đang bị bệnh ung thư...&quot;), màng lọc lập tức hạ bớt tone về mức khuyến nghị đánh giá rủi ro (&quot;Triệu chứng của bạn cho thấy dấu hiệu cần kiểm tra y tế định kỳ...&quot;).
          </p>
        </div>

        {/* CARD 3: HITL JUSTIFICATION FIREWALL PARAMETERS */}
        <div className="p-6 rounded-2xl bg-card border border-border shadow-2xs space-y-5">
          <div className="flex items-center justify-between border-b border-slate-100 pb-4">
            <h2 className="text-lg font-bold text-foreground font-mono uppercase">
              Tham Số Kiểm Duyệt Override HITL (Zod Runtime Enforcement)
            </h2>
            <Lock className="w-5 h-5 text-slate-400 stroke-[2.2]" />
          </div>

          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
            <div>
              <span className="text-sm font-bold text-slate-800 block dark:text-slate-100">
                Độ dài lý do giải trình tối thiểu khi Bác sĩ phủ quyết AI (Override):
              </span>
              <span className="text-xs text-muted-foreground">
                Nhân viên y tế buộc phải gõ đủ số lượng ký tự tối thiểu mới được cấp quyền nộp quyết định ACID.
              </span>
            </div>

            <div className="flex items-center gap-3 shrink-0">
              <input
                type="number"
                min={5}
                max={100}
                value={justificationMinLength}
                onChange={(e) => setJustificationMinLength(Number(e.target.value))}
                className="w-20 min-h-[40px] px-3 text-center rounded-xl bg-background border border-slate-300 font-mono font-bold text-foreground shadow-2xs focus:outline-none focus:ring-2 focus:ring-sky-500 dark:border-slate-700"
              />
              <span className="text-sm font-semibold text-slate-600 font-mono dark:text-slate-300">Ký tự (Chars)</span>
            </div>
          </div>
        </div>

      </div>

      <div className="p-4 bg-background rounded-xl border border-border text-xs text-muted-foreground flex items-center justify-between font-mono">
        <span>Mục tiêu cam kết an toàn lâm sàng: Tỷ lệ Hallucination &lt; 0.01% &amp; Phản xạ Red-Flag 100%.</span>
        <span className="text-emerald-700 font-bold flex items-center gap-1"><ShieldCheck className="w-4 h-4" /> AI Safety Enforced</span>
      </div>
    </div>
  );
}
