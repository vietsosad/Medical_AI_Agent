import type { Metadata } from "next";

import { NurseCaseWorkspace } from "@/components/clinical/nurse/NurseCaseWorkspace";

export const metadata: Metadata = {
  title: "Rà soát ca | Nurse Triage",
  description: "Rà soát dữ liệu, chốt ESI và bàn giao ca Triage.",
};

export default async function NurseCasePage({
  params,
}: {
  params: Promise<{ caseId: string }>;
}) {
  const { caseId } = await params;
  return <NurseCaseWorkspace caseId={caseId} />;
}
