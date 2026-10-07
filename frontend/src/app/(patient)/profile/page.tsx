"use client";

import React, { useEffect, useState } from "react";
import Link from "next/link";
import {
  AlertTriangle,
  ArrowRight,
  FileText,
  Loader2,
  Plus,
  ShieldCheck,
  Trash2,
  Users,
} from "lucide-react";

import { AccountContactCard } from "@/components/profile/AccountContactCard";
import { AddProfileModal } from "@/components/profile/AddProfileModal";
import { EditProfileModal } from "@/components/profile/EditProfileModal";
import { FamilyMemberCard } from "@/components/profile/FamilyMemberCard";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { useDeleteProfile, useGetProfiles } from "@/queries/useProfileQueries";
import type { ProfileResponseDTO } from "@/services/profile.service";
import { useActiveProfileStore } from "@/store/useActiveProfileStore";
import { useAuthStore } from "@/store/useAuthStore";
import { toast } from "sonner";

// ============================================================================
// CONFIRM DELETE DIALOG
// ============================================================================
interface ConfirmDeleteDialogProps {
  profile: ProfileResponseDTO | null;
  isOpen: boolean;
  isPending: boolean;
  onConfirm: () => void;
  onCancel: () => void;
}

function ConfirmDeleteDialog({
  profile,
  isOpen,
  isPending,
  onConfirm,
  onCancel,
}: ConfirmDeleteDialogProps) {
  return (
    <Dialog open={isOpen} onOpenChange={(open) => { if (!open) onCancel(); }}>
      <DialogContent className="max-w-md rounded-2xl border-rose-100 bg-card p-0 shadow-xl">
        <DialogHeader className="space-y-3 border-b border-rose-100 bg-rose-50/60 p-6 text-left">
          <div className="flex items-center gap-3">
            <div className="flex size-10 shrink-0 items-center justify-center rounded-xl bg-rose-100 text-rose-700">
              <AlertTriangle className="size-5 stroke-[2.25]" />
            </div>
            <DialogTitle className="text-lg font-bold text-foreground">Xóa hồ sơ thành viên</DialogTitle>
          </div>
          <DialogDescription className="text-sm leading-relaxed text-slate-600 dark:text-slate-300">
            Bạn có chắc muốn xóa hồ sơ y khoa của{" "}
            <strong className="text-foreground">{profile?.full_name}</strong> không? Toàn bộ dữ liệu
            tiền sử bệnh, dị ứng và người liên hệ SOS sẽ bị{" "}
            <strong className="text-rose-700">xóa vĩnh viễn</strong> và không thể khôi phục.
          </DialogDescription>
        </DialogHeader>
        <div className="flex flex-row justify-end gap-2 p-4">
          <Button
            type="button"
            variant="secondary"
            onClick={onCancel}
            disabled={isPending}
            className="min-h-11 px-5 text-sm font-semibold"
          >
            Hủy bỏ
          </Button>
          <Button
            type="button"
            onClick={onConfirm}
            disabled={isPending}
            className="min-h-11 bg-rose-600 px-5 text-sm font-bold text-white hover:bg-rose-700"
          >
            {isPending ? (
              <Loader2 className="mr-1.5 size-4 animate-spin" />
            ) : (
              <Trash2 className="mr-1.5 size-4" />
            )}
            Xóa vĩnh viễn
          </Button>
        </div>
      </DialogContent>
    </Dialog>
  );
}

function MemberCardSkeleton() {
  return (
    <div className="flex h-64 animate-pulse flex-col justify-between rounded-2xl border border-border bg-card p-5">
      <div className="flex items-center gap-3">
        <div className="size-11 rounded-xl bg-slate-200 dark:bg-slate-700" />
        <div className="space-y-2">
          <div className="h-4 w-32 rounded bg-slate-200 dark:bg-slate-700" />
          <div className="h-3 w-20 rounded bg-muted" />
        </div>
      </div>
      <div className="space-y-2">
        <div className="h-3 w-24 rounded bg-muted" />
        <div className="h-11 w-full rounded-xl bg-muted" />
      </div>
      <div className="h-11 w-full rounded-xl bg-muted" />
    </div>
  );
}

/**
 * ============================================================================
 * [FAMILY HEALTH PROFILE] HỒ SƠ Y KHOA CỦA GIA ĐÌNH
 * ============================================================================
 * Bố cục theo lớp thông tin: tổng quan -> liên hệ của tôi -> người thân ->
 * lối tắt. Bảng màu thống nhất với phần còn lại của sản phẩm: teal/sky cho
 * hành động lâm sàng, emerald cho trạng thái tốt, amber cho lưu ý, và đỏ chỉ
 * dành cho SOS hoặc hành động phá hủy.
 */
export default function PatientProfileRootPage() {
  const { data: profiles, isLoading } = useGetProfiles();
  const { activeProfileId, setActiveProfileId, openAddProfileModal, openEditProfileModal } =
    useActiveProfileStore();
  const deleteProfileMutation = useDeleteProfile();
  const user = useAuthStore((state) => state.user);

  const [profileToDelete, setProfileToDelete] = useState<ProfileResponseDTO | null>(null);

  // Tự động chọn hồ sơ gốc nếu người dùng chưa chọn thủ công
  useEffect(() => {
    if (!activeProfileId && profiles && profiles.length > 0) {
      const primary = profiles.find((p) => p.is_primary) || profiles[0];
      if (primary) setActiveProfileId(primary.id);
    }
  }, [profiles, activeProfileId, setActiveProfileId]);

  const handleConfirmDelete = () => {
    if (!profileToDelete) return;

    deleteProfileMutation.mutate(profileToDelete.id, {
      onSuccess: () => {
        toast.success(`Đã xóa hồ sơ "${profileToDelete.full_name}".`, {
          description: "Hồ sơ y khoa đã được loại bỏ vĩnh viễn khỏi hệ thống.",
        });
        if (activeProfileId === profileToDelete.id) {
          const primaryProfile = profiles?.find((p) => p.is_primary && p.id !== profileToDelete.id);
          if (primaryProfile) setActiveProfileId(primaryProfile.id);
        }
        setProfileToDelete(null);
      },
      onError: (error) => {
        toast.error("Không thể xóa hồ sơ này.", { description: error.message });
        setProfileToDelete(null);
      },
    });
  };

  const memberCount = profiles?.length ?? 0;
  const missingPhoneCount = profiles?.filter((p) => !p.phone_number).length ?? 0;

  return (
    <main className="min-h-[calc(100vh-64px)] bg-background/80 px-4 py-8 font-sans text-slate-800 sm:px-6 lg:px-8 dark:text-slate-100">
      <div className="mx-auto max-w-6xl space-y-6">

        {/* ---------- 1. TỔNG QUAN HỒ SƠ ---------- */}
        <header className="overflow-hidden rounded-2xl border border-border bg-card shadow-xs">
          <div className="flex flex-col gap-4 border-b border-slate-100 bg-gradient-to-r from-teal-50/80 to-sky-50/50 p-6 md:flex-row md:items-center md:justify-between">
            <div className="flex items-center gap-4">
              <span className="flex size-12 shrink-0 items-center justify-center rounded-xl bg-teal-600 text-white">
                <Users className="size-6 stroke-[2.2]" aria-hidden="true" />
              </span>
              <div className="min-w-0">
                <h1 className="text-xl font-bold tracking-tight text-foreground sm:text-2xl">
                  Hồ sơ y khoa của gia đình
                </h1>
                <p className="mt-0.5 text-sm text-slate-600 dark:text-slate-300">
                  Quản lý thông tin sức khỏe &amp; liên hệ của bạn và người thân
                </p>
              </div>
            </div>

            <button
              type="button"
              onClick={openAddProfileModal}
              id="btn-open-add-member"
              className="inline-flex min-h-11 shrink-0 items-center justify-center gap-1.5 rounded-xl bg-teal-600 px-4 text-sm font-bold text-white shadow-sm transition-colors hover:bg-teal-700 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-teal-600 focus-visible:ring-offset-2"
            >
              <Plus className="size-4 stroke-[2.4]" aria-hidden="true" />
              Thêm thành viên
            </button>
          </div>

          <dl className="grid grid-cols-1 divide-y divide-slate-100 sm:grid-cols-3 sm:divide-x sm:divide-y-0">
            <div className="p-5">
              <dt className="text-xs font-bold uppercase tracking-wide text-muted-foreground">Chủ tài khoản</dt>
              <dd className="mt-1 truncate text-base font-semibold text-foreground">
                {user?.name ?? "—"}
              </dd>
            </div>
            <div className="p-5">
              <dt className="text-xs font-bold uppercase tracking-wide text-muted-foreground">Số hồ sơ</dt>
              <dd className="mt-1 text-base font-semibold text-foreground">
                {isLoading ? "—" : `${memberCount} thành viên`}
              </dd>
            </div>
            <div className="p-5">
              <dt className="text-xs font-bold uppercase tracking-wide text-muted-foreground">Liên hệ</dt>
              <dd className="mt-1 text-base font-semibold">
                {isLoading ? (
                  <span className="text-foreground">—</span>
                ) : missingPhoneCount === 0 ? (
                  <span className="inline-flex items-center gap-1.5 text-emerald-700">
                    <ShieldCheck className="size-4 shrink-0" aria-hidden="true" />
                    Đã đủ số điện thoại
                  </span>
                ) : (
                  <span className="inline-flex items-center gap-1.5 text-amber-700">
                    <AlertTriangle className="size-4 shrink-0" aria-hidden="true" />
                    {missingPhoneCount} hồ sơ thiếu số
                  </span>
                )}
              </dd>
            </div>
          </dl>
        </header>

        {/* ---------- 2. THÔNG TIN LIÊN HỆ CỦA TÔI ---------- */}
        <AccountContactCard />

        {/* ---------- 3. NGƯỜI THÂN & GIA ĐÌNH ---------- */}
        <section className="space-y-4">
          <div className="flex flex-wrap items-end justify-between gap-3">
            <div>
              <h2 className="text-lg font-bold tracking-tight text-foreground sm:text-xl">
                Người thân &amp; gia đình
              </h2>
              <p className="mt-0.5 text-sm text-slate-600 dark:text-slate-300">
                Chọn một hồ sơ để dùng cho phiên khám Triage tiếp theo
              </p>
            </div>
          </div>

          {isLoading ? (
            <div className="grid grid-cols-1 gap-5 sm:grid-cols-2 lg:grid-cols-3">
              {[1, 2, 3].map((key) => (
                <MemberCardSkeleton key={key} />
              ))}
            </div>
          ) : memberCount === 0 ? (
            <div className="flex flex-col items-center gap-3 rounded-2xl border border-dashed border-slate-300 bg-card p-10 text-center dark:border-slate-700">
              <span className="flex size-12 items-center justify-center rounded-xl bg-muted text-muted-foreground">
                <Users className="size-6" aria-hidden="true" />
              </span>
              <p className="text-base font-semibold text-foreground">Chưa có hồ sơ thành viên nào</p>
              <p className="max-w-md text-sm leading-6 text-slate-600 dark:text-slate-300">
                Thêm hồ sơ cho bản thân và người thân để lưu lại thông tin sức khỏe cần thiết.
              </p>
              <button
                type="button"
                onClick={openAddProfileModal}
                className="mt-1 inline-flex min-h-11 items-center gap-1.5 rounded-xl bg-teal-600 px-4 text-sm font-bold text-white hover:bg-teal-700 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-teal-600 focus-visible:ring-offset-2"
              >
                <Plus className="size-4" aria-hidden="true" />
                Thêm thành viên đầu tiên
              </button>
            </div>
          ) : (
            <div className="grid grid-cols-1 gap-5 sm:grid-cols-2 lg:grid-cols-3">
              {profiles?.map((member) => (
                <FamilyMemberCard
                  key={member.id}
                  member={member}
                  isSelected={activeProfileId === member.id}
                  onSelect={() => setActiveProfileId(member.id)}
                  onEdit={() => openEditProfileModal(member.id)}
                  onDelete={
                    !member.is_primary && member.relationship_type !== "SELF"
                      ? () => setProfileToDelete(member)
                      : null
                  }
                />
              ))}
            </div>
          )}
        </section>

        {/* ---------- 4. LỐI TẮT SANG HỒ SƠ BỆNH ÁN ----------
             Một lối vào duy nhất, đi thẳng tới biểu mẫu khai báo ở /profile/ehr
             (không có bước xác nhận trung gian nào). Thẻ "gọi cấp cứu 115" cũ đã
             được gỡ theo yêu cầu -- số 115 vẫn còn ở chân trang chủ, nơi nó phục
             vụ đúng ngữ cảnh cảnh báo thay vì nằm cạnh thao tác quản trị hồ sơ. */}
        <section>
          <Link
            href="/profile/ehr"
            className="group flex items-center gap-4 rounded-2xl border border-border bg-card p-5 shadow-xs transition-all hover:border-sky-300 hover:shadow-md focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-sky-600 focus-visible:ring-offset-2 sm:p-6"
          >
            <span className="flex size-12 shrink-0 items-center justify-center rounded-xl border border-sky-100 bg-sky-50 text-sky-700 transition-colors group-hover:bg-sky-600 group-hover:text-white">
              <FileText className="size-6 stroke-[2.2]" aria-hidden="true" />
            </span>
            <div className="min-w-0 flex-1">
              <h3 className="text-base font-bold text-foreground sm:text-lg">
                Khai báo hồ sơ bệnh án (EHR Lite)
              </h3>
              <p className="mt-1 text-sm leading-6 text-slate-600 dark:text-slate-300">
                Lưu những thông tin bạn biết về cơ thể, bệnh nền, dị ứng và thuốc đang dùng. Bạn có thể
                cập nhật bất cứ lúc nào.
              </p>
            </div>
            <ArrowRight
              className="size-5 shrink-0 text-slate-400 transition-transform group-hover:translate-x-1"
              aria-hidden="true"
            />
          </Link>
        </section>

        {/* ---------- MODALS ---------- */}
        <AddProfileModal />
        <EditProfileModal />
        <ConfirmDeleteDialog
          profile={profileToDelete}
          isOpen={profileToDelete !== null}
          isPending={deleteProfileMutation.isPending}
          onConfirm={handleConfirmDelete}
          onCancel={() => setProfileToDelete(null)}
        />
      </div>
    </main>
  );
}
