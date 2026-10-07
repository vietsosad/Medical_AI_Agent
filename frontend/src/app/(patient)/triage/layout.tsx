import React from "react";
import { Suspense } from "react";
import { TriageSidebar } from "@/components/chat/TriageSidebar";

export default function TriageLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="flex flex-col md:flex-row w-full h-[calc(100vh-120px)] md:h-[85vh] min-h-[600px] gap-4">
      {/* Sidebar - Hiển thị trên Desktop, có thể ẩn/hiện trên Mobile nếu cần */}
      <div className="hidden md:block w-72 lg:w-80 shrink-0 h-full">
        <Suspense fallback={<div className="h-full animate-pulse rounded-3xl bg-muted" />}>
          <TriageSidebar />
        </Suspense>
      </div>

      {/* Main Chat Area */}
      <div className="flex-1 h-full overflow-hidden bg-card rounded-3xl shadow-sm border border-border relative">
        <Suspense fallback={<div className="h-full animate-pulse bg-muted" />}>
          {children}
        </Suspense>
      </div>
    </div>
  );
}
