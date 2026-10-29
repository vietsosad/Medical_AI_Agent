"use client";

import React, { useEffect, useState, useRef, Suspense } from "react";
import { useParams, useSearchParams, useRouter } from "next/navigation";
import Link from "next/link";
import { authService } from "@/services/auth.service";
import { useAuthStore } from "@/store/useAuthStore";
import { toast } from "sonner";
import { AlertCircle, ArrowLeft, CheckCircle2, KeyRound, Loader2 } from "lucide-react";
import { GitHubMark, GoogleMark } from "@/components/auth/provider-marks";
import { getHomeRouteForRole } from "@/lib/auth-routing";
import { AuthHeading } from "@/components/auth/auth-heading";
import { AuthStatusIcon, AuthSwap } from "@/components/auth/auth-status";
import { primaryButtonClass, secondaryButtonClass } from "@/components/auth/auth-styles";

/** Tên hiển thị của nhà cung cấp; giá trị gửi lên máy chủ vẫn là tham số gốc của URL. */
const PROVIDER_LABELS: Record<string, string> = {
  google: "Google",
  github: "GitHub",
};

function ProviderMark({ provider }: { provider: string }) {
  if (provider === "google") return <GoogleMark className="size-8" />;
  if (provider === "github") return <GitHubMark className="size-8" />;
  return <KeyRound className="size-8 text-muted-foreground" />;
}

function OAuthCallbackContent() {
  const params = useParams<{ provider: string }>();
  const searchParams = useSearchParams();
  const router = useRouter();
  const loginSuccess = useAuthStore((state) => state.loginSuccess);

  const provider = params?.provider || "oauth";
  const code = searchParams?.get("code");

  const [status, setStatus] = useState<"loading" | "success" | "error">("loading");
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  // Dùng ref để đảm bảo callback chỉ gọi 1 lần trong chế độ StrictMode của React
  const hasProcessed = useRef(false);

  useEffect(() => {
    if (hasProcessed.current) return;
    hasProcessed.current = true;

    if (!code) {
      setTimeout(() => {
        setStatus("error");
        const msg = "Không tìm thấy mã xác thực (Authorization Code) trong URL từ nhà cung cấp OAuth.";
        setErrorMessage(msg);
        toast.error(msg);
      }, 0);
      return;
    }

    const processOAuth = async () => {
      try {
        const res = await authService.oauthCallback(provider, code);

        // Lưu trữ Token và User vào Zustand Store
        loginSuccess(res.user, res.access_token, res.refresh_token);

        setStatus("success");
        toast.success(`Đồng bộ tài khoản ${res.user.name || res.user.email} từ ${provider.toUpperCase()} thành công!`);

        // Điều hướng tự động sau 1.5 giây để trải nghiệm mượt mà
        setTimeout(() => {
          router.replace(getHomeRouteForRole(res.user.role));
        }, 1500);
      } catch (error) {
        console.error("❌ [OAuth Callback Error]:", error);
        const msg = error instanceof Error ? error.message : "Quá trình xác thực OAuth bị từ chối hoặc máy chủ gặp sự cố.";
        setStatus("error");
        setErrorMessage(msg);
        toast.error(msg);
      }
    };

    processOAuth();
  }, [code, provider, loginSuccess, router]);

  const providerKey = provider.toLowerCase();
  const providerLabel = PROVIDER_LABELS[providerKey] ?? provider;

  return (
    <div className="page-enter flex w-full flex-col">
      <AuthSwap stateKey={status}>
        {status === "loading" && (
          <div className="flex flex-col items-center gap-6 py-4 text-center">
            {/* Logo nhà cung cấp đứng yên, vòng xoay nhỏ ở góc báo hệ thống đang làm việc. */}
            <AuthStatusIcon tone="neutral">
              <ProviderMark provider={providerKey} />
              <span className="absolute -right-2 -bottom-2 grid size-8 place-items-center rounded-full border border-border bg-card text-brand">
                <Loader2 className="size-4 motion-safe:animate-spin" />
              </span>
            </AuthStatusIcon>
            <AuthHeading
              align="center"
              title={`Đang hoàn tất đăng nhập với ${providerLabel}`}
              description="Vui lòng giữ trang này mở trong lúc hệ thống xác nhận tài khoản của bạn."
            />
          </div>
        )}

        {status === "success" && (
          <div className="flex flex-col items-center gap-6 py-4 text-center">
            <AuthStatusIcon tone="success">
              <CheckCircle2 className="size-8" />
            </AuthStatusIcon>
            <div role="status">
              <AuthHeading
                align="center"
                title="Đăng nhập thành công"
                description="Đang chuyển bạn tới trang phù hợp với tài khoản…"
              />
            </div>
          </div>
        )}

        {status === "error" && (
          <div className="flex flex-col items-center gap-6 py-4 text-center">
            <AuthStatusIcon tone="error">
              <AlertCircle className="size-8" />
            </AuthStatusIcon>
            <AuthHeading align="center" title={`Chưa đăng nhập được với ${providerLabel}`} />
            <p
              role="alert"
              className="w-full rounded-xl border border-rose-200 bg-rose-50 p-4 text-left text-sm font-medium break-words text-rose-900 dark:border-rose-900/60 dark:bg-rose-950/40 dark:text-rose-100"
            >
              {errorMessage}
            </p>
            <div className="flex w-full flex-col gap-2">
              <Link href="/auth/login" className={primaryButtonClass}>
                <ArrowLeft className="size-5" aria-hidden="true" />
                Thử đăng nhập lại
              </Link>
              <Link href="/" className={secondaryButtonClass}>
                Về trang chủ
              </Link>
            </div>
          </div>
        )}
      </AuthSwap>
    </div>
  );
}

export default function OAuthCallbackPage() {
  return (
    <Suspense
      fallback={
        <div className="flex flex-col items-center gap-4 py-8 text-center">
          <Loader2 className="size-8 text-brand motion-safe:animate-spin" aria-hidden="true" />
          <p className="text-sm font-medium text-muted-foreground">Đang khởi tạo kết nối…</p>
        </div>
      }
    >
      <OAuthCallbackContent />
    </Suspense>
  );
}
