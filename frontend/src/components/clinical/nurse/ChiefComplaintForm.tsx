"use client";

import { Save } from "lucide-react";
import { useState, type FormEvent } from "react";

import { Button } from "@/components/ui/button";
import { useUpdateIntake } from "@/hooks/mutations/use-hitl-mutations";

export function ChiefComplaintForm({
  caseId,
  caseVersion,
  chiefComplaint,
}: {
  caseId: string;
  caseVersion: number;
  chiefComplaint: string;
}) {
  const mutation = useUpdateIntake(caseId);
  const [value, setValue] = useState(chiefComplaint);
  const normalized = value.trim();
  const unchanged = normalized === chiefComplaint.trim();
  const invalid = normalized.length < 2 || normalized.length > 160;

  const submit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (invalid || unchanged) return;
    mutation.mutate({ case_version: caseVersion, chief_complaint: normalized });
  };

  return (
    <form onSubmit={submit} className="mt-6 border-l-4 border-sky-600 bg-sky-50 p-4">
      <label htmlFor="chief-complaint" className="text-sm font-semibold text-sky-950">
        Triệu chứng chính
      </label>
      <textarea
        id="chief-complaint"
        value={value}
        onChange={(event) => setValue(event.target.value)}
        rows={3}
        maxLength={160}
        className="mt-2 w-full rounded-lg border border-slate-300 bg-card p-3 text-base leading-6 text-slate-950 focus:border-sky-600 focus:outline-none focus:ring-2 focus:ring-sky-200 dark:border-slate-700 dark:text-slate-50"
        placeholder="Ví dụ: Đau ngực khi gắng sức, xuất hiện khoảng 30 phút."
      />
      <div className="mt-3 flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <p className="text-sm text-slate-600 dark:text-slate-300">
          Ghi theo lời bệnh nhân hoặc quan sát đã xác minh; không nhập chẩn đoán.
        </p>
        <Button
          type="submit"
          variant="outline"
          disabled={invalid || unchanged || mutation.isPending}
          className="min-h-11 shrink-0 border-sky-300 bg-card text-sky-800 hover:bg-sky-100"
        >
          <Save className="size-4" aria-hidden="true" />
          {mutation.isPending ? "Đang lưu..." : "Lưu triệu chứng"}
        </Button>
      </div>
      {normalized.length > 0 && invalid && (
        <p className="mt-3 text-sm text-rose-700" role="alert">
          Triệu chứng chính cần từ 2 đến 160 ký tự.
        </p>
      )}
      {mutation.isError && (
        <p className="mt-3 text-sm text-rose-700" role="alert">
          {mutation.error.message}
        </p>
      )}
      {mutation.isSuccess && (
        <p className="mt-3 text-sm text-emerald-800" role="status">
          {mutation.data.message}
        </p>
      )}
    </form>
  );
}
