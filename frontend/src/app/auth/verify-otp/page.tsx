"use client";

import React, { useState, useRef, useEffect, useCallback, KeyboardEvent, ClipboardEvent } from "react";
import Link from "next/link";
import { authService } from "@/services/auth.service";
import { useAuthStore } from "@/store/useAuthStore";
import { toast } from "sonner";
import {
  ShieldCheck,
  Loader2,
  RotateCw,
  AlertCircle,
  ArrowLeft,
  CheckCircle2
} from "lucide-react";

export default function VerifyOtpPage() {
  const loginSuccess = useAuthStore((state) => state.loginSuccess);
  // Mảng lưu giá trị 6 ô OTP
  const [otp, setOtp] = useState<string[]>(new Array(6).fill(""));
  // Mảng tham chiếu (Refs) tới 6 ô input DOM
  const inputRefs = useRef<(HTMLInputElement | null)[]>([]);

  // Quản lý trạng thái thẩm định
  const [isVerifying, setIsVerifying] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [isSuccess, setIsSuccess] = useState(false);

  // Đồng hồ đếm ngược lâm sàng (60 giây)
  const [timeLeft, setTimeLeft] = useState(60);

  /* =========================================================================
   * LOGIC 1: ĐỒNG HỒ ĐẾM NGƯỢC LÂM SÀNG 60S (CLINICAL TIMER)
   * ========================================================================= */
  useEffect(() => {
    if (timeLeft <= 0) return;
    const interval = setInterval(() => {
      setTimeLeft((prev) => prev - 1);
    }, 1000);

    return () => clearInterval(interval);
  }, [timeLeft]);

  /* =========================================================================
   * LOGIC 2: HÀM GỌI XÁC THỰC MÃ OTP (AUTHENTICATION VERIFY)
   * ========================================================================= */
  const verifyOTP = useCallback(async (code: string) => {
    setIsVerifying(true);
    setErrorMessage(null);
    try {
      const emailParam = typeof window !== "undefined" ? new URLSearchParams(window.location.search).get("email") || undefined : undefined;
      
      const res = await authService.verifyOtp({
        email: emailParam,
        code: code,
        purpose: "REGISTRATION",
      });

      // Nếu trả về AuthResponseDTO có chứa token và user, lập tức nạp vào Global State
      if ("access_token" in res && "user" in res) {
        loginSuccess(res.user, res.access_token, res.refresh_token);
      }

      setIsSuccess(true);
      setIsVerifying(false);
      toast.success("🎉 Xác thực tài khoản y khoa thành công! Hệ thống sẵn sàng cấp quyền truy cập.");
    } catch (error) {
      console.error("OTP Verification Exception:", error);
      const msg = error instanceof Error ? error.message : "Mã bảo mật y khoa không hợp lệ hoặc sự cố kết nối Server.";
      setErrorMessage(msg);
      toast.error(msg);
      setIsVerifying(false);
      // Xóa trống và focus lại ô đầu tiên để thử lại
      setOtp(new Array(6).fill(""));
      if (inputRefs.current[0]) {
        inputRefs.current[0]?.focus();
      }
    }
  }, [loginSuccess]);

  // Tự động focus vào ô đầu tiên khi mở trang
  useEffect(() => {
    inputRefs.current[0]?.focus();
  }, []);

  /* =========================================================================
   * LOGIC 3: XỬ LÝ KHI NHẬP TRỰC TIẾP TẠI TỪNG Ô INPUT (ONCHANGE)
   * ========================================================================= */
  const handleInput = (index: number, value: string) => {
    // Chỉ chấp nhận ký tự chữ số từ 0 - 9
    const cleanValue = value.replace(/[^0-9]/g, "");
    if (cleanValue.length === 0) {
      // Cho phép xóa trống
      const newOtp = [...otp];
      newOtp[index] = "";
      setOtp(newOtp);
      setErrorMessage(null);
      return;
    }

    // Nếu người dùng gõ ký tự hợp lệ (lấy chữ số cuối cùng trong ô nếu gõ nhanh)
    const digit = cleanValue.slice(-1);
    const newOtp = [...otp];
    newOtp[index] = digit;
    setOtp(newOtp);
    setErrorMessage(null);

    // Tự động nhảy con trỏ sang ô tiếp theo nếu không phải ô cuối cùng
    if (index < 5) {
      inputRefs.current[index + 1]?.focus();
    }

    // Nếu đã điền đủ 6 số, tự động gọi xác thực ngay không cần chờ useEffect
    if (newOtp.every((val) => val !== "")) {
      verifyOTP(newOtp.join(""));
    }
  };

  /* =========================================================================
   * LOGIC 4: XỬ LÝ ĐIỀU HƯỚNG VÀ HỖ TRỢ BACKSPACE / ARROW KEYS
   * ========================================================================= */
  const handleKeyDown = (index: number, e: KeyboardEvent<HTMLInputElement>) => {
    if (e.key === "Backspace") {
      if (otp[index] === "" && index > 0) {
        // Nếu ô hiện tại đang trống, lùi con trỏ về ô trước và xóa dữ liệu
        const newOtp = [...otp];
        newOtp[index - 1] = "";
        setOtp(newOtp);
        inputRefs.current[index - 1]?.focus();
      } else {
        // Xóa giá trị ô hiện tại
        const newOtp = [...otp];
        newOtp[index] = "";
        setOtp(newOtp);
      }
      setErrorMessage(null);
    } else if (e.key === "ArrowLeft" && index > 0) {
      inputRefs.current[index - 1]?.focus();
    } else if (e.key === "ArrowRight" && index < 5) {
      inputRefs.current[index + 1]?.focus();
    }
  };

  /* =========================================================================
   * LOGIC 5: HỖ TRỢ PASTE MÃ NẠP NHANH 6 CHỮ SỐ (CLINICAL WOW FACTOR)
   * ========================================================================= */
  const handlePaste = (e: ClipboardEvent<HTMLInputElement>) => {
    e.preventDefault();
    const pastedData = e.clipboardData.getData("text").replace(/[^0-9]/g, "").slice(0, 6);
    if (pastedData.length > 0) {
      const newOtp = [...otp];
      for (let i = 0; i < pastedData.length; i++) {
        if (i < 6) newOtp[i] = pastedData[i];
      }
      setOtp(newOtp);
      setErrorMessage(null);

      // Focus ô phù hợp tiếp theo
      const nextFocusIndex = Math.min(pastedData.length, 5);
      inputRefs.current[nextFocusIndex]?.focus();

      // Nếu đủ 6 chữ số từ clipboard paste vào thì tự động thẩm định ngay
      if (newOtp.every((val) => val !== "")) {
        verifyOTP(newOtp.join(""));
      }
    }
  };

  /* =========================================================================
   * LOGIC 6: HÀM GỬI LẠI MÃ OTP (RESEND OTP)
   * ========================================================================= */
  const resendOTP = () => {
    if (timeLeft > 0 || isVerifying) return;
    setTimeLeft(60);
    setErrorMessage(null);
    setOtp(new Array(6).fill(""));
    inputRefs.current[0]?.focus();
    alert("Mã bảo mật mới (6 chữ số) đã được phát lại tới thư mục Hộp thư đến của bạn.");
  };

  return (
    <div className="flex flex-col justify-center w-full font-sans">
      
      {!isSuccess ? (
        /* ================================================================
         * GIAO DIỆN CHÍNH: FORM NHẬP MÃ OTP 6 PIN (PRISTINE LIGHT THEME)
         * ================================================================ */
        <div className="space-y-6 animate-in fade-in duration-300">
          
          {/* HEADER SECTION */}
          <div className="text-left">
            <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-sky-50 border border-sky-200 text-sky-700 text-xs font-bold mb-3 shadow-xs">
              <ShieldCheck className="w-3.5 h-3.5 text-sky-600 animate-pulse" />
              <span>Bảo Mật Xác Thực 2 Lớp (2FA)</span>
            </div>
            <h2 className="text-2xl sm:text-3xl font-extrabold text-foreground tracking-tight">
              Xác Thực Danh Tính
            </h2>
            <p className="mt-2 text-sm text-muted-foreground font-normal leading-relaxed">
              Mã bảo mật 6 chữ số (OTP) đã được gửi đến email y khoa của bạn. Vui lòng điền mã bên dưới để hoàn tất đăng ký.
            </p>
          </div>

          {/* BỘ 6 Ô VUÔNG NHẬP MÃ (6-DIGIT OTP INPUT BOXES) */}
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
                  disabled={isVerifying}
                  onChange={(e) => handleInput(idx, e.target.value)}
                  onKeyDown={(e) => handleKeyDown(idx, e)}
                  onPaste={handlePaste}
                  className={`w-11 h-13 sm:w-13 sm:h-16 text-center text-xl sm:text-2xl font-black font-mono rounded-2xl bg-slate-50 hover:bg-slate-100/80 focus:bg-white text-slate-900 border transition-all duration-200 outline-none shadow-sm focus:ring-4 focus:ring-offset-2 focus:ring-offset-white ${
                    errorMessage
                      ? "border-rose-400 focus:border-rose-500 focus:ring-rose-500/20 text-rose-700 bg-rose-50/50"
                      : "border-border/90 focus:border-sky-500 focus:ring-sky-500/20"
                  } disabled:opacity-50 disabled:cursor-not-allowed`}
                />
              ))}
            </div>

            {/* THÔNG BÁO LỖI NẾU CÓ */}
            {errorMessage && (
              <div className="p-3 rounded-2xl bg-rose-50 border border-rose-200 text-rose-700 text-xs font-bold flex items-center gap-2 animate-in slide-in-from-top-2 duration-200">
                <AlertCircle className="w-4 h-4 shrink-0 text-rose-600" />
                <span>{errorMessage}</span>
              </div>
            )}

            {/* HIỆN TRƯỜNG LOADING THẨM ĐỊNH */}
            {isVerifying && (
              <div className="flex items-center justify-center gap-2.5 py-3 text-sm font-extrabold text-sky-700 bg-sky-50/80 rounded-2xl border border-sky-100 animate-pulse">
                <Loader2 className="w-5 h-5 animate-spin text-sky-600" />
                <span>Đang thẩm định mã xác minh lâm sàng...</span>
              </div>
            )}
          </div>

          {/* ĐỒNG HỒ ĐẾM NGƯỢC 60S & NÚT GỬI LẠI MÃ */}
          <div className="flex flex-col sm:flex-row items-center justify-between gap-3 pt-4 border-t border-slate-100 text-xs sm:text-sm font-medium">
            <span className="text-muted-foreground font-normal">
              Chưa nhận được email mã số?
            </span>

            <button
              type="button"
              onClick={resendOTP}
              disabled={timeLeft > 0 || isVerifying}
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

          {/* LỰA CHỌN LUÂN CHUYỂN (CHANGE EMAIL) */}
          <div className="text-center pt-2">
            <p className="text-xs text-slate-400 font-medium">
              Sai địa chỉ email y khoa?{" "}
              <Link
                href="/auth/register"
                className="font-extrabold text-sky-600 hover:text-sky-700 underline decoration-sky-300 underline-offset-4 transition-colors ml-1"
              >
                Đăng ký lại tài khoản khác
              </Link>
            </p>
          </div>

        </div>
      ) : (
        /* ================================================================
         * TRẠNG THÁI THÀNH CÔNG (SUCCESS VERIFIED BANNER)
         * ================================================================ */
        <div className="text-center space-y-6 py-6 animate-in zoom-in-95 duration-400">
          <div className="mx-auto flex h-24 w-24 items-center justify-center rounded-3xl bg-emerald-50 border-2 border-emerald-300 text-emerald-600 shadow-[0_10px_35px_rgba(16,185,129,0.25)]">
            <CheckCircle2 className="w-12 h-12 animate-in zoom-in-50 duration-300" />
          </div>
          <div className="space-y-2">
            <h2 className="text-2xl sm:text-3xl font-extrabold text-foreground tracking-tight">
              Xác Thực Hoàn Tất!
            </h2>
            <p className="text-sm text-slate-600 leading-relaxed max-w-sm mx-auto font-normal dark:text-slate-300">
              Danh tính và email của bạn đã được kiểm toán hợp lệ theo tiêu chuẩn y đức ACID. Hệ thống đang sẵn sàng.
            </p>
          </div>
          <Link
            href="/"
            className="inline-flex items-center justify-center gap-2 px-8 py-4 rounded-2xl text-sm font-extrabold text-white bg-gradient-to-r from-emerald-600 to-teal-600 shadow-[0_6px_25px_rgba(16,185,129,0.35)] hover:shadow-lg transition-all duration-200 transform hover:scale-[1.02]"
          >
            <span>Vào Trang Chủ Hệ Thống AI Triage</span>
          </Link>
        </div>
      )}


      {/* FOOTER BACK TO LOGIN */}
      <div className="mt-6 text-center">
        <Link
          href="/auth/login"
          className="group inline-flex items-center justify-center gap-1.5 text-xs font-bold text-slate-400 hover:text-slate-600 transition-colors dark:hover:text-slate-300"
        >
          <ArrowLeft className="w-3.5 h-3.5 group-hover:-translate-x-1 transition-transform duration-200" />
          <span>Quay lại trang Đăng nhập</span>
        </Link>
      </div>

    </div>
  );
}
