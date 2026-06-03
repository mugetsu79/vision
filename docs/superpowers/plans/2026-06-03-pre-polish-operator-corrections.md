# Pre-Polish Operator Corrections Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fix concrete operator-facing layout, illustration, Operations matrix, and installer-copy issues before the broader OmniSight UI/UX polish pass.

**Architecture:** Keep runtime behavior unchanged. Make targeted frontend component changes in Scene setup, the reusable calibration SVG, Operations scene readiness, and Deployment installer cards. Use focused React Testing Library tests plus existing regression suites to verify the corrections.

**Tech Stack:** React, TypeScript, Vitest, Testing Library, Tailwind utility classes, Lucide React, existing OmniSight workspace components.

---

## Scope Check

This plan implements one focused correction pass:

- responsive Scene setup Browser stream layout
- clearer detection-region calibration illustration
- easier-to-scan Operations scene readiness component
- installer target wording that distinguishes host wrapper from Docker runtime

It does not include broader Operations information architecture, route renames,
runtime behavior changes, backend changes, installer script changes, or new
dependencies.

## File Structure And Ownership

Modify:

- `frontend/src/components/cameras/CameraWizard.tsx`
  - tighten the `Privacy, Processing & Delivery` / browser stream layout
  - rename visible `Live delivery` copy to `Browser stream`
  - avoid side-panel overflow at medium widths
- `frontend/src/components/cameras/CameraWizard.test.tsx`
  - assert browser stream copy and processed controls remain present
- `frontend/src/components/guidance/CalibrationFlowIllustration.tsx`
  - add mode-specific coordinate/layout data for `regions`
  - keep connector lines behind overlays
  - improve labels and avoid cramped exclusion placement
- `frontend/src/components/guidance/guidance.test.tsx`
  - assert region SVG labels remain exact and accessible
- `frontend/src/components/operations/SceneIntelligenceMatrix.tsx`
  - convert table to responsive scene readiness rows
  - replace `Mode` cell copy with a human placement line
  - group signals into Runtime and Stream clusters
- `frontend/src/components/operations/SceneIntelligenceMatrix.test.tsx`
  - update assertions from table/mode text to readiness rows and placement copy
- `frontend/src/pages/Deployment.tsx`
  - rename installer target cards and details
- `frontend/src/pages/Deployment.test.tsx`
  - update installer package guidance assertions

No backend files should change.

## Task 1: Scene Setup Browser Stream Layout

**Files:**

- Modify: `frontend/src/components/cameras/CameraWizard.tsx`
- Test: `frontend/src/components/cameras/CameraWizard.test.tsx`

- [ ] **Step 1: Add a failing copy/layout-focused test**

In `frontend/src/components/cameras/CameraWizard.test.tsx`, update the existing
wizard progression test that reaches `Privacy, Processing & Delivery`:

```tsx
expect(screen.getByText(/browser stream/i)).toBeInTheDocument();
expect(screen.queryByText(/live delivery/i)).not.toBeInTheDocument();
expect(screen.getByLabelText(/transport profile/i)).toBeInTheDocument();
expect(screen.getByLabelText(/processed custom/i)).toBeChecked();
expect(screen.getByLabelText(/live rendition resolution/i)).toHaveValue("720p");
expect(screen.getByLabelText(/live rendition fps cap/i)).toHaveValue("25");
```

Keep the later select/change assertions in the same test so processed rendition
behavior is still covered.

- [ ] **Step 2: Run the focused Camera Wizard test and confirm failure**

Run:

```bash
corepack pnpm --dir frontend exec vitest run src/components/cameras/CameraWizard.test.tsx
```

Expected: FAIL because `Browser stream` is not rendered yet and `Live delivery`
still appears.

- [ ] **Step 3: Rename and compact the browser stream section**

In `frontend/src/components/cameras/CameraWizard.tsx`, replace the current
section header:

```tsx
<p className="text-[11px] font-semibold uppercase tracking-[0.24em] text-[#8ea4c7]">
  Live delivery
</p>
<p className="mt-1 text-sm text-[#9eb2cf]">
  Transport controls relay access. Rendition controls the video operators see.
</p>
```

with:

```tsx
<p className="text-[11px] font-semibold uppercase tracking-[0.24em] text-[#8ea4c7]">
  Browser stream
</p>
<p className="mt-1 max-w-2xl text-sm text-[#9eb2cf]">
  Choose the transport path and the video rendition operators will watch in Live.
</p>
```

- [ ] **Step 4: Make the controls stack before overflow**

In the same section, replace:

```tsx
<div className="grid gap-3 lg:grid-cols-[minmax(16rem,1fr)_minmax(20rem,1.4fr)]">
```

with:

```tsx
<div className="grid gap-4 xl:grid-cols-[minmax(14rem,0.9fr)_minmax(0,1.4fr)]">
```

Replace the rendition radio group class:

```tsx
<div className="grid gap-2 sm:grid-cols-3">
```

with:

```tsx
<div className="grid gap-2 md:grid-cols-3">
```

Replace each rendition label class:

```tsx
className={`flex items-center justify-center gap-2 rounded-[0.8rem] border px-3 py-2 text-xs font-semibold transition ${
```

with:

```tsx
className={`flex min-h-12 items-center justify-center gap-2 rounded-[0.8rem] border px-3 py-2 text-center text-xs font-semibold leading-4 transition ${
```

Replace the processed control grid:

```tsx
<div className="grid gap-2 sm:grid-cols-2">
```

with:

```tsx
<div className="grid gap-2 md:grid-cols-2">
```

- [ ] **Step 5: Run the focused Camera Wizard test**

Run:

```bash
corepack pnpm --dir frontend exec vitest run src/components/cameras/CameraWizard.test.tsx
```

Expected: PASS.

- [ ] **Step 6: Commit this task if working task-by-task**

```bash
git add frontend/src/components/cameras/CameraWizard.tsx frontend/src/components/cameras/CameraWizard.test.tsx
git commit -m "fix(cameras): tighten browser stream layout"
```

## Task 2: Detection Region Illustration

**Files:**

- Modify: `frontend/src/components/guidance/CalibrationFlowIllustration.tsx`
- Test: `frontend/src/components/guidance/guidance.test.tsx`

- [ ] **Step 1: Add a failing test for the region-specific SVG layout**

In `frontend/src/components/guidance/guidance.test.tsx`, replace the body of
`CalibrationFlowIllustration can show region guidance` with:

```tsx
const { container } = render(<CalibrationFlowIllustration mode="regions" />);

expect(
  screen.getByRole("img", { name: /detection regions refine the calibrated plane/i }),
).toBeInTheDocument();
const includeRegion = screen.getByText(/^include region$/i);
const exclusionRegion = screen.getByText(/^exclusion region$/i);
expect(includeRegion).toHaveAttribute("y", "88");
expect(exclusionRegion).toHaveAttribute("y", "148");

const exclusionShape = container.querySelector("[data-region='exclusion']");
expect(exclusionShape).toHaveAttribute("x", "318");
expect(exclusionShape).toHaveAttribute("y", "108");
```

- [ ] **Step 2: Run the guidance test and confirm failure**

Run:

```bash
corepack pnpm --dir frontend exec vitest run src/components/guidance/guidance.test.tsx
```

Expected: FAIL because region shapes do not have `data-region` attributes and
the current label coordinates differ.

- [ ] **Step 3: Move region shapes and labels into clearer positions**

In `frontend/src/components/guidance/CalibrationFlowIllustration.tsx`, update
the `mode === "regions"` block to:

```tsx
{mode === "regions" ? (
  <g>
    <rect
      data-region="include"
      x="284"
      y="96"
      width="48"
      height="38"
      rx="8"
      fill="#6fe0c5"
      opacity="0.18"
      stroke="#6fe0c5"
      strokeWidth="1.5"
    />
    <text x="308" y="88" textAnchor="middle" fill="#bcefe3" fontSize="10">
      include region
    </text>
    <rect
      data-region="exclusion"
      x="318"
      y="108"
      width="30"
      height="28"
      rx="6"
      fill="#ffb86b"
      opacity="0.18"
      stroke="#ffb86b"
      strokeWidth="1.5"
    />
    <text x="333" y="148" textAnchor="middle" fill="#ffd9a1" fontSize="10">
      exclusion region
    </text>
  </g>
) : null}
```

This keeps the exclusion region inside the top-down plane and away from the
measured-distance ruler.

- [ ] **Step 4: Run the guidance test**

Run:

```bash
corepack pnpm --dir frontend exec vitest run src/components/guidance/guidance.test.tsx
```

Expected: PASS.

- [ ] **Step 5: Commit this task if working task-by-task**

```bash
git add frontend/src/components/guidance/CalibrationFlowIllustration.tsx frontend/src/components/guidance/guidance.test.tsx
git commit -m "fix(guidance): clarify region calibration illustration"
```

## Task 3: Operations Scene Readiness Rows

**Files:**

- Modify: `frontend/src/components/operations/SceneIntelligenceMatrix.tsx`
- Test: `frontend/src/components/operations/SceneIntelligenceMatrix.test.tsx`

- [ ] **Step 1: Update the matrix test for row/card semantics**

In `frontend/src/components/operations/SceneIntelligenceMatrix.test.tsx`,
rename the first test to:

```tsx
test("renders scene readiness rows with grouped runtime and stream signals", () => {
```

Replace the heading and mode assertions:

```tsx
expect(
  screen.getByRole("heading", { name: /scene intelligence matrix/i }),
).toBeInTheDocument();
expect(screen.getByText("central / central")).toBeInTheDocument();
expect(screen.getByText("edge / orin1")).toBeInTheDocument();
```

with:

```tsx
expect(
  screen.getByRole("heading", { name: /scene readiness/i }),
).toBeInTheDocument();
expect(
  screen.getByText(/central processing on master supervisor/i),
).toBeInTheDocument();
expect(screen.getByText(/edge processing on orin1/i)).toBeInTheDocument();
expect(screen.queryByText("central / central")).not.toBeInTheDocument();
expect(screen.queryByText("edge / orin1")).not.toBeInTheDocument();
expect(screen.getAllByText("Runtime")).toHaveLength(2);
expect(screen.getAllByText("Stream")).toHaveLength(2);
```

Keep the existing assertions for privacy, rules, worker, transport, live
rendition, telemetry, and action links.

- [ ] **Step 2: Run the matrix test and confirm failure**

Run:

```bash
corepack pnpm --dir frontend exec vitest run src/components/operations/SceneIntelligenceMatrix.test.tsx
```

Expected: FAIL because the component still renders the table heading and raw
mode/node text.

- [ ] **Step 3: Add placement and grouped signal helpers**

In `frontend/src/components/operations/SceneIntelligenceMatrix.tsx`, add:

```tsx
function placementLabel(row: SceneHealthRow) {
  if (row.processingMode.toLowerCase() === "edge") {
    return `Edge processing on ${row.nodeLabel}`;
  }
  const centralLabel =
    row.nodeLabel.toLowerCase() === "central"
      ? "master supervisor"
      : row.nodeLabel;
  return `Central processing on ${centralLabel}`;
}

function SignalGroup({
  title,
  signals,
}: {
  title: string;
  signals: Array<{ label: string; signal: HealthSignal }>;
}) {
  return (
    <div className="rounded-lg border border-white/8 bg-black/15 p-3">
      <p className="text-[10px] font-semibold uppercase tracking-[0.18em] text-[var(--vz-text-muted)]">
        {title}
      </p>
      <div className="mt-2 grid gap-2">
        {signals.map(({ label, signal }) => (
          <div key={label} className="grid gap-1">
            <span className="text-[11px] font-semibold uppercase tracking-[0.14em] text-[var(--vz-text-muted)]">
              {label}
            </span>
            <HealthCell signal={signal} />
          </div>
        ))}
      </div>
    </div>
  );
}
```

- [ ] **Step 4: Replace the table with responsive readiness rows**

In the non-empty branch of `SceneIntelligenceMatrix`, replace the
`overflow-x-auto` table with:

```tsx
<div className="grid gap-3 p-4">
  {rows.map((row) => (
    <article
      key={row.cameraId}
      className="grid gap-4 rounded-xl border border-white/8 bg-white/[0.025] p-4 xl:grid-cols-[minmax(14rem,0.8fr)_minmax(0,1fr)_minmax(0,1fr)_auto] xl:items-start"
    >
      <div>
        <h3 className="text-base font-semibold text-[var(--vz-text-primary)]">
          {row.cameraName}
        </h3>
        <p className="mt-1 text-sm text-[var(--vz-text-secondary)]">
          {row.siteName}
        </p>
        <p className="mt-2 text-sm text-[var(--vz-text-muted)]">
          {placementLabel(row)}
        </p>
      </div>

      <SignalGroup
        title="Runtime"
        signals={[
          { label: "Worker", signal: row.worker },
          { label: "Telemetry", signal: row.telemetry },
          { label: "Rules", signal: row.rules },
        ]}
      />

      <SignalGroup
        title="Stream"
        signals={[
          { label: "Transport", signal: row.transport },
          { label: "Live rendition", signal: row.liveRendition },
          { label: "Privacy", signal: row.privacy },
        ]}
      />

      <Link
        to={row.actionHref}
        aria-label={`${row.actionLabel} for ${row.cameraName}`}
        className="self-start text-sm font-semibold text-[var(--vz-lens-cerulean)] transition hover:text-[var(--vz-text-primary)]"
      >
        {row.actionLabel}
      </Link>
    </article>
  ))}
</div>
```

Also change the heading from `Scene intelligence matrix` to `Scene readiness`.

- [ ] **Step 5: Run the matrix test**

Run:

```bash
corepack pnpm --dir frontend exec vitest run src/components/operations/SceneIntelligenceMatrix.test.tsx
```

Expected: PASS.

- [ ] **Step 6: Commit this task if working task-by-task**

```bash
git add frontend/src/components/operations/SceneIntelligenceMatrix.tsx frontend/src/components/operations/SceneIntelligenceMatrix.test.tsx
git commit -m "fix(operations): simplify scene readiness rows"
```

## Task 4: Installer Target Copy

**Files:**

- Modify: `frontend/src/pages/Deployment.tsx`
- Test: `frontend/src/pages/Deployment.test.tsx`

- [ ] **Step 1: Update installer target test expectations**

In `frontend/src/pages/Deployment.test.tsx`, replace:

```tsx
expect(within(workspace).getByText(/macOS master/i)).toBeInTheDocument();
expect(within(workspace).getByText(/Linux master/i)).toBeInTheDocument();
```

with:

```tsx
expect(within(workspace).getByText(/MacBook local master/i)).toBeInTheDocument();
expect(within(workspace).getByText(/Linux host master/i)).toBeInTheDocument();
expect(
  within(workspace).getByText(/Docker-backed local master/i),
).toBeInTheDocument();
expect(
  within(workspace).getByText(/launchd wrapper for Docker-backed master services/i),
).toBeInTheDocument();
```

Keep the command assertions unchanged.

- [ ] **Step 2: Run the Deployment test and confirm failure**

Run:

```bash
corepack pnpm --dir frontend exec vitest run src/pages/Deployment.test.tsx
```

Expected: FAIL because the old installer copy is still rendered.

- [ ] **Step 3: Update installer target copy**

In `frontend/src/pages/Deployment.tsx`, replace the first two
`installerTargets` entries with:

```tsx
{
  title: "MacBook local master",
  platform: "Docker-backed local master",
  command: "installer/macos/install-master.sh",
  detail:
    "Creates a launchd wrapper for Docker-backed master services and opens first-run setup.",
  icon: Laptop,
},
{
  title: "Linux host master",
  platform: "Systemd Docker master",
  command: "installer/linux/install-master.sh",
  detail: "Installs the systemd-owned Docker master appliance on the host.",
  icon: Server,
},
```

Leave the Jetson target command unchanged.

- [ ] **Step 4: Run the Deployment test**

Run:

```bash
corepack pnpm --dir frontend exec vitest run src/pages/Deployment.test.tsx
```

Expected: PASS.

- [ ] **Step 5: Commit this task if working task-by-task**

```bash
git add frontend/src/pages/Deployment.tsx frontend/src/pages/Deployment.test.tsx
git commit -m "fix(deployment): clarify installer host targets"
```

## Task 5: Final Verification

**Files:**

- No new implementation files.

- [ ] **Step 1: Run focused correction tests**

Run:

```bash
corepack pnpm --dir frontend exec vitest run \
  src/components/cameras/CameraWizard.test.tsx \
  src/components/guidance/guidance.test.tsx \
  src/components/operations/SceneIntelligenceMatrix.test.tsx \
  src/pages/Deployment.test.tsx
```

Expected: PASS.

- [ ] **Step 2: Run related regressions**

Run:

```bash
corepack pnpm --dir frontend exec vitest run \
  src/pages/Settings.test.tsx \
  src/pages/Live.test.tsx \
  src/lib/operational-health.test.ts
```

Expected: PASS.

- [ ] **Step 3: Run the frontend build**

Run:

```bash
corepack pnpm --dir frontend build
```

Expected: PASS.

- [ ] **Step 4: Browser visual QA**

Run the app locally and inspect at least these widths:

- 1024px desktop/tablet-width browser
- 1440px desktop browser

Check:

- Scene setup `Browser stream` controls do not overlap the sidebar.
- Region help diagram is readable and labels do not collide.
- Operations scene readiness rows scan cleanly.
- Installer target cards read as host targets and keep commands visible.

- [ ] **Step 5: Commit final docs if changed**

```bash
git add docs/superpowers/specs/2026-06-03-pre-polish-operator-corrections-design.md docs/superpowers/plans/2026-06-03-pre-polish-operator-corrections.md
git commit -m "docs: plan pre-polish operator corrections"
```

## Self-Review

Before implementation starts:

- Confirm the spec requirements map to Tasks 1-4.
- Confirm no backend files are included.
- Confirm installer command paths remain unchanged.
- Confirm Operations overload remains deferred to the broader UI/UX polish spec.
