"use client";

import { Clock3, LoaderCircle, X } from "lucide-react";

import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import type { AgentStreamEvent } from "@/types/triage-chat";

interface AgentActivityCardProps {
  event: AgentStreamEvent;
  onCancel?: () => void;
}

export function AgentActivityCard({ event, onCancel }: AgentActivityCardProps) {
  const seconds = Math.max(0, Math.floor(event.elapsedMs / 1000));
  const progress = event.progress;
  const label = event.label ?? event.message;
  const detail = event.detail ?? (
    seconds >= 12
      ? "Lượt này cần thêm thời gian để đối chiếu an toàn. Bạn không cần gửi lại."
      : "Tiến trình sẽ tự cập nhật tại đây."
  );

  return (
    <section
      role="status"
      aria-live="polite"
      aria-atomic="true"
      aria-label="Trạng thái xử lý của trợ lý Triage"
      className="w-full max-w-3xl rounded-2xl border border-sky-200 bg-card p-6 text-slate-950 shadow-sm dark:text-slate-50"
    >
      <div className="flex items-start gap-4">
        <span className="flex size-12 shrink-0 items-center justify-center rounded-xl bg-sky-600 text-white">
          <LoaderCircle className="size-6 animate-spin" aria-hidden="true" />
        </span>

        <div className="min-w-0 flex-1">
          <div className="flex flex-wrap items-start justify-between gap-4">
            <div className="min-w-0">
              <h2 className="text-lg font-bold text-slate-950 dark:text-slate-50">{label}</h2>
              <p className="mt-2 text-sm leading-6 text-slate-700 dark:text-slate-200">{detail}</p>
            </div>
            <span className="flex items-center gap-2 text-sm font-semibold text-slate-600 dark:text-slate-300">
              <Clock3 className="size-4" aria-hidden="true" />
              {seconds} giây
            </span>
          </div>

          <div className="mt-4">
            <div
              role="progressbar"
              aria-label="Tiến độ xử lý"
              aria-valuemin={0}
              aria-valuemax={100}
              aria-valuenow={progress ?? undefined}
              className="h-2 overflow-hidden rounded-full bg-slate-200 dark:bg-slate-700"
            >
              <span
                className={cn(
                  "block h-full rounded-full bg-sky-600",
                  progress == null && "w-1/3 animate-pulse",
                )}
                style={progress == null ? undefined : { width: `${progress}%` }}
              />
            </div>
            <div className="mt-2 flex items-center justify-between gap-4 text-sm text-slate-600 dark:text-slate-300">
              <span>{event.phase?.replaceAll("_", " ") ?? "ĐANG TIẾP NHẬN"}</span>
              {progress != null && <span>{progress}%</span>}
            </div>
          </div>

          {onCancel && (
            <Button
              type="button"
              variant="outline"
              onClick={onCancel}
              className={cn(
                "mt-4 min-h-12 gap-2 border-slate-300 px-4 text-sm text-slate-700 dark:text-slate-200 dark:border-slate-700",
                "focus-visible:ring-sky-600",
              )}
            >
              <X className="size-5" aria-hidden="true" />
              Hủy lượt xử lý
            </Button>
          )}
        </div>
      </div>
    </section>
  );
}
