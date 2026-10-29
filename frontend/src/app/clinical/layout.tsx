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
 * [CLINICAL WORKSTATION LAYOUT]
 * ============================================================================
 * Bao bọc phân khu Lâm sàng bởi tường lửa ClinicalRoleGuard và thanh điều phối
 * ClinicalSidebar (luôn tối, ghim theo khung nhìn). Vùng nội dung đi theo chế độ
 * sáng/tối của người dùng qua token (`bg-background`, `text-foreground`).
 *
 * Cảnh báo ca khẩn toàn cục nằm trên mọi trang lâm sàng, ngay trên nội dung,
 * để một ca nguy kịch chưa ai nhận không bao giờ bị bỏ lỡ vì đang đứng ở màn khác.
 */
export default function ClinicalLayout({ children }: ClinicalLayoutProps) {
  return (
    <ClinicalRoleGuard>
      {/* Kênh thời gian thực mở ở cấp workspace, không phải trong màn hình chi
          tiết ca: nhân viên nhận được việc dù đang đứng ở bất kỳ màn hình nào. */}
      <ClinicalRealtimeProvider>
        <div className="min-h-screen w-full bg-background font-sans text-foreground lg:flex">
          {/* Thanh điều phối có nhiều liên kết: người dùng bàn phím nhảy thẳng vào nội dung. */}
          <a
            href="#clinical-main"
            className="sr-only focus:not-sr-only focus:fixed focus:left-4 focus:top-4 focus:z-50 focus:rounded-xl focus:bg-card focus:px-4 focus:py-2 focus:text-sm focus:font-bold focus:text-foreground focus:shadow-lg focus:outline-none focus:ring-2 focus:ring-brand"
          >
            Bỏ qua tới nội dung chính
          </a>
          <ClinicalSidebar />
          <div className="min-w-0 flex-1">
            <GlobalRedFlagAlert />
            <main id="clinical-main" tabIndex={-1} className="p-4 focus:outline-none sm:p-6 lg:p-8">
              <div className="mx-auto w-full max-w-6xl">{children}</div>
            </main>
          </div>
        </div>
      </ClinicalRealtimeProvider>
    </ClinicalRoleGuard>
  );
}
