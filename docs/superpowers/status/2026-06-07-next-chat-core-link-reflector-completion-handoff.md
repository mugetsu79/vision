# Core Link Reflector Completion Next-Chat Handoff

Date: 2026-06-07
Current branch: `codex/sceneops-pack-registry`
Implementation head before this docs handoff: `3b66ebfa`

## Read First

Start the next chat here, then read:

1. `docs/core-link-performance-guide.md`
2. `docs/superpowers/specs/2026-06-07-core-link-performance-workspace-design.md`
3. `docs/superpowers/specs/2026-06-07-core-link-edge-agent-design.md`
4. `docs/superpowers/specs/2026-06-07-core-link-reflector-loss-design.md`
5. `docs/superpowers/plans/2026-06-07-core-link-reflector-loss.md`
6. `docs/superpowers/specs/2026-06-07-core-link-master-target-site-design.md`
7. `docs/superpowers/specs/2026-06-07-core-link-master-reflector-deployment-design.md`
8. `docs/superpowers/plans/2026-06-07-core-link-master-reflector-deployment.md`

The 2026-06-05/06 pack-boundary and FleetOps docs remain binding for all
`CC-*` constraints. Core Link must stay domain-neutral. FleetOps may deep-link
to Core Link by site id, but core routes, contracts, services, tests, and copy
must not become maritime-specific.

## What Is Implemented

The branch now has the full first-pass Core Link/FleetOps sequence:

```text
3b66ebfa feat: surface master link reflector controls
cda44f97 feat: add edge agent udp sequence probes
3cf28280 feat: wire master link reflector runtime
cd9ad029 feat: expose master link reflector controls
0b26acd7 feat: persist master link reflector profile
29f1750d feat: add link udp reflector
d1524407 feat: add link udp sequence codec
86dae480 docs: plan master link reflector deployment
a2326ffe feat: add master link target workspace
acd1056e feat: expose master link target probes
def08345 feat: track link probe target sites
192929ff feat: add control plane site support
5530b344 feat: add core link site roles
```

Current product behavior:

- `/links` is the domain-neutral Core Link Performance workspace.
- Edge sites own link paths, budgets, policies, monitoring targets, probe
  samples, queues, and manual throughput controls.
- The Vezor master/control-plane site is target-only. Operators cannot add
  local link paths, budgets, probes, queues, or throughput checks to it.
- Link paths are logical operator inventory. They can represent an ISP circuit,
  provider-managed SD-WAN handoff, LTE, satellite, Wi-Fi, ethernet, or another
  operator-defined path without pretending Vezor sees every internal hop.
- Backend synthetic checks measure from the backend network. Edge-agent checks
  measure from the edge vantage point.
- Throughput measurement is manual only and is intentionally not run at the
  monitoring interval.
- The edge agent supports operational `icmp_sequence` and Vezor
  `udp_sequence`.
- Vezor UDP sequence uses authenticated sequenced packets against a cooperating
  reflector and records packet counts, loss, RTT statistics, RTT variation,
  late, duplicate, and out-of-order counters.
- STAMP/TWAMP/provider responder modes are reserved future integrations.
- The master deployment has reflector capability, disabled by default. A
  backend UDP listener starts only when deployment env enables it at process
  startup and provides a shared HMAC secret.
- The UI persists the master reflector profile intent/key metadata and exposes
  enable, disable, and rotate controls. Profile changes now reconcile into the
  running backend listener.

## Verification Evidence

Implementation verification already run on this branch:

```bash
cd /Users/yann.moren/vision/frontend
corepack pnpm test
corepack pnpm lint
corepack pnpm build

cd /Users/yann.moren/vision/backend
.venv/bin/pytest tests/api/test_link_routes.py tests/link/test_link_service.py tests/link/test_edge_agent.py tests/link/test_reflector.py tests/link/test_udp_sequence.py tests/test_app_lifecycle.py -q
.venv/bin/ruff check src/argus/link src/argus/core/config.py src/argus/main.py tests/api/test_link_routes.py tests/link/test_link_service.py tests/link/test_edge_agent.py tests/link/test_reflector.py tests/link/test_udp_sequence.py tests/test_app_lifecycle.py
.venv/bin/mypy src/argus/link src/argus/core/config.py src/argus/main.py
```

Results:

- Frontend tests: 94 files, 466 tests passed. Existing React `act(...)` and
  router warnings were present.
- Frontend lint: passed.
- Frontend build: passed.
- Backend scoped pytest: 78 passed. Existing `/run/secrets` warnings were
  present.
- Backend Ruff: passed.
- Backend mypy: passed.
- Browser smoke: a temporary Vite dev server loaded `/links` and redirected to
  sign-in without auth, as expected. The temporary server was stopped.

This docs handoff pass should be verified with `git diff --check` before
commit. Re-run the product test suites above before claiming new code changes.

## Current Documentation State

The docs now reflect the current product model:

- `README.md` includes Link Performance/FleetOps and edge-agent/reflector
  status.
- `docs/core-link-performance-guide.md` is the operator-facing Core Link guide.
- `docs/operator-deployment-playbook.md`, `docs/runbook.md`,
  `docs/deployment-modes-and-matrix.md`, and
  `docs/product-installer-and-first-run-guide.md` describe the master reflector,
  edge-agent measurement source, manual throughput posture, and current gaps.
- The Core Link workspace, edge-agent, reflector-loss, master target, and
  master reflector specs/plans are marked implemented where appropriate.
- The older FleetOps/Core Link handoff is marked superseded.

## Known Gaps

Recommended next work, in priority order:

1. Edge-agent service packaging, pairing credentials, and reflector secret
   distribution UX.
2. Authenticated browser smoke with realistic dev data for `/links`, including
   master target and edge-to-master reflector flows.
3. Deployment hardening for reflector secrets in installer/Helm/service-manager
   contexts.
4. STAMP/TWAMP/provider responder integrations behind the existing measurement
   model.

## Working Tree Warning

Do not stage unrelated local files. This workspace has unrelated untracked
items such as `.claude/`, `.codex/`, `.playwright-mcp/`, `.superpowers/`
brainstorm folders, `.vite/`, screenshots, brand images, strategy drafts,
`camera-capture.md`, `codex-review-findings.md`, and `taste-skill/`.

Use explicit staging paths only. Do not use `git add -A`.

## Hard Constraints

Preserve:

- `CC-1 Packless Core Compatibility`
- `CC-2 Pack Boundary`
- `CC-3 Traffic Boundary`
- `CC-4 Link Is Core`
- `CC-5 Fleet Is Core`
- `CC-6 Billing Positioning`
- `CC-7 Support Tunnel`
- `CC-8 Evidence Integrity`
- `CC-9 Frontend Reuse`
- `CC-10 Full Product Scope`

Stop and surface a conflict if a task requires moving vertical FleetOps nouns
into Core Link, relaxing evidence hash semantics, changing runtime detector
semantics outside the active plan, adding traffic/public-space runtime, adding
home-lab pack/status/UI, or integrating proprietary carrier/payment/accounting
systems without an explicit new plan.
