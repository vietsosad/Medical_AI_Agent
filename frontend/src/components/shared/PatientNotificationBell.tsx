"use client";

import React, { useState, useRef, useEffect } from "react";
import { Bell, MessageCircle, X } from "lucide-react";
import Link from "next/link";
import { useTriageHistory } from "@/hooks/queries/use-triage-history";
import { useSimplePatientRealtime, useSimpleTriageSessions } from "@/queries/useSimpleTriageQueries";
import { cn } from "@/lib/utils";

// Một mục thông báo chuông, dù nguồn là production `/triage` hay pilot
// `/triage-pilot` -- gộp cả 2 nguồn vào chung 1 danh sách hiển thị thay vì 2
// chuông riêng, chỉ khác nhau ở `href` (2026-08-29, xem ghi chú bên dưới).
interface UnreadNotificationItem {
  sessionId: string;
  title: string;
  subtitle: string;
  unread: number;
  href: string;
}

export function PatientNotificationBell() {
  const [isOpen, setIsOpen] = useState(false);
  const containerRef = useRef<HTMLDivElement>(null);

  // Lấy lịch sử ca khám. Vì trong PatientRealtimeNotification đã gọi invalidate
  // mỗi khi có tin mới, hook này sẽ tự động chạy lại và lấy data mới nhất.
  const { data: historyItems = [] } = useTriageHistory();

  // Nguồn thứ 2: các phiên pilot simple_agent (`/triage-pilot`), hoàn toàn
  // song song với production ở trên -- trước đây chuông này chỉ đọc
  // `useTriageHistory()` (production), nên tin nhắn mới từ điều dưỡng trên
  // 1 ca pilot không bao giờ hiện ở đây dù trang pilot đã tính đúng
  // `unread_from_staff`. `useSimplePatientRealtime()` mở kênh
  // `/ws/simple-patient` ngay tại đây (không phải chỉ khi đang ở trang pilot)
  // để chuông này luôn realtime dù đang ở trang nào trong app.
  const { data: pilotSessions = [] } = useSimpleTriageSessions();
  useSimplePatientRealtime();

  const productionUnread: UnreadNotificationItem[] = historyItems
    .filter((item) => (item.unread_from_staff ?? 0) > 0)
    .map((item) => ({
      sessionId: item.session_id,
      title: item.profile_name || "Khám Nhanh",
      subtitle: item.chief_complaint,
      unread: item.unread_from_staff ?? 0,
      href: `/triage?session_id=${item.session_id}`,
    }));
  const pilotUnread: UnreadNotificationItem[] = pilotSessions
    .filter((session) => session.unread_from_staff > 0)
    .map((session) => ({
      sessionId: session.session_id,
      title: "Ca sàng lọc Triage Agent",
      subtitle: session.initial_message,
      unread: session.unread_from_staff,
      // Mở thẳng khung trao đổi với nhân viên y tế, không chỉ tới trang ca --
      // xem SimpleCareTeamDock.tsx's initialOpen prop.
      href: `/triage-pilot?session_id=${session.session_id}&openChat=1`,
    }));

  const unreadCases = [...productionUnread, ...pilotUnread];
  const totalUnread = unreadCases.reduce((sum, item) => sum + item.unread, 0);

  // Xử lý click ra ngoài để đóng dropdown
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (containerRef.current && !containerRef.current.contains(event.target as Node)) {
        setIsOpen(false);
      }
    };
    if (isOpen) {
      document.addEventListener("mousedown", handleClickOutside);
    }
    return () => {
      document.removeEventListener("mousedown", handleClickOutside);
    };
  }, [isOpen]);

  if (historyItems.length === 0 && pilotSessions.length === 0) return null;

  return (
    <div className="relative" ref={containerRef}>
      <button
        onClick={() => setIsOpen(!isOpen)}
        className={cn(
          "relative p-2 rounded-xl transition-all flex items-center justify-center",
          isOpen ? "bg-muted text-foreground" : "text-slate-600 hover:bg-muted hover:text-foreground dark:text-slate-300",
          totalUnread > 0 && !isOpen && "text-sky-700"
        )}
        aria-label="Thông báo tin nhắn"
      >
        <Bell className="w-5 h-5 stroke-[2.2]" />
        {totalUnread > 0 && (
          <span className="absolute top-1.5 right-1.5 w-2.5 h-2.5 bg-rose-500 border-2 border-white rounded-full" />
        )}
      </button>

      {isOpen && (
        <div className="absolute right-0 mt-2 w-80 bg-card rounded-2xl shadow-xl border border-border overflow-hidden z-50 animate-in fade-in slide-in-from-top-2 origin-top-right">
          <div className="px-4 py-3 border-b border-slate-100 flex items-center justify-between bg-background/50">
            <h3 className="font-semibold text-foreground flex items-center gap-2">
              <span>Tin nhắn chưa đọc</span>
              {totalUnread > 0 && (
                <span className="bg-rose-100 text-rose-700 text-xs font-bold px-2 py-0.5 rounded-full">
                  {totalUnread}
                </span>
              )}
            </h3>
            <button 
              onClick={() => setIsOpen(false)}
              className="p-1 rounded-md text-slate-400 hover:text-slate-600 hover:bg-slate-200/50 dark:hover:text-slate-300 dark:hover:bg-slate-700"
            >
              <X className="w-4 h-4" />
            </button>
          </div>

          <div className="max-h-[360px] overflow-y-auto overscroll-contain">
            {unreadCases.length === 0 ? (
              <div className="px-4 py-8 text-center flex flex-col items-center">
                <MessageCircle className="w-10 h-10 text-slate-200 mb-3 stroke-[1.5]" />
                <p className="text-sm font-medium text-slate-600 dark:text-slate-300">Bạn không có tin nhắn nào chưa đọc</p>
              </div>
            ) : (
              <div className="flex flex-col">
                {unreadCases.map((c) => (
                  <Link
                    key={c.sessionId}
                    href={c.href}
                    onClick={() => setIsOpen(false)}
                    className="flex flex-col p-4 hover:bg-background transition-colors border-b border-slate-100 last:border-0 group"
                  >
                    <div className="flex justify-between items-start mb-1">
                      <span className="font-semibold text-sm text-foreground line-clamp-1 pr-4">{c.title}</span>
                      <span className="shrink-0 text-xs font-bold text-rose-600 bg-rose-50 px-2 py-0.5 rounded-md">
                        {c.unread} mới
                      </span>
                    </div>
                    <span className="text-xs text-muted-foreground line-clamp-1 group-hover:text-slate-700 transition-colors dark:group-hover:text-slate-200">
                      {c.subtitle}
                    </span>
                  </Link>
                ))}
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
