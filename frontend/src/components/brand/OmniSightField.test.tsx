import { render, screen } from "@testing-library/react";
import { describe, expect, test } from "vitest";

import { OmniSightField } from "@/components/brand/OmniSightField";

describe("OmniSightField", () => {
  test("renders decorative entry variant with logo-derived field hooks", () => {
    render(<OmniSightField variant="entry" />);

    const field = screen.getByTestId("omnisight-field");
    expect(field).toHaveAttribute("aria-hidden", "true");
    expect(field).toHaveClass("omnisight-field--entry");
    expect(field.querySelector(".omnisight-field__lens")).toBeNull();
    expect(field.querySelector(".omnisight-field__mark-stack")).not.toBeNull();
    expect(field.querySelector(".omnisight-field__orbital-map")).not.toBeNull();
    const layers = field.querySelectorAll<HTMLImageElement>(".omnisight-field__mark-layer");
    expect(layers).toHaveLength(3);
    for (const layer of layers) {
      expect(layer).toHaveAttribute("src", "/brand/3d_logo_no_bg.png");
    }
    expect(field.querySelectorAll(".omnisight-field__ring")).toHaveLength(2);
    expect(field.querySelectorAll(".omnisight-field__surface")).toHaveLength(0);
  });

  test("renders shell variant with meaningful orbital nodes instead of empty rectangles", () => {
    render(<OmniSightField variant="shell" />);

    const field = screen.getByTestId("omnisight-field");
    expect(field).toHaveClass("omnisight-field--shell");
    expect(field.querySelector(".omnisight-field__lens")).toBeNull();
    expect(field.querySelector(".omnisight-field__mark-stack")).not.toBeNull();
    expect(field.querySelectorAll(".omnisight-field__surface")).toHaveLength(0);
    expect(field.querySelectorAll(".omnisight-field__node")).toHaveLength(4);
  });

  test("renders stage variant without node labels competing with sign-in copy", () => {
    render(<OmniSightField variant="stage" />);

    const field = screen.getByTestId("omnisight-field");
    expect(field).toHaveAttribute("aria-hidden", "true");
    expect(field).toHaveClass("omnisight-field--stage");
    expect(field.querySelector(".omnisight-field__mark-stack")).not.toBeNull();
    expect(field.querySelectorAll(".omnisight-field__node")).toHaveLength(0);
  });

  test("renders dashboard variant with orbital nodes for the overview cockpit", () => {
    render(<OmniSightField variant="dashboard" />);

    const field = screen.getByTestId("omnisight-field");
    expect(field).toHaveClass("omnisight-field--dashboard");
    expect(field.querySelectorAll(".omnisight-field__node")).toHaveLength(4);
  });
});
