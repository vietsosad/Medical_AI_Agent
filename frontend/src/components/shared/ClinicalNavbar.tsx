"use client";

import React, { useState, useRef, useEffect } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  Activity,
  FileText,
  History,
  MessageSquare,
  LayoutGrid,
  Menu,
  X,
  ChevronDown,
  LogOut,
  KeyRound,
  UserPlus,
  User,
  Home,
  Building2,
  ShieldCheck,
  Layers,
  BookOpen
} from "lucide-react";
import { nurseQueueHref, triageHistoryListHref, triageStartHref } from "@/lib/agent-mode";
import { cn } from "@/lib/utils";
import { useAuthStore } from "@/store/useAuthStore";
import { toast } from "sonner";
import { PatientNotificationBell } from "./PatientNotificationBell";
import { ThemeToggle } from "./ThemeToggle";

/**
 * ============================================================================
 * [CLINICAL NAVBAR] THANH ĐIỀU HƯỚNG HIỆN ĐẠI TỔNG BỘ (ROLE-ADAPTIVE & RBAC)
 * ============================================================================
 * Chuẩn kiến trúc UI_REDESIGN_SYSTEM:
 * - Touch Targets >= 44px (min-h-[44px]).
 * - Typography mượt mà rành mạch, không dùng chữ quá nhỏ dưới 12px.
 * - Loại bỏ hoàn toàn emoji trong giao diện và thông báo toast.
 */
export const ClinicalNavbar: React.FC = () => {
  const pathname = usePathname() || "/";
  const { user, isAuthenticated, isLoading: isAuthLoading, logout } = useAuthStore();

  // Ẩn ClinicalNavbar chung khi truy cập các phân khu đã có Bố cục định chuẩn theo Role (Staff/Admin)
  const isDedicatedRoleRoute = 
    pathname.startsWith("/clinical") || 
    pathname.startsWith("/admin");
  
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const [userDropdownOpen, setUserDropdownOpen] = useState(false);
  const [activeSection, setActiveSection] = useState<string | null>(null);

  const dropdownRef = useRef<HTMLDivElement>(null);

  // Đóng dropdown khi click ra ngoài
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
        setUserDropdownOpen(false);
      }
    };
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  // Đảm bảo mỗi khi chuyển đổi màn hình hoặc điều hướng tuyến, cửa sổ hiển thị chính xác từ vùng đỉnh top = 0.
  // Ngoại lệ: khi đường dẫn kèm mỏ neo (#) thì trình duyệt đang cuộn tới đúng khối nội dung,
  // kéo về đỉnh trang lúc này sẽ phá luôn thao tác điều hướng của người dùng.
  useEffect(() => {
    if (typeof window !== "undefined" && window.location.hash) return;
    window.scrollTo({ top: 0, left: 0, behavior: "instant" as ScrollBehavior });
  }, [pathname]);

  // Xác định người dùng có thuộc đội ngũ lâm sàng hợp nhất hoặc Admin hay không
  const isClinicalStaff = Boolean(
    isAuthenticated && user && [
      "CLINICAL_NURSE",
      "SYSTEM_ADMIN",
      "AI_OPS"
    ].includes(user.role)
  );

  // Xử lý đăng xuất tài khoản
  const handleLogout = async () => {
    setUserDropdownOpen(false);
    setMobileMenuOpen(false);
    await logout(true);
    toast.success("Đã kết thúc phiên và đăng xuất tài khoản lâm sàng an toàn.");
  };

  interface NavItem {
    name: string;
    href: string;
    icon: React.ComponentType<{ className?: string }>;
    highlight?: boolean;
    /** Mục trỏ tới một khối nội dung ngay trên trang chủ, dùng để tô sáng theo vị trí cuộn. */
    sectionId?: string;
    /** Chỉ hiện từ breakpoint xl trở lên để thanh điều hướng không bị chật ở màn hình vừa. */
    wideOnly?: boolean;
  }

  // DANH SÁCH MENU CÔNG KHAI CHO KHÁCH CHƯA ĐĂNG NHẬP.
  // Các chức năng cần hồ sơ bệnh nhân (khám, lịch sử, hồ sơ y khoa) không xuất hiện ở đây
  // vì chúng đều yêu cầu phiên đăng nhập hợp lệ tại PatientRoleGuard.
  // Thay vào đó là các mỏ neo tới những khối nội dung công khai đã có sẵn trên trang chủ,
  // nên khách vẫn có đường dẫn rõ ràng mà không lộ bất kỳ chức năng cần đăng nhập nào.
  const publicNavigation: NavItem[] = [
    { name: "Trang Chủ", href: "/", icon: Home },
    { name: "An Toàn Y Khoa", href: "/#an-toan-lam-sang", icon: ShieldCheck, sectionId: "an-toan-lam-sang" },
    { name: "Trải Nghiệm", href: "/#trai-nghiem-triage", icon: Layers, sectionId: "trai-nghiem-triage", wideOnly: true },
    { name: "Kiến Thức Sức Khỏe", href: "/#thong-tin-suc-khoe", icon: BookOpen, sectionId: "thong-tin-suc-khoe" },
  ];

  // DANH SÁCH MENU DÀNH CHO BỆNH NHÂN ĐÃ ĐĂNG NHẬP
  // Khám Triage AI / Lịch Sử Khám trỏ sang simple_agent pilot khi
  // NEXT_PUBLIC_TRIAGE_PILOT_ACTIVE="YES" -- xem @/lib/agent-mode.
  const patientNavigation: NavItem[] = [
    { name: "Trang Chủ", href: "/", icon: Home },
    { name: "Khám Triage AI", href: triageStartHref(), icon: MessageSquare },
    { name: "Lịch Sử Khám", href: triageHistoryListHref(), icon: History },
    { name: "Hồ Sơ Y Khoa", href: "/profile", icon: FileText },
  ];

  // DANH SÁCH MENU DÀNH CHO NHÂN VIÊN LÂM SÀNG HỢP NHẤT
  const clinicalNavigation: NavItem[] = [
    { name: "Hàng đợi", href: nurseQueueHref(), icon: LayoutGrid, highlight: true },
    { name: "Hỗ Trợ Triage", href: triageStartHref(), icon: MessageSquare },
    { name: "Kho Bệnh Án", href: triageHistoryListHref(), icon: History },
  ];

  // Quyết định menu hiển thị theo trạng thái phiên và Role hiện tại
  const hasActiveSession = Boolean(isAuthenticated && user);
  const activeNavigation: NavItem[] = isClinicalStaff
    ? clinicalNavigation
    : hasActiveSession
      ? patientNavigation
      : publicNavigation;

  // SCROLL-SPY: tô sáng mục điều hướng ứng với khối nội dung đang đọc.
  // Chỉ hoạt động trên trang chủ, nơi các mỏ neo thực sự tồn tại. Phải chờ phiên
  // hydrate xong vì trang chủ chỉ dựng nội dung sau bước đó (xem RoleHomeRedirect).
  //
  // Bản trước dựng trên IntersectionObserver và bị KẸT SÁNG (lỗi thật,
  // 2026-09-14): callback của observer chỉ chạy khi có khối ĐỔI trạng thái cắt
  // nhau. Người đọc cuộn ngược từ "An Toàn Y Khoa" lên đầu trang thì khối đó
  // rời vùng quan sát lúc scrollY vẫn còn lớn -- nhánh dọn dẹp `scrollY < 240`
  // không chạy -- rồi từ đó tới lúc chạm đỉnh trang không còn sự kiện nào nữa,
  // nên mục cũ nằm sáng trong khi màn hình đang hiển thị Hero.
  //
  // Đọc thẳng hình học theo từng lần cuộn thì không còn trạng thái nào để kẹt:
  // mỗi lần đo đều tự trả lời lại câu hỏi "đang đứng ở khối nào".
  const anchorKey = activeNavigation
    .map((item) => item.sectionId)
    .filter(Boolean)
    .join("|");

  useEffect(() => {
    if (pathname !== "/" || !anchorKey) return;

    const ids = anchorKey.split("|");
    let frame = 0;

    /**
     * Khối đang đọc là khối cuối cùng đã bắt đầu phía trên đường ngắm. Nhờ vậy
     * phần chân trang (không có mỏ neo nào) vẫn giữ mục cuối sáng, còn khi
     * đường ngắm nằm trong Hero -- phía trên mọi mỏ neo -- thì không mục nào
     * sáng và "Trang Chủ" nhận lại đúng vai của nó.
     */
    const sync = () => {
      frame = 0;
      const probe = window.innerHeight * 0.35;
      let current: string | null = null;
      for (const id of ids) {
        const section = document.getElementById(id);
        // Các mỏ neo nằm đúng thứ tự DOM, nên cái khớp cuối cùng là cái đang đọc.
        if (section && section.getBoundingClientRect().top <= probe) current = id;
      }
      setActiveSection((previous) => (previous === current ? previous : current));
    };

    const schedule = () => {
      if (frame) return;
      frame = window.requestAnimationFrame(sync);
    };

    schedule();
    window.addEventListener("scroll", schedule, { passive: true });
    window.addEventListener("resize", schedule);

    // Ảnh trong Hero và các thẻ sức khỏe về muộn làm trang dài ra mà không sinh
    // ra lần cuộn nào; thiếu bước này thì kết quả đo lúc mount sẽ sai mãi.
    const observer = typeof ResizeObserver === "function" ? new ResizeObserver(schedule) : null;
    observer?.observe(document.body);

    return () => {
      if (frame) window.cancelAnimationFrame(frame);
      window.removeEventListener("scroll", schedule);
      window.removeEventListener("resize", schedule);
      observer?.disconnect();
    };
  }, [pathname, anchorKey, isAuthLoading]);

  // Chỉ tô sáng theo mỏ neo khi đang thực sự đứng trên trang chủ; rời trang chủ thì
  // giá trị cũ bị bỏ qua thay vì phải ghi đè state bên trong effect.
  const activeAnchor = pathname === "/" ? activeSection : null;

  // Cuộn tới một khối nội dung trên trang chủ. Các khối này chỉ tồn tại sau khi
  // trang chủ hydrate xong (RoleHomeRedirect dựng nội dung ở phía client), nên
  // phần tử đích có thể chưa có mặt ngay lúc bấm. Thử lại theo khung hình trong
  // một khoảng ngắn thay vì bỏ cuộc ngay ở lần tìm đầu tiên.
  const scrollToSection = React.useCallback((sectionId: string) => {
    const startedAt = performance.now();

    const attempt = () => {
      const target = document.getElementById(sectionId);
      if (target) {
        target.scrollIntoView({ behavior: "smooth", block: "start" });
        // Ghi lại mỏ neo để tải lại trang / chia sẻ đường dẫn vẫn về đúng khối,
        // nhưng không đẩy thêm một mục vào lịch sử duyệt cho mỗi lần bấm.
        window.history.replaceState(null, "", `/#${sectionId}`);
        return;
      }
      if (performance.now() - startedAt < 3000) {
        window.requestAnimationFrame(attempt);
      }
    };

    window.requestAnimationFrame(attempt);
  }, []);

  // Sau khi điều hướng từ trang khác về "/#mo-neo", trình duyệt không tự cuộn
  // được vì khối đích chưa render lúc đó. Tự xử lý một lần khi vào trang chủ.
  useEffect(() => {
    if (pathname !== "/") return;
    const hash = window.location.hash.replace("#", "");
    if (!hash) return;
    scrollToSection(hash);
  }, [pathname, scrollToSection]);

  const handleNavItemNavigate = (item: NavItem) => (event: { preventDefault: () => void }) => {
    // Mỏ neo trên trang chủ: tự cuộn thay vì để router xử lý. <Link> của Next
    // mặc định GIỮ NGUYÊN vị trí cuộn và chỉ can thiệp vào "first Page element"
    // (xem node_modules/next/dist/docs/.../components/link.md, mục `scroll`),
    // nên một liên kết chỉ khác nhau ở phần hash không cuộn đi đâu cả.
    if (item.sectionId && pathname === "/") {
      event.preventDefault();
      scrollToSection(item.sectionId);
      setMobileMenuOpen(false);
      return;
    }

    // "Trang Chủ" khi đã đứng sẵn ở trang chủ: đưa về đầu trang và xoá mỏ neo,
    // nếu không thì bấm vào sẽ không có phản hồi nào.
    if (item.href === "/" && pathname === "/") {
      event.preventDefault();
      window.scrollTo({ top: 0, left: 0, behavior: "smooth" });
      window.history.replaceState(null, "", "/");
      setActiveSection(null);
      setMobileMenuOpen(false);
    }
  };

  // Chọn mục khớp SÂU NHẤT với đường dẫn hiện tại. Nếu chỉ dùng startsWith cho
  // từng mục một cách độc lập thì "/triage-pilot/history" sẽ khớp cả mục
  // "Khám Triage AI" (/triage-pilot) lẫn "Lịch Sử Khám", làm sáng cùng lúc hai
  // mục -- đúng lỗi người dùng báo.
  const deepestMatchedHref = (() => {
    let best: string | null = null;
    for (const item of activeNavigation) {
      if (item.sectionId) continue;
      const base = item.href.split("?")[0].split("#")[0];
      if (base === "/") continue;
      if (pathname === base || pathname.startsWith(`${base}/`)) {
        if (best === null || base.length > best.length) best = base;
      }
    }
    return best;
  })();

  const isNavItemActive = (item: NavItem, path: string) => {
    if (item.sectionId) return activeAnchor === item.sectionId;
    if (item.href === "/") return path === "/" && activeAnchor === null;
    return deepestMatchedHref !== null && item.href.split("?")[0].split("#")[0] === deepestMatchedHref;
  };

  // Thi hành ngắt kết nối ClinicalNavbar sau khi toàn bộ React Hooks đã chạy thành công
  if (isDedicatedRoleRoute) {
    return null;
  }

  return (
    <header className="sticky top-0 z-50 w-full bg-card/95 backdrop-blur-sm border-b border-border shadow-2xs font-sans text-foreground transition-all">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 min-h-[64px] flex items-center justify-between gap-4 py-2">
        
        {/* KHỐI BRAND & LOGOING NHẬN DIỆN VAI TRÒ (MINIMALIST MONOCHROME) */}
        <div className="flex items-center gap-4 shrink-0">
          <Link
            href={isClinicalStaff ? nurseQueueHref() : "/"}
            title="AI Triage Clinical System"
            className="flex items-center gap-3 group transition-transform hover:opacity-95 active:scale-98"
          >
            <div className="w-10 h-10 rounded-xl bg-slate-900 text-white flex items-center justify-center shadow-xs transition-transform group-hover:scale-105 shrink-0">
              <Activity className="w-5 h-5 stroke-[2.5]" />
            </div>
            <div className="flex flex-col">
              <div className="flex items-center gap-2">
                <span className="font-extrabold text-lg sm:text-xl tracking-tight text-slate-950 leading-none dark:text-slate-50">
                  AI <span className="text-slate-700 font-bold dark:text-slate-200">Triage</span>
                </span>
              </div>
              
              <span className="text-xs font-medium mt-1 hidden sm:flex lg:hidden items-center gap-1.5 text-muted-foreground">
                {isClinicalStaff ? (
                  <>
                    <Building2 className="w-3.5 h-3.5 stroke-[2.2]" />
                    <span>Cổng Clinical Triage hợp nhất</span>
                  </>
                ) : (
                  <>
                    <User className="w-3.5 h-3.5 stroke-[2.2]" />
                    <span>Cổng Khám Bệnh Nhân</span>
                  </>
                )}
              </span>
            </div>
          </Link>
        </div>

        {/* THANH ĐIỀU HƯỚNG DẠNG PHÂN ĐOẠN (SEGMENTED PILL)
            Gom các mục thành một khối liền mạch để phần giữa navbar không bị trống trải,
            đồng thời giữ nguyên vùng chạm tối thiểu 44px cho từng mục. */}
        <nav className="hidden lg:flex min-w-0 items-center gap-1 rounded-2xl border border-border bg-muted p-1 text-sm font-semibold shadow-inner">
          {activeNavigation.map((item) => {
            const Icon = item.icon;
            const isActive = isNavItemActive(item, pathname);

            const accentClass = isActive
              ? "bg-card text-slate-950 shadow-sm font-bold ring-1 ring-slate-900/5 dark:text-slate-50"
              : "text-slate-600 hover:text-slate-950 hover:bg-card/70 font-semibold dark:text-slate-300";

            return (
              <Link
                key={item.name}
                href={item.href}
                onNavigate={handleNavItemNavigate(item)}
                aria-current={isActive ? "page" : undefined}
                className={cn(
                  "relative min-h-[44px] px-3 xl:px-3.5 py-2.5 rounded-xl flex items-center gap-2 text-sm whitespace-nowrap transition-all duration-200",
                  item.wideOnly && "hidden xl:flex",
                  accentClass
                )}
              >
                <Icon
                  className={cn(
                    "w-4.5 h-4.5 shrink-0 stroke-[2.2] hidden xl:block transition-colors",
                    isActive ? "text-foreground" : "text-muted-foreground"
                  )}
                />
                <span>{item.name}</span>
                {item.highlight && (
                  <span className="w-2 h-2 rounded-full bg-rose-600 animate-pulse ml-1" title="Có ca ESI 1/2 mới trong hàng đợi" />
                )}
                {/* Gạch chân mảnh chạy ra khi mục đang được chọn */}
                <span
                  aria-hidden="true"
                  className={cn(
                    "pointer-events-none absolute inset-x-3 bottom-1 h-0.5 rounded-full bg-slate-900 transition-transform duration-300 origin-left motion-reduce:transition-none",
                    isActive ? "scale-x-100" : "scale-x-0"
                  )}
                />
              </Link>
            );
          })}
        </nav>

        {/* KHỐI HÀNH ĐỘNG PHẢI: AUTHENTICATION CONTROLS */}
        <div className="flex items-center gap-2.5 shrink-0" ref={dropdownRef}>

          {/* CHUYỂN CHẾ ĐỘ SÁNG / TỐI — đứng ngoài nhánh đăng nhập vì đây là
              lựa chọn hiển thị của thiết bị, không phụ thuộc người dùng là ai. */}
          <ThemeToggle className="hidden md:inline-flex" />

          {/* CHƯA ĐĂNG NHẬP: HIỂN THỊ TRỌN VẸN BUTTON ĐĂNG NHẬP & ĐĂNG KÝ */}
          {!isAuthenticated || !user ? (
            <div className="hidden sm:flex items-center gap-2">
              <Link
                href="/auth/login"
                className="min-h-[44px] px-4 py-2.5 rounded-xl text-sm font-semibold text-slate-700 hover:text-foreground bg-muted hover:bg-slate-200 border border-border/80 transition-all flex items-center gap-2 dark:text-slate-200 dark:hover:bg-slate-700"
              >
                <KeyRound className="w-4 h-4 text-slate-600 stroke-[2.2] dark:text-slate-300" />
                <span>Đăng Nhập</span>
              </Link>

              <Link
                href="/auth/register"
                className="min-h-[44px] px-4 py-2.5 rounded-xl text-sm font-semibold text-white bg-slate-900 hover:bg-slate-800 shadow-xs transition-all flex items-center gap-2"
              >
                <UserPlus className="w-4 h-4 text-slate-300 stroke-[2.2]" />
                <span>Đăng Ký</span>
              </Link>

            </div>
          ) : (
            /* ĐÃ ĐĂNG NHẬP: THẺ HIỂN THỊ TÀI KHOẢN & LOGOUT (MIN TOUCH TARGET >= 44PX) */
            <div className="flex items-center gap-2">
              {!isClinicalStaff && <PatientNotificationBell />}
              <div className="relative">
                <button
                  type="button"
                  onClick={() => setUserDropdownOpen(!userDropdownOpen)}
                  className="min-h-[44px] px-3.5 py-2 rounded-xl flex items-center gap-3 border transition-all cursor-pointer shadow-2xs bg-background hover:bg-muted text-foreground border-border"
                >
                <div className="w-7 h-7 rounded-lg bg-slate-900 flex items-center justify-center font-bold text-xs text-white shrink-0">
                  {user?.name?.charAt(0)?.toUpperCase() || <User className="w-4 h-4 stroke-[2.2]" />}
                </div>
                <div className="hidden lg:flex flex-col text-left">
                  <span className="text-sm font-bold leading-tight max-w-[140px] truncate">
                    {user?.name || "Người Dùng"}
                  </span>
                  <span className="text-xs uppercase text-muted-foreground font-medium">
                    {user?.role === "CLINICAL_NURSE" ? "Clinical Triage" : "Bệnh Nhân"}
                  </span>
                </div>
                <ChevronDown className="w-4 h-4 opacity-70 ml-0.5 stroke-[2.2]" />
              </button>

              {/* DROPDOWN QUẢN TRỊ USER & LOGOUT */}
              {userDropdownOpen && (
                <div className="absolute right-0 mt-2 w-80 rounded-2xl bg-card border border-border shadow-xl p-4 space-y-4 z-50 font-sans animate-in fade-in zoom-in-95 duration-150">
                  <div className="p-4 rounded-xl bg-background border border-border space-y-2">
                    <span className="text-sm font-bold text-foreground block">
                      {user?.name}
                    </span>
                    <span className="text-xs text-muted-foreground block break-all">
                      {user?.email}
                    </span>
                    <div className="pt-2 flex items-center gap-2">
                      <span className="px-2.5 py-1 rounded-md text-xs font-bold font-mono uppercase bg-slate-900 text-white">
                        Role: {user?.role}
                      </span>
                      {user?.department && (
                        <span className="text-xs font-semibold text-slate-700 bg-slate-200/60 px-2.5 py-1 rounded-md truncate max-w-[140px] border border-slate-300/60 dark:text-slate-200 dark:bg-slate-700 dark:border-slate-700">
                          {user.department}
                        </span>
                      )}
                    </div>
                  </div>

                  {/* KHỐI NÚT QUẢN TRỊ TRANG (MIN TOUCH TARGETS >= 44PX) */}
                  <div className="space-y-1.5">
                    {isClinicalStaff ? (
                      <Link
                        href={nurseQueueHref()}
                        onClick={() => setUserDropdownOpen(false)}
                        className="min-h-[44px] w-full text-left py-2.5 px-4 rounded-xl hover:bg-background text-foreground font-semibold text-sm flex items-center gap-3 transition-all border border-transparent hover:border-border"
                      >
                        <LayoutGrid className="w-5 h-5 text-slate-700 stroke-[2.2] dark:text-slate-200" />
                        <span>Mở Hàng Đợi Kanban Lâm Sàng</span>
                      </Link>
                    ) : (
                      <Link
                        href="/profile/ehr"
                        onClick={() => setUserDropdownOpen(false)}
                        className="min-h-[44px] w-full text-left py-2.5 px-4 rounded-xl hover:bg-background text-foreground font-semibold text-sm flex items-center gap-3 transition-all border border-transparent hover:border-border"
                      >
                        <FileText className="w-5 h-5 text-slate-700 stroke-[2.2] dark:text-slate-200" />
                        <span>Hồ Sơ Tiền Sử Y Khoa (EHR Lite)</span>
                      </Link>
                    )}

                  </div>

                  {/* NÚT LOGOUT AN TOÀN */}
                  <div className="pt-3 border-t border-slate-100">
                    <button
                      type="button"
                      onClick={handleLogout}
                      className="min-h-[44px] w-full py-3 px-4 rounded-xl bg-rose-50 hover:bg-rose-100 text-rose-700 font-bold text-sm flex items-center justify-center gap-2 transition-all cursor-pointer border border-rose-200"
                    >
                      <LogOut className="w-4.5 h-4.5 text-rose-600 stroke-[2.2]" />
                      <span>Đăng Xuất Tài Khoản</span>
                    </button>
                  </div>
                </div>
              )}
            </div>
          </div>
        )}

          {/* MOBILE MENU TOGGLE BUTTON (TOUCH TARGET >= 44PX) */}
          <button
            type="button"
            onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
            className="lg:hidden min-h-[44px] p-2.5 rounded-xl bg-muted hover:bg-slate-200 text-slate-800 transition-colors cursor-pointer border border-border dark:text-slate-100 dark:hover:bg-slate-700"
            aria-label="Mở Trình Đơn Lâm Sàng Mobile"
          >
            {mobileMenuOpen ? <X className="w-6 h-6 stroke-[2.2]" /> : <Menu className="w-6 h-6 stroke-[2.2]" />}
          </button>
        </div>
      </div>

      {/* MOBILE COLLAPSIBLE NAVIGATION DRAWER */}
      {mobileMenuOpen && (
        <div className="lg:hidden bg-card border-t border-border shadow-lg px-4 pt-4 pb-6 space-y-4 font-sans animate-in fade-in slide-in-from-top-2 duration-200">
          {/* CHUYỂN CHẾ ĐỘ SÁNG / TỐI — trên màn hình hẹp thì bản đầy đủ có nhãn
              chữ, vì ba biểu tượng trần rất dễ đoán nhầm. */}
          <div>
            <div className="text-xs font-semibold text-slate-400 px-2 mb-2">CHẾ ĐỘ HIỂN THỊ:</div>
            <ThemeToggle variant="full" />
          </div>

          {/* USER PROFILE INFO TRÊN MOBILE */}
          {isAuthenticated && user && (
            <div className="p-4 rounded-2xl bg-background border border-border flex items-center justify-between">
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 rounded-xl bg-slate-900 text-white font-bold flex items-center justify-center text-base shrink-0">
                  {user.name?.charAt(0) || "U"}
                </div>
                <div>
                  <div className="font-bold text-base text-foreground">{user.name}</div>
                  <div className="text-xs text-muted-foreground font-medium mt-0.5">{user.role}</div>
                </div>
              </div>
              <button
                type="button"
                onClick={handleLogout}
                className="min-h-[44px] px-3 py-2 rounded-xl bg-rose-50 text-rose-700 hover:bg-rose-100 border border-rose-200 text-xs font-bold flex items-center gap-1.5"
              >
                <LogOut className="w-4 h-4 stroke-[2.2]" />
                <span>Logout</span>
              </button>
            </div>
          )}

          {/* DANH SÁCH MENU LÂM SÀNG TRÊN MOBILE */}
          <div className="space-y-2 pt-2">
            <div className="text-xs font-semibold text-slate-400 px-2 mb-2 flex items-center gap-2">
              {isClinicalStaff ? (
                <>
                  <Building2 className="w-4 h-4 stroke-[2.2]" />
                  <span>CỔNG CLINICAL TRIAGE HỢP NHẤT:</span>
                </>
              ) : hasActiveSession ? (
                <>
                  <User className="w-4 h-4 stroke-[2.2]" />
                  <span>CỔNG TỰ KHÁM BỆNH NHÂN:</span>
                </>
              ) : (
                <>
                  <Home className="w-4 h-4 stroke-[2.2]" />
                  <span>ĐIỀU HƯỚNG CHUNG:</span>
                </>
              )}
            </div>
            {activeNavigation.map((item) => {
              const Icon = item.icon;
              const isActive = isNavItemActive(item, pathname);
              
              const mobileAccent = isActive ? "bg-slate-900 text-white font-bold" : "text-slate-700 hover:bg-muted font-semibold dark:text-slate-200";

              return (
                <Link
                  key={item.name}
                  href={item.href}
                  onNavigate={handleNavItemNavigate(item)}
                  onClick={() => setMobileMenuOpen(false)}
                  aria-current={isActive ? "page" : undefined}
                  className={cn("min-h-[44px] w-full py-3 px-4 rounded-xl flex items-center gap-3 text-sm transition-all", mobileAccent)}
                >
                  <Icon className="w-5 h-5 opacity-80 shrink-0 stroke-[2.2]" />
                  <span>{item.name}</span>
                </Link>
              );
            })}
          </div>

          {/* HÀNH ĐỘNG ĐĂNG NHẬP/ĐĂNG KÝ CHO KHÁCH TRÊN MOBILE */}
          {(!isAuthenticated || !user) && (
            <div className="grid grid-cols-2 gap-4 pt-4 border-t border-border">
              <Link
                href="/auth/login"
                onClick={() => setMobileMenuOpen(false)}
                className="min-h-[44px] flex items-center justify-center py-3 px-4 rounded-xl text-center font-semibold text-sm text-foreground bg-muted hover:bg-slate-200 border border-border/80 dark:hover:bg-slate-700"
              >
                Đăng Nhập
              </Link>
              <Link
                href="/auth/register"
                onClick={() => setMobileMenuOpen(false)}
                className="min-h-[44px] flex items-center justify-center py-3 px-4 rounded-xl text-center font-semibold text-sm text-white bg-slate-900 hover:bg-slate-800 shadow-xs"
              >
                Đăng Ký
              </Link>
            </div>
          )}
        </div>
      )}
    </header>
  );
};

export default ClinicalNavbar;
