"use client";

import { motion } from "framer-motion";
import { Droplet, Mail, Phone, ShieldAlert, UserRound } from "lucide-react";

import {
  contactLines,
  genderLabel,
  profileRelationshipLabel,
  telHref,
} from "@/components/clinical/nurse-simple/case/case-format";
import { riseIn } from "@/components/clinical/nurse-simple/case/case-motion";
import { cn } from "@/lib/utils";
import type { SimpleNursePatientContactDTO } from "@/types/simple-nurse";

/**
 * Cột "gọi cho ai" của hồ sơ ca: thẻ Liên lạc và thẻ Hồ sơ sức khỏe.
 *
 * Dữ liệu lấy từ khối `patient` của `GET /nurse-simple/cases/{id}` (xem
 * `_patient_contact_block`). Tách bạch có chủ đích giữa hai danh tính:
 * - "Người được khám" là thẻ hồ sơ đã chọn lúc bắt đầu phiên, có thể là trẻ
 *   nhỏ hoặc người thân không tự nghe máy được.
 * - "Chủ tài khoản" là người thực sự đã ngồi gõ và cầm máy.
 * Gộp hai thứ này lại sẽ dẫn tới gọi nhầm người trong tình huống cần gấp, nên
 * mỗi số điện thoại luôn đi kèm câu "người này là ai của người bệnh".
 */

const cardClass = "@container rounded-2xl border border-border bg-card p-4 shadow-xs sm:p-6";

function CardTitle({ id, children }: { id: string; children: React.ReactNode }) {
  return (
    <h2 id={id} className="text-base font-bold text-foreground">
      {children}
    </h2>
  );
}

function Missing({ children }: { children: React.ReactNode }) {
  return <span className="font-medium text-muted-foreground">{children}</span>;
}

export function PatientContactCard({
  patient,
  delay = 0,
  className,
}: {
  patient: SimpleNursePatientContactDTO;
  delay?: number;
  className?: string;
}) {
  const lines = contactLines(patient);
  const [primary, ...others] = lines;
  const emergencyNameOnly =
    patient.profile?.emergency_contact_name && !patient.profile.emergency_contact_phone
      ? patient.profile.emergency_contact_name
      : null;

  return (
    <motion.section {...riseIn(delay)} aria-labelledby="case-contact-title" className={cn(cardClass, className)}>
      <CardTitle id="case-contact-title">Liên lạc</CardTitle>

      {primary ? (
        <div className="mt-4">
          <p className="text-base font-bold text-foreground">
            {primary.name}
            <span className="font-semibold text-muted-foreground"> · {primary.relation}</span>
          </p>
          <p className="text-sm leading-6 tabular-nums text-muted-foreground">{primary.phone}</p>
          <motion.a
            href={telHref(primary.phone)}
            whileTap={{ scale: 0.97 }}
            aria-label={`${primary.callLabel}: ${primary.name}, số ${primary.phone}`}
            className="mt-4 flex min-h-11 items-center justify-center gap-2 rounded-xl border border-brand-edge bg-brand-soft px-4 text-sm font-extrabold text-brand-ink transition-colors hover:border-brand focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand focus-visible:ring-offset-2 focus-visible:ring-offset-card"
          >
            <Phone className="size-4 shrink-0" aria-hidden="true" />
            {primary.callLabel}
          </motion.a>
        </div>
      ) : (
        <p className="mt-4 text-sm leading-6 text-muted-foreground">
          Hồ sơ chưa có số điện thoại nào. Hãy nhắn tin cho người bệnh để xin số liên lạc.
        </p>
      )}

      {(others.length > 0 || patient.account.email || emergencyNameOnly) && (
        <ul className="mt-4 flex flex-col gap-2 border-t border-border pt-4">
          {others.map((line) => (
            <li key={line.key}>
              <a
                href={telHref(line.phone)}
                aria-label={`${line.callLabel}: ${line.name}, số ${line.phone}`}
                className={cn(
                  "flex min-h-11 items-center gap-2 rounded-xl px-2 text-sm transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand",
                  line.key === "emergency"
                    ? "text-rose-900 hover:bg-rose-50 dark:text-rose-200 dark:hover:bg-rose-950/40"
                    : "text-foreground hover:bg-muted",
                )}
              >
                {line.key === "emergency" ? (
                  <ShieldAlert className="size-4 shrink-0" aria-hidden="true" />
                ) : (
                  <Phone className="size-4 shrink-0 text-muted-foreground" aria-hidden="true" />
                )}
                <span className="min-w-0">
                  <span className="block truncate font-semibold">
                    {line.name} · {line.relation}
                  </span>
                  <span className="block tabular-nums opacity-80">{line.phone}</span>
                </span>
              </a>
            </li>
          ))}
          {emergencyNameOnly && (
            <li className="flex items-start gap-2 px-2 text-sm leading-6 text-rose-900 dark:text-rose-200">
              <span className="flex h-6 shrink-0 items-center" aria-hidden="true">
                <ShieldAlert className="size-4" />
              </span>
              <span>
                <span className="font-semibold">{emergencyNameOnly} · liên hệ khẩn cấp</span>
                <span className="block opacity-80">Chưa khai báo số điện thoại</span>
              </span>
            </li>
          )}
          {patient.account.email && (
            <li>
              <a
                href={`mailto:${patient.account.email}`}
                className="flex min-h-11 min-w-0 items-center gap-2 rounded-xl px-2 text-sm text-foreground transition-colors hover:bg-muted focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand"
              >
                <Mail className="size-4 shrink-0 text-muted-foreground" aria-hidden="true" />
                <span className="truncate">{patient.account.email}</span>
              </a>
            </li>
          )}
        </ul>
      )}
    </motion.section>
  );
}

function Chips({ items, tone }: { items: string[]; tone: "allergy" | "neutral" }) {
  return (
    <ul className="flex flex-wrap gap-2">
      {items.map((item) => (
        <li
          key={item}
          className={cn(
            "inline-flex min-h-8 items-center rounded-full border px-4 text-sm font-semibold",
            tone === "allergy"
              ? "border-rose-200 bg-rose-50 text-rose-900 dark:border-rose-800 dark:bg-rose-950/40 dark:text-rose-100"
              : "border-border bg-muted text-foreground",
          )}
        >
          {item}
        </li>
      ))}
    </ul>
  );
}

export function PatientHealthCard({
  patient,
  delay = 0,
  className,
}: {
  patient: SimpleNursePatientContactDTO;
  delay?: number;
  className?: string;
}) {
  const { profile } = patient;
  const gender = profile ? genderLabel(profile.gender) : null;

  return (
    <motion.section {...riseIn(delay)} aria-labelledby="case-health-title" className={cn(cardClass, className)}>
      <CardTitle id="case-health-title">Hồ sơ sức khỏe</CardTitle>

      {profile === null ? (
        <p className="mt-4 flex items-start gap-2 rounded-xl bg-amber-50 p-4 text-sm leading-6 text-amber-950 dark:bg-amber-950/40 dark:text-amber-100">
          <span className="flex h-6 shrink-0 items-center" aria-hidden="true">
            <ShieldAlert className="size-4" />
          </span>
          <span>
            Phiên ẩn danh: người bệnh không gắn thẻ hồ sơ nào khi bắt đầu, nên hệ thống không có nhân khẩu học của
            người được khám. Hãy liên lạc qua số ở thẻ Liên lạc và xác minh lại danh tính trực tiếp.
          </span>
        </p>
      ) : (
        <>
          {/* Thẻ hẹp (cột trái ở màn rất rộng) thì nhãn nằm trên giá trị; thẻ
              đủ rộng thì nhãn và giá trị chung một hàng. */}
          <dl className="mt-4 flex flex-col gap-2 text-sm leading-6">
            <div className="flex flex-col @xs:flex-row @xs:gap-4">
              <dt className="shrink-0 text-muted-foreground @xs:w-32">Người được khám</dt>
              <dd className="min-w-0 font-semibold text-foreground">
                <span className="flex items-center gap-2">
                  <UserRound className="size-4 shrink-0 text-muted-foreground" aria-hidden="true" />
                  <span className="min-w-0 break-words">{profile.full_name}</span>
                </span>
                <span className="block font-medium text-muted-foreground">{profileRelationshipLabel(profile)}</span>
              </dd>
            </div>

            <div className="flex flex-col @xs:flex-row @xs:gap-4">
              <dt className="shrink-0 text-muted-foreground @xs:w-32">Tuổi / giới tính</dt>
              <dd className="font-semibold text-foreground">
                {profile.age !== null || gender ? (
                  <>
                    {profile.age !== null ? `${profile.age} tuổi` : "Chưa rõ tuổi"}
                    {gender ? ` · ${gender}` : ""}
                  </>
                ) : (
                  <Missing>Chưa ghi nhận</Missing>
                )}
              </dd>
            </div>

            <div className="flex flex-col @xs:flex-row @xs:gap-4">
              <dt className="shrink-0 text-muted-foreground @xs:w-32">Nhóm máu</dt>
              <dd className="font-semibold text-foreground">
                {profile.blood_type ? (
                  <span className="inline-flex items-center gap-2 tabular-nums">
                    <Droplet className="size-4 shrink-0 text-rose-600 dark:text-rose-400" aria-hidden="true" />
                    {profile.blood_type}
                  </span>
                ) : (
                  <Missing>Chưa rõ</Missing>
                )}
              </dd>
            </div>
          </dl>

          <div className="mt-4 flex flex-col gap-2">
            <h3 className="text-sm font-bold text-muted-foreground">Bệnh nền</h3>
            {profile.chronic_conditions.length > 0 ? (
              <Chips items={profile.chronic_conditions} tone="neutral" />
            ) : (
              <p className="text-sm">
                <Missing>Không ghi nhận</Missing>
              </p>
            )}
          </div>

          <div className="mt-4 flex flex-col gap-2">
            <h3 className="text-sm font-bold text-muted-foreground">Dị ứng</h3>
            {profile.allergies.length > 0 ? (
              <Chips items={profile.allergies} tone="allergy" />
            ) : (
              <p className="text-sm">
                <Missing>Không ghi nhận</Missing>
              </p>
            )}
          </div>
        </>
      )}
    </motion.section>
  );
}

/** Hai thẻ của cột trái, theo thứ tự đọc: gọi cho ai, rồi người đó có gì cần lưu ý. */
export function SimplePatientContactPanel({
  patient,
  delay = 0,
  className,
}: {
  patient: SimpleNursePatientContactDTO;
  delay?: number;
  className?: string;
}) {
  return (
    <div className={cn("grid gap-6", className)}>
      <PatientContactCard patient={patient} delay={delay} />
      <PatientHealthCard patient={patient} delay={delay + 0.05} />
    </div>
  );
}
