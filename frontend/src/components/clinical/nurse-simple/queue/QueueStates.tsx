"use client";

import { motion, type Variants } from "framer-motion";
import {
  Archive,
  CircleAlert,
  CircleCheckBig,
  Inbox,
  RefreshCw,
  SearchX,
  UserRoundCheck,
  WifiOff,
  type LucideIcon,
} from "lucide-react";

import { DURATION, dropVariants, enterTransition, riseVariants, staggerDelay } from "@/lib/motion";
import { cn } from "@/lib/utils";

const pressable = { scale: 0.97 };
const pressTransition = { duration: DURATION.press };

const staggerRise: Variants = {
  hidden: { opacity: 0, y: 8 },
  visible: (index: number) => ({ opacity: 1, y: 0, transition: { ...enterTransition, delay: staggerDelay(index) } }),
};

const bone = "rounded-lg bg-slate-200 dark:bg-slate-700";
const boneSoft = "rounded-lg bg-muted";

/**
 * Khung chờ đúng hình một hàng ca thật: người trực thấy ngay bảng sắp trông ra
 * sao và có khoảng bao nhiêu ca, thay vì một vòng xoay giữa màn hình. Vệt sáng
 * chạy ngang nói "đang tải", khác hẳn một khối xám đứng im.
 */
export function QueueSkeleton({ rows = 4 }: { rows?: number }) {
  return (
    <div>
      <span className="sr-only" role="status">
        Đang tải hàng đợi
      </span>
      <ul aria-hidden="true" className="flex flex-col gap-2">
        {Array.from({ length: rows }, (_, index) => (
          <motion.li
            key={`skeleton-${index}`}
            variants={staggerRise}
            custom={index}
            initial="hidden"
            animate="visible"
            className="skeleton-sweep relative overflow-hidden rounded-2xl border border-border bg-card py-4 pl-6 pr-4"
          >
            <span className="absolute inset-y-0 left-0 w-2 bg-slate-200 dark:bg-slate-700" />
            <div className="grid grid-cols-[3.5rem_minmax(0,1fr)] gap-x-4 gap-y-4 md:grid-cols-[3.5rem_minmax(0,1fr)_auto] md:items-center xl:grid-cols-[3.5rem_minmax(0,1fr)_10rem_11rem_auto]">
              <span className={cn("size-14 rounded-2xl", "bg-slate-200 dark:bg-slate-700")} />
              <span className="flex min-w-0 flex-col gap-2">
                <span className={cn("h-4 w-32", bone)} />
                <span className={cn("h-4 w-full max-w-md", boneSoft)} />
              </span>
              <span className="hidden flex-col gap-2 xl:flex">
                <span className={cn("h-4 w-28", bone)} />
                <span className={cn("h-4 w-20", boneSoft)} />
              </span>
              <span className={cn("hidden h-4 w-20 xl:block", boneSoft)} />
              <span className={cn("hidden h-11 w-24 rounded-xl md:block", "bg-slate-200 dark:bg-slate-700")} />
            </div>
          </motion.li>
        ))}
      </ul>
    </div>
  );
}

export type QueueEmptyVariant = "queue" | "mine" | "parked" | "decided" | "filtered";

const EMPTY_COPY: Record<QueueEmptyVariant, { icon: LucideIcon; title: string; body: string }> = {
  queue: {
    icon: Inbox,
    title: "Hàng đợi đang trống",
    body: "Ca mới sẽ tự hiện lên ngay khi bệnh nhân hoàn tất sàng lọc, hoặc sớm hơn nếu có dấu hiệu cần xem ngay.",
  },
  mine: {
    icon: UserRoundCheck,
    title: "Bạn chưa phụ trách ca nào",
    body: "Ca bạn nhận ở hàng đợi chung sẽ nằm ở đây cho tới khi được chốt hoặc tạm gác.",
  },
  parked: {
    icon: Archive,
    title: "Không có ca nào đang tạm gác",
    body: "Ca được tạm gác kèm lý do sẽ nằm ở đây cho tới khi có người đẩy lại hàng đợi.",
  },
  decided: {
    icon: CircleCheckBig,
    title: "Chưa có ca nào được quyết định",
    body: "Ca sẽ hiện ở đây sau khi điều dưỡng chốt mức ESI cuối cùng.",
  },
  filtered: {
    icon: SearchX,
    title: "Không có ca nào khớp bộ lọc hiện tại.",
    body: "Thử bỏ bớt từ khóa, email hoặc mức ESI đang chọn.",
  },
};

export function QueueEmptyState({
  variant,
  action,
}: {
  variant: QueueEmptyVariant;
  action?: { label: string; onClick: () => void };
}) {
  const { icon: Icon, title, body } = EMPTY_COPY[variant];
  return (
    <motion.div
      variants={riseVariants}
      initial="hidden"
      animate="visible"
      className="flex flex-col items-center gap-4 rounded-3xl border border-dashed border-border bg-card/60 px-6 py-12 text-center"
    >
      <span className="relative flex size-16 items-center justify-center rounded-2xl bg-brand-soft text-brand-ink">
        <Icon className="size-8" strokeWidth={1.8} aria-hidden="true" />
        {/* Hàng đợi chung trống nhưng vẫn đang nghe: chấm sáng nói "ca mới sẽ tự tới". */}
        {variant === "queue" && (
          <span
            aria-hidden="true"
            className="live-dot live-teal absolute right-0 top-0 size-4 -translate-y-1/2 translate-x-1/2 rounded-full border-2 border-card bg-brand"
          />
        )}
      </span>
      <div className="max-w-sm">
        <h2 className="text-lg font-bold text-foreground">{title}</h2>
        <p className="mt-2 text-sm leading-6 text-muted-foreground">{body}</p>
      </div>
      {action && (
        <motion.button
          type="button"
          whileTap={pressable}
          transition={pressTransition}
          onClick={action.onClick}
          className="flex min-h-11 items-center rounded-xl border border-border bg-card px-4 text-sm font-bold text-brand-ink transition-colors hover:bg-muted focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand focus-visible:ring-offset-2 focus-visible:ring-offset-background"
        >
          {action.label}
        </motion.button>
      )}
    </motion.div>
  );
}

/** Lần tải đầu hỏng: chưa có gì để hiển thị, chỉ còn lỗi và nút thử lại. */
export function QueueErrorState({
  message,
  retrying,
  onRetry,
}: {
  message: string;
  retrying: boolean;
  onRetry: () => void;
}) {
  return (
    <motion.div
      role="alert"
      variants={dropVariants}
      initial="hidden"
      animate="visible"
      className="flex flex-col items-center gap-4 rounded-3xl border border-rose-200 bg-rose-50 px-6 py-12 text-center dark:border-rose-500/30 dark:bg-rose-500/10"
    >
      <span className="flex size-14 items-center justify-center rounded-2xl bg-card text-rose-700 dark:text-rose-300">
        <CircleAlert className="size-7" aria-hidden="true" />
      </span>
      <div className="max-w-md">
        <h2 className="text-lg font-bold text-rose-950 dark:text-rose-100">Không tải được hàng đợi</h2>
        <p className="mt-2 text-sm font-semibold leading-6 text-rose-800 dark:text-rose-200">{message}</p>
      </div>
      <motion.button
        type="button"
        whileTap={pressable}
        transition={pressTransition}
        onClick={onRetry}
        disabled={retrying}
        className="flex min-h-11 items-center gap-2 rounded-xl border border-border bg-card px-4 text-sm font-bold text-foreground transition-colors hover:bg-muted disabled:opacity-60 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-rose-600 focus-visible:ring-offset-2"
      >
        <RefreshCw className={cn("size-4", retrying && "animate-spin motion-reduce:animate-none")} aria-hidden="true" />
        Thử tải lại
      </motion.button>
    </motion.div>
  );
}

/**
 * Làm mới hỏng nhưng vẫn còn dữ liệu lần trước: giữ danh sách trên màn hình
 * (người trực không mất bức tranh đang có) và nói rõ rằng nó có thể đã cũ.
 */
export function QueueStaleNotice({
  message,
  retrying,
  onRetry,
  className,
}: {
  message: string;
  retrying: boolean;
  onRetry: () => void;
  className?: string;
}) {
  return (
    <motion.div
      role="alert"
      variants={dropVariants}
      initial="hidden"
      animate="visible"
      exit="exit"
      className={cn(
        "flex flex-wrap items-center gap-4 rounded-2xl border border-amber-200 bg-amber-50 px-4 py-2 text-sm text-amber-900 dark:border-amber-500/30 dark:bg-amber-500/10 dark:text-amber-100",
        className,
      )}
    >
      <WifiOff className="size-5 shrink-0" aria-hidden="true" />
      <p className="min-w-0 flex-1 leading-6">
        <span className="font-bold">Không cập nhật được hàng đợi.</span> {message} Danh sách bên dưới có thể đã cũ.
      </p>
      <motion.button
        type="button"
        whileTap={pressable}
        transition={pressTransition}
        onClick={onRetry}
        disabled={retrying}
        className="flex min-h-11 items-center gap-2 rounded-xl px-4 text-sm font-bold text-amber-900 transition-colors hover:bg-amber-100 disabled:opacity-60 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-amber-600 dark:text-amber-100 dark:hover:bg-amber-500/20"
      >
        <RefreshCw className={cn("size-4", retrying && "animate-spin motion-reduce:animate-none")} aria-hidden="true" />
        Thử lại
      </motion.button>
    </motion.div>
  );
}
