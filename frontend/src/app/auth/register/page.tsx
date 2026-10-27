"use client";

import React, { useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { authService } from "@/services/auth.service";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import * as z from "zod";
import {
  User,
  Mail,
  Lock,
  Eye,
  EyeOff,
  UserPlus,
  Loader2,
  AlertCircle,
  ArrowRight
} from "lucide-react";
import { GitHubMark, GoogleMark } from "@/components/auth/provider-marks";
import { toast } from "sonner";

// Zod Validation Schema cho Form Đăng Ký Tài Khoản Lâm Sàng
const registerSchema = z
  .object({
    fullName: z
      .string()
      .min(2, "Vui lòng nhập đầy đủ Họ và Tên hợp lệ (tối thiểu 2 ký tự)."),
    email: z
      .string()
      .min(1, "Vui lòng nhập địa chỉ Email y khoa.")
      .email("Địa chỉ Email không đúng định dạng hợp lệ."),
    password: z
      .string()
      .min(8, "Mật khẩu bảo mật bắt buộc có độ dài tối thiểu 8 ký tự."),
    confirmPassword: z
      .string()
      .min(1, "Vui lòng nhập lại mật khẩu xác nhận."),
  })
  .refine((data) => data.password === data.confirmPassword, {
    message: "Mật khẩu xác nhận không khớp với mật khẩu vừa nhập.",
    path: ["confirmPassword"],
  });

type RegisterFormValues = z.infer<typeof registerSchema>;

export default function RegisterPage() {
  const router = useRouter();
  const [showPassword, setShowPassword] = useState(false);
  const [showConfirmPassword, setShowConfirmPassword] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  useEffect(() => {
    const resetOAuthNavigationState = () => {
      setIsSubmitting(false);
      toast.dismiss("oauth-reg-load");
    };

    window.addEventListener("pageshow", resetOAuthNavigationState);
    return () => {
      window.removeEventListener("pageshow", resetOAuthNavigationState);
    };
  }, []);

  // Khởi tạo React Hook Form kèm Zod Resolver
  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<RegisterFormValues>({
    resolver: zodResolver(registerSchema),
    defaultValues: {
      fullName: "",
      email: "",
      password: "",
      confirmPassword: "",
    },
  });

  // Hàm xử lý khi submit form đăng ký
  const onSubmit = async (data: RegisterFormValues) => {
    setIsSubmitting(true);
    setErrorMessage(null);
    try {
      await authService.register({
        name: data.fullName,
        email: data.email,
        password: data.password,
      });

      toast.success(`Đăng ký hồ sơ y khoa thành công cho: ${data.fullName}! Vui lòng nhập mã OTP để kích hoạt.`);
      router.push(`/auth/verify-otp?email=${encodeURIComponent(data.email)}`);
    } catch (error) {
      console.error("Registration Error:", error);
      const msg = error instanceof Error ? error.message : "Đăng ký tài khoản thất bại. Vui lòng thử lại sau.";
      setErrorMessage(msg);
      toast.error(msg);
    } finally {
      setIsSubmitting(false);
    }
  };

  // Hàm xử lý đăng ký qua OAuth (Google & GitHub)
  const handleOAuthRegister = async (provider: "Google" | "GitHub") => {
    setIsSubmitting(true);
    setErrorMessage(null);
    try {
      toast.loading(`Đang kết nối sang cổng đăng ký xác thực ${provider}...`, { id: "oauth-reg-load" });
      const targetProvider = provider.toLowerCase() as "google" | "github";
      const res = await authService.getOAuthUrl(targetProvider);
      toast.dismiss("oauth-reg-load");
      if (res.url) {
        window.location.assign(res.url);
        setIsSubmitting(false);
      } else {
        throw new Error("Không nhận được URL xác thực từ máy chủ.");
      }
    } catch (error) {
      toast.dismiss("oauth-reg-load");
      const msg = error instanceof Error ? error.message : `Không thể kết nối sang cổng ${provider}.`;
      console.error("OAuth Init Error:", error);
      setErrorMessage(msg);
      toast.error(msg);
      setIsSubmitting(false);
    }
  };

  return (
    <div className="flex flex-col justify-center w-full font-sans">
      
      {/* HEADER */}
      <div className="mb-7 text-left">
        <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-sky-50 border border-sky-200 text-sky-700 text-xs font-bold mb-3 shadow-sm">
          <UserPlus className="w-3.5 h-3.5 text-sky-600" />
          <span>Đăng Ký Hồ Sơ Lâm Sàng Mới</span>
        </div>
        <h2 className="text-2xl sm:text-3xl font-extrabold text-foreground tracking-tight">
          Tạo Tài Khoản Hệ Thống
        </h2>
        <p className="mt-2 text-sm text-muted-foreground font-normal leading-relaxed">
          Được phân quyền thẩm định SBAR, tương tác với AI Triage và truy cập sổ kiểm toán y đức ACID.
        </p>
      </div>

      {/* FORM ĐĂNG KÝ */}
      <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
        
        {/* TRƯỜNG 1: HỌ VÀ TÊN */}
        <div className="space-y-1.5">
          <label 
            htmlFor="fullname-input" 
            className="block text-xs font-bold text-slate-700 uppercase tracking-wider dark:text-slate-200"
          >
            Họ và Tên Điều Dưỡng / Bác Sĩ
          </label>
          <div className="relative rounded-2xl shadow-sm transition-all duration-200">
            <div className="absolute inset-y-0 left-0 pl-4 flex items-center pointer-events-none text-slate-400">
              <User className="w-4 h-4" />
            </div>
            <input
              id="fullname-input"
              type="text"
              placeholder="BS. Nguyễn Văn An"
              disabled={isSubmitting}
              className={`w-full pl-11 pr-4 py-3.5 text-sm bg-slate-50 hover:bg-slate-100/70 focus:bg-white text-slate-900 placeholder-slate-400 font-medium rounded-2xl border transition-all duration-200 outline-none focus:ring-4 ${
                errors.fullName 
                  ? "border-rose-400 focus:border-rose-500 focus:ring-rose-500/15 text-rose-900" 
                  : "border-border focus:border-sky-500 focus:ring-sky-500/15"
              } disabled:opacity-50 disabled:cursor-not-allowed`}
              {...register("fullName")}
            />
          </div>
          {errors.fullName && (
            <p className="flex items-center gap-1.5 text-xs text-rose-600 font-semibold mt-1 animate-in fade-in slide-in-from-top-1 duration-200">
              <AlertCircle className="w-3.5 h-3.5 shrink-0" />
              <span>{errors.fullName.message}</span>
            </p>
          )}
        </div>

        {/* TRƯỜNG 2: EMAIL Y KHOA */}
        <div className="space-y-1.5">
          <label 
            htmlFor="email-input-register" 
            className="block text-xs font-bold text-slate-700 uppercase tracking-wider dark:text-slate-200"
          >
            Địa chỉ Email Lâm Sàng
          </label>
          <div className="relative rounded-2xl shadow-sm transition-all duration-200">
            <div className="absolute inset-y-0 left-0 pl-4 flex items-center pointer-events-none text-slate-400">
              <Mail className="w-4 h-4" />
            </div>
            <input
              id="email-input-register"
              type="email"
              placeholder="doctor.nguyen@vinai.io"
              disabled={isSubmitting}
              className={`w-full pl-11 pr-4 py-3.5 text-sm bg-slate-50 hover:bg-slate-100/70 focus:bg-white text-slate-900 placeholder-slate-400 font-medium rounded-2xl border transition-all duration-200 outline-none focus:ring-4 ${
                errors.email 
                  ? "border-rose-400 focus:border-rose-500 focus:ring-rose-500/15 text-rose-900" 
                  : "border-border focus:border-sky-500 focus:ring-sky-500/15"
              } disabled:opacity-50 disabled:cursor-not-allowed`}
              {...register("email")}
            />
          </div>
          {errors.email && (
            <p className="flex items-center gap-1.5 text-xs text-rose-600 font-semibold mt-1 animate-in fade-in slide-in-from-top-1 duration-200">
              <AlertCircle className="w-3.5 h-3.5 shrink-0" />
              <span>{errors.email.message}</span>
            </p>
          )}
        </div>

        {/* TRƯỜNG 3: MẬT KHẨU BẢO MẬT */}
        <div className="space-y-1.5">
          <label 
            htmlFor="password-input-register" 
            className="block text-xs font-bold text-slate-700 uppercase tracking-wider dark:text-slate-200"
          >
            Mật khẩu Bảo Mật
          </label>
          <div className="relative rounded-2xl shadow-sm transition-all duration-200">
            <div className="absolute inset-y-0 left-0 pl-4 flex items-center pointer-events-none text-slate-400">
              <Lock className="w-4 h-4" />
            </div>
            <input
              id="password-input-register"
              type={showPassword ? "text" : "password"}
              placeholder="•••••••••••• (Tối thiểu 8 ký tự)"
              disabled={isSubmitting}
              className={`w-full pl-11 pr-12 py-3.5 text-sm bg-slate-50 hover:bg-slate-100/70 focus:bg-white text-slate-900 placeholder-slate-400 font-medium rounded-2xl border transition-all duration-200 outline-none focus:ring-4 ${
                errors.password 
                  ? "border-rose-400 focus:border-rose-500 focus:ring-rose-500/15 text-rose-900" 
                  : "border-border focus:border-sky-500 focus:ring-sky-500/15"
              } disabled:opacity-50 disabled:cursor-not-allowed`}
              {...register("password")}
            />
            <button
              type="button"
              onClick={() => setShowPassword(!showPassword)}
              className="absolute inset-y-0 right-0 pr-4 flex items-center text-slate-400 hover:text-slate-700 focus:outline-none transition-colors dark:hover:text-slate-200"
              aria-label={showPassword ? "Ẩn mật khẩu" : "Hiện mật khẩu"}
            >
              {showPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
            </button>
          </div>
          {errors.password && (
            <p className="flex items-center gap-1.5 text-xs text-rose-600 font-semibold mt-1 animate-in fade-in slide-in-from-top-1 duration-200">
              <AlertCircle className="w-3.5 h-3.5 shrink-0" />
              <span>{errors.password.message}</span>
            </p>
          )}
        </div>

        {/* TRƯỜNG 4: XÁC NHẬN MẬT KHẨU */}
        <div className="space-y-1.5">
          <label 
            htmlFor="confirm-password-input" 
            className="block text-xs font-bold text-slate-700 uppercase tracking-wider dark:text-slate-200"
          >
            Xác nhận Mật khẩu
          </label>
          <div className="relative rounded-2xl shadow-sm transition-all duration-200">
            <div className="absolute inset-y-0 left-0 pl-4 flex items-center pointer-events-none text-slate-400">
              <Lock className="w-4 h-4" />
            </div>
            <input
              id="confirm-password-input"
              type={showConfirmPassword ? "text" : "password"}
              placeholder="Nhập lại chính xác mật khẩu trên"
              disabled={isSubmitting}
              className={`w-full pl-11 pr-12 py-3.5 text-sm bg-slate-50 hover:bg-slate-100/70 focus:bg-white text-slate-900 placeholder-slate-400 font-medium rounded-2xl border transition-all duration-200 outline-none focus:ring-4 ${
                errors.confirmPassword 
                  ? "border-rose-400 focus:border-rose-500 focus:ring-rose-500/15 text-rose-900" 
                  : "border-border focus:border-sky-500 focus:ring-sky-500/15"
              } disabled:opacity-50 disabled:cursor-not-allowed`}
              {...register("confirmPassword")}
            />
            <button
              type="button"
              onClick={() => setShowConfirmPassword(!showConfirmPassword)}
              className="absolute inset-y-0 right-0 pr-4 flex items-center text-slate-400 hover:text-slate-700 focus:outline-none transition-colors dark:hover:text-slate-200"
              aria-label={showConfirmPassword ? "Ẩn xác nhận mật khẩu" : "Hiện xác nhận mật khẩu"}
            >
              {showConfirmPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
            </button>
          </div>
          {errors.confirmPassword && (
            <p className="flex items-center gap-1.5 text-xs text-rose-600 font-semibold mt-1 animate-in fade-in slide-in-from-top-1 duration-200">
              <AlertCircle className="w-3.5 h-3.5 shrink-0" />
              <span>{errors.confirmPassword.message}</span>
            </p>
          )}
        </div>

        {/* THÔNG BÁO LỖI TỪ BACKEND FASTAPI */}
        {errorMessage && (
          <div className="p-3.5 rounded-2xl bg-rose-50 border border-rose-200 text-rose-800 text-xs font-bold flex items-center gap-2.5 animate-in slide-in-from-top-2 duration-200 shadow-xs">
            <AlertCircle className="w-4 h-4 shrink-0 text-rose-600" />
            <span>{errorMessage}</span>
          </div>
        )}

        {/* SUBMIT BUTTON */}
        <button
          type="submit"
          disabled={isSubmitting}
          className="w-full relative group overflow-hidden rounded-2xl p-px font-bold text-white shadow-[0_6px_25px_rgba(14,165,233,0.35)] transition-all duration-300 hover:shadow-[0_8px_35px_rgba(14,165,233,0.45)] hover:scale-[1.01] active:scale-[0.99] disabled:opacity-60 disabled:pointer-events-none mt-3"
        >
          <div className="absolute inset-0 bg-gradient-to-r from-sky-600 via-indigo-600 to-sky-600 rounded-2xl transition-all duration-300 group-hover:opacity-90" />
          
          <div className="relative px-6 py-4 rounded-2xl flex items-center justify-center gap-2 text-sm">
            {isSubmitting ? (
              <>
                <Loader2 className="w-4 h-4 animate-spin shrink-0" />
                <span className="font-bold tracking-wide">ĐANG TẠO HỒ SƠ Y KHOA...</span>
              </>
            ) : (
              <>
                <span className="font-extrabold tracking-wide uppercase text-sm">Đăng Ký Tài Khoản</span>
                <ArrowRight className="w-4 h-4 transition-transform duration-200 group-hover:translate-x-1" />
              </>
            )}
          </div>
        </button>
      </form>

      {/* DIVIDER - HOẶC ĐĂNG KÝ BẰNG */}
      <div className="relative my-7">
        <div className="absolute inset-0 flex items-center">
          <span className="w-full border-t border-border" />
        </div>
        <div className="relative flex justify-center text-[11px] uppercase tracking-wider">
          <span className="bg-card px-3 text-slate-400 font-mono font-bold">
            Hoặc tiếp tục với
          </span>
        </div>
      </div>

      {/* 2 OAUTH BUTTONS (Google & GitHub) */}
      <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
        <button
          type="button"
          onClick={() => handleOAuthRegister("Google")}
          disabled={isSubmitting}
          className="flex min-h-[52px] items-center justify-center gap-3 rounded-2xl border border-slate-300 bg-card px-4 py-3.5 text-sm font-bold text-slate-800 shadow-2xs transition-all duration-200 hover:border-slate-400 hover:bg-background disabled:cursor-not-allowed disabled:opacity-50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-sky-600 focus-visible:ring-offset-2 dark:text-slate-100 dark:border-slate-700"
        >
          <GoogleMark />
          <span>Tiếp tục với Google</span>
        </button>

        <button
          type="button"
          onClick={() => handleOAuthRegister("GitHub")}
          disabled={isSubmitting}
          className="flex min-h-[52px] items-center justify-center gap-3 rounded-2xl border border-slate-900 bg-slate-900 px-4 py-3.5 text-sm font-bold text-white shadow-2xs transition-all duration-200 hover:bg-slate-800 disabled:cursor-not-allowed disabled:opacity-50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-slate-900 focus-visible:ring-offset-2"
        >
          <GitHubMark />
          <span>Tiếp tục với GitHub</span>
        </button>
      </div>

      {/* LOGIN REDIRECT LINK */}
      <div className="mt-8 text-center">
        <p className="text-xs text-muted-foreground font-medium">
          Đã có tài khoản y khoa?{" "}
          <Link
            href="/auth/login"
            className="font-extrabold text-sky-600 hover:text-sky-700 transition-colors underline decoration-sky-300 underline-offset-4"
          >
            Đăng nhập tại đây
          </Link>
        </p>
      </div>


    </div>
  );
}
