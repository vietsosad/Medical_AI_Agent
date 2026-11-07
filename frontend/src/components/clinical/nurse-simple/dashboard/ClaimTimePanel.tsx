"use client";

import { AnimatePresence, motion } from "framer-motion";
import { ShieldAlert, TriangleAlert } from "lucide-react";
import { useState, type CSSProperties } from "react";

import { WAIT_CRITICAL_MINUTES, WAIT_WARNING_MINUTES } from "@/components/clinical/nurse-simple/wait-time";
import { DURATION, EASE_OUT } from "@/lib/motion";
import { cn } from "@/lib/utils";
import type { SimpleClaimBinDTO, SimpleFlaggedClaimDTO, SimpleWaitBucketKey } from "@/types/simple-nurse";

import { AnimatedNumber } from "./AnimatedNumber";
import {
  claimBinBucket,
  claimBinLabel,
  formatCount,
  hasEnoughCases,
  niceCountAxis,
  percentOf,
  WAIT_BUCKET_META,
} from "./dashboard-model";
import {
  type ChartView,
  DashboardPanel,
  EmptyNote,
  MarkTooltip,
  TooltipBody,
  useMarkFocus,
  ViewSwitch,
} from "./primitives";

const PLOT_HEIGHT_CLASS = "h-48";
/** Nhãn trục hoành đặt ở ranh giới cột, mỗi 10 phút. */
const AXIS_LABEL_EVERY_MINUTES = 10;

/** Sắc biểu tượng của mốc chờ trên nền thẻ, như tiêu đề cột của ma trận chờ. */
const MARK_ICON_INK: Record<SimpleWaitBucketKey, string> = {
  UNDER_WARNING: "text-emerald-600 dark:text-emerald-400",
  WARNING: "text-amber-600 dark:text-amber-400",
  CRITICAL: "text-rose-600 dark:text-rose-400",
};

/**
 * Ca bộ lọc khẩn cấp gắn cờ: bao nhiêu phút từ lúc gắn cờ tới khi có điều dưỡng
 * nhận ca (ca được chốt thẳng thì tới lúc chốt).
 *
 * Hệ thống KHÔNG có chỉ tiêu thời gian nhận ca. Hai vạch đứng là hai mốc tô màu
 * thời gian chờ mà bảng ca đang dùng (30 và 60 phút, `wait-time.ts`), ghi rõ là
 * như vậy; tỉ lệ "nhận trước mốc 30 phút" đếm đúng điều đó, không gọi là đạt
 * hay không đạt. Cột một sắc; mốc được nói bằng vạch, nhãn chữ và biểu tượng.
 *
 * Ca chưa ai nhận không có thời gian để vẽ: nêu riêng, không bao giờ tính như
 * một ca "nhận sau 0 phút".
 */
export function ClaimTimePanel({
  claim,
  windowDays,
  order,
}: {
  claim: SimpleFlaggedClaimDTO;
  windowDays: number;
  order: number;
}) {
  const [view, setView] = useState<ChartView>("chart");
  const enough = hasEnoughCases(claim.claimed, claim.min_cases);

  return (
    <DashboardPanel
      id="flagged-claim"
      order={order}
      title="Từ lúc gắn cờ tới khi có người nhận"
      subtitle={`Ca bộ lọc khẩn cấp gắn cờ trong ${windowDays} ngày qua, theo số phút tới khi có điều dưỡng nhận ca.`}
      action={
        enough ? (
          <ViewSwitch id="flagged-claim-view" label="Cách xem thời gian nhận ca có cờ" view={view} onChange={setView} />
        ) : undefined
      }
    >
      {claim.flagged_total === 0 ? (
        <EmptyNote icon={ShieldAlert}>Bộ lọc khẩn cấp chưa gắn cờ ca nào trong {windowDays} ngày qua.</EmptyNote>
      ) : (
        <>
          {enough ? (
            <>
              <p className="flex flex-wrap items-baseline gap-x-2 gap-y-1">
                <span className="text-3xl font-extrabold leading-none tracking-tight text-foreground">
                  {percentOf(claim.claimed_under_warning, claim.claimed)}
                </span>
                <span className="text-sm leading-6 text-muted-foreground">
                  nhận trước mốc {WAIT_WARNING_MINUTES} phút: {formatCount(claim.claimed_under_warning)} trên{" "}
                  {formatCount(claim.claimed)} ca đã có người nhận
                </span>
              </p>
              <AnimatePresence mode="wait" initial={false}>
                <motion.div
                  key={view}
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  exit={{ opacity: 0 }}
                  transition={{ duration: DURATION.quick, ease: EASE_OUT }}
                >
                  {view === "chart" ? <ClaimHistogram claim={claim} /> : <ClaimTable bins={claim.bins} />}
                </motion.div>
              </AnimatePresence>
            </>
          ) : (
            <EmptyNote icon={ShieldAlert}>
              {claim.claimed === 0
                ? `Chưa có ca có cờ nào được nhận trong ${windowDays} ngày qua.`
                : `Chưa đủ ca để vẽ: mới có ${formatCount(claim.claimed)} ca có cờ được nhận trong ${windowDays} ngày qua, cần ít nhất ${formatCount(claim.min_cases)} ca.`}
            </EmptyNote>
          )}

          {claim.unclaimed > 0 ? (
            <p className="mt-4 flex items-start gap-2 text-sm leading-6 text-foreground">
              <TriangleAlert className="mt-1 size-4 shrink-0 text-rose-600 dark:text-rose-400" aria-hidden="true" />
              <span>
                <AnimatedNumber value={claim.unclaimed} className="font-semibold" /> ca có cờ trong khoảng này hiện chưa
                có người nhận, nên chưa nằm trong phần thời gian ở trên.
              </span>
            </p>
          ) : null}
          {claim.untimed > 0 ? (
            <p className="mt-2 text-sm leading-6 text-muted-foreground">
              {formatCount(claim.untimed)} ca có người giữ nhưng không ghi thời điểm nhận, nên không có trong phần thời
              gian.
            </p>
          ) : null}

          <p className="mt-4 border-t border-border pt-4 text-sm leading-6 text-muted-foreground">
            Vạch {WAIT_WARNING_MINUTES} và {WAIT_CRITICAL_MINUTES} phút là hai mốc tô màu thời gian chờ của bảng ca,
            không phải chỉ tiêu lâm sàng: cơ sở chưa cấu hình chỉ tiêu thời gian nhận ca. Thời điểm nhận là lần nhận
            đang ghi trên ca; ca từng bị trả lại hoặc tạm gác rồi khôi phục được tính tới lần nhận sau cùng.
          </p>
        </>
      )}
    </DashboardPanel>
  );
}

/** Vạch tham chiếu nằm ở mép trái cột bắt đầu đúng mốc; nhãn ở dải trên vùng vẽ. */
function ReferenceMark({
  minutes,
  offsetClass,
  labelSide,
}: {
  minutes: number;
  offsetClass: string;
  /** Mốc sát cột cuối thì nhãn nằm bên trái vạch, không tràn khỏi thẻ. */
  labelSide: "left" | "right";
}) {
  const bucket = minutes >= WAIT_CRITICAL_MINUTES ? "CRITICAL" : "WARNING";
  const Icon = WAIT_BUCKET_META[bucket].icon;
  return (
    <span
      aria-hidden="true"
      className={cn("pointer-events-none absolute -top-8 bottom-0 z-10 w-0.5 bg-foreground/50", offsetClass)}
    >
      <span
        className={cn(
          "absolute top-0 flex items-center gap-1 whitespace-nowrap text-sm font-semibold leading-6 text-foreground",
          labelSide === "right" ? "left-2" : "right-2",
        )}
      >
        <Icon className={cn("size-4 shrink-0", MARK_ICON_INK[bucket])} />
        {minutes} phút
      </span>
    </span>
  );
}

function ClaimHistogram({ claim }: { claim: SimpleFlaggedClaimDTO }) {
  const bins = claim.bins;
  const max = bins.reduce((peak, bin) => Math.max(peak, bin.count), 0);
  const axis = niceCountAxis(max);
  const keys = bins.map((bin) => String(bin.min_minutes));
  const { shownKey, markProps } = useMarkFocus(keys);
  const activeIndex = shownKey === null ? -1 : keys.indexOf(shownKey);
  const active = activeIndex >= 0 ? bins[activeIndex] : undefined;

  return (
    <div className="mt-10 grid grid-cols-[2rem_minmax(0,1fr)] gap-x-2">
      <div aria-hidden="true" className={cn("relative", PLOT_HEIGHT_CLASS)}>
        {axis.ticks.map((tick) => (
          <span
            key={tick}
            style={{ bottom: `${(tick / axis.top) * 100}%` }}
            className="absolute right-0 translate-y-1/2 text-sm leading-none tabular-nums text-muted-foreground"
          >
            {formatCount(tick)}
          </span>
        ))}
      </div>

      <div className={cn("relative", PLOT_HEIGHT_CLASS)}>
        {axis.ticks.map((tick) => (
          <span
            key={tick}
            aria-hidden="true"
            style={{ bottom: `${(tick / axis.top) * 100}%` }}
            className={cn("absolute inset-x-0 h-px", tick === 0 ? "bg-[var(--viz-axis)]" : "bg-[var(--viz-grid)]")}
          />
        ))}

        <div
          role="list"
          aria-label={`Số ca có cờ theo số phút tới khi có người nhận, trên ${claim.claimed} ca đã có người nhận`}
          className="relative flex h-full items-end gap-0.5"
        >
          {bins.map((bin, index) => {
            const height = (bin.count / axis.top) * 100;
            const overflow = bin.max_minutes === null;
            return (
              <div
                key={bin.min_minutes}
                role="listitem"
                aria-label={`${claimBinLabel(bin)}: ${bin.count} ca`}
                {...markProps(String(bin.min_minutes))}
                className={cn(
                  "group relative h-full min-w-0 flex-1 cursor-default rounded-t-[4px] outline-hidden focus-visible:ring-2 focus-visible:ring-brand",
                  overflow && "ml-3",
                )}
              >
                {bin.min_minutes === WAIT_WARNING_MINUTES ? (
                  <ReferenceMark minutes={WAIT_WARNING_MINUTES} offsetClass="-left-0.5" labelSide="right" />
                ) : null}
                {overflow ? (
                  <ReferenceMark minutes={WAIT_CRITICAL_MINUTES} offsetClass="-left-2" labelSide="left" />
                ) : null}
                {bin.count > 0 ? (
                  <span
                    aria-hidden="true"
                    style={
                      {
                        "--col-h": `${height}%`,
                        "--col-delay": `${index * 24}ms`,
                        backgroundColor: "var(--viz-slot-1)",
                      } as CSSProperties
                    }
                    className="col-fill col-reveal absolute inset-y-0 left-1/2 w-full max-w-6 -translate-x-1/2 group-hover:brightness-110 group-focus-visible:brightness-110"
                  />
                ) : null}
              </div>
            );
          })}
        </div>

        <AnimatePresence>
          {active ? (
            <MarkTooltip key={active.min_minutes} anchor={((activeIndex + 0.5) / bins.length) * 100}>
              <TooltipBody
                value={`${formatCount(active.count)} ca`}
                label={
                  active.max_minutes === null
                    ? `Nhận sau ${active.min_minutes} phút trở lên`
                    : `Nhận sau ${claimBinLabel(active)}`
                }
                detail={`${percentOf(active.count, claim.claimed)} trên ${formatCount(claim.claimed)} ca đã có người nhận`}
              />
            </MarkTooltip>
          ) : null}
        </AnimatePresence>
      </div>

      <span aria-hidden="true" />
      <div aria-hidden="true" className="mt-2 flex gap-0.5">
        {bins.map((bin) => (
          <span
            key={bin.min_minutes}
            className={cn(
              "relative min-w-0 flex-1 text-sm leading-6 tabular-nums text-muted-foreground",
              bin.max_minutes === null && "ml-3 text-center",
            )}
          >
            {bin.max_minutes === null ? (
              `${bin.min_minutes}+`
            ) : bin.min_minutes % AXIS_LABEL_EVERY_MINUTES === 0 ? (
              <span className="absolute left-0 -translate-x-1/2">{bin.min_minutes}</span>
            ) : null}
          </span>
        ))}
      </div>
      <span aria-hidden="true" />
      <p className="mt-2 text-sm leading-6 text-muted-foreground">Số phút từ lúc gắn cờ tới khi có người nhận</p>
    </div>
  );
}

function ClaimTable({ bins }: { bins: SimpleClaimBinDTO[] }) {
  return (
    <div className="mt-4 max-h-80 overflow-y-auto">
      <table className="w-full text-left text-sm">
        <caption className="sr-only">Số ca có cờ theo thời gian từ lúc gắn cờ tới khi có người nhận</caption>
        <thead className="sticky top-0 bg-card">
          <tr className="border-b border-border">
            <th scope="col" className="py-2 pr-4 font-semibold text-muted-foreground">
              Thời gian tới khi có người nhận
            </th>
            <th scope="col" className="py-2 pl-4 text-right font-semibold text-muted-foreground">
              Số ca
            </th>
          </tr>
        </thead>
        <tbody className="divide-y divide-border">
          {bins.map((bin) => {
            const bucket = claimBinBucket(bin);
            const Icon = WAIT_BUCKET_META[bucket].icon;
            return (
              <tr key={bin.min_minutes}>
                <th scope="row" className="py-2 pr-4 font-medium tabular-nums text-foreground">
                  <span className="flex items-center gap-2">
                    {bucket === "UNDER_WARNING" ? (
                      <span aria-hidden="true" className="size-4 shrink-0" />
                    ) : (
                      <Icon className={cn("size-4 shrink-0", MARK_ICON_INK[bucket])} aria-hidden="true" />
                    )}
                    {claimBinLabel(bin)}
                    {bucket !== "UNDER_WARNING" ? (
                      <span className="sr-only">
                        , từ mốc {bucket === "CRITICAL" ? WAIT_CRITICAL_MINUTES : WAIT_WARNING_MINUTES} phút của bảng ca
                      </span>
                    ) : null}
                  </span>
                </th>
                <td className="py-2 pl-4 text-right font-semibold tabular-nums text-foreground">
                  {formatCount(bin.count)}
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}
