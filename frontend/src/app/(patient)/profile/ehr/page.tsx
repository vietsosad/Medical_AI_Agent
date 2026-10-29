import type { Metadata } from "next";
import { ClinicalProfileDashboard } from "@/components/profile/ClinicalProfileDashboard";

/**
 * ============================================================================
 * NEXT.JS SERVER COMPONENT BOUNDARY - PATIENT HEALTH PROFILE PAGE
 * ============================================================================
 * Trang hồ sơ sức khỏe và liên hệ khẩn cấp của người dùng. Layout nhóm
 * (patient) đã có thẻ <main> và lề trang, nên ở đây chỉ là một khối bao.
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
    <div className="w-full text-foreground">
      <ClinicalProfileDashboard />
    </div>
  );
}
