"use client";

import Link from "next/link";
import { ArrowRight, HeartPulse, History, Siren, Users } from "lucide-react";
import type { LucideIcon } from "lucide-react";

import { triageHistoryListHref, triageStartHref } from "@/lib/agent-mode";
import { patientEntryHref } from "@/lib/auth-routing";
import { useAuthStore } from "@/store/useAuthStore";

interface Shortcut {
  icon: LucideIcon;
  label: string;
  href: string;
}

/**
 * Khối kết trang: một lời mời hành động và ba lối tắt, thay cho lưới thẻ chữ
 * "danh bạ chức năng" cũ. Khách chưa đăng nhập đi qua màn đăng nhập trước, vì
 * mọi chức năng của người bệnh đều cần phiên đăng nhập (PatientRoleGuard).
 *
 * Dòng 115 ở đây chỉ là lời nhắc bằng chữ: nút gọi 115 chỉ xuất hiện trong phiên
 * sàng lọc có dấu hiệu nguy kịch hoặc kết quả ESI 1-2.
 */
export function LandingClosingCta() {
  const isAuthenticated = useAuthStore((state) => state.isAuthenticated);

  const shortcuts: Shortcut[] = [
    { icon: HeartPulse, label: "Hồ sơ sức khỏe", href: patientEntryHref("/profile/ehr", isAuthenticated) },
    { icon: History, label: "Lịch sử sàng lọc", href: patientEntryHref(triageHistoryListHref(), isAuthenticated) },
    { icon: Users, label: "Khám giúp người thân", href: patientEntryHref("/profile", isAuthenticated) },
  ];

  return (
    <section aria-labelledby="closing-cta-title" className="bg-teal-700 text-white dark:bg-teal-900">
      <div className="mx-auto flex max-w-7xl flex-col gap-12 px-4 py-20 sm:px-6 lg:flex-row lg:items-center lg:justify-between lg:px-8 lg:py-24">
        <div className="max-w-xl">
          <h2
            id="closing-cta-title"
            className="text-[2rem] font-extrabold leading-[1.12] tracking-[-0.03em] text-white text-balance sm:text-5xl sm:leading-[1.08]"
          >
            Thấy không ổn? Bắt đầu ngay.
          </h2>
          <p className="mt-4 text-base leading-7 text-teal-50 sm:text-lg sm:leading-8">
            {isAuthenticated
              ? "Hồ sơ gia đình và các lần sàng lọc trước luôn ở đây khi bạn cần."
              : "Đăng nhập để lưu hồ sơ gia đình và xem lại mọi lần sàng lọc."}
          </p>
          <div className="mt-8 flex flex-col gap-2 sm:flex-row sm:gap-4">
            <Link
              href={patientEntryHref(triageStartHref(), isAuthenticated)}
              className="group inline-flex min-h-14 items-center justify-center gap-2 rounded-2xl bg-white px-8 text-[17px] font-extrabold text-teal-900 transition duration-200 hover:bg-teal-50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-white focus-visible:ring-offset-2 focus-visible:ring-offset-teal-700 active:scale-[0.97] motion-reduce:transition-none motion-reduce:active:scale-100 dark:focus-visible:ring-offset-teal-900"
            >
              Bắt đầu sàng lọc
              <ArrowRight
                className="size-5 transition-transform duration-200 group-hover:translate-x-1 motion-reduce:transition-none motion-reduce:group-hover:translate-x-0"
                aria-hidden="true"
              />
            </Link>
            {!isAuthenticated && (
              <Link
                href="/auth/register"
                className="inline-flex min-h-14 items-center justify-center rounded-2xl border border-white/50 px-6 text-[17px] font-semibold text-white transition-colors duration-200 hover:bg-white/10 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-white focus-visible:ring-offset-2 focus-visible:ring-offset-teal-700 dark:focus-visible:ring-offset-teal-900"
              >
                Tạo tài khoản
              </Link>
            )}
          </div>
          <p className="mt-8 flex items-center gap-2 text-[15px] font-semibold">
            <Siren className="size-5 shrink-0" aria-hidden="true" />
            Trường hợp nguy kịch, gọi ngay 115.
          </p>
        </div>

        <ul className="grid w-full grid-cols-3 gap-2 sm:gap-4 lg:max-w-xl">
          {shortcuts.map(({ icon: Icon, label, href }) => (
            <li key={label}>
              <Link
                href={href}
                className="group flex h-full min-h-28 flex-col justify-between gap-4 rounded-3xl border border-white/25 bg-white/10 p-4 text-sm font-extrabold leading-snug text-white transition duration-200 hover:-translate-y-0.5 hover:bg-white/15 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-white focus-visible:ring-offset-2 focus-visible:ring-offset-teal-700 sm:min-h-40 sm:p-6 sm:text-[17px] motion-reduce:transition-none motion-reduce:hover:translate-y-0 dark:focus-visible:ring-offset-teal-900"
              >
                <span className="flex size-11 items-center justify-center rounded-xl bg-white/15">
                  <Icon className="size-[22px]" strokeWidth={2.2} aria-hidden="true" />
                </span>
                {label}
              </Link>
            </li>
          ))}
        </ul>
      </div>
    </section>
  );
}
