import { render, screen } from "@testing-library/react";
import { describe, expect, test } from "vitest";

import {
  CommandBand,
  DetailDrawer,
  OperationalSection,
} from "@/components/layout/command-surfaces";

describe("command surfaces", () => {
  test("CommandBand renders the contract and forwards native props", () => {
    render(
      <CommandBand
        eyebrow="Control"
        title="Command Center"
        description="Route operators, previews, and actions through one surface."
        actions={<button type="button">Run</button>}
        className="custom-band"
        data-testid="command-band"
      />,
    );

    const band = screen.getByTestId("command-band");
    expect(band.tagName).toBe("SECTION");
    expect(band).toHaveClass("command-band", "custom-band");
    expect(screen.getByRole("heading", { name: "Command Center" })).toBeInTheDocument();
    expect(screen.getByText("Control")).toHaveClass("command-eyebrow");
    expect(screen.getByText("Route operators, previews, and actions through one surface.")).toHaveClass("command-description");
    expect(screen.getByRole("button", { name: "Run" })).toBeInTheDocument();
    expect(band.querySelector(".command-actions")).toBeInTheDocument();
  });

  test("CommandBand omits actions when none are passed", () => {
    render(
      <CommandBand
        eyebrow="Control"
        title="Command Center"
        description="Route operators, previews, and actions through one surface."
      />,
    );

    expect(screen.getByRole("heading", { name: "Command Center" })).toBeInTheDocument();
    expect(document.querySelector(".command-actions")).not.toBeInTheDocument();
  });

  test("OperationalSection wires aria-labelledby and forwards native props", () => {
    render(
      <OperationalSection
        id="ops"
        label="Operations"
        eyebrow="Live"
        className="custom-section"
      >
        <p>Ops body</p>
      </OperationalSection>,
    );

    const section = screen.getByRole("region", { name: "Operations" });
    expect(section.tagName).toBe("SECTION");
    expect(section).toHaveClass("operational-section", "custom-section");
    expect(section).toHaveAttribute("id", "ops");
    expect(section).toHaveAttribute("aria-labelledby", "ops-heading");
    expect(screen.getByRole("heading", { name: "Operations" })).toHaveAttribute(
      "id",
      "ops-heading",
    );
    expect(screen.getByText("Live")).toHaveClass("command-eyebrow");
  });

  test("OperationalSection overrides a caller-supplied aria-labelledby", () => {
    render(
      <OperationalSection
        id="ops"
        label="Operations"
        aria-labelledby="external-label"
      >
        <p>Ops body</p>
      </OperationalSection>,
    );

    const section = screen.getByRole("region", { name: "Operations" });
    expect(section).toHaveAttribute("aria-labelledby", "ops-heading");
    expect(screen.getByRole("heading", { name: "Operations" })).toHaveAttribute(
      "id",
      "ops-heading",
    );
  });

  test("OperationalSection omits eyebrow when not passed", () => {
    render(
      <OperationalSection id="ops" label="Operations">
        <p>Ops body</p>
      </OperationalSection>,
    );

    expect(screen.getByRole("heading", { name: "Operations" })).toBeInTheDocument();
    expect(screen.queryByText("Live")).not.toBeInTheDocument();
  });

  test("DetailDrawer renders a details root, summary label, and forwards props", () => {
    render(
      <DetailDrawer
        label="More details"
        className="custom-drawer"
        data-testid="detail-drawer"
      >
        <p>Drawer body</p>
      </DetailDrawer>,
    );

    const drawer = screen.getByTestId("detail-drawer");
    expect(drawer.tagName).toBe("DETAILS");
    expect(drawer).toHaveClass("detail-drawer", "custom-drawer");
    expect(drawer.querySelector("summary")).toHaveTextContent("More details");
    expect(screen.getByText("Drawer body")).toBeInTheDocument();
  });
});
