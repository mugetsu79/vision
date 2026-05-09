# Operational Readiness UI Phase 5A Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a frontend-only operational readiness layer that makes Vezor's sovereign spatial intelligence loop legible: sites, scenes, central/edge/hybrid deployment posture, privacy posture, evidence awaiting review, scene readiness, worker/delivery health, and telemetry freshness.

**Architecture:** Create a shared `operational-health` utility that derives normalized health, deployment posture, privacy posture, and scene readiness objects from existing `FleetOverview`, `Camera`, `Site`, incident, and live telemetry data. Add focused presentational components for the Dashboard deployment posture strip, Dashboard attention stack, Operations scene intelligence matrix, Live scene status strip, and Scenes readiness cue. Wire those components into existing pages without backend changes, new dependencies, WebGL, or continuous animation.

**Tech Stack:** React 19, Vite 6, TypeScript 5.7, Tailwind v4, TanStack Query, React Router, Vitest, React Testing Library, Playwright. Frontend root: `/Users/yann.moren/vision/frontend`. Working branch: `codex/omnisight-ui-spec-implementation`.

**Spec source:** `/Users/yann.moren/vision/docs/superpowers/specs/2026-05-09-operational-readiness-ui-design.md`

---

## Execution Protocol

The user prefers one implementation task at a time. Execute **one task**, run its verification, commit it, report the result, then wait for the user's next "go" before starting the next task.

Do not stage unrelated untracked scratch files. Current known unrelated untracked files include `.claude/`, `.codex/`, `.superpowers/brainstorm/*`, screenshot files, `camera-capture.md`, `codex-review-findings.md`, `docs/brand/2d_logo.png`, and `docs/brand/3d_logo.png`.

## Pre-flight

```bash
cd /Users/yann.moren/vision
git status --short
git rev-parse --abbrev-ref HEAD
test "$(git rev-parse --abbrev-ref HEAD)" = "codex/omnisight-ui-spec-implementation"
corepack pnpm --dir frontend test
corepack pnpm --dir frontend lint
corepack pnpm --dir frontend build
```

Expected:

- branch is `codex/omnisight-ui-spec-implementation`
- tests, lint, and build pass or only show the already-known warnings from the current branch
- no unrelated scratch files are staged

## File Structure

| Path | Action | Responsibility |
|---|---|---|
| `frontend/src/lib/operational-health.ts` | create | shared health, deployment posture, privacy posture, scene readiness, labels, route targets |
| `frontend/src/lib/operational-health.test.ts` | create | derivation tests |
| `frontend/src/components/operations/DeploymentPostureStrip.tsx` | create | dashboard posture summary for sites/scenes/modes/privacy/evidence/fleet |
| `frontend/src/components/operations/DeploymentPostureStrip.test.tsx` | create | component tests |
| `frontend/src/components/operations/AttentionStack.tsx` | create | dashboard attention list and healthy state |
| `frontend/src/components/operations/AttentionStack.test.tsx` | create | component tests |
| `frontend/src/components/operations/SceneIntelligenceMatrix.tsx` | create | operations scene matrix for site/mode/privacy/worker/delivery/telemetry |
| `frontend/src/components/operations/SceneIntelligenceMatrix.test.tsx` | create | component tests |
| `frontend/src/components/operations/SceneStatusStrip.tsx` | create | compact per-scene mode/privacy/worker/delivery/telemetry badges |
| `frontend/src/components/operations/SceneStatusStrip.test.tsx` | create | component tests |
| `frontend/src/pages/Dashboard.tsx` | modify | add deployment posture strip, attention stack, and derived fleet health |
| `frontend/src/pages/Dashboard.test.tsx` | modify | cover posture, attention, and healthy states |
| `frontend/src/pages/Settings.tsx` | modify | add scene intelligence matrix above lower operations panels |
| `frontend/src/pages/Settings.test.tsx` | modify | cover matrix rows and action links |
| `frontend/src/pages/Live.tsx` | modify | add fleet data and scene status strip to tiles |
| `frontend/src/pages/Live.test.tsx` | modify | cover per-tile status strip |
| `frontend/src/pages/Cameras.tsx` | modify | add readiness cue to scene inventory |
| `frontend/src/pages/Cameras.test.tsx` | modify | cover readiness cue |
| `frontend/e2e/operational-readiness.spec.ts` | create | smoke coverage across pages |
| `frontend/CHANGELOG.md` | modify | document Phase 5A |

---

## Task 1: Shared Operational Readiness Model

**Files:**
- Create: `frontend/src/lib/operational-health.ts`
- Create: `frontend/src/lib/operational-health.test.ts`

- [ ] **Step 1: Write the failing tests**

Create `frontend/src/lib/operational-health.test.ts`:

```ts
import { describe, expect, test } from "vitest";

import {
  deriveAttentionItems,
  deriveDeploymentPosture,
  deriveFleetHealth,
  derivePrivacyPosture,
  deriveSceneReadinessRows,
  healthToTone,
} from "@/lib/operational-health";
import type { components } from "@/lib/api.generated";

type FleetOverview = components["schemas"]["FleetOverviewResponse"];
type Camera = components["schemas"]["CameraResponse"];
type Site = components["schemas"]["SiteResponse"];
type TelemetryFrame = components["schemas"]["TelemetryFrame"];

const fleet: FleetOverview = {
  mode: "manual_dev",
  generated_at: "2026-05-09T08:00:00Z",
  summary: {
    desired_workers: 2,
    running_workers: 1,
    stale_nodes: 1,
    offline_nodes: 0,
    native_unavailable_cameras: 1,
  },
  nodes: [
    {
      id: null,
      kind: "central",
      hostname: "central",
      site_id: null,
      status: "unknown",
      version: null,
      last_seen_at: null,
      assigned_camera_ids: ["camera-1"],
      reported_camera_count: null,
    },
    {
      id: "00000000-0000-0000-0000-000000000999",
      kind: "edge",
      hostname: "orin1",
      site_id: "site-1",
      status: "stale",
      version: "0.1.0",
      last_seen_at: "2026-05-09T07:58:00Z",
      assigned_camera_ids: ["camera-2"],
      reported_camera_count: null,
    },
  ],
  camera_workers: [
    {
      camera_id: "camera-1",
      camera_name: "North Gate",
      site_id: "site-1",
      node_id: null,
      node_hostname: null,
      processing_mode: "central",
      desired_state: "manual",
      runtime_status: "running",
      lifecycle_owner: "manual_dev",
      dev_run_command: null,
      detail: null,
    },
    {
      camera_id: "camera-2",
      camera_name: "Depot Yard",
      site_id: "site-1",
      node_id: "00000000-0000-0000-0000-000000000999",
      node_hostname: "orin1",
      processing_mode: "edge",
      desired_state: "supervised",
      runtime_status: "stale",
      lifecycle_owner: "edge_supervisor",
      dev_run_command: null,
      detail: "Edge heartbeat is stale.",
    },
  ],
  delivery_diagnostics: [
    {
      camera_id: "camera-1",
      camera_name: "North Gate",
      processing_mode: "central",
      assigned_node_id: null,
      source_capability: { width: 1920, height: 1080, fps: 15 },
      default_profile: "native",
      available_profiles: [],
      native_status: { available: true, reason: null },
      selected_stream_mode: "passthrough",
    },
    {
      camera_id: "camera-2",
      camera_name: "Depot Yard",
      processing_mode: "edge",
      assigned_node_id: "00000000-0000-0000-0000-000000000999",
      source_capability: { width: 1920, height: 1080, fps: 15 },
      default_profile: "native",
      available_profiles: [],
      native_status: { available: false, reason: "source_unavailable" },
      selected_stream_mode: "passthrough",
    },
  ],
};

function createCamera(overrides: Partial<Camera>): Camera {
  return {
    id: "camera-1",
    site_id: "site-1",
    edge_node_id: null,
    name: "North Gate",
    rtsp_url_masked: "rtsp://redacted@camera.local/live",
    processing_mode: "central",
    primary_model_id: "00000000-0000-0000-0000-000000000001",
    secondary_model_id: null,
    tracker_type: "bytetrack",
    active_classes: ["person"],
    attribute_rules: [],
    zones: [{ id: "entry-line", type: "line", points: [[0, 0], [1, 1]] }],
    homography: { src: [], dst: [], ref_distance_m: 1 },
    privacy: {
      blur_faces: true,
      blur_plates: true,
      method: "gaussian",
      strength: 7,
    },
    browser_delivery: {
      default_profile: "native",
      allow_native_on_demand: true,
      profiles: [],
      unsupported_profiles: [],
      native_status: { available: true, reason: null },
    },
    source_capability: { width: 1920, height: 1080, fps: 15 },
    frame_skip: 1,
    fps_cap: 25,
    created_at: "2026-05-09T07:00:00Z",
    updated_at: "2026-05-09T07:00:00Z",
    ...overrides,
  };
}

const cameras: Camera[] = [
  createCamera({ id: "camera-1", name: "North Gate" }),
  createCamera({
    id: "camera-2",
    name: "Depot Yard",
    processing_mode: "edge",
    edge_node_id: "00000000-0000-0000-0000-000000000999",
    zones: [],
    browser_delivery: {
      default_profile: "native",
      allow_native_on_demand: true,
      profiles: [],
      unsupported_profiles: [],
      native_status: { available: false, reason: "source_unavailable" },
    },
  }),
];

const sites: Site[] = [
  {
    id: "site-1",
    tenant_id: "tenant-1",
    name: "Zurich Lab",
    description: null,
    tz: "Europe/Zurich",
    geo_point: null,
    created_at: "2026-05-09T07:00:00Z",
  },
];

const freshFrame: TelemetryFrame = {
  camera_id: "camera-1",
  ts: new Date().toISOString(),
  profile: "central-gpu",
  stream_mode: "annotated-whip",
  counts: {},
  tracks: [],
};

describe("operational health", () => {
  test("maps health to status tone badges", () => {
    expect(healthToTone("healthy")).toBe("healthy");
    expect(healthToTone("attention")).toBe("attention");
    expect(healthToTone("danger")).toBe("danger");
    expect(healthToTone("unknown")).toBe("muted");
  });

  test("derives fleet attention from existing summary fields", () => {
    const result = deriveFleetHealth(fleet);
    expect(result.health).toBe("attention");
    expect(result.label).toBe("Attention needed");
    expect(result.reasons).toEqual([
      "1 stale node",
      "1 worker missing",
      "1 direct stream unavailable",
    ]);
  });

  test("derives dashboard attention items ordered by severity", () => {
    const items = deriveAttentionItems({
      fleet,
      cameras,
      pendingIncidents: [{ id: "incident-1" }],
    });

    expect(items.map((item) => item.title)).toEqual([
      "Evidence waiting for review",
      "Edge or central workers need attention",
      "Direct streams unavailable",
      "Node heartbeats stale",
    ]);
    expect(items[0].href).toBe("/incidents");
  });

  test("derives deployment posture from existing sites cameras incidents and fleet", () => {
    const posture = deriveDeploymentPosture({
      sites,
      cameras,
      fleet,
      pendingIncidents: [{ id: "incident-1" }],
    });

    expect(posture).toMatchObject({
      siteCount: 1,
      sceneCount: 2,
      centralScenes: 1,
      edgeScenes: 1,
      hybridScenes: 0,
      assignedEdgeNodes: 1,
      pendingEvidence: 1,
      privacyConfiguredScenes: 2,
    });
  });

  test("derives privacy posture without making compliance claims", () => {
    expect(derivePrivacyPosture(cameras[0])).toMatchObject({
      health: "healthy",
      label: "Face/plate filtering configured",
    });
  });

  test("derives scene readiness rows from cameras, fleet records, and telemetry", () => {
    const rows = deriveSceneReadinessRows({
      cameras,
      sites,
      fleet,
      framesByCamera: { "camera-1": freshFrame },
    });

    expect(rows).toHaveLength(2);
    expect(rows[0]).toMatchObject({
      cameraId: "camera-1",
      cameraName: "North Gate",
      siteName: "Zurich Lab",
      readiness: { health: "healthy", label: "Ready" },
      privacy: { health: "healthy", label: "Face/plate filtering configured" },
      worker: { health: "healthy", label: "Worker running" },
      delivery: { health: "healthy", label: "Native stream available" },
      telemetry: { health: "healthy", label: "Telemetry live" },
    });
    expect(rows[1]).toMatchObject({
      cameraId: "camera-2",
      cameraName: "Depot Yard",
      readiness: { health: "attention", label: "Needs setup" },
      worker: { health: "attention", label: "Worker stale" },
      delivery: { health: "danger", label: "Direct stream unavailable" },
      telemetry: { health: "unknown", label: "Awaiting telemetry" },
    });
  });
});
```

- [ ] **Step 2: Run the failing tests**

```bash
corepack pnpm --dir frontend exec vitest run src/lib/operational-health.test.ts
```

Expected: FAIL because `@/lib/operational-health` does not exist.

- [ ] **Step 3: Implement `frontend/src/lib/operational-health.ts`**

```ts
import type { components } from "@/lib/api.generated";
import { getHeartbeatStatus } from "@/lib/live";

type FleetOverview = components["schemas"]["FleetOverviewResponse"];
type FleetCameraWorker = components["schemas"]["FleetCameraWorkerSummary"];
type FleetDeliveryDiagnostic = components["schemas"]["FleetDeliveryDiagnostic"];
type Camera = components["schemas"]["CameraResponse"];
type TelemetryFrame = components["schemas"]["TelemetryFrame"];

export type OperationalHealth = "healthy" | "attention" | "danger" | "unknown";
export type HealthTone = "healthy" | "attention" | "danger" | "muted";

export type HealthSignal = {
  health: OperationalHealth;
  label: string;
  detail?: string;
};

export type FleetHealth = HealthSignal & {
  reasons: string[];
};

export type AttentionItem = {
  id: string;
  health: Exclude<OperationalHealth, "healthy" | "unknown">;
  title: string;
  detail: string;
  href: string;
};

export type SceneHealthRow = {
  cameraId: string;
  cameraName: string;
  siteName: string;
  nodeLabel: string;
  processingMode: Camera["processing_mode"];
  readiness: HealthSignal;
  overall: HealthSignal;
  privacy: HealthSignal;
  worker: HealthSignal;
  delivery: HealthSignal;
  telemetry: HealthSignal;
  actionHref: string;
  actionLabel: string;
};

export type DeploymentPosture = {
  siteCount: number;
  sceneCount: number;
  centralScenes: number;
  edgeScenes: number;
  hybridScenes: number;
  assignedEdgeNodes: number;
  pendingEvidence: number;
  privacyConfiguredScenes: number;
  fleetHealth: FleetHealth;
};

export function healthToTone(health: OperationalHealth): HealthTone {
  if (health === "healthy") return "healthy";
  if (health === "attention") return "attention";
  if (health === "danger") return "danger";
  return "muted";
}

export function deriveFleetHealth(fleet: FleetOverview | null | undefined): FleetHealth {
  if (!fleet) {
    return {
      health: "unknown",
      label: "Fleet status unknown",
      reasons: ["Fleet overview has not loaded"],
    };
  }

  const missingWorkers = Math.max(
    0,
    fleet.summary.desired_workers - fleet.summary.running_workers,
  );
  const reasons: string[] = [];

  if (fleet.summary.offline_nodes > 0) {
    reasons.push(plural(fleet.summary.offline_nodes, "offline node"));
  }
  if (fleet.summary.stale_nodes > 0) {
    reasons.push(plural(fleet.summary.stale_nodes, "stale node"));
  }
  if (missingWorkers > 0) {
    reasons.push(plural(missingWorkers, "worker missing", "workers missing"));
  }
  if (fleet.summary.native_unavailable_cameras > 0) {
    reasons.push(
      plural(
        fleet.summary.native_unavailable_cameras,
        "direct stream unavailable",
        "direct streams unavailable",
      ),
    );
  }

  if (fleet.summary.offline_nodes > 0) {
    return { health: "danger", label: "Critical attention needed", reasons };
  }
  if (reasons.length > 0) {
    return { health: "attention", label: "Attention needed", reasons };
  }
  return { health: "healthy", label: "Fleet healthy", reasons: ["All desired workers running"] };
}

export function deriveAttentionItems({
  fleet,
  cameras,
  pendingIncidents,
}: {
  fleet: FleetOverview | null | undefined;
  cameras: Camera[];
  pendingIncidents: Array<{ id: string }>;
}): AttentionItem[] {
  const items: AttentionItem[] = [];
  const missingWorkers = fleet
    ? Math.max(0, fleet.summary.desired_workers - fleet.summary.running_workers)
    : 0;

  if (pendingIncidents.length > 0) {
    items.push({
      id: "pending-evidence",
      health: "attention",
      title: "Evidence waiting for review",
      detail: plural(pendingIncidents.length, "pending evidence record"),
      href: "/incidents",
    });
  }

  if (fleet && (missingWorkers > 0 || fleet.summary.offline_nodes > 0)) {
    items.push({
      id: "workers",
      health: fleet.summary.offline_nodes > 0 ? "danger" : "attention",
      title: "Edge or central workers need attention",
      detail:
        missingWorkers > 0
          ? plural(missingWorkers, "worker is not running", "workers are not running")
          : plural(fleet.summary.offline_nodes, "node is offline", "nodes are offline"),
      href: "/settings",
    });
  }

  if (fleet && fleet.summary.native_unavailable_cameras > 0) {
    items.push({
      id: "direct-streams",
      health: "attention",
      title: "Direct streams unavailable",
      detail: affectedSceneDetail(
        cameras,
        fleet.delivery_diagnostics
          .filter((diagnostic) => diagnostic.native_status?.available === false)
          .map((diagnostic) => diagnostic.camera_id),
      ),
      href: "/settings",
    });
  }

  if (fleet && fleet.summary.stale_nodes > 0) {
    items.push({
      id: "stale-nodes",
      health: "attention",
      title: "Node heartbeats stale",
      detail: plural(fleet.summary.stale_nodes, "node needs a fresh heartbeat"),
      href: "/settings",
    });
  }

  return items.sort((a, b) => severityRank(b.health) - severityRank(a.health));
}

export function deriveDeploymentPosture({
  sites,
  cameras,
  fleet,
  pendingIncidents,
}: {
  sites: Array<{ id: string }>;
  cameras: Camera[];
  fleet: FleetOverview | null | undefined;
  pendingIncidents: Array<{ id: string }>;
}): DeploymentPosture {
  return {
    siteCount: sites.length,
    sceneCount: cameras.length,
    centralScenes: cameras.filter((camera) => camera.processing_mode === "central").length,
    edgeScenes: cameras.filter((camera) => camera.processing_mode === "edge").length,
    hybridScenes: cameras.filter((camera) => camera.processing_mode === "hybrid").length,
    assignedEdgeNodes: new Set(cameras.map((camera) => camera.edge_node_id).filter(Boolean)).size,
    pendingEvidence: pendingIncidents.length,
    privacyConfiguredScenes: cameras.filter((camera) => derivePrivacyPosture(camera).health === "healthy").length,
    fleetHealth: deriveFleetHealth(fleet),
  };
}

export function derivePrivacyPosture(camera: Camera): HealthSignal {
  if (camera.privacy?.blur_faces && camera.privacy.blur_plates) {
    return { health: "healthy", label: "Face/plate filtering configured" };
  }
  if (camera.privacy?.blur_faces || camera.privacy?.blur_plates) {
    return { health: "attention", label: "Partial privacy controls" };
  }
  return { health: "unknown", label: "Privacy posture not reported" };
}

export function deriveSceneReadinessRows({
  cameras,
  sites,
  fleet,
  framesByCamera,
}: {
  cameras: Camera[];
  sites?: Array<{ id: string; name: string }>;
  fleet: FleetOverview | null | undefined;
  framesByCamera?: Record<string, TelemetryFrame | undefined>;
}): SceneHealthRow[] {
  const workers = new Map<string, FleetCameraWorker>(
    fleet?.camera_workers.map((worker) => [worker.camera_id, worker]) ?? [],
  );
  const diagnostics = new Map<string, FleetDeliveryDiagnostic>(
    fleet?.delivery_diagnostics.map((diagnostic) => [diagnostic.camera_id, diagnostic]) ?? [],
  );

  return cameras.map((camera) => {
    const worker = workers.get(camera.id);
    const diagnostic = diagnostics.get(camera.id);
    const telemetry = telemetrySignal(framesByCamera?.[camera.id]);
    const privacy = derivePrivacyPosture(camera);
    const workerHealth = workerSignal(worker);
    const delivery = deliverySignal(camera, diagnostic);
    const readiness = readinessSignal(camera, workerHealth, delivery, telemetry);
    const overall = strongestSignal([readiness, workerHealth, delivery, telemetry]);

    return {
      cameraId: camera.id,
      cameraName: camera.name,
      siteName: sites?.find((site) => site.id === camera.site_id)?.name ?? "Unknown site",
      nodeLabel: worker?.node_hostname ?? (camera.edge_node_id ? "assigned edge" : "central"),
      processingMode: camera.processing_mode,
      readiness,
      overall,
      privacy,
      worker: workerHealth,
      delivery,
      telemetry,
      actionHref: actionHrefFor(overall, delivery),
      actionLabel: actionLabelFor(overall, delivery),
    };
  });
}

function readinessSignal(
  camera: Camera,
  worker: HealthSignal,
  delivery: HealthSignal,
  telemetry: HealthSignal,
): HealthSignal {
  if (!camera.source_capability || camera.zones.length === 0) {
    return { health: "attention", label: "Needs setup" };
  }
  if (worker.health === "danger" || delivery.health === "danger") {
    return { health: "danger", label: "Needs attention" };
  }
  if (worker.health === "attention" || delivery.health === "attention" || telemetry.health === "attention") {
    return { health: "attention", label: "Needs attention" };
  }
  return { health: "healthy", label: "Ready" };
}

function workerSignal(worker: FleetCameraWorker | undefined): HealthSignal {
  if (!worker) {
    return { health: "unknown", label: "Worker not reported" };
  }
  if (worker.runtime_status === "running") {
    return { health: "healthy", label: "Worker running", detail: worker.lifecycle_owner };
  }
  if (worker.runtime_status === "offline") {
    return { health: "danger", label: "Worker offline", detail: worker.detail ?? undefined };
  }
  if (worker.runtime_status === "stale") {
    return { health: "attention", label: "Worker stale", detail: worker.detail ?? undefined };
  }
  return { health: "attention", label: "Worker not reported", detail: worker.detail ?? undefined };
}

function deliverySignal(
  camera: Camera,
  diagnostic: FleetDeliveryDiagnostic | undefined,
): HealthSignal {
  const nativeStatus =
    diagnostic?.native_status ?? camera.browser_delivery?.native_status ?? undefined;
  const defaultProfile = diagnostic?.default_profile ?? camera.browser_delivery?.default_profile;
  if (nativeStatus?.available === false) {
    return {
      health: defaultProfile === "native" ? "danger" : "attention",
      label: "Direct stream unavailable",
      detail: formatReason(nativeStatus.reason),
    };
  }
  if (nativeStatus?.available === true) {
    return { health: "healthy", label: "Native stream available" };
  }
  if (camera.source_capability) {
    return { health: "healthy", label: "Source capability reported" };
  }
  return { health: "unknown", label: "Delivery not reported" };
}

function telemetrySignal(frame: TelemetryFrame | undefined): HealthSignal {
  const status = getHeartbeatStatus(frame);
  if (status === "fresh") return { health: "healthy", label: "Telemetry live" };
  if (status === "stale") return { health: "attention", label: "Telemetry stale" };
  return { health: "unknown", label: "Awaiting telemetry" };
}

function strongestSignal(signals: HealthSignal[]): HealthSignal {
  return signals.reduce((current, next) =>
    severityRank(next.health) > severityRank(current.health) ? next : current,
  );
}

function severityRank(health: OperationalHealth): number {
  if (health === "danger") return 3;
  if (health === "attention") return 2;
  if (health === "unknown") return 1;
  return 0;
}

function actionHrefFor(overall: HealthSignal, delivery: HealthSignal): string {
  if (delivery.health === "danger" || delivery.health === "attention") return "/settings";
  if (overall.health === "attention" || overall.health === "danger") return "/settings";
  return "/live";
}

function actionLabelFor(overall: HealthSignal, delivery: HealthSignal): string {
  if (delivery.health === "danger" || delivery.health === "attention") return "Inspect delivery";
  if (overall.health === "attention" || overall.health === "danger") return "Inspect operations";
  return "Open live";
}

function affectedSceneDetail(cameras: Camera[], ids: string[]): string {
  const names = ids
    .map((id) => cameras.find((camera) => camera.id === id)?.name)
    .filter((name): name is string => Boolean(name));
  if (names.length === 0) return "Review stream diagnostics";
  if (names.length <= 2) return names.join(", ");
  return `${names.slice(0, 2).join(", ")} and ${names.length - 2} more`;
}

function formatReason(reason: string | null | undefined): string | undefined {
  return reason ? reason.replaceAll("_", " ") : undefined;
}

function plural(count: number, singular: string, pluralLabel = `${singular}s`): string {
  return `${count} ${count === 1 ? singular : pluralLabel}`;
}
```

- [ ] **Step 4: Run targeted tests**

```bash
corepack pnpm --dir frontend exec vitest run src/lib/operational-health.test.ts
```

Expected: PASS.

- [ ] **Step 5: Run lint**

```bash
corepack pnpm --dir frontend lint
```

Expected: PASS with no new warnings from these files.

- [ ] **Step 6: Commit**

```bash
git add frontend/src/lib/operational-health.ts frontend/src/lib/operational-health.test.ts
git commit -m "feat(ops): derive frontend operational readiness"
```

---

## Task 2: Dashboard Deployment Posture And Attention Stack

**Files:**
- Create: `frontend/src/components/operations/DeploymentPostureStrip.tsx`
- Create: `frontend/src/components/operations/DeploymentPostureStrip.test.tsx`
- Create: `frontend/src/components/operations/AttentionStack.tsx`
- Create: `frontend/src/components/operations/AttentionStack.test.tsx`
- Modify: `frontend/src/pages/Dashboard.tsx`
- Modify: `frontend/src/pages/Dashboard.test.tsx`

- [ ] **Step 1: Write component tests**

Create `frontend/src/components/operations/DeploymentPostureStrip.test.tsx`:

```tsx
import { render, screen } from "@testing-library/react";
import { describe, expect, test } from "vitest";

import { DeploymentPostureStrip } from "@/components/operations/DeploymentPostureStrip";
import type { DeploymentPosture } from "@/lib/operational-health";

const posture: DeploymentPosture = {
  siteCount: 2,
  sceneCount: 5,
  centralScenes: 2,
  edgeScenes: 2,
  hybridScenes: 1,
  assignedEdgeNodes: 1,
  pendingEvidence: 3,
  privacyConfiguredScenes: 4,
  fleetHealth: {
    health: "attention",
    label: "Attention needed",
    reasons: ["1 worker missing"],
  },
};

describe("DeploymentPostureStrip", () => {
  test("renders sites scenes modes privacy evidence and fleet posture", () => {
    render(<DeploymentPostureStrip posture={posture} />);

    expect(screen.getByTestId("deployment-posture-strip")).toBeInTheDocument();
    expect(screen.getByText("Sites")).toBeInTheDocument();
    expect(screen.getByText("2 / 2 / 1")).toBeInTheDocument();
    expect(screen.getByText("Privacy configured")).toBeInTheDocument();
    expect(screen.getByText("Evidence awaiting review")).toBeInTheDocument();
    expect(screen.getByText("Attention needed")).toBeInTheDocument();
  });
});
```

Create `frontend/src/components/operations/AttentionStack.test.tsx`:

```tsx
import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, test } from "vitest";

import { AttentionStack } from "@/components/operations/AttentionStack";
import type { AttentionItem, FleetHealth } from "@/lib/operational-health";

describe("AttentionStack", () => {
  test("renders ordered attention items with route links", () => {
    const items: AttentionItem[] = [
      {
        id: "workers",
        health: "danger",
        title: "Edge or central workers need attention",
        detail: "1 worker is not running",
        href: "/settings",
      },
      {
        id: "evidence",
        health: "attention",
        title: "Evidence waiting for review",
        detail: "2 pending evidence records",
        href: "/incidents",
      },
    ];

    render(
      <MemoryRouter>
        <AttentionStack items={items} fleetHealth={{ health: "attention", label: "Attention needed", reasons: [] }} />
      </MemoryRouter>,
    );

    expect(screen.getByRole("heading", { name: /attention stack/i })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /edge or central workers/i })).toHaveAttribute("href", "/settings");
    expect(screen.getByRole("link", { name: /evidence waiting/i })).toHaveAttribute("href", "/incidents");
  });

  test("renders a healthy state when there are no attention items", () => {
    const fleetHealth: FleetHealth = {
      health: "healthy",
      label: "Fleet healthy",
      reasons: ["All desired workers running"],
    };

    render(
      <MemoryRouter>
        <AttentionStack items={[]} fleetHealth={fleetHealth} />
      </MemoryRouter>,
    );

    expect(screen.getByText(/no operational attention needed/i)).toBeInTheDocument();
    expect(screen.getByText(/all desired workers running/i)).toBeInTheDocument();
  });
});
```

- [ ] **Step 2: Run the failing component tests**

```bash
corepack pnpm --dir frontend exec vitest run src/components/operations/DeploymentPostureStrip.test.tsx src/components/operations/AttentionStack.test.tsx
```

Expected: FAIL because the component does not exist.

- [ ] **Step 3: Implement `DeploymentPostureStrip`**

Create `frontend/src/components/operations/DeploymentPostureStrip.tsx`:

```tsx
import { KpiTile } from "@/components/dashboard/KpiTile";
import { StatusToneBadge } from "@/components/layout/workspace-surfaces";
import {
  healthToTone,
  type DeploymentPosture,
} from "@/lib/operational-health";

type DeploymentPostureStripProps = {
  posture: DeploymentPosture;
};

export function DeploymentPostureStrip({ posture }: DeploymentPostureStripProps) {
  return (
    <section
      data-testid="deployment-posture-strip"
      aria-label="Deployment posture"
      className="grid gap-3 sm:grid-cols-2 xl:grid-cols-6"
    >
      <KpiTile
        eyebrow="Sites"
        value={posture.siteCount}
        caption={`${posture.sceneCount} operational scenes`}
      />
      <KpiTile
        eyebrow="Central / Edge / Hybrid"
        value={`${posture.centralScenes} / ${posture.edgeScenes} / ${posture.hybridScenes}`}
        caption={`${posture.assignedEdgeNodes} assigned edge nodes`}
      />
      <KpiTile
        eyebrow="Privacy configured"
        value={posture.privacyConfiguredScenes}
        caption="face or plate controls present"
      />
      <KpiTile
        eyebrow="Evidence awaiting review"
        value={posture.pendingEvidence}
        caption="pending records"
      />
      <div className="rounded-[var(--vz-r-md)] border border-[color:var(--vz-hair)] bg-[color:var(--vz-canvas-graphite-up)] px-4 py-3 shadow-[var(--vz-elev-1)] sm:col-span-2 xl:col-span-2">
        <p className="text-[11px] font-semibold uppercase tracking-normal text-[var(--vz-text-muted)]">
          Fleet health
        </p>
        <div className="mt-2">
          <StatusToneBadge tone={healthToTone(posture.fleetHealth.health)}>
            {posture.fleetHealth.label}
          </StatusToneBadge>
        </div>
        <p className="mt-2 text-xs text-[var(--vz-text-secondary)]">
          {posture.fleetHealth.reasons[0] ?? "No reported fleet issues"}
        </p>
      </div>
    </section>
  );
}
```

- [ ] **Step 4: Implement `AttentionStack`**

Create `frontend/src/components/operations/AttentionStack.tsx`:

```tsx
import { Link } from "react-router-dom";

import {
  StatusToneBadge,
  WorkspaceSurface,
} from "@/components/layout/workspace-surfaces";
import {
  healthToTone,
  type AttentionItem,
  type FleetHealth,
} from "@/lib/operational-health";

type AttentionStackProps = {
  items: AttentionItem[];
  fleetHealth: FleetHealth;
};

export function AttentionStack({ items, fleetHealth }: AttentionStackProps) {
  return (
    <WorkspaceSurface data-testid="attention-stack" className="p-4">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <p className="text-[11px] font-semibold uppercase tracking-[0.22em] text-[var(--vz-text-muted)]">
            Operational readiness
          </p>
          <h2 className="mt-2 text-lg font-semibold text-[var(--vz-text-primary)]">
            Attention stack
          </h2>
        </div>
        <StatusToneBadge tone={healthToTone(fleetHealth.health)}>
          {fleetHealth.label}
        </StatusToneBadge>
      </div>

      {items.length === 0 ? (
        <div className="mt-4 rounded-[var(--vz-r-md)] border border-[rgba(111,224,163,0.22)] bg-[rgba(10,36,24,0.38)] px-4 py-3">
          <p className="text-sm font-semibold text-[var(--vz-state-healthy)]">
            No operational attention needed
          </p>
          <p className="mt-1 text-sm text-[var(--vz-text-secondary)]">
            {fleetHealth.reasons[0] ?? "Fleet data is ready."}
          </p>
        </div>
      ) : (
        <div className="mt-4 divide-y divide-white/8 overflow-hidden rounded-[var(--vz-r-md)] border border-[color:var(--vz-hair)]">
          {items.map((item) => (
            <Link
              key={item.id}
              to={item.href}
              className="grid gap-3 px-4 py-3 transition hover:bg-white/[0.04] sm:grid-cols-[auto_minmax(0,1fr)_auto]"
            >
              <StatusToneBadge tone={healthToTone(item.health)}>
                {item.health}
              </StatusToneBadge>
              <span className="min-w-0">
                <span className="block text-sm font-semibold text-[var(--vz-text-primary)]">
                  {item.title}
                </span>
                <span className="mt-1 block text-sm text-[var(--vz-text-secondary)]">
                  {item.detail}
                </span>
              </span>
              <span className="text-sm font-semibold text-[var(--vz-lens-cerulean)]">
                Open
              </span>
            </Link>
          ))}
        </div>
      )}
    </WorkspaceSurface>
  );
}
```

- [ ] **Step 5: Wire Dashboard**

Modify `frontend/src/pages/Dashboard.tsx`:

```tsx
import { useMemo } from "react";
```

Add imports:

```tsx
import { AttentionStack } from "@/components/operations/AttentionStack";
import { DeploymentPostureStrip } from "@/components/operations/DeploymentPostureStrip";
import {
  deriveAttentionItems,
  deriveDeploymentPosture,
  deriveFleetHealth,
} from "@/lib/operational-health";
```

Inside `DashboardPage`, after `const fleet = useFleetOverview();`, add:

```tsx
  const fleetHealth = deriveFleetHealth(fleet.data);
  const deploymentPosture = useMemo(
    () =>
      deriveDeploymentPosture({
        sites,
        cameras,
        fleet: fleet.data,
        pendingIncidents: incidents,
      }),
    [cameras, fleet.data, incidents, sites],
  );
  const attentionItems = useMemo(
    () =>
      deriveAttentionItems({
        fleet: fleet.data,
        cameras,
        pendingIncidents: incidents,
      }),
    [cameras, fleet.data, incidents],
  );
```

Render the posture strip and stack immediately after `WorkspaceHero`:

```tsx
      <DeploymentPostureStrip posture={deploymentPosture} />
      <AttentionStack items={attentionItems} fleetHealth={fleetHealth} />
```

The surrounding grid should still compile with the existing `InstrumentRail` and overview links.

- [ ] **Step 6: Update Dashboard tests**

In `frontend/src/pages/Dashboard.test.tsx`, assert the new stack:

```tsx
    expect(screen.getByTestId("attention-stack")).toBeInTheDocument();
    expect(screen.getByTestId("deployment-posture-strip")).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: /attention stack/i })).toBeInTheDocument();
    expect(screen.getByText(/evidence waiting for review/i)).toBeInTheDocument();
    expect(screen.getByText(/direct streams unavailable/i)).toBeInTheDocument();
```

Add a second test with mocked healthy fleet/incidents if needed:

```tsx
  test("can render the healthy attention state", () => {
    render(
      <MemoryRouter>
        <AttentionStack
          items={[]}
          fleetHealth={{
            health: "healthy",
            label: "Fleet healthy",
            reasons: ["All desired workers running"],
          }}
        />
      </MemoryRouter>,
    );

    expect(screen.getByText(/no operational attention needed/i)).toBeInTheDocument();
  });
```

If this second test belongs better in `AttentionStack.test.tsx`, keep it there and do not duplicate it.

- [ ] **Step 7: Run targeted tests**

```bash
corepack pnpm --dir frontend exec vitest run src/components/operations/DeploymentPostureStrip.test.tsx src/components/operations/AttentionStack.test.tsx src/pages/Dashboard.test.tsx
```

Expected: PASS.

- [ ] **Step 8: Run lint and commit**

```bash
corepack pnpm --dir frontend lint
git add frontend/src/components/operations/DeploymentPostureStrip.tsx frontend/src/components/operations/DeploymentPostureStrip.test.tsx frontend/src/components/operations/AttentionStack.tsx frontend/src/components/operations/AttentionStack.test.tsx frontend/src/pages/Dashboard.tsx frontend/src/pages/Dashboard.test.tsx
git commit -m "feat(dashboard): add deployment posture and attention stack"
```

---

## Task 3: Operations Scene Intelligence Matrix

**Files:**
- Create: `frontend/src/components/operations/SceneIntelligenceMatrix.tsx`
- Create: `frontend/src/components/operations/SceneIntelligenceMatrix.test.tsx`
- Modify: `frontend/src/pages/Settings.tsx`
- Modify: `frontend/src/pages/Settings.test.tsx`

- [ ] **Step 1: Write the failing component tests**

Create `frontend/src/components/operations/SceneIntelligenceMatrix.test.tsx`:

```tsx
import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, test } from "vitest";

import { SceneIntelligenceMatrix } from "@/components/operations/SceneIntelligenceMatrix";
import type { SceneHealthRow } from "@/lib/operational-health";

const rows: SceneHealthRow[] = [
  {
    cameraId: "camera-1",
    cameraName: "North Gate",
    siteName: "Zurich Lab",
    nodeLabel: "central",
    processingMode: "central",
    readiness: { health: "healthy", label: "Ready" },
    overall: { health: "healthy", label: "Worker running" },
    privacy: { health: "healthy", label: "Face/plate filtering configured" },
    worker: { health: "healthy", label: "Worker running" },
    delivery: { health: "healthy", label: "Native stream available" },
    telemetry: { health: "healthy", label: "Telemetry live" },
    actionHref: "/live",
    actionLabel: "Open live",
  },
  {
    cameraId: "camera-2",
    cameraName: "Depot Yard",
    siteName: "Zurich Lab",
    nodeLabel: "orin1",
    processingMode: "edge",
    readiness: { health: "attention", label: "Needs setup" },
    overall: { health: "danger", label: "Direct stream unavailable" },
    privacy: { health: "healthy", label: "Face/plate filtering configured" },
    worker: { health: "attention", label: "Worker stale", detail: "Edge heartbeat is stale." },
    delivery: { health: "danger", label: "Direct stream unavailable", detail: "source unavailable" },
    telemetry: { health: "unknown", label: "Awaiting telemetry" },
    actionHref: "/settings",
    actionLabel: "Inspect delivery",
  },
];

describe("SceneIntelligenceMatrix", () => {
  test("renders scene rows with site mode privacy worker delivery telemetry and actions", () => {
    render(
      <MemoryRouter>
        <SceneIntelligenceMatrix rows={rows} />
      </MemoryRouter>,
    );

    expect(screen.getByRole("heading", { name: /scene intelligence matrix/i })).toBeInTheDocument();
    expect(screen.getByText("North Gate")).toBeInTheDocument();
    expect(screen.getByText("Depot Yard")).toBeInTheDocument();
    expect(screen.getAllByText(/face\/plate filtering configured/i).length).toBeGreaterThan(0);
    expect(screen.getAllByText(/worker stale/i).length).toBeGreaterThan(0);
    expect(screen.getByRole("link", { name: /inspect delivery for depot yard/i })).toHaveAttribute("href", "/settings");
  });

  test("renders an empty state when no scenes exist", () => {
    render(
      <MemoryRouter>
        <SceneIntelligenceMatrix rows={[]} />
      </MemoryRouter>,
    );
    expect(screen.getByText(/no scenes configured/i)).toBeInTheDocument();
  });
});
```

- [ ] **Step 2: Run the failing component tests**

```bash
corepack pnpm --dir frontend exec vitest run src/components/operations/SceneIntelligenceMatrix.test.tsx
```

Expected: FAIL because the component does not exist.

- [ ] **Step 3: Implement `SceneIntelligenceMatrix`**

Create `frontend/src/components/operations/SceneIntelligenceMatrix.tsx`:

```tsx
import { Link } from "react-router-dom";

import {
  StatusToneBadge,
  WorkspaceSurface,
} from "@/components/layout/workspace-surfaces";
import { healthToTone, type SceneHealthRow } from "@/lib/operational-health";

type SceneIntelligenceMatrixProps = {
  rows: SceneHealthRow[];
};

export function SceneIntelligenceMatrix({ rows }: SceneIntelligenceMatrixProps) {
  return (
    <WorkspaceSurface data-testid="scene-intelligence-matrix" className="overflow-hidden">
      <div className="border-b border-white/8 px-4 py-3">
        <p className="text-[11px] font-semibold uppercase tracking-[0.22em] text-[var(--vz-text-muted)]">
          Operational readiness
        </p>
        <h2 className="mt-2 text-lg font-semibold text-[var(--vz-text-primary)]">
          Scene intelligence matrix
        </h2>
      </div>

      {rows.length === 0 ? (
        <p className="px-4 py-5 text-sm text-[var(--vz-text-secondary)]">
          No scenes configured.
        </p>
      ) : (
        <div className="overflow-x-auto">
          <table className="min-w-full text-left text-sm">
            <thead className="bg-black/20 text-[11px] uppercase tracking-[0.16em] text-[var(--vz-text-muted)]">
              <tr>
                <th className="px-4 py-3 font-semibold">Scene</th>
                <th className="px-4 py-3 font-semibold">Site</th>
                <th className="px-4 py-3 font-semibold">Mode</th>
                <th className="px-4 py-3 font-semibold">Privacy</th>
                <th className="px-4 py-3 font-semibold">Worker</th>
                <th className="px-4 py-3 font-semibold">Delivery</th>
                <th className="px-4 py-3 font-semibold">Telemetry</th>
                <th className="px-4 py-3 font-semibold">Action</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-white/8">
              {rows.map((row) => (
                <tr key={row.cameraId}>
                  <td className="px-4 py-3 font-semibold text-[var(--vz-text-primary)]">
                    {row.cameraName}
                  </td>
                  <td className="px-4 py-3 text-[var(--vz-text-secondary)]">
                    {row.siteName}
                  </td>
                  <td className="px-4 py-3 text-[var(--vz-text-secondary)]">
                    {row.processingMode} / {row.nodeLabel}
                  </td>
                  <td className="px-4 py-3">
                    <HealthCell signal={row.privacy} />
                  </td>
                  <td className="px-4 py-3">
                    <HealthCell signal={row.worker} />
                  </td>
                  <td className="px-4 py-3">
                    <HealthCell signal={row.delivery} />
                  </td>
                  <td className="px-4 py-3">
                    <HealthCell signal={row.telemetry} />
                  </td>
                  <td className="px-4 py-3">
                    <Link
                      to={row.actionHref}
                      aria-label={`${row.actionLabel} for ${row.cameraName}`}
                      className="text-sm font-semibold text-[var(--vz-lens-cerulean)] transition hover:text-[var(--vz-text-primary)]"
                    >
                      {row.actionLabel}
                    </Link>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </WorkspaceSurface>
  );
}

function HealthCell({
  signal,
}: {
  signal: SceneHealthRow["worker"];
}) {
  return (
    <div className="space-y-1">
      <StatusToneBadge tone={healthToTone(signal.health)}>
        {signal.label}
      </StatusToneBadge>
      {signal.detail ? (
        <p className="text-xs text-[var(--vz-text-muted)]">{signal.detail}</p>
      ) : null}
    </div>
  );
}
```

- [ ] **Step 4: Wire Settings**

In `frontend/src/pages/Settings.tsx`, import:

```tsx
import { SceneIntelligenceMatrix } from "@/components/operations/SceneIntelligenceMatrix";
import { deriveSceneReadinessRows } from "@/lib/operational-health";
import { useCameras } from "@/hooks/use-cameras";
import { useSites } from "@/hooks/use-sites";
```

Inside `SettingsPage`, add:

```tsx
  const { data: cameras = [] } = useCameras();
  const { data: sites = [] } = useSites();
```

After the error/loading guards and before the current `edge-fleet-grid`, derive:

```tsx
  const sceneHealthRows = deriveSceneReadinessRows({
    cameras,
    sites,
    fleet: fleet.data,
  });
```

Render the matrix after the `WorkspaceBand`:

```tsx
      <SceneIntelligenceMatrix rows={sceneHealthRows} />
```

- [ ] **Step 5: Update Settings tests**

In `frontend/src/pages/Settings.test.tsx`, update the `useCameras` mock or add one if missing:

```ts
vi.mock("@/hooks/use-cameras", () => ({
  useCameras: () => ({
    data: [
      {
        id: "camera-1",
        site_id: "site-1",
        name: "North Gate",
        processing_mode: "edge",
        edge_node_id: "00000000-0000-0000-0000-000000000999",
        browser_delivery: {
          default_profile: "native",
          profiles: [],
          native_status: { available: false, reason: "source_unavailable" },
        },
        source_capability: { width: 1920, height: 1080, fps: 15 },
      },
    ],
  }),
}));
```

Add assertions:

```tsx
    expect(screen.getByTestId("scene-intelligence-matrix")).toBeInTheDocument();
    expect(screen.getByText(/scene intelligence matrix/i)).toBeInTheDocument();
    expect(screen.getByText(/direct stream unavailable/i)).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /inspect delivery for north gate/i })).toHaveAttribute("href", "/settings");
```

- [ ] **Step 6: Run targeted tests**

```bash
corepack pnpm --dir frontend exec vitest run src/components/operations/SceneIntelligenceMatrix.test.tsx src/pages/Settings.test.tsx
```

Expected: PASS.

- [ ] **Step 7: Run lint and commit**

```bash
corepack pnpm --dir frontend lint
git add frontend/src/components/operations/SceneIntelligenceMatrix.tsx frontend/src/components/operations/SceneIntelligenceMatrix.test.tsx frontend/src/pages/Settings.tsx frontend/src/pages/Settings.test.tsx
git commit -m "feat(operations): add scene intelligence matrix"
```

---

## Task 4: Live Scene Status Strip

**Files:**
- Create: `frontend/src/components/operations/SceneStatusStrip.tsx`
- Create: `frontend/src/components/operations/SceneStatusStrip.test.tsx`
- Modify: `frontend/src/pages/Live.tsx`
- Modify: `frontend/src/pages/Live.test.tsx`

- [ ] **Step 1: Write the failing component tests**

Create `frontend/src/components/operations/SceneStatusStrip.test.tsx`:

```tsx
import { render, screen } from "@testing-library/react";
import { describe, expect, test } from "vitest";

import { SceneStatusStrip } from "@/components/operations/SceneStatusStrip";
import type { SceneHealthRow } from "@/lib/operational-health";

const row: SceneHealthRow = {
  cameraId: "camera-1",
  cameraName: "North Gate",
  siteName: "Zurich Lab",
  nodeLabel: "central",
  processingMode: "central",
  readiness: { health: "attention", label: "Needs attention" },
  overall: { health: "attention", label: "Telemetry stale" },
  privacy: { health: "healthy", label: "Face/plate filtering configured" },
  worker: { health: "healthy", label: "Worker running" },
  delivery: { health: "healthy", label: "Native stream available" },
  telemetry: { health: "attention", label: "Telemetry stale" },
  actionHref: "/settings",
  actionLabel: "Inspect operations",
};

describe("SceneStatusStrip", () => {
  test("renders worker stream and telemetry signals", () => {
    render(<SceneStatusStrip row={row} />);
    expect(screen.getByLabelText(/north gate operational status/i)).toBeInTheDocument();
    expect(screen.getByText(/central/i)).toBeInTheDocument();
    expect(screen.getByText(/face\/plate filtering configured/i)).toBeInTheDocument();
    expect(screen.getByText(/worker running/i)).toBeInTheDocument();
    expect(screen.getByText(/native stream available/i)).toBeInTheDocument();
    expect(screen.getByText(/telemetry stale/i)).toBeInTheDocument();
  });
});
```

- [ ] **Step 2: Run the failing component tests**

```bash
corepack pnpm --dir frontend exec vitest run src/components/operations/SceneStatusStrip.test.tsx
```

Expected: FAIL because the component does not exist.

- [ ] **Step 3: Implement `SceneStatusStrip`**

Create `frontend/src/components/operations/SceneStatusStrip.tsx`:

```tsx
import { StatusToneBadge } from "@/components/layout/workspace-surfaces";
import { healthToTone, type SceneHealthRow } from "@/lib/operational-health";

type SceneStatusStripProps = {
  row: SceneHealthRow;
};

export function SceneStatusStrip({ row }: SceneStatusStripProps) {
  return (
    <div
      aria-label={`${row.cameraName} operational status`}
      className="flex flex-wrap gap-2"
    >
      <StatusToneBadge tone="muted">
        {row.processingMode}
      </StatusToneBadge>
      <StatusToneBadge tone={healthToTone(row.privacy.health)}>
        {row.privacy.label}
      </StatusToneBadge>
      <StatusToneBadge tone={healthToTone(row.worker.health)}>
        {row.worker.label}
      </StatusToneBadge>
      <StatusToneBadge tone={healthToTone(row.delivery.health)}>
        {row.delivery.label}
      </StatusToneBadge>
      <StatusToneBadge tone={healthToTone(row.telemetry.health)}>
        {row.telemetry.label}
      </StatusToneBadge>
    </div>
  );
}
```

- [ ] **Step 4: Wire Live page**

In `frontend/src/pages/Live.tsx`, import:

```tsx
import { SceneStatusStrip } from "@/components/operations/SceneStatusStrip";
import { useFleetOverview } from "@/hooks/use-operations";
import { deriveSceneReadinessRows } from "@/lib/operational-health";
```

Inside `WorkspacePage`, add:

```tsx
  const fleet = useFleetOverview();
```

After `framesByCamera`, derive rows:

```tsx
  const sceneHealthRows = useMemo(
    () =>
      deriveSceneReadinessRows({
        cameras,
        fleet: fleet.data,
        framesByCamera,
      }),
    [cameras, fleet.data, framesByCamera],
  );
  const sceneHealthByCamera = useMemo(
    () => new Map(sceneHealthRows.map((row) => [row.cameraId, row])),
    [sceneHealthRows],
  );
```

Inside each camera tile, after the existing tracker/heartbeat badge group or below the header copy, render:

```tsx
                        {sceneHealthByCamera.get(camera.id) ? (
                          <div className="mt-3">
                            <SceneStatusStrip
                              row={sceneHealthByCamera.get(camera.id)!}
                            />
                          </div>
                        ) : null}
```

- [ ] **Step 5: Update Live tests**

In `frontend/src/pages/Live.test.tsx`, mock `useFleetOverview` if not already mocked:

```ts
vi.mock("@/hooks/use-operations", () => ({
  useFleetOverview: () => ({
    data: {
      mode: "manual_dev",
      generated_at: "2026-05-09T08:00:00Z",
      summary: {
        desired_workers: 2,
        running_workers: 2,
        stale_nodes: 0,
        offline_nodes: 0,
        native_unavailable_cameras: 0,
      },
      nodes: [],
      camera_workers: [
        {
          camera_id: "11111111-1111-1111-1111-111111111111",
          camera_name: "North Gate",
          site_id: "site-1",
          node_id: null,
          node_hostname: null,
          processing_mode: "central",
          desired_state: "manual",
          runtime_status: "running",
          lifecycle_owner: "manual_dev",
          dev_run_command: null,
          detail: null,
        },
      ],
      delivery_diagnostics: [
        {
          camera_id: "11111111-1111-1111-1111-111111111111",
          camera_name: "North Gate",
          processing_mode: "central",
          assigned_node_id: null,
          source_capability: { width: 1920, height: 1080, fps: 15 },
          default_profile: "native",
          available_profiles: [],
          native_status: { available: true, reason: null },
          selected_stream_mode: "passthrough",
        },
      ],
    },
  }),
}));
```

Add assertion to the main live wall test:

```tsx
    expect(screen.getAllByLabelText(/operational status/i).length).toBeGreaterThanOrEqual(1);
    expect(screen.getAllByText(/worker running/i).length).toBeGreaterThanOrEqual(1);
```

- [ ] **Step 6: Run targeted tests**

```bash
corepack pnpm --dir frontend exec vitest run src/components/operations/SceneStatusStrip.test.tsx src/pages/Live.test.tsx
```

Expected: PASS.

- [ ] **Step 7: Run lint and commit**

```bash
corepack pnpm --dir frontend lint
git add frontend/src/components/operations/SceneStatusStrip.tsx frontend/src/components/operations/SceneStatusStrip.test.tsx frontend/src/pages/Live.tsx frontend/src/pages/Live.test.tsx
git commit -m "feat(live): show per-scene operational status"
```

---

## Task 5: Scenes Inventory Readiness Cue

**Files:**
- Modify: `frontend/src/pages/Cameras.tsx`
- Modify: `frontend/src/pages/Cameras.test.tsx`

- [ ] **Step 1: Write the failing page test**

In `frontend/src/pages/Cameras.test.tsx`, add or extend a test so it expects a Readiness column and setup/delivery issue:

```tsx
    expect(screen.getByRole("columnheader", { name: /readiness/i })).toBeInTheDocument();
    expect(screen.getByText(/needs setup/i)).toBeInTheDocument();
```

Make sure the mocked camera or mocked fleet data includes `native_status: { available: false, reason: "source_unavailable" }`.

- [ ] **Step 2: Run the failing page test**

```bash
corepack pnpm --dir frontend exec vitest run src/pages/Cameras.test.tsx
```

Expected: FAIL because the Readiness column is not rendered yet.

- [ ] **Step 3: Wire readiness into `Cameras.tsx`**

In `frontend/src/pages/Cameras.tsx`, import:

```tsx
import { StatusToneBadge } from "@/components/layout/workspace-surfaces";
import { useFleetOverview } from "@/hooks/use-operations";
import {
  deriveSceneReadinessRows,
  healthToTone,
} from "@/lib/operational-health";
```

Inside `CamerasContent`, add:

```tsx
  const fleet = useFleetOverview();
  const sceneHealthRows = useMemo(
    () => deriveSceneReadinessRows({ cameras, fleet: fleet.data }),
    [cameras, fleet.data],
  );
  const sceneHealthByCamera = useMemo(
    () => new Map(sceneHealthRows.map((row) => [row.cameraId, row])),
    [sceneHealthRows],
  );
```

Update the table headers:

```tsx
              <TH>Readiness</TH>
```

Place it before `Actions`.

Update loading and empty `colSpan` from `6` to `7`.

Inside each camera row, before actions:

```tsx
                  <TD>
                    {sceneHealthByCamera.get(camera.id) ? (
                      <StatusToneBadge
                        tone={healthToTone(
                          sceneHealthByCamera.get(camera.id)!.readiness.health,
                        )}
                      >
                        {sceneHealthByCamera.get(camera.id)!.readiness.label}
                      </StatusToneBadge>
                    ) : (
                      <StatusToneBadge tone="muted">Readiness pending</StatusToneBadge>
                    )}
                  </TD>
```

- [ ] **Step 4: Update Cameras tests**

Mock `useFleetOverview` in `frontend/src/pages/Cameras.test.tsx` if missing:

```ts
vi.mock("@/hooks/use-operations", () => ({
  useFleetOverview: () => ({
    data: {
      mode: "manual_dev",
      generated_at: "2026-05-09T08:00:00Z",
      summary: {
        desired_workers: 1,
        running_workers: 1,
        stale_nodes: 0,
        offline_nodes: 0,
        native_unavailable_cameras: 1,
      },
      nodes: [],
      camera_workers: [
        {
          camera_id: "camera-1",
          camera_name: "Dock Camera",
          site_id: "site-1",
          node_id: null,
          node_hostname: null,
          processing_mode: "central",
          desired_state: "manual",
          runtime_status: "running",
          lifecycle_owner: "manual_dev",
          dev_run_command: null,
          detail: null,
        },
      ],
      delivery_diagnostics: [
        {
          camera_id: "camera-1",
          camera_name: "Dock Camera",
          processing_mode: "central",
          assigned_node_id: null,
          source_capability: { width: 1920, height: 1080, fps: 15 },
          default_profile: "native",
          available_profiles: [],
          native_status: { available: false, reason: "source_unavailable" },
          selected_stream_mode: "passthrough",
        },
      ],
    },
  }),
}));
```

- [ ] **Step 5: Run targeted tests**

```bash
corepack pnpm --dir frontend exec vitest run src/pages/Cameras.test.tsx
```

Expected: PASS.

- [ ] **Step 6: Run lint and commit**

```bash
corepack pnpm --dir frontend lint
git add frontend/src/pages/Cameras.tsx frontend/src/pages/Cameras.test.tsx
git commit -m "feat(scenes): add inventory readiness cue"
```

---

## Task 6: E2E Smoke And Changelog

**Files:**
- Create: `frontend/e2e/operational-readiness.spec.ts`
- Modify: `frontend/CHANGELOG.md`

- [ ] **Step 1: Add E2E smoke**

Create `frontend/e2e/operational-readiness.spec.ts`:

```ts
import { expect, test } from "@playwright/test";

test.describe("Operational readiness UI", () => {
  test("dashboard exposes deployment posture and the attention stack", async ({ page }) => {
    await page.goto("/dashboard");
    await expect(page.getByTestId("deployment-posture-strip")).toBeVisible();
    await expect(page.getByTestId("attention-stack")).toBeVisible();
    await expect(page.getByRole("heading", { name: /attention stack/i })).toBeVisible();
  });

  test("operations exposes the scene intelligence matrix", async ({ page }) => {
    await page.goto("/settings");
    await expect(page.getByTestId("scene-intelligence-matrix")).toBeVisible();
    await expect(page.getByRole("heading", { name: /scene intelligence matrix/i })).toBeVisible();
  });

  test("live and scenes keep their primary workspaces", async ({ page }) => {
    await page.goto("/live");
    await expect(page.getByTestId("live-intelligence-workspace")).toBeVisible();

    await page.goto("/cameras");
    await expect(page.getByTestId("scene-setup-workspace")).toBeVisible();
    await expect(page.getByRole("columnheader", { name: /readiness/i })).toBeVisible();
  });
});
```

- [ ] **Step 2: Document Phase 5A**

Add to the top of `frontend/CHANGELOG.md`:

```md
## Phase 5A - Operational Readiness UI

- Added a frontend-only operational readiness model that derives fleet health, deployment posture, privacy posture, scene readiness, delivery, telemetry, and evidence attention from existing APIs.
- Added a Dashboard deployment posture strip for sites, scenes, central/edge/hybrid split, privacy-configured scenes, evidence awaiting review, and fleet health.
- Added a Dashboard attention stack for pending evidence, missing workers, stale nodes, and unavailable direct streams.
- Added an Operations scene intelligence matrix, Live scene status strip, and Scenes inventory readiness cue.
- Kept WebGL off and left runtime metrics such as `capture_wait_*` for the backend-backed Phase 5B.
```

- [ ] **Step 3: Run full frontend verification**

```bash
corepack pnpm --dir frontend test
corepack pnpm --dir frontend lint
corepack pnpm --dir frontend build
corepack pnpm --dir frontend exec playwright test e2e/operational-readiness.spec.ts
```

Expected:

- unit tests pass
- lint passes with only existing warnings
- build passes
- Playwright smoke passes against the configured local dev stack

- [ ] **Step 4: Commit**

```bash
git add frontend/e2e/operational-readiness.spec.ts frontend/CHANGELOG.md
git commit -m "test(ops): cover operational readiness surfaces"
```

---

## Task 7: Final Verification And Branch Push

**Files:**
- No code changes expected.

- [ ] **Step 1: Inspect git status**

```bash
git status --short
```

Expected: only unrelated scratch files are untracked; no intended Phase 5A files are unstaged.

- [ ] **Step 2: Run final verification**

```bash
corepack pnpm --dir frontend test
corepack pnpm --dir frontend lint
corepack pnpm --dir frontend build
```

Expected: all pass. Existing warnings should be called out in the final report if they remain.

- [ ] **Step 3: Push**

```bash
git push origin codex/omnisight-ui-spec-implementation
```

Expected: push succeeds.

- [ ] **Step 4: Report**

Report:

- commit range added for Phase 5A
- verification commands and results
- any existing warnings
- confirmation that WebGL remains off and no backend API changes were made
