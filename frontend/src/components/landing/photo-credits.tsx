import { Camera } from "lucide-react";

import { cn } from "@/lib/utils";

/** Ghi công một ảnh Wikimedia Commons theo đúng giấy phép của nó. */
export interface PhotoCredit {
  author: string;
  license: string;
  licenseUrl: string | null;
  sourceUrl: string;
}

export interface CreditedPhoto {
  key: string;
  /** Ảnh chụp gì, đứng đầu mỗi dòng ghi công. */
  label: string;
  credit: PhotoCredit;
}

const LINK_CLASS =
  "underline decoration-slate-300 underline-offset-4 hover:text-teal-700 hover:decoration-teal-500 dark:decoration-slate-600 dark:hover:text-teal-300";

/**
 * Danh sách ghi công gập lại sau một dòng: tác giả trỏ về trang ảnh gốc, giấy
 * phép trỏ về văn bản giấy phép (ảnh public domain thì không có liên kết).
 */
export function PhotoCreditDisclosure({
  summary,
  photos,
  centered = false,
  className,
}: {
  summary: string;
  photos: CreditedPhoto[];
  centered?: boolean;
  className?: string;
}) {
  if (photos.length === 0) return null;

  return (
    <details
      className={cn("group/credits text-sm text-slate-600 dark:text-slate-300", centered && "mx-auto max-w-3xl", className)}
    >
      <summary
        className={cn(
          "flex min-h-11 w-fit cursor-pointer list-none items-center gap-2 rounded-lg px-3 font-semibold text-slate-700 transition-colors hover:text-teal-700 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-teal-600 dark:text-slate-200 dark:hover:text-teal-300 [&::-webkit-details-marker]:hidden",
          centered && "mx-auto",
        )}
      >
        <Camera className="size-4" aria-hidden="true" />
        {summary}
      </summary>
      <ul className="mt-3 grid gap-x-8 gap-y-2 rounded-xl border border-slate-200 bg-white p-4 leading-6 sm:grid-cols-2 dark:border-slate-800 dark:bg-slate-900">
        {photos.map(({ key, label, credit }) => (
          <li key={key}>
            <span className="font-semibold text-slate-800 dark:text-slate-100">{label}</span>
            {": "}
            <a href={credit.sourceUrl} target="_blank" rel="noopener noreferrer" className={LINK_CLASS}>
              {credit.author}
            </a>
            {", "}
            {credit.licenseUrl ? (
              <a href={credit.licenseUrl} target="_blank" rel="noopener noreferrer" className={LINK_CLASS}>
                {credit.license}
              </a>
            ) : (
              credit.license
            )}
          </li>
        ))}
      </ul>
    </details>
  );
}
