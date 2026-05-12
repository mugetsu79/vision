import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, test, vi } from "vitest";

import { EffectiveConfigurationPanel } from "@/components/configuration/EffectiveConfigurationPanel";

const resolveConfiguration = vi.fn();

vi.mock("@/hooks/use-configuration", () => ({
  useResolvedConfiguration: (cameraId?: string) => {
    resolveConfiguration(cameraId);
    return {
      data: {
        entries: {
          evidence_storage: {
            kind: "evidence_storage",
            profile_id: "profile-storage",
            profile_name: "Camera MinIO",
            profile_slug: "camera-minio",
            profile_hash: "a".repeat(64),
            winner_scope: "camera",
            winner_scope_key: "camera-1",
            validation_status: "valid",
            resolution_status: "resolved",
            applies_to_runtime: true,
            secret_state: { secret_key: "present" },
            operator_message: null,
            config: { provider: "minio", bucket: "incidents" },
          },
          operations_mode: {
            kind: "operations_mode",
            profile_id: "profile-ops",
            profile_name: "Manual operations",
            profile_slug: "manual-operations",
            profile_hash: "b".repeat(64),
            winner_scope: "tenant",
            winner_scope_key: "tenant-1",
            validation_status: "valid",
            resolution_status: "resolved",
            applies_to_runtime: false,
            secret_state: {},
            operator_message: "Runtime-wired in Task 20.",
            config: {},
          },
          runtime_selection: {
            kind: "runtime_selection",
            profile_id: "profile-runtime",
            profile_name: "TensorRT first",
            profile_slug: "tensorrt-first",
            profile_hash: "c".repeat(64),
            winner_scope: "tenant",
            winner_scope_key: "tenant-1",
            validation_status: "invalid",
            resolution_status: "unresolved",
            applies_to_runtime: false,
            secret_state: {},
            operator_message: "Selected profile is invalid: artifact missing.",
            config: {},
          },
        },
      },
      isLoading: false,
    };
  },
}));

const cameras = [
  { id: "camera-1", label: "Dock camera" },
  { id: "camera-2", label: "Gate camera" },
];

describe("EffectiveConfigurationPanel", () => {
  test("shows effective profile winners and redacted secret state", async () => {
    const user = userEvent.setup();
    render(<EffectiveConfigurationPanel cameras={cameras} />);

    expect(screen.getByRole("heading", { name: /effective configuration/i })).toBeInTheDocument();
    const storageRow = screen.getByTestId("effective-config-evidence_storage");
    expect(within(storageRow).getByText("Camera MinIO")).toBeInTheDocument();
    expect(within(storageRow).getByText("camera")).toBeInTheDocument();
    expect(within(storageRow).getByText("valid")).toBeInTheDocument();
    expect(within(storageRow).getByText("runtime-wired now")).toBeInTheDocument();
    expect(within(storageRow).getByText("secret_key stored")).toBeInTheDocument();
    expect(screen.queryByText("sk-runtime-secret")).not.toBeInTheDocument();
    expect(screen.getByText("Runtime-wired in Task 20.")).toBeInTheDocument();
    expect(screen.getByText("Selected profile is invalid: artifact missing.")).toBeInTheDocument();

    await user.selectOptions(screen.getByLabelText("Resolved target"), "camera:camera-2");

    expect(resolveConfiguration).toHaveBeenLastCalledWith({ cameraId: "camera-2" });
  });

  test("renders unresolved entries with operator-facing status", () => {
    render(<EffectiveConfigurationPanel cameras={cameras} />);

    const runtimeRow = screen.getByTestId("effective-config-runtime_selection");

    expect(within(runtimeRow).getByText("Unresolved")).toBeInTheDocument();
    expect(within(runtimeRow).getByText("TensorRT first")).toBeInTheDocument();
  });
});
