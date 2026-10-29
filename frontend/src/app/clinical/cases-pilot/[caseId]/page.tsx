import type { Metadata } from "next";

import { SimpleNurseCaseWorkspace } from "@/components/clinical/nurse-simple/SimpleNurseCaseWorkspace";

export const metadata: Metadata = {
  title: "Hồ sơ ca và bàn quyết định | AI Triage",
  description: "Đọc hồ sơ ca Triage Agent, đối chiếu căn cứ của AI rồi xác nhận hoặc điều chỉnh mức ESI.",
};

export default async function SimpleNurseCasePage({
  params,
  searchParams,
}: {
  params: Promise<{ caseId: string }>;
  searchParams: Promise<Record<string, string | string[] | undefined>>;
}) {
  const [{ caseId }, query] = await Promise.all([params, searchParams]);
  // `?openChat=1` từ hộp thư "Tin nhắn mới": mở sẵn kênh nhắn tin với người bệnh.
  return <SimpleNurseCaseWorkspace sessionId={caseId} openChat={query.openChat === "1"} />;
}
