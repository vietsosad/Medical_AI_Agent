"use client";

import { useState } from "react";
import Link from "next/link";
import { usePathname, useSearchParams } from "next/navigation";
import { LayoutGroup, motion } from "framer-motion";
import {
  Activity,
  Archive,
  CircleCheckBig,
  ClipboardList,
  FileCheckCorner,
  LayoutDashboard,
  LogOut,
  Stethoscope,
  UserRoundCheck,
  type LucideIcon,
} from "lucide-react";
import { toast } from "sonner";

import { ClinicalInbox } from "@/components/clinical/ClinicalInbox";
import { useClinicalRealtime } from "@/components/clinical/ClinicalRealtimeProvider";
import { SimpleClinicalInbox } from "@/components/clinical/nurse-simple/SimpleClinicalInbox";
import { AnimatedCount } from "@/components/clinical/nurse-simple/queue/AnimatedCount";
import {
  SHARED_QUEUE_PARAMS,
  initialsOf,
  isUrgentCase,
  parseQueueTab,
} from "@/components/clinical/nurse-simple/queue/queue-model";
import { useNurseQueue } from "@/hooks/queries/use-clinical-hitl";
import { IS_PILOT_AGENT_ACTIVE, nurseQueueHref } from "@/lib/agent-mode";
import { DURATION, EASE_IN_OUT } from "@/lib/motion";
import type { ClinicalSocketStatus } from "@/lib/realtime/useClinicalSocket";
import { cn } from "@/lib/utils";
import { useSimpleNurseQueue } from "@/queries/useSimpleNurseQueries";
import { useAuthStore } from "@/store/useAuthStore";

/**
 * ============================================================================
 * [CLINICAL RAIL] THANH ĐIỀU PHỐI CỦA TRẠM LÂM SÀNG
 * ============================================================================
 * Ba điều thanh này phải luôn nói được, không cần cuộn:
 *
 * 1. **Còn bao nhiêu ca đang chờ.** Con số đứng ngay cạnh mục điều hướng thay vì
 *    bắt nhân viên mở từng danh sách ra đếm; số đỏ khi trong đó có ca khẩn chưa
 *    ai nhận.
 * 2. **Kênh thời gian thực còn sống hay không.** Một hàng đợi đứng im vì mất kết
 *    nối trông y hệt một hàng đợi rỗng — phải phân biệt được hai tình huống đó.
 * 3. **Ai đang đăng nhập và làm sao thoát ra.** Thanh được ghim theo khung nhìn
 *    nên nút đăng xuất không bao giờ trôi khỏi màn hình.
 *
 * Thanh luôn tối ở cả hai chế độ (bản thiết kế "Hàng đợi điều phối"). Class
 * `dark` trên `<aside>` biến nó thành một "đảo tối": token màu (`bg-card`,
 * `text-foreground`, `border-border`, `bg-brand`...) và biến thể `dark:` bên
 * trong đều lấy giá trị tối, kể cả nút hộp thư do component khác vẽ. Ngăn kéo
 * hộp thư của Triage Agent được portal ra `<body>` nên vẫn theo chế độ của trang.
 */

/** Đường điều hướng khi Triage Agent không phải luồng đang chạy (hàng đợi cũ). */
const legacyLinks = [
  {
    label: "Hàng đợi",
    href: nurseQueueHref(),
    mode: "all",
    icon: ClipboardList,
    hint: "Toàn bộ ca đang chờ",
  },
  {
    label: "Ca của tôi",
    href: "/clinical/queue?mine=1",
    mode: "mine",
    icon: UserRoundCheck,
    hint: "Ca bạn đang phụ trách",
  },
  {
    label: "Đánh giá chuyên sâu",
    href: "/clinical/queue?specialist=1",
    mode: "specialist",
    icon: FileCheckCorner,
    hint: "Ca chờ bác sĩ rà soát",
  },
] as const;

// Hàng đợi pilot (/clinical/queue-pilot) điều hướng bằng query `?tab=` (xem
// .claude/plans/sunny-launching-mitten.md) -- cơ chế khác hẳn production
// (`mine`/`specialist`) nên dùng mảng riêng. "Tổng quan" là mục duy nhất trỏ
// ra một tuyến riêng, nên nó mang `href`; phần render phân biệt hai dạng bằng
// chính khóa đó.
const pilotLinks = [
  {
    label: "Tổng quan",
    href: "/clinical/dashboard-pilot",
    icon: LayoutDashboard,
    hint: "Số liệu toàn trạm trực",
  },
  { label: "Hàng đợi", tab: "queue", icon: ClipboardList, hint: "Ca đang chờ, chưa ai nhận" },
  { label: "Ca của tôi", tab: "mine", icon: UserRoundCheck, hint: "Ca bạn đang phụ trách" },
  { label: "Tạm gác", tab: "parked", icon: Archive, hint: "Ca đã tạm gác, chờ xử lý tiếp" },
  { label: "Đã quyết định", tab: "decided", icon: CircleCheckBig, hint: "Ca đã có quyết định cuối cùng" },
] as const;

type CountTone = "neutral" | "urgent" | "info";

function NavItem({
  href,
  label,
  hint,
  icon: Icon,
  active,
  count,
  countLabel,
  countTone = "neutral",
}: {
  href: string;
  label: string;
  hint: string;
  icon: LucideIcon;
  active: boolean;
  count?: number;
  countLabel?: string;
  countTone?: CountTone;
}) {
  return (
    <Link
      href={href}
      title={hint}
      aria-current={active ? "page" : undefined}
      className={cn(
        "group relative flex min-h-11 shrink-0 items-center gap-2 rounded-xl px-4 text-sm font-semibold transition-colors duration-200",
        "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-teal-300",
        active ? "text-white" : "text-slate-300 hover:bg-white/5 hover:text-white",
      )}
    >
      {/* Nền của mục đang mở trượt sang mục mới khi chuyển trang: mắt đi theo được mình vừa tới đâu. */}
      {active && (
        <motion.span
          layoutId="clinical-nav-active"
          aria-hidden="true"
          className="absolute inset-0 rounded-xl bg-slate-800 shadow-sm ring-1 ring-white/5"
          transition={{ type: "tween", duration: DURATION.base, ease: EASE_IN_OUT }}
        />
      )}
      <Icon
        aria-hidden="true"
        className={cn(
          "relative size-5 shrink-0 transition-colors duration-200",
          active ? "text-teal-300" : "text-slate-400 group-hover:text-slate-200",
        )}
      />
      <span className="relative truncate max-sm:sr-only lg:flex-1">{label}</span>
      {typeof count === "number" && (
        <span
          className={cn(
            "relative ml-auto inline-flex min-w-8 items-center justify-center rounded-full px-2 text-sm font-bold leading-6 transition-colors duration-200",
            countTone === "urgent"
              ? "bg-rose-600 text-white"
              : countTone === "info"
                ? "bg-sky-400/20 text-sky-100"
                : active
                  ? "bg-teal-300/15 text-teal-100"
                  : "bg-slate-700/80 text-slate-100",
          )}
        >
          <AnimatedCount value={count} />
          {countLabel && <span className="sr-only"> {countLabel}</span>}
        </span>
      )}
    </Link>
  );
}

function PilotNavItems({ pathname, tab }: { pathname: string; tab: string }) {
  // Cùng khóa với lời gọi mặc định của màn hàng đợi (SHARED_QUEUE_PARAMS) nên
  // hai nơi dùng chung một lần gọi mạng; kênh realtime làm mới cả hai.
  const queue = useSimpleNurseQueue(SHARED_QUEUE_PARAMS);
  // Số ca chưa ai nhận: đúng bằng số hàng của tab "Đang chờ". Trang 1 đã xếp ca
  // khẩn lên đầu, nên nếu có ca khẩn chưa ai nhận thì nó nằm ở trang này.
  const waiting = queue.data?.pagination.total_items;
  const mine = queue.data?.summary.mine_count;
  const hasUrgent = (queue.data?.items ?? []).some(isUrgentCase);

  return (
    <>
      {pilotLinks.map((item) => {
        if ("href" in item) {
          return (
            <NavItem
              key={item.href}
              href={item.href}
              label={item.label}
              hint={item.hint}
              icon={item.icon}
              active={pathname === item.href}
            />
          );
        }

        const href = `/clinical/queue-pilot?tab=${item.tab}`;
        const urgent = item.tab === "queue" && hasUrgent && (waiting ?? 0) > 0;
        // "Tạm gác"/"Đã quyết định" không có bộ đếm ở đây: thà bỏ trống còn hơn
        // gọi thêm hai request ở mọi trang chỉ để hiện một con số.
        const count = item.tab === "queue" ? waiting : item.tab === "mine" ? mine : undefined;
        const countLabel =
          item.tab === "queue"
            ? urgent
              ? "ca chưa ai nhận, có ca khẩn"
              : "ca chưa ai nhận"
            : "ca bạn phụ trách";

        return (
          <NavItem
            key={href}
            href={href}
            label={item.label}
            hint={item.hint}
            icon={item.icon}
            active={pathname === "/clinical/queue-pilot" && tab === item.tab}
            count={count}
            countLabel={countLabel}
            countTone={urgent ? "urgent" : "neutral"}
          />
        );
      })}
    </>
  );
}

function LegacyNavItems({ pathname, mine, specialist }: { pathname: string; mine: boolean; specialist: boolean }) {
  // Cùng query key với màn hình hàng đợi nên TanStack Query dùng chung một lần
  // gọi mạng; kênh realtime bên dưới làm mới cả hai.
  const queue = useNurseQueue({});
  const summary = queue.data?.summary;
  const counts: Record<(typeof legacyLinks)[number]["mode"], number | undefined> = {
    all: summary?.total_waiting,
    mine: summary?.mine_count,
    specialist: summary?.specialist_count,
  };

  return (
    <>
      {legacyLinks.map((item) => {
        const active =
          pathname === "/clinical/queue" &&
          ((item.mode === "all" && !mine && !specialist) ||
            (item.mode === "mine" && mine) ||
            (item.mode === "specialist" && specialist));
        const count = counts[item.mode];
        return (
          <NavItem
            key={item.href}
            href={item.href}
            label={item.label}
            hint={item.hint}
            icon={item.icon}
            active={active}
            count={count}
            countTone={item.mode === "specialist" && (count ?? 0) > 0 ? "info" : "neutral"}
          />
        );
      })}
    </>
  );
}

/** Kênh realtime còn sống hay đang nối lại -- chấm xanh tỏa sáng khi còn sống. */
function ChannelStatus({ status, compact = false }: { status: ClinicalSocketStatus; compact?: boolean }) {
  const online = status === "open";
  const label = online ? "Trực tuyến" : status === "connecting" ? "Đang kết nối" : "Đang kết nối lại";
  return (
    <p
      title={online ? "Ca mới và báo động đỏ được đẩy tới ngay" : "Mất kết nối realtime. Đang kết nối lại..."}
      className={cn("flex items-center gap-2 text-sm font-medium", online ? "text-emerald-300" : "text-amber-300")}
    >
      <span
        aria-hidden="true"
        className={cn(
          "size-2 shrink-0 rounded-full",
          online ? "live-dot bg-emerald-400" : "animate-pulse bg-amber-400 motion-reduce:animate-none",
        )}
      />
      <span className={compact ? "max-sm:sr-only" : undefined}>{label}</span>
    </p>
  );
}

export function ClinicalSidebar() {
  const pathname = usePathname();
  const searchParams = useSearchParams();
  const mine = searchParams.get("mine") === "1";
  const specialist = searchParams.get("specialist") === "1";
  const pilotTab = parseQueueTab(searchParams.get("tab"));
  const { user, logout } = useAuthStore();
  const { status: realtimeStatus } = useClinicalRealtime();
  const [signingOut, setSigningOut] = useState(false);

  const isSpecialist = user?.capabilities?.includes("SPECIALIST_REVIEW") ?? false;
  const roleLabel = isSpecialist ? "Bác sĩ · đánh giá chuyên sâu" : "Điều dưỡng phân luồng";

  const handleLogout = async () => {
    setSigningOut(true);
    await logout(true);
    toast.success("Đã kết thúc phiên trực và đăng xuất an toàn.");
  };

  return (
    <aside
      className={cn(
        "dark flex w-full shrink-0 flex-col border-b border-border bg-slate-900 text-foreground",
        // Ghim theo khung nhìn: nút đăng xuất và bộ đếm ca luôn trong tầm mắt,
        // dù hàng đợi có dài tới đâu.
        "lg:sticky lg:top-0 lg:h-screen lg:w-64 lg:overflow-y-auto lg:border-b-0 lg:border-r",
      )}
    >
      {/* ---------------------------------------------------- NHẬN DIỆN TRẠM */}
      <div className="flex items-center justify-between gap-4 p-4 lg:px-4 lg:pb-6 lg:pt-6">
        <Link
          href={nurseQueueHref()}
          className="group/brand flex min-h-11 items-center gap-2 rounded-xl pr-2 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-teal-300 focus-visible:ring-offset-2 focus-visible:ring-offset-slate-900"
        >
          <span className="flex size-10 shrink-0 items-center justify-center rounded-xl bg-brand text-brand-foreground transition-transform duration-200 ease-out group-hover/brand:scale-105 motion-reduce:group-hover/brand:scale-100">
            <Activity className="size-5" strokeWidth={2.4} aria-hidden="true" />
          </span>
          <span className="min-w-0">
            <span className="block text-base font-extrabold tracking-tight text-white">Trạm điều phối</span>
            <span className="block text-sm text-muted-foreground">Clinical Triage</span>
          </span>
        </Link>

        <div className="flex shrink-0 items-center gap-2 lg:hidden">
          <ChannelStatus status={realtimeStatus} compact />
          <button
            type="button"
            onClick={() => void handleLogout()}
            disabled={signingOut}
            aria-label="Đăng xuất khỏi trạm lâm sàng"
            className="flex size-11 shrink-0 items-center justify-center rounded-xl border border-white/10 text-slate-300 transition-colors hover:border-rose-400/50 hover:bg-rose-500/10 hover:text-rose-100 disabled:opacity-60 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-rose-400"
          >
            <LogOut className="size-5" strokeWidth={2.2} aria-hidden="true" />
          </button>
        </div>
      </div>

      {/* ------------------------------------------------------- ĐIỀU HƯỚNG */}
      <LayoutGroup id="clinical-nav">
        <nav
          aria-label="Điều hướng nhân viên lâm sàng"
          className="flex gap-2 overflow-x-auto px-4 pb-4 lg:flex-col lg:overflow-visible lg:pb-0"
        >
          <p className="hidden px-4 pb-2 text-xs font-bold uppercase tracking-wider text-slate-400 lg:block">
            Điều phối
          </p>
          {IS_PILOT_AGENT_ACTIVE ? (
            <PilotNavItems pathname={pathname} tab={pilotTab} />
          ) : (
            <LegacyNavItems pathname={pathname} mine={mine} specialist={specialist} />
          )}
        </nav>
      </LayoutGroup>

      <div className="px-4 pb-4 lg:pt-4">
        {/* Ca pilot đã claim + có tin nhắn mới -- không dùng ClinicalInbox
            production ở đây vì nó chỉ đọc dữ liệu production, không hề biết
            gì về simple_agent (bug thật, 2026-08-29: điều dưỡng không thấy
            thông báo tin nhắn pilot ở đúng chỗ họ đang nhìn). */}
        {IS_PILOT_AGENT_ACTIVE ? <SimpleClinicalInbox /> : <ClinicalInbox />}
      </div>

      {/* ------------------------------------------- NGƯỜI TRỰC & ĐĂNG XUẤT */}
      <div className="mt-auto hidden p-4 lg:block">
        <div className="rounded-2xl bg-slate-800/80 p-4">
          <div className="flex items-center gap-2">
            <span
              aria-hidden="true"
              className="flex size-10 shrink-0 items-center justify-center rounded-full bg-teal-100 text-sm font-extrabold text-teal-900"
            >
              {initialsOf(user?.name)}
            </span>
            {/* Tên dài xuống dòng thay vì bị cắt: người trực phải đọc được đúng tên mình. */}
            <p className="line-clamp-2 min-w-0 text-sm font-bold leading-5 text-white">
              {user?.name ?? "Nhân viên lâm sàng"}
            </p>
          </div>
          <p className="mt-2 flex items-start gap-2 text-sm text-muted-foreground">
            <span className="flex h-5 shrink-0 items-center">
              <Stethoscope className="size-4" aria-hidden="true" />
            </span>
            <span className="min-w-0 leading-5">{roleLabel}</span>
          </p>
          <div className="mt-2">
            <ChannelStatus status={realtimeStatus} />
          </div>
        </div>

        <button
          type="button"
          onClick={() => void handleLogout()}
          disabled={signingOut}
          className="mt-2 flex min-h-11 w-full items-center justify-center gap-2 rounded-xl border border-white/10 px-4 text-sm font-bold text-slate-200 transition-colors hover:border-rose-400/50 hover:bg-rose-500/10 hover:text-rose-100 disabled:cursor-not-allowed disabled:opacity-60 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-rose-400 focus-visible:ring-offset-2 focus-visible:ring-offset-slate-900"
        >
          <LogOut className="size-4 shrink-0" strokeWidth={2.2} aria-hidden="true" />
          {signingOut ? "Đang đăng xuất..." : "Đăng xuất"}
        </button>
      </div>
    </aside>
  );
}
