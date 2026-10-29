"use client";

import { useRef, useState, type ReactNode } from "react";
import { BadgeCheck, CircleCheck, CircleHelp, FileText, Library, MessageCircle, UserCheck } from "lucide-react";
import type { LucideIcon } from "lucide-react";

import { esiTheme, ESI_UNKNOWN } from "@/components/clinical/nurse-simple/esi-theme";
import { EvidenceBackdrop } from "@/components/landing/EvidenceBackdrop";
import { LANDING_ANCHORS } from "@/components/landing/landing-anchors";
import { MotionPauseButton } from "@/components/landing/MotionPauseButton";
import { useDemoTimeline } from "@/components/landing/use-demo-timeline";
import { cn } from "@/lib/utils";

/**
 * "Không đủ căn cứ thì không đoán" -- sơ đồ thay cho ba thẻ chữ cũ.
 *
 * Chỉ vẽ những hành vi chỉ thẳng ra được trong mã nguồn của `src/simple_agent`:
 * - đối chiếu từng tiêu chí phác đồ một cách tất định (decision.py
 *   evaluate_atoms/atom_status), không nhờ mô hình phán đoán mức độ;
 * - kết quả kèm tiêu chí đã thỏa (sbar.py _citation_entries);
 * - không truy xuất được căn cứ thì lượt kết thúc RETURN_INCOMPLETE, báo rõ là
 *   chưa đủ dữ liệu thay vì tự nghĩ ra một mức ESI;
 * - điều dưỡng giữ nguyên hoặc điều chỉnh mức đề xuất (routes_nurse_simple.py).
 * Các con số kho là số bản ghi thật trong các bảng simple_agent_*.
 *
 * Một chấm sáng đi qua sơ đồ hai lượt: lượt đầu khớp đủ tiêu chí và tới tay
 * điều dưỡng, lượt sau chưa đủ căn cứ và dừng lại. Phía sau là ảnh kho sách với
 * tia quét (EvidenceBackdrop); một nút dừng cả sơ đồ lẫn nền.
 */

const GATE_STEPS = [0, 1000, 2900, 4000, 5300, 6300, 7700, 8000, 9000, 10900, 12000, 14600] as const;
const GATE_CYCLE_MS = 16_000;
const STEP = {
  storyIn: 0,
  scan: 1,
  forkMatch: 2,
  matched: 3,
  toNurse: 4,
  nurse: 5,
  idle: 6,
  storyInAgain: 7,
  scanAgain: 8,
  forkIncomplete: 9,
  incomplete: 10,
} as const;

/** Hai nhánh rẽ trong cột 64 x 312 px: tâm hai hàng cao 148 px, cách nhau 16 px. */
const FORK_MATCH_PATH = "M 0 156 C 36 156, 28 74, 64 74";
const FORK_INCOMPLETE_PATH = "M 0 156 C 36 156, 28 238, 64 238";

const STORY_CHIPS = ["Đau bụng phải", "Sốt", "Đau 6/10"] as const;

function NodeTitle({ icon: Icon, children, className }: { icon: LucideIcon; children: ReactNode; className?: string }) {
  return (
    <p className={cn("flex items-center gap-2 text-[15px] font-extrabold text-foreground", className)}>
      <Icon className="size-[18px] shrink-0" strokeWidth={2.3} aria-hidden="true" />
      {children}
    </p>
  );
}

function IconTile({ icon: Icon }: { icon: LucideIcon }) {
  return (
    <span className="flex size-11 shrink-0 items-center justify-center rounded-xl bg-brand-soft text-brand">
      <Icon className="size-[22px]" strokeWidth={2.2} aria-hidden="true" />
    </span>
  );
}

/** Đường nối nét đứt; khi `run` bật, một chấm sáng chạy hết chiều dài của nó một lần. */
function Connector({ run, runKey, vertical = false }: { run: boolean; runKey: string; vertical?: boolean }) {
  return (
    <div aria-hidden="true" className={cn("relative", vertical ? "mx-auto h-12 w-3" : "h-3 w-full self-center")}>
      <span
        className={cn(
          "absolute border-dashed border-brand-edge",
          vertical ? "inset-y-0 left-1/2 -translate-x-1/2 border-l-2" : "inset-x-0 top-1/2 -translate-y-1/2 border-t-2",
        )}
      />
      {run && (
        <span
          key={runKey}
          className={cn(
            "absolute size-3 -translate-x-1/2 -translate-y-1/2 rounded-full bg-brand",
            vertical ? "lp-travel-y left-1/2" : "lp-travel-x top-1/2",
          )}
        />
      )}
    </div>
  );
}

function StoryNode({ lit }: { lit: boolean }) {
  return (
    <div
      className={cn(
        "rounded-3xl border p-4 transition-colors duration-300",
        lit ? "border-brand bg-brand-soft" : "border-border bg-background",
      )}
    >
      <IconTile icon={MessageCircle} />
      <p className="mt-4 text-base font-extrabold text-foreground">Lời kể của bạn</p>
      <div className="mt-2 flex flex-wrap gap-2">
        {STORY_CHIPS.map((chip) => (
          <span key={chip} className="rounded-full border border-border bg-card px-4 py-2 text-sm font-semibold text-foreground">
            {chip}
          </span>
        ))}
      </div>
    </div>
  );
}

function LibraryNode({ scanning, scanKey }: { scanning: boolean; scanKey: string }) {
  return (
    <div className="rounded-3xl border border-border bg-card p-4 shadow-[0_20px_40px_-32px_rgba(15,23,42,0.45)] dark:shadow-none">
      <IconTile icon={Library} />
      <p className="mt-4 text-base font-extrabold text-foreground">Kho phác đồ ESI</p>
      <div aria-hidden="true" className="relative mt-2 h-20 overflow-hidden rounded-xl border border-border bg-background p-2">
        {["w-4/5", "w-3/5", "w-2/3", "w-1/2"].map((width) => (
          <span key={width} className={cn("mb-2 block h-2 rounded bg-muted", width)} />
        ))}
        {scanning && (
          <span
            key={scanKey}
            className="lp-scan absolute inset-x-0 top-0 h-6 bg-gradient-to-b from-transparent via-brand-edge to-transparent"
          />
        )}
      </div>
      <p className="mt-2 text-sm text-muted-foreground">1.314 tài liệu · 1.768 tiêu chí</p>
    </div>
  );
}

function MatchedNode({ lit, className }: { lit: boolean; className?: string }) {
  const theme = esiTheme(3);
  return (
    <div
      className={cn(
        "rounded-3xl border-2 p-4 transition-colors duration-300",
        lit ? "border-brand bg-brand-soft" : "border-brand-edge bg-card",
        className,
      )}
    >
      <NodeTitle icon={CircleCheck} className="text-brand-ink">
        Khớp đủ tiêu chí
      </NodeTitle>
      <div className="mt-4 flex flex-col items-start gap-2 sm:flex-row sm:items-center">
        <span
          className={cn(
            "flex size-12 shrink-0 flex-col items-center justify-center rounded-xl border leading-none",
            theme.chip,
          )}
        >
          <span className="text-xs font-bold">ESI</span>
          <span className="text-xl font-extrabold">3</span>
        </span>
        <div className="min-w-0">
          <p className="text-base font-extrabold text-foreground">{theme.label}</p>
          <p className="flex items-center gap-2 text-sm text-muted-foreground">
            <FileText className="size-4 shrink-0" aria-hidden="true" />
            Kèm trích dẫn
          </p>
        </div>
      </div>
    </div>
  );
}

function IncompleteNode({ lit, className }: { lit: boolean; className?: string }) {
  return (
    <div
      className={cn(
        "rounded-3xl border-2 p-4 transition-colors duration-300",
        lit ? "border-slate-500 bg-muted dark:border-slate-400" : "border-border bg-card",
        className,
      )}
    >
      <NodeTitle icon={CircleHelp}>Chưa đủ căn cứ</NodeTitle>
      <div className="mt-4 flex flex-col items-start gap-2 sm:flex-row sm:items-center">
        <span
          className={cn(
            "flex size-12 shrink-0 items-center justify-center rounded-xl border text-xl font-extrabold",
            ESI_UNKNOWN.chip,
          )}
        >
          ?
        </span>
        <div className="min-w-0">
          <p className="text-base font-extrabold text-foreground">{ESI_UNKNOWN.label}</p>
          <p className="text-sm text-muted-foreground">Hỏi thêm, không đoán</p>
        </div>
      </div>
    </div>
  );
}

function NurseNode({ lit, className }: { lit: boolean; className?: string }) {
  return (
    <div
      className={cn(
        "rounded-3xl border-2 p-4 transition-colors duration-300",
        lit ? "border-brand bg-brand-soft" : "border-border bg-background",
        className,
      )}
    >
      <NodeTitle icon={UserCheck}>Điều dưỡng xác nhận</NodeTitle>
      <div className="mt-4 flex flex-col gap-2">
        <span className="flex h-9 items-center justify-center gap-2 rounded-xl bg-brand text-sm font-bold text-brand-foreground">
          {lit && <BadgeCheck className="size-4" aria-hidden="true" />}
          Giữ nguyên
        </span>
        <span className="flex h-9 items-center justify-center rounded-xl border border-border bg-card text-sm font-semibold text-foreground">
          Điều chỉnh
        </span>
      </div>
    </div>
  );
}

export function EvidenceGateSection() {
  const sectionRef = useRef<HTMLElement>(null);
  const [paused, setPaused] = useState(false);
  const { step, cycle } = useDemoTimeline(sectionRef, GATE_STEPS, GATE_CYCLE_MS, { finalStep: STEP.idle, hold: paused });
  const key = (name: string) => `${name}-${cycle}-${step}`;

  const storyLit = step === STEP.storyIn || step === STEP.storyInAgain;
  const storyRun = storyLit;
  const scanning = step === STEP.scan || step === STEP.scanAgain;
  const matchedLit = step >= STEP.matched && step <= STEP.nurse;
  const nurseLit = step === STEP.nurse;
  const incompleteLit = step === STEP.incomplete;

  return (
    <section
      ref={sectionRef}
      id={LANDING_ANCHORS.safety}
      aria-labelledby="evidence-gate-title"
      className="relative isolate scroll-mt-24 overflow-hidden border-b border-border bg-card"
    >
      <EvidenceBackdrop paused={paused} />

      <div className="relative mx-auto max-w-7xl px-4 py-20 sm:px-6 sm:py-24 lg:px-8 lg:py-28">
        <header className="landing-scrim max-w-2xl">
          <h2
            id="evidence-gate-title"
            className="text-[2rem] font-extrabold leading-[1.12] tracking-[-0.03em] text-foreground text-balance sm:text-5xl sm:leading-[1.08]"
          >
            Không đủ căn cứ thì không đoán
          </h2>
          <p className="mt-4 text-base leading-7 text-muted-foreground sm:text-lg sm:leading-8">
            Mỗi mức đề xuất phải khớp tiêu chí trong kho phác đồ. Thiếu căn cứ, hệ thống nói rõ.
          </p>
        </header>

        <div
          role="img"
          aria-label="Sơ đồ: lời kể của bạn được đối chiếu với kho phác đồ ESI gồm 1.314 tài liệu và 1.768 tiêu chí. Khớp đủ tiêu chí thì ra mức ESI kèm trích dẫn và chuyển điều dưỡng xác nhận. Chưa đủ căn cứ thì hệ thống hỏi thêm hoặc báo rõ là chưa đủ dữ liệu, không đoán."
          className="landing-scrim mt-12 lg:mt-16"
        >
          {/* Máy tính: một hàng chảy từ trái sang phải, rẽ hai nhánh ở giữa. */}
          <div className="hidden lg:grid lg:grid-cols-[minmax(0,1fr)_3.5rem_minmax(0,1.05fr)_4rem_minmax(0,1.2fr)_3.5rem_minmax(0,1fr)] lg:grid-rows-[9.25rem_9.25rem] lg:items-center lg:gap-y-4">
            <div className="col-start-1 row-span-2 row-start-1">
              <StoryNode lit={storyLit} />
            </div>
            <div className="col-start-2 row-span-2 row-start-1 flex px-2">
              <Connector run={storyRun} runKey={key("story")} />
            </div>
            <div className="col-start-3 row-span-2 row-start-1">
              <LibraryNode scanning={scanning} scanKey={key("scan")} />
            </div>
            <div aria-hidden="true" className="relative col-start-4 row-span-2 row-start-1 h-[19.5rem] w-16">
              <svg viewBox="0 0 64 312" fill="none" className="absolute inset-0 size-full">
                <path d={FORK_MATCH_PATH} strokeWidth={2} strokeDasharray="5 5" className="stroke-brand-edge" />
                <path
                  d={FORK_INCOMPLETE_PATH}
                  strokeWidth={2}
                  strokeDasharray="5 5"
                  className="stroke-slate-300 dark:stroke-slate-600"
                />
              </svg>
              {step === STEP.forkMatch && (
                <span
                  key={key("fork-match")}
                  className="lp-fork absolute left-0 top-0 size-3 rounded-full bg-brand"
                  style={{ offsetPath: `path("${FORK_MATCH_PATH}")` }}
                />
              )}
              {step === STEP.forkIncomplete && (
                <span
                  key={key("fork-incomplete")}
                  className="lp-fork absolute left-0 top-0 size-3 rounded-full bg-slate-500"
                  style={{ offsetPath: `path("${FORK_INCOMPLETE_PATH}")` }}
                />
              )}
            </div>
            <MatchedNode lit={matchedLit} className="col-start-5 row-start-1 h-full" />
            <div className="col-start-6 row-start-1 flex px-2">
              <Connector run={step === STEP.toNurse} runKey={key("nurse")} />
            </div>
            <NurseNode lit={nurseLit} className="col-start-7 row-start-1 h-full" />
            <IncompleteNode lit={incompleteLit} className="col-start-5 row-start-2 h-full" />
          </div>

          {/* Điện thoại: cùng sơ đồ, chảy từ trên xuống. */}
          <div className="mx-auto flex max-w-md flex-col lg:hidden">
            <StoryNode lit={storyLit} />
            <Connector vertical run={storyRun} runKey={key("story-m")} />
            <LibraryNode scanning={scanning} scanKey={key("scan-m")} />
            <Connector
              vertical
              run={step === STEP.forkMatch || step === STEP.forkIncomplete}
              runKey={key("fork-m")}
            />
            <div className="grid grid-cols-2 gap-2">
              <MatchedNode lit={matchedLit} />
              <IncompleteNode lit={incompleteLit} />
            </div>
            <div className="grid grid-cols-2 gap-2">
              <Connector vertical run={step === STEP.toNurse} runKey={key("nurse-m")} />
            </div>
            <NurseNode lit={nurseLit} />
          </div>
        </div>

        <MotionPauseButton
          paused={paused}
          onToggle={() => setPaused((current) => !current)}
          subject="sơ đồ đối chiếu"
          className="absolute bottom-6 right-4 sm:right-6 lg:right-8"
        />
      </div>
    </section>
  );
}
