"use client";

import React, { useState, useRef, useEffect, useCallback, KeyboardEvent, ClipboardEvent } from "react";
import Link from "next/link";
import { authService } from "@/services/auth.service";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import * as z from "zod";
import {
  Mail,
  Loader2,
  CheckCircle2,
  KeyRound,
  AlertCircle,
  ArrowLeft,
  ArrowRight,
  RotateCw,
  Lock,
  Eye,
  EyeOff,
  ShieldCheck
} from "lucide-react";

// ============================================================================
// 1. ZOD VALIDATION SCHEMAS CHO CÁC BƯỚC KHÔI PHỤC MẬT KHẨU
// ============================================================================

// Schema Bước 1: Nhập Email
const emailStepSchema = z.object({
  email: z
    .string()
    .min(1, "Vui lòng nhập địa chỉ Email của bạn.")
    .email("Địa chỉ Email y khoa không đúng định dạng hợp lệ."),
});
type EmailStepValues = z.infer<typeof emailStepSchema>;

// Schema Bước 3: Đặt Mật Khẩu Mới
const newPasswordSchema = z
  .object({
    newPassword: z
      .string()
      .min(8, "Mật khẩu bảo mật mới bắt buộc có độ dài tối thiểu 8 ký tự."),
    confirmPassword: z
      .string()
      .min(1, "Vui lòng nhập lại mật khẩu xác nhận."),
  })
  .refine((data) => data.newPassword === data.confirmPassword, {
    message: "Mật khẩu xác nhận không khớp với mật khẩu mới vừa nhập.",
    path: ["confirmPassword"],
  });
type NewPasswordValues = z.infer<typeof newPasswordSchema>;

// ============================================================================
// 2. COMPONENT KHÔI PHỤC MẬT KHẨU 4 BƯỚC TÍCH HỢP MÃ OTP 6 CHỮ SỐ
// ============================================================================
export default function ForgotPasswordPage() {
  // Quản lý bước hiện tại: EMAIL -> OTP -> NEW_PASSWORD -> SUCCESS
  const [step, setStep] = useState<"EMAIL" | "OTP" | "NEW_PASSWORD" | "SUCCESS">("EMAIL");
  const [submittedEmail, setSubmittedEmail] = useState("");

  // States cho loading và mật khẩu hiển thị
  const [isSubmittingEmail, setIsSubmittingEmail] = useState(false);
  const [isVerifyingOtp, setIsVerifyingOtp] = useState(false);
  const [isSubmittingNewPass, setIsSubmittingNewPass] = useState(false);
  const [otpError, setOtpError] = useState<string | null>(null);
  const [showNewPass, setShowNewPass] = useState(false);
  const [showConfirmPass, setShowConfirmPass] = useState(false);

  // Mảng lưu giá trị 6 ô OTP & Refs
  const [otp, setOtp] = useState<string[]>(new Array(6).fill(""));
  const inputRefs = useRef<(HTMLInputElement | null)[]>([]);

  // Đồng hồ đếm ngược 60 giây cho OTP
  const [timeLeft, setTimeLeft] = useState(60);

  // Form Bước 1: Email
  const {
    register: registerEmail,
    handleSubmit: handleSubmitEmail,
    formState: { errors: emailErrors },
  } = useForm<EmailStepValues>({
    resolver: zodResolver(emailStepSchema),
    defaultValues: { email: "" },
  });

  // Form Bước 3: New Password
  const {
    register: registerNewPass,
    handleSubmit: handleSubmitNewPass,
    formState: { errors: passErrors },
  } = useForm<NewPasswordValues>({
    resolver: zodResolver(newPasswordSchema),
    defaultValues: { newPassword: "", confirmPassword: "" },
  });

  /* =========================================================================
   * LOGIC ĐỒNG HỒ ĐẾM NGƯỢC LÂM SÀNG 60S (CHỈ KÍCH HOẠT Ở BƯỚC OTP)
   * ========================================================================= */
  useEffect(() => {
    if (step !== "OTP" || timeLeft <= 0) return;
    const interval = setInterval(() => {
      setTimeLeft((prev) => prev - 1);
    }, 1000);
    return () => clearInterval(interval);
  }, [step, timeLeft]);

  // Tự động focus ô OTP đầu tiên ngay khi bước chuyển sang "OTP"
  useEffect(() => {
    if (step === "OTP") {
      setTimeout(() => {
        inputRefs.current[0]?.focus();
      }, 50);
    }
  }, [step]);

  /* =========================================================================
   * XỬ LÝ BƯỚC 1: SUBMIT EMAIL YÊU CẦU MÃ OTP
   * ========================================================================= */
  const onEmailSubmit = async (data: EmailStepValues) => {
    setIsSubmittingEmail(true);
    try {
      await authService.forgotPassword({ email: data.email });
      setSubmittedEmail(data.email);
      setTimeLeft(60);
      setOtp(new Array(6).fill(""));
      setStep("OTP");
    } catch (error) {
      console.error("Email Step Error:", error);
      alert(error instanceof Error ? error.message : "Yêu cầu khôi phục mật khẩu thất bại. Vui lòng thử lại.");
    } finally {
      setIsSubmittingEmail(false);
    }
  };

  /* =========================================================================
   * XỬ LÝ BƯỚC 2: THẨM ĐỊNH MÃ OTP 6 CHỮ SỐ
   * ========================================================================= */
  const verifyOTP = useCallback(async (code: string) => {
    setIsVerifyingOtp(true);
    setOtpError(null);
    try {
      await authService.verifyOtp({
        email: submittedEmail || undefined,
        code: code,
        purpose: "PASSWORD_RESET",
      });

      setIsVerifyingOtp(false);
      setStep("NEW_PASSWORD");
    } catch (error) {
      console.error("OTP Recovery Error:", error);
      setOtpError(error instanceof Error ? error.message : "Mã OTP khôi phục không hợp lệ hoặc sự cố kết nối Server.");
      setIsVerifyingOtp(false);
      setOtp(new Array(6).fill(""));
      if (inputRefs.current[0]) {
        inputRefs.current[0]?.focus();
      }
    }
  }, [submittedEmail]);

  const handleOtpInput = (index: number, value: string) => {
    const cleanValue = value.replace(/[^0-9]/g, "");
    if (cleanValue.length === 0) {
      const newOtp = [...otp];
      newOtp[index] = "";
      setOtp(newOtp);
      setOtpError(null);
      return;
    }

    const digit = cleanValue.slice(-1);
    const newOtp = [...otp];
    newOtp[index] = digit;
    setOtp(newOtp);
    setOtpError(null);

    if (index < 5) {
      inputRefs.current[index + 1]?.focus();
    }
    if (newOtp.every((val) => val !== "")) {
      verifyOTP(newOtp.join(""));
    }
  };

  const handleOtpKeyDown = (index: number, e: KeyboardEvent<HTMLInputElement>) => {
    if (e.key === "Backspace") {
      if (otp[index] === "" && index > 0) {
        const newOtp = [...otp];
        newOtp[index - 1] = "";
        setOtp(newOtp);
        inputRefs.current[index - 1]?.focus();
      } else {
        const newOtp = [...otp];
        newOtp[index] = "";
        setOtp(newOtp);
      }
      setOtpError(null);
    } else if (e.key === "ArrowLeft" && index > 0) {
      inputRefs.current[index - 1]?.focus();
    } else if (e.key === "ArrowRight" && index < 5) {
      inputRefs.current[index + 1]?.focus();
    }
  };

  const handleOtpPaste = (e: ClipboardEvent<HTMLInputElement>) => {
    e.preventDefault();
    const pastedData = e.clipboardData.getData("text").replace(/[^0-9]/g, "").slice(0, 6);
    if (pastedData.length > 0) {
      const newOtp = [...otp];
      for (let i = 0; i < pastedData.length; i++) {
        if (i < 6) newOtp[i] = pastedData[i];
      }
      setOtp(newOtp);
      setOtpError(null);

      const nextFocusIndex = Math.min(pastedData.length, 5);
      inputRefs.current[nextFocusIndex]?.focus();

      if (newOtp.every((val) => val !== "")) {
        verifyOTP(newOtp.join(""));
      }
    }
  };

  const resendOTP = () => {
    if (timeLeft > 0 || isVerifyingOtp) return;
    setTimeLeft(60);
    setOtpError(null);
    setOtp(new Array(6).fill(""));
    inputRefs.current[0]?.focus();
    alert(`Mã OTP khôi phục mới (6 chữ số) đã được gửi lại tới email: ${submittedEmail}`);
  };

  /* =========================================================================
   * XỬ LÝ BƯỚC 3: SUBMIT MẬT KHẨU MỚI
   * ========================================================================= */
  const onNewPasswordSubmit = async (data: NewPasswordValues) => {
    setIsSubmittingNewPass(true);
    try {
      await authService.resetPassword({
        email: submittedEmail || undefined,
        otp: otp.join(""),
        newPassword: data.newPassword,
      });
      setStep("SUCCESS");
    } catch (error) {
      console.error("Password Update Error:", error);
      alert(error instanceof Error ? error.message : "Cập nhật mật khẩu thất bại. Vui lòng thử lại sau.");
    } finally {
      setIsSubmittingNewPass(false);
    }
  };

  return (
    <div className="flex flex-col justify-center w-full font-sans">
      
      {/* =====================================================================
       * BƯỚC 1: NHẬP EMAIL Y KHOA ĐỂ YÊU CẦU MÃ OTP
       * ===================================================================== */}
      {step === "EMAIL" && (
        <div className="space-y-6 animate-in fade-in-50 duration-300">
          <div className="text-left">
            <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-sky-50 border border-sky-200 text-sky-700 text-xs font-bold mb-3 shadow-xs">
              <KeyRound className="w-3.5 h-3.5 text-sky-600" />
              <span>Khôi Phục Quyền Truy Cập Lâm Sàng</span>
            </div>
            <h2 className="text-2xl sm:text-3xl font-extrabold text-foreground tracking-tight">
              Quên Mật Khẩu?
            </h2>
            <p className="mt-2 text-sm text-muted-foreground font-normal leading-relaxed">
              Nhập địa chỉ email của bạn để hệ thống phát hành mã bảo mật OTP 6 chữ số nhằm đặt lại mật khẩu an toàn.
            </p>
          </div>

          <form onSubmit={handleSubmitEmail(onEmailSubmit)} className="space-y-5">
            <div className="space-y-1.5">
              <label 
                htmlFor="email-input-reset" 
                className="block text-xs font-bold text-slate-700 uppercase tracking-wider dark:text-slate-200"
              >
                Địa chỉ Email Y Khoa Đã Đăng Ký
              </label>
              <div className="relative rounded-2xl shadow-sm transition-all duration-200">
                <div className="absolute inset-y-0 left-0 pl-4 flex items-center pointer-events-none text-slate-400">
                  <Mail className="w-4 h-4" />
                </div>
                <input
                  id="email-input-reset"
                  type="email"
                  placeholder="doctor.nguyen@vinai.io"
                  disabled={isSubmittingEmail}
                  className={`w-full pl-11 pr-4 py-3.5 text-sm bg-slate-50 hover:bg-slate-100/70 focus:bg-white text-slate-900 placeholder-slate-400 font-medium rounded-2xl border transition-all duration-200 outline-none focus:ring-4 ${
                    emailErrors.email 
                      ? "border-rose-400 focus:border-rose-500 focus:ring-rose-500/15 text-rose-900" 
                      : "border-border focus:border-sky-500 focus:ring-sky-500/15"
                  } disabled:opacity-50 disabled:cursor-not-allowed`}
                  {...registerEmail("email")}
                />
              </div>
              {emailErrors.email && (
                <p className="flex items-center gap-1.5 text-xs text-rose-600 font-semibold mt-1 animate-in fade-in slide-in-from-top-1 duration-200">
                  <AlertCircle className="w-3.5 h-3.5 shrink-0" />
                  <span>{emailErrors.email.message}</span>
                </p>
              )}
            </div>

            <button
              type="submit"
              disabled={isSubmittingEmail}
              className="w-full relative group overflow-hidden rounded-2xl p-px font-bold text-white shadow-[0_6px_25px_rgba(14,165,233,0.35)] transition-all duration-300 hover:shadow-[0_8px_35px_rgba(14,165,233,0.45)] hover:scale-[1.01] active:scale-[0.99] disabled:opacity-60 disabled:pointer-events-none mt-2"
            >
              <div className="absolute inset-0 bg-gradient-to-r from-sky-600 via-indigo-600 to-sky-600 rounded-2xl transition-all duration-300 group-hover:opacity-90" />
              
              <div className="relative px-6 py-4 rounded-2xl flex items-center justify-center gap-2 text-sm">
                {isSubmittingEmail ? (
                  <>
                    <Loader2 className="w-4 h-4 animate-spin shrink-0" />
                    <span className="font-bold tracking-wide">ĐANG PHÁT HÀNH MÃ OTP...</span>
                  </>
                ) : (
                  <>
                    <span className="font-extrabold tracking-wide uppercase text-sm">Gửi Mã OTP Khôi Phục</span>
                    <ArrowRight className="w-4 h-4 transition-transform duration-200 group-hover:translate-x-1" />
                  </>
                )}
              </div>
            </button>
          </form>
        </div>
      )}

      {/* =====================================================================
       * BƯỚC 2: NHẬP VÀ THẨM ĐỊNH MÃ OTP 6 CHỮ SỐ
       * ===================================================================== */}
      {step === "OTP" && (
        <div className="space-y-6 animate-in zoom-in-95 fade-in duration-300">
          <div className="text-left">
            <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-sky-50 border border-sky-200 text-sky-700 text-xs font-bold mb-3 shadow-xs">
              <ShieldCheck className="w-3.5 h-3.5 text-sky-600 animate-pulse" />
              <span>Xác Thực Danh Tính 2 Lớp</span>
            </div>
            <h2 className="text-2xl sm:text-3xl font-extrabold text-foreground tracking-tight">
              Nhập Mã Bảo Mật OTP
            </h2>
            <p className="mt-2 text-sm text-muted-foreground font-normal leading-relaxed">
              Mã xác minh 6 chữ số đã được chuyển tới email <span className="font-bold text-foreground bg-muted px-2 py-0.5 rounded-md">{submittedEmail}</span>. Vui lòng nhập để tiếp tục.
            </p>
          </div>

          <div className="space-y-4 pt-2">
            <div className="flex items-center justify-between gap-2 sm:gap-3 max-w-sm mx-auto sm:mx-0">
              {otp.map((digit, idx) => (
                <input
                  key={idx}
                  ref={(el) => {
                    inputRefs.current[idx] = el;
                  }}
                  type="text"
                  inputMode="numeric"
                  autoComplete="one-time-code"
                  maxLength={1}
                  value={digit}
                  disabled={isVerifyingOtp}
                  onChange={(e) => handleOtpInput(idx, e.target.value)}
                  onKeyDown={(e) => handleOtpKeyDown(idx, e)}
                  onPaste={handleOtpPaste}
                  className={`w-11 h-13 sm:w-13 sm:h-16 text-center text-xl sm:text-2xl font-black font-mono rounded-2xl bg-slate-50 hover:bg-slate-100/80 focus:bg-white text-slate-900 border transition-all duration-200 outline-none shadow-sm focus:ring-4 focus:ring-offset-2 focus:ring-offset-white ${
                    otpError
                      ? "border-rose-400 focus:border-rose-500 focus:ring-rose-500/20 text-rose-700 bg-rose-50/50"
                      : "border-border/90 focus:border-sky-500 focus:ring-sky-500/20"
                  } disabled:opacity-50 disabled:cursor-not-allowed`}
                />
              ))}
            </div>

            {otpError && (
              <div className="p-3 rounded-2xl bg-rose-50 border border-rose-200 text-rose-700 text-xs font-bold flex items-center gap-2 animate-in slide-in-from-top-2 duration-200">
                <AlertCircle className="w-4 h-4 shrink-0 text-rose-600" />
                <span>{otpError}</span>
              </div>
            )}

            {isVerifyingOtp && (
              <div className="flex items-center justify-center gap-2.5 py-3 text-sm font-extrabold text-sky-700 bg-sky-50/80 rounded-2xl border border-sky-100 animate-pulse">
                <Loader2 className="w-5 h-5 animate-spin text-sky-600" />
                <span>Đang kiểm định mã OTP lâm sàng...</span>
              </div>
            )}
          </div>

          <div className="flex flex-col sm:flex-row items-center justify-between gap-3 pt-4 border-t border-slate-100 text-xs sm:text-sm font-medium">
            <button
              type="button"
              onClick={() => setStep("EMAIL")}
              className="text-muted-foreground hover:text-slate-800 transition-colors font-semibold underline decoration-slate-300 underline-offset-4 dark:hover:text-slate-100"
            >
              Nhập lại địa chỉ email khác
            </button>

            <button
              type="button"
              onClick={resendOTP}
              disabled={timeLeft > 0 || isVerifyingOtp}
              className={`inline-flex items-center justify-center gap-2 px-4 py-2 rounded-xl text-xs font-extrabold transition-all duration-200 ${
                timeLeft > 0
                  ? "bg-muted text-slate-400 cursor-not-allowed border border-border font-mono"
                  : "bg-sky-50 text-sky-700 hover:bg-sky-100 border border-sky-200 shadow-xs hover:scale-[1.02] active:scale-[0.98]"
              }`}
            >
              <RotateCw className={`w-3.5 h-3.5 shrink-0 ${timeLeft > 0 ? "opacity-40" : "text-sky-600 animate-spin-slow"}`} />
              <span>
                {timeLeft > 0 ? `Gửi lại mã sau (${timeLeft}s)` : "Gửi lại mã OTP ngay"}
              </span>
            </button>
          </div>
        </div>
      )}

      {/* =====================================================================
       * BƯỚC 3: ĐẶT MẬT KHẨU MỚI & XÁC NHẬN
       * ===================================================================== */}
      {step === "NEW_PASSWORD" && (
        <div className="space-y-6 animate-in slide-in-from-right-4 fade-in duration-300">
          <div className="text-left">
            <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-emerald-50 border border-emerald-200 text-emerald-700 text-xs font-bold mb-3 shadow-xs">
              <CheckCircle2 className="w-3.5 h-3.5 text-emerald-600" />
              <span>Mã OTP Hợp Lệ — Cho Phép Đổi Mật Khẩu</span>
            </div>
            <h2 className="text-2xl sm:text-3xl font-extrabold text-foreground tracking-tight">
              Thiết Lập Mật Khẩu Mới
            </h2>
            <p className="mt-2 text-sm text-muted-foreground font-normal leading-relaxed">
              Vui lòng đặt mật khẩu mới với tiêu chuẩn bảo mật tối thiểu 8 ký tự để bảo vệ dữ liệu bệnh án điện tử (PHI).
            </p>
          </div>

          <form onSubmit={handleSubmitNewPass(onNewPasswordSubmit)} className="space-y-4">
            {/* TRƯỜNG 1: MẬT KHẨU MỚI */}
            <div className="space-y-1.5">
              <label 
                htmlFor="new-password-input" 
                className="block text-xs font-bold text-slate-700 uppercase tracking-wider dark:text-slate-200"
              >
                Mật khẩu mới (Tối thiểu 8 ký tự)
              </label>
              <div className="relative rounded-2xl shadow-sm transition-all duration-200">
                <div className="absolute inset-y-0 left-0 pl-4 flex items-center pointer-events-none text-slate-400">
                  <Lock className="w-4 h-4" />
                </div>
                <input
                  id="new-password-input"
                  type={showNewPass ? "text" : "password"}
                  placeholder="••••••••••••"
                  disabled={isSubmittingNewPass}
                  className={`w-full pl-11 pr-12 py-3.5 text-sm bg-slate-50 hover:bg-slate-100/70 focus:bg-white text-slate-900 placeholder-slate-400 font-medium rounded-2xl border transition-all duration-200 outline-none focus:ring-4 ${
                    passErrors.newPassword 
                      ? "border-rose-400 focus:border-rose-500 focus:ring-rose-500/15 text-rose-900" 
                      : "border-border focus:border-sky-500 focus:ring-sky-500/15"
                  } disabled:opacity-50 disabled:cursor-not-allowed`}
                  {...registerNewPass("newPassword")}
                />
                <button
                  type="button"
                  onClick={() => setShowNewPass(!showNewPass)}
                  className="absolute inset-y-0 right-0 pr-4 flex items-center text-slate-400 hover:text-slate-700 focus:outline-none transition-colors dark:hover:text-slate-200"
                >
                  {showNewPass ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                </button>
              </div>
              {passErrors.newPassword && (
                <p className="flex items-center gap-1.5 text-xs text-rose-600 font-semibold mt-1">
                  <AlertCircle className="w-3.5 h-3.5 shrink-0" />
                  <span>{passErrors.newPassword.message}</span>
                </p>
              )}
            </div>

            {/* TRƯỜNG 2: XÁC NHẬN MẬT KHẨU MỚI */}
            <div className="space-y-1.5">
              <label 
                htmlFor="confirm-new-password-input" 
                className="block text-xs font-bold text-slate-700 uppercase tracking-wider dark:text-slate-200"
              >
                Xác nhận Mật khẩu Mới
              </label>
              <div className="relative rounded-2xl shadow-sm transition-all duration-200">
                <div className="absolute inset-y-0 left-0 pl-4 flex items-center pointer-events-none text-slate-400">
                  <Lock className="w-4 h-4" />
                </div>
                <input
                  id="confirm-new-password-input"
                  type={showConfirmPass ? "text" : "password"}
                  placeholder="Nhập lại chính xác mật khẩu mới"
                  disabled={isSubmittingNewPass}
                  className={`w-full pl-11 pr-12 py-3.5 text-sm bg-slate-50 hover:bg-slate-100/70 focus:bg-white text-slate-900 placeholder-slate-400 font-medium rounded-2xl border transition-all duration-200 outline-none focus:ring-4 ${
                    passErrors.confirmPassword 
                      ? "border-rose-400 focus:border-rose-500 focus:ring-rose-500/15 text-rose-900" 
                      : "border-border focus:border-sky-500 focus:ring-sky-500/15"
                  } disabled:opacity-50 disabled:cursor-not-allowed`}
                  {...registerNewPass("confirmPassword")}
                />
                <button
                  type="button"
                  onClick={() => setShowConfirmPass(!showConfirmPass)}
                  className="absolute inset-y-0 right-0 pr-4 flex items-center text-slate-400 hover:text-slate-700 focus:outline-none transition-colors dark:hover:text-slate-200"
                >
                  {showConfirmPass ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                </button>
              </div>
              {passErrors.confirmPassword && (
                <p className="flex items-center gap-1.5 text-xs text-rose-600 font-semibold mt-1">
                  <AlertCircle className="w-3.5 h-3.5 shrink-0" />
                  <span>{passErrors.confirmPassword.message}</span>
                </p>
              )}
            </div>

            <button
              type="submit"
              disabled={isSubmittingNewPass}
              className="w-full relative group overflow-hidden rounded-2xl p-px font-bold text-white shadow-[0_6px_25px_rgba(14,165,233,0.35)] transition-all duration-300 hover:shadow-[0_8px_35px_rgba(14,165,233,0.45)] hover:scale-[1.01] active:scale-[0.99] disabled:opacity-60 disabled:pointer-events-none mt-3"
            >
              <div className="absolute inset-0 bg-gradient-to-r from-sky-600 via-indigo-600 to-sky-600 rounded-2xl transition-all duration-300 group-hover:opacity-90" />
              
              <div className="relative px-6 py-4 rounded-2xl flex items-center justify-center gap-2 text-sm">
                {isSubmittingNewPass ? (
                  <>
                    <Loader2 className="w-4 h-4 animate-spin shrink-0" />
                    <span className="font-bold tracking-wide">ĐANG TÁI KÝ BẮT CUỘT...</span>
                  </>
                ) : (
                  <>
                    <span className="font-extrabold tracking-wide uppercase text-sm">Cập Nhật Mật Khẩu Mới</span>
                    <ArrowRight className="w-4 h-4 transition-transform duration-200 group-hover:translate-x-1" />
                  </>
                )}
              </div>
            </button>
          </form>
        </div>
      )}

      {/* =====================================================================
       * BƯỚC 4: THÔNG BÁO THÀNH CÔNG (SUCCESS VERIFICATION BANNER)
       * ===================================================================== */}
      {step === "SUCCESS" && (
        <div className="text-center space-y-6 py-4 animate-in zoom-in-95 duration-400">
          <div className="mx-auto flex h-24 w-24 items-center justify-center rounded-3xl bg-emerald-50 border-2 border-emerald-300 text-emerald-600 shadow-[0_10px_35px_rgba(16,185,129,0.25)]">
            <CheckCircle2 className="w-12 h-12 animate-in zoom-in-50 duration-300" />
          </div>
          <div className="space-y-2">
            <h2 className="text-2xl sm:text-3xl font-extrabold text-foreground tracking-tight">
              Đổi Mật Khẩu Thành Công!
            </h2>
            <p className="text-sm text-slate-600 leading-relaxed max-w-sm mx-auto font-normal dark:text-slate-300">
              Mật khẩu cho tài khoản <span className="font-bold text-foreground bg-muted px-2 py-0.5 rounded-md">{submittedEmail}</span> đã được cập nhật thành công theo tiêu chuẩn bảo mật y đức ACID.
            </p>
          </div>
          <div className="pt-2">
            <Link
              href="/auth/login"
              className="inline-flex items-center justify-center gap-2 w-full px-8 py-4 rounded-2xl text-sm font-extrabold text-white bg-gradient-to-r from-emerald-600 to-teal-600 shadow-[0_6px_25px_rgba(16,185,129,0.35)] hover:shadow-lg transition-all duration-200 transform hover:scale-[1.02]"
            >
              <span>Đăng Nhập Ngay Với Mật Khẩu Mới</span>
              <ArrowRight className="w-4 h-4" />
            </Link>
          </div>
        </div>
      )}

      {/* =====================================================================
       * ĐIỀU HƯỚNG DƯỚI CÙNG & NÚT CẤP CỨU (LUÔN TỒN TẠI TẠI CẢ 4 BƯỚC)
       * ===================================================================== */}
      <div className="mt-8 pt-6 border-t border-slate-100 text-center space-y-5">
        
        {step !== "SUCCESS" && (
          <Link
            href="/auth/login"
            className="group inline-flex items-center justify-center gap-2 text-xs sm:text-sm font-bold text-sky-600 hover:text-sky-700 transition-all hover:translate-x-[-2px]"
          >
            <ArrowLeft className="w-4 h-4 text-sky-600 group-hover:translate-x-[-3px] transition-transform duration-200" />
            <span className="underline decoration-sky-300 underline-offset-4 font-extrabold">
              Quay lại trang Đăng nhập
            </span>
          </Link>
        )}


      </div>

    </div>
  );
}
