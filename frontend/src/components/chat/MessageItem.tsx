"use client";

import React from "react";
import { motion, useReducedMotion } from "framer-motion";
import { Bot, CheckCircle2, Info, ShieldCheck, Stethoscope, User } from "lucide-react";

import { ClinicalMarkdown } from "@/components/chat/ClinicalMarkdown";
import { EvidenceSources } from "@/components/chat/EvidenceSources";
import { StructuredChoiceCards } from "@/components/chat/StructuredChoiceCards";
import { cn } from "@/lib/utils";
import type { ChatMessage, WorkflowPhase } from "@/types/triage-chat";

interface MessageItemProps {
  message: ChatMessage;
  onSelectAnswer: (
    messageId: string,
    answer: string | string[] | number,
    optionId?: string,
  ) => void;
  disabled?: boolean;
}

function formattedMessageTime(timestamp: string): string | null {
  const parsed = new Date(timestamp);
  if (Number.isNaN(parsed.getTime())) return null;
  return parsed.toLocaleTimeString("vi-VN", { hour: "2-digit", minute: "2-digit" });
}

const WORKFLOW_PHASE_LABELS: Record<WorkflowPhase, string> = {
  SAFETY_CHECK: "Kiểm tra an toàn",
  INTENT_CLASSIFICATION: "Xác định nhu cầu",
  INTAKE_EXTRACTION: "Thu thập thông tin",
  CLARIFICATION: "Làm rõ thông tin",
  PATIENT_CONFIRMATION: "Chờ xác nhận",
  RETRIEVAL: "Đối chiếu nguồn",
  REASONING: "Phân tích có căn cứ",
  REASSESSMENT: "Đánh giá lại",
  HANDOFF: "Chuyển thẩm định",
  COMPLETE: "Hoàn tất",
};

export function MessageItem({
  message,
  onSelectAnswer,
  disabled = false,
}: MessageItemProps) {
  const isBot = message.sender === "bot";
  const isUser = message.sender === "user";
  const isSystem = message.sender === "system_shield";
  const isNurse = message.sender === "nurse";
  const shouldReduceMotion = useReducedMotion();
  const displayTime = formattedMessageTime(message.timestamp);

  // Tin của nhân viên lâm sàng phải trông khác hẳn tin của AI. Người bệnh cần
  // biết chắc câu này do một con người có chuyên môn viết ra.
  if (isNurse) {
    return (
      <motion.article
        initial={shouldReduceMotion ? false : { opacity: 0, y: 12 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: shouldReduceMotion ? 0 : 0.25, ease: "easeOut" }}
        className="my-4 flex min-w-0 w-full justify-start gap-4 font-sans"
      >
        <div className="flex shrink-0 flex-col items-center">
          <span className="flex size-14 items-center justify-center rounded-2xl bg-gradient-to-br from-teal-500 to-teal-700 text-white shadow-xs">
            <Stethoscope className="size-6" aria-hidden="true" />
          </span>
          <span className="mt-2 text-sm font-bold text-teal-700 dark:text-teal-300">
            Nhân viên y tế
          </span>
        </div>

        <div className="flex min-w-0 max-w-3xl flex-col rounded-3xl rounded-tl-sm border border-teal-200 bg-teal-50/80 p-4 text-slate-900 shadow-xs sm:p-5 dark:border-teal-800 dark:bg-teal-950/60 dark:text-teal-50">
          <header className="flex flex-wrap items-center justify-between gap-2 border-b border-teal-200 pb-3 text-sm font-bold text-teal-800 dark:border-teal-800 dark:text-teal-200">
            <span className="flex items-center gap-2">
              <span className="size-2 rounded-full bg-teal-600" aria-hidden="true" />
              {message.senderName ?? "Nhân viên y tế phụ trách"}
            </span>
            <time dateTime={message.timestamp}>{displayTime}</time>
          </header>
          <p className="mt-3 whitespace-pre-wrap break-words text-base leading-relaxed sm:text-lg">
            {message.content}
          </p>
        </div>
      </motion.article>
    );
  }

  if (isSystem) {
    return (
      <motion.div
        role="alert"
        aria-live="assertive"
        initial={shouldReduceMotion ? false : { opacity: 0, scale: 0.95 }}
        animate={{ opacity: 1, scale: 1 }}
        transition={{ duration: shouldReduceMotion ? 0 : 0.25 }}
        className="my-4 flex items-center justify-center px-4 font-sans"
      >
        <div className="flex max-w-2xl items-start gap-3 rounded-xl border-2 border-rose-300 bg-rose-50 p-4 text-left text-base font-semibold leading-6 text-rose-950 dark:border-rose-700 dark:bg-rose-950/80 dark:text-rose-100">
          <ShieldCheck
            className="mt-0.5 size-5 shrink-0 text-rose-700 dark:text-rose-300"
            aria-hidden="true"
          />
          <ClinicalMarkdown content={message.content} className="min-w-0" />
        </div>
      </motion.div>
    );
  }

  return (
    <motion.article
      initial={shouldReduceMotion ? false : { opacity: 0, y: 12, scale: 0.98 }}
      animate={{ opacity: 1, y: 0, scale: 1 }}
      transition={{ duration: shouldReduceMotion ? 0 : 0.25, ease: "easeOut" }}
      className={cn("my-4 flex min-w-0 w-full gap-4 font-sans", {
        "justify-end": isUser,
        "justify-start": isBot,
      })}
    >
      {isBot && (
        <div className="flex shrink-0 flex-col items-center">
          <span className="flex size-14 items-center justify-center rounded-2xl border border-sky-200/80 bg-gradient-to-br from-sky-50 to-white text-sky-700 shadow-xs dark:border-sky-800 dark:from-sky-950 dark:to-zinc-900 dark:text-sky-300">
            <Bot className="size-6" aria-hidden="true" />
          </span>
          <span className="mt-2 text-sm font-bold text-slate-500 dark:text-slate-400">
            AI Triage
          </span>
        </div>
      )}

      <div
        className={cn("flex min-w-0 flex-col", {
          "max-w-xl rounded-3xl rounded-tr-sm bg-gradient-to-br from-sky-600 to-sky-700 p-4 text-base font-semibold leading-relaxed text-white shadow-xs sm:px-5 sm:py-4 sm:text-lg":
            isUser,
          "w-full max-w-3xl space-y-4 rounded-3xl rounded-tl-sm border border-slate-200/90 bg-white p-4 text-slate-900 shadow-xs dark:border-slate-800 dark:bg-zinc-900 dark:text-slate-100 sm:p-5":
            isBot,
        })}
      >
        {isBot && (
          <header className="flex flex-wrap items-center justify-between gap-2 border-b border-slate-100 pb-3 text-sm font-bold text-slate-500 dark:border-slate-800/80 dark:text-slate-400">
            <span className="flex items-center gap-2">
              <span className="size-2 rounded-full bg-emerald-500" aria-hidden="true" />
              <span className="font-bold text-sky-700 dark:text-sky-300">
                Trợ lý sàng lọc
                {message.workflowPhase ? ` · ${WORKFLOW_PHASE_LABELS[message.workflowPhase]}` : ""}
              </span>
            </span>
            {displayTime && <time dateTime={message.timestamp}>{displayTime}</time>}
          </header>
        )}

        {isBot && message.decisionStatus === "NEEDS_CLARIFICATION" && (
          <div
            role="status"
            className="flex items-start gap-3 rounded-xl border border-sky-200 bg-sky-50 p-4 text-sm leading-6 text-sky-950 dark:border-sky-800 dark:bg-sky-950/50 dark:text-sky-100"
          >
            <Info className="mt-0.5 size-5 shrink-0" aria-hidden="true" />
            <div>
              <p className="font-bold">Cần làm rõ thông tin</p>
              <p>Thông tin hiện có cần được làm rõ trước khi tiếp tục.</p>
            </div>
          </div>
        )}

        {isBot ? (
          <ClinicalMarkdown
            content={message.content}
            className="text-base font-medium leading-relaxed text-slate-800 dark:text-slate-100 sm:text-lg"
          />
        ) : (
          <div className="break-words whitespace-pre-wrap">{message.content}</div>
        )}

        {isBot && (
          <EvidenceSources
            citations={message.ragCitations}
            caseSupport={message.caseSupport}
            decisionStatus={message.decisionStatus}
            evidenceStatus={message.evidenceStatus}
            retrievalDegradedModes={message.retrievalDegradedModes}
          />
        )}

        {isBot && message.structured && (
          <div className="pt-2">
            {!message.structured.submitted ? (
              <StructuredChoiceCards
                payload={message.structured}
                onSubmitAnswer={(answer, optionId) =>
                  onSelectAnswer(message.id, answer, optionId)
                }
                disabled={disabled}
              />
            ) : (
              <div className="mt-4 flex items-center gap-4 rounded-2xl border-2 border-emerald-300 bg-emerald-50 p-4 text-sm font-bold text-emerald-950 dark:border-emerald-800 dark:bg-emerald-950/80 dark:text-emerald-100 sm:text-base">
                <CheckCircle2
                  className="size-6 shrink-0 text-emerald-600 dark:text-emerald-400"
                  aria-hidden="true"
                />
                <span>
                  Đã ghi nhận câu trả lời:{" "}
                  <strong className="ml-1 font-mono font-bold text-emerald-950 dark:text-white">
                    {Array.isArray(message.structured.selectedAnswer)
                      ? message.structured.selectedAnswer.join(" • ")
                      : String(message.structured.selectedAnswer)}
                  </strong>
                </span>
              </div>
            )}
          </div>
        )}
      </div>

      {isUser && (
        <div className="flex shrink-0 flex-col items-center">
          <span className="flex size-14 items-center justify-center rounded-2xl bg-gradient-to-br from-slate-700 to-slate-900 text-white shadow-xs">
            <User className="size-6" aria-hidden="true" />
          </span>
          <span className="mt-2 text-sm font-bold text-slate-500 dark:text-slate-400">
            Bạn
          </span>
        </div>
      )}
    </motion.article>
  );
}
