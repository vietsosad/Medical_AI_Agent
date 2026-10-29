"use client";

import React from "react";
import { Activity, ShieldCheck } from "lucide-react";

import { BACKDROP_CREDITS } from "./backdrop-photos";
import { CareLoopSection } from "./CareLoopSection";
import { EvidenceGateSection } from "./EvidenceGateSection";
import { HealthTopicsSection } from "./HealthTopicsSection";
import { LandingClosingCta } from "./LandingClosingCta";
import { LandingHero } from "./LandingHero";
import { PhotoCreditDisclosure } from "./photo-credits";

/**
 * Trang chủ: ít chữ, để hình động kể. Phiên mẫu ở đầu trang cho thấy một lần
 * sàng lọc, sơ đồ "không đoán" cho thấy kết luận đến từ đâu, hai màn hình cho
 * thấy kết quả tới tay điều dưỡng, rồi kiến thức sức khỏe và lời mời bắt đầu.
 */
export default function ClinicalLandingClient() {
  return (
    <main className="flex min-h-screen w-full flex-col bg-background text-foreground selection:bg-brand-edge selection:text-brand-ink">
      <LandingHero />
      <EvidenceGateSection />
      <CareLoopSection />
      <HealthTopicsSection />
      <LandingClosingCta />

      {/* Chân trang chỉ nêu điều kiểm chứng được: dữ liệu định danh được che
          trong nhật ký hệ thống (src/services/log_redaction.py) và giới hạn sử
          dụng của công cụ. Không đặt lại nhãn HIPAA/ISO khi chưa có chứng nhận.
          Ảnh nền của trang được ghi công ở đây theo giấy phép của từng ảnh. */}
      <footer className="border-t border-border bg-background">
        <div className="mx-auto flex max-w-7xl flex-col gap-4 px-4 pb-4 pt-8 sm:px-6 md:flex-row md:items-center md:justify-between lg:px-8">
          <div className="flex items-center gap-4">
            <span className="flex size-9 shrink-0 items-center justify-center rounded-xl bg-slate-900 text-white dark:bg-slate-100 dark:text-slate-900">
              <Activity className="size-[18px]" strokeWidth={2.4} aria-hidden="true" />
            </span>
            <div>
              <p className="text-base font-extrabold text-foreground">AI Triage</p>
              <p className="text-sm leading-6 text-muted-foreground">
                Hỗ trợ sàng lọc ban đầu, không thay thế chẩn đoán của nhân viên y tế.
              </p>
            </div>
          </div>
          <p className="flex items-center gap-2 text-sm leading-6 text-muted-foreground">
            <ShieldCheck className="size-4 shrink-0 text-emerald-600 dark:text-emerald-400" aria-hidden="true" />
            Thông tin định danh được che trong nhật ký hệ thống.
          </p>
        </div>
        <div className="mx-auto max-w-7xl px-4 pb-8 sm:px-6 lg:px-8">
          <PhotoCreditDisclosure summary="Ảnh nền: Wikimedia Commons" photos={BACKDROP_CREDITS} className="-ml-3" />
        </div>
      </footer>
    </main>
  );
}
