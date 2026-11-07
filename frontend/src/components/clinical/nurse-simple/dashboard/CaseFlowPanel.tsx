"use client";

import { Archive, ChevronRight, CircleCheckBig, Inbox, UserRoundCheck, type LucideIcon } from "lucide-react";
import { useState } from "react";

import { cn } from "@/lib/utils";
import type { SimpleNurseDashboardDTO } from "@/types/simple-nurse";

import { AnimatedNumber } from "./AnimatedNumber";
import { formatCount } from "./dashboard-model";
import { DashboardPanel } from "./primitives";

interface FlowStage {
  key: "waiting" | "assigned" | "decided" | "parked";
  label: string;
  value: number;
  hint: string;
  icon: LucideIcon;
}

/**
 * Đếm số lần một giá trị TĂNG giữa hai lần làm mới. Lần hiện đầu tiên không
 * tính: chấm trên đường nối chỉ được nói "vừa có thêm ca tới bước này", không
 * phải trang trí lúc tải trang. Giữ giá trị trước bằng state và cập nhật ngay
 * trong lúc render (mẫu "lưu thông tin của lần render trước" của React), nên
 * không cần effect hay ref.
 */
function useIncreaseTick(value: number): number {
  const [previous, setPrevious] = useState(value);
  const [tick, setTick] = useState(0);
  if (value !== previous) {
    setPrevious(value);
    if (value > previous) setTick(tick + 1);
  }
  return tick;
}

/**
 * Luồng xử lý ca: ca đang ở bước nào của kíp trực. Ba bước chính nối nhau theo
 * đúng chiều một ca đi qua (chờ người nhận → đang xử lý → đã chốt); "Tạm gác"
 * đứng riêng vì ca có thể bị gác từ bước nào cũng được và quay về hàng đợi.
 *
 * Khi số ca của một bước tăng giữa hai lần làm mới, một chấm chạy dọc đường nối
 * vào bước đó đúng một lượt, còn con số sáng lên. Đó là "cái gì vừa thay đổi";
 * con số vẫn là sự thật, chấm chỉ chỉ chỗ.
 */
export function CaseFlowPanel({
  dashboard,
  decidedLast24h,
  order,
}: {
  dashboard: SimpleNurseDashboardDTO;
  decidedLast24h: number;
  order: number;
}) {
  const assignedTick = useIncreaseTick(dashboard.assigned_total);
  const decidedTick = useIncreaseTick(dashboard.decided);

  const waiting: FlowStage = {
    key: "waiting",
    label: "Chờ người nhận",
    value: dashboard.waiting,
    hint: "Chưa ai nhận ca",
    icon: Inbox,
  };
  const assigned: FlowStage = {
    key: "assigned",
    label: "Đang xử lý",
    value: dashboard.assigned_total,
    hint: `Bạn đang giữ ${formatCount(dashboard.assigned_to_me)} ca`,
    icon: UserRoundCheck,
  };
  const decided: FlowStage = {
    key: "decided",
    label: "Đã chốt",
    value: dashboard.decided,
    hint: `${formatCount(decidedLast24h)} ca trong 24 giờ qua`,
    icon: CircleCheckBig,
  };
  const parked: FlowStage = {
    key: "parked",
    label: "Tạm gác",
    value: dashboard.parked,
    hint: "Chờ bổ sung thông tin",
    icon: Archive,
  };

  return (
    <DashboardPanel
      id="case-flow"
      order={order}
      title="Luồng xử lý ca"
      subtitle="Ca của cả kíp trực đang ở bước nào, tính đến lúc cập nhật."
    >
      <ol
        role="list"
        className="grid grid-cols-2 gap-4 lg:grid-cols-[minmax(0,1fr)_4rem_minmax(0,1fr)_4rem_minmax(0,1fr)_minmax(0,1fr)] lg:gap-0"
      >
        <StageItem stage={waiting} />
        <Connector tick={assignedTick} />
        <StageItem stage={assigned} />
        <Connector tick={decidedTick} />
        <StageItem stage={decided} />
        <StageItem stage={parked} detached />
      </ol>
    </DashboardPanel>
  );
}

function StageItem({ stage, detached = false }: { stage: FlowStage; detached?: boolean }) {
  const Icon = stage.icon;
  return (
    <li
      className={cn(
        "flex min-w-0 flex-col rounded-xl bg-muted/50 p-4",
        detached && "lg:ml-6 lg:bg-transparent lg:ring-1 lg:ring-inset lg:ring-border",
      )}
    >
      <span className="flex items-center gap-2 text-sm font-semibold leading-6 text-muted-foreground">
        <span className="flex size-8 shrink-0 items-center justify-center rounded-xl bg-card text-brand-ink shadow-xs">
          <Icon className="size-4" aria-hidden="true" />
        </span>
        {stage.label}
      </span>
      <span className="mt-4 block text-3xl font-extrabold leading-none tracking-tight text-foreground">
        <AnimatedNumber value={stage.value} />
      </span>
      <span className="mt-2 block text-sm leading-6 text-muted-foreground">{stage.hint}</span>
    </li>
  );
}

/** Đường nối giữa hai bước (chỉ hiện trên màn rộng), kèm chấm chạy khi bước sau vừa tăng. */
function Connector({ tick }: { tick: number }) {
  return (
    <li aria-hidden="true" className="relative hidden items-center lg:flex">
      <span className="relative mx-2 h-0.5 flex-1 rounded-full bg-[var(--viz-axis)]">
        {tick > 0 ? (
          <span
            key={tick}
            className="flow-travel absolute top-1/2 size-2.5 -translate-x-1/2 -translate-y-1/2 rounded-full bg-brand shadow-[0_0_0_2px_var(--card)]"
          />
        ) : null}
      </span>
      <ChevronRight className="-ml-3 size-4 shrink-0 text-[var(--viz-axis)]" strokeWidth={3} />
    </li>
  );
}
