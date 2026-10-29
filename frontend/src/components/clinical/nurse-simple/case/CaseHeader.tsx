"use client";

import { useEffect, useId, useRef, useState } from "react";
import Link from "next/link";
import { zodResolver } from "@hookform/resolvers/zod";
import { AnimatePresence, motion } from "framer-motion";
import {
  Archive,
  ArchiveRestore,
  ArrowDown,
  CheckCircle2,
  ChevronLeft,
  CircleDashed,
  Loader2,
  PauseCircle,
  RefreshCw,
  Undo2,
  UserRoundCheck,
  UsersRound,
} from "lucide-react";
import { useForm, useWatch } from "react-hook-form";

import {
  QUEUE_HREF,
  formatClock,
  patientContextParts,
  patientDisplayName,
} from "@/components/clinical/nurse-simple/case/case-format";
import { riseIn } from "@/components/clinical/nurse-simple/case/case-motion";
import {
  MIN_PARK_REASON_LENGTH,
  parkReasonSchema,
  type ParkReasonValues,
} from "@/components/clinical/nurse-simple/case/decision-schema";
import type { ClaimAction, ClaimActionOptions, Ownership } from "@/components/clinical/nurse-simple/case/ownership";
import { esiTheme } from "@/components/clinical/nurse-simple/esi-theme";
import { DURATION, EASE_OUT, dropVariants } from "@/lib/motion";
import { cn } from "@/lib/utils";
import type { SimpleNurseCaseDetailDTO } from "@/types/simple-nurse";

/**
 * Đầu hồ sơ ca: ai (tên, tuổi, ai khai báo giúp), cái gì (lời kể ban đầu),
 * ai đang giữ ca, và các việc với chính ca đó -- nhận, tạm gác, trả lại hàng
 * đợi, đưa ca đang gác trở lại. Mọi thao tác gửi kèm `case_version` hiện tại;
 * backend từ chối nếu ca vừa đổi ở nơi khác.
 */

const outlineButton =
  "inline-flex min-h-11 items-center justify-center gap-2 rounded-xl border border-border bg-card px-4 text-sm font-bold text-foreground transition-colors hover:bg-muted focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand focus-visible:ring-offset-2 focus-visible:ring-offset-card disabled:cursor-not-allowed disabled:opacity-60";

const primaryButton =
  "inline-flex min-h-11 items-center justify-center gap-2 rounded-xl bg-brand px-4 text-sm font-bold text-brand-foreground shadow-sm transition-colors hover:bg-brand-strong focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand focus-visible:ring-offset-2 focus-visible:ring-offset-card disabled:cursor-not-allowed disabled:opacity-60";

function OwnershipPill({ ownership, finalEsi }: { ownership: Ownership; finalEsi: number | null }) {
  const pill = (() => {
    switch (ownership) {
      case "closed": {
        const theme = esiTheme(finalEsi);
        return {
          icon: CheckCircle2,
          label: finalEsi ? `Đã chốt ESI ${finalEsi} · ${theme.label}` : "Ca đã đóng",
          className: theme.chip,
        };
      }
      case "mine":
        return { icon: null, label: "Bạn đang xử lý ca này", className: "border-brand-edge bg-brand-soft text-brand-ink" };
      case "parked-mine":
        return {
          icon: PauseCircle,
          label: "Bạn đã tạm gác ca này",
          className:
            "border-amber-200 bg-amber-50 text-amber-900 dark:border-amber-800 dark:bg-amber-950/40 dark:text-amber-100",
        };
      case "parked-other":
        return {
          icon: PauseCircle,
          label: "Ca đang được tạm gác",
          className:
            "border-amber-200 bg-amber-50 text-amber-900 dark:border-amber-800 dark:bg-amber-950/40 dark:text-amber-100",
        };
      case "other":
        return { icon: UsersRound, label: "Y tá khác đang phụ trách", className: "border-border bg-muted text-foreground" };
      case "open":
      default:
        return { icon: CircleDashed, label: "Chưa ai nhận ca", className: "border-border bg-muted text-foreground" };
    }
  })();
  const Icon = pill.icon;

  return (
    <AnimatePresence mode="wait" initial={false}>
      <motion.span
        key={`${ownership}-${finalEsi ?? "none"}`}
        initial={{ opacity: 0, scale: 0.96 }}
        animate={{ opacity: 1, scale: 1 }}
        exit={{ opacity: 0, scale: 0.96 }}
        transition={{ duration: DURATION.quick, ease: EASE_OUT }}
        className={cn("inline-flex min-h-11 items-center gap-2 rounded-full border px-4 text-sm font-bold", pill.className)}
      >
        {Icon ? (
          <Icon className="size-4 shrink-0" aria-hidden="true" />
        ) : (
          <span className="size-2 shrink-0 rounded-full bg-brand" aria-hidden="true" />
        )}
        {pill.label}
      </motion.span>
    </AnimatePresence>
  );
}

function ParkReasonForm({
  pending,
  onCancel,
  onConfirm,
}: {
  pending: boolean;
  onCancel: () => void;
  onConfirm: (reason: string) => void;
}) {
  const ids = useId();
  const fieldId = `${ids}-reason`;
  const hintId = `${ids}-hint`;
  const errorId = `${ids}-error`;
  const {
    control,
    register,
    handleSubmit,
    setFocus,
    formState: { errors },
  } = useForm<ParkReasonValues>({
    resolver: zodResolver(parkReasonSchema),
    defaultValues: { reason: "" },
  });
  const typed = (useWatch({ control, name: "reason" }) ?? "").trim().length;

  useEffect(() => {
    setFocus("reason");
  }, [setFocus]);

  return (
    <motion.form
      variants={dropVariants}
      initial="hidden"
      animate="visible"
      exit="exit"
      noValidate
      aria-label="Tạm gác ca"
      onSubmit={handleSubmit((values) => onConfirm(values.reason))}
      onKeyDown={(event) => {
        if (event.key === "Escape") {
          event.preventDefault();
          onCancel();
        }
      }}
      className="mt-4 flex flex-col gap-2 rounded-xl bg-amber-50 p-4 text-amber-950 dark:bg-amber-950/40 dark:text-amber-100"
    >
      <label htmlFor={fieldId} className="text-sm font-bold">
        Lý do tạm gác lại (tối thiểu {MIN_PARK_REASON_LENGTH} ký tự)
      </label>
      <p id={hintId} className="text-sm leading-6 opacity-90">
        Ghi rõ còn thiếu gì, để người xử lý tiếp theo biết cần bổ sung trước khi đưa ca trở lại hàng đợi. Đã nhập{" "}
        {typed}/{MIN_PARK_REASON_LENGTH} ký tự.
      </p>
      <textarea
        id={fieldId}
        rows={2}
        {...register("reason")}
        aria-invalid={Boolean(errors.reason)}
        aria-describedby={errors.reason ? `${hintId} ${errorId}` : hintId}
        placeholder="Vd: dữ liệu không rõ ràng, cần liên hệ thêm bệnh nhân trước khi xử lý..."
        className="w-full resize-none rounded-xl border border-amber-300 bg-card px-4 py-2 text-sm leading-6 text-foreground placeholder:text-muted-foreground focus-visible:border-amber-500 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-amber-500/40 dark:border-amber-800"
      />
      {errors.reason?.message && (
        <p id={errorId} role="alert" className="text-sm font-semibold text-rose-700 dark:text-rose-400">
          {errors.reason.message}
        </p>
      )}
      <div className="flex flex-wrap items-center gap-2">
        <motion.button
          type="submit"
          whileTap={{ scale: 0.97 }}
          disabled={pending}
          className="inline-flex min-h-11 items-center gap-2 rounded-xl bg-amber-700 px-4 text-sm font-bold text-white transition-colors hover:bg-amber-800 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-amber-600 focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-60"
        >
          {pending ? (
            <Loader2 className="size-4 animate-spin motion-reduce:animate-none" aria-hidden="true" />
          ) : (
            <Archive className="size-4" aria-hidden="true" />
          )}
          Xác nhận tạm gác
        </motion.button>
        <button type="button" onClick={onCancel} className={outlineButton}>
          Hủy
        </button>
      </div>
    </motion.form>
  );
}

export function CaseHeader({
  data,
  ownership,
  canDecide,
  actionsLocked = false,
  pendingAction,
  onClaimAction,
  refreshFailed,
}: {
  data: SimpleNurseCaseDetailDTO;
  ownership: Ownership;
  canDecide: boolean;
  /** Vừa chốt xong: ca đã đóng ở backend, chỉ chờ dữ liệu mới về -- không còn việc gì để làm. */
  actionsLocked?: boolean;
  pendingAction: ClaimAction | null;
  onClaimAction: (action: ClaimAction, options?: ClaimActionOptions) => void;
  /** Lần làm mới gần nhất thất bại; dữ liệu trên màn là bản đã tải trước đó. */
  refreshFailed: boolean;
}) {
  const [parking, setParking] = useState(false);
  const parkButtonRef = useRef<HTMLButtonElement>(null);
  const statusRef = useRef<HTMLSpanElement>(null);
  const returnFocusToPark = useRef(false);
  const focusStatusOnChange = useRef(false);

  useEffect(() => {
    if (!parking && returnFocusToPark.current) {
      returnFocusToPark.current = false;
      parkButtonRef.current?.focus();
    }
  }, [parking]);

  // Nhận ca, tạm gác hay đưa lại đều làm biến mất chính nút vừa bấm. Đưa tiêu
  // điểm về ô trạng thái (một vùng thông báo) để người dùng bàn phím không bị
  // rơi về đầu trang, và trình đọc màn hình đọc lên trạng thái mới.
  useEffect(() => {
    if (focusStatusOnChange.current) {
      focusStatusOnChange.current = false;
      statusRef.current?.focus();
    }
  }, [ownership]);

  const runAndFocusStatus = (action: ClaimAction, options: ClaimActionOptions = {}) =>
    onClaimAction(action, {
      ...options,
      onSuccess: () => {
        focusStatusOnChange.current = true;
        options.onSuccess?.();
      },
    });

  const busy = pendingAction !== null;
  const name = patientDisplayName(data.patient);
  const context = patientContextParts(data.patient);
  const startedAt = formatClock(data.messages[0]?.created_at);
  const meta = [
    startedAt ? `Bắt đầu ${startedAt}` : null,
    `${data.messages.length} tin nhắn với trợ lý`,
    data.session_status === "ACTIVE" ? "Người bệnh vẫn đang trò chuyện" : null,
  ].filter((part): part is string => part !== null);
  const aiTheme = esiTheme(data.ai_proposed_esi);
  const complaint = data.initial_message.trim();

  const cancelParking = () => {
    returnFocusToPark.current = true;
    setParking(false);
  };

  const canPark = !actionsLocked && (ownership === "open" || ownership === "mine");
  const canRelease = !actionsLocked && ownership === "mine";
  const canRestore = !actionsLocked && (ownership === "parked-mine" || ownership === "parked-other");
  const canClaim = !actionsLocked && ownership === "open";

  return (
    <motion.header {...riseIn(0)} className="rounded-2xl border border-border bg-card p-4 shadow-xs sm:p-6">
      <div className="flex flex-col gap-4 lg:flex-row lg:items-start">
        <div className="flex min-w-0 flex-1 items-start gap-2 sm:gap-4">
          <Link
            href={QUEUE_HREF}
            className="inline-flex min-h-11 shrink-0 items-center gap-2 rounded-xl px-2 text-sm font-bold text-muted-foreground transition-colors hover:bg-muted hover:text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand"
          >
            <ChevronLeft className="size-5" aria-hidden="true" />
            Hàng đợi
          </Link>
          <span className="hidden h-11 w-px shrink-0 bg-border sm:block" aria-hidden="true" />

          <div className="min-w-0 flex-1">
            <h1 className="text-xl font-extrabold leading-tight tracking-tight text-foreground sm:text-2xl">
              {name}
              {context.length > 0 && (
                <span className="text-base font-semibold tracking-normal text-muted-foreground">
                  {" · "}
                  {context.join(" · ")}
                </span>
              )}
            </h1>
            <p className="mt-2 text-sm text-muted-foreground">{meta.join(" · ")}</p>
            {complaint && (
              <p className="mt-2 line-clamp-2 text-base leading-6 text-foreground">“{complaint}”</p>
            )}
            {/* Màn hẹp thì bàn quyết định nằm cuối trang: đặt đề xuất của AI
                ngay đầu hồ sơ để không phải cuộn xuống mới biết mức độ. */}
            <p
              className={cn(
                "mt-4 inline-flex min-h-8 items-center rounded-lg border px-2 text-sm font-bold xl:hidden",
                aiTheme.chip,
              )}
            >
              {data.ai_proposed_esi
                ? `AI đề xuất: ESI ${data.ai_proposed_esi} · ${aiTheme.label}`
                : "AI: chưa đủ dữ liệu kết luận"}
            </p>
          </div>
        </div>

        <div className="flex flex-wrap items-center gap-2 lg:max-w-md lg:justify-end">
          <span
            ref={statusRef}
            tabIndex={-1}
            role="status"
            aria-live="polite"
            className="inline-flex rounded-full focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand"
          >
            <OwnershipPill ownership={ownership} finalEsi={data.final_esi} />
          </span>

          {canClaim && (
            <motion.button
              type="button"
              whileTap={{ scale: 0.97 }}
              onClick={() => runAndFocusStatus("CLAIM")}
              disabled={busy}
              className={primaryButton}
            >
              {pendingAction === "CLAIM" ? (
                <Loader2 className="size-4 animate-spin motion-reduce:animate-none" aria-hidden="true" />
              ) : (
                <UserRoundCheck className="size-4" aria-hidden="true" />
              )}
              {pendingAction === "CLAIM" ? "Đang nhận ca..." : "Nhận ca này"}
            </motion.button>
          )}

          {canPark && (
            <motion.button
              ref={parkButtonRef}
              type="button"
              whileTap={{ scale: 0.97 }}
              onClick={() => (parking ? cancelParking() : setParking(true))}
              disabled={busy}
              aria-expanded={parking}
              className={outlineButton}
            >
              <Archive className="size-4" aria-hidden="true" />
              Tạm gác
            </motion.button>
          )}

          {canRelease && (
            <motion.button
              type="button"
              whileTap={{ scale: 0.97 }}
              onClick={() => onClaimAction("RELEASE")}
              disabled={busy}
              className={outlineButton}
            >
              {pendingAction === "RELEASE" ? (
                <Loader2 className="size-4 animate-spin motion-reduce:animate-none" aria-hidden="true" />
              ) : (
                <Undo2 className="size-4" aria-hidden="true" />
              )}
              {pendingAction === "RELEASE" ? "Đang trả ca..." : "Trả lại hàng đợi"}
            </motion.button>
          )}

          {canRestore && (
            <motion.button
              type="button"
              whileTap={{ scale: 0.97 }}
              onClick={() => runAndFocusStatus("RESTORE")}
              disabled={busy}
              className={outlineButton}
            >
              {pendingAction === "RESTORE" ? (
                <Loader2 className="size-4 animate-spin motion-reduce:animate-none" aria-hidden="true" />
              ) : (
                <ArchiveRestore className="size-4" aria-hidden="true" />
              )}
              {pendingAction === "RESTORE" ? "Đang đẩy lại..." : "Đẩy lại hàng đợi"}
            </motion.button>
          )}

          {canDecide && (
            <a href="#decision-desk" className={cn(outlineButton, "xl:hidden")}>
              <ArrowDown className="size-4" aria-hidden="true" />
              Tới bàn quyết định
            </a>
          )}
        </div>
      </div>

      <AnimatePresence initial={false}>
        {parking && canPark && (
          <ParkReasonForm
            key="park"
            pending={pendingAction === "PARK"}
            onCancel={cancelParking}
            onConfirm={(reason) => runAndFocusStatus("PARK", { reason, onSuccess: () => setParking(false) })}
          />
        )}
      </AnimatePresence>

      {ownership === "other" && (
        <p className="mt-4 rounded-xl bg-amber-50 px-4 py-2 text-sm font-semibold leading-6 text-amber-950 dark:bg-amber-950/40 dark:text-amber-100">
          Ca này đang được một y tá khác phụ trách — bạn xem được hồ sơ nhưng không ra quyết định.
        </p>
      )}
      {ownership === "parked-other" && (
        <p className="mt-4 rounded-xl bg-amber-50 px-4 py-2 text-sm font-semibold leading-6 text-amber-950 dark:bg-amber-950/40 dark:text-amber-100">
          Ca đang được một y tá khác tạm gác. Ai cũng có thể đẩy ca lại hàng đợi khi đã đủ thông tin.
        </p>
      )}
      {refreshFailed && (
        <p
          role="status"
          className="mt-4 flex items-center gap-2 text-sm font-semibold text-amber-800 dark:text-amber-300"
        >
          <RefreshCw className="size-4 shrink-0" aria-hidden="true" />
          Không tải được dữ liệu mới nhất của ca. Màn hình đang hiện bản trước đó và sẽ tự thử lại.
        </p>
      )}
    </motion.header>
  );
}
