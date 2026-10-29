"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { motion } from "framer-motion";
import { History, MessageSquare, Users, type LucideIcon } from "lucide-react";

import { triageHistoryListHref, triageStartHref } from "@/lib/agent-mode";
import { DURATION, EASE_IN_OUT } from "@/lib/motion";
import { cn } from "@/lib/utils";

interface BottomNavItem {
  href: string;
  label: string;
  icon: LucideIcon;
  /** Mọi tiền tố đường dẫn thuộc mục này, cả bản pilot lẫn bản DeepAgent. */
  match: readonly string[];
}

/**
 * Màn hội thoại có ô soạn tin nằm sát đáy; thanh điều hướng ở đó sẽ đè lên ô
 * soạn và chiếm chỗ của câu trả lời. Chỉ ẩn đúng các màn hội thoại, các màn
 * con (lịch sử, chi tiết phiên) vẫn có thanh.
 */
const CHAT_SCREENS = new Set(["/triage-pilot", "/triage", "/triage/guest-session"]);

export function isChatScreen(pathname: string): boolean {
  return CHAT_SCREENS.has(pathname);
}

function isUnder(pathname: string, prefix: string): boolean {
  return pathname === prefix || pathname.startsWith(`${prefix}/`);
}

/**
 * Mục đang chọn: tiền tố khớp dài nhất thắng, để "/triage-pilot/history" sáng
 * "Lịch sử" chứ không sáng cả "Sàng lọc".
 */
export function activeBottomNavHref(
  pathname: string,
  items: ReadonlyArray<Pick<BottomNavItem, "href" | "match">>,
): string | null {
  let best: { href: string; length: number } | null = null;
  for (const item of items) {
    for (const prefix of item.match) {
      if (isUnder(pathname, prefix) && (best === null || prefix.length > best.length)) {
        best = { href: item.href, length: prefix.length };
      }
    }
  }
  return best?.href ?? null;
}

const PILL_TRANSITION = { duration: DURATION.base, ease: EASE_IN_OUT };

/**
 * Thanh điều hướng đáy cho người bệnh trên điện thoại (ẩn từ md trở lên, nơi
 * thanh điều hướng trên cùng đã đủ chỗ). Dấu hiệu mục đang chọn là một viên
 * nền thương hiệu trượt sang mục mới, nên người dùng thấy mình vừa chuyển tới
 * đâu. Đường dẫn "Sàng lọc"/"Lịch sử" theo công tắc của @/lib/agent-mode, giống
 * thanh trên cùng.
 *
 * Đi kèm một khối đệm cùng chiều cao để nội dung cuối trang không bao giờ bị
 * thanh che, kể cả phần vùng an toàn của iOS.
 */
export function PatientBottomNav() {
  const pathname = usePathname() ?? "";
  if (isChatScreen(pathname)) return null;

  const items: BottomNavItem[] = [
    { href: triageStartHref(), label: "Sàng lọc", icon: MessageSquare, match: ["/triage-pilot", "/triage"] },
    {
      href: triageHistoryListHref(),
      label: "Lịch sử",
      icon: History,
      match: ["/triage-pilot/history", "/history"],
    },
    { href: "/profile", label: "Hồ sơ", icon: Users, match: ["/profile"] },
  ];
  const activeHref = activeBottomNavHref(pathname, items);

  return (
    <>
      <div aria-hidden="true" className="h-[calc(4rem_+_1px_+_env(safe-area-inset-bottom))] shrink-0 md:hidden" />
      <nav
        aria-label="Điều hướng chính"
        className="fixed inset-x-0 bottom-0 z-40 border-t border-border bg-card/95 pb-[env(safe-area-inset-bottom)] backdrop-blur-sm md:hidden"
      >
        <ul className="mx-auto flex max-w-md px-2">
          {items.map((item) => {
            const active = item.href === activeHref;
            const Icon = item.icon;
            return (
              <li key={item.label} className="flex-1">
                <Link
                  href={item.href}
                  aria-current={active ? "page" : undefined}
                  className={cn(
                    "group flex h-16 flex-col items-center justify-center rounded-2xl text-sm transition-colors duration-[180ms] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-brand",
                    active ? "font-bold text-brand" : "font-semibold text-muted-foreground hover:text-foreground",
                  )}
                >
                  <span className="relative flex h-8 w-16 items-center justify-center">
                    {active && (
                      <motion.span
                        layoutId="patient-bottom-nav-pill"
                        transition={PILL_TRANSITION}
                        aria-hidden="true"
                        className="absolute inset-0 rounded-full bg-brand-soft"
                      />
                    )}
                    <Icon
                      className="relative size-6 transition-transform duration-[120ms] group-active:scale-[0.97] motion-reduce:transition-none"
                      strokeWidth={active ? 2.25 : 2}
                      aria-hidden="true"
                    />
                  </span>
                  {item.label}
                </Link>
              </li>
            );
          })}
        </ul>
      </nav>
    </>
  );
}
