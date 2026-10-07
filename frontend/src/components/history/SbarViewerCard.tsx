"use client";

import React from "react";
import { BookOpen, FileCheck2, Layers } from "lucide-react";

import { cn } from "@/lib/utils";
import { ClinicalMarkdown } from "@/components/chat/ClinicalMarkdown";
import type { SbarReportDTO } from "@/types/clinical-history";

export interface SbarViewerCardProps {
  sbar: SbarReportDTO;
  sbarFinalized: boolean;
  className?: string;
}

const SBAR_SECTIONS = [
  { key: "situation", code: "S", title: "Situation — Tình trạng hiện tại" },
  { key: "background", code: "B", title: "Background — Tiền sử liên quan" },
  { key: "assessment", code: "A", title: "Assessment — Đánh giá lâm sàng" },
  { key: "recommendation", code: "R", title: "Recommendation — Khuyến nghị" },
] as const satisfies ReadonlyArray<{
  key: keyof Pick<
    SbarReportDTO,
    "situation" | "background" | "assessment" | "recommendation"
  >;
  code: string;
  title: string;
}>;

/** Render only the finalized SBAR persisted by the backend. */
export const SbarViewerCard: React.FC<SbarViewerCardProps> = ({
  sbar,
  sbarFinalized,
  className,
}) => {
  if (!sbarFinalized) return null;

  const citations = Array.from(
    new Set(sbar.citations.map((citation) => citation.trim()).filter(Boolean)),
  );

  return (
    <section
      className={cn(
        "space-y-6 rounded-2xl border border-border bg-card p-6 text-slate-800 shadow-sm dark:text-slate-100",
        className,
      )}
      aria-labelledby="finalized-sbar-title"
    >
      <header className="flex flex-wrap items-start justify-between gap-4 border-b border-border pb-4">
        <div className="flex items-start gap-4">
          <span className="flex size-12 shrink-0 items-center justify-center rounded-xl bg-sky-50 text-sky-700">
            <Layers className="size-6" aria-hidden="true" />
          </span>
          <div className="space-y-2">
            <h2 id="finalized-sbar-title" className="text-lg font-bold text-slate-950 dark:text-slate-50">
              Phiếu Triage SBAR
            </h2>
            <p className="text-sm leading-6 text-slate-600 dark:text-slate-300">
              Bản tóm tắt đã hoàn tất và được tải từ hồ sơ của phiên khám này.
            </p>
          </div>
        </div>
        <span className="flex min-h-12 items-center gap-2 rounded-xl border border-emerald-200 bg-emerald-50 px-4 text-sm font-semibold text-emerald-900">
          <FileCheck2 className="size-5" aria-hidden="true" />
          Đã hoàn tất
        </span>
      </header>

      <div className="space-y-6">
        {SBAR_SECTIONS.map((section) => (
          <section key={section.key} className="space-y-2 border-l-4 border-sky-600 pl-4">
            <h3 className="text-sm font-bold uppercase tracking-wide text-slate-700 dark:text-slate-200">
              {section.code}. {section.title}
            </h3>
            <ClinicalMarkdown
              content={sbar[section.key]}
              className="text-base font-medium leading-7 text-foreground"
            />
          </section>
        ))}
      </div>

      {citations.length > 0 && (
        <section
          className="space-y-4 border-t border-border pt-4"
          aria-labelledby="sbar-source-codes-title"
        >
          <h3
            id="sbar-source-codes-title"
            className="flex items-center gap-2 text-sm font-bold text-slate-800 dark:text-slate-100"
          >
            <BookOpen className="size-5 text-sky-700" aria-hidden="true" />
            Mã nguồn được lưu cùng SBAR
          </h3>
          <p className="text-sm leading-6 text-slate-600 dark:text-slate-300">
            Đây là mã tham chiếu do máy chủ cung cấp. Chi tiết nguồn bằng chứng được hiển thị trong
            hội thoại khi có dữ liệu tương ứng.
          </p>
          <ul className="flex flex-wrap gap-2" aria-label="Danh sách mã nguồn SBAR">
            {citations.map((citation) => (
              <li
                key={citation}
                className="rounded-lg border border-slate-300 bg-background px-4 py-2 text-sm font-semibold text-slate-800 dark:text-slate-100 dark:border-slate-700"
              >
                {citation}
              </li>
            ))}
          </ul>
        </section>
      )}
    </section>
  );
};

export default SbarViewerCard;
