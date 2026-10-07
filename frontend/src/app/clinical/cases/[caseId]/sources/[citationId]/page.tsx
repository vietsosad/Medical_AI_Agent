import type { Metadata } from "next";

import { CitationSourceWorkspace } from "@/components/clinical/nurse/CitationSourceWorkspace";

export const metadata: Metadata = {
  title: "Nguồn tham chiếu | Nurse Triage",
  description: "Nội dung nguồn RAG đã hỗ trợ đề xuất phân luồng.",
};

export default async function CitationSourcePage({
  params,
}: {
  params: Promise<{ caseId: string; citationId: string }>;
}) {
  const { caseId, citationId } = await params;
  return <CitationSourceWorkspace caseId={caseId} citationId={citationId} />;
}
