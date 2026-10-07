"use client";

import React, { useState } from "react";
import { Check, Loader2, Mail, Pencil, Phone, User, X } from "lucide-react";
import { toast } from "sonner";

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
          parsed.data
            ? "Đã cập nhật số điện thoại liên lạc."
            : "Đã gỡ bỏ số điện thoại khỏi tài khoản.",
        );
      },
      onError: (error) => {
        setValidationError(error.message);
      },
    });
  };

  const isSaving = updatePhoneMutation.isPending;

  return (
    <section className="space-y-6 rounded-2xl border border-border bg-card p-6 shadow-xs sm:p-8">
      <div className="flex flex-wrap items-center justify-between gap-4 border-b border-slate-100 pb-4">
        <h2 className="flex items-center gap-2 text-lg font-bold text-foreground sm:text-xl">
          <User className="size-5 stroke-[2.2] text-sky-600" aria-hidden="true" />
          <span>Thông tin liên lạc của chủ tài khoản</span>
        </h2>
        <span className="text-sm text-muted-foreground">
          Dùng để nhân viên y tế liên hệ lại sau khi thẩm định ca khám
        </span>
      </div>

      <div className="grid grid-cols-1 gap-6 md:grid-cols-3">
        <div className="space-y-1.5 rounded-xl border border-border/80 bg-background/80 p-5">
          <span className="block text-xs font-bold uppercase tracking-wider text-muted-foreground">
            Họ và tên
          </span>
          <p className="truncate text-base font-semibold text-foreground">{user.name}</p>
        </div>

        <div className="space-y-1.5 rounded-xl border border-border/80 bg-background/80 p-5">
          <span className="flex items-center gap-1.5 text-xs font-bold uppercase tracking-wider text-muted-foreground">
            <Mail className="size-3.5 stroke-[2.4]" aria-hidden="true" />
            Email đăng nhập
          </span>
          <p className="break-all text-base font-semibold text-foreground">{user.email}</p>
        </div>

        <div className="space-y-2 rounded-xl border border-sky-100 bg-sky-50/60 p-5">
          <span className="flex items-center gap-1.5 text-xs font-bold uppercase tracking-wider text-sky-800">
            <Phone className="size-3.5 stroke-[2.4]" aria-hidden="true" />
            Số điện thoại
          </span>

          {isEditing ? (
            <form onSubmit={handleSubmit} className="space-y-2.5">
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
                aria-describedby={validationError ? "account-phone-error" : undefined}
                placeholder="Ví dụ 0912345678"
                className="min-h-11 w-full rounded-xl border-2 border-border bg-card px-3 text-base font-semibold text-foreground outline-none transition-colors focus:border-sky-500 focus:ring-2 focus:ring-sky-600/20 disabled:cursor-not-allowed disabled:bg-muted"
              />

              {validationError && (
                <p
                  id="account-phone-error"
                  role="alert"
                  className="text-sm font-medium leading-5 text-rose-700"
                >
                  {validationError}
                </p>
              )}

              <div className="flex flex-wrap items-center gap-2">
                <button
                  type="submit"
                  disabled={isSaving}
                  className="flex min-h-11 items-center gap-1.5 rounded-xl bg-sky-600 px-4 text-sm font-bold text-white transition-colors hover:bg-sky-700 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-sky-600 focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:bg-slate-300"
                >
                  {isSaving ? (
                    <Loader2 className="size-4 animate-spin" aria-hidden="true" />
                  ) : (
                    <Check className="size-4 stroke-[2.6]" aria-hidden="true" />
                  )}
                  Lưu
                </button>
                <button
                  type="button"
                  onClick={cancelEditing}
                  disabled={isSaving}
                  className="flex min-h-11 items-center gap-1.5 rounded-xl border border-slate-300 bg-card px-4 text-sm font-semibold text-slate-700 transition-colors hover:bg-muted focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-slate-600 disabled:cursor-not-allowed dark:text-slate-200 dark:border-slate-700"
                >
                  <X className="size-4 stroke-[2.6]" aria-hidden="true" />
                  Hủy
                </button>
              </div>

              <p className="text-xs leading-5 text-muted-foreground">
                Để trống rồi lưu nếu bạn muốn gỡ số điện thoại khỏi tài khoản.
              </p>
            </form>
          ) : (
            <div className="flex flex-wrap items-center justify-between gap-3">
              <p className="text-base font-semibold text-foreground">
                {user.phoneNumber ? (
                  formatVietnamPhoneForDisplay(user.phoneNumber)
                ) : (
                  <span className="font-medium italic text-muted-foreground">Chưa cập nhật</span>
                )}
              </p>
              <button
                type="button"
                onClick={startEditing}
                className="flex min-h-11 items-center gap-1.5 rounded-xl border border-sky-200 bg-card px-3.5 text-sm font-semibold text-sky-700 transition-colors hover:bg-sky-50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-sky-600 focus-visible:ring-offset-2"
              >
                <Pencil className="size-4 stroke-[2.4]" aria-hidden="true" />
                Chỉnh sửa
              </button>
            </div>
          )}
        </div>
      </div>
    </section>
  );
}

export default AccountContactCard;
