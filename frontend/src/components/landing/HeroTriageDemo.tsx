"use client";

import type { ReactNode } from "react";
import { AnimatePresence, motion } from "framer-motion";
import { Activity, BadgeCheck, Check, Library, Mic, SendHorizontal } from "lucide-react";

import { esiTheme } from "@/components/clinical/nurse-simple/esi-theme";
import { DURATION, EASE_IN_OUT, EASE_OUT, popVariants, riseVariants } from "@/lib/motion";
import { cn } from "@/lib/utils";

/**
 * Phiên mẫu ở đầu trang chủ: một cuộc sàng lọc tự diễn ra trong 14 giây thay
 * cho đoạn văn giải thích. Người bệnh kể, trợ lý hỏi đúng hai điều còn thiếu,
 * mỗi câu trả lời rơi vào "Mình đã ghi nhận", rồi đối chiếu phác đồ, ra mức
 * ESI và điều dưỡng xác nhận -- đúng thứ tự của màn sàng lọc thật.
 *
 * Toàn bộ là dữ liệu minh họa và luôn ghi rõ như vậy; khối này là một hình
 * minh họa (role="img"), không có nút nào bấm được.
 */
export const HERO_DEMO_STEPS = [
  0, 700, 1300, 2000, 2800, 3700, 4100, 4700, 5500, 6400, 6800, 7400, 9000, 11000, 13200,
] as const;
export const HERO_DEMO_CYCLE_MS = 14_000;

const STEP = {
  story: 1,
  storyRecorded: 2,
  typingFever: 3,
  askFever: 4,
  tapYes: 5,
  answerYes: 6,
  typingPain: 7,
  askPain: 8,
  tapSix: 9,
  answerSix: 10,
  matching: 11,
  result: 12,
  confirmed: 13,
  fade: 14,
} as const;

export const HERO_DEMO_FINAL_STEP = STEP.confirmed;
/** Mức ESI phiên mẫu đi tới -- thang ESI dưới đầu trang sáng đúng mức này. */
export const HERO_DEMO_ESI = 3;
export function heroDemoShowsResult(step: number): boolean {
  return step >= STEP.result && step < STEP.fade;
}

const PAIN_SCALE = ["0", "1", "2", "3", "4", "5", "6", "7", "8", "9", "10"] as const;
const SELECTED_PAIN = "6";

function AgentBubble({ children }: { children: ReactNode }) {
  return (
    <p className="max-w-[18.5rem] rounded-2xl rounded-tl-sm bg-muted px-4 py-2 text-[15px] leading-6 text-foreground">
      {children}
    </p>
  );
}

function PatientBubble({ children }: { children: ReactNode }) {
  return (
    <p className="ml-auto max-w-[18rem] rounded-2xl rounded-tr-sm bg-brand px-4 py-2 text-[15px] leading-6 text-brand-foreground">
      {children}
    </p>
  );
}

function TypingBubble() {
  return (
    <span className="flex w-fit items-center gap-2 rounded-2xl rounded-tl-sm bg-muted px-4 py-4">
      {[0, 150, 300].map((delay) => (
        <span
          key={delay}
          className="typing-dot size-2 rounded-full bg-muted-foreground"
          style={{ animationDelay: `${delay}ms` }}
        />
      ))}
    </span>
  );
}

function Choice({ label, selected, className }: { label: string; selected: boolean; className?: string }) {
  return (
    <motion.span
      animate={selected ? { scale: [1, 0.94, 1] } : { scale: 1 }}
      transition={{ duration: DURATION.base, ease: EASE_OUT }}
      className={cn(
        "flex items-center justify-center rounded-xl border text-sm font-semibold transition-colors duration-200",
        selected ? "border-brand bg-brand text-brand-foreground" : "border-border bg-card text-foreground",
        className,
      )}
    >
      {label}
    </motion.span>
  );
}

/** Một mục trong khung chat: nổi lên từ dưới, đẩy các tin cũ lên trên. */
function Line({ children, align = "start" }: { children: ReactNode; align?: "start" | "end" }) {
  return (
    <motion.div
      layout="position"
      variants={riseVariants}
      initial="hidden"
      animate="visible"
      exit="exit"
      transition={{ layout: { duration: DURATION.base, ease: EASE_IN_OUT } }}
      className={cn("flex shrink-0 flex-col gap-2", align === "end" && "items-end")}
    >
      {children}
    </motion.div>
  );
}

function DemoResultCard({ confirmed }: { confirmed: boolean }) {
  const theme = esiTheme(HERO_DEMO_ESI);
  return (
    <div className="overflow-hidden rounded-2xl border-2 border-border bg-card">
      <p
        className={cn(
          "flex min-h-10 items-center gap-2 px-4 text-sm font-bold transition-colors duration-300",
          confirmed
            ? "bg-emerald-50 text-emerald-900 dark:bg-emerald-950/50 dark:text-emerald-100"
            : "bg-muted text-foreground",
        )}
      >
        {confirmed && <BadgeCheck className="size-4 shrink-0" aria-hidden="true" />}
        {confirmed ? "Điều dưỡng đã xác nhận mức này" : "Mức đề xuất của AI, chờ điều dưỡng xem lại"}
      </p>
      <div className="flex items-center gap-4 p-4">
        <motion.span
          variants={popVariants}
          initial="hidden"
          animate="visible"
          transition={{ delay: 0.15 }}
          className={cn(
            "flex size-14 shrink-0 flex-col items-center justify-center rounded-2xl border leading-none",
            theme.chip,
          )}
        >
          <span className="text-xs font-bold">ESI</span>
          <span className="text-2xl font-extrabold">{HERO_DEMO_ESI}</span>
        </motion.span>
        <div className="min-w-0">
          <p className="text-lg font-extrabold tracking-tight text-foreground">
            ESI {HERO_DEMO_ESI} · {theme.label}
          </p>
          <p className="mt-2 text-sm leading-6 text-muted-foreground">3/3 tiêu chí phác đồ khớp · có trích dẫn</p>
        </div>
      </div>
    </div>
  );
}

function ChatWindow({ step, cycle }: { step: number; cycle: number }) {
  const hasResult = step >= STEP.result;

  return (
    <div className="flex h-[31rem] flex-col overflow-hidden rounded-3xl border border-border bg-card shadow-[0_32px_64px_-36px_rgba(15,23,42,0.45)] sm:h-[36.5rem] dark:shadow-[0_32px_64px_-36px_rgba(0,0,0,0.9)]">
      <div className="flex items-center justify-between gap-4 border-b border-border px-4 py-4">
        <div className="flex min-w-0 items-center gap-2">
          <span className="flex size-10 shrink-0 items-center justify-center rounded-xl bg-brand-soft text-brand">
            <Activity className="size-5" strokeWidth={2.2} />
          </span>
          <div className="min-w-0">
            <p className="truncate text-[15px] font-bold text-foreground">Trợ lý sàng lọc</p>
            <p className="text-sm text-muted-foreground">Ví dụ minh họa</p>
          </div>
        </div>
        <AnimatePresence mode="wait" initial={false}>
          <motion.span
            key={hasResult ? "result" : "asking"}
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: DURATION.quick }}
            className={cn(
              "flex shrink-0 items-center gap-2 rounded-full px-4 py-2 text-sm font-semibold",
              hasResult
                ? "bg-amber-100 text-amber-900 dark:bg-amber-950/60 dark:text-amber-100"
                : "bg-brand-soft text-brand-ink",
            )}
          >
            <span className={cn("size-2 rounded-full", hasResult ? "bg-amber-500" : "bg-brand")} />
            {hasResult ? "Đã có kết quả" : "Đang hỏi thêm"}
          </motion.span>
        </AnimatePresence>
      </div>

      {/* Mỗi vòng dựng lại khung chat từ đầu. Khung cũ đã mờ hẳn ở mốc cuối nên
          việc thay khung không lộ ra; khung mới rõ dần từ lời chào. */}
      <motion.div
        key={cycle}
        initial={{ opacity: cycle === 0 ? 1 : 0 }}
        animate={{ opacity: step === STEP.fade ? 0 : 1 }}
        transition={{ duration: DURATION.gentle, ease: EASE_OUT }}
        className="flex min-h-0 flex-1 flex-col justify-end gap-4 overflow-hidden px-4 pb-4 [mask-image:linear-gradient(to_bottom,transparent,#000_3rem)]"
      >
        <AnimatePresence initial={false}>
          <Line key="greeting">
            <AgentBubble>Chào bạn! Bạn có đang gặp vấn đề sức khỏe nào cần hỗ trợ không?</AgentBubble>
          </Line>
          {step >= STEP.story && (
            <Line key="story" align="end">
              <PatientBubble>Tôi đau bụng bên phải từ tối qua, hơi buồn nôn.</PatientBubble>
            </Line>
          )}
          {step === STEP.typingFever && (
            <Line key="typing-fever">
              <TypingBubble />
            </Line>
          )}
          {step >= STEP.askFever && (
            <Line key="ask-fever">
              <AgentBubble>Bạn có sốt không?</AgentBubble>
              <span className="flex gap-2">
                <Choice label="Có" selected={step >= STEP.tapYes} className="min-h-11 px-4" />
                <Choice label="Không" selected={false} className="min-h-11 px-4" />
                <Choice label="Không rõ" selected={false} className="min-h-11 px-4" />
              </span>
            </Line>
          )}
          {step >= STEP.answerYes && (
            <Line key="answer-yes" align="end">
              <PatientBubble>Có</PatientBubble>
            </Line>
          )}
          {step === STEP.typingPain && (
            <Line key="typing-pain">
              <TypingBubble />
            </Line>
          )}
          {step >= STEP.askPain && (
            <Line key="ask-pain">
              <AgentBubble>Mức đau lúc này, từ 0 đến 10?</AgentBubble>
              <span className="grid w-full grid-cols-11 gap-2">
                {PAIN_SCALE.map((value) => (
                  <Choice
                    key={value}
                    label={value}
                    selected={value === SELECTED_PAIN && step >= STEP.tapSix}
                    className="h-10 rounded-lg"
                  />
                ))}
              </span>
            </Line>
          )}
          {step >= STEP.answerSix && (
            <Line key="answer-six" align="end">
              <PatientBubble>6/10</PatientBubble>
            </Line>
          )}
          {step === STEP.matching && (
            <Line key="matching">
              <span className="flex w-fit items-center gap-2 rounded-full bg-brand-soft px-4 py-2 text-sm font-semibold text-brand-ink">
                <Library className="size-4" aria-hidden="true" />
                Đang đối chiếu phác đồ…
              </span>
            </Line>
          )}
          {step >= STEP.result && (
            <Line key="result">
              <DemoResultCard confirmed={step >= STEP.confirmed} />
            </Line>
          )}
        </AnimatePresence>
      </motion.div>

      <div className="border-t border-border px-4 py-4">
        <div className="flex items-center gap-2 rounded-2xl border border-border py-2 pl-4 pr-2">
          <span className="flex-1 text-[15px] text-muted-foreground">Nhập câu trả lời…</span>
          <span className="flex size-10 items-center justify-center rounded-xl bg-muted text-muted-foreground">
            <Mic className="size-4" aria-hidden="true" />
          </span>
          <span className="flex size-10 items-center justify-center rounded-xl bg-brand text-brand-foreground">
            <SendHorizontal className="size-4" aria-hidden="true" />
          </span>
        </div>
      </div>
    </div>
  );
}

const RECORDED_FACTS = [
  { label: "Triệu chứng", value: "Đau bụng phải", from: STEP.storyRecorded, delay: 0 },
  { label: "Kèm theo", value: "Buồn nôn", from: STEP.storyRecorded, delay: 0.15 },
  { label: "Bắt đầu", value: "Tối qua", from: STEP.storyRecorded, delay: 0.3 },
  { label: "Sốt", value: "Có", from: STEP.answerYes, delay: 0.2 },
  { label: "Mức đau", value: "6/10", from: STEP.answerSix, delay: 0.2 },
] as const;

const MATCHED_CRITERIA = ["Đau bụng khu trú", "Có sốt", "Không dấu hiệu nguy kịch"] as const;

/** Bảng "Mình đã ghi nhận" bên cạnh khung chat, như cột phải của màn sàng lọc thật. */
function RecordedPanel({ step }: { step: number }) {
  const matching = step >= STEP.matching && step < STEP.fade;

  return (
    <div className="rounded-3xl border border-border bg-card p-4 shadow-[0_28px_56px_-32px_rgba(15,23,42,0.45)] dark:shadow-[0_28px_56px_-32px_rgba(0,0,0,0.9)]">
      <p className="text-[15px] font-extrabold text-foreground">Mình đã ghi nhận</p>
      <dl className="mt-2">
        {RECORDED_FACTS.map((fact) => {
          const shown = step >= fact.from && step < STEP.fade;
          return (
            <motion.div
              key={fact.label}
              animate={shown ? { opacity: 1, x: 0 } : { opacity: 0, x: -8 }}
              transition={{ duration: DURATION.base, ease: EASE_OUT, delay: shown ? fact.delay : 0 }}
              className={cn("flex justify-between gap-2 rounded-xl px-2 py-2", shown && "fact-flash")}
            >
              <dt className="text-sm text-muted-foreground">{fact.label}</dt>
              <dd className="text-right text-sm font-bold text-foreground">{fact.value}</dd>
            </motion.div>
          );
        })}
      </dl>
      <div className="mt-2 border-t border-border pt-4">
        <p className="flex items-center gap-2 text-sm font-bold text-brand-ink">
          <Library className="size-4" aria-hidden="true" />
          Đối chiếu phác đồ
        </p>
        <span className="mt-2 block h-2 overflow-hidden rounded-full bg-muted">
          <motion.span
            initial={false}
            animate={{ scaleX: matching ? 1 : 0 }}
            transition={{ duration: matching ? 1.4 : DURATION.quick, ease: EASE_IN_OUT }}
            className="block h-full origin-left rounded-full bg-brand"
          />
        </span>
        <ul className="mt-4 flex flex-col gap-2">
          {MATCHED_CRITERIA.map((criterion, index) => (
            <li key={criterion} className="flex items-center gap-2 text-sm text-foreground">
              <motion.span
                initial={false}
                animate={matching ? { opacity: 1, scale: 1 } : { opacity: 0.25, scale: 0.6 }}
                transition={{ duration: DURATION.base, ease: EASE_OUT, delay: matching ? 0.35 + index * 0.45 : 0 }}
                className="flex size-5 shrink-0 items-center justify-center rounded-full bg-brand text-brand-foreground"
              >
                <Check className="size-3" strokeWidth={3.2} aria-hidden="true" />
              </motion.span>
              {criterion}
            </li>
          ))}
        </ul>
      </div>
    </div>
  );
}

/** Bản gọn cho điện thoại: các dữ kiện vừa ghi nhận xếp thành hàng chip dưới khung chat. */
function RecordedChips({ step }: { step: number }) {
  const chips = [
    { text: "Đau bụng phải", from: STEP.storyRecorded },
    { text: "Buồn nôn", from: STEP.storyRecorded },
    { text: "Có sốt", from: STEP.answerYes },
    { text: "Đau 6/10", from: STEP.answerSix },
  ] as const;

  return (
    <div className="rounded-2xl border border-border bg-card px-4 py-4">
      <p className="text-sm font-extrabold text-foreground">Mình đã ghi nhận</p>
      <div className="mt-2 flex flex-wrap gap-2">
        {chips.map((chip) => {
          const shown = step >= chip.from && step < STEP.fade;
          return (
            <motion.span
              key={chip.text}
              animate={shown ? { opacity: 1, scale: 1 } : { opacity: 0, scale: 0.8 }}
              transition={{ duration: DURATION.base, ease: EASE_OUT }}
              className="rounded-full bg-brand-soft px-4 py-2 text-sm font-semibold text-brand-ink"
            >
              {chip.text}
            </motion.span>
          );
        })}
      </div>
    </div>
  );
}

interface HeroTriageDemoProps {
  step: number;
  cycle: number;
  onHoldChange: (hold: boolean) => void;
}

export function HeroTriageDemo({ step, cycle, onHoldChange }: HeroTriageDemoProps) {
  return (
    <div
      role="img"
      aria-label="Ví dụ minh họa một phiên sàng lọc: người bệnh kể đau bụng bên phải, trả lời hai câu hỏi về sốt và mức đau, nhận mức ESI 3 Khẩn trương và điều dưỡng xác nhận."
      onPointerEnter={(event) => event.pointerType === "mouse" && onHoldChange(true)}
      onPointerLeave={(event) => event.pointerType === "mouse" && onHoldChange(false)}
      className="grid w-full gap-4 lg:max-w-[25rem] xl:max-w-[41.5rem] xl:grid-cols-[minmax(0,25rem)_15rem] xl:items-start xl:gap-6"
    >
      <ChatWindow step={step} cycle={cycle} />
      <div className="hidden xl:mt-16 xl:block">
        <RecordedPanel step={step} />
      </div>
      <div className="xl:hidden">
        <RecordedChips step={step} />
      </div>
    </div>
  );
}
