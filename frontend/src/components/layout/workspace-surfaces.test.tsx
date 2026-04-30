import { render, screen } from "@testing-library/react";
import { describe, expect, test } from "vitest";

import {
  InstrumentRail,
  MediaSurface,
  StatusToneBadge,
  WorkspaceBand,
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
      "bg-[color:var(--vezor-surface-neutral)]",
    );
    expect(screen.getByLabelText("Media")).toHaveClass(
      "bg-[color:var(--vezor-media-black)]",
    );
    expect(screen.getByLabelText("Rail")).toHaveClass(
      "bg-[color:var(--vezor-surface-rail)]",
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

    expect(screen.getByText("Live")).toHaveClass("text-[var(--vezor-success)]");
    expect(screen.getByText("Pending")).toHaveClass(
      "text-[var(--vezor-attention)]",
    );
    expect(screen.getByText("Failed")).toHaveClass("text-[var(--vezor-risk)]");
    expect(screen.getByText("Selected")).toHaveClass(
      "text-[var(--vezor-lens-cerulean)]",
    );
  });
});
