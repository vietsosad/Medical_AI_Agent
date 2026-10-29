"use client";

import React, { Suspense } from "react";
import { usePathname } from "next/navigation";

/**
 * Khung chung của khu `/triage-pilot`.
 *
 * Màn hội thoại tự dựng bố cục hai cột của nó (khung chat + cột "Mình đã ghi
 * nhận"), nên ở đây chỉ còn việc cấp chiều cao cố định để khung chat cuộn bên
 * trong và ô nhập luôn ghim ở đáy. Danh sách phiên cũ nằm ở trang Lịch sử,
 * không chiếm chỗ cạnh cuộc trò chuyện đang diễn ra nữa.
 *
 * `/triage-pilot/history` vẫn là route con (giữ nguyên URL mà các liên kết
 * khác đang trỏ tới) nhưng được dựng toàn chiều rộng, cuộn theo trang.
 */
export default function TriagePilotLayout({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const isHistorySection = pathname?.startsWith("/triage-pilot/history") ?? false;

  // Trang lịch sử cuộn theo trang, không lồng một vùng cuộn cố định chiều cao
  // vào trong (trên điện thoại vùng đó còn nằm dưới thanh điều hướng đáy).
  if (isHistorySection) {
    return (
      <div className="w-full">
        <Suspense fallback={<div className="skeleton-sweep relative h-64 overflow-hidden rounded-3xl bg-muted" />}>
          {children}
        </Suspense>
      </div>
    );
  }

  return (
    <div className="h-[calc(100dvh-7.5rem)] min-h-[560px] w-full">
      <Suspense fallback={<div className="skeleton-sweep relative h-full overflow-hidden rounded-3xl bg-muted" />}>
        {children}
      </Suspense>
    </div>
  );
}
