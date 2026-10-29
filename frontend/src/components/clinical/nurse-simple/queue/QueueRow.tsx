"use client";

import { useEffect, useId, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { AnimatePresence, motion, type Variants } from "framer-motion";
import {
  Archive,
  ArchiveRestore,
  ArrowRight,
  CircleAlert,
  CircleCheck,
  Clock3,
  LoaderCircle,
  MessageSquareText,
  MessagesSquare,
  ShieldAlert,
  TriangleAlert,
} from "lucide-react";

import { DURATION, EASE_OUT, enterTransition, exitTransition, layoutTransition, staggerDelay } from "@/lib/motion";
import { cn } from "@/lib/utils";
import { useClaimSimpleCase } from "@/queries/useSimpleNurseQueries";
import { useAuthStore } from "@/store/useAuthStore";
import type { SimpleNurseQueueItemDTO } from "@/types/simple-nurse";
import { esiTheme } from "@/components/clinical/nurse-simple/esi-theme";
import { waitingMinutes } from "@/components/clinical/nurse-simple/wait-time";

import {
  type QueueView,
  esiInk,
  formatDateTime,
  initialsOf,
  isCriticalCase,
  waitLabel,
  waitTone,
} from "./queue-model";

const MIN_PARK_REASON_LENGTH = 10;

/**
 * Một hàng của bảng điều phối: AI đề xuất gì, ai, chờ bao lâu, và đúng một
 * hành động chính. Mỗi hàng có một dải màu ESI ở mép trái để đọc được mức ưu
 * tiên từ xa; màu luôn đi kèm chữ ("ESI 2", "Cấp cứu"), không bao giờ là kênh
 * thông tin duy nhất.
 *
 * Chuyển động:
 * - Lần đầu danh sách hiện, các hàng nổi lên lần lượt.
 * - Ca tới sau (lần làm mới kế tiếp) trượt vào đúng chỗ của nó và sáng lên một
 *   nhịp; các hàng khác dời chỗ bằng `layout`.
 * - Ca hạng 1 (hồi sức hoặc "Cần xem ngay") viền đỏ và tỏa ba vòng sáng một lần
 *   khi xuất hiện, rồi đứng yên -- không nhấp nháy mãi.
 * Hàng đã có trên màn hình không diễn hoạt lại khi hàng đợi tự làm mới: lời
 * đánh dấu "vừa tới" được chốt lúc hàng gắn vào DOM, và khóa là `session_id`.
 */

interface RowMotion {
  index: number;
  arrived: boolean;
}

const rowVariants: Variants = {
  hidden: { opacity: 0, y: 8 },
  arrive: { opacity: 0, y: -16, scale: 0.98 },
  visible: ({ index, arrived }: RowMotion) => ({
    opacity: 1,
    y: 0,
    scale: 1,
    transition: arrived
      ? { duration: DURATION.gentle, ease: EASE_OUT }
      : { ...enterTransition, delay: staggerDelay(index) },
  }),
  exit: { opacity: 0, scale: 0.98, transition: exitTransition },
};

const pressable = { scale: 0.97 };
const pressTransition = { duration: DURATION.press };

const focusRing =
  "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand focus-visible:ring-offset-2 focus-visible:ring-offset-card";

function EsiBadge({ item }: { item: SimpleNurseQueueItemDTO }) {
  const esi = item.ai_proposed_esi;

  if (esi === null && item.attention_required) {
    // Cờ không phải mức ESI: ô này không bao giờ ghi "ESI 1" cho ca chưa có đề xuất.
    return (
      <span className="flex size-14 shrink-0 items-center justify-center rounded-2xl bg-rose-700 text-white dark:bg-rose-600">
        <TriangleAlert className="size-6" strokeWidth={2.4} aria-hidden="true" />
        <span className="sr-only">Chưa có mức ESI</span>
      </span>
    );
  }

  if (esi === null) {
    return (
      <span className="flex size-14 shrink-0 flex-col items-center justify-center rounded-2xl border-2 border-dashed border-slate-300 bg-muted leading-none text-muted-foreground dark:border-slate-600">
        <span className="text-xs font-bold" aria-hidden="true">
          ESI
        </span>
        <span className="text-xl font-extrabold" aria-hidden="true">
          ?
        </span>
        <span className="sr-only">Chưa có mức ESI</span>
      </span>
    );
  }

  return (
    <span
      className={cn(
        "flex size-14 shrink-0 flex-col items-center justify-center rounded-2xl border leading-none",
        esiTheme(esi).chip,
      )}
    >
      <span className="text-xs font-bold" aria-hidden="true">
        ESI
      </span>
      <span className="text-2xl font-extrabold tabular-nums" aria-hidden="true">
        {esi}
      </span>
      <span className="sr-only">ESI {esi}</span>
    </span>
  );
}

function StatusLine({ item }: { item: SimpleNurseQueueItemDTO }) {
  if (item.attention_required) {
    return (
      <p className="flex flex-wrap items-center gap-2 text-sm font-semibold">
        <span className="inline-flex items-center gap-2 rounded-full bg-rose-700 px-2 font-bold leading-6 text-white">
          <ShieldAlert className="size-4" aria-hidden="true" />
          Cần xem ngay
        </span>
        {item.attention_reason && <span className="text-rose-800 dark:text-rose-300">{item.attention_reason}</span>}
      </p>
    );
  }

  if (item.ai_proposed_esi !== null) {
    return (
      <p className={cn("text-sm font-semibold", esiInk(item.ai_proposed_esi))}>
        {esiTheme(item.ai_proposed_esi).label} · AI đề xuất
      </p>
    );
  }

  return (
    <p className="text-sm font-semibold text-muted-foreground">
      {item.is_insufficient ? "Chưa đủ dữ liệu để đề xuất" : "Chưa có đề xuất ESI"}
    </p>
  );
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
  const fieldId = useId();
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const [reason, setReason] = useState("");
  const length = reason.trim().length;
  const tooShort = length < MIN_PARK_REASON_LENGTH;

  // Mở biểu mẫu là để gõ lý do ngay -- đưa con trỏ vào ô nhập.
  useEffect(() => {
    textareaRef.current?.focus();
  }, []);

  return (
    <motion.div
      initial={{ opacity: 0, y: -8 }}
      animate={{ opacity: 1, y: 0, transition: { duration: DURATION.base, ease: EASE_OUT } }}
      exit={{ opacity: 0, transition: exitTransition }}
      className="relative mx-4 mb-4 rounded-xl bg-amber-50 p-4 dark:bg-amber-500/10 xl:ml-26"
    >
      <label htmlFor={fieldId} className="block text-sm font-bold text-amber-900 dark:text-amber-200">
        Lý do tạm gác lại (tối thiểu {MIN_PARK_REASON_LENGTH} ký tự)
      </label>
      <textarea
        ref={textareaRef}
        id={fieldId}
        value={reason}
        onChange={(event) => setReason(event.target.value)}
        onKeyDown={(event) => {
          if (event.key === "Escape") onCancel();
        }}
        rows={2}
        aria-describedby={`${fieldId}-count`}
        placeholder="Vd: dữ liệu không rõ ràng, cần liên hệ thêm bệnh nhân trước khi xử lý..."
        className="mt-2 w-full rounded-xl border border-amber-300 bg-card px-4 py-2 text-sm text-foreground placeholder:text-muted-foreground focus:border-amber-500 focus:outline-none focus:ring-2 focus:ring-amber-500/40 dark:border-amber-500/40"
      />
      <div className="mt-2 flex flex-wrap items-center gap-2">
        <motion.button
          type="button"
          whileTap={pressable}
          transition={pressTransition}
          onClick={() => onConfirm(reason.trim())}
          disabled={tooShort || isPending}
          className="flex min-h-11 items-center gap-2 rounded-xl bg-amber-700 px-4 text-sm font-bold text-white transition-colors hover:bg-amber-800 disabled:cursor-not-allowed disabled:opacity-50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-amber-600 focus-visible:ring-offset-2"
        >
          {isPending ? (
            <LoaderCircle className="size-4 animate-spin motion-reduce:animate-none" aria-hidden="true" />
          ) : (
            <Archive className="size-4" aria-hidden="true" />
          )}
          Xác nhận tạm gác
        </motion.button>
        <motion.button
          type="button"
          whileTap={pressable}
          transition={pressTransition}
          onClick={onCancel}
          className={cn(
            "flex min-h-11 items-center rounded-xl border border-border bg-card px-4 text-sm font-semibold text-foreground transition-colors hover:bg-muted",
            focusRing,
          )}
        >
          Hủy
        </motion.button>
        <span
          id={`${fieldId}-count`}
          className={cn(
            "ml-auto text-sm tabular-nums",
            tooShort ? "text-amber-800 dark:text-amber-300" : "text-emerald-700 dark:text-emerald-300",
          )}
        >
          {length}/{MIN_PARK_REASON_LENGTH} ký tự
        </span>
      </div>
    </motion.div>
  );
}

interface QueueRowProps {
  item: SimpleNurseQueueItemDTO;
  view: QueueView;
  index: number;
  /** Ca này vừa xuất hiện trong lần làm mới gần nhất (không phải lần tải đầu). */
  arrived: boolean;
}

export function QueueRow({ item, view, index, arrived }: QueueRowProps) {
  const router = useRouter();
  const currentUser = useAuthStore((state) => state.user);
  const claim = useClaimSimpleCase(item.session_id);
  const [isParking, setIsParking] = useState(false);
  // Chốt lúc gắn vào DOM: lần làm mới sau không biến hàng cũ thành "vừa tới".
  const [arrivedOnMount] = useState(arrived);
  const nameId = useId();

  const isDecided = view.bucket === "DECIDED";
  const mine = Boolean(currentUser?.id) && item.assigned_nurse_id === currentUser?.id;
  const ownedByOther = Boolean(item.assigned_nurse_id) && !mine;
  // Viền đỏ và vòng sáng chỉ dành cho ca còn mở: một ca đã chốt không còn việc gì phải làm ngay.
  const critical = !isDecided && isCriticalCase(item);
  const minutes = waitingMinutes(item.waiting_since);
  const pendingAction = claim.isPending ? claim.variables?.action : undefined;
  const message = item.initial_message.trim();
  const patientName = item.patient_name?.trim();

  const openCase = () => {
    if (mine || isDecided) {
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

  // Nút nhận ca nổi bật theo đúng mức cần làm ngay: đỏ cho hạng 1, màu thương
  // hiệu cho ESI 2, viền mảnh cho phần còn lại.
  const claimTone = critical
    ? "bg-rose-700 text-white hover:bg-rose-800 focus-visible:ring-rose-600"
    : item.ai_proposed_esi === 2
        ? "bg-brand text-brand-foreground hover:bg-brand-strong focus-visible:ring-brand"
        : "border border-border bg-card text-foreground hover:bg-muted focus-visible:ring-brand";

  return (
    <motion.li
      layout="position"
      variants={rowVariants}
      custom={{ index, arrived: arrivedOnMount } satisfies RowMotion}
      initial={arrivedOnMount ? "arrive" : "hidden"}
      animate="visible"
      exit="exit"
      transition={{ layout: layoutTransition }}
      data-arrived={arrivedOnMount ? "true" : undefined}
      data-critical={critical ? "true" : undefined}
    >
      <article
        aria-labelledby={nameId}
        className={cn(
          "group/row relative overflow-hidden rounded-2xl bg-card",
          "transition-[transform,box-shadow,border-color] duration-200 ease-out",
          "hover:-translate-y-0.5 hover:shadow-[0_12px_24px_-16px_rgb(15_23_42/0.45)]",
          "motion-reduce:transition-none motion-reduce:hover:translate-y-0",
          "focus-within:shadow-[0_12px_24px_-16px_rgb(15_23_42/0.45)]",
          critical
            ? "ring-pulse border-2 border-rose-600 dark:border-rose-500"
            : "border border-border hover:border-slate-300 dark:hover:border-slate-600",
        )}
      >
        {/* Dải mức độ ở mép trái -- đọc được mức ưu tiên từ xa. */}
        <span
          aria-hidden="true"
          className={cn(
            "absolute inset-y-0 left-0 w-2",
            critical && item.ai_proposed_esi === null ? "bg-rose-600" : esiTheme(item.ai_proposed_esi).rail,
            item.ai_proposed_esi === null && !critical && "dark:bg-slate-600",
          )}
        />

        {/* Ca vừa tới sáng lên một nhịp rồi tắt dần, để mắt biết hàng nào mới chen vào. */}
        {arrivedOnMount && (
          <motion.span
            aria-hidden="true"
            className={cn(
              "pointer-events-none absolute inset-0",
              critical ? "bg-rose-100 dark:bg-rose-500/20" : "bg-brand-edge/50",
            )}
            initial={{ opacity: 1 }}
            animate={{ opacity: 0, transition: { duration: 1.2, delay: DURATION.base, ease: EASE_OUT } }}
          />
        )}

        <div
          className={cn(
            "relative grid grid-cols-[3.5rem_minmax(0,1fr)] gap-x-4 gap-y-4 py-4 pl-6 pr-4",
            "md:grid-cols-[3.5rem_minmax(0,1fr)_auto]",
            "xl:grid-cols-[3.5rem_minmax(0,1fr)_10rem_11rem_auto] xl:items-center",
          )}
        >
          <EsiBadge item={item} />

          {/* AI đề xuất gì và người bệnh kể gì. */}
          <div className="min-w-0">
            <StatusLine item={item} />
            <p
              className="mt-2 line-clamp-2 text-base font-semibold leading-6 text-foreground xl:line-clamp-1"
              title={message || undefined}
            >
              {message ? `“${message}”` : <span className="font-normal text-muted-foreground">Chưa có mô tả triệu chứng</span>}
            </p>

            {item.is_insufficient && (item.ai_proposed_esi !== null || item.attention_required) && (
              <p className="mt-2 inline-flex items-center gap-2 rounded-full bg-amber-50 px-2 text-sm font-semibold leading-6 text-amber-900 dark:bg-amber-500/10 dark:text-amber-200">
                <CircleAlert className="size-4" aria-hidden="true" />
                Thiếu dữ liệu kết luận
              </p>
            )}

            {view.bucket === "PARKED" && item.parked_reason && (
              <p className="mt-2 border-l-4 border-amber-400 pl-4 text-sm leading-6 text-amber-900 dark:border-amber-500/60 dark:text-amber-200">
                <span className="font-bold">Lý do tạm gác:</span> {item.parked_reason}
                {item.parked_at && (
                  <span className="text-amber-700 dark:text-amber-300"> ({formatDateTime(item.parked_at)})</span>
                )}
              </p>
            )}

            {isDecided && (
              <p className="mt-2 flex flex-wrap items-center gap-2 text-sm leading-6 text-emerald-900 dark:text-emerald-200">
                <CircleCheck className="size-4 shrink-0 text-emerald-600 dark:text-emerald-400" aria-hidden="true" />
                <span className="font-bold">
                  {item.decision_type === "ADJUST_ESI" ? "Đã điều chỉnh" : "Đã xác nhận"}
                  {item.final_esi !== null && (
                    <>
                      : <span className={esiInk(item.final_esi)}>ESI {item.final_esi}</span>
                    </>
                  )}
                </span>
                {item.decision_note && <span className="text-foreground">— {item.decision_note}</span>}
              </p>
            )}
          </div>

          {/* Ai và chờ bao lâu. Dưới xl xếp thành một dòng phụ; từ xl tách thành hai cột. */}
          <div className="col-start-2 flex min-w-0 flex-wrap gap-x-6 gap-y-2 md:row-start-2 xl:contents">
            <div className="min-w-0 xl:col-start-3 xl:row-start-1">
              <p id={nameId} className={cn("truncate text-base font-bold", patientName ? "text-foreground" : "text-muted-foreground")}>
                {patientName || "Chưa rõ danh tính"}
              </p>
              {item.session_status === "ACTIVE" ? (
                <p className="flex items-center gap-2 text-sm font-medium text-sky-800 dark:text-sky-300">
                  <MessagesSquare className="size-4 shrink-0" aria-hidden="true" />
                  Người bệnh vẫn đang trò chuyện
                </p>
              ) : item.patient_email ? (
                <p className="truncate text-sm text-muted-foreground">{item.patient_email}</p>
              ) : null}
              {(item.unread_count > 0 || (!isDecided && (mine || ownedByOther))) && (
                <div className="mt-2 flex flex-wrap gap-2">
                  {item.unread_count > 0 && (
                    <span className="inline-flex items-center gap-2 rounded-full border border-brand-edge bg-brand-soft px-2 text-sm font-bold leading-6 text-brand-ink">
                      <MessageSquareText className="size-4" aria-hidden="true" />
                      <span className="tabular-nums">{item.unread_count}</span> tin mới
                    </span>
                  )}
                  {!isDecided && mine && (
                    <span className="inline-flex items-center rounded-full bg-brand-soft px-2 text-sm font-bold leading-6 text-brand-ink">
                      Bạn phụ trách
                    </span>
                  )}
                  {!isDecided && ownedByOther && (
                    <span className="inline-flex items-center rounded-full bg-muted px-2 text-sm font-semibold leading-6 text-muted-foreground">
                      Người khác phụ trách
                    </span>
                  )}
                </div>
              )}
            </div>

            <div className="xl:col-start-4 xl:row-start-1">
              {isDecided ? (
                <>
                  <p className="text-sm text-muted-foreground">Chốt lúc</p>
                  <p className="text-base font-bold tabular-nums text-foreground">
                    {formatDateTime(item.decided_at) || "Chưa ghi nhận"}
                  </p>
                </>
              ) : (
                <>
                  <p
                    className={cn(
                      "flex items-center gap-2 text-base font-bold tabular-nums",
                      critical ? "text-rose-700 dark:text-rose-300" : waitTone(minutes),
                    )}
                  >
                    <Clock3 className="size-4 shrink-0" aria-hidden="true" />
                    {waitLabel(minutes)}
                  </p>
                  <p className="text-sm text-muted-foreground">
                    <span className="tabular-nums">{item.turn_count}</span> lượt hội thoại
                  </p>
                </>
              )}
            </div>
          </div>

          {/* Đúng một hành động chính cho mỗi ca. */}
          <div className="col-span-2 flex flex-wrap items-center justify-end gap-2 md:col-span-1 md:col-start-3 md:row-span-2 md:row-start-1 md:self-center xl:col-start-5 xl:row-span-1">
            {isDecided ? (
              <motion.button
                type="button"
                whileTap={pressable}
                transition={pressTransition}
                onClick={openCase}
                className={cn(
                  "flex min-h-11 items-center gap-2 rounded-xl border border-border bg-card px-4 text-sm font-semibold text-foreground transition-colors hover:bg-muted",
                  focusRing,
                )}
              >
                Xem hồ sơ ca
                <ArrowRight className="size-4" aria-hidden="true" />
              </motion.button>
            ) : view.bucket === "PARKED" ? (
              <motion.button
                type="button"
                whileTap={pressable}
                transition={pressTransition}
                onClick={handleRestore}
                disabled={claim.isPending}
                className={cn(
                  "flex min-h-11 items-center gap-2 rounded-xl border border-brand-edge bg-brand-soft px-4 text-sm font-bold text-brand-ink transition-colors hover:bg-brand-edge/40 disabled:opacity-60",
                  focusRing,
                )}
              >
                {pendingAction === "RESTORE" ? (
                  <LoaderCircle className="size-4 animate-spin motion-reduce:animate-none" aria-hidden="true" />
                ) : (
                  <ArchiveRestore className="size-4" aria-hidden="true" />
                )}
                Đẩy lại hàng đợi
              </motion.button>
            ) : ownedByOther ? (
              <span className="text-sm font-medium text-muted-foreground">Y tá khác phụ trách</span>
            ) : (
              <>
                <motion.button
                  type="button"
                  whileTap={pressable}
                  transition={pressTransition}
                  onClick={openCase}
                  disabled={claim.isPending}
                  className={cn(
                    "flex min-h-11 items-center gap-2 rounded-xl px-4 text-sm font-bold shadow-xs transition-colors disabled:opacity-60",
                    "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-offset-2 focus-visible:ring-offset-card",
                    mine
                      ? "border border-brand-edge bg-brand-soft text-brand-ink hover:bg-brand-edge/40 focus-visible:ring-brand"
                      : claimTone,
                  )}
                >
                  {pendingAction === "CLAIM" ? (
                    <LoaderCircle className="size-4 animate-spin motion-reduce:animate-none" aria-hidden="true" />
                  ) : mine ? (
                    <span
                      aria-hidden="true"
                      className="flex size-6 items-center justify-center rounded-full bg-brand text-xs font-bold text-brand-foreground"
                    >
                      {initialsOf(currentUser?.name)}
                    </span>
                  ) : null}
                  {mine ? "Mở ca" : pendingAction === "CLAIM" ? "Đang nhận..." : "Nhận ca"}
                </motion.button>
                <motion.button
                  type="button"
                  whileTap={pressable}
                  transition={pressTransition}
                  onClick={() => setIsParking((value) => !value)}
                  disabled={claim.isPending}
                  aria-expanded={isParking}
                  title="Tạm gác lại"
                  aria-label="Tạm gác lại ca này"
                  className={cn(
                    "flex size-11 items-center justify-center rounded-xl border border-border bg-card text-muted-foreground transition-colors hover:bg-muted hover:text-foreground disabled:opacity-60",
                    isParking && "border-amber-300 bg-amber-50 text-amber-800 dark:border-amber-500/40 dark:bg-amber-500/10 dark:text-amber-200",
                    focusRing,
                  )}
                >
                  <Archive className="size-4" aria-hidden="true" />
                </motion.button>
              </>
            )}
          </div>
        </div>

        <AnimatePresence initial={false}>
          {isParking && (
            <ParkReasonForm
              key="park-form"
              onCancel={() => setIsParking(false)}
              onConfirm={handlePark}
              isPending={pendingAction === "PARK"}
            />
          )}
        </AnimatePresence>

        {/* Thao tác hỏng (ví dụ người khác vừa nhận ca) phải nói ra, không im lặng. */}
        {claim.isError && (
          <p
            role="alert"
            className="relative mx-4 mb-4 flex items-start gap-2 rounded-xl bg-rose-50 px-4 py-2 text-sm font-semibold leading-6 text-rose-900 dark:bg-rose-500/10 dark:text-rose-200 xl:ml-26"
          >
            <span className="flex h-6 shrink-0 items-center">
              <CircleAlert className="size-4" aria-hidden="true" />
            </span>
            {claim.error instanceof Error ? claim.error.message : "Không thực hiện được thao tác này."}
          </p>
        )}
      </article>
    </motion.li>
  );
}
