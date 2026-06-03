# OmniSight Whole UI/UX Review Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement the product-wide OmniSight UI/UX reset described in `docs/superpowers/specs/2026-06-03-omnisight-whole-ui-ux-review-design.md`, with obvious visual change on Sign-in, Dashboard, and Operations while preserving runtime truth.

**Architecture:** Start by adding UI regression guardrails for brand motion, route hierarchy, and Operations overload. Then replace the moving 3D brand treatment, introduce a stricter shared surface hierarchy, recompose Dashboard as a command overview, and recompose Operations into attention-first sections with progressive details. Finish with route consistency passes and visual QA.

**Tech Stack:** React 19, TypeScript, Vite, Tailwind v4 utilities and CSS variables in `frontend/src/index.css`, Vitest, Playwright e2e, existing `@/components/ui` primitives, existing `lucide-react` icons.

---

## Source Material

- `docs/superpowers/specs/2026-06-03-omnisight-whole-ui-ux-review-design.md`
- `docs/superpowers/specs/2026-06-03-taste-led-omnisight-ui-ux-polish-design.md`
- `docs/brand/omnisight-ui-spec-sheet.md`
- `docs/superpowers/specs/2026-04-30-omnisight-ui-distinctiveness-followup-design.md`
- `taste-skill/SKILL.md`
- `taste-skill/dashboards/skill.md`
- `taste-skill/dark-luxe/skill.md`
- `taste-skill/swiss-system/skill.md`
- `taste-skill/components/style-recipes.md`

## File Map

- Modify: `frontend/src/components/brand/OmniSightLens.tsx`
- Modify: `frontend/src/components/brand/use-lens-tilt.ts`
- Modify: `frontend/src/components/layout/ProductLockup.tsx`
- Modify: `frontend/src/components/layout/workspace-surfaces.tsx`
- Modify: `frontend/src/index.css`
- Modify: `frontend/src/pages/SignIn.tsx`
- Modify: `frontend/src/pages/Dashboard.tsx`
- Modify: `frontend/src/pages/Settings.tsx`
- Modify: `frontend/src/pages/Live.tsx`
- Modify: `frontend/src/pages/History.tsx`
- Modify: `frontend/src/pages/Incidents.tsx`
- Modify: `frontend/src/pages/Sites.tsx`
- Modify: `frontend/src/pages/Cameras.tsx`
- Modify: `frontend/src/pages/Deployment.tsx`
- Modify: `frontend/src/pages/Dashboard.test.tsx`
- Modify: `frontend/src/pages/Settings.test.tsx`
- Modify: `frontend/src/pages/History.test.tsx`
- Modify: `frontend/e2e/operational-readiness.spec.ts`
- Create: `frontend/src/components/layout/command-surfaces.tsx`
- Create: `frontend/src/components/brand/OmniSightStaticMark.tsx`
- Create: `frontend/e2e/omnisight-ui-audit.spec.ts`

## Task 1: Add Product UI Guardrails

**Files:**
- Create: `frontend/e2e/omnisight-ui-audit.spec.ts`
- Modify: `frontend/e2e/operational-readiness.spec.ts`

- [ ] **Step 1: Write the failing Playwright UI audit**

Create `frontend/e2e/omnisight-ui-audit.spec.ts` with this structure, reusing the fixture style from `frontend/e2e/operational-readiness.spec.ts`:

```ts
import { expect, test, type Page } from "@playwright/test";

async function installUiAuditFixtures(page: Page) {
  await page.addInitScript(() => {
    const authority = "http://127.0.0.1:8080/realms/argus-dev";
    const clientId = "argus-frontend";
    window.localStorage.setItem(
      `oidc.user:${authority}:${clientId}`,
      JSON.stringify({
        id_token: "e2e-id-token",
        access_token: "e2e-access-token",
        token_type: "Bearer",
        scope: "openid profile email",
        expires_at: Math.floor(Date.now() / 1000) + 3600,
        profile: {
          sub: "e2e-admin",
          email: "admin@example.test",
          iss: authority,
          tenant_id: "tenant-1",
          realm_access: { roles: ["admin"] },
        },
      }),
    );
  });

  await page.route("**/api/v1/deployment/bootstrap/status", async (route) => {
    await route.fulfill({
      contentType: "application/json",
      body: JSON.stringify({ first_run_required: false }),
    });
  });
}

async function countPanelLikeSurfaces(page: Page) {
  return page.evaluate(() => {
    return Array.from(document.querySelectorAll("body *")).filter((element) => {
      const rect = element.getBoundingClientRect();
      const style = getComputedStyle(element);
      const borderWidth =
        parseFloat(style.borderTopWidth) +
        parseFloat(style.borderRightWidth) +
        parseFloat(style.borderBottomWidth) +
        parseFloat(style.borderLeftWidth);
      const hasSurface =
        style.backgroundColor !== "rgba(0, 0, 0, 0)" &&
        style.backgroundColor !== "transparent";
      return rect.width >= 40 && rect.height >= 24 && (borderWidth > 0 || hasSurface);
    }).length;
  });
}

test("dashboard does not render the moving 3D brand object", async ({ page }) => {
  await installUiAuditFixtures(page);
  await page.goto("/dashboard");
  await expect(page.locator('[data-testid="omnisight-lens"]')).toHaveCount(0);
  await expect(page.locator('img[src*="3d_logo"]')).toHaveCount(0);
});

test("operations default surface count stays below the overload budget", async ({ page }) => {
  await installUiAuditFixtures(page);
  await page.goto("/settings");
  const surfaceCount = await countPanelLikeSurfaces(page);
  expect(surfaceCount).toBeLessThanOrEqual(120);
});
```

- [ ] **Step 2: Run the audit and verify it fails**

Run:

```bash
corepack pnpm --dir frontend test:e2e -- omnisight-ui-audit.spec.ts
```

Expected: FAIL because Dashboard still renders `OmniSightLens` and Operations currently exceeds the surface budget.

- [ ] **Step 3: Commit the failing guardrail**

```bash
git add frontend/e2e/omnisight-ui-audit.spec.ts
git commit -m "test(ui): add omnisight visual hierarchy guardrails"
```

## Task 2: Replace The Moving 3D Brand Treatment

**Files:**
- Create: `frontend/src/components/brand/OmniSightStaticMark.tsx`
- Modify: `frontend/src/components/brand/OmniSightLens.tsx`
- Modify: `frontend/src/components/brand/use-lens-tilt.ts`
- Modify: `frontend/src/pages/SignIn.tsx`
- Modify: `frontend/src/pages/Dashboard.tsx`
- Modify: `frontend/src/index.css`
- Modify: `frontend/src/pages/Dashboard.test.tsx`

- [ ] **Step 1: Add a static mark component**

Create `frontend/src/components/brand/OmniSightStaticMark.tsx`:

```tsx
import { productBrand } from "@/brand/product";

export function OmniSightStaticMark({ className = "" }: { className?: string }) {
  return (
    <img
      src={productBrand.runtimeAssets.logo2dNoRing}
      alt={`${productBrand.name} mark`}
      className={className}
      draggable={false}
    />
  );
}
```

- [ ] **Step 2: Update Sign-in and Dashboard imports**

Replace `OmniSightLens` usage in `frontend/src/pages/SignIn.tsx` and `frontend/src/pages/Dashboard.tsx` with `OmniSightStaticMark`. Dashboard should not pass a `lens` prop to its first-page surface.

The Sign-in replacement should look like:

```tsx
import { OmniSightStaticMark } from "@/components/brand/OmniSightStaticMark";

<WorkspaceHero
  eyebrow={productBrand.descriptor}
  title="OmniSight for every live environment."
  description={`${brandName} connects scenes, models, events, evidence, and edge operations into one spatial intelligence layer.`}
  tone="blue"
  lens={
    <div className="flex min-h-48 items-center justify-center">
      <OmniSightStaticMark className="h-32 w-32 object-contain opacity-95" />
    </div>
  }
  body={...}
/>
```

- [ ] **Step 3: Remove perpetual lens motion**

In `frontend/src/index.css`, remove or neutralize the default `.lens-mark` animation rule:

```css
.lens-mark {
  transform: none;
  transition: opacity var(--vz-dur-base) var(--vz-ease-product);
}
```

Remove the `@keyframes lens-breathe` block if no selector uses it after this change.

- [ ] **Step 4: Update tests**

In `frontend/src/pages/Dashboard.test.tsx`, replace the current lens assertion:

```ts
expect(screen.getByTestId("omnisight-lens")).toBeInTheDocument();
```

with:

```ts
expect(screen.queryByTestId("omnisight-lens")).not.toBeInTheDocument();
expect(screen.getByText("OmniSight Overview")).toBeInTheDocument();
```

- [ ] **Step 5: Verify**

Run:

```bash
corepack pnpm --dir frontend exec vitest run src/pages/Dashboard.test.tsx
corepack pnpm --dir frontend test:e2e -- omnisight-ui-audit.spec.ts
```

Expected: Dashboard lens assertions pass. The Operations budget test may still fail until Task 4.

- [ ] **Step 6: Commit**

```bash
git add frontend/src/components/brand/OmniSightStaticMark.tsx frontend/src/components/brand/OmniSightLens.tsx frontend/src/components/brand/use-lens-tilt.ts frontend/src/pages/SignIn.tsx frontend/src/pages/Dashboard.tsx frontend/src/pages/Dashboard.test.tsx frontend/src/index.css
git commit -m "fix(ui): remove moving 3d brand default"
```

## Task 3: Add Command Surface Primitives

**Files:**
- Create: `frontend/src/components/layout/command-surfaces.tsx`
- Modify: `frontend/src/components/layout/workspace-surfaces.tsx`
- Modify: `frontend/src/index.css`

- [ ] **Step 1: Create the command surface primitives**

Create `frontend/src/components/layout/command-surfaces.tsx`:

```tsx
import type { PropsWithChildren, ReactNode } from "react";

export function CommandBand({
  eyebrow,
  title,
  description,
  actions,
}: {
  eyebrow: string;
  title: string;
  description: string;
  actions?: ReactNode;
}) {
  return (
    <section className="command-band">
      <div>
        <p className="command-eyebrow">{eyebrow}</p>
        <h1 className="command-title">{title}</h1>
        <p className="command-description">{description}</p>
      </div>
      {actions ? <div className="command-actions">{actions}</div> : null}
    </section>
  );
}

export function OperationalSection({
  id,
  label,
  eyebrow,
  children,
}: PropsWithChildren<{ id: string; label: string; eyebrow?: string }>) {
  return (
    <section id={id} className="operational-section" aria-labelledby={`${id}-heading`}>
      <div className="operational-section-header">
        {eyebrow ? <p className="command-eyebrow">{eyebrow}</p> : null}
        <h2 id={`${id}-heading`}>{label}</h2>
      </div>
      {children}
    </section>
  );
}

export function DetailDrawer({
  label,
  children,
}: PropsWithChildren<{ label: string }>) {
  return (
    <details className="detail-drawer">
      <summary>{label}</summary>
      <div>{children}</div>
    </details>
  );
}
```

- [ ] **Step 2: Add CSS rules**

Add to `frontend/src/index.css`:

```css
.command-band {
  display: grid;
  gap: 1rem;
  border: 1px solid var(--vz-hair);
  background: linear-gradient(180deg, rgba(15, 22, 35, 0.9), rgba(8, 12, 20, 0.92));
  padding: clamp(1rem, 2vw, 1.5rem);
}

.command-eyebrow {
  color: var(--vz-text-muted);
  font-size: 0.6875rem;
  font-weight: 700;
  letter-spacing: 0.14em;
  text-transform: uppercase;
}

.command-title {
  margin-top: 0.5rem;
  color: var(--vz-text-primary);
  font-family: var(--vz-font-display);
  font-size: clamp(1.75rem, 3vw, 2.75rem);
  font-weight: 650;
  letter-spacing: 0;
}

.command-description {
  margin-top: 0.5rem;
  max-width: 62ch;
  color: var(--vz-text-secondary);
  font-size: 0.9375rem;
  line-height: 1.6;
}

.command-actions {
  display: flex;
  flex-wrap: wrap;
  align-items: start;
  justify-content: end;
  gap: 0.5rem;
}

.operational-section {
  border-top: 1px solid var(--vz-hair);
  padding-block: 1.25rem;
}

.operational-section-header {
  display: flex;
  align-items: end;
  justify-content: space-between;
  gap: 1rem;
  margin-bottom: 0.75rem;
}

.operational-section-header h2 {
  color: var(--vz-text-primary);
  font-size: 1rem;
  font-weight: 650;
  letter-spacing: 0;
}

.detail-drawer {
  border-top: 1px solid rgba(255, 255, 255, 0.08);
  padding-top: 0.5rem;
}

.detail-drawer summary {
  cursor: pointer;
  color: var(--vz-text-secondary);
  font-size: 0.75rem;
  font-weight: 650;
}
```

- [ ] **Step 3: Verify typecheck/build**

Run:

```bash
corepack pnpm --dir frontend exec tsc --noEmit
corepack pnpm --dir frontend build
```

Expected: PASS.

- [ ] **Step 4: Commit**

```bash
git add frontend/src/components/layout/command-surfaces.tsx frontend/src/index.css
git commit -m "feat(ui): add command surface primitives"
```

## Task 4: Recompose Operations Around Attention First

**Files:**
- Modify: `frontend/src/pages/Settings.tsx`
- Modify: `frontend/src/pages/Settings.test.tsx`
- Modify: `frontend/src/components/operations/AttentionStack.tsx`
- Modify: `frontend/src/components/operations/SceneIntelligenceMatrix.tsx`

- [ ] **Step 1: Update Settings tests for section order and disclosure**

In `frontend/src/pages/Settings.test.tsx`, add assertions to the existing Operations test:

```ts
const workspace = screen.getByTestId("operations-workspace");
const attention = screen.getByTestId("attention-stack");
const workerRail = screen.getByTestId("worker-rail");
const configuration = screen.getByTestId("configuration-workspace");

expect(
  attention.compareDocumentPosition(workerRail) & Node.DOCUMENT_POSITION_FOLLOWING,
).toBeTruthy();
expect(
  workerRail.compareDocumentPosition(configuration) & Node.DOCUMENT_POSITION_FOLLOWING,
).toBeTruthy();
expect(within(workspace).getByRole("navigation", { name: /operations sections/i }))
  .toBeInTheDocument();
expect(within(configuration).getByRole("button", { name: /show configuration/i }))
  .toHaveAttribute("aria-expanded", "false");
```

- [ ] **Step 2: Run the test to verify it fails**

Run:

```bash
corepack pnpm --dir frontend exec vitest run src/pages/Settings.test.tsx
```

Expected: FAIL because Configuration is fully visible by default and the new disclosure button does not exist.

- [ ] **Step 3: Implement the Operations default structure**

In `frontend/src/pages/Settings.tsx`:

- Keep `AttentionStack` first.
- Keep `SceneIntelligenceMatrix` second.
- Keep `worker-rail` third.
- Wrap Stream Diagnostics, Deployment Nodes, Configuration, and Installer Guidance in `OperationalSection`.
- Make Configuration collapsed by default behind a button labeled `Show configuration`.
- Keep all runtime details available in the expanded section.

Use this state pattern:

```tsx
const [configurationOpen, setConfigurationOpen] = useState(false);

<OperationalSection id="configuration" label="Configuration" eyebrow="Control plane">
  <button
    type="button"
    aria-expanded={configurationOpen}
    className="..."
    onClick={() => setConfigurationOpen((current) => !current)}
  >
    {configurationOpen ? "Hide configuration" : "Show configuration"}
  </button>
  {configurationOpen ? (
    <ConfigurationWorkspace cameras={cameras} sites={sites} edgeNodes={edgeNodes} />
  ) : (
    <p className="text-sm text-[var(--vz-text-secondary)]">
      Profiles, bindings, effective runtime hashes, and installer defaults are available when needed.
    </p>
  )}
</OperationalSection>
```

- [ ] **Step 4: Verify tests and e2e budget**

Run:

```bash
corepack pnpm --dir frontend exec vitest run src/pages/Settings.test.tsx
corepack pnpm --dir frontend test:e2e -- omnisight-ui-audit.spec.ts
```

Expected: PASS for the Settings test and Operations surface budget.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/pages/Settings.tsx frontend/src/pages/Settings.test.tsx frontend/src/components/operations/AttentionStack.tsx frontend/src/components/operations/SceneIntelligenceMatrix.tsx
git commit -m "feat(operations): make workbench attention first"
```

## Task 5: Recompose Dashboard As Command Overview

**Files:**
- Modify: `frontend/src/pages/Dashboard.tsx`
- Modify: `frontend/src/pages/Dashboard.test.tsx`

- [ ] **Step 1: Update Dashboard test intent**

In `frontend/src/pages/Dashboard.test.tsx`, assert a command overview exists before route cards:

```ts
const overview = screen.getByTestId("dashboard-command-overview");
const attention = screen.getByTestId("attention-stack");
expect(overview).toBeInTheDocument();
expect(
  overview.compareDocumentPosition(attention) & Node.DOCUMENT_POSITION_FOLLOWING,
).toBeTruthy();
expect(screen.queryByTestId("omnisight-lens")).not.toBeInTheDocument();
```

- [ ] **Step 2: Run the test to verify it fails**

Run:

```bash
corepack pnpm --dir frontend exec vitest run src/pages/Dashboard.test.tsx
```

Expected: FAIL until the command overview replaces the current hero/lens layout.

- [ ] **Step 3: Implement the command overview**

In `frontend/src/pages/Dashboard.tsx`, replace the lens-led hero section with:

```tsx
<section data-testid="dashboard-command-overview" className="grid gap-3 xl:grid-cols-[minmax(0,1fr)_20rem]">
  <CommandBand
    eyebrow="Dashboard"
    title="Command overview"
    description="Live scenes, evidence, fleet state, and operational attention in one operator surface."
  />
  <div className="grid gap-2">
    {commandMetrics.map((metric) => (
      <div key={metric.label} className="border-t border-[color:var(--vz-hair)] py-3">
        <p className="command-eyebrow">{metric.label}</p>
        <p className="mt-1 text-2xl font-semibold text-[var(--vz-text-primary)]">
          {metric.value}
        </p>
        <p className="text-sm text-[var(--vz-text-secondary)]">{metric.detail}</p>
      </div>
    ))}
  </div>
</section>
```

- [ ] **Step 4: Verify**

Run:

```bash
corepack pnpm --dir frontend exec vitest run src/pages/Dashboard.test.tsx
corepack pnpm --dir frontend test:e2e -- omnisight-ui-audit.spec.ts
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/pages/Dashboard.tsx frontend/src/pages/Dashboard.test.tsx
git commit -m "feat(dashboard): replace hero with command overview"
```

## Task 6: Tighten Live, Patterns, Evidence, Sites, Scenes, And Deployment

**Files:**
- Modify: `frontend/src/pages/Live.tsx`
- Modify: `frontend/src/pages/History.tsx`
- Modify: `frontend/src/pages/Incidents.tsx`
- Modify: `frontend/src/pages/Sites.tsx`
- Modify: `frontend/src/pages/Cameras.tsx`
- Modify: `frontend/src/pages/Deployment.tsx`
- Modify: `frontend/src/pages/History.test.tsx`

- [ ] **Step 1: Fix Patterns heading hierarchy**

In `frontend/src/pages/History.tsx`, ensure only the route title is an `h1`. Change the active metric title from `h1` to `h2` or a styled paragraph.

Update `frontend/src/pages/History.test.tsx`:

```ts
expect(screen.getAllByRole("heading", { level: 1 })).toHaveLength(1);
expect(screen.getByRole("heading", { name: /history & patterns/i, level: 1 }))
  .toBeInTheDocument();
```

- [ ] **Step 2: Reduce repeated card chrome without changing data**

Apply these route-specific changes:

- Live: preserve black video slabs; reduce borders around tile controls.
- Evidence: keep queue / selected media / facts; reduce nested accountability borders.
- Sites: use a desktop row group for sites and mobile cards below `md`.
- Scenes: add section headings for inventory and setup flow.
- Deployment: show deployment nodes before installer package reference when `nodes.data.length > 0`.

- [ ] **Step 3: Verify route tests**

Run:

```bash
corepack pnpm --dir frontend exec vitest run \
  src/pages/History.test.tsx \
  src/pages/Incidents.test.tsx \
  src/pages/Sites.test.tsx \
  src/pages/Cameras.test.tsx \
  src/pages/Deployment.test.tsx
```

Expected: PASS.

- [ ] **Step 4: Commit**

```bash
git add frontend/src/pages/Live.tsx frontend/src/pages/History.tsx frontend/src/pages/Incidents.tsx frontend/src/pages/Sites.tsx frontend/src/pages/Cameras.tsx frontend/src/pages/Deployment.tsx frontend/src/pages/History.test.tsx
git commit -m "refactor(ui): tighten secondary workspace hierarchy"
```

## Task 7: Final Visual QA And Handoff

**Files:**
- Create: `docs/superpowers/status/2026-06-03-omnisight-whole-ui-ux-review-handoff.md`

- [ ] **Step 1: Run full frontend verification**

Run:

```bash
corepack pnpm --dir frontend exec vitest run
corepack pnpm --dir frontend test:e2e
corepack pnpm --dir frontend build
git diff --check
```

Expected: all commands pass.

- [ ] **Step 2: Capture visual QA**

Capture Sign-in, Dashboard, Live, Evidence, Operations, and Deployment at:

```text
375 px
768 px
1024 px
1440 px
```

Check:

- no moving 3D logo on default routes
- Operations first viewport shows attention, readiness, and workers before configuration
- video/evidence media remain unobscured
- mobile text does not overlap or clip

- [ ] **Step 3: Write handoff**

Create `docs/superpowers/status/2026-06-03-omnisight-whole-ui-ux-review-handoff.md` with:

```md
# OmniSight Whole UI/UX Review Handoff

Date: 2026-06-03
Branch: codex/omnisight-ui-ux-polish

## Implemented

- Removed moving 3D brand object from default product UI.
- Replaced Dashboard hero with command overview.
- Reworked Operations into attention-first sections with collapsed configuration.
- Tightened secondary workspace hierarchy.

## Verification

- `corepack pnpm --dir frontend exec vitest run`
- `corepack pnpm --dir frontend test:e2e`
- `corepack pnpm --dir frontend build`
- `git diff --check`

## Visual QA

List screenshot artifact paths and any residual risks.
```

- [ ] **Step 4: Commit and push**

```bash
git add docs/superpowers/status/2026-06-03-omnisight-whole-ui-ux-review-handoff.md
git commit -m "docs(ui): hand off omnisight whole ui review"
git status -sb
git push -u origin codex/omnisight-ui-ux-polish
```

## Self-Review Checklist

- Every route recommendation in the spec maps to a task above.
- Brand motion is covered by both component changes and e2e guardrails.
- Operations overload is covered by unit tests and e2e surface budget.
- No task requires backend/runtime semantic changes.
- Visual QA includes mobile and desktop widths.
