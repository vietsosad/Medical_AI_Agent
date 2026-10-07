import { describe, expect, it } from "vitest";

import {
  getHistorySessionHref,
  hasFinalizedSbar,
  isActiveTriageSession,
  isResumableTriageSession,
} from "@/components/history/history-session-state";
import type { TriageSessionDetailDTO } from "@/types/clinical-history";
import { dedupeHistoryItems } from "@/hooks/queries/use-triage-history";

const baseSession: TriageSessionDetailDTO = {
  session_id: "session-1",
  chief_complaint: "Đau ngực",
  created_at: "2026-08-20T00:00:00Z",
  status: "IN_PROGRESS",
  final_esi: null,
  hitl_status: "PENDING_REVIEW",
  sbar_snippet: "",
  sbar_finalized: false,
  messages: [],
  sbar_report: null,
  hitl_signature: null,
};

describe("history session lifecycle", () => {
  it("distinguishes resumable intake from active HITL review", () => {
    expect(isActiveTriageSession("IN_PROGRESS")).toBe(true);
    expect(isResumableTriageSession("IN_PROGRESS")).toBe(true);

    expect(isActiveTriageSession("HITL_REVIEWING")).toBe(true);
    expect(isResumableTriageSession("HITL_REVIEWING")).toBe(false);
  });

  it("routes active sessions to triage and terminal sessions to history detail", () => {
    expect(getHistorySessionHref(baseSession)).toBe("/triage?session_id=session-1");
    expect(
      getHistorySessionHref({ ...baseSession, status: "HITL_REVIEWING" }),
    ).toBe("/triage?session_id=session-1");
    expect(getHistorySessionHref({ ...baseSession, status: "COMPLETED" })).toBe(
      "/history/session-1",
    );
    expect(getHistorySessionHref({ ...baseSession, status: "CANCELLED" })).toBe(
      "/history/session-1",
    );
  });

  it("keeps one current case per backend session id", () => {
    const activeItem = { ...baseSession };
    const duplicate = { ...baseSession, chief_complaint: "Bản sao cache cũ" };

    expect(dedupeHistoryItems([activeItem, duplicate])).toEqual([activeItem]);
  });
});

describe("finalized SBAR gate", () => {
  const report = {
    situation: "Tình trạng",
    background: "Tiền sử",
    assessment: "Đánh giá",
    recommendation: "Khuyến nghị",
    citations: ["PROTOCOL-1"],
  };

  it("fails closed when either the finalized signal or report is missing", () => {
    expect(
      hasFinalizedSbar({ ...baseSession, sbar_finalized: false, sbar_report: report }),
    ).toBe(false);
    expect(
      hasFinalizedSbar({ ...baseSession, sbar_finalized: true, sbar_report: null }),
    ).toBe(false);
  });

  it("opens only when the explicit signal and persisted report are both present", () => {
    expect(
      hasFinalizedSbar({ ...baseSession, sbar_finalized: true, sbar_report: report }),
    ).toBe(true);
  });
});
