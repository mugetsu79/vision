# Taste-Led OmniSight UI/UX Polish Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Produce and implement a taste-led 2026 UI/UX polish pass for OmniSight that improves Operations overload, logo/lens treatment, and product-wide visual hierarchy while preserving operator density and runtime truth.

**Architecture:** Start with an audit and visual direction lock before code. Then land focused frontend-only tasks: shared surface rules, logo/lens treatment, Operations IA, and selected page consistency updates. Keep backend contracts and runtime semantics unchanged.

**Tech Stack:** React 19, Vite, TypeScript, Tailwind v4 utilities/CSS variables in `frontend/src/index.css`, Vitest, Playwright/browser visual QA. Local `taste-skill/` is design input only and should not be staged unless explicitly requested.

---

## Source Material

Read first:

- `docs/superpowers/specs/2026-06-03-taste-led-omnisight-ui-ux-polish-design.md`
- `docs/brand/omnisight-ui-spec-sheet.md`
- `docs/superpowers/specs/2026-04-30-omnisight-ui-distinctiveness-followup-design.md`
- `docs/superpowers/specs/2026-06-03-pre-polish-operator-corrections-design.md`
- `taste-skill/SKILL.md` if the local untracked folder exists
- `taste-skill/dashboards/skill.md`
- `taste-skill/dark-luxe/skill.md`
- `taste-skill/swiss-system/skill.md`
- `taste-skill/components/style-recipes.md`

## Working Rules

- Start from `main` at the handoff commit or newer.
- Create `codex/omnisight-ui-ux-polish`.
- Do not use `git add -A`.
- Do not stage untracked scratch files or `taste-skill/`.
- Do not change backend/runtime semantics unless a real integration gap is
  found and documented.
- Preserve honest labels for unknown, stale, awaiting, offline, and
  not-reported runtime states.

## File Map To Audit

Likely files:

- `frontend/src/index.css` - tokens, surface hierarchy, motion rules.
- `frontend/src/components/brand/OmniSightField.tsx` - ambient logo field.
- `frontend/src/components/brand/OmniSightLens.tsx` - dimensional mark/lens.
- `frontend/src/components/layout/AppShell.tsx` - shell background and logo use.
- `frontend/src/components/layout/AppIconRail.tsx` - stable app identity.
- `frontend/src/components/layout/AppContextRail.tsx` - navigation hierarchy.
- `frontend/src/components/layout/workspace-surfaces.tsx` - shared surfaces.
- `frontend/src/pages/SignIn.tsx` - sign-in logo/lens stage.
- `frontend/src/pages/Dashboard.tsx` - cockpit overview.
- `frontend/src/pages/Live.tsx` - live tile density and video priority.
- `frontend/src/pages/Settings.tsx` - Operations workbench.
- `frontend/src/components/operations/*` - readiness, posture, attention, worker
  and stream surfaces.
- `frontend/src/pages/Cameras.tsx` and `frontend/src/components/cameras/*` -
  Scene setup consistency.
- `frontend/src/pages/Deployment.tsx` - installer and deployment guidance.

## Task 1: Audit Current Product Against Taste Direction

- [ ] **Step 1: Confirm branch and baseline**

Run:

```bash
git fetch origin
git switch main
git pull --ff-only origin main
git switch -c codex/omnisight-ui-ux-polish
git status -sb
```

Expected: branch is `codex/omnisight-ui-ux-polish`; only existing unrelated
untracked scratch files are present.

- [ ] **Step 2: Read design inputs**

Read the source material listed above. Confirm whether `taste-skill/` exists
locally. If it does not, continue from the tracked spec and brand docs.

- [ ] **Step 3: Capture product screenshots**

Run the local frontend or installed stack and capture desktop plus mobile views
for:

- Sign-in
- Dashboard
- Live
- Operations
- Scenes
- Evidence
- Sites
- Deployment

Widths: 375, 768, 1024, 1440.

- [ ] **Step 4: Write a short audit note**

Create `docs/superpowers/status/2026-06-03-omnisight-ui-ux-polish-audit.md`
with:

- top five issues by operator impact
- logo/lens recommendation
- Operations IA recommendation
- pages that should not be touched in the first implementation slice
- screenshots or screenshot paths if captured locally

Commit:

```bash
git add docs/superpowers/status/2026-06-03-omnisight-ui-ux-polish-audit.md
git commit -m "docs(ui): audit taste-led polish scope"
```

## Task 2: Lock The Logo And Motion Direction

- [ ] **Step 1: Add or update tests around logo/lens behavior**

Target existing tests or create focused tests near:

- `frontend/src/components/brand/OmniSightField.test.tsx`
- `frontend/src/components/brand/OmniSightLens.test.tsx`
- `frontend/src/pages/SignIn.test.tsx`
- `frontend/src/components/layout/AppShell.test.tsx`

Assertions should cover:

- workflow shell does not rely on a prominent moving 3D sphere
- stable 2D lockup remains visible in app chrome
- sign-in/dashboard can still use a deliberate dimensional mark
- reduced-motion path remains usable

- [ ] **Step 2: Implement the revised logo treatment**

Likely direction:

- make app chrome logo stable and mostly 2D
- reduce or remove ambient workflow-page logo motion
- keep dimensional mark only in intentional contexts
- make motion event/state-driven instead of perpetual decoration

- [ ] **Step 3: Verify**

Run:

```bash
corepack pnpm --dir frontend exec vitest run \
  src/components/brand/OmniSightField.test.tsx \
  src/components/brand/OmniSightLens.test.tsx \
  src/pages/SignIn.test.tsx \
  src/components/layout/AppShell.test.tsx
corepack pnpm --dir frontend build
```

Commit:

```bash
git add frontend/src/components/brand frontend/src/components/layout frontend/src/pages/SignIn.tsx frontend/src/pages/SignIn.test.tsx frontend/src/index.css
git commit -m "fix(ui): refine omnisight logo treatment"
```

## Task 3: Rework Operations Into Attention-First Sections

- [ ] **Step 1: Write focused Operations tests**

Update or add tests around:

- `frontend/src/pages/Settings.test.tsx`
- `frontend/src/components/operations/SceneIntelligenceMatrix.test.tsx`
- relevant worker/configuration panel tests

Assertions should verify:

- urgent fleet/scene status appears before low-level diagnostics
- Workers, Stream Diagnostics, Deployment Nodes, Configuration, and Installer
  Guidance are navigable or clearly sectioned
- diagnostic hashes, copy diagnostics, and low-level runtime metadata are
  progressively disclosed
- unknown/stale/not-reported states remain explicit

- [ ] **Step 2: Implement Operations IA changes**

Prefer:

- an attention strip or command overview at the top
- section navigation or anchors
- dense rows for workers/scenes
- collapsible diagnostic detail blocks
- fewer identical card shells

- [ ] **Step 3: Verify**

Run:

```bash
corepack pnpm --dir frontend exec vitest run \
  src/pages/Settings.test.tsx \
  src/components/operations/SceneIntelligenceMatrix.test.tsx \
  src/lib/operational-health.test.ts
corepack pnpm --dir frontend build
```

Commit:

```bash
git add frontend/src/pages/Settings.tsx frontend/src/pages/Settings.test.tsx frontend/src/components/operations frontend/src/lib/operational-health.test.ts frontend/src/index.css
git commit -m "feat(operations): organize attention-first workbench"
```

## Task 4: Apply Surface Hierarchy Across The First Slice

- [ ] **Step 1: Choose the first page slice**

Default recommendation:

- Dashboard
- Live
- Scenes setup header/calibration surface
- Deployment installer guidance

Avoid touching every page if the Operations changes are already large.

- [ ] **Step 2: Write/update focused tests**

Use existing page tests:

```bash
corepack pnpm --dir frontend exec vitest run \
  src/pages/Dashboard.test.tsx \
  src/pages/Live.test.tsx \
  src/pages/Cameras.test.tsx \
  src/pages/Deployment.test.tsx
```

Expected first run may fail after test updates until implementation lands.

- [ ] **Step 3: Implement shared surface tuning**

Use `dashboards` density as the primary taste input:

- instrument bands instead of repeated KPI cards
- black media slabs for video/evidence
- stricter Swiss alignment and spacing
- dark-luxe material restraint without decorative glow
- no nested cards unless they communicate hierarchy

- [ ] **Step 4: Verify**

Run:

```bash
corepack pnpm --dir frontend exec vitest run \
  src/pages/Dashboard.test.tsx \
  src/pages/Live.test.tsx \
  src/pages/Cameras.test.tsx \
  src/pages/Deployment.test.tsx
corepack pnpm --dir frontend build
```

Commit:

```bash
git add frontend/src/pages/Dashboard.tsx frontend/src/pages/Dashboard.test.tsx frontend/src/pages/Live.tsx frontend/src/pages/Live.test.tsx frontend/src/pages/Cameras.tsx frontend/src/pages/Cameras.test.tsx frontend/src/pages/Deployment.tsx frontend/src/pages/Deployment.test.tsx frontend/src/components/layout frontend/src/index.css
git commit -m "style(ui): tune omnisight surface hierarchy"
```

## Task 5: Browser Visual QA And Final Polish

- [ ] **Step 1: Run visual QA**

Use Playwright or the browser tool to inspect:

- Sign-in
- Dashboard
- Live
- Operations
- Scenes
- Deployment

Widths: 375, 768, 1024, 1440.

Check:

- no horizontal overflow
- text does not overlap controls
- logo/lens no longer feels like a distracting moving sphere
- video/evidence media remains unobscured
- Operations can be scanned quickly
- reduced-motion path is acceptable

- [ ] **Step 2: Run final verification**

Run:

```bash
corepack pnpm --dir frontend exec vitest run \
  src/components/brand/OmniSightField.test.tsx \
  src/components/brand/OmniSightLens.test.tsx \
  src/components/layout/AppShell.test.tsx \
  src/pages/Dashboard.test.tsx \
  src/pages/Live.test.tsx \
  src/pages/Settings.test.tsx \
  src/pages/Cameras.test.tsx \
  src/pages/Deployment.test.tsx \
  src/lib/operational-health.test.ts
corepack pnpm --dir frontend build
git diff --check
git status --short --branch
```

- [ ] **Step 3: Commit final visual QA fixes**

If visual QA found fixes:

```bash
git status --short
git add frontend/src/index.css
git add frontend/src/components/brand/OmniSightField.tsx frontend/src/components/brand/OmniSightField.test.tsx
git add frontend/src/components/brand/OmniSightLens.tsx frontend/src/components/brand/OmniSightLens.test.tsx
git add frontend/src/components/layout/AppShell.tsx frontend/src/components/layout/AppShell.test.tsx
git add frontend/src/components/layout/workspace-surfaces.tsx frontend/src/components/layout/workspace-surfaces.test.tsx
git add frontend/src/pages/Dashboard.tsx frontend/src/pages/Dashboard.test.tsx
git add frontend/src/pages/Live.tsx frontend/src/pages/Live.test.tsx
git add frontend/src/pages/Settings.tsx frontend/src/pages/Settings.test.tsx
git add frontend/src/pages/Cameras.tsx frontend/src/pages/Cameras.test.tsx
git add frontend/src/pages/Deployment.tsx frontend/src/pages/Deployment.test.tsx
git commit -m "fix(ui): polish omnisight responsive surfaces"
```

Omit any `git add` line for a file that was not changed. If no fixes were
needed, do not create an empty commit.

## Completion

Before reporting completion:

- confirm no untracked scratch files were staged
- summarize which pages changed
- summarize runtime semantics preserved
- include verification commands and results
- update the handoff document with the final commit range
