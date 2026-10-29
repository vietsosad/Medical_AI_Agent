"use client";

import React, { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { authService } from "@/services/auth.service";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import * as z from "zod";
import { toast } from "sonner";
import {
  AuthDivider,
  AuthSubmitButton,
  AuthSwitchLine,
  OAuthButtons,
} from "@/components/auth/auth-actions";
import { AuthField, AuthFormAlert, AuthInput, PasswordInput } from "@/components/auth/auth-fields";
import { AuthHeading } from "@/components/auth/auth-heading";
import { enterDelay } from "@/components/auth/auth-styles";

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
    <div className="flex w-full flex-col">
      {/* Đăng ký luôn tạo tài khoản người bệnh (kèm hồ sơ sức khỏe của chính
          chủ), nên lời dẫn chỉ nói tới những gì tài khoản đó thật sự có. */}
      <AuthHeading
        className="page-enter"
        title="Tạo tài khoản"
        description="Lưu kết quả sàng lọc, quản lý hồ sơ sức khỏe gia đình và nhắn với nhân viên y tế."
      />

      <form
        onSubmit={handleSubmit(onSubmit)}
        noValidate
        className="page-enter mt-8 flex flex-col"
        style={enterDelay(1)}
      >
        <div className="flex flex-col gap-4">
          <AuthField id="fullname-input" label="Họ và tên" error={errors.fullName?.message}>
            <AuthInput
              id="fullname-input"
              type="text"
              autoComplete="name"
              placeholder="Nguyễn Văn An"
              disabled={isSubmitting}
              invalid={Boolean(errors.fullName)}
              {...register("fullName")}
            />
          </AuthField>

          <AuthField
            id="email-input-register"
            label="Email"
            hint="Mã xác minh 6 chữ số sẽ được gửi tới email này."
            error={errors.email?.message}
          >
            <AuthInput
              id="email-input-register"
              type="email"
              inputMode="email"
              autoComplete="email"
              placeholder="vidu@email.com"
              hasHint
              disabled={isSubmitting}
              invalid={Boolean(errors.email)}
              {...register("email")}
            />
          </AuthField>

          <AuthField
            id="password-input-register"
            label="Mật khẩu"
            hint="Tối thiểu 8 ký tự."
            error={errors.password?.message}
          >
            <PasswordInput
              id="password-input-register"
              autoComplete="new-password"
              hasHint
              visible={showPassword}
              onToggleVisibility={() => setShowPassword(!showPassword)}
              disabled={isSubmitting}
              invalid={Boolean(errors.password)}
              {...register("password")}
            />
          </AuthField>

          <AuthField
            id="confirm-password-input"
            label="Xác nhận mật khẩu"
            error={errors.confirmPassword?.message}
          >
            <PasswordInput
              id="confirm-password-input"
              autoComplete="new-password"
              visible={showConfirmPassword}
              onToggleVisibility={() => setShowConfirmPassword(!showConfirmPassword)}
              showLabel="Hiện xác nhận mật khẩu"
              hideLabel="Ẩn xác nhận mật khẩu"
              disabled={isSubmitting}
              invalid={Boolean(errors.confirmPassword)}
              {...register("confirmPassword")}
            />
          </AuthField>
        </div>

        {/* Lỗi do máy chủ trả về (email đã tồn tại, mất kết nối...) */}
        <AuthFormAlert message={errorMessage} />

        <AuthSubmitButton className="mt-6" pending={isSubmitting} pendingLabel="Đang tạo tài khoản…">
          Tạo tài khoản
        </AuthSubmitButton>
      </form>

      <div className="page-enter" style={enterDelay(2)}>
        <AuthDivider />
        <OAuthButtons disabled={isSubmitting} onSelect={handleOAuthRegister} />
      </div>

      <AuthSwitchLine
        className="page-enter"
        style={enterDelay(3)}
        prompt="Đã có tài khoản?"
        href="/auth/login"
        action="Đăng nhập"
      />
    </div>
  );
}
