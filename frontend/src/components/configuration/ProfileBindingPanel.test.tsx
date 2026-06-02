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
