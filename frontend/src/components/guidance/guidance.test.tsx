import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { test, expect } from "vitest";

import { FieldHelp } from "@/components/guidance/FieldHelp";
import { GuidancePanel } from "@/components/guidance/GuidancePanel";
import { ReadinessChecklist } from "@/components/guidance/ReadinessChecklist";

test("FieldHelp exposes inline hint and expandable details", async () => {
  const user = userEvent.setup();
  render(
    <FieldHelp
      id="transport-mode-help"
      guidance={{
        label: "Transport mode",
        hint: "How the browser connects to live video.",
        details: ["WebRTC is low latency.", "HLS is resilient."],
        safeDefault: "Native/direct",
      }}
    />,
  );

  expect(screen.getByText("How the browser connects to live video.")).toBeInTheDocument();
  await user.click(screen.getByRole("button", { name: /show details for transport mode/i }));
  expect(screen.getByText("WebRTC is low latency.")).toBeInTheDocument();
  expect(screen.getByText(/safe default/i)).toBeInTheDocument();
});

test("GuidancePanel renders steps and common mistakes", () => {
  render(
    <GuidancePanel
      guidance={{
        eyebrow: "Geometry",
        title: "Map the camera image",
        summary: "Use matching source and destination points.",
        steps: ["Confirm the still.", "Place source points."],
        commonMistakes: ["Mixing point order."],
      }}
    />,
  );

  expect(screen.getByRole("heading", { name: "Map the camera image" })).toBeInTheDocument();
  expect(screen.getByText("Place source points.")).toBeInTheDocument();
  expect(screen.getByText("Mixing point order.")).toBeInTheDocument();
});

test("ReadinessChecklist renders status rows", () => {
  render(
    <ReadinessChecklist
      items={[
        { id: "source", label: "Source", detail: "Still ready", tone: "success" },
        { id: "geometry", label: "Geometry", detail: "Needs destination points", tone: "warning" },
      ]}
    />,
  );

  const list = screen.getByRole("list", { name: /readiness/i });
  expect(within(list).getByText("Source")).toBeInTheDocument();
  expect(within(list).getByText("Needs destination points")).toBeInTheDocument();
});
