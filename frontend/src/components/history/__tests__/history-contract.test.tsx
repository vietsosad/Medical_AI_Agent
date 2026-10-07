import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { SbarViewerCard } from "@/components/history/SbarViewerCard";
import { TriageSessionDetailSchema } from "@/lib/validations/clinical-history.schema";

const sbar = {
  situation: "Tình trạng đã lưu",
  background: "Tiền sử đã lưu",
  assessment: "Đánh giá đã lưu",
  recommendation: "Khuyến nghị đã lưu",
  citations: ["PROTOCOL-1"],
};

describe("history replay contract", () => {
  it("preserves canonical authority citations and non-authoritative case support", () => {
    const parsed = TriageSessionDetailSchema.parse({
      session_id: "session-1",
      chief_complaint: "",
      created_at: "2026-08-20T00:00:00Z",
      status: "IN_PROGRESS",
      final_esi: null,
      hitl_status: "PENDING_REVIEW",
      sbar_snippet: "",
      sbar_finalized: false,
      sbar_report: null,
      hitl_signature: null,
      messages: [
        {
          id: "message-1",
          sender: "bot",
          timestamp: "2026-08-20T00:00:01Z",
          content: "Nội dung",
          step: 1,
          ragCitations: [
            {
              id: "citation-1",
              title: "Phác đồ",
              protocolId: "PROTOCOL-1",
              excerpt: "Đoạn bằng chứng",
              sourceType: "validated_protocol",
              validationStatus: "approved",
            },
          ],
          caseSupport: [
            {
              caseId: "case-1",
              excerpt: "Ca tương tự đã khử định danh",
              similarityScore: 0.82,
              retrievalScope: "CASE_SUPPORT",
              authorityStatus: "NOT_PROTOCOL",
              sourceType: "case_example",
            },
          ],
        },
      ],
    });

    expect(parsed.messages[0]?.ragCitations?.[0]?.protocolId).toBe("PROTOCOL-1");
    expect(parsed.messages[0]?.caseSupport?.[0]).toMatchObject({
      caseId: "case-1",
      retrievalScope: "CASE_SUPPORT",
      authorityStatus: "NOT_PROTOCOL",
    });
  });

  it("accepts the backend CANCELLED lifecycle without treating it as resumable", () => {
    const parsed = TriageSessionDetailSchema.parse({
      session_id: "session-cancelled",
      chief_complaint: "",
      created_at: "2026-08-20T00:00:00Z",
      status: "CANCELLED",
      final_esi: null,
      hitl_status: "PENDING_REVIEW",
      sbar_snippet: "",
      sbar_finalized: false,
      messages: [],
      sbar_report: null,
      hitl_signature: null,
    });

    expect(parsed.status).toBe("CANCELLED");
  });
});

describe("SBAR viewer authorization", () => {
  it("renders nothing until the explicit finalized signal is true", () => {
    const { container } = render(<SbarViewerCard sbar={sbar} sbarFinalized={false} />);

    expect(container).toBeEmptyDOMElement();
  });

  it("renders only the supplied finalized report and source codes", () => {
    render(<SbarViewerCard sbar={sbar} sbarFinalized />);

    expect(screen.getByText("Tình trạng đã lưu")).toBeInTheDocument();
    expect(screen.getByText("PROTOCOL-1")).toBeInTheDocument();
    expect(screen.queryByText(/Bộ Y tế/i)).not.toBeInTheDocument();
  });
});
