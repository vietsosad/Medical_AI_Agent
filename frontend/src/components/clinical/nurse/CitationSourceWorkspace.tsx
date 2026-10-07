"use client";

import { AlertTriangle, ArrowLeft, ExternalLink, FileCheck2 } from "lucide-react";
import Link from "next/link";

import { useNurseCase } from "@/hooks/queries/use-clinical-hitl";

function safeSourceUri(uri: string | null): string | null {
  if (!uri) return null;
  try {
    const parsed = new URL(uri);
    return parsed.protocol === "https:" || parsed.protocol === "http:" ? parsed.toString() : null;
  } catch {
    return null;
  }
}

export function CitationSourceWorkspace({
  caseId,
  citationId,
}: {
  caseId: string;
  citationId: string;
}) {
  const detail = useNurseCase(caseId);
  const backHref = `/clinical/cases/${encodeURIComponent(caseId)}#sbar-can-cu`;

  if (detail.isLoading) {
    return <div className="h-80 animate-pulse rounded-xl bg-slate-200 dark:bg-slate-700" aria-label="Đang tải nguồn tham chiếu" />;
  }

  const citation = detail.data?.citations.find((item) => item.code === citationId);
  if (detail.isError || !citation) {
    return (
      <section className="rounded-xl border border-rose-200 bg-card p-8 text-center" role="alert">
        <AlertTriangle className="mx-auto size-10 text-rose-700" aria-hidden="true" />
        <h1 className="mt-4 text-2xl font-semibold text-slate-950 dark:text-slate-50">Không tìm thấy nguồn tham chiếu</h1>
        <p className="mt-2 text-base text-slate-600 dark:text-slate-300">
          Nguồn không thuộc proposal của ca này hoặc dữ liệu ca không còn khả dụng.
        </p>
        <Link className="mt-6 inline-flex min-h-11 items-center gap-2 text-sky-800" href={backHref}>
          <ArrowLeft className="size-5" aria-hidden="true" />
          Quay lại ca
        </Link>
      </section>
    );
  }

  const sourceUri = safeSourceUri(citation.source_uri);
  const provenance = [
    citation.section ? `Mục: ${citation.section}` : null,
    citation.version ? `Phiên bản: ${citation.version}` : null,
    citation.content_hash ? `Mã kiểm chứng: ${citation.content_hash}` : null,
  ].filter((item): item is string => Boolean(item));

  return (
    <article className="rounded-xl border border-border bg-card p-6" aria-labelledby="citation-title">
      <Link className="inline-flex min-h-11 items-center gap-2 font-semibold text-sky-800" href={backHref}>
        <ArrowLeft className="size-5" aria-hidden="true" />
        Quay lại đề xuất phân luồng
      </Link>

      <div className="mt-6 flex items-start gap-4">
        <FileCheck2 className="mt-2 size-6 shrink-0 text-emerald-700" aria-hidden="true" />
        <div className="min-w-0">
          <p className="break-all text-sm font-semibold text-sky-800">{citation.code}</p>
          <h1 id="citation-title" className="mt-2 text-2xl font-semibold text-slate-950 dark:text-slate-50">
            {citation.title || "Nguồn tham chiếu đã truy xuất"}
          </h1>
        </div>
      </div>

      {provenance.length > 0 && (
        <dl className="mt-6 space-y-2 text-sm leading-6 text-slate-600 dark:text-slate-300">
          {provenance.map((item) => <div key={item}>{item}</div>)}
        </dl>
      )}

      <section className="mt-6 border-t border-border pt-6" aria-labelledby="excerpt-title">
        <h2 id="excerpt-title" className="text-lg font-semibold text-slate-950 dark:text-slate-50">Đoạn nội dung hệ thống đã truy xuất</h2>
        <p className="mt-4 whitespace-pre-wrap text-base leading-7 text-slate-800 dark:text-slate-100">
          {citation.excerpt || "Ca cũ chỉ lưu mã citation, chưa lưu đoạn nội dung nguồn."}
        </p>
      </section>

      {sourceUri && (
        <a
          href={sourceUri}
          target="_blank"
          rel="noreferrer noopener"
          className="mt-6 inline-flex min-h-11 items-center gap-2 rounded-lg bg-sky-700 px-4 font-semibold text-white hover:bg-sky-800 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-sky-600 focus-visible:ring-offset-2"
        >
          Mở tài liệu gốc
          <ExternalLink className="size-5" aria-hidden="true" />
        </a>
      )}
    </article>
  );
}
