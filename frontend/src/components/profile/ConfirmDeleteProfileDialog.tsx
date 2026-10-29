"use client";

import { Loader2, Trash2, TriangleAlert } from "lucide-react";
import { toast } from "sonner";

import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { isOwnProfile } from "@/components/patient/history-model";
import { useDeleteProfile } from "@/queries/useProfileQueries";
import type { ProfileResponseDTO } from "@/services/profile.service";
import { useActiveProfileStore } from "@/store/useActiveProfileStore";

interface ConfirmDeleteProfileDialogProps {
  /** Hồ sơ sắp xóa; null là hộp thoại đóng. */
  profile: ProfileResponseDTO | null;
  /** Danh sách hiện tại, để chọn lại người khác nếu đang xem đúng người bị xóa. */
  profiles: ProfileResponseDTO[] | undefined;
  onClose: () => void;
}

/**
 * Xác nhận xóa một hồ sơ người thân, dùng chung cho trang Hồ sơ và bộ chọn
 * người trên trang EHR. Xóa xong mà người bị xóa đang được chọn thì chuyển về
 * hồ sơ chính (hoặc người còn lại đầu tiên), không để trang trỏ vào hồ sơ đã mất.
 */
export function ConfirmDeleteProfileDialog({ profile, profiles, onClose }: ConfirmDeleteProfileDialogProps) {
  const deleteProfileMutation = useDeleteProfile();
  const activeProfileId = useActiveProfileStore((state) => state.activeProfileId);
  const setActiveProfileId = useActiveProfileStore((state) => state.setActiveProfileId);
  const isPending = deleteProfileMutation.isPending;

  const handleConfirm = () => {
    if (!profile) return;
    deleteProfileMutation.mutate(profile.id, {
      onSuccess: () => {
        toast.success(`Đã xóa hồ sơ "${profile.full_name}".`, {
          description: "Hồ sơ y khoa đã được loại bỏ vĩnh viễn khỏi hệ thống.",
        });
        if (activeProfileId === profile.id) {
          const remaining = (profiles ?? []).filter((item) => item.id !== profile.id);
          const next = remaining.find((item) => isOwnProfile(item)) ?? remaining[0] ?? null;
          setActiveProfileId(next?.id ?? null);
        }
        onClose();
      },
      onError: (error) => {
        toast.error("Không thể xóa hồ sơ này.", { description: error.message });
        onClose();
      },
    });
  };

  return (
    <Dialog
      open={profile !== null}
      onOpenChange={(open) => {
        if (!open && !isPending) onClose();
      }}
    >
      <DialogContent
        role="alertdialog"
        hideCloseButton
        overlayClassName="bg-slate-950/55 backdrop-blur-sm"
        className="max-w-md gap-0 rounded-3xl border-border bg-card p-0 text-foreground shadow-xl"
      >
        <DialogHeader className="space-y-4 border-b border-border p-6 text-left">
          <div className="flex items-center gap-4">
            <span className="flex size-11 shrink-0 items-center justify-center rounded-xl bg-rose-100 text-rose-700 dark:bg-rose-950 dark:text-rose-300">
              <TriangleAlert className="size-5" aria-hidden="true" />
            </span>
            <DialogTitle className="text-lg font-bold text-foreground">Xóa hồ sơ thành viên</DialogTitle>
          </div>
          <DialogDescription className="text-sm leading-6 text-muted-foreground">
            Bạn có chắc muốn xóa hồ sơ y khoa của <strong className="text-foreground">{profile?.full_name}</strong>{" "}
            không? Toàn bộ dữ liệu tiền sử bệnh, dị ứng và người liên hệ khẩn cấp sẽ bị{" "}
            <strong className="text-rose-700 dark:text-rose-300">xóa vĩnh viễn</strong> và không thể khôi phục.
          </DialogDescription>
        </DialogHeader>
        <div className="flex flex-col-reverse gap-2 p-4 sm:flex-row sm:justify-end">
          <button
            type="button"
            onClick={onClose}
            disabled={isPending}
            className="flex min-h-11 items-center justify-center rounded-xl border border-border bg-card px-4 text-sm font-semibold text-foreground transition-colors hover:bg-muted focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand disabled:opacity-50"
          >
            Hủy bỏ
          </button>
          <button
            type="button"
            onClick={handleConfirm}
            disabled={isPending}
            className="flex min-h-11 items-center justify-center gap-2 rounded-xl bg-rose-600 px-4 text-sm font-bold text-white transition-colors hover:bg-rose-700 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-rose-600 focus-visible:ring-offset-2 disabled:opacity-60"
          >
            {isPending ? (
              <Loader2 className="size-4 animate-spin" aria-hidden="true" />
            ) : (
              <Trash2 className="size-4" aria-hidden="true" />
            )}
            Xóa vĩnh viễn
          </button>
        </div>
      </DialogContent>
    </Dialog>
  );
}
