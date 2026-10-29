"use client";

import React, { useState, useRef, useEffect, useCallback, KeyboardEvent, ClipboardEvent } from "react";
import Link from "next/link";
import { authService } from "@/services/auth.service";
import { useAuthStore } from "@/store/useAuthStore";
import { toast } from "sonner";
import { CheckCircle2, TriangleAlert } from "lucide-react";
import { cn } from "@/lib/utils";
import { AuthBackLink } from "@/components/auth/auth-actions";
import { AuthHeading } from "@/components/auth/auth-heading";
import { AuthStatusIcon, AuthSwap } from "@/components/auth/auth-status";
import { enterDelay, primaryButtonClass, textLinkClass } from "@/components/auth/auth-styles";
import { OtpCodeInput, OtpFeedback, ResendCodeButton } from "@/components/auth/otp-code-input";
import { useLocationSearch } from "@/components/auth/use-location-search";

const CODE_RULES = "Mã có hiệu lực 15 phút và bị hủy sau 5 lần nhập sai.";

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
      toast.success("Xác thực tài khoản y khoa thành công! Hệ thống sẵn sàng cấp quyền truy cập.");
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
  const resendOTP = async () => {
    if (timeLeft > 0 || isVerifying) return;
    // Cùng nguồn email với lệnh xác minh ở trên: mã chỉ được cấp lại cho đúng
    // email đã đăng ký.
    const email = new URLSearchParams(window.location.search).get("email");
    if (!email) {
      toast.error("Đường dẫn thiếu email nên chưa gửi lại được mã. Vui lòng đăng ký lại.");
      return;
    }
    setTimeLeft(60);
    setErrorMessage(null);
    setOtp(new Array(6).fill(""));
    inputRefs.current[0]?.focus();
    try {
      const response = await authService.resendRegistrationOtp({ email });
      toast.info(response.message);
    } catch (error: unknown) {
      // Chưa gửi được thì cho bấm lại ngay, không bắt chờ hết 60 giây.
      setTimeLeft(0);
      toast.error(error instanceof Error ? error.message : "Chưa gửi lại được mã. Vui lòng thử lại sau.");
    }
  };

  // Chỉ để hiển thị email người dùng đã nhập. Lệnh xác minh ở trên vẫn tự đọc
  // email từ URL như trước. null = chưa biết (đang hydrate), "" = URL thiếu email.
  const locationSearch = useLocationSearch();
  const emailFromUrl =
    locationSearch === null ? null : new URLSearchParams(locationSearch).get("email") ?? "";

  return (
    <div className="flex w-full flex-col">
      <AuthSwap stateKey={isSuccess ? "verified" : "enter-code"}>
        {!isSuccess ? (
          <div className="flex flex-col">
            <AuthHeading
              className="page-enter"
              title="Nhập mã xác minh"
              description={
                emailFromUrl ? (
                  <>
                    Chúng tôi đã gửi mã 6 chữ số tới{" "}
                    <strong className="font-semibold break-words text-foreground">{emailFromUrl}</strong>.{" "}
                    {CODE_RULES}
                  </>
                ) : (
                  `Mã 6 chữ số đã được gửi tới email bạn dùng để đăng ký. ${CODE_RULES}`
                )
              }
            />

            {/* Máy chủ chỉ chấp nhận mã đi kèm đúng email; thiếu email thì mã nào cũng bị từ chối. */}
            {emailFromUrl === "" ? (
              <p className="page-enter mt-6 flex items-start gap-2 rounded-xl border border-amber-300 bg-amber-50 p-4 text-sm font-medium text-amber-900 dark:border-amber-800/60 dark:bg-amber-950/40 dark:text-amber-100">
                <span className="flex h-5 shrink-0 items-center">
                  <TriangleAlert className="size-4" aria-hidden="true" />
                </span>
                <span>
                  Đường dẫn này thiếu địa chỉ email nên chưa thể xác minh mã. Hãy{" "}
                  <Link href="/auth/register" className={textLinkClass}>
                    đăng ký lại
                  </Link>{" "}
                  để nhận mã mới.
                </span>
              </p>
            ) : null}

            <div className="page-enter mt-8" style={enterDelay(1)}>
              <p id="otp-label" className="mb-2 text-sm font-semibold text-foreground">
                Mã xác minh
              </p>
              <OtpCodeInput
                digits={otp}
                labelId="otp-label"
                errorId="otp-error"
                invalid={Boolean(errorMessage)}
                disabled={isVerifying}
                registerInput={(index, element) => {
                  inputRefs.current[index] = element;
                }}
                onDigitChange={handleInput}
                onDigitKeyDown={handleKeyDown}
                onPaste={handlePaste}
              />
              <OtpFeedback verifying={isVerifying} error={errorMessage} errorId="otp-error" />
            </div>

            <div
              className="page-enter mt-6 flex flex-wrap items-center justify-between gap-2 border-t border-border pt-6"
              style={enterDelay(2)}
            >
              <p className="text-sm text-muted-foreground">Chưa nhận được mã?</p>
              <ResendCodeButton
                secondsLeft={timeLeft}
                disabled={timeLeft > 0 || isVerifying}
                onResend={resendOTP}
              />
            </div>

            <p
              className="page-enter flex min-h-11 flex-wrap items-center gap-x-2 text-sm text-muted-foreground"
              style={enterDelay(3)}
            >
              Sai email?
              <Link href="/auth/register" className={cn(textLinkClass, "inline-flex min-h-11 items-center")}>
                Đăng ký lại
              </Link>
            </p>
          </div>
        ) : (
          <div className="flex flex-col items-center gap-6 py-4 text-center">
            <AuthStatusIcon tone="success">
              <CheckCircle2 className="size-8" />
            </AuthStatusIcon>
            <AuthHeading
              align="center"
              title="Xác minh thành công"
              description="Tài khoản của bạn đã được kích hoạt."
            />
            <Link href="/" className={primaryButtonClass}>
              Vào trang chủ
            </Link>
          </div>
        )}
      </AuthSwap>

      <div className="mt-6 flex justify-center">
        <AuthBackLink />
      </div>
    </div>
  );
}
