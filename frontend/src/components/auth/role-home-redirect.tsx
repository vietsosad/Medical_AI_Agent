"use client";

import { useEffect, type ReactNode } from "react";
import { Loader2, ShieldCheck } from "lucide-react";
import { useRouter } from "next/navigation";

import { getHomeRouteForRole } from "@/lib/auth-routing";
import { useAuthStore } from "@/store/useAuthStore";

interface RoleHomeRedirectProps {
  children: ReactNode;
}

/** Keep the public landing page public while routing restored sessions home by role. */
export function RoleHomeRedirect({ children }: RoleHomeRedirectProps) {
  const router = useRouter();
  const { user, isAuthenticated, isLoading } = useAuthStore();

  const destination = isAuthenticated && user
    ? getHomeRouteForRole(user.role)
    : null;
  const shouldRedirect = destination !== null && destination !== "/";

  useEffect(() => {
    if (!isLoading && destination && destination !== "/") {
      router.replace(destination);
    }
  }, [destination, isLoading, router]);

  if (isLoading || (isAuthenticated && !user) || shouldRedirect) {
    return (
      <main
        className="flex min-h-[70vh] items-center justify-center bg-background p-6"
        aria-busy="true"
        aria-label="Đang xác định không gian làm việc theo vai trò"
      >
        <div className="flex items-center gap-3 rounded-xl border border-border bg-card px-5 py-4 text-sm font-medium text-slate-700 dark:text-slate-200">
          <span className="relative flex size-9 items-center justify-center rounded-lg bg-sky-50 text-sky-700">
            <ShieldCheck className="size-5" aria-hidden="true" />
            <Loader2 className="absolute -right-1 -top-1 size-4 animate-spin text-sky-700" aria-hidden="true" />
          </span>
          Đang chuyển tới không gian làm việc phù hợp...
        </div>
      </main>
    );
  }

  return <>{children}</>;
}

export default RoleHomeRedirect;
