"use client";

import React from "react";
import { CheckCircle2, Droplet, Pencil, Phone, PhoneOff, Trash2, User } from "lucide-react";

import { formatVietnamPhoneForDisplay } from "@/lib/validations/account-contact.schema";
import { cn } from "@/lib/utils";
import type { ProfileResponseDTO, RelationshipType } from "@/services/profile.service";

/** Nhãn tiếng Việt cho quan hệ gia đình. */
export function formatRelation(relation: RelationshipType | string, isPrimary: boolean): string {
  if (isPrimary || relation === "SELF") return "Chính chủ";
  switch (relation) {
    case "CHILD":
      return "Con cái";
    case "SPOUSE":
      return "Vợ / Chồng";
    case "PARENT":
      return "Cha mẹ";
    case "SIBLING":
      return "Anh / Chị em";
    default:
      return "Người thân";
  }
}

function formatGender(gender: string | null): string | null {
  if (gender === "MALE") return "Nam";
  if (gender === "FEMALE") return "Nữ";
  if (gender === "OTHER") return "Khác";
  return null;
}

interface FamilyMemberCardProps {
  member: ProfileResponseDTO;
  isSelected: boolean;
  onSelect: () => void;
  onEdit: () => void;
  onDelete: (() => void) | null;
}

/**
 * ============================================================================
 * [FAMILY MEMBER CARD] THẺ THÀNH VIÊN TRONG HỒ SƠ GIA ĐÌNH
 * ============================================================================
 * Một thẻ = một người: danh tính, chỉ số cơ bản, số liên lạc riêng và hành động.
 * Màu teal/sky cho hành động lâm sàng, emerald cho trạng thái tốt, rose chỉ dành
 * cho hành động phá hủy (xóa hồ sơ).
 */
export function FamilyMemberCard({
  member,
  isSelected,
  onSelect,
  onEdit,
  onDelete,
}: FamilyMemberCardProps) {
  const relationTitle = formatRelation(member.relationship_type, member.is_primary);
  const genderLabel = formatGender(member.gender);
  const metaParts = [
    member.age !== null && member.age !== undefined ? `${member.age} tuổi` : null,
    genderLabel,
    member.blood_type && member.blood_type !== "UNKNOWN" ? member.blood_type : null,
  ].filter(Boolean) as string[];

  return (
    <article
      onClick={onSelect}
      aria-current={isSelected ? "true" : undefined}
      className={cn(
        "group relative flex cursor-pointer flex-col rounded-2xl border bg-card p-5 shadow-xs transition-all duration-200",
        isSelected
          ? "border-teal-500 ring-2 ring-teal-500/15"
          : "border-border hover:border-teal-300 hover:shadow-md",
      )}
    >
      <header className="flex items-start justify-between gap-3">
        <div className="flex min-w-0 items-center gap-3">
          <span
            className={cn(
              "flex size-11 shrink-0 items-center justify-center rounded-xl text-base font-bold",
              member.is_primary
                ? "bg-teal-600 text-white"
                : "bg-muted text-slate-700 dark:text-slate-200",
            )}
            aria-hidden="true"
          >
            {member.full_name?.charAt(0)?.toUpperCase() || <User className="size-5" />}
          </span>

          <div className="min-w-0">
            <h3 className="truncate text-base font-bold tracking-tight text-foreground">
              {member.full_name}
            </h3>
            <span
              className={cn(
                "mt-0.5 inline-block rounded-md px-2 py-0.5 text-xs font-semibold",
                member.is_primary
                  ? "bg-teal-50 text-teal-800"
                  : "bg-muted text-slate-600 dark:text-slate-300",
              )}
            >
              {relationTitle}
            </span>
          </div>
        </div>

        {isSelected && (
          <CheckCircle2
            className="size-5 shrink-0 text-teal-600"
            aria-label="Hồ sơ đang được chọn"
          />
        )}
      </header>

      {metaParts.length > 0 && (
        <p className="mt-3 flex flex-wrap items-center gap-x-2 gap-y-1 text-sm text-slate-600 dark:text-slate-300">
          {metaParts.map((part, index) => (
            <React.Fragment key={part}>
              {index > 0 && <span aria-hidden="true" className="text-slate-300">·</span>}
              <span className={part === member.blood_type ? "inline-flex items-center gap-1" : undefined}>
                {part === member.blood_type && (
                  <Droplet className="size-3.5 shrink-0 text-rose-500" aria-hidden="true" />
                )}
                {part}
              </span>
            </React.Fragment>
          ))}
        </p>
      )}

      {/* Số liên lạc riêng của thành viên này */}
      <div className="mt-3">
        {member.phone_number ? (
          <a
            href={`tel:${member.phone_number}`}
            onClick={(event) => event.stopPropagation()}
            className="inline-flex min-h-11 items-center gap-2 rounded-xl border border-slate-200 bg-background px-3 text-sm font-semibold text-slate-800 transition-colors hover:border-teal-300 hover:bg-teal-50 hover:text-teal-900 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-teal-600"
          >
            <Phone className="size-4 shrink-0 text-teal-600" aria-hidden="true" />
            {formatVietnamPhoneForDisplay(member.phone_number)}
          </a>
        ) : (
          <button
            type="button"
            onClick={(event) => {
              event.stopPropagation();
              onEdit();
            }}
            className="inline-flex min-h-11 items-center gap-2 rounded-xl border border-dashed border-slate-300 bg-card px-3 text-sm font-medium text-muted-foreground transition-colors hover:border-teal-400 hover:text-teal-800 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-teal-600 dark:border-slate-700"
          >
            <PhoneOff className="size-4 shrink-0" aria-hidden="true" />
            Chưa cập nhật — Thêm số điện thoại
          </button>
        )}
      </div>

      <div className="mt-4 space-y-1.5 border-t border-slate-100 pt-3">
        <span className="text-xs font-bold uppercase tracking-wide text-muted-foreground">
          Tiền sử ghi nhận
        </span>
        {member.chronic_conditions && member.chronic_conditions.length > 0 ? (
          <ul className="flex flex-wrap gap-1.5">
            {member.chronic_conditions.slice(0, 3).map((condition) => (
              <li
                key={condition}
                className="rounded-lg border border-amber-200 bg-amber-50 px-2 py-1 text-xs font-medium text-amber-900"
              >
                {condition}
              </li>
            ))}
          </ul>
        ) : (
          <p className="text-xs font-medium text-emerald-700">Chưa ghi nhận bệnh mạn tính</p>
        )}
      </div>

      <div className="mt-4 flex items-center gap-2 border-t border-slate-100 pt-3">
        <button
          type="button"
          onClick={(event) => {
            event.stopPropagation();
            onEdit();
          }}
          aria-label={`Chỉnh sửa hồ sơ ${member.full_name}`}
          className="flex min-h-11 flex-1 items-center justify-center gap-1.5 rounded-xl border border-slate-300 bg-card px-3 text-sm font-semibold text-slate-700 transition-colors hover:bg-background focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-slate-500 dark:text-slate-200 dark:border-slate-700"
        >
          <Pencil className="size-4 shrink-0" aria-hidden="true" />
          Chỉnh sửa
        </button>

        {onDelete && (
          <button
            type="button"
            onClick={(event) => {
              event.stopPropagation();
              onDelete();
            }}
            aria-label={`Xóa hồ sơ ${member.full_name}`}
            className="flex size-11 shrink-0 items-center justify-center rounded-xl border border-rose-200 bg-card text-rose-600 transition-colors hover:bg-rose-50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-rose-600"
          >
            <Trash2 className="size-4" aria-hidden="true" />
          </button>
        )}
      </div>
    </article>
  );
}

export default FamilyMemberCard;
