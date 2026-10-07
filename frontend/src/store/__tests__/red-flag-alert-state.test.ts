import { beforeEach, describe, expect, it } from "vitest";

import { useTriageStore } from "@/store/useTriageStore";

const store = () => useTriageStore.getState();

describe("red flag alert presentation state", () => {
  beforeEach(() => {
    store().resetSession();
  });

  it("opens the inline alert when the backend reports an emergency", () => {
    store().triggerRedFlag("session-1:2");

    expect(store().redFlagTriggered).toBe(true);
    expect(store().redFlagAlertOpen).toBe(true);
  });

  it("never raises the client-side chat lock, which stays a backend decision", () => {
    store().triggerRedFlag("session-1:2");

    expect(store().isChatLocked).toBe(false);
  });

  it("keeps the session flagged after the patient closes the card", () => {
    store().triggerRedFlag("session-1:2");
    store().dismissRedFlagAlert();

    expect(store().redFlagAlertOpen).toBe(false);
    // The safety state survives dismissal; only the card collapses.
    expect(store().redFlagTriggered).toBe(true);
  });

  it("does not re-open a dismissed card when the same event is reported again", () => {
    store().triggerRedFlag("session-1:2");
    store().dismissRedFlagAlert();

    // Every refetch of the session replays is_red_flag_triggered.
    store().triggerRedFlag("session-1:2");
    store().triggerRedFlag("session-1:2");

    expect(store().redFlagAlertOpen).toBe(false);
    expect(store().redFlagTriggered).toBe(true);
  });

  it("opens a new alert when a different, more severe emergency arrives", () => {
    store().triggerRedFlag("session-1:2");
    store().dismissRedFlagAlert();

    store().triggerRedFlag("session-1:1");

    expect(store().redFlagAlertOpen).toBe(true);
  });

  it("lets the patient re-open the card they dismissed", () => {
    store().triggerRedFlag("session-1:2");
    store().dismissRedFlagAlert();
    store().reopenRedFlagAlert();

    expect(store().redFlagAlertOpen).toBe(true);
  });

  it("clears alert state when the workspace moves to another session", () => {
    store().triggerRedFlag("session-1:2");
    store().dismissRedFlagAlert();

    store().resetSession();

    expect(store().redFlagTriggered).toBe(false);
    expect(store().redFlagAlertOpen).toBe(false);
    expect(store().acknowledgedRedFlagKey).toBeNull();
    expect(store().activeRedFlagKey).toBeNull();
  });

  it("re-alerts in a new session even at the same acuity as a dismissed one", () => {
    store().triggerRedFlag("session-1:2");
    store().dismissRedFlagAlert();
    store().resetSession();

    store().triggerRedFlag("session-2:2");

    expect(store().redFlagAlertOpen).toBe(true);
  });
});
