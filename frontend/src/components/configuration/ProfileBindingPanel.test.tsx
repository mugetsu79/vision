import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, test, vi } from "vitest";

import { ProfileBindingPanel } from "@/components/configuration/ProfileBindingPanel";
import type {
  OperatorConfigBindingResponse,
  OperatorConfigProfile,
} from "@/hooks/use-configuration";

const profiles: OperatorConfigProfile[] = [
  {
    id: "profile-operations",
    tenant_id: "tenant-1",
    kind: "operations_mode",
    scope: "tenant",
    name: "Edge polling",
    slug: "edge-polling",
    enabled: true,
    is_default: true,
    config: {
      lifecycle_owner: "edge_supervisor",
      supervisor_mode: "polling",
      restart_policy: "on_failure",
    },
    secret_state: {},
    validation_status: "valid",
    validation_message: null,
    validated_at: "2026-06-01T10:00:00Z",
    config_hash: "a".repeat(64),
    created_at: "2026-06-01T10:00:00Z",
    updated_at: "2026-06-01T10:00:00Z",
  },
  {
    id: "profile-operations-push",
    tenant_id: "tenant-1",
    kind: "operations_mode",
    scope: "tenant",
    name: "Central push",
    slug: "central-push",
    enabled: true,
    is_default: false,
    config: {
      lifecycle_owner: "central_supervisor",
      supervisor_mode: "push",
      restart_policy: "always",
    },
    secret_state: {},
    validation_status: "invalid",
    validation_message: "Push dispatcher unavailable.",
    validated_at: "2026-06-01T11:00:00Z",
    config_hash: "b".repeat(64),
    created_at: "2026-06-01T11:00:00Z",
    updated_at: "2026-06-01T11:00:00Z",
  },
];

const bindings: OperatorConfigBindingResponse[] = [
  {
    id: "binding-1",
    tenant_id: "tenant-1",
    kind: "operations_mode",
    scope: "camera",
    scope_key: "camera-1",
    profile_id: "profile-operations",
    created_at: "2026-06-01T10:00:00Z",
    updated_at: "2026-06-01T10:00:00Z",
  },
];

describe("ProfileBindingPanel", () => {
  test("explains binding precedence before binding", () => {
    render(
      <ProfileBindingPanel
        kind="operations_mode"
        profiles={profiles}
        bindings={[]}
        cameras={[{ id: "camera-1", label: "Dock camera" }]}
        sites={[{ id: "site-1", label: "Dock" }]}
        edgeNodes={[{ id: "edge-1", label: "Jetson" }]}
        onBind={vi.fn()}
      />,
    );

    expect(screen.getByText(/camera binding wins/i)).toBeInTheDocument();
    expect(screen.getByText(/tenant default is the fallback/i)).toBeInTheDocument();
    expect(screen.getByText(/next config refresh or lifecycle action/i)).toBeInTheDocument();
  });

  test("previews the selected binding impact and direct replacement", async () => {
    const user = userEvent.setup();
    render(
      <ProfileBindingPanel
        kind="operations_mode"
        profiles={profiles}
        bindings={bindings}
        cameras={[{ id: "camera-1", label: "Dock camera" }]}
        sites={[{ id: "site-1", label: "Dock" }]}
        edgeNodes={[{ id: "edge-1", label: "Jetson" }]}
        onBind={vi.fn()}
      />,
    );

    await user.selectOptions(screen.getByLabelText("Profile"), "profile-operations-push");

    const preview = screen.getByTestId("configuration-binding-preview");
    expect(within(preview).getByText(/will affect/i)).toBeInTheDocument();
    expect(within(preview).getByText(/central push/i)).toBeInTheDocument();
    expect(within(preview).getByText(/validation invalid/i)).toBeInTheDocument();
    expect(within(preview).getByText(/^camera$/i)).toBeInTheDocument();
    expect(within(preview).getByText(/dock camera/i)).toBeInTheDocument();
    expect(within(preview).getByText(/replaces direct binding: edge polling/i)).toBeInTheDocument();
    expect(within(preview).getByText(/config refresh or lifecycle action/i)).toBeInTheDocument();
    expect(within(preview).getByText(/applied hash bbbbbbbb/i)).toBeInTheDocument();
  });

  test("renders existing bindings and unbinds one binding", async () => {
    const user = userEvent.setup();
    const onBind = vi.fn();
    const onUnbind = vi.fn();

    render(
      <ProfileBindingPanel
        kind="operations_mode"
        profiles={profiles}
        bindings={bindings}
        cameras={[{ id: "camera-1", label: "Dock camera" }]}
        sites={[]}
        edgeNodes={[]}
        onBind={onBind}
        onUnbind={onUnbind}
      />,
    );

    const row = screen.getByTestId("configuration-binding-binding-1");
    expect(within(row).getByText("Edge polling")).toBeInTheDocument();
    expect(within(row).getByText("Dock camera")).toBeInTheDocument();

    await user.click(within(row).getByRole("button", { name: /unbind/i }));

    expect(onUnbind).toHaveBeenCalledWith("binding-1");
  });
});
