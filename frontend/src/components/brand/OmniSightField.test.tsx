import { render, screen } from "@testing-library/react";
import { describe, expect, test } from "vitest";

import { OmniSightField } from "@/components/brand/OmniSightField";

describe("OmniSightField", () => {
  test("renders decorative entry variant with stable lens hooks", () => {
    render(<OmniSightField variant="entry" />);

    const field = screen.getByTestId("omnisight-field");
    expect(field).toHaveAttribute("aria-hidden", "true");
    expect(field).toHaveClass("omnisight-field--entry");
    expect(field.querySelector(".omnisight-field__lens")).not.toBeNull();
    expect(field.querySelectorAll(".omnisight-field__ring")).toHaveLength(2);
    expect(field.querySelectorAll(".omnisight-field__surface").length).toBeGreaterThan(
      0,
    );
  });

  test("renders quiet variant without overview surfaces", () => {
    render(<OmniSightField variant="quiet" />);

    const field = screen.getByTestId("omnisight-field");
    expect(field).toHaveClass("omnisight-field--quiet");
    expect(field.querySelector(".omnisight-field__lens")).not.toBeNull();
    expect(field.querySelectorAll(".omnisight-field__surface")).toHaveLength(0);
  });
});
