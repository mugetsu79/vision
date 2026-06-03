# Configuration Guidance Progressive Disclosure Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace heavy always-visible configuration guidance with compact info affordances and add an accessible calibration visual explainer.

**Architecture:** Introduce a reusable guidance disclosure component that renders a circular `i` trigger and an on-demand detail panel. Reuse the existing guidance data, move field help into labels, and add a lightweight SVG/CSS calibration illustration for source/destination points, measured distance, boundaries, and regions. Keep runtime semantics unchanged.

**Tech Stack:** React, TypeScript, Vitest, Testing Library, Lucide React, Tailwind utility classes, existing OmniSight guidance data.

**Implementation Status:** Implemented on `codex/guidance-progressive-disclosure`.
The detailed checklist below remains as the execution recipe; the current branch
contains the reusable disclosure, calibration illustration, Scene setup
integration, Control Plane Configuration integration, focused tests, and build
verification. Commit/push is intentionally left as the final integration step.

---

## Scope Check

This plan covers one focused UX correction:

- compact progressive disclosure for guidance
- calibration visual explanation
- Scene setup integration
- Control Plane Configuration integration
- focused frontend tests and build

It does not include broader visual redesign, runtime behavior changes, backend
schema changes, or new generated media assets.

## File Structure And Ownership

Create:

- `frontend/src/components/guidance/GuidanceDisclosure.tsx`: reusable circular
  info trigger and on-demand panel for field and section guidance.
- `frontend/src/components/guidance/CalibrationFlowIllustration.tsx`: reusable
  SVG/CSS explanation for source points, destination points, measured distance,
  event boundaries, and detection regions.

Modify:

- `frontend/src/components/guidance/FieldHelp.tsx`: turn existing field help
  into a compatibility wrapper around `GuidanceDisclosure`.
- `frontend/src/components/guidance/GuidancePanel.tsx`: leave unchanged unless
  no imports remain after direct consumers move to `GuidanceDisclosure`.
- `frontend/src/components/guidance/guidance.test.tsx`: tests for compact help,
  Escape close, and calibration illustration.
- `frontend/src/index.css`: reduced-motion-safe calibration connector
  animation.
- `frontend/src/components/cameras/CameraWizard.tsx`: replace visible step
  guidance and speed-accuracy card with compact info triggers; keep readiness
  checklist visible.
- `frontend/src/components/cameras/HomographyEditor.tsx`: move source,
  destination, and reference-distance help into label/header info triggers.
- `frontend/src/components/cameras/CameraWizard.test.tsx`: assert calibration
  guidance is compact and visual help opens.
- `frontend/src/components/configuration/ProfileEditor.tsx`: replace top
  guidance panel and field help rows with label-row info triggers.
- `frontend/src/components/configuration/ProfileEditor.test.tsx`: assert profile
  guidance opens on demand.
- `frontend/src/components/configuration/ProfileBindingPanel.tsx`: move scope
  explanation behind section info.
- `frontend/src/components/configuration/EffectiveConfigurationPanel.tsx`: move
  desired/applied explanatory copy behind section info.
- `frontend/src/components/configuration/ConfigurationWorkspace.test.tsx`: assert
  configuration guidance is not heavy by default and remains discoverable.
- `frontend/src/components/configuration/ProfileBindingPanel.test.tsx`: assert
  binding precedence help opens on demand.
- `frontend/src/components/configuration/EffectiveConfigurationPanel.test.tsx`:
  assert desired/applied runtime help opens on demand.

No backend files should change.

## Task 1: Reusable Guidance Disclosure

**Files:**

- Create: `frontend/src/components/guidance/GuidanceDisclosure.tsx`
- Modify: `frontend/src/components/guidance/FieldHelp.tsx`
- Test: `frontend/src/components/guidance/guidance.test.tsx`

- [ ] **Step 1: Add failing tests for compact disclosure**

Append these tests to `frontend/src/components/guidance/guidance.test.tsx`:

```tsx
test("GuidanceDisclosure hides rich guidance until opened", async () => {
  const user = userEvent.setup();
  render(
    <GuidanceDisclosure
      id="transport-disclosure"
      label="Transport mode"
      guidance={{
        label: "Transport mode",
        hint: "How browsers connect.",
        details: ["WebRTC is low latency.", "HLS is resilient."],
        safeDefault: "Native/direct",
      }}
    />,
  );

  expect(screen.queryByText("WebRTC is low latency.")).not.toBeInTheDocument();
  await user.click(screen.getByRole("button", { name: /show transport mode help/i }));
  expect(screen.getByText("WebRTC is low latency.")).toBeInTheDocument();
  expect(screen.getByText(/safe default/i)).toBeInTheDocument();
});

test("GuidanceDisclosure closes with Escape", async () => {
  const user = userEvent.setup();
  render(
    <GuidanceDisclosure
      id="runtime-disclosure"
      label="Runtime"
      guidance={{
        title: "Rank model runtimes",
        summary: "Choose which runtime should start first.",
        commonMistakes: ["Disabling fallback before an artifact exists."],
      }}
    />,
  );

  const trigger = screen.getByRole("button", { name: /show runtime help/i });
  await user.click(trigger);
  expect(screen.getByText("Rank model runtimes")).toBeInTheDocument();
  await user.keyboard("{Escape}");
  expect(screen.queryByText("Rank model runtimes")).not.toBeInTheDocument();
  expect(trigger).toHaveFocus();
});
```

Add the import at the top:

```tsx
import { GuidanceDisclosure } from "@/components/guidance/GuidanceDisclosure";
```

- [ ] **Step 2: Run the focused guidance tests and confirm failure**

Run:

```bash
corepack pnpm --dir frontend exec vitest run src/components/guidance/guidance.test.tsx
```

Expected: FAIL because `GuidanceDisclosure` does not exist.

- [ ] **Step 3: Implement `GuidanceDisclosure`**

Create `frontend/src/components/guidance/GuidanceDisclosure.tsx`:

```tsx
import { type ReactNode, useEffect, useRef, useState } from "react";
import { Info, X } from "lucide-react";

import type {
  FieldGuidance,
  SectionGuidance,
} from "@/components/guidance/guidance-types";

type GuidanceDisclosureProps = {
  id: string;
  label: string;
  guidance: FieldGuidance | SectionGuidance;
  children?: ReactNode;
};

function isFieldGuidance(
  guidance: FieldGuidance | SectionGuidance,
): guidance is FieldGuidance {
  return "hint" in guidance;
}

export function GuidanceDisclosure({
  id,
  label,
  guidance,
  children,
}: GuidanceDisclosureProps) {
  const [open, setOpen] = useState(false);
  const triggerRef = useRef<HTMLButtonElement | null>(null);
  const rootRef = useRef<HTMLSpanElement | null>(null);
  const panelId = `${id}-panel`;
  const title = isFieldGuidance(guidance) ? guidance.label : guidance.title;
  const summary = isFieldGuidance(guidance) ? guidance.hint : guidance.summary;
  const details = isFieldGuidance(guidance) ? guidance.details : guidance.steps;
  const concepts = isFieldGuidance(guidance) ? [] : guidance.concepts ?? [];
  const examples = guidance.examples ?? [];
  const warnings = isFieldGuidance(guidance) ? [] : guidance.warnings ?? [];
  const commonMistakes = guidance.commonMistakes ?? [];

  useEffect(() => {
    if (!open) {
      return undefined;
    }

    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        setOpen(false);
        triggerRef.current?.focus();
      }
    };

    const handlePointerDown = (event: PointerEvent) => {
      if (
        event.target instanceof Node
        && rootRef.current
        && !rootRef.current.contains(event.target)
      ) {
        setOpen(false);
      }
    };

    window.addEventListener("keydown", handleKeyDown);
    window.addEventListener("pointerdown", handlePointerDown);
    return () => {
      window.removeEventListener("keydown", handleKeyDown);
      window.removeEventListener("pointerdown", handlePointerDown);
    };
  }, [open]);

  return (
    <span ref={rootRef} className="relative inline-flex align-middle">
      <button
        id={id}
        ref={triggerRef}
        type="button"
        className="inline-flex size-6 cursor-pointer items-center justify-center rounded-full border border-white/12 bg-white/[0.03] text-[#8fd3ff] transition hover:bg-white/[0.08] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#8fd3ff]"
        aria-controls={panelId}
        aria-expanded={open}
        aria-label={`${open ? "Hide" : "Show"} ${label} help`}
        onClick={() => setOpen((current) => !current)}
      >
        <Info className="size-3.5" aria-hidden="true" />
      </button>
      {open ? (
        <div
          id={panelId}
          className="absolute right-0 top-8 z-30 w-[min(28rem,calc(100vw-2rem))] rounded-lg border border-white/10 bg-[#07101b] p-4 text-left text-xs leading-5 text-[#9fb2cf] shadow-[0_24px_80px_-40px_rgba(0,0,0,0.9)]"
          role="dialog"
          aria-label={`${label} help`}
        >
          <div className="flex items-start justify-between gap-3">
            <div>
              <h4 className="text-sm font-semibold text-[#f4f8ff]">{title}</h4>
              <p className="mt-1">{summary}</p>
            </div>
            <button
              type="button"
              className="inline-flex size-7 cursor-pointer items-center justify-center rounded-full border border-white/10 text-[#d8e2f2] hover:bg-white/[0.06] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#8fd3ff]"
              aria-label={`Close ${label} help`}
              onClick={() => {
                setOpen(false);
                triggerRef.current?.focus();
              }}
            >
              <X className="size-3.5" aria-hidden="true" />
            </button>
          </div>
          {children ? <div className="mt-4">{children}</div> : null}
          {concepts.length ? (
            <dl className="mt-3 grid gap-2">
              {concepts.map((concept) => (
                <div key={concept.term}>
                  <dt className="font-semibold text-[#d8e2f2]">{concept.term}</dt>
                  <dd>{concept.definition}</dd>
                </div>
              ))}
            </dl>
          ) : null}
          {details?.length ? (
            <ul className="mt-3 grid gap-1">
              {details.map((detail) => (
                <li key={detail}>{detail}</li>
              ))}
            </ul>
          ) : null}
          {isFieldGuidance(guidance) && guidance.safeDefault ? (
            <p className="mt-3 text-[#d8e2f2]">
              <span className="font-semibold">Safe default:</span>{" "}
              {guidance.safeDefault}
            </p>
          ) : null}
          {isFieldGuidance(guidance) && guidance.runtimeEffect ? (
            <p className="mt-3">
              <span className="font-semibold text-[#d8e2f2]">Runtime effect:</span>{" "}
              {guidance.runtimeEffect}
            </p>
          ) : null}
          {examples.length ? (
            <div className="mt-3">
              <p className="font-semibold text-[#d8e2f2]">Examples</p>
              <ul className="mt-1 grid gap-1">
                {examples.map((example) => (
                  <li key={example.label}>
                    <span className="font-semibold text-[#d8e2f2]">
                      {example.label}:
                    </span>{" "}
                    {example.description}
                  </li>
                ))}
              </ul>
            </div>
          ) : null}
          {warnings.length ? (
            <div className="mt-3 rounded-md border border-amber-300/20 bg-amber-950/20 p-2 text-amber-100">
              <p className="font-semibold">Watch for</p>
              <ul className="mt-1 grid gap-1">
                {warnings.map((warning) => (
                  <li key={warning}>{warning}</li>
                ))}
              </ul>
            </div>
          ) : null}
          {commonMistakes.length ? (
            <div className="mt-3 rounded-md border border-amber-300/20 bg-amber-950/20 p-2 text-amber-100">
              <p className="font-semibold">Common mistakes</p>
              <ul className="mt-1 grid gap-1">
                {commonMistakes.map((mistake) => (
                  <li key={mistake}>{mistake}</li>
                ))}
              </ul>
            </div>
          ) : null}
        </div>
      ) : null}
    </span>
  );
}
```

- [ ] **Step 4: Refactor `FieldHelp` to use `GuidanceDisclosure`**

Replace `frontend/src/components/guidance/FieldHelp.tsx` with:

```tsx
import type { FieldGuidance } from "@/components/guidance/guidance-types";
import { GuidanceDisclosure } from "@/components/guidance/GuidanceDisclosure";

type FieldHelpProps = {
  id: string;
  guidance: FieldGuidance;
};

export function FieldHelp({ id, guidance }: FieldHelpProps) {
  return (
    <GuidanceDisclosure
      id={id}
      label={guidance.label}
      guidance={guidance}
    />
  );
}
```

- [ ] **Step 5: Run focused guidance tests**

Run:

```bash
corepack pnpm --dir frontend exec vitest run src/components/guidance/guidance.test.tsx
```

Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add frontend/src/components/guidance/GuidanceDisclosure.tsx frontend/src/components/guidance/FieldHelp.tsx frontend/src/components/guidance/guidance.test.tsx
git commit -m "feat(guidance): add compact info disclosure"
```

## Task 2: Calibration Visual Explainer

**Files:**

- Create: `frontend/src/components/guidance/CalibrationFlowIllustration.tsx`
- Modify: `frontend/src/index.css`
- Test: `frontend/src/components/guidance/guidance.test.tsx`

- [ ] **Step 1: Add failing tests for the visual explainer**

Append to `frontend/src/components/guidance/guidance.test.tsx`:

```tsx
test("CalibrationFlowIllustration shows source and destination point mapping", () => {
  render(<CalibrationFlowIllustration />);

  expect(screen.getByRole("img", { name: /source points map to top-down points/i }))
    .toBeInTheDocument();
  expect(screen.getByText("S1")).toBeInTheDocument();
  expect(screen.getByText("D1")).toBeInTheDocument();
  expect(screen.getByText(/measured distance/i)).toBeInTheDocument();
});

test("CalibrationFlowIllustration can show region guidance", () => {
  render(<CalibrationFlowIllustration mode="regions" />);

  expect(screen.getByText(/include region/i)).toBeInTheDocument();
  expect(screen.getByText(/exclusion region/i)).toBeInTheDocument();
});
```

Add the import:

```tsx
import { CalibrationFlowIllustration } from "@/components/guidance/CalibrationFlowIllustration";
```

- [ ] **Step 2: Run the focused guidance tests and confirm failure**

Run:

```bash
corepack pnpm --dir frontend exec vitest run src/components/guidance/guidance.test.tsx
```

Expected: FAIL because `CalibrationFlowIllustration` does not exist.

- [ ] **Step 3: Implement `CalibrationFlowIllustration`**

Create `frontend/src/components/guidance/CalibrationFlowIllustration.tsx`:

```tsx
type CalibrationFlowIllustrationProps = {
  mode?: "source-destination" | "boundaries" | "regions";
  animated?: boolean;
};

const sourcePoints = [
  { label: "S1", x: 52, y: 74 },
  { label: "S2", x: 118, y: 58 },
  { label: "S3", x: 158, y: 122 },
  { label: "S4", x: 36, y: 144 },
];

const destinationPoints = [
  { label: "D1", x: 260, y: 68 },
  { label: "D2", x: 342, y: 68 },
  { label: "D3", x: 342, y: 150 },
  { label: "D4", x: 260, y: 150 },
];

export function CalibrationFlowIllustration({
  mode = "source-destination",
  animated = true,
}: CalibrationFlowIllustrationProps) {
  return (
    <figure className="rounded-lg border border-white/10 bg-[#050b13] p-3">
      <svg
        role="img"
        aria-label="Source points map to top-down points"
        className="h-auto w-full"
        viewBox="0 0 400 210"
      >
        <title>Source points map to top-down points</title>
        <desc>
          Four source points in the camera image connect to four destination
          points in the top-down plane with a measured distance marker.
        </desc>

        <defs>
          <linearGradient id="source-plane" x1="0" x2="1" y1="0" y2="1">
            <stop offset="0%" stopColor="#17345c" />
            <stop offset="100%" stopColor="#09182a" />
          </linearGradient>
          <linearGradient id="destination-plane" x1="0" x2="1" y1="0" y2="1">
            <stop offset="0%" stopColor="#2a1f56" />
            <stop offset="100%" stopColor="#111426" />
          </linearGradient>
        </defs>

        <path
          d="M20 48 L178 26 L188 166 L10 176 Z"
          fill="url(#source-plane)"
          stroke="#6cb0ff"
          strokeWidth="2"
        />
        <text x="24" y="28" fill="#d8e2f2" fontSize="11">
          Camera image
        </text>

        <rect
          x="242"
          y="42"
          width="124"
          height="124"
          rx="10"
          fill="url(#destination-plane)"
          stroke="#b28fff"
          strokeWidth="2"
        />
        <text x="248" y="28" fill="#d8e2f2" fontSize="11">
          Top-down plane
        </text>

        {sourcePoints.map((sourcePoint, index) => {
          const destinationPoint = destinationPoints[index];
          return (
            <line
              key={`${sourcePoint.label}-${destinationPoint.label}`}
              className={animated ? "calibration-map-line" : undefined}
              x1={sourcePoint.x}
              y1={sourcePoint.y}
              x2={destinationPoint.x}
              y2={destinationPoint.y}
              stroke="#8fd3ff"
              strokeDasharray="4 6"
              strokeWidth="1.5"
              opacity="0.55"
            />
          );
        })}

        {sourcePoints.map((point) => (
          <g key={point.label}>
            <circle cx={point.x} cy={point.y} r="11" fill="#09192c" stroke="#6cb0ff" />
            <text
              x={point.x}
              y={point.y + 4}
              textAnchor="middle"
              fill="#eef6ff"
              fontSize="10"
              fontWeight="700"
            >
              {point.label}
            </text>
          </g>
        ))}

        {destinationPoints.map((point) => (
          <g key={point.label}>
            <circle cx={point.x} cy={point.y} r="11" fill="#161428" stroke="#b28fff" />
            <text
              x={point.x}
              y={point.y + 4}
              textAnchor="middle"
              fill="#f3eeff"
              fontSize="10"
              fontWeight="700"
            >
              {point.label}
            </text>
          </g>
        ))}

        <line x1="260" x2="342" y1="184" y2="184" stroke="#6fe0c5" strokeWidth="3" />
        <line x1="260" x2="260" y1="177" y2="191" stroke="#6fe0c5" strokeWidth="2" />
        <line x1="342" x2="342" y1="177" y2="191" stroke="#6fe0c5" strokeWidth="2" />
        <text x="301" y="202" textAnchor="middle" fill="#bcefe3" fontSize="11">
          measured distance
        </text>

        {mode === "boundaries" ? (
          <g>
            <line x1="276" x2="328" y1="104" y2="104" stroke="#6fe0c5" strokeWidth="4" />
            <text x="302" y="94" textAnchor="middle" fill="#bcefe3" fontSize="10">
              event line
            </text>
          </g>
        ) : null}

        {mode === "regions" ? (
          <g>
            <rect
              x="272"
              y="82"
              width="52"
              height="44"
              rx="8"
              fill="#6fe0c5"
              opacity="0.16"
              stroke="#6fe0c5"
            />
            <text x="298" y="78" textAnchor="middle" fill="#bcefe3" fontSize="10">
              include region
            </text>
            <rect
              x="326"
              y="126"
              width="28"
              height="24"
              rx="6"
              fill="#ffb86b"
              opacity="0.16"
              stroke="#ffb86b"
            />
            <text x="340" y="164" textAnchor="middle" fill="#ffd9a1" fontSize="10">
              exclusion region
            </text>
          </g>
        ) : null}
      </svg>
      <figcaption className="mt-2 text-xs leading-5 text-[#9fb2cf]">
        Match the same four real marks in the same order, then measure a real
        distance on that plane.
      </figcaption>
    </figure>
  );
}
```

- [ ] **Step 4: Add reduced-motion CSS**

Add this CSS to `frontend/src/index.css` near the existing `@keyframes`
definitions:

```css
.calibration-map-line {
  animation: calibration-map-line-enter 260ms ease-out both;
}

@keyframes calibration-map-line-enter {
  from {
    opacity: 0;
    transform: translateY(4px);
  }

  to {
    opacity: 0.55;
    transform: translateY(0);
  }
}

@media (prefers-reduced-motion: reduce) {
  .calibration-map-line {
    animation: none;
  }
}
```

- [ ] **Step 5: Run focused guidance tests**

Run:

```bash
corepack pnpm --dir frontend exec vitest run src/components/guidance/guidance.test.tsx
```

Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add frontend/src/components/guidance/CalibrationFlowIllustration.tsx frontend/src/components/guidance/guidance.test.tsx frontend/src/index.css
git commit -m "feat(guidance): add calibration visual explainer"
```

## Task 3: Scene Setup Progressive Disclosure

**Files:**

- Modify: `frontend/src/components/cameras/CameraWizard.tsx`
- Modify: `frontend/src/components/cameras/HomographyEditor.tsx`
- Test: `frontend/src/components/cameras/CameraWizard.test.tsx`

- [ ] **Step 1: Add failing Camera Wizard tests**

Add tests to `frontend/src/components/cameras/CameraWizard.test.tsx` that assert:

```tsx
expect(screen.queryByText("The better those marks match the real floor"))
  .not.toBeInTheDocument();
await user.click(screen.getByRole("button", { name: /show calibration help/i }));
expect(screen.getByText(/source points map to top-down points/i)).toBeInTheDocument();
```

Also assert the readiness checklist still remains visible:

```tsx
expect(screen.getByText(/Camera is fixed and not zooming/i)).toBeInTheDocument();
```

- [ ] **Step 2: Run the Camera Wizard test and confirm failure**

Run:

```bash
corepack pnpm --dir frontend exec vitest run src/components/cameras/CameraWizard.test.tsx
```

Expected: FAIL because calibration help is still visible as a large card and no
calibration visual trigger exists.

- [ ] **Step 3: Replace the speed-accuracy card with compact help**

In `frontend/src/components/cameras/CameraWizard.tsx`, replace the large
`Speed accuracy` section with a compact header row:

```tsx
<section className="rounded-[1.5rem] border border-[#284066] bg-[#0c1522] p-4">
  <div className="flex flex-wrap items-center justify-between gap-3">
    <div className="flex items-center gap-2">
      <div>
        <p className="text-[11px] font-semibold uppercase tracking-[0.24em] text-[#8ea4c7]">
          Speed accuracy
        </p>
        <h3 className="mt-2 text-lg font-semibold text-[#f4f8ff]">
          Calibrate speed on the floor where objects move
        </h3>
      </div>
      <GuidanceDisclosure
        id="calibration-speed-guidance"
        label="calibration"
        guidance={SCENE_STEP_GUIDANCE.Calibration}
      >
        <CalibrationFlowIllustration />
        <p className="mt-3 rounded-[1rem] border border-[#5b4b28] bg-[#19150c] px-4 py-3 text-sm text-[#ffd9a1]">
          {SPEED_CALIBRATION_WARNING}
        </p>
      </GuidanceDisclosure>
    </div>
    <span className="rounded-full border border-white/10 bg-white/[0.04] px-3 py-1.5 text-xs font-medium text-[#d8e2f2]">
      {data.visionProfile.speedEnabled ? "Speed metrics on" : "Speed metrics off"}
    </span>
  </div>
  <ul className="mt-4 grid gap-2 md:grid-cols-2">
    {SPEED_CALIBRATION_CHECKLIST.map((item) => (
      <li
        key={item}
        className="rounded-[1rem] border border-white/8 bg-white/[0.03] px-3 py-2 text-sm text-[#d8e2f2]"
      >
        {item}
      </li>
    ))}
  </ul>
</section>
```

Add imports:

```tsx
import { CalibrationFlowIllustration } from "@/components/guidance/CalibrationFlowIllustration";
import { GuidanceDisclosure } from "@/components/guidance/GuidanceDisclosure";
```

- [ ] **Step 4: Replace Step context guidance panel with compact trigger**

In the Camera Wizard aside, replace:

```tsx
{stepGuidance ? <GuidancePanel guidance={stepGuidance} /> : null}
```

with:

```tsx
{stepGuidance ? (
  <div className="flex items-center justify-between gap-3 rounded-[1.1rem] border border-white/8 bg-white/[0.03] px-4 py-3">
    <span className="text-sm font-medium text-[#d8e2f2]">Step help</span>
    <GuidanceDisclosure
      id={`step-help-${stepTitle.toLowerCase().replace(/[^a-z0-9]+/g, "-")}`}
      label={`${stepTitle} step`}
      guidance={stepGuidance}
    />
  </div>
) : null}
```

Remove the `GuidancePanel` import if it is no longer used.

- [ ] **Step 5: Move Homography help into header label rows**

In `frontend/src/components/cameras/HomographyEditor.tsx`, keep the source and
destination titles visible, but render `FieldHelp` as an icon beside the title
instead of a paragraph below it:

```tsx
<div className="flex items-center gap-2">
  <h3 className="mt-2 text-lg font-semibold text-[#f4f8ff]">Source points</h3>
  <FieldHelp id="source-points-help" guidance={SCENE_FIELD_GUIDANCE.sourcePoints} />
</div>
```

Use the same pattern for destination points and reference distance.

- [ ] **Step 6: Run Camera Wizard tests**

Run:

```bash
corepack pnpm --dir frontend exec vitest run src/components/cameras/CameraWizard.test.tsx src/components/guidance/guidance.test.tsx
```

Expected: PASS.

- [ ] **Step 7: Commit**

```bash
git add frontend/src/components/cameras/CameraWizard.tsx frontend/src/components/cameras/HomographyEditor.tsx frontend/src/components/cameras/CameraWizard.test.tsx
git commit -m "feat(cameras): compact calibration guidance"
```

## Task 4: Control Plane Configuration Progressive Disclosure

**Files:**

- Modify: `frontend/src/components/configuration/ProfileEditor.tsx`
- Modify: `frontend/src/components/configuration/ProfileBindingPanel.tsx`
- Modify: `frontend/src/components/configuration/EffectiveConfigurationPanel.tsx`
- Test: `frontend/src/components/configuration/ProfileEditor.test.tsx`
- Test: `frontend/src/components/configuration/ConfigurationWorkspace.test.tsx`
- Test: `frontend/src/components/configuration/ProfileBindingPanel.test.tsx`
- Test: `frontend/src/components/configuration/EffectiveConfigurationPanel.test.tsx`

- [ ] **Step 1: Add failing Profile Editor tests**

In `frontend/src/components/configuration/ProfileEditor.test.tsx`, add a test
that renders the editor and asserts the section summary is hidden until opened:

```tsx
expect(screen.queryByText(/Transport profiles control the stream route/i))
  .not.toBeInTheDocument();
await user.click(screen.getByRole("button", { name: /show transport profile help/i }));
expect(screen.getByText(/Transport profiles control the stream route/i))
  .toBeInTheDocument();
```

- [ ] **Step 2: Run focused configuration tests and confirm failure**

Run:

```bash
corepack pnpm --dir frontend exec vitest run src/components/configuration/ProfileEditor.test.tsx src/components/configuration/ConfigurationWorkspace.test.tsx
```

Expected: FAIL because the profile-kind guidance is currently rendered as a
visible panel.

- [ ] **Step 3: Replace the Profile Editor full guidance panel**

In `frontend/src/components/configuration/ProfileEditor.tsx`, replace:

```tsx
<GuidancePanel guidance={PROFILE_KIND_GUIDANCE[state.kind]} />
```

with an info trigger in the editor header:

```tsx
<div className="flex items-center gap-2">
  <h3 className="text-sm font-semibold text-[var(--vz-text-primary)]">
    {title}
  </h3>
  <GuidanceDisclosure
    id={`profile-kind-help-${state.kind}`}
    label={kindLabel}
    guidance={PROFILE_KIND_GUIDANCE[state.kind]}
  />
</div>
```

Add the import:

```tsx
import { GuidanceDisclosure } from "@/components/guidance/GuidanceDisclosure";
```

Remove the `GuidancePanel` import if it is no longer used.

- [ ] **Step 4: Move field help into label rows in `Field`**

Replace the label span in `Field` with:

```tsx
<span className="inline-flex items-center gap-2">
  {label}
  {help && helpId ? <FieldHelp id={helpId} guidance={help} /> : null}
</span>
```

Remove the lower help row:

```tsx
{help && helpId ? <FieldHelp id={helpId} guidance={help} /> : null}
```

Keep `aria-describedby={helpId}` on controls so fields remain associated with
the help trigger id.

- [ ] **Step 5: Move checkbox help into label rows**

In `CheckboxField`, render the `FieldHelp` inside the label:

```tsx
<label className="flex items-center gap-2">
  <input
    aria-describedby={helpId}
    aria-label={label}
    type="checkbox"
    checked={checked}
    onChange={(event) => onChange(event.target.checked)}
  />
  {label}
  {help && helpId ? <FieldHelp id={helpId} guidance={help} /> : null}
</label>
```

Remove the old help row below the label.

- [ ] **Step 6: Add failing binding/effective panel tests**

In `frontend/src/components/configuration/ProfileBindingPanel.test.tsx`, change
the first test to prove binding precedence is on demand:

```tsx
test("shows binding precedence help on demand", async () => {
  const user = userEvent.setup();
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

  expect(screen.queryByText(/camera binding wins/i)).not.toBeInTheDocument();
  await user.click(screen.getByRole("button", { name: /show operations mode bindings help/i }));
  expect(screen.getByText(/camera binding wins/i)).toBeInTheDocument();
  expect(screen.getByText(/tenant default is the fallback/i)).toBeInTheDocument();
  expect(screen.getByText(/next config refresh or lifecycle action/i)).toBeInTheDocument();
});
```

In `frontend/src/components/configuration/EffectiveConfigurationPanel.test.tsx`,
replace the visible explanation test with:

```tsx
test("shows desired and runtime applied configuration help on demand", async () => {
  const user = userEvent.setup();
  render(<EffectiveConfigurationPanel cameras={cameras} catalog={catalog} />);

  expect(screen.queryByText(/desired configuration/i)).not.toBeInTheDocument();
  await user.click(screen.getByRole("button", { name: /show effective configuration help/i }));
  expect(screen.getByText(/desired configuration/i)).toBeInTheDocument();
  expect(screen.getByText(/runtime-applied hash/i)).toBeInTheDocument();
  expect(screen.getByText(/direct camera binding/i)).toBeInTheDocument();
});
```

- [ ] **Step 7: Move binding precedence prose behind section help**

In `frontend/src/components/configuration/ProfileBindingPanel.tsx`, add imports:

```tsx
import { GuidanceDisclosure } from "@/components/guidance/GuidanceDisclosure";
import type { SectionGuidance } from "@/components/guidance/guidance-types";
```

Add this constant near the top of the file:

```tsx
const BINDING_SCOPE_GUIDANCE: SectionGuidance = {
  title: "Binding precedence",
  summary:
    "Camera binding wins, then edge node, then site. Tenant default is the fallback.",
  steps: [
    "Bind at camera scope for an explicit one-camera override.",
    "Bind at edge node or site scope for groups of cameras.",
    "Bind at tenant scope only for the default fallback.",
    "Workers apply the resolved profile after their next config refresh or lifecycle action.",
  ],
};
```

Replace the binding title block:

```tsx
<div className="flex items-center gap-2 text-sm font-semibold text-[var(--vz-text-primary)]">
  <Link2 className="size-4 text-[#8fd3ff]" />
  <h3>{labelForKind(kind)} bindings</h3>
</div>
```

with:

```tsx
<div className="flex items-center gap-2 text-sm font-semibold text-[var(--vz-text-primary)]">
  <Link2 className="size-4 text-[#8fd3ff]" />
  <h3>{labelForKind(kind)} bindings</h3>
  <GuidanceDisclosure
    id={`binding-help-${kind}`}
    label={`${labelForKind(kind)} bindings`}
    guidance={BINDING_SCOPE_GUIDANCE}
  />
</div>
```

Remove this always-visible prose block:

```tsx
<div className="rounded-lg border border-white/10 bg-[#07101b] px-3 py-3 text-xs leading-5 text-[#9fb2cf]">
  <p>
    Camera binding wins, then edge node, then site. Tenant default is the fallback.
  </p>
  <p className="mt-1">
    Test profiles before binding; workers apply the resolved profile after their
    next config refresh or lifecycle action.
  </p>
</div>
```

- [ ] **Step 8: Move effective-runtime prose behind section help**

In `frontend/src/components/configuration/EffectiveConfigurationPanel.tsx`, add
imports:

```tsx
import { GuidanceDisclosure } from "@/components/guidance/GuidanceDisclosure";
import type { SectionGuidance } from "@/components/guidance/guidance-types";
```

Add this constant near the top of the file:

```tsx
const EFFECTIVE_CONFIGURATION_GUIDANCE: SectionGuidance = {
  title: "Desired and runtime-applied state",
  summary:
    "Desired configuration is the profile set resolved by binding precedence. Runtime-applied hash shows what a worker has actually reported.",
  steps: [
    "Direct camera binding means the camera won; inherited means an edge node, site, or tenant binding supplied the profile.",
    "Validation status shows tested state: valid, invalid, or unvalidated.",
    "Desired-only rows are saved intent without a worker report.",
    "Applied hash and aligned mean the worker reported the same profile hash.",
  ],
};
```

Replace the effective configuration heading with:

```tsx
<div className="mt-1 flex items-center gap-2">
  <h3 className="text-sm font-semibold text-[#f4f8ff]">
    Effective configuration
  </h3>
  <GuidanceDisclosure
    id="effective-configuration-help"
    label="effective configuration"
    guidance={EFFECTIVE_CONFIGURATION_GUIDANCE}
  />
</div>
```

Remove the visible paragraph and list below the heading:

```tsx
<p className="mt-2 max-w-2xl text-xs leading-5 text-[#9fb2cf]">
  Desired configuration is the profile set resolved by binding precedence.
  Runtime-applied hash shows what a worker has actually reported. A mismatch
  means the UI has saved intent that the runtime has not applied yet.
</p>
<ul className="mt-2 grid max-w-2xl gap-1 text-xs leading-5 text-[#9fb2cf]">
  ...
</ul>
```

Do not hide runtime state, validation messages, status badges, hashes, or
diagnostics.

- [ ] **Step 9: Run focused configuration tests**

Run:

```bash
corepack pnpm --dir frontend exec vitest run src/components/configuration/ProfileEditor.test.tsx src/components/configuration/ProfileBindingPanel.test.tsx src/components/configuration/EffectiveConfigurationPanel.test.tsx src/components/configuration/ConfigurationWorkspace.test.tsx src/components/guidance/guidance.test.tsx
```

Expected: PASS.

- [ ] **Step 10: Commit**

```bash
git add frontend/src/components/configuration/ProfileEditor.tsx frontend/src/components/configuration/ProfileBindingPanel.tsx frontend/src/components/configuration/EffectiveConfigurationPanel.tsx frontend/src/components/configuration/ProfileEditor.test.tsx frontend/src/components/configuration/ProfileBindingPanel.test.tsx frontend/src/components/configuration/EffectiveConfigurationPanel.test.tsx frontend/src/components/configuration/ConfigurationWorkspace.test.tsx
git commit -m "feat(config): compact profile guidance"
```

## Task 5: Final Verification And Visual QA

**Files:**

- Verify touched frontend files.
- Optionally update `docs/superpowers/status/2026-05-29-next-chat-omnisight-installer-main-merge-readiness-handoff.md` after implementation.

- [ ] **Step 1: Run focused frontend tests**

Run:

```bash
corepack pnpm --dir frontend exec vitest run src/components/guidance/guidance.test.tsx src/components/cameras/CameraWizard.test.tsx src/components/configuration/ProfileEditor.test.tsx src/components/configuration/ProfileBindingPanel.test.tsx src/components/configuration/EffectiveConfigurationPanel.test.tsx src/components/configuration/ConfigurationWorkspace.test.tsx
```

Expected: PASS.

- [ ] **Step 2: Run Live/Operations regression tests if shared components changed layout behavior**

Run:

```bash
corepack pnpm --dir frontend exec vitest run src/pages/Live.test.tsx src/components/operations/SceneStatusStrip.test.tsx src/lib/operational-health.test.ts
```

Expected: PASS.

- [ ] **Step 3: Run frontend build**

Run:

```bash
corepack pnpm --dir frontend build
```

Expected: PASS.

- [ ] **Step 4: Browser visual QA**

Start the app using the existing local dev or installed stack. Verify:

- Scene setup default view is compact.
- Calibration help opens from a circular `i`.
- Calibration visual shows source points, destination points, connectors, and
  measured distance.
- Reduced motion setting shows a static diagram without motion.
- Control Plane Configuration no longer shows large guidance panels by default.
- Info disclosures work on desktop and narrow mobile widths.
- Text does not overflow inside popovers.
- Escape closes popovers and focus returns to the trigger.

- [ ] **Step 5: Update handoff after implementation**

If this plan is implemented, update:

```text
docs/superpowers/status/2026-05-29-next-chat-omnisight-installer-main-merge-readiness-handoff.md
```

Record:

- guidance-density correction implemented
- calibration visual explainer added
- verification commands and results

- [ ] **Step 6: Commit final docs if changed**

```bash
git add docs/superpowers/status/2026-05-29-next-chat-omnisight-installer-main-merge-readiness-handoff.md
git commit -m "docs: record compact guidance follow-up"
```

Run this only if the handoff changed.

## Self-Review

- Spec coverage: the plan covers compact field help, section help, calibration
  source/destination visual guidance, boundaries/regions mini guidance,
  accessibility, reduced motion, and tests.
- Placeholder scan: no task contains a placeholder requirement; every task has
  exact files and commands.
- Type consistency: `GuidanceDisclosure`, `CalibrationFlowIllustration`,
  `FieldGuidance`, and `SectionGuidance` names match across tasks.
