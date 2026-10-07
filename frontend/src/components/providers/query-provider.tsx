"use client";

import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { ReactQueryDevtools } from "@tanstack/react-query-devtools";
import { useState, type ReactNode } from "react";
import { Toaster } from "sonner";
import { AuthProvider } from "@/components/providers/auth-provider";

interface QueryProviderProps {
  children: ReactNode;
}

/**
 * ============================================================================
 * GLOBAL CLIENT PROVIDERS FOR TANSTACK QUERY V5 & TOASTS
 * ============================================================================
 * Quản lý vòng đời QueryClient trên nền tảng Next.js 15 App Router (SSR & Streaming)
 * đồng thời cấu hình hệ thống Toaster thông báo chuẩn lâm sàng từ sonner.
 */
export function QueryProvider({ children }: QueryProviderProps) {
  // Khởi tạo QueryClient bên trong useState để bảo toàn cache độc lập cho từng request SSR/Client
  const [queryClient] = useState(
    () =>
      new QueryClient({
        defaultOptions: {
          queries: {
            staleTime: 5 * 60 * 1000, // 5 phút default
            gcTime: 15 * 60 * 1000,
            refetchOnWindowFocus: false,
            retry: 1,
          },
        },
      })
  );

  return (
    <QueryClientProvider client={queryClient}>
      <AuthProvider>
        {children}
      </AuthProvider>
      <Toaster position="top-right" richColors closeButton duration={4000} />
      <ReactQueryDevtools initialIsOpen={false} />
    </QueryClientProvider>
  );
}
