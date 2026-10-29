"use client";

import Link from "next/link";
import { motion, type Variants } from "framer-motion";
import { ChevronRight, FileHeart, Pencil, Plus, Trash2, TriangleAlert } from "lucide-react";

import { genderLabel, relationTitle } from "@/components/patient/family-identity";
import { formatVietnamPhoneForDisplay } from "@/lib/validations/account-contact.schema";
import { enterTransition, staggerDelay } from "@/lib/motion";
import type { ProfileResponseDTO } from "@/services/profile.service";

interface FamilyMemberCardProps {
  member: ProfileResponseDTO;
  /** id gắn vào tiêu đề tên, để vùng bao ngoài trỏ aria-labelledby về đây. */
  headingId: string;
  onEdit: () => void;
  /** Null với hồ sơ của chính chủ tài khoản: hồ sơ đó không xóa được. */
  onDelete: (() => void) | null;
}

/** Các chip nổi lên lần lượt sau khi thẻ đã hiện, theo thứ tự đọc. */
const chipVariants: Variants = {
  hidden: { opacity: 0, y: 8 },
  visible: (index: number) => ({
    opacity: 1,
    y: 0,
    transition: { ...enterTransition, delay: 0.12 + staggerDelay(index) },
  }),
};

function uniqueValues(values: string[] | null | undefined): string[] {
  return Array.from(new Set((values ?? []).map((value) => value.trim()).filter(Boolean)));
}

/**
 * ============================================================================
 * [FAMILY MEMBER CARD] THẺ HỒ SƠ CỦA NGƯỜI ĐANG ĐƯỢC CHỌN
 * ============================================================================
 * Đúng những gì điều dưỡng thấy khi nhận một ca sàng lọc của người này: tên,
 * quan hệ, tuổi, giới, nhóm máu, số liên lạc, bệnh nền và dị ứng. Dị ứng mang
 * màu hồng đỏ kèm biểu tượng cảnh báo; "chưa ghi nhận" luôn để trung tính vì
 * chưa khai báo không có nghĩa là không có.
 */
export function FamilyMemberCard({ member, headingId, onEdit, onDelete }: FamilyMemberCardProps) {
  const meta = [relationTitle(member), genderLabel(member.gender), member.age != null ? `${member.age} tuổi` : null]
    .filter(Boolean)
    .join(" · ");
  const bloodType = member.blood_type && member.blood_type !== "UNKNOWN" ? member.blood_type : null;
  const conditions = uniqueValues(member.chronic_conditions);
  const allergies = uniqueValues(member.allergies);

  return (
    <section aria-labelledby={headingId} className="rounded-3xl border border-border bg-card p-4 shadow-xs sm:p-6">
      <div className="flex items-start justify-between gap-4">
        <div className="min-w-0">
          <h2 id={headingId} className="truncate text-xl font-extrabold tracking-tight text-foreground">
            {member.full_name}
          </h2>
          {meta && <p className="text-sm leading-6 text-muted-foreground">{meta}</p>}
        </div>
        <button
          type="button"
          onClick={onEdit}
          aria-label={`Sửa hồ sơ của ${member.full_name}`}
          className="flex size-11 shrink-0 items-center justify-center rounded-xl border border-border bg-card text-foreground transition duration-[180ms] hover:bg-muted focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand focus-visible:ring-offset-2 focus-visible:ring-offset-card active:scale-[0.97] motion-reduce:transition-none motion-reduce:active:scale-100"
        >
          <Pencil className="size-4" aria-hidden="true" />
        </button>
      </div>

      <dl className="mt-4 grid grid-cols-2 gap-2">
        <div className="rounded-2xl bg-muted/70 px-4 py-2">
          <dt className="text-sm font-semibold text-muted-foreground">Nhóm máu</dt>
          <dd className="flex min-h-11 items-center">
            {bloodType ? (
              <span className="text-lg font-extrabold text-foreground">{bloodType}</span>
            ) : (
              <span className="text-base font-semibold text-muted-foreground">Chưa rõ</span>
            )}
          </dd>
        </div>
        <div className="min-w-0 rounded-2xl bg-muted/70 px-4 py-2">
          <dt className="text-sm font-semibold text-muted-foreground">Điện thoại</dt>
          <dd className="flex min-h-11 items-center">
            {member.phone_number ? (
              <a
                href={`tel:${member.phone_number}`}
                className="truncate rounded-lg text-base font-bold text-foreground underline-offset-4 hover:text-brand hover:underline focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand"
              >
                {formatVietnamPhoneForDisplay(member.phone_number)}
              </a>
            ) : (
              <button
                type="button"
                onClick={onEdit}
                className="inline-flex min-h-11 items-center gap-2 rounded-lg text-sm font-semibold text-brand hover:text-brand-strong focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand"
              >
                <Plus className="size-4" aria-hidden="true" />
                Thêm số
              </button>
            )}
          </dd>
        </div>
      </dl>

      <div className="mt-6 space-y-4">
        <div>
          <h3 className="text-sm font-bold text-muted-foreground">Bệnh nền</h3>
          {conditions.length > 0 ? (
            <ul className="mt-2 flex flex-wrap gap-2">
              {conditions.map((condition, index) => (
                <motion.li
                  key={condition}
                  custom={index}
                  variants={chipVariants}
                  initial="hidden"
                  animate="visible"
                  className="rounded-full border border-border bg-muted px-4 text-sm font-semibold leading-8 text-foreground"
                >
                  {condition}
                </motion.li>
              ))}
            </ul>
          ) : (
            <p className="mt-2 text-sm leading-6 text-muted-foreground">Chưa ghi nhận bệnh nền.</p>
          )}
        </div>

        <div>
          <h3 className="text-sm font-bold text-muted-foreground">Dị ứng</h3>
          {allergies.length > 0 ? (
            <ul className="mt-2 flex flex-wrap gap-2">
              {allergies.map((allergy, index) => (
                <motion.li
                  key={allergy}
                  custom={conditions.length + index}
                  variants={chipVariants}
                  initial="hidden"
                  animate="visible"
                  className="inline-flex items-center gap-2 rounded-full border border-rose-200 bg-rose-50 px-4 text-sm font-bold leading-8 text-rose-900 dark:border-rose-900 dark:bg-rose-950/50 dark:text-rose-100"
                >
                  <TriangleAlert className="size-4 shrink-0" aria-hidden="true" />
                  <span className="sr-only">Dị ứng: </span>
                  {allergy}
                </motion.li>
              ))}
            </ul>
          ) : (
            <p className="mt-2 text-sm leading-6 text-muted-foreground">Chưa ghi nhận dị ứng.</p>
          )}
        </div>
      </div>

      {/* Lối vào chính của hồ sơ: chiều cao, cân nặng, BMI, bệnh nền, dị ứng và thuốc
          được khai báo ở /profile/ehr cho đúng người đang chọn (cùng activeProfileId).
          Từng chỉ là một dòng chữ nhỏ và người bệnh bỏ sót, nên giờ là nút đặc màu chủ
          đạo, nói rõ bên trong có gì. */}
      <Link
        href="/profile/ehr"
        className="group mt-6 flex min-h-16 items-center gap-4 rounded-2xl bg-brand px-4 py-3 text-brand-foreground shadow-[0_14px_28px_-18px_rgba(15,118,110,0.9)] transition duration-200 hover:bg-brand-strong focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand focus-visible:ring-offset-2 focus-visible:ring-offset-card active:scale-[0.99] motion-reduce:transition-none motion-reduce:active:scale-100"
      >
        <span className="flex size-11 shrink-0 items-center justify-center rounded-xl bg-brand-foreground/15">
          <FileHeart className="size-[22px]" strokeWidth={2.2} aria-hidden="true" />
        </span>
        <span className="min-w-0 flex-1">
          <span className="block text-base font-extrabold leading-6 text-balance">
            Cập nhật <span className="whitespace-nowrap">hồ sơ</span> <span className="whitespace-nowrap">sức khỏe</span>
          </span>
          <span className="block text-sm leading-5 text-pretty text-brand-foreground/90">
            {/* Từ ghép nối bằng dấu cách không ngắt, để chỉ xuống dòng sau dấu phẩy. */}
            {"Chiều cao, cân nặng, BMI, bệnh nền, dị ứng, thuốc"}
          </span>
        </span>
        <ChevronRight
          className="size-5 shrink-0 transition-transform duration-200 group-hover:translate-x-1 motion-reduce:transition-none motion-reduce:group-hover:translate-x-0"
          aria-hidden="true"
        />
      </Link>

      {onDelete && (
        <div className="mt-2 flex justify-end">
          <button
            type="button"
            onClick={onDelete}
            className="inline-flex min-h-11 items-center gap-2 rounded-xl px-2 text-sm font-semibold text-rose-700 transition-colors hover:bg-rose-50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-rose-600 dark:text-rose-300 dark:hover:bg-rose-950/40"
          >
            <Trash2 className="size-4" aria-hidden="true" />
            Xóa hồ sơ
          </button>
        </div>
      )}
    </section>
  );
}

export default FamilyMemberCard;
