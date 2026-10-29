/**
 * Cách gọi tên và nhận diện một người trong hồ sơ gia đình, dùng chung cho bộ
 * chọn người (vòng tròn chữ cái) và thẻ hồ sơ.
 */
import { isOwnProfile } from "@/components/patient/history-model";
import type { AvatarColorToken, GenderType, ProfileResponseDTO, RelationshipType } from "@/services/profile.service";

function nameParts(fullName: string): string[] {
  return fullName.trim().split(/\s+/).filter(Boolean);
}

/** Chữ cái đầu của tên gọi (từ cuối trong họ tên tiếng Việt): "Nguyễn Văn Demo" → "D". */
export function avatarInitial(fullName: string): string {
  const parts = nameParts(fullName);
  const given = parts[parts.length - 1];
  return given ? given.charAt(0).toLocaleUpperCase("vi-VN") : "?";
}

/**
 * Nhãn ngắn dưới vòng tròn: "Tôi" cho hồ sơ của chính chủ tài khoản; tên ngắn
 * ("Bé An", "Mẹ Nga") giữ nguyên; họ tên đầy đủ rút về tên gọi ("Trần Thị Hoa" → "Hoa").
 */
export function switcherLabel(profile: Pick<ProfileResponseDTO, "full_name" | "is_primary" | "relationship_type">): string {
  if (isOwnProfile(profile)) return "Tôi";
  const parts = nameParts(profile.full_name);
  if (parts.length <= 2) return parts.join(" ") || "Không tên";
  return parts[parts.length - 1];
}

const RELATION_TITLE: Record<RelationshipType, string> = {
  SELF: "Hồ sơ chính",
  CHILD: "Con",
  SPOUSE: "Vợ / chồng",
  PARENT: "Cha / mẹ",
  SIBLING: "Anh / chị / em",
  OTHER: "Người thân",
};

/** "Hồ sơ chính" cho chính chủ, quan hệ gia đình cho người thân. */
export function relationTitle(profile: Pick<ProfileResponseDTO, "is_primary" | "relationship_type">): string {
  if (isOwnProfile(profile)) return RELATION_TITLE.SELF;
  return RELATION_TITLE[profile.relationship_type] ?? RELATION_TITLE.OTHER;
}

export function genderLabel(gender: GenderType | string | null): string | null {
  if (gender === "MALE") return "nam";
  if (gender === "FEMALE") return "nữ";
  if (gender === "OTHER") return "khác";
  return null;
}

/**
 * Sắc nhận diện cho vòng tròn chưa chọn, lấy từ màu đã lưu của hồ sơ. Tông
 * "rose" được dời sang chàm: trên màn này màu hồng đỏ dành riêng cho dị ứng và
 * cảnh báo khẩn cấp, không được dùng để nhận diện một người.
 */
const AVATAR_TONE: Record<AvatarColorToken, string> = {
  emerald: "bg-emerald-100 text-emerald-900 dark:bg-emerald-950 dark:text-emerald-200",
  blue: "bg-sky-100 text-sky-900 dark:bg-sky-950 dark:text-sky-200",
  purple: "bg-violet-100 text-violet-900 dark:bg-violet-950 dark:text-violet-200",
  rose: "bg-indigo-100 text-indigo-900 dark:bg-indigo-950 dark:text-indigo-200",
  amber: "bg-amber-100 text-amber-900 dark:bg-amber-950 dark:text-amber-200",
  zinc: "bg-slate-200 text-slate-800 dark:bg-slate-800 dark:text-slate-200",
  slate: "bg-slate-200 text-slate-800 dark:bg-slate-800 dark:text-slate-200",
};

export function avatarToneClass(color: AvatarColorToken | string | null | undefined): string {
  return AVATAR_TONE[color as AvatarColorToken] ?? AVATAR_TONE.slate;
}
