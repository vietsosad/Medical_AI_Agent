"use client";

import React, { Suspense } from "react";
import { usePathname } from "next/navigation";
import { SimplePilotSidebar } from "@/components/chat/SimplePilotSidebar";

/**
 * Same flex-row shell as production's `(patient)/triage/layout.tsx` (sidebar
 * + card), forked only because the sidebar itself needs a different data
 * source (`SimplePilotSidebar` vs `TriageSidebar` -- see that file for why).
 *
 * Production's own `/history` is a fully separate top-level route (sibling
 * of `/triage`, never wrapped by `triage/layout.tsx`), which is why it has
 * no sidebar and uses the full page width. `/triage-pilot/history` had to
 * stay a *child* route of `/triage-pilot` here (same URL, same "Lịch sử khám
 * pilot" links already pointing at it elsewhere) -- restructuring it to a
 * true sibling would change the URL. Reaching the same "no sidebar, full
 * width" result without moving the route: this layout checks `usePathname()`
 * and skips the sidebar + width cap for `/triage-pilot/history` and its
 * `[id]` detail page, while `/triage-pilot` itself (the chat screen) keeps
 * the sidebar exactly as before.
 */
export default function TriagePilotLayout({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const isHistorySection = pathname?.startsWith("/triage-pilot/history") ?? false;

  if (isHistorySection) {
    return (
      <div className="w-full h-[calc(100vh-120px)] md:h-[85vh] min-h-[600px]">
        <div className="h-full w-full overflow-hidden bg-card rounded-3xl shadow-sm border border-border relative">
          <Suspense fallback={<div className="h-full animate-pulse bg-muted" />}>
            {children}
          </Suspense>
        </div>
      </div>
    );
  }

  return (
    <div className="flex flex-col md:flex-row w-full h-[calc(100vh-120px)] md:h-[85vh] min-h-[600px] gap-4">
      <div className="hidden md:block w-72 lg:w-80 shrink-0 h-full">
        <Suspense fallback={<div className="h-full animate-pulse rounded-3xl bg-muted" />}>
          <SimplePilotSidebar />
        </Suspense>
      </div>

      <div className="flex-1 h-full overflow-hidden bg-card rounded-3xl shadow-sm border border-border relative">
        <Suspense fallback={<div className="h-full animate-pulse bg-muted" />}>
          {children}
        </Suspense>
      </div>
    </div>
  );
}
