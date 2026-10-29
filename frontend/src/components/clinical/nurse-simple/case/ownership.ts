import type { SimpleClaimPayload, SimpleNurseCaseDetailDTO } from "@/types/simple-nurse";

/**
 * Ai đang giữ ca, đọc từ `review_status` + `assigned_nurse_id`. Một ca tạm gác
 * luôn có người giữ (PARK tự nhận ca cho người gác, xem `claim_simple_case`).
 */
export type Ownership = "closed" | "parked-mine" | "parked-other" | "mine" | "other" | "open";

export type ClaimAction = SimpleClaimPayload["action"];

export interface ClaimActionOptions {
  reason?: string;
  onSuccess?: () => void;
}

export function ownershipOf(data: SimpleNurseCaseDetailDTO, currentUserId: string | undefined): Ownership {
  const mine = Boolean(data.assigned_nurse_id) && data.assigned_nurse_id === currentUserId;
  if (data.review_status === "HANDED_OFF") return "closed";
  if (data.review_status === "PARKED") return mine ? "parked-mine" : "parked-other";
  if (mine) return "mine";
  if (data.assigned_nurse_id) return "other";
  return "open";
}

/** Người khác đang giữ ca, kể cả khi ca đã đóng -- khi đó kênh nhắn tin là của họ. */
export function isOwnedByOther(data: SimpleNurseCaseDetailDTO, currentUserId: string | undefined): boolean {
  return Boolean(data.assigned_nurse_id) && data.assigned_nurse_id !== currentUserId;
}
