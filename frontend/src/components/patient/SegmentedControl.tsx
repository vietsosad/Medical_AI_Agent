"use client";

import { useRef, type KeyboardEvent } from "react";
import { motion } from "framer-motion";

import { DURATION, EASE_IN_OUT } from "@/lib/motion";
import { cn } from "@/lib/utils";

export interface SegmentOption<T extends string> {
  value: T;
  label: string;
}

interface SegmentedControlProps<T extends string> {
  /** Tên của cả nhóm, đọc cho trình đọc màn hình. */
  label: string;
  options: ReadonlyArray<SegmentOption<T>>;
  value: T;
  onChange: (value: T) => void;
  /** Tiền tố id cho từng nút, để vùng nội dung trỏ ngược lại bằng aria-labelledby. */
  idPrefix: string;
  /** id của vùng nội dung mà nhóm nút này điều khiển. */
  panelId: string;
  /** Duy nhất trên trang: nền trắng trượt giữa các nút nhờ layoutId này. */
  layoutId: string;
  className?: string;
}

const HIGHLIGHT_TRANSITION = { duration: DURATION.quick, ease: EASE_IN_OUT };

export function segmentTabId(idPrefix: string, value: string): string {
  return `${idPrefix}-${value}`;
}

/**
 * Nhóm nút chọn một trong nhiều (tablist). Nền của nút đang chọn trượt sang nút
 * mới thay vì nhảy, nên mắt thấy ngay bộ lọc vừa đổi sang đâu. Phím mũi tên,
 * Home và End di chuyển giữa các nút theo đúng mẫu tablist của WAI-ARIA.
 */
export function SegmentedControl<T extends string>({
  label,
  options,
  value,
  onChange,
  idPrefix,
  panelId,
  layoutId,
  className,
}: SegmentedControlProps<T>) {
  const buttonsRef = useRef<Array<HTMLButtonElement | null>>([]);

  const focusOption = (index: number) => {
    const option = options[index];
    if (!option) return;
    onChange(option.value);
    buttonsRef.current[index]?.focus();
  };

  const handleKeyDown = (event: KeyboardEvent<HTMLButtonElement>, index: number) => {
    const last = options.length - 1;
    if (event.key === "ArrowRight") {
      event.preventDefault();
      focusOption(index === last ? 0 : index + 1);
    } else if (event.key === "ArrowLeft") {
      event.preventDefault();
      focusOption(index === 0 ? last : index - 1);
    } else if (event.key === "Home") {
      event.preventDefault();
      focusOption(0);
    } else if (event.key === "End") {
      event.preventDefault();
      focusOption(last);
    }
  };

  return (
    <div
      role="tablist"
      aria-label={label}
      className={cn("flex w-full rounded-2xl border border-border bg-muted", className)}
    >
      {options.map((option, index) => {
        const selected = option.value === value;
        return (
          <button
            key={option.value}
            ref={(node) => {
              buttonsRef.current[index] = node;
            }}
            id={segmentTabId(idPrefix, option.value)}
            type="button"
            role="tab"
            aria-selected={selected}
            aria-controls={panelId}
            tabIndex={selected ? 0 : -1}
            onClick={() => onChange(option.value)}
            onKeyDown={(event) => handleKeyDown(event, index)}
            className={cn(
              // Không đệm ngang: nút đã rộng sẵn, nhãn căn giữa và không xuống dòng.
              "relative flex min-h-11 flex-1 items-center justify-center whitespace-nowrap rounded-2xl text-sm transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand focus-visible:ring-offset-2 focus-visible:ring-offset-background",
              selected ? "font-bold text-foreground" : "font-semibold text-muted-foreground hover:text-foreground",
            )}
          >
            {selected && (
              // Viền 2px cùng màu nền rãnh tạo khe hở giữa nền trắng và mép rãnh.
              <motion.span
                layoutId={layoutId}
                transition={HIGHLIGHT_TRANSITION}
                aria-hidden="true"
                className="absolute inset-0 rounded-2xl border-2 border-muted bg-card shadow-sm dark:bg-slate-700"
              />
            )}
            <span className="relative">{option.label}</span>
          </button>
        );
      })}
    </div>
  );
}
