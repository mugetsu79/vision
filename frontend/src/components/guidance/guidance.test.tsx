import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { test, expect } from "vitest";

import { CalibrationFlowIllustration } from "@/components/guidance/CalibrationFlowIllustration";
import { FieldHelp } from "@/components/guidance/FieldHelp";
import { GuidanceDisclosure } from "@/components/guidance/GuidanceDisclosure";
import { GuidancePanel } from "@/components/guidance/GuidancePanel";
import { ReadinessChecklist } from "@/components/guidance/ReadinessChecklist";

test("FieldHelp keeps rich guidance compact until opened", async () => {
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

  expect(screen.getByText("How the browser connects to live video.")).toHaveClass("sr-only");
  await user.click(screen.getByRole("button", { name: /show transport mode help/i }));
  expect(screen.getByText("WebRTC is low latency.")).toBeInTheDocument();
  expect(screen.getByText(/safe default/i)).toBeInTheDocument();
});

test("GuidanceDisclosure hides rich guidance until opened", async () => {
  const user = userEvent.setup();
  render(
    <GuidanceDisclosure
      id="transport-disclosure"
      label="Transport mode"
      guidance={{
        label: "Transport mode",
        hint: "How browsers connect.",
        details: ["WebRTC is low latency.", "HLS is resilient."],
        safeDefault: "Native/direct",
      }}
    />,
  );

  expect(screen.queryByText("WebRTC is low latency.")).not.toBeInTheDocument();
  await user.click(screen.getByRole("button", { name: /show transport mode help/i }));
  expect(screen.getByText("WebRTC is low latency.")).toBeInTheDocument();
  expect(screen.getByText(/safe default/i)).toBeInTheDocument();
});

test("GuidanceDisclosure closes with Escape", async () => {
  const user = userEvent.setup();
  render(
    <GuidanceDisclosure
      id="runtime-disclosure"
      label="Runtime"
      guidance={{
        title: "Rank model runtimes",
        summary: "Choose which runtime should start first.",
        commonMistakes: ["Disabling fallback before an artifact exists."],
      }}
    />,
  );

  const trigger = screen.getByRole("button", { name: /show runtime help/i });
  await user.click(trigger);
  expect(screen.getByText("Rank model runtimes")).toBeInTheDocument();
  await user.keyboard("{Escape}");
  expect(screen.queryByText("Rank model runtimes")).not.toBeInTheDocument();
  expect(trigger).toHaveFocus();
});

test("CalibrationFlowIllustration shows source and destination point mapping", () => {
  render(<CalibrationFlowIllustration />);

  expect(
    screen.getByRole("img", { name: /source points map to top-down points/i }),
  ).toBeInTheDocument();
  expect(screen.getByText("S1")).toBeInTheDocument();
  expect(screen.getByText("D1")).toBeInTheDocument();
  expect(screen.getByText(/measured distance/i)).toBeInTheDocument();
});

test("CalibrationFlowIllustration can show region guidance", () => {
  render(<CalibrationFlowIllustration mode="regions" />);

  expect(
    screen.getByRole("img", { name: /detection regions refine the calibrated plane/i }),
  ).toBeInTheDocument();
  expect(screen.getByText(/^include region$/i)).toBeInTheDocument();
  expect(screen.getByText(/^exclusion region$/i)).toBeInTheDocument();
});

test("CalibrationFlowIllustration can show event boundary guidance", () => {
  render(<CalibrationFlowIllustration mode="boundaries" />);

  expect(
    screen.getByRole("img", { name: /event boundaries belong on the calibrated plane/i }),
  ).toBeInTheDocument();
  expect(screen.getByText(/^event line$/i)).toBeInTheDocument();
});

test("CalibrationFlowIllustration keeps SVG ids unique across instances", () => {
  const { container } = render(
    <>
      <CalibrationFlowIllustration />
      <CalibrationFlowIllustration />
    </>,
  );

  const gradientIds = Array.from(container.querySelectorAll("linearGradient")).map(
    (gradient) => gradient.id,
  );

  expect(new Set(gradientIds).size).toBe(gradientIds.length);
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
