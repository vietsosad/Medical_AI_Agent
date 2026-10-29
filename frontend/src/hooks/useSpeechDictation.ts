"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { toast } from "sonner";

/**
 * Đọc chính tả tiếng Việt bằng Web Speech API, dùng chung cho mọi ô nhập
 * triệu chứng. Chữ nhận được nối vào sau nội dung đang có trong ô, và câu tạm
 * thời được thay thế (không lặp lại) khi trình duyệt chỉnh lại kết quả.
 */

interface SpeechRecognitionErrorEvent extends Event {
  error: string;
  message: string;
}

interface SpeechRecognitionEvent extends Event {
  resultIndex: number;
  results: SpeechRecognitionResultList;
}

interface ISpeechRecognition extends EventTarget {
  lang: string;
  continuous: boolean;
  interimResults: boolean;
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

const SPEECH_SILENCE_TIMEOUT_MS = 8_000;

export function joinSpeechText(...parts: string[]): string {
  return parts
    .map((part) => part.trim())
    .filter(Boolean)
    .join(" ")
    .replace(/\s+([,.!?;:])/g, "$1")
    .replace(/\s+/g, " ")
    .trim();
}

interface UseSpeechDictationOptions {
  /** Nội dung hiện có trong ô nhập; chữ đọc được nối vào sau nó. */
  text: string;
  onTextChange: (text: string) => void;
  disabled?: boolean;
}

export function useSpeechDictation({ text, onTextChange, disabled = false }: UseSpeechDictationOptions) {
  const [isRecording, setIsRecording] = useState(false);
  const recognitionRef = useRef<ISpeechRecognition | null>(null);
  const baseTextRef = useRef("");
  const finalTranscriptRef = useRef("");
  const silenceTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const clearSilenceTimeout = useCallback(() => {
    if (silenceTimeoutRef.current) {
      clearTimeout(silenceTimeoutRef.current);
      silenceTimeoutRef.current = null;
    }
  }, []);

  // Dừng nhận diện khi component rời màn hình.
  useEffect(() => {
    return () => {
      clearSilenceTimeout();
      try {
        recognitionRef.current?.stop();
      } catch {
        // Trình duyệt có thể đã tự dừng.
      }
    };
  }, [clearSilenceTimeout]);

  const resetSilenceTimeout = (recognition: ISpeechRecognition) => {
    clearSilenceTimeout();
    silenceTimeoutRef.current = setTimeout(() => {
      if (recognitionRef.current !== recognition) return;
      try {
        recognition.stop();
        toast.info("Đã tự dừng sau 8 giây không phát hiện giọng nói.");
      } catch {
        // Trình duyệt có thể đã tự dừng.
      }
    }, SPEECH_SILENCE_TIMEOUT_MS);
  };

  /** Dừng im lặng, không báo gì -- dùng khi người bệnh bấm gửi giữa chừng. */
  const stop = useCallback(() => {
    clearSilenceTimeout();
    try {
      recognitionRef.current?.stop();
    } catch {
      // Trình duyệt có thể đã tự dừng.
    }
    setIsRecording(false);
  }, [clearSilenceTimeout]);

  const toggle = () => {
    if (disabled) return;

    if (isRecording) {
      stop();
      toast.success("Đã chuyển giọng nói thành chữ.");
      return;
    }

    const win = typeof window !== "undefined" ? (window as unknown as WindowWithSpeech) : null;
    const SpeechRecognitionConstructor = win?.SpeechRecognition || win?.webkitSpeechRecognition;
    if (!SpeechRecognitionConstructor) {
      toast.error(
        "Trình duyệt của bạn chưa hỗ trợ nhập bằng giọng nói. Vui lòng dùng Google Chrome, Microsoft Edge hoặc Safari.",
      );
      return;
    }

    try {
      const recognition = new SpeechRecognitionConstructor();
      recognition.lang = "vi-VN";
      recognition.continuous = true;
      recognition.interimResults = true;
      recognition.maxAlternatives = 3;

      recognition.onstart = () => {
        baseTextRef.current = text.trim();
        finalTranscriptRef.current = "";
        setIsRecording(true);
        resetSilenceTimeout(recognition);
        toast.info("Đang nghe tiếng Việt. Bạn có thể nói tự nhiên và ngắt câu ngắn.");
      };

      recognition.onresult = (event: SpeechRecognitionEvent) => {
        resetSilenceTimeout(recognition);
        const finalParts: string[] = [];
        const interimParts: string[] = [];

        // Dựng lại cả lượt nghe mỗi lần để câu tạm thời được thay thế thay vì
        // nối lặp khi trình duyệt chỉnh lại kết quả tiếng Việt.
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
        onTextChange(joinSpeechText(baseTextRef.current, finalTranscriptRef.current, ...interimParts));
      };

      recognition.onerror = (event: SpeechRecognitionErrorEvent) => {
        clearSilenceTimeout();
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
        clearSilenceTimeout();
        recognitionRef.current = null;
        setIsRecording(false);
      };

      recognitionRef.current = recognition;
      recognition.start();
    } catch (err) {
      clearSilenceTimeout();
      recognitionRef.current = null;
      setIsRecording(false);
      toast.error("Không thể khởi động bộ thu âm giọng nói.");
      console.error("[SpeechRecognition Error]:", err);
    }
  };

  return { isRecording, toggle, stop };
}
