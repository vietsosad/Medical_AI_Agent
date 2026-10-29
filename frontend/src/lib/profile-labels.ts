/**
 * Tên tiếng Việt cho các mã hồ sơ máy chủ trả về (`relationship_type`,
 * `gender`). Mã lạ trả về null để nơi gọi tự bỏ qua, không in mã thô ra màn hình.
 */

const RELATION_LABELS: Record<string, string> = {
  SELF: "Chính chủ",
  CHILD: "Con",
  PARENT: "Cha mẹ",
  SPOUSE: "Vợ hoặc chồng",
  SIBLING: "Anh chị em",
  OTHER: "Người thân",
};

const GENDER_LABELS: Record<string, string> = {
  MALE: "Nam",
  FEMALE: "Nữ",
  OTHER: "Khác",
};

export function relationLabel(code: string | null | undefined, isPrimary = false): string | null {
  if (isPrimary) return RELATION_LABELS.SELF;
  return code ? (RELATION_LABELS[code.toUpperCase()] ?? null) : null;
}

export function genderLabel(code: string | null | undefined): string | null {
  return code ? (GENDER_LABELS[code.toUpperCase()] ?? null) : null;
}
