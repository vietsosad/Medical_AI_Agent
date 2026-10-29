/**
 * Quy tắc hiển thị dùng chung cho màn "Lịch sử sàng lọc" và màn chi tiết một
 * phiên. Tách khỏi component để kiểm thử được bằng dữ liệu thuần, và để hai
 * màn không bao giờ hiểu cùng một phiên theo hai cách khác nhau.
 */
import { pilotAiProposedEsi } from "@/components/chat/SimplePilotNurseDecisionSummary";
import type { ProfileResponseDTO, RelationshipType } from "@/services/profile.service";
import type { SimpleTriageSessionSummaryDTO } from "@/types/simple-triage";

type Session = SimpleTriageSessionSummaryDTO;

/** Bộ lọc chính của danh sách, khớp ba nút trên thiết kế. */
export type HistorySegment = "ALL" | "PENDING" | "CONFIRMED";

/**
 * Bộ lọc phụ chỉ hiện dưới "Đã xác nhận": giữ lại hai lựa chọn của bộ lọc cũ
 * ("Điều dưỡng đã duyệt" và "Có can thiệp") mà ba nút chính không phân biệt.
 */
export type ConfirmedKind = "ALL" | "APPROVED" | "OVERRIDDEN";

/**
 * Trạng thái một phiên theo góc nhìn người bệnh.
 *
 * `review_display_status` của máy chủ là PENDING_REVIEW cho mọi phiên chưa có
 * quyết định, kể cả phiên đang hỏi dở. Phiên đang hỏi dở chưa hề vào hàng đợi
 * của điều dưỡng, nên gọi nó là "chờ điều dưỡng xác nhận" là nói sai.
 */
export type SessionStatusKind = "IN_PROGRESS" | "STOPPED" | "AWAITING_NURSE" | "CONFIRMED" | "ADJUSTED";

export function hasNurseDecision(session: Pick<Session, "review_display_status">): boolean {
  return session.review_display_status === "APPROVED" || session.review_display_status === "OVERRIDDEN";
}

function validEsi(level: number | null | undefined): number | null {
  return level != null && Number.isInteger(level) && level >= 1 && level <= 5 ? level : null;
}

/** Mức AI đề xuất: mức nặng nhất trong các mức đã khớp, hoặc null. */
export function aiProposedEsiOf(session: Pick<Session, "matched_esi_levels">): number | null {
  return pilotAiProposedEsi(session.matched_esi_levels);
}

/**
 * Mức hiển thị trên ô ESI: mức điều dưỡng đã chốt nếu có quyết định, nếu không
 * thì mức AI đề xuất. Null nghĩa là chưa có mức nào, ô hiển thị "?".
 */
export function displayedEsiOf(
  session: Pick<Session, "review_display_status" | "final_esi" | "matched_esi_levels">,
): number | null {
  const finalEsi = validEsi(session.final_esi);
  if (hasNurseDecision(session) && finalEsi !== null) return finalEsi;
  return aiProposedEsiOf(session);
}

export function sessionStatusKind(session: Pick<Session, "status" | "review_display_status">): SessionStatusKind {
  if (session.status === "ACTIVE") return "IN_PROGRESS";
  if (session.review_display_status === "OVERRIDDEN") return "ADJUSTED";
  if (session.review_display_status === "APPROVED") return "CONFIRMED";
  if (session.status === "ABANDONED") return "STOPPED";
  return "AWAITING_NURSE";
}

export function matchesSegment(session: Session, segment: HistorySegment, confirmedKind: ConfirmedKind): boolean {
  const kind = sessionStatusKind(session);
  switch (segment) {
    case "ALL":
      return true;
    case "PENDING":
      return kind === "AWAITING_NURSE";
    case "CONFIRMED":
      if (confirmedKind === "APPROVED") return kind === "CONFIRMED";
      if (confirmedKind === "OVERRIDDEN") return kind === "ADJUSTED";
      return kind === "CONFIRMED" || kind === "ADJUSTED";
    default:
      return true;
  }
}

/** Nhãn quan hệ viết thường, dùng giữa câu: "Trần Thị Hoa · cha/mẹ". */
const RELATION_SHORT: Record<RelationshipType, string> = {
  SELF: "bản thân",
  CHILD: "con",
  SPOUSE: "vợ/chồng",
  PARENT: "cha/mẹ",
  SIBLING: "anh/chị/em",
  OTHER: "người thân",
};

export function relationShortLabel(relation: RelationshipType | string): string {
  return RELATION_SHORT[relation as RelationshipType] ?? "người thân";
}

export function isOwnProfile(profile: Pick<ProfileResponseDTO, "is_primary" | "relationship_type">): boolean {
  return profile.is_primary || profile.relationship_type === "SELF";
}

export interface SubjectLabel {
  /** "Bạn", họ tên người thân, "Ẩn danh"... */
  name: string;
  /** Quan hệ với chủ tài khoản, chỉ có với hồ sơ người thân. */
  relation: string | null;
}

/**
 * Phiên này được sàng lọc cho ai. `profiles` còn đang tải thì trả null để giao
 * diện bỏ trống chỗ đó thay vì tạm ghi một cái tên sai.
 */
export function subjectLabelFor(
  profileId: string | null,
  profiles: ProfileResponseDTO[] | undefined,
): SubjectLabel | null {
  if (profileId === null) return { name: "Ẩn danh", relation: null };
  if (!profiles) return null;
  const profile = profiles.find((item) => item.id === profileId);
  if (!profile) return { name: "Hồ sơ đã xóa", relation: null };
  if (isOwnProfile(profile)) return { name: "Bạn", relation: null };
  return { name: profile.full_name, relation: relationShortLabel(profile.relationship_type) };
}

export function formatSubject(subject: SubjectLabel | null): string | null {
  if (!subject) return null;
  return subject.relation ? `${subject.name} · ${subject.relation}` : subject.name;
}

export function parseDate(value: string | null | undefined): Date | null {
  if (!value) return null;
  const parsed = new Date(value);
  return Number.isNaN(parsed.getTime()) ? null : parsed;
}

/** Thời điểm xếp nhóm và hiển thị: lần hoạt động gần nhất, đúng thứ tự máy chủ trả về. */
export function activityDateOf(session: Pick<Session, "last_activity_at" | "started_at">): Date | null {
  return parseDate(session.last_activity_at) ?? parseDate(session.started_at);
}

export function formatClock(date: Date): string {
  return date.toLocaleTimeString("vi-VN", { hour: "2-digit", minute: "2-digit" });
}

/** "29/10/2026 lúc 10:29": ngày trước, giờ sau, như cách nói thường ngày. */
export function formatDateTime(date: Date): string {
  const day = date.toLocaleDateString("vi-VN", { day: "2-digit", month: "2-digit", year: "numeric" });
  return `${day} lúc ${formatClock(date)}`;
}

function dayKey(date: Date): string {
  return `${date.getFullYear()}-${date.getMonth() + 1}-${date.getDate()}`;
}

export function dayLabel(date: Date, now: Date): string {
  const today = new Date(now.getFullYear(), now.getMonth(), now.getDate());
  const target = new Date(date.getFullYear(), date.getMonth(), date.getDate());
  const diffDays = Math.round((today.getTime() - target.getTime()) / 86_400_000);
  if (diffDays === 0) return "Hôm nay";
  if (diffDays === 1) return "Hôm qua";
  return date.toLocaleDateString("vi-VN", {
    weekday: "long",
    day: "2-digit",
    month: "2-digit",
    ...(date.getFullYear() === now.getFullYear() ? {} : { year: "numeric" }),
  });
}

export interface DayGroup<T> {
  key: string;
  label: string;
  items: T[];
}

/**
 * Nhóm theo ngày, giữ nguyên thứ tự đầu vào (máy chủ đã xếp mới nhất trước).
 * Mục không đọc được ngày dồn vào một nhóm riêng ở cuối thay vì biến mất.
 */
export function groupByDay<T>(items: T[], getDate: (item: T) => Date | null, now: Date): DayGroup<T>[] {
  const groups = new Map<string, DayGroup<T>>();
  const undated: T[] = [];
  for (const item of items) {
    const date = getDate(item);
    if (!date) {
      undated.push(item);
      continue;
    }
    const key = dayKey(date);
    const group = groups.get(key);
    if (group) group.items.push(item);
    else groups.set(key, { key, label: dayLabel(date, now), items: [item] });
  }
  const result = [...groups.values()];
  if (undated.length > 0) result.push({ key: "undated", label: "Không rõ thời gian", items: undated });
  return result;
}
