import type {
  SbarReportDTO,
  TriageHistoryListItemDTO,
  TriageSessionDetailDTO,
  TriageSessionStatus,
} from "@/types/clinical-history";

const ACTIVE_SESSION_STATUSES = new Set<TriageSessionStatus>([
  "IN_PROGRESS",
  "HITL_REVIEWING",
]);

export function isActiveTriageSession(status: TriageSessionStatus): boolean {
  return ACTIVE_SESSION_STATUSES.has(status);
}

export function isResumableTriageSession(status: TriageSessionStatus): boolean {
  return status === "IN_PROGRESS";
}

export function getHistorySessionHref(session: TriageHistoryListItemDTO): string {
  return isActiveTriageSession(session.status)
    ? `/triage?session_id=${session.session_id}`
    : `/history/${session.session_id}`;
}

export function getTriageSessionStatusLabel(status: TriageSessionStatus): string {
  switch (status) {
    case "IN_PROGRESS":
      return "Đang thu thập";
    case "HITL_REVIEWING":
      return "Chờ thẩm định";
    case "COMPLETED":
      return "Đã hoàn tất";
    case "RED_FLAG_LOCKED":
      return "Đã chuyển cấp cứu";
    case "CANCELLED":
      return "Đã hủy";
  }
}

export function hasFinalizedSbar(
  session: TriageSessionDetailDTO,
): session is TriageSessionDetailDTO & {
  sbar_finalized: true;
  sbar_report: SbarReportDTO;
} {
  return session.sbar_finalized === true && session.sbar_report !== null;
}
