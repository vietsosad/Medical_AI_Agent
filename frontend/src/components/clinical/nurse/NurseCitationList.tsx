import { FileText } from "lucide-react";
import Link from "next/link";

import type { NurseCaseDetailDTO } from "@/types/clinical-hitl";

interface NurseCitationListProps {
  caseId: string;
  citations: NurseCaseDetailDTO["citations"];
}

export function NurseCitationList({ caseId, citations }: NurseCitationListProps) {
  if (citations.length === 0) {
    return <span className="text-muted-foreground">Chưa có dữ liệu</span>;
  }

  return (
    <ul className="space-y-2 text-base" aria-label="Danh sách nguồn tham chiếu">
      {citations.map((citation) => (
        <li key={citation.code}>
          <Link
            href={`/clinical/cases/${encodeURIComponent(caseId)}/sources/${encodeURIComponent(citation.code)}`}
            className="inline-flex min-h-11 items-center gap-2 rounded-lg text-sky-800 underline decoration-sky-300 underline-offset-4 hover:text-sky-950 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-sky-600 focus-visible:ring-offset-2"
            aria-label={`Xem nguồn tham chiếu ${citation.code}`}
          >
            <FileText className="size-5 shrink-0" aria-hidden="true" />
            <span className="break-all">{citation.code}</span>
          </Link>
        </li>
      ))}
    </ul>
  );
}
