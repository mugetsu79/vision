import { fireEvent, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
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
  test("puts measured distance before the point canvases", () => {
    render(
      <HomographyEditor
        dst={[]}
        onChange={vi.fn()}
        refDistanceM={12.5}
        src={[]}
      />,
    );

    const distanceInput = screen.getByLabelText(/measured distance \(m\)/i);
    const sourceCanvas = screen.getByLabelText(/source points canvas/i);

    expect(
      distanceInput.compareDocumentPosition(sourceCanvas) &
        Node.DOCUMENT_POSITION_FOLLOWING,
    ).toBeTruthy();
  });

  test("keeps measured distance compact with the full tutorial behind help", async () => {
    const user = userEvent.setup();

    render(
      <HomographyEditor
        dst={[
          [0, 0],
          [0, 2],
          [4, 2],
          [4, 0],
        ]}
        onChange={vi.fn()}
        refDistanceM={2}
        src={[
          [10, 90],
          [10, 10],
          [90, 10],
          [90, 90],
        ]}
      />,
    );

    expect(
      screen.getByText(/measure d1 to d2 on the same calibrated plane/i),
    ).toBeInTheDocument();
    expect(
      screen.getByText(
        /s1\/s2 in the camera still, d1\/d2 in the drawn world plane/i,
      ),
    ).toBeInTheDocument();
    expect(
      screen.queryByText(/put s1 and s2 on two fixed floor marks/i),
    ).not.toBeInTheDocument();
    expect(
      screen.queryByRole("img", {
        name: /calibrated span measured distance example/i,
      }),
    ).not.toBeInTheDocument();

    await user.click(
      screen.getByRole("button", { name: /show measured distance help/i }),
    );

    expect(
      screen.getByText(/no third still capture is needed/i),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("img", {
        name: /calibrated span measured distance example/i,
      }),
    ).toBeInTheDocument();
  });

  test("shows a real-world example for setting the measured distance", async () => {
    const user = userEvent.setup();

    render(
      <HomographyEditor
        dst={[
          [0, 0],
          [2.5, 0],
          [2.5, 5],
          [0, 5],
        ]}
        onChange={vi.fn()}
        refDistanceM={2.5}
        src={[
          [180, 620],
          [920, 610],
          [860, 260],
          [230, 250],
        ]}
      />,
    );

    await user.click(
      screen.getByRole("button", { name: /show measured distance help/i }),
    );

    expect(
      screen.getByRole("img", {
        name: /calibrated span measured distance example/i,
      }),
    ).toBeInTheDocument();
    expect(
      screen.getByText(/example: known reference span = 2.5 m/i),
    ).toBeInTheDocument();
    expect(screen.queryByText(/parking bay/i)).not.toBeInTheDocument();
    expect(screen.getByText(/s points are camera pixels/i)).toBeInTheDocument();
    expect(
      screen.getByText(/d points are a top-down sketch/i),
    ).toBeInTheDocument();
    expect(screen.getByText(/s1 is d1 and s2 is d2/i)).toBeInTheDocument();
  });

  test("clarifies that destination points are drawn, not captured from another still", () => {
    render(
      <HomographyEditor
        dst={[
          [0, 0],
          [2.5, 0],
          [2.5, 5],
          [0, 5],
        ]}
        onChange={vi.fn()}
        refDistanceM={2.5}
        src={[
          [180, 620],
          [920, 610],
          [860, 260],
          [230, 250],
        ]}
      />,
    );

    expect(
      screen.getByText(
        /s1\/s2 in the camera still, d1\/d2 in the drawn world plane/i,
      ),
    ).toBeInTheDocument();
    expect(
      screen.getByText(/top-down drawing is not captured from the camera/i),
    ).toBeInTheDocument();
    expect(
      screen.getByText(/this is a drawn world plane, not a camera still/i),
    ).toBeInTheDocument();
  });

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

    expect(
      screen.getByRole("button", { name: /destination point 1/i }),
    ).toHaveStyle({
      left: "0%",
      top: "100%",
    });
    expect(
      screen.getByRole("button", { name: /destination point 2/i }),
    ).toHaveStyle({
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
