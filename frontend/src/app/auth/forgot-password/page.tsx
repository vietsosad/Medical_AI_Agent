"use client";

import React, { useState, useRef, useEffect, useCallback, KeyboardEvent, ClipboardEvent } from "react";
import Link from "next/link";
import { authService } from "@/services/auth.service";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import * as z from "zod";
import { toast } from "sonner";
import { ArrowRight, CheckCircle2 } from "lucide-react";
import { cn } from "@/lib/utils";
import { AuthBackLink, AuthSubmitButton } from "@/components/auth/auth-actions";
import { AuthField, AuthFormAlert, AuthInput, PasswordInput } from "@/components/auth/auth-fields";
import { AuthHeading } from "@/components/auth/auth-heading";
import { AuthStatusIcon, AuthSwap } from "@/components/auth/auth-status";
import { focusOutlineClass, primaryButtonClass } from "@/components/auth/auth-styles";
import { OtpCodeInput, OtpFeedback, ResendCodeButton } from "@/components/auth/otp-code-input";

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

const CODE_RULES = "Mã có hiệu lực 15 phút và bị hủy sau 5 lần nhập sai.";

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
  // Lỗi máy chủ của bước nhập email / đặt mật khẩu (trước đây hiện bằng alert()).
  const [formError, setFormError] = useState<string | null>(null);

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

  /* =========================================================================
   * XỬ LÝ BƯỚC 1: SUBMIT EMAIL YÊU CẦU MÃ OTP
   * ========================================================================= */
  const onEmailSubmit = async (data: EmailStepValues) => {
    setIsSubmittingEmail(true);
    setFormError(null);
    try {
      await authService.forgotPassword({ email: data.email });
      setSubmittedEmail(data.email);
      setTimeLeft(60);
      setOtp(new Array(6).fill(""));
      setStep("OTP");
    } catch (error) {
      console.error("Email Step Error:", error);
      const msg = error instanceof Error ? error.message : "Yêu cầu khôi phục mật khẩu thất bại. Vui lòng thử lại.";
      setFormError(msg);
      toast.error(msg);
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

  const resendOTP = async () => {
    if (timeLeft > 0 || isVerifyingOtp) return;
    setTimeLeft(60);
    setOtpError(null);
    setOtp(new Array(6).fill(""));
    inputRefs.current[0]?.focus();
    // Gửi lại đúng yêu cầu của bước 1: máy chủ cấp mã mới và huỷ mã cũ.
    try {
      const response = await authService.forgotPassword({ email: submittedEmail });
      toast.info(response.message);
    } catch (error: unknown) {
      // Chưa gửi được thì cho bấm lại ngay, không bắt chờ hết 60 giây.
      setTimeLeft(0);
      toast.error(error instanceof Error ? error.message : "Chưa gửi lại được mã. Vui lòng thử lại sau.");
    }
  };

  /* =========================================================================
   * XỬ LÝ BƯỚC 3: SUBMIT MẬT KHẨU MỚI
   * ========================================================================= */
  const onNewPasswordSubmit = async (data: NewPasswordValues) => {
    setIsSubmittingNewPass(true);
    setFormError(null);
    try {
      await authService.resetPassword({
        email: submittedEmail || undefined,
        otp: otp.join(""),
        newPassword: data.newPassword,
      });
      setStep("SUCCESS");
    } catch (error) {
      console.error("Password Update Error:", error);
      const msg = error instanceof Error ? error.message : "Cập nhật mật khẩu thất bại. Vui lòng thử lại sau.";
      setFormError(msg);
      toast.error(msg);
    } finally {
      setIsSubmittingNewPass(false);
    }
  };

  return (
    <div className="page-enter flex w-full flex-col">
      <AuthSwap stateKey={step}>
        {/* =================================================================
         * BƯỚC 1: NHẬP EMAIL ĐỂ YÊU CẦU MÃ OTP
         * ================================================================= */}
        {step === "EMAIL" && (
          <div className="flex flex-col">
            <AuthHeading
              title="Quên mật khẩu?"
              description="Nhập email bạn đã đăng ký. Chúng tôi sẽ gửi mã 6 chữ số để bạn đặt mật khẩu mới."
            />

            <form onSubmit={handleSubmitEmail(onEmailSubmit)} noValidate className="mt-8 flex flex-col">
              <AuthField id="email-input-reset" label="Email" error={emailErrors.email?.message}>
                <AuthInput
                  id="email-input-reset"
                  type="email"
                  inputMode="email"
                  autoComplete="email"
                  placeholder="vidu@email.com"
                  disabled={isSubmittingEmail}
                  invalid={Boolean(emailErrors.email)}
                  {...registerEmail("email")}
                />
              </AuthField>

              <AuthFormAlert message={formError} />

              <AuthSubmitButton className="mt-6" pending={isSubmittingEmail} pendingLabel="Đang gửi mã…">
                Gửi mã xác minh
              </AuthSubmitButton>
            </form>
          </div>
        )}

        {/* =================================================================
         * BƯỚC 2: NHẬP VÀ THẨM ĐỊNH MÃ OTP 6 CHỮ SỐ
         * ================================================================= */}
        {step === "OTP" && (
          <div className="flex flex-col">
            {/* Máy chủ không cho biết email có tồn tại hay không, nên câu chữ
                cũng không khẳng định là mã chắc chắn đã được gửi. */}
            <AuthHeading
              title="Nhập mã xác minh"
              description={
                <>
                  Nếu <strong className="font-semibold break-words text-foreground">{submittedEmail}</strong>{" "}
                  đã được đăng ký, mã 6 chữ số đã được gửi tới hộp thư này. {CODE_RULES}
                </>
              }
            />

            <div className="mt-8">
              <p id="reset-otp-label" className="mb-2 text-sm font-semibold text-foreground">
                Mã xác minh
              </p>
              <OtpCodeInput
                digits={otp}
                labelId="reset-otp-label"
                errorId="reset-otp-error"
                invalid={Boolean(otpError)}
                disabled={isVerifyingOtp}
                registerInput={(index, element) => {
                  inputRefs.current[index] = element;
                }}
                onDigitChange={handleOtpInput}
                onDigitKeyDown={handleOtpKeyDown}
                onPaste={handleOtpPaste}
              />
              <OtpFeedback verifying={isVerifyingOtp} error={otpError} errorId="reset-otp-error" />
            </div>

            <div className="mt-6 flex flex-wrap items-center justify-between gap-2 border-t border-border pt-6">
              <button
                type="button"
                onClick={() => setStep("EMAIL")}
                className={cn(
                  "inline-flex min-h-11 items-center rounded-xl px-2 text-sm font-semibold text-muted-foreground transition-colors duration-180 hover:text-foreground",
                  focusOutlineClass,
                )}
              >
                Nhập email khác
              </button>
              <ResendCodeButton
                secondsLeft={timeLeft}
                disabled={timeLeft > 0 || isVerifyingOtp}
                onResend={resendOTP}
              />
            </div>
          </div>
        )}

        {/* =================================================================
         * BƯỚC 3: ĐẶT MẬT KHẨU MỚI & XÁC NHẬN
         * ================================================================= */}
        {step === "NEW_PASSWORD" && (
          <div className="flex flex-col">
            <AuthHeading
              title="Đặt mật khẩu mới"
              description="Mã xác minh hợp lệ. Mật khẩu mới cần tối thiểu 8 ký tự."
            />

            <form onSubmit={handleSubmitNewPass(onNewPasswordSubmit)} noValidate className="mt-8 flex flex-col">
              <div className="flex flex-col gap-4">
                <AuthField id="new-password-input" label="Mật khẩu mới" error={passErrors.newPassword?.message}>
                  <PasswordInput
                    id="new-password-input"
                    autoComplete="new-password"
                    visible={showNewPass}
                    onToggleVisibility={() => setShowNewPass(!showNewPass)}
                    showLabel="Hiện mật khẩu mới"
                    hideLabel="Ẩn mật khẩu mới"
                    disabled={isSubmittingNewPass}
                    invalid={Boolean(passErrors.newPassword)}
                    {...registerNewPass("newPassword")}
                  />
                </AuthField>

                <AuthField
                  id="confirm-new-password-input"
                  label="Xác nhận mật khẩu mới"
                  error={passErrors.confirmPassword?.message}
                >
                  <PasswordInput
                    id="confirm-new-password-input"
                    autoComplete="new-password"
                    visible={showConfirmPass}
                    onToggleVisibility={() => setShowConfirmPass(!showConfirmPass)}
                    showLabel="Hiện xác nhận mật khẩu mới"
                    hideLabel="Ẩn xác nhận mật khẩu mới"
                    disabled={isSubmittingNewPass}
                    invalid={Boolean(passErrors.confirmPassword)}
                    {...registerNewPass("confirmPassword")}
                  />
                </AuthField>
              </div>

              <AuthFormAlert message={formError} />

              <AuthSubmitButton className="mt-6" pending={isSubmittingNewPass} pendingLabel="Đang cập nhật mật khẩu…">
                Cập nhật mật khẩu
              </AuthSubmitButton>
            </form>
          </div>
        )}

        {/* =================================================================
         * BƯỚC 4: THÔNG BÁO THÀNH CÔNG
         * ================================================================= */}
        {step === "SUCCESS" && (
          <div className="flex flex-col items-center gap-6 py-4 text-center">
            <AuthStatusIcon tone="success">
              <CheckCircle2 className="size-8" />
            </AuthStatusIcon>
            <AuthHeading
              align="center"
              title="Đã đổi mật khẩu"
              description={
                <>
                  Mật khẩu của <strong className="font-semibold break-words text-foreground">{submittedEmail}</strong> đã
                  được cập nhật. Hãy đăng nhập lại bằng mật khẩu mới.
                </>
              }
            />
            <Link href="/auth/login" className={primaryButtonClass}>
              Đăng nhập bằng mật khẩu mới
              <ArrowRight className="size-5" aria-hidden="true" />
            </Link>
          </div>
        )}
      </AuthSwap>

      {step !== "SUCCESS" && (
        <div className="mt-6 flex justify-center">
          <AuthBackLink />
        </div>
      )}
    </div>
  );
}
