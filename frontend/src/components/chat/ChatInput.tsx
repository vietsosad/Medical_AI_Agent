"use client";

import React, { useState, useRef, useEffect } from "react";
import { useTriageStore } from "@/store/useTriageStore";
import { AudioLines, LoaderCircle, Lock, Mic, Send, ShieldCheck } from "lucide-react";
import { cn } from "@/lib/utils";
import { toast } from "sonner";

interface SpeechRecognitionErrorEvent extends Event {
  error: string;
  message?: string;
}

interface SpeechRecognitionEvent extends Event {
  resultIndex: number;
  results: SpeechRecognitionResultList;
}

interface ISpeechRecognition extends EventTarget {
  continuous: boolean;
  interimResults: boolean;
  lang: string;
  maxAlternatives: number;
  start: () => void;
  stop: () => void;
  abort: () => void;
  onstart: ((this: ISpeechRecognition, ev: Event) => void) | null;
  onresult: ((this: ISpeechRecognition, ev: SpeechRecognitionEvent) => void) | null;
  onerror: ((this: ISpeechRecognition, ev: SpeechRecognitionErrorEvent) => void) | null;
  onend: ((this: ISpeechRecognition, ev: Event) => void) | null;
}

interface WindowWithSpeech extends Window {
  SpeechRecognition?: new () => ISpeechRecognition;
  webkitSpeechRecognition?: new () => ISpeechRecognition;
}

interface ChatInputProps {
  onSendMessage: (content: string) => void;
  placeholder?: string;
  isProcessing?: boolean;
  disabled?: boolean;
}

const SPEECH_SILENCE_TIMEOUT_MS = 8_000;

function joinSpeechText(...parts: string[]): string {
  return parts
    .map((part) => part.trim())
    .filter(Boolean)
    .join(" ")
    .replace(/\s+([,.!?;:])/g, "$1")
    .replace(/\s+/g, " ")
    .trim();
}

/**
 * ============================================================================
 * [CHAT INPUT & ZERO-DIAGNOSIS SHIELD] KHUNG NHẬP LIỆU & TƯỜNG LỬA CHỐNG BỊA - G3
 * ============================================================================
 * Chuẩn Hiến pháp UI:
 * - Touch Targets >= 44px: Nút gửi min-h-[52px], ô nhập py-3.5.
 * - Readability over decoration: Phông chữ tối thiểu text-base (16px), không gây giật cúp hay khó đọc.
 * - Clinical Trust Blue Focus State: focus:border-sky-500 focus:ring-2 focus:ring-sky-600/20.
 * - Native Web Speech API STT (vi-VN): Nhận diện giọng nói Tiếng Việt thời gian thực.
 */
export function ChatInput({
  onSendMessage,
  placeholder = "Mô tả triệu chứng của bạn hoặc trả lời câu hỏi của trợ lý...",
  isProcessing = false,
  disabled = false,
}: ChatInputProps) {
  const { isChatLocked, redFlagTriggered } = useTriageStore();
  const [inputText, setInputText] = useState("");
  const [isRecording, setIsRecording] = useState(false);
  const textareaRef = useRef<HTMLTextAreaElement | null>(null);
  const recognitionRef = useRef<ISpeechRecognition | null>(null);
  const speechBaseTextRef = useRef("");
  const finalTranscriptRef = useRef("");
  const silenceTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  // Stop active speech recognition on unmount
  useEffect(() => {
    return () => {
      if (silenceTimeoutRef.current) {
        clearTimeout(silenceTimeoutRef.current);
      }
      if (recognitionRef.current) {
        try {
          recognitionRef.current.stop();
        } catch {
          // Ignore cleanup errors
        }
      }
    };
  }, []);

  useEffect(() => {
    const textarea = textareaRef.current;
    if (!textarea) return;

    textarea.style.height = "auto";
    textarea.style.height = `${Math.min(textarea.scrollHeight, 160)}px`;
  }, [inputText]);

  const resetSilenceTimeout = (recognition: ISpeechRecognition) => {
    if (silenceTimeoutRef.current) {
      clearTimeout(silenceTimeoutRef.current);
    }

    silenceTimeoutRef.current = setTimeout(() => {
      if (recognitionRef.current !== recognition) return;

      try {
        recognition.stop();
        toast.info("Đã tự dừng sau 8 giây không phát hiện giọng nói.");
      } catch {
        // The browser may already have stopped recognition.
      }
    }, SPEECH_SILENCE_TIMEOUT_MS);
  };

  const handleSubmit = (e?: React.FormEvent) => {
    if (e) e.preventDefault();
    if (disabled || isChatLocked || isProcessing) return;
    if (!inputText.trim()) return;

    if (isRecording && recognitionRef.current) {
      if (silenceTimeoutRef.current) {
        clearTimeout(silenceTimeoutRef.current);
      }
      try {
        recognitionRef.current.stop();
      } catch {
        // Ignore stop error
      }
      setIsRecording(false);
    }

    onSendMessage(inputText.trim());
    setInputText("");
  };

  const handleKeyDown = (event: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (event.key !== "Enter" || event.shiftKey || event.nativeEvent.isComposing) return;

    event.preventDefault();
    handleSubmit();
  };

  const toggleVoiceRecording = () => {
    if (disabled || isChatLocked || isProcessing) return;

    // If currently recording, stop it
    if (isRecording) {
      if (silenceTimeoutRef.current) {
        clearTimeout(silenceTimeoutRef.current);
      }
      if (recognitionRef.current) {
        try {
          recognitionRef.current.stop();
        } catch {
          // Ignore error on stop
        }
      }
      setIsRecording(false);
      toast.success("Đã hoàn tất bóc băng âm thanh giọng nói Tiếng Việt.");
      return;
    }

    // Check browser compatibility for Web Speech API
    const win = typeof window !== "undefined" ? (window as unknown as WindowWithSpeech) : null;
    const SpeechRecognitionConstructor = win?.SpeechRecognition || win?.webkitSpeechRecognition;

    if (!SpeechRecognitionConstructor) {
      toast.error(
        "Trình duyệt của bạn chưa hỗ trợ Web Speech API. Vui lòng sử dụng Google Chrome, Microsoft Edge hoặc Safari."
      );
      return;
    }

    try {
      const recognition = new SpeechRecognitionConstructor();
      recognition.lang = "vi-VN"; // Vietnamese Speech-to-Text
      recognition.continuous = true;
      recognition.interimResults = true;
      recognition.maxAlternatives = 3;

      recognition.onstart = () => {
        speechBaseTextRef.current = inputText.trim();
        finalTranscriptRef.current = "";
        setIsRecording(true);
        resetSilenceTimeout(recognition);
        toast.info("Đang nghe tiếng Việt. Bạn có thể nói tự nhiên và ngắt câu ngắn.");
      };

      recognition.onresult = (event: SpeechRecognitionEvent) => {
        resetSilenceTimeout(recognition);
        const finalParts: string[] = [];
        const interimParts: string[] = [];

        // Rebuild the current session so interim hypotheses are replaced instead
        // of appended repeatedly as the browser refines Vietnamese speech.
        for (let i = 0; i < event.results.length; i += 1) {
          const transcript = event.results[i][0]?.transcript.trim();
          if (!transcript) continue;
          if (event.results[i].isFinal) {
            finalParts.push(transcript);
          } else {
            interimParts.push(transcript);
          }
        }

        finalTranscriptRef.current = joinSpeechText(...finalParts);
        setInputText(
          joinSpeechText(
            speechBaseTextRef.current,
            finalTranscriptRef.current,
            ...interimParts,
          ),
        );
      };

      recognition.onerror = (event: SpeechRecognitionErrorEvent) => {
        if (silenceTimeoutRef.current) {
          clearTimeout(silenceTimeoutRef.current);
        }
        setIsRecording(false);
        if (event.error === "not-allowed") {
          toast.error("Vui lòng cho phép quyền truy cập Micro trong trình duyệt để sử dụng giọng nói.");
        } else if (event.error === "no-speech") {
          toast.warning("Không phát hiện được âm thanh giọng nói. Vui lòng thử lại.");
        } else if (event.error !== "aborted") {
          toast.error(`Lỗi nhận diện giọng nói: ${event.error}`);
        }
      };

      recognition.onend = () => {
        if (silenceTimeoutRef.current) {
          clearTimeout(silenceTimeoutRef.current);
        }
        recognitionRef.current = null;
        setIsRecording(false);
      };

      recognitionRef.current = recognition;
      recognition.start();
    } catch (err) {
      if (silenceTimeoutRef.current) {
        clearTimeout(silenceTimeoutRef.current);
      }
      recognitionRef.current = null;
      setIsRecording(false);
      toast.error("Không thể khởi động bộ thu âm giọng nói.");
      console.error("[SpeechRecognition Error]:", err);
    }
  };

  // Cảnh báo khẩn cấp KHÔNG tự khóa ô nhập: khi phiên đã bị chốt an toàn phía
  // backend, trang khám không dựng ChatInput nữa. Ở đây chỉ nhắc lại khuyến nghị
  // để người bệnh vẫn trao đổi tiếp được nếu quy trình còn cho phép.
  const safetyMessage = isChatLocked
    ? "Hội thoại đang tạm khóa trong khi phiên được xử lý hoặc thẩm định."
    : redFlagTriggered
      ? "Đang có khuyến nghị khẩn cấp trong phiên này. Nếu tình trạng nặng lên, hãy gọi 115 ngay."
      : disabled
        ? "Ô nhập hiện chưa sẵn sàng cho lượt này."
        : "AI chỉ hỗ trợ sàng lọc ban đầu; không thay thế chẩn đoán hoặc kê đơn của nhân viên y tế.";

  return (
    <div className="relative z-10 flex w-full flex-col border-t border-slate-200/90 bg-white font-sans shadow-xl dark:border-slate-800 dark:bg-zinc-950">
      <p
        id="triage-chat-safety-status"
        role={redFlagTriggered ? "alert" : "status"}
        aria-live={redFlagTriggered ? "assertive" : "polite"}
        className={cn(
          "flex min-h-12 items-center justify-center gap-2 border-b px-4 py-2 text-center text-sm font-semibold leading-6",
          redFlagTriggered
            ? "border-rose-200 bg-rose-50 text-rose-900 dark:border-rose-800 dark:bg-rose-950 dark:text-rose-100"
            : isChatLocked
              ? "border-amber-300 bg-amber-50 text-amber-950 dark:border-amber-800 dark:bg-amber-950 dark:text-amber-100"
              : "border-emerald-200 bg-emerald-50 text-emerald-950 dark:border-emerald-800 dark:bg-emerald-950 dark:text-emerald-100",
        )}
      >
        <ShieldCheck className="size-5 shrink-0" aria-hidden="true" />
        <span className="max-w-3xl text-pretty">{safetyMessage}</span>
      </p>

      <form
        onSubmit={handleSubmit}
        aria-busy={isProcessing}
        className="mx-auto flex w-full max-w-5xl items-end gap-4 px-4 py-4 sm:px-6"
      >
        <label htmlFor="triage-chat-input" className="sr-only">
          Nhập câu trả lời hoặc mô tả triệu chứng
        </label>
        <div className="relative flex min-w-0 flex-1 items-end">
          <textarea
            ref={textareaRef}
            id="triage-chat-input"
            name="triage_message"
            rows={1}
            autoComplete="off"
            aria-describedby="triage-chat-safety-status"
            disabled={disabled || isChatLocked || isProcessing}
            value={inputText}
            onChange={(e) => setInputText(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder={
              isChatLocked
                ? "Thanh chat đang tạm khóa trong khi phiên được xử lý hoặc thẩm định…"
                : isProcessing
                ? "Đang xử lý thông tin vừa gửi…"
                : isRecording
                  ? "Đang lắng nghe giọng nói của bạn… Hãy nói triệu chứng y tế."
                  : disabled
                    ? "Ô nhập chưa sẵn sàng cho lượt này…"
                    : placeholder
            }
            className={cn(
              // min-h-20 (not the 52px touch-target minimum): the longest
              // placeholder ("Mô tả triệu chứng của bạn hoặc trả lời câu hỏi
              // của trợ lý...") wraps to 2 lines at leading-6
              // (24px) + py-4 (32px) padding = 80px. Real bug observed live
              // (2026-08-28): at 52px the box's *style.height* (set by the
              // auto-resize effect below, floored from an *empty* textarea's
              // scrollHeight -- placeholder text never counts towards
              // scrollHeight in any browser) was too short for the wrapped
              // placeholder to render fully, visually cutting off its last
              // word. min-height still applies as a floor under an inline
              // style.height, so this fixes it regardless of what the effect
              // computes.
              "max-h-40 min-h-20 w-full resize-none overflow-y-auto rounded-2xl border-2 border-slate-200 bg-slate-50 py-4 pl-4 pr-14 text-base font-semibold leading-6 text-slate-900 outline-none shadow-inner transition-colors placeholder:text-slate-500 focus:border-sky-500 focus:bg-white focus:ring-2 focus:ring-sky-600/20 disabled:cursor-not-allowed disabled:border-slate-200 disabled:bg-slate-100 disabled:text-slate-500 dark:border-slate-800 dark:bg-zinc-900 dark:text-slate-100 dark:placeholder:text-slate-400 dark:focus:border-sky-400 dark:focus:bg-zinc-900 dark:disabled:border-slate-800 dark:disabled:bg-slate-900 sm:text-lg",
              {
                "border-rose-400 bg-rose-50/50 ring-2 ring-rose-500/20 dark:bg-rose-950/40": isRecording,
              }
            )}
          />

          <button
            type="button"
            disabled={disabled || isChatLocked || isProcessing}
            onClick={toggleVoiceRecording}
            aria-label={isRecording ? "Dừng nhận diện giọng nói" : "Bắt đầu nhập bằng giọng nói"}
            aria-pressed={isRecording}
            aria-describedby="triage-speech-status"
            className={cn(
              "absolute bottom-1 right-2 flex min-h-[44px] min-w-[44px] cursor-pointer items-center justify-center rounded-xl p-2 text-slate-400 transition-colors hover:bg-slate-200/60 hover:text-sky-600 disabled:pointer-events-none disabled:opacity-40 dark:hover:bg-slate-800 dark:hover:text-sky-400",
              {
                "text-rose-600 bg-rose-100 dark:bg-rose-900/80 border border-rose-300 dark:border-rose-700 animate-pulse":
                  isRecording,
              }
            )}
            title={isRecording ? "Dừng ghi âm y tế" : "Chuyển lời nói Tiếng Việt thành văn bản lâm sàng"}
          >
            {isRecording ? (
              <AudioLines className="w-6 h-6 text-rose-600 dark:text-rose-400 animate-bounce stroke-[2.5]" />
            ) : (
              <Mic className="w-6 h-6 stroke-[2.5]" />
            )}
          </button>
          <span id="triage-speech-status" className="sr-only" aria-live="polite">
            {isRecording
              ? "Đang nghe. Nội dung nhận diện sẽ xuất hiện trong ô nhập."
              : "Nhận diện giọng nói đang tắt."}
          </span>
        </div>

        <button
          type="submit"
          disabled={disabled || isChatLocked || isProcessing || !inputText.trim()}
          className="flex min-h-[52px] min-w-[52px] shrink-0 cursor-pointer items-center justify-center gap-2 rounded-2xl border-2 border-sky-600 bg-sky-600 px-4 text-base font-bold text-white shadow-md transition-colors hover:bg-sky-700 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-sky-500 focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:border-slate-200 disabled:bg-slate-200 disabled:text-slate-500 disabled:shadow-none dark:disabled:border-slate-800 dark:disabled:bg-slate-800 dark:disabled:text-slate-400 sm:px-6"
        >
          {isProcessing ? (
            <>
              <LoaderCircle className="size-5 animate-spin" aria-hidden="true" />
              <span className="hidden sm:inline">Đang xử lý…</span>
            </>
          ) : disabled || isChatLocked ? (
            <>
              <Lock className="size-5" aria-hidden="true" />
              <span className="hidden sm:inline">
                {isChatLocked ? "Đã khóa" : "Chưa sẵn sàng"}
              </span>
            </>
          ) : (
            <>
              <span>Gửi</span>
              <Send className="size-5 shrink-0" aria-hidden="true" />
            </>
          )}
        </button>
      </form>
    </div>
  );
}
