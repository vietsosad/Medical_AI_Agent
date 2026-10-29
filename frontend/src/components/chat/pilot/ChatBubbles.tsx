"use client";

import { motion } from "framer-motion";
import { Activity, AlertCircle, AlertTriangle, ShieldAlert } from "lucide-react";

import { riseVariants } from "@/lib/motion";
import { cn } from "@/lib/utils";

import type { SafetyNotice } from "./pilot-transcript";

/**
 * Bong bóng hội thoại của màn sàng lọc. Mỗi dòng nổi lên 8 px khi được thêm;
 * những dòng đã có sẵn lúc mở phiên thì không diễn hoạt (danh sách cha bọc
 * `AnimatePresence initial={false}`).
 */

export function AgentAvatar({ className }: { className?: string }) {
  return (
    <span
      aria-hidden="true"
      className={cn("flex size-10 shrink-0 items-center justify-center rounded-xl bg-brand-soft text-brand", className)}
    >
      <Activity className="size-5" strokeWidth={2.2} />
    </span>
  );
}

const bubbleText = "whitespace-pre-line text-pretty text-base leading-7";

export function PatientBubble({
  content,
  state = "sent",
}: {
  content: string;
  state?: "sent" | "sending" | "failed";
}) {
  return (
    <motion.li variants={riseVariants} initial="hidden" animate="visible" className="flex justify-end">
      <div className="flex max-w-[85%] flex-col items-end gap-2 sm:max-w-[75%]">
        <p
          className={cn(
            bubbleText,
            "rounded-2xl rounded-tr-md px-4 py-2 transition-opacity duration-200",
            state === "failed"
              ? "border border-dashed border-slate-400 bg-card text-foreground dark:border-slate-500"
              : "bg-brand text-brand-foreground",
            state === "sending" && "opacity-80",
          )}
        >
          {content}
        </p>
        {state === "sending" && <span className="text-sm text-muted-foreground">Đang gửi…</span>}
        {state === "failed" && (
          <span className="flex items-center gap-2 text-sm font-semibold text-amber-700 dark:text-amber-400">
            <AlertCircle className="size-4" aria-hidden="true" />
            Chưa gửi được
          </span>
        )}
      </div>
    </motion.li>
  );
}

export function AgentBubble({
  content,
  guarded = false,
  safety = null,
  children,
}: {
  content: string;
  guarded?: boolean;
  safety?: SafetyNotice | null;
  /** Nút trả lời nhanh, chỉ gắn vào câu hỏi cuối cùng đang chờ. */
  children?: React.ReactNode;
}) {
  return (
    <motion.li variants={riseVariants} initial="hidden" animate="visible" className="flex items-start gap-2 sm:gap-4">
      <AgentAvatar />
      <div className="flex min-w-0 max-w-[85%] flex-col gap-2 sm:max-w-[75%]">
        {safety && <SafetyNoticeCard notice={safety} />}
        {content && (
          <p
            className={cn(
              bubbleText,
              "rounded-2xl rounded-tl-md px-4 py-2",
              guarded
                ? "border border-amber-200 bg-amber-50 text-amber-950 dark:border-amber-800 dark:bg-amber-950/40 dark:text-amber-100"
                : "bg-muted text-foreground",
            )}
          >
            {guarded && <ShieldAlert className="mr-2 inline size-4 align-[-2px]" aria-hidden="true" />}
            {content}
          </p>
        )}
        {children}
      </div>
    </motion.li>
  );
}

/**
 * Câu hướng dẫn cố định của bộ sàng lọc cấp cứu, tách khỏi câu trả lời của trợ
 * lý để không bị đọc lướt như một tin nhắn thường. Nút gọi 115 nằm ở thanh
 * ghim ngay trên ô nhập (luôn trong tầm mắt), không lặp lại ở đây.
 */
function SafetyNoticeCard({ notice }: { notice: SafetyNotice }) {
  return (
    <section className="rounded-2xl border border-rose-300 bg-rose-50 p-4 text-rose-950 dark:border-rose-800 dark:bg-rose-950/40 dark:text-rose-100">
      <h3 className="flex items-center gap-2 text-base font-bold">
        <AlertTriangle className="size-5 shrink-0 text-rose-700 dark:text-rose-300" aria-hidden="true" />
        Lưu ý an toàn
      </h3>
      <p className="mt-2 text-base leading-7">{notice.text}</p>
    </section>
  );
}
