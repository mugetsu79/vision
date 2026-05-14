import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, test, vi } from "vitest";
import { MemoryRouter, Route, Routes } from "react-router-dom";

import { RequireAuth } from "@/components/auth/RequireAuth";
import { FirstRunPage } from "@/pages/FirstRun";
import { useAuthStore } from "@/stores/auth-store";

const bootstrapMocks = vi.hoisted(() => ({
  status: vi.fn(),
  complete: vi.fn(),
}));

vi.mock("@/hooks/use-bootstrap", () => ({
  useBootstrapStatus: () => bootstrapMocks.status() as unknown,
  useCompleteBootstrap: () => ({
    mutateAsync: bootstrapMocks.complete,
    isPending: false,
  }),
}));

function renderFirstRun(initialPath = "/first-run") {
  return render(
    <MemoryRouter initialEntries={[initialPath]}>
      <Routes>
        <Route path="/first-run" element={<FirstRunPage />} />
        <Route path="/signin" element={<div>Sign-in route</div>} />
      </Routes>
    </MemoryRouter>,
  );
}

describe("FirstRunPage", () => {
  beforeEach(() => {
    bootstrapMocks.status.mockReset();
    bootstrapMocks.complete.mockReset();
    bootstrapMocks.status.mockReturnValue({
      data: {
        first_run_required: true,
        has_active_local_token: true,
        active_token_expires_at: "2026-05-14T08:15:00Z",
        completed_at: null,
        tenant_slug: null,
      },
      isLoading: false,
      isError: false,
    });
    bootstrapMocks.complete.mockResolvedValue({
      first_run_required: false,
      tenant_id: "00000000-0000-0000-0000-000000000001",
      tenant_slug: "vezor-pilot",
      admin_subject: "bootstrap:admin@vezor.local",
      completed_at: "2026-05-14T08:10:00Z",
      central_node: {
        id: "00000000-0000-0000-0000-000000000002",
        tenant_id: "00000000-0000-0000-0000-000000000001",
        node_kind: "central",
        edge_node_id: null,
        supervisor_id: "central-master",
        hostname: "macbook-pro-master",
        install_status: "installed",
        credential_status: "missing",
        service_manager: null,
        service_status: null,
        version: null,
        os_name: null,
        host_profile: null,
        last_service_reported_at: null,
        diagnostics: {},
        created_at: "2026-05-14T08:10:00Z",
        updated_at: "2026-05-14T08:10:00Z",
      },
    });
    useAuthStore.setState({
      status: "anonymous",
      user: null,
      accessToken: null,
    });
  });

  test("fresh install redirects an anonymous local user to first-run", async () => {
    render(
      <MemoryRouter initialEntries={["/dashboard"]}>
        <Routes>
          <Route
            path="/dashboard"
            element={
              <RequireAuth>
                <div>Dashboard route</div>
              </RequireAuth>
            }
          />
          <Route path="/first-run" element={<div>First-run route</div>} />
          <Route path="/signin" element={<div>Sign-in route</div>} />
        </Routes>
      </MemoryRouter>,
    );

    expect(await screen.findByText("First-run route")).toBeInTheDocument();
    expect(screen.queryByText("Sign-in route")).not.toBeInTheDocument();
  });

  test("requires bootstrap code and initial admin fields before completion", async () => {
    renderFirstRun();

    expect(
      screen.getByRole("heading", { name: /first-run setup/i }),
    ).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /complete setup/i })).toBeDisabled();

    await userEvent.type(screen.getByLabelText(/bootstrap code/i), "vzboot_local_once");
    await userEvent.type(screen.getByLabelText(/tenant name/i), "Vezor Pilot");
    await userEvent.type(screen.getByLabelText(/admin email/i), "admin@vezor.local");
    await userEvent.type(screen.getByLabelText(/admin password/i), "strong-password");
    await userEvent.type(screen.getByLabelText(/master node name/i), "macbook-pro-master");

    expect(screen.getByRole("button", { name: /complete setup/i })).toBeEnabled();
    expect(bootstrapMocks.complete).not.toHaveBeenCalled();
  });

  test("successful first-run completion routes to sign-in", async () => {
    const user = userEvent.setup();
    renderFirstRun();

    await user.type(screen.getByLabelText(/bootstrap code/i), "vzboot_local_once");
    await user.type(screen.getByLabelText(/tenant name/i), "Vezor Pilot");
    await user.type(screen.getByLabelText(/admin email/i), "admin@vezor.local");
    await user.type(screen.getByLabelText(/admin password/i), "strong-password");
    await user.type(screen.getByLabelText(/master node name/i), "macbook-pro-master");
    await user.type(screen.getByLabelText(/supervisor id/i), "central-master");
    await user.click(screen.getByRole("button", { name: /complete setup/i }));

    await waitFor(() =>
      expect(bootstrapMocks.complete).toHaveBeenCalledWith({
        bootstrap_token: "vzboot_local_once",
        tenant_name: "Vezor Pilot",
        tenant_slug: undefined,
        admin_email: "admin@vezor.local",
        admin_password: "strong-password",
        central_node_name: "macbook-pro-master",
        central_supervisor_id: "central-master",
      }),
    );
    expect(await screen.findByText("Sign-in route")).toBeInTheDocument();
  });
});
