import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, test } from "vitest";

import { WorkspaceTransition } from "@/components/layout/WorkspaceTransition";

describe("WorkspaceTransition", () => {
  test("wraps routed content with a transition surface", () => {
    render(
      <MemoryRouter initialEntries={["/live"]}>
        <WorkspaceTransition>
          <h1>Live Intelligence</h1>
        </WorkspaceTransition>
      </MemoryRouter>,
    );

    expect(screen.getByRole("heading", { name: /live intelligence/i })).toBeInTheDocument();
    expect(screen.getByTestId("workspace-transition")).toHaveAttribute(
      "data-route",
      "/live",
    );
  });
});
