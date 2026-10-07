"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { Send } from "lucide-react";
import { useRouter } from "next/navigation";
import { useForm } from "react-hook-form";

import { Button } from "@/components/ui/button";
import { useHandoffCase } from "@/hooks/mutations/use-hitl-mutations";
import {
  handoffFormSchema,
  type HandoffFormValues,
} from "@/lib/validations/clinical-hitl.schema";
import type { EsiLevel } from "@/types/clinical-hitl";

function defaultDestination(esi: EsiLevel | null): HandoffFormValues["destination"] {
  if (esi === 1) return "IMMEDIATE_CARE";
  if (esi === 2 || esi === 3) return "PRIORITY_IN_PERSON";
  return "ROUTINE_QUEUE";
}

export function HandoffForm({
  caseId,
  caseVersion,
  finalEsi,
}: {
  caseId: string;
  caseVersion: number;
  finalEsi: EsiLevel | null;
}) {
  const router = useRouter();
  const mutation = useHandoffCase(caseId);
  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<HandoffFormValues>({
    resolver: zodResolver(handoffFormSchema),
    defaultValues: {
      destination: defaultDestination(finalEsi),
      note: "",
    },
  });

  const submit = handleSubmit((values) => {
    mutation.mutate(
      { case_version: caseVersion, destination: values.destination, note: values.note.trim() },
      { onSuccess: () => router.push("/clinical/queue") },
    );
  });

  return (
    <form onSubmit={submit} className="space-y-4">
      <label className="block text-sm font-medium text-slate-800 dark:text-slate-100">
        Điểm đến nghiệp vụ
        <select
          {...register("destination")}
          className="mt-2 min-h-11 w-full rounded-lg border border-slate-300 bg-card px-4 text-base text-slate-950 dark:border-slate-700 dark:text-slate-50"
        >
          <option value="IMMEDIATE_CARE">Xử trí cấp cứu tức thì</option>
          <option value="PRIORITY_IN_PERSON">Khám trực tiếp ưu tiên</option>
          <option value="ROUTINE_QUEUE">Hàng đợi thường quy</option>
        </select>
      </label>
      <label className="block text-sm font-medium text-slate-800 dark:text-slate-100">
        Ghi chú bàn giao SBAR ngắn
        <textarea
          {...register("note")}
          rows={4}
          className="mt-2 w-full rounded-lg border border-slate-300 p-4 text-base leading-6 text-slate-950 focus:border-sky-600 focus:outline-none focus:ring-2 focus:ring-sky-200 dark:border-slate-700 dark:text-slate-50"
          placeholder="Tình trạng, dữ liệu liên quan và mức ESI đã chốt."
        />
        {errors.note?.message && (
          <span className="mt-2 block text-sm text-rose-700" role="alert">
            {errors.note.message}
          </span>
        )}
      </label>
      <div className="flex justify-end">
        <Button
          type="submit"
          disabled={mutation.isPending}
          className="min-h-11 bg-sky-700 px-6 text-white hover:bg-sky-800"
        >
          <Send className="size-4" aria-hidden="true" />
          {mutation.isPending ? "Đang bàn giao..." : "Bàn giao và hoàn tất"}
        </Button>
      </div>
      {mutation.isError && (
        <p className="text-sm text-rose-700" role="alert">
          {mutation.error.message}
        </p>
      )}
    </form>
  );
}
