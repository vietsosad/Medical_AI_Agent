import type { SimpleNurseQueueParams } from "@/types/simple-nurse";

export const SIMPLE_NURSE_QUERY_KEYS = {
  all: ["simple-nurse"] as const,
  // Params-less prefix -- use this (not `queue(params)`) for
  // `invalidateQueries`, so a claim/park/decision mutation refreshes every
  // open tab/filter/page combo, not just whichever one happens to match `{}`.
  queueAll: () => [...SIMPLE_NURSE_QUERY_KEYS.all, "queue"] as const,
  // Params in the key so TanStack Query caches per filter/tab/page combo
  // separately -- switching tabs or paging must not show stale data from a
  // different bucket.
  queue: (params: SimpleNurseQueueParams = {}) => [...SIMPLE_NURSE_QUERY_KEYS.queueAll(), params] as const,
  case: (sessionId: string) => [...SIMPLE_NURSE_QUERY_KEYS.all, "case", sessionId] as const,
  dashboard: () => [...SIMPLE_NURSE_QUERY_KEYS.all, "dashboard"] as const,
};
