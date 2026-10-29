"use client";

import { useEffect, useState } from "react";
import { Trash2 } from "lucide-react";

import { AddProfileModal } from "@/components/profile/AddProfileModal";
import { ConfirmDeleteProfileDialog } from "@/components/profile/ConfirmDeleteProfileDialog";
import { FamilySwitcher } from "@/components/patient/FamilySwitcher";
import { relationTitle } from "@/components/patient/family-identity";
import { isOwnProfile } from "@/components/patient/history-model";
import { useGetProfiles } from "@/queries/useProfileQueries";
import type { ProfileResponseDTO } from "@/services/profile.service";
import { useActiveProfileStore } from "@/store/useActiveProfileStore";

/** id vùng biểu mẫu EHR mà bộ chọn người này điều khiển (xem ClinicalProfileDashboard). */
export const EHR_SUBJECT_PANEL_ID = "ehr-subject-panel";

/**
 * Bộ chọn người cho trang EHR Lite: cùng hàng vòng tròn chữ cái với trang Hồ
 * sơ, để người dùng nhận ra ngay mình đang khai báo cho ai. Giữ đủ chức năng
 * cũ: thêm người thân, xóa hồ sơ người thân (hồ sơ chính không xóa được), và
 * tự chọn hồ sơ chính khi chưa chọn ai.
 */
export default function FamilyProfilePills() {
  const { data: profiles, isLoading } = useGetProfiles();
  const activeProfileId = useActiveProfileStore((state) => state.activeProfileId);
  const setActiveProfileId = useActiveProfileStore((state) => state.setActiveProfileId);
  const openAddProfileModal = useActiveProfileStore((state) => state.openAddProfileModal);

  const [profileToDelete, setProfileToDelete] = useState<ProfileResponseDTO | null>(null);

  // Tự động chọn hồ sơ chính nếu chưa chọn ai.
  useEffect(() => {
    if (!activeProfileId && profiles && profiles.length > 0) {
      const primary = profiles.find((profile) => isOwnProfile(profile)) ?? profiles[0];
      if (primary) setActiveProfileId(primary.id);
    }
  }, [profiles, activeProfileId, setActiveProfileId]);

  if (isLoading) {
    return (
      <div aria-busy="true" aria-label="Đang tải hồ sơ gia đình" className="flex gap-4 py-2">
        {[0, 1, 2].map((item) => (
          <div key={item} className="flex w-16 flex-col items-center gap-2">
            <div className="skeleton-sweep relative size-14 overflow-hidden rounded-full bg-muted" />
            <div className="h-4 w-12 rounded-lg bg-muted" />
          </div>
        ))}
      </div>
    );
  }

  const selected = profiles?.find((profile) => profile.id === activeProfileId) ?? null;

  return (
    <section aria-label="Chọn người để khai báo hồ sơ sức khỏe" className="space-y-2">
      {profiles && profiles.length > 0 && (
        <FamilySwitcher
          profiles={profiles}
          selectedId={activeProfileId}
          onSelect={setActiveProfileId}
          onAdd={openAddProfileModal}
          panelId={EHR_SUBJECT_PANEL_ID}
          idPrefix="ehr-subject"
          layoutId="ehr-family-switcher-ring"
        />
      )}

      {selected && (
        <div className="flex flex-wrap items-center justify-between gap-2">
          <p className="text-sm leading-6 text-muted-foreground">
            Đang khai báo cho <strong className="font-bold text-foreground">{selected.full_name}</strong> ·{" "}
            {relationTitle(selected).toLocaleLowerCase("vi-VN")}
          </p>
          {!isOwnProfile(selected) && (
            <button
              type="button"
              onClick={() => setProfileToDelete(selected)}
              className="inline-flex min-h-11 items-center gap-2 rounded-xl px-2 text-sm font-semibold text-rose-700 transition-colors hover:bg-rose-50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-rose-600 dark:text-rose-300 dark:hover:bg-rose-950/40"
            >
              <Trash2 className="size-4" aria-hidden="true" />
              Xóa hồ sơ {selected.full_name}
            </button>
          )}
        </div>
      )}

      <AddProfileModal />
      <ConfirmDeleteProfileDialog
        profile={profileToDelete}
        profiles={profiles}
        onClose={() => setProfileToDelete(null)}
      />
    </section>
  );
}
