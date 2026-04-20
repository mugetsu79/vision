import { render, screen } from "@testing-library/react";
import { describe, expect, test } from "vitest";

import { ProductLockup } from "@/components/layout/ProductLockup";

describe("ProductLockup", () => {
  test("renders the product lockup image by default", () => {
    render(<ProductLockup />);

    expect(
      screen.getByRole("img", { name: /vezor product lockup/i }),
    ).toHaveAttribute("src", "/brand/product-lockup-ui.svg");
  });

  test("renders the symbol image when symbolOnly is enabled", () => {
    render(<ProductLockup symbolOnly />);

    expect(screen.getByRole("img", { name: /vezor symbol/i })).toHaveAttribute(
      "src",
      "/brand/product-symbol-ui.svg",
    );
  });
});
