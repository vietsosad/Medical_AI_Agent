/**
 * Single on/off switch deciding whether the app's *entry-point* navigation
 * (top navbar, nurse sidebar, "bắt đầu khám mới"/"xem lịch sử" CTAs, the
 * post-login home route for nurses) points at the `simple_agent` pilot
 * screens (`/triage-pilot`, `/triage-pilot/history`, `/clinical/queue-pilot`)
 * or production's DeepAgent screens (`/triage`, `/history`, `/clinical/queue`).
 * Read once at module load, like every other `NEXT_PUBLIC_*` var in this
 * codebase (inlined at build time by Next.js either way) -- see
 * `.claude/plans/sunny-launching-mitten.md` for the full investigation this
 * came from.
 *
 * IMPORTANT invariant: these helpers are for entry points that don't carry
 * an existing case/session id yet. Any link that already has a real id
 * (`?session_id=...`, `/history/{id}`, `/clinical/cases/{id}`) must NEVER be
 * rebuilt through these -- `TriageCase.id` (production) and
 * `SimpleAgentChatSession.session_id` (pilot) are two independent tables;
 * an id from one has no meaning in the other and would just 404. Only
 * "start something new" / "show me the general list" navigation switches.
 */
export const IS_PILOT_AGENT_ACTIVE = process.env.NEXT_PUBLIC_TRIAGE_PILOT_ACTIVE === "YES";

/** Where "bắt đầu khám mới" (no session id yet) should point. */
export function triageStartHref(): string {
  return IS_PILOT_AGENT_ACTIVE ? "/triage-pilot" : "/triage";
}

/** Where "xem lịch sử khám" (the list, not one specific case) should point. */
export function triageHistoryListHref(): string {
  return IS_PILOT_AGENT_ACTIVE ? "/triage-pilot/history" : "/history";
}

/** Where the nurse's general queue entry point (not one specific case) should point. */
export function nurseQueueHref(): string {
  return IS_PILOT_AGENT_ACTIVE ? "/clinical/queue-pilot" : "/clinical/queue";
}
