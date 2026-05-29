# Next Chat Handoff: OmniSight Installer Main Merge Readiness

Date: 2026-05-29
Last updated: 2026-05-29
Status: Current merge-readiness handoff for `codex/omnisight-installer`.

Purpose: continue from the installer branch after field validation showed the
core MacBook master plus Jetson edge path is ready to merge to `main`, pending
normal verification and review.

## Branch And Repository State

Current branch:

```text
codex/omnisight-installer
```

Latest pushed checkpoint before this handoff:

```text
ac2715c5 Fix edge scene startup and live scene deletion
```

`omnisight-ui-check` is not a separate blocker. It points at
`d5282c60 docs: refresh markdown cleanup and handoff`, which is an ancestor of
`codex/omnisight-installer`. Everything from that branch is already contained
in the installer branch.

Recommended next local checks:

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

## Field Validation Summary

Validated by Yann after the latest branch work:

- MacBook master reinstall works with LAN HTTP Keycloak sign-in.
- Jetson edge reinstall works after network address changes.
- Native video stream is online.
- Worker telemetry posts to the master again after the corrected Jetson API URL.
- Second scene startup is validated after the worker metrics-port collision fix.
- Profile/rendition switching appears to work.
- Live scene deletion exists for cleaning up old scenes such as `Room1`.

Known follow-up:

- Live view tile resizing can produce odd video resolution/rendering behavior
  when increasing or decreasing the video window size. Treat this as UI/live
  layout polish, not as a blocker for the installer branch merge unless visual
  QA shows it breaks normal Live operation.
- Profile-addressed rendition work remains deferred as a product-expansion
  lane. The current branch is acceptable for demo validation, but do not resume
  the deferred plan without a fresh approval pass.
- Do not start Task 24 / DeepStream until Track A/B Jetson soak evidence exists
  or the risk is explicitly accepted.

## Current Documentation State

Operator-facing docs refreshed for main merge readiness:

- `README.md`
- `docs/product-installer-and-first-run-guide.md`
- `docs/macbook-jetson-cross-network-reinstall-guide.md`
- `docs/documentation-audit-2026-05-19.md`

The current installer docs now tell source users to update `main` or a release
tag, instead of hard-coding `codex/omnisight-installer`. Historical plans,
handoffs, and archived lab guides may still mention the branch as provenance.

Current operator docs to keep discoverable:

- `docs/product-installer-and-first-run-guide.md`
- `docs/macbook-jetson-cross-network-reinstall-guide.md`
- `docs/runbook.md`
- `docs/operator-deployment-playbook.md`
- `docs/deployment-modes-and-matrix.md`
- `docs/model-loading-and-configuration-guide.md`
- `docs/scene-vision-profile-configuration-guide.md`

Legacy lab guides remain archived:

- `archive/macbook-pro-jetson-portable-demo-install-guide.md`
- `archive/imac-master-orin-lab-test-guide.md`

## Merge Recommendation

Recommendation: merge `codex/omnisight-installer` to `main` after the focused
test suite and doc checks pass.

Rationale:

- The branch is a straight descendant of `main`; `main..HEAD` contains the
  installer, doc cleanup, LAN auth, live profile fixes, and second-scene fix.
- `omnisight-ui-check` is already included.
- Field validation has covered the core demo risk areas: reinstall, auth,
  Jetson pairing, native stream, profile/rendition switching, second scene, and
  scene cleanup.
- The remaining Live resize/rendering issue is scoped enough to become the next
  UI branch rather than holding the installer merge.

## Verification Expectations

Before claiming merge readiness, run:

```bash
git diff --check
python3 -m uv run --project backend pytest backend/tests/inference/test_engine.py -q
python3 -m uv run --project backend pytest backend/tests/services/test_camera_worker_config.py -q
python3 -m uv run --project backend pytest backend/tests/services/test_identity_bootstrap.py -q
python3 -m uv run --project backend pytest backend/tests/api/test_app.py -q
corepack pnpm --dir frontend exec vitest run src/pages/Live.test.tsx src/pages/Cameras.test.tsx src/lib/config.test.ts src/lib/auth-manager.test.ts
corepack pnpm --dir frontend exec eslint src/pages/Live.tsx src/pages/Live.test.tsx src/hooks/use-cameras.ts src/lib/config.ts src/lib/auth.ts
corepack pnpm --dir frontend exec tsc -b
make verify-installers
```

After merge, rebuild the MacBook master and Jetson edge from `main`, then run
the reboot-only and cross-network validation paths from:

```text
docs/macbook-jetson-cross-network-reinstall-guide.md
```
