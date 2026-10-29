"use client";

import Link from "next/link";
import { AnimatePresence, motion } from "framer-motion";
import { FileText, ShieldAlert } from "lucide-react";

import { useAcknowledgeAlert } from "@/hooks/mutations/use-hitl-mutations";
import { useNurseQueue } from "@/hooks/queries/use-clinical-hitl";
import { IS_PILOT_AGENT_ACTIVE } from "@/lib/agent-mode";
import { DURATION, dropVariants } from "@/lib/motion";
import { useSimpleNurseQueue } from "@/queries/useSimpleNurseQueries";
import type { SimpleNurseQueueItemDTO } from "@/types/simple-nurse";
import { urgencyRank } from "@/components/clinical/nurse-simple/queue/queue-model";

/**
 * Cảnh báo ca khẩn ở mọi trang lâm sàng, không riêng màn hàng đợi.
 *
 * Khi Triage Agent là luồng đang chạy, nguồn phải là hàng đợi của chính nó.
 * Đọc hàng đợi cũ ở chế độ đó nghĩa là một ca ESI 1/2 mới của người bệnh chỉ
 * hiện thành một dòng nhấp nháy trên màn hàng đợi -- điều dưỡng đang đứng ở
 * màn khác sẽ không thấy. `IS_PILOT_AGENT_ACTIVE` cố định lúc build, nên chọn
 * component theo nó không làm đổi thứ tự hook giữa các lần render.
 *
 * Chuyển động: dải cảnh báo trượt xuống khi xuất hiện, biểu tượng tỏa ba vòng
 * sáng rồi đứng yên. Đổi sang một ca khẩn khác thì dải cũ rút đi trước, dải mới
 * mới trượt vào -- người trực thấy rõ cảnh báo vừa đổi ca.
 */
export function GlobalRedFlagAlert() {
  return IS_PILOT_AGENT_ACTIVE ? <PilotUrgentCaseAlert /> : <LegacyRedFlagAlert />;
}

const alertBand =
  "border-b border-rose-200 bg-rose-50 px-4 py-4 sm:px-6 lg:px-8 dark:border-rose-500/30 dark:bg-rose-950/60";

const openCaseLink =
  "flex min-h-11 shrink-0 items-center gap-2 rounded-xl bg-rose-700 px-4 text-sm font-bold text-white transition-colors hover:bg-rose-800 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-rose-700 focus-visible:ring-offset-2 focus-visible:ring-offset-rose-50 dark:focus-visible:ring-offset-rose-950";

function AlertIcon() {
  return (
    <span
      aria-hidden="true"
      className="ring-pulse flex size-12 shrink-0 items-center justify-center rounded-2xl bg-rose-700 text-white"
    >
      <ShieldAlert className="size-6" strokeWidth={2.4} />
    </span>
  );
}

function isUrgentUnclaimed(item: SimpleNurseQueueItemDTO): boolean {
  return urgencyRank(item) <= 2 && item.review_status === "WAITING_REVIEW" && item.assigned_nurse_id === null;
}

/** Ca chưa ai nhận ở mức ESI 1/2 hoặc đang bị gắn cờ: khẩn nhất trước, rồi ca chờ lâu nhất. */
export function pickUrgentUnclaimedCase(items: SimpleNurseQueueItemDTO[]): SimpleNurseQueueItemDTO | null {
  const urgent = items.filter(isUrgentUnclaimed);
  urgent.sort(
    (a, b) =>
      urgencyRank(a) - urgencyRank(b) || new Date(a.waiting_since).getTime() - new Date(b.waiting_since).getTime(),
  );
  return urgent[0] ?? null;
}

function alertHeading(item: SimpleNurseQueueItemDTO): string {
  if (item.ai_proposed_esi !== null && item.ai_proposed_esi <= 2) {
    return `Ca ESI ${item.ai_proposed_esi} chưa có người nhận:`;
  }
  return `Ca cần xem ngay (${item.attention_reason ?? "dấu hiệu nguy kịch"}) chưa có người nhận:`;
}

function PilotUrgentCaseAlert() {
  const queue = useSimpleNurseQueue({ bucket: "QUEUE", mineOnly: false, esiLevels: [1, 2], page: 1, pageSize: 20 });
  const items = queue.data?.items ?? [];
  const alert = pickUrgentUnclaimedCase(items);
  const patientLabel = alert ? alert.patient_name || alert.patient_email || "Người bệnh chưa định danh" : "";
  const otherUrgent = alert
    ? items.filter((item) => item.session_id !== alert.session_id && isUrgentUnclaimed(item)).length
    : 0;

  // Không có nút "đã thấy": cảnh báo tự rút khi có người nhận ca, vì việc
  // cần làm với một ca ESI 1/2 là nhận nó chứ không phải tắt chuông.
  return (
    <AnimatePresence mode="wait">
      {alert && (
        <motion.section
          key={alert.session_id}
          role="alert"
          aria-live="assertive"
          variants={dropVariants}
          initial="hidden"
          animate="visible"
          exit="exit"
          className={alertBand}
        >
          <div className="mx-auto flex max-w-6xl flex-wrap items-center gap-4">
            <AlertIcon />
            <div className="min-w-0 flex-1 basis-64">
              <p className="text-lg font-bold leading-7 text-rose-950 dark:text-rose-50">
                {alertHeading(alert)} <span className="break-words">{patientLabel}</span>
              </p>
              <p className="line-clamp-2 text-base leading-6 text-rose-900 dark:text-rose-100">{alert.initial_message}</p>
              {otherUrgent > 0 && (
                <p className="mt-2 text-sm font-semibold text-rose-800 dark:text-rose-200">
                  Còn {otherUrgent} ca khẩn khác đang chờ nhận.
                </p>
              )}
            </div>
            <Link
              href={`/clinical/cases-pilot/${encodeURIComponent(alert.session_id)}`}
              aria-label={`Mở hồ sơ lâm sàng của ${patientLabel}`}
              className={openCaseLink}
            >
              <FileText className="size-4" aria-hidden="true" />
              Mở hồ sơ lâm sàng
            </Link>
          </div>
        </motion.section>
      )}
    </AnimatePresence>
  );
}

function LegacyRedFlagAlert() {
  const queue = useNurseQueue({ mineOnly: false, urgentOnly: true, needsInfoOnly: false });
  const alert = queue.data?.items.find((item) => item.is_red_flag && !item.alert_acknowledged);
  const acknowledge = useAcknowledgeAlert(alert?.case_id ?? "");

  return (
    <AnimatePresence mode="wait">
      {alert && (
        <motion.section
          key={alert.case_id}
          role="alert"
          aria-live="assertive"
          variants={dropVariants}
          initial="hidden"
          animate="visible"
          exit="exit"
          className={alertBand}
        >
          <div className="mx-auto flex max-w-6xl flex-wrap items-center gap-4">
            <AlertIcon />
            <div className="min-w-0 flex-1 basis-64">
              <p className="text-lg font-bold leading-7 text-rose-950 dark:text-rose-50">
                Ca Red Flag mới: <span className="break-words">{alert.patient_name}</span>
              </p>
              <p className="text-base leading-6 text-rose-900 dark:text-rose-100">{alert.chief_complaint}</p>
              <p className="mt-2 text-sm text-rose-800 dark:text-rose-200">
                Xác nhận không xóa cảnh báo và không hoàn tất ca.
              </p>
            </div>
            <div className="flex flex-wrap items-center gap-2">
              <Link
                href={`/clinical/cases/${encodeURIComponent(alert.case_id)}`}
                aria-label={`Mở hồ sơ lâm sàng của ${alert.patient_name}`}
                className={openCaseLink}
              >
                <FileText className="size-4" aria-hidden="true" />
                Mở hồ sơ lâm sàng
              </Link>
              <motion.button
                type="button"
                whileTap={{ scale: 0.97 }}
                transition={{ duration: DURATION.press }}
                disabled={acknowledge.isPending}
                onClick={() => acknowledge.mutate(alert.case_version)}
                className="flex min-h-11 shrink-0 items-center rounded-xl border border-rose-300 bg-card px-4 text-sm font-bold text-rose-900 transition-colors hover:bg-rose-100 disabled:opacity-60 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-rose-700 focus-visible:ring-offset-2 dark:border-rose-500/40 dark:text-rose-100 dark:hover:bg-rose-500/15"
              >
                Xác nhận đã thấy
              </motion.button>
            </div>
          </div>
        </motion.section>
      )}
    </AnimatePresence>
  );
}
