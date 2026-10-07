"use client";

import React, { useEffect, useState, useRef, Suspense } from "react";
import { useParams, useSearchParams, useRouter } from "next/navigation";
import Link from "next/link";
import { authService } from "@/services/auth.service";
import { useAuthStore } from "@/store/useAuthStore";
import { toast } from "sonner";
import {
  Loader2,
  CheckCircle2,
  AlertCircle,
  ArrowLeft,
  ShieldCheck,
} from "lucide-react";
import { GitHubMark, GoogleMark } from "@/components/auth/provider-marks";
import { getHomeRouteForRole } from "@/lib/auth-routing";

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
        toast.success(`🎉 Đồng bộ tài khoản ${res.user.name || res.user.email} từ ${provider.toUpperCase()} thành công!`);

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

  return (
    <div className="w-full max-w-md bg-card rounded-3xl p-8 shadow-[0_10px_40px_rgba(0,0,0,0.06)] border border-border/80 text-center relative overflow-hidden transition-all duration-300">

      {/* HEADER BADGE */}
      <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-sky-50 border border-sky-200 text-sky-700 text-xs font-bold mb-6 shadow-xs">
        {provider.toLowerCase() === "google" ? (
          <GoogleMark className="size-3.5" />
        ) : (
          <GitHubMark className="size-3.5" />
        )}
        <span className="uppercase font-mono font-black">Cổng Liên Thông {provider}</span>
      </div>

      {/* LOADING STATE */}
      {status === "loading" && (
        <div className="space-y-5 py-6 animate-in fade-in duration-300">
          <div className="mx-auto flex h-20 w-20 items-center justify-center rounded-3xl bg-sky-50 border border-sky-100 text-sky-600 shadow-sm animate-bounce">
            <Loader2 className="w-10 h-10 animate-spin text-sky-600" />
          </div>
          <div className="space-y-1.5">
            <h3 className="text-xl font-black text-foreground tracking-tight">
              Đang Thẩm Định Hồ Sơ OAuth...
            </h3>
            <p className="text-xs sm:text-sm text-muted-foreground leading-relaxed font-medium">
              Hệ thống AI20K đang kết nối an toàn với máy chủ {provider.toUpperCase()} để đồng bộ quyền hạn định danh y khoa.
            </p>
          </div>
        </div>
      )}

      {/* SUCCESS STATE */}
      {status === "success" && (
        <div className="space-y-5 py-6 animate-in zoom-in-95 duration-400">
          <div className="mx-auto flex h-20 w-20 items-center justify-center rounded-3xl bg-emerald-50 border-2 border-emerald-300 text-emerald-600 shadow-[0_10px_30px_rgba(16,185,129,0.25)]">
            <CheckCircle2 className="w-10 h-10 animate-in zoom-in-50 duration-300" />
          </div>
          <div className="space-y-1.5">
            <h3 className="text-xl font-black text-foreground tracking-tight">
              Đăng Nhập Thành Công!
            </h3>
            <p className="text-xs sm:text-sm text-slate-600 leading-relaxed font-medium dark:text-slate-300">
              Danh tính {provider.toUpperCase()} hợp lệ. Bạn đang được tự động chuyển đến Trạm làm việc chính...
            </p>
          </div>
        </div>
      )}

      {/* ERROR STATE */}
      {status === "error" && (
        <div className="space-y-5 py-4 animate-in fade-in duration-300">
          <div className="mx-auto flex h-20 w-20 items-center justify-center rounded-3xl bg-rose-50 border-2 border-rose-300 text-rose-600 shadow-[0_10px_30px_rgba(244,63,94,0.25)]">
            <AlertCircle className="w-10 h-10 animate-in zoom-in-50 duration-300" />
          </div>
          <div className="space-y-2">
            <h3 className="text-xl font-black text-foreground tracking-tight">
              Xác Thực Ngoại Vi Thất Bại
            </h3>
            <div className="p-3.5 rounded-2xl bg-rose-50 border border-rose-200 text-rose-800 text-xs font-bold flex items-center gap-2 text-left">
              <AlertCircle className="w-4 h-4 shrink-0 text-rose-600" />
              <span className="break-words">{errorMessage}</span>
            </div>
          </div>

          <div className="pt-3 flex flex-col sm:flex-row gap-3">
            <Link
              href="/auth/login"
              className="flex-1 py-3 px-5 rounded-2xl bg-slate-900 hover:bg-slate-800 text-white font-extrabold text-xs shadow-sm transition-all duration-200 flex items-center justify-center gap-2"
            >
              <ArrowLeft className="w-4 h-4" />
              <span>Thử Đăng Nhập Lại</span>
            </Link>
            <Link
              href="/"
              className="py-3 px-5 rounded-2xl bg-muted hover:bg-slate-200 text-slate-700 font-extrabold text-xs transition-all duration-200 flex items-center justify-center dark:text-slate-200 dark:hover:bg-slate-700"
            >
              Về Trang Chủ
            </Link>
          </div>
        </div>
      )}

      {/* FOOTER NOTE */}
      <div className="mt-6 pt-4 border-t border-slate-100 text-[11px] font-mono text-slate-400 flex items-center justify-center gap-1.5">
        <ShieldCheck className="w-3.5 h-3.5 text-sky-500 shrink-0" />
        <span>Thông tin định danh được che trong nhật ký hệ thống</span>
      </div>
    </div>
  );
}

export default function OAuthCallbackPage() {
  return (
    <div className="flex flex-col justify-center items-center w-full min-h-[65vh] px-4 font-sans text-slate-800 dark:text-slate-100">
      <Suspense
        fallback={
          <div className="p-8 bg-card rounded-3xl shadow-sm border border-border text-center flex flex-col items-center gap-3">
            <Loader2 className="w-8 h-8 animate-spin text-sky-600" />
            <span className="text-xs font-bold text-muted-foreground">Đang khởi tạo kết nối OAuth...</span>
          </div>
        }
      >
        <OAuthCallbackContent />
      </Suspense>
    </div>
  );
}
