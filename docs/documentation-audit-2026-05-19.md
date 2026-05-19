# Documentation Audit: Markdown Freshness And Archive Candidates

Date: 2026-05-19
Branch: `codex/omnisight-installer`

Follow-up applied on 2026-05-19:

- created `docs/auth.md`, `docs/benchmarks/central-l4.md`, and
  `infra/central/README.md`
- updated ADR and brand-plan links to existing documents
- deleted `docs/error.md`
- moved the legacy MacBook and iMac lab guides into `archive/`
- marked profile-addressed live renditions and WebGL work as deferred
- added top-level `Status:` metadata to tracked Superpowers plans/specs
- created a fresh current handoff

## Scope

Audited tracked Markdown files with:

```bash
git ls-files '*.md'
```

Inventory:

| Area | Count |
|---|---:|
| repo root | 4 |
| `archive/` | 4 |
| `backend/`, `frontend/`, `infra/`, `installer/` | 4 |
| `docs/ADR/` | 3 |
| `docs/brand/` | 4 |
| top-level `docs/*.md` guides | 10 |
| `docs/superpowers/plans/` | 39 |
| `docs/superpowers/specs/` | 32 |
| `docs/superpowers/status/` | 9 |
| `docs/superpowers/summaries/` | 2 |
| **Total tracked `.md` files** | **111** |

Untracked Markdown files observed but not touched:

- `camera-capture.md`
- `codex-review-findings.md`
- `docs/strategy/vezor-market-positioning-report.md`
- `docs/superpowers/plans/2026-05-16-browser-delivery-overlays-and-profile-grid.md`

## Method

- Checked every tracked `.md` path.
- Scanned for explicit stale markers: `legacy`, `superseded`, `deprecated`,
  `obsolete`, `stale`, `fallback`, `next chat`, `not implemented`, `deferred`,
  and branch-specific handoff language.
- Checked Markdown references to local `.md` files for missing targets.
- Manually reviewed the primary operator/install docs and the documents with
  explicit stale markers.

## High-Priority Updates

### 1. Fix Broken Internal Documentation Links

Original audit findings are listed below. The 2026-05-19 follow-up resolved the
ADR and brand-plan targets; DeepStream references remain deferred until Task 24
is explicitly approved.

| Source | Missing target | Recommendation |
|---|---|---|
| `docs/ADR/ADR-0001-identity-provider.md` | `docs/auth.md` | Create `docs/auth.md` or update the ADR action item to the current auth/installer docs. |
| `docs/ADR/ADR-0002-central-gpu.md` | `docs/benchmarks/central-l4.md` | Create the benchmark placeholder or remove the action item until central GPU work resumes. |
| `docs/ADR/ADR-0002-central-gpu.md` | `infra/central/README.md` | Create the central runtime placeholder or point to the deployment matrix. |
| `docs/ADR/README.md` | `/Users/yann.moren/vision/argus_v4_spec.md` | Update to `product-spec-v4.md`; the old `argus_v4_spec.md` path is gone. |
| `docs/superpowers/plans/2026-04-20-vezor-brand-rename-implementation-plan.md` | `docs/brand/argus-logo-brand-spec.md` | Replace with `docs/brand/logo-brand-spec.md` or archive the completed rename plan. |
| `docs/superpowers/plans/2026-04-20-vezor-brand-rename-implementation-plan.md` | `docs/brand/usage-guide.md` | Replace with `docs/brand/logo-usage-guide.md` or archive the completed rename plan. |
| `docs/superpowers/plans/2026-05-10-jetson-optimized-runtime-artifacts-and-open-vocab-implementation-plan.md` | `docs/superpowers/specs/YYYY-MM-DD-deepstream-jetson-runtime-design.md` | Leave as a placeholder only if the plan is explicitly historical; otherwise replace with a real deferred DeepStream doc when Task 24 starts. |
| `docs/superpowers/plans/2026-05-10-jetson-optimized-runtime-artifacts-and-open-vocab-implementation-plan.md` | `docs/superpowers/plans/YYYY-MM-DD-deepstream-jetson-runtime-implementation-plan.md` | Same as above. |
| `docs/superpowers/plans/2026-05-11-accountable-scene-intelligence-and-evidence-recording-implementation-plan.md` | `infra/deepstream/README.md` | Do not create until Task 24 is approved; mark the reference as future/deferred. |

### 2. Deleted `docs/error.md`

`docs/error.md` is a pasted terminal failure about camera JSON parsing, not a
guide, runbook, ADR, or durable troubleshooting note.

Follow-up: deleted after confirming it was only a raw transcript.

### 3. Demote Legacy MacBook/iMac Guides

These guides still contain useful lab context, but they should not compete with
the canonical installer path:

Follow-up: both guides were moved under `archive/`, and primary docs now point
operators to the product installer and cross-network reinstall guides first.

| File | Current state | Recommendation |
|---|---|---|
| `archive/macbook-pro-jetson-portable-demo-install-guide.md` | Already marked `legacy manual/dev fallback`; still large and easy to confuse with the installer-managed path. | Move to `archive/` or retitle as `legacy-portable-demo-dev-fallback.md` after confirming `docs/product-installer-and-first-run-guide.md` and `docs/macbook-jetson-cross-network-reinstall-guide.md` cover the current operator path. |
| `archive/imac-master-orin-lab-test-guide.md` | Historical 2019 iMac lab path with old/manual validation language. | Move to `archive/` or add a stronger historical banner and remove it from primary reading lists. |

### 4. Update The Latest Installer Handoff

`docs/superpowers/status/2026-05-15-next-chat-omnisight-installer-portable-demo-handoff.md`
is the newest tracked handoff, but it predates the recent live profile/tracker
fixes and the new cross-network reinstall guide.

Recommendation: either update it with the latest pushed commits and current
restart/reinstall docs, or mark it superseded by a new dated handoff.

Follow-up: created
`docs/superpowers/status/2026-05-19-next-chat-omnisight-installer-current-branch-handoff.md`.

### 5. Mark Profile-Addressed Live Renditions As Deferred

These docs describe the profile-addressed stream path work:

- `docs/superpowers/specs/2026-05-17-profile-addressed-live-renditions-design.md`
- `docs/superpowers/plans/2026-05-17-profile-addressed-live-renditions-implementation-plan.md`

The branch contains fixes around active profile paths and no-op refresh state,
but the operator decided to keep this class of functionality for a later stage
after live validation surfaced tracker/telemetry instability.

Recommendation: update both docs with a `Status: Deferred after May 2026 field
validation` note and link to the commits that stabilized the interim behavior.
Do not treat the implementation plan as the next active plan without a new
approval pass.

Follow-up: both documents now carry `Status: Deferred after May 2026 field
validation.`

## Medium-Priority Updates

### Product Installer Guide Is Current But Too Large

`docs/product-installer-and-first-run-guide.md` is still the canonical
installer-managed guide. It has the right command surface, but it is now doing
too many jobs:

- macOS master install
- Linux master install
- first-run
- model registration
- central supervisor pairing
- Jetson bootstrap/install
- TensorRT artifact build/registration
- troubleshooting
- upgrade and reboot validation

Recommendation: keep it canonical, but add a short "Use These Companion Docs"
section near the top:

- cross-network reinstall guide for different networks
- model/runtime artifact guide for TensorRT/open-vocab work
- runbook for operations and diagnostics

### Runbook And Deployment Docs Need A Merge-Time Pass

These are mostly current and should not be archived:

- `docs/runbook.md`
- `docs/operator-deployment-playbook.md`
- `docs/deployment-modes-and-matrix.md`
- `docs/model-loading-and-configuration-guide.md`
- `docs/scene-vision-profile-configuration-guide.md`

Recommendation: after `codex/omnisight-installer` merges, remove or rewrite
branch-specific language such as `codex/omnisight-installer`, installer branch
validation, and temporary pilot wording where it has become product behavior.

### Brand/UI Spec Sheet Needs Refresh Or Historical Label

`docs/brand/omnisight-ui-spec-sheet.md` is dated 2026-04-30 and says its review
basis is the current UI on `main`. The Live tile, Pattern graph, Operations,
and installer UI have moved since then.

Recommendation: either refresh it against the current product surface or mark
it as a historical UI audit. Keep the token and design language if still useful,
but do not let it read as a current source of truth until it is revalidated.

### Frontend Changelog Is Stale

`frontend/CHANGELOG.md` still carries several `Unreleased - Phase ...` sections
from the UI work. That is useful history, but it is not a normal release
changelog.

Recommendation: either convert it to dated release entries or move the phase
notes into `docs/superpowers/` and start a compact frontend changelog.

## Archive Candidates

These are safe archive candidates once the team confirms no current workflow
still depends on them:

| Candidate | Why |
|---|---|
| `docs/error.md` | Deleted in the 2026-05-19 follow-up cleanup. |
| `archive/imac-master-orin-lab-test-guide.md` | Historical iMac lab path; superseded by installer-managed MacBook/Linux master + Jetson docs. |
| `archive/macbook-pro-jetson-portable-demo-install-guide.md` | Already marked legacy manual/dev fallback; canonical path lives elsewhere. |
| `docs/superpowers/status/2026-04-26-precise-counting-and-setup-handoff.md` | Old handoff. |
| `docs/superpowers/status/2026-04-28-imac-jetson-dev-validation-handoff.md` | Old handoff. |
| `docs/superpowers/status/2026-04-28-omnisight-ui-redesign-followup-handoff.md` | Old handoff. |
| `docs/superpowers/status/2026-04-30-main-merge-phase-b-handoff.md` | Old handoff. |
| `docs/superpowers/status/2026-05-01-next-chat-two-stream-handoff.md` | Title already says `Superseded Handoff`. |
| `docs/superpowers/status/2026-05-11-next-chat-accountable-scene-intelligence-handoff.md` | Superseded by later Task 14/17/productization handoffs. |
| `docs/superpowers/status/2026-05-12-next-chat-accountable-scene-task14-handoff.md` | Superseded by later productization handoffs. |
| `docs/superpowers/status/2026-05-13-next-chat-installable-supervisor-productization-handoff.md` | Superseded by installer portable demo handoff. |
| `docs/superpowers/summaries/2026-04-21-live-stream-debugging-handoff.md` | Historical debugging handoff. |
| `docs/superpowers/summaries/2026-04-21-project-delivery-status.md` | Historical status snapshot. |
| `docs/superpowers/plans/2026-04-30-omnisight-spec-phase-4-webgl.md` | WebGL remains off/deferred; do not leave as active work. |
| `docs/superpowers/plans/2026-05-17-profile-addressed-live-renditions-implementation-plan.md` | Deferred after validation; archive or mark deferred. |

## Superpowers Plan/Spec Cleanup

The `docs/superpowers/plans/` and `docs/superpowers/specs/` directories contain
valuable design history, but many files are completed implementation plans.
They should not all remain in the same active lane.

Recommended structure:

```text
docs/superpowers/
  active/
  archive/
    2026-04/
    2026-05/
  plans/
  specs/
  status/
```

Minimum cleanup without moving files:

1. Add `Status:` metadata to each plan/spec:
   - `Implemented`
   - `Superseded`
   - `Deferred`
   - `Active`
2. Keep only current approved work in `plans/` and `specs/`.
3. Move old handoffs out of `status/` after a newer handoff supersedes them.

Likely active or recently relevant plan/spec pairs:

- `2026-05-14-product-installer-and-no-console-first-run-*`
- `2026-05-16-live-tile-and-pattern-graph-ux-*`
- `2026-05-17-profile-addressed-live-renditions-*` only if explicitly
  re-approved; otherwise mark deferred.
- `2026-05-11-accountable-scene-intelligence-and-evidence-recording-*` as a
  large historical roadmap with remaining deferred items.

Everything older than 2026-05-09 should be treated as historical unless a
current source explicitly points to it as active.

## Documents To Keep As Current Sources

Do not archive these without replacing their role:

- `README.md`
- `product-spec-v4.md`
- `CLAUDE.md`
- `backend/README.md`
- `installer/README.md`
- `infra/secrets/README.md`
- `docs/product-installer-and-first-run-guide.md`
- `docs/macbook-jetson-cross-network-reinstall-guide.md`
- `docs/runbook.md`
- `docs/operator-deployment-playbook.md`
- `docs/deployment-modes-and-matrix.md`
- `docs/model-loading-and-configuration-guide.md`
- `docs/scene-vision-profile-configuration-guide.md`
- `docs/ADR/ADR-0001-identity-provider.md`
- `docs/ADR/ADR-0002-central-gpu.md`

Some of these still need update passes for branch-specific wording, but they
are current enough to remain discoverable.

## Recommended Next Actions

1. Keep the repaired local doc links healthy when docs move again.
2. Keep `docs/error.md` deleted unless the raw transcript is explicitly needed again.
3. Treat profile-addressed live rendition work as deferred until re-approved.
4. Use the 2026-05-19 current handoff for the next chat, then archive older
   `docs/superpowers/status/*` handoffs when the team wants a deeper cleanup.
5. Keep legacy lab guides under `archive/` unless a current operator flow needs
   a new, installer-managed replacement.
6. Preserve top-level `Status:` metadata on new Superpowers plan/spec docs.
7. Re-run this audit after the branch merges to main and remove branch-specific
   validation wording from current operator docs.
