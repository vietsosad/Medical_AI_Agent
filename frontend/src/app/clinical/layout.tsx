import React from "react";
import { ClinicalRoleGuard } from "@/components/auth/clinical-role-guard";
import { ClinicalRealtimeProvider } from "@/components/clinical/ClinicalRealtimeProvider";
import { ClinicalSidebar } from "@/components/clinical/ClinicalSidebar";
import { GlobalRedFlagAlert } from "@/components/clinical/nurse/GlobalRedFlagAlert";

interface ClinicalLayoutProps {
  children: React.ReactNode;
}

/**
 * ============================================================================
 * [CLINICAL ER WORKSTATION LAYOUT - PRISTINE DAY MEDICAL BRIGHT THEME]
 * ============================================================================
 * Bao bọc phân khu Lâm sàng bởi tường lửa ClinicalRoleGuard và thanh điều hướng dọc
 * ClinicalSidebar. Tuân thủ tuyệt đối giao diện sáng (Pristine Day Medical Theme -
 * bg-slate-50 text-slate-900), mang lại độ minh bạch và rõ ràng tối đa cho nhân viên lâm sàng.
 */
export default function ClinicalLayout({ children }: ClinicalLayoutProps) {
  return (
    <ClinicalRoleGuard>
      {/* Kênh thời gian thực mở ở cấp workspace, không phải trong màn hình chi
          tiết ca: nhân viên nhận được việc dù đang đứng ở bất kỳ màn hình nào. */}
      <ClinicalRealtimeProvider>
        <div className="min-h-screen w-full bg-background font-sans text-slate-950 lg:flex dark:text-slate-50">
          <ClinicalSidebar />
          <div className="min-w-0 flex-1">
            <GlobalRedFlagAlert />
            <main className="p-4 sm:p-6 lg:p-8">
              <div className="mx-auto w-full max-w-6xl">
                {children}
              </div>
            </main>
          </div>
        </div>
      </ClinicalRealtimeProvider>
    </ClinicalRoleGuard>
  );
}
