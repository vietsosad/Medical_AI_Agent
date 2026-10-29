"use client";

import { useEffect, useRef } from "react";
import { AnimatePresence, motion } from "framer-motion";
import { ArrowLeft, CheckCircle2, CircleDashed, Lock, PauseCircle } from "lucide-react";

import { riseIn } from "@/components/clinical/nurse-simple/case/case-motion";
import { reasonLabel, type EsiLevel } from "@/components/clinical/nurse-simple/case/decision-schema";
import type { Ownership } from "@/components/clinical/nurse-simple/case/ownership";
import { esiTheme } from "@/components/clinical/nurse-simple/esi-theme";
import { SimpleDecisionForm, type DecidedSummary } from "@/components/clinical/nurse-simple/SimpleDecisionForm";
import { DURATION, EASE_OUT, enterTransition, exitTransition } from "@/lib/motion";
import { cn } from "@/lib/utils";
import type { SimpleNurseCaseDetailDTO } from "@/types/simple-nurse";

/**
 * Bàn "Quyết định của điều dưỡng", ghim bên phải từ màn rộng trở lên để điều
 * dưỡng đọc xong là chốt được ngay, không phải cuộn ngược lên.
 *
 * Bốn trạng thái, chuyển qua lại bằng một nhịp mờ dần ngắn:
 * - form: ca của bạn và chưa đóng -- chọn mức ESI, lý do, ghi chú.
 * - confirmation: vừa lưu xong -- xác nhận rõ ràng trước khi quay về hàng đợi.
 * - closed: ca đã đóng -- chỉ đọc lại quyết định đã ghi.
 * - locked: ca chưa nhận hoặc người khác đang giữ.
 */

export type DeskView = "form" | "confirmation" | "closed" | "locked";

/** Nhịp mờ đi của trạng thái cũ trước khi trạng thái mới của bàn hiện lên. */
const DESK_EXIT_SECONDS = DURATION.quick * 0.75;

function EsiBadge({ level, className }: { level: number | null; className?: string }) {
  const theme = esiTheme(level);
  return (
    <span
      aria-hidden="true"
      className={cn(
        "flex size-12 shrink-0 flex-col items-center justify-center rounded-xl border leading-none",
        theme.chip,
        className,
      )}
    >
      {level ? (
        <>
          <span className="text-xs font-bold">ESI</span>
          <span className="text-xl font-black leading-tight tabular-nums">{level}</span>
        </>
      ) : (
        <CircleDashed className="size-5" />
      )}
    </span>
  );
}

function AiProposal({ aiEsi }: { aiEsi: EsiLevel | null }) {
  const theme = esiTheme(aiEsi);
  return (
    <div className="flex items-center gap-4 rounded-2xl bg-muted p-4">
      <EsiBadge level={aiEsi} />
      <div className="min-w-0">
        <p className="text-sm font-semibold text-foreground/75">AI đề xuất · chưa phải kết luận</p>
        <p className="text-base font-extrabold text-foreground">
          {aiEsi ? `ESI ${aiEsi} · ${theme.label}` : "Chưa đủ dữ liệu để đề xuất"}
        </p>
      </div>
    </div>
  );
}

function ClosedSummary({ data }: { data: SimpleNurseCaseDetailDTO }) {
  const theme = esiTheme(data.final_esi);
  const reason = reasonLabel(data.decision_reason_code);
  const how =
    data.decision_type === "CONFIRM_ESI"
      ? "Điều dưỡng đã xác nhận đúng mức AI đề xuất."
      : data.decision_type === "ADJUST_ESI"
        ? data.ai_proposed_esi
          ? `Điều dưỡng đã điều chỉnh từ mức AI đề xuất (ESI ${data.ai_proposed_esi}).`
          : "AI chưa đề xuất mức nào; mức này do điều dưỡng chốt."
        : null;

  return (
    <div className="flex flex-col gap-4">
      <div className="flex items-center gap-4">
        <EsiBadge level={data.final_esi} className="size-14" />
        <div className="min-w-0">
          <p className="text-sm font-semibold text-muted-foreground">Mức đã chốt · ca đã đóng</p>
          <p className="text-lg font-extrabold text-foreground">
            {data.final_esi ? `ESI ${data.final_esi} · ${theme.label}` : "Chưa ghi nhận mức ESI"}
          </p>
        </div>
      </div>
      {how && <p className="text-sm leading-6 text-foreground">{how}</p>}
      <dl className="flex flex-col gap-4 border-t border-border pt-4 text-sm leading-6">
        {reason && (
          <div>
            <dt className="font-bold text-muted-foreground">Lý do</dt>
            <dd className="text-foreground">{reason}</dd>
          </div>
        )}
        <div>
          <dt className="font-bold text-muted-foreground">Ghi chú gửi người bệnh</dt>
          <dd className="whitespace-pre-wrap break-words text-foreground">
            {data.decision_note?.trim() || "Điều dưỡng không ghi chú thêm."}
          </dd>
        </div>
      </dl>
    </div>
  );
}

function LockedNotice({ aiEsi, ownership }: { aiEsi: EsiLevel | null; ownership: Ownership }) {
  const text =
    ownership === "other"
      ? "Ca này thuộc về một y tá khác. Bạn vẫn đọc được toàn bộ hồ sơ để phối hợp."
      : ownership === "parked-other"
        ? "Ca đang được một y tá khác tạm gác. Đẩy ca lại hàng đợi rồi nhận ca để ra quyết định."
        : "Nhấn “Nhận ca này” ở đầu trang để mở bàn quyết định.";
  return (
    <div className="flex flex-col gap-4">
      <AiProposal aiEsi={aiEsi} />
      <p className="flex items-start gap-2 text-sm leading-6 text-muted-foreground">
        <span className="flex h-6 shrink-0 items-center" aria-hidden="true">
          <Lock className="size-4" />
        </span>
        {text}
      </p>
    </div>
  );
}

function DecisionConfirmation({
  decided,
  aiEsi,
  holdSeconds,
  onLeaveNow,
}: {
  decided: DecidedSummary;
  aiEsi: EsiLevel | null;
  holdSeconds: number;
  onLeaveNow: () => void;
}) {
  const theme = esiTheme(decided.finalEsi);
  const how =
    decided.decisionType === "CONFIRM_ESI"
      ? "Bạn đã xác nhận đề xuất của AI."
      : aiEsi !== null
        ? "Bạn đã điều chỉnh đề xuất của AI."
        : "Ca chưa có đề xuất của AI, mức này do bạn chốt.";
  const containerRef = useRef<HTMLDivElement>(null);

  // Nút "Xác nhận" vừa biến mất cùng biểu mẫu; đưa tiêu điểm về chính lời xác
  // nhận để người dùng bàn phím và trình đọc màn hình không bị rơi về đầu trang.
  useEffect(() => {
    containerRef.current?.focus();
  }, []);

  return (
    <div ref={containerRef} tabIndex={-1} role="status" className="flex flex-col gap-4 focus:outline-none">
      <p className="flex items-center gap-2 text-base font-bold text-emerald-800 dark:text-emerald-300">
        <CheckCircle2 className="size-5 shrink-0" aria-hidden="true" />
        Đã lưu quyết định, ca đã đóng
      </p>
      <div className="flex items-center gap-4">
        {/* Thẻ lên trước, mức ESI bật vào sau -- giống thẻ kết quả bên người bệnh. */}
        <motion.span
          initial={{ opacity: 0, scale: 0.6 }}
          animate={{ opacity: 1, scale: 1 }}
          transition={{ duration: DURATION.base, ease: EASE_OUT, delay: 0.15 }}
        >
          <EsiBadge level={decided.finalEsi} className="size-16" />
        </motion.span>
        <div className="min-w-0">
          <p className="text-lg font-extrabold text-foreground">
            ESI {decided.finalEsi} · {theme.label}
          </p>
          <p className="text-sm leading-6 text-muted-foreground">
            {how} Người bệnh sẽ thấy mức này trong phiên của họ.
          </p>
        </div>
      </div>
      <div className="h-2 overflow-hidden rounded-full bg-muted" aria-hidden="true">
        <motion.span
          className="block h-full origin-left rounded-full bg-emerald-500"
          initial={{ scaleX: 0 }}
          animate={{ scaleX: 1 }}
          transition={{ duration: holdSeconds, ease: "linear" }}
        />
      </div>
      <div className="flex flex-wrap items-center justify-between gap-2">
        <p className="text-sm text-muted-foreground">Đang quay về hàng đợi…</p>
        <motion.button
          type="button"
          whileTap={{ scale: 0.97 }}
          onClick={onLeaveNow}
          className="inline-flex min-h-11 items-center gap-2 rounded-xl border border-border bg-card px-4 text-sm font-bold text-foreground transition-colors hover:bg-muted focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand focus-visible:ring-offset-2 focus-visible:ring-offset-card"
        >
          <ArrowLeft className="size-4" aria-hidden="true" />
          Về hàng đợi ngay
        </motion.button>
      </div>
    </div>
  );
}

export function DecisionDesk({
  data,
  sessionId,
  view,
  ownership,
  decided,
  holdSeconds,
  onDecided,
  onDecisionError,
  onLeaveNow,
  delay = 0,
  className,
}: {
  data: SimpleNurseCaseDetailDTO;
  sessionId: string;
  view: DeskView;
  ownership: Ownership;
  decided: DecidedSummary | null;
  holdSeconds: number;
  onDecided: (summary: DecidedSummary) => void;
  onDecisionError: (error: Error) => void;
  onLeaveNow: () => void;
  delay?: number;
  className?: string;
}) {
  const aiEsi = data.ai_proposed_esi;

  return (
    <motion.aside
      id="decision-desk"
      {...riseIn(delay)}
      aria-labelledby="decision-desk-title"
      className={cn(
        "scroll-mt-6 self-start overflow-hidden rounded-3xl border border-border bg-card shadow-[0_24px_48px_-32px_rgb(15_23_42/0.45)]",
        "xl:sticky xl:top-6 xl:max-h-[calc(100dvh-3rem)] xl:overflow-y-auto xl:overscroll-contain",
        className,
      )}
    >
      <div className="bg-slate-900 px-4 py-4 sm:px-6 dark:bg-slate-800">
        <h2 id="decision-desk-title" className="text-lg font-extrabold text-white">
          Quyết định của điều dưỡng
        </h2>
        <p className="mt-2 text-sm text-slate-300">Mức bạn chốt sẽ hiển thị cho người bệnh.</p>
      </div>

      <div className="p-4 sm:p-6">
        <AnimatePresence mode="wait" initial={false}>
          <motion.div
            key={view}
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0, transition: enterTransition }}
            exit={{ opacity: 0, transition: { ...exitTransition, duration: DESK_EXIT_SECONDS } }}
          >
            {view === "confirmation" && decided ? (
              <DecisionConfirmation
                decided={decided}
                aiEsi={aiEsi}
                // Thanh đếm bắt đầu khi lời xác nhận đã hiện, tức là sau nhịp
                // mờ đi của biểu mẫu -- để nó chạy hết đúng lúc rời trang.
                holdSeconds={Math.max(holdSeconds - DESK_EXIT_SECONDS, 0)}
                onLeaveNow={onLeaveNow}
              />
            ) : view === "form" ? (
              <div className="flex flex-col gap-6">
                <AiProposal aiEsi={aiEsi} />
                {ownership === "parked-mine" && (
                  <p className="flex items-start gap-2 rounded-xl bg-amber-50 px-4 py-2 text-sm leading-6 text-amber-950 dark:bg-amber-950/40 dark:text-amber-100">
                    <span className="flex h-6 shrink-0 items-center" aria-hidden="true">
                      <PauseCircle className="size-4" />
                    </span>
                    Ca đang tạm gác. Bạn vẫn chốt được ESI khi đã đủ thông tin.
                  </p>
                )}
                {/* Đề xuất của AI đổi (ca còn đang trò chuyện vừa kết thúc) thì
                    dựng lại biểu mẫu: lựa chọn cũ được chọn trên một căn cứ khác. */}
                <SimpleDecisionForm
                  key={aiEsi ?? "none"}
                  sessionId={sessionId}
                  caseVersion={data.case_version}
                  aiEsi={aiEsi}
                  onDecided={onDecided}
                  onError={onDecisionError}
                />
              </div>
            ) : view === "closed" ? (
              <ClosedSummary data={data} />
            ) : (
              <LockedNotice aiEsi={aiEsi} ownership={ownership} />
            )}
          </motion.div>
        </AnimatePresence>
      </div>
    </motion.aside>
  );
}
