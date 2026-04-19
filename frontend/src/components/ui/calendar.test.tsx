import { render } from "@testing-library/react";
import { describe, expect, test } from "vitest";

import { Calendar } from "@/components/ui/calendar";

describe("Calendar", () => {
  test("keeps multi-month layouts stacked to avoid clipping in narrow cards", () => {
    const { container } = render(
      <Calendar mode="single" month={new Date("2026-04-01T00:00:00Z")} numberOfMonths={2} />,
    );
    const markup = container.innerHTML;

    expect(markup).toContain("flex flex-col gap-6");
    expect(markup).not.toContain("sm:flex-row");
    expect(markup).toContain("min-w-[17.5rem]");
  });
});
