import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, test } from "vitest";

import type { Incident } from "@/hooks/use-incidents";

import { CaseContextStrip } from "./CaseContextStrip";

function incident(overrides: Partial<Incident> = {}): Incident {
  return {
    id: "incident-1",
    camera_id: "camera-1",
    camera_name: "Dock",
    ts: "2026-05-11T10:05:00Z",
    type: "ppe-missing",
    payload: { hard_hat: false },
    snapshot_url: null,
    clip_url: null,
    storage_bytes: 0,
    review_status: "pending",
    reviewed_at: null,
    reviewed_by_subject: null,
    ...overrides,
  };
}

describe("CaseContextStrip", () => {
  test("shows accountability status and keeps raw payload collapsed", async () => {
    const user = userEvent.setup();

    render(
      <CaseContextStrip
        incident={incident({
          scene_contract_hash: "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
          privacy_manifest_hash: "bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb",
          evidence_artifacts: [
            {
              id: "artifact-1",
              incident_id: "incident-1",
              camera_id: "camera-1",
              kind: "event_clip",
              status: "local_only",
              storage_provider: "local_filesystem",
              storage_scope: "edge",
              bucket: null,
              object_key: "edge/clip.mjpeg",
              content_type: "video/x-motion-jpeg",
              sha256: "c".repeat(64),
              size_bytes: 1024,
              clip_started_at: null,
              triggered_at: null,
              clip_ended_at: null,
              duration_seconds: 8,
              fps: 10,
              scene_contract_hash: "a".repeat(64),
              privacy_manifest_hash: "b".repeat(64),
              review_url: null,
            },
          ],
          ledger_summary: {
            entry_count: 4,
            latest_action: "incident.reviewed",
            latest_at: "2026-05-11T10:10:00Z",
          },
        })}
      />,
    );

    const strip = screen.getByTestId("case-context-strip");

    expect(within(strip).getByText(/clip only/i)).toBeInTheDocument();
    expect(within(strip).getByText(/scene contract/i)).toBeInTheDocument();
    expect(within(strip).getByText(/aaaaaaaa/i)).toBeInTheDocument();
    expect(within(strip).getByText(/privacy manifest/i)).toBeInTheDocument();
    expect(within(strip).getByText(/bbbbbbbb/i)).toBeInTheDocument();
    expect(within(strip).getByText(/local only/i)).toBeInTheDocument();
    expect(within(strip).getByText(/4 ledger entries/i)).toBeInTheDocument();

    const rawPayloadButton = within(strip).getByRole("button", {
      name: /show raw payload/i,
    });
    expect(rawPayloadButton).toHaveAttribute("aria-expanded", "false");
    expect(screen.queryByText(/hard_hat/i)).not.toBeInTheDocument();

    await user.click(rawPayloadButton);

    expect(rawPayloadButton).toHaveAttribute("aria-expanded", "true");
    expect(screen.getByText(/hard_hat/i)).toBeInTheDocument();
  });
});
