# Domain-Neutral Scene Authoring Canvas Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make OmniSight scene-authoring guidance object-neutral so event lines, polygon zones, include regions, and exclusion regions do not visually imply cars, people, roads, or any other single domain.

**Architecture:** Keep runtime geometry unchanged. Update only the guidance SVG, default wizard copy, and tests. The default visual language becomes abstract tracked anchors, motion paths, object envelopes, and authoring geometry.

**Tech Stack:** React 19, TypeScript, Vite, Tailwind utility classes, Vitest, Testing Library.

---

## Source Material

Read before implementation:

- `docs/superpowers/specs/2026-06-04-domain-neutral-scene-authoring-canvas-design.md`
- `docs/superpowers/specs/2026-06-03-taste-led-omnisight-ui-ux-polish-design.md`
- `docs/brand/omnisight-ui-spec-sheet.md`
- `taste-skill/SKILL.md` if present, routed to `dashboards`
- `taste-skill/dashboards/skill.md` if present
- `taste-skill/components/style-recipes.md` if present

## File Map

- Modify: `frontend/src/components/guidance/CalibrationFlowIllustration.tsx`
  - Owns the calibration, event-boundary, and detection-region SVG guidance.
  - Add neutral tracked-anchor visuals here.
- Modify: `frontend/src/components/guidance/guidance.test.tsx`
  - Locks the SVG contract.
  - Add tests that require neutral anchors/motion paths and reject category glyphs.
- Modify: `frontend/src/components/cameras/scene-guidance.ts`
  - Owns help-panel text for event boundaries and detection regions.
  - Remove road/loading-bay/default traffic wording.
- Modify: `frontend/src/components/cameras/CameraWizard.tsx`
  - Owns inline default helper/background copy in the scene setup wizard.
  - Make line/zone/include/exclude copy scene-neutral.
- Modify: `frontend/src/components/cameras/CameraWizard.test.tsx`
  - Locks the new default helper copy.
  - Keep existing payload/runtime tests unchanged.

No backend files should change.

## Task 1: Add Neutral Illustration Contract Tests

**Files:**

- Modify: `frontend/src/components/guidance/guidance.test.tsx`

- [ ] **Step 1: Add the failing boundary illustration test**

Add this test after `CalibrationFlowIllustration can show event boundary guidance`:

```tsx
test("CalibrationFlowIllustration uses neutral tracked anchors for event guidance", () => {
  const { container } = render(<CalibrationFlowIllustration mode="boundaries" />);

  expect(screen.getByText(/tracked anchor/i)).toBeInTheDocument();
  expect(screen.getByText(/object path/i)).toBeInTheDocument();
  expect(container.querySelectorAll("[data-track-anchor]").length).toBeGreaterThanOrEqual(3);
  expect(container.querySelectorAll("[data-motion-path]").length).toBeGreaterThanOrEqual(2);
  expect(container.querySelectorAll("[data-object-envelope]").length).toBeGreaterThanOrEqual(2);
  expect(container.querySelector("[data-scene-glyph='vehicle']")).not.toBeInTheDocument();
  expect(container.querySelector("[data-scene-glyph='person']")).not.toBeInTheDocument();
  expect(container.querySelector("[data-scene-glyph='boat']")).not.toBeInTheDocument();
  expect(container.querySelector("[data-scene-glyph='animal']")).not.toBeInTheDocument();
});
```

- [ ] **Step 2: Add the failing region illustration test**

Add this test after the boundary neutral test:

```tsx
test("CalibrationFlowIllustration uses neutral tracked anchors for region guidance", () => {
  const { container } = render(<CalibrationFlowIllustration mode="regions" />);

  expect(screen.getByText(/tracked anchor/i)).toBeInTheDocument();
  expect(screen.getByText(/object path/i)).toBeInTheDocument();
  expect(container.querySelectorAll("[data-track-anchor]").length).toBeGreaterThanOrEqual(3);
  expect(container.querySelectorAll("[data-motion-path]").length).toBeGreaterThanOrEqual(2);
  expect(container.querySelectorAll("[data-object-envelope]").length).toBeGreaterThanOrEqual(2);
  expect(container.querySelector("[data-scene-glyph='vehicle']")).not.toBeInTheDocument();
  expect(container.querySelector("[data-scene-glyph='person']")).not.toBeInTheDocument();
  expect(container.querySelector("[data-scene-glyph='boat']")).not.toBeInTheDocument();
  expect(container.querySelector("[data-scene-glyph='animal']")).not.toBeInTheDocument();
});
```

- [ ] **Step 3: Run the focused test and verify RED**

Run:

```bash
cd /Users/yann.moren/vision/frontend
corepack pnpm vitest run src/components/guidance/guidance.test.tsx
```

Expected: FAIL because the current illustration does not render
`tracked anchor`, `object path`, `[data-track-anchor]`,
`[data-motion-path]`, or `[data-object-envelope]`.

- [ ] **Step 4: Commit nothing**

Do not commit the failing test alone unless the implementation will happen in a
separate branch checkpoint. Continue to Task 2.

## Task 2: Replace Category-Like Scene Glyphs With Neutral Track Graphics

**Files:**

- Modify: `frontend/src/components/guidance/CalibrationFlowIllustration.tsx`
- Test: `frontend/src/components/guidance/guidance.test.tsx`

- [ ] **Step 1: Add neutral track data**

In `CalibrationFlowIllustration.tsx`, add these constants below
`destinationPoints`:

```tsx
const neutralAnchors = [
  { id: "alpha", x: 118, y: 128, envelope: "circle" },
  { id: "bravo", x: 218, y: 104, envelope: "capsule" },
  { id: "charlie", x: 310, y: 134, envelope: "diamond" },
] as const;

const neutralMotionPaths = [
  "M84 154 C118 132 146 124 190 138",
  "M188 90 C224 108 260 126 326 130",
] as const;
```

- [ ] **Step 2: Add the neutral track layer component**

Add this component above `SceneAuthoringIllustration`:

```tsx
function NeutralTrackLayer() {
  return (
    <g data-scene-glyph="neutral-tracks" opacity="0.96">
      {neutralMotionPaths.map((path, index) => (
        <path
          key={path}
          data-motion-path={`path-${index + 1}`}
          d={path}
          fill="none"
          stroke="#9fb2cf"
          strokeDasharray="5 7"
          strokeLinecap="round"
          strokeWidth="1.8"
          opacity="0.72"
        />
      ))}

      {neutralAnchors.map((anchor) => (
        <g key={anchor.id}>
          {anchor.envelope === "capsule" ? (
            <rect
              data-object-envelope={anchor.id}
              x={anchor.x - 20}
              y={anchor.y - 10}
              width="40"
              height="20"
              rx="10"
              fill="#c5d6e8"
              opacity="0.16"
              stroke="#c5d6e8"
              strokeWidth="1.5"
            />
          ) : null}
          {anchor.envelope === "circle" ? (
            <circle
              data-object-envelope={anchor.id}
              cx={anchor.x}
              cy={anchor.y}
              r="15"
              fill="#c5d6e8"
              opacity="0.14"
              stroke="#c5d6e8"
              strokeWidth="1.5"
            />
          ) : null}
          {anchor.envelope === "diamond" ? (
            <path
              data-object-envelope={anchor.id}
              d={`M${anchor.x} ${anchor.y - 16} L${anchor.x + 18} ${anchor.y} L${anchor.x} ${
                anchor.y + 16
              } L${anchor.x - 18} ${anchor.y} Z`}
              fill="#c5d6e8"
              opacity="0.14"
              stroke="#c5d6e8"
              strokeWidth="1.5"
            />
          ) : null}
          <circle
            data-track-anchor={anchor.id}
            cx={anchor.x}
            cy={anchor.y}
            r="4.5"
            fill="#f4f8ff"
            stroke="#08111a"
            strokeWidth="1.5"
          />
        </g>
      ))}

      <text x="112" y="116" textAnchor="middle" fill="#d8e2f2" fontSize="9">
        tracked anchor
      </text>
      <text x="232" y="84" textAnchor="middle" fill="#9fb2cf" fontSize="9">
        object path
      </text>
    </g>
  );
}
```

- [ ] **Step 3: Replace the existing car/person-like `<g>`**

In `SceneAuthoringIllustration`, remove this block:

```tsx
<g opacity="0.95">
  <rect x="206" y="84" width="42" height="24" rx="6" fill="#c5d6e8" />
  <circle cx="216" cy="112" r="5" fill="#08111a" />
  <circle cx="238" cy="112" r="5" fill="#08111a" />
  <circle cx="118" cy="128" r="7" fill="#ffc978" />
  <line x1="118" x2="118" y1="135" y2="158" stroke="#ffc978" strokeWidth="3" />
  <line x1="106" x2="130" y1="150" y2="150" stroke="#ffc978" strokeWidth="3" />
</g>
```

Replace it with:

```tsx
<NeutralTrackLayer />
```

- [ ] **Step 4: Run the focused test and verify GREEN**

Run:

```bash
cd /Users/yann.moren/vision/frontend
corepack pnpm vitest run src/components/guidance/guidance.test.tsx
```

Expected: PASS.

- [ ] **Step 5: Commit the neutral illustration**

Run:

```bash
cd /Users/yann.moren/vision
git add frontend/src/components/guidance/CalibrationFlowIllustration.tsx frontend/src/components/guidance/guidance.test.tsx
git commit -m "fix(ui): neutralize scene authoring illustration"
```

## Task 3: Add Neutral Default Copy Tests

**Files:**

- Modify: `frontend/src/components/cameras/CameraWizard.test.tsx`

- [ ] **Step 1: Update the line boundary expectation**

In `event boundaries still submit to zones instead of detection regions`,
replace:

```tsx
expect(screen.getByText(/line = crossing trigger/i)).toBeInTheDocument();
```

With:

```tsx
expect(
  screen.getByText(/line = crossing trigger\. Place it where tracked anchors should cross/i),
).toBeInTheDocument();
expect(screen.queryByText(/door, lane, or threshold/i)).not.toBeInTheDocument();
```

- [ ] **Step 2: Update the polygon zone expectation**

In `polygon event zones show enter and exit guidance before submit`, replace:

```tsx
expect(
  screen.getByText(/enter and exit events fire when tracks move through the zone/i),
).toBeInTheDocument();
```

With:

```tsx
expect(
  screen.getByText(/enter and exit events fire when tracked anchors move through the zone/i),
).toBeInTheDocument();
```

- [ ] **Step 3: Update include/exclusion expectations**

In the include-region test, replace:

```tsx
expect(screen.getByText(/include = detector gate/i)).toBeInTheDocument();
```

With:

```tsx
expect(
  screen.getByText(/include = detector gate\. Keep eligible detections inside the observation area/i),
).toBeInTheDocument();
```

In the exclusion-region test, replace:

```tsx
expect(screen.getByText(/exclude = detector mask/i)).toBeInTheDocument();
```

With:

```tsx
expect(
  screen.getByText(/exclude = detector mask\. Remove reflections, screens, repeated background motion, or irrelevant scene areas/i),
).toBeInTheDocument();
expect(screen.queryByText(/public road/i)).not.toBeInTheDocument();
```

- [ ] **Step 4: Run the focused test and verify RED**

Run:

```bash
cd /Users/yann.moren/vision/frontend
corepack pnpm vitest run src/components/cameras/CameraWizard.test.tsx
```

Expected: FAIL because the implementation still contains the previous helper
copy.

## Task 4: Implement Neutral Scene Authoring Copy

**Files:**

- Modify: `frontend/src/components/cameras/CameraWizard.tsx`
- Modify: `frontend/src/components/cameras/scene-guidance.ts`
- Test: `frontend/src/components/cameras/CameraWizard.test.tsx`

- [ ] **Step 1: Update CameraWizard event-boundary copy**

In `CameraWizard.tsx`, replace the line-boundary background content:

```tsx
"Click two points across a door, lane, or threshold. Crossings generate events."
```

With:

```tsx
"Click two points across the path where tracked anchors should cross. Crossings generate events."
```

Replace the line-boundary helper text:

```tsx
"Line = crossing trigger. Place it where tracked motion should cross."
```

With:

```tsx
"Line = crossing trigger. Place it where tracked anchors should cross."
```

Replace the polygon-zone helper text:

```tsx
"Polygon zone = event area. Enter and exit events fire when tracks move through the zone."
```

With:

```tsx
"Polygon zone = event area. Enter and exit events fire when tracked anchors move through the zone."
```

- [ ] **Step 2: Update CameraWizard detection-region copy**

Replace the include-region background content:

```tsx
"Draw the valid operating space. Outside include polygons is ignored when any include exists."
```

With:

```tsx
"Draw the observation area. Outside include polygons is ignored when any include exists."
```

Replace the include-region helper text:

```tsx
"Include = detector gate. Keep detections inside the operating area."
```

With:

```tsx
"Include = detector gate. Keep eligible detections inside the observation area."
```

Replace the exclusion-region helper text:

```tsx
"Exclude = detector mask. Remove reflections, public road, screens, or background motion."
```

With:

```tsx
"Exclude = detector mask. Remove reflections, screens, repeated background motion, or irrelevant scene areas."
```

- [ ] **Step 3: Update scene guidance examples and details**

In `scene-guidance.ts`, replace the `eventBoundaries` entry with:

```ts
eventBoundaries: {
  label: "Event boundaries",
  hint: "Draw lines or zones on the analytics still where tracked anchors move.",
  details: [
    "Line boundaries emit crossing events when a tracked anchor changes sides.",
    "Polygon zones emit enter and exit events when a tracked anchor moves into or out of the marked area.",
    "Draw both shapes on the camera analytics still, not on the destination point sketch.",
    "Use line boundaries for any transition path where crossing matters.",
    "Use polygon zones for bounded areas where enter and exit matters.",
    "Class scope on line boundaries narrows which tracked classes emit events.",
  ],
  examples: [
    {
      label: "Transition crossing",
      description:
        "Draw a line across the path where crossing direction should become an event.",
    },
    {
      label: "Controlled zone",
      description:
        "Draw a polygon around any bounded area that should emit enter and exit events.",
    },
  ],
},
```

Replace the `detectionRegions` entry with:

```ts
detectionRegions: {
  label: "Detection regions",
  hint: "Include polygons keep detections eligible; exclusion polygons suppress detections.",
  details: [
    "Draw detection regions on the camera analytics still, not on the destination point sketch.",
    "Use include regions to focus detection on the observation area; if any include region exists, detections outside include regions are ignored.",
    "Use exclusion regions to ignore reflections, screens, repeated background motion, or irrelevant scene areas.",
    "Detection regions are applied before event boundaries are evaluated, so masked detections cannot create line or zone events.",
  ],
  examples: [
    {
      label: "Observation area include",
      description:
        "Keep detections inside the useful part of the scene and ignore adjacent background.",
    },
    {
      label: "Noise pocket exclusion",
      description:
        "Mask a repeated reflection, display, surface, or background area that creates irrelevant detections.",
    },
  ],
},
```

- [ ] **Step 4: Run focused wizard tests and verify GREEN**

Run:

```bash
cd /Users/yann.moren/vision/frontend
corepack pnpm vitest run src/components/cameras/CameraWizard.test.tsx
```

Expected: PASS.

- [ ] **Step 5: Commit the neutral copy**

Run:

```bash
cd /Users/yann.moren/vision
git add frontend/src/components/cameras/CameraWizard.tsx frontend/src/components/cameras/CameraWizard.test.tsx frontend/src/components/cameras/scene-guidance.ts
git commit -m "fix(ui): generalize scene authoring guidance copy"
```

## Task 5: Final Verification And Push

**Files:**

- Verify: all modified frontend files

- [ ] **Step 1: Run combined focused tests**

Run:

```bash
cd /Users/yann.moren/vision/frontend
corepack pnpm vitest run \
  src/components/guidance/guidance.test.tsx \
  src/components/cameras/CameraWizard.test.tsx
```

Expected: PASS for both files.

- [ ] **Step 2: Run production build**

Run:

```bash
cd /Users/yann.moren/vision/frontend
corepack pnpm build
```

Expected: exit code 0 with `✓ built`.

- [ ] **Step 3: Run touched-file lint**

Run:

```bash
cd /Users/yann.moren/vision/frontend
corepack pnpm exec eslint \
  src/components/guidance/CalibrationFlowIllustration.tsx \
  src/components/guidance/guidance.test.tsx \
  src/components/cameras/CameraWizard.tsx \
  src/components/cameras/CameraWizard.test.tsx \
  src/components/cameras/scene-guidance.ts
```

Expected: no errors. Existing repository-wide lint issues in unrelated files do
not block this task, but any error in these five touched files must be fixed.

- [ ] **Step 4: Check the diff**

Run:

```bash
cd /Users/yann.moren/vision
git diff --check
git status --short
```

Expected: no whitespace errors. Only the intended tracked frontend files are
modified, plus existing unrelated untracked scratch files if they were already
present.

- [ ] **Step 5: Push**

Run:

```bash
cd /Users/yann.moren/vision
git push origin codex/omnisight-ui-ux-polish
```

Expected: branch pushes successfully.

## Self-Review Checklist

- Spec requirement "no category silhouettes" is covered by Task 1 and Task 2.
- Spec requirement "neutral testable markers" is covered by `data-track-anchor`,
  `data-motion-path`, and `data-object-envelope`.
- Spec requirement "event copy avoids road/traffic-specific language" is
  covered by Task 3 and Task 4.
- Spec requirement "detection copy avoids public-road/loading-bay-specific
  language" is covered by Task 3 and Task 4.
- Spec requirement "runtime payload behavior unchanged" is protected by the
  existing CameraWizard submit tests that remain in the focused test run.
- Plan contains no backend tasks and no dependency changes.
