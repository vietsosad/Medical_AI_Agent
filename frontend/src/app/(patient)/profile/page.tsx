"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { AnimatePresence, motion, type Variants } from "framer-motion";
import { ChevronRight, MessageSquare, Plus, Users } from "lucide-react";

import { AccountContactCard } from "@/components/profile/AccountContactCard";
import { AddProfileModal } from "@/components/profile/AddProfileModal";
import { ConfirmDeleteProfileDialog } from "@/components/profile/ConfirmDeleteProfileDialog";
import { EditProfileModal } from "@/components/profile/EditProfileModal";
import { EmergencySosManager } from "@/components/profile/EmergencySosManager";
import { FamilyMemberCard } from "@/components/profile/FamilyMemberCard";
import { FamilySwitcher, familyTabId } from "@/components/patient/FamilySwitcher";
import { isOwnProfile } from "@/components/patient/history-model";
import { triageStartHref } from "@/lib/agent-mode";
import { enterTransition, exitTransition } from "@/lib/motion";
import { useGetProfiles } from "@/queries/useProfileQueries";
import type { ProfileResponseDTO } from "@/services/profile.service";
import { useActiveProfileStore } from "@/store/useActiveProfileStore";

const PANEL_ID = "family-member-panel";
const TAB_ID_PREFIX = "family-member";

/** Đổi người: hồ sơ cũ mờ đi rồi hồ sơ mới hiện lên, không chồng lên nhau. */
const memberPanelVariants: Variants = {
  hidden: { opacity: 0, y: 8 },
  visible: { opacity: 1, y: 0, transition: enterTransition },
  exit: { opacity: 0, transition: exitTransition },
};

function ProfileSkeleton() {
  return (
    <div aria-busy="true" aria-label="Đang tải hồ sơ gia đình" className="space-y-6">
      <div className="flex gap-4 py-2">
        {[0, 1, 2].map((item) => (
          <div key={item} className="flex w-16 flex-col items-center gap-2">
            <div className="skeleton-sweep relative size-14 overflow-hidden rounded-full bg-muted" />
            <div className="h-4 w-12 rounded-lg bg-muted" />
          </div>
        ))}
      </div>
      <div className="skeleton-sweep relative h-72 overflow-hidden rounded-3xl border border-border bg-card" />
    </div>
  );
}

/**
 * ============================================================================
 * [FAMILY HEALTH PROFILE] HỒ SƠ SỨC KHỎE GIA ĐÌNH
 * ============================================================================
 * Chọn một người ở hàng vòng tròn, xem đúng những gì điều dưỡng sẽ thấy khi
 * nhận ca sàng lọc của người đó, sửa ngay tại chỗ, quản lý người liên hệ khẩn
 * cấp của người đó, rồi bắt đầu sàng lọc. Người đang chọn là `activeProfileId`
 * của store chung, nên trang EHR Lite và người liên hệ khẩn cấp luôn khớp người.
 */
export default function PatientProfileRootPage() {
  const { data: profiles, isLoading, isError, refetch } = useGetProfiles();
  const activeProfileId = useActiveProfileStore((state) => state.activeProfileId);
  const setActiveProfileId = useActiveProfileStore((state) => state.setActiveProfileId);
  const openAddProfileModal = useActiveProfileStore((state) => state.openAddProfileModal);
  const openEditProfileModal = useActiveProfileStore((state) => state.openEditProfileModal);

  const [profileToDelete, setProfileToDelete] = useState<ProfileResponseDTO | null>(null);

  // Chưa chọn ai (hoặc người đang chọn vừa bị xóa) thì về hồ sơ chính.
  const selectedProfile =
    profiles?.find((profile) => profile.id === activeProfileId) ??
    profiles?.find((profile) => isOwnProfile(profile)) ??
    profiles?.[0] ??
    null;

  useEffect(() => {
    if (selectedProfile && selectedProfile.id !== activeProfileId) {
      setActiveProfileId(selectedProfile.id);
    }
  }, [selectedProfile, activeProfileId, setActiveProfileId]);

  const memberCount = profiles?.length ?? 0;
  const headingId = selectedProfile ? `family-member-name-${selectedProfile.id}` : undefined;

  return (
    <div className="mx-auto w-full max-w-5xl space-y-6 pb-8 font-sans">
      <header className="page-enter max-w-2xl">
        <h1 className="text-2xl font-extrabold tracking-tight text-foreground sm:text-3xl">Hồ sơ sức khỏe</h1>
        <p className="mt-2 text-sm leading-6 text-muted-foreground">
          Khi bạn sàng lọc cho một người trong gia đình, điều dưỡng xem hồ sơ của người đó lúc nhận ca để không phải hỏi
          lại từ đầu.
        </p>
      </header>

      {isLoading ? (
        <ProfileSkeleton />
      ) : isError ? (
        <div
          role="alert"
          className="space-y-4 rounded-2xl border border-rose-200 bg-rose-50 p-6 text-rose-900 dark:border-rose-900 dark:bg-rose-950/40 dark:text-rose-100"
        >
          <p className="text-base font-bold">Không tải được hồ sơ gia đình.</p>
          <p className="text-sm leading-6">Vui lòng kiểm tra kết nối mạng rồi thử lại.</p>
          <button
            type="button"
            onClick={() => void refetch()}
            className="flex min-h-11 items-center gap-2 rounded-xl border border-rose-300 bg-card px-4 text-sm font-semibold text-rose-800 transition-colors hover:bg-rose-100 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-rose-600 dark:border-rose-800 dark:text-rose-200 dark:hover:bg-rose-950"
          >
            Thử lại
          </button>
        </div>
      ) : memberCount === 0 || !selectedProfile ? (
        <div className="flex flex-col items-center gap-4 rounded-3xl border border-dashed border-border bg-card px-6 py-12 text-center">
          <span className="flex size-14 items-center justify-center rounded-2xl bg-brand-soft text-brand">
            <Users className="size-7" aria-hidden="true" />
          </span>
          <div className="max-w-md space-y-2">
            <p className="text-base font-bold text-foreground">Chưa có hồ sơ thành viên nào</p>
            <p className="text-sm leading-6 text-muted-foreground">
              Thêm hồ sơ cho bản thân và người thân để lưu lại thông tin sức khỏe cần thiết.
            </p>
          </div>
          <button
            type="button"
            onClick={openAddProfileModal}
            className="flex min-h-11 items-center gap-2 rounded-xl bg-brand px-4 text-sm font-bold text-brand-foreground transition-colors hover:bg-brand-strong focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand focus-visible:ring-offset-2"
          >
            <Plus className="size-4" aria-hidden="true" />
            Thêm thành viên đầu tiên
          </button>
        </div>
      ) : (
        <>
          <FamilySwitcher
            profiles={profiles ?? []}
            selectedId={selectedProfile.id}
            onSelect={setActiveProfileId}
            onAdd={openAddProfileModal}
            panelId={PANEL_ID}
            idPrefix={TAB_ID_PREFIX}
            layoutId="family-switcher-ring"
          />

          <div id={PANEL_ID} role="tabpanel" aria-labelledby={familyTabId(TAB_ID_PREFIX, selectedProfile.id)}>
            <AnimatePresence mode="wait">
              <motion.div
                key={selectedProfile.id}
                variants={memberPanelVariants}
                initial="hidden"
                animate="visible"
                exit="exit"
                className="grid grid-cols-1 gap-4 md:grid-cols-2 md:items-start md:gap-6"
              >
                <div className="space-y-4">
                  <FamilyMemberCard
                    member={selectedProfile}
                    headingId={headingId ?? "family-member-name"}
                    onEdit={() => openEditProfileModal(selectedProfile.id)}
                    onDelete={isOwnProfile(selectedProfile) ? null : () => setProfileToDelete(selectedProfile)}
                  />
                  {/* Lối tắt chính của khối này: bắt đầu sàng lọc cho đúng người đang xem. */}
                  <Link
                    href={`${triageStartHref()}?for=${encodeURIComponent(selectedProfile.id)}`}
                    className="group flex min-h-14 items-center gap-4 rounded-2xl border border-brand-edge bg-brand-soft px-4 text-base font-bold text-brand-ink transition duration-[180ms] hover:-translate-y-0.5 hover:shadow-md focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand focus-visible:ring-offset-2 focus-visible:ring-offset-background active:scale-[0.97] motion-reduce:transition-none motion-reduce:hover:translate-y-0 motion-reduce:active:scale-100"
                  >
                    <MessageSquare className="size-5 shrink-0 text-brand" aria-hidden="true" />
                    <span className="min-w-0 flex-1 truncate">Sàng lọc cho {selectedProfile.full_name}</span>
                    <ChevronRight
                      className="size-5 shrink-0 transition-transform duration-[180ms] group-hover:translate-x-0.5 motion-reduce:transition-none"
                      aria-hidden="true"
                    />
                  </Link>
                </div>

                <EmergencySosManager subjectName={selectedProfile.full_name} />
              </motion.div>
            </AnimatePresence>
          </div>
        </>
      )}

      {/* Số của chính chủ tài khoản: khác số trên từng hồ sơ thành viên. */}
      <AccountContactCard />

      <AddProfileModal />
      <EditProfileModal />
      <ConfirmDeleteProfileDialog
        profile={profileToDelete}
        profiles={profiles}
        onClose={() => setProfileToDelete(null)}
      />
    </div>
  );
}
