import { nurseQueueHref } from "@/lib/agent-mode";
import type { UserRole } from "@/store/useAuthStore";

const HOME_ROUTE_BY_ROLE = {
  CLINICAL_NURSE: "/clinical/queue",
  SYSTEM_ADMIN: "/admin",
  AI_OPS: "/admin",
  PATIENT: "/",
  GUEST: "/triage",
} satisfies Record<UserRole, string>;

/**
 * Return a trusted internal destination after authentication.
 *
 * `CLINICAL_NURSE` is special-cased through `nurseQueueHref()` instead of
 * `HOME_ROUTE_BY_ROLE` directly, so every caller (login, OAuth callback,
 * role-home-redirect, patient-role-guard, guest-guard) automatically lands a
 * nurse on the pilot queue when NEXT_PUBLIC_TRIAGE_PILOT_ACTIVE="YES" without
 * each call site needing its own check. `GUEST`/`PATIENT` stay untouched --
 * simple_agent has no anonymous/guest flow equivalent.
 */
export function getHomeRouteForRole(role: UserRole): string {
  if (role === "CLINICAL_NURSE") return nurseQueueHref();
  return HOME_ROUTE_BY_ROLE[role];
}

/**
 * Điểm đến cho các CTA công khai trỏ vào chức năng của bệnh nhân.
 *
 * Các tuyến `/triage`, `/history`, `/profile` đều yêu cầu phiên đăng nhập, nên
 * khách chưa đăng nhập được đưa thẳng vào luồng đăng nhập hiện có thay vì bị
 * PatientRoleGuard đẩy ngược lại sau một nhịp chờ.
 */
export function patientEntryHref(href: string, isAuthenticated: boolean): string {
  return isAuthenticated ? href : "/auth/login";
}
