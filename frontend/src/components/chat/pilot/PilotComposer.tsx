"use client";

import { useEffect, useImperativeHandle, useRef, useState } from "react";
import { AnimatePresence, motion } from "framer-motion";
import { AudioLines, LoaderCircle, Mic, SendHorizontal } from "lucide-react";

import { useSpeechDictation } from "@/hooks/useSpeechDictation";
import { DURATION, EASE_OUT } from "@/lib/motion";
import { cn } from "@/lib/utils";

export interface PilotComposerHandle {
  focus: () => void;
}

interface PilotComposerProps {
  onSend: (content: string) => void;
  disabled?: boolean;
  isProcessing?: boolean;
  placeholder?: string;
  ref?: React.Ref<PilotComposerHandle>;
}

/**
 * Ô nhập của màn sàng lọc: gõ, hoặc bấm micro để nói tiếng Việt. Enter để gửi,
 * Shift+Enter để xuống dòng. Nút trả lời nhanh chỉ là lối tắt -- ô này luôn mở
 * cho người muốn kể chi tiết hơn.
 */
export function PilotComposer({
  onSend,
  disabled = false,
  isProcessing = false,
  placeholder = "Hoặc gõ câu trả lời của bạn…",
  ref,
}: PilotComposerProps) {
  const [text, setText] = useState("");
  const textareaRef = useRef<HTMLTextAreaElement | null>(null);
  const blocked = disabled || isProcessing;
  const dictation = useSpeechDictation({ text, onTextChange: setText, disabled: blocked });

  useImperativeHandle(ref, () => ({ focus: () => textareaRef.current?.focus() }), []);

  // Ô cao dần theo nội dung, tối đa khoảng 6 dòng rồi mới cuộn.
  useEffect(() => {
    const textarea = textareaRef.current;
    if (!textarea) return;
    textarea.style.height = "auto";
    textarea.style.height = `${Math.min(textarea.scrollHeight, 168)}px`;
  }, [text]);

  const canSend = !blocked && text.trim().length > 0;

  const submit = (event?: React.FormEvent) => {
    event?.preventDefault();
    if (!canSend) return;
    if (dictation.isRecording) dictation.stop();
    onSend(text.trim());
    setText("");
  };

  const handleKeyDown = (event: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (event.key !== "Enter" || event.shiftKey || event.nativeEvent.isComposing) return;
    event.preventDefault();
    submit();
  };

  return (
    <form onSubmit={submit} aria-busy={isProcessing} className="px-4 pb-4 pt-2 sm:px-6">
      <div
        className={cn(
          "flex items-end gap-2 rounded-2xl border bg-card py-2 pl-4 pr-2 transition-[border-color,box-shadow] duration-200",
          dictation.isRecording
            ? "border-rose-400 shadow-[0_0_0_4px_rgb(244_63_94_/_0.15)]"
            : "border-border focus-within:border-brand focus-within:shadow-[0_0_0_4px_var(--brand-soft)]",
        )}
      >
        <label htmlFor="pilot-chat-input" className="sr-only">
          Câu trả lời của bạn
        </label>
        <textarea
          ref={textareaRef}
          id="pilot-chat-input"
          name="triage_message"
          rows={1}
          autoComplete="off"
          value={text}
          disabled={blocked}
          onChange={(event) => setText(event.target.value)}
          onKeyDown={handleKeyDown}
          placeholder={
            isProcessing ? "Trợ lý đang trả lời…" : dictation.isRecording ? "Đang nghe bạn nói…" : placeholder
          }
          className="max-h-42 min-h-11 flex-1 resize-none bg-transparent py-2 text-base leading-7 text-foreground outline-none placeholder:text-muted-foreground disabled:cursor-not-allowed"
        />
        <button
          type="button"
          onClick={dictation.toggle}
          disabled={blocked}
          aria-pressed={dictation.isRecording}
          aria-label={dictation.isRecording ? "Dừng nói" : "Nói thay vì gõ"}
          className={cn(
            "flex size-11 shrink-0 items-center justify-center rounded-xl transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand disabled:cursor-not-allowed disabled:opacity-50",
            dictation.isRecording
              ? "bg-rose-100 text-rose-700 dark:bg-rose-950 dark:text-rose-300"
              : "bg-muted text-muted-foreground hover:text-foreground",
          )}
        >
          {dictation.isRecording ? (
            <AudioLines className="size-5 animate-pulse" aria-hidden="true" />
          ) : (
            <Mic className="size-5" aria-hidden="true" />
          )}
        </button>
        <motion.button
          type="submit"
          disabled={!canSend}
          whileTap={canSend ? { scale: 0.97 } : undefined}
          aria-label="Gửi câu trả lời"
          className={cn(
            "flex size-11 shrink-0 items-center justify-center rounded-xl transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand focus-visible:ring-offset-2 focus-visible:ring-offset-card",
            canSend ? "bg-brand text-brand-foreground hover:bg-brand-strong" : "bg-muted text-muted-foreground",
          )}
        >
          <AnimatePresence mode="wait" initial={false}>
            <motion.span
              key={isProcessing ? "busy" : "send"}
              initial={{ opacity: 0, scale: 0.8 }}
              animate={{ opacity: 1, scale: 1 }}
              exit={{ opacity: 0, scale: 0.8 }}
              transition={{ duration: DURATION.quick, ease: EASE_OUT }}
              className="flex"
            >
              {isProcessing ? (
                <LoaderCircle className="size-5 animate-spin" aria-hidden="true" />
              ) : (
                <SendHorizontal className="size-5" aria-hidden="true" />
              )}
            </motion.span>
          </AnimatePresence>
        </motion.button>
      </div>
      <p className="mt-2 text-sm leading-6 text-muted-foreground">
        Kết quả chỉ là gợi ý sơ bộ, luôn được nhân viên y tế xem lại. Không thay thế thăm khám trực tiếp.
      </p>
    </form>
  );
}
