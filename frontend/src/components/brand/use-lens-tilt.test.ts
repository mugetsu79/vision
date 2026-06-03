import { act, render } from "@testing-library/react";
import { createElement, useRef } from "react";
import { afterEach, describe, expect, test, vi } from "vitest";

import { useLensTilt } from "@/components/brand/use-lens-tilt";

function Harness() {
  const ref = useRef<HTMLDivElement>(null);
  useLensTilt(ref);
  return createElement("div", {
    "data-testid": "harness",
    ref,
    style: { width: 200, height: 200 },
  });
}

function setHarnessBounds(el: HTMLDivElement) {
  Object.defineProperty(el, "getBoundingClientRect", {
    value: () => ({
      left: 0,
      top: 0,
      width: 200,
      height: 200,
      right: 200,
      bottom: 200,
      x: 0,
      y: 0,
      toJSON: () => "",
    }),
  });
}

function nextAnimationFrame() {
  return new Promise<void>((resolve) => {
    window.requestAnimationFrame(() => resolve());
  });
}

describe("useLensTilt", () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  test("writes --lens-rx and --lens-ry on pointermove", async () => {
    const { getByTestId } = render(createElement(Harness));
    const el = getByTestId("harness") as HTMLDivElement;

    setHarnessBounds(el);

    await act(async () => {
      el.dispatchEvent(
        new MouseEvent("pointermove", {
          clientX: 150,
          clientY: 50,
          bubbles: true,
        }),
      );
      await nextAnimationFrame();
    });

    expect(el.style.getPropertyValue("--lens-ry")).toMatch(/deg$/);
    expect(el.style.getPropertyValue("--lens-rx")).toMatch(/deg$/);
  });

  test("clears tilt on pointerleave", async () => {
    const { getByTestId } = render(createElement(Harness));
    const el = getByTestId("harness") as HTMLDivElement;

    setHarnessBounds(el);

    await act(async () => {
      el.dispatchEvent(
        new MouseEvent("pointermove", {
          clientX: 150,
          clientY: 50,
          bubbles: true,
        }),
      );
      await nextAnimationFrame();
      el.dispatchEvent(new MouseEvent("pointerleave", { bubbles: true }));
    });

    expect(el.style.getPropertyValue("--lens-rx")).toBe("0deg");
    expect(el.style.getPropertyValue("--lens-ry")).toBe("0deg");
  });

  test("keeps the lens static when reduced motion is requested", async () => {
    vi.spyOn(window, "matchMedia").mockReturnValue({
      matches: true,
      media: "(prefers-reduced-motion: reduce)",
      onchange: null,
      addEventListener: vi.fn(),
      removeEventListener: vi.fn(),
      addListener: vi.fn(),
      removeListener: vi.fn(),
      dispatchEvent: vi.fn(),
    });

    const { getByTestId } = render(createElement(Harness));
    const el = getByTestId("harness") as HTMLDivElement;

    setHarnessBounds(el);

    await act(async () => {
      el.dispatchEvent(
        new MouseEvent("pointermove", {
          clientX: 150,
          clientY: 50,
          bubbles: true,
        }),
      );
      await nextAnimationFrame();
    });

    expect(el.style.getPropertyValue("--lens-rx")).toBe("");
    expect(el.style.getPropertyValue("--lens-ry")).toBe("");
  });
});
