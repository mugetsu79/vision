import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import { describe, expect, test } from "vitest";

import { AppContextRail } from "@/components/layout/AppContextRail";
import { TestMemoryRouter } from "@/test/router";

function renderWith(initialPath: string) {
  const client = new QueryClient();
  return render(
    <QueryClientProvider client={client}>
      <TestMemoryRouter initialEntries={[initialPath]}>
        <AppContextRail />
      </TestMemoryRouter>
    </QueryClientProvider>,
  );
}

describe("AppContextRail", () => {
  test("renders a nav focus indicator on the active route", () => {
    renderWith("/dashboard");
    expect(screen.getByTestId("nav-focus-indicator")).toBeInTheDocument();
  });
});
