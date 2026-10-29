"use client";

import { memo } from "react";
import { motion } from "framer-motion";
import { ClipboardList } from "lucide-react";

import { riseIn } from "@/components/clinical/nurse-simple/case/case-motion";
import { cn } from "@/lib/utils";
import type { SimpleAgentSbarDTO } from "@/types/simple-nurse";

/**
 * Tóm tắt SBAR do backend ghép từ dữ kiện đã ghi nhận trong phiên (không phải
 * một lần gọi mô hình, xem `src/simple_agent/sbar.py`). Nó là tài liệu để đối
 * chiếu, không phải kết luận: mọi câu đều bắt nguồn từ lời người bệnh tự kể.
 */

const SBAR_SECTIONS: { key: "situation" | "background" | "assessment" | "recommendation"; letter: string; label: string }[] = [
  { key: "situation", letter: "S", label: "Tình huống" },
  { key: "background", letter: "B", label: "Bối cảnh" },
  { key: "assessment", letter: "A", label: "Đánh giá" },
  { key: "recommendation", letter: "R", label: "Khuyến nghị" },
];

function SbarSummaryView({ sbar, delay = 0 }: { sbar: SimpleAgentSbarDTO | null; delay?: number }) {
  return (
    <motion.section
      {...riseIn(delay)}
      aria-labelledby="case-sbar-title"
      className="@container overflow-hidden rounded-2xl border border-border bg-card shadow-xs"
    >
      <div className="flex flex-wrap items-center justify-between gap-2 border-b border-border px-4 py-4 sm:px-6">
        <h2 id="case-sbar-title" className="flex items-center gap-2 text-base font-bold text-foreground">
          <ClipboardList className="size-5 shrink-0 text-brand" aria-hidden="true" />
          Tóm tắt SBAR
        </h2>
        <p className="text-sm font-semibold text-muted-foreground">Tạo tự động từ cuộc hội thoại · cần đối chiếu</p>
      </div>

      {sbar ? (
        <dl className="grid @md:grid-cols-2">
          {SBAR_SECTIONS.map((section, index) => (
            <div
              key={section.key}
              className={cn(
                "border-border px-4 py-4 sm:px-6 @md:odd:border-r",
                index < 3 && "border-b",
                index === 2 && "@md:border-b-0",
              )}
            >
              <dt className="text-sm font-bold text-brand">
                {section.letter} · {section.label}
              </dt>
              <dd className="mt-2 break-words text-sm leading-6 text-foreground">{sbar[section.key]}</dd>
            </div>
          ))}
        </dl>
      ) : (
        <p className="px-4 py-4 text-sm leading-6 text-muted-foreground sm:px-6">
          Ca chưa có tóm tắt SBAR, thường vì người bệnh chưa hoàn tất phần hỏi đáp. Hãy đọc hội thoại gốc bên dưới.
        </p>
      )}

      <p className="border-t border-border bg-muted/40 px-4 py-2 text-sm leading-6 text-muted-foreground sm:px-6">
        Tổng hợp từ lời người bệnh khai báo, chưa phải chẩn đoán. Đối chiếu với hội thoại gốc trước khi chốt.
      </p>
    </motion.section>
  );
}

/** Chỉ dựng lại khi nội dung SBAR thật sự đổi (xem ghi chú ở TranscriptCard). */
export const SbarSummary = memo(SbarSummaryView);
