import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { beforeEach, describe, expect, test, vi } from "vitest";

const bootstrapMocks = vi.hoisted(() => ({
  status: vi.fn(),
  complete: vi.fn(),
}));

vi.mock("@/hooks/use-platform-bootstrap", () => ({
  usePlatformBootstrapStatus: () => bootstrapMocks.status() as unknown,
  useCompletePlatformBootstrap: () => ({
    mutateAsync: bootstrapMocks.complete,
    isPending: false,
    isError: false,
    error: null,
  }),
}));

import { PlatformBootstrapPage } from "@/pages/PlatformBootstrap";

function renderPlatformBootstrapPage() {
  render(
    <MemoryRouter initialEntries={["/platform-bootstrap"]}>
      <Routes>
        <Route path="/platform-bootstrap" element={<PlatformBootstrapPage />} />
        <Route path="/signin" element={<div>Sign-in route</div>} />
      </Routes>
    </MemoryRouter>,
  );
}

describe("PlatformBootstrapPage", () => {
  beforeEach(() => {
    bootstrapMocks.status.mockReset();
    bootstrapMocks.complete.mockReset();
    bootstrapMocks.status.mockReturnValue({
      isLoading: false,
      data: { available: true, consumed_at: null },
    });
    bootstrapMocks.complete.mockResolvedValue({
      email: "owner@example.com",
      realm: "platform-admin",
      role: "superadmin",
      completed_at: "2026-06-09T12:00:00Z",
    });
  });

  test("submits bootstrap form without rendering secrets", async () => {
    const user = userEvent.setup();
    renderPlatformBootstrapPage();

    await user.type(screen.getByLabelText("Bootstrap token"), "vzplat_local_once");
    await user.type(screen.getByLabelText("Email"), "owner@example.com");
    await user.type(screen.getByLabelText("First name"), "Owner");
    await user.type(screen.getByLabelText("Last name"), "One");
    await user.type(screen.getByLabelText("Password"), "change-me-123456");
    await user.click(screen.getByRole("button", { name: "Create platform admin" }));

    await waitFor(() => {
      expect(bootstrapMocks.complete).toHaveBeenCalledWith({
        bootstrap_token: "vzplat_local_once",
        email: "owner@example.com",
        first_name: "Owner",
        last_name: "One",
        password: "change-me-123456",
      });
    });
    expect(await screen.findByText("Sign-in route")).toBeInTheDocument();
    expect(screen.queryByText("change-me-123456")).not.toBeInTheDocument();
    expect(screen.queryByText("vzplat_local_once")).not.toBeInTheDocument();
  });
});
