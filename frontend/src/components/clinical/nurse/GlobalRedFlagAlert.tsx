"use client";

import Link from "next/link";
import { FileText, ShieldAlert } from "lucide-react";

import { Button } from "@/components/ui/button";
import { useAcknowledgeAlert } from "@/hooks/mutations/use-hitl-mutations";
import { useNurseQueue } from "@/hooks/queries/use-clinical-hitl";

export function GlobalRedFlagAlert() {
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
