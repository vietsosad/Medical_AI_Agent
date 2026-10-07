import type { HitlReviewStatus } from "@/types/clinical-history";
import type { ChatMessage } from "@/types/triage-chat";
import type { SessionStatusDTO } from "@/services/triage.service";

export type HitlUiStatus =
  | "idle"
  | "waiting_for_hitl_review"
  | "approved"
  | "overridden";

export function deriveHitlUiStatus(
  session: Pick<SessionStatusDTO, "status" | "hitl_status"> | null | undefined,
): HitlUiStatus {
  if (!session) return "idle";
  if (session.hitl_status === "OVERRIDDEN") return "overridden";
  if (session.hitl_status === "APPROVED" || session.status === "COMPLETED") {
    return "approved";
  }
  if (session.status === "HITL_REVIEWING") return "waiting_for_hitl_review";
  return "idle";
}

export function isSessionWritable(
  session: Pick<SessionStatusDTO, "status" | "is_red_flag_triggered"> | null | undefined,
): boolean {
  return Boolean(
    session &&
      session.status === "IN_PROGRESS" &&
      !session.is_red_flag_triggered,
  );
}

export function latestActionableQuestionId(messages: ChatMessage[]): string | null {
  for (let index = messages.length - 1; index >= 0; index -= 1) {
    const message = messages[index];
    if (
      message.sender !== "user" &&
      message.structured &&
      !message.structured.submitted
    ) {
      return message.id;
    }
  }
  return null;
}

export function isFinalizedSbar(
  session: Pick<SessionStatusDTO, "sbar_finalized" | "sbar_summary"> | null | undefined,
): boolean {
  return session?.sbar_finalized === true && session.sbar_summary != null;
}

export function reviewStatusLabel(status: HitlReviewStatus): string {
  if (status === "OVERRIDDEN") return "Đã được nhân viên y tế điều chỉnh";
  if (status === "APPROVED") return "Đã được nhân viên y tế xác nhận";
  if (status === "EMERGENCY_REJECTED") return "Đã chuyển sang quy trình cấp cứu";
  return "Đề xuất AI đã kiểm tra đầu ra; đang chờ nhân viên y tế thẩm định";
}
