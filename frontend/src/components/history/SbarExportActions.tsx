"use client";

import React, { useState } from "react";
import { Check, Copy, Download, Loader2 } from "lucide-react";
import { cn } from "@/lib/utils";
import { downloadSbarPdf } from "@/lib/download-sbar-pdf";
import { toast } from "sonner";
import type { TriageSessionDetailDTO } from "@/types/clinical-history";
import { hasFinalizedSbar } from "@/components/history/history-session-state";

export interface SbarExportActionsProps {
  session: TriageSessionDetailDTO;
  className?: string;
}

export const SbarExportActions: React.FC<SbarExportActionsProps> = ({
  session,
  className,
}) => {
  const [isCopied, setIsCopied] = useState(false);
  const [isDownloading, setIsDownloading] = useState(false);

  if (!hasFinalizedSbar(session)) return null;

  const {
    session_id,
    created_at,
    chief_complaint,
    final_esi,
    sbar_report,
    hitl_signature,
  } = session;

  const handleDownloadPdf = async () => {
    setIsDownloading(true);
    toast.info("Đang tạo phiếu SBAR chuẩn A4...");
    try {
      await downloadSbarPdf(session_id);
      toast.success("Đã tải phiếu SBAR. Bạn có thể mở tệp để in.");
    } catch (error: unknown) {
      toast.error("Không thể tạo phiếu SBAR lúc này.");
      console.error(error);
    } finally {
      setIsDownloading(false);
    }
  };

  const handleCopySbar = async () => {
    const markdownText = `### PHIẾU TRIAGE LÂM SÀNG SBAR — MÃ CA #${session_id.slice(-8)}
**Thời điểm khám:** ${new Date(created_at).toLocaleString("vi-VN")}
**Triệu chứng chính:** ${chief_complaint}
**Phân độ:** ${final_esi == null ? "Chưa có kết luận ESI" : `ESI ${final_esi}`}
**Trạng thái thẩm định:** ${hitl_signature ? `${hitl_signature.status}${hitl_signature.reviewer_name ? ` — ${hitl_signature.reviewer_name}` : ""}` : "Đang chờ nhân viên y tế thẩm định"}

#### S — Situation / Tình trạng hiện tại
${sbar_report.situation}

#### B — Background / Tiền sử liên quan
${sbar_report.background}

#### A — Assessment / Đánh giá
${sbar_report.assessment}

#### R — Recommendation / Khuyến nghị
${sbar_report.recommendation}

**Mã nguồn được lưu cùng SBAR:** ${sbar_report.citations?.join(", ") || "Chưa ghi nhận"}`;

    try {
      await navigator.clipboard.writeText(markdownText);
      setIsCopied(true);
      toast.success("Đã sao chép nội dung SBAR.");
      window.setTimeout(() => setIsCopied(false), 2500);
    } catch (error: unknown) {
      toast.error("Không thể sao chép nội dung SBAR.");
      console.error(error);
    }
  };

  return (
    <div className={cn("space-y-4 pt-2 font-sans", className)}>
      <button
        type="button"
        onClick={handleDownloadPdf}
        disabled={isDownloading}
        className="flex min-h-12 w-full items-center justify-center gap-2 rounded-xl bg-sky-700 px-4 text-sm font-bold text-white transition-colors hover:bg-sky-800 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-sky-600 focus-visible:ring-offset-2 disabled:cursor-wait disabled:opacity-70"
      >
        {isDownloading ? (
          <Loader2 className="size-5 animate-spin" aria-hidden="true" />
        ) : (
          <Download className="size-5" aria-hidden="true" />
        )}
        {isDownloading
          ? "Đang tạo phiếu PDF..."
          : "Tải / in phiếu SBAR cho bác sĩ cấp cứu"}
      </button>

      <div className="grid grid-cols-1 gap-4">
        <button
          type="button"
          onClick={handleCopySbar}
          className="flex min-h-12 items-center justify-center gap-2 rounded-xl border border-slate-300 bg-card px-4 text-sm font-semibold text-slate-800 transition-colors hover:bg-muted focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-sky-600 focus-visible:ring-offset-2 dark:text-slate-100 dark:border-slate-700"
        >
          {isCopied ? (
            <Check className="size-5 text-emerald-600" aria-hidden="true" />
          ) : (
            <Copy className="size-5 text-sky-700" aria-hidden="true" />
          )}
          {isCopied ? "Đã sao chép SBAR" : "Sao chép trích lục"}
        </button>

      </div>
    </div>
  );
};

export default SbarExportActions;
