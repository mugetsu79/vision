import { render, screen, within } from "@testing-library/react";
import { describe, expect, test } from "vitest";

import type { components } from "@/lib/api.generated";

import { RuntimePassportPanel } from "./RuntimePassportPanel";

type RuntimePassportSummary = components["schemas"]["RuntimePassportSummary"];

function summary(
  overrides: Partial<RuntimePassportSummary> = {},
): RuntimePassportSummary {
  return {
    id: "11111111-1111-1111-1111-111111111111",
    passport_hash: "e".repeat(64),
    selected_backend: "tensorrt_engine",
    model_hash: "f".repeat(64),
    runtime_artifact_id: "22222222-2222-2222-2222-222222222222",
    runtime_artifact_hash: "d".repeat(64),
    target_profile: "linux-aarch64-nvidia-jetson",
    precision: "fp16",
    validated_at: "2026-05-11T10:00:00Z",
    fallback_reason: null,
    runtime_selection_profile_id: "33333333-3333-3333-3333-333333333333",
    runtime_selection_profile_name: "Jetson runtime",
    runtime_selection_profile_hash: "g".repeat(64),
    provider_versions: { tensorrt: "10.0.0", cuda: "12.6" },
    ...overrides,
  };
}

describe("RuntimePassportPanel", () => {
  test("renders runtime artifact and profile accountability", () => {
    render(<RuntimePassportPanel summary={summary()} />);

    const panel = screen.getByTestId("runtime-passport-panel");
    expect(within(panel).getByText("Runtime passport")).toBeInTheDocument();
    expect(within(panel).getByText("tensorrt_engine")).toBeInTheDocument();
    expect(within(panel).getByText("ffffffffffff")).toBeInTheDocument();
    expect(within(panel).getByText("dddddddddddd")).toBeInTheDocument();
    expect(
      within(panel).getByText("linux-aarch64-nvidia-jetson"),
    ).toBeInTheDocument();
    expect(within(panel).getByText("fp16")).toBeInTheDocument();
    expect(within(panel).getByText("Jetson runtime")).toBeInTheDocument();
    expect(within(panel).getByText("tensorrt 10.0.0")).toBeInTheDocument();
  });

  test("shows dynamic fallback reasons", () => {
    render(
      <RuntimePassportPanel
        summary={summary({
          selected_backend: "ultralytics_pt",
          runtime_artifact_id: null,
          runtime_artifact_hash: null,
          target_profile: null,
          precision: null,
          validated_at: null,
          fallback_reason: "no_validated_runtime_artifact",
          provider_versions: {},
        })}
      />,
    );

    const panel = screen.getByTestId("runtime-passport-panel");
    expect(within(panel).getByText("ultralytics_pt")).toBeInTheDocument();
    expect(within(panel).getByText("Fallback")).toBeInTheDocument();
    expect(
      within(panel).getByText("no_validated_runtime_artifact"),
    ).toBeInTheDocument();
    expect(within(panel).getByText("Dynamic runtime")).toBeInTheDocument();
  });
});
