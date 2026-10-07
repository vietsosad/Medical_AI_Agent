"use client";

import React, { useEffect, useState } from "react";
import { useGetProfiles, useDeleteProfile } from "@/queries/useProfileQueries";
import { useActiveProfileStore } from "@/store/useActiveProfileStore";
import { RelationshipType, ProfileResponseDTO } from "@/services/profile.service";
import { User, Baby, Heart, ShieldCheck, Plus, Loader2, Check, Trash2, AlertTriangle } from "lucide-react";
import { AddProfileModal } from "@/components/profile/AddProfileModal";
import { toast } from "sonner";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";

// ============================================================================
// 1. HELPER: TRÌNH CHỌN BIỂU TƯỢNG VÀ MÀU SẮC NHẬN DIỆN LÂM SÀNG TỐI GIẢN
// ============================================================================
function getRelationshipMeta(relationship: RelationshipType, isPrimary: boolean) {
  if (isPrimary || relationship === "SELF") {
    return {
      label: "CHÍNH CHỦ (BẠN)",
      icon: User,
      colorClass: "text-blue-700 bg-blue-100/80 border-blue-200",
      activeTabStyle: "bg-blue-600 text-white border-blue-500 shadow-md shadow-blue-900/10",
      inactiveTabStyle: "bg-card text-slate-800 hover:bg-blue-50/50 hover:border-blue-300 border-slate-200/90 shadow-2xs",
    };
  }
  switch (relationship) {
    case "CHILD":
      return {
        label: "CON CÁI (NHI KHOA)",
        icon: Baby,
        colorClass: "text-sky-700 bg-sky-100/80 border-sky-200",
        activeTabStyle: "bg-sky-600 text-white border-sky-500 shadow-md shadow-sky-900/10",
        inactiveTabStyle: "bg-card text-slate-800 hover:bg-sky-50/50 hover:border-sky-300 border-slate-200/90 shadow-2xs",
      };
    case "SPOUSE":
      return {
        label: "VỢ / CHỒNG",
        icon: Heart,
        colorClass: "text-teal-700 bg-teal-100/80 border-teal-200",
        activeTabStyle: "bg-teal-600 text-white border-teal-500 shadow-md shadow-teal-900/10",
        inactiveTabStyle: "bg-card text-slate-800 hover:bg-teal-50/50 hover:border-teal-300 border-slate-200/90 shadow-2xs",
      };
    case "PARENT":
      return {
        label: "CHA MẸ (LÃO KHOA)",
        icon: ShieldCheck,
        colorClass: "text-slate-800 bg-slate-200/80 border-slate-300 dark:text-slate-100 dark:bg-slate-700 dark:border-slate-700",
        activeTabStyle: "bg-slate-900 text-white border-slate-800 shadow-md shadow-slate-900/20",
        inactiveTabStyle: "bg-card text-slate-800 hover:bg-muted/60 hover:border-slate-400 border-border/90 shadow-2xs dark:text-slate-100",
      };
    default:
      return {
        label: "NGƯỜI THÂN",
        icon: User,
        colorClass: "text-blue-700 bg-blue-50 border-blue-200",
        activeTabStyle: "bg-blue-700 text-white border-blue-600 shadow-md",
        inactiveTabStyle: "bg-card text-slate-800 hover:bg-background border-border shadow-2xs dark:text-slate-100",
      };
  }
}

// ============================================================================
// 2. CONFIRM DELETE DIALOG
// ============================================================================
interface ConfirmDeleteDialogProps {
  profile: ProfileResponseDTO | null;
  isOpen: boolean;
  isPending: boolean;
  onConfirm: () => void;
  onCancel: () => void;
}

function ConfirmDeleteDialog({ profile, isOpen, isPending, onConfirm, onCancel }: ConfirmDeleteDialogProps) {
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
          <DialogDescription className="text-sm text-slate-600 leading-relaxed dark:text-slate-300">
            Bạn có chắc muốn xóa hồ sơ y khoa của{" "}
            <strong className="text-foreground">{profile?.full_name}</strong> không?{" "}
            Toàn bộ dữ liệu tiền sử bệnh và dị ứng sẽ bị xóa vĩnh viễn và không thể khôi phục.
          </DialogDescription>
        </DialogHeader>
        <div className="flex flex-row justify-end gap-2 p-4">
          <Button
            type="button"
            variant="secondary"
            onClick={onCancel}
            disabled={isPending}
            className="min-h-10 px-5 text-sm font-semibold"
          >
            Hủy bỏ
          </Button>
          <Button
            type="button"
            onClick={onConfirm}
            disabled={isPending}
            className="min-h-10 bg-rose-600 px-5 text-sm font-bold text-white hover:bg-rose-700"
          >
            {isPending ? (
              <Loader2 className="size-4 animate-spin mr-1" />
            ) : (
              <Trash2 className="size-4 mr-1" />
            )}
            Xóa vĩnh viễn
          </Button>
        </div>
      </DialogContent>
    </Dialog>
  );
}

// ============================================================================
// 3. COMPONENT CHÍNH: THANH BENTO TABS CHỌN HỒ SƠ & MODAL THÊM NHANH
// ============================================================================
export default function FamilyProfilePills() {
  const { data: profiles, isLoading } = useGetProfiles();
  const { activeProfileId, setActiveProfileId, openAddProfileModal } = useActiveProfileStore();
  const deleteProfileMutation = useDeleteProfile();

  // State confirm dialog xóa thành viên
  const [profileToDelete, setProfileToDelete] = useState<ProfileResponseDTO | null>(null);

  // Tự động fallback chọn hồ sơ chính nếu activeProfileId đang null
  useEffect(() => {
    if (!activeProfileId && profiles && profiles.length > 0) {
      const primary = profiles.find((p) => p.is_primary) || profiles[0];
      if (primary) {
        setActiveProfileId(primary.id);
      }
    }
  }, [profiles, activeProfileId, setActiveProfileId]);

  // Xử lý xác nhận xóa profile
  const handleConfirmDelete = () => {
    if (!profileToDelete) return;

    deleteProfileMutation.mutate(profileToDelete.id, {
      onSuccess: () => {
        toast.success(`Đã xóa hồ sơ "${profileToDelete.full_name}" thành công.`, {
          description: "Hồ sơ y khoa đã được loại bỏ vĩnh viễn.",
        });
        // Nếu đang chọn profile bị xóa → tự động chuyển về hồ sơ chính (SELF)
        if (activeProfileId === profileToDelete.id) {
          const primaryProfile = profiles?.find((p) => p.is_primary && p.id !== profileToDelete.id);
          if (primaryProfile) setActiveProfileId(primaryProfile.id);
        }
        setProfileToDelete(null);
      },
      onError: (error) => {
        toast.error("Không thể xóa hồ sơ này.", {
          description: error.message,
        });
        setProfileToDelete(null);
      },
    });
  };

  if (isLoading) {
    return (
      <div className="flex items-center gap-3 p-5 bg-background rounded-2xl border border-border text-slate-600 min-h-[60px] shadow-2xs dark:text-slate-300">
        <Loader2 className="w-5 h-5 animate-spin text-blue-600" />
        <span className="text-base font-semibold font-sans">Đang đồng bộ hồ sơ gia đình lâm sàng...</span>
      </div>
    );
  }

  return (
    <section aria-label="Bộ chọn hồ sơ gia đình (Multi-Profile Selector)" className="w-full mb-6">
      <div className="flex flex-col gap-3">
        <header className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 px-1">
          <span className="text-xs sm:text-sm font-black uppercase tracking-wider text-slate-800 flex items-center gap-2 font-sans dark:text-slate-100">
            <span className="inline-block w-2.5 h-2.5 rounded-full bg-blue-600 animate-pulse shadow-xs"></span>
            ĐỐI TƯỢNG KHÁM BỆNH (HỒ SƠ GIA ĐÌNH)
          </span>
          <span className="text-xs font-semibold text-muted-foreground bg-muted/80 px-2.5 py-1 rounded-lg border border-border w-fit">
            Quy tắc lâm sàng: Tách biệt hoàn toàn ký ức AI từng thành viên
          </span>
        </header>

        {/* BENTO PILLS TABS */}
        <div className="flex flex-wrap items-center gap-3 p-3 bg-muted/90 rounded-3xl border border-border/80 shadow-inner backdrop-blur-md">
          {profiles?.map((profile: ProfileResponseDTO) => {
            const isSelected = activeProfileId === profile.id;
            const meta = getRelationshipMeta(profile.relationship_type, profile.is_primary);
            const IconComponent = meta.icon;
            const canDelete = !profile.is_primary && profile.relationship_type !== "SELF";

            return (
              <div key={profile.id} className="relative group/pill">
                <button
                  type="button"
                  onClick={() => setActiveProfileId(profile.id)}
                  aria-pressed={isSelected}
                  id={`pill-profile-${profile.id}`}
                  className={`group flex items-center gap-3.5 px-4 py-3.5 min-h-[52px] rounded-2xl font-sans font-medium transition-all duration-200 focus:outline-none focus-visible:ring-2 focus-visible:ring-blue-600 text-left border ${
                    isSelected ? meta.activeTabStyle : meta.inactiveTabStyle
                  } ${canDelete ? "pr-10" : ""}`}
                >
                  <div
                    className={`flex items-center justify-center w-9 h-9 rounded-xl transition-transform duration-200 group-hover:scale-105 ${
                      isSelected ? "bg-card/20 text-white shadow-xs" : meta.colorClass
                    }`}
                  >
                    <IconComponent className="w-5 h-5 shrink-0 stroke-[2.3]" />
                  </div>
                  <div className="flex flex-col pr-1">
                    <div className="flex items-center gap-2">
                      <span className="text-base font-extrabold tracking-tight line-clamp-1">{profile.full_name}</span>
                      {isSelected && <Check className="w-4 h-4 text-white stroke-[3] shrink-0 animate-in zoom-in-75 duration-150" />}
                    </div>
                    <span className={`text-[11px] uppercase tracking-wider font-extrabold ${isSelected ? "text-blue-100" : "text-muted-foreground"}`}>
                      {meta.label} {profile.age !== null ? `• ${profile.age} tuổi` : ""}
                    </span>
                  </div>
                </button>

                {/* Nút xóa — chỉ hiện với thành viên phụ (không phải SELF/is_primary) */}
                {canDelete && (
                  <button
                    type="button"
                    onClick={(e) => {
                      e.stopPropagation();
                      setProfileToDelete(profile);
                    }}
                    aria-label={`Xóa hồ sơ ${profile.full_name}`}
                    title="Xóa hồ sơ thành viên"
                    className={`absolute right-2 top-1/2 -translate-y-1/2 flex items-center justify-center w-7 h-7 rounded-lg opacity-0 group-hover/pill:opacity-100 transition-all duration-150 focus:outline-none focus-visible:ring-2 focus-visible:ring-rose-500 ${
                      isSelected
                        ? "bg-card/20 hover:bg-card/30 text-white"
                        : "bg-rose-50 hover:bg-rose-100 text-rose-600 border border-rose-200"
                    }`}
                  >
                    <Trash2 className="w-3.5 h-3.5 stroke-[2.5]" />
                  </button>
                )}
              </div>
            );
          })}

          {/* NÚT THÊM NGƯỜI THÂN */}
          <button
            type="button"
            onClick={openAddProfileModal}
            id="btn-add-family-member"
            className="flex items-center justify-center gap-2 px-5 py-3.5 min-h-[52px] rounded-2xl bg-card text-blue-700 hover:bg-blue-600 hover:text-white border-2 border-dashed border-blue-300 hover:border-blue-600 font-bold text-sm transition-all duration-200 shadow-2xs group"
          >
            <Plus className="w-5 h-5 stroke-[2.5] transition-transform duration-200 group-hover:rotate-90" />
            <span>Thêm Người Thân</span>
          </button>
        </div>
      </div>

      {/* MODAL ONBOARDING NHANH (<15 GIÂY) */}
      <AddProfileModal />

      {/* CONFIRM DELETE DIALOG */}
      <ConfirmDeleteDialog
        profile={profileToDelete}
        isOpen={profileToDelete !== null}
        isPending={deleteProfileMutation.isPending}
        onConfirm={handleConfirmDelete}
        onCancel={() => setProfileToDelete(null)}
      />
    </section>
  );
}
