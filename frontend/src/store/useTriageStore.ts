import { create } from "zustand";

/**
 * UI-only triage state.
 *
 * Clinical workflow, ESI, HITL, phases, and question progression live in the
 * backend session contract and TanStack Query. This store intentionally keeps
 * only local consent and the presentation state of the emergency alert.
 *
 * Detection is NOT owned here. `redFlagTriggered` mirrors a decision the
 * backend already made (`decision_status === "EMERGENCY_ESCALATED"` /
 * `session_status.is_red_flag_triggered`); this store never decides that a red
 * flag exists and never clears one the backend still reports.
 *
 * Whether a red-flagged session may still receive turns is likewise a backend
 * fact (`isSessionWritable`, plus a 400 on a `RED_FLAG_LOCKED` session), so
 * `triggerRedFlag` deliberately does not raise the client-side `isChatLocked`
 * flag: the alert is presentation, the lock is clinical state.
 */
export interface TriageState {
  hasConsented: boolean;
  isChatLocked: boolean;
  redFlagTriggered: boolean;
  /** Whether the inline emergency card is expanded inside the conversation. */
  redFlagAlertOpen: boolean;
  /** Identity of the emergency event currently being reported by the backend. */
  activeRedFlagKey: string | null;
  /** Identity of the event the patient already closed, so it stops re-opening. */
  acknowledgedRedFlagKey: string | null;
}

export interface TriageActions {
  setConsent: (consented: boolean) => void;
  /**
   * Record an emergency signal coming from the backend.
   *
   * `alertKey` identifies the clinical event (session + acuity). Re-reporting
   * the same event leaves a closed card closed; a different, escalated event
   * opens a fresh alert.
   */
  triggerRedFlag: (alertKey?: string) => void;
  dismissRedFlagAlert: () => void;
  reopenRedFlagAlert: () => void;
  clearRedFlag: () => void;
  setChatLocked: (locked: boolean) => void;
  resetSession: () => void;
}

export type TriageStore = TriageState & TriageActions;

const DEFAULT_ALERT_KEY = "active";

const INITIAL_SESSION_STATE = {
  isChatLocked: false,
  redFlagTriggered: false,
  redFlagAlertOpen: false,
  activeRedFlagKey: null,
  acknowledgedRedFlagKey: null,
} satisfies Omit<TriageState, "hasConsented">;

export const useTriageStore = create<TriageStore>((set) => ({
  hasConsented: false,
  ...INITIAL_SESSION_STATE,
  setConsent: (hasConsented) => set({ hasConsented }),
  triggerRedFlag: (alertKey = DEFAULT_ALERT_KEY) =>
    set((state) => ({
      redFlagTriggered: true,
      activeRedFlagKey: alertKey,
      // A repeat of an acknowledged event must not pop the card open again;
      // a new (more severe) event must.
      redFlagAlertOpen:
        state.acknowledgedRedFlagKey === alertKey ? state.redFlagAlertOpen : true,
    })),
  dismissRedFlagAlert: () =>
    set((state) => ({
      redFlagAlertOpen: false,
      acknowledgedRedFlagKey: state.activeRedFlagKey ?? DEFAULT_ALERT_KEY,
    })),
  reopenRedFlagAlert: () => set({ redFlagAlertOpen: true }),
  clearRedFlag: () => set({ ...INITIAL_SESSION_STATE }),
  setChatLocked: (isChatLocked) => set({ isChatLocked }),
  resetSession: () => set({ ...INITIAL_SESSION_STATE }),
}));
