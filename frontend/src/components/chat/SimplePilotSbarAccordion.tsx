"use client";

import React, { useState } from "react";
import Link from "next/link";
import { toast } from "sonner";
import {
  Accordion,
  AccordionContent,
  AccordionItem,
  AccordionTrigger,
} from "@/components/ui/accordion";
import {
  AlertCircle,
  BookOpen,
  CheckCircle2,
  Download,
  FileText,
  FolderHeart,
  Loader2,
  MapPin,
  ShieldCheck,
  XCircle,
} from "lucide-react";
import { cn } from "@/lib/utils";
import type { SimpleAgentCitationDTO, SimpleAgentSbarDTO } from "@/types/simple-nurse";
import { ClinicalMarkdown } from "@/components/chat/ClinicalMarkdown";
import { simpleTriageService } from "@/services/simple-triage.service";

// EQ/NEQ/GT/GTE/LT/LTE -> ký hiệu toán học dễ đọc, mirror cách hiển thị điều
// kiện đã dùng ở protocol_atoms.jsonl.
const OPERATOR_SYMBOLS: Record<string, string> = {
  EQ: "=",
  NEQ: "≠",
  GT: ">",
  GTE: "≥",
  LT: "<",
  LTE: "≤",
};

function citationStatusMeta(status: SimpleAgentCitationDTO["status"]) {
  switch (status) {
    case "SATISFIED":
      return { label: "Đã thỏa mãn", className: "border-sky-200 bg-sky-50 text-sky-900", icon: CheckCircle2 };
    case "MISSING_INFO":
      return { label: "Chưa đủ dữ liệu", className: "border-amber-200 bg-amber-50 text-amber-900", icon: AlertCircle };
    case "CONTRADICTED":
    default:
      return { label: "Không khớp", className: "border-rose-200 bg-rose-50 text-rose-900", icon: XCircle };
  }
}

/**
 * Patient-facing SBAR for `/triage-pilot`, structurally forked from
 * production's `SbarSummaryAccordion.tsx` (same accordion pattern, sections,
 * citation chips) -- but with the two production-only side actions dropped/
 * redirected, since neither maps onto simple_agent:
 *  - "Lịch sử khám" now points at `/triage-pilot/history`, not production's
 *    `/history`.
 *  - The PDF button now calls the pilot's own
 *    `GET /simple-triage/sessions/{id}/pdf` (added alongside the history-page
 *    redesign) instead of production's `downloadSbarPdf()` -- downloadable
 *    as soon as this component renders at all (only ever COMPLETED, see
 *    page.tsx), regardless of nurse-review status; the PDF itself states
 *    that honestly (see `routes_simple_triage.py`'s `export_simple_triage_pdf`).
 * Only ever rendered once a session is COMPLETED (see page.tsx), so there is
 * no `finalized` prop to thread through -- `sessionId` is needed only for
 * the PDF call.
 */

const SBAR_SECTIONS = [
  { key: "situation", code: "S", title: "Situation — Tình trạng hiện tại", accent: "border-sky-600 text-sky-800" },
  { key: "background", code: "B", title: "Background — Tiền sử liên quan", accent: "border-amber-500 text-amber-900" },
  { key: "assessment", code: "A", title: "Assessment — Đánh giá lâm sàng", accent: "border-rose-500 text-rose-800" },
  { key: "recommendation", code: "R", title: "Recommendation — Khuyến nghị", accent: "border-emerald-600 text-emerald-800" },
] as const satisfies ReadonlyArray<{
  key: keyof Pick<SimpleAgentSbarDTO, "situation" | "background" | "assessment" | "recommendation">;
  code: string;
  title: string;
  accent: string;
}>;

export function SimplePilotSbarAccordion({
  sbar,
  sessionId,
}: {
  sbar: SimpleAgentSbarDTO;
  sessionId: string;
}) {
  const [isDownloading, setIsDownloading] = useState(false);

  const handleLocateHospital = () => {
    window.open(
      "https://www.google.com/maps/search/Benh+vien+cap+cuu+gan+nhat",
      "_blank",
      "noopener,noreferrer",
    );
  };

  const handleDownloadPdf = async () => {
    setIsDownloading(true);
    toast.info("Đang tạo phiếu SBAR...");
    try {
      await simpleTriageService.downloadPdf(sessionId);
      toast.success("Đã tải phiếu SBAR. Bạn có thể mở tệp để in.");
    } catch (error: unknown) {
      const message = error instanceof Error ? error.message : "Không thể tạo phiếu SBAR lúc này.";
      toast.error(message);
    } finally {
      setIsDownloading(false);
    }
  };

  return (
    <section className="w-full space-y-4 font-sans">
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
                  <div key={section.key} className={cn("space-y-2 border-l-4 pl-4", section.accent)}>
                    <h3 className="text-sm font-bold uppercase tracking-wide">
                      {section.code}. {section.title}
                    </h3>
                    <ClinicalMarkdown
                      content={sbar[section.key]}
                      className="text-base font-medium leading-7 text-slate-800 dark:text-slate-100"
                    />
                  </div>
                ))}

                {sbar.citations.length > 0 && (
                  <div className="space-y-2 border-t border-border pt-4">
                    <h3 className="flex items-center gap-2 text-sm font-bold text-slate-800 dark:text-slate-100">
                      <BookOpen className="size-5 text-sky-700" aria-hidden="true" />
                      Phác đồ đã tham chiếu trong phiên
                    </h3>
                    <p className="text-sm leading-6 text-slate-600 dark:text-slate-300">
                      Mỗi mục tự nói rõ đã thỏa mãn điều kiện hay chưa, và vì sao — không phải mọi
                      mục đều dẫn tới kết luận ở trên.
                    </p>
                    <div className="space-y-2">
                      {sbar.citations.map((citation) => {
                        const meta = citationStatusMeta(citation.status);
                        const StatusIcon = meta.icon;
                        return (
                          <div key={citation.atom_id} className={cn("rounded-xl border p-3.5", meta.className)}>
                            <div className="flex flex-wrap items-center gap-2">
                              <StatusIcon className="size-4 shrink-0" aria-hidden="true" />
                              <span className="text-xs font-bold uppercase tracking-wide">{meta.label}</span>
                              {citation.decision_point && (
                                <span className="rounded-lg border border-white/70 bg-card/70 px-2 py-0.5 font-mono text-xs font-bold">
                                  {citation.decision_point}
                                </span>
                              )}
                              <span className="font-mono text-xs opacity-70">{citation.atom_id}</span>
                            </div>
                            {citation.criteria_text && (
                              <p className="mt-2 text-sm leading-6">{citation.criteria_text}</p>
                            )}
                            {citation.satisfied_requirements.length > 0 && (
                              <ul className="mt-2 space-y-1 text-sm font-semibold">
                                {citation.satisfied_requirements.map((req) => (
                                  <li key={req.fact_target_id}>
                                    {req.name} {OPERATOR_SYMBOLS[req.operator] ?? req.operator}{" "}
                                    {String(req.expected_value)} — bạn báo cáo: {String(req.actual_value)}
                                  </li>
                                ))}
                              </ul>
                            )}
                          </div>
                        );
                      })}
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
        <button
          type="button"
          onClick={() => void handleDownloadPdf()}
          disabled={isDownloading}
          className="flex min-h-12 items-center justify-center gap-2 rounded-xl border border-sky-300 bg-sky-50 px-4 text-sm font-bold text-sky-900 transition-colors hover:bg-sky-100 disabled:cursor-not-allowed disabled:opacity-60"
        >
          {isDownloading ? (
            <Loader2 className="size-5 shrink-0 animate-spin" aria-hidden="true" />
          ) : (
            <Download className="size-5 shrink-0" aria-hidden="true" />
          )}
          Tải / in phiếu SBAR
        </button>

        <button
          type="button"
          onClick={handleLocateHospital}
          className="flex min-h-12 items-center justify-center gap-2 rounded-xl bg-slate-900 px-4 text-sm font-bold text-white transition-colors hover:bg-slate-800 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-sky-600 focus-visible:ring-offset-2"
        >
          <MapPin className="size-5 shrink-0 text-sky-300" aria-hidden="true" />
          Tìm cơ sở y tế gần nhất
        </button>

        <Link
          href="/triage-pilot/history"
          className="flex min-h-12 items-center justify-center gap-2 rounded-xl border border-slate-300 bg-card px-4 text-sm font-bold text-slate-800 transition-colors hover:bg-muted focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-sky-600 focus-visible:ring-offset-2 dark:text-slate-100 dark:border-slate-700"
        >
          <FolderHeart className="size-5 shrink-0 text-sky-700" aria-hidden="true" />
          Lịch sử khám pilot
        </Link>
      </div>
    </section>
  );
}
