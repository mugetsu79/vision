# Operator Focus Consistency Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make scene, site, and FleetOps context selection explicit across the operator UI, while adding searchable/paginated/editable Sites inventory and a stable searchable History scene filter.

**Architecture:** Reuse existing React workspace surfaces and TanStack Query hooks. Add small shared selector helpers/components where multiple pages need the same explicit focus behavior. Keep backend contracts unchanged except for using the existing generated core site update endpoint.

**Tech Stack:** React 19, TypeScript, TanStack Query, Vitest, Testing Library, Playwright, pnpm.

---

## Non-Negotiable Constraints

- Preserve all `CC-*` constraints from FleetOps runtime and operator-completion
  plans.
- Do not add traffic/public-space runtime, home-lab packs/status/UI,
  proprietary carrier SDKs, payment/accounting integrations, or runtime
  semantic changes.
- Do not stage unrelated scratch files, `.claude/`, `.codex/`, `.superpowers/`,
  `.vite/`, screenshots, or `taste-skill/`.
- Do not use `git add -A`.

## Task 1: Scene Focus Invariant

**Files:**
- Modify: `frontend/src/pages/Cameras.test.tsx`
- Modify: `frontend/src/pages/Settings.test.tsx`
- Modify: `frontend/src/pages/Live.test.tsx`
- Modify: `frontend/src/pages/Cameras.tsx`
- Modify: `frontend/src/pages/Settings.tsx`
- Modify: `frontend/src/pages/Live.tsx`

- [x] Write failing tests showing no default scene detail on Scenes,
  Operations, and Live.
- [x] Run targeted tests and verify they fail on current first-scene/all-scene
  fallback behavior.
- [x] Remove implicit first-scene/all-scene detail fallbacks while keeping
  search and explicit checkbox selection working.
- [x] Run targeted tests green.

## Task 2: Stable Searchable History Scope

**Files:**
- Modify: `frontend/src/pages/History.test.tsx`
- Modify: `frontend/src/hooks/use-history.ts`
- Modify: `frontend/src/pages/History.tsx`
- Modify: `frontend/src/components/history/HistoryTrendPanel.tsx`

- [x] Write failing tests for no-scope History empty state, searchable scene
  selector behavior, and no full-page loading blink on filter refetch.
- [x] Run the History tests red.
- [x] Replace raw scene multi-select with a searchable selector that writes the
  existing `cameras` URL state.
- [x] Disable History series/classes queries until a selected scene exists.
- [x] Keep prior chart/detail surface during refetch with inline pending copy.
- [x] Run History tests green.

## Task 3: Sites Search, Pagination, And Edit

**Files:**
- Modify: `frontend/src/pages/Sites.test.tsx`
- Modify: `frontend/src/hooks/use-sites.ts`
- Modify: `frontend/src/components/sites/SiteDialog.tsx`
- Modify: `frontend/src/pages/Sites.tsx`

- [x] Write failing tests for search filtering, 10/25/50 page-size caps, page
  navigation, and edit-site submission.
- [x] Run Sites tests red.
- [x] Add `useUpdateSite`, edit-mode dialog defaults, search, page size, and
  pagination.
- [x] Run Sites tests green.

## Task 4: FleetOps Explicit Vessel/Site Scope

**Files:**
- Create: `frontend/src/components/fleetops/FleetOpsScopeSelector.tsx`
- Modify: `frontend/src/pages/FleetOpsEvidence.test.tsx`
- Modify: `frontend/src/pages/FleetOpsSupport.test.tsx`
- Modify: `frontend/src/pages/FleetOpsOnboarding.test.tsx`
- Modify: `frontend/src/pages/FleetOpsEvidence.tsx`
- Modify: `frontend/src/pages/FleetOpsSupport.tsx`
- Modify: `frontend/src/pages/FleetOpsOnboarding.tsx`
- Modify: `frontend/src/components/fleetops/types.ts`

- [x] Write failing tests proving FleetOps pages do not auto-bind the first
  vessel/site and actions stay disabled until selection.
- [x] Run FleetOps page tests red.
- [x] Add shared vessel/site selector and use selected vessel/site state on
  Evidence, Support, and Onboarding.
- [x] Run FleetOps page tests green.

## Task 5: Verification And Checkpoint

**Files:**
- No new production files unless required by failures.

- [x] Run targeted page tests.
- [x] Run `corepack pnpm lint`.
- [x] Run `corepack pnpm build`.
- [x] Run full frontend tests if targeted/lint/build are clean.
- [x] Browser-check the changed pages with realistic mocked data. Browser
  reached the protected sign-in route in the isolated in-app session; protected
  page behavior was verified through focused UI tests instead.
- [ ] Commit focused changes and push `origin codex/sceneops-pack-registry`.

Suggested commit:

```bash
git add docs/superpowers/specs/2026-06-07-operator-focus-consistency-design.md docs/superpowers/plans/2026-06-07-operator-focus-consistency.md frontend/src/pages/Cameras.test.tsx frontend/src/pages/Settings.test.tsx frontend/src/pages/Live.test.tsx frontend/src/pages/History.test.tsx frontend/src/pages/Sites.test.tsx frontend/src/pages/FleetOpsEvidence.test.tsx frontend/src/pages/FleetOpsSupport.test.tsx frontend/src/pages/FleetOpsOnboarding.test.tsx frontend/src/hooks/use-history.ts frontend/src/hooks/use-sites.ts frontend/src/components/sites/SiteDialog.tsx frontend/src/components/fleetops/FleetOpsScopeSelector.tsx frontend/src/components/fleetops/types.ts frontend/src/pages/Cameras.tsx frontend/src/pages/Settings.tsx frontend/src/pages/Live.tsx frontend/src/pages/History.tsx frontend/src/pages/Sites.tsx frontend/src/pages/FleetOpsEvidence.tsx frontend/src/pages/FleetOpsSupport.tsx frontend/src/pages/FleetOpsOnboarding.tsx
git commit -m "feat: align operator focus selectors"
git push origin codex/sceneops-pack-registry
```
