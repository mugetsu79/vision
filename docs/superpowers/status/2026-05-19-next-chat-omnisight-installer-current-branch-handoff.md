# Next Chat Handoff: OmniSight Installer Current Branch

Date: 2026-05-19
Last updated: 2026-05-29
Status: Superseded by
`docs/superpowers/status/2026-05-29-next-chat-omnisight-installer-main-merge-readiness-handoff.md`.

Purpose: paste this document into a fresh chat to continue work on the current
repository branch. Keep `main` untouched unless Yann explicitly changes that
instruction.

## Branch And Repository State

Continue from:

```text
codex/omnisight-installer
```

Do not merge this branch to `main` yet. Do not start Task 24 / DeepStream.
Keep WebGL off.

Start the next chat with:

```bash
cd "$HOME/vision"
git fetch origin
git switch codex/omnisight-installer
git pull --ff-only origin codex/omnisight-installer
git status -sb
git log --oneline -12
```

Known local hygiene:

- unrelated untracked scratch files may exist locally
- do not use `git add -A`
- stage only files needed for the current task
- keep unrelated untracked files untouched

Recent pushed history before this handoff cleanup:

```text
9e79559c docs: add markdown freshness audit
1cbab946 docs(installer): add cross-network reinstall guide
b9d78e57 fix(live): keep tracker state on profile refresh
dfa4af05 fix(live): poll worker config for stream changes
d04dd127 fix(live): wait for active stream profile
02e10a6e fix(live): recover from profile stream standby
14ba06cd fix(streams): use mediamtx-safe profile paths
fe7d62c4 feat(live): enforce profile-addressed renditions
1d103128 docs(live): plan profile-addressed renditions
8a56052b fix(frontend): satisfy build type check for history trend test
21e77b02 feat(live): improve scene tile focus and signal graphs
219d89b3 docs(handoff): note live runtime review
```

## Current Documentation State

Use these as the current operator-facing docs:

- `docs/product-installer-and-first-run-guide.md`
- `docs/macbook-jetson-cross-network-reinstall-guide.md`
- `docs/runbook.md`
- `docs/operator-deployment-playbook.md`
- `docs/deployment-modes-and-matrix.md`
- `docs/model-loading-and-configuration-guide.md`
- `docs/scene-vision-profile-configuration-guide.md`

The legacy lab guides are archived:

- `archive/macbook-pro-jetson-portable-demo-install-guide.md`
- `archive/imac-master-orin-lab-test-guide.md`

The raw camera JSON error transcript was removed:

- `docs/error.md`

The Markdown audit is:

- `docs/documentation-audit-2026-05-19.md`

Follow-up cleanup from the audit:

- broken ADR links now point to real docs
- `docs/auth.md` exists as the ADR-0001 primer
- `docs/benchmarks/central-l4.md` exists as the ADR-0002 benchmark placeholder
- `infra/central/README.md` exists as the ADR-0002 central runtime placeholder
- tracked Superpowers plans/specs now carry top-level `Status:` metadata

## Current Live/Profile Validation State

The branch includes profile-addressed live stream work and follow-up fixes, but
field validation showed that this area is still not ready to be treated as a
finished product behavior.

Current understanding:

- profile changes can now change the active stream resolution/FPS path
- the tile still needs deeper tracker and telemetry stability checks
- the profile-addressed rendition design/plan are marked deferred after May
  2026 field validation
- the smaller, practical goal is to keep the branch stable for the current demo
  while avoiding further scope growth

Relevant deferred docs:

- `docs/superpowers/specs/2026-05-17-profile-addressed-live-renditions-design.md`
- `docs/superpowers/plans/2026-05-17-profile-addressed-live-renditions-implementation-plan.md`

## Current Open Work

Recommended next technical focus:

1. Reproduce the tracker instability on the current branch with logs and visual
   evidence.
2. Confirm whether profile switches are causing tracker resets, telemetry
   queue pressure, or frontend heartbeat gaps.
3. Fix only the proven root cause.
4. Run focused backend/frontend tests and visually validate Live.

Do not use the profile-addressed rendition plan as active work without a fresh
approval pass.

## Verification Expectations

Before claiming future doc cleanup is complete, run:

```bash
git diff --check
```

Before claiming installer or Live changes are fixed, run the focused tests for
the touched area and include the exact command output summary in the final
message.

For installed MacBook/Jetson reruns, use:

```text
docs/macbook-jetson-cross-network-reinstall-guide.md
```

For full installer context, use:

```text
docs/product-installer-and-first-run-guide.md
```
