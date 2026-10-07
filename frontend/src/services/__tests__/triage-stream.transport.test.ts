import { afterEach, describe, expect, it, vi } from "vitest";

import {
  TriageStreamError,
  triageService,
} from "@/services/triage.service";
import type { AgentStreamEvent } from "@/types/triage-chat";

function responseFromChunks(chunks: string[]): Response {
  const encoder = new TextEncoder();
  let index = 0;
  const reader = {
    read: vi.fn(async () => {
      if (index >= chunks.length) {
        return { done: true as const, value: undefined };
      }
      const value = encoder.encode(chunks[index]);
      index += 1;
      return { done: false as const, value };
    }),
    releaseLock: vi.fn(),
  };

  return {
    status: 200,
    ok: true,
    body: { getReader: () => reader },
  } as unknown as Response;
}

const eventWire = (event: object): string => `data: ${JSON.stringify(event)}\r\n\r\n`;

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("triage SSE transport", () => {
  it("reassembles fragmented CRLF frames and returns the typed result", async () => {
    const accepted = {
      type: "accepted",
      message: "Đã tiếp nhận",
      sequence: 0,
      elapsedMs: 0,
      timestamp: "2026-08-20T00:00:00Z",
    };
    const terminal = {
      type: "result",
      message: "Hoàn tất",
      sequence: 1,
      elapsedMs: 25,
      timestamp: "2026-08-20T00:00:01Z",
      result: {
        id: "message-result",
        sender: "bot",
        timestamp: "2026-08-20T00:00:01Z",
        content: "Câu hỏi tiếp theo",
        step: 2,
        responseType: "STRUCTURED_QUESTION",
        decisionStatus: "COLLECTING",
        workflowPhase: "CLARIFICATION",
      },
    };
    const wire = eventWire(accepted) + eventWire(terminal);
    const firstBoundary = wire.indexOf("\r\n\r\n");
    const chunks = [
      wire.slice(0, 5),
      wire.slice(5, firstBoundary + 1),
      wire.slice(firstBoundary + 1, firstBoundary + 3),
      wire.slice(firstBoundary + 3, wire.length - 3),
      wire.slice(wire.length - 3),
    ];
    const fetchMock = vi.fn().mockResolvedValue(responseFromChunks(chunks));
    vi.stubGlobal("fetch", fetchMock);
    const progress: AgentStreamEvent[] = [];

    const result = await triageService.submitChatTurnStream(
      "session-1",
      { message: "Tiếp tục" },
      (event) => progress.push(event),
    );

    expect(result).toMatchObject({
      id: "message-result",
      decisionStatus: "COLLECTING",
      retrievalDegradedModes: [],
      sbarFinalized: false,
    });
    expect(progress.map((event) => event.type)).toEqual(["accepted", "result"]);
    expect(fetchMock).toHaveBeenCalledOnce();
  });

  it("surfaces a terminal SSE error with its code and retryability", async () => {
    const terminalError = {
      type: "error",
      message: "Không thể truy xuất bằng chứng",
      sequence: 1,
      elapsedMs: 20,
      timestamp: "2026-08-20T00:00:01Z",
      retryable: true,
      errorCode: "RETRIEVAL_UNAVAILABLE",
    };
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(responseFromChunks([eventWire(terminalError)])),
    );

    const request = triageService.submitChatTurnStream(
      "session-1",
      { message: "Tiếp tục" },
      () => undefined,
    );

    await expect(request).rejects.toMatchObject({
      name: "TriageStreamError",
      message: "Không thể truy xuất bằng chứng",
      errorCode: "RETRIEVAL_UNAVAILABLE",
      retryable: true,
    } satisfies Partial<TriageStreamError>);
  });

  it("preserves AbortError identity and forwards the caller signal", async () => {
    const controller = new AbortController();
    const abortError = new DOMException("The operation was aborted", "AbortError");
    const fetchMock = vi.fn().mockRejectedValue(abortError);
    vi.stubGlobal("fetch", fetchMock);

    await expect(
      triageService.submitChatTurnStream(
        "session-1",
        { message: "Tiếp tục" },
        () => undefined,
        controller.signal,
      ),
    ).rejects.toBe(abortError);

    expect(fetchMock).toHaveBeenCalledWith(
      expect.stringContaining("/api/v1/triage/chat/session-1"),
      expect.objectContaining({ signal: controller.signal }),
    );
  });
});
