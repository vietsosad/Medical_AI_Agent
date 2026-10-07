import React, { Suspense } from "react";
import { PatientRoleGuard } from "@/components/auth/patient-role-guard";
import { PatientRealtimeNotification } from "@/components/chat/PatientRealtimeNotification";

interface PatientLayoutProps {
  children: React.ReactNode;
}

/**
 * ============================================================================
 * [PATIENT PORTAL LAYOUT & RBAC SHIELD]
 * ============================================================================
 * Sử dụng thanh điều hướng chung ClinicalNavbar trên RootLayout để đảm bảo
 * sự thống nhất 100% khi chuyển tab và bảo đảm quyền riêng tư qua PatientRoleGuard.
 */
export default function PatientLayout({ children }: PatientLayoutProps) {
  return (
    <PatientRoleGuard>
      <Suspense fallback={null}>
        <PatientRealtimeNotification />
      </Suspense>
      <main className="flex-1 w-full max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6 sm:py-8 font-sans">
        {children}
      </main>
    </PatientRoleGuard>
  );
}
