"use client";

import { AlertTriangle, Droplet, Mail, Phone, ShieldAlert, UserRound, Users } from "lucide-react";

import type { SimpleNursePatientContactDTO } from "@/types/simple-nurse";

/**
 * Khối "gọi cho ai" trong màn thẩm định ca.
 *
 * Trước đây màn này chỉ có hội thoại với AI và phiếu SBAR, nên điều dưỡng đọc
 * xong vẫn không biết liên lạc với ai -- đúng phần còn thiếu so với quy trình
 * y tế chuẩn. Dữ liệu lấy từ khối `patient` của
 * `GET /nurse-simple/cases/{id}` (xem `_patient_contact_block`).
 *
 * Tách bạch có chủ đích giữa hai danh tính:
 * - "Người được khám" là thẻ hồ sơ đã chọn lúc bắt đầu phiên, có thể là trẻ
 *   nhỏ hoặc người thân không tự nghe máy được.
 * - "Chủ tài khoản" là người thực sự đã ngồi gõ và cầm máy.
 * Gộp hai thứ này lại sẽ dẫn tới gọi nhầm người trong tình huống cần gấp.
 */

const RELATIONSHIP_LABELS: Record<string, string> = {
  SELF: "Chính chủ tài khoản",
  CHILD: "Con của chủ tài khoản",
  SPOUSE: "Vợ / chồng của chủ tài khoản",
  PARENT: "Cha / mẹ của chủ tài khoản",
  SIBLING: "Anh / chị / em của chủ tài khoản",
  OTHER: "Người thân của chủ tài khoản",
};

function relationshipLabel(value: string): string {
  return RELATIONSHIP_LABELS[value] ?? value;
}

function genderLabel(value: string | null): string | null {
  if (!value) return null;
  const normalized = value.trim().toUpperCase();
  if (normalized === "MALE") return "Nam";
  if (normalized === "FEMALE") return "Nữ";
  if (normalized === "OTHER") return "Khác";
  return value;
}

/** Số điện thoại bấm gọi được; giữ nguyên chữ số hiển thị cho điều dưỡng đọc/ghi lại. */
function PhoneLink({ value }: { value: string }) {
  return (
    <a
      href={`tel:${value.replace(/\s+/g, "")}`}
      className="glow-soft glow-sky inline-flex min-h-9 items-center gap-1.5 rounded-lg border border-sky-200 bg-sky-50 px-2.5 font-mono text-sm font-bold tabular-nums text-sky-900 hover:bg-sky-100 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-sky-600"
    >
      <Phone className="size-3.5 shrink-0" aria-hidden="true" />
      {value}
    </a>
  );
}

function EmailLink({ value }: { value: string }) {
  return (
    <a
      href={`mailto:${value}`}
      className="glow-soft glow-sky inline-flex min-h-9 min-w-0 items-center gap-1.5 rounded-lg border border-border bg-background px-2.5 text-sm font-semibold text-slate-800 hover:bg-muted focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-sky-600 dark:text-slate-100"
    >
      <Mail className="size-3.5 shrink-0" aria-hidden="true" />
      <span className="truncate">{value}</span>
    </a>
  );
}

function MissingValue({ label }: { label: string }) {
  return <span className="text-sm font-medium italic text-muted-foreground">{label}</span>;
}

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="min-w-0">
      <dt className="text-xs font-bold uppercase tracking-wide text-muted-foreground">{label}</dt>
      <dd className="mt-1 min-w-0 break-words text-sm font-semibold text-foreground">{children}</dd>
    </div>
  );
}

export function SimplePatientContactPanel({ patient }: { patient: SimpleNursePatientContactDTO }) {
  const { account, profile } = patient;
  const subjectIsAccountHolder = profile !== null && profile.relationship_type === "SELF";
  const gender = profile ? genderLabel(profile.gender) : null;

  return (
    <section className="group/contact glow-soft glow-sky rise-in overflow-hidden rounded-2xl border border-border bg-card shadow-xs">
      {/* Đầu khối dùng chung ngôn ngữ với các panel khác của màn thẩm định ca */}
      <header className="flex items-start gap-3 border-b border-slate-100 bg-background/70 px-4 py-3.5 sm:px-5">
        <span className="flex size-9 shrink-0 items-center justify-center rounded-xl bg-card text-sky-700 shadow-xs transition-[background-color,color] duration-300 group-hover/contact:bg-sky-700 group-hover/contact:text-white">
          <UserRound className="size-4.5" aria-hidden="true" />
        </span>
        <div className="min-w-0">
          <h2 className="text-base font-bold text-slate-950 dark:text-slate-50">Thông tin người bệnh &amp; đường liên lạc</h2>
          <p className="mt-0.5 text-sm text-slate-600 dark:text-slate-300">Xác định gọi cho ai trước khi xử lý ca</p>
        </div>
      </header>

      <div className="space-y-4 p-4 sm:p-5">

      {/* NGƯỜI ĐƯỢC KHÁM */}
      {profile === null ? (
        <div className="flex items-start gap-3 rounded-xl border border-amber-200 bg-amber-50 p-4 text-sm leading-6 text-amber-950">
          <ShieldAlert className="mt-0.5 size-5 shrink-0" aria-hidden="true" />
          <p>
            Phiên ẩn danh: người bệnh không gắn thẻ hồ sơ nào khi bắt đầu, nên hệ thống không có
            nhân khẩu học của người được khám. Hãy liên lạc qua thông tin tài khoản bên dưới và xác
            minh lại danh tính trực tiếp.
          </p>
        </div>
      ) : (
        <div className="rounded-xl border border-sky-200 bg-sky-50/60 p-4">
          <div className="flex flex-wrap items-center gap-x-3 gap-y-2">
            <span className="text-lg font-black tracking-tight text-slate-950 dark:text-slate-50">{profile.full_name}</span>
            <span className="rounded-lg border border-sky-300 bg-card px-2.5 py-0.5 text-xs font-bold uppercase tracking-wide text-sky-900">
              {relationshipLabel(profile.relationship_type)}
            </span>
          </div>

          <dl className="mt-4 grid grid-cols-1 gap-4 sm:grid-cols-3">
            <Field label="Tuổi / giới tính">
              {profile.age !== null || gender ? (
                <>
                  {profile.age !== null ? `${profile.age} tuổi` : "Chưa rõ tuổi"}
                  {gender ? ` · ${gender}` : ""}
                </>
              ) : (
                <MissingValue label="Chưa ghi nhận" />
              )}
            </Field>

            <Field label="Điện thoại người bệnh">
              {profile.phone_number ? (
                <PhoneLink value={profile.phone_number} />
              ) : (
                <MissingValue label="Chưa khai báo" />
              )}
            </Field>

            <Field label="Nhóm máu">
              {profile.blood_type ? (
                <span className="inline-flex items-center gap-1.5 font-mono">
                  <Droplet className="size-3.5 shrink-0 text-rose-600" aria-hidden="true" />
                  {profile.blood_type}
                </span>
              ) : (
                <MissingValue label="Chưa rõ" />
              )}
            </Field>
          </dl>

          {(profile.allergies.length > 0 || profile.chronic_conditions.length > 0) && (
            <dl className="mt-4 grid grid-cols-1 gap-4 border-t border-sky-200/70 pt-4 sm:grid-cols-2">
              {profile.allergies.length > 0 && (
                <Field label="Dị ứng đã khai báo">
                  <span className="inline-flex items-start gap-1.5 text-rose-800">
                    <AlertTriangle className="mt-0.5 size-4 shrink-0" aria-hidden="true" />
                    {profile.allergies.join(", ")}
                  </span>
                </Field>
              )}
              {profile.chronic_conditions.length > 0 && (
                <Field label="Bệnh nền đã khai báo">{profile.chronic_conditions.join(", ")}</Field>
              )}
            </dl>
          )}
        </div>
      )}

      {/* CHỦ TÀI KHOẢN -- người thực sự cầm máy */}
      <div className="rounded-xl border border-border bg-background p-4">
        <div className="flex items-center gap-2">
          <Users className="size-4 shrink-0 text-slate-600 dark:text-slate-300" aria-hidden="true" />
          <h3 className="text-sm font-bold text-foreground">
            Chủ tài khoản {subjectIsAccountHolder ? "(cũng là người được khám)" : "— người đã gửi phiên này"}
          </h3>
        </div>

        <dl className="mt-3 grid grid-cols-1 gap-4 sm:grid-cols-3">
          <Field label="Họ tên">
            {account.full_name ?? <MissingValue label="Chưa ghi nhận" />}
          </Field>
          <Field label="Điện thoại">
            {account.phone ? <PhoneLink value={account.phone} /> : <MissingValue label="Chưa khai báo" />}
          </Field>
          <Field label="Email">
            {account.email ? <EmailLink value={account.email} /> : <MissingValue label="Chưa khai báo" />}
          </Field>
        </dl>
      </div>

      {/* LIÊN HỆ KHẨN CẤP */}
      {profile && (profile.emergency_contact_name || profile.emergency_contact_phone) && (
        <div className="glow-soft glow-rose rounded-xl border border-rose-200 bg-rose-50/70 p-4">
          <div className="flex items-center gap-2">
            <ShieldAlert className="size-4 shrink-0 text-rose-700" aria-hidden="true" />
            <h3 className="text-sm font-bold text-rose-950">Người liên hệ khẩn cấp</h3>
          </div>
          <dl className="mt-3 grid grid-cols-1 gap-4 sm:grid-cols-2">
            <Field label="Họ tên">
              {profile.emergency_contact_name ?? <MissingValue label="Chưa khai báo" />}
            </Field>
            <Field label="Điện thoại">
              {profile.emergency_contact_phone ? (
                <PhoneLink value={profile.emergency_contact_phone} />
              ) : (
                <MissingValue label="Chưa khai báo" />
              )}
            </Field>
          </dl>
          </div>
        )}
      </div>
    </section>
  );
}
