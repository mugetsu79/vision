import { readFile } from "node:fs/promises";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";

import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, test } from "vitest";

import { WorkspaceTransition } from "@/components/layout/WorkspaceTransition";

const srcRoot = resolve(dirname(fileURLToPath(import.meta.url)), "../..");

async function readIndexCss() {
  return readFile(resolve(srcRoot, "index.css"), "utf8");
}

function workspaceEnterBlock(css: string) {
  const start = css.indexOf("@keyframes workspace-enter");
  const end = css.indexOf(
    "/* --------------------------------------------------------- */",
    start,
  );

  expect(start).toBeGreaterThanOrEqual(0);
  expect(end).toBeGreaterThan(start);

  return css.slice(start, end);
}

describe("WorkspaceTransition", () => {
  test("wraps routed content with a transition surface", () => {
    render(
      <MemoryRouter initialEntries={["/live"]}>
        <WorkspaceTransition>
          <h1>Live Intelligence</h1>
        </WorkspaceTransition>
      </MemoryRouter>,
    );

    expect(screen.getByRole("heading", { name: /live intelligence/i })).toBeInTheDocument();
    expect(screen.getByTestId("workspace-transition")).toHaveAttribute(
      "data-route",
      "/live",
    );
  });

  test("uses product motion tokens for workspace-enter", () => {
    render(
      <MemoryRouter initialEntries={["/live"]}>
        <WorkspaceTransition>
          <h1>Live Intelligence</h1>
        </WorkspaceTransition>
      </MemoryRouter>,
    );

    expect(screen.getByTestId("workspace-transition")).toHaveClass(
      "animate-[workspace-enter_var(--vz-dur-base)_var(--vz-ease-product)_both]",
    );
  });

  test("keeps workspace-enter to a 6px translate without scale", async () => {
    const block = workspaceEnterBlock(await readIndexCss());

    expect(block).toContain("transform: translate3d(0, 6px, 0);");
    expect(block).toContain("transform: translate3d(0, 0, 0);");
    expect(block).not.toContain("scale(");
    expect(block).not.toContain("0.35rem");
  });
});
