"use client";

import React, { useState, useEffect, useCallback } from "react";
import Link from "next/link";
import { useForm, FormProvider, type SubmitHandler } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { motion, AnimatePresence, type Variants } from "framer-motion";
import { Activity, ArrowLeft, PhoneCall, Save, RotateCcw, TriangleAlert, RefreshCw, FileText } from "lucide-react";
import { cn } from "@/lib/utils";
import { DURATION, EASE_IN_OUT, EASE_OUT, enterTransition, exitTransition } from "@/lib/motion";
import { useEhrLite, EMPTY_EHR_LITE } from "@/queries/use-clinical-profile";
import { useUpdateEhrLite } from "@/queries/use-profile-mutations";
import { EhrLiteSchema, type EhrLiteFormValues } from "@/schemas/clinical-profile.schema";
import { useActiveProfileStore } from "@/store/useActiveProfileStore";

// Import toàn bộ các component con của Hồ sơ Lâm sàng (Nhóm 2)
import { VitalsBmiCard } from "@/components/profile/VitalsBmiCard";
import { ChronicConditionsSelector } from "@/components/profile/ChronicConditionsSelector";
import { AllergiesMedicationsInput } from "@/components/profile/AllergiesMedicationsInput";
import { VerifiedClinicalContextPreview } from "@/components/profile/VerifiedClinicalContextPreview";
import { EmergencySosManager } from "@/components/profile/EmergencySosManager";
import FamilyProfilePills, { EHR_SUBJECT_PANEL_ID } from "@/components/profile/FamilyProfilePills";
import { toast } from "sonner";

// ============================================================================
// COMPONENT INTERFACE
// ============================================================================
export interface ClinicalProfileDashboardProps {
  className?: string;
}

type DashboardTab = "EHR" | "SOS";

const TAB_HIGHLIGHT_TRANSITION = { duration: DURATION.quick, ease: EASE_IN_OUT };

/** Đổi nhóm thông tin: nhóm cũ mờ đi, nhóm mới nổi lên 8px. */
const tabPanelVariants: Variants = {
  hidden: { opacity: 0, y: 8 },
  visible: { opacity: 1, y: 0, transition: enterTransition },
  exit: { opacity: 0, transition: exitTransition },
};

/** Thanh lưu trượt lên khi có thay đổi chưa lưu, không nảy. */
const saveBarVariants: Variants = {
  hidden: { opacity: 0, y: 24 },
  visible: { opacity: 1, y: 0, transition: { duration: DURATION.gentle, ease: EASE_OUT } },
  exit: { opacity: 0, y: 24, transition: exitTransition },
};

const TABS: Array<{ value: DashboardTab; label: string; icon: typeof Activity }> = [
  { value: "EHR", label: "Thông tin sức khỏe", icon: Activity },
  { value: "SOS", label: "Liên hệ khẩn cấp", icon: PhoneCall },
];

/**
 * Hồ sơ sức khỏe để người dùng tự khai báo và rà soát thông tin của mình.
 */
export const ClinicalProfileDashboard: React.FC<ClinicalProfileDashboardProps> = ({ className }) => {
  // Tab State
  const [activeTab, setActiveTab] = useState<DashboardTab>("EHR");
  const activeProfileId = useActiveProfileStore((state) => state.activeProfileId);

  // TanStack Query & Mutation Hooks cho EHR Lite
  const { data: ehrData, isLoading, isError, refetch } = useEhrLite();
  const updateMutation = useUpdateEhrLite();

  // Thiết lập React Hook Form cho EHR Lite
  const form = useForm<EhrLiteFormValues>({
    resolver: zodResolver(EhrLiteSchema),
    defaultValues: ehrData || EMPTY_EHR_LITE,
  });

  // Đồng bộ giá trị khi TanStack Query fetch thành công từ máy chủ
  useEffect(() => {
    if (ehrData) {
      form.reset(ehrData);
    }
  }, [ehrData, form]);

  // Xử lý Lưu Bệnh Án Sơ Bộ
  const onSubmit: SubmitHandler<EhrLiteFormValues> = useCallback(
    (values) => {
      updateMutation.mutate(values, {
        onSuccess: (updated) => {
          form.reset(updated); // Reset lại state isDirty về false sau khi lưu thành công
        },
      });
    },
    [updateMutation, form]
  );

  // Xử lý Khôi Phục (Reset) thay đổi chưa lưu
  const handleReset = useCallback(() => {
    form.reset(ehrData ?? EMPTY_EHR_LITE);
    toast.info("Đã khôi phục các thông tin chưa lưu.");
  }, [ehrData, form]);

  // ==========================================================================
  // STATE 1: LOADING STATE
  // ==========================================================================
  if (isLoading) {
    return (
      <div aria-busy="true" aria-label="Đang tải hồ sơ sức khỏe" className={cn("mx-auto max-w-6xl space-y-6", className)}>
        <div className="space-y-2">
          <div className="h-8 w-64 rounded-xl bg-muted" />
          <div className="h-4 w-full max-w-md rounded-lg bg-muted" />
        </div>
        <div className="grid grid-cols-1 gap-6 lg:grid-cols-12">
          <div className="skeleton-sweep relative h-96 overflow-hidden rounded-3xl border border-border bg-card lg:col-span-7" />
          <div className="skeleton-sweep relative h-96 overflow-hidden rounded-3xl border border-border bg-card lg:col-span-5" />
        </div>
      </div>
    );
  }

  // ==========================================================================
  // STATE 2: ERROR STATE (KÈM NÚT TẢI LẠI)
  // ==========================================================================
  if (isError) {
    return (
      <div className={cn("mx-auto max-w-2xl", className)}>
        <div
          role="alert"
          className="space-y-4 rounded-3xl border border-rose-200 bg-rose-50 p-6 text-center text-rose-950 dark:border-rose-900 dark:bg-rose-950/40 dark:text-rose-100 md:p-8"
        >
          <span className="mx-auto flex size-14 items-center justify-center rounded-2xl bg-rose-100 text-rose-700 dark:bg-rose-950 dark:text-rose-300">
            <TriangleAlert className="size-7" aria-hidden="true" />
          </span>
          <div className="space-y-2">
            <h2 className="text-xl font-extrabold tracking-tight">Không thể tải hồ sơ sức khỏe</h2>
            <p className="text-sm leading-6">
              Vui lòng kiểm tra kết nối mạng rồi thử lại. Nếu lỗi vẫn tiếp diễn, hãy liên hệ bộ phận hỗ trợ.
            </p>
          </div>
          <button
            type="button"
            onClick={() => refetch()}
            className="mx-auto flex min-h-11 items-center gap-2 rounded-xl bg-rose-600 px-6 text-sm font-bold text-white transition-colors hover:bg-rose-700 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-rose-600 focus-visible:ring-offset-2"
          >
            <RefreshCw className="size-4" aria-hidden="true" />
            Thử lại
          </button>
        </div>
      </div>
    );
  }

  const isDirty = form.formState.isDirty;

  return (
    <FormProvider {...form}>
      <div className={cn("mx-auto max-w-6xl space-y-8 pb-28", className)}>
        <header className="page-enter flex flex-col gap-6 md:flex-row md:items-end md:justify-between">
          <div className="space-y-2">
            <Link
              href="/profile"
              className="-ml-2 inline-flex min-h-11 items-center gap-2 rounded-xl px-2 text-sm font-semibold text-brand transition-colors hover:text-brand-strong focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand"
            >
              <ArrowLeft className="size-4" aria-hidden="true" />
              Hồ sơ gia đình
            </Link>
            <h1 className="text-2xl font-extrabold tracking-tight text-foreground md:text-3xl">
              Thông tin sức khỏe của bạn
            </h1>
            <p className="max-w-2xl text-sm leading-6 text-muted-foreground">
              Lưu những thông tin bạn biết để tiện chia sẻ khi cần. Bạn có thể cập nhật bất cứ lúc nào.
            </p>
          </div>

          {/* Hai nhóm thông tin; nền trắng trượt sang nhóm vừa chọn. */}
          <div
            role="tablist"
            aria-label="Chọn nhóm thông tin y khoa"
            className="flex w-full items-center rounded-2xl border border-border bg-muted md:w-auto"
          >
            {TABS.map((tab) => {
              const selected = activeTab === tab.value;
              const Icon = tab.icon;
              return (
                <button
                  key={tab.value}
                  id={`ehr-tab-${tab.value}`}
                  type="button"
                  role="tab"
                  aria-selected={selected}
                  aria-controls={`ehr-tabpanel-${tab.value}`}
                  onClick={() => setActiveTab(tab.value)}
                  className={cn(
                    "relative flex min-h-11 flex-1 items-center justify-center gap-2 rounded-2xl px-4 text-sm transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand focus-visible:ring-offset-2 focus-visible:ring-offset-background md:flex-none",
                    selected ? "font-bold text-foreground" : "font-semibold text-muted-foreground hover:text-foreground",
                  )}
                >
                  {selected && (
                    <motion.span
                      layoutId="ehr-dashboard-tab-highlight"
                      transition={TAB_HIGHLIGHT_TRANSITION}
                      aria-hidden="true"
                      className="absolute inset-0 rounded-2xl border-2 border-muted bg-card shadow-sm dark:bg-slate-700"
                    />
                  )}
                  <Icon className={cn("relative size-4 shrink-0", selected ? "text-brand" : "text-muted-foreground")} aria-hidden="true" />
                  <span className="relative">{tab.label}</span>
                </button>
              );
            })}
          </div>
        </header>

        {/* =================================================================== */}
        {/* BỘ CHỌN NGƯỜI TRONG GIA ĐÌNH (cùng hàng vòng tròn với trang Hồ sơ)  */}
        {/* =================================================================== */}
        <FamilyProfilePills />

        {/* =================================================================== */}
        {/* NỘI DUNG CỦA NGƯỜI ĐANG CHỌN                                         */}
        {/* =================================================================== */}
        <div
          id={EHR_SUBJECT_PANEL_ID}
          role="tabpanel"
          aria-labelledby={activeProfileId ? `ehr-subject-${activeProfileId}` : undefined}
        >
          <AnimatePresence mode="wait" initial={false}>
            {activeTab === "EHR" ? (
              <motion.div
                key="tab-ehr-content"
                id="ehr-tabpanel-EHR"
                role="tabpanel"
                aria-labelledby="ehr-tab-EHR"
                variants={tabPanelVariants}
                initial="hidden"
                animate="visible"
                exit="exit"
                className="space-y-10"
              >
                <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-10">
                  {/* 1. Bảng Sinh Hiệu & Thanh Đọc BMI Động */}
                  <section aria-label="Thông số Sinh hiệu & BMI">
                    <VitalsBmiCard form={form} />
                  </section>
                  <section aria-label="Tình trạng sức khỏe đã biết">
                    <ChronicConditionsSelector form={form} />
                  </section>

                  {/* 3. Quản Trị Dị Ứng & Thuốc Đang Dùng */}
                  <section aria-label="Dị ứng & Thuốc hằng ngày">
                    <AllergiesMedicationsInput form={form} />
                  </section>

                  <section aria-label="Tóm tắt thông tin đã khai báo">
                    <VerifiedClinicalContextPreview form={form} />
                  </section>
                </form>
              </motion.div>
            ) : (
              <motion.div
                key="tab-sos-content"
                id="ehr-tabpanel-SOS"
                role="tabpanel"
                aria-labelledby="ehr-tab-SOS"
                variants={tabPanelVariants}
                initial="hidden"
                animate="visible"
                exit="exit"
              >
                <EmergencySosManager />
              </motion.div>
            )}
          </AnimatePresence>
        </div>

        {/* =================================================================== */}
        {/* THANH LƯU: TRƯỢT LÊN KHI CÓ THAY ĐỔI CHƯA LƯU                        */}
        {/* Trên điện thoại nằm trên thanh điều hướng đáy, không đè lên nó.      */}
        {/* =================================================================== */}
        <AnimatePresence>
          {activeTab === "EHR" && isDirty && (
            <motion.div
              variants={saveBarVariants}
              initial="hidden"
              animate="visible"
              exit="exit"
              role="region"
              aria-label="Thay đổi chưa lưu"
              className="fixed inset-x-4 bottom-[calc(5rem_+_env(safe-area-inset-bottom))] z-50 mx-auto flex max-w-4xl flex-col justify-between gap-4 rounded-3xl border border-border bg-card/95 p-4 text-foreground shadow-xl backdrop-blur-xl sm:flex-row sm:items-center md:bottom-6 md:px-6"
            >
              <div className="flex items-center gap-4">
                <span className="flex size-11 shrink-0 items-center justify-center rounded-2xl border border-brand-edge bg-brand-soft text-brand">
                  <FileText className="size-5" aria-hidden="true" />
                </span>
                <div>
                  <p className="text-sm font-extrabold text-foreground">Bạn có thay đổi chưa lưu</p>
                  <p className="hidden text-sm text-muted-foreground md:block">
                    Nhấn Lưu thay đổi để cập nhật hồ sơ của bạn.
                  </p>
                </div>
              </div>

              <div className="flex w-full shrink-0 items-center justify-end gap-2 sm:w-auto">
                <button
                  type="button"
                  onClick={handleReset}
                  className="flex min-h-11 items-center gap-2 rounded-xl border border-border bg-card px-4 text-sm font-semibold text-foreground transition-colors hover:bg-muted focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand"
                >
                  <RotateCcw className="size-4" aria-hidden="true" />
                  <span>Hoàn tác</span>
                </button>

                <button
                  type="button"
                  onClick={form.handleSubmit(onSubmit)}
                  disabled={updateMutation.isPending}
                  className="flex min-h-11 items-center gap-2 rounded-xl bg-brand px-6 text-sm font-bold text-brand-foreground shadow-sm transition duration-[180ms] hover:bg-brand-strong focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand focus-visible:ring-offset-2 focus-visible:ring-offset-card active:scale-[0.97] disabled:opacity-50 motion-reduce:transition-none motion-reduce:active:scale-100"
                >
                  {updateMutation.isPending ? (
                    <RefreshCw className="size-4 animate-spin" aria-hidden="true" />
                  ) : (
                    <Save className="size-4" aria-hidden="true" />
                  )}
                  <span>Lưu thay đổi</span>
                </button>
              </div>
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    </FormProvider>
  );
};
