import type { Metadata } from "next";
import { ClinicalProfileDashboard } from "@/components/profile/ClinicalProfileDashboard";

/**
 * ============================================================================
 * NEXT.JS SERVER COMPONENT BOUNDARY - PATIENT HEALTH PROFILE PAGE
 * ============================================================================
 * Trang hồ sơ sức khỏe và liên hệ khẩn cấp của người dùng.
 */

export const metadata: Metadata = {
  title: "Hồ sơ sức khỏe | AI Triage",
  description:
    "Lưu và cập nhật thông tin sức khỏe, dị ứng, thuốc đang dùng và người liên hệ khẩn cấp.",
  keywords: [
    "Hồ sơ sức khỏe",
    "Thông tin sức khỏe",
    "Liên hệ khẩn cấp",
  ],
};

export default function ClinicalProfileEhrPage() {
  return (
    <main className="min-h-screen bg-background px-4 py-8 text-slate-800 selection:bg-sky-500/20 selection:text-sky-900 md:px-8 lg:px-12 dark:text-slate-100">
      <div className="mx-auto max-w-7xl">
        <ClinicalProfileDashboard />
      </div>
    </main>
  );
}
