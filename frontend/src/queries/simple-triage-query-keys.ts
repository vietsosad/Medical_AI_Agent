export const SIMPLE_TRIAGE_QUERY_KEYS = {
  all: ["simple-triage"] as const,
  sessions: () => [...SIMPLE_TRIAGE_QUERY_KEYS.all, "sessions"] as const,
  session: (sessionId: string) =>
    [...SIMPLE_TRIAGE_QUERY_KEYS.all, "session", sessionId] as const,
};
