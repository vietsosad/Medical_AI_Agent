import React from "react";
import { Info, type LucideIcon } from "lucide-react";

/**
 * Trạng thái trống trung thực cho các trang quản trị chưa nối dữ liệu thật.
 *
 * Các trang này từng hiện số liệu, nhật ký và công tắc cấu hình dựng sẵn trong
 * mã nguồn ("96.4%", "99.6% Precision", "100% Verified Compliant", nút "Lưu"
 * chỉ bật một `alert`). Với một sản phẩm y tế, một con số chưa từng đo là một
 * tuyên bố sai, nên trang chỉ được nói điều kiểm chứng được trong mã nguồn và
 * nói thẳng phần nào chưa có.
 */
export function AdminNotConnectedPanel({
  icon: Icon,
  title,
  summary,
  facts,
}: {
  icon: LucideIcon;
  title: string;
  summary: string;
  /** Những điều đúng về hệ thống hiện tại, mỗi dòng một ý, đều kiểm chứng được trong mã nguồn. */
  facts: string[];
}) {
  return (
    <div className="mx-auto max-w-4xl space-y-6 p-6 font-sans text-foreground sm:p-8">
      <div className="flex items-center gap-4 rounded-2xl border border-border bg-card p-6">
        <div className="flex size-12 shrink-0 items-center justify-center rounded-xl bg-slate-900 text-sky-400">
          <Icon className="size-6" aria-hidden="true" />
        </div>
        <h1 className="text-xl font-bold tracking-tight sm:text-2xl">{title}</h1>
      </div>

      <div className="flex items-start gap-4 rounded-2xl border border-sky-200 bg-sky-50 p-6 text-sky-950">
        <Info className="mt-0.5 size-5 shrink-0" aria-hidden="true" />
        <div className="space-y-4">
          <p className="text-base font-semibold leading-7">{summary}</p>
          <ul className="list-disc space-y-2 pl-6 text-sm leading-6">
            {facts.map((fact) => (
              <li key={fact}>{fact}</li>
            ))}
          </ul>
        </div>
      </div>
    </div>
  );
}
