"use client";

import { useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import {
  AlertCircle,
  ArchiveRestore,
  Archive,
  CheckCircle2,
  ChevronLeft,
  ChevronRight,
  Clock3,
  FlaskConical,
  Inbox,
  Loader2,
  Mail,
  MessagesSquare,
  RefreshCw,
  Search,
  ShieldAlert,
  Stethoscope,
  UserRound,
  UserRoundCheck,
  X,
} from "lucide-react";

import { useAuthStore } from "@/store/useAuthStore";
import { useClaimSimpleCase, useSimpleNurseQueue, useSimpleNurseQueueRealtime } from "@/queries/useSimpleNurseQueries";
import type { SimpleNurseQueueBucket, SimpleNurseQueueItemDTO } from "@/types/simple-nurse";
import { cn } from "@/lib/utils";
import { ESI_THEME, esiTheme } from "@/components/clinical/nurse-simple/esi-theme";
import { formatWait, waitClasses, waitingMinutes } from "@/components/clinical/nurse-simple/wait-time";

/**
 * Bảng điều phối ca Triage Agent (HITL). 4 tab đều gọi chung
 * `GET /nurse-simple/queue` (qua `useSimpleNurseQueue`), chỉ khác
 * `bucket`/`mine_only` -- không có 4 hook/endpoint riêng.
 *
 * NGÔN NGỮ THỊ GIÁC theo quy ước bảng phân loại cấp cứu:
 * - Mỗi ca có một dải màu mức độ ở mép trái, đọc được từ xa trong lúc trực.
 * - Bảng màu bám đúng thang ESI 5 cấp: 1 đỏ (hồi sức) - 2 cam (cấp cứu) -
 *   3 vàng (khẩn trương) - 4 lục (ít khẩn) - 5 lam (không khẩn).
 * - Thời gian chờ tự đổi màu khi kéo dài, vì đó là tín hiệu điều phối chứ
 *   không phải một dòng chữ trang trí.
 * Màu sắc luôn đi kèm chữ ("ESI 2", "Chờ 45 phút") -- không bao giờ là kênh
 * thông tin duy nhất, để người rối loạn sắc giác vẫn đọc được bảng.
 */

const PAGE_SIZE = 20;
const MIN_PARK_REASON_LENGTH = 10;

type TabKey = "queue" | "mine" | "parked" | "decided";

const TABS: Array<{
  key: TabKey;
  label: string;
  bucket: SimpleNurseQueueBucket;
  mineOnly: boolean;
  description: string;
}> = [
  { key: "queue", label: "Hàng đợi", bucket: "QUEUE", mineOnly: false, description: "Ca đã hoàn tất sàng lọc, đang chờ nhân viên y tế tiếp nhận" },
  { key: "mine", label: "Ca của tôi", bucket: "QUEUE", mineOnly: true, description: "Ca bạn đang phụ trách và cần ra quyết định" },
  { key: "parked", label: "Tạm gác lại", bucket: "PARKED", mineOnly: false, description: "Ca đã tạm gác, chờ bổ sung thông tin trước khi xử lý tiếp" },
  { key: "decided", label: "Đã xác nhận", bucket: "DECIDED", mineOnly: false, description: "Ca đã có quyết định phân luồng cuối cùng" },
];

function formatDateTime(iso: string): string {
  const parsed = new Date(iso);
  if (Number.isNaN(parsed.getTime())) return "";
  return parsed.toLocaleString("vi-VN", { day: "2-digit", month: "2-digit", hour: "2-digit", minute: "2-digit" });
}

function ParkReasonForm({
  onCancel,
  onConfirm,
  isPending,
}: {
  onCancel: () => void;
  onConfirm: (reason: string) => void;
  isPending: boolean;
}) {
  const [reason, setReason] = useState("");
  const tooShort = reason.trim().length < MIN_PARK_REASON_LENGTH;
  return (
    <div className="rise-in mt-3 space-y-2 rounded-xl border border-amber-200 bg-amber-50/80 p-3.5">
      <label className="block text-xs font-bold uppercase tracking-wide text-amber-900">
        Lý do tạm gác lại (tối thiểu {MIN_PARK_REASON_LENGTH} ký tự)
      </label>
      <textarea
        value={reason}
        onChange={(event) => setReason(event.target.value)}
        rows={2}
        placeholder="Vd: dữ liệu không rõ ràng, cần liên hệ thêm bệnh nhân trước khi xử lý..."
        className="w-full rounded-lg border border-amber-300 bg-card p-2.5 text-sm focus:border-amber-500 focus:outline-none focus:ring-1 focus:ring-amber-500"
      />
      <div className="flex items-center gap-2">
        <button
          type="button"
          onClick={() => onConfirm(reason.trim())}
          disabled={tooShort || isPending}
          className="glow-soft glow-rose flex min-h-10 items-center gap-2 rounded-lg border border-amber-700 bg-amber-700 px-3.5 text-sm font-semibold text-white hover:bg-amber-800 disabled:cursor-not-allowed disabled:opacity-50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-amber-600 focus-visible:ring-offset-2"
        >
          {isPending ? <Loader2 className="size-4 animate-spin" aria-hidden="true" /> : <Archive className="size-4" aria-hidden="true" />}
          Xác nhận tạm gác
        </button>
        <button
          type="button"
          onClick={onCancel}
          className="glow-soft glow-sky flex min-h-10 items-center rounded-lg border border-slate-300 bg-card px-3.5 text-sm font-semibold text-slate-700 hover:bg-muted focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-slate-500 focus-visible:ring-offset-2 dark:text-slate-200 dark:border-slate-700"
        >
          Hủy
        </button>
      </div>
    </div>
  );
}

/** Nhãn nhỏ dùng chung cho hàng thông tin phụ của mỗi ca. */
function MetaChip({
  icon: Icon,
  children,
  className,
}: {
  icon: React.ComponentType<{ className?: string }>;
  children: React.ReactNode;
  className?: string;
}) {
  return (
    <span
      className={cn(
        "inline-flex min-w-0 items-center gap-1.5 rounded-lg border px-2 py-1 text-xs font-semibold",
        className ?? "border-border bg-background text-slate-600 dark:text-slate-300",
      )}
    >
      <Icon className="size-3.5 shrink-0" aria-hidden="true" />
      <span className="truncate">{children}</span>
    </span>
  );
}

function QueueRow({ item, tab, index }: { item: SimpleNurseQueueItemDTO; tab: TabKey; index: number }) {
  const router = useRouter();
  const currentUserId = useAuthStore((state) => state.user?.id);
  const claim = useClaimSimpleCase(item.session_id);
  const [isParking, setIsParking] = useState(false);
  const mine = item.assigned_nurse_id === currentUserId;
  const ownedByOther = Boolean(item.assigned_nurse_id) && !mine;

  const theme = esiTheme(item.ai_proposed_esi);
  const minutes = waitingMinutes(item.waiting_since);
  // Chỉ hồi sức và cấp cứu mới được chuyển động. Nếu mức nào cũng nhấp nháy
  // thì chẳng mức nào nổi bật, và bảng trực thành một cái đèn nháy.
  // Ca bị bộ sàng lọc cấp cứu gắn cờ cũng được chuyển động, nhưng giữ màu
  // "chưa có ESI": cờ là lý do để xem ngay, không phải một mức ESI.
  const isHighAcuity = (item.ai_proposed_esi !== null && item.ai_proposed_esi <= 2) || Boolean(item.attention_required);

  const openCase = () => {
    if (mine || tab === "decided") {
      router.push(`/clinical/cases-pilot/${item.session_id}`);
      return;
    }
    claim.mutate(
      { version: item.case_version, action: "CLAIM" },
      { onSuccess: () => router.push(`/clinical/cases-pilot/${item.session_id}`) },
    );
  };

  const handlePark = (reason: string) => {
    claim.mutate({ version: item.case_version, action: "PARK", reason }, { onSuccess: () => setIsParking(false) });
  };

  const handleRestore = () => {
    claim.mutate({ version: item.case_version, action: "RESTORE" });
  };

  return (
    <article
      style={{ "--rise-delay": `${Math.min(index, 8) * 45}ms` } as React.CSSProperties}
      className={cn(
        "rise-in group/row relative border-b border-border bg-card last:border-b-0",
        "transition-[background-color,box-shadow] duration-200",
        "hover:bg-sky-50/40 hover:shadow-[inset_0_0_0_1px_rgb(2_132_199/0.28)]",
        "focus-within:bg-sky-50/40 focus-within:shadow-[inset_0_0_0_1px_rgb(2_132_199/0.4)]",
      )}
    >
      {/* Dải màu mức độ ở mép trái -- đọc được mức ưu tiên từ xa. Nở rộng khi
          con trỏ đặt lên hàng, nên mắt biết chắc đang đứng ở ca nào. */}
      <span
        className={cn(
          "absolute inset-y-0 left-0 w-1.5 transition-[width] duration-200 ease-out group-hover/row:w-2.5",
          theme.rail,
          isHighAcuity && "acuity-pulse",
        )}
        aria-hidden="true"
      />

      <div className="py-4 pl-5 pr-4 sm:pl-6">
        <div className="grid gap-4 lg:grid-cols-[7.5rem_minmax(0,1fr)_13rem] lg:items-start">
          {/* CỘT 1: MỨC ĐỘ */}
          <div className="flex flex-row items-center gap-2 lg:flex-col lg:items-start">
            <span
              className={cn(
                "inline-flex min-h-11 w-fit items-center rounded-xl border px-3.5 text-base font-black tabular-nums tracking-tight",
                "transition-transform duration-200 group-hover/row:scale-[1.04] motion-reduce:group-hover/row:scale-100",
                theme.chip,
                isHighAcuity && "border-2 shadow-xs",
              )}
            >
              {item.ai_proposed_esi ? `ESI ${item.ai_proposed_esi}` : "Chưa có ESI"}
            </span>
            <span className="text-xs font-semibold text-muted-foreground">{theme.label}</span>
          </div>

          {/* CỘT 2: DANH TÍNH + LÝ DO ĐẾN KHÁM */}
          <div className="min-w-0">
            <div className="flex flex-wrap items-center gap-x-2 gap-y-1">
              <UserRound className="size-4 shrink-0 text-slate-400" aria-hidden="true" />
              <span className="truncate text-sm font-bold text-foreground">
                {item.patient_name?.trim() || "Chưa rõ danh tính"}
              </span>
              {ownedByOther && (
                <span className="rounded-md border border-border bg-muted px-1.5 py-0.5 text-xs font-semibold text-slate-600 dark:text-slate-300">
                  Người khác phụ trách
                </span>
              )}
              {mine && tab !== "decided" && (
                <span className="rounded-md border border-sky-200 bg-sky-50 px-1.5 py-0.5 text-xs font-bold text-sky-800">
                  Bạn phụ trách
                </span>
              )}
            </div>

            <p className="mt-1.5 line-clamp-2 text-base leading-6 text-slate-800 dark:text-slate-100">
              {item.initial_message.trim() || "Chưa có mô tả triệu chứng"}
            </p>

            <div className="mt-2.5 flex flex-wrap items-center gap-1.5">
              {item.attention_required && (
                <MetaChip icon={ShieldAlert} className="border-rose-300 bg-rose-50 font-bold text-rose-900">
                  Cần xem ngay{item.attention_reason ? `: ${item.attention_reason}` : ""}
                </MetaChip>
              )}
              {item.session_status === "ACTIVE" && (
                <MetaChip icon={MessagesSquare} className="border-sky-200 bg-sky-50 text-sky-900">
                  Người bệnh vẫn đang trò chuyện
                </MetaChip>
              )}
              <MetaChip icon={Clock3} className={waitClasses(minutes)}>
                Chờ {formatWait(minutes)}
              </MetaChip>
              <MetaChip icon={MessagesSquare}>{item.turn_count} lượt hội thoại</MetaChip>
              {item.patient_email && <MetaChip icon={Mail}>{item.patient_email}</MetaChip>}
              {item.is_insufficient && (
                <MetaChip icon={AlertCircle} className="border-amber-200 bg-amber-50 text-amber-800">
                  Thiếu dữ liệu kết luận
                </MetaChip>
              )}
              {item.unread_count > 0 && (
                <MetaChip icon={Stethoscope} className="border-teal-600 bg-teal-600 text-white">
                  {item.unread_count} tin mới
                </MetaChip>
              )}
            </div>

            {tab === "parked" && item.parked_reason && (
              <p className="mt-2.5 rounded-lg border border-amber-200 bg-amber-50 p-2.5 text-sm leading-6 text-amber-900">
                <span className="font-bold">Lý do tạm gác:</span> {item.parked_reason}
                {item.parked_at && <span className="ml-1 text-amber-700">({formatDateTime(item.parked_at)})</span>}
              </p>
            )}

            {tab === "decided" && (
              <p className="mt-2.5 flex flex-wrap items-center gap-1.5 rounded-lg border border-emerald-200 bg-emerald-50 p-2.5 text-sm leading-6 text-emerald-900">
                <CheckCircle2 className="size-4 shrink-0" aria-hidden="true" />
                <span className="font-bold">
                  {item.decision_type === "ADJUST_ESI" ? "Đã điều chỉnh" : "Đã xác nhận"}: ESI {item.final_esi}
                </span>
                {item.decision_note && <span>— {item.decision_note}</span>}
                {item.decided_at && <span className="text-emerald-700">({formatDateTime(item.decided_at)})</span>}
              </p>
            )}
          </div>

          {/* CỘT 3: HÀNH ĐỘNG */}
          <div className="flex flex-wrap items-center gap-2 lg:justify-end">
            {tab === "decided" ? (
              <button
                type="button"
                onClick={openCase}
                className="glow-soft glow-sky min-h-11 rounded-xl border border-slate-300 bg-card px-4 text-sm font-semibold text-slate-800 hover:bg-muted focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-sky-600 focus-visible:ring-offset-2 dark:text-slate-100 dark:border-slate-700"
              >
                Xem hồ sơ ca
              </button>
            ) : tab === "parked" ? (
              <button
                type="button"
                onClick={handleRestore}
                disabled={claim.isPending}
                className="glow-soft glow-sky flex min-h-11 items-center gap-2 rounded-xl border border-sky-700 bg-sky-700 px-4 text-sm font-semibold text-white hover:bg-sky-800 disabled:opacity-60 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-sky-600 focus-visible:ring-offset-2"
              >
                <ArchiveRestore className="size-4" aria-hidden="true" />
                Đẩy lại hàng đợi
              </button>
            ) : ownedByOther ? (
              <span className="text-sm font-medium text-muted-foreground">Y tá khác phụ trách</span>
            ) : (
              <>
                <button
                  type="button"
                  onClick={openCase}
                  disabled={claim.isPending}
                  className="glow-soft glow-sky min-h-11 rounded-xl border border-sky-700 bg-sky-700 px-4 text-sm font-bold text-white shadow-xs hover:bg-sky-800 disabled:opacity-60 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-sky-600 focus-visible:ring-offset-2"
                >
                  {mine ? "Mở ca" : claim.isPending ? "Đang nhận..." : "Nhận ca"}
                </button>
                <button
                  type="button"
                  onClick={() => setIsParking((v) => !v)}
                  disabled={claim.isPending}
                  aria-expanded={isParking}
                  title="Tạm gác lại"
                  aria-label="Tạm gác lại ca này"
                  className="glow-soft glow-sky flex min-h-11 min-w-11 items-center justify-center rounded-xl border border-slate-300 bg-card text-slate-700 hover:bg-muted disabled:opacity-60 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-sky-600 focus-visible:ring-offset-2 dark:text-slate-200 dark:border-slate-700"
                >
                  <Archive className="size-4" aria-hidden="true" />
                </button>
              </>
            )}
          </div>
        </div>

        {isParking && <ParkReasonForm onCancel={() => setIsParking(false)} onConfirm={handlePark} isPending={claim.isPending} />}
      </div>
    </article>
  );
}

/** Ô chỉ số trên đầu bảng điều phối. */
function SummaryTile({
  icon: Icon,
  label,
  value,
  tone,
}: {
  icon: React.ComponentType<{ className?: string }>;
  label: string;
  value: number;
  tone: "neutral" | "active" | "warning";
}) {
  const tones = {
    neutral: {
      box: "border-border bg-card glow-sky",
      icon: "bg-muted text-slate-600 group-hover/tile:bg-slate-900 group-hover/tile:text-white dark:text-slate-300",
      value: "text-slate-950 dark:text-slate-50",
    },
    active: {
      box: "border-sky-200 bg-sky-50/60 glow-sky",
      icon: "bg-sky-100 text-sky-700 group-hover/tile:bg-sky-700 group-hover/tile:text-white",
      value: "text-sky-900",
    },
    warning: {
      box: "border-amber-200 bg-amber-50/70 glow-rose",
      icon: "bg-amber-100 text-amber-700 group-hover/tile:bg-amber-700 group-hover/tile:text-white",
      value: "text-amber-900",
    },
  }[tone];

  return (
    <div className={cn("group/tile glow-soft flex items-center gap-3.5 rounded-xl border p-4", tones.box)}>
      <span
        className={cn(
          "flex size-11 shrink-0 items-center justify-center rounded-xl transition-colors duration-200",
          tones.icon,
        )}
      >
        <Icon className="size-5" aria-hidden="true" />
      </span>
      <div className="min-w-0">
        <p className="text-xs font-bold uppercase tracking-wide text-muted-foreground">{label}</p>
        <p className={cn("mt-0.5 text-2xl font-black leading-none tabular-nums", tones.value)}>{value}</p>
      </div>
    </div>
  );
}

/**
 * Khung chờ mô phỏng đúng hình dáng một hàng ca thật. Một vòng xoay đứng giữa
 * màn hình không nói được sắp có bao nhiêu ca hay bảng trông ra sao, và bảng
 * giật một nhịp khi dữ liệu về. Khung chờ đúng hình thì không.
 */
function QueueRowSkeleton({ index }: { index: number }) {
  return (
    <div
      style={{ "--rise-delay": `${index * 70}ms` } as React.CSSProperties}
      className="rise-in skeleton-sweep relative overflow-hidden border-b border-border bg-card py-4 pl-5 pr-4 last:border-b-0 sm:pl-6"
    >
      <span className="absolute inset-y-0 left-0 w-1.5 bg-slate-200 dark:bg-slate-700" aria-hidden="true" />
      <div className="grid gap-4 lg:grid-cols-[7.5rem_minmax(0,1fr)_13rem] lg:items-start">
        <div className="h-11 w-24 animate-pulse rounded-xl bg-slate-200 dark:bg-slate-700" />
        <div className="space-y-2.5">
          <div className="h-4 w-40 animate-pulse rounded bg-slate-200 dark:bg-slate-700" />
          <div className="h-4 w-full max-w-md animate-pulse rounded bg-muted" />
          <div className="flex gap-1.5">
            <div className="h-6 w-24 animate-pulse rounded-lg bg-muted" />
            <div className="h-6 w-28 animate-pulse rounded-lg bg-muted" />
          </div>
        </div>
        <div className="flex gap-2 lg:justify-end">
          <div className="h-11 w-24 animate-pulse rounded-xl bg-slate-200 dark:bg-slate-700" />
          <div className="h-11 w-11 animate-pulse rounded-xl bg-muted" />
        </div>
      </div>
    </div>
  );
}

export function SimpleNurseQueueWorkspace() {
  // Mở khi trang hàng đợi đang mở -- xem `useSimpleNurseQueueRealtime`.
  useSimpleNurseQueueRealtime();

  const searchParams = useSearchParams();
  const tab = (searchParams.get("tab") as TabKey | null) ?? "queue";
  const activeTab = TABS.find((t) => t.key === tab) ?? TABS[0];

  const [q, setQ] = useState("");
  const [patientEmail, setPatientEmail] = useState("");
  const [esiLevels, setEsiLevels] = useState<number[]>([]);
  const [page, setPage] = useState(1);

  const toggleEsiLevel = (level: number) => {
    setEsiLevels((current) =>
      current.includes(level) ? current.filter((value) => value !== level) : [...current, level].sort(),
    );
  };

  const { data, isLoading, isError, error, refetch, isFetching } = useSimpleNurseQueue({
    bucket: activeTab.bucket,
    mineOnly: activeTab.mineOnly,
    q: q.trim() || undefined,
    patientEmail: patientEmail.trim() || undefined,
    esiLevels: esiLevels.length > 0 ? esiLevels : undefined,
    page,
    pageSize: PAGE_SIZE,
  });

  const isFilterActive = q.trim() !== "" || patientEmail.trim() !== "" || esiLevels.length > 0;
  const resetFilters = () => {
    setQ("");
    setPatientEmail("");
    setEsiLevels([]);
  };

  // Reset về trang 1 khi đổi tab/bộ lọc -- theo đúng khuyến nghị của React
  // (đặt state trong lúc render thay vì dùng useEffect chỉ để gọi setState),
  // cùng cách đã dùng ở /triage-pilot/history/page.tsx.
  const filterKey = `${tab}|${q}|${patientEmail}|${esiLevels.join(",")}`;
  const [prevFilterKey, setPrevFilterKey] = useState(filterKey);
  if (filterKey !== prevFilterKey) {
    setPrevFilterKey(filterKey);
    if (page !== 1) setPage(1);
  }

  return (
    <div className="mx-auto max-w-6xl space-y-5 p-4 sm:p-6">

      {/* ------------------------------------------------ ĐẦU TRẠM ĐIỀU PHỐI */}
      <header className="overflow-hidden rounded-2xl border border-border bg-card shadow-xs">
        <div className="flex flex-wrap items-center justify-between gap-4 border-b border-slate-100 bg-gradient-to-r from-slate-50 to-white p-5">
          <div className="min-w-0">
            <div className="flex items-center gap-2.5">
              <span className="flex size-10 shrink-0 items-center justify-center rounded-xl bg-sky-700 text-white">
                <Inbox className="size-5" aria-hidden="true" />
              </span>
              <div className="min-w-0">
                <h1 className="truncate text-xl font-bold tracking-tight text-slate-950 dark:text-slate-50">{activeTab.label}</h1>
                <p className="mt-0.5 text-sm text-slate-600 dark:text-slate-300">{activeTab.description}</p>
              </div>
            </div>
          </div>

          <button
            type="button"
            onClick={() => void refetch()}
            disabled={isFetching}
            className="glow-soft glow-sky flex min-h-11 shrink-0 items-center gap-2 rounded-xl border border-slate-300 bg-card px-4 text-sm font-semibold text-slate-800 hover:bg-muted disabled:opacity-60 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-sky-600 focus-visible:ring-offset-2 dark:text-slate-100 dark:border-slate-700"
          >
            <RefreshCw className={cn("size-4", isFetching && "animate-spin")} aria-hidden="true" />
            Tải lại
          </button>
        </div>

        <p className="flex items-start gap-2 bg-amber-50 px-5 py-2.5 text-sm font-medium leading-6 text-amber-900">
          <FlaskConical className="mt-0.5 size-4 shrink-0" aria-hidden="true" />
          Hàng đợi Triage Agent — tách biệt hoàn toàn với hàng đợi Triage chính thức
        </p>
      </header>

      {/* ------------------------------------------------------- CHỈ SỐ TRẠM */}
      {data && (
        <div className="grid gap-3 sm:grid-cols-3">
          <SummaryTile icon={Inbox} label="Đang chờ" value={data.summary.total_waiting} tone="neutral" />
          <SummaryTile icon={UserRoundCheck} label="Bạn phụ trách" value={data.summary.mine_count} tone="active" />
          <SummaryTile icon={AlertCircle} label="Thiếu dữ liệu" value={data.summary.insufficient_count} tone="warning" />
        </div>
      )}

      {/* --------------------------------------------------------- BỘ LỌC CA */}
      <div className="space-y-3 rounded-2xl border border-border bg-card p-4">
        <div className="flex flex-col gap-3 sm:flex-row">
          <div className="relative flex-1">
            <Search className="pointer-events-none absolute left-3 top-1/2 size-4 -translate-y-1/2 text-slate-400" aria-hidden="true" />
            <input
              type="text"
              value={q}
              onChange={(event) => setQ(event.target.value)}
              placeholder="Tìm theo mã ca hoặc mô tả triệu chứng..."
              aria-label="Tìm theo mã ca hoặc mô tả triệu chứng"
              className="glow-soft glow-sky h-11 w-full rounded-xl border border-slate-300 bg-card pl-9 pr-3 text-sm text-slate-800 focus:border-sky-500 focus:outline-none focus:ring-1 focus:ring-sky-500 dark:text-slate-100 dark:border-slate-700"
            />
          </div>
          <div className="relative flex-1">
            <Mail className="pointer-events-none absolute left-3 top-1/2 size-4 -translate-y-1/2 text-slate-400" aria-hidden="true" />
            <input
              type="text"
              value={patientEmail}
              onChange={(event) => setPatientEmail(event.target.value)}
              placeholder="Tìm theo email bệnh nhân..."
              aria-label="Tìm theo email bệnh nhân"
              className="glow-soft glow-sky h-11 w-full rounded-xl border border-slate-300 bg-card pl-9 pr-3 text-sm text-slate-800 focus:border-sky-500 focus:outline-none focus:ring-1 focus:ring-sky-500 dark:text-slate-100 dark:border-slate-700"
            />
          </div>
          {isFilterActive && (
            <button
              type="button"
              onClick={resetFilters}
              className="glow-soft glow-rose flex min-h-11 shrink-0 items-center gap-1.5 rounded-xl border border-rose-200 bg-rose-50 px-3.5 text-sm font-bold text-rose-800 hover:bg-rose-100 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-rose-600 focus-visible:ring-offset-2"
            >
              <X className="size-3.5" aria-hidden="true" />
              Xóa bộ lọc
            </button>
          )}
        </div>

        <div className="flex flex-wrap items-center gap-2 border-t border-slate-100 pt-3">
          <span className="text-xs font-bold uppercase tracking-wide text-muted-foreground">Mức ESI:</span>
          {[1, 2, 3, 4, 5].map((level) => {
            const active = esiLevels.includes(level);
            return (
              <button
                key={level}
                type="button"
                onClick={() => toggleEsiLevel(level)}
                aria-pressed={active}
                className={cn(
                  "glow-soft glow-sky flex min-h-9 items-center gap-1.5 rounded-full border px-3 text-xs font-bold focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-sky-600 focus-visible:ring-offset-2",
                  active
                    ? "border-sky-600 bg-sky-600 text-white"
                    : "border-slate-300 bg-card text-slate-700 hover:bg-background dark:text-slate-200 dark:border-slate-700",
                )}
              >
                {/* Chấm luôn giữ đúng màu thang ESI, kể cả khi chip đã bật --
                    người trực đọc mức độ bằng màu ở cả hai trạng thái. */}
                <span
                  className={cn(
                    "size-2 rounded-full",
                    ESI_THEME[level].rail,
                    active && "ring-1 ring-white/80",
                  )}
                  aria-hidden="true"
                />
                ESI {level}
              </button>
            );
          })}
        </div>
      </div>

      {/* ---------------------------------------------------------- BẢNG CA */}
      <div className="overflow-hidden rounded-2xl border border-border bg-card shadow-xs">
        {isLoading ? (
          <>
            <span className="sr-only" role="status">
              Đang tải hàng đợi
            </span>
            {[0, 1, 2, 3].map((key) => (
              <QueueRowSkeleton key={key} index={key} />
            ))}
          </>
        ) : isError ? (
          <div role="alert" className="flex flex-col items-center gap-3 px-6 py-12 text-center">
            <span className="flex size-12 items-center justify-center rounded-2xl border border-rose-200 bg-rose-50 text-rose-700">
              <AlertCircle className="size-6" aria-hidden="true" />
            </span>
            <p className="text-sm font-bold text-rose-800">
              {error instanceof Error ? error.message : "Không thể tải hàng đợi."}
            </p>
            <button
              type="button"
              onClick={() => void refetch()}
              className="glow-soft glow-sky mt-1 flex min-h-11 items-center gap-2 rounded-xl border border-slate-300 bg-card px-4 text-sm font-bold text-slate-800 hover:bg-muted focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-sky-600 focus-visible:ring-offset-2 dark:text-slate-100 dark:border-slate-700"
            >
              <RefreshCw className={cn("size-4", isFetching && "animate-spin")} aria-hidden="true" />
              Thử tải lại
            </button>
          </div>
        ) : data && data.items.length > 0 ? (
          data.items.map((item, index) => (
            <QueueRow key={item.session_id} item={item} tab={tab} index={index} />
          ))
        ) : (
          <div className="flex flex-col items-center gap-3 px-6 py-14 text-center">
            <span className="flex size-14 items-center justify-center rounded-2xl border border-border bg-background text-slate-400">
              <Inbox className="size-7" aria-hidden="true" />
            </span>
            <p className="max-w-sm text-sm font-semibold leading-6 text-slate-600 dark:text-slate-300">
              {isFilterActive
                ? "Không có ca nào khớp bộ lọc hiện tại."
                : "Không có ca nào ở mục này. Ca mới sẽ tự hiện lên ngay khi bệnh nhân hoàn tất sàng lọc."}
            </p>
            {isFilterActive && (
              <button
                type="button"
                onClick={resetFilters}
                className="glow-soft glow-sky flex min-h-11 items-center rounded-xl border border-slate-300 bg-card px-4 text-sm font-bold text-sky-700 hover:bg-background focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-sky-600 focus-visible:ring-offset-2 dark:border-slate-700"
              >
                Xóa bộ lọc để xem toàn bộ
              </button>
            )}
          </div>
        )}
      </div>

      {/* -------------------------------------------------------- PHÂN TRANG */}
      {data && data.pagination.total_items > 0 && (
        <div className="flex flex-wrap items-center justify-between gap-3 rounded-2xl border border-border bg-card p-3.5">
          <span className="text-xs font-semibold text-muted-foreground">
            Hiển thị {(data.pagination.page - 1) * data.pagination.page_size + 1}-
            {Math.min(data.pagination.page * data.pagination.page_size, data.pagination.total_items)} trên{" "}
            {data.pagination.total_items} ca
          </span>
          <div className="flex items-center gap-2">
            <button
              type="button"
              disabled={data.pagination.page === 1}
              onClick={() => setPage((p) => Math.max(1, p - 1))}
              aria-label="Trang trước"
              className="glow-soft glow-sky flex size-10 items-center justify-center rounded-lg border border-slate-300 bg-card text-slate-700 hover:bg-muted disabled:cursor-not-allowed disabled:opacity-40 disabled:shadow-none focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-sky-600 focus-visible:ring-offset-2 dark:text-slate-200 dark:border-slate-700"
            >
              <ChevronLeft className="size-4" aria-hidden="true" />
            </button>
            <span className="text-sm font-semibold text-slate-700 dark:text-slate-200">
              Trang {data.pagination.page} / {data.pagination.total_pages}
            </span>
            <button
              type="button"
              disabled={data.pagination.page === data.pagination.total_pages}
              onClick={() => setPage((p) => Math.min(data.pagination.total_pages, p + 1))}
              aria-label="Trang sau"
              className="glow-soft glow-sky flex size-10 items-center justify-center rounded-lg border border-slate-300 bg-card text-slate-700 hover:bg-muted disabled:cursor-not-allowed disabled:opacity-40 disabled:shadow-none focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-sky-600 focus-visible:ring-offset-2 dark:text-slate-200 dark:border-slate-700"
            >
              <ChevronRight className="size-4" aria-hidden="true" />
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
