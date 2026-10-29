"use client";

import React, { useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { authService } from "@/services/auth.service";
import { useAuthStore } from "@/store/useAuthStore";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import * as z from "zod";
import { toast } from "sonner";
import { getHomeRouteForRole } from "@/lib/auth-routing";
import { cn } from "@/lib/utils";
import {
  AuthDivider,
  AuthSubmitButton,
  AuthSwitchLine,
  OAuthButtons,
} from "@/components/auth/auth-actions";
import { AuthField, AuthFormAlert, AuthInput, PasswordInput } from "@/components/auth/auth-fields";
import { AuthHeading } from "@/components/auth/auth-heading";
import { enterDelay, textLinkClass } from "@/components/auth/auth-styles";

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
    <div className="flex w-full flex-col">
      <AuthHeading
        className="page-enter"
        title="Chào mừng bạn trở lại"
        description="Đăng nhập để sàng lọc, xem lại kết quả và nhắn với nhân viên y tế."
      />

      {/* noValidate: lỗi định dạng email hiện bằng câu tiếng Việt ngay dưới ô
          (theo đúng schema ở trên) thay vì bong bóng mặc định của trình duyệt. */}
      <form
        onSubmit={handleSubmit(onSubmit)}
        noValidate
        className="page-enter mt-8 flex flex-col"
        style={enterDelay(1)}
      >
        <div className="flex flex-col gap-4">
          <AuthField id="email-input" label="Email" error={errors.email?.message}>
            <AuthInput
              id="email-input"
              type="email"
              inputMode="email"
              autoComplete="email"
              placeholder="vidu@email.com"
              disabled={isSubmitting}
              invalid={Boolean(errors.email)}
              {...register("email")}
            />
          </AuthField>

          <AuthField
            id="password-input"
            label="Mật khẩu"
            error={errors.password?.message}
            aside={
              <Link
                href="/auth/forgot-password"
                className={cn(
                  textLinkClass,
                  "relative text-sm after:absolute after:-inset-x-2 after:-inset-y-3 after:content-['']",
                )}
              >
                Quên mật khẩu?
              </Link>
            }
          >
            <PasswordInput
              id="password-input"
              autoComplete="current-password"
              visible={showPassword}
              onToggleVisibility={() => setShowPassword(!showPassword)}
              disabled={isSubmitting}
              invalid={Boolean(errors.password)}
              {...register("password")}
            />
          </AuthField>
        </div>

        {/* Lỗi do máy chủ trả về (sai mật khẩu, chưa xác minh OTP, mất kết nối) */}
        <AuthFormAlert message={errorMessage} />

        <AuthSubmitButton className="mt-6" pending={isSubmitting} pendingLabel="Đang đăng nhập…">
          Đăng nhập
        </AuthSubmitButton>
      </form>

      {/* Đăng nhập qua nhà cung cấp -- dùng đúng logo thương hiệu (provider-marks). */}
      <div className="page-enter" style={enterDelay(2)}>
        <AuthDivider />
        <OAuthButtons disabled={isSubmitting} onSelect={handleOAuthLogin} />
      </div>

      <AuthSwitchLine
        className="page-enter"
        style={enterDelay(3)}
        prompt="Chưa có tài khoản?"
        href="/auth/register"
        action="Đăng ký"
      />
    </div>
  );
}
