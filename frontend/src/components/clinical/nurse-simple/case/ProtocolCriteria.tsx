"use client";

import { memo } from "react";
import { motion } from "framer-motion";
import { AlertCircle, CheckCircle2, ListChecks, XCircle } from "lucide-react";

import { describeRequirement } from "@/components/clinical/nurse-simple/case/case-format";
import { riseIn, useInitialIds } from "@/components/clinical/nurse-simple/case/case-motion";
import { staggerDelay } from "@/lib/motion";
import { cn } from "@/lib/utils";
import type { SimpleAgentCitationDTO } from "@/types/simple-nurse";

/**
 * Các tiêu chí phác đồ mà trợ lý đã đem ra xét trong phiên (`seen_atom_ids`),
 * mỗi tiêu chí kèm trạng thái thật của nó. Không gọi chung là "đã khớp": một
 * tiêu chí có mặt ở đây vẫn có thể chưa bao giờ được thỏa mãn -- xem docstring
 * của `src/simple_agent/sbar.py`.
 */

const STATUS_META: Record<
  SimpleAgentCitationDTO["status"],
  { label: string; icon: typeof CheckCircle2; row: string; iconClass: string }
> = {
  SATISFIED: {
    label: "Khớp",
    icon: CheckCircle2,
    row: "bg-emerald-50 text-emerald-950 dark:bg-emerald-950/40 dark:text-emerald-100",
    iconClass: "text-emerald-700 dark:text-emerald-300",
  },
  MISSING_INFO: {
    label: "Thiếu thông tin",
    icon: AlertCircle,
    row: "bg-amber-50 text-amber-950 dark:bg-amber-950/40 dark:text-amber-100",
    iconClass: "text-amber-700 dark:text-amber-300",
  },
  CONTRADICTED: {
    label: "Không khớp",
    icon: XCircle,
    row: "bg-rose-50 text-rose-950 dark:bg-rose-950/40 dark:text-rose-100",
    iconClass: "text-rose-700 dark:text-rose-300",
  },
};

function ProtocolCriteriaView({
  citations,
  delay = 0,
}: {
  citations: SimpleAgentCitationDTO[];
  delay?: number;
}) {
  const initialIds = useInitialIds(citations.map((citation) => citation.atom_id));

  return (
    <motion.section
      {...riseIn(delay)}
      aria-labelledby="case-criteria-title"
      className="rounded-2xl border border-border bg-card p-4 shadow-xs sm:p-6"
    >
      <h2 id="case-criteria-title" className="flex items-center gap-2 text-base font-bold text-foreground">
        <ListChecks className="size-5 shrink-0 text-brand" aria-hidden="true" />
        Tiêu chí phác đồ đã xét
      </h2>
      <p className="mt-2 text-sm leading-6 text-muted-foreground">
        Từng tiêu chí kèm giá trị người bệnh đã khai báo, để bạn rà soát lại căn cứ của AI.
      </p>

      <ul className="mt-4 flex flex-col gap-2">
        {citations.map((citation, index) => {
          const meta = STATUS_META[citation.status];
          const Icon = meta.icon;
          // Các dòng có sẵn nối nhau hiện lên sau khi thẻ đã đứng yên; dòng
          // đến sau (ca còn đang trò chuyện) hiện ngay, không chờ lượt.
          const rowDelay = initialIds.has(citation.atom_id) ? delay + 0.1 + staggerDelay(index) : 0;
          return (
            <motion.li
              key={citation.atom_id}
              {...riseIn(rowDelay)}
              className={cn("flex items-start gap-2 rounded-xl p-4 text-sm leading-6", meta.row)}
            >
              <span className="flex h-6 shrink-0 items-center" aria-hidden="true">
                <Icon className={cn("size-5", meta.iconClass)} />
              </span>
              <div className="min-w-0 flex-1">
                <p className="break-words">
                  <strong>{meta.label}:</strong> {citation.criteria_text?.trim() || "Tiêu chí không kèm mô tả."}
                </p>
                {citation.satisfied_requirements.length > 0 && (
                  <ul className="mt-2 flex flex-col gap-2 font-semibold">
                    {citation.satisfied_requirements.map((requirement) => (
                      <li key={requirement.fact_target_id} className="break-words">
                        {describeRequirement(requirement)}
                      </li>
                    ))}
                  </ul>
                )}
                <p className="mt-2 font-medium">
                  Mã tiêu chí:{" "}
                  <span className="break-all font-mono">
                    {citation.decision_point ? `${citation.decision_point} · ` : ""}
                    {citation.atom_id}
                  </span>
                </p>
              </div>
            </motion.li>
          );
        })}
      </ul>
    </motion.section>
  );
}

/** Chỉ dựng lại khi danh sách tiêu chí thật sự đổi (xem ghi chú ở TranscriptCard). */
export const ProtocolCriteria = memo(ProtocolCriteriaView);
