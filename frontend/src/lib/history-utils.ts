/**
 * CLINICAL FORMATTING UTILS & TIME GROUPING HELPERS FOR CLINICAL ARCHIVES MODULE (NHÓM 4)
 * Đảm bảo màu sắc theo phân kỳ khẩn cấp chuẩn mực y khoa & hiển thị "WOW Factor" High-Contrast Dark Theme.
 */
import type { EsiLevel, TimeGroupKey, TriageHistoryListItemDTO } from "@/types/clinical-history";

// ============================================================================
// 1. CHUẨN THẨM MỸ MÀU PHÂN ĐỘ KHẨN CẤP ESI (ESI BADGE CONFIGURATION)
// ============================================================================
export interface EsiBadgeConfig {
  /**
   * Tên định vị đầy đủ chuẩn lâm sàng (vd: ESI 2 - Emergent)
   */
  label: string;
  
  /**
   * Chuỗi Tailwind CSS classes cho nền, chữ, viền và shadow bồ hóng phản quan
   */
  colorClass: string;
  
  /**
   * Cường độ rọi phát sáng bờ viền (Glowing Border) dành riêng cho khung khẩn cấp
   */
  glowingBorder: string;
  
  /**
   * Chuỗi tóm lược ngắn gọn hiển thị ngay trên các thẻ badge
   */
  badgeText: string;
}

/**
 * Hàm phân định màu khẩn cấp ESI lâm sàng với phong cách thẩm mỹ "WOW Factor" Sleek Dark Mode
 * @param esi Phân độ cấp cứu ESI (1 - 5)
 */
export const getEsiBadgeConfig = (esi: EsiLevel | null): EsiBadgeConfig => {
  switch (esi) {
    case 1:
      return {
        label: "ESI 1 - Resuscitation (Tối Cấp Cứu)",
        colorClass: "bg-red-950/90 text-red-200 border-red-500 shadow-[0_0_18px_rgba(239,68,68,0.5)] font-bold animate-pulse",
        glowingBorder: "border-red-500 shadow-[0_0_15px_rgba(239,68,68,0.7)]",
        badgeText: "ESI 1 • CẤP CỨU LÂM SÀNG",
      };
    case 2:
      return {
        label: "ESI 2 - Emergent (Khẩn Cấp Cực Cao)",
        colorClass: "bg-rose-950/85 text-rose-200 border-rose-500/90 shadow-[0_0_14px_rgba(244,63,94,0.45)] font-semibold",
        glowingBorder: "border-rose-500 shadow-[0_0_12px_rgba(244,63,94,0.6)]",
        badgeText: "ESI 2 • KHẨN CẤP CỰC CAO",
      };
    case 3:
      return {
        label: "ESI 3 - Urgent (Khám Ngoại Trú Ưu Tiên)",
        colorClass: "bg-amber-950/75 text-amber-200 border-amber-500/80 shadow-[0_0_12px_rgba(245,158,11,0.35)] font-medium",
        glowingBorder: "border-amber-500/90 shadow-[0_0_10px_rgba(245,158,11,0.4)]",
        badgeText: "ESI 3 • ƯU TIÊN THĂM KHÁM",
      };
    case 4:
      return {
        label: "ESI 4 - Less Urgent (Bất Thường Nhẹ • Khám Chuẩn)",
        colorClass: "bg-cyan-950/70 text-cyan-200 border-cyan-500/70 shadow-[0_0_10px_rgba(6,182,212,0.25)] font-medium",
        glowingBorder: "border-cyan-500/80 shadow-[0_0_8px_rgba(6,182,212,0.3)]",
        badgeText: "ESI 4 • THĂM KHÁM CHUẨN",
      };
    case 5:
      return {
        label: "ESI 5 - Non-urgent (Chăm Sóc Thường Quy / Tự Theo Dõi)",
        colorClass: "bg-emerald-950/65 text-emerald-300 border-emerald-500/60 shadow-[0_0_8px_rgba(16,185,129,0.2)] font-medium",
        glowingBorder: "border-emerald-500/60 shadow-[0_0_6px_rgba(16,185,129,0.25)]",
        badgeText: "ESI 5 • TỰ THEO DÕI NỘI VÙNG",
      };
    default:
      return {
        label: "Chưa có đề xuất ESI",
        colorClass: "bg-slate-100 text-slate-700 border-slate-300 font-medium",
        glowingBorder: "border-slate-300",
        badgeText: "ĐANG THU THẬP THÔNG TIN",
      };
  }
};

// ============================================================================
// 2. HÀM PHÂN NHÓM CHUỖI DANH SÁCH CA KHÁM THEO TRỤC THỜI GIAN
// ============================================================================
/**
 * Phân nhóm chuỗi danh sách ca khám thành cấu trúc từ điển Record<TimeGroupKey, TriageHistoryListItemDTO[]>
 * được chia thành các múi thời gian lâm sàng: Hôm nay, 7 ngày qua, Trong tháng, và Quá khứ xa hơn.
 * 
 * @param sessions Danh sách các ca khám chưa được nhóm
 * @returns Dictionary các ca khám đã phân cụm theo thời gian (đã sắp xếp mới nhất xếp trước)
 */
export const groupSessionsByTime = (
  sessions: TriageHistoryListItemDTO[]
): Record<TimeGroupKey, TriageHistoryListItemDTO[]> => {
  const groups: Record<TimeGroupKey, TriageHistoryListItemDTO[]> = {
    TODAY: [],
    LAST_7_DAYS: [],
    LAST_MONTH: [],
    OLDER: [],
  };

  if (!sessions || sessions.length === 0) {
    return groups;
  }

  const now = new Date();

  // Mốc thời gian 00:00:00 của ngày hôm nay
  const todayStart = new Date(now.getFullYear(), now.getMonth(), now.getDate()).getTime();
  // 7 ngày trước lúc 00:00:00
  const last7DaysStart = todayStart - 7 * 24 * 60 * 60 * 1000;
  // 30 ngày trước lúc 00:00:00
  const lastMonthStart = todayStart - 30 * 24 * 60 * 60 * 1000;

  sessions.forEach((session) => {
    const sessionTime = new Date(session.created_at).getTime();

    if (isNaN(sessionTime) || sessionTime >= todayStart) {
      groups.TODAY.push(session);
    } else if (sessionTime >= last7DaysStart) {
      groups.LAST_7_DAYS.push(session);
    } else if (sessionTime >= lastMonthStart) {
      groups.LAST_MONTH.push(session);
    } else {
      groups.OLDER.push(session);
    }
  });

  // Sắp xếp chronologically (mới nhất dời lên hàng đầu) cho mỗi nhóm
  const keys: TimeGroupKey[] = ["TODAY", "LAST_7_DAYS", "LAST_MONTH", "OLDER"];
  keys.forEach((key) => {
    groups[key].sort((a, b) => {
      const timeB = new Date(b.created_at).getTime();
      const timeA = new Date(a.created_at).getTime();
      return (isNaN(timeB) ? 0 : timeB) - (isNaN(timeA) ? 0 : timeA);
    });
  });

  return groups;
};
