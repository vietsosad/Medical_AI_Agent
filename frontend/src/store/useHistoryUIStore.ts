import { create } from "zustand";
import type { EsiLevel, HitlReviewStatus } from "@/types/clinical-history";

// ============================================================================
// 1. ĐỊNH NGHĨA CONTRACT TRANG THÁI UI TRA CỨU LÂM SÀNG (ZUSTAND CLIENT STORE)
// ============================================================================
export type HistoryStatusFilter = "ALL" | HitlReviewStatus;
export type HistoryViewingMode = "SPLIT_TERMINAL" | "FEED_ONLY";

/**
 * Interface Quản lý Trạng Thái Giao Diện & Bộ Lọc cho Mô-đun Tra Khảo Lịch Sử Lâm Sàng
 * Cam kết tuân thủ Điều 3.2 (frontend-rules.md) & AGENTS.md:
 * TUYỆT ĐỐI KHÔNG LƯU danh sách ca bệnh từ API tại đây (thuộc đặc quyền quản trị của TanStack Query).
 */
export interface HistoryUIState {
  /**
   * Từ khóa tìm kiếm tự do theo triệu chứng, mã bệnh án hoặc ID ca khám
   */
  searchQuery: string;
  
  /**
   * Mảng các mức độ phân cấp ESI đang chọn lọc (Rỗng = hiển thị tất cả các cấp ESI)
   */
  selectedEsiFilters: EsiLevel[];
  
  /**
   * Bộ lọc trạng thái thẩm định từ bác sĩ / chuyên gia trực chiến HITL
   */
  statusFilter: HistoryStatusFilter;
  
  /**
   * Trạng thái thu hồi / mở rộng thanh trình đơn bên trái (Sidebar list vs Replay focus)
   */
  isSidebarExpanded: boolean;

  /**
   * Chế độ quan sát giao diện: Bố trí chia màn hình trạm lâm sàng (SPLIT) hoặc xem cuộn tin (FEED)
   */
  viewingMode: HistoryViewingMode;
}

export interface HistoryUIActions {
  setSearchQuery: (text: string) => void;
  toggleEsiFilter: (level: EsiLevel) => void;
  setStatusFilter: (status: HistoryStatusFilter) => void;
  toggleSidebar: () => void;
  setViewingMode: (mode: HistoryViewingMode) => void;
  resetFilters: () => void;
}

export type HistoryUIStore = HistoryUIState & HistoryUIActions;

// ============================================================================
// 2. KHỞI TẠO ZUSTAND STORE VỚI INITIAL STATE
// ============================================================================
const INITIAL_STATE: HistoryUIState = {
  searchQuery: "",
  selectedEsiFilters: [], // Mặc định rỗng nhằm hiển thị toàn bộ các ca bệnh
  statusFilter: "ALL",
  isSidebarExpanded: true,
  viewingMode: "SPLIT_TERMINAL",
};

export const useHistoryUIStore = create<HistoryUIStore>((set, get) => ({
  // --- TRẠNG THÁI KHỞI TẠO ---
  ...INITIAL_STATE,

  // --- HỆ THỐNG ACTIONS IMPLEMENTATION ---
  setSearchQuery: (text: string) => {
    set({ searchQuery: text });
  },

  toggleEsiFilter: (level: EsiLevel) => {
    const current = get().selectedEsiFilters;
    const exists = current.includes(level);
    const updated = exists
      ? current.filter((item) => item !== level)
      : [...current, level];
      
    set({ selectedEsiFilters: updated });
  },

  setStatusFilter: (status: HistoryStatusFilter) => {
    set({ statusFilter: status });
  },

  toggleSidebar: () => {
    const nextState = !get().isSidebarExpanded;
    set({ isSidebarExpanded: nextState });
  },

  setViewingMode: (mode: HistoryViewingMode) => {
    set({ viewingMode: mode });
  },

  resetFilters: () => {
    set({
      searchQuery: INITIAL_STATE.searchQuery,
      selectedEsiFilters: INITIAL_STATE.selectedEsiFilters,
      statusFilter: INITIAL_STATE.statusFilter,
    });
  },
}));
