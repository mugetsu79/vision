import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, test, vi } from "vitest";

import { ProfileEditor } from "@/components/configuration/ProfileEditor";
import type { OperatorConfigProfileCreate } from "@/hooks/use-configuration";

const saveProfile = vi.fn();

describe("ProfileEditor", () => {
  beforeEach(() => {
    saveProfile.mockReset();
    saveProfile.mockResolvedValue(undefined);
  });

  test("renders concrete controls for every configuration category", async () => {
    const user = userEvent.setup();
    render(
      <ProfileEditor
        kind="stream_delivery"
        selectedProfile={null}
        onSave={saveProfile}
      />,
    );

    expect(screen.getByText("Transport profile")).toBeInTheDocument();
    expect(screen.getByText(/reusable relay and browser transport settings/i)).toBeInTheDocument();
    expect(screen.getByLabelText("Transport mode")).toBeInTheDocument();
    expect(screen.getByLabelText("Public base URL")).toBeInTheDocument();
    expect(screen.getByLabelText("Edge override URL")).toBeInTheDocument();

    await user.selectOptions(screen.getByLabelText("Configuration kind"), "runtime_selection");
    expect(screen.getByLabelText("Preferred backend")).toBeInTheDocument();
    expect(screen.getByLabelText("Artifact preference")).toBeInTheDocument();
    expect(screen.getByLabelText("Allow fallback")).toBeInTheDocument();

    await user.selectOptions(screen.getByLabelText("Configuration kind"), "privacy_policy");
    expect(screen.getByLabelText("Retention days")).toBeInTheDocument();
    expect(screen.getByLabelText("Storage quota bytes")).toBeInTheDocument();
    expect(screen.getByLabelText("Plaintext plate posture")).toBeInTheDocument();
    expect(screen.getByLabelText("Residency guardrail")).toBeInTheDocument();

    await user.selectOptions(screen.getByLabelText("Configuration kind"), "llm_provider");
    expect(screen.getByLabelText("Provider")).toBeInTheDocument();
    expect(screen.getByLabelText("Model")).toBeInTheDocument();
    expect(screen.getByLabelText("Base URL")).toBeInTheDocument();
    expect(screen.getByLabelText("API key")).toBeInTheDocument();
    expect(screen.getByText("Replace secret")).toBeInTheDocument();

    await user.selectOptions(screen.getByLabelText("Configuration kind"), "operations_mode");
    expect(screen.getByLabelText("Lifecycle owner")).toBeInTheDocument();
    expect(screen.getByLabelText("Supervisor mode")).toBeInTheDocument();
    expect(screen.getByLabelText("Restart policy")).toBeInTheDocument();
  });

  test("saves local-first evidence storage profiles from concrete controls", async () => {
    const user = userEvent.setup();
    render(
      <ProfileEditor
        kind="evidence_storage"
        selectedProfile={null}
        onSave={saveProfile}
      />,
    );

    await user.clear(screen.getByLabelText("Profile name"));
    await user.type(screen.getByLabelText("Profile name"), "Local First");
    await user.clear(screen.getByLabelText("Slug"));
    await user.type(screen.getByLabelText("Slug"), "local-first");
    await user.selectOptions(screen.getByLabelText("Provider"), "local_first");
    await user.selectOptions(screen.getByLabelText("Storage scope"), "edge");
    await user.type(screen.getByLabelText("Local root"), "/var/lib/argus/evidence");
    await user.type(screen.getByLabelText("Path prefix"), "pending");
    await user.click(screen.getByRole("button", { name: /save profile/i }));

    const savedPayload = saveProfile.mock.calls[0]?.[0] as OperatorConfigProfileCreate;
    expect(savedPayload.kind).toBe("evidence_storage");
    expect(savedPayload.name).toBe("Local First");
    expect(savedPayload.slug).toBe("local-first");
    expect(savedPayload.config).toMatchObject({
      provider: "local_first",
      storage_scope: "edge",
      local_root: "/var/lib/argus/evidence",
      path_prefix: "pending",
    });
  });

  test("saved secret values are never rendered as plaintext", () => {
    render(
      <ProfileEditor
        kind="evidence_storage"
        selectedProfile={{
          id: "profile-minio",
          tenant_id: "tenant-1",
          kind: "evidence_storage",
          scope: "tenant",
          name: "Central MinIO",
          slug: "central-minio",
          enabled: true,
          is_default: true,
          config: {
            provider: "minio",
            storage_scope: "central",
            endpoint: "localhost:9000",
            bucket: "incidents",
            secure: false,
          },
          secret_state: { access_key: "present", secret_key: "present" },
          validation_status: "unvalidated",
          validation_message: null,
          validated_at: null,
          config_hash: "a".repeat(64),
          created_at: "2026-05-11T10:00:00Z",
          updated_at: "2026-05-11T10:00:00Z",
        }}
        onSave={saveProfile}
      />,
    );

    expect(screen.getAllByText("Stored")).toHaveLength(2);
    expect(screen.getAllByText("Replace secret")).toHaveLength(2);
    expect(screen.queryByText("argus-dev-secret")).not.toBeInTheDocument();
  });
});
