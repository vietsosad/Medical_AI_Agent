"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { Undo2 } from "lucide-react";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { useForm } from "react-hook-form";
import { z } from "zod";

import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogClose,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import { useClaimCase } from "@/hooks/mutations/use-hitl-mutations";

const releaseSchema = z.object({
  reason: z.string().min(5, "Lý do trả ca cần ít nhất 5 ký tự.").max(300),
});
type ReleaseValues = z.infer<typeof releaseSchema>;

export function ReleaseCaseDialog({ caseId, caseVersion }: { caseId: string; caseVersion: number }) {
  const [open, setOpen] = useState(false);
  const router = useRouter();
  const mutation = useClaimCase(caseId);
  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<ReleaseValues>({
    resolver: zodResolver(releaseSchema),
    defaultValues: { reason: "" },
  });

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>
        <Button type="button" variant="outline" className="min-h-11 border-slate-300 bg-card text-slate-800 dark:text-slate-100 dark:border-slate-700">
          <Undo2 className="size-4" aria-hidden="true" />
          Trả ca
        </Button>
      </DialogTrigger>
      <DialogContent
        hideCloseButton
        className="max-w-lg border-border bg-card text-slate-950 shadow-xl dark:text-slate-50"
        overlayClassName="bg-slate-950/50 backdrop-blur-sm"
      >
        <DialogHeader>
          <DialogTitle className="text-xl text-slate-950 dark:text-slate-50">Trả ca về hàng đợi</DialogTitle>
          <DialogDescription className="text-base text-slate-600 dark:text-slate-300">
            Ca sẽ không còn thuộc trách nhiệm hiện tại của bạn. Hành động này được lưu audit.
          </DialogDescription>
        </DialogHeader>
        <form
          className="space-y-4"
          onSubmit={handleSubmit((values) =>
            mutation.mutate(
              { case_version: caseVersion, action: "RELEASE", reason: values.reason.trim() },
              { onSuccess: () => router.push("/clinical/queue") },
            ),
          )}
        >
          <label className="block text-sm font-medium text-slate-800 dark:text-slate-100">
            Lý do trả ca
            <textarea
              {...register("reason")}
              rows={3}
              className="mt-2 w-full rounded-lg border border-slate-300 p-4 text-base text-slate-950 focus:border-sky-600 focus:outline-none focus:ring-2 focus:ring-sky-200 dark:border-slate-700 dark:text-slate-50"
            />
            {errors.reason?.message && (
              <span className="mt-2 block text-sm text-rose-700" role="alert">
                {errors.reason.message}
              </span>
            )}
          </label>
          {mutation.isError && (
            <p className="text-sm text-rose-700" role="alert">
              {mutation.error.message}
            </p>
          )}
          <DialogFooter className="gap-2">
            <DialogClose asChild>
              <Button type="button" variant="outline" className="min-h-11 border-slate-300 text-slate-800 dark:text-slate-100 dark:border-slate-700">
                Hủy
              </Button>
            </DialogClose>
            <Button type="submit" disabled={mutation.isPending} className="min-h-11 bg-sky-700 text-white hover:bg-sky-800">
              {mutation.isPending ? "Đang trả ca..." : "Xác nhận trả ca"}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
