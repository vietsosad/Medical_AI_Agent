import type { Metadata } from "next";

import { SimpleNurseQueueWorkspace } from "@/components/clinical/nurse-simple/SimpleNurseQueueWorkspace";

export const metadata: Metadata = {
  title: "Hàng đợi Triage Agent | AI Triage",
  description: "Hàng đợi thẩm định dành riêng cho các ca chạy trên Triage Agent -- tách biệt hàng đợi chính.",
};

export default function SimpleNurseQueuePage() {
  return <SimpleNurseQueueWorkspace />;
}
