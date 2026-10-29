"use client";

import { motion } from "framer-motion";
import { RefreshCw } from "lucide-react";

import { DURATION } from "@/lib/motion";
import { cn } from "@/lib/utils";
import type { ClinicalSocketStatus } from "@/lib/realtime/useClinicalSocket";

import { useNow } from "./queue-hooks";

function formatAgo(seconds: number): string {
  if (seconds < 10) return "vừa xong";
  if (seconds < 60) return `${Math.floor(seconds / 5) * 5} giây trước`;
  if (seconds < 3600) return `${Math.floor(seconds / 60)} phút trước`;
  return `${Math.floor(seconds / 3600)} giờ trước`;
}

/**
 * "Hệ thống có đang nghe không?" Hàng đợi tự tải lại định kỳ và được kênh trực
 * tiếp đẩy làm mới khi có thay đổi; chấm sáng và mốc "cập nhật x giây trước"
 * (lấy từ lần tải thành công gần nhất) cho người trực thấy điều đó. Một hàng
 * đợi đứng im vì mất kết nối không được trông giống một hàng đợi rỗng.
 */
export function QueueLiveStatus({
  updatedAt,
  failed,
  channel,
  refreshing,
  onRefresh,
}: {
  /** `dataUpdatedAt` của TanStack Query; 0 khi chưa tải được lần nào. */
  updatedAt: number;
  failed: boolean;
  channel: ClinicalSocketStatus;
  refreshing: boolean;
  onRefresh: () => void;
}) {
  const now = useNow(5_000);
  const seconds = updatedAt > 0 ? Math.max(0, Math.round((now - updatedAt) / 1000)) : null;
  const channelNote =
    channel === "open"
      ? "Kênh trực tiếp đang mở: thay đổi được đẩy tới ngay, hàng đợi vẫn tự tải lại định kỳ."
      : "Kênh trực tiếp đang kết nối lại; hàng đợi vẫn tự tải lại định kỳ.";

  return (
    <div className="flex flex-wrap items-center gap-2">
      <p
        title={channelNote}
        className={cn(
          "flex items-center gap-2 text-sm font-semibold",
          failed ? "text-amber-800 dark:text-amber-300" : "text-muted-foreground",
        )}
      >
        <span
          aria-hidden="true"
          className={cn("size-2 shrink-0 rounded-full", failed ? "bg-amber-500" : "live-dot bg-emerald-500")}
        />
        {failed ? "Chưa cập nhật được" : "Tự cập nhật"}
        {seconds !== null && (
          <span className="font-medium">
            {failed ? " · lần cuối " : " · "}
            {formatAgo(seconds)}
          </span>
        )}
      </p>
      <motion.button
        type="button"
        whileTap={{ scale: 0.97 }}
        transition={{ duration: DURATION.press }}
        onClick={onRefresh}
        disabled={refreshing}
        className="flex min-h-11 items-center gap-2 rounded-xl border border-border bg-card px-4 text-sm font-semibold text-foreground transition-colors hover:bg-muted disabled:opacity-60 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand focus-visible:ring-offset-2 focus-visible:ring-offset-background"
      >
        <RefreshCw className={cn("size-4", refreshing && "animate-spin motion-reduce:animate-none")} aria-hidden="true" />
        Tải lại
      </motion.button>
      {/* Chỉ đổi nội dung khi trạng thái đổi, để trình đọc màn hình không đọc mỗi nhịp đồng hồ. */}
      <span role="status" className="sr-only">
        {failed ? "Không cập nhật được hàng đợi, đang thử lại." : ""}
      </span>
    </div>
  );
}
