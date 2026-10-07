"use client";

import React from "react";
import { motion } from "framer-motion";
import { Activity, CheckCircle2, ShieldCheck } from "lucide-react";
import type { EsiLevel, HitlReviewStatus } from "@/types/clinical-history";
import { ClinicalMarkdown } from "@/components/chat/ClinicalMarkdown";

interface VerifiedRecommendationCardProps {
  esiLevel: EsiLevel;
  reviewStatus: HitlReviewStatus;
  recommendation: string;
}

const ESI_LABELS: Record<EsiLevel, string> = {
  1: "Cần xử trí ngay",
  2: "Cần được ưu tiên khẩn",
  3: "Cần thăm khám sớm",
  4: "Ít khẩn cấp",
  5: "Không khẩn cấp",
};

export function VerifiedRecommendationCard({
  esiLevel,
  reviewStatus,
  recommendation,
}: VerifiedRecommendationCardProps) {
  const isOverridden = reviewStatus === "OVERRIDDEN";
  const isPending = reviewStatus === "PENDING_REVIEW";

  return (
    <motion.section
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.25, ease: "easeOut" }}
      className="mx-auto my-6 w-full max-w-3xl space-y-4 font-sans"
    >
      <div className="flex items-center justify-center gap-2 rounded-xl border border-emerald-200 bg-emerald-50 p-4 text-center text-sm font-bold text-emerald-900">
        <CheckCircle2 className="size-5 shrink-0 text-emerald-600" aria-hidden="true" />
        <span>
          {isPending
            ? "Đề xuất AI đã qua kiểm tra đầu ra và được lưu; đang chờ nhân viên y tế thẩm định"
            : isOverridden
              ? "Kết quả đã được nhân viên y tế điều chỉnh và xác nhận"
              : "Kết quả đã được nhân viên y tế xác nhận"}
        </span>
      </div>

      <div className="space-y-6 rounded-2xl border border-border bg-card p-6 text-center shadow-sm sm:p-8">
        <div className="mx-auto flex size-14 items-center justify-center rounded-2xl bg-slate-900 text-white">
          <Activity className="size-7" aria-hidden="true" />
        </div>

        <div className="space-y-2">
          <p className="text-sm font-semibold uppercase tracking-wide text-slate-600 dark:text-slate-300">
            {isPending
              ? "Đề xuất phân loại đang chờ thẩm định"
              : "Kết quả phân loại của phiên khám"}
          </p>
          <h2 className="text-2xl font-black tracking-tight text-slate-950 sm:text-3xl dark:text-slate-50">
            ESI {esiLevel} — {ESI_LABELS[esiLevel]}
          </h2>
        </div>

        <div className="border-l-4 border-sky-600 bg-sky-50 p-4 text-left">
          <div className="text-base font-medium leading-7 text-foreground">
            <strong className="mr-1">
              {isPending ? "Khuyến nghị đề xuất đã lưu:" : "Khuyến nghị đã lưu:"}
            </strong>
            <ClinicalMarkdown content={recommendation} className="inline" />
          </div>
        </div>

        <div className="flex items-center justify-center gap-2 border-t border-border pt-4 text-sm font-medium text-slate-600 dark:text-slate-300">
          <ShieldCheck className="size-5 shrink-0 text-emerald-600" aria-hidden="true" />
          <span>Kết quả hiển thị theo dữ liệu hiện có của phiên khám</span>
        </div>
      </div>
    </motion.section>
  );
}
