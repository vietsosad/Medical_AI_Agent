import { render, screen } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { PatientRoleGuard } from "@/components/auth/patient-role-guard";
import { useAuthStore, type UserProfile } from "@/store/useAuthStore";

const replace = vi.fn();
let currentPath = "/triage";

vi.mock("next/navigation", () => ({
  useRouter: () => ({ replace }),
  usePathname: () => currentPath,
}));

const patient: UserProfile = {
  id: "user-1",
  name: "Người Bệnh",
  email: "patient@example.com",
  role: "PATIENT",
};

const signOut = () =>
  useAuthStore.setState({ user: null, isAuthenticated: false, isLoading: false });

const signIn = (user: UserProfile) =>
  useAuthStore.setState({ user, isAuthenticated: true, isLoading: false });

const renderGuard = () =>
  render(
    <PatientRoleGuard>
      <p>Nội dung cổng bệnh nhân</p>
    </PatientRoleGuard>,
  );

describe("patient portal access", () => {
  beforeEach(() => {
    replace.mockClear();
    currentPath = "/triage";
  });

  afterEach(() => signOut());

  it.each(["/triage", "/history", "/history/session-1", "/profile", "/profile/ehr"])(
    "sends a signed-out visitor at %s to the existing login flow",
    (path) => {
      currentPath = path;
      signOut();
      renderGuard();

      expect(replace).toHaveBeenCalledWith("/auth/login?reason=auth_required");
      expect(screen.queryByText("Nội dung cổng bệnh nhân")).not.toBeInTheDocument();
    },
  );

  it("keeps the guest emergency entry point reachable without a session", () => {
    currentPath = "/triage/guest-session";
    signOut();
    renderGuard();

    expect(replace).not.toHaveBeenCalled();
    expect(screen.getByText("Nội dung cổng bệnh nhân")).toBeInTheDocument();
  });

  it("waits for hydration instead of bouncing a returning patient to login", () => {
    currentPath = "/triage";
    useAuthStore.setState({ user: null, isAuthenticated: false, isLoading: true });
    renderGuard();

    expect(replace).not.toHaveBeenCalled();
  });

  it("lets an authenticated patient through", () => {
    signIn(patient);
    renderGuard();

    expect(replace).not.toHaveBeenCalled();
    expect(screen.getByText("Nội dung cổng bệnh nhân")).toBeInTheDocument();
  });

  it("lets an emergency guest session through", () => {
    signIn({ ...patient, role: "GUEST" });
    renderGuard();

    expect(replace).not.toHaveBeenCalled();
    expect(screen.getByText("Nội dung cổng bệnh nhân")).toBeInTheDocument();
  });

  it("still routes clinical staff back to their own workspace", () => {
    signIn({ ...patient, role: "CLINICAL_NURSE" });
    renderGuard();

    expect(replace).toHaveBeenCalledWith("/clinical/queue");
  });
});
