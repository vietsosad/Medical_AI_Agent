import { describe, expect, it } from "vitest";

import {
  isFinalizedSbar,
  isSessionWritable,
  latestActionableQuestionId,
} from "@/lib/triage-ui-state";
import type { ChatMessage } from "@/types/triage-chat";

const message = (
  id: string,
  overrides: Partial<ChatMessage> = {},
): ChatMessage => ({
  id,
  sender: "bot",
  timestamp: "2026-08-20T00:00:00Z",
  content: id,
  step: 1,
  ...overrides,
});

describe("triage UI recovery state", () => {
  it("recovers the latest unanswered structured question", () => {
    const messages: ChatMessage[] = [
      message("older-question", {
        structured: { optionsType: "text_only", submitted: false },
      }),
      message("answered-question", {
        structured: { optionsType: "text_only", submitted: true },
      }),
      message("patient-message", {
        sender: "user",
        structured: { optionsType: "text_only", submitted: false },
      }),
      message("latest-question", {
        structured: { optionsType: "single", submitted: false, options: [] },
      }),
      message("later-non-question"),
    ];

    expect(latestActionableQuestionId(messages)).toBe("latest-question");
  });

  it("returns no active question after every structured prompt is submitted", () => {
    expect(
      latestActionableQuestionId([
        message("answered", {
          structured: { optionsType: "text_only", submitted: true },
        }),
        message("plain"),
      ]),
    ).toBeNull();
  });

  it("allows writes only for a non-red-flag IN_PROGRESS session", () => {
    expect(
      isSessionWritable({ status: "IN_PROGRESS", is_red_flag_triggered: false }),
    ).toBe(true);
    expect(
      isSessionWritable({ status: "IN_PROGRESS", is_red_flag_triggered: true }),
    ).toBe(false);
    expect(
      isSessionWritable({ status: "HITL_REVIEWING", is_red_flag_triggered: false }),
    ).toBe(false);
    expect(
      isSessionWritable({ status: "COMPLETED", is_red_flag_triggered: false }),
    ).toBe(false);
    expect(isSessionWritable(null)).toBe(false);
  });

  it("fails the finalized-output gate unless both signal and report exist", () => {
    expect(isFinalizedSbar({ sbar_finalized: true, sbar_summary: null })).toBe(false);
    expect(isFinalizedSbar({ sbar_finalized: false, sbar_summary: {} })).toBe(false);
    expect(isFinalizedSbar({ sbar_finalized: true, sbar_summary: {} })).toBe(true);
    expect(isFinalizedSbar(undefined)).toBe(false);
  });
});
