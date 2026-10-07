"use client";

import React, { useState } from "react";
import Link from "next/link";
import {
  Accordion,
  AccordionContent,
  AccordionItem,
  AccordionTrigger,
} from "@/components/ui/accordion";
import {
  BookOpen,
  Download,
  FileText,
  FolderHeart,
  Loader2,
  MapPin,
  ShieldCheck,
} from "lucide-react";
import { toast } from "sonner";
import { cn } from "@/lib/utils";
import { downloadSbarPdf } from "@/lib/download-sbar-pdf";
import type { SbarReportDTO } from "@/types/clinical-history";
import { ClinicalMarkdown } from "@/components/chat/ClinicalMarkdown";

interface SbarSummaryAccordionProps {
  sessionId: string;
  sbar: SbarReportDTO;
  finalized: boolean;
}

const SBAR_SECTIONS = [
  {
    key: "situation",
    code: "S",
    title: "Situation — Tình trạng hiện tại",
    accent: "border-sky-600 text-sky-800",
  },
  {
    key: "background",
    code: "B",
    title: "Background — Tiền sử liên quan",
    accent: "border-amber-500 text-amber-900",
  },
  {
    key: "assessment",
    code: "A",
    title: "Assessment — Đánh giá lâm sàng",
    accent: "border-rose-500 text-rose-800",
  },
  {
    key: "recommendation",
    code: "R",
    title: "Recommendation — Khuyến nghị",
    accent: "border-emerald-600 text-emerald-800",
  },
] as const satisfies ReadonlyArray<{
  key: keyof Pick<
    SbarReportDTO,
    "situation" | "background" | "assessment" | "recommendation"
  >;
  code: string;
  title: string;
  accent: string;
}>;

export function SbarSummaryAccordion({
  sessionId,
  sbar,
  finalized,
}: SbarSummaryAccordionProps) {
  const citations = Array.from(new Set(sbar.citations));
  const [isDownloading, setIsDownloading] = useState(false);

  const handleDownloadPdf = async () => {
    if (!finalized) return;
    toast.info("Đang chuẩn bị phiếu SBAR...");
    setIsDownloading(true);
    try {
      await downloadSbarPdf(sessionId);
      toast.success("Đã tải phiếu SBAR.");
    } catch (error: unknown) {
      toast.error("Không thể tải phiếu SBAR lúc này.");
      console.error(error);
    } finally {
      setIsDownloading(false);
    }
  };

  const handleLocateHospital = () => {
    window.open(
      "https://www.google.com/maps/search/Benh+vien+cap+cuu+gan+nhat",
      "_blank",
      "noopener,noreferrer",
    );
  };

  return (
    <section className="mx-auto my-6 w-full max-w-3xl space-y-6 font-sans">
      <div className="overflow-hidden rounded-2xl border border-border bg-card p-2 shadow-sm sm:p-4">
        <Accordion type="single" collapsible defaultValue="sbar-summary">
          <AccordionItem value="sbar-summary" className="border-none">
            <AccordionTrigger className="min-h-12 gap-4 px-4 py-4 text-left text-base font-bold text-slate-950 transition-colors hover:text-sky-800 dark:text-slate-50">
              <span className="flex min-w-0 flex-1 items-center gap-2">
                <FileText className="size-5 shrink-0 text-sky-700" aria-hidden="true" />
                <span>Chi tiết bản tóm tắt SBAR</span>
              </span>
            </AccordionTrigger>

            <AccordionContent className="px-4 pb-4 pt-2 text-slate-700 dark:text-slate-200">
              <div className="space-y-6 text-left">
                {SBAR_SECTIONS.map((section) => (
                  <div
                    key={section.key}
                    className={cn("space-y-2 border-l-4 pl-4", section.accent)}
                  >
                    <h3 className="text-sm font-bold uppercase tracking-wide">
                      {section.code}. {section.title}
                    </h3>
                    <ClinicalMarkdown
                      content={sbar[section.key]}
                      className="text-base font-medium leading-7 text-slate-800 dark:text-slate-100"
                    />
                  </div>
                ))}

                {citations.length > 0 && (
                  <div className="space-y-2 border-t border-border pt-4">
                    <h3 className="flex items-center gap-2 text-sm font-bold text-slate-800 dark:text-slate-100">
                      <BookOpen className="size-5 text-sky-700" aria-hidden="true" />
                      Nguồn tham chiếu đã lưu
                    </h3>
                    <div className="flex flex-wrap gap-2">
                      {citations.map((citation) => (
                        <span
                          key={citation}
                          className="rounded-lg border border-sky-200 bg-sky-50 px-2 py-2 text-sm font-semibold text-sky-900"
                        >
                          {citation}
                        </span>
                      ))}
                    </div>
                  </div>
                )}

                <div className="flex items-center justify-end gap-2 border-t border-border pt-4 text-sm font-semibold text-slate-600 dark:text-slate-300">
                  <ShieldCheck className="size-5 text-emerald-600" aria-hidden="true" />
                  <span>Dữ liệu được tải từ hồ sơ của phiên khám này</span>
                </div>
              </div>
            </AccordionContent>
          </AccordionItem>
        </Accordion>
      </div>

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
        {finalized && (
          <button
            type="button"
            onClick={handleDownloadPdf}
            disabled={isDownloading}
            className="flex min-h-12 items-center justify-center gap-2 rounded-xl bg-sky-700 px-4 text-sm font-bold text-white transition-colors hover:bg-sky-800 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-sky-600 focus-visible:ring-offset-2 disabled:cursor-wait disabled:opacity-70 sm:col-span-3"
          >
            {isDownloading ? (
              <Loader2 className="size-5 shrink-0 animate-spin" aria-hidden="true" />
            ) : (
              <Download className="size-5 shrink-0" aria-hidden="true" />
            )}
            {isDownloading ? "Đang tạo phiếu PDF..." : "Tải phiếu SBAR dạng PDF"}
          </button>
        )}

        <button
          type="button"
          onClick={handleLocateHospital}
          className="flex min-h-12 items-center justify-center gap-2 rounded-xl bg-slate-900 px-4 text-sm font-bold text-white transition-colors hover:bg-slate-800 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-sky-600 focus-visible:ring-offset-2 sm:col-span-2"
        >
          <MapPin className="size-5 shrink-0 text-sky-300" aria-hidden="true" />
          Tìm cơ sở y tế gần nhất
        </button>

        <Link
          href="/history"
          className="flex min-h-12 items-center justify-center gap-2 rounded-xl border border-slate-300 bg-card px-4 text-sm font-bold text-slate-800 transition-colors hover:bg-muted focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-sky-600 focus-visible:ring-offset-2 dark:text-slate-100 dark:border-slate-700"
        >
          <FolderHeart className="size-5 shrink-0 text-sky-700" aria-hidden="true" />
          Lịch sử khám
        </Link>
      </div>
    </section>
  );
}
