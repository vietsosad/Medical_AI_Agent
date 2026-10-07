export const TRIAGE_QUERY_KEYS = {
  all: ["triage"] as const,
  messages: (sessionId: string) =>
    [...TRIAGE_QUERY_KEYS.all, "messages", sessionId] as const,
  history: () => [...TRIAGE_QUERY_KEYS.all, "history"] as const,
  replayDetail: (sessionId: string) =>
    [...TRIAGE_QUERY_KEYS.all, "replay", sessionId] as const,
  careTeam: (sessionId: string) =>
    [...TRIAGE_QUERY_KEYS.all, "care-team", sessionId] as const,
};
