import { render, screen } from "@testing-library/react";
import { describe, expect, test } from "vitest";

import { KpiTile } from "@/components/dashboard/KpiTile";

describe("KpiTile", () => {
  test("renders eyebrow, value, and caption", () => {
    render(
      <KpiTile eyebrow="Live scenes" value="12" caption="2 attention" />,
    );

    expect(screen.getByText("Live scenes")).toBeInTheDocument();
    expect(screen.getByText("12")).toBeInTheDocument();
    expect(screen.getByText("2 attention")).toBeInTheDocument();
  });

  test("uses tabular numerics for the value", () => {
    render(<KpiTile eyebrow="Workers" value="4/6" />);

    expect(screen.getByText("4/6")).toHaveClass("tabular-nums");
  });
});
