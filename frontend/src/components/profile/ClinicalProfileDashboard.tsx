"use client";

import React, { useState, useEffect, useCallback } from "react";
import { useForm, FormProvider, type SubmitHandler } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { motion, AnimatePresence } from "framer-motion";
import {
  Activity,
  PhoneCall,
  Save,
  RotateCcw,
  AlertTriangle,
  RefreshCw,
  FileText,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { useEhrLite, EMPTY_EHR_LITE } from "@/queries/use-clinical-profile";
import { useUpdateEhrLite } from "@/queries/use-profile-mutations";
import { EhrLiteSchema, type EhrLiteFormValues } from "@/schemas/clinical-profile.schema";

// Import toàn bộ các component con của Hồ sơ Lâm sàng (Nhóm 2)
import { VitalsBmiCard } from "@/components/profile/VitalsBmiCard";
import { ChronicConditionsSelector } from "@/components/profile/ChronicConditionsSelector";
import { AllergiesMedicationsInput } from "@/components/profile/AllergiesMedicationsInput";
import { VerifiedClinicalContextPreview } from "@/components/profile/VerifiedClinicalContextPreview";
import { EmergencySosManager } from "@/components/profile/EmergencySosManager";
import FamilyProfilePills from "@/components/profile/FamilyProfilePills";
import { toast } from "sonner";

// ============================================================================
// COMPONENT INTERFACE
// ============================================================================
export interface ClinicalProfileDashboardProps {
  className?: string;
}

/**
 * Hồ sơ sức khỏe để người dùng tự khai báo và rà soát thông tin của mình.
 */
export const ClinicalProfileDashboard: React.FC<ClinicalProfileDashboardProps> = ({ className }) => {
  // Tab State
  const [activeTab, setActiveTab] = useState<"EHR" | "SOS">("EHR");

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
  // STATE 1: LOADING STATE (SKELETON SHIMMER SANG TRỌNG)
  // ==========================================================================
  if (isLoading) {
    return (
      <div className={cn("space-y-8 animate-pulse p-4 md:p-6 max-w-7xl mx-auto", className)}>
        {/* Skeleton Tabs Header */}
        <div className="flex flex-col sm:flex-row items-center justify-between gap-4 pb-6 border-b border-border">
          <div className="space-y-2 w-full sm:w-1/3">
            <div className="h-8 bg-slate-200 rounded-xl w-3/4 dark:bg-slate-700" />
            <div className="h-4 bg-slate-200/70 rounded-lg w-full dark:bg-slate-700" />
          </div>
          <div className="h-12 bg-slate-200 border border-slate-300/60 rounded-2xl w-full sm:w-80 dark:bg-slate-700 dark:border-slate-700" />
        </div>

        {/* Skeleton Card Component */}
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-8">
          <div className="lg:col-span-7 h-96 bg-card border border-border rounded-3xl shadow-sm" />
          <div className="lg:col-span-5 h-96 bg-card border border-border rounded-3xl shadow-sm" />
        </div>
        <div className="h-72 bg-card border border-border rounded-3xl shadow-sm" />
      </div>
    );
  }

  // ==========================================================================
  // STATE 2: ERROR STATE (ALERTBOX KÈM NÚT RETRY QUERY)
  // ==========================================================================
  if (isError) {
    return (
      <div className={cn("p-6 md:p-12 max-w-4xl mx-auto", className)}>
        <div className="bg-rose-50 border border-rose-200 rounded-3xl p-8 md:p-12 text-center space-y-6 shadow-xl relative overflow-hidden">
          <div className="absolute top-0 right-0 w-64 h-64 bg-rose-200/30 rounded-full blur-3xl pointer-events-none" />

          <div className="w-16 h-16 rounded-2xl bg-rose-100 border border-rose-200 flex items-center justify-center mx-auto shadow-sm">
            <AlertTriangle className="w-8 h-8 text-rose-600 animate-bounce" />
          </div>

          <div className="space-y-2 max-w-xl mx-auto">
            <h2 className="text-xl md:text-2xl font-extrabold text-foreground tracking-tight">
              Không thể tải hồ sơ sức khỏe
            </h2>
            <p className="text-xs md:text-sm text-slate-600 leading-relaxed font-normal dark:text-slate-300">
              Vui lòng kiểm tra kết nối mạng rồi thử lại. Nếu lỗi vẫn tiếp diễn, hãy liên hệ bộ phận hỗ trợ.
            </p>
          </div>

          <button
            type="button"
            onClick={() => refetch()}
            className="px-6 py-3 rounded-2xl bg-rose-600 hover:bg-rose-500 text-white font-bold text-sm inline-flex items-center gap-2 shadow-lg shadow-rose-600/25 transition-all duration-200 active:scale-95"
          >
            <RefreshCw className="w-4 h-4 animate-spin-slow" />
            <span>Thử lại</span>
          </button>
        </div>
      </div>
    );
  }

  const isDirty = form.formState.isDirty;

  return (
    <FormProvider {...form}>
      <div className={cn("mx-auto max-w-6xl space-y-8 pb-28", className)}>
        <header className="flex flex-col gap-6 rounded-3xl border border-sky-100 bg-card p-6 shadow-sm md:flex-row md:items-center md:justify-between md:p-8">
          <div className="flex items-start gap-4">
            <span className="flex size-12 shrink-0 items-center justify-center rounded-2xl bg-sky-50 text-sky-700">
              <FileText className="size-6" aria-hidden="true" />
            </span>
            <div>
              <p className="text-sm font-semibold text-sky-700">Hồ sơ sức khỏe</p>
              <h1 className="mt-1 text-2xl font-bold tracking-tight text-foreground md:text-3xl">
                Thông tin sức khỏe của bạn
              </h1>
              <p className="mt-2 max-w-2xl text-sm leading-6 text-slate-600 dark:text-slate-300">
                Lưu những thông tin bạn biết để tiện chia sẻ khi cần. Bạn có thể cập nhật bất cứ lúc nào.
              </p>
            </div>
          </div>

          {/* Tabs Control Board (Bright Medical Card Switcher) */}
          <div
            role="tablist"
            aria-label="Chọn nhóm thông tin y khoa"
            className="flex w-full items-center rounded-2xl bg-muted p-2 md:w-auto"
          >
            {/* Tab 1 Button: EHR Lite */}
            <button
              type="button"
              role="tab"
              aria-selected={activeTab === "EHR"}
              onClick={() => setActiveTab("EHR")}
              className={cn(
                "relative flex min-h-11 flex-1 items-center justify-center gap-2 rounded-xl px-4 text-sm font-semibold transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-sky-600 focus-visible:ring-offset-2 md:flex-none",
                activeTab === "EHR" ? "text-sky-800 font-extrabold" : "text-slate-600 hover:text-foreground hover:bg-card/50 dark:text-slate-300"
              )}
            >
              {activeTab === "EHR" && (
                <motion.div
                  layoutId="active-profile-tab"
                  className="absolute inset-0 -z-10 rounded-xl bg-card shadow-sm"
                  transition={{ type: "spring", stiffness: 350, damping: 25 }}
                />
              )}
              <Activity className={cn("size-4 shrink-0", activeTab === "EHR" ? "text-sky-600" : "text-muted-foreground")} />
              <span>Thông tin sức khỏe</span>
            </button>

            {/* Tab 2 Button: SOS Contacts */}
            <button
              type="button"
              role="tab"
              aria-selected={activeTab === "SOS"}
              onClick={() => setActiveTab("SOS")}
              className={cn(
                "relative flex min-h-11 flex-1 items-center justify-center gap-2 rounded-xl px-4 text-sm font-semibold transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-sky-600 focus-visible:ring-offset-2 md:flex-none",
                activeTab === "SOS" ? "text-sky-800" : "text-slate-600 hover:text-foreground hover:bg-card/50 dark:text-slate-300"
              )}
            >
              {activeTab === "SOS" && (
                <motion.div
                  layoutId="active-profile-tab"
                  className="absolute inset-0 -z-10 rounded-xl bg-card shadow-sm"
                  transition={{ type: "spring", stiffness: 350, damping: 25 }}
                />
              )}
              <PhoneCall className={cn("size-4 shrink-0", activeTab === "SOS" ? "text-sky-600" : "text-muted-foreground")} />
              <span>Liên hệ khẩn cấp</span>
            </button>
          </div>
        </header>

        {/* =================================================================== */}
        {/* THANH BENTO CHỌN ĐỐI TƯỢNG HỒ SƠ GIA ĐÌNH (MULTI-PROFILE TABS)         */}
        {/* =================================================================== */}
        <FamilyProfilePills />

        {/* =================================================================== */}
        {/* NỘI DUNG TABS CHUYỂN HOẠT TRANG THÁI (TAB CONTENT ASSEMBLY)          */}
        {/* =================================================================== */}
        <AnimatePresence mode="wait">
          {activeTab === "EHR" ? (
            <motion.div
              key="tab-ehr-content"
              initial={{ opacity: 0, y: 12 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -12 }}
              transition={{ duration: 0.25, ease: "easeOut" }}
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
              initial={{ opacity: 0, y: 12 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -12 }}
              transition={{ duration: 0.25, ease: "easeOut" }}
              className="space-y-10"
            >
              {/* Trung Tâm Liên Hệ Khẩn Cấp SOS & PII Shield */}
              <section aria-label="Quản trị số điện thoại cấp cứu 115">
                <EmergencySosManager />
              </section>
            </motion.div>
          )}
        </AnimatePresence>

        {/* =================================================================== */}
        {/* FLOATING SAVE BAR (BAY LÊN NHẸ NHÀNG KHI PHÁT HIỆN FORM ISDIRTY)    */}
        {/* =================================================================== */}
        <AnimatePresence>
          {activeTab === "EHR" && isDirty && (
            <motion.div
              initial={{ y: 100, opacity: 0 }}
              animate={{ y: 0, opacity: 1 }}
              exit={{ y: 100, opacity: 0 }}
              transition={{ type: "spring", stiffness: 350, damping: 28 }}
              className="fixed bottom-6 left-1/2 -translate-x-1/2 z-50 w-[94%] max-w-4xl bg-card/95 backdrop-blur-2xl border border-border/90 rounded-3xl p-4 md:px-6 md:py-4 shadow-[0_20px_60px_rgba(14,165,233,0.18),0_4px_25px_rgba(0,0,0,0.06)] flex flex-col sm:flex-row sm:items-center justify-between gap-4 text-foreground"
            >
              <div className="flex items-center gap-3.5">
                <div className="flex h-11 w-11 shrink-0 items-center justify-center rounded-2xl bg-sky-50 text-sky-600 border border-sky-200 animate-pulse shadow-sm">
                  <FileText className="w-5 h-5" />
                </div>
                <div>
                  <div className="text-sm font-extrabold text-foreground">
                    Bạn có thay đổi chưa lưu
                  </div>
                  <div className="text-sm text-slate-600 hidden md:block dark:text-slate-300">
                    Nhấn Lưu thay đổi để cập nhật hồ sơ của bạn.
                  </div>
                </div>
              </div>

              <div className="flex items-center gap-3 shrink-0 self-end sm:self-center w-full sm:w-auto justify-end">
                <button
                  type="button"
                  onClick={handleReset}
                  className="h-10 px-4 rounded-xl bg-muted hover:bg-slate-200 text-slate-700 font-bold text-xs flex items-center gap-1.5 transition-all border border-slate-300/80 shadow-xs dark:text-slate-200 dark:hover:bg-slate-700 dark:border-slate-700"
                >
                  <RotateCcw className="w-3.5 h-3.5" />
                  <span>Hoàn tác</span>
                </button>

                <button
                  type="button"
                  onClick={form.handleSubmit(onSubmit)}
                  disabled={updateMutation.isPending}
                  className="h-11 rounded-xl bg-sky-600 px-6 text-sm font-bold text-white shadow-sm transition-colors hover:bg-sky-700 disabled:opacity-50"
                >
                  {updateMutation.isPending ? (
                    <RefreshCw className="w-4 h-4 animate-spin-slow stroke-[2.5]" />
                  ) : (
                    <Save className="w-4 h-4 stroke-[2.5]" />
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
