"use client";

import React, { useEffect, useMemo, useRef, useState } from "react";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { toast } from "sonner";
import { AnimatePresence, motion } from "framer-motion";
import { ChevronDown, ClipboardList, History, Info, PhoneCall, Plus, RefreshCw, ShieldAlert } from "lucide-react";

import { DisclaimerConsentModal } from "@/components/chat/DisclaimerConsentModal";
import { EmergencyCallHint } from "@/components/chat/EmergencyCallHint";
import { SimpleCareTeamDock } from "@/components/chat/SimpleCareTeamDock";
import { SimplePilotProfileSelector } from "@/components/chat/SimplePilotProfileSelector";
import { SimpleEsiResultCard, isUrgentEsi } from "@/components/chat/SimpleEsiResultCard";
import { NearbyFacilitiesCard } from "@/components/chat/NearbyFacilitiesCard";
import { SimpleMatchedProtocolsCard } from "@/components/chat/SimpleMatchedProtocolsCard";
import { SimplePilotNurseDecisionSummary } from "@/components/chat/SimplePilotNurseDecisionSummary";
import { SimplePilotSbarAccordion } from "@/components/chat/SimplePilotSbarAccordion";
import { SimpleProcessingIndicator } from "@/components/chat/SimpleProcessingIndicator";
import { SimpleTurnErrorCard } from "@/components/chat/SimpleTurnErrorCard";
import { AgentAvatar, AgentBubble, PatientBubble } from "@/components/chat/pilot/ChatBubbles";
import { PilotComposer, type PilotComposerHandle } from "@/components/chat/pilot/PilotComposer";
import { QuickReplies } from "@/components/chat/pilot/QuickReplies";
import { DangerSignsReminder, RecordedPanel, StepsPanel } from "@/components/chat/pilot/SessionInsights";
import {
  PILOT_GREETING,
  buildTranscript,
  currentStep,
  patientKey,
  pendingQuickReply,
  recordedSnapshot,
} from "@/components/chat/pilot/pilot-transcript";
// Read-only, account-level profile display -- neither component touches
// TriageCase/production triage state, safe to reuse directly (see plan).
import StickyProfileContextBar from "@/components/profile/StickyProfileContextBar";
import { VerifiedClinicalContextHeader } from "@/components/chat/VerifiedClinicalContextHeader";
import { DURATION, EASE_OUT, riseVariants, staggerDelay } from "@/lib/motion";
import { cn } from "@/lib/utils";
import {
  useSimpleTriageSessionDetail,
  useStartSimpleTriage,
  useSubmitSimpleTriageChat,
} from "@/queries/useSimpleTriageQueries";
import { isPilotUnavailableError } from "@/services/simple-triage.service";
import type { EsiLevel } from "@/types/clinical-history";

/**
 * Màn sàng lọc của `src/simple_agent`, tách riêng khỏi `/triage` (xem
 * `.claude/plans/sunny-launching-mitten.md`) và chỉ nói chuyện với
 * `/api/v1/simple-triage/*` qua `@/services/simple-triage.service`.
 *
 * Bố cục theo bản thiết kế "Màn chat sàng lọc": khung hội thoại bên trái, cột
 * "Mình đã ghi nhận" + các bước bên phải (màn hẹp thì gập vào đầu khung chat).
 * Nút trả lời nhanh chỉ xuất hiện khi máy chủ báo câu hỏi có dạng trả lời rõ
 * ràng (`question_input`); mỗi nút gửi đúng câu người bệnh có thể tự gõ.
 */

interface Outgoing {
  content: string;
  /** `turn_count` lúc gửi = `turn_index` mà dòng thật sẽ mang. */
  turn: number;
}

export default function TriagePilotPage() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const sessionId = searchParams.get("session_id");

  const sessionQuery = useSimpleTriageSessionDetail(sessionId);
  const startMutation = useStartSimpleTriage();
  const chatMutation = useSubmitSimpleTriageChat();
  const session = sessionQuery.data;

  // "Đang khám cho ai?" -- undefined = chưa chọn, null = ẩn danh. Chỉ ảnh hưởng
  // hồ sơ nào được gắn vào /start (xem agent.py's _sex_compatible).
  const [chosenProfileId, setChosenProfileId] = useState<string | null | undefined>(undefined);
  // Tin nhắn hiện ngay khi bấm gửi, và ở lại ngay dưới chỗ người bệnh vừa gõ
  // nếu gửi lỗi (kèm nút gửi lại) -- không chỉ là một toast ở góc màn hình.
  const [outgoing, setOutgoing] = useState<Outgoing | null>(null);
  const [lastError, setLastError] = useState<string | null>(null);
  const [composerHint, setComposerHint] = useState<string | undefined>(undefined);
  const [recordedOpen, setRecordedOpen] = useState(false);
  const composerRef = useRef<PilotComposerHandle>(null);

  const transcript = useMemo(() => buildTranscript(session?.messages ?? []), [session?.messages]);
  const confirmedTurns = session?.turn_count ?? 0;
  // Dòng thật của lượt vừa gửi đã về thì bong bóng tạm nhường chỗ cho nó (cùng
  // khóa nên không nháy); trước đó trợ lý vẫn "đang soạn".
  const showOutgoing = outgoing !== null && confirmedTurns <= outgoing.turn;
  const awaitingReply = showOutgoing && lastError === null;

  const isCompleted = session?.status === "COMPLETED";
  // Mức nặng nhất trong các mức khớp -- cùng cách thu hẹp với matched_atoms của
  // agent.py và citations của sbar.py.
  const rawTopEsiLevel = session?.matched_esi_levels.length ? Math.min(...session.matched_esi_levels) : null;
  const topEsiLevel: EsiLevel | null =
    rawTopEsiLevel !== null && rawTopEsiLevel >= 1 && rawTopEsiLevel <= 5 ? (rawTopEsiLevel as EsiLevel) : null;
  const rawFinalEsi = session?.final_esi;
  const finalEsiLevel: EsiLevel | null =
    rawFinalEsi != null && rawFinalEsi >= 1 && rawFinalEsi <= 5 ? (rawFinalEsi as EsiLevel) : null;
  const hasNurseDecision =
    session?.review_display_status === "APPROVED" || session?.review_display_status === "OVERRIDDEN";
  const displayedEsiLevel = hasNurseDecision && finalEsiLevel !== null ? finalEsiLevel : topEsiLevel;
  const showUrgentCall = isCompleted && displayedEsiLevel !== null && isUrgentEsi(displayedEsiLevel);
  // Bộ sàng lọc cấp cứu ở backend gắn `safety_alert` vào lượt có dấu hiệu nguy
  // kịch. Tin nhắn đó có thể bị cuộn khuất, nên nút 115 ở lại ngay trên ô nhập
  // cho tới hết phiên -- phiên vẫn tiếp tục, không bị khoá.
  const hasSafetyAlert = useMemo(
    () => (session?.messages ?? []).some((row) => row.decision_snapshot.safety_alert),
    [session?.messages],
  );

  const quickReply = awaitingReply || lastError ? null : pendingQuickReply(session);
  const recorded = recordedSnapshot(session);
  const lastAgentSnapshot = session?.messages.findLast((row) => row.sender === "AGENT")?.decision_snapshot;
  const freshFactIds = useMemo(() => new Set(lastAgentSnapshot?.accepted_fact_ids ?? []), [lastAgentSnapshot]);
  const freshSymptomIds = useMemo(
    () => new Set(lastAgentSnapshot?.asserted_concept_ids ?? []),
    [lastAgentSnapshot],
  );
  const step = currentStep(session);
  const recordedCount = recorded.symptoms.length + recorded.facts.length;

  const handleStart = async (content: string) => {
    const trimmed = content.trim();
    if (!trimmed || chosenProfileId === undefined) return;
    setOutgoing({ content: trimmed, turn: 0 });
    setLastError(null);
    try {
      const result = await startMutation.mutateAsync({ message: trimmed, profileId: chosenProfileId });
      router.push(`/triage-pilot?session_id=${result.session_id}`);
    } catch (error: unknown) {
      const message = error instanceof Error ? error.message : "Khởi tạo phiên sàng lọc thất bại.";
      setLastError(message);
      toast.error(message);
    }
  };

  const handleSend = async (content: string) => {
    const trimmed = content.trim();
    if (!sessionId || !trimmed) return;
    setOutgoing({ content: trimmed, turn: confirmedTurns });
    setLastError(null);
    setComposerHint(undefined);
    try {
      await chatMutation.mutateAsync({ sessionId, message: trimmed });
    } catch (error: unknown) {
      const message = error instanceof Error ? error.message : "Gửi thông điệp thất bại.";
      setLastError(message);
      toast.error(message);
    }
  };

  const handleRetry = () => {
    if (!outgoing) return;
    if (sessionId) {
      void handleSend(outgoing.content);
    } else {
      void handleStart(outgoing.content);
    }
  };

  const handleWantToAdd = () => {
    setComposerHint("Bạn muốn bổ sung điều gì?");
    composerRef.current?.focus();
  };

  const handleNewSession = () => {
    window.location.href = "/triage-pilot";
  };

  // `scrollIntoView` tự tìm vùng cuộn gần nhất (chính là khung hội thoại).
  const bottomRef = useRef<HTMLDivElement>(null);
  // Khi phiên đã có kết quả, mốc cuộn là chính thẻ kết quả chứ không phải đáy:
  // bên dưới thẻ còn danh sách cơ sở y tế, tiêu chí phác đồ và SBAR, nên cuộn
  // tới đáy sẽ đẩy mức ESI -- và nút gọi 115 của ESI 1/2 -- ra khỏi tầm mắt.
  const resultRef = useRef<HTMLDivElement>(null);
  const hasAutoScrolledRef = useRef(false);
  useEffect(() => {
    if (transcript.length === 0 && !outgoing) return;
    // Lần đầu vào phiên thì nhảy thẳng, các lượt sau thì cuộn mượt.
    const behavior: ScrollBehavior = hasAutoScrolledRef.current ? "smooth" : "auto";
    hasAutoScrolledRef.current = true;
    const id = window.requestAnimationFrame(() => {
      if (resultRef.current) {
        resultRef.current.scrollIntoView({ behavior, block: "start" });
      } else {
        bottomRef.current?.scrollIntoView({ behavior, block: "end" });
      }
    });
    return () => window.cancelAnimationFrame(id);
  }, [transcript.length, outgoing, awaitingReply, isCompleted, displayedEsiLevel, quickReply?.kind]);

  // -- 503: dịch vụ tắt ở môi trường này -----------------------------------
  // Người bệnh không bật được cờ nào ở máy chủ, nên màn này không nói về cấu
  // hình -- chỉ nói việc họ làm được ngay bây giờ.
  if (sessionId && sessionQuery.isError && isPilotUnavailableError(sessionQuery.error)) {
    return (
      <div className="page-enter mx-auto flex h-full max-w-lg flex-col items-center justify-center gap-4 p-8 text-center">
        <ShieldAlert className="size-12 text-amber-600" aria-hidden="true" />
        <h1 className="text-xl font-bold text-foreground">Dịch vụ sàng lọc AI tạm thời chưa hoạt động</h1>
        <p className="text-base leading-7 text-muted-foreground">
          Bạn vẫn có thể liên hệ trực tiếp cơ sở y tế gần nhất để được thăm khám.
        </p>
        <EmergencyCallHint className="justify-center" />
      </div>
    );
  }

  const profileChosen = chosenProfileId !== undefined;
  const activeProfileId = (sessionId ? session?.profile_id : chosenProfileId) ?? null;
  const showIntro = !sessionId && !profileChosen;
  const showComposer = sessionId ? !isCompleted : profileChosen;
  // Đang mở một phiên cũ (không phải vừa gửi lượt đầu): hiện khung chờ thay vì
  // một danh sách rỗng.
  const showLoader = Boolean(sessionId) && sessionQuery.isLoading && !outgoing;

  const statusLine = !sessionId
    ? "Mỗi lượt, trợ lý chỉ hỏi một điều còn thiếu."
    : awaitingReply
      ? "Trợ lý đang trả lời…"
      : isCompleted
        ? hasNurseDecision
          ? "Điều dưỡng đã xem kết quả"
          : "Đã có kết quả · chờ nhân viên y tế xem lại"
        : step === 3
          ? "Chờ bạn xác nhận lại thông tin"
          : "Đang hỏi thêm";

  const recordedPanel = (
    <RecordedPanel recorded={recorded} freshFactIds={freshFactIds} freshSymptomIds={freshSymptomIds} />
  );

  return (
    <div className="page-enter flex h-full min-h-0 gap-4">
      <DisclaimerConsentModal />

      <section
        aria-label="Hội thoại sàng lọc"
        className="flex min-w-0 flex-1 flex-col overflow-hidden rounded-3xl border border-border bg-card shadow-sm"
      >
        <header className="flex items-center gap-2 border-b border-border px-4 py-2 sm:px-6">
          <div className="min-w-0 flex-1 py-2">
            <h1 className="truncate text-lg font-bold text-foreground">
              <span className="sm:hidden">Sàng lọc</span>
              <span className="hidden sm:inline">{sessionId ? "Phiên sàng lọc" : "Phiên sàng lọc mới"}</span>
            </h1>
            <p className="flex items-center gap-2 text-sm text-muted-foreground">
              {sessionId && !isCompleted && (
                <span
                  aria-hidden="true"
                  className={cn("live-dot size-2 shrink-0 rounded-full", awaitingReply ? "bg-amber-500" : "bg-brand")}
                />
              )}
              <AnimatePresence mode="wait" initial={false}>
                <motion.span
                  key={statusLine}
                  initial={{ opacity: 0, y: 4 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0, y: -4 }}
                  transition={{ duration: DURATION.quick, ease: EASE_OUT }}
                  className="truncate"
                >
                  {statusLine}
                </motion.span>
              </AnimatePresence>
            </p>
          </div>
          {recorded.available && (
            <button
              type="button"
              onClick={() => setRecordedOpen((open) => !open)}
              aria-expanded={recordedOpen}
              aria-controls="recorded-drawer"
              aria-label={`Mình đã ghi nhận ${recordedCount} thông tin`}
              className="flex min-h-11 shrink-0 items-center gap-2 rounded-xl border border-border px-2 text-sm font-semibold text-foreground transition-colors hover:bg-muted sm:px-4 xl:hidden"
            >
              <ClipboardList className="size-5 text-brand sm:hidden" aria-hidden="true" />
              <span className="hidden sm:inline">Đã ghi nhận</span>
              <span className="rounded-full bg-brand-soft px-2 text-sm font-bold text-brand-ink">{recordedCount}</span>
              <ChevronDown
                className={cn("size-4 transition-transform duration-200", recordedOpen && "rotate-180")}
                aria-hidden="true"
              />
            </button>
          )}
          <Link
            href="/triage-pilot/history"
            aria-label="Lịch sử sàng lọc"
            title="Lịch sử sàng lọc"
            className="flex size-11 shrink-0 items-center justify-center rounded-xl text-muted-foreground transition-colors hover:bg-muted hover:text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand"
          >
            <History className="size-5" aria-hidden="true" />
          </Link>
          {sessionId && (
            <button
              type="button"
              onClick={handleNewSession}
              aria-label="Bắt đầu phiên mới"
              title="Bắt đầu phiên mới"
              className="flex size-11 shrink-0 items-center justify-center rounded-xl text-muted-foreground transition-colors hover:bg-muted hover:text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand"
            >
              <Plus className="size-5" aria-hidden="true" />
            </button>
          )}
        </header>

        <AnimatePresence initial={false}>
          {recordedOpen && recorded.available && (
            <motion.div
              id="recorded-drawer"
              key="recorded-drawer"
              initial={{ height: 0, opacity: 0 }}
              animate={{ height: "auto", opacity: 1 }}
              exit={{ height: 0, opacity: 0 }}
              transition={{ duration: DURATION.base, ease: EASE_OUT }}
              className="max-h-[45%] shrink-0 overflow-y-auto border-b border-border bg-muted/40 xl:hidden"
            >
              <div className="p-4">{recordedPanel}</div>
            </motion.div>
          )}
        </AnimatePresence>

        <div className="min-h-0 flex-1 overflow-y-auto overscroll-contain">
          <div className="mx-auto flex w-full max-w-3xl flex-col gap-6 p-4 sm:p-6">
            {showIntro ? (
              <motion.div
                variants={riseVariants}
                initial="hidden"
                animate="visible"
                className="flex flex-col gap-6"
              >
                <div className="flex flex-col items-start gap-4">
                  <AgentAvatar className="size-12 rounded-2xl" />
                  <div>
                    <p className="text-2xl font-extrabold tracking-tight text-foreground">
                      Bạn đang thấy không khỏe ở đâu?
                    </p>
                    <p className="mt-2 max-w-xl text-base leading-7 text-muted-foreground">
                      Kể cho trợ lý bằng lời của bạn. Mỗi lượt trợ lý chỉ hỏi thêm một điều còn thiếu, rồi chuyển
                      kết quả cho nhân viên y tế xem lại.
                    </p>
                  </div>
                </div>
                <SimplePilotProfileSelector
                  onProfileChosen={setChosenProfileId}
                  preselectedId={searchParams.get("for")}
                />
                <p className="flex items-start gap-2 rounded-2xl bg-muted px-4 py-4 text-sm leading-6 text-muted-foreground">
                  <Info className="mt-1 size-4 shrink-0" aria-hidden="true" />
                  <span>
                    AI Triage hỗ trợ ghi nhận triệu chứng và sàng lọc mức độ ưu tiên dựa trên thông tin bạn cung cấp.
                    Hãy mô tả đầy đủ, chính xác để nhận được gợi ý phù hợp. Nếu xuất hiện dấu hiệu nguy hiểm hoặc
                    tình trạng xấu đi, hãy gọi 115 hoặc đến cơ sở y tế gần nhất.
                  </span>
                </p>
              </motion.div>
            ) : (
              <>
                {/* "Đang khám cho ai": chỉ hiện khi có thẻ hồ sơ. Ẩn danh thì bỏ
                    hẳn -- truyền null sẽ tự rơi về hồ sơ chính chủ, gây hiểu lầm. */}
                {activeProfileId && <StickyProfileContextBar lockedProfileId={activeProfileId} />}
                <VerifiedClinicalContextHeader profileId={activeProfileId} />

                {sessionId && sessionQuery.isError && !isPilotUnavailableError(sessionQuery.error) ? (
                  <div role="alert" className="rounded-2xl border border-rose-200 bg-rose-50 p-6 text-center dark:border-rose-900 dark:bg-rose-950/40">
                    <p className="text-base font-semibold text-rose-900 dark:text-rose-100">Không thể tải phiên này.</p>
                    <p className="mt-2 text-sm text-rose-800 dark:text-rose-200">
                      {sessionQuery.error instanceof Error ? sessionQuery.error.message : "Vui lòng thử lại."}
                    </p>
                    <button
                      type="button"
                      onClick={() => void sessionQuery.refetch()}
                      className="mx-auto mt-4 flex min-h-11 items-center gap-2 rounded-xl border border-rose-300 bg-card px-4 text-sm font-semibold text-rose-800 transition-colors hover:bg-rose-100 dark:text-rose-200"
                    >
                      <RefreshCw className="size-4" aria-hidden="true" />
                      Tải lại
                    </button>
                    <EmergencyCallHint className="mt-4 justify-center" />
                  </div>
                ) : showLoader ? (
                  <div className="flex flex-col gap-6" aria-busy="true" aria-label="Đang tải hội thoại">
                    {[0, 1, 2].map((row) => (
                      <div
                        key={row}
                        className={cn(
                          "skeleton-sweep relative h-14 overflow-hidden rounded-2xl bg-muted",
                          row % 2 === 1 ? "ml-auto w-1/2" : "w-2/3",
                        )}
                      />
                    ))}
                  </div>
                ) : (
                  <ol role="log" aria-label="Nội dung hội thoại" aria-live="polite" className="flex flex-col gap-6">
                    {/* Phiên cũ mở ra thì hiện ngay; chỉ những gì tới sau mới nổi lên. */}
                    <AnimatePresence initial={!sessionId}>
                      <AgentBubble key="greeting" content={PILOT_GREETING} />
                      {transcript.map((entry, index) =>
                        entry.kind === "patient" ? (
                          <PatientBubble key={entry.key} content={entry.content} />
                        ) : (
                          <AgentBubble key={entry.key} content={entry.content} guarded={entry.guarded} safety={entry.safety}>
                            {quickReply && index === transcript.length - 1 && (
                              <QuickReplies
                                kind={quickReply.kind}
                                questionTargetId={quickReply.questionTargetId}
                                disabled={awaitingReply || !sessionId}
                                onReply={(text) => void handleSend(text)}
                                onWantToAdd={handleWantToAdd}
                              />
                            )}
                          </AgentBubble>
                        ),
                      )}
                      {showOutgoing && outgoing && (
                        <PatientBubble
                          key={patientKey(outgoing.turn)}
                          content={outgoing.content}
                          state={lastError ? "failed" : "sending"}
                        />
                      )}
                      {awaitingReply && <SimpleProcessingIndicator key="typing" />}
                    </AnimatePresence>
                  </ol>
                )}

                {lastError && !awaitingReply && <SimpleTurnErrorCard message={lastError} onRetry={handleRetry} />}

                {isCompleted && (
                  <div className="flex flex-col gap-4">
                    {displayedEsiLevel !== null && (
                      <div ref={resultRef} className="scroll-mt-4">
                        <SimpleEsiResultCard
                          esiLevel={displayedEsiLevel}
                          source={hasNurseDecision && finalEsiLevel !== null ? "NURSE" : "AI"}
                        />
                      </div>
                    )}
                    {/* Các phần bổ trợ lên lần lượt sau thẻ kết quả. Cơ sở y tế gần
                        nhất chỉ là phần hiển thị thêm: đọc đúng mức đã chốt ở trên
                        và tự ẩn với ESI 4/5 -- xem NearbyFacilitiesCard. */}
                    {[
                      { key: "nearby", node: <NearbyFacilitiesCard esiLevel={displayedEsiLevel} /> },
                      ...(session
                        ? [
                            {
                              key: "nurse",
                              node: (
                                <SimplePilotNurseDecisionSummary
                                  aiProposedEsi={topEsiLevel}
                                  finalEsi={finalEsiLevel}
                                  reviewStatus={session.review_display_status}
                                  reviewerName={session.reviewer_name}
                                  reviewedAt={session.reviewed_at}
                                  decisionNote={session.decision_note}
                                />
                              ),
                            },
                          ]
                        : []),
                      {
                        key: "criteria",
                        node: (
                          <SimpleMatchedProtocolsCard
                            matchedAtoms={session?.messages.at(-1)?.decision_snapshot.matched_atoms ?? []}
                          />
                        ),
                      },
                      ...(session?.sbar && sessionId
                        ? [{ key: "sbar", node: <SimplePilotSbarAccordion sbar={session.sbar} sessionId={sessionId} /> }]
                        : []),
                    ].map(({ key, node }, index) => (
                      <motion.div
                        key={key}
                        initial={{ opacity: 0, y: 8 }}
                        animate={{ opacity: 1, y: 0 }}
                        transition={{ duration: DURATION.base, ease: EASE_OUT, delay: staggerDelay(index, 0.3) }}
                        className="empty:hidden"
                      >
                        {node}
                      </motion.div>
                    ))}
                  </div>
                )}

                <div ref={bottomRef} aria-hidden="true" className="h-px w-full" />
              </>
            )}
          </div>
        </div>

        {showComposer && (
          <div className="shrink-0 border-t border-border bg-card">
            <AnimatePresence initial={false}>
              {hasSafetyAlert && (
                <motion.div
                  key="safety-strip"
                  role="alert"
                  initial={{ height: 0, opacity: 0 }}
                  animate={{ height: "auto", opacity: 1 }}
                  transition={{ duration: DURATION.gentle, ease: EASE_OUT }}
                  className="overflow-hidden border-b border-rose-200 bg-rose-50 dark:border-rose-900 dark:bg-rose-950/40"
                >
                  <div className="flex items-center justify-between gap-4 px-4 py-2 sm:px-6">
                    <p className="text-sm font-semibold text-rose-900 dark:text-rose-100">
                      Có dấu hiệu nguy kịch? Đừng chờ trợ lý.
                    </p>
                    <a
                      href="tel:115"
                      aria-label="Gọi Tổng đài Cấp cứu Quốc gia 115"
                      className="ring-pulse flex min-h-11 shrink-0 items-center gap-2 rounded-xl bg-rose-700 px-4 text-base font-extrabold text-white transition-colors hover:bg-rose-800 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-rose-600 focus-visible:ring-offset-2"
                    >
                      <PhoneCall className="size-4 shrink-0" aria-hidden="true" />
                      Gọi 115
                    </a>
                  </div>
                </motion.div>
              )}
            </AnimatePresence>
            <PilotComposer
              key={sessionId ?? "new"}
              ref={composerRef}
              onSend={(text) => void (sessionId ? handleSend(text) : handleStart(text))}
              isProcessing={awaitingReply}
              disabled={sessionId ? sessionQuery.isLoading || isCompleted : false}
              placeholder={
                composerHint ?? (sessionId ? "Hoặc gõ câu trả lời của bạn…" : "Ví dụ: tôi bị đau bụng từ sáng nay…")
              }
            />
          </div>
        )}

        {/* Thanh ghim đáy luôn trong tầm mắt, kể cả khi người bệnh cuộn đọc SBAR.
            Với ESI 1/2, hành động chính ở đây là gọi 115 -- "Bắt đầu phiên mới"
            lùi xuống làm lựa chọn phụ. Mức hiển thị là mức điều dưỡng đã chốt
            nếu có, nên khi điều dưỡng hạ mức thì nút 115 cũng rút đi. */}
        {isCompleted && (
          <div className="grid shrink-0 grid-cols-2 gap-2 border-t border-border bg-card p-4 sm:flex sm:justify-center">
            {showUrgentCall && (
              <a
                href="tel:115"
                aria-label="Gọi Tổng đài Cấp cứu Quốc gia 115"
                className="col-span-2 flex min-h-12 items-center justify-center gap-2 rounded-xl bg-rose-700 px-6 text-base font-extrabold text-white transition-colors hover:bg-rose-800 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-rose-600 focus-visible:ring-offset-2"
              >
                <PhoneCall className="size-5 shrink-0" aria-hidden="true" />
                Gọi 115
              </a>
            )}
            {/* Kênh nhắn tin chỉ mở sau khi phiên đã COMPLETED -- trước đó chưa
                có review row nào để y tá theo dõi, khớp điều kiện phía backend. */}
            {sessionId && (
              <SimpleCareTeamDock sessionId={sessionId} initialOpen={searchParams.get("openChat") === "1"} inline />
            )}
            <button
              type="button"
              onClick={handleNewSession}
              aria-label="Bắt đầu phiên mới"
              className="flex min-h-12 items-center justify-center gap-2 rounded-xl border border-border bg-background px-4 text-sm font-semibold text-foreground transition-colors hover:bg-muted sm:px-6 sm:text-base"
            >
              <Plus className="size-5 shrink-0" aria-hidden="true" />
              <span className="sm:hidden">Phiên mới</span>
              <span className="hidden sm:inline">Bắt đầu phiên mới</span>
            </button>
          </div>
        )}
      </section>

      <aside aria-label="Thông tin phiên" className="hidden w-80 shrink-0 flex-col gap-4 overflow-y-auto xl:flex">
        {(recorded.available || !sessionId) && recordedPanel}
        <StepsPanel step={step} />
        <DangerSignsReminder />
      </aside>
    </div>
  );
}
