"use client";

import React from "react";
import { HeroSection } from "./HeroSection";
import { TrustBentoGrid } from "./TrustBentoGrid";
import { DynamicTriagePreview } from "./DynamicTriagePreview";
import { SystemPathwaysGrid } from "./SystemPathwaysGrid";
import { HealthTopicsSection } from "./HealthTopicsSection";
import { ShieldCheck, HeartPulse } from "lucide-react";

export default function ClinicalLandingClient() {
  return (
    <main className="w-full min-h-screen bg-white dark:bg-slate-950 text-slate-800 dark:text-slate-100 flex flex-col justify-between selection:bg-sky-100 dark:selection:bg-sky-900 selection:text-sky-900 dark:selection:text-white">
      {/* 1. HERO SECTION (VID-01 + IMG-01) */}
      <HeroSection />

      {/* 2. NGUYÊN TẮC AN TOÀN LÂM SÀNG (cổng bằng chứng + đối chiếu tất định) */}
      <TrustBentoGrid />

      {/* 3. INTERACTIVE DYNAMIC TRIAGE PREVIEW (Patient vs Clinician Tabs) */}
      <DynamicTriagePreview />

      {/* 4. THÔNG TIN SỨC KHỎE ĐÁNG CHÚ Ý (HEALTH EDUCATION -> TRIAGE) */}
      <HealthTopicsSection />

      {/* 5. PATIENT PATHWAYS & EHR / ARCHIVE DIRECTORY */}
      <SystemPathwaysGrid />

      {/* 6. FOOTER -- chỉ nêu điều kiểm chứng được: dữ liệu định danh được che
             trong nhật ký hệ thống (src/services/log_redaction.py) và giới hạn
             sử dụng của công cụ. Không đặt lại nhãn HIPAA/ISO khi chưa có
             chứng nhận thật. */}
      <footer className="border-t border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-950 py-8 px-4 sm:px-6 lg:px-8 text-sm font-semibold text-slate-600 dark:text-slate-400">
        <div className="max-w-7xl mx-auto flex flex-col sm:flex-row items-start sm:items-center justify-between gap-6">
          <div className="flex items-start gap-3">
            <div className="p-2 bg-emerald-100 dark:bg-emerald-950 rounded-lg text-emerald-600 dark:text-emerald-400 border border-emerald-300 dark:border-emerald-800 shrink-0">
              <ShieldCheck className="w-5 h-5 stroke-[2.2]" />
            </div>
            <div className="min-w-0">
              <div className="font-bold text-slate-900 dark:text-slate-200">Hệ Thống Sàng Lọc Lâm Sàng AI20K</div>
              <div className="text-xs text-slate-500 dark:text-slate-400 leading-relaxed">
                Thông tin định danh được che trong nhật ký hệ thống; toàn bộ hội thoại được lưu để nhân viên y tế rà soát
              </div>
            </div>
          </div>

          <div className="flex items-start gap-2 max-w-md">
            <HeartPulse className="w-4.5 h-4.5 text-rose-500 shrink-0 stroke-[2.2] mt-0.5" />
            <span className="text-xs leading-relaxed font-medium">
              Công cụ hỗ trợ sàng lọc ban đầu, không thay thế chẩn đoán hoặc chỉ định của nhân viên y tế.
              Trong tình huống nguy kịch, hãy gọi cấp cứu 115.
            </span>
          </div>
        </div>
      </footer>
    </main>
  );
}
