import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, test } from "vitest";

import { AppContextRail } from "@/components/layout/AppContextRail";

function renderWith(initialPath: string) {
  const client = new QueryClient();
  return render(
    <QueryClientProvider client={client}>
      <MemoryRouter
        future={{
          v7_relativeSplatPath: true,
          v7_startTransition: true,
        }}
        initialEntries={[initialPath]}
      >
        <AppContextRail />
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

describe("AppContextRail", () => {
  test("renders a nav focus indicator on the active route", () => {
    renderWith("/dashboard");
    expect(screen.getByTestId("nav-focus-indicator")).toBeInTheDocument();
  });
});
