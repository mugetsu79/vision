import { render, screen } from "@testing-library/react";
import { describe, expect, test } from "vitest";

import { productBrand } from "@/brand/product";
import { OmniSightLens } from "@/components/brand/OmniSightLens";

describe("OmniSightLens", () => {
  test("renders the 3D mark image as the lens hero", () => {
    render(<OmniSightLens variant="signin" />);

    const lens = screen.getByTestId("omnisight-lens");
    expect(lens).toBeInTheDocument();

    const img = lens.querySelector("img");
    expect(img).not.toBeNull();
    expect(img).toHaveAttribute("src", productBrand.runtimeAssets.logo3d);
    expect(img).toHaveAttribute("alt", "");
  });

  test("renders a halo and kinetic fragments without full orbital rings", () => {
    render(<OmniSightLens variant="signin" />);

    const lens = screen.getByTestId("omnisight-lens");
    expect(lens.querySelector("[data-lens-halo]")).not.toBeNull();
    expect(lens.querySelectorAll("[data-lens-energy]")).toHaveLength(3);
    expect(lens.querySelectorAll("[data-lens-ring]")).toHaveLength(0);
  });

  test("variant=dashboard scales the lens down for cockpit context", () => {
    render(<OmniSightLens variant="dashboard" />);

    expect(screen.getByTestId("omnisight-lens")).toHaveAttribute(
      "data-variant",
      "dashboard",
    );
  });
});
