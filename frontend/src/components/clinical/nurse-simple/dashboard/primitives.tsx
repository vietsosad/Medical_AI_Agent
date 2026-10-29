"use client";

import { motion, type Variants } from "framer-motion";
import { Info, type LucideIcon } from "lucide-react";
import { useRef, useState, type KeyboardEvent, type ReactNode } from "react";

import { DURATION, EASE_OUT, exitTransition, riseVariants, staggerDelay } from "@/lib/motion";
import { cn } from "@/lib/utils";

import { AnimatedNumber } from "./AnimatedNumber";

// ============================================================================
// CHUYỂN ĐỘNG CHUNG
// ============================================================================

/**
 * Ô chỉ số và thẻ nổi lên lần lượt theo thứ tự đọc khi bảng hiện lần đầu
 * (`custom` = thứ tự; tối đa 6 tầng, cách nhau 50 ms). Chỉ chạy lúc gắn vào
 * cây: các vòng làm mới số liệu giữ nguyên phần tử nên không phát lại.
 */
export const cardRiseVariants: Variants = {
  hidden: riseVariants.hidden,
  visible: (order: number) => ({
    opacity: 1,
    y: 0,
    transition: { duration: DURATION.gentle, ease: EASE_OUT, delay: staggerDelay(order) },
  }),
};

/** Độ trễ (ms) để các vạch của một biểu đồ mọc lần lượt sau khi thẻ đã lên. */
export function barDelayMs(index: number): number {
  return Math.round(staggerDelay(index, 0.15) * 1000);
}

// ============================================================================
// THẺ
// ============================================================================

/** Khung thẻ biểu đồ: tiêu đề + phụ đề + (tùy chọn) điều khiển ở góc phải. */
export function DashboardPanel({
  id,
  title,
  subtitle,
  action,
  order,
  className,
  children,
}: {
  id: string;
  title: string;
  subtitle?: ReactNode;
  action?: ReactNode;
  order: number;
  className?: string;
  children: ReactNode;
}) {
  const titleId = `${id}-title`;
  return (
    <motion.section
      aria-labelledby={titleId}
      custom={order}
      variants={cardRiseVariants}
      initial="hidden"
      animate="visible"
      className={cn("flex min-w-0 flex-col rounded-2xl border border-border bg-card p-4 shadow-xs sm:p-6", className)}
    >
      <header className="flex flex-wrap items-start justify-between gap-4">
        {/* Nền 16rem: màn hẹp thì nút điều khiển xuống dòng thay vì ép tiêu đề thành một cột chữ. */}
        <div className="min-w-0 flex-[1_1_16rem]">
          <h2 id={titleId} className="text-base font-bold leading-6 tracking-tight text-foreground">
            {title}
          </h2>
          {subtitle ? <p className="text-sm leading-6 text-muted-foreground">{subtitle}</p> : null}
        </div>
        {action}
      </header>
      <div className="mt-6 flex min-w-0 flex-1 flex-col">{children}</div>
    </motion.section>
  );
}

/** Ô chỉ số: một con số hiện tại thì đọc bằng chữ số, không cần vẽ biểu đồ. */
export function StatTile({
  id,
  label,
  value,
  hint,
  order,
}: {
  id: string;
  label: string;
  value: number;
  hint: string;
  order: number;
}) {
  const labelId = `${id}-label`;
  return (
    <motion.section
      aria-labelledby={labelId}
      custom={order}
      variants={cardRiseVariants}
      initial="hidden"
      animate="visible"
      className="flex min-w-0 flex-col rounded-2xl border border-border bg-card p-4 shadow-xs sm:p-6"
    >
      <h2 id={labelId} className="text-sm font-semibold leading-6 text-muted-foreground">
        {label}
      </h2>
      <p className="mt-2 text-4xl font-extrabold leading-none tracking-tight text-foreground">
        <AnimatedNumber value={value} />
      </p>
      <p className="mt-2 text-sm leading-6 text-muted-foreground">{hint}</p>
    </motion.section>
  );
}

/** Thay cho một biểu đồ rỗng: nói thẳng vì sao chưa có số. */
export function EmptyNote({ icon: Icon = Info, children }: { icon?: LucideIcon; children: ReactNode }) {
  return (
    <div className="flex items-start gap-4 rounded-xl bg-muted/70 p-4">
      <span className="flex h-6 shrink-0 items-center">
        <Icon className="size-5 text-muted-foreground" aria-hidden="true" />
      </span>
      <p className="text-sm leading-6 text-muted-foreground">{children}</p>
    </div>
  );
}

// ============================================================================
// TƯƠNG TÁC TRÊN VẠCH: DI CHUỘT, BÀN PHÍM, CHẠM
// ============================================================================

/**
 * Mỗi biểu đồ là MỘT điểm dừng Tab; trong đó mũi tên / Home / End đi qua từng
 * vạch (roving tabindex), Esc ẩn chú thích nổi. Chú thích hiện khi di chuột
 * HOẶC khi vạch đang được focus -- chạm trên màn hình cảm ứng cũng là focus,
 * nên chú thích không biến mất ngay khi nhấc tay.
 */
export function useMarkFocus<K extends string>(keys: readonly K[]) {
  const [tabStop, setTabStop] = useState<K | null>(null);
  const [hovered, setHovered] = useState<K | null>(null);
  const [focused, setFocused] = useState<K | null>(null);
  const [dismissed, setDismissed] = useState(false);
  const nodes = useRef(new Map<K, HTMLElement>());

  const activeTabStop = tabStop !== null && keys.includes(tabStop) ? tabStop : (keys[0] ?? null);
  const candidate = hovered ?? focused;
  const shownKey = !dismissed && candidate !== null && keys.includes(candidate) ? candidate : null;

  function markProps(key: K) {
    return {
      ref: (node: HTMLElement | null) => {
        if (node) nodes.current.set(key, node);
        else nodes.current.delete(key);
      },
      tabIndex: key === activeTabStop ? 0 : -1,
      onPointerEnter: () => {
        setHovered(key);
        setDismissed(false);
      },
      onPointerLeave: () => setHovered((current) => (current === key ? null : current)),
      onFocus: () => {
        setFocused(key);
        setTabStop(key);
        setDismissed(false);
      },
      onBlur: () => setFocused((current) => (current === key ? null : current)),
      onKeyDown: (event: KeyboardEvent<HTMLElement>) => {
        if (event.key === "Escape") {
          setDismissed(true);
          return;
        }
        const index = keys.indexOf(key);
        const target = steppedIndex(event.key, index, keys.length);
        if (target === null || target === index) return;
        event.preventDefault();
        nodes.current.get(keys[target])?.focus();
      },
    };
  }

  return { shownKey, markProps };
}

function steppedIndex(key: string, index: number, count: number): number | null {
  if (key === "ArrowRight" || key === "ArrowDown") return Math.min(count - 1, index + 1);
  if (key === "ArrowLeft" || key === "ArrowUp") return Math.max(0, index - 1);
  if (key === "Home") return 0;
  if (key === "End") return count - 1;
  return null;
}

/**
 * Chú thích nổi của một vạch. `anchor` (0..100) là vị trí của vạch theo chiều
 * ngang trong khung chứa; dịch ngược đúng ngần ấy phần trăm bề rộng của chính
 * chú thích nên nó luôn chứa điểm neo mà không bao giờ tràn ra hai mép.
 *
 * Nội dung đã có sẵn ở nhãn chữ trên vạch và ở `aria-label`, nên chú thích chỉ
 * bổ sung (tỉ lệ, mẫu số) và được ẩn khỏi trình đọc màn hình.
 *
 * Dựng bằng `span` khối (không phải `div`/`p`) vì nó nằm bên trong vùng vạch,
 * vốn là nội dung dạng dòng.
 */
export function MarkTooltip({ anchor, children }: { anchor: number; children: ReactNode }) {
  const position = Math.min(100, Math.max(0, anchor));
  return (
    <motion.span
      aria-hidden="true"
      initial={{ opacity: 0, y: 4 }}
      animate={{ opacity: 1, y: 0, transition: { duration: DURATION.quick, ease: EASE_OUT } }}
      exit={{ opacity: 0, transition: exitTransition }}
      style={{ left: `${position}%`, x: `-${position}%` }}
      className="pointer-events-none absolute bottom-full z-30 mb-2 block w-max max-w-64 rounded-xl border border-border bg-popover px-4 py-2 text-left shadow-lg"
    >
      {children}
    </motion.span>
  );
}

/** Thân chú thích: giá trị đứng trước và đậm, tên chuỗi đứng sau. */
export function TooltipBody({
  value,
  label,
  detail,
  swatch,
}: {
  value: string;
  label: string;
  detail?: string;
  swatch?: ReactNode;
}) {
  return (
    <>
      <span className="block text-base font-bold leading-6 text-popover-foreground">{value}</span>
      <span className="flex items-center gap-2 text-sm leading-6 text-popover-foreground">
        {swatch}
        {label}
      </span>
      {detail ? <span className="block text-sm leading-6 text-muted-foreground">{detail}</span> : null}
    </>
  );
}

/** Mẫu màu soi gương vạch (khối ngang cho thanh, nét mảnh cho đường). */
export function SeriesSwatch({
  shape = "bar",
  className,
  color,
}: {
  shape?: "bar" | "line";
  className?: string;
  color?: string;
}) {
  return (
    <span
      aria-hidden="true"
      style={color ? { backgroundColor: color } : undefined}
      className={cn(
        "inline-block w-4 shrink-0",
        shape === "bar" ? "h-2 rounded-[2px]" : "h-0.5 rounded-full",
        className,
      )}
    />
  );
}
