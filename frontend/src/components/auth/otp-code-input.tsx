"use client";

import { useEffect, useRef, type ClipboardEvent, type KeyboardEvent } from "react";
import { Loader2, RotateCw } from "lucide-react";
import { motion, useAnimate, useReducedMotion } from "framer-motion";

import { DURATION, EASE_OUT, staggerDelay } from "@/lib/motion";
import { cn } from "@/lib/utils";

import { FieldError } from "./auth-fields";
import { fieldBaseClass, fieldInvalidToneClass, fieldToneClass, focusOutlineClass } from "./auth-styles";

/** Lắc ngang một lần khi mã sai: biên độ 6 px, chuyển động tuyến tính, không lò xo. */
const SHAKE_X = [0, -6, 6, -6, 6, 0];
const SHAKE_SECONDS = 0.4;

const filledToneClass =
  "border-brand-edge bg-brand-soft focus-visible:border-brand focus-visible:inset-ring-1 focus-visible:inset-ring-brand focus-visible:ring-4 focus-visible:ring-brand/20";

interface OtpCodeInputProps {
  digits: string[];
  /** `id` của nhãn hiển thị phía trên nhóm ô. */
  labelId: string;
  /** `id` của câu lỗi (FieldError) bên dưới nhóm ô. */
  errorId: string;
  invalid: boolean;
  disabled: boolean;
  registerInput: (index: number, element: HTMLInputElement | null) => void;
  onDigitChange: (index: number, value: string) => void;
  onDigitKeyDown: (index: number, event: KeyboardEvent<HTMLInputElement>) => void;
  onPaste: (event: ClipboardEvent<HTMLInputElement>) => void;
}

/**
 * Sáu ô nhập mã. Chỉ lo phần trình bày: nhập, dán, phím lùi... vẫn do trang
 * gọi xử lý như trước. Các ô bật vào lần lượt (cách nhau 50 ms); ô đã có số
 * chuyển sang nền thương hiệu nhạt; khi mã bị từ chối cả nhóm lắc một lần.
 */
export function OtpCodeInput({
  digits,
  labelId,
  errorId,
  invalid,
  disabled,
  registerInput,
  onDigitChange,
  onDigitKeyDown,
  onPaste,
}: OtpCodeInputProps) {
  const [scope, animate] = useAnimate<HTMLDivElement>();
  const reduceMotion = useReducedMotion() ?? false;
  const wasInvalid = useRef(invalid);

  // Con trỏ vào ô đầu đúng lúc nhóm ô xuất hiện. Trang khôi phục mật khẩu dựng
  // nhóm này sau một hiệu ứng chuyển bước, nên một lệnh focus hẹn giờ ở phía
  // trang có thể chạy trước khi ô tồn tại, hoặc giật con trỏ về ô đầu giữa
  // lúc người dùng đang gõ.
  useEffect(() => {
    scope.current?.querySelector<HTMLInputElement>("input:not([disabled])")?.focus();
  }, [scope]);

  useEffect(() => {
    const becameInvalid = invalid && !wasInvalid.current;
    wasInvalid.current = invalid;
    const group = scope.current;
    if (!becameInvalid || !group) return;

    // Trang xóa trống các ô rồi gọi focus() ô đầu ngay trong cùng lượt cập nhật
    // trạng thái, lúc các ô vẫn còn bị khóa nên lệnh focus bị bỏ qua. Đặt lại
    // con trỏ ở đây, sau khi ô đã mở khóa, để người dùng gõ lại được ngay.
    if (!disabled) group.querySelector<HTMLInputElement>("input")?.focus();
    if (!reduceMotion) {
      animate(group, { x: SHAKE_X }, { duration: SHAKE_SECONDS, ease: "linear" });
    }
  }, [invalid, disabled, reduceMotion, animate, scope]);

  return (
    <div
      ref={scope}
      role="group"
      aria-labelledby={labelId}
      className="grid w-full max-w-sm grid-cols-6 gap-2"
    >
      {digits.map((digit, index) => (
        <motion.input
          // Vị trí ô (1-6) chính là danh tính của ô, không đổi thứ tự.
          key={`otp-slot-${index}`}
          ref={(element) => registerInput(index, element)}
          type="text"
          inputMode="numeric"
          autoComplete="one-time-code"
          maxLength={1}
          value={digit}
          disabled={disabled}
          aria-label={`Chữ số thứ ${index + 1} của mã`}
          aria-invalid={invalid || undefined}
          aria-describedby={invalid ? errorId : undefined}
          onChange={(event) => onDigitChange(index, event.target.value)}
          onKeyDown={(event) => onDigitKeyDown(index, event)}
          onPaste={onPaste}
          initial={{ opacity: 0, scale: 0.9 }}
          animate={{ opacity: 1, scale: 1 }}
          transition={{ duration: DURATION.base, ease: EASE_OUT, delay: staggerDelay(index) }}
          className={cn(
            fieldBaseClass,
            "h-14 px-0 text-center text-2xl font-bold tabular-nums",
            invalid
              ? cn(fieldInvalidToneClass, "bg-rose-50 text-rose-900 dark:bg-rose-950/40 dark:text-rose-100")
              : digit
                ? filledToneClass
                : fieldToneClass,
          )}
        />
      ))}
    </div>
  );
}

/**
 * Dòng trạng thái dưới nhóm ô: "đang kiểm tra" hoặc câu lỗi. Giữ sẵn chiều cao
 * một dòng nên lúc bắt đầu kiểm tra, phần bên dưới không bị đẩy xuống.
 */
export function OtpFeedback({
  verifying,
  error,
  errorId,
}: {
  verifying: boolean;
  error: string | null;
  errorId: string;
}) {
  return (
    <div className="mt-4 min-h-6">
      <div role="status" className="flex items-center gap-2 text-sm font-medium text-muted-foreground">
        {verifying ? (
          <>
            <Loader2 className="size-4 text-brand motion-safe:animate-spin" aria-hidden="true" />
            Đang kiểm tra mã…
          </>
        ) : null}
      </div>
      <FieldError id={errorId} message={error} className="pt-0" />
    </div>
  );
}

/** Nút gửi lại mã: mờ trong lúc đếm ngược, chuyển sang màu thương hiệu khi bấm được. */
export function ResendCodeButton({
  secondsLeft,
  disabled,
  onResend,
}: {
  secondsLeft: number;
  disabled: boolean;
  onResend: () => void;
}) {
  const waiting = secondsLeft > 0;

  return (
    <button
      type="button"
      onClick={onResend}
      disabled={disabled}
      className={cn(
        "inline-flex min-h-11 items-center gap-2 rounded-xl px-4 text-sm font-semibold transition-colors duration-180 disabled:cursor-not-allowed",
        focusOutlineClass,
        waiting ? "text-muted-foreground" : "text-brand hover:bg-brand-soft disabled:opacity-60",
      )}
    >
      <RotateCw className="size-4" aria-hidden="true" />
      <span className="tabular-nums">
        {waiting ? `Gửi lại sau ${secondsLeft} giây` : "Gửi lại mã"}
      </span>
    </button>
  );
}
