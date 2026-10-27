"use client";

import Link from "next/link";
import { FileText, ShieldAlert } from "lucide-react";

import { Button } from "@/components/ui/button";
import { useAcknowledgeAlert } from "@/hooks/mutations/use-hitl-mutations";
import { useNurseQueue } from "@/hooks/queries/use-clinical-hitl";
import { IS_PILOT_AGENT_ACTIVE } from "@/lib/agent-mode";
import { useSimpleNurseQueue } from "@/queries/useSimpleNurseQueries";
import type { SimpleNurseQueueItemDTO } from "@/types/simple-nurse";

/**
 * Cảnh báo ca khẩn ở mọi trang lâm sàng, không riêng màn hàng đợi.
 *
 * Khi Triage Agent là luồng đang chạy, nguồn phải là hàng đợi của chính nó.
 * Đọc hàng đợi cũ ở chế độ đó nghĩa là một ca ESI 1/2 mới của người bệnh chỉ
 * hiện thành một dòng nhấp nháy trên màn hàng đợi -- điều dưỡng đang đứng ở
 * màn khác sẽ không thấy. `IS_PILOT_AGENT_ACTIVE` cố định lúc build, nên chọn
 * component theo nó không làm đổi thứ tự hook giữa các lần render.
 */
export function GlobalRedFlagAlert() {
  return IS_PILOT_AGENT_ACTIVE ? <PilotUrgentCaseAlert /> : <LegacyRedFlagAlert />;
}

/** Ca bị sàng lọc cấp cứu gắn cờ xếp ngang ESI 1 -- cùng quy tắc với hàng đợi ở backend. */
function urgencyRank(item: SimpleNurseQueueItemDTO): number {
  const rank = item.ai_proposed_esi ?? 6;
  return item.attention_required ? Math.min(rank, 1) : rank;
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

  // Không có nút "đã thấy": cảnh báo tự rút khi có người nhận ca, vì việc
  // cần làm với một ca ESI 1/2 là nhận nó chứ không phải tắt chuông.
  if (!alert) return null;

  const patientLabel = alert.patient_name || alert.patient_email || "Người bệnh chưa định danh";
  const otherUrgent = items.filter((item) => item.session_id !== alert.session_id && isUrgentUnclaimed(item)).length;

  return (
    <section className="border-b border-rose-300 bg-rose-50 p-4" role="alert" aria-live="assertive">
      <div className="mx-auto flex max-w-6xl flex-col gap-2">
        <p className="flex flex-wrap items-center gap-2 text-lg font-bold text-rose-950">
          <ShieldAlert className="size-6" aria-hidden="true" />
          <span>{alertHeading(alert)}</span>
          <Link
            href={`/clinical/cases-pilot/${encodeURIComponent(alert.session_id)}`}
            aria-label={`Mở hồ sơ lâm sàng của ${patientLabel}`}
            className="inline-flex min-h-11 min-w-11 items-center gap-2 rounded-lg px-2 underline decoration-2 underline-offset-4 transition-colors hover:bg-rose-100 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-rose-700 focus-visible:ring-offset-2 focus-visible:ring-offset-rose-50"
          >
            <span className="break-all">{patientLabel}</span>
            <FileText className="size-5 shrink-0" aria-hidden="true" />
          </Link>
        </p>
        <p className="text-base text-rose-900">{alert.initial_message}</p>
        {otherUrgent > 0 && (
          <p className="text-sm font-semibold text-rose-800">Còn {otherUrgent} ca khẩn khác đang chờ nhận.</p>
        )}
      </div>
    </section>
  );
}

function LegacyRedFlagAlert() {
  const queue = useNurseQueue({ mineOnly: false, urgentOnly: true, needsInfoOnly: false });
  const alert = queue.data?.items.find((item) => item.is_red_flag && !item.alert_acknowledged);
  const acknowledge = useAcknowledgeAlert(alert?.case_id ?? "");

  if (!alert) return null;

  return (
    <section
      className="border-b border-rose-300 bg-rose-50 p-4"
      role="alert"
      aria-live="assertive"
    >
      <div className="mx-auto flex max-w-6xl flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <p className="flex flex-wrap items-center gap-2 text-lg font-bold text-rose-950">
            <ShieldAlert className="size-6" aria-hidden="true" />
            <span>Ca Red Flag mới:</span>
            <Link
              href={`/clinical/cases/${encodeURIComponent(alert.case_id)}`}
              aria-label={`Mở hồ sơ lâm sàng của ${alert.patient_name}`}
              className="inline-flex min-h-11 min-w-11 items-center gap-2 rounded-lg px-2 underline decoration-2 underline-offset-4 transition-colors hover:bg-rose-100 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-rose-700 focus-visible:ring-offset-2 focus-visible:ring-offset-rose-50"
            >
              <span className="break-all">{alert.patient_name}</span>
              <FileText className="size-5 shrink-0" aria-hidden="true" />
            </Link>
          </p>
          <p className="mt-2 text-base text-rose-900">{alert.chief_complaint}</p>
          <p className="mt-2 text-sm text-rose-800">Xác nhận không xóa cảnh báo và không hoàn tất ca.</p>
        </div>
        <Button
          type="button"
          variant="outline"
          disabled={acknowledge.isPending}
          onClick={() => acknowledge.mutate(alert.case_version)}
          className="min-h-11 shrink-0 border-rose-300 bg-card text-rose-900 hover:bg-rose-100"
        >
          Xác nhận đã thấy
        </Button>
      </div>
    </section>
  );
}
