import { act, fireEvent, render, screen } from "@testing-library/react";
import type { HTMLAttributes, ReactNode } from "react";
import { afterEach, describe, expect, test, vi } from "vitest";

import { ToastProvider } from "@/components/feedback/ToastProvider";
import { useToast } from "@/hooks/use-toast";

vi.mock("framer-motion", () => ({
  AnimatePresence: ({ children }: { children: ReactNode }) => <>{children}</>,
  motion: {
    div: (props: HTMLAttributes<HTMLDivElement> & Record<string, unknown>) => {
      const domProps = { ...props };
      const { children } = domProps;
      delete domProps.animate;
      delete domProps.children;
      delete domProps.exit;
      delete domProps.initial;
      delete domProps.transition;
      return <div {...domProps}>{children}</div>;
    },
  },
  useReducedMotion: () => false,
}));

function Trigger() {
  const toast = useToast();
  return (
    <button
      type="button"
      onClick={() => toast.show({ tone: "healthy", message: "Saved" })}
    >
      Trigger
    </button>
  );
}

describe("Toast", () => {
  afterEach(() => {
    vi.useRealTimers();
  });

  test("shows a toast on demand and auto-dismisses after timeout", () => {
    vi.useFakeTimers();

    render(
      <ToastProvider>
        <Trigger />
      </ToastProvider>,
    );

    fireEvent.click(screen.getByRole("button", { name: /trigger/i }));
    expect(screen.getByText("Saved")).toBeInTheDocument();

    act(() => {
      vi.advanceTimersByTime(6000);
    });

    expect(screen.queryByText("Saved")).not.toBeInTheDocument();
  });
});
