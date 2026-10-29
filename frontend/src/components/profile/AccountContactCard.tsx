"use client";

import React, { useState } from "react";
import { Check, Loader2, Mail, Pencil, Phone, X } from "lucide-react";
import { toast } from "sonner";

import { cn } from "@/lib/utils";
import {
  formatVietnamPhoneForDisplay,
  MAX_RAW_PHONE_LENGTH,
  optionalVietnamPhoneSchema,
} from "@/lib/validations/account-contact.schema";
import { useUpdatePhoneNumber } from "@/queries/useAccountMutations";
import { useAuthStore } from "@/store/useAuthStore";

/**
 * ============================================================================
 * [ACCOUNT CONTACT CARD] THÔNG TIN LIÊN LẠC CỦA CHỦ TÀI KHOẢN
 * ============================================================================
 * Xem và cập nhật số điện thoại gắn với chính tài khoản đang đăng nhập
 * (cột `users.phone`). Danh tính do Bearer Token quyết định phía máy chủ,
 * biểu mẫu này không bao giờ gửi kèm user id.
 */
export function AccountContactCard() {
  const user = useAuthStore((state) => state.user);
  const updatePhoneMutation = useUpdatePhoneNumber();

  const [isEditing, setIsEditing] = useState(false);
  const [draftPhone, setDraftPhone] = useState("");
  const [validationError, setValidationError] = useState<string | null>(null);

  if (!user) return null;

  const startEditing = () => {
    setDraftPhone(user.phoneNumber ?? "");
    setValidationError(null);
    setIsEditing(true);
  };

  const cancelEditing = () => {
    setIsEditing(false);
    setDraftPhone("");
    setValidationError(null);
  };

  const handleSubmit = (event: React.FormEvent) => {
    event.preventDefault();

    const parsed = optionalVietnamPhoneSchema.safeParse(draftPhone);
    if (!parsed.success) {
      setValidationError(parsed.error.issues[0]?.message ?? "Số điện thoại không hợp lệ.");
      return;
    }
    setValidationError(null);

    updatePhoneMutation.mutate(parsed.data, {
      onSuccess: () => {
        setIsEditing(false);
        setDraftPhone("");
        toast.success(
          parsed.data ? "Đã cập nhật số điện thoại liên lạc." : "Đã gỡ bỏ số điện thoại khỏi tài khoản.",
        );
      },
      onError: (error) => {
        setValidationError(error.message);
      },
    });
  };

  const isSaving = updatePhoneMutation.isPending;

  return (
    <section aria-labelledby="account-contact-title" className="rounded-3xl border border-border bg-card p-4 shadow-xs sm:p-6">
      <h2 id="account-contact-title" className="text-lg font-extrabold tracking-tight text-foreground">
        Thông tin liên lạc của chủ tài khoản
      </h2>
      <p className="mt-2 text-sm leading-6 text-muted-foreground">
        Dùng để nhân viên y tế liên hệ lại sau khi thẩm định ca khám.
      </p>

      <dl className="mt-4 grid grid-cols-1 gap-2 sm:grid-cols-3">
        <div className="min-w-0 rounded-2xl bg-muted/70 px-4 py-2">
          <dt className="text-sm font-semibold text-muted-foreground">Họ và tên</dt>
          <dd className="truncate text-base font-bold leading-7 text-foreground">{user.name}</dd>
        </div>

        <div className="min-w-0 rounded-2xl bg-muted/70 px-4 py-2">
          <dt className="flex items-center gap-2 text-sm font-semibold text-muted-foreground">
            <Mail className="size-4" aria-hidden="true" />
            Email đăng nhập
          </dt>
          <dd className="break-all text-base font-bold leading-7 text-foreground">{user.email}</dd>
        </div>

        <div className={cn("min-w-0 rounded-2xl bg-muted/70 px-4 py-2", isEditing && "sm:col-span-3")}>
          <dt className="flex items-center gap-2 text-sm font-semibold text-muted-foreground">
            <Phone className="size-4" aria-hidden="true" />
            Số điện thoại
          </dt>
          <dd>
            {isEditing ? (
              <form onSubmit={handleSubmit} className="space-y-2 py-2">
                <label htmlFor="account-phone-input" className="sr-only">
                  Số điện thoại liên lạc
                </label>
                <input
                  id="account-phone-input"
                  name="phoneNumber"
                  type="tel"
                  inputMode="tel"
                  autoComplete="tel"
                  autoFocus
                  maxLength={MAX_RAW_PHONE_LENGTH}
                  disabled={isSaving}
                  value={draftPhone}
                  onChange={(event) => setDraftPhone(event.target.value)}
                  aria-invalid={validationError !== null}
                  aria-describedby={validationError ? "account-phone-error" : "account-phone-hint"}
                  placeholder="Ví dụ 0912345678"
                  className="min-h-11 w-full rounded-xl border border-border bg-card px-4 text-base font-semibold tabular-nums text-foreground outline-none transition-colors focus-visible:border-brand focus-visible:ring-2 focus-visible:ring-brand/30 disabled:cursor-not-allowed disabled:opacity-60 sm:max-w-sm"
                />

                {validationError && (
                  <p id="account-phone-error" role="alert" className="text-sm font-medium leading-6 text-rose-700 dark:text-rose-300">
                    {validationError}
                  </p>
                )}

                <div className="flex flex-wrap items-center gap-2">
                  <button
                    type="submit"
                    disabled={isSaving}
                    className="flex min-h-11 items-center gap-2 rounded-xl bg-brand px-4 text-sm font-bold text-brand-foreground transition-colors hover:bg-brand-strong focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand focus-visible:ring-offset-2 focus-visible:ring-offset-card disabled:cursor-not-allowed disabled:opacity-60"
                  >
                    {isSaving ? (
                      <Loader2 className="size-4 animate-spin" aria-hidden="true" />
                    ) : (
                      <Check className="size-4" aria-hidden="true" />
                    )}
                    Lưu
                  </button>
                  <button
                    type="button"
                    onClick={cancelEditing}
                    disabled={isSaving}
                    className="flex min-h-11 items-center gap-2 rounded-xl border border-border bg-card px-4 text-sm font-semibold text-foreground transition-colors hover:bg-muted focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand disabled:cursor-not-allowed"
                  >
                    <X className="size-4" aria-hidden="true" />
                    Hủy
                  </button>
                </div>

                <p id="account-phone-hint" className="text-sm leading-6 text-muted-foreground">
                  Để trống rồi lưu nếu bạn muốn gỡ số điện thoại khỏi tài khoản.
                </p>
              </form>
            ) : (
              <div className="flex items-center justify-between gap-2">
                <span className="text-base font-bold leading-7 tabular-nums text-foreground">
                  {user.phoneNumber ? (
                    formatVietnamPhoneForDisplay(user.phoneNumber)
                  ) : (
                    <span className="font-semibold text-muted-foreground">Chưa cập nhật</span>
                  )}
                </span>
                <button
                  type="button"
                  onClick={startEditing}
                  aria-label="Sửa số điện thoại của tài khoản"
                  className="flex size-11 shrink-0 items-center justify-center rounded-xl text-brand transition-colors hover:bg-brand-soft focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand"
                >
                  <Pencil className="size-4" aria-hidden="true" />
                </button>
              </div>
            )}
          </dd>
        </div>
      </dl>
    </section>
  );
}

export default AccountContactCard;
