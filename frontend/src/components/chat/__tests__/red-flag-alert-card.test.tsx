import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { RedFlagAlertCard } from "@/components/chat/RedFlagAlertCard";
import { useTriageStore } from "@/store/useTriageStore";

vi.mock("@/hooks/queries/use-clinical-profile", () => ({
  useEmergencyContacts: () => ({ data: [] }),
}));

const store = () => useTriageStore.getState();

describe("inline red flag alert card", () => {
  beforeEach(() => {
    store().resetSession();
  });

  it("renders nothing while no emergency has been reported", () => {
    const { container } = render(<RedFlagAlertCard />);
    expect(container).toBeEmptyDOMElement();
  });

  it("shows an in-conversation alert rather than a full-screen overlay", () => {
    store().triggerRedFlag("session-1:2");
    render(<RedFlagAlertCard />);

    const alert = screen.getByRole("alert");
    expect(alert).toBeInTheDocument();
    expect(alert.className).not.toMatch(/fixed|inset-0/);
  });

  it("dials the national emergency line through a real tel: link", () => {
    store().triggerRedFlag("session-1:2");
    render(<RedFlagAlertCard />);

    expect(screen.getByRole("link", { name: /Gọi cấp cứu 115/i })).toHaveAttribute(
      "href",
      "tel:115",
    );
  });

  it("collapses to a re-openable chip once the patient closes it", async () => {
    const user = userEvent.setup();
    store().triggerRedFlag("session-1:2");
    const { rerender } = render(<RedFlagAlertCard />);

    await user.click(screen.getByRole("button", { name: /Đóng cảnh báo khẩn cấp/i }));
    rerender(<RedFlagAlertCard />);

    expect(screen.queryByRole("alert")).not.toBeInTheDocument();
    const chip = screen.getByRole("button", { name: /Khuyến nghị khẩn cấp/i });
    expect(chip).toBeInTheDocument();

    await user.click(chip);
    rerender(<RedFlagAlertCard />);
    expect(screen.getByRole("alert")).toBeInTheDocument();
  });

  it('also closes from the "Tôi đã biết" acknowledgement button', async () => {
    const user = userEvent.setup();
    store().triggerRedFlag("session-1:2");
    const { rerender } = render(<RedFlagAlertCard />);

    await user.click(screen.getByRole("button", { name: "Tôi đã biết" }));
    rerender(<RedFlagAlertCard />);

    expect(screen.queryByRole("alert")).not.toBeInTheDocument();
    // Dismissing is presentation only: the session stays flagged.
    expect(store().redFlagTriggered).toBe(true);
  });

  it("keeps the waiting-for-help guidance that the old overlay carried", () => {
    store().triggerRedFlag("session-1:2");
    render(<RedFlagAlertCard />);

    expect(screen.getByText(/Trong khi chờ hỗ trợ/i)).toBeInTheDocument();
    expect(screen.getByText(/Không tự lái xe/i)).toBeInTheDocument();
  });
});
