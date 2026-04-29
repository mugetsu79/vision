import { render, screen } from "@testing-library/react";
import { describe, expect, test } from "vitest";

import { ProductLockup } from "@/components/layout/ProductLockup";

describe("ProductLockup", () => {
  test("renders the product lockup from the standalone symbol and live text", () => {
    render(<ProductLockup />);

    expect(
      screen.getByRole("group", { name: /vezor product lockup/i }),
    ).toBeInTheDocument();
    expect(screen.getByRole("img", { name: /vezor 2d logo/i })).toHaveAttribute(
      "src",
      "/brand/2d_logo_no_ring.png",
    );
    expect(screen.getByText("Vezor")).toBeInTheDocument();
    expect(screen.getByText(/the omnisight/i)).toBeInTheDocument();
  });

  test("renders the symbol image when symbolOnly is enabled", () => {
    render(<ProductLockup symbolOnly />);

    expect(screen.getByRole("img", { name: /vezor 2d logo/i })).toHaveAttribute(
      "src",
      "/brand/2d_logo_no_ring.png",
    );
  });
});
