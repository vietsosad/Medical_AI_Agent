import { render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import type { NurseQueueItemDTO } from "@/types/clinical-hitl";

const hooks = vi.hoisted(() => ({
  useNurseQueue: vi.fn(),
  useAcknowledgeAlert: vi.fn(),
}));

vi.mock("@/hooks/queries/use-clinical-hitl", () => ({
  useNurseQueue: hooks.useNurseQueue,
}));

vi.mock("@/hooks/mutations/use-hitl-mutations", () => ({
  useAcknowledgeAlert: hooks.useAcknowledgeAlert,
}));

const { GlobalRedFlagAlert } = await import(
  "@/components/clinical/nurse/GlobalRedFlagAlert"
);

const RED_FLAG_CASE: NurseQueueItemDTO = {
  case_id: "case/red flag 01",
  patient_name: "E2E_AUDIT_Simulated Patient",
  masked_patient_label: "E2E_AUDIT_Simulated Patient",
  age: null,
  sex: null,
  chief_complaint: "Tôi thấy tức ngực mấy hôm nay.",
  ai_recommended_esi: 2,
  red_flags: ["chest_pain"],
  is_red_flag: true,
  waiting_since: "2026-08-27T00:00:00Z",
  wait_time_seconds: 60,
  review_status: "WAITING_REVIEW",
  assignee: null,
  data_completeness: { is_complete: false, missing_fields: ["vitals"] },
  case_version: 3,
  alert_acknowledged: false,
  unread_count: 0,
  last_message_at: null,
};

function setupAlert() {
  hooks.useNurseQueue.mockReturnValue({
    data: {
      items: [RED_FLAG_CASE],
      summary: {
        total_waiting: 1,
        urgent_count: 1,
        mine_count: 0,
        specialist_count: 0,
        longest_wait_seconds: 60,
      },
      sla_target_minutes: null,
    },
  });
  hooks.useAcknowledgeAlert.mockReturnValue({
    mutate: vi.fn(),
    isPending: false,
  });
}

describe("cảnh báo Red Flag toàn cục cho điều dưỡng", () => {
  afterEach(() => Object.values(hooks).forEach((hook) => hook.mockReset()));

  it("mở thẳng hồ sơ lâm sàng khi chọn mã định danh người bệnh", () => {
    setupAlert();
    render(<GlobalRedFlagAlert />);

    expect(
      screen.getByRole("link", {
        name: "Mở hồ sơ lâm sàng của E2E_AUDIT_Simulated Patient",
      }),
    ).toHaveAttribute("href", "/clinical/cases/case%2Fred%20flag%2001");
  });
});
