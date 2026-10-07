"use client";

import { useEffect, useState } from "react";
import {
  CheckCircle2,
  Circle,
  Clock3,
  HeartPulse,
  PhoneCall,
  ShieldCheck,
  UserRoundCheck,
} from "lucide-react";

function formatElapsed(totalSeconds: number): string {
  const minutes = Math.floor(totalSeconds / 60);
  const seconds = totalSeconds % 60;
  return `${String(minutes).padStart(2, "0")}:${String(seconds).padStart(2, "0")}`;
}

const REVIEW_STEPS = [
  {
    label: "Hồ sơ đã được gửi",
    description: "Thông tin bạn xác nhận đã được chuyển sang hàng đợi thẩm định.",
    status: "complete",
  },
  {
    label: "Đang chờ nhân viên y tế xem xét",
    description: "Hệ thống đang theo dõi trạng thái và sẽ cập nhật khi có quyết định.",
    status: "current",
  },
  {
    label: "Nhận hướng xử trí đã thẩm định",
    description: "Kết quả chỉ hiển thị sau khi nhân viên y tế xác nhận hoặc điều chỉnh.",
    status: "pending",
  },
] as const;

export function HitlWaitingRoom() {
  const [elapsedSeconds, setElapsedSeconds] = useState(0);

  useEffect(() => {
    const timer = window.setInterval(() => {
      setElapsedSeconds((current) => current + 1);
    }, 1000);
    return () => window.clearInterval(timer);
  }, []);

  return (
    <section
      role="status"
      aria-live="polite"
      aria-labelledby="hitl-waiting-title"
      className="mx-auto w-full max-w-3xl rounded-2xl border border-sky-200 bg-card p-6 shadow-sm"
    >
      <div className="flex flex-col gap-6 sm:flex-row sm:items-start sm:justify-between">
        <div className="flex items-start gap-4">
          <span className="relative flex size-12 shrink-0 items-center justify-center rounded-xl bg-sky-600 text-white">
            <UserRoundCheck className="size-6" aria-hidden="true" />
            <span className="absolute -right-1 -top-1 size-3 animate-pulse rounded-full bg-emerald-500 ring-2 ring-white" aria-hidden="true" />
          </span>
          <div className="space-y-2">
            <h2 id="hitl-waiting-title" className="text-lg font-bold text-slate-950 dark:text-slate-50">
              Hồ sơ đang chờ nhân viên y tế thẩm định
            </h2>
            <p className="text-sm leading-6 text-slate-700 dark:text-slate-200">
              Bạn không cần khai lại thông tin hoặc tải lại trang. Kết quả sẽ tự cập nhật tại đây khi
              quá trình thẩm định hoàn tất.
            </p>
          </div>
        </div>

        <div className="flex min-h-12 shrink-0 items-center gap-2 rounded-xl bg-muted px-4 text-slate-800 dark:text-slate-100" aria-hidden="true">
          <Clock3 className="size-5 text-sky-700" />
          <span className="text-base font-bold tabular-nums">{formatElapsed(elapsedSeconds)}</span>
        </div>
      </div>

      <ol className="mt-6 space-y-2" aria-label="Tiến trình thẩm định">
        {REVIEW_STEPS.map((step) => (
          <li key={step.label} className="flex min-h-20 items-start gap-4 rounded-xl bg-background p-4">
            {step.status === "complete" ? (
              <CheckCircle2 className="mt-0.5 size-6 shrink-0 text-emerald-700" aria-hidden="true" />
            ) : step.status === "current" ? (
              <HeartPulse className="mt-0.5 size-6 shrink-0 animate-pulse text-sky-700" aria-hidden="true" />
            ) : (
              <Circle className="mt-0.5 size-6 shrink-0 text-slate-400" aria-hidden="true" />
            )}
            <div className="space-y-2">
              <p className="text-base font-semibold text-foreground">{step.label}</p>
              <p className="text-sm leading-6 text-slate-600 dark:text-slate-300">{step.description}</p>
            </div>
          </li>
        ))}
      </ol>

      <div className="mt-6 flex flex-col gap-4 border-t border-border pt-6 sm:flex-row sm:items-center sm:justify-between">
        <div className="flex items-start gap-2 text-sm leading-6 text-slate-700 dark:text-slate-200">
          <ShieldCheck className="mt-0.5 size-5 shrink-0 text-sky-700" aria-hidden="true" />
          <p>
            Đề xuất AI đã được kiểm tra và lưu; kết luận của nhân viên y tế vẫn đang chờ thẩm định.
          </p>
        </div>
        <a
          href="tel:115"
          className="inline-flex min-h-12 shrink-0 items-center justify-center gap-2 rounded-xl border border-rose-300 bg-rose-50 px-4 text-base font-bold text-rose-800 transition-colors hover:bg-rose-100 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-rose-600 focus-visible:ring-offset-2"
        >
          <PhoneCall className="size-5" aria-hidden="true" />
          Gọi 115 nếu triệu chứng xấu đi
        </a>
      </div>
    </section>
  );
}
