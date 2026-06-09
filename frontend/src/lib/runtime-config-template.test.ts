import { readFileSync } from "node:fs";
import { join } from "node:path";

import { describe, expect, test } from "vitest";

function readFrontendFile(relativePath: string): string {
  return readFileSync(join(process.cwd(), relativePath), "utf8");
}

describe("frontend runtime config template", () => {
  test("injects the platform OIDC authority into appliance config.js", () => {
    const template = readFrontendFile("config.template.js");
    const entrypoint = readFrontendFile("docker-entrypoint.d/10-vezor-config.sh");

    expect(template).toContain("VITE_PLATFORM_OIDC_AUTHORITY");
    expect(entrypoint).toContain("$VITE_PLATFORM_OIDC_AUTHORITY");
  });
});
