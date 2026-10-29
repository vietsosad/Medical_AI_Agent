"use client";

import React, { useCallback, useEffect, useRef, useState } from "react";
import { Lock, Pause, Play, RotateCcw, ScrollText } from "lucide-react";

import { MessageItem } from "@/components/chat/MessageItem";
import type { ChatMessage } from "@/types/triage-chat";

/**
 * Auto-replay animation for one pilot session's transcript, on
 * `/triage-pilot/history/[id]`. Forked from production's
 * `ConversationReplayFeed.tsx` for the *reveal-timer + control-button*
 * mechanism only (same `visibleCount` + `setInterval` @1500ms approach,
 * same 4 controls, same read-only notice) -- but renders each revealed
 * message via `MessageItem` (already used for every pilot chat message,
 * live or replayed, and already handles bot/user/system_shield/markdown on
 * its own, including its own rise-in animation) instead of hand-rolling
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

const SECONDARY_BUTTON =
  "flex min-h-11 items-center gap-2 rounded-xl border border-border bg-card px-4 text-sm font-semibold text-foreground transition duration-[180ms] hover:bg-muted focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand focus-visible:ring-offset-2 focus-visible:ring-offset-background active:scale-[0.97] motion-reduce:transition-none motion-reduce:active:scale-100";

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
  const isShowingAll = visibleCount === messages.length && !isPlaying;

  return (
    <section aria-labelledby="replay-heading" className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div className="flex flex-wrap items-center gap-2">
          <h2 id="replay-heading" className="text-lg font-bold text-foreground">
            Hội thoại
          </h2>
          <span className="inline-flex items-center gap-2 rounded-full border border-border bg-muted px-2 text-sm font-semibold leading-6 text-slate-700 dark:text-slate-300">
            <Lock className="size-4" aria-hidden="true" />
            Chỉ đọc
          </span>
        </div>

        {isShowingAll ? (
          <button
            type="button"
            onClick={startSimulation}
            disabled={messages.length === 0}
            className="flex min-h-11 items-center gap-2 rounded-xl bg-brand px-4 text-sm font-bold text-brand-foreground transition duration-[180ms] hover:bg-brand-strong focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand focus-visible:ring-offset-2 focus-visible:ring-offset-background active:scale-[0.97] disabled:cursor-not-allowed disabled:opacity-50 motion-reduce:transition-none motion-reduce:active:scale-100"
          >
            <Play className="size-4" aria-hidden="true" />
            Tự động phát lại
          </button>
        ) : (
          <div className="flex flex-wrap items-center gap-2">
            <button type="button" onClick={togglePlayPause} className={SECONDARY_BUTTON}>
              {isPlaying ? <Pause className="size-4" aria-hidden="true" /> : <Play className="size-4" aria-hidden="true" />}
              {isPlaying ? "Tạm dừng" : "Tiếp tục"}
            </button>
            <button type="button" onClick={startSimulation} className={SECONDARY_BUTTON}>
              <RotateCcw className="size-4" aria-hidden="true" />
              Phát lại từ đầu
            </button>
            <button type="button" onClick={showAllImmediately} className={SECONDARY_BUTTON}>
              <ScrollText className="size-4" aria-hidden="true" />
              Mở toàn bộ
            </button>
          </div>
        )}
      </div>

      {messages.length === 0 ? (
        <p className="rounded-2xl border border-dashed border-border bg-card p-4 text-sm leading-6 text-muted-foreground">
          Phiên này chưa có tin nhắn nào được lưu.
        </p>
      ) : (
        // Khi đang phát lại, trình đọc màn hình đọc từng tin vừa hiện ra.
        <div aria-live={isPlaying ? "polite" : "off"}>
          {visibleMessages.map((message) => (
            <MessageItem key={message.id} message={message} onSelectAnswer={noopSelectAnswer} disabled />
          ))}
        </div>
      )}

      <p className="rounded-2xl border border-border bg-muted/60 p-4 text-sm leading-6 text-muted-foreground">
        Bản ghi hội thoại chỉ đọc: nội dung được tải lại từ hồ sơ phiên và không thể chỉnh sửa tại màn hình này.
      </p>
    </section>
  );
}
