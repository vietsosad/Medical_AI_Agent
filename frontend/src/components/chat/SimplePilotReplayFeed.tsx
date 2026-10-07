"use client";

import React, { useCallback, useEffect, useRef, useState } from "react";
import { History, Pause, Play, RotateCcw, ScrollText } from "lucide-react";

import { MessageItem } from "@/components/chat/MessageItem";
import type { ChatMessage } from "@/types/triage-chat";

/**
 * Auto-replay animation for one pilot session's transcript, on
 * `/triage-pilot/history/[id]`. Forked from production's
 * `ConversationReplayFeed.tsx` for the *reveal-timer + control-button*
 * mechanism only (same `visibleCount` + `setInterval` @1500ms approach,
 * same 4 controls, same "READ-ONLY MODE" pill/lock banner) -- but renders
 * each revealed message via `MessageItem` (already used for every pilot
 * chat message, live or replayed, and already handles bot/user/
 * system_shield/markdown on its own) instead of hand-rolling
 * `ClinicalMarkdown`/`EvidenceSources`/`ReadOnlyStructuredPayload` the way
 * the production version does -- simple_agent has no structured option
 * cards or RAG-citation objects to replay, so none of that machinery is
 * needed here.
 */

const REVEAL_INTERVAL_MS = 1500;

export interface SimplePilotReplayFeedProps {
  messages: ChatMessage[];
}

function noopSelectAnswer() {}

export function SimplePilotReplayFeed({ messages }: SimplePilotReplayFeedProps) {
  const [isPlaying, setIsPlaying] = useState(false);
  const [visibleCount, setVisibleCount] = useState(messages.length);
  const timerRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const startSimulation = useCallback(() => {
    if (timerRef.current) clearInterval(timerRef.current);
    setVisibleCount(messages.length > 0 ? 1 : 0);
    setIsPlaying(true);
  }, [messages.length]);

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
          if (prev < messages.length) return prev + 1;
          setIsPlaying(false);
          if (timerRef.current) clearInterval(timerRef.current);
          return prev;
        });
      }, REVEAL_INTERVAL_MS);
    } else if (timerRef.current) {
      clearInterval(timerRef.current);
    }
    return () => {
      if (timerRef.current) clearInterval(timerRef.current);
    };
  }, [isPlaying, messages.length]);

  const visibleMessages = messages.slice(0, visibleCount);

  return (
    <section className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-3 rounded-2xl border border-border bg-card p-4">
        <span className="flex items-center gap-2 text-sm font-bold text-slate-800 dark:text-slate-100">
          <History className="size-4 text-sky-700" aria-hidden="true" />
          Trình tái hiện hội thoại
          <span className="rounded-full border border-slate-300 bg-muted px-2 py-0.5 text-[11px] font-bold uppercase tracking-wide text-slate-600 dark:text-slate-300 dark:border-slate-700">
            Read-only mode
          </span>
        </span>

        {visibleCount === messages.length && !isPlaying ? (
          <button
            type="button"
            onClick={startSimulation}
            disabled={messages.length === 0}
            className="flex min-h-9 items-center gap-2 rounded-lg bg-sky-700 px-3 text-sm font-semibold text-white transition-colors hover:bg-sky-800 disabled:cursor-not-allowed disabled:opacity-60"
          >
            <Play className="size-4" aria-hidden="true" />
            Tự động phát lại ca khám
          </button>
        ) : (
          <div className="flex flex-wrap items-center gap-2">
            <button
              type="button"
              onClick={togglePlayPause}
              className="flex min-h-9 items-center gap-2 rounded-lg border border-slate-300 bg-card px-3 text-sm font-semibold text-slate-800 hover:bg-muted dark:text-slate-100 dark:border-slate-700"
            >
              {isPlaying ? <Pause className="size-4" aria-hidden="true" /> : <Play className="size-4" aria-hidden="true" />}
              {isPlaying ? "Tạm dừng" : "Tiếp tục"}
            </button>
            <button
              type="button"
              onClick={startSimulation}
              className="flex min-h-9 items-center gap-2 rounded-lg border border-slate-300 bg-card px-3 text-sm font-semibold text-slate-800 hover:bg-muted dark:text-slate-100 dark:border-slate-700"
            >
              <RotateCcw className="size-4" aria-hidden="true" />
              Phát lại từ đầu
            </button>
            <button
              type="button"
              onClick={showAllImmediately}
              className="flex min-h-9 items-center gap-2 rounded-lg border border-slate-300 bg-card px-3 text-sm font-semibold text-slate-800 hover:bg-muted dark:text-slate-100 dark:border-slate-700"
            >
              <ScrollText className="size-4" aria-hidden="true" />
              Mở toàn bộ
            </button>
          </div>
        )}
      </div>

      <div>
        {visibleMessages.map((message) => (
          <MessageItem key={message.id} message={message} onSelectAnswer={noopSelectAnswer} disabled />
        ))}
      </div>

      <div className="rounded-xl border border-border bg-background p-3 text-center text-xs font-semibold text-muted-foreground">
        Bản ghi hội thoại chỉ đọc — nội dung được tải lại từ hồ sơ ca khám và không thể chỉnh sửa tại
        màn hình này.
      </div>
    </section>
  );
}
