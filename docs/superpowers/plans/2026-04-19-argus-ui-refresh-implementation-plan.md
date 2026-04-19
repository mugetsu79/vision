# Argus UI Refresh Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Refresh the full Argus frontend into the approved `Matte Command Rail` / `Balanced` / `Unified Left Rail Workspace` design while preserving all existing auth, live, history, incident, and admin functionality.

**Architecture:** Introduce a new shared shell and page-chrome system first, then migrate page families onto it in controlled slices. Keep behavior and data flow stable; most work is layout, hierarchy, and shared-component modernization backed by focused regression tests and existing Playwright flows.

**Tech Stack:** React 19, React Router 6, TypeScript, Tailwind CSS v4, TanStack Query, Zustand, Vitest, Playwright, Vite

---

## File Map

### New Files

- `frontend/public/brand/argus-lockup-ui.svg`
  - Product/UI lockup copied from the approved attached logo direction.
- `frontend/public/brand/argus-symbol-ui.svg`
  - Square symbol crop for the icon rail and compact contexts.
- `frontend/src/components/layout/ProductLockup.tsx`
  - Central brand/logo component for the shell and sign-in.
- `frontend/src/components/layout/AppIconRail.tsx`
  - Slim icon-only workspace rail.
- `frontend/src/components/layout/AppContextRail.tsx`
  - Grouped textual navigation and workspace context rail.
- `frontend/src/components/layout/PageHeader.tsx`
  - Compact page label/title/action header.
- `frontend/src/components/layout/PageUtilityBar.tsx`
  - Shared utility bar for filters, actions, and lightweight status chips.
- `frontend/src/components/layout/InspectorPanel.tsx`
  - Shared optional inspector surface.
- `frontend/src/pages/Live.tsx`
  - Thin route-level wrapper for live monitoring if the refresh separates `/live` from `/dashboard`.
- `frontend/src/pages/SignIn.test.tsx`
  - Regression coverage for the refreshed sign-in surface.
- `frontend/src/pages/Incidents.test.tsx`
  - Regression coverage for incidents layout and evidence actions.

### Existing Files To Modify

- `frontend/src/index.css`
  - Global visual tokens, matte surface variables, and shell-level background tuning.
- `frontend/src/app/router.tsx`
  - Route wiring for the refreshed shell and optional distinct `Live` page.
- `frontend/src/components/layout/AppShell.tsx`
  - Replace the top-heavy shell with the new left-rail workspace.
- `frontend/src/components/layout/AppShell.test.tsx`
  - Update expectations for the new shell structure.
- `frontend/src/components/layout/TopNav.tsx`
  - Either retire or convert into route-prefetch helpers used by the new rails.
- `frontend/src/components/layout/TenantSwitcher.tsx`
  - Adapt into quieter context-rail presentation.
- `frontend/src/components/layout/UserMenu.tsx`
  - Adapt into calmer session controls.
- `frontend/src/components/ui/button.tsx`
  - New default matte button treatment.
- `frontend/src/components/ui/badge.tsx`
  - Quieter status chips for utility bars and inline state.
- `frontend/src/components/ui/input.tsx`
  - Update field styling to match the matte configuration family.
- `frontend/src/components/ui/select.tsx`
  - Update select styling for the same system.
- `frontend/src/components/ui/table.tsx`
  - Improve row density, separators, and scanability.
- `frontend/src/components/ui/dialog.tsx`
  - Flatten dialog chrome to match the new product surfaces.
- `frontend/src/pages/SignIn.tsx`
  - Refresh sign-in branding and structure.
- `frontend/src/pages/Dashboard.tsx`
  - Convert to content-first operations workspace.
- `frontend/src/pages/History.tsx`
  - Convert to utility-bar-driven analysis canvas.
- `frontend/src/pages/Incidents.tsx`
  - Convert to evidence-first incident review surface.
- `frontend/src/pages/Sites.tsx`
  - Convert to cleaner admin workspace.
- `frontend/src/pages/Cameras.tsx`
  - Convert to cleaner admin workspace and wizard entry flow.
- `frontend/src/pages/Settings.tsx`
  - Convert placeholder route into a proper settings scaffold.
- `frontend/src/components/sites/SiteDialog.tsx`
  - Update site create/edit dialog styling.
- `frontend/src/components/cameras/CameraWizard.tsx`
  - Refresh wizard shell and step chrome without changing payload behavior.
- `frontend/src/components/cameras/CameraWizard.test.tsx`
  - Update layout/text assertions while preserving behavioral tests.
- `frontend/src/pages/History.test.tsx`
  - Adjust for new utility-bar copy and structure if needed.
- `frontend/e2e/prompt7-auth-and-camera.spec.ts`
  - Update for new shell/navigation if selectors change.
- `frontend/e2e/prompt8-live-dashboard.spec.ts`
  - Update dashboard/live selectors if needed.
- `frontend/e2e/prompt9-history-and-incidents.spec.ts`
  - Update history/incidents selectors if needed.

## Task 1: Establish Brand Assets And Shared Matte UI Foundations

**Files:**
- Create: `frontend/public/brand/argus-lockup-ui.svg`
- Create: `frontend/public/brand/argus-symbol-ui.svg`
- Create: `frontend/src/components/layout/ProductLockup.tsx`
- Modify: `frontend/src/index.css`
- Modify: `frontend/src/components/ui/button.tsx`
- Modify: `frontend/src/components/ui/badge.tsx`
- Modify: `frontend/src/components/ui/input.tsx`
- Modify: `frontend/src/components/ui/select.tsx`
- Modify: `frontend/src/components/ui/table.tsx`
- Modify: `frontend/src/components/ui/dialog.tsx`
- Test: `frontend/src/pages/SignIn.test.tsx`

- [ ] **Step 1: Write the failing sign-in brand test**

```tsx
import { render, screen } from "@testing-library/react";
import { describe, expect, test, vi } from "vitest";

vi.mock("@/stores/auth-store", () => ({
  useAuthStore: (selector: (state: { signIn: () => Promise<void> }) => unknown) =>
    selector({ signIn: vi.fn().mockResolvedValue(undefined) }),
}));

import { SignInPage } from "@/pages/SignIn";

describe("SignInPage", () => {
  test("renders the ProductLockup and a single primary sign-in action", () => {
    render(<SignInPage />);

    expect(screen.getByAltText(/Argus product lockup/i)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /^sign in$/i })).toBeInTheDocument();
    expect(screen.getByText(/vigilant intelligence/i)).toBeInTheDocument();
  });
});
```

- [ ] **Step 2: Run the failing test**

Run:

```bash
cd /Users/yann.moren/vision/frontend
corepack pnpm exec vitest run src/pages/SignIn.test.tsx
```

Expected: FAIL because `SignInPage` does not yet render the shared `ProductLockup`.

- [ ] **Step 3: Add the approved brand assets and shared brand component**

Copy the selected logo files into `frontend/public/brand/` and add the shared component:

```tsx
// frontend/src/components/layout/ProductLockup.tsx
type ProductLockupProps = {
  compact?: boolean;
  symbolOnly?: boolean;
  className?: string;
};

export function ProductLockup({
  compact = false,
  symbolOnly = false,
  className,
}: ProductLockupProps) {
  if (symbolOnly) {
    return (
      <img
        src="/brand/argus-symbol-ui.svg"
        alt="Argus symbol"
        className={className ?? "h-11 w-11 rounded-[0.95rem]"}
      />
    );
  }

  return (
    <img
      src="/brand/argus-lockup-ui.svg"
      alt="Argus product lockup"
      className={
        className ??
        (compact ? "h-10 w-auto" : "h-12 w-auto")
      }
    />
  );
}
```

Then set new global matte tokens:

```css
/* frontend/src/index.css */
:root {
  --argus-bg-obsidian: #0a0d12;
  --argus-bg-charcoal: #151a22;
  --argus-surface-1: rgba(12, 17, 24, 0.94);
  --argus-surface-2: rgba(17, 23, 31, 0.96);
  --argus-surface-3: rgba(255, 255, 255, 0.025);
  --argus-border-soft: rgba(255, 255, 255, 0.07);
  --argus-text-primary: #f4f7fb;
  --argus-text-secondary: #97a9c0;
  --argus-accent-cerulean: #35b8ff;
  --argus-accent-violet: #9b7cff;
}
```

Update shared primitives to use flatter matte styling:

```tsx
// frontend/src/components/ui/button.tsx
className={cn(
  "inline-flex items-center justify-center rounded-[1rem] border border-white/10 bg-[rgba(255,255,255,0.04)] px-4 py-2.5 text-sm font-medium text-[#eef4ff] transition duration-200 hover:border-[#355888] hover:bg-[rgba(255,255,255,0.07)] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#74a8ff]/50 focus-visible:ring-offset-2 focus-visible:ring-offset-[#0a1018] disabled:cursor-not-allowed disabled:opacity-60",
  className,
)}
```

```tsx
// Primary CTA usage stays opt-in via className:
<Button className="border-transparent bg-[linear-gradient(135deg,#35b8ff_0%,#6d84ff_100%)] text-[#06111a] shadow-[0_18px_38px_-24px_rgba(53,184,255,0.55)] hover:brightness-110" />
```

- [ ] **Step 4: Re-run the test**

Run:

```bash
cd /Users/yann.moren/vision/frontend
corepack pnpm exec vitest run src/pages/SignIn.test.tsx
```

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add frontend/public/brand/argus-lockup-ui.svg frontend/public/brand/argus-symbol-ui.svg frontend/src/components/layout/ProductLockup.tsx frontend/src/index.css frontend/src/components/ui/button.tsx frontend/src/components/ui/badge.tsx frontend/src/components/ui/input.tsx frontend/src/components/ui/select.tsx frontend/src/components/ui/table.tsx frontend/src/components/ui/dialog.tsx frontend/src/pages/SignIn.test.tsx
git commit -m "feat: add Argus matte UI foundations"
```

## Task 2: Build The Unified Left Rail Workspace Shell

**Files:**
- Create: `frontend/src/components/layout/AppIconRail.tsx`
- Create: `frontend/src/components/layout/AppContextRail.tsx`
- Create: `frontend/src/components/layout/PageHeader.tsx`
- Create: `frontend/src/components/layout/PageUtilityBar.tsx`
- Create: `frontend/src/components/layout/InspectorPanel.tsx`
- Modify: `frontend/src/components/layout/AppShell.tsx`
- Modify: `frontend/src/components/layout/AppShell.test.tsx`
- Modify: `frontend/src/components/layout/TenantSwitcher.tsx`
- Modify: `frontend/src/components/layout/UserMenu.tsx`
- Modify: `frontend/src/components/layout/TopNav.tsx`

- [ ] **Step 1: Update the shell regression test first**

```tsx
test("renders icon rail, grouped navigation, and removes the permanent management aside", () => {
  render(
    <QueryClientProvider client={createQueryClient()}>
      <MemoryRouter future={{ v7_relativeSplatPath: true, v7_startTransition: true }}>
        <AppShell>
          <div>Page body</div>
        </AppShell>
      </MemoryRouter>
    </QueryClientProvider>,
  );

  expect(screen.getByLabelText(/primary workspace/i)).toBeInTheDocument();
  expect(screen.getByRole("navigation", { name: /operations/i })).toBeInTheDocument();
  expect(screen.getByRole("navigation", { name: /configuration/i })).toBeInTheDocument();
  expect(screen.queryByText(/configuration surfaces stay one step away/i)).not.toBeInTheDocument();
});
```

- [ ] **Step 2: Run the shell test to verify it fails**

Run:

```bash
cd /Users/yann.moren/vision/frontend
corepack pnpm exec vitest run src/components/layout/AppShell.test.tsx
```

Expected: FAIL because the current shell still renders the top-heavy header and management aside.

- [ ] **Step 3: Implement the new shell and navigation rails**

Use focused components instead of one oversized shell file:

```tsx
// frontend/src/components/layout/AppIconRail.tsx
const primaryIcons = [
  { label: "Dashboard", to: "/dashboard", short: "D" },
  { label: "History", to: "/history", short: "H" },
  { label: "Incidents", to: "/incidents", short: "I" },
  { label: "Settings", to: "/settings", short: "S" },
] as const;

export function AppIconRail() {
  return (
    <aside
      aria-label="Primary workspace"
      className="flex min-h-full flex-col items-center gap-3 border-r border-white/5 bg-[linear-gradient(180deg,#0a0f16,#0d131b)] px-3 py-4"
    >
      <ProductLockup symbolOnly />
      {primaryIcons.map((item) => (
        <NavLink
          key={item.label}
          to={item.to}
          className={({ isActive }) =>
            cn(
              "flex h-12 w-12 items-center justify-center rounded-[1rem] border text-sm font-semibold transition",
              isActive
                ? "border-[#43658f] bg-[#182537] text-[#f4f7fb]"
                : "border-white/8 bg-white/[0.02] text-[#9fb1c8] hover:border-[#31506f] hover:bg-white/[0.05]",
            )
          }
        >
          {item.short}
        </NavLink>
      ))}
    </aside>
  );
}
```

```tsx
// frontend/src/components/layout/AppShell.tsx
export function AppShell({ children }: PropsWithChildren) {
  return (
    <main className="min-h-screen bg-[radial-gradient(circle_at_top,rgba(53,184,255,0.08),transparent_24%),linear-gradient(180deg,#090d13_0%,#0d131b_48%,#121922_100%)] px-4 py-4 text-[#eef4ff] sm:px-6">
      <div className="mx-auto flex min-h-[calc(100vh-2rem)] max-w-[1560px] overflow-hidden rounded-[2rem] border border-white/8 bg-[linear-gradient(180deg,rgba(12,17,24,0.96),rgba(15,20,27,0.96))] shadow-[0_28px_80px_-44px_rgba(0,0,0,0.72)]">
        <AppIconRail />
        <AppContextRail />
        <section className="min-w-0 flex-1 p-5">{children}</section>
      </div>
    </main>
  );
}
```

Adapt `TenantSwitcher` and `UserMenu` into context-rail modules instead of header pills, and reduce `TopNav` to route-prefetch helpers if it still owns useful prefetch behavior.

- [ ] **Step 4: Re-run the shell test**

Run:

```bash
cd /Users/yann.moren/vision/frontend
corepack pnpm exec vitest run src/components/layout/AppShell.test.tsx
```

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add frontend/src/components/layout/AppIconRail.tsx frontend/src/components/layout/AppContextRail.tsx frontend/src/components/layout/PageHeader.tsx frontend/src/components/layout/PageUtilityBar.tsx frontend/src/components/layout/InspectorPanel.tsx frontend/src/components/layout/AppShell.tsx frontend/src/components/layout/AppShell.test.tsx frontend/src/components/layout/TenantSwitcher.tsx frontend/src/components/layout/UserMenu.tsx frontend/src/components/layout/TopNav.tsx
git commit -m "feat: add unified left rail workspace shell"
```

## Task 3: Refresh Sign-In And Route-Level Brand Entry

**Files:**
- Modify: `frontend/src/pages/SignIn.tsx`
- Modify: `frontend/src/app/router.tsx`
- Test: `frontend/src/pages/SignIn.test.tsx`

- [ ] **Step 1: Expand the sign-in test to assert the new structure**

```tsx
test("renders a brand-forward but restrained sign-in layout", () => {
  render(<SignInPage />);

  expect(screen.getByAltText(/Argus product lockup/i)).toBeInTheDocument();
  expect(screen.getByText(/Use your Argus identity provider account to continue/i)).toBeInTheDocument();
  expect(screen.getByRole("button", { name: /^sign in$/i })).toBeInTheDocument();
});
```

- [ ] **Step 2: Run the sign-in test**

Run:

```bash
cd /Users/yann.moren/vision/frontend
corepack pnpm exec vitest run src/pages/SignIn.test.tsx
```

Expected: FAIL until `SignInPage` adopts `ProductLockup` and the calmer matte composition.

- [ ] **Step 3: Implement the refreshed sign-in page**

```tsx
// frontend/src/pages/SignIn.tsx
export function SignInPage() {
  const signIn = useAuthStore((state) => state.signIn);

  return (
    <main className="min-h-screen bg-[radial-gradient(circle_at_top,rgba(53,184,255,0.12),transparent_30%),linear-gradient(180deg,#0a0f16_0%,#101720_100%)] px-6 py-8 text-[#eef4ff]">
      <div className="mx-auto grid min-h-[calc(100vh-4rem)] max-w-7xl items-center gap-10 rounded-[2rem] border border-white/8 bg-[linear-gradient(180deg,rgba(12,17,24,0.92),rgba(15,20,27,0.9))] p-8 shadow-[0_36px_120px_-56px_rgba(0,0,0,0.78)] lg:grid-cols-[1.15fr_0.85fr]">
        <section className="space-y-5">
          <ProductLockup />
          <p className="text-[11px] font-semibold uppercase tracking-[0.3em] text-[#a7bad2]">
            Vigilant intelligence, rendered with quieter confidence.
          </p>
          <h1 className="max-w-2xl text-5xl font-semibold tracking-[0.01em] text-[#f7f9ff]">
            A premium command workspace for live monitoring, forensic history, and secure evidence review.
          </h1>
          <p className="max-w-xl text-base text-[#a5b6cb]">
            Sign in with your Argus identity provider account to continue into the hybrid command center.
          </p>
        </section>

        <section className="rounded-[1.75rem] border border-white/8 bg-[rgba(10,14,20,0.88)] p-6 shadow-[inset_0_1px_0_rgba(255,255,255,0.04)]">
          <h2 className="text-2xl font-semibold text-[#f7f9ff]">Sign in</h2>
          <p className="mt-2 text-sm text-[#97a9c0]">
            Use your Argus identity provider account to continue.
          </p>
          <Button
            className="mt-6 w-full border-transparent bg-[linear-gradient(135deg,#35b8ff_0%,#6d84ff_100%)] text-[#06111a] shadow-[0_18px_38px_-24px_rgba(53,184,255,0.55)] hover:brightness-110"
            onClick={() => void signIn()}
          >
            Sign in
          </Button>
        </section>
      </div>
    </main>
  );
}
```

If `router.tsx` still imports `SignIn` with a mismatched casing, correct it in the same task rather than carrying naming debt forward.

- [ ] **Step 4: Run the sign-in test and a production build**

Run:

```bash
cd /Users/yann.moren/vision/frontend
corepack pnpm exec vitest run src/pages/SignIn.test.tsx
corepack pnpm build
```

Expected: all PASS

- [ ] **Step 5: Commit**

```bash
git add frontend/src/pages/SignIn.tsx frontend/src/pages/SignIn.test.tsx frontend/src/app/router.tsx
git commit -m "feat: refresh sign-in brand entry"
```

## Task 4: Refresh Dashboard And Introduce The Operations Workspace Pattern

**Files:**
- Create: `frontend/src/pages/Live.tsx`
- Modify: `frontend/src/app/router.tsx`
- Modify: `frontend/src/pages/Dashboard.tsx`
- Test: `frontend/src/components/layout/AppShell.test.tsx`
- Test: `frontend/e2e/prompt8-live-dashboard.spec.ts`

- [ ] **Step 1: Update the dashboard route test to check for the new utility-bar-first copy**

```tsx
test("routes authenticated users into the refreshed operations workspace", async () => {
  window.history.pushState({}, "", "/dashboard");

  const { default: App } = await import("@/App");
  render(<App />);

  expect(await screen.findByRole("link", { name: "Dashboard" })).toBeInTheDocument();
  expect(screen.getByText(/Live command surface/i)).toBeInTheDocument();
  expect(screen.queryByText(/operator-grade visibility without native-bandwidth waste/i)).not.toBeInTheDocument();
});
```

- [ ] **Step 2: Run the dashboard route test**

Run:

```bash
cd /Users/yann.moren/vision/frontend
corepack pnpm exec vitest run src/components/layout/AppShell.test.tsx
```

Expected: FAIL until the hero copy and layout are replaced.

- [ ] **Step 3: Implement the operations workspace refresh**

Refactor `DashboardPage` to use the new page primitives:

```tsx
// frontend/src/pages/Dashboard.tsx
return (
  <div className="grid gap-5 xl:grid-cols-[minmax(0,1fr)_320px]">
    <section className="min-w-0 space-y-5">
      <PageHeader
        label="Dashboard"
        title="Live command surface"
        description="Monitor active streams, resolve natural-language filters, and review telemetry without oversized hero framing."
        actions={
          <>
            <Badge>{connectionBadgeLabel(connectionState)}</Badge>
            <Badge>{cameras.length} cameras</Badge>
          </>
        }
      />

      <PageUtilityBar>
        <AgentInput ... />
      </PageUtilityBar>

      <section className="rounded-[1.6rem] border border-white/8 bg-[linear-gradient(180deg,rgba(11,16,23,0.96),rgba(8,12,18,0.96))] p-4">
        {/* existing camera grid moved here */}
      </section>
    </section>

    <InspectorPanel
      title="Current command resolution"
      subtitle="Selection-aware detail only"
    >
      {/* existing activeQuery summary */}
    </InspectorPanel>
  </div>
);
```

Split `/live` into a wrapper page only if it improves clarity:

```tsx
// frontend/src/pages/Live.tsx
export function LivePage() {
  return <DashboardPage />;
}
```

Update `router.tsx` so `/live` imports `LivePage` instead of reusing the dashboard lazy import inline.

- [ ] **Step 4: Run focused tests and the live Playwright flow**

Run:

```bash
cd /Users/yann.moren/vision/frontend
corepack pnpm exec vitest run src/components/layout/AppShell.test.tsx
corepack pnpm exec playwright test e2e/prompt8-live-dashboard.spec.ts
```

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add frontend/src/pages/Dashboard.tsx frontend/src/pages/Live.tsx frontend/src/app/router.tsx frontend/src/components/layout/AppShell.test.tsx frontend/e2e/prompt8-live-dashboard.spec.ts
git commit -m "feat: refresh operations workspace shell"
```

## Task 5: Refresh History And Incidents Into Analysis And Evidence Workspaces

**Files:**
- Modify: `frontend/src/pages/History.tsx`
- Modify: `frontend/src/pages/Incidents.tsx`
- Modify: `frontend/src/pages/History.test.tsx`
- Create: `frontend/src/pages/Incidents.test.tsx`
- Test: `frontend/e2e/prompt9-history-and-incidents.spec.ts`

- [ ] **Step 1: Add or update page tests to match the new page structure**

```tsx
// frontend/src/pages/Incidents.test.tsx
test("renders filters in the utility bar and evidence cards as the primary artifact", async () => {
  render(
    <QueryClientProvider client={createQueryClient()}>
      <IncidentsPage />
    </QueryClientProvider>,
  );

  expect(await screen.findByLabelText(/camera filter/i)).toBeInTheDocument();
  expect(screen.getByText(/Recent incident evidence/i)).toBeInTheDocument();
});
```

Update History expectations toward compact headers:

```tsx
expect(screen.getByText(/History/i)).toBeInTheDocument();
expect(screen.queryByText(/Fleet history without reshaping penalties in the browser/i)).not.toBeInTheDocument();
```

- [ ] **Step 2: Run the focused page tests**

Run:

```bash
cd /Users/yann.moren/vision/frontend
corepack pnpm exec vitest run src/pages/History.test.tsx src/pages/Incidents.test.tsx
```

Expected: FAIL until both pages adopt the new shared header and utility-bar structure.

- [ ] **Step 3: Implement the new History and Incidents layouts**

For `History.tsx`, move filters into `PageUtilityBar` and make the chart plane visually dominant:

```tsx
<PageHeader
  label="History"
  title="Forensic history"
  description="Review chart-ready event buckets, camera filters, and export controls from one analysis canvas."
  actions={<Badge>{totalCount} detections</Badge>}
/>

<PageUtilityBar>
  {/* preset range buttons, granularity select, export actions */}
</PageUtilityBar>

<div className="grid gap-5 xl:grid-cols-[minmax(0,1fr)_320px]">
  <section>{/* chart plane */}</section>
  <InspectorPanel title="Filter context" subtitle="Date window and scope">
    {/* calendar + filter modules */}
  </InspectorPanel>
</div>
```

For `Incidents.tsx`, shrink the intro, make preview media and evidence actions lead:

```tsx
<PageHeader
  label="Incidents"
  title="Evidence review"
  description="Filter recent incidents and open signed previews without losing camera context."
  actions={<Badge>{incidents.length} incidents</Badge>}
/>

<PageUtilityBar>
  {/* camera/type filters */}
</PageUtilityBar>
```

Keep the existing clip and payload behavior unchanged.

- [ ] **Step 4: Re-run tests and the prompt 9 flow**

Run:

```bash
cd /Users/yann.moren/vision/frontend
corepack pnpm exec vitest run src/pages/History.test.tsx src/pages/Incidents.test.tsx
corepack pnpm exec playwright test e2e/prompt9-history-and-incidents.spec.ts
```

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add frontend/src/pages/History.tsx frontend/src/pages/Incidents.tsx frontend/src/pages/History.test.tsx frontend/src/pages/Incidents.test.tsx frontend/e2e/prompt9-history-and-incidents.spec.ts
git commit -m "feat: refresh analysis and evidence workspaces"
```

## Task 6: Refresh Configuration Pages, Dialogs, And Camera Wizard Chrome

**Files:**
- Modify: `frontend/src/pages/Sites.tsx`
- Modify: `frontend/src/pages/Cameras.tsx`
- Modify: `frontend/src/pages/Settings.tsx`
- Modify: `frontend/src/components/sites/SiteDialog.tsx`
- Modify: `frontend/src/components/cameras/CameraWizard.tsx`
- Modify: `frontend/src/components/cameras/CameraWizard.test.tsx`
- Test: `frontend/e2e/prompt7-auth-and-camera.spec.ts`

- [ ] **Step 1: Update the wizard test headings to the new, flatter configuration wording**

```tsx
expect(
  screen.getByRole("heading", { name: /Models & Tracking/i, level: 2 }),
).toBeInTheDocument();

expect(
  screen.getByText(/Analytics ingest remains native/i),
).toBeInTheDocument();
```

Add one assertion that the wizard summary lives in a matte side panel:

```tsx
expect(screen.getByText(/Configuration summary/i)).toBeInTheDocument();
```

- [ ] **Step 2: Run the configuration-focused tests**

Run:

```bash
cd /Users/yann.moren/vision/frontend
corepack pnpm exec vitest run src/components/cameras/CameraWizard.test.tsx
```

Expected: FAIL until the refreshed wizard shell and copy land.

- [ ] **Step 3: Implement the configuration family refresh**

For `Sites.tsx` and `Cameras.tsx`, replace large intros with compact headers and cleaner action bars:

```tsx
<PageHeader
  label="Cameras"
  title="Camera configuration"
  description="Manage ingest, privacy, calibration, and browser delivery profiles."
  actions={<Button className="border-transparent bg-[linear-gradient(135deg,#35b8ff_0%,#6d84ff_100%)] text-[#06111a]">Add camera</Button>}
/>
```

For `SiteDialog.tsx`, update to the matte surface system:

```tsx
<Dialog
  open={open}
  title="Create site"
  description="Add a deployment location and operating time zone."
>
  {/* existing fields with updated Input styles */}
</Dialog>
```

For `CameraWizard.tsx`, keep behavior and payload-building logic untouched but refresh the shell:

```tsx
<div className="grid gap-5 xl:grid-cols-[minmax(0,1fr)_320px]">
  <section className="rounded-[1.8rem] border border-white/8 bg-[linear-gradient(180deg,rgba(12,17,24,0.96),rgba(15,20,27,0.96))] p-5">
    {/* step content */}
  </section>
  <InspectorPanel title="Configuration summary" subtitle={stepTitle}>
    <CameraStepSummary ... />
  </InspectorPanel>
</div>
```

For `Settings.tsx`, convert placeholder copy into a proper settings workspace scaffold using `PageHeader` plus a matte section surface.

- [ ] **Step 4: Re-run the wizard tests and prompt 7 end-to-end flow**

Run:

```bash
cd /Users/yann.moren/vision/frontend
corepack pnpm exec vitest run src/components/cameras/CameraWizard.test.tsx
corepack pnpm exec playwright test e2e/prompt7-auth-and-camera.spec.ts
```

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add frontend/src/pages/Sites.tsx frontend/src/pages/Cameras.tsx frontend/src/pages/Settings.tsx frontend/src/components/sites/SiteDialog.tsx frontend/src/components/cameras/CameraWizard.tsx frontend/src/components/cameras/CameraWizard.test.tsx frontend/e2e/prompt7-auth-and-camera.spec.ts
git commit -m "feat: refresh configuration workspaces"
```

## Task 7: Cross-App Consistency Pass And Full Verification

**Files:**
- Modify: any touched frontend files from Tasks 1-6
- Test: `frontend/src/components/layout/AppShell.test.tsx`
- Test: `frontend/src/pages/SignIn.test.tsx`
- Test: `frontend/src/pages/History.test.tsx`
- Test: `frontend/src/pages/Incidents.test.tsx`
- Test: `frontend/src/components/cameras/CameraWizard.test.tsx`
- Test: `frontend/e2e/prompt7-auth-and-camera.spec.ts`
- Test: `frontend/e2e/prompt8-live-dashboard.spec.ts`
- Test: `frontend/e2e/prompt9-history-and-incidents.spec.ts`

- [ ] **Step 1: Add final assertions for shared shell and compact page headers**

If needed, tighten existing tests so they enforce:

```tsx
expect(screen.getByRole("navigation", { name: /operations/i })).toBeInTheDocument();
expect(screen.getAllByText(/Dashboard|History|Incidents|Sites|Cameras|Settings/i).length).toBeGreaterThan(0);
```

Keep assertions focused on structure and key UX copy, not brittle pixel-perfect snapshots.

- [ ] **Step 2: Run the focused frontend test suite**

Run:

```bash
cd /Users/yann.moren/vision/frontend
corepack pnpm exec vitest run src/components/layout/AppShell.test.tsx src/pages/SignIn.test.tsx src/pages/History.test.tsx src/pages/Incidents.test.tsx src/components/cameras/CameraWizard.test.tsx src/components/ui/calendar.test.tsx
```

Expected: PASS

- [ ] **Step 3: Run the production build**

Run:

```bash
cd /Users/yann.moren/vision/frontend
corepack pnpm build
```

Expected: PASS with no new TypeScript or Vite errors

- [ ] **Step 4: Run the full prompt regression flows**

Run:

```bash
cd /Users/yann.moren/vision/frontend
corepack pnpm exec playwright test e2e/prompt7-auth-and-camera.spec.ts e2e/prompt8-live-dashboard.spec.ts e2e/prompt9-history-and-incidents.spec.ts
```

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add frontend
git commit -m "feat: finalize Argus UI refresh"
```

## Spec Coverage Check

This plan covers:

- full-product scope
- structural shell changes
- left-rail workspace navigation
- balanced density
- selected in-product logo usage
- sign-in refresh
- operations family refresh
- history and incidents refresh
- configuration family refresh
- conditional inspector behavior
- regression verification against Prompt 7, 8, and 9 flows

No approved spec section is intentionally omitted.

## Notes For The Implementer

- Keep data hooks, API contracts, and auth logic stable unless a task explicitly touches them.
- Prefer introducing shared page-chrome primitives early rather than duplicating new styling into each page.
- Do not reintroduce a permanent right rail while implementing individual pages.
- Use the selected product/UI logo asset in the shell and sign-in exactly once through `ProductLockup`, not via repeated ad hoc `<img>` tags.
- Keep the refresh product-focused. If copy starts reading like marketing, cut it down.
