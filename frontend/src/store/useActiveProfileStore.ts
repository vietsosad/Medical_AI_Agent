import { create } from "zustand";

// ============================================================================
// 1. ĐỊNH NGHĨA CONTRACT TRẠNG THÁI PHIÊN HỒ SƠ LÂM SÀNG GIA ĐÌNH (ZUSTAND STORE)
// ============================================================================

/**
 * Interface Quản lý Trạng Thái Chọn Hồ Sơ Thân Nhân Khám Bệnh & Modal Phụ Trợ.
 * Cam kết tuân thủ Điều 5 (AGENTS.md) & frontend-rules.md:
 * TUYỆT ĐỐI KHÔNG LƯU trữ hay cache mảng danh sách hồ sơ (ProfileResponseDTO[]) từ API tại đây.
 * Mọi remote data thuộc quyền cai trị tuyệt đối và đồng bộ hóa của TanStack Query v5!
 * Zustand Store này chỉ điều phối phiên làm việc phía client (Active Selection & Modal togggles).
 */
export interface ActiveProfileState {
  /**
   * UUID Hồ sơ đang được chọn để tiến hành tư vấn AI Triage hoặc tra cứu EHR.
   * Nếu null, hệ thống tự động fallback chọn hồ sơ chính (is_primary=True / SELF) từ cache TanStack Query.
   */
  activeProfileId: string | null;

  /**
   * Cờ bật/tắt Modal tạo nhanh hồ sơ người thân gia đình (< 15s Agile Onboarding)
   */
  isAddProfileModalOpen: boolean;

  /**
   * Cờ bật/tắt Modal chỉnh sửa hồ sơ
   */
  isEditProfileModalOpen: boolean;

  /**
   * UUID Hồ sơ đang được chọn để chỉnh sửa.
   */
  editProfileId: string | null;

  /**
   * Cờ bật/tắt ngăn xả / dropdown chuyên sâu khi gạt chuyển hồ sơ trong lúc khám khẩn cấp
   */
  isProfileSwitcherOpen: boolean;
}

export interface ActiveProfileActions {
  /**
   * Gán ID hồ sơ gia đình đang thao tác
   */
  setActiveProfileId: (profileId: string | null) => void;

  /**
   * Mở modal chép nhanh thông tin thân nhân mới
   */
  openAddProfileModal: () => void;

  /**
   * Đóng modal
   */
  closeAddProfileModal: () => void;

  /**
   * Mở modal chỉnh sửa hồ sơ (Edit)
   */
  openEditProfileModal: (profileId: string) => void;

  /**
   * Đóng modal chỉnh sửa hồ sơ
   */
  closeEditProfileModal: () => void;

  /**
   * Đảo trạng thái hiển thị trình gạt chọn hồ sơ
   */
  toggleProfileSwitcher: () => void;

  /**
   * Khôi phục toàn bộ cờ trạng thái về mặc định
   */
  resetActiveProfileStore: () => void;
}

export type ActiveProfileStore = ActiveProfileState & ActiveProfileActions;

// ============================================================================
// 2. TRIỂN KHAI STORE VỚI ZUSTAND (CLIENT-ONLY TRANSIENT STATE)
// ============================================================================
export const useActiveProfileStore = create<ActiveProfileStore>((set) => ({
  activeProfileId: null,
  isAddProfileModalOpen: false,
  isEditProfileModalOpen: false,
  editProfileId: null,
  isProfileSwitcherOpen: false,

  setActiveProfileId: (profileId: string | null) => {
    set({ activeProfileId: profileId });
  },

  openAddProfileModal: () => set({ isAddProfileModalOpen: true }),
  closeAddProfileModal: () => set({ isAddProfileModalOpen: false }),

  openEditProfileModal: (profileId: string) => set({ isEditProfileModalOpen: true, editProfileId: profileId }),
  closeEditProfileModal: () => set({ isEditProfileModalOpen: false, editProfileId: null }),

  toggleProfileSwitcher: () => set((state) => ({ isProfileSwitcherOpen: !state.isProfileSwitcherOpen })),

  resetActiveProfileStore: () =>
    set({
      activeProfileId: null,
      isAddProfileModalOpen: false,
      isEditProfileModalOpen: false,
      editProfileId: null,
      isProfileSwitcherOpen: false,
    }),
}));
