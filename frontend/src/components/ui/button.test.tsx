import { render, screen } from "@testing-library/react";
import { describe, expect, test } from "vitest";

import { Button } from "@/components/ui/button";

describe("Button", () => {
  test("primary variant renders with cerulean gradient class", () => {
    render(<Button variant="primary">Sign in</Button>);
    const btn = screen.getByRole("button", { name: /sign in/i });
    expect(btn.className).toContain("from-[var(--vz-lens-cerulean)]");
  });

  test("secondary is the default variant", () => {
    render(<Button>Cancel</Button>);
    const btn = screen.getByRole("button", { name: /cancel/i });
    expect(btn.className).toContain("bg-[linear-gradient(180deg,#161c26,#0d121a)]");
  });

  test("ghost variant has transparent background", () => {
    render(<Button variant="ghost">Skip</Button>);
    const btn = screen.getByRole("button", { name: /skip/i });
    expect(btn.className).toContain("bg-transparent");
  });

  test("renders type=button by default to avoid accidental form submits", () => {
    render(<Button>Click</Button>);
    expect(screen.getByRole("button", { name: /click/i })).toHaveAttribute(
      "type",
      "button",
    );
  });

  test("disabled prop applies disabled styling", () => {
    render(<Button disabled>Off</Button>);
    const btn = screen.getByRole("button", { name: /off/i });
    expect(btn).toBeDisabled();
    expect(btn.className).toContain("disabled:opacity-60");
  });
});
