import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, test, vi } from "vitest";

import { SceneFocusPicker } from "@/components/scenes/SceneFocusPicker";
import type { SceneFocusItem } from "@/components/scenes/scene-focus";

function sceneItems(count: number): SceneFocusItem[] {
  return Array.from({ length: count }, (_, index) => {
    const number = index + 1;
    return {
      id: `scene-${number}`,
      name: `Batch Scene ${String(number).padStart(2, "0")}`,
      siteName: "Zurich Lab",
    };
  });
}

describe("SceneFocusPicker", () => {
  test("paginates long scene selector results with 10, 25, and 50 sizes", async () => {
    const user = userEvent.setup();

    render(
      <SceneFocusPicker
        defaultSummary="No scenes focused"
        items={sceneItems(12)}
        onClearSelection={vi.fn()}
        onSearchChange={vi.fn()}
        onToggleScene={vi.fn()}
        searchLabel="Search test scenes"
        searchPlaceholder="Search scenes"
        searchValue=""
        selectedSceneIds={new Set()}
        testId="test-scene-focus"
        title="Choose scenes"
      />,
    );

    const picker = screen.getByTestId("test-scene-focus");
    expect(
      within(picker).getByRole("checkbox", { name: "Batch Scene 10" }),
    ).toBeInTheDocument();
    expect(
      within(picker).queryByRole("checkbox", { name: "Batch Scene 11" }),
    ).not.toBeInTheDocument();
    expect(within(picker).getByText("1-10 of 12 scenes")).toBeInTheDocument();

    await user.selectOptions(
      within(picker).getByLabelText(/scenes per page/i),
      "25",
    );

    expect(
      within(picker).getByRole("checkbox", { name: "Batch Scene 11" }),
    ).toBeInTheDocument();
    expect(within(picker).getByText("1-12 of 12 scenes")).toBeInTheDocument();
  });
});
