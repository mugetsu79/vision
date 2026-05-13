import { render, screen, within } from "@testing-library/react";
import { describe, expect, test } from "vitest";

import { CrossCameraThreadPanel } from "@/components/evidence/CrossCameraThreadPanel";
import type { components } from "@/lib/api.generated";

type CrossCameraThread =
  components["schemas"]["CrossCameraThreadResponse"];

function threadPayload(): CrossCameraThread {
  return {
    id: "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
    tenant_id: "bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb",
    site_id: "cccccccc-cccc-cccc-cccc-cccccccccccc",
    camera_ids: [
      "11111111-1111-1111-1111-111111111111",
      "22222222-2222-2222-2222-222222222222",
    ],
    source_incident_ids: [
      "99999999-9999-9999-9999-999999999999",
      "88888888-8888-8888-8888-888888888888",
    ],
    privacy_manifest_hashes: [
      "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
      "bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb",
    ],
    confidence: 0.82,
    rationale: [
      "Same object class observed across adjacent cameras.",
      "Privacy manifests allowed only non-biometric attributes.",
    ],
    signals: {
      class_name: "person",
      zone_id: "server-room",
      direction: "eastbound",
      attributes: { vest_color: "red" },
    },
    privacy_labels: ["identity-light", "non-biometric"],
    thread_hash: "cccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccc",
    created_at: "2026-05-13T08:05:00Z",
  };
}

describe("CrossCameraThreadPanel", () => {
  test("renders identity-light thread context with citations and privacy labels", () => {
    render(
      <CrossCameraThreadPanel threads={[threadPayload()]} loading={false} />,
    );

    const panel = screen.getByTestId("cross-camera-thread-panel");
    expect(
      within(panel).getByRole("heading", { name: /cross-camera context/i }),
    ).toBeInTheDocument();
    expect(within(panel).getByText("82% confidence")).toBeInTheDocument();
    expect(within(panel).getByText("identity-light")).toBeInTheDocument();
    expect(within(panel).getByText("non-biometric")).toBeInTheDocument();
    expect(
      within(panel).getByText(/same object class observed/i),
    ).toBeInTheDocument();
    expect(
      within(panel).getByText(/privacy manifests allowed/i),
    ).toBeInTheDocument();
    expect(within(panel).getByText("person")).toBeInTheDocument();
    expect(within(panel).getByText("server-room")).toBeInTheDocument();
    expect(within(panel).getByText("eastbound")).toBeInTheDocument();
    expect(within(panel).getByText("cccccccccccc")).toBeInTheDocument();
    expect(within(panel).getByText("99999999-9999")).toBeInTheDocument();
    expect(within(panel).getByText("88888888-8888")).toBeInTheDocument();
    expect(panel).not.toHaveTextContent(/person identity/i);
    expect(panel).not.toHaveTextContent(/face id/i);
  });

  test("renders an empty privacy-safe state", () => {
    render(<CrossCameraThreadPanel threads={[]} loading={false} />);

    expect(screen.getByText("No cross-camera context")).toBeInTheDocument();
    expect(
      screen.getByText(/identity-light correlation only/i),
    ).toBeInTheDocument();
  });
});
