"use client";

import Link from "next/link";
import { AlertCircle, ArrowLeft, RefreshCw } from "lucide-react";

import { QUEUE_HREF } from "@/components/clinical/nurse-simple/case/case-format";
import { cn } from "@/lib/utils";

/**
 * Khung chờ dựng đúng hình của hồ sơ ca (đầu hồ sơ, cột liên lạc, cột đọc,
 * bàn quyết định), nên trang không nhảy một nhịp khi dữ liệu về.
 */
export function CaseSkeleton() {
  const block = "skeleton-sweep relative overflow-hidden rounded-2xl border border-border bg-card";
  const bar = "rounded-lg bg-muted";
  return (
    <div className="flex flex-col gap-6" aria-busy="true">
      <span className="sr-only" role="status">
        Đang tải ca
      </span>
      <div className={cn(block, "flex flex-col gap-4 p-6")}>
        <div className={cn(bar, "h-4 w-24")} />
        <div className={cn(bar, "h-8 w-72 max-w-full")} />
        <div className={cn(bar, "h-4 w-full max-w-xl")} />
      </div>
      <div className="grid gap-6 xl:grid-cols-[minmax(0,1fr)_22rem] 2xl:grid-cols-[16rem_minmax(0,1fr)_22rem]">
        <div className="hidden flex-col gap-6 2xl:flex">
          <div className={cn(block, "h-48")} />
          <div className={cn(block, "h-56")} />
        </div>
        <div className="flex flex-col gap-6">
          <div className={cn(block, "flex flex-col gap-4 p-6")}>
            <div className={cn(bar, "h-4 w-40")} />
            <div className={cn(bar, "h-4 w-full")} />
            <div className={cn(bar, "h-4 w-5/6")} />
            <div className={cn(bar, "h-4 w-2/3")} />
          </div>
          <div className={cn(block, "h-40")} />
        </div>
        <div className={cn(block, "flex h-96 flex-col gap-4 rounded-3xl p-6")}>
          <div className={cn(bar, "h-16 w-full")} />
          <div className={cn(bar, "h-16 w-full")} />
          <div className={cn(bar, "h-12 w-full")} />
        </div>
      </div>
    </div>
  );
}

export function CaseLoadError({ message, onRetry }: { message: string; onRetry: () => void }) {
  return (
    <div
      role="alert"
      className="page-enter mx-auto flex max-w-xl flex-col items-center gap-4 rounded-2xl border border-rose-200 bg-rose-50 p-6 text-center text-rose-950 dark:border-rose-800 dark:bg-rose-950/40 dark:text-rose-100"
    >
      <AlertCircle className="size-6 text-rose-700 dark:text-rose-300" aria-hidden="true" />
      <div>
        <p className="text-base font-bold">Không thể tải ca này.</p>
        <p className="mt-2 text-sm leading-6">{message}</p>
      </div>
      <div className="flex flex-wrap justify-center gap-2">
        <button
          type="button"
          onClick={onRetry}
          className="inline-flex min-h-11 items-center gap-2 rounded-xl bg-brand px-4 text-sm font-bold text-brand-foreground transition-colors hover:bg-brand-strong focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand focus-visible:ring-offset-2"
        >
          <RefreshCw className="size-4" aria-hidden="true" />
          Thử tải lại
        </button>
        <Link
          href={QUEUE_HREF}
          className="inline-flex min-h-11 items-center gap-2 rounded-xl border border-border bg-card px-4 text-sm font-bold text-foreground transition-colors hover:bg-muted focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand focus-visible:ring-offset-2"
        >
          <ArrowLeft className="size-4" aria-hidden="true" />
          Về hàng đợi
        </Link>
      </div>
    </div>
  );
}
