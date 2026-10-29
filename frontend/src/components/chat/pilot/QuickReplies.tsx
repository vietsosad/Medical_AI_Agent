"use client";

import { useState } from "react";
import { motion } from "framer-motion";

import { DURATION, EASE_OUT, STAGGER_SECONDS } from "@/lib/motion";
import { cn } from "@/lib/utils";

import type { QuickReplyKind } from "./pilot-transcript";

/**
 * Lối tắt cho câu hỏi đang chờ. Mỗi nút gửi đúng câu người bệnh có thể tự gõ
 * ("Có", "Không rõ", "7/10"), nên trợ lý hiểu nó như mọi câu trả lời khác --
 * ô nhập vẫn luôn mở cho ai muốn kể chi tiết hơn.
 */

const container = {
  hidden: {},
  visible: { transition: { staggerChildren: STAGGER_SECONDS, delayChildren: 0.12 } },
};

const chip = {
  hidden: { opacity: 0, y: 6 },
  visible: { opacity: 1, y: 0, transition: { duration: DURATION.base, ease: EASE_OUT } },
};

const SCALE = [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10] as const;

interface QuickRepliesProps {
  kind: QuickReplyKind;
  questionTargetId: string | null;
  disabled: boolean;
  onReply: (text: string) => void;
  /** "Tôi muốn bổ sung": chỉ đưa con trỏ về ô nhập, không gửi lượt rỗng. */
  onWantToAdd: () => void;
}

export function QuickReplies({ kind, questionTargetId, disabled, onReply, onWantToAdd }: QuickRepliesProps) {
  const [chosen, setChosen] = useState<string | null>(null);

  const reply = (text: string) => {
    if (disabled) return;
    setChosen(text);
    onReply(text);
  };

  if (kind === "SCALE_0_10") {
    const isPain = questionTargetId?.includes("pain") ?? false;
    return (
      <motion.fieldset
        variants={container}
        initial="hidden"
        animate="visible"
        className="m-0 rounded-2xl border border-border bg-card p-4"
      >
        <legend className="px-2 text-sm font-semibold text-muted-foreground">
          {isPain ? "Chọn nhanh mức đau" : "Chọn nhanh mức độ"}
        </legend>
        <div className="grid grid-cols-6 gap-2 sm:grid-cols-11">
          {SCALE.map((value) => {
            const text = `${value}/10`;
            return (
              <motion.button
                key={value}
                type="button"
                variants={chip}
                whileTap={{ scale: 0.97 }}
                disabled={disabled}
                aria-pressed={chosen === text}
                aria-label={`Mức ${value} trên 10`}
                onClick={() => reply(text)}
                className={cn(
                  "min-h-11 rounded-xl border text-base font-semibold transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand focus-visible:ring-offset-2 focus-visible:ring-offset-card disabled:cursor-not-allowed",
                  chosen === text
                    ? "border-2 border-brand bg-brand-soft font-bold text-brand-ink"
                    : "border-border bg-background text-foreground hover:border-brand-edge hover:bg-brand-soft disabled:opacity-60",
                )}
              >
                {value}
              </motion.button>
            );
          })}
        </div>
        <div className="mt-2 flex justify-between gap-4 whitespace-nowrap text-sm text-muted-foreground">
          <span>{isPain ? "0 · Không đau" : "0 · Không có"}</span>
          <span className="text-right">
            10 · {isPain ? "Đau nhất" : "Nặng nhất"}
            {isPain && <span className="hidden sm:inline"> từng gặp</span>}
          </span>
        </div>
      </motion.fieldset>
    );
  }

  const options: Array<{ label: string; send: string | null; tone: "brand" | "plain" }> =
    kind === "CONFIRM"
      ? [
          { label: "Đúng rồi, đánh giá giúp tôi", send: "Thông tin đã đúng, bạn đánh giá giúp tôi.", tone: "brand" },
          { label: "Tôi muốn bổ sung", send: null, tone: "plain" },
        ]
      : [
          { label: "Có", send: "Có", tone: "brand" },
          { label: "Không", send: "Không", tone: "brand" },
          { label: "Không rõ", send: "Không rõ", tone: "plain" },
        ];

  return (
    <motion.div
      role="group"
      aria-label="Trả lời nhanh"
      variants={container}
      initial="hidden"
      animate="visible"
      className="flex flex-wrap gap-2"
    >
      {options.map((option) => (
        <motion.button
          key={option.label}
          type="button"
          variants={chip}
          whileTap={{ scale: 0.97 }}
          disabled={disabled}
          aria-pressed={option.send !== null ? chosen === option.send : undefined}
          onClick={() => (option.send === null ? onWantToAdd() : reply(option.send))}
          className={cn(
            "min-h-11 rounded-full border px-6 text-base font-semibold transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand focus-visible:ring-offset-2 focus-visible:ring-offset-background disabled:cursor-not-allowed disabled:opacity-60",
            chosen !== null && chosen === option.send
              ? "border-brand bg-brand text-brand-foreground"
              : option.tone === "brand"
                ? "border-brand-edge bg-brand-soft text-brand-ink hover:border-brand"
                : "border-border bg-card text-foreground hover:bg-muted",
          )}
        >
          {option.label}
        </motion.button>
      ))}
    </motion.div>
  );
}
