import { render, screen } from "@testing-library/react";
import { describe, expect, test } from "vitest";

import {
  InstrumentRail,
  MediaSurface,
  StatusToneBadge,
  WorkspaceBand,
  WorkspaceHero,
  WorkspaceSurface,
} from "@/components/layout/workspace-surfaces";

describe("workspace surfaces", () => {
  test("renders neutral workspace primitives", () => {
    render(
      <>
        <WorkspaceBand title="Live Intelligence" eyebrow="Live">
          <p>Signals converge here.</p>
        </WorkspaceBand>
        <WorkspaceSurface aria-label="Surface">Surface body</WorkspaceSurface>
        <MediaSurface aria-label="Media">Media body</MediaSurface>
        <InstrumentRail aria-label="Rail">Rail body</InstrumentRail>
      </>,
    );

    expect(
      screen.getByRole("heading", { name: "Live Intelligence" }),
    ).toBeInTheDocument();
    expect(screen.getByLabelText("Surface")).toHaveClass(
      "bg-[color:var(--vz-canvas-graphite)]",
    );
    expect(screen.getByLabelText("Media")).toHaveClass(
      "bg-[color:var(--vz-media-black)]",
    );
    expect(screen.getByLabelText("Rail")).toHaveClass(
      "bg-[color:var(--vz-canvas-graphite)]",
    );
  });

  test("maps status tones to semantic classes", () => {
    render(
      <>
        <StatusToneBadge tone="healthy">Live</StatusToneBadge>
        <StatusToneBadge tone="attention">Pending</StatusToneBadge>
        <StatusToneBadge tone="danger">Failed</StatusToneBadge>
        <StatusToneBadge tone="accent">Selected</StatusToneBadge>
      </>,
    );

    expect(screen.getByText("Live")).toHaveClass(
      "text-[var(--vz-state-healthy)]",
    );
    expect(screen.getByText("Pending")).toHaveClass(
      "text-[var(--vz-state-attention)]",
    );
    expect(screen.getByText("Failed")).toHaveClass(
      "text-[var(--vz-state-risk)]",
    );
    expect(screen.getByText("Selected")).toHaveClass(
      "text-[var(--vz-lens-cerulean)]",
    );
  });

  test("WorkspaceBand applies cerulean rim when accent='cerulean'", () => {
    render(
      <WorkspaceBand
        eyebrow="Live"
        title="Live Intelligence"
        accent="cerulean"
      />,
    );

    const heading = screen.getByRole("heading", { name: "Live Intelligence" });
    const band = heading.closest("section");
    expect(band).not.toBeNull();
    expect(band?.className).toContain(
      "border-t-[color:var(--vz-lens-cerulean)]",
    );
  });

  test("WorkspaceBand compact density reduces vertical padding", () => {
    render(
      <WorkspaceBand
        eyebrow="Sites"
        title="Deployment Sites"
        density="compact"
      />,
    );

    const heading = screen.getByRole("heading", { name: "Deployment Sites" });
    const band = heading.closest("section");
    expect(band?.className).toContain("py-4");
  });

  test("WorkspaceHero renders body and lens slot regions", () => {
    render(
      <WorkspaceHero
        eyebrow="Hero"
        title="Spatial cockpit"
        description="OmniSight for every live environment."
        lens={<div data-testid="lens-slot">lens</div>}
        body={<button type="button">Sign in</button>}
      />,
    );

    expect(
      screen.getByRole("heading", { name: /spatial cockpit/i }),
    ).toBeInTheDocument();
    expect(screen.getByTestId("lens-slot")).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: /sign in/i }),
    ).toBeInTheDocument();
    expect(screen.getByTestId("workspace-hero")).toHaveAttribute(
      "data-tone",
      "neutral",
    );
  });

  test("WorkspaceHero accepts tone='violet' and exposes data-tone for styling", () => {
    render(
      <WorkspaceHero
        eyebrow="Sign in"
        title="OmniSight"
        tone="violet"
        lens={<span>lens</span>}
        body={<span>body</span>}
      />,
    );

    expect(screen.getByTestId("workspace-hero")).toHaveAttribute(
      "data-tone",
      "violet",
    );
  });
});
