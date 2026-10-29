"use client";

import { useRef, useState, type MouseEvent } from "react";
import Link from "next/link";
import { motion } from "framer-motion";
import { ArrowRight, FileText, Layers, UserCheck } from "lucide-react";

import { esiTheme } from "@/components/clinical/nurse-simple/esi-theme";
import { HeroBackdrop } from "@/components/landing/HeroBackdrop";
import {
  HERO_DEMO_CYCLE_MS,
  HERO_DEMO_ESI,
  HERO_DEMO_FINAL_STEP,
  HERO_DEMO_STEPS,
  HeroTriageDemo,
  heroDemoShowsResult,
} from "@/components/landing/HeroTriageDemo";
import { LANDING_ANCHORS } from "@/components/landing/landing-anchors";
import { MotionPauseButton } from "@/components/landing/MotionPauseButton";
import { useDemoTimeline } from "@/components/landing/use-demo-timeline";
import { triageStartHref } from "@/lib/agent-mode";
import { patientEntryHref } from "@/lib/auth-routing";
import { DURATION, EASE_OUT } from "@/lib/motion";
import { cn } from "@/lib/utils";
import { useAuthStore } from "@/store/useAuthStore";

/**
 * Đầu trang chủ. Mọi điều trang này nói phải kiểm chứng được từ chính hệ
 * thống: không đặt lại chỉ số hiệu năng (độ trễ, % chính xác) hay nhãn tuân
 * thủ (HIPAA/ISO) khi chưa có phép đo và chứng nhận thật -- đây là sản phẩm y
 * tế, một câu quảng cáo sai là một rủi ro lâm sàng.
 *
 * Thay cho đoạn văn giải thích là một phiên mẫu tự diễn ra (HeroTriageDemo);
 * khi phiên mẫu ra kết quả, thang ESI ngay bên dưới sáng đúng mức đó. Phía sau
 * là bức tường ảnh trôi chậm (HeroBackdrop). Phiên mẫu và bức tường cùng dừng
 * bằng một nút: hình động tự chạy quá 5 giây phải có cách dừng (WCAG 2.2.2).
 */

const PROOF_POINTS = [
  { icon: Layers, label: "Thang ESI 5 cấp" },
  { icon: FileText, label: "Có trích dẫn phác đồ" },
  { icon: UserCheck, label: "Điều dưỡng xác nhận" },
] as const;

/** Ô số của thang: nền đặc theo mức, chữ chọn theo độ sáng của nền để luôn đọc được. */
const ESI_SCALE = [
  { level: 1, tile: "bg-rose-600 text-white" },
  { level: 2, tile: "bg-orange-500 text-orange-950" },
  { level: 3, tile: "bg-amber-400 text-amber-950" },
  { level: 4, tile: "bg-emerald-500 text-emerald-950" },
  { level: 5, tile: "bg-sky-500 text-sky-950" },
] as const;

function EsiScaleStrip({ lit }: { lit: number | null }) {
  return (
    <div>
      <ol aria-label="Thang ESI 5 cấp" className="grid grid-cols-5 gap-2">
        {ESI_SCALE.map(({ level, tile }) => {
          const theme = esiTheme(level);
          const isLit = lit === level;
          return (
            <motion.li
              key={level}
              animate={{ y: isLit ? -6 : 0 }}
              transition={{ duration: DURATION.gentle, ease: EASE_OUT }}
              aria-current={isLit ? "step" : undefined}
              className={cn(
                "flex items-center justify-center gap-4 rounded-2xl border p-2 transition-[background-color,border-color,box-shadow] duration-300 sm:justify-start sm:px-4",
                isLit
                  ? cn(theme.chip, "shadow-[0_14px_28px_-16px_rgba(146,64,14,0.55)]")
                  : "border-border bg-card",
              )}
            >
              <span
                className={cn(
                  "flex size-8 shrink-0 items-center justify-center rounded-lg text-[15px] font-extrabold",
                  tile,
                )}
              >
                {level}
              </span>
              <span className="sr-only text-[15px] font-bold sm:not-sr-only">{theme.label}</span>
            </motion.li>
          );
        })}
      </ol>
      <p aria-hidden="true" className="mt-2 flex justify-between text-sm font-semibold text-muted-foreground sm:hidden">
        <span>{esiTheme(1).label}</span>
        <span>{esiTheme(5).label}</span>
      </p>
    </div>
  );
}

export function LandingHero() {
  const sectionRef = useRef<HTMLElement>(null);
  const [hold, setHold] = useState(false);
  const [paused, setPaused] = useState(false);
  const isAuthenticated = useAuthStore((state) => state.isAuthenticated);
  const { step, cycle } = useDemoTimeline(sectionRef, HERO_DEMO_STEPS, HERO_DEMO_CYCLE_MS, {
    finalStep: HERO_DEMO_FINAL_STEP,
    hold: hold || paused,
  });

  // Cuộn mượt tới phần "không đoán"; ai đã tắt hiệu ứng thì nhảy thẳng tới.
  const goToSafety = (event: MouseEvent<HTMLAnchorElement>) => {
    const target = document.getElementById(LANDING_ANCHORS.safety);
    if (!target) return;
    event.preventDefault();
    const reduce = window.matchMedia?.("(prefers-reduced-motion: reduce)").matches ?? false;
    target.scrollIntoView({ behavior: reduce ? "auto" : "smooth", block: "start" });
    window.history.replaceState(null, "", `#${LANDING_ANCHORS.safety}`);
  };

  return (
    <section
      ref={sectionRef}
      aria-labelledby="landing-hero-title"
      className="relative isolate overflow-hidden border-b border-brand-edge/60 bg-brand-soft"
    >
      <HeroBackdrop paused={paused} />

      <div className="mx-auto flex max-w-7xl flex-col gap-12 px-4 pb-8 pt-12 sm:px-6 lg:flex-row lg:items-center lg:gap-12 lg:px-8 lg:pb-10 lg:pt-16">
        <div className="page-enter max-w-xl lg:flex-1">
          <h1
            id="landing-hero-title"
            className="text-[2.5rem] font-extrabold leading-[1.08] tracking-[-0.035em] text-foreground text-balance sm:text-6xl sm:leading-[1.04]"
          >
            Bạn cần khám gấp đến mức nào?
          </h1>
          <p className="mt-6 max-w-[30em] text-[17px] leading-7 text-slate-700 sm:text-lg sm:leading-8 dark:text-slate-300">
            Kể triệu chứng, trả lời vài câu hỏi ngắn. Trợ lý đối chiếu phác đồ ESI, điều dưỡng xác nhận kết quả.
          </p>

          <div className="mt-8 flex flex-col gap-2 sm:flex-row sm:gap-4">
            <Link
              href={patientEntryHref(triageStartHref(), isAuthenticated)}
              className="group inline-flex min-h-14 items-center justify-center gap-2 rounded-2xl bg-brand px-8 text-[17px] font-bold text-brand-foreground shadow-[0_14px_28px_-16px_rgba(15,118,110,0.9)] transition duration-200 hover:bg-brand-strong focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand focus-visible:ring-offset-2 focus-visible:ring-offset-background active:scale-[0.97] motion-reduce:transition-none motion-reduce:active:scale-100"
            >
              Bắt đầu sàng lọc
              <ArrowRight
                className="size-5 transition-transform duration-200 group-hover:translate-x-1 motion-reduce:transition-none motion-reduce:group-hover:translate-x-0"
                aria-hidden="true"
              />
            </Link>
            <a
              href={`#${LANDING_ANCHORS.safety}`}
              onClick={goToSafety}
              className="inline-flex min-h-14 items-center justify-center rounded-2xl border border-brand-edge bg-card px-6 text-[17px] font-semibold text-brand-ink transition-colors duration-200 hover:bg-brand-soft focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand focus-visible:ring-offset-2 focus-visible:ring-offset-background"
            >
              Xem cách hoạt động
            </a>
          </div>

          <ul className="mt-10 flex flex-wrap gap-x-6 gap-y-4">
            {PROOF_POINTS.map(({ icon: Icon, label }) => (
              <li key={label} className="flex items-center gap-2 text-[15px] font-semibold text-brand-ink">
                <span className="flex size-9 items-center justify-center rounded-xl bg-brand-edge/40 text-brand">
                  <Icon className="size-[18px]" strokeWidth={2.2} aria-hidden="true" />
                </span>
                {label}
              </li>
            ))}
          </ul>
        </div>

        <HeroTriageDemo step={step} cycle={cycle} onHoldChange={setHold} />
      </div>

      <div className="relative mx-auto max-w-7xl px-4 pb-16 sm:px-6 lg:px-8">
        <EsiScaleStrip lit={heroDemoShowsResult(step) ? HERO_DEMO_ESI : null} />
        <MotionPauseButton
          paused={paused}
          onToggle={() => setPaused((current) => !current)}
          subject="hình động đầu trang"
          className="absolute bottom-2 right-4 sm:right-6 lg:right-8"
        />
      </div>
    </section>
  );
}
