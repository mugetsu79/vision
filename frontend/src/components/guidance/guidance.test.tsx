import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { test, expect } from "vitest";

import { CalibrationFlowIllustration } from "@/components/guidance/CalibrationFlowIllustration";
import { CalibrationScaleExample } from "@/components/guidance/CalibrationScaleExample";
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
    >
      <p>Rich visual guidance stays inside the help panel.</p>
    </FieldHelp>,
  );

  expect(
    screen.getByText("How the browser connects to live video."),
  ).toHaveClass("sr-only");
  expect(screen.queryByText(/rich visual guidance/i)).not.toBeInTheDocument();
  await user.click(
    screen.getByRole("button", { name: /show transport mode help/i }),
  );
  expect(screen.getByText("WebRTC is low latency.")).toBeInTheDocument();
  expect(screen.getByText(/safe default/i)).toBeInTheDocument();
  expect(screen.getByText(/rich visual guidance/i)).toBeInTheDocument();
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
  await user.click(
    screen.getByRole("button", { name: /show transport mode help/i }),
  );
  expect(screen.getByText("WebRTC is low latency.")).toBeInTheDocument();
  expect(screen.getByText(/safe default/i)).toBeInTheDocument();
});

test("GuidanceDisclosure opens help in a portaled readable panel", async () => {
  const user = userEvent.setup();
  render(
    <div data-testid="clipping-root" className="overflow-hidden">
      <GuidanceDisclosure
        id="source-points-disclosure"
        label="source points"
        guidance={{
          label: "Source points",
          hint: "Pick fixed marks in the camera view.",
          details: ["Use marks that sit on the same floor plane."],
        }}
      />
    </div>,
  );

  await user.click(
    screen.getByRole("button", { name: /show source points help/i }),
  );

  const panel = screen.getByRole("dialog", { name: /source points help/i });
  expect(panel.closest("[data-testid='clipping-root']")).toBeNull();
  expect(panel).toHaveAttribute("aria-modal", "true");
  expect(panel).toHaveClass("overflow-y-auto");
  expect(screen.getByTestId("source-points-disclosure-portal")).toHaveClass(
    "fixed",
  );
  expect(screen.getByTestId("source-points-disclosure-portal")).toHaveClass(
    "z-50",
  );
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
  const { container } = render(<CalibrationFlowIllustration mode="regions" />);

  expect(
    screen.getByRole("img", {
      name: /detection regions gate the analytics still/i,
    }),
  ).toBeInTheDocument();
  const includeRegion = screen.getByText(/^include area$/i);
  const exclusionRegion = screen.getByText(/^exclude mask$/i);
  expect(includeRegion).toBeInTheDocument();
  expect(exclusionRegion).toBeInTheDocument();
  expect(
    screen.getAllByText(/include keeps detections eligible/i).length,
  ).toBeGreaterThan(0);
  expect(
    screen.getAllByText(/exclude suppresses noisy motion/i).length,
  ).toBeGreaterThan(0);

  const includeShape = container.querySelector("[data-region='include']");
  const exclusionShape = container.querySelector("[data-region='exclusion']");
  expect(includeShape).toBeInTheDocument();
  expect(exclusionShape).toBeInTheDocument();
  expect(includeShape?.tagName.toLowerCase()).toBe("polygon");
  expect(exclusionShape?.tagName.toLowerCase()).toBe("polygon");
});

test("CalibrationFlowIllustration can show event boundary guidance", () => {
  const { container } = render(<CalibrationFlowIllustration mode="boundaries" />);

  expect(
    screen.getByRole("img", {
      name: /event lines and zones use the analytics still/i,
    }),
  ).toBeInTheDocument();
  expect(screen.getByText(/^line boundary$/i)).toBeInTheDocument();
  expect(screen.getByText(/^event zone$/i)).toBeInTheDocument();
  expect(screen.getAllByText(/crossing event/i).length).toBeGreaterThan(0);
  expect(screen.getByText(/enter\/exit event/i)).toBeInTheDocument();
  expect(container.querySelector("[data-boundary='line-crossing']")).toBeInTheDocument();
  expect(container.querySelector("[data-boundary='event-zone']")).toBeInTheDocument();
});

test("CalibrationFlowIllustration uses neutral tracked anchors for event guidance", () => {
  const { container } = render(<CalibrationFlowIllustration mode="boundaries" />);

  expect(screen.getByText(/tracked anchor/i)).toBeInTheDocument();
  expect(screen.getByText(/object path/i)).toBeInTheDocument();
  expect(container.querySelectorAll("[data-track-anchor]").length).toBeGreaterThanOrEqual(3);
  expect(container.querySelectorAll("[data-motion-path]").length).toBeGreaterThanOrEqual(2);
  expect(container.querySelectorAll("[data-object-envelope]").length).toBeGreaterThanOrEqual(2);
  expect(container.querySelector("[data-scene-glyph='vehicle']")).not.toBeInTheDocument();
  expect(container.querySelector("[data-scene-glyph='person']")).not.toBeInTheDocument();
  expect(container.querySelector("[data-scene-glyph='boat']")).not.toBeInTheDocument();
  expect(container.querySelector("[data-scene-glyph='animal']")).not.toBeInTheDocument();
});

test("CalibrationFlowIllustration uses neutral tracked anchors for region guidance", () => {
  const { container } = render(<CalibrationFlowIllustration mode="regions" />);

  expect(screen.getByText(/tracked anchor/i)).toBeInTheDocument();
  expect(screen.getByText(/object path/i)).toBeInTheDocument();
  expect(container.querySelectorAll("[data-track-anchor]").length).toBeGreaterThanOrEqual(3);
  expect(container.querySelectorAll("[data-motion-path]").length).toBeGreaterThanOrEqual(2);
  expect(container.querySelectorAll("[data-object-envelope]").length).toBeGreaterThanOrEqual(2);
  expect(container.querySelector("[data-scene-glyph='vehicle']")).not.toBeInTheDocument();
  expect(container.querySelector("[data-scene-glyph='person']")).not.toBeInTheDocument();
  expect(container.querySelector("[data-scene-glyph='boat']")).not.toBeInTheDocument();
  expect(container.querySelector("[data-scene-glyph='animal']")).not.toBeInTheDocument();
});

test("CalibrationFlowIllustration uses external event annotation rails", () => {
  const { container } = render(<CalibrationFlowIllustration mode="boundaries" />);

  const labelIds = Array.from(
    container.querySelectorAll("[data-annotation-rail]"),
  ).map((label) => label.getAttribute("data-annotation-label"));

  expect(labelIds).toEqual(
    expect.arrayContaining([
      "line-crossing",
      "crossing-event",
      "event-zone",
      "tracked-anchor",
      "object-path",
    ]),
  );
  expect(container.querySelectorAll("[data-scene-callout]").length).toBeGreaterThanOrEqual(5);
  expect(container.querySelectorAll("[data-label-leader]").length).toBe(0);
  expect(screen.queryByText(/operating space/i)).not.toBeInTheDocument();
});

test("CalibrationFlowIllustration uses external detection annotation rails", () => {
  const { container } = render(<CalibrationFlowIllustration mode="regions" />);

  const labelIds = Array.from(
    container.querySelectorAll("[data-annotation-rail]"),
  ).map((label) => label.getAttribute("data-annotation-label"));

  expect(labelIds).toEqual(
    expect.arrayContaining([
      "include-region",
      "exclusion-region",
      "tracked-anchor",
      "object-path",
    ]),
  );
  expect(container.querySelectorAll("[data-scene-callout]").length).toBeGreaterThanOrEqual(4);
  expect(container.querySelectorAll("[data-label-leader]").length).toBe(0);
  expect(screen.queryByText(/operating space/i)).not.toBeInTheDocument();
});

test("CalibrationFlowIllustration keeps SVG ids unique across instances", () => {
  const { container } = render(
    <>
      <CalibrationFlowIllustration />
      <CalibrationFlowIllustration />
    </>,
  );

  const gradientIds = Array.from(
    container.querySelectorAll("linearGradient"),
  ).map((gradient) => gradient.id);

  expect(new Set(gradientIds).size).toBe(gradientIds.length);
});

test("CalibrationScaleExample maps S1 to D1 and S2 to D2", () => {
  const { container } = render(<CalibrationScaleExample />);

  expect(
    screen.getByRole("img", { name: /calibrated span measured distance example/i }),
  ).toBeInTheDocument();
  expect(container.textContent).not.toMatch(/\b(parking|bay|car|vehicle|person)\b/i);
  expect(container.querySelectorAll("[data-reference-mark]").length).toBeGreaterThanOrEqual(4);
  expect(screen.getByText(/coordinates can differ/i)).toBeInTheDocument();
  expect(screen.getByText(/enter the real d1-d2 span/i)).toBeInTheDocument();
  expect(
    container.querySelector("[data-calibration-link='s1-d1']"),
  ).toHaveAttribute("d", expect.stringMatching(/^M92 220 C.*430 236$/));
  expect(
    container.querySelector("[data-calibration-link='s2-d2']"),
  ).toHaveAttribute("d", expect.stringMatching(/^M202 224 C.*670 236$/));
});

test("CalibrationScaleExample labels destination as a drawn plane", () => {
  render(<CalibrationScaleExample />);

  expect(screen.getByText("Drawn world plane")).toBeInTheDocument();
  expect(
    screen.getByText(
      /destination plane is drawn by you, not captured from another camera still/i,
    ),
  ).toBeInTheDocument();
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

  expect(
    screen.getByRole("heading", { name: "Map the camera image" }),
  ).toBeInTheDocument();
  expect(screen.getByText("Place source points.")).toBeInTheDocument();
  expect(screen.getByText("Mixing point order.")).toBeInTheDocument();
});

test("ReadinessChecklist renders status rows", () => {
  render(
    <ReadinessChecklist
      items={[
        {
          id: "source",
          label: "Source",
          detail: "Still ready",
          tone: "success",
        },
        {
          id: "geometry",
          label: "Geometry",
          detail: "Needs destination points",
          tone: "warning",
        },
      ]}
    />,
  );

  const list = screen.getByRole("list", { name: /readiness/i });
  expect(within(list).getByText("Source")).toBeInTheDocument();
  expect(
    within(list).getByText("Needs destination points"),
  ).toBeInTheDocument();
});
