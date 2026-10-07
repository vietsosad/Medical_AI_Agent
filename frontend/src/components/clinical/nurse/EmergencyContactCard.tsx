"use client";

import React, { useState } from "react";
import { AlertCircle, Eye, Loader2, Phone, PhoneOff, ShieldCheck } from "lucide-react";

import { useEmergencyContacts } from "@/hooks/queries/use-clinical-hitl";
import { cn } from "@/lib/utils";
import type { EmergencyContactPersonDTO } from "@/types/clinical-hitl";

/**
 * ============================================================================
 * [EMERGENCY CONTACT] DANH BẠ KHẨN CẤP CỦA MỘT CA
 * ============================================================================
 * Điểm quan trọng nhất ở đây không phải là bố cục mà là **nhãn**: một ca có thể
 * thuộc về người thân chứ không phải chủ tài khoản. Gọi nhầm số chủ tài khoản
 * khi bệnh nhân là trẻ nhỏ là một sai sót thật vào đúng lúc cần gọi gấp, nên
 * mỗi số luôn đi kèm vai trò của người cầm máy.
 *
 * Số điện thoại không tự hiện: nhân viên phải chủ động mở, và mỗi lần mở đều
 * được ghi vào nhật ký kiểm toán ở backend.
 */

/** Nhãn tiếng Việt cho quan hệ lưu trong hồ sơ. */
const RELATIONSHIP_LABELS: Record<string, string> = {
  SELF: "Chính chủ",
  CHILD: "Con",
  SPOUSE: "Vợ/Chồng",
  PARENT: "Cha mẹ",
  SIBLING: "Anh chị em",
  OTHER: "Người thân",
};

function ContactRow({ contact }: { contact: EmergencyContactPersonDTO }) {
  const relationship = contact.relationship
    ? (RELATIONSHIP_LABELS[contact.relationship] ?? contact.relationship)
    : null;
  const isPatient = contact.label === "Bệnh nhân";

  return (
    <li
      className={cn(
        "flex flex-wrap items-center justify-between gap-3 rounded-xl border p-4",
        isPatient ? "border-teal-200 bg-teal-50/60" : "border-border bg-card",
      )}
    >
      <div className="min-w-0">
        <span
          className={cn(
            "inline-flex rounded-full border px-2.5 py-0.5 text-xs font-bold uppercase tracking-wide",
            isPatient
              ? "border-teal-300 bg-teal-100 text-teal-900"
              : "border-slate-300 bg-muted text-slate-700 dark:text-slate-200 dark:border-slate-700",
          )}
        >
          {contact.label}
        </span>
        <p className="mt-1.5 truncate text-sm font-bold text-foreground">
          {contact.full_name ?? "Chưa có tên"}
        </p>
        {relationship && <p className="text-xs text-slate-600 dark:text-slate-300">{relationship}</p>}
      </div>

      {contact.phone ? (
        <a
          href={`tel:${contact.phone}`}
          className="flex min-h-11 shrink-0 items-center gap-2 rounded-xl bg-slate-900 px-4 text-sm font-bold text-white transition-colors hover:bg-slate-800 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-slate-900 focus-visible:ring-offset-2"
        >
          <Phone className="size-4" aria-hidden="true" />
          {contact.phone}
        </a>
      ) : (
        <span className="flex min-h-11 shrink-0 items-center gap-2 rounded-xl border border-dashed border-slate-300 px-4 text-sm font-semibold text-muted-foreground dark:border-slate-700">
          <PhoneOff className="size-4" aria-hidden="true" />
          Chưa cập nhật
        </span>
      )}
    </li>
  );
}

interface EmergencyContactCardProps {
  caseId: string;
  isAssignedToMe: boolean;
}

export function EmergencyContactCard({ caseId, isAssignedToMe }: EmergencyContactCardProps) {
  const [revealed, setRevealed] = useState(false);
  const { data, isLoading, isError } = useEmergencyContacts(caseId, revealed && isAssignedToMe);

  return (
    <section className="rounded-2xl border border-border bg-card p-5">
      <header className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h3 className="flex items-center gap-2 text-base font-bold text-foreground">
            <Phone className="size-4 shrink-0 text-slate-700 dark:text-slate-200" aria-hidden="true" />
            Liên hệ khẩn cấp
          </h3>
          <p className="mt-1 text-sm text-slate-600 dark:text-slate-300">
            Số của người bệnh và số của người liên hệ được tách riêng.
          </p>
        </div>

        {!revealed && (
          <button
            type="button"
            onClick={() => setRevealed(true)}
            disabled={!isAssignedToMe}
            className="flex min-h-11 items-center gap-2 rounded-xl border border-slate-300 bg-card px-4 text-sm font-semibold text-slate-800 transition-colors hover:bg-background disabled:cursor-not-allowed disabled:opacity-45 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-slate-500 focus-visible:ring-offset-2 dark:text-slate-100 dark:border-slate-700"
          >
            <Eye className="size-4" aria-hidden="true" />
            Hiện số liên hệ
          </button>
        )}
      </header>

      {!isAssignedToMe ? (
        <p className="mt-4 rounded-xl border border-border bg-background p-4 text-sm text-slate-600 dark:text-slate-300">
          Cần nhận ca trước khi xem thông tin liên hệ của người bệnh.
        </p>
      ) : !revealed ? (
        <p className="mt-4 flex items-start gap-2.5 rounded-xl border border-border bg-background p-4 text-sm leading-6 text-slate-600 dark:text-slate-300">
          <ShieldCheck className="mt-0.5 size-4 shrink-0 text-emerald-600" aria-hidden="true" />
          Số điện thoại được che mặc định. Mỗi lần mở đều được ghi vào nhật ký kiểm toán
          kèm danh tính người mở.
        </p>
      ) : isLoading ? (
        <p className="mt-4 flex items-center gap-2 py-6 text-sm text-muted-foreground">
          <Loader2 className="size-4 animate-spin" aria-hidden="true" />
          Đang mở thông tin liên hệ...
        </p>
      ) : isError || !data ? (
        <p
          role="alert"
          className="mt-4 flex items-center gap-2 rounded-xl border border-amber-200 bg-amber-50 p-4 text-sm font-medium text-amber-900"
        >
          <AlertCircle className="size-4 shrink-0" aria-hidden="true" />
          Không mở được thông tin liên hệ lúc này.
        </p>
      ) : (
        <ul className="mt-4 space-y-2.5">
          {data.contacts.map((contact) => (
            <ContactRow key={`${contact.label}-${contact.full_name ?? "?"}`} contact={contact} />
          ))}
        </ul>
      )}
    </section>
  );
}

export default EmergencyContactCard;
