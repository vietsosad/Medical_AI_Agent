"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { Eye, EyeOff } from "lucide-react";
import { useEffect, useState } from "react";
import { useForm } from "react-hook-form";

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
import { useAccessPii } from "@/hooks/mutations/use-hitl-mutations";
import {
  piiAccessFormSchema,
  type PiiAccessFormValues,
} from "@/lib/validations/clinical-hitl.schema";

export function PiiAccessDialog({ caseId }: { caseId: string }) {
  const [open, setOpen] = useState(false);
  const access = useAccessPii(caseId);
  const {
    register,
    handleSubmit,
    reset,
    formState: { errors },
  } = useForm<PiiAccessFormValues>({
    resolver: zodResolver(piiAccessFormSchema),
    defaultValues: { reason: "" },
  });
  const piiData = access.data;
  const resetAccess = access.reset;

  useEffect(() => {
    if (!piiData) return;
    const delay = Math.max(0, new Date(piiData.expires_at).getTime() - Date.now());
    const timer = window.setTimeout(() => {
      resetAccess();
      setOpen(false);
    }, delay);
    return () => window.clearTimeout(timer);
  }, [piiData, resetAccess]);

  const changeOpen = (next: boolean) => {
    setOpen(next);
    if (!next) {
      access.reset();
      reset();
    }
  };

  return (
    <Dialog open={open} onOpenChange={changeOpen}>
      <DialogTrigger asChild>
        <Button type="button" variant="outline" className="min-h-11 border-slate-300 bg-card text-slate-800 dark:text-slate-100 dark:border-slate-700">
          <Eye className="size-4" aria-hidden="true" />
          Xem thông tin liên hệ
        </Button>
      </DialogTrigger>
      <DialogContent
        hideCloseButton
        className="max-w-lg border-border bg-card text-slate-950 shadow-xl dark:text-slate-50"
        overlayClassName="bg-slate-950/50 backdrop-blur-sm"
      >
        <DialogHeader>
          <DialogTitle className="text-xl text-slate-950 dark:text-slate-50">Truy cập PII có kiểm soát</DialogTitle>
          <DialogDescription className="text-base text-slate-600 dark:text-slate-300">
            Chỉ dùng khi cần liên hệ ca đang phụ trách. Lý do và người truy cập sẽ được audit; dữ liệu tự che sau 5 phút.
          </DialogDescription>
        </DialogHeader>

        {piiData ? (
          <div className="space-y-4" aria-live="polite">
            <dl className="grid gap-4 text-base sm:grid-cols-2">
              <div>
                <dt className="text-sm text-slate-600 dark:text-slate-300">Họ tên</dt>
                <dd className="mt-2 font-semibold text-slate-950 dark:text-slate-50">{piiData.full_name}</dd>
              </div>
              <div>
                <dt className="text-sm text-slate-600 dark:text-slate-300">Số điện thoại</dt>
                <dd className="mt-2 font-semibold text-slate-950 dark:text-slate-50">{piiData.phone ?? "Không có dữ liệu"}</dd>
              </div>
              <div>
                <dt className="text-sm text-slate-600 dark:text-slate-300">Người liên hệ khẩn cấp</dt>
                <dd className="mt-2 font-semibold text-slate-950 dark:text-slate-50">
                  {piiData.emergency_contact_name ?? "Không có dữ liệu"}
                </dd>
              </div>
              <div>
                <dt className="text-sm text-slate-600 dark:text-slate-300">SĐT liên hệ khẩn cấp</dt>
                <dd className="mt-2 font-semibold text-slate-950 dark:text-slate-50">
                  {piiData.emergency_contact_phone ?? "Không có dữ liệu"}
                </dd>
              </div>
            </dl>
            <DialogFooter>
              <DialogClose asChild>
                <Button type="button" className="min-h-11 bg-slate-900 text-white hover:bg-slate-800">
                  <EyeOff className="size-4" aria-hidden="true" />
                  Che lại ngay
                </Button>
              </DialogClose>
            </DialogFooter>
          </div>
        ) : (
          <form onSubmit={handleSubmit((values) => access.mutate(values.reason.trim()))} className="space-y-4">
            <label className="block text-sm font-medium text-slate-800 dark:text-slate-100">
              Lý do cần thông tin liên hệ
              <textarea
                {...register("reason")}
                rows={4}
                className="mt-2 w-full rounded-lg border border-slate-300 p-4 text-base text-slate-950 focus:border-sky-600 focus:outline-none focus:ring-2 focus:ring-sky-200 dark:border-slate-700 dark:text-slate-50"
                placeholder="Ví dụ: Gọi xác minh thời điểm khởi phát triệu chứng."
              />
              {errors.reason?.message && (
                <span className="mt-2 block text-sm text-rose-700" role="alert">
                  {errors.reason.message}
                </span>
              )}
            </label>
            {access.isError && (
              <p className="text-sm text-rose-700" role="alert">
                {access.error.message}
              </p>
            )}
            <DialogFooter className="gap-2">
              <DialogClose asChild>
                <Button type="button" variant="outline" className="min-h-11 border-slate-300 text-slate-800 dark:text-slate-100 dark:border-slate-700">
                  Hủy
                </Button>
              </DialogClose>
              <Button
                type="submit"
                disabled={access.isPending}
                className="min-h-11 bg-sky-700 text-white hover:bg-sky-800"
              >
                {access.isPending ? "Đang ghi audit..." : "Mở trong 5 phút"}
              </Button>
            </DialogFooter>
          </form>
        )}
      </DialogContent>
    </Dialog>
  );
}
