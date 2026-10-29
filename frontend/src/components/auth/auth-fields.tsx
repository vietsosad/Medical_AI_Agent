"use client";

import type { ComponentPropsWithRef, ReactNode } from "react";
import { AlertCircle, Eye, EyeOff } from "lucide-react";
import { AnimatePresence, motion, useReducedMotion, type Transition } from "framer-motion";

import { DURATION, EASE_OUT, exitTransition } from "@/lib/motion";
import { cn } from "@/lib/utils";

import {
  fieldBaseClass,
  fieldInvalidToneClass,
  fieldToneClass,
  focusOutlineClass,
} from "./auth-styles";

/** Khi hệ điều hành bật "giảm chuyển động": chỉ mờ dần, dưới 150 ms. */
const REDUCED_FADE: Transition = { duration: 0.12 };

/**
 * Mở ra / thu lại theo chiều cao và độ mờ. Dùng cho lỗi dưới ô nhập và lỗi của
 * cả biểu mẫu: lỗi trượt xuống đúng chỗ thay vì làm nội dung bên dưới giật.
 */
export function AuthReveal({ show, children }: { show: boolean; children: ReactNode }) {
  const reduceMotion = useReducedMotion() ?? false;

  return (
    <AnimatePresence initial={false}>
      {show ? (
        <motion.div
          key="reveal"
          className="overflow-hidden"
          initial={reduceMotion ? { opacity: 0 } : { opacity: 0, height: 0 }}
          animate={
            reduceMotion
              ? { opacity: 1, transition: REDUCED_FADE }
              : { opacity: 1, height: "auto", transition: { duration: DURATION.base, ease: EASE_OUT } }
          }
          exit={
            reduceMotion
              ? { opacity: 0, transition: REDUCED_FADE }
              : { opacity: 0, height: 0, transition: exitTransition }
          }
        >
          {children}
        </motion.div>
      ) : null}
    </AnimatePresence>
  );
}

/**
 * Lỗi của một ô nhập. Vùng `aria-live` luôn có mặt để trình đọc màn hình đọc
 * được câu lỗi ngay khi nó xuất hiện; ô nhập trỏ tới `id` qua
 * `aria-describedby`.
 */
export function FieldError({
  id,
  message,
  className,
}: {
  id: string;
  message?: string | null;
  className?: string;
}) {
  return (
    <div aria-live="polite">
      <AuthReveal show={Boolean(message)}>
        <p
          id={id}
          className={cn(
            "flex items-start gap-2 pt-2 text-sm font-medium text-rose-700 dark:text-rose-300",
            className,
          )}
        >
          <span className="flex h-5 shrink-0 items-center">
            <AlertCircle className="size-4" aria-hidden="true" />
          </span>
          <span className="min-w-0 break-words">{message}</span>
        </p>
      </AuthReveal>
    </div>
  );
}

/** Lỗi do máy chủ trả về cho cả biểu mẫu (sai mật khẩu, mất kết nối...). */
export function AuthFormAlert({ message }: { message: string | null }) {
  return (
    <div role="alert">
      <AuthReveal show={Boolean(message)}>
        <div className="pt-4">
          <p className="flex items-start gap-2 rounded-xl border border-rose-200 bg-rose-50 p-4 text-sm font-medium text-rose-900 dark:border-rose-900/60 dark:bg-rose-950/40 dark:text-rose-100">
            <span className="flex h-5 shrink-0 items-center">
              <AlertCircle className="size-4 text-rose-700 dark:text-rose-300" aria-hidden="true" />
            </span>
            <span className="min-w-0 break-words">{message}</span>
          </p>
        </div>
      </AuthReveal>
    </div>
  );
}

interface AuthFieldProps {
  id: string;
  label: string;
  error?: string;
  hint?: string;
  /** Nội dung đặt cạnh nhãn, ví dụ liên kết "Quên mật khẩu?". */
  aside?: ReactNode;
  children: ReactNode;
}

export function AuthField({ id, label, error, hint, aside, children }: AuthFieldProps) {
  return (
    <div className="flex flex-col">
      <div className="mb-2 flex items-center justify-between gap-4">
        <label htmlFor={id} className="text-sm font-semibold text-foreground">
          {label}
        </label>
        {aside}
      </div>
      {children}
      {hint ? (
        <p id={`${id}-hint`} className="mt-2 text-sm text-muted-foreground">
          {hint}
        </p>
      ) : null}
      <FieldError id={`${id}-error`} message={error} />
    </div>
  );
}

export interface AuthInputProps extends ComponentPropsWithRef<"input"> {
  id: string;
  invalid?: boolean;
  /** Ô có dòng gợi ý `${id}-hint` bên dưới (xem AuthField). */
  hasHint?: boolean;
}

export function AuthInput({ id, invalid = false, hasHint = false, className, ...props }: AuthInputProps) {
  const describedBy =
    [hasHint ? `${id}-hint` : null, invalid ? `${id}-error` : null].filter(Boolean).join(" ") ||
    undefined;

  return (
    <input
      id={id}
      aria-invalid={invalid || undefined}
      aria-describedby={describedBy}
      className={cn(fieldBaseClass, invalid ? fieldInvalidToneClass : fieldToneClass, className)}
      {...props}
    />
  );
}

interface PasswordInputProps extends Omit<AuthInputProps, "type"> {
  visible: boolean;
  onToggleVisibility: () => void;
  showLabel?: string;
  hideLabel?: string;
}

/** Ô mật khẩu với nút hiện/ẩn 48 px nằm trong ô, có nhãn cho trình đọc màn hình. */
export function PasswordInput({
  id,
  visible,
  onToggleVisibility,
  showLabel = "Hiện mật khẩu",
  hideLabel = "Ẩn mật khẩu",
  className,
  ...props
}: PasswordInputProps) {
  const reduceMotion = useReducedMotion() ?? false;

  return (
    <div className="relative">
      <AuthInput id={id} type={visible ? "text" : "password"} className={cn("pr-12", className)} {...props} />
      <button
        type="button"
        onClick={onToggleVisibility}
        aria-label={visible ? hideLabel : showLabel}
        aria-controls={id}
        className={cn(
          "absolute inset-y-0 right-0 flex w-12 items-center justify-center rounded-xl text-muted-foreground transition-colors duration-180 hover:text-foreground",
          focusOutlineClass,
          "focus-visible:-outline-offset-4",
        )}
      >
        <AnimatePresence initial={false} mode="wait">
          <motion.span
            key={visible ? "hide" : "show"}
            className="flex"
            initial={reduceMotion ? { opacity: 0 } : { opacity: 0, scale: 0.8 }}
            animate={{ opacity: 1, scale: 1, transition: { duration: DURATION.press, ease: EASE_OUT } }}
            exit={{ opacity: 0, transition: { duration: DURATION.press * 0.75 } }}
          >
            {visible ? (
              <EyeOff className="size-5" aria-hidden="true" />
            ) : (
              <Eye className="size-5" aria-hidden="true" />
            )}
          </motion.span>
        </AnimatePresence>
      </button>
    </div>
  );
}
