import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import {
  SimplePilotEsiBadge,
  SimplePilotNurseDecisionSummary,
} from "@/components/chat/SimplePilotNurseDecisionSummary";

describe("SimplePilotNurseDecisionSummary", () => {
  it("shows the AI proposal, nurse final ESI, and persisted note for an adjustment", () => {
    render(
      <SimplePilotNurseDecisionSummary
        aiProposedEsi={4}
        finalEsi={2}
        reviewStatus="OVERRIDDEN"
        reviewerName="Điều dưỡng Minh Anh"
        reviewedAt="2026-08-31T09:30:00Z"
        decisionNote="Đau tăng nhanh, cần được đánh giá ưu tiên."
      />,
    );

    expect(screen.getByText("AI đề xuất: ESI 4")).toBeInTheDocument();
    expect(screen.getByText("Kết quả điều dưỡng: ESI 2")).toBeInTheDocument();
    expect(screen.getByText(/Đau tăng nhanh, cần được đánh giá ưu tiên/)).toBeInTheDocument();
    expect(screen.getByText(/Điều dưỡng Minh Anh đã lưu quyết định/)).toBeInTheDocument();
  });

  it("makes an adjusted ESI transition visible in compact history UI", () => {
    render(<SimplePilotEsiBadge aiProposedEsi={4} finalEsi={2} reviewStatus="OVERRIDDEN" />);

    expect(screen.getByText("ESI 4 → ESI 2")).toBeInTheDocument();
  });
});
