"use client";

import { useEffect, useRef, useState } from "react";
import Link from "next/link";
import { AlertTriangle, Loader2, RotateCcw } from "lucide-react";
import { useRouter } from "next/navigation";

import { authService } from "@/services/auth.service";
import { useAuthStore } from "@/store/useAuthStore";

export default function GuestSessionPage() {
  const router = useRouter();
  const startedRef = useRef(false);
  const [error, setError] = useState<string | null>(null);
  const { isAuthenticated, isLoading, loginSuccess } = useAuthStore();

  useEffect(() => {
    if (isLoading || startedRef.current) return;

    if (isAuthenticated) {
      router.replace("/triage");
      return;
    }

    startedRef.current = true;
    const createGuestSession = async () => {
      try {
        const result = await authService.loginAsGuest();
        loginSuccess(result.user, result.access_token, result.refresh_token);
        router.replace("/triage");
      } catch (guestError: unknown) {
        setError(
          guestError instanceof Error
            ? guestError.message
            : "Không thể khởi tạo phiên khám nhanh.",
        );
      }
    };

    void createGuestSession();
  }, [isAuthenticated, isLoading, loginSuccess, router]);

  if (error) {
    return (
      <main
        role="alert"
        aria-live="assertive"
        className="mx-auto flex min-h-[60vh] w-full max-w-2xl flex-col items-center justify-center gap-4 text-center"
      >
        <AlertTriangle className="size-12 text-rose-600" aria-hidden="true" />
        <h1 className="text-xl font-bold text-slate-950 dark:text-slate-50">Không thể mở phiên khám nhanh</h1>
        <p className="text-base leading-6 text-slate-700 dark:text-slate-200">{error}</p>
        <Link
          href="/auth/login"
          className="flex min-h-12 items-center gap-2 rounded-xl bg-sky-600 px-4 text-base font-semibold text-white hover:bg-sky-700 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-sky-600 focus-visible:ring-offset-2"
        >
          <RotateCcw className="size-5" aria-hidden="true" />
          Quay lại và thử lại
        </Link>
      </main>
    );
  }

  return (
    <main
      className="flex min-h-[60vh] flex-col items-center justify-center gap-4 text-center"
      aria-busy="true"
      aria-live="polite"
    >
      <Loader2 className="size-12 animate-spin text-sky-600" aria-hidden="true" />
      <h1 className="text-xl font-bold text-slate-950 dark:text-slate-50">Đang mở phiên khám nhanh an toàn</h1>
      <p className="max-w-lg text-base leading-6 text-slate-700 dark:text-slate-200">
        Hệ thống đang tạo định danh khách không chứa thông tin cá nhân và kết nối tới bộ lọc cảnh báo khẩn cấp.
      </p>
    </main>
  );
}
