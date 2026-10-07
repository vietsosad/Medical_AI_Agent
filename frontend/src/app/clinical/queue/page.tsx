import type { Metadata } from "next";
import { redirect } from "next/navigation";

import { NurseQueueWorkspace } from "@/components/clinical/nurse/NurseQueueWorkspace";
import { IS_PILOT_AGENT_ACTIVE } from "@/lib/agent-mode";

export const metadata: Metadata = {
  title: "Hàng đợi lâm sàng | AI Triage",
  description: "Hàng đợi Triage ưu tiên theo Red Flag, ESI và thời gian chờ.",
};

export default async function NurseQueuePage({
  searchParams,
}: {
  searchParams: Promise<{ mine?: string; specialist?: string }>;
}) {
  // Lưới an toàn: trang này không bao giờ mang theo 1 case id cụ thể (kể cả
  // với ?mine=/?specialist=), nên an toàn để chuyển hẳn sang hàng đợi pilot
  // khi cờ đang bật -- cùng pattern redirect() đã dùng ở các trang "tuyến cũ"
  // khác trong thư mục này (clinical/page.tsx, emergency-feed, ...).
  if (IS_PILOT_AGENT_ACTIVE) {
    redirect("/clinical/queue-pilot");
  }

  const { mine, specialist } = await searchParams;
  return (
    <NurseQueueWorkspace
      mineOnly={mine === "1"}
      specialistOnly={specialist === "1"}
    />
  );
}
