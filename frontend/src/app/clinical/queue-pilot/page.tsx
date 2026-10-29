import type { Metadata } from "next";
import { Suspense } from "react";

import { SimpleNurseQueueWorkspace } from "@/components/clinical/nurse-simple/SimpleNurseQueueWorkspace";
import { QueueSkeleton } from "@/components/clinical/nurse-simple/queue/QueueStates";

export const metadata: Metadata = {
  title: "Hàng đợi Triage Agent | AI Triage",
  description: "Hàng đợi thẩm định dành riêng cho các ca chạy trên Triage Agent -- tách biệt hàng đợi chính.",
};

export default function SimpleNurseQueuePage() {
  // Workspace đọc `?tab=` bằng useSearchParams: đặt ranh giới Suspense ngay
  // quanh nó (khuyến nghị của Next 16), khung chờ đúng hình hàng ca thật.
  return (
    <Suspense fallback={<QueueSkeleton />}>
      <SimpleNurseQueueWorkspace />
    </Suspense>
  );
}
