import type { Metadata } from "next";

import { SimpleNurseDashboard } from "@/components/clinical/nurse-simple/SimpleNurseDashboard";

export const metadata: Metadata = {
  title: "Tổng quan trạm điều phối | AI Triage",
  description:
    "Số liệu tổng quan của hàng đợi Triage Agent: mức độ AI đề xuất, thời gian chờ tiếp nhận và quyết định của điều dưỡng.",
};

export default function SimpleNurseDashboardPage() {
  return <SimpleNurseDashboard />;
}
