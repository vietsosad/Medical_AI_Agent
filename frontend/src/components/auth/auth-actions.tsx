"use client";

import type { CSSProperties, ReactNode } from "react";
import Link from "next/link";
import { ArrowLeft, Loader2 } from "lucide-react";
import { motion } from "framer-motion";

import { DURATION, EASE_OUT } from "@/lib/motion";
import { cn } from "@/lib/utils";

import { GitHubMark, GoogleMark } from "./provider-marks";
import { primaryButtonClass, secondaryButtonClass, textLinkClass } from "./auth-styles";

/** Nhấn thu 3% trong 120 ms; di chuột nhấc 1 px. Không lò xo. */
const PRESS = { scale: 0.97, transition: { duration: DURATION.press, ease: EASE_OUT } };
const LIFT = { y: -1, transition: { duration: DURATION.quick, ease: EASE_OUT } };

interface AuthSubmitButtonProps {
  pending: boolean;
  pendingLabel: string;
  children: ReactNode;
  disabled?: boolean;
  className?: string;
}

/**
 * Nút gửi biểu mẫu. Nhãn thường và nhãn "đang xử lý" chồng lên nhau trong cùng
 * một ô lưới và chỉ đổi độ mờ, nên nút không đổi kích thước khi chuyển trạng
 * thái -- không có gì bên dưới bị đẩy đi.
 */
export function AuthSubmitButton({
  pending,
  pendingLabel,
  children,
  disabled = false,
  className,
}: AuthSubmitButtonProps) {
  const isDisabled = disabled || pending;

  return (
    <motion.button
      type="submit"
      disabled={isDisabled}
      aria-busy={pending || undefined}
      whileHover={isDisabled ? undefined : LIFT}
      whileTap={isDisabled ? undefined : PRESS}
      className={cn(
        primaryButtonClass,
        pending && "disabled:cursor-progress disabled:opacity-100",
        className,
      )}
    >
      <span className="grid place-items-center">
        <span
          aria-hidden={pending || undefined}
          className={cn(
            "col-start-1 row-start-1 inline-flex items-center gap-2 transition-opacity duration-180",
            pending ? "opacity-0" : "opacity-100",
          )}
        >
          {children}
        </span>
        <span
          aria-hidden={pending ? undefined : true}
          className={cn(
            "col-start-1 row-start-1 inline-flex items-center gap-2 transition-opacity duration-180",
            pending ? "opacity-100" : "opacity-0",
          )}
        >
          <Loader2 className="size-5 motion-safe:animate-spin" aria-hidden="true" />
          {pendingLabel}
        </span>
      </span>
    </motion.button>
  );
}

export type OAuthProviderName = "Google" | "GitHub";

interface OAuthButtonsProps {
  disabled: boolean;
  onSelect: (provider: OAuthProviderName) => void | Promise<void>;
}

/**
 * Đăng nhập qua nhà cung cấp. Google đứng trước theo bản thiết kế; GitHub là
 * cổng thật của máy chủ nên vẫn giữ, cùng một kiểu nút.
 */
export function OAuthButtons({ disabled, onSelect }: OAuthButtonsProps) {
  return (
    <div className="flex flex-col gap-2">
      <motion.button
        type="button"
        onClick={() => onSelect("Google")}
        disabled={disabled}
        whileHover={disabled ? undefined : LIFT}
        whileTap={disabled ? undefined : PRESS}
        className={secondaryButtonClass}
      >
        <GoogleMark />
        Tiếp tục với Google
      </motion.button>
      <motion.button
        type="button"
        onClick={() => onSelect("GitHub")}
        disabled={disabled}
        whileHover={disabled ? undefined : LIFT}
        whileTap={disabled ? undefined : PRESS}
        className={secondaryButtonClass}
      >
        <GitHubMark />
        Tiếp tục với GitHub
      </motion.button>
    </div>
  );
}

export function AuthDivider({ label = "hoặc" }: { label?: string }) {
  return (
    <div className="my-6 flex items-center gap-4 text-sm text-muted-foreground">
      <span aria-hidden="true" className="h-px flex-1 bg-border" />
      {label}
      <span aria-hidden="true" className="h-px flex-1 bg-border" />
    </div>
  );
}

/** Dòng "Chưa có tài khoản? Đăng ký" và các dòng chuyển trang tương tự. */
export function AuthSwitchLine({
  prompt,
  href,
  action,
  className,
  style,
}: {
  prompt: string;
  href: string;
  action: string;
  className?: string;
  style?: CSSProperties;
}) {
  return (
    <p
      className={cn(
        "mt-6 flex min-h-11 flex-wrap items-center justify-center gap-x-2 text-center text-base text-muted-foreground",
        className,
      )}
      style={style}
    >
      {prompt}
      <Link href={href} className={cn(textLinkClass, "inline-flex min-h-11 items-center font-bold")}>
        {action}
      </Link>
    </p>
  );
}

export function AuthBackLink({ href = "/auth/login", children = "Quay lại đăng nhập" }: { href?: string; children?: ReactNode }) {
  return (
    <Link
      href={href}
      className={cn(
        "group inline-flex min-h-11 items-center gap-2 self-center px-2 text-sm",
        textLinkClass,
        "text-muted-foreground hover:text-foreground",
      )}
    >
      <ArrowLeft
        className="size-4 transition-transform duration-180 group-hover:-translate-x-0.5"
        aria-hidden="true"
      />
      {children}
    </Link>
  );
}
