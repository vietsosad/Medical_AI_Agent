"use client";

import React, { useState, useEffect, useCallback, useRef } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  Bot,
  User,
  CheckCircle2,
  FileText,
  Lock,
  Play,
  Pause,
  RotateCcw,
  FastForward,
  Activity,
  AlertTriangle,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { Slider } from "@/components/ui/slider";
import { ClinicalMarkdown } from "@/components/chat/ClinicalMarkdown";
import { EvidenceSources } from "@/components/chat/EvidenceSources";
import type {
  ChatMessage,
  StructuredPayload,
} from "@/types/triage-chat";

export interface ConversationReplayFeedProps {
  messages: ChatMessage[];
  className?: string;
  chiefComplaint?: string;
}

interface ReadOnlyStructuredProps {
  payload: StructuredPayload;
}

const ReadOnlyStructuredPayload: React.FC<ReadOnlyStructuredProps> = ({ payload }) => {
  const { optionsType, options, minScale = 0, maxScale = 10, selectedAnswer } = payload;

  if ((optionsType === "single" || optionsType === "multiple") && options && options.length > 0) {
    const selectedList: Array<string | number> = Array.isArray(selectedAnswer)
      ? selectedAnswer
      : selectedAnswer !== undefined
      ? [selectedAnswer]
      : [];

    return (
      <div className="mt-3.5 space-y-2.5 w-full pt-2 border-t border-slate-100 font-sans">
        <p className="text-[11px] font-mono uppercase tracking-wider text-sky-700 font-extrabold flex items-center gap-1">
          <FileText className="w-3.5 h-3.5 stroke-[2.5]" />
          <span>Biểu Mẫu Trắc Nghiệm Quá Khứ ({optionsType === "single" ? "Chọn 1" : "Chọn nhiều"}):</span>
        </p>
        <div className="space-y-2">
          {options.map((opt) => {
            const isSelected =
              selectedList.includes(opt.value) ||
              selectedList.includes(opt.id) ||
              selectedList.includes(opt.label);

            if (isSelected) {
              return (
                <div
                  key={opt.id}
                  className="p-3.5 rounded-2xl bg-emerald-50 border border-emerald-300 text-emerald-950 shadow-2xs flex flex-col sm:flex-row items-start sm:items-center justify-between gap-2 transition-all"
                >
                  <div className="space-y-0.5">
                    <div className="flex items-center gap-1.5 font-bold text-emerald-950 text-sm">
                      <span>{opt.label}</span>
                      {opt.isRisk && (
                        <span className="px-1.5 py-0.5 rounded-md bg-rose-100 text-rose-800 border border-rose-300 text-[10px] uppercase font-bold animate-pulse">
                          Cờ đỏ nguy cơ
                        </span>
                      )}
                    </div>
                    {opt.description && (
                      <p className="text-xs text-emerald-800 font-normal">{opt.description}</p>
                    )}
                  </div>

                  <div className="shrink-0 flex items-center gap-1.5 text-xs font-black text-emerald-900 bg-emerald-100 px-2.5 py-1 rounded-full border border-emerald-300 shadow-2xs">
                    <CheckCircle2 className="w-4 h-4 text-emerald-600 shrink-0 stroke-[2.5]" />
                    <span>Bệnh nhân đã chọn</span>
                  </div>
                </div>
              );
            }

            return (
              <div
                key={opt.id}
                className="p-3.5 rounded-2xl text-slate-400 bg-background border border-border pointer-events-none opacity-60 flex items-center justify-between select-none"
              >
                <div className="space-y-0.5">
                  <span className="text-sm font-medium text-muted-foreground line-through decoration-slate-400">
                    {opt.label}
                  </span>
                  {opt.description && <p className="text-xs text-slate-400 font-normal">{opt.description}</p>}
                </div>
                <span className="text-[11px] text-slate-400 uppercase font-mono font-bold">Không chọn</span>
              </div>
            );
          })}
        </div>
      </div>
    );
  }

  if (optionsType === "scale") {
    const numericVal =
      typeof selectedAnswer === "number"
        ? selectedAnswer
        : typeof selectedAnswer === "string" && selectedAnswer.trim() !== ""
          ? Number(selectedAnswer)
          : Number.NaN;

    if (
      !Number.isFinite(numericVal) ||
      minScale > maxScale ||
      numericVal < minScale ||
      numericVal > maxScale
    ) {
      return (
        <div className="mt-4 rounded-xl border border-border bg-background p-4 text-sm text-slate-600 dark:text-slate-300">
          Chưa có câu trả lời hợp lệ được lưu cho thang điểm này.
        </div>
      );
    }

    return (
      <div className="mt-4 pt-3 border-t border-slate-100 space-y-3.5 w-full font-sans">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
          <span className="text-xs font-extrabold text-slate-700 uppercase tracking-wider flex items-center gap-1.5 dark:text-slate-200">
            <Activity className="w-4 h-4 text-rose-600 animate-pulse stroke-[2.5]" />
            <span>Câu trả lời trên thang điểm:</span>
          </span>

          <div className="flex min-h-11 items-center rounded-full border border-slate-300 bg-background px-4 text-sm font-bold text-foreground shadow-2xs dark:border-slate-700">
            {numericVal} / {maxScale}
          </div>
        </div>

        <div className="px-2 pt-2 pb-1 pointer-events-none opacity-90">
          <Slider
            defaultValue={[numericVal]}
            value={[numericVal]}
            min={minScale}
            max={maxScale}
            step={1}
            disabled={true}
            className="cursor-not-allowed"
            trackClassName="h-3.5 bg-slate-200 border-slate-300 dark:bg-slate-700 dark:border-slate-700"
            thumbClassName="h-7 w-7 border-2 border-rose-600 bg-card shadow-sm"
          />
          <div className="flex justify-between text-xs font-mono text-muted-foreground mt-2 font-bold">
            <span>{minScale}</span>
            <span>{maxScale}</span>
          </div>
        </div>
      </div>
    );
  }

  return null;
};

/**
 * ⭐ [SCR-HIST-02] TRANG TRUNG TÂM TÁI HIỆN HỘI THOẠI CẤU TRÚC (ConversationReplayFeed) - G4
 * Giao diện Sáng Hiện Đại Chuẩn Lâm Sàng (Pristine Light Mode).
 */
export const ConversationReplayFeed: React.FC<ConversationReplayFeedProps> = ({
  messages,
  className,
}) => {
  const [isPlaying, setIsPlaying] = useState<boolean>(false);
  const [visibleCount, setVisibleCount] = useState<number>(messages.length);
  const timerRef = useRef<NodeJS.Timeout | null>(null);

  const startSimulation = useCallback(() => {
    if (timerRef.current) clearInterval(timerRef.current);
    setVisibleCount(1);
    setIsPlaying(true);
  }, []);

  const togglePlayPause = useCallback(() => {
    setIsPlaying((prev) => !prev);
  }, []);

  const showAllImmediately = useCallback(() => {
    if (timerRef.current) clearInterval(timerRef.current);
    setIsPlaying(false);
    setVisibleCount(messages.length);
  }, [messages.length]);

  useEffect(() => {
    if (isPlaying) {
      timerRef.current = setInterval(() => {
        setVisibleCount((prev) => {
          if (prev < messages.length) {
            return prev + 1;
          } else {
            setIsPlaying(false);
            if (timerRef.current) clearInterval(timerRef.current);
            return prev;
          }
        });
      }, 1500);
    } else if (timerRef.current) {
      clearInterval(timerRef.current);
    }

    return () => {
      if (timerRef.current) clearInterval(timerRef.current);
    };
  }, [isPlaying, messages.length]);

  const visibleMessages = messages.slice(0, visibleCount);
  const isSimulationInProgress = visibleCount < messages.length || isPlaying;

  return (
    <div className={cn("flex flex-col h-full space-y-4 text-slate-800 font-sans dark:text-slate-100", className)}>
      {/* NÚT BÀN CỜ TỰ ĐỘNG PHÁT LẠI */}
      <div className="p-3.5 md:p-4 rounded-2xl bg-background border border-border/90 shadow-2xs flex flex-col sm:flex-row sm:items-center justify-between gap-3 sticky top-0 z-20">
        <div className="flex items-center gap-2.5">
          <div className="p-2 rounded-xl bg-card border border-border text-sky-600 shadow-2xs">
            <Activity className="w-5 h-5 animate-pulse stroke-[2.5]" />
          </div>
          <div>
            <h3 className="text-sm font-extrabold text-foreground flex items-center gap-1.5">
              <span>Trình Tái Hiện Ký Ức Hỏi-Đáp</span>
              <span className="px-2 py-0.5 rounded-full text-[10px] font-black bg-card text-slate-600 border border-border shadow-2xs dark:text-slate-300">
                READ-ONLY MODE
              </span>
            </h3>
            <p className="text-xs text-muted-foreground font-medium">
              Hiển thị {visibleCount} / {messages.length} tin nhắn trong bản ghi
            </p>
          </div>
        </div>

        <div className="flex items-center gap-2 shrink-0">
          {!isSimulationInProgress ? (
            <button
              type="button"
              onClick={startSimulation}
              className="px-4 py-2 rounded-xl bg-sky-600 hover:bg-sky-700 text-white font-bold text-xs shadow-2xs transition-all duration-200 flex items-center gap-2 hover:scale-[1.01] active:scale-[0.99] cursor-pointer"
            >
              <Play className="w-4 h-4 fill-current text-white" />
              <span>Tự động phát lại ca khám</span>
            </button>
          ) : (
            <div className="flex items-center gap-2 bg-card p-1 rounded-xl border border-border shadow-2xs">
              <button
                type="button"
                onClick={togglePlayPause}
                className={cn(
                  "px-3 py-1.5 rounded-lg text-xs font-extrabold transition-all flex items-center gap-1.5 shadow-2xs cursor-pointer",
                  isPlaying ? "bg-amber-500 hover:bg-amber-600 text-white" : "bg-emerald-600 hover:bg-emerald-700 text-white"
                )}
              >
                {isPlaying ? <Pause className="w-3.5 h-3.5 fill-current" /> : <Play className="w-3.5 h-3.5 fill-current" />}
                <span>{isPlaying ? "Tạm Dừng" : "Tiếp Tục Phát"}</span>
              </button>

              <button
                type="button"
                onClick={startSimulation}
                className="p-1.5 rounded-lg bg-background hover:bg-muted text-slate-700 border border-border text-xs transition-colors cursor-pointer dark:text-slate-200"
                title="Phát lại từ đầu"
              >
                <RotateCcw className="w-3.5 h-3.5 stroke-[2.5]" />
              </button>

              <button
                type="button"
                onClick={showAllImmediately}
                className="px-2.5 py-1.5 rounded-lg bg-background hover:bg-muted text-sky-700 border border-border text-[11px] font-extrabold transition-colors flex items-center gap-1 cursor-pointer"
                title="Hiển thị ngay toàn bộ hội thoại"
              >
                <FastForward className="w-3.5 h-3.5 stroke-[2.5]" />
                <span>Mở toàn bộ</span>
              </button>
            </div>
          )}
        </div>
      </div>

      {/* CỘT KÝ ỨC HỘI THOẠI */}
      <div className="flex-1 overflow-y-auto space-y-6 px-2 py-4">
        {messages.length === 0 ? (
          <div className="p-12 text-center text-slate-400 italic text-sm font-semibold">
            Ca khám này không có lịch sử ghi chép tin nhắn hội thoại hoặc được chuyển tiếp trực tiếp sang cấp cứu 115.
          </div>
        ) : (
          <AnimatePresence mode="popLayout">
            {visibleMessages.map((msg) => {
              const isBot = msg.sender === "bot";
              const isUser = msg.sender === "user";
              const isSystem = msg.sender === "system_shield";

              if (isSystem) {
                return (
                  <motion.div
                    key={msg.id}
                    initial={{ opacity: 0, y: 15, scale: 0.95 }}
                    animate={{ opacity: 1, y: 0, scale: 1 }}
                    exit={{ opacity: 0, scale: 0.9 }}
                    transition={{ duration: 0.35, ease: "easeOut" }}
                    className="flex justify-center my-6 px-2"
                  >
                    <div className="bg-rose-50 border-2 border-rose-400 text-slate-800 p-5 rounded-3xl shadow-sm max-w-2xl w-full text-left space-y-2.5">
                      <div className="flex items-center gap-2 font-black text-rose-900 text-sm md:text-base uppercase tracking-tight">
                        <AlertTriangle className="w-6 h-6 text-rose-600 shrink-0 animate-bounce stroke-[2.5]" />
                        <span>Ký Ức Rào Chắn Lâm Sàng &amp; Báo Động Đỏ</span>
                      </div>
                      <ClinicalMarkdown
                        content={msg.content}
                        className="border-l-2 border-rose-500 pl-8 text-sm font-bold leading-relaxed text-foreground md:text-base"
                      />
                      <div className="flex items-center justify-between pt-2 border-t border-rose-200 text-[11px] font-mono text-slate-600 dark:text-slate-300">
                        <span className="font-bold">Thời điểm thẩm định: {new Date(msg.timestamp).toLocaleTimeString("vi-VN")}</span>
                        <span className="font-black text-rose-700">Đã kích hoạt chặn an toàn</span>
                      </div>
                    </div>
                  </motion.div>
                );
              }

              return (
                <motion.div
                  key={msg.id}
                  initial={{ opacity: 0, y: 20, scale: 0.96 }}
                  animate={{ opacity: 1, y: 0, scale: 1 }}
                  transition={{ duration: 0.35, ease: "easeOut" }}
                  className={cn("flex gap-3 sm:gap-4 w-full", {
                    "justify-end": isUser,
                    "justify-start": isBot,
                  })}
                >
                  {isBot && (
                    <div className="shrink-0 flex flex-col items-center">
                      <div className="p-2.5 rounded-2xl bg-sky-50 border border-sky-200 text-sky-600 shadow-2xs">
                        <Bot className="w-5 h-5 animate-pulse stroke-[2.5]" />
                      </div>
                      <span className="text-[10px] font-mono font-bold text-slate-400 mt-1 uppercase tracking-tight">
                        AI Triage
                      </span>
                    </div>
                  )}

                  <div
                    className={cn("flex flex-col transition-colors duration-300", {
                      "max-w-xl bg-sky-600 text-white rounded-3xl rounded-tr-xs p-4 sm:p-5 shadow-sm text-sm leading-relaxed font-semibold":
                        isUser,

                      "max-w-2xl bg-card border border-border/90 text-slate-800 rounded-3xl rounded-tl-xs p-4 sm:p-6 shadow-sm space-y-4 dark:text-slate-100":
                        isBot,
                    })}
                  >
                    <div className="flex items-center justify-between text-[11px] opacity-80 gap-4 pb-2 border-b border-slate-100">
                      <span className="font-black uppercase tracking-wider text-xs">
                        {isUser
                          ? "Bệnh nhân khai báo"
                          : msg.workflowPhase
                            ? `DeepAgent • ${msg.workflowPhase.replaceAll("_", " ")}`
                            : "DeepAgent"}
                      </span>
                      <span className="font-mono font-bold">
                        {new Date(msg.timestamp).toLocaleTimeString("vi-VN", {
                          hour: "2-digit",
                          minute: "2-digit",
                          second: "2-digit",
                        })}
                      </span>
                    </div>

                    {isBot ? (
                      <ClinicalMarkdown
                        content={msg.content}
                        className="text-sm font-normal leading-relaxed md:text-base"
                      />
                    ) : (
                      <p className="whitespace-pre-wrap text-sm font-normal leading-relaxed md:text-base">
                        {msg.content}
                      </p>
                    )}

                    {msg.structured && <ReadOnlyStructuredPayload payload={msg.structured} />}
                    {isBot && (
                      <EvidenceSources
                        citations={msg.ragCitations}
                        caseSupport={msg.caseSupport}
                        decisionStatus={msg.decisionStatus}
                        evidenceStatus={msg.evidenceStatus}
                        retrievalDegradedModes={msg.retrievalDegradedModes}
                      />
                    )}
                  </div>

                  {isUser && (
                    <div className="shrink-0 flex flex-col items-center">
                      <div className="p-2.5 rounded-2xl bg-muted border border-border text-slate-700 shadow-2xs dark:text-slate-200">
                        <User className="w-5 h-5 stroke-[2.5]" />
                      </div>
                      <span className="text-[10px] font-mono text-slate-400 mt-1 uppercase font-bold tracking-tight">
                        Bệnh Nhân
                      </span>
                    </div>
                  )}
                </motion.div>
              );
            })}
          </AnimatePresence>
        )}

        {isPlaying && (
          <div className="flex items-center justify-center gap-2 py-4 text-sky-700 font-mono text-xs font-bold animate-pulse">
            <span className="w-2 h-2 rounded-full bg-sky-600 animate-ping" />
            <span>Đang phát lại tin nhắn tiếp theo...</span>
          </div>
        )}
      </div>

      {/* THANH TƯỜNG LỬA BẢO TỒN KÝ ỨC */}
      <div className="pt-2 shrink-0">
        <div className="bg-background border border-border py-3.5 px-5 rounded-2xl text-xs sm:text-sm text-slate-700 flex flex-col sm:flex-row items-center justify-center gap-2.5 shadow-2xs text-center sm:text-left select-none font-sans dark:text-slate-200">
          <div className="p-2 rounded-xl bg-card border border-border text-slate-600 shrink-0 shadow-2xs dark:text-slate-300">
            <Lock className="w-5 h-5 stroke-[2.5]" />
          </div>
          <div>
            <p className="font-extrabold text-foreground tracking-tight uppercase">
              Bản ghi hội thoại chỉ đọc
            </p>
            <p className="text-xs text-muted-foreground font-medium mt-0.5">
              Nội dung được tải lại từ hồ sơ ca khám và không thể chỉnh sửa tại màn hình này.
            </p>
          </div>
        </div>
      </div>
    </div>
  );
};

export default ConversationReplayFeed;
