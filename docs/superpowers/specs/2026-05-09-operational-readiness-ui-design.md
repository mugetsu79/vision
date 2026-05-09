# Operational Readiness For Sovereign Spatial Intelligence Design

**Date:** 2026-05-09
**Status:** Proposed for Phase 5A, reframed after the market-positioning report
**Scope:** Frontend-only UI/UX improvements that make Vezor's existing multi-site, central/edge/hybrid, privacy-aware scene-intelligence loop visible. WebGL remains off and out of scope.

---

## 1. Goal

Make OmniSight feel like a credible **sovereign spatial intelligence** product, not a generic camera dashboard.

The strategy report says the product does not need to become bigger; it needs to become more legible. Phase 5A should therefore help an operator, buyer, or integrator quickly see:

1. Which sites and scenes exist?
2. Where does inference run: central, edge, or hybrid?
3. Which scenes are ready, degraded, or missing setup?
4. Which scenes have privacy controls configured?
5. Which evidence records need review?
6. Where should the operator go next?

Phase 5A remains intentionally frontend-only. It does not add backend fields, migrations, worker reports, supervisor controls, commercial packaging, or runtime metrics. It composes data that already exists:

- `GET /api/v1/operations/fleet`
- `GET /api/v1/cameras`
- `GET /api/v1/sites`
- `GET /api/v1/incidents`
- `/ws/telemetry`

## 2. Strategic Position

The recommended category phrase is **Sovereign Spatial Intelligence**:

> Vezor turns existing cameras and edge nodes into live operational awareness, evidence, patterns, and fleet control across many sites.

Phase 5A should make that statement visible inside the product by emphasizing:

- existing scenes, not camera replacement
- central, edge, and hybrid processing as buyer-level deployment posture
- privacy posture as a runtime and configuration concern
- evidence awaiting review, not generic alerts
- scene readiness, not only system health
- Operations as proof of edge/central fleet control, without overclaiming supervisor-backed lifecycle

The product should keep using "scene", "signal", "event", "evidence", "patterns", and "operations" as primary language. It should avoid framing itself as a VMS replacement, facial-recognition product, generic computer-vision builder, or magical AI agent.

## 3. Non-Goals

Phase 5A does not include:

- WebGL, `three`, or `@react-three/fiber`
- new backend contracts
- new worker heartbeat payload fields
- `capture_wait_*` metrics in the UI
- telemetry drop counters in the UI
- process start/stop/restart buttons
- supervisor-backed lifecycle claims
- credential rotation
- model pack marketplace UI
- pricing, SKU, or sales packaging UI
- alert acknowledgement/snooze
- evidence comments, assignment, escalation, or case management
- compliance claims such as "GDPR-ready" or "AI Act compliant"
- a new landing page or marketing hero

Those items remain eligible for later phases. Phase 5B should add real worker runtime metrics once the backend contract is ready.

## 4. Existing Data Sources

### Fleet Overview

`useFleetOverview()` already exposes:

- `summary.desired_workers`
- `summary.running_workers`
- `summary.stale_nodes`
- `summary.offline_nodes`
- `summary.native_unavailable_cameras`
- `nodes`
- `camera_workers`
- `delivery_diagnostics`

Use this for worker, node, and delivery truth. Do not infer unsupported runtime details such as capture jitter or last worker error.

### Cameras

`useCameras()` already exposes:

- camera/scene name
- site id
- processing mode
- edge node assignment
- browser delivery profiles
- native stream availability
- source capability
- tracker
- active classes
- zones
- privacy settings

Use this for scene inventory, deployment mode, setup readiness, and privacy posture.

### Sites

`useSites()` already exposes deployment locations and time zones.

Use this to make Vezor feel multi-site. The UI should not imply a single-location toy deployment when the product already models sites.

### Incidents

`useIncidents({ reviewStatus: "pending" })` already exposes pending evidence records.

Use "evidence awaiting review" language. This aligns with the Evidence Desk, audit expectations, and the report's "Evidence and Patterns, Not Footage Piles" pillar.

### Live Telemetry

`useLiveTelemetry(cameraIds)` and `getHeartbeatStatus(frame)` already expose per-scene live heartbeat freshness.

Use this for UI-observed telemetry freshness only. Do not claim worker health metrics beyond the current API.

## 5. Readiness Model

Add a frontend-only readiness model in `frontend/src/lib/operational-health.ts`.

Keep the simple health state for badges:

```ts
type OperationalHealth = "healthy" | "attention" | "danger" | "unknown";
```

But expand the derived model beyond "health":

- `deriveFleetHealth`
- `deriveDeploymentPosture`
- `derivePrivacyPosture`
- `deriveSceneReadinessRows`
- `deriveAttentionItems`

The model should produce structured data, not JSX. Components render those results.

### Fleet Health

Fleet health rules:

- `danger` if any offline node exists
- `attention` if any stale node exists
- `attention` if desired workers exceed running workers
- `attention` if any direct/native streams are unavailable
- `healthy` when all desired workers are running, no nodes are stale/offline, and native unavailable count is zero
- `unknown` when fleet data is unavailable

### Deployment Posture

Deployment posture summarizes the product's central/edge/hybrid architecture:

- total sites
- total scenes
- central scene count
- edge scene count
- hybrid scene count
- assigned edge-node count
- pending evidence count
- privacy-configured scene count

This should be visible on Dashboard because central/edge/hybrid deployment is a primary differentiator, not a hidden setting.

### Privacy Posture

Privacy posture is derived from existing camera configuration:

- face blur enabled
- plate blur enabled
- edge or hybrid mode selected
- native/direct delivery availability

Labels must stay honest:

- "Face/plate filtering configured"
- "Privacy controls configured"
- "Direct/native delivery available"
- "Privacy posture not reported"

Do not claim compliance or enforced privacy policy unless the current data proves it.

### Scene Readiness

Scene readiness answers: "Is this scene configured enough for a pilot?"

Inputs:

- source capability reported
- processing mode selected
- privacy settings present
- zones configured
- model/classes configured
- delivery profile selected
- worker state from fleet overview
- telemetry state where live frames are available

Scene readiness should have a concise label:

- `Ready`
- `Needs setup`
- `Needs attention`
- `Unknown`

Readiness is broader than health. A scene may have a healthy worker but still need setup if it has no zones/rules for the intended pilot.

### Scene Health

Scene health still matters for runtime status:

- worker desired/runtime state from `camera_workers`
- stream availability from `delivery_diagnostics` or camera browser delivery
- telemetry freshness from live frames where available
- processing mode and assigned node label

Because Phase 5A does not have backend stage timings, the copy must not claim capture latency, TensorRT state, dropped frames, or jitter values. It may say "Telemetry stale" or "Worker not reported"; it must not say "capture_wait high" until Phase 5B exists.

## 6. Dashboard Changes

Dashboard should become the product's command overview for the full OmniSight loop.

Add a **Deployment Posture Strip** near the top:

- Sites
- Scenes
- Central / Edge / Hybrid split
- Privacy-configured scenes
- Evidence awaiting review
- Fleet health

Add or retain an **Attention Stack** below the posture strip:

- Evidence awaiting review
- Workers missing: `desired_workers - running_workers`
- Stale/offline node count
- Direct/native stream unavailable count
- Top affected scene names when available

Healthy state:

- "No operational attention needed"
- short supporting copy
- links to Live and Operations still visible

Attention state:

- show ordered issues by severity
- each issue has a concise reason and route link
- copy should be operational, not theatrical

## 7. Operations Changes

Operations should become the strongest proof of central/edge/hybrid deployment.

Replace the narrow **Scene Health Matrix** concept with a **Scene Intelligence Matrix**.

Columns:

- Scene
- Site
- Mode
- Privacy
- Worker
- Delivery
- Telemetry
- Action

Rows:

- one row per scene
- mode shows central, edge, or hybrid
- privacy is derived from existing privacy settings
- worker, delivery, and telemetry use the shared health model
- actions point to `/live`, `/cameras`, or stay on `/settings` depending on the issue

The existing Nodes, Bootstrap, Scene workers, and Stream diagnostics panels should remain. Phase 5A should place the matrix above those lower detail panels as the first scannable operator surface.

## 8. Live Changes

Live scene tiles should show the same derived signals without becoming cluttered.

Each scene tile should show a compact status strip:

- Mode
- Privacy
- Worker
- Delivery
- Telemetry

The existing heartbeat badge stays. The new strip explains why a scene may be degraded and reinforces that each live scene has a deployment and privacy posture.

## 9. Scenes Changes

Add a **Scene Readiness Cue** to the Scenes inventory.

The Scenes inventory should show whether each scene is pilot-ready using existing data:

- source capability known
- processing mode selected
- privacy controls configured
- zones/rules present
- delivery profile selected
- worker/telemetry status when available

This makes setup and operations meet: an operator editing a scene should see whether it is production- or pilot-ready before opening the wizard.

## 10. Accessibility And Interaction

Requirements:

- Health/readiness state must not rely on color alone.
- Every status badge must have text.
- Attention items must be keyboard reachable when they link to another route.
- No new continuous animation.
- Reduced motion behavior remains unchanged from Phase 3.
- Text must fit at 375px, 768px, 1024px, and 1440px.
- Dense tables must remain horizontally scrollable rather than overflowing on mobile.

## 11. Testing

Unit and page tests should cover:

- fleet health derivation
- deployment posture derivation
- privacy posture derivation
- scene readiness derivation
- dashboard posture strip
- dashboard attention stack ordering
- healthy dashboard empty state
- Operations scene intelligence matrix rows
- Live tile status strip
- Scenes inventory readiness cue

E2E smoke should cover:

- `/dashboard` shows the deployment posture strip and attention stack
- `/settings` shows the scene intelligence matrix
- `/live` still renders scene tiles
- `/cameras` shows the scene readiness column

No backend tests are required for Phase 5A because the backend contract is unchanged.

## 12. Phase 5B Hand-Off

Phase 5B should add backend/runtime metrics after Phase 5A lands:

- `capture_wait_p95_ms`
- `capture_wait_p99_ms`
- `capture_wait_max_ms`
- telemetry dropped frame count
- last worker frame age
- active capture backend
- detection provider
- stream publish status
- last worker error

Phase 5A must not fake those values. It should leave clear room in the UI for them, but only display data the current APIs actually provide.
