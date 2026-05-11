import { render, screen, within } from "@testing-library/react";
import { describe, expect, test } from "vitest";

import { AccountabilityStrip } from "@/components/evidence/AccountabilityStrip";
import type { Incident } from "@/hooks/use-incidents";

function accountableIncident(overrides: Partial<Incident> = {}): Incident {
  return {
    id: "99999999-9999-9999-9999-999999999999",
    camera_id: "11111111-1111-1111-1111-111111111111",
    camera_name: "Forklift Gate",
    ts: "2026-04-18T10:15:00Z",
    type: "ppe-missing",
    payload: { severity: "high" },
    snapshot_url: null,
    clip_url: null,
    storage_bytes: 2_097_152,
    review_status: "pending",
    reviewed_at: null,
    reviewed_by_subject: null,
    scene_contract_hash:
      "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
    scene_contract_id: "22222222-2222-2222-2222-222222222222",
    privacy_manifest_hash:
      "bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb",
    privacy_manifest_id: "33333333-3333-3333-3333-333333333333",
    recording_policy: {
      enabled: true,
      mode: "event_clip",
      pre_seconds: 4,
      post_seconds: 8,
      fps: 10,
      max_duration_seconds: 15,
      storage_profile: "edge_local",
    },
    evidence_artifacts: [
      {
        id: "44444444-4444-4444-4444-444444444444",
        incident_id: "99999999-9999-9999-9999-999999999999",
        camera_id: "11111111-1111-1111-1111-111111111111",
        kind: "event_clip",
        status: "local_only",
        storage_provider: "local_filesystem",
        storage_scope: "edge",
        bucket: null,
        object_key: "tenant/camera/clip.mjpeg",
        content_type: "video/x-motion-jpeg",
        sha256:
          "cccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccc",
        size_bytes: 2_097_152,
        clip_started_at: null,
        triggered_at: null,
        clip_ended_at: null,
        duration_seconds: null,
        fps: 10,
        scene_contract_hash:
          "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
        privacy_manifest_hash:
          "bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb",
        review_url: null,
      },
    ],
    ledger_summary: {
      entry_count: 3,
      latest_action: "evidence.clip.available",
      latest_at: "2026-04-18T10:16:00Z",
    },
    ...overrides,
  };
}

describe("AccountabilityStrip", () => {
  test("shows contract, manifest, local clip, and ledger status", () => {
    render(<AccountabilityStrip incident={accountableIncident()} />);

    expect(screen.getByTestId("accountability-strip")).toBeInTheDocument();
    expect(screen.getByText("Scene contract")).toBeInTheDocument();
    expect(screen.getByText("aaaaaaaa")).toBeInTheDocument();
    expect(screen.getByText("Privacy manifest")).toBeInTheDocument();
    expect(screen.getByText("bbbbbbbb")).toBeInTheDocument();
    expect(screen.getByText("Evidence clip")).toBeInTheDocument();
    expect(screen.getByText("Local evidence")).toBeInTheDocument();
    expect(screen.getByText("Ledger")).toBeInTheDocument();
    expect(screen.getByText("3 entries")).toBeInTheDocument();
  });

  test("uses cloud evidence wording for cloud artifact storage", () => {
    const baseArtifact = accountableIncident().evidence_artifacts?.[0];
    expect(baseArtifact).toBeDefined();

    render(
      <AccountabilityStrip
        incident={accountableIncident({
          evidence_artifacts: [
            {
              ...baseArtifact!,
              status: "remote_available",
              storage_provider: "s3_compatible",
              storage_scope: "cloud",
              review_url: "https://minio.local/signed/incidents/clip.mjpeg",
            },
          ],
        })}
      />,
    );

    const clipCell = screen.getByText("Evidence clip").closest("div");
    expect(clipCell).not.toBeNull();
    expect(within(clipCell as HTMLElement).getByText("Cloud evidence")).toBeInTheDocument();
  });
});
