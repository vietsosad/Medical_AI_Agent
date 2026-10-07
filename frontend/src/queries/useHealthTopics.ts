"use client";

import { useQuery, type UseQueryResult } from "@tanstack/react-query";

import {
  healthService,
  type HealthTopicDetailDTO,
  type HealthTopicSummaryDTO,
} from "@/services/health.service";

export const HEALTH_TOPIC_QUERY_KEYS = {
  all: ["health-topics"] as const,
  detail: (slug: string) => ["health-topics", slug] as const,
};

/**
 * Nội dung sức khỏe đổi rất chậm (chỉ khi chạy lại lệnh seed), nên giữ cache lâu
 * để trang chủ không gọi lại API mỗi lần điều hướng.
 */
const HEALTH_CONTENT_STALE_MS = 30 * 60 * 1000;

export function useHealthTopics(): UseQueryResult<HealthTopicSummaryDTO[], Error> {
  return useQuery({
    queryKey: HEALTH_TOPIC_QUERY_KEYS.all,
    queryFn: () => healthService.getTopics(),
    staleTime: HEALTH_CONTENT_STALE_MS,
    gcTime: 60 * 60 * 1000,
    retry: 1,
    refetchOnWindowFocus: false,
  });
}

export function useHealthTopicDetail(
  slug: string | null,
): UseQueryResult<HealthTopicDetailDTO, Error> {
  return useQuery({
    queryKey: HEALTH_TOPIC_QUERY_KEYS.detail(slug ?? "inactive"),
    queryFn: () => healthService.getTopicBySlug(slug as string),
    enabled: Boolean(slug),
    staleTime: HEALTH_CONTENT_STALE_MS,
    gcTime: 60 * 60 * 1000,
    retry: 1,
    refetchOnWindowFocus: false,
  });
}
