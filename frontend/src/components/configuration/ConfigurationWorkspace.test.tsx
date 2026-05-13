import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, test, vi } from "vitest";

import { ConfigurationWorkspace } from "@/components/configuration/ConfigurationWorkspace";

const createProfile = vi.fn();
const updateProfile = vi.fn();
const deleteProfile = vi.fn();
const testProfile = vi.fn();
const upsertBinding = vi.fn();

const profiles = [
  {
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
  },
  {
    id: "profile-local",
    tenant_id: "tenant-1",
    kind: "evidence_storage",
    scope: "tenant",
    name: "Edge local",
    slug: "edge-local",
    enabled: true,
    is_default: false,
    config: {
      provider: "local_filesystem",
      storage_scope: "edge",
      local_root: "/var/lib/argus/evidence",
    },
    secret_state: {},
    validation_status: "valid",
    validation_message: "Local evidence storage is writable.",
    validated_at: "2026-05-11T10:05:00Z",
    config_hash: "b".repeat(64),
    created_at: "2026-05-11T10:00:00Z",
    updated_at: "2026-05-11T10:00:00Z",
  },
];
let profileRows = profiles;

vi.mock("@/hooks/use-configuration", () => ({
  useConfigurationCatalog: () => ({
    data: {
      kinds: [
        { kind: "evidence_storage", label: "Evidence storage" },
        { kind: "stream_delivery", label: "Streams" },
        { kind: "runtime_selection", label: "Runtime" },
        { kind: "privacy_policy", label: "Privacy and retention" },
        { kind: "llm_provider", label: "LLM and policy" },
        { kind: "operations_mode", label: "Operations" },
      ],
    },
    isLoading: false,
  }),
  useConfigurationProfiles: () => ({
    data: profileRows,
    isLoading: false,
  }),
  useCreateConfigurationProfile: () => ({
    mutateAsync: createProfile,
    isPending: false,
  }),
  useUpdateConfigurationProfile: () => ({
    mutateAsync: updateProfile,
    isPending: false,
  }),
  useDeleteConfigurationProfile: () => ({
    mutateAsync: deleteProfile,
    isPending: false,
  }),
  useTestConfigurationProfile: () => ({
    mutateAsync: testProfile,
    isPending: false,
  }),
  useUpsertConfigurationBinding: () => ({
    mutateAsync: upsertBinding,
    isPending: false,
  }),
  useResolvedConfiguration: () => ({
    data: {
      entries: {
        evidence_storage: {
          kind: "evidence_storage",
          profile_id: "profile-minio",
          profile_name: "Central MinIO",
          profile_slug: "central-minio",
          profile_hash: "a".repeat(64),
          winner_scope: "tenant",
          winner_scope_key: "tenant-1",
          validation_status: "unvalidated",
          resolution_status: "resolved",
          applies_to_runtime: true,
          secret_state: { secret_key: "present" },
          operator_message: null,
          config: {},
        },
      },
    },
    isLoading: false,
  }),
}));

const cameras = [
  {
    id: "camera-1",
    site_id: "site-1",
    edge_node_id: "edge-1",
    name: "Dock camera",
  },
];
const sites = [{ id: "site-1", name: "Zurich Lab" }];
const edgeNodes = [{ id: "edge-1", hostname: "jetson-1" }];

function renderWorkspace() {
  return render(
    <ConfigurationWorkspace
      cameras={cameras}
      sites={sites}
      edgeNodes={edgeNodes}
    />,
  );
}

describe("ConfigurationWorkspace", () => {
  beforeEach(() => {
    profileRows = profiles;
    createProfile.mockReset();
    createProfile.mockResolvedValue(profiles[0]);
    updateProfile.mockReset();
    updateProfile.mockResolvedValue(profiles[0]);
    deleteProfile.mockReset();
    deleteProfile.mockResolvedValue(undefined);
    testProfile.mockReset();
    testProfile.mockResolvedValue({
      profile_id: "profile-minio",
      status: "valid",
      message: "bucket reachable",
      tested_at: "2026-05-11T12:00:00Z",
    });
    upsertBinding.mockReset();
    upsertBinding.mockResolvedValue({});
  });

  test("renders operator configuration categories and a single default badge", () => {
    renderWorkspace();

    const workspace = screen.getByTestId("configuration-workspace");
    expect(
      within(workspace).getByRole("heading", { name: /^configuration$/i }),
    ).toBeInTheDocument();
    for (const label of [
      "Evidence storage",
      "Streams",
      "Runtime",
      "Privacy and retention",
      "LLM and policy",
      "Operations",
    ]) {
      expect(within(workspace).getByRole("tab", { name: label })).toBeInTheDocument();
    }
    expect(within(workspace).getAllByText("Default")).toHaveLength(1);
    expect(screen.queryByText("argus-dev-secret")).not.toBeInTheDocument();
    expect(screen.getAllByText("Stored").length).toBeGreaterThan(0);
    expect(screen.getAllByText("Replace secret").length).toBeGreaterThan(0);
    expect(screen.getByRole("heading", { name: /effective configuration/i })).toBeInTheDocument();
    expect(screen.getAllByText("Central MinIO").length).toBeGreaterThan(0);
  });

  test("creates a cloud S3-compatible evidence profile with write-only secrets", async () => {
    const user = userEvent.setup();
    renderWorkspace();

    await user.click(screen.getByRole("button", { name: /new profile/i }));
    await user.clear(screen.getByLabelText("Profile name"));
    await user.type(screen.getByLabelText("Profile name"), "Cloud Archive");
    await user.clear(screen.getByLabelText("Slug"));
    await user.type(screen.getByLabelText("Slug"), "cloud-archive");
    await user.selectOptions(screen.getByLabelText("Provider"), "s3_compatible");
    await user.selectOptions(screen.getByLabelText("Storage scope"), "cloud");
    await user.type(screen.getByLabelText("Endpoint"), "s3.example.com");
    await user.type(screen.getByLabelText("Region"), "eu-central-1");
    await user.type(screen.getByLabelText("Bucket"), "omnisight-evidence");
    await user.click(screen.getByLabelText("Secure TLS"));
    await user.type(screen.getByLabelText("Path prefix"), "prod/incidents");
    await user.type(screen.getByLabelText("Access key"), "AKIA_TEST");
    await user.type(screen.getByLabelText("Secret key"), "super-secret");
    await user.click(screen.getByRole("button", { name: /save profile/i }));

    expect(createProfile).toHaveBeenCalledWith({
      kind: "evidence_storage",
      scope: "tenant",
      name: "Cloud Archive",
      slug: "cloud-archive",
      enabled: true,
      is_default: false,
      config: {
        provider: "s3_compatible",
        storage_scope: "cloud",
        endpoint: "s3.example.com",
        region: "eu-central-1",
        bucket: "omnisight-evidence",
        secure: true,
        path_prefix: "prod/incidents",
      },
      secrets: {
        access_key: "AKIA_TEST",
        secret_key: "super-secret",
      },
    });
    expect(await screen.findByText(/profile saved/i)).toBeInTheDocument();
  });

  test("tests profiles and binds selected profile to each supported scope", async () => {
    const user = userEvent.setup();
    renderWorkspace();

    await user.click(screen.getByRole("button", { name: /test profile/i }));
    expect(testProfile).toHaveBeenCalledWith("profile-minio");
    expect(await screen.findByText(/^valid - bucket reachable$/i)).toBeInTheDocument();
    expect(await screen.findByText(/bucket reachable/i)).toBeInTheDocument();

    const bindingPanel = screen.getByTestId("configuration-binding-panel");
    for (const [scope, target] of [
      ["camera", "camera-1"],
      ["site", "site-1"],
      ["edge_node", "edge-1"],
      ["tenant", "tenant"],
    ]) {
      await user.selectOptions(within(bindingPanel).getByLabelText("Binding scope"), scope);
      if (scope !== "tenant") {
        await user.selectOptions(within(bindingPanel).getByLabelText("Target"), target);
      }
      await user.click(within(bindingPanel).getByRole("button", { name: /bind profile/i }));
      expect(upsertBinding).toHaveBeenLastCalledWith({
        kind: "evidence_storage",
        scope,
        scope_key: target,
        profile_id: "profile-minio",
      });
      expect(await screen.findByText(/binding saved/i)).toBeInTheDocument();
    }
  });

  test("updates default profile and deletes the selected profile from list actions", async () => {
    const user = userEvent.setup();
    renderWorkspace();

    await user.click(screen.getByRole("button", { name: /set default/i }));

    expect(updateProfile).toHaveBeenCalledWith({
      profileId: "profile-local",
      payload: { is_default: true },
    });
    expect(await screen.findByText(/default profile updated/i)).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: /delete/i }));

    expect(deleteProfile).toHaveBeenCalledWith("profile-minio");
  });

  test("binds a profile that loads after the initial render", async () => {
    const user = userEvent.setup();
    profileRows = [];
    const { rerender } = renderWorkspace();

    profileRows = profiles;
    rerender(
      <ConfigurationWorkspace
        cameras={cameras}
        sites={sites}
        edgeNodes={edgeNodes}
      />,
    );

    await user.click(screen.getByRole("button", { name: /bind profile/i }));

    expect(upsertBinding).toHaveBeenCalledWith({
      kind: "evidence_storage",
      scope: "camera",
      scope_key: "camera-1",
      profile_id: "profile-minio",
    });
  });
});
