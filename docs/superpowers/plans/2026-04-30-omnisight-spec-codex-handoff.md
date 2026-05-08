# Codex Handoff — OmniSight UI Spec Implementation

**For:** Codex CLI agent (`codex exec`) running on the user's machine.
**Mission:** Implement the OmniSight UI/UX spec across four phased plans.
**Created:** 2026-04-30.
**Repo:** `/Users/yann.moren/vision` (do not change working directory unless instructed).
**Branch you operate on:** create or use `codex/omnisight-ui-spec-implementation` from current `main`.

---

## 0. Read This First

You will execute four implementation plans, **in order**, each living at:

| Phase | Plan file | Subject |
|---|---|---|
| 1 | `docs/superpowers/plans/2026-04-30-omnisight-spec-phase-1-foundations.md` | Design tokens, brand fonts, primitive refactors |
| 2 | `docs/superpowers/plans/2026-04-30-omnisight-spec-phase-2-spatial-cockpit.md` | CSS-3D `OmniSightLens`, `WorkspaceHero`, Live tile upgrades, Sites cleanup |
| 3 | `docs/superpowers/plans/2026-04-30-omnisight-spec-phase-3-motion.md` | Framer Motion choreography, nav focus shaft, toast |
| 4 | `docs/superpowers/plans/2026-04-30-omnisight-spec-phase-4-webgl.md` | **Gated.** Optional WebGL lens behind a feature flag |

The original design brief is at `docs/brand/omnisight-ui-spec-sheet.md`. Read that for context only — the four plans contain the executable steps.

You **must not** start Phase N until Phase N-1 is fully merged green (per the exit gate below).

---

## 1. Operating Rules

These rules override the plans where they conflict.

### 1.1 Working tree

- Branch should be `codex/omnisight-ui-spec-implementation` at session start. Confirm with `git rev-parse --abbrev-ref HEAD`.
- Stage only files explicitly named in the current task. Never `git add -A`.
- Never amend commits. Always create new ones — one per task — with the message provided in the task.
- Never `git push --force` and never run `git reset --hard` without explicit human authorization.
- Never `--no-verify` a commit. If a pre-commit hook fails, **fix the underlying issue and create a new commit**.
- Do not modify files outside `frontend/` unless the plan tells you to (e.g., `docs/superpowers/plans/...` for changelog, but the plans only modify `frontend/CHANGELOG.md`).

### 1.2 Out-of-scope changes

Several files are dirty in the user's working tree but unrelated to this work. Per `CLAUDE.md`:

- `.superpowers/brainstorm/...` — leave alone.
- Anything else that appears modified at session start that is not named in the active plan task — leave alone.

If you find unfamiliar uncommitted changes when you start a phase, **stop and report**. Do not stash, revert, or delete.

### 1.3 TDD discipline

Every task in the plans follows the same shape:

1. Write or modify the failing test.
2. Run it; confirm it fails for the **right reason** (missing module, missing prop, wrong class). If it fails for the wrong reason, fix the test before proceeding.
3. Implement the minimum code to pass.
4. Re-run; confirm it passes.
5. Run the broader checks specified by the task (lint / full test suite).
6. Commit with the exact message in the task.

If a step asks you to "wrap an existing element" or "replace a JSX block" and you cannot find the exact lines referenced, **stop and ask**. Do not improvise.

### 1.4 Commit cadence

One commit per task. Commit messages follow Conventional Commits (`feat:`, `fix:`, `chore:`, `docs:`, `style:`). The plans give you the exact message — use it verbatim.

The expected commit graph at the end of all four phases is roughly:
- Phase 1: 8 commits.
- Phase 2: 10 commits.
- Phase 3: 9 commits.
- Phase 4: 9 commits (only if executed).

### 1.5 Failure protocol

If, while executing a task:

- A test refuses to pass after the implementation step → **stop**. Do not delete or weaken the test. Report the failure and the last passing checkpoint.
- A lint rule fires → fix the root cause. Do **not** run `eslint --fix` blanket-style. Do not add `// eslint-disable-next-line` unless the plan explicitly authorizes it.
- The build (`pnpm --dir frontend build`) fails after a CSS or token edit → revert that single file edit and report the parser error.
- A page test asserts something the plan changed (e.g., legacy class names) → either (a) update the test to match the new tokens or (b) add a backwards-compatibility alias to `frontend/src/index.css`, **whichever the plan instructs in that task's "Step 7" / "Step 8" tail**. If the plan does not tell you which to choose, prefer adding the alias.

When you stop, write a short report (5–10 lines) describing:
1. Which task you were on.
2. The exact command output of the failure.
3. Your hypothesis for the root cause.
4. What you tried (if anything) before stopping.

Then wait for human input.

---

## 2. Pre-flight (Run Once, Before Phase 1)

```bash
cd /Users/yann.moren/vision
git rev-parse --abbrev-ref HEAD
# Expected: codex/omnisight-ui-spec-implementation

git status --short
# Expected: untracked .superpowers/brainstorm/* and similar; nothing else modified

ls docs/superpowers/plans/2026-04-30-omnisight-spec-phase-*.md
# Expected: 4 phase plans + this handoff

pnpm --dir frontend install
pnpm --dir frontend lint
pnpm --dir frontend test
pnpm --dir frontend build
# All four commands must exit 0
```

If any pre-flight command fails, stop and report. Do not start Phase 1 on a red baseline.

---

## 3. Phase Execution Loop

For **each** of phases 1, 2, 3, (and 4 only if approved — see §6):

### 3.1 Entry gate

Before starting a phase, confirm:

- The previous phase's commits are present in `git log`.
- `pnpm --dir frontend lint && pnpm --dir frontend test && pnpm --dir frontend build` all pass.
- The working tree has no uncommitted modifications inside `frontend/` (your previous phase committed cleanly).

If any of those is false, stop.

### 3.2 Execute the plan

Open the plan file for the phase. Execute each task in numerical order. For each task:

1. Read the entire task before doing anything.
2. Run the steps in the order written.
3. Use the **exact** code, paths, and commit messages provided.
4. After the task's final commit step, run `git log --oneline -n 3` to confirm the commit landed.

Do not parallelize tasks. Do not skip ahead. Do not collapse multiple tasks into one commit.

### 3.3 Exit gate

After the last task in the phase (which is always a "verify and document phase completion" task that includes a changelog commit), confirm:

```bash
pnpm --dir frontend lint
pnpm --dir frontend test
pnpm --dir frontend build
```

All three must exit 0. Then run a manual smoke pass per the plan's "Done criteria" section. If smoke fails, **stop and report** — do not proceed to the next phase.

When the exit gate passes, the phase is complete. **Pause and notify the user before starting the next phase.** The user may want to review or push the branch before more work lands.

---

## 4. Phase 1 — Foundations

**Plan:** `docs/superpowers/plans/2026-04-30-omnisight-spec-phase-1-foundations.md`

**What it does:** Adds the `--vz-*` design token namespace, brand fonts (Space Grotesk + Inter), refactors `Button` to support `primary | secondary | ghost`, migrates `WorkspaceBand`, `WorkspaceSurface`, `MediaSurface`, `InstrumentRail`, `StatusToneBadge` to the new tokens (with legacy aliases), and lightens the shell gradient.

**Why first:** Every later phase consumes these tokens.

**Risk:** Low. No new dependencies. No new components. No motion.

**Special notes:**
- Task 7's "Step 7" warns: if existing page tests assert legacy `--vezor-*` token classes, **add aliases in `index.css`** rather than rewriting those page tests. The aliases keep tests green while consumers migrate gradually.
- Do not delete the `--argus-*` or `--vezor-*` tokens from `index.css`. They are kept as aliases until a future migration phase.

**Estimated commits:** 8.

---

## 5. Phase 2 — Spatial Cockpit

**Plan:** `docs/superpowers/plans/2026-04-30-omnisight-spec-phase-2-spatial-cockpit.md`

**What it does:** Replaces the 20 MB sign-in MP4 with a CSS-perspective `OmniSightLens` (with pointer-driven tilt). Adds `WorkspaceHero` and `KpiTile` primitives. Upgrades the Live scene tile with CSS-only corner brackets and Z-pop hover. Drops the duplicate Sites table and ships a real empty state.

**Why second:** Establishes the "spatial cockpit" feel before any choreographed motion is layered on.

**Risk:** Medium. Touches sign-in (auth-critical surface) and Live (operator-critical surface). Do not change auth flow, OIDC handlers, or telemetry rendering — only their surrounding chrome.

**Special notes:**
- **Do not delete `frontend/public/brand/logo-no-bg.mp4`.** Phase 4 may opt back in to it. The MP4 simply stops being rendered by default.
- The `useLensTilt` test relies on jsdom dispatching pointer events synchronously. If the assertion in Task 2 Step 4 fails on `getPropertyValue` returning empty, follow the test's commented hint: wrap the dispatch in `await new Promise((r) => setTimeout(r, 0));` and mark the test `async`. Do not change the hook to bypass `requestAnimationFrame`.
- The Live tile change in Task 8 adds two `data-` attributes and a self-closing `<span data-bracket />`. The CSS pseudo-element selectors depend on those attributes literally — do not rename them.

**Estimated commits:** 10.

---

## 6. Phase 3 — Motion Choreography

**Plan:** `docs/superpowers/plans/2026-04-30-omnisight-spec-phase-3-motion.md`

**What it does:** Adds Framer Motion. Ships the sliding cerulean nav focus shaft (`layoutId="nav-focus"`), evidence selection cross-fade, Patterns bucket-selection animated shaft, and a token-driven `Toast` primitive wired to evidence review success/failure.

**Why third:** Every motion respects `prefers-reduced-motion`, which is verified at the end of the phase. Layered on top of the Phase-2 cockpit, not before.

**Risk:** Medium. Adds a new runtime dependency (`framer-motion@^11`). Wraps several existing components in motion containers — do not change their props or signatures.

**Special notes:**
- The `Toast.test.tsx` uses `vi.useFakeTimers()`. If the `userEvent.setup` API rejects the `advanceTimers` option in the installed `@testing-library/user-event` version, fall back to:
  ```ts
  const user = userEvent.setup();
  ```
  and replace the `act(() => vi.advanceTimersByTime(6000))` block with the same call followed by `await Promise.resolve();` to flush microtasks.
- The Patterns bucket shaft (Task 5) requires a `bucketLeftPercent` helper. If `HistoryTrendPanel.tsx` already exposes a similar helper for the X axis, **reuse it**. Do not duplicate.
- Mount `<ToastProvider>` inside the existing top-level providers in `main.tsx` (typically below `QueryClientProvider`). Do not re-order existing providers.

**Estimated commits:** 9.

---

## 7. Phase 4 — Optional WebGL Lens (Gated)

**Plan:** `docs/superpowers/plans/2026-04-30-omnisight-spec-phase-4-webgl.md`

**🛑 STOP CONDITIONS — DO NOT PROCEED PAST THIS LINE WITHOUT ALL THREE:**

1. The user (Yann) has explicitly told you to start Phase 4. Phases 1–3 do not authorize Phase 4.
2. Leadership approval to add `@react-three/fiber` + `three` (~85 KB gzip) is recorded in the rollout PR description.
3. The plan's "Approval gate" section at the top of the Phase 4 plan has all three checkboxes signed off.

If any of these is missing, **end your run after Phase 3** and report:
> "Phase 3 complete. Phase 4 paused — awaiting Phase 4 approval per handoff §7."

**What Phase 4 does (only if executed):** Adds a feature-flagged `OmniSightLensSwitch` that lazy-loads `OmniSightLensGL` (a `@react-three/fiber` renderer) when `VITE_FEATURE_WEBGL_LENS=true`, the runtime supports WebGL, and the user does not prefer reduced motion or reduced data. Otherwise falls back to the Phase-2 CSS lens.

**Hard limit:** If the bundle audit at Phase 4 Task 8 measures a delta **greater than 120 KB gzipped**, stop and report. Do not merge.

**Estimated commits:** 9 (or 8 if no GLB asset is provided).

---

## 8. Inter-Phase Pause Points

After Phase 1 exit gate passes:
> Stop. Notify the user. Do not start Phase 2 until they reply.

After Phase 2 exit gate passes:
> Stop. Notify the user. Do not start Phase 3 until they reply.

After Phase 3 exit gate passes:
> Stop. Notify the user. **Do not start Phase 4** unless the user explicitly authorizes it (see §7).

This cadence gives the user time to review, push, and gather feedback between batches of UI changes.

---

## 9. Verification Commands (Reference)

| Purpose | Command |
|---|---|
| Branch check | `git rev-parse --abbrev-ref HEAD` |
| Status check | `git status --short` |
| Install deps | `pnpm --dir frontend install` |
| Lint | `pnpm --dir frontend lint` |
| Tests (one-shot) | `pnpm --dir frontend test` |
| Single test file | `pnpm --dir frontend exec vitest run src/path/to/file.test.tsx` |
| Build | `pnpm --dir frontend build` |
| Dev server | `pnpm --dir frontend dev` |
| Type-check | `pnpm --dir frontend exec tsc -b --noEmit` |
| Recent commits | `git log --oneline -n 10` |
| Bundle inspection | `ls -lah frontend/dist/assets` |

Always run from `/Users/yann.moren/vision` (the repo root). Never `cd frontend/` — the `--dir frontend` flag covers it.

---

## 10. Communication

When you finish a task: do not summarize at length. State only "Task N complete" and run the next task.

When you finish a phase: write a short report:
- Phase X complete.
- N commits added.
- Lint / test / build all green.
- Smoke results (one line per route touched).
- Any deviations from the plan, with reason.

When you stop on a failure: write the failure report described in §1.5.

Avoid speculation. Avoid asking permission for steps the plan already authorizes. Avoid asking permission for steps inside the active task. Ask permission only when:
- The plan instructions diverge from the actual repo state.
- A pre-flight or exit gate fails.
- You are about to do anything outside the active task's "Files" list.
- You have reached an inter-phase pause point.

---

## 11. Done

You are done when:

1. Phase 1, 2, and 3 are all merged green to `codex/omnisight-ui-spec-implementation`, OR
2. Phase 4 is also done **and** explicitly authorized.

In both cases, the final report should include:
- All commit hashes.
- The state of `frontend/CHANGELOG.md`.
- Any open follow-ups (e.g., "the spec sheet's open question 3 — `wall mode` persistence — is unresolved and not addressed by these phases").

After the final report, **stop**. Do not open a PR unless explicitly asked. Do not push to `origin` unless explicitly asked.

---

## Appendix A — Spec Reference Map

| Spec sheet section | Implemented in |
|---|---|
| §2.1 Palette tokens | Phase 1 Task 1 |
| §2.3 Typography | Phase 1 Task 2 |
| §3.1 Elevation ladder | Phase 1 Task 1 |
| §3.2 Border-radius scale | Phase 1 Task 1 |
| §3.3 3D depth tokens | Phase 1 Task 1 (defined), Phase 2 (consumed) |
| §3.4 WebGL upgrade path | Phase 4 |
| §4 Motion system | Phase 1 (tokens), Phase 3 (presets + use) |
| §5.1–§5.6 Composition primitives | Phase 1 (refactor), Phase 2 (`WorkspaceHero`) |
| §6.1 Buttons | Phase 1 Task 4 |
| §6.6 Live scene tile | Phase 2 Task 8 |
| §6.8 Sign-in lens | Phase 2 Tasks 1–5 |
| §6.9 Nav rail | Phase 3 Task 3 |
| §6.10 Workspace transition | Phase 3 Task 8 |
| §6.11 Toast | Phase 3 Tasks 6–7 |
| §7.1 Sign-in | Phase 2 Task 5 |
| §7.2 Dashboard | Phase 2 Task 7 |
| §7.3 Live | Phase 2 Task 8 |
| §7.4 Patterns | Phase 3 Task 5 |
| §7.5 Evidence | Phase 3 Tasks 4 + 7 |
| §7.7 Sites | Phase 2 Task 9 |
| §7.9 App shell | Phase 1 Task 3 |

Items in the spec **not** addressed by these phases (intentional follow-ups):
- §6.7 Evidence card per-row colored stripe (left for a future polish pass).
- §6.12 Command palette (`⌘K`) — explicitly listed as a future deliverable in the spec's open questions.
- §7.6 Scenes overflow menu redesign (mentioned in spec; light-touch in Phase 1, deeper rework deferred).
- §7.8 Operations tabs and command/config split (deferred — current Settings page is dense but functional).
- §8.3 Empty-state illustrations (only Sites empty state is shipped; Live and Evidence reuse text-only states).
