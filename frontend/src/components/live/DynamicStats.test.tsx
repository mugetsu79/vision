import { render, screen, within } from "@testing-library/react";
import { describe, expect, test } from "vitest";

import { DynamicStats } from "@/components/live/DynamicStats";
import {
  colorForClass,
  type SignalCountRow,
} from "@/lib/live-signal-stability";

const rows: SignalCountRow[] = [
  {
    className: "person",
    color: colorForClass("person"),
    liveCount: 2,
    heldCount: 0,
    totalCount: 2,
    state: "live",
  },
  {
    className: "car",
    color: colorForClass("car"),
    liveCount: 0,
    heldCount: 1,
    totalCount: 1,
    state: "held",
  },
];

describe("DynamicStats", () => {
  test("renders live signal rows with held state", () => {
    render(<DynamicStats signalRows={rows} />);

    const section = screen
      .getByRole("heading", { name: /live signals in view/i })
      .closest("section");

    expect(section).not.toBeNull();
    expect(within(section!).getByText(/person/i)).toBeInTheDocument();
    expect(within(section!).getByText(/car/i)).toBeInTheDocument();
    expect(within(section!).getByText(/held/i)).toBeInTheDocument();
  });

  test("renders empty copy when no live signal rows exist", () => {
    render(<DynamicStats signalRows={[]} />);

    expect(screen.getByText(/no live signals/i)).toBeInTheDocument();
  });
});
