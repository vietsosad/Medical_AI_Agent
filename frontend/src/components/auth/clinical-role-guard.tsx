"use client";

import { LockKeyhole } from "lucide-react";
import Link from "next/link";

import { useAuthStore } from "@/store/useAuthStore";

export function ClinicalRoleGuard({ children }: { children: React.ReactNode }) {
  const { user, isAuthenticated, isLoading } = useAuthStore();

  if (isLoading) {
    return (
      <div className="min-h-screen bg-background p-8" aria-busy="true" aria-label="Đang kiểm tra quyền truy cập">
        <div className="mx-auto h-32 max-w-xl animate-pulse rounded-lg bg-slate-200 dark:bg-slate-700" />
      </div>
    );
  }

  if (isAuthenticated && user?.role === "CLINICAL_NURSE") return <>{children}</>;

  return (
    <main className="flex min-h-screen items-center justify-center bg-background p-4">
      <section className="w-full max-w-lg rounded-xl border border-border bg-card p-8 text-center">
        <LockKeyhole className="mx-auto size-10 text-slate-700 dark:text-slate-200" aria-hidden="true" />
        <h1 className="mt-6 text-2xl font-semibold text-slate-950 dark:text-slate-50">Khu vực nhân viên lâm sàng</h1>
        <p className="mt-4 text-base leading-6 text-slate-600 dark:text-slate-300">
          Tài khoản hiện tại không có quyền phân luồng lâm sàng. Quyền truy cập được kiểm tra lại tại mọi API.
        </p>
        <Link
          href="/auth/login"
          className="mt-6 inline-flex min-h-11 items-center justify-center rounded-lg bg-sky-700 px-6 text-sm font-semibold text-white hover:bg-sky-800"
        >
          Đăng nhập tài khoản lâm sàng
        </Link>
      </section>
    </main>
  );
}

export default ClinicalRoleGuard;
