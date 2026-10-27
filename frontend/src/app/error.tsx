"use client";

import { useEffect } from "react";
import Link from "next/link";
import { AlertTriangle, Home, RefreshCw } from "lucide-react";

import { EmergencyCallHint } from "@/components/chat/EmergencyCallHint";

/**
 * Ranh giới lỗi cấp ứng dụng: mọi trang dưới layout gốc rơi vào đây khi dựng
 * giao diện thất bại, thay vì một trang trắng.
 *
 * Không bao giờ hiện `error.message` hay stack trace -- người đọc có thể là
 * người bệnh đang hoảng, và chuỗi kỹ thuật vừa vô nghĩa với họ vừa có thể lộ
 * chi tiết hệ thống. Lối gọi 115 luôn có mặt vì trang vừa hỏng có thể là trang
 * họ đang dùng để mô tả một tình huống khẩn cấp.
 */
export default function AppError({
  error,
  unstable_retry,
}: {
  error: Error & { digest?: string };
  unstable_retry: () => void;
}) {
  useEffect(() => {
    console.error(error);
  }, [error]);

  return (
    <div className="mx-auto flex min-h-[60vh] max-w-lg flex-col items-center justify-center gap-4 p-8 text-center">
      <AlertTriangle className="size-12 text-amber-600" aria-hidden="true" />
      <h1 className="text-xl font-bold text-slate-950 dark:text-slate-50">Trang này chưa hiển thị được</h1>
      <p className="text-base leading-7 text-slate-700 dark:text-slate-200">
        Đã có sự cố khi tải nội dung. Bạn có thể thử lại, hoặc quay về trang chủ.
      </p>
      <div className="flex flex-wrap justify-center gap-2">
        <button
          type="button"
          onClick={() => unstable_retry()}
          className="inline-flex min-h-11 items-center gap-2 rounded-xl border border-slate-300 bg-card px-4 text-sm font-semibold text-slate-800 hover:bg-muted dark:border-slate-700 dark:text-slate-100"
        >
          <RefreshCw className="size-4" aria-hidden="true" />
          Thử lại
        </button>
        <Link
          href="/"
          className="inline-flex min-h-11 items-center gap-2 rounded-xl border border-slate-300 bg-card px-4 text-sm font-semibold text-slate-800 hover:bg-muted dark:border-slate-700 dark:text-slate-100"
        >
          <Home className="size-4" aria-hidden="true" />
          Về trang chủ
        </Link>
      </div>
      <EmergencyCallHint className="justify-center" />
    </div>
  );
}
