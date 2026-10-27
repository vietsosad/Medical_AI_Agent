import React from "react";
import { PhoneCall } from "lucide-react";

import { cn } from "@/lib/utils";

/**
 * Lối gọi 115 gắn vào mọi trạng thái lỗi phía người bệnh.
 *
 * Khi phiên sàng lọc hỏng (mất mạng, dịch vụ AI tắt, máy chủ lỗi), người đang
 * nhập triệu chứng có thể chính là người đang nguy kịch. Một màn lỗi chỉ nói
 * "thử lại" sẽ đóng mất lối thoát duy nhất của họ, nên mọi màn lỗi đều phải
 * kèm dòng này. Đây là liên kết do người bệnh chủ động bấm -- hệ thống không
 * tự gọi 115 thay ai.
 */
export function EmergencyCallHint({ className }: { className?: string }) {
  return (
    <div
      className={cn(
        "flex flex-wrap items-center gap-2 text-sm font-semibold leading-6 text-rose-900 dark:text-rose-200",
        className,
      )}
    >
      <span>Nếu đang có dấu hiệu nguy kịch, gọi 115 ngay.</span>
      <a
        href="tel:115"
        aria-label="Gọi Tổng đài Cấp cứu Quốc gia 115"
        className="inline-flex min-h-11 items-center gap-2 rounded-xl bg-rose-700 px-4 text-sm font-bold text-white transition-colors hover:bg-rose-800 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-rose-600 focus-visible:ring-offset-2"
      >
        <PhoneCall className="size-4 shrink-0" aria-hidden="true" />
        Gọi 115
      </a>
    </div>
  );
}
