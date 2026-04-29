import { useState } from "react";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, test, vi } from "vitest";

import { HistorySearchBox } from "@/components/history/HistorySearchBox";
import type { HistorySearchResult } from "@/lib/history-search";

const results: HistorySearchResult[] = [
  {
    id: "class:car",
    type: "class",
    group: "Classes",
    label: "car",
    className: "car",
  },
  {
    id: "camera:gate",
    type: "camera",
    group: "Scenes",
    label: "Gate scene",
    cameraId: "cam-1",
  },
];

describe("HistorySearchBox", () => {
  test("selects the first result with ArrowDown and Enter", async () => {
    const user = userEvent.setup();
    const onSelect = vi.fn();

    render(
      <HistorySearchBox
        value="ca"
        results={results}
        onChange={vi.fn()}
        onSelect={onSelect}
      />,
    );

    const input = screen.getByRole("combobox", { name: /search patterns/i });
    await user.click(input);
    await user.keyboard("{ArrowDown}{Enter}");

    expect(onSelect).toHaveBeenCalledWith(results[0]);
  });

  test("dismisses the dropdown with Escape", async () => {
    const user = userEvent.setup();

    function Harness() {
      const [value, setValue] = useState("ca");
      return (
        <HistorySearchBox
          value={value}
          results={results}
          onChange={setValue}
          onSelect={vi.fn()}
        />
      );
    }

    render(<Harness />);

    const input = screen.getByRole("combobox", { name: /search patterns/i });
    expect(screen.getByRole("listbox")).toBeInTheDocument();

    await user.click(input);
    await user.keyboard("{Escape}");

    await waitFor(() =>
      expect(screen.queryByRole("listbox")).not.toBeInTheDocument(),
    );
    expect(input).toHaveValue("");
  });
});
