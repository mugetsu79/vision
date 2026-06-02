import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, test, vi } from "vitest";

import { CONFIGURATION_KINDS } from "@/components/configuration/configuration-copy";
import {
  PROFILE_COMMON_FIELD_GUIDANCE,
  PROFILE_FIELD_GUIDANCE,
  PROFILE_KIND_GUIDANCE,
} from "@/components/configuration/configuration-guidance";
import { ProfileEditor } from "@/components/configuration/ProfileEditor";
import type {
  ConfigurationCatalog,
  OperatorConfigKind,
  OperatorConfigProfileCreate,
} from "@/hooks/use-configuration";

const saveProfile = vi.fn();

describe("ProfileEditor", () => {
  beforeEach(() => {
    saveProfile.mockReset();
    saveProfile.mockResolvedValue(undefined);
  });

  test("renders guidance for each configuration kind", () => {
    for (const kind of CONFIGURATION_KINDS) {
      const { unmount } = render(
        <ProfileEditor kind={kind} selectedProfile={null} onSave={saveProfile} />,
      );

      expect(screen.getByText(PROFILE_KIND_GUIDANCE[kind].title)).toBeInTheDocument();
      expect(screen.getByText(PROFILE_KIND_GUIDANCE[kind].summary)).toBeInTheDocument();
      unmount();
    }
  });

  test("renders field guidance for every visible configuration field", () => {
    const expectedFieldsByKind: Record<OperatorConfigKind, string[]> = {
      evidence_storage: [
        "provider",
        "storage_scope",
        "local_root",
        "endpoint",
        "region",
        "bucket",
        "secure",
        "path_prefix",
        "access_key",
        "secret_key",
      ],
      stream_delivery: ["delivery_mode", "public_base_url", "edge_override_url"],
      runtime_selection: [
        "preferred_backend",
        "artifact_preference",
        "fallback_allowed",
      ],
      privacy_policy: [
        "retention_days",
        "storage_quota_bytes",
        "plaintext_plate_storage",
        "residency",
      ],
      llm_provider: ["provider", "model", "base_url", "api_key"],
      operations_mode: ["lifecycle_owner", "supervisor_mode", "restart_policy"],
    };

    for (const kind of CONFIGURATION_KINDS) {
      const { unmount } = render(
        <ProfileEditor kind={kind} selectedProfile={null} onSave={saveProfile} />,
      );

      for (const help of Object.values(PROFILE_COMMON_FIELD_GUIDANCE)) {
        expect(screen.getByText(help.hint)).toBeInTheDocument();
      }
      for (const fieldKey of expectedFieldsByKind[kind]) {
        expect(
          screen.getByText(PROFILE_FIELD_GUIDANCE[kind][fieldKey].hint),
        ).toBeInTheDocument();
      }

      unmount();
    }
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

  test("shows backend capability messages without offering legacy transcode as a new route", () => {
    const catalog: ConfigurationCatalog = {
      kinds: [
        {
          kind: "stream_delivery",
          label: "Transport profile",
          runtime_support: "active",
          operator_summary: "Selects the browser stream route.",
          fields: [
            {
              name: "delivery_mode",
              label: "Transport mode",
              support: "active",
              values: [
                { value: "native", support: "active" },
                {
                  value: "transcode",
                  support: "unsupported",
                  operator_message: "Use camera live rendition profiles for transcoding.",
                },
              ],
            },
          ],
        },
      ],
    };

    render(
      <ProfileEditor
        kind="stream_delivery"
        selectedProfile={null}
        catalog={catalog}
        onSave={saveProfile}
      />,
    );

    expect(screen.getByText(/selects the browser stream route/i)).toBeInTheDocument();
    expect(
      screen.getByText(/use camera live rendition profiles for transcoding/i),
    ).toBeInTheDocument();
    expect(screen.queryByRole("option", { name: /transcode/i })).not.toBeInTheDocument();
  });

  test("normalizes existing legacy transcode transport profiles", async () => {
    const user = userEvent.setup();
    render(
      <ProfileEditor
        kind="stream_delivery"
        selectedProfile={{
          id: "profile-transport",
          tenant_id: "tenant-1",
          kind: "stream_delivery",
          scope: "tenant",
          name: "Legacy transcode",
          slug: "legacy-transcode",
          enabled: true,
          is_default: false,
          config: {
            delivery_mode: "transcode",
            public_base_url: "https://streams.example.test",
          },
          secret_state: {},
          validation_status: "valid",
          validation_message: null,
          validated_at: "2026-05-11T10:00:00Z",
          config_hash: "b".repeat(64),
          created_at: "2026-05-11T10:00:00Z",
          updated_at: "2026-05-11T10:00:00Z",
        }}
        onSave={saveProfile}
      />,
    );

    expect(
      screen.getByText(/transcode route mode was normalized/i),
    ).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: /normalize transport/i }));

    const savedPayload = saveProfile.mock.calls[0]?.[0] as OperatorConfigProfileCreate;
    expect(savedPayload.config).toMatchObject({
      delivery_mode: "native",
      public_base_url: "https://streams.example.test",
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
