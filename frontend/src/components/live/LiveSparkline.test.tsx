import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, test, vi } from "vitest";

vi.mock("@/hooks/use-live-sparkline", () => ({
  useLiveSparkline: () => ({
    buckets: {
      person: [1, 2, 3, 4, 5, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
      car: [0, 0, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
      truck: [0, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
      bicycle: [0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
      bus: [0, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
    },
    latestValues: { person: 5, car: 1, truck: 1, bicycle: 1, bus: 1 },
    loading: false,
    error: null,
  }),
}));

import { LiveSparkline } from "@/components/live/LiveSparkline";

describe("LiveSparkline", () => {
  test("renders top 3 classes by total", () => {
    render(<LiveSparkline cameraId="cam-1" activeClasses={["person", "car", "truck", "bicycle", "bus"]} />);
    expect(screen.getByText(/person/i)).toBeInTheDocument();
    const visibleClasses = ["person", "car", "truck", "bicycle", "bus"].filter(
      (cls) => screen.queryByText(new RegExp(`\\b${cls}\\b`, "i")) !== null,
    );
    expect(visibleClasses.length).toBeGreaterThanOrEqual(3);
  });

  test("shows the +N more button when there are more than 3 classes", () => {
    render(<LiveSparkline cameraId="cam-1" activeClasses={["person", "car", "truck", "bicycle", "bus"]} />);
    expect(screen.getByRole("button", { name: /\+2 more/i })).toBeInTheDocument();
  });

  test("expands to show all classes after clicking +N more", async () => {
    const user = userEvent.setup();
    render(<LiveSparkline cameraId="cam-1" activeClasses={["person", "car", "truck", "bicycle", "bus"]} />);
    await user.click(screen.getByRole("button", { name: /\+2 more/i }));
    expect(screen.getByText(/bicycle/i)).toBeInTheDocument();
    expect(screen.getByText(/bus/i)).toBeInTheDocument();
  });

  test("renders latest occupancy next to each class", () => {
    render(<LiveSparkline cameraId="cam-1" activeClasses={["person", "car", "truck"]} />);
    expect(screen.getByText("5")).toBeInTheDocument();
  });
});
