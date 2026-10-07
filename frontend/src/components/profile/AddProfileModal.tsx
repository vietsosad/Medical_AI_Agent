"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { useForm, useWatch } from "react-hook-form";
import {
  Baby,
  Check,
  CircleAlert,
  HeartHandshake,
  Loader2,
  UserPlus,
  UsersRound,
  X,
  type LucideIcon,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogClose,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { cn } from "@/lib/utils";
import { useCreateProfile } from "@/queries/useProfileQueries";
import {
  CreateFamilyProfileFormSchema,
  type CreateFamilyProfileFormInput,
  type CreateFamilyProfileFormValues,
} from "@/schemas/clinical-profile.schema";
import type { AvatarColorToken, RelationshipType } from "@/services/profile.service";
import { useActiveProfileStore } from "@/store/useActiveProfileStore";

const DEFAULT_FORM_VALUES: CreateFamilyProfileFormInput = {
  fullName: "",
  relationship: "CHILD",
  age: "",
  gender: "Male",
  bloodType: "O+",
  phoneNumber: "",
};

const RELATIONSHIP_OPTIONS: Array<{
  value: CreateFamilyProfileFormInput["relationship"];
  label: string;
  icon: LucideIcon;
}> = [
  { value: "CHILD", label: "Con cái", icon: Baby },
  { value: "PARENT", label: "Cha mẹ", icon: UsersRound },
  { value: "SPOUSE", label: "Vợ hoặc chồng", icon: HeartHandshake },
  { value: "OTHER", label: "Người thân khác", icon: UsersRound },
];

const AVATAR_COLOR_BY_RELATIONSHIP: Record<RelationshipType, AvatarColorToken> = {
  SELF: "blue",
  CHILD: "blue",
  SPOUSE: "emerald",
  PARENT: "rose",
  SIBLING: "slate",
  OTHER: "amber",
};

/**
 * Dialog tạo nhanh hồ sơ gia đình.
 * Chỉ thu thập dữ liệu cần thiết; tiền sử và thuốc được bổ sung sau trong EHR Lite.
 */
export function AddProfileModal() {
  const { isAddProfileModalOpen, closeAddProfileModal, setActiveProfileId } = useActiveProfileStore();
  const createProfileMutation = useCreateProfile();
  const {
    formState: { errors },
    control,
    handleSubmit,
    register,
    reset,
    setError,
  } = useForm<CreateFamilyProfileFormInput, unknown, CreateFamilyProfileFormValues>({
    resolver: zodResolver(CreateFamilyProfileFormSchema),
    defaultValues: DEFAULT_FORM_VALUES,
  });
  const selectedRelationship = useWatch({ control, name: "relationship" });

  const handleClose = () => {
    reset(DEFAULT_FORM_VALUES);
    closeAddProfileModal();
  };

  const handleOpenChange = (open: boolean) => {
    if (!open) {
      handleClose();
    }
  };

  const handleQuickSubmit = (values: CreateFamilyProfileFormValues) => {
    const normalizedAge = values.age.trim();

    createProfileMutation.mutate(
      {
        full_name: values.fullName.trim(),
        relationship_type: values.relationship,
        age: normalizedAge ? Number(normalizedAge) : undefined,
        gender: values.gender.toUpperCase() as "MALE" | "FEMALE" | "OTHER",
        blood_type: values.bloodType === "Chưa rõ" ? undefined : values.bloodType,
        phone_number: values.phoneNumber,
        avatar_color: AVATAR_COLOR_BY_RELATIONSHIP[values.relationship],
      },
      {
        onSuccess: (newProfile) => {
          reset(DEFAULT_FORM_VALUES);
          closeAddProfileModal();
          setActiveProfileId(newProfile.id);
        },
        onError: (error) => {
          setError("root", {
            message: error.message || "Không thể tạo hồ sơ thành viên lúc này.",
          });
        },
      }
    );
  };

  return (
    <Dialog open={isAddProfileModalOpen} onOpenChange={handleOpenChange}>
      <DialogContent
        hideCloseButton
        overlayClassName="bg-slate-950/55 backdrop-blur-sm"
        className="max-h-[calc(100dvh-32px)] max-w-xl gap-0 overflow-y-auto rounded-2xl border-sky-100 bg-card p-0 text-slate-800 shadow-xl shadow-slate-950/20 dark:text-slate-100"
      >
        <DialogHeader className="space-y-2 border-b border-sky-100 bg-sky-50/60 p-6 pr-16 text-left">
          <div className="flex items-center gap-4">
            <div className="flex size-12 shrink-0 items-center justify-center rounded-xl bg-card text-sky-700 shadow-sm ring-1 ring-sky-100">
              <UserPlus className="size-6 stroke-[2.25]" aria-hidden="true" />
            </div>
            <div className="space-y-2">
              <DialogTitle className="text-xl font-bold leading-tight text-foreground">
                Thêm thành viên gia đình
              </DialogTitle>
              <DialogDescription className="text-sm leading-6 text-slate-600 dark:text-slate-300">
                Chỉ cần thông tin cơ bản. Bạn có thể bổ sung bệnh sử và thuốc đang dùng sau.
              </DialogDescription>
            </div>
          </div>
        </DialogHeader>

        <DialogClose asChild>
          <Button
            type="button"
            variant="ghost"
            size="icon"
            aria-label="Đóng cửa sổ thêm thành viên"
            className="absolute right-4 top-4 size-12 rounded-xl text-muted-foreground hover:bg-card hover:text-foreground focus-visible:ring-2 focus-visible:ring-sky-600 focus-visible:ring-offset-2"
          >
            <X className="size-5 stroke-[2.5]" aria-hidden="true" />
          </Button>
        </DialogClose>

        <form
          id="create-profile-form"
          noValidate
          onSubmit={handleSubmit(handleQuickSubmit)}
          className="space-y-6 p-6"
        >
          {errors.root?.message ? (
            <div
              role="alert"
              aria-live="assertive"
              className="flex items-start gap-2 rounded-xl border border-rose-200 bg-rose-50 p-4 text-sm font-medium leading-6 text-rose-800"
            >
              <CircleAlert className="size-5 shrink-0 stroke-[2.25]" aria-hidden="true" />
              <p>{errors.root.message}</p>
            </div>
          ) : null}

          <div className="space-y-2">
            <label htmlFor="input-profile-name" className="block text-sm font-semibold text-slate-800 dark:text-slate-100">
              Họ và tên thành viên <span className="text-sky-700">*</span>
            </label>
            <input
              id="input-profile-name"
              type="text"
              autoComplete="name"
              autoFocus
              aria-invalid={Boolean(errors.fullName)}
              aria-describedby={errors.fullName ? "input-profile-name-error" : undefined}
              placeholder="Ví dụ: Bé Bông, Mẹ Nga, Anh Hùng"
              className={cn(
                "min-h-12 w-full rounded-xl border bg-background px-4 text-base text-foreground outline-none transition-colors placeholder:text-slate-400 focus-visible:bg-card focus-visible:ring-2 focus-visible:ring-sky-600 focus-visible:ring-offset-2",
                errors.fullName
                  ? "border-rose-500 focus-visible:ring-rose-600"
                  : "border-slate-300 focus-visible:border-sky-600 dark:border-slate-700"
              )}
              {...register("fullName")}
            />
            {errors.fullName?.message ? (
              <p id="input-profile-name-error" className="text-sm font-medium text-rose-700">
                {errors.fullName.message}
              </p>
            ) : null}
          </div>

          <fieldset className="space-y-2">
            <legend className="text-sm font-semibold text-slate-800 dark:text-slate-100">Mối quan hệ với bạn</legend>
            <div className="grid grid-cols-1 gap-2 sm:grid-cols-2">
              {RELATIONSHIP_OPTIONS.map((relationshipOption) => {
                const Icon = relationshipOption.icon;
                const isSelected = selectedRelationship === relationshipOption.value;

                return (
                  <label
                    key={relationshipOption.value}
                    className={cn(
                      "flex min-h-14 cursor-pointer items-center gap-4 rounded-xl border px-4 text-left text-base font-semibold transition-colors focus-within:ring-2 focus-within:ring-sky-600 focus-within:ring-offset-2",
                      isSelected
                        ? "border-sky-600 bg-sky-50 text-sky-950"
                        : "border-slate-200 bg-card text-slate-800 hover:border-sky-300 hover:bg-sky-50/60"
                    )}
                  >
                    <input
                      type="radio"
                      value={relationshipOption.value}
                      className="sr-only"
                      {...register("relationship")}
                    />
                    <Icon
                      className={cn("size-5 shrink-0 stroke-[2.25]", isSelected ? "text-sky-700" : "text-muted-foreground")}
                      aria-hidden="true"
                    />
                    <span className="flex-1">{relationshipOption.label}</span>
                    {isSelected ? <Check className="size-5 shrink-0 text-sky-700 stroke-[2.5]" aria-hidden="true" /> : null}
                  </label>
                );
              })}
            </div>
          </fieldset>

          <div className="space-y-2">
            <label htmlFor="input-profile-phone" className="block text-sm font-semibold text-slate-800 dark:text-slate-100">
              Số điện thoại <span className="font-normal text-muted-foreground">(không bắt buộc)</span>
            </label>
            <input
              id="input-profile-phone"
              type="tel"
              inputMode="tel"
              autoComplete="tel"
              maxLength={24}
              aria-invalid={Boolean(errors.phoneNumber)}
              aria-describedby={errors.phoneNumber ? "input-profile-phone-error" : undefined}
              placeholder="Ví dụ: 0912345678"
              className={cn(
                "min-h-12 w-full rounded-xl border bg-background px-4 text-base text-foreground outline-none transition-colors placeholder:text-slate-400 focus-visible:bg-card focus-visible:ring-2 focus-visible:ring-sky-600 focus-visible:ring-offset-2",
                errors.phoneNumber
                  ? "border-rose-500 focus-visible:ring-rose-600"
                  : "border-slate-300 focus-visible:border-sky-600 dark:border-slate-700"
              )}
              {...register("phoneNumber")}
            />
            {errors.phoneNumber?.message ? (
              <p id="input-profile-phone-error" className="text-sm font-medium text-rose-700">
                {errors.phoneNumber.message}
              </p>
            ) : null}
          </div>

          <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
            <div className="space-y-2">
              <label htmlFor="input-profile-age" className="block text-sm font-semibold text-slate-800 dark:text-slate-100">
                Tuổi <span className="font-normal text-muted-foreground">(không bắt buộc)</span>
              </label>
              <input
                id="input-profile-age"
                type="number"
                min="0"
                max="120"
                inputMode="numeric"
                aria-invalid={Boolean(errors.age)}
                aria-describedby={errors.age ? "input-profile-age-error" : undefined}
                placeholder="Ví dụ: 68"
                className={cn(
                  "min-h-12 w-full rounded-xl border bg-background px-4 text-base text-foreground outline-none transition-colors placeholder:text-slate-400 focus-visible:bg-card focus-visible:ring-2 focus-visible:ring-sky-600 focus-visible:ring-offset-2",
                  errors.age ? "border-rose-500 focus-visible:ring-rose-600" : "border-slate-300 focus-visible:border-sky-600 dark:border-slate-700"
                )}
                {...register("age")}
              />
              {errors.age?.message ? (
                <p id="input-profile-age-error" className="text-sm font-medium text-rose-700">
                  {errors.age.message}
                </p>
              ) : null}
            </div>

            <div className="space-y-2">
              <label htmlFor="select-profile-gender" className="block text-sm font-semibold text-slate-800 dark:text-slate-100">
                Giới tính
              </label>
              <select
                id="select-profile-gender"
                className="min-h-12 w-full rounded-xl border border-slate-300 bg-background px-4 text-base text-foreground outline-none transition-colors focus-visible:border-sky-600 focus-visible:bg-card focus-visible:ring-2 focus-visible:ring-sky-600 focus-visible:ring-offset-2 dark:border-slate-700"
                {...register("gender")}
              >
                <option value="Male">Nam</option>
                <option value="Female">Nữ</option>
                <option value="Other">Khác</option>
              </select>
            </div>

            <div className="space-y-2">
              <label htmlFor="select-profile-blood" className="block text-sm font-semibold text-slate-800 dark:text-slate-100">
                Nhóm máu
              </label>
              <select
                id="select-profile-blood"
                className="min-h-12 w-full rounded-xl border border-slate-300 bg-background px-4 text-base text-foreground outline-none transition-colors focus-visible:border-sky-600 focus-visible:bg-card focus-visible:ring-2 focus-visible:ring-sky-600 focus-visible:ring-offset-2 dark:border-slate-700"
                {...register("bloodType")}
              >
                <option value="O+">O+</option>
                <option value="A+">A+</option>
                <option value="B+">B+</option>
                <option value="AB+">AB+</option>
                <option value="O-">O-</option>
                <option value="A-">A-</option>
                <option value="B-">B-</option>
                <option value="AB-">AB-</option>
                <option value="Chưa rõ">Chưa rõ</option>
              </select>
            </div>
          </div>
        </form>

        <footer className="flex flex-col-reverse gap-2 border-t border-border bg-card px-6 py-4 sm:flex-row sm:justify-end">
          <Button
            type="button"
            variant="secondary"
            onClick={handleClose}
            disabled={createProfileMutation.isPending}
            className="min-h-12 px-6 text-sm font-semibold text-slate-700 focus-visible:ring-2 focus-visible:ring-sky-600 focus-visible:ring-offset-2 dark:text-slate-200"
          >
            Hủy
          </Button>
          <Button
            type="submit"
            form="create-profile-form"
            disabled={createProfileMutation.isPending}
            className="min-h-12 bg-teal-600 px-6 text-base font-bold text-white hover:bg-teal-700 focus-visible:ring-2 focus-visible:ring-teal-600 focus-visible:ring-offset-2"
          >
            {createProfileMutation.isPending ? <Loader2 className="size-5 animate-spin" aria-hidden="true" /> : null}
            Lưu thành viên
          </Button>
        </footer>
      </DialogContent>
    </Dialog>
  );
}
