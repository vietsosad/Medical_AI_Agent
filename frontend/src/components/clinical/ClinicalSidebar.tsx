"use client";

import { useState } from "react";
import {
  Archive,
  ClipboardList,
  FileCheck2,
  LayoutDashboard,
  LogOut,
  ShieldCheck,
  Stethoscope,
  UserRoundCheck,
} from "lucide-react";
import Link from "next/link";
import { usePathname, useSearchParams } from "next/navigation";
import { toast } from "sonner";

import { ClinicalInbox } from "@/components/clinical/ClinicalInbox";
import { SimpleClinicalInbox } from "@/components/clinical/nurse-simple/SimpleClinicalInbox";
import { useClinicalRealtime } from "@/components/clinical/ClinicalRealtimeProvider";
import { useNurseQueue } from "@/hooks/queries/use-clinical-hitl";
import { useSimpleNurseQueue } from "@/queries/useSimpleNurseQueries";
import { IS_PILOT_AGENT_ACTIVE, nurseQueueHref } from "@/lib/agent-mode";
import { cn } from "@/lib/utils";
import { useAuthStore } from "@/store/useAuthStore";

/**
 * ============================================================================
 * [CLINICAL RAIL] THANH ĐIỀU PHỐI CỦA TRẠM LÂM SÀNG
 * ============================================================================
 * Ba điều thanh này phải luôn nói được, không cần cuộn:
 *
 * 1. **Còn bao nhiêu ca đang chờ.** Con số đứng ngay cạnh mục điều hướng thay vì
 *    bắt nhân viên mở từng danh sách ra đếm.
 * 2. **Kênh thời gian thực còn sống hay không.** Một hàng đợi đứng im vì mất kết
 *    nối trông y hệt một hàng đợi rỗng — phải phân biệt được hai tình huống đó.
 * 3. **Ai đang đăng nhập và làm sao thoát ra.** Bản trước đặt khối này ở đáy một
 *    ``<aside>`` cao bằng cả trang, nên với hàng đợi dài thì nút đăng xuất nằm
 *    cách màn hình hàng nghìn pixel. Giờ thanh được ghim theo khung nhìn.
 */

const links = [
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
    icon: FileCheck2,
    hint: "Ca chờ bác sĩ rà soát",
  },
] as const;

// Hàng đợi pilot (/clinical/queue-pilot) có 4 tab thật riêng của nó (Hàng
// đợi/Ca của tôi/Tạm gác lại/Đã xác nhận, xem
// .claude/plans/sunny-launching-mitten.md) -- theo yêu cầu người dùng, 4 tab
// đó chuyển hẳn lên sidebar (điều hướng bằng query `?tab=`) thay vì nằm
// thành thanh tab ngang trong chính trang. Cơ chế lọc khác hẳn production
// (`tab` thay vì `mine`/`specialist`) nên dùng mảng riêng, không tái dùng
// `links` ở trên.
const pilotLinks = [
  // Mục duy nhất trỏ ra một tuyến riêng thay vì một tab của hàng đợi, nên nó
  // mang `href`; phần render bên dưới phân biệt hai dạng bằng chính khóa đó.
  {
    label: "Tổng quan",
    href: "/clinical/dashboard-pilot",
    icon: LayoutDashboard,
    hint: "Số liệu toàn trạm trực",
  },
  { label: "Hàng đợi", tab: "queue", icon: ClipboardList, hint: "Toàn bộ ca đang chờ" },
  { label: "Ca của tôi", tab: "mine", icon: UserRoundCheck, hint: "Ca bạn đang phụ trách" },
  { label: "Tạm gác lại", tab: "parked", icon: Archive, hint: "Ca đã tạm gác, chờ xử lý tiếp" },
  { label: "Đã xác nhận", tab: "decided", icon: FileCheck2, hint: "Ca đã có quyết định cuối cùng" },
] as const;

export function ClinicalSidebar() {
  const pathname = usePathname();
  const searchParams = useSearchParams();
  const mine = searchParams.get("mine") === "1";
  const specialist = searchParams.get("specialist") === "1";
  const pilotTab = searchParams.get("tab") ?? "queue";
  const { user, logout } = useAuthStore();
  const [signingOut, setSigningOut] = useState(false);

  // Cùng query key với màn hình hàng đợi nên TanStack Query dùng chung một lần
  // gọi mạng; kênh realtime bên dưới làm mới cả hai.
  const queue = useNurseQueue({});
  // Bộ đếm cho 4 tab của Triage Agent. Tham số trùng khớp lời gọi mặc định của
  // SimpleNurseQueueWorkspace (tab "Hàng đợi", chưa áp bộ lọc nào) nên hai nơi
  // dùng chung một kết quả đã cache, không phát sinh request thứ hai.
  const pilotQueue = useSimpleNurseQueue(
    { bucket: "QUEUE", mineOnly: false, page: 1, pageSize: 20 },
    { enabled: IS_PILOT_AGENT_ACTIVE },
  );
  const pilotSummary = pilotQueue.data?.summary;
  // Chỉ hai bucket có số liệu thật trong `summary`; "Tạm gác lại"/"Đã xác nhận"
  // không có, và thà bỏ trống còn hơn hiện một con số không đúng nghĩa.
  const pilotCounts: Record<string, number | undefined> = {
    queue: pilotSummary?.total_waiting,
    mine: pilotSummary?.mine_count,
  };
  const { status: realtimeStatus } = useClinicalRealtime();
  const summary = queue.data?.summary;

  const counts: Record<string, number | undefined> = {
    all: summary?.total_waiting,
    mine: summary?.mine_count,
    specialist: summary?.specialist_count,
  };

  const isSpecialist = user?.capabilities?.includes("SPECIALIST_REVIEW") ?? false;
  const initial = user?.name?.trim()?.charAt(0)?.toUpperCase() ?? "?";

  const handleLogout = async () => {
    setSigningOut(true);
    await logout(true);
    toast.success("Đã kết thúc phiên trực và đăng xuất an toàn.");
  };

  const online = realtimeStatus === "open";

  return (
    <aside
      className={cn(
        "flex w-full shrink-0 flex-col border-b border-border bg-card",
        // Ghim theo khung nhìn: nút đăng xuất và bộ đếm ca luôn trong tầm mắt,
        // dù hàng đợi có dài tới đâu.
        "lg:sticky lg:top-0 lg:h-screen lg:w-72 lg:border-b-0 lg:border-r",
      )}
    >
      {/* ---------------------------------------------------- NHẬN DIỆN TRẠM */}
      <div className="flex items-center justify-between gap-3 border-slate-100 p-4 lg:block lg:border-b lg:p-5">
        <Link
          href={nurseQueueHref()}
          className="group/brand glow-soft glow-teal flex min-h-11 items-center gap-3 rounded-xl border border-transparent px-1 text-slate-950 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-teal-600 focus-visible:ring-offset-2 dark:text-slate-50"
        >
          <span className="flex size-11 shrink-0 items-center justify-center rounded-xl bg-gradient-to-br from-teal-600 to-sky-700 text-white shadow-sm transition-transform duration-300 ease-out group-hover/brand:scale-105 motion-reduce:group-hover/brand:scale-100">
            <ShieldCheck className="size-5 stroke-[2.2]" aria-hidden="true" />
          </span>
          <span className="min-w-0">
            <span className="block text-base font-bold tracking-tight">Clinical Triage</span>
            <span className="block text-sm text-muted-foreground">Trạm điều phối lâm sàng</span>
          </span>
        </Link>

        <div className="flex shrink-0 items-center gap-2 lg:mt-4 lg:block">
        <span
          title={
            online
              ? "Ca mới và báo động đỏ được đẩy tới ngay"
              : "Mất kết nối realtime. Đang kết nối lại..."
          }
          className={cn(
            "inline-flex shrink-0 items-center gap-2 rounded-full border px-2.5 py-1 text-xs font-bold lg:flex lg:w-fit",
            online
              ? "border-emerald-200 bg-emerald-50 text-emerald-800"
              : "border-amber-200 bg-amber-50 text-amber-900",
          )}
        >
          <span
            className={cn(
              "size-2 shrink-0 rounded-full",
              online ? "live-dot bg-emerald-500" : "animate-pulse bg-amber-500",
            )}
            aria-hidden="true"
          />
          {online ? "Realtime" : "Đang kết nối lại"}
        </span>

        <button
          type="button"
          onClick={() => void handleLogout()}
          disabled={signingOut}
          aria-label="Đăng xuất khỏi trạm lâm sàng"
          className="glow-soft glow-rose flex size-11 shrink-0 items-center justify-center rounded-xl border border-border bg-card text-slate-600 hover:border-rose-300 hover:text-rose-700 disabled:opacity-60 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-rose-500 lg:hidden dark:text-slate-300"
        >
          <LogOut className="size-5 stroke-[2.2]" aria-hidden="true" />
        </button>
        </div>
      </div>

      {/* ------------------------------------------------------- ĐIỀU HƯỚNG */}
      <nav
        aria-label="Điều hướng nhân viên lâm sàng"
        className="flex gap-2 px-4 pb-4 lg:mt-5 lg:flex-col lg:px-3 lg:pb-0"
      >
        <p className="hidden px-2 pb-2 text-xs font-bold uppercase tracking-wider text-slate-400 lg:block">
          Điều phối
        </p>

        {IS_PILOT_AGENT_ACTIVE
          ? pilotLinks.map((item) => {
              const href = "href" in item ? item.href : `/clinical/queue-pilot?tab=${item.tab}`;
              const active =
                "href" in item
                  ? pathname === item.href
                  : pathname === "/clinical/queue-pilot" && pilotTab === item.tab;
              const Icon = item.icon;
              const count = "tab" in item ? pilotCounts[item.tab] : undefined;
              return (
                <Link
                  key={href}
                  href={href}
                  title={item.hint}
                  aria-current={active ? "page" : undefined}
                  className={cn(
                    "group glow-soft glow-sky relative flex min-h-11 items-center gap-3 overflow-hidden rounded-xl border border-transparent px-3 text-sm font-semibold focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-sky-600 focus-visible:ring-offset-2",
                    active
                      ? "bg-slate-900 text-white"
                      : "text-slate-700 hover:bg-muted hover:text-slate-950 dark:text-slate-200",
                  )}
                >
                  <span
                    aria-hidden="true"
                    className={cn(
                      "absolute inset-y-1.5 left-0 w-1 rounded-full bg-sky-400 transition-transform duration-300 ease-out",
                      active ? "scale-y-100" : "scale-y-0",
                    )}
                  />
                  <Icon
                    className={cn(
                      "size-5 shrink-0 stroke-[2.1] transition-transform duration-300 ease-out group-hover:scale-110 motion-reduce:group-hover:scale-100",
                      active ? "text-white" : "text-muted-foreground group-hover:text-slate-700 dark:group-hover:text-slate-200",
                    )}
                    aria-hidden="true"
                  />
                  <span className="hidden truncate sm:inline lg:flex-1">{item.label}</span>

                  {/* Số ca đứng ngay cạnh mục, để không phải mở từng danh sách ra đếm. */}
                  {typeof count === "number" && (
                    <span
                      className={cn(
                        "ml-auto hidden shrink-0 rounded-md px-2 py-0.5 text-xs font-bold tabular-nums transition-colors sm:inline-block",
                        active
                          ? "bg-card/15 text-white"
                          : "bg-muted text-slate-700 group-hover:bg-card group-hover:text-foreground dark:text-slate-200",
                      )}
                    >
                      {count}
                    </span>
                  )}
                </Link>
              );
            })
          : links.map((item) => {
              const active =
                pathname === "/clinical/queue" &&
                ((item.mode === "all" && !mine && !specialist) ||
                  (item.mode === "mine" && mine) ||
                  (item.mode === "specialist" && specialist));
              const Icon = item.icon;
              const count = counts[item.mode];

              return (
                <Link
                  key={item.href}
                  href={item.href}
                  title={item.hint}
                  aria-current={active ? "page" : undefined}
                  className={cn(
                    "group glow-soft glow-sky relative flex min-h-11 items-center gap-3 overflow-hidden rounded-xl border border-transparent px-3 text-sm font-semibold focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-sky-600 focus-visible:ring-offset-2",
                    active
                      ? "bg-slate-900 text-white"
                      : "text-slate-700 hover:bg-muted hover:text-slate-950 dark:text-slate-200",
                  )}
                >
                  <span
                    aria-hidden="true"
                    className={cn(
                      "absolute inset-y-1.5 left-0 w-1 rounded-full bg-sky-400 transition-transform duration-300 ease-out",
                      active ? "scale-y-100" : "scale-y-0",
                    )}
                  />
                  <Icon
                    className={cn(
                      "size-5 shrink-0 stroke-[2.1] transition-transform duration-300 ease-out group-hover:scale-110 motion-reduce:group-hover:scale-100",
                      active ? "text-white" : "text-muted-foreground group-hover:text-slate-700 dark:group-hover:text-slate-200",
                    )}
                    aria-hidden="true"
                  />
                  <span className="hidden truncate sm:inline lg:flex-1">{item.label}</span>

                  {/* Con số đứng ngay cạnh mục, để không phải mở từng danh sách ra đếm. */}
                  {typeof count === "number" && (
                    <span
                      className={cn(
                        "ml-auto hidden shrink-0 rounded-md px-2 py-0.5 text-xs font-bold tabular-nums transition-colors sm:inline-block",
                        active
                          ? "bg-card/15 text-white"
                          : item.mode === "specialist" && count > 0
                            ? "bg-sky-100 text-sky-900"
                            : "bg-muted text-slate-700 group-hover:bg-card group-hover:text-foreground dark:text-slate-200",
                      )}
                    >
                      {count}
                    </span>
                  )}
                </Link>
              );
            })}
      </nav>

      <div className="px-4 pb-4 lg:px-3 lg:pt-2">
        {/* Ca pilot đã claim + có tin nhắn mới -- không dùng ClinicalInbox
            production ở đây vì nó chỉ đọc dữ liệu production, không hề biết
            gì về simple_agent (bug thật, 2026-08-29: điều dưỡng không thấy
            thông báo tin nhắn pilot ở đúng chỗ họ đang nhìn). */}
        {IS_PILOT_AGENT_ACTIVE ? <SimpleClinicalInbox /> : <ClinicalInbox />}
      </div>

      {/* ------------------------------------------- NGƯỜI TRỰC & ĐĂNG XUẤT */}
      <div className="mt-auto hidden border-t border-border p-3 lg:block lg:p-4">
        <div className="group/who glow-soft glow-sky flex items-center gap-3 rounded-xl border border-transparent bg-background p-3">
          <span className="flex size-10 shrink-0 items-center justify-center rounded-lg bg-slate-900 text-sm font-bold text-white transition-transform duration-300 ease-out group-hover/who:scale-105 motion-reduce:group-hover/who:scale-100">
            {initial}
          </span>
          <div className="min-w-0 flex-1">
            <p className="truncate text-sm font-bold text-foreground">
              {user?.name ?? "Nhân viên lâm sàng"}
            </p>
            <p className="mt-0.5 flex items-center gap-1.5 text-xs font-semibold text-muted-foreground">
              <Stethoscope className="size-3.5 shrink-0" aria-hidden="true" />
              {isSpecialist ? "Bác sĩ · đánh giá chuyên sâu" : "Điều dưỡng phân luồng"}
            </p>
          </div>
        </div>

        <button
          type="button"
          onClick={() => void handleLogout()}
          disabled={signingOut}
          className="glow-soft glow-rose mt-2.5 flex min-h-11 w-full items-center justify-center gap-2 rounded-xl border border-border bg-card px-4 text-sm font-bold text-slate-700 hover:border-rose-300 hover:text-rose-700 disabled:cursor-not-allowed disabled:opacity-60 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-rose-500 focus-visible:ring-offset-2 dark:text-slate-200"
        >
          <LogOut className="size-4 shrink-0 stroke-[2.2]" aria-hidden="true" />
          {signingOut ? "Đang đăng xuất..." : "Đăng xuất"}
        </button>
      </div>
    </aside>
  );
}
