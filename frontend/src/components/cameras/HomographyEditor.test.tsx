import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, test, vi } from "vitest";

import { HomographyEditor } from "@/components/cameras/HomographyEditor";

function stubRect(element: HTMLElement, width: number, height: number) {
  Object.defineProperty(element, "getBoundingClientRect", {
    configurable: true,
    value: () => ({
      width,
      height,
      top: 0,
      left: 0,
      right: width,
      bottom: height,
      x: 0,
      y: 0,
      toJSON: () => ({}),
    }),
  });
}

describe("HomographyEditor", () => {
  test("reuses the authoring canvas for draggable source points", () => {
    const onChange = vi.fn();

    render(
      <HomographyEditor
        dst={[[0, 0]]}
        onChange={onChange}
        refDistanceM={12.5}
        src={[[0, 0]]}
      />,
    );

    const canvas = screen.getByLabelText(/source points canvas/i);
    stubRect(canvas, 200, 100);

    const handle = screen.getByRole("button", { name: /source point 1/i });

    fireEvent.mouseDown(handle, { button: 0, clientX: 0, clientY: 0 });
    fireEvent.mouseMove(window, { clientX: 100, clientY: 50 });
    fireEvent.mouseUp(window);

    expect(onChange).toHaveBeenCalled();
    expect(onChange.mock.lastCall?.[0]).toEqual({
      src: [[50, 50]],
      dst: [[0, 0]],
      refDistanceM: 12.5,
    });
  });

  test("renders destination world coordinates with y increasing upward", () => {
    render(
      <HomographyEditor
        destinationFrameSize={{ width: 100, height: 100 }}
        dst={[
          [0, 0],
          [100, 100],
        ]}
        onChange={vi.fn()}
        refDistanceM={12.5}
        src={[]}
      />,
    );

    expect(screen.getByRole("button", { name: /destination point 1/i })).toHaveStyle({
      left: "0%",
      top: "100%",
    });
    expect(screen.getByRole("button", { name: /destination point 2/i })).toHaveStyle({
      left: "100%",
      top: "0%",
    });
  });

  test("maps destination clicks back into upward world coordinates", () => {
    const onChange = vi.fn();

    render(
      <HomographyEditor
        destinationFrameSize={{ width: 100, height: 100 }}
        dst={[]}
        onChange={onChange}
        refDistanceM={12.5}
        src={[]}
      />,
    );

    const canvas = screen.getByLabelText(/destination points canvas/i);
    stubRect(canvas, 100, 100);

    fireEvent.click(canvas, { clientX: 25, clientY: 10 });

    expect(onChange).toHaveBeenCalledWith({
      src: [],
      dst: [[25, 90]],
      refDistanceM: 12.5,
    });
  });
});
