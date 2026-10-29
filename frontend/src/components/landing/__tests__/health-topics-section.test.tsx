import { render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { triageHrefForTopic } from "@/components/landing/HealthTopicsSection";
import { useAuthStore } from "@/store/useAuthStore";
import type { HealthTopicSummaryDTO } from "@/services/health.service";

const useHealthTopicsMock = vi.hoisted(() => vi.fn());

vi.mock("@/queries/useHealthTopics", () => ({
  useHealthTopics: useHealthTopicsMock,
  useHealthTopicDetail: () => ({ data: undefined, isLoading: false, isError: false }),
}));

const { HealthTopicsSection } = await import("@/components/landing/HealthTopicsSection");

const topic: HealthTopicSummaryDTO = {
  slug: "sot-xuat-huyet-dengue",
  name: "Sốt xuất huyết Dengue",
  summary: "Bệnh do virus Dengue lây qua muỗi vằn.",
  symptoms: ["Sốt cao đột ngột", "Đau đầu dữ dội", "Đau cơ", "Phát ban"],
  prevention: ["Ngủ màn", "Diệt lăng quăng"],
  source: "WHO",
  source_url: "https://www.who.int/",
  last_updated: "2026-08-22T00:00:00",
  ai_assisted: true,
};

const setState = (data: unknown, flags: { isLoading?: boolean; isError?: boolean } = {}) =>
  useHealthTopicsMock.mockReturnValue({
    data,
    isLoading: flags.isLoading ?? false,
    isError: flags.isError ?? false,
  });

describe("health topics section", () => {
  afterEach(() => {
    useAuthStore.setState({ user: null, isAuthenticated: false, isLoading: false });
    useHealthTopicsMock.mockReset();
  });

  it("renders the agreed heading and subtitle", () => {
    setState([topic]);
    render(<HealthTopicsSection />);

    expect(screen.getByRole("heading", { name: "Thông tin sức khỏe đáng chú ý" })).toBeInTheDocument();
    expect(
      screen.getByText(/Cập nhật các vấn đề sức khỏe đang được quan tâm và cách phòng ngừa/),
    ).toBeInTheDocument();
  });

  it("never claims these are the most common diseases", () => {
    setState([topic]);
    const { container } = render(<HealthTopicsSection />);
    expect(container.textContent).not.toMatch(/phổ biến nhất/i);
  });

  it("shows a topic card with its source and update date", () => {
    setState([topic]);
    render(<HealthTopicsSection />);

    expect(screen.getByRole("heading", { name: "Sốt xuất huyết Dengue" })).toBeInTheDocument();
    expect(screen.getByText(/Nguồn: WHO/)).toBeInTheDocument();
    expect(screen.getByText(/Cập nhật 22\/08\/2026/)).toBeInTheDocument();
  });

  it("marks a summary that the model rewrote", () => {
    setState([topic]);
    render(<HealthTopicsSection />);
    expect(screen.getByText("AI diễn giải")).toBeInTheDocument();
  });

  it("renders the empty state with the agreed wording", () => {
    setState([]);
    render(<HealthTopicsSection />);
    expect(screen.getByText("Hiện chưa có thông tin sức khỏe đáng chú ý.")).toBeInTheDocument();
  });

  it("degrades to an error message instead of breaking the homepage", () => {
    setState(undefined, { isError: true });
    render(<HealthTopicsSection />);

    expect(screen.getByText("Không thể tải thông tin sức khỏe lúc này.")).toBeInTheDocument();
    // Phần còn lại của section vẫn hiển thị.
    expect(screen.getByRole("heading", { name: "Thông tin sức khỏe đáng chú ý" })).toBeInTheDocument();
  });

  it("shows skeletons while loading", () => {
    setState(undefined, { isLoading: true });
    const { container } = render(<HealthTopicsSection />);
    expect(container.querySelectorAll(".skeleton-sweep").length).toBeGreaterThan(0);
  });

  it("carries the disclaimer that this does not replace a clinician", () => {
    setState([topic]);
    render(<HealthTopicsSection />);
    expect(screen.getByText(/không thay thế cho thăm khám/i)).toBeInTheDocument();
  });
});

describe("triage entry point from a health topic", () => {
  it("sends a signed-out reader through the existing login flow", () => {
    expect(triageHrefForTopic("sot-xuat-huyet-dengue", false)).toBe("/auth/login");
  });

  it("carries the topic as context once the reader has a session", () => {
    expect(triageHrefForTopic("sot-xuat-huyet-dengue", true)).toBe(
      "/triage?health_topic=sot-xuat-huyet-dengue",
    );
  });

  it("escapes a slug rather than trusting it into the URL", () => {
    expect(triageHrefForTopic("a b&c=d", true)).toBe("/triage?health_topic=a%20b%26c%3Dd");
  });
});
