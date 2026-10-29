"use client";

import { useRef, useState, type ReactNode } from "react";
import { AnimatePresence, motion } from "framer-motion";
import {
  Activity,
  BadgeCheck,
  Check,
  ClipboardList,
  FileText,
  ListOrdered,
  MessageCircle,
  Mic,
  Monitor,
  MousePointerClick,
  PenLine,
  Send,
  Smartphone,
  Users,
} from "lucide-react";
import type { LucideIcon } from "lucide-react";

import { esiTheme } from "@/components/clinical/nurse-simple/esi-theme";
import { CareLoopBackdrop } from "@/components/landing/CareLoopBackdrop";
import { LANDING_ANCHORS } from "@/components/landing/landing-anchors";
import { MotionPauseButton } from "@/components/landing/MotionPauseButton";
import { useDemoTimeline } from "@/components/landing/use-demo-timeline";
import { DURATION, EASE_OUT, layoutTransition } from "@/lib/motion";
import { cn } from "@/lib/utils";

/**
 * "Một phiên, hai màn hình": cùng một ca nhìn từ điện thoại người bệnh và từ
 * hàng đợi của điều dưỡng. Ca vừa có kết quả chuyển sang hàng đợi, chen vào
 * đúng chỗ theo mức ESI rồi thời gian chờ (thứ tự của GET /nurse-simple/queue),
 * điều dưỡng mở ca, chốt kèm lý do, và điện thoại đổi sang "đã xác nhận".
 *
 * Tên và số liệu là dữ liệu minh họa, ghi rõ trên khung hàng đợi. Phía sau là
 * hai nửa ảnh nhà / bệnh viện nối bằng đường tín hiệu (CareLoopBackdrop); một
 * nút dừng cả ví dụ lẫn nền.
 */

const LOOP_STEPS = [0, 1000, 2800, 4400, 6600, 7000, 7800, 10000, 11200] as const;
const LOOP_CYCLE_MS = 12_000;
const STEP = {
  sent: 1,
  arrived: 2,
  opened: 3,
  press: 4,
  confirmed: 5,
  patientSees: 6,
  settled: 7,
  reset: 8,
} as const;

interface QueueCase {
  id: string;
  esi: number;
  name: string;
  complaint: string;
  wait: string;
}

const WAITING_CASES: readonly QueueCase[] = [
  { id: "case-b", esi: 2, name: "Trần Thị B.", complaint: "Khó thở", wait: "3 phút" },
  { id: "case-c", esi: 3, name: "Lê Văn C.", complaint: "Sốt cao", wait: "9 phút" },
  { id: "case-d", esi: 4, name: "Phạm Thị D.", complaint: "Đau họng", wait: "14 phút" },
];
const ARRIVING_CASE: QueueCase = {
  id: "case-demo",
  esi: 3,
  name: "Nguyễn Văn Demo",
  complaint: "Đau bụng phải",
  wait: "Vừa xong",
};

const PATIENT_FEATURES = [
  { icon: MessageCircle, label: "Mỗi lượt một câu hỏi" },
  { icon: Mic, label: "Gõ, chọn nhanh hoặc nói" },
  { icon: Users, label: "Khám giúp người thân" },
] as const;

const NURSE_FEATURES = [
  { icon: ListOrdered, label: "Xếp theo mức ESI" },
  { icon: ClipboardList, label: "SBAR kèm trích dẫn" },
  { icon: PenLine, label: "Mỗi quyết định kèm lý do" },
] as const;

function FeatureList({ items, className }: { items: readonly { icon: LucideIcon; label: string }[]; className?: string }) {
  return (
    <ul className={cn("landing-scrim flex flex-col gap-4 [--landing-scrim:var(--background)]", className)}>
      {items.map(({ icon: Icon, label }) => (
        <li key={label} className="flex items-center gap-4 text-[15px] font-semibold text-foreground">
          <span className="flex size-9 shrink-0 items-center justify-center rounded-xl bg-brand-soft text-brand">
            <Icon className="size-[18px]" strokeWidth={2.2} aria-hidden="true" />
          </span>
          {label}
        </li>
      ))}
    </ul>
  );
}

function EsiTile({ esi, size = "md" }: { esi: number; size?: "md" | "lg" }) {
  return (
    <span
      className={cn(
        "flex shrink-0 items-center justify-center rounded-xl border font-extrabold",
        size === "lg" ? "size-12 text-xl" : "size-10 text-base",
        esiTheme(esi).chip,
      )}
    >
      {esi}
    </span>
  );
}

function PatientResultCard({ confirmed }: { confirmed: boolean }) {
  const theme = esiTheme(ARRIVING_CASE.esi);
  return (
    <div className="overflow-hidden rounded-2xl border-2 border-border bg-card">
      <AnimatePresence mode="wait" initial={false}>
        <motion.p
          key={confirmed ? "confirmed" : "pending"}
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          transition={{ duration: DURATION.quick }}
          className={cn(
            "flex min-h-10 items-center gap-2 px-4 text-sm font-bold",
            confirmed
              ? "bg-emerald-50 text-emerald-900 dark:bg-emerald-950/50 dark:text-emerald-100"
              : "bg-muted text-foreground",
          )}
        >
          {confirmed && <BadgeCheck className="size-4 shrink-0" aria-hidden="true" />}
          {confirmed ? "Điều dưỡng đã xác nhận" : "Chờ điều dưỡng xem lại"}
        </motion.p>
      </AnimatePresence>
      <div className="flex items-center gap-4 p-4">
        <span
          className={cn(
            "flex size-12 shrink-0 flex-col items-center justify-center rounded-xl border leading-none",
            theme.chip,
          )}
        >
          <span className="text-xs font-bold">ESI</span>
          <span className="text-xl font-extrabold">{ARRIVING_CASE.esi}</span>
        </span>
        <div className="min-w-0">
          <p className="text-base font-extrabold text-foreground">{theme.label}</p>
          <p className="text-sm text-muted-foreground">Nên đến cơ sở y tế sớm</p>
        </div>
      </div>
    </div>
  );
}

function PatientScreen({ step }: { step: number }) {
  const confirmed = step >= STEP.patientSees && step < STEP.reset;
  const sending = step === STEP.sent;
  return (
    <div className="flex flex-col gap-4">
      <p className="max-w-[16rem] rounded-2xl rounded-tl-sm bg-muted px-4 py-2 text-sm leading-6 text-foreground">
        Cảm ơn bạn. Mình đã gửi kết quả tới điều dưỡng.
      </p>
      <PatientResultCard confirmed={confirmed} />
      <p
        className={cn(
          "flex items-center gap-2 text-sm font-semibold transition-colors duration-300",
          sending ? "text-brand" : "text-brand-ink",
        )}
      >
        <Send className="size-4 shrink-0" aria-hidden="true" />
        Đã gửi tới trạm điều phối
      </p>
      <div className="rounded-2xl border border-border bg-card p-4">
        <p className="text-sm font-bold text-foreground">Mình đã ghi nhận</p>
        <div className="mt-2 flex flex-wrap gap-2">
          {["Đau bụng phải", "Sốt", "Đau 6/10"].map((fact) => (
            <span key={fact} className="flex h-8 items-center rounded-full bg-brand-soft px-2 text-sm text-brand-ink">
              {fact}
            </span>
          ))}
        </div>
      </div>
    </div>
  );
}

function QueueRow({ item, selected, confirmed }: { item: QueueCase; selected: boolean; confirmed: boolean }) {
  return (
    <div
      className={cn(
        "relative flex items-center gap-2 rounded-2xl border bg-card p-2 transition-[border-color,box-shadow,background-color] duration-300",
        selected ? "border-brand bg-brand-soft shadow-[0_0_0_1px_var(--brand)]" : "border-border",
      )}
    >
      <EsiTile esi={item.esi} />
      <div className="min-w-0 flex-1">
        <p className="truncate text-[15px] font-bold text-foreground">{item.name}</p>
        <p className="truncate text-sm text-muted-foreground">{item.complaint}</p>
      </div>
      {confirmed ? (
        <span className="flex h-8 shrink-0 items-center gap-2 rounded-full bg-emerald-50 px-2 text-sm font-bold text-emerald-800 dark:bg-emerald-950/50 dark:text-emerald-200">
          <Check className="size-4" strokeWidth={2.6} aria-hidden="true" />
          Đã chốt
        </span>
      ) : (
        <span className="shrink-0 text-sm text-muted-foreground">{item.wait}</span>
      )}
    </div>
  );
}

function QueueList({ step, cycle }: { step: number; cycle: number }) {
  const arrived = step >= STEP.arrived && step < STEP.reset;
  const opened = step >= STEP.opened && step < STEP.reset;
  const confirmed = step >= STEP.confirmed && step < STEP.reset;
  const rows = arrived
    ? [WAITING_CASES[0], WAITING_CASES[1], ARRIVING_CASE, WAITING_CASES[2]]
    : [...WAITING_CASES];

  return (
    <ul className="flex flex-col gap-2">
      <AnimatePresence initial={false}>
        {rows.map((item) => {
          const isArriving = item.id === ARRIVING_CASE.id;
          return (
            <motion.li
              key={isArriving ? `${item.id}-${cycle}` : item.id}
              layout="position"
              initial={isArriving ? { opacity: 0, height: 0 } : false}
              animate={{ opacity: 1, height: "auto" }}
              exit={{ opacity: 0, height: 0 }}
              transition={{ ...layoutTransition, opacity: { duration: DURATION.base, ease: EASE_OUT } }}
              className={cn("overflow-hidden rounded-2xl", isArriving && "fact-flash")}
            >
              <QueueRow item={item} selected={isArriving && opened} confirmed={isArriving && confirmed} />
            </motion.li>
          );
        })}
      </AnimatePresence>
    </ul>
  );
}

function CaseDetail({ step }: { step: number }) {
  const opened = step >= STEP.opened && step < STEP.reset;
  const pressing = step === STEP.press;
  const confirmed = step >= STEP.confirmed && step < STEP.reset;
  const theme = esiTheme(ARRIVING_CASE.esi);

  return (
    <div className="relative min-h-[16rem]">
      <AnimatePresence mode="wait" initial={false}>
        {opened ? (
          <motion.div
            key="detail"
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0 }}
            transition={{ duration: DURATION.base, ease: EASE_OUT }}
          >
            <div className="flex flex-wrap items-center justify-between gap-2">
              <p className="text-base font-extrabold text-foreground">{ARRIVING_CASE.name}</p>
              <span className={cn("flex h-8 items-center rounded-full border px-2 text-sm font-bold", theme.chip)}>
                ESI {ARRIVING_CASE.esi} · {theme.label}
              </span>
            </div>
            <dl className="mt-4 flex flex-col gap-2 text-sm leading-6">
              {[
                ["S", "Đau bụng phải từ tối qua, buồn nôn"],
                ["A", "Có sốt, mức đau 6/10"],
                ["R", "Đề xuất ESI 3, chờ xác nhận"],
              ].map(([letter, text]) => (
                <div key={letter} className="flex gap-2">
                  <dt className="w-4 shrink-0 font-extrabold text-brand">{letter}</dt>
                  <dd className="text-foreground">{text}</dd>
                </div>
              ))}
            </dl>
            <p className="mt-4 flex items-center gap-2 rounded-xl bg-brand-soft px-2 py-2 text-sm font-semibold text-brand-ink">
              <FileText className="size-4 shrink-0" aria-hidden="true" />
              3/3 tiêu chí khớp · có trích dẫn
            </p>
            <div className="mt-4 flex flex-wrap items-center gap-2">
              <motion.span
                animate={pressing ? { scale: [1, 0.94, 1] } : { scale: 1 }}
                transition={{ duration: DURATION.gentle, ease: EASE_OUT }}
                className="flex min-h-11 items-center gap-2 rounded-xl bg-brand px-4 text-sm font-bold text-brand-foreground"
              >
                {confirmed && <Check className="size-4" strokeWidth={2.8} aria-hidden="true" />}
                Giữ ESI 3
              </motion.span>
              <span className="flex min-h-11 items-center rounded-xl border border-border bg-card px-4 text-sm font-semibold text-foreground">
                Điều chỉnh
              </span>
            </div>
          </motion.div>
        ) : (
          <motion.div
            key="empty"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: DURATION.quick }}
            className="absolute inset-0 flex flex-col items-center justify-center gap-2 rounded-2xl border border-dashed border-border text-sm text-muted-foreground"
          >
            <MousePointerClick className="size-6" aria-hidden="true" />
            Chọn một ca để xem
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}

function StationToast({ show }: { show: boolean }) {
  return (
    <AnimatePresence>
      {show && (
        <motion.p
          initial={{ opacity: 0, y: 12 }}
          animate={{ opacity: 1, y: 0 }}
          exit={{ opacity: 0, y: 12 }}
          transition={{ duration: DURATION.base, ease: EASE_OUT }}
          className="absolute bottom-4 right-4 flex items-center gap-2 rounded-xl bg-slate-900 px-4 py-2 text-sm font-semibold text-white shadow-[0_16px_32px_-16px_rgba(15,23,42,0.6)] dark:bg-slate-100 dark:text-slate-900"
        >
          <Check className="size-4 text-teal-300 dark:text-teal-700" strokeWidth={2.8} aria-hidden="true" />
          Đã xác nhận ESI 3
        </motion.p>
      )}
    </AnimatePresence>
  );
}

function StationWindow({ step, cycle, stacked = false }: { step: number; cycle: number; stacked?: boolean }) {
  const toast = step === STEP.confirmed || step === STEP.patientSees;
  return (
    <div className="relative overflow-hidden rounded-3xl border border-border bg-card shadow-[0_40px_64px_-44px_rgba(15,23,42,0.5)] dark:shadow-[0_40px_64px_-44px_rgba(0,0,0,0.9)]">
      <div className="flex items-center justify-between gap-2 border-b border-border px-4 py-4">
        <p className="text-[15px] font-extrabold text-foreground">Hàng đợi điều phối</p>
        <span className="flex h-8 items-center rounded-full bg-muted px-4 text-sm font-semibold text-muted-foreground">
          Ví dụ minh họa
        </span>
      </div>
      <div className={cn("grid gap-4 p-4", !stacked && "xl:grid-cols-[minmax(0,1fr)_minmax(0,1.1fr)]")}>
        <QueueList step={step} cycle={cycle} />
        <CaseDetail step={step} />
      </div>
      <StationToast show={toast} />
    </div>
  );
}

/** Ô ESI nhỏ chạy dọc đường nối: ca vừa có kết quả đang đi sang hàng đợi. */
function Handoff({ run, runKey, vertical = false }: { run: boolean; runKey: string; vertical?: boolean }) {
  return (
    <div aria-hidden="true" className={cn("relative", vertical ? "mx-auto h-16 w-10" : "h-10 w-full")}>
      <span
        className={cn(
          "absolute border-dashed border-brand-edge",
          vertical ? "inset-y-0 left-1/2 -translate-x-1/2 border-l-2" : "inset-x-0 top-1/2 -translate-y-1/2 border-t-2",
        )}
      />
      {run && (
        <span
          key={runKey}
          style={{ animationDuration: "1600ms" }}
          className={cn(
            "absolute flex size-10 -translate-x-1/2 -translate-y-1/2 items-center justify-center rounded-xl border-2 border-brand bg-card text-base font-extrabold text-foreground shadow-[0_12px_24px_-12px_rgba(15,118,110,0.7)]",
            vertical ? "lp-travel-y left-1/2" : "lp-travel-x top-1/2",
          )}
        >
          3
        </span>
      )}
    </div>
  );
}

function ScreenCaption({ icon: Icon, children }: { icon: LucideIcon; children: ReactNode }) {
  return (
    <p className="mb-2 flex items-center gap-2 text-sm font-bold text-muted-foreground">
      <Icon className="size-4" aria-hidden="true" />
      {children}
    </p>
  );
}

export function CareLoopSection() {
  const sectionRef = useRef<HTMLElement>(null);
  const [paused, setPaused] = useState(false);
  const { step, cycle } = useDemoTimeline(sectionRef, LOOP_STEPS, LOOP_CYCLE_MS, { finalStep: STEP.settled, hold: paused });
  const sending = step === STEP.sent;
  const runKey = `${cycle}-${step}`;

  return (
    <section
      ref={sectionRef}
      id={LANDING_ANCHORS.experience}
      aria-labelledby="care-loop-title"
      className="relative isolate scroll-mt-24 overflow-hidden border-b border-border bg-background"
    >
      <CareLoopBackdrop paused={paused} />

      <div className="relative mx-auto max-w-7xl px-4 py-20 sm:px-6 sm:py-24 lg:px-8 lg:py-28">
        <header className="landing-scrim max-w-2xl [--landing-scrim:var(--background)]">
          <h2
            id="care-loop-title"
            className="text-[2rem] font-extrabold leading-[1.12] tracking-[-0.03em] text-foreground text-balance sm:text-5xl sm:leading-[1.08]"
          >
            Một phiên, hai màn hình
          </h2>
          <p className="mt-4 text-base leading-7 text-muted-foreground sm:text-lg sm:leading-8">
            Bạn trả lời trên điện thoại. Điều dưỡng nhận ca theo mức ưu tiên và xác nhận.
          </p>
        </header>

        <div
          role="img"
          aria-label="Ví dụ minh họa: kết quả ESI 3 từ điện thoại người bệnh chuyển vào hàng đợi điều phối, chen vào sau ca ESI 2 và ca ESI 3 chờ lâu hơn. Điều dưỡng mở ca, xem SBAR kèm tiêu chí phác đồ, bấm giữ ESI 3, và điện thoại người bệnh đổi sang đã xác nhận."
          className="mt-12 lg:mt-16"
        >
          {/* Máy tính: điện thoại bên trái, trạm điều phối bên phải, ca chạy dọc đường nối. */}
          <div className="hidden lg:grid lg:grid-cols-[18.75rem_6rem_minmax(0,1fr)] lg:items-start">
            <div>
              <div className="h-[37.5rem] overflow-hidden rounded-[2.75rem] border-[10px] border-slate-900 bg-background shadow-[0_40px_64px_-40px_rgba(15,23,42,0.6)] dark:border-slate-700">
                <div className="flex items-center gap-2 border-b border-border bg-card px-4 pb-4 pt-6">
                  <span className="flex size-7 items-center justify-center rounded-lg bg-slate-900 text-white dark:bg-slate-100 dark:text-slate-900">
                    <Activity className="size-4" strokeWidth={2.4} aria-hidden="true" />
                  </span>
                  <span className="text-[15px] font-extrabold text-foreground">AI Triage</span>
                </div>
                <div className="p-4">
                  <PatientScreen step={step} />
                </div>
              </div>
              <FeatureList items={PATIENT_FEATURES} className="mt-8" />
            </div>
            <div className="pt-52">
              <Handoff run={sending} runKey={runKey} />
            </div>
            <div className="min-w-0">
              <StationWindow step={step} cycle={cycle} />
              <FeatureList items={NURSE_FEATURES} className="mt-8 xl:grid xl:grid-cols-3 xl:gap-4" />
            </div>
          </div>

          {/* Điện thoại và máy tính bảng: hai màn hình xếp chồng, ca chạy từ trên xuống. */}
          <div className="mx-auto flex max-w-md flex-col lg:hidden">
            <ScreenCaption icon={Smartphone}>Bạn thấy</ScreenCaption>
            <PatientScreen step={step} />
            <Handoff vertical run={sending} runKey={`${runKey}-m`} />
            <ScreenCaption icon={Monitor}>Điều dưỡng thấy</ScreenCaption>
            <StationWindow step={step} cycle={cycle} stacked />
            <div className="mt-8 grid grid-cols-1 gap-4 sm:grid-cols-2">
              <FeatureList items={PATIENT_FEATURES} />
              <FeatureList items={NURSE_FEATURES} />
            </div>
          </div>
        </div>

        <MotionPauseButton
          paused={paused}
          onToggle={() => setPaused((current) => !current)}
          subject="ví dụ hai màn hình"
          className="absolute bottom-6 right-4 sm:right-6 lg:right-8"
        />
      </div>
    </section>
  );
}

