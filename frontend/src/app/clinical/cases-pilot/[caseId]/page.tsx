import type { Metadata } from "next";

import { SimpleNurseCaseWorkspace } from "@/components/clinical/nurse-simple/SimpleNurseCaseWorkspace";

export const metadata: Metadata = {
  title: "Rà soát ca Triage Agent | Nurse Triage",
  description: "Rà soát dữ liệu, chốt ESI và đóng ca cho một phiên Triage Agent.",
};

export default async function SimpleNurseCasePage({
  params,
}: {
  params: Promise<{ caseId: string }>;
}) {
  const { caseId } = await params;
  return <SimpleNurseCaseWorkspace sessionId={caseId} />;
}
