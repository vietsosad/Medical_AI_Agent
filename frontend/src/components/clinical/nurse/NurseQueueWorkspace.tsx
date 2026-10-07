"use client";

import {
  AlertTriangle,
  ClipboardList,
  Clock3,
  FileCheck2,
  HeartPulse,
  MessageSquareText,
  PhoneCall,
  RefreshCw,
  ShieldAlert,
  UserRoundCheck,
} from "lucide-react";
import { useRouter } from "next/navigation";
import { useState } from "react";

import { Button } from "@/components/ui/button";
import { useClaimCase } from "@/hooks/mutations/use-hitl-mutations";
import { useClinicalRealtime } from "@/components/clinical/ClinicalRealtimeProvider";
import { useNurseQueue } from "@/hooks/queries/use-clinical-hitl";
import { cn } from "@/lib/utils";
import { useAuthStore } from "@/store/useAuthStore";
import type { EsiLevel, NurseQueueItemDTO, ReviewStatus } from "@/types/clinical-hitl";

const statusLabels: Record<ReviewStatus, string> = {
  WAITING_REVIEW: "Chưa nhận",
  ASSIGNED: "Đã phân công",
  IN_REVIEW: "Đang rà soát",
  NEEDS_MORE_INFO: "Thiếu dữ liệu",
  SPECIALIST_REVIEW_REQUIRED: "Cần đánh giá chuyên sâu",
  TRIAGE_DECIDED: "Đã chốt ESI",
  HANDED_OFF: "Đã bàn giao",
};

function formatElapsed(totalSeconds: number): string {
  const minutes = Math.floor(totalSeconds / 60);
  if (minutes < 1) return "Dưới 1 phút";
  if (minutes < 60) return `${minutes} phút`;
  const hours = Math.floor(minutes / 60);
  return `${hours} giờ ${minutes % 60} phút`;
}

function esiClasses(esi: EsiLevel | null): string {
  if (esi === 1) return "border-rose-300 bg-rose-50 text-rose-900";
  if (esi === 2) return "border-amber-300 bg-amber-50 text-amber-950";
  if (esi === 3) return "border-sky-200 bg-sky-50 text-sky-900";
  if (esi === 4 || esi === 5) return "border-emerald-200 bg-emerald-50 text-emerald-900";
  return "border-border bg-muted text-slate-700 dark:text-slate-200";
}

function QueueCase({ item }: { item: NurseQueueItemDTO }) {
  const router = useRouter();
  const currentUserId = useAuthStore((state) => state.user?.id);
  const claim = useClaimCase(item.case_id);
  const { openQuickChat } = useClinicalRealtime();
  const mine = item.assignee?.id === currentUserId;
  const ownedByOther = Boolean(item.assignee && !mine);

  const openCase = () => {
    if (mine) {
      router.push(`/clinical/cases/${item.case_id}`);
      return;
    }
    claim.mutate(
      { case_version: item.case_version, action: "CLAIM" },
      { onSuccess: () => router.push(`/clinical/cases/${item.case_id}`) },
    );
  };

  return (
    <article
      className={cn(
        "grid gap-4 border-b border-border bg-card p-4 transition-colors last:border-b-0 hover:bg-background/70 lg:grid-cols-[9rem_minmax(0,1fr)_11rem_12rem] lg:items-center",
        item.is_red_flag && "border-l-4 border-l-rose-600 bg-rose-50/30 hover:bg-rose-50/60",
      )}
    >
      <div>
        <span
          className={cn(
            "inline-flex min-h-11 items-center rounded-lg border px-4 text-base font-bold",
            esiClasses(item.ai_recommended_esi),
          )}
        >
          {item.is_red_flag ? "Red Flag" : item.ai_recommended_esi ? `ESI ${item.ai_recommended_esi}` : "Chưa có ESI"}
        </span>
      </div>

      <div className="min-w-0">
        <div className="flex flex-wrap items-center gap-2">
          <h2 className="text-lg font-semibold text-slate-950 dark:text-slate-50">{item.patient_name}</h2>
          <span className="text-sm text-slate-600 dark:text-slate-300">
            {[item.age !== null ? `${item.age} tuổi` : null, item.sex].filter(Boolean).join(" · ") ||
              "Chưa có nhân khẩu học"}
          </span>

          {/* Người bệnh đã nhắn mà chưa ai đọc. Không thấy được từ hàng đợi thì
              tin đó nằm im cho tới khi có người tình cờ mở ca ra. */}
          {item.unread_count > 0 && (
            <span
              title={`${item.unread_count} tin nhắn của người bệnh chưa đọc`}
              className="inline-flex items-center gap-1.5 rounded-full border border-teal-300 bg-teal-50 px-2.5 py-0.5 text-xs font-bold text-teal-900"
            >
              <MessageSquareText className="size-3.5 shrink-0" aria-hidden="true" />
              {item.unread_count} tin mới
            </span>
          )}
        </div>
        <p className="mt-2 line-clamp-2 text-base leading-6 text-slate-800 dark:text-slate-100">
          {item.chief_complaint.trim() || "Chưa ghi nhận triệu chứng chính"}
        </p>
        {!item.data_completeness.is_complete && (
          <p className="mt-2 flex items-center gap-2 text-sm font-medium text-amber-800">
            <AlertTriangle className="size-4 shrink-0" aria-hidden="true" />
            Thiếu: {item.data_completeness.missing_fields.join(", ")}
          </p>
        )}
      </div>

      <div className="text-sm text-slate-700 dark:text-slate-200">
        <p className="flex items-center gap-2 text-base font-semibold text-slate-950 dark:text-slate-50">
          <Clock3 className="size-5" aria-hidden="true" />
          {formatElapsed(item.wait_time_seconds)}
        </p>
        <p className="mt-2">{statusLabels[item.review_status]}</p>
        {item.assignee && <p className="mt-2 truncate">{item.assignee.name}</p>}
      </div>

      <div className="space-y-2">
        {/* Trả lời được ngay từ hàng đợi: bắt mở toàn bộ hồ sơ chỉ để nhắn một
            câu chính là thứ làm tin của người bệnh nằm im ở bản trước. */}
        <Button
          type="button"
          variant="outline"
          onClick={() => openQuickChat(item.case_id)}
          className={cn(
            "min-h-11 w-full text-sm font-semibold",
            item.unread_count > 0
              ? "border-teal-400 bg-teal-50 text-teal-900 hover:bg-teal-100"
              : "border-slate-300 bg-card text-slate-800 dark:text-slate-100 dark:border-slate-700",
          )}
        >
          <MessageSquareText className="size-4" aria-hidden="true" />
          {item.unread_count > 0 ? `Mở chat · ${item.unread_count} mới` : "Mở chat"}
        </Button>

        <Button
          type="button"
          onClick={openCase}
          disabled={ownedByOther || claim.isPending}
          className="min-h-11 w-full bg-sky-700 text-sm font-semibold text-white hover:bg-sky-800"
        >
          {claim.isPending
            ? "Đang nhận ca..."
            : ownedByOther
              ? "Đang được xử lý"
              : mine
                ? "Mở hồ sơ lâm sàng"
                : "Nhận và mở hồ sơ"}
        </Button>
        {claim.isError && (
          <p className="mt-2 text-sm text-rose-700" role="alert">
            {claim.error.message}
          </p>
        )}
      </div>
    </article>
  );
}

export function NurseQueueWorkspace({
  mineOnly = false,
  specialistOnly = false,
}: {
  mineOnly?: boolean;
  specialistOnly?: boolean;
}) {
  const [urgentOnly, setUrgentOnly] = useState(false);
  const [needsInfoOnly, setNeedsInfoOnly] = useState(false);
  // Kênh thời gian thực do thanh điều phối sở hữu để mỗi tab chỉ mở đúng một
  // kết nối; nó làm mới chung query key này, còn nhịp poll 10s là lưới an toàn.
  const queue = useNurseQueue({ mineOnly, urgentOnly, needsInfoOnly, specialistOnly });
  const title = specialistOnly
    ? "Đánh giá chuyên sâu"
    : mineOnly
      ? "Ca của tôi"
      : "Hàng đợi lâm sàng";
  const responseItems = queue.data?.items ?? [];
  const specialistItems = responseItems.filter(
    (item) => item.review_status === "SPECIALIST_REVIEW_REQUIRED",
  );
  const visibleItems = specialistOnly ? specialistItems : responseItems;
  const specialistCount = Math.max(
    queue.data?.summary.specialist_count ?? 0,
    specialistItems.length,
  );

  return (
    <div className="space-y-6">
      <header>
        <p className="text-sm font-semibold uppercase tracking-wide text-sky-800">Triage + HITL</p>
        <div className="mt-2 flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
          <div>
            <h1 className="text-3xl font-semibold tracking-tight text-slate-950 dark:text-slate-50">
              {title}
            </h1>
            <p className="mt-2 text-base text-slate-600 dark:text-slate-300">
              {specialistOnly
                ? "Các ca được đồng nghiệp yêu cầu rà soát lại vì dữ liệu mâu thuẫn hoặc nằm ngoài giao thức."
                : "Red Flag trước, sau đó ESI và thời gian chờ. Không áp dụng ngưỡng SLA khi cơ sở chưa cấu hình."}
            </p>
          </div>
          <div className="flex items-center gap-3">
          <Button
            type="button"
            variant="outline"
            onClick={() => void queue.refetch()}
            disabled={queue.isFetching}
            className="min-h-11 border-slate-300 bg-card text-slate-800 dark:text-slate-100 dark:border-slate-700"
          >
            <RefreshCw className={cn("size-4", queue.isFetching && "animate-spin")} aria-hidden="true" />
            Làm mới
          </Button>
          </div>
        </div>
      </header>

      <section className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4" aria-label="Tóm tắt hàng đợi">
        {(
          [
            {
              label: "Đang chờ",
              value: queue.data?.summary.total_waiting ?? 0,
              icon: ClipboardList,
              accent: "border-l-slate-400",
            },
            {
              label: "Nguy cấp",
              value: queue.data?.summary.urgent_count ?? 0,
              icon: ShieldAlert,
              // Đỏ chỉ dành cho ca thật sự nguy cấp; con số 0 không được nhuộm đỏ.
              accent:
                (queue.data?.summary.urgent_count ?? 0) > 0
                  ? "border-l-rose-600"
                  : "border-l-slate-300",
            },
            {
              label: "Đánh giá chuyên sâu",
              value: specialistCount,
              icon: FileCheck2,
              accent: specialistCount > 0 ? "border-l-sky-600" : "border-l-slate-300",
            },
            {
              label: "Chờ lâu nhất",
              value: formatElapsed(queue.data?.summary.longest_wait_seconds ?? 0),
              icon: Clock3,
              accent: "border-l-amber-500",
            },
          ] as const
        ).map((tile) => {
          const Icon = tile.icon;
          return (
            <div
              key={tile.label}
              className={cn(
                "rounded-xl border border-l-4 border-border bg-card p-4 shadow-xs transition-shadow hover:shadow-md",
                tile.accent,
              )}
            >
              <p className="flex items-center gap-2 text-sm font-semibold text-slate-600 dark:text-slate-300">
                <Icon className="size-4 shrink-0" aria-hidden="true" />
                {tile.label}
              </p>
              <p className="mt-2 text-2xl font-bold tabular-nums text-slate-950 dark:text-slate-50">{tile.value}</p>
            </div>
          );
        })}
      </section>

      <section
        className="rounded-xl border border-border bg-card p-4"
        aria-labelledby="clinical-tools-title"
      >
        <h2 id="clinical-tools-title" className="text-sm font-bold text-foreground">
          Mở một ca để dùng các công cụ lâm sàng
        </h2>
        <ul className="mt-3 flex flex-wrap gap-2">
          {(
            [
              { label: "Sinh hiệu có nguồn", icon: HeartPulse },
              { label: "SBAR, căn cứ và transcript", icon: MessageSquareText },
              { label: "Xác nhận hoặc điều chỉnh ESI", icon: UserRoundCheck },
              { label: "Liên hệ khẩn cấp và hội thoại", icon: PhoneCall },
              { label: "Yêu cầu đánh giá chuyên sâu", icon: FileCheck2 },
            ] as const
          ).map((tool) => {
            const Icon = tool.icon;
            return (
              <li
                key={tool.label}
                className="inline-flex items-center gap-2 rounded-lg border border-border bg-background px-3 py-1.5 text-sm font-medium text-slate-700 dark:text-slate-200"
              >
                <Icon className="size-4 shrink-0 text-sky-700" aria-hidden="true" />
                {tool.label}
              </li>
            );
          })}
        </ul>
      </section>

      <section className="flex flex-wrap gap-2" aria-label="Bộ lọc hàng đợi">
        <Button
          type="button"
          variant="outline"
          aria-pressed={urgentOnly}
          onClick={() => setUrgentOnly((value) => !value)}
          className={cn("min-h-11", urgentOnly && "border-rose-300 bg-rose-50 text-rose-900")}
        >
          <ShieldAlert className="size-4" aria-hidden="true" />
          Chỉ ca nguy cấp
        </Button>
        <Button
          type="button"
          variant="outline"
          aria-pressed={needsInfoOnly}
          onClick={() => setNeedsInfoOnly((value) => !value)}
          className={cn("min-h-11", needsInfoOnly && "border-amber-300 bg-amber-50 text-amber-950")}
        >
          <AlertTriangle className="size-4" aria-hidden="true" />
          Chỉ ca thiếu dữ liệu
        </Button>
      </section>

      <section className="overflow-hidden rounded-xl border border-border bg-card" aria-label="Danh sách ca ưu tiên">
        {queue.isLoading && (
          <div className="space-y-4 p-4" aria-busy="true">
            {["queue-loading-1", "queue-loading-2", "queue-loading-3"].map((key) => (
              <div key={key} className="h-32 animate-pulse rounded-lg bg-muted" />
            ))}
          </div>
        )}
        {queue.isError && (
          <div className="p-8 text-center" role="alert">
            <AlertTriangle className="mx-auto size-8 text-rose-700" aria-hidden="true" />
            <p className="mt-4 text-base font-semibold text-slate-950 dark:text-slate-50">Không tải được hàng đợi thật</p>
            <p className="mt-2 text-sm text-slate-600 dark:text-slate-300">{queue.error.message}</p>
          </div>
        )}
        {visibleItems.map((item) => <QueueCase key={item.case_id} item={item} />)}
        {queue.data && visibleItems.length === 0 && (
          <div className="p-8 text-center">
            <UserRoundCheck className="mx-auto size-8 text-emerald-700" aria-hidden="true" />
            <p className="mt-4 text-base font-semibold text-slate-950 dark:text-slate-50">Không có ca phù hợp bộ lọc</p>
          </div>
        )}
      </section>
    </div>
  );
}
