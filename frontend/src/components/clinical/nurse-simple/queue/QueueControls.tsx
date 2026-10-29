"use client";

import type { KeyboardEvent } from "react";
import { AnimatePresence, LayoutGroup, motion } from "framer-motion";
import { Archive, Check, CircleCheckBig, Inbox, Mail, Search, X, type LucideIcon } from "lucide-react";

import { DURATION, EASE_IN_OUT, EASE_OUT, exitTransition, popVariants } from "@/lib/motion";
import { cn } from "@/lib/utils";
import { ESI_THEME } from "@/components/clinical/nurse-simple/esi-theme";

import { AnimatedCount } from "./AnimatedCount";
import type { QueueBucketKey } from "./queue-model";

export const QUEUE_PANEL_ID = "queue-panel";

export function bucketTabId(key: QueueBucketKey): string {
  return `queue-bucket-${key}`;
}

const pressable = { scale: 0.97 };
const pressTransition = { duration: DURATION.press };

const BUCKETS: Array<{ key: QueueBucketKey; label: string; icon: LucideIcon }> = [
  { key: "queue", label: "Đang chờ", icon: Inbox },
  { key: "parked", label: "Tạm gác", icon: Archive },
  { key: "decided", label: "Đã quyết định", icon: CircleCheckBig },
];

/**
 * Ba nhóm ca. Nền sáng của nhóm đang chọn trượt sang nhóm mới (cùng
 * `layoutId`), nên mắt đi theo được mình vừa chuyển tới đâu. Phím mũi tên,
 * Home và End di chuyển giữa các nhóm theo mẫu tab của WAI-ARIA.
 */
export function QueueBucketTabs({
  active,
  counts,
  onSelect,
}: {
  active: QueueBucketKey;
  counts: Partial<Record<QueueBucketKey, number>>;
  onSelect: (key: QueueBucketKey) => void;
}) {
  const select = (key: QueueBucketKey, moveFocus: boolean) => {
    if (moveFocus) document.getElementById(bucketTabId(key))?.focus();
    if (key !== active) onSelect(key);
  };

  const handleKeyDown = (event: KeyboardEvent<HTMLButtonElement>, index: number) => {
    const last = BUCKETS.length - 1;
    const target =
      event.key === "ArrowRight"
        ? index === last
          ? 0
          : index + 1
        : event.key === "ArrowLeft"
          ? index === 0
            ? last
            : index - 1
          : event.key === "Home"
            ? 0
            : event.key === "End"
              ? last
              : null;
    if (target === null) return;
    event.preventDefault();
    select(BUCKETS[target].key, true);
  };

  return (
    <LayoutGroup id="queue-buckets">
      <div
        role="tablist"
        aria-label="Nhóm ca"
        className="flex w-full overflow-x-auto rounded-xl border border-border bg-muted sm:w-auto"
      >
        {BUCKETS.map(({ key, label, icon: Icon }, index) => {
          const selected = key === active;
          const count = counts[key];
          return (
            <button
              key={key}
              id={bucketTabId(key)}
              type="button"
              role="tab"
              aria-selected={selected}
              aria-controls={QUEUE_PANEL_ID}
              tabIndex={selected ? 0 : -1}
              onClick={() => select(key, false)}
              onKeyDown={(event) => handleKeyDown(event, index)}
              className={cn(
                "relative flex min-h-11 flex-1 shrink-0 items-center justify-center gap-2 whitespace-nowrap rounded-xl px-2 text-sm font-semibold transition-colors duration-200 sm:flex-none sm:px-4",
                "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-brand",
                selected ? "text-foreground" : "text-muted-foreground hover:text-foreground",
              )}
            >
              {selected && (
                <motion.span
                  layoutId="queue-bucket-highlight"
                  aria-hidden="true"
                  className="absolute inset-0 rounded-xl border border-border bg-card shadow-sm"
                  transition={{ type: "tween", duration: DURATION.quick, ease: EASE_IN_OUT }}
                />
              )}
              {/* Màn hẹp bỏ biểu tượng để cả ba nhóm vừa một hàng, không phải cuộn ngang. */}
              <Icon className={cn("relative hidden size-4 shrink-0 sm:block", selected && "text-brand")} aria-hidden="true" />
              <span className="relative">{label}</span>
              {typeof count === "number" && (
                <span
                  className={cn(
                    "relative rounded-full px-2 text-sm font-bold leading-6 transition-colors duration-200",
                    selected ? "bg-brand-soft text-brand-ink" : "bg-background text-muted-foreground",
                  )}
                >
                  <AnimatedCount value={count} />
                </span>
              )}
            </button>
          );
        })}
      </div>
    </LayoutGroup>
  );
}

/** "Chỉ ca của tôi" -- một công tắc thật (`role="switch"`), không phải tab thứ tư. */
export function MineOnlySwitch({
  checked,
  count,
  onChange,
}: {
  checked: boolean;
  count?: number;
  onChange: (next: boolean) => void;
}) {
  return (
    <button
      type="button"
      role="switch"
      aria-checked={checked}
      onClick={() => onChange(!checked)}
      className="flex min-h-11 items-center gap-2 rounded-xl px-2 text-sm font-semibold text-foreground transition-colors duration-200 hover:bg-muted focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand focus-visible:ring-offset-2 focus-visible:ring-offset-background"
    >
      {/* Viền trong suốt 4px làm khoảng đệm cho núm gạt, nền vẫn phủ dưới viền. */}
      <span
        aria-hidden="true"
        className={cn(
          "flex h-6 w-10 shrink-0 items-center rounded-full border-4 border-transparent transition-colors duration-200",
          checked ? "justify-end bg-brand" : "justify-start bg-slate-300 dark:bg-slate-600",
        )}
      >
        <motion.span
          layout
          transition={{ duration: DURATION.quick, ease: EASE_OUT }}
          className="size-4 rounded-full bg-white shadow-sm"
        />
      </span>
      Chỉ ca của tôi
      {typeof count === "number" && (
        <span
          className={cn(
            "rounded-full px-2 text-sm font-bold leading-6 transition-colors duration-200",
            checked ? "bg-brand-soft text-brand-ink" : "bg-muted text-muted-foreground",
          )}
        >
          <AnimatedCount value={count} />
        </span>
      )}
    </button>
  );
}

function SearchField({
  icon: Icon,
  label,
  value,
  placeholder,
  inputMode,
  onChange,
}: {
  icon: LucideIcon;
  label: string;
  value: string;
  placeholder: string;
  inputMode?: "email" | "search";
  onChange: (next: string) => void;
}) {
  return (
    <label className="relative block min-w-0">
      <Icon
        className="pointer-events-none absolute left-4 top-1/2 size-4 -translate-y-1/2 text-muted-foreground"
        aria-hidden="true"
      />
      <input
        type="search"
        inputMode={inputMode}
        value={value}
        onChange={(event) => onChange(event.target.value)}
        placeholder={placeholder}
        aria-label={label}
        className="h-11 w-full rounded-xl border border-border bg-card pl-10 pr-4 text-sm text-foreground transition-[border-color,box-shadow] duration-200 placeholder:text-muted-foreground focus:border-brand focus:outline-none focus:ring-2 focus:ring-brand/25"
      />
    </label>
  );
}

/**
 * Hai ô tìm riêng như backend nhận (`q` chỉ dò mã ca và lời kể, `patient_email`
 * dò email) -- gộp làm một ô sẽ hứa tìm được cả tên, điều backend không làm.
 */
export function QueueSearchFields({
  q,
  email,
  onQueryChange,
  onEmailChange,
}: {
  q: string;
  email: string;
  onQueryChange: (next: string) => void;
  onEmailChange: (next: string) => void;
}) {
  return (
    <div className="grid min-w-0 flex-1 gap-2 sm:grid-cols-2">
      <SearchField
        icon={Search}
        label="Tìm theo mã ca hoặc mô tả triệu chứng"
        value={q}
        placeholder="Tìm theo mã ca hoặc mô tả triệu chứng..."
        onChange={onQueryChange}
      />
      <SearchField
        icon={Mail}
        label="Tìm theo email bệnh nhân"
        value={email}
        placeholder="Tìm theo email bệnh nhân..."
        inputMode="email"
        onChange={onEmailChange}
      />
    </div>
  );
}

/** Chip mức ESI. Chip đang bật mang màu mức đó kèm dấu tích, nên không chỉ dựa vào màu. */
export function EsiFilterChips({
  selected,
  onToggle,
}: {
  selected: readonly number[];
  onToggle: (level: number) => void;
}) {
  return (
    <div role="group" aria-label="Lọc theo mức ESI" className="flex flex-wrap items-center gap-2">
      {[1, 2, 3, 4, 5].map((level) => {
        const active = selected.includes(level);
        const theme = ESI_THEME[level];
        return (
          <motion.button
            key={level}
            type="button"
            aria-pressed={active}
            onClick={() => onToggle(level)}
            whileTap={pressable}
            transition={pressTransition}
            className={cn(
              "flex min-h-11 items-center gap-2 rounded-full border px-4 text-sm font-bold transition-colors duration-200",
              "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand focus-visible:ring-offset-2 focus-visible:ring-offset-background",
              active
                ? theme.chip
                : "border-border bg-card text-muted-foreground hover:bg-muted hover:text-foreground",
            )}
          >
            {active ? (
              <Check className="size-4" strokeWidth={2.6} aria-hidden="true" />
            ) : (
              <span aria-hidden="true" className={cn("size-2 rounded-full", theme.rail)} />
            )}
            ESI {level}
          </motion.button>
        );
      })}
    </div>
  );
}

export function ClearFiltersButton({ visible, onClear }: { visible: boolean; onClear: () => void }) {
  return (
    <AnimatePresence initial={false}>
      {visible && (
        <motion.button
          key="clear-filters"
          type="button"
          variants={popVariants}
          initial="hidden"
          animate="visible"
          exit={{ opacity: 0, scale: 0.9, transition: exitTransition }}
          whileTap={pressable}
          onClick={onClear}
          className="flex min-h-11 shrink-0 items-center gap-2 rounded-xl border border-border bg-card px-4 text-sm font-bold text-foreground transition-colors hover:bg-muted focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand focus-visible:ring-offset-2 focus-visible:ring-offset-background"
        >
          <X className="size-4" aria-hidden="true" />
          Xóa bộ lọc
        </motion.button>
      )}
    </AnimatePresence>
  );
}
