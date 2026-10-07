"use client";

import React, { useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { authService } from "@/services/auth.service";
import { useAuthStore } from "@/store/useAuthStore";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import * as z from "zod";
import {
  Mail,
  Lock,
  Eye,
  EyeOff,
  LogIn,
  Loader2,
  AlertCircle,
  ArrowRight,
} from "lucide-react";
import { toast } from "sonner";
import { getHomeRouteForRole } from "@/lib/auth-routing";
import { GitHubMark, GoogleMark } from "@/components/auth/provider-marks";

// Zod Validation Schema cho Form Đăng Nhập
const loginSchema = z.object({
  email: z
    .string()
    .min(1, "Vui lòng nhập địa chỉ Email.")
    .email("Địa chỉ Email không đúng định dạng."),
  password: z
    .string()
    .min(8, "Mật khẩu bảo mật bắt buộc có độ dài tối thiểu 8 ký tự."),
});

type LoginFormValues = z.infer<typeof loginSchema>;

export default function LoginPage() {
  const router = useRouter();
  const loginSuccess = useAuthStore((state) => state.loginSuccess);
  const [showPassword, setShowPassword] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  useEffect(() => {
    const resetOAuthNavigationState = () => {
      setIsSubmitting(false);
      toast.dismiss("oauth-load");
    };

    window.addEventListener("pageshow", resetOAuthNavigationState);
    return () => {
      window.removeEventListener("pageshow", resetOAuthNavigationState);
    };
  }, []);

  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<LoginFormValues>({
    resolver: zodResolver(loginSchema),
    defaultValues: {
      email: "",
      password: "",
    },
  });

  const onSubmit = async (data: LoginFormValues) => {
    setIsSubmitting(true);
    setErrorMessage(null);
    try {
      const res = await authService.login(data);
      
      // Lưu trữ User và Tokens vào Zustand Store + Cookie
      loginSuccess(res.user, res.access_token, res.refresh_token);
      
      toast.success(`Đăng nhập thành công. Chào mừng ${res.user.name || data.email} quay trở lại.`);
      router.replace(getHomeRouteForRole(res.user.role));
    } catch (error) {
      console.error("Authentication Error:", error);
      const msg = error instanceof Error ? error.message : "Đăng nhập thất bại. Vui lòng kiểm tra lại tài khoản.";
      setErrorMessage(msg);
      toast.error(msg);
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleOAuthLogin = async (provider: "Google" | "GitHub") => {
    setIsSubmitting(true);
    setErrorMessage(null);
    try {
      toast.loading(`Đang chuyển sang ${provider} để xác thực...`, { id: "oauth-load" });
      const targetProvider = provider.toLowerCase() as "google" | "github";
      const res = await authService.getOAuthUrl(targetProvider);
      toast.dismiss("oauth-load");
      if (res.url) {
        window.location.assign(res.url);
        setIsSubmitting(false);
      } else {
        throw new Error("Không nhận được URL xác thực từ máy chủ.");
      }
    } catch (error) {
      toast.dismiss("oauth-load");
      const msg = error instanceof Error ? error.message : `Không thể kết nối sang cổng ${provider}.`;
      console.error("OAuth Init Error:", error);
      setErrorMessage(msg);
      toast.error(msg);
      setIsSubmitting(false);
    }
  };

  return (
    <div className="flex flex-col justify-center w-full font-sans">
      
      {/* HEADER TỐI GIẢN CHUẨN NAVY BLUE */}
      <div className="mb-8 text-left">
        <div className="inline-flex items-center gap-2 px-3.5 py-1 rounded-full bg-blue-50 border border-blue-200 text-blue-800 text-xs font-black mb-3 shadow-2xs">
          <LogIn className="w-3.5 h-3.5 text-blue-600 stroke-[2.5]" />
          <span>Cổng đăng nhập hệ thống</span>
        </div>
        <h2 className="text-2xl sm:text-3xl font-black text-foreground tracking-tight">
          Chào Mừng Quay Trở Lại
        </h2>
        <p className="mt-2 text-sm font-medium text-muted-foreground leading-relaxed">
          Đăng nhập để bắt đầu phiên sàng lọc, xem lại lịch sử khám và quản lý hồ sơ y khoa của gia đình.
        </p>
      </div>

      {/* FORM ĐĂNG NHẬP (MINIMALIST NAVY THEME) */}
      <form onSubmit={handleSubmit(onSubmit)} className="space-y-5">
        
        {/* EMAIL FIELD */}
        <div className="space-y-1.5">
          <label 
            htmlFor="email-input" 
            className="block text-xs font-extrabold text-slate-800 uppercase tracking-wider dark:text-slate-100"
          >
            Địa chỉ Email
          </label>
          <div className="relative rounded-2xl transition-all duration-200">
            <div className="absolute inset-y-0 left-0 pl-4 flex items-center pointer-events-none text-slate-400">
              <Mail className="w-5 h-5 stroke-[2]" />
            </div>
            <input
              id="email-input"
              type="email"
              placeholder="doctor.nguyen@vinai.io"
              disabled={isSubmitting}
              className={`w-full pl-12 pr-4 py-3.5 text-base bg-slate-50/80 hover:bg-slate-100/70 focus:bg-white text-slate-900 placeholder-slate-400 font-medium rounded-2xl border-2 transition-all duration-200 outline-none focus:ring-4 ${
                errors.email 
                  ? "border-slate-800 focus:border-slate-900 focus:ring-slate-900/10 text-foreground bg-muted" 
                  : "border-border focus:border-blue-600 focus:ring-blue-600/15"
              } disabled:opacity-50 disabled:cursor-not-allowed`}
              {...register("email")}
            />
          </div>
          {errors.email && (
            <p className="flex items-center gap-1.5 text-xs text-blue-900 font-bold bg-blue-50 px-3 py-1.5 rounded-xl border border-blue-200 mt-1">
              <AlertCircle className="w-3.5 h-3.5 shrink-0 text-blue-700" />
              <span>{errors.email.message}</span>
            </p>
          )}
        </div>

        {/* PASSWORD FIELD */}
        <div className="space-y-1.5">
          <div className="flex items-center justify-between">
            <label 
              htmlFor="password-input" 
              className="block text-xs font-extrabold text-slate-800 uppercase tracking-wider dark:text-slate-100"
            >
              Mật khẩu
            </label>
            <Link
              href="/auth/forgot-password"
              className="text-xs font-bold text-blue-600 hover:text-blue-800 transition-colors underline decoration-blue-300 decoration-2"
            >
              Quên mật khẩu?
            </Link>
          </div>

          <div className="relative rounded-2xl transition-all duration-200">
            <div className="absolute inset-y-0 left-0 pl-4 flex items-center pointer-events-none text-slate-400">
              <Lock className="w-5 h-5 stroke-[2]" />
            </div>
            <input
              id="password-input"
              type={showPassword ? "text" : "password"}
              placeholder="••••••••••••"
              disabled={isSubmitting}
              className={`w-full pl-12 pr-12 py-3.5 text-base bg-slate-50/80 hover:bg-slate-100/70 focus:bg-white text-slate-900 placeholder-slate-400 font-medium rounded-2xl border-2 transition-all duration-200 outline-none focus:ring-4 ${
                errors.password 
                  ? "border-slate-800 focus:border-slate-900 focus:ring-slate-900/10 text-foreground bg-muted" 
                  : "border-border focus:border-blue-600 focus:ring-blue-600/15"
              } disabled:opacity-50 disabled:cursor-not-allowed`}
              {...register("password")}
            />
            <button
              type="button"
              onClick={() => setShowPassword(!showPassword)}
              className="absolute inset-y-0 right-0 pr-4 flex items-center text-slate-400 hover:text-slate-700 focus:outline-none transition-colors min-h-[44px] min-w-[44px] justify-center dark:hover:text-slate-200"
              aria-label={showPassword ? "Ẩn mật khẩu" : "Hiện mật khẩu"}
            >
              {showPassword ? <EyeOff className="w-5 h-5" /> : <Eye className="w-5 h-5" />}
            </button>
          </div>
          {errors.password && (
            <p className="flex items-center gap-1.5 text-xs text-blue-900 font-bold bg-blue-50 px-3 py-1.5 rounded-xl border border-blue-200 mt-1">
              <AlertCircle className="w-3.5 h-3.5 shrink-0 text-blue-700" />
              <span>{errors.password.message}</span>
            </p>
          )}
        </div>

        {/* THÔNG BÁO LỖI TỪ BACKEND FASTAPI (CALM SLATE ALERT) */}
        {errorMessage && (
          <div className="p-4 rounded-2xl bg-slate-900 border border-slate-800 text-white text-xs font-extrabold flex items-center gap-2.5 animate-in slide-in-from-top-2 duration-200 shadow-md">
            <AlertCircle className="w-5 h-5 shrink-0 text-blue-400 stroke-[2.3]" />
            <span>{errorMessage}</span>
          </div>
        )}

        {/* SUBMIT BUTTON - SINGLE COLOR HOSPITAL BLUE */}
        <button
          type="submit"
          disabled={isSubmitting}
          className="w-full relative group overflow-hidden rounded-2xl bg-blue-600 hover:bg-blue-700 text-white font-black py-4 px-6 shadow-md shadow-blue-600/25 transition-all duration-200 active:scale-95 disabled:opacity-60 disabled:pointer-events-none mt-3 min-h-[52px]"
        >
          <div className="flex items-center justify-center gap-2.5 text-base">
            {isSubmitting ? (
              <>
                <Loader2 className="w-5 h-5 animate-spin shrink-0" />
                <span className="font-extrabold tracking-wider text-sm uppercase">Đang xác thực...</span>
              </>
            ) : (
              <>
                <span className="font-extrabold tracking-wide uppercase text-sm">Đăng Nhập Vào Hệ Thống</span>
                <ArrowRight className="w-5 h-5 stroke-[2.5] transition-transform duration-200 group-hover:translate-x-1.5" />
              </>
            )}
          </div>
        </button>
      </form>

      {/* DIVIDER - HOẶC ĐĂNG NHẬP BẰNG */}
      <div className="relative my-7">
        <div className="absolute inset-0 flex items-center">
          <span className="w-full border-t border-border" />
        </div>
        <div className="relative flex justify-center text-xs uppercase tracking-wider">
          <span className="bg-card px-3 text-slate-400 font-sans font-extrabold">
            Hoặc tiếp tục với
          </span>
        </div>
      </div>

      {/* ĐĂNG NHẬP QUA NHÀ CUNG CẤP -- dùng đúng logo thương hiệu.
          Google yêu cầu hiển thị logo "G" bốn màu chính thức, GitHub dùng
          mark Octocat; icon chung chung (quả địa cầu / nhánh git) vừa sai
          nhận diện vừa khiến người dùng không tin đây là nút OAuth thật. */}
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
        <button
          type="button"
          onClick={() => handleOAuthLogin("Google")}
          disabled={isSubmitting}
          className="group flex items-center justify-center gap-3 py-3.5 px-4 rounded-2xl bg-card hover:bg-background border border-slate-300 hover:border-slate-400 text-slate-800 text-sm font-bold shadow-2xs transition-all duration-200 disabled:opacity-50 disabled:cursor-not-allowed min-h-[52px] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-600 focus-visible:ring-offset-2 dark:text-slate-100 dark:border-slate-700"
        >
          <GoogleMark />
          <span>Tiếp tục với Google</span>
        </button>

        <button
          type="button"
          onClick={() => handleOAuthLogin("GitHub")}
          disabled={isSubmitting}
          className="group flex items-center justify-center gap-3 py-3.5 px-4 rounded-2xl bg-slate-900 hover:bg-slate-800 border border-slate-900 text-white text-sm font-bold shadow-2xs transition-all duration-200 disabled:opacity-50 disabled:cursor-not-allowed min-h-[52px] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-slate-900 focus-visible:ring-offset-2"
        >
          <GitHubMark />
          <span>Tiếp tục với GitHub</span>
        </button>
      </div>

      {/* REGISTER REDIRECT LINK */}
      <div className="mt-8 text-center">
        <p className="text-sm text-slate-600 font-semibold dark:text-slate-300">
          Chưa có tài khoản?{" "}
          <Link
            href="/auth/register"
            className="font-black text-blue-600 hover:text-blue-800 transition-colors underline decoration-blue-300 decoration-2 underline-offset-4"
          >
            Đăng ký hồ sơ mới
          </Link>
        </p>
      </div>

    </div>
  );
}
