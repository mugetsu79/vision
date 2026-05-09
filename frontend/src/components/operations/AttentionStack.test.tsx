import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, test } from "vitest";

import { AttentionStack } from "@/components/operations/AttentionStack";
import type { AttentionItem, FleetHealth } from "@/lib/operational-health";

describe("AttentionStack", () => {
  test("renders ordered attention items with route links", () => {
    const items: AttentionItem[] = [
      {
        id: "workers",
        health: "danger",
        title: "Edge or central workers need attention",
        detail: "1 worker is not running",
        href: "/settings",
      },
      {
        id: "evidence",
        health: "attention",
        title: "Evidence waiting for review",
        detail: "2 pending evidence records",
        href: "/incidents",
      },
    ];

    render(
      <MemoryRouter>
        <AttentionStack
          items={items}
          fleetHealth={{
            health: "attention",
            label: "Attention needed",
            reasons: [],
          }}
        />
      </MemoryRouter>,
    );

    expect(
      screen.getByRole("heading", { name: /attention stack/i }),
    ).toBeInTheDocument();
    const links = screen.getAllByRole("link");
    expect(links[0]).toHaveTextContent(/edge or central workers/i);
    expect(links[1]).toHaveTextContent(/evidence waiting/i);
    expect(
      screen.getByRole("link", { name: /edge or central workers/i }),
    ).toHaveAttribute("href", "/settings");
    expect(screen.getByRole("link", { name: /evidence waiting/i })).toHaveAttribute(
      "href",
      "/incidents",
    );
  });

  test("renders a healthy state when there are no attention items", () => {
    const fleetHealth: FleetHealth = {
      health: "healthy",
      label: "Fleet healthy",
      reasons: ["All desired workers running"],
    };

    render(
      <MemoryRouter>
        <AttentionStack items={[]} fleetHealth={fleetHealth} />
      </MemoryRouter>,
    );

    expect(screen.getByText(/no operational attention needed/i)).toBeInTheDocument();
    expect(screen.getByText(/all desired workers running/i)).toBeInTheDocument();
  });
});
