"use client";

import React from "react";
import {
  AlertTriangle,
  ArrowRight,
  CheckCircle2,
  Clock,
  FileText,
  ShieldCheck,
  UserCheck,
} from "lucide-react";

import { cn } from "@/lib/utils";
import type { HitlSignatureDTO } from "@/types/clinical-history";

export interface HitlSignatureBadgeProps {
  signature?: HitlSignatureDTO | null;
  className?: string;
}

function formatSignatureTime(value?: string): string {
  if (!value) return "Chưa ghi nhận thời điểm";
  const parsed = new Date(value);
  return Number.isNaN(parsed.getTime())
    ? value
    : parsed.toLocaleString("vi-VN", {
        dateStyle: "short",
        timeStyle: "medium",
      });
}

export const HitlSignatureBadge: React.FC<HitlSignatureBadgeProps> = ({
  signature,
  className,
}) => {
  if (!signature) {
    return (
      <section
        className={cn(
          "space-y-2 rounded-2xl border border-sky-200 bg-sky-50 p-6 text-sky-950",
          className,
        )}
        aria-label="Trạng thái thẩm định"
      >
        <div className="flex items-center gap-2 text-base font-bold">
          <Clock className="size-5 text-sky-700" aria-hidden="true" />
          Đang chờ nhân viên y tế thẩm định
        </div>
        <p className="text-sm leading-6 text-slate-700 dark:text-slate-200">
          Chưa có chữ ký thẩm định được lưu cho ca khám này.
        </p>
      </section>
    );
  }

  const {
    status,
    reviewer_name,
    review_timestamp,
    original_esi,
    final_esi,
    justification_note,
  } = signature;
  const formattedTime = formatSignatureTime(review_timestamp);

  if (status === "APPROVED") {
    return (
      <section
        className={cn(
          "space-y-4 rounded-2xl border border-emerald-300 bg-emerald-50 p-6 text-slate-900",
          className,
        )}
        aria-label="Kết quả đã được thẩm định"
      >
        <div className="flex items-start gap-4">
          <CheckCircle2 className="size-6 shrink-0 text-emerald-700" aria-hidden="true" />
          <div className="space-y-2">
            <h2 className="text-base font-bold text-emerald-950">
              Đã được nhân viên y tế xác nhận
            </h2>
            <p className="text-sm leading-6 text-slate-700 dark:text-slate-200">
              {reviewer_name ? `${reviewer_name} xác nhận` : "Đã xác nhận"} ESI {final_esi} lúc{" "}
              {formattedTime}.
            </p>
          </div>
        </div>
        {justification_note && (
          <div className="flex items-start gap-2 border-t border-emerald-200 pt-4 text-sm leading-6 text-slate-800 dark:text-slate-100">
            <FileText className="mt-0.5 size-5 shrink-0 text-emerald-700" aria-hidden="true" />
            <p>{justification_note}</p>
          </div>
        )}
      </section>
    );
  }

  if (status === "OVERRIDDEN") {
    return (
      <section
        className={cn(
          "space-y-4 rounded-2xl border border-amber-300 bg-amber-50 p-6 text-slate-900",
          className,
        )}
        aria-label="Kết quả đã được điều chỉnh"
      >
        <div className="flex items-start gap-4">
          <UserCheck className="size-6 shrink-0 text-amber-700" aria-hidden="true" />
          <div className="space-y-2">
            <h2 className="text-base font-bold text-amber-950">
              Nhân viên y tế đã điều chỉnh mức ưu tiên
            </h2>
            <p className="text-sm leading-6 text-slate-700 dark:text-slate-200">
              {reviewer_name ? `${reviewer_name} cập nhật` : "Kết quả được cập nhật"} lúc{" "}
              {formattedTime}.
            </p>
          </div>
        </div>
        <div className="flex items-center justify-center gap-4 rounded-xl border border-amber-200 bg-card p-4 text-base font-bold">
          <span>Đề xuất AI: ESI {original_esi}</span>
          <ArrowRight className="size-5 text-amber-700" aria-hidden="true" />
          <span className="text-amber-950">Kết quả thẩm định: ESI {final_esi}</span>
        </div>
        {justification_note && (
          <div className="flex items-start gap-2 border-t border-amber-200 pt-4 text-sm leading-6 text-slate-800 dark:text-slate-100">
            <FileText className="mt-0.5 size-5 shrink-0 text-amber-700" aria-hidden="true" />
            <p>{justification_note}</p>
          </div>
        )}
      </section>
    );
  }

  if (status === "PENDING_REVIEW") {
    return (
      <section
        className={cn(
          "space-y-2 rounded-2xl border border-sky-200 bg-sky-50 p-6 text-sky-950",
          className,
        )}
        aria-label="Đang chờ thẩm định"
      >
        <div className="flex items-center gap-2 text-base font-bold">
          <Clock className="size-5 text-sky-700" aria-hidden="true" />
          Đang chờ nhân viên y tế thẩm định
        </div>
        <p className="text-sm leading-6 text-slate-700 dark:text-slate-200">
          Trạng thái được ghi nhận lúc {formattedTime}.
        </p>
      </section>
    );
  }

  return (
    <section
      className={cn(
        "space-y-4 rounded-2xl border border-rose-400 bg-rose-50 p-6 text-rose-950",
        className,
      )}
      role="alert"
    >
      <div className="flex items-start gap-4">
        <AlertTriangle className="size-6 shrink-0 text-rose-700" aria-hidden="true" />
        <div className="space-y-2">
          <h2 className="text-base font-bold">Ca khám đã chuyển sang luồng xử trí khẩn cấp</h2>
          <p className="text-sm leading-6 text-slate-800 dark:text-slate-100">
            Trạng thái được ghi nhận lúc {formattedTime}
            {reviewer_name ? ` bởi ${reviewer_name}` : ""}.
          </p>
        </div>
      </div>
      {justification_note && (
        <div className="flex items-start gap-2 border-t border-rose-200 pt-4 text-sm leading-6 text-slate-800 dark:text-slate-100">
          <ShieldCheck className="mt-0.5 size-5 shrink-0 text-rose-700" aria-hidden="true" />
          <p>{justification_note}</p>
        </div>
      )}
    </section>
  );
};

export default HitlSignatureBadge;
