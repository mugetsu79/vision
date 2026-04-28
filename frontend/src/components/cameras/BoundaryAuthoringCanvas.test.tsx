import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, test, vi } from "vitest";

import { BoundaryAuthoringCanvas } from "@/components/cameras/BoundaryAuthoringCanvas";

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

describe("BoundaryAuthoringCanvas", () => {
  test("creates a line by clicking two points on the setup canvas", () => {
    const onChange = vi.fn();

    render(
      <BoundaryAuthoringCanvas
        ariaLabel="Setup frame canvas"
        frameSize={{ width: 1280, height: 720 }}
        maxPoints={2}
        mode="line"
        pointLabelPrefix="Line"
        value={[]}
        onChange={onChange}
      />,
    );

    const canvas = screen.getByLabelText(/setup frame canvas/i);
    stubRect(canvas, 640, 360);

    fireEvent.click(canvas, { clientX: 160, clientY: 60 });
    fireEvent.click(canvas, { clientX: 160, clientY: 300 });

    expect(onChange).toHaveBeenLastCalledWith([
      [0.25, 0.166667],
      [0.25, 0.833333],
    ]);
  });
});
