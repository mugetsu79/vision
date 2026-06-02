# Configuration Guidance UX Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add contextual, operational guidance to scene setup and Control Plane Configuration so operators understand each setting before saving, binding, or deploying it.

**Architecture:** Build a shared guidance content layer and reusable help components first. Then wire those primitives into the CameraWizard calibration flow and the configuration profile editor, binding panel, and effective configuration panel. Keep runtime behavior unchanged except for display-only validation/readiness messages.

**Tech Stack:** React, TypeScript, existing component primitives, Lucide icons, TanStack Query data already available in hooks, Vitest/Testing Library, existing backend capability catalog.

---

## Scope Check

This plan covers one UX system with two product surfaces:

- Scene camera setup guidance.
- Control Plane Configuration guidance.

The surfaces can be implemented by separate workers after Tasks 1 and 2 land.
Do not start Tasks 3 and 4 before the shared guidance primitives exist.

## File Structure And Ownership

Create:

- `frontend/src/components/guidance/FieldHelp.tsx`: reusable field shell with
  inline hint, details disclosure, examples, and `aria-describedby`.
- `frontend/src/components/guidance/GuidancePanel.tsx`: section-level guidance
  panel with concepts, steps, examples, warnings, and common mistakes.
- `frontend/src/components/guidance/ReadinessChecklist.tsx`: compact checklist
  for complete/warning/blocked states.
- `frontend/src/components/guidance/guidance-types.ts`: shared guidance types.
- `frontend/src/components/guidance/guidance.test.tsx`: unit tests for the
  reusable components.
- `frontend/src/components/cameras/scene-guidance.ts`: scene setup and geometry
  guidance copy.
- `frontend/src/components/configuration/configuration-guidance.ts`: profile,
  field, value, binding, and effective configuration guidance copy.

Modify:

- `frontend/src/components/cameras/CameraWizard.tsx`
- `frontend/src/components/cameras/HomographyEditor.tsx`
- `frontend/src/components/cameras/BoundaryAuthoringCanvas.tsx`
- `frontend/src/components/cameras/CameraWizard.test.tsx`
- `frontend/src/components/configuration/ProfileEditor.tsx`
- `frontend/src/components/configuration/ProfileBindingPanel.tsx`
- `frontend/src/components/configuration/EffectiveConfigurationPanel.tsx`
- `frontend/src/components/configuration/RuntimeImpactPanel.tsx`
- `frontend/src/components/configuration/ProfileEditor.test.tsx`
- `frontend/src/components/configuration/ProfileBindingPanel.test.tsx`
- `frontend/src/components/configuration/EffectiveConfigurationPanel.test.tsx`
- `frontend/src/components/configuration/ConfigurationWorkspace.test.tsx`

No backend schema change is required for the first pass.

## Task 1: Shared Guidance Content Types

**Files:**

- Create: `frontend/src/components/guidance/guidance-types.ts`
- Create: `frontend/src/components/cameras/scene-guidance.ts`
- Create: `frontend/src/components/configuration/configuration-guidance.ts`
- Test: `frontend/src/components/configuration/ProfileEditor.test.tsx`

- [ ] **Step 1: Create guidance types**

Create `frontend/src/components/guidance/guidance-types.ts`:

```ts
export type GuidanceTone = "info" | "success" | "warning" | "danger";

export type GuidanceExample = {
  label: string;
  value?: string;
  description: string;
};

export type FieldGuidance = {
  label: string;
  hint: string;
  details: string[];
  safeDefault?: string;
  examples?: GuidanceExample[];
  commonMistakes?: string[];
  runtimeEffect?: string;
  required?: boolean;
};

export type SectionGuidance = {
  eyebrow?: string;
  title: string;
  summary: string;
  concepts?: Array<{ term: string; definition: string }>;
  steps?: string[];
  examples?: GuidanceExample[];
  warnings?: string[];
  commonMistakes?: string[];
};

export type ReadinessItem = {
  id: string;
  label: string;
  detail: string;
  tone: GuidanceTone;
};
```

- [ ] **Step 2: Add scene guidance copy**

Create `frontend/src/components/cameras/scene-guidance.ts`:

```ts
import type { FieldGuidance, SectionGuidance } from "@/components/guidance/guidance-types";

export const SCENE_STEP_GUIDANCE: Record<string, SectionGuidance> = {
  Identity: {
    eyebrow: "Scene setup",
    title: "Identify where this camera runs",
    summary:
      "Name the camera, choose the site, and decide whether inference runs centrally, at the edge, or in a hybrid path.",
    concepts: [
      {
        term: "Camera source",
        definition: "The RTSP stream or USB device that provides frames to the analytics pipeline.",
      },
      {
        term: "Processing mode",
        definition: "Where the worker performs inference for this camera.",
      },
    ],
    examples: [
      {
        label: "Central",
        description: "Start here when the master can reliably pull the RTSP stream.",
      },
      {
        label: "Edge",
        description: "Use for USB capture, weak uplink, or privacy-sensitive sites.",
      },
      {
        label: "Hybrid",
        description: "Use when an edge node runs local inference but central services may consume results.",
      },
    ],
  },
  Calibration: {
    eyebrow: "Geometry",
    title: "Map the camera image to operational space",
    summary:
      "Use source and destination points to calibrate perspective, then draw boundaries and detection masks on the same analytics frame.",
    steps: [
      "Confirm the still image matches the camera view.",
      "Place four source points on stable ground-plane reference marks in the camera image.",
      "Place four destination points in the same order on the top-down plane.",
      "Enter a known reference distance in meters.",
      "Draw line boundaries or polygon zones for events.",
      "Add include or exclusion regions only when detector attention needs masking.",
    ],
  },
};

export const SCENE_FIELD_GUIDANCE: Record<string, FieldGuidance> = {
  sourcePoints: {
    label: "Source points",
    hint: "Points on the camera image that identify the real-world reference plane.",
    details: [
      "Use four stable points on the floor, ground, lane, doorway, or loading bay.",
      "Avoid shadows, moving objects, vertical walls, and temporary equipment.",
      "Use the same point order as destination points.",
    ],
    safeDefault: "Four corners of a visible rectangular ground-plane area.",
    runtimeEffect:
      "Completed source and destination points allow distance, direction, and speed features to trust the camera perspective.",
  },
  destinationPoints: {
    label: "Destination points",
    hint: "Matching points on an abstract top-down world plane.",
    details: [
      "They represent the same real-world marks as the source points.",
      "They do not need to be GPS coordinates.",
      "Keep the point order identical to source points.",
    ],
    safeDefault: "A simple rectangle with the same corner order as the source plane.",
  },
  referenceDistance: {
    label: "Reference distance",
    hint: "A known real-world distance in meters between reference marks.",
    details: [
      "Measure a visible lane width, doorway width, floor marking, or loading-bay span.",
      "Use meters so downstream distance and speed logic uses consistent units.",
    ],
    safeDefault: "A measured distance, not an estimate, whenever speed or distance is important.",
  },
  eventBoundaries: {
    label: "Event boundaries",
    hint: "Lines emit crossing events; polygon zones emit enter and exit events.",
    details: [
      "Use line boundaries for directional counts through doors, lanes, gates, and thresholds.",
      "Use polygon zones for restricted areas, occupancy areas, staging areas, and dwell regions.",
    ],
  },
  detectionRegions: {
    label: "Detection regions",
    hint: "Include regions keep detections inside; exclusion regions suppress detections inside.",
    details: [
      "Use include regions to focus detection on the operational area.",
      "Use exclusion regions to ignore reflections, screens, public roads, or background motion.",
      "Detection regions are applied before event boundaries are evaluated.",
    ],
  },
};
```

- [ ] **Step 3: Add configuration guidance copy**

Create `frontend/src/components/configuration/configuration-guidance.ts`:

```ts
import type {
  FieldGuidance,
  SectionGuidance,
} from "@/components/guidance/guidance-types";
import type { OperatorConfigKind } from "@/hooks/use-configuration";

export const PROFILE_KIND_GUIDANCE: Record<OperatorConfigKind, SectionGuidance> = {
  evidence_storage: {
    eyebrow: "Evidence",
    title: "Choose where incident evidence is written",
    summary:
      "Evidence storage profiles decide whether event clips and snapshots write locally, centrally, to object storage, or through a local-first path.",
    commonMistakes: [
      "Selecting cloud storage without bucket credentials.",
      "Choosing a storage scope that conflicts with the privacy residency policy.",
      "Expecting this profile to enable continuous recording; camera recording policy controls event clips.",
    ],
  },
  stream_delivery: {
    eyebrow: "Live transport",
    title: "Choose how browsers reach live streams",
    summary:
      "Transport profiles control the stream route. Camera live rendition controls clean, annotated, or reduced video quality.",
    commonMistakes: [
      "Using localhost in a public base URL when operators connect from another machine.",
      "Selecting WebRTC when UDP 8189 is blocked.",
      "Expecting transport profile to change resolution or FPS.",
    ],
  },
  runtime_selection: {
    eyebrow: "Inference runtime",
    title: "Rank model runtimes and fallback behavior",
    summary:
      "Runtime selection profiles tell workers which backend and artifact family to prefer before starting inference.",
    commonMistakes: [
      "Disabling fallback before a valid TensorRT artifact exists.",
      "Choosing TensorRT-first on hardware with no compatible engine.",
    ],
  },
  privacy_policy: {
    eyebrow: "Privacy and retention",
    title: "Set residency, retention, and sensitive text posture",
    summary:
      "Privacy policies protect evidence lifecycle and decide where sensitive outputs may live.",
    commonMistakes: [
      "Using cloud residency for an edge-only privacy-sensitive site.",
      "Setting retention shorter than the review workflow needs.",
    ],
  },
  llm_provider: {
    eyebrow: "Policy assistance",
    title: "Configure policy draft assistance",
    summary:
      "LLM provider profiles power policy drafting. They do not affect detector inference or scene telemetry.",
    commonMistakes: [
      "Omitting base URL for local/custom providers.",
      "Expecting this setting to change model detection behavior.",
    ],
  },
  operations_mode: {
    eyebrow: "Lifecycle",
    title: "Decide who owns worker lifecycle",
    summary:
      "Operations mode profiles control whether workers are manual, supervisor-managed, polling, push-driven, and restartable.",
    commonMistakes: [
      "Selecting edge supervisor for a camera without an edge node.",
      "Selecting push while the supporting dispatch service is unavailable.",
      "Using always restart during manual debugging.",
    ],
  },
};

export const PROFILE_FIELD_GUIDANCE: Record<OperatorConfigKind, Record<string, FieldGuidance>> = {
  evidence_storage: {
    provider: {
      label: "Provider",
      hint: "Storage technology used for incident evidence.",
      details: [
        "MinIO is the default appliance object store.",
        "S3-compatible is for external object stores.",
        "Local filesystem is useful for simple edge-local evidence paths.",
        "Local first writes locally before central or cloud movement.",
      ],
      safeDefault: "MinIO for the portable master appliance.",
      runtimeEffect: "Incident capture uses this provider when writing clips and snapshots.",
    },
    storage_scope: {
      label: "Storage scope",
      hint: "Where evidence should live first: edge, central, cloud, or local-first.",
      details: ["Match this to privacy residency and network reliability."],
      safeDefault: "Central for a single MacBook master test build.",
    },
    endpoint: {
      label: "Endpoint",
      hint: "Object-store host and port for MinIO or S3-compatible storage.",
      details: ["Use a network-reachable endpoint from the backend container or worker."],
    },
    bucket: {
      label: "Bucket",
      hint: "Object-store bucket where evidence objects are written.",
      details: ["Use a dedicated bucket or prefix for OmniSight evidence."],
    },
  },
  stream_delivery: {
    delivery_mode: {
      label: "Transport mode",
      hint: "How the browser connects to live video.",
      details: [
        "Native/direct keeps clean passthrough when available.",
        "WebRTC is low latency but requires reachable WebRTC hosts and UDP.",
        "HLS is resilient and easier across networks, with higher latency.",
        "MJPEG is a compatibility fallback and can use more bandwidth.",
      ],
      safeDefault: "Native/direct for normal appliance testing.",
    },
    public_base_url: {
      label: "Public base URL",
      hint: "Browser-facing stream base URL when a direct route is required.",
      details: ["Do not use localhost when operators connect from another machine."],
    },
    edge_override_url: {
      label: "Edge override URL",
      hint: "Edge-specific stream host override for remote or routed edge nodes.",
      details: ["Use when an edge node publishes streams through a dedicated IP, DNS name, or forwarded port."],
    },
  },
  runtime_selection: {
    preferred_backend: {
      label: "Preferred backend",
      hint: "Runtime backend workers should try first.",
      details: ["Auto lets the worker pick the best compatible backend."],
      safeDefault: "Auto until validated artifacts exist.",
    },
    artifact_preference: {
      label: "Artifact preference",
      hint: "Order for compiled and portable model artifacts.",
      details: ["TensorRT first is fastest on compatible NVIDIA targets when a valid engine exists."],
      safeDefault: "TensorRT first on Jetson after artifact validation; ONNX first for portability.",
    },
    fallback_allowed: {
      label: "Allow fallback",
      hint: "Permit a compatible slower runtime if the preferred runtime is unavailable.",
      details: ["Disable only when you want startup to fail instead of silently degrading."],
      safeDefault: "Enabled during setup and validation.",
    },
  },
  privacy_policy: {
    retention_days: {
      label: "Retention days",
      hint: "How long evidence remains eligible for storage.",
      details: ["Set this longer than the expected review and export window."],
      safeDefault: "30 days for test builds.",
    },
    storage_quota_bytes: {
      label: "Storage quota",
      hint: "Maximum evidence storage budget.",
      details: ["Display bytes as GB/TB in the UI so operators can reason about capacity."],
      safeDefault: "10 GB for a small test build.",
    },
    plaintext_plate_storage: {
      label: "Plaintext plate posture",
      hint: "Whether unredacted license plate text may be stored.",
      details: ["Blocked is safest unless a site has explicit permission to retain plaintext plate data."],
      safeDefault: "Blocked.",
    },
    residency: {
      label: "Residency guardrail",
      hint: "Where sensitive evidence is allowed to live.",
      details: ["Choose edge or local-first when privacy or bandwidth requires local handling."],
      safeDefault: "Central for controlled local tests; edge/local-first for privacy-sensitive sites.",
    },
  },
  llm_provider: {
    provider: {
      label: "Provider",
      hint: "Service used for policy draft assistance.",
      details: ["This does not change detector inference."],
    },
    model: {
      label: "Model",
      hint: "Provider model used for drafting policy text.",
      details: ["Use a model name that exists at the configured provider."],
    },
    base_url: {
      label: "Base URL",
      hint: "Endpoint for local or custom LLM-compatible providers.",
      details: ["Leave empty only when the provider uses its default hosted endpoint."],
    },
    api_key: {
      label: "API key",
      hint: "Write-only credential for the provider.",
      details: ["Saved keys are shown as stored, never redisplayed."],
    },
  },
  operations_mode: {
    lifecycle_owner: {
      label: "Lifecycle owner",
      hint: "Who owns start, stop, and restart behavior for workers.",
      details: [
        "Manual means OmniSight observes but does not own lifecycle.",
        "Edge supervisor owns local edge workers.",
        "Central supervisor owns central workers.",
      ],
      safeDefault: "Edge supervisor for Jetson-assigned cameras; manual for debugging.",
    },
    supervisor_mode: {
      label: "Supervisor mode",
      hint: "How lifecycle intent reaches the supervisor.",
      details: [
        "Disabled blocks automated lifecycle actions.",
        "Polling lets the supervisor periodically reconcile desired state.",
        "Push dispatches lifecycle requests immediately when the service is available.",
      ],
      safeDefault: "Polling for appliance tests.",
    },
    restart_policy: {
      label: "Restart policy",
      hint: "Recovery behavior after worker exit or failure.",
      details: [
        "Never leaves stopped workers stopped.",
        "On failure restarts after crashes or unhealthy exits.",
        "Always restarts even after intentional exits.",
      ],
      safeDefault: "On failure.",
    },
  },
};
```

- [ ] **Step 4: Write a failing copy coverage test**

Add this test to `frontend/src/components/configuration/ProfileEditor.test.tsx`:

```ts
import {
  PROFILE_FIELD_GUIDANCE,
  PROFILE_KIND_GUIDANCE,
} from "@/components/configuration/configuration-guidance";
import { CONFIGURATION_KINDS } from "@/components/configuration/configuration-copy";

test("configuration guidance covers every profile kind", () => {
  for (const kind of CONFIGURATION_KINDS) {
    expect(PROFILE_KIND_GUIDANCE[kind].title).toBeTruthy();
    expect(Object.keys(PROFILE_FIELD_GUIDANCE[kind]).length).toBeGreaterThan(0);
  }
});
```

- [ ] **Step 5: Run the failing copy coverage test**

Run:

```bash
corepack pnpm --dir frontend test src/components/configuration/ProfileEditor.test.tsx -t "configuration guidance covers every profile kind"
```

Expected: PASS after the files exist. If imports fail, fix the paths before
continuing.

## Task 2: Reusable Guidance Components

**Files:**

- Create: `frontend/src/components/guidance/FieldHelp.tsx`
- Create: `frontend/src/components/guidance/GuidancePanel.tsx`
- Create: `frontend/src/components/guidance/ReadinessChecklist.tsx`
- Create: `frontend/src/components/guidance/guidance.test.tsx`

- [ ] **Step 1: Add component tests**

Create `frontend/src/components/guidance/guidance.test.tsx`:

```tsx
import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { FieldHelp } from "@/components/guidance/FieldHelp";
import { GuidancePanel } from "@/components/guidance/GuidancePanel";
import { ReadinessChecklist } from "@/components/guidance/ReadinessChecklist";

test("FieldHelp exposes inline hint and expandable details", async () => {
  const user = userEvent.setup();
  render(
    <FieldHelp
      id="transport-mode-help"
      guidance={{
        label: "Transport mode",
        hint: "How the browser connects to live video.",
        details: ["WebRTC is low latency.", "HLS is resilient."],
        safeDefault: "Native/direct",
      }}
    />,
  );

  expect(screen.getByText("How the browser connects to live video.")).toBeInTheDocument();
  await user.click(screen.getByRole("button", { name: /show details for transport mode/i }));
  expect(screen.getByText("WebRTC is low latency.")).toBeInTheDocument();
  expect(screen.getByText(/safe default/i)).toBeInTheDocument();
});

test("GuidancePanel renders steps and common mistakes", () => {
  render(
    <GuidancePanel
      guidance={{
        eyebrow: "Geometry",
        title: "Map the camera image",
        summary: "Use matching source and destination points.",
        steps: ["Confirm the still.", "Place source points."],
        commonMistakes: ["Mixing point order."],
      }}
    />,
  );

  expect(screen.getByRole("heading", { name: "Map the camera image" })).toBeInTheDocument();
  expect(screen.getByText("Place source points.")).toBeInTheDocument();
  expect(screen.getByText("Mixing point order.")).toBeInTheDocument();
});

test("ReadinessChecklist renders status rows", () => {
  render(
    <ReadinessChecklist
      items={[
        { id: "source", label: "Source", detail: "Still ready", tone: "success" },
        { id: "geometry", label: "Geometry", detail: "Needs destination points", tone: "warning" },
      ]}
    />,
  );

  const list = screen.getByRole("list", { name: /readiness/i });
  expect(within(list).getByText("Source")).toBeInTheDocument();
  expect(within(list).getByText("Needs destination points")).toBeInTheDocument();
});
```

- [ ] **Step 2: Run tests to verify failure**

Run:

```bash
corepack pnpm --dir frontend test src/components/guidance/guidance.test.tsx
```

Expected: FAIL because the components do not exist.

- [ ] **Step 3: Implement `FieldHelp`**

Create `frontend/src/components/guidance/FieldHelp.tsx`:

```tsx
import { useState } from "react";
import { Info } from "lucide-react";
import type { FieldGuidance } from "@/components/guidance/guidance-types";

type FieldHelpProps = {
  id: string;
  guidance: FieldGuidance;
};

export function FieldHelp({ id, guidance }: FieldHelpProps) {
  const [open, setOpen] = useState(false);
  return (
    <div id={id} className="space-y-2 text-xs text-[#9fb2cf]">
      <div className="flex items-start gap-2">
        <p className="leading-5">{guidance.hint}</p>
        <button
          type="button"
          className="inline-flex size-6 shrink-0 items-center justify-center rounded-full border border-white/10 text-[#8fd3ff] transition hover:bg-white/[0.06] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#8fd3ff]"
          aria-expanded={open}
          aria-controls={`${id}-details`}
          aria-label={`Show details for ${guidance.label}`}
          onClick={() => setOpen((current) => !current)}
        >
          <Info className="size-3.5" />
        </button>
      </div>
      {open ? (
        <div id={`${id}-details`} className="rounded-lg border border-white/10 bg-[#07101b] p-3">
          <ul className="grid gap-1">
            {guidance.details.map((detail) => (
              <li key={detail}>{detail}</li>
            ))}
          </ul>
          {guidance.safeDefault ? (
            <p className="mt-2 text-[#d8e2f2]">
              <span className="font-semibold">Safe default:</span> {guidance.safeDefault}
            </p>
          ) : null}
          {guidance.runtimeEffect ? (
            <p className="mt-2">
              <span className="font-semibold text-[#d8e2f2]">Runtime effect:</span>{" "}
              {guidance.runtimeEffect}
            </p>
          ) : null}
        </div>
      ) : null}
    </div>
  );
}
```

- [ ] **Step 4: Implement `GuidancePanel`**

Create `frontend/src/components/guidance/GuidancePanel.tsx`:

```tsx
import type { SectionGuidance } from "@/components/guidance/guidance-types";

type GuidancePanelProps = {
  guidance: SectionGuidance;
};

export function GuidancePanel({ guidance }: GuidancePanelProps) {
  return (
    <aside className="rounded-lg border border-white/10 bg-[#07101b] p-4">
      {guidance.eyebrow ? (
        <p className="text-[11px] font-semibold uppercase tracking-[0.18em] text-[#7894bd]">
          {guidance.eyebrow}
        </p>
      ) : null}
      <h3 className="mt-2 text-sm font-semibold text-[#f4f8ff]">{guidance.title}</h3>
      <p className="mt-2 text-xs leading-5 text-[#9fb2cf]">{guidance.summary}</p>
      {guidance.steps?.length ? (
        <ol className="mt-3 grid gap-1 text-xs leading-5 text-[#d8e2f2]">
          {guidance.steps.map((step, index) => (
            <li key={step}>
              <span className="mr-2 text-[#8fd3ff]">{index + 1}.</span>
              {step}
            </li>
          ))}
        </ol>
      ) : null}
      {guidance.commonMistakes?.length ? (
        <div className="mt-3 rounded-lg border border-amber-300/20 bg-amber-950/20 p-3">
          <p className="text-xs font-semibold text-amber-100">Common mistakes</p>
          <ul className="mt-2 grid gap-1 text-xs leading-5 text-amber-100/85">
            {guidance.commonMistakes.map((mistake) => (
              <li key={mistake}>{mistake}</li>
            ))}
          </ul>
        </div>
      ) : null}
    </aside>
  );
}
```

- [ ] **Step 5: Implement `ReadinessChecklist`**

Create `frontend/src/components/guidance/ReadinessChecklist.tsx`:

```tsx
import type { ReadinessItem } from "@/components/guidance/guidance-types";

const TONE_CLASS: Record<ReadinessItem["tone"], string> = {
  info: "border-sky-300/20 bg-sky-950/20 text-sky-100",
  success: "border-emerald-300/20 bg-emerald-950/20 text-emerald-100",
  warning: "border-amber-300/20 bg-amber-950/20 text-amber-100",
  danger: "border-rose-300/20 bg-rose-950/20 text-rose-100",
};

export function ReadinessChecklist({ items }: { items: ReadinessItem[] }) {
  if (items.length === 0) {
    return null;
  }
  return (
    <ul aria-label="Readiness checklist" className="grid gap-2">
      {items.map((item) => (
        <li key={item.id} className={`rounded-lg border px-3 py-2 ${TONE_CLASS[item.tone]}`}>
          <p className="text-xs font-semibold">{item.label}</p>
          <p className="mt-1 text-xs leading-5 opacity-85">{item.detail}</p>
        </li>
      ))}
    </ul>
  );
}
```

- [ ] **Step 6: Run guidance component tests**

Run:

```bash
corepack pnpm --dir frontend test src/components/guidance/guidance.test.tsx
```

Expected: PASS.

## Task 3: Scene Setup Guidance

**Files:**

- Modify: `frontend/src/components/cameras/CameraWizard.tsx`
- Modify: `frontend/src/components/cameras/HomographyEditor.tsx`
- Modify: `frontend/src/components/cameras/BoundaryAuthoringCanvas.tsx`
- Modify: `frontend/src/components/cameras/CameraWizard.test.tsx`

- [ ] **Step 1: Add failing CameraWizard guidance test**

Add to `frontend/src/components/cameras/CameraWizard.test.tsx`:

```tsx
test("calibration explains source, destination, boundaries, and detection regions", async () => {
  const user = userEvent.setup();
  renderWizard();

  await user.click(screen.getByRole("button", { name: /next/i }));
  await user.click(screen.getByRole("button", { name: /next/i }));
  await user.click(screen.getByRole("button", { name: /next/i }));

  expect(screen.getByText(/map the camera image to operational space/i)).toBeInTheDocument();
  expect(screen.getByText(/source points/i)).toBeInTheDocument();
  expect(screen.getByText(/destination points/i)).toBeInTheDocument();
  expect(screen.getByText(/line boundaries/i)).toBeInTheDocument();
  expect(screen.getByText(/include or exclusion regions/i)).toBeInTheDocument();
});
```

Use the existing test helper name in this file. If the helper has a different
name, adapt only the render call and keep the assertions.

- [ ] **Step 2: Run failing CameraWizard test**

Run:

```bash
corepack pnpm --dir frontend test src/components/cameras/CameraWizard.test.tsx -t "calibration explains source"
```

Expected: FAIL because the guidance panel is not rendered yet.

- [ ] **Step 3: Render step guidance panel**

In `CameraWizard.tsx`, import:

```ts
import { GuidancePanel } from "@/components/guidance/GuidancePanel";
import { ReadinessChecklist } from "@/components/guidance/ReadinessChecklist";
import { SCENE_STEP_GUIDANCE } from "@/components/cameras/scene-guidance";
import type { ReadinessItem } from "@/components/guidance/guidance-types";
```

Add a memo near `stepTitle`:

```ts
const stepGuidance = SCENE_STEP_GUIDANCE[stepTitle];
```

In the right summary column, render:

```tsx
{stepGuidance ? <GuidancePanel guidance={stepGuidance} /> : null}
```

Place it above `CameraStepSummary` so the current task is explained before the
final review summary.

- [ ] **Step 4: Add calibration readiness items**

Add this helper inside `CameraWizard.tsx`:

```ts
function calibrationReadinessItems(data: CameraWizardData): ReadinessItem[] {
  const items: ReadinessItem[] = [];
  items.push({
    id: "source-points",
    label: "Source points",
    detail:
      data.homography.src.length === 4
        ? "Four camera-image source points are set."
        : `${data.homography.src.length} of 4 source points set.`,
    tone: data.homography.src.length === 4 ? "success" : "warning",
  });
  items.push({
    id: "destination-points",
    label: "Destination points",
    detail:
      data.homography.dst.length === 4
        ? "Four matching top-down destination points are set."
        : `${data.homography.dst.length} of 4 destination points set.`,
    tone: data.homography.dst.length === 4 ? "success" : "warning",
  });
  items.push({
    id: "reference-distance",
    label: "Reference distance",
    detail:
      data.homography.refDistanceM > 0
        ? `${data.homography.refDistanceM} m reference distance set.`
        : "Add a measured distance in meters before trusting speed or distance.",
    tone: data.homography.refDistanceM > 0 ? "success" : "warning",
  });
  items.push({
    id: "detection-regions",
    label: "Detection regions",
    detail:
      data.detectionRegions.length > 0
        ? `${data.detectionRegions.length} detector mask region configured.`
        : "No include or exclusion regions; detector considers the full frame.",
    tone: "info",
  });
  return items;
}
```

Render it when `stepTitle === "Calibration"`:

```tsx
<ReadinessChecklist items={calibrationReadinessItems(data)} />
```

- [ ] **Step 5: Wire field guidance into HomographyEditor**

In `HomographyEditor.tsx`, import:

```ts
import { FieldHelp } from "@/components/guidance/FieldHelp";
import { SCENE_FIELD_GUIDANCE } from "@/components/cameras/scene-guidance";
```

Render `FieldHelp` under the source points heading:

```tsx
<FieldHelp id="source-points-help" guidance={SCENE_FIELD_GUIDANCE.sourcePoints} />
```

Render under the destination points heading:

```tsx
<FieldHelp id="destination-points-help" guidance={SCENE_FIELD_GUIDANCE.destinationPoints} />
```

Render under the reference distance input:

```tsx
<FieldHelp id="reference-distance-help" guidance={SCENE_FIELD_GUIDANCE.referenceDistance} />
```

- [ ] **Step 6: Add boundary and region field guidance**

In `CameraWizard.tsx`, import `FieldHelp` and `SCENE_FIELD_GUIDANCE`.

In the Event boundaries section, render:

```tsx
<FieldHelp id="event-boundaries-help" guidance={SCENE_FIELD_GUIDANCE.eventBoundaries} />
```

In the Detection regions section, render:

```tsx
<FieldHelp id="detection-regions-help" guidance={SCENE_FIELD_GUIDANCE.detectionRegions} />
```

- [ ] **Step 7: Improve canvas text equivalents**

In `BoundaryAuthoringCanvas.tsx`, add a visible status line under helper text:

```tsx
<p className="text-xs text-[#8ea4c7]">
  {value.length} {value.length === 1 ? "point" : "points"} placed
  {Number.isFinite(pointLimit) ? ` of ${pointLimit}` : ""}. Click the canvas to add points; drag numbered handles to adjust.
</p>
```

This gives keyboard and screen-reader users a persistent text summary.

- [ ] **Step 8: Run CameraWizard tests**

Run:

```bash
corepack pnpm --dir frontend test src/components/cameras/CameraWizard.test.tsx
```

Expected: PASS.

## Task 4: Control Plane Configuration Guidance

**Files:**

- Modify: `frontend/src/components/configuration/ProfileEditor.tsx`
- Modify: `frontend/src/components/configuration/ProfileBindingPanel.tsx`
- Modify: `frontend/src/components/configuration/EffectiveConfigurationPanel.tsx`
- Modify: `frontend/src/components/configuration/RuntimeImpactPanel.tsx`
- Modify: `frontend/src/components/configuration/ProfileEditor.test.tsx`
- Modify: `frontend/src/components/configuration/ProfileBindingPanel.test.tsx`
- Modify: `frontend/src/components/configuration/EffectiveConfigurationPanel.test.tsx`

- [ ] **Step 1: Add failing ProfileEditor guidance test**

Add to `ProfileEditor.test.tsx`:

```tsx
test("renders guidance for each configuration kind", () => {
  for (const kind of CONFIGURATION_KINDS) {
    const { unmount } = render(
      <ProfileEditor kind={kind} selectedProfile={null} onSave={vi.fn()} />,
    );
    expect(screen.getByText(PROFILE_KIND_GUIDANCE[kind].title)).toBeInTheDocument();
    expect(screen.getByText(PROFILE_KIND_GUIDANCE[kind].summary)).toBeInTheDocument();
    unmount();
  }
});
```

Import `PROFILE_KIND_GUIDANCE` from `configuration-guidance`.

- [ ] **Step 2: Run failing ProfileEditor guidance test**

Run:

```bash
corepack pnpm --dir frontend test src/components/configuration/ProfileEditor.test.tsx -t "renders guidance for each configuration kind"
```

Expected: FAIL until the guidance panel is rendered.

- [ ] **Step 3: Render profile kind guidance**

In `ProfileEditor.tsx`, import:

```ts
import { FieldHelp } from "@/components/guidance/FieldHelp";
import { GuidancePanel } from "@/components/guidance/GuidancePanel";
import {
  PROFILE_FIELD_GUIDANCE,
  PROFILE_KIND_GUIDANCE,
} from "@/components/configuration/configuration-guidance";
```

After the editor header, render:

```tsx
<GuidancePanel guidance={PROFILE_KIND_GUIDANCE[state.kind]} />
```

- [ ] **Step 4: Replace `Field` with guidance-aware field shell**

Change `Field` signature in `ProfileEditor.tsx`:

```tsx
function Field({
  label,
  help,
  children,
}: {
  label: string;
  help?: FieldGuidance;
  children: ReactNode;
}) {
  const helpId = help ? `${label.toLowerCase().replace(/[^a-z0-9]+/g, "-")}-help` : undefined;
  return (
    <label className="flex flex-col gap-1 text-sm font-medium text-[#d8e2f2]">
      {label}
      {children}
      {help && helpId ? <FieldHelp id={helpId} guidance={help} /> : null}
    </label>
  );
}
```

Import `type FieldGuidance`.

- [ ] **Step 5: Attach field guidance to Evidence and Transport fields**

Use:

```tsx
const guidance = PROFILE_FIELD_GUIDANCE[state.kind];
```

Pass `help={guidance.provider}` to Provider, `help={guidance.storage_scope}` to
Storage scope, `help={guidance.endpoint}` to Endpoint, `help={guidance.bucket}`
to Bucket, `help={guidance.delivery_mode}` to Transport mode,
`help={guidance.public_base_url}` to Public base URL, and
`help={guidance.edge_override_url}` to Edge override URL.

- [ ] **Step 6: Attach field guidance to Runtime, Privacy, LLM, and Operations**

Pass matching help objects for:

- `preferred_backend`
- `artifact_preference`
- `fallback_allowed`
- `retention_days`
- `storage_quota_bytes`
- `plaintext_plate_storage`
- `residency`
- `provider`
- `model`
- `base_url`
- `api_key`
- `lifecycle_owner`
- `supervisor_mode`
- `restart_policy`

For checkbox labels, render `FieldHelp` directly below the checkbox row.

- [ ] **Step 7: Add binding precedence guidance test**

Add to `ProfileBindingPanel.test.tsx`:

```tsx
test("explains binding precedence before binding", () => {
  render(
    <ProfileBindingPanel
      kind="operations_mode"
      profiles={profiles}
      bindings={[]}
      cameras={[{ id: "camera-1", label: "Dock camera" }]}
      sites={[{ id: "site-1", label: "Dock" }]}
      edgeNodes={[{ id: "edge-1", label: "Jetson" }]}
      onBind={vi.fn()}
    />,
  );

  expect(screen.getByText(/camera binding wins/i)).toBeInTheDocument();
  expect(screen.getByText(/tenant default is the fallback/i)).toBeInTheDocument();
});
```

- [ ] **Step 8: Render binding guidance**

In `ProfileBindingPanel.tsx`, add a compact guidance callout above the binding
form:

```tsx
<div className="rounded-lg border border-white/10 bg-[#07101b] px-3 py-3 text-xs leading-5 text-[#9fb2cf]">
  <p>
    Camera binding wins, then edge node, then site. Tenant default is the fallback.
  </p>
  <p className="mt-1">
    Test profiles before binding; workers apply the resolved profile after their next config refresh or lifecycle action.
  </p>
</div>
```

- [ ] **Step 9: Add effective configuration explanation test**

Add to `EffectiveConfigurationPanel.test.tsx`:

```tsx
test("explains desired and runtime applied configuration states", () => {
  render(<EffectiveConfigurationPanel cameras={cameras} catalog={catalog} />);

  expect(screen.getByText(/desired configuration/i)).toBeInTheDocument();
  expect(screen.getByText(/runtime-applied hash/i)).toBeInTheDocument();
});
```

- [ ] **Step 10: Render effective configuration explanation**

In `EffectiveConfigurationPanel.tsx`, add an intro callout near the heading:

```tsx
<p className="text-xs leading-5 text-[#9fb2cf]">
  Desired configuration is the profile set resolved by binding precedence. Runtime-applied hash shows what a worker has actually reported. A mismatch means the UI has saved intent that the runtime has not applied yet.
</p>
```

- [ ] **Step 11: Run configuration tests**

Run:

```bash
corepack pnpm --dir frontend test \
  src/components/configuration/ProfileEditor.test.tsx \
  src/components/configuration/ProfileBindingPanel.test.tsx \
  src/components/configuration/EffectiveConfigurationPanel.test.tsx \
  src/components/configuration/ConfigurationWorkspace.test.tsx
```

Expected: PASS.

## Task 5: Visual Polish And Regression Checks

**Files:**

- Modify: `frontend/src/components/guidance/*.tsx`
- Modify only if needed: `frontend/src/index.css`

- [ ] **Step 1: Check text density in desktop and mobile**

Run the app locally and inspect Settings -> Configuration and Scenes -> Camera
setup at:

- 375 px width
- 768 px width
- 1440 px width

Confirm:

- guidance does not push primary controls below the fold excessively
- detailed content is collapsed by default where sections become long
- no button text wraps awkwardly
- no cards are nested inside decorative cards beyond existing repeated item
  patterns

- [ ] **Step 2: Confirm keyboard and screen-reader basics**

Manually verify:

- Tab reaches info buttons.
- Enter/Space opens and closes details.
- Inline help is visible without hover.
- Canvas point count is visible as text.

- [ ] **Step 3: Run focused frontend tests**

Run:

```bash
corepack pnpm --dir frontend test \
  src/components/guidance/guidance.test.tsx \
  src/components/cameras/CameraWizard.test.tsx \
  src/components/configuration/ProfileEditor.test.tsx \
  src/components/configuration/ProfileBindingPanel.test.tsx \
  src/components/configuration/EffectiveConfigurationPanel.test.tsx \
  src/components/configuration/ConfigurationWorkspace.test.tsx
```

Expected: PASS.

- [ ] **Step 4: Run frontend build**

Run:

```bash
corepack pnpm --dir frontend build
```

Expected: PASS.

## Completion Criteria

- Scene camera setup explains source/destination geometry, reference distance,
  event boundaries, include regions, and exclusion regions in the UI.
- Control Plane Configuration explains every profile kind and every visible
  field with operational consequences.
- Binding precedence and effective configuration desired/applied state are
  visible near the relevant controls.
- Tests cover guidance presence for scenes and configuration profiles.
- Frontend build passes.
