# Boundary Authoring and Normalized Zones Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace raw line/polygon coordinate entry with visual authoring on a frozen analytics frame, while persisting boundaries as normalized coordinates that stay stable across browser display sizes.

**Architecture:** Add a camera setup preview contract in the backend, normalize zone coordinates against the analytics frame, and build a reusable frontend authoring canvas that the camera wizard uses for both boundaries and future calibration work. Keep worker-facing zones backward-compatible by materializing pixel coordinates from normalized values before publishing config to the worker.

**Tech Stack:** FastAPI, Pydantic, SQLAlchemy JSONB camera config, React, TypeScript, Vitest, React Testing Library, TanStack Query.

---

## File Structure

- Create: `backend/src/argus/api/v1/camera_setup.py`
  - Serve frozen analytics-frame setup previews and preview metadata.
- Modify: `backend/src/argus/api/contracts.py`
  - Add normalized zone payloads and setup preview response models.
- Modify: `backend/src/argus/api/v1/cameras.py`
  - Register the setup preview route under the camera API.
- Modify: `backend/src/argus/services/app.py`
  - Normalize incoming zones, denormalize worker-facing zones, and expose setup preview metadata.
- Test: `backend/tests/services/test_camera_service.py`
  - Validate normalization/denormalization and update behavior.
- Test: `backend/tests/api/test_app.py`
  - Validate the setup preview route contract.
- Create: `frontend/src/components/cameras/BoundaryAuthoringCanvas.tsx`
  - Visual line/polygon authoring surface.
- Create: `frontend/src/components/cameras/boundary-geometry.ts`
  - Shared normalization and hit-testing helpers.
- Modify: `frontend/src/components/cameras/HomographyEditor.tsx`
  - Reuse the same frozen-frame canvas primitives instead of placeholder panels.
- Modify: `frontend/src/components/cameras/CameraWizard.tsx`
  - Replace raw-first boundary entry with visual authoring and move numeric fields behind `Advanced`.
- Modify: `frontend/src/components/cameras/CameraStepSummary.tsx`
  - Summarize boundary names, scope, and direction rather than raw numbers.
- Test: `frontend/src/components/cameras/CameraWizard.test.tsx`
  - Validate the new authoring workflow.
- Test: `frontend/src/components/cameras/HomographyEditor.test.tsx`
  - Add coverage for canvas-backed point editing.

### Task 1: Add normalized zone contracts and setup preview API

**Files:**
- Create: `backend/src/argus/api/v1/camera_setup.py`
- Modify: `backend/src/argus/api/contracts.py`
- Modify: `backend/src/argus/api/v1/cameras.py`
- Modify: `backend/src/argus/services/app.py`
- Test: `backend/tests/services/test_camera_service.py`
- Test: `backend/tests/api/test_app.py`

- [ ] **Step 1: Write the failing backend tests for normalized zones and preview metadata**

```python
async def test_update_camera_normalizes_line_zone_coordinates(camera_service, tenant_context, camera):
    payload = CameraUpdate(
        zones=[
            {
                "id": "room-split",
                "type": "line",
                "points": [[640, 120], [640, 710]],
                "class_names": ["person"],
                "frame_size": {"width": 1280, "height": 720},
            }
        ]
    )

    response = await camera_service.update_camera(tenant_context, camera.id, payload)

    assert response.zones[0]["points_normalized"] == [[0.5, 0.166667], [0.5, 0.986111]]
    assert response.zones[0]["frame_size"] == {"width": 1280, "height": 720}


async def test_camera_setup_preview_returns_analytics_frame_metadata(client, admin_headers, camera_id):
    response = await client.get(f"/api/v1/cameras/{camera_id}/setup-preview", headers=admin_headers)

    assert response.status_code == 200
    assert response.json()["frame_size"] == {"width": 1280, "height": 720}
    assert "preview_url" in response.json()
```

- [ ] **Step 2: Run the backend tests to verify they fail**

Run: `python3 -m uv run pytest backend/tests/services/test_camera_service.py backend/tests/api/test_app.py -q`

Expected: FAIL with missing preview route and missing normalized zone fields.

- [ ] **Step 3: Add the preview and normalized-zone contracts**

```python
class FrameSize(BaseModel):
    width: int = Field(gt=0)
    height: int = Field(gt=0)


class CameraSetupPreviewResponse(BaseModel):
    camera_id: UUID
    preview_url: str
    frame_size: FrameSize
    captured_at: datetime


def _normalize_points(points: list[list[float]], frame_size: FrameSize) -> list[list[float]]:
    return [
        [round(point[0] / frame_size.width, 6), round(point[1] / frame_size.height, 6)]
        for point in points
    ]
```

```python
@router.get("/{camera_id}/setup-preview", response_model=CameraSetupPreviewResponse)
async def get_camera_setup_preview(...):
    return await services.cameras.get_setup_preview(tenant_context, camera_id)
```

- [ ] **Step 4: Normalize zones on write and denormalize them for workers**

```python
def _normalize_zone_payload(zone: dict[str, object]) -> dict[str, object]:
    frame_size = FrameSize.model_validate(zone["frame_size"])
    points = zone.get("points") or zone.get("polygon")
    normalized = _normalize_points(points, frame_size)
    payload = dict(zone)
    payload["frame_size"] = frame_size.model_dump(mode="python")
    payload["points_normalized"] = normalized
    return payload


def _worker_zone_payload(zone: dict[str, object]) -> dict[str, object]:
    frame_size = FrameSize.model_validate(zone["frame_size"])
    denormalized = [
        [round(point[0] * frame_size.width), round(point[1] * frame_size.height)]
        for point in zone["points_normalized"]
    ]
    payload = dict(zone)
    if zone.get("type") == "line":
        payload["points"] = denormalized
    else:
        payload["polygon"] = denormalized
    return payload
```

- [ ] **Step 5: Re-run the backend tests**

Run: `python3 -m uv run pytest backend/tests/services/test_camera_service.py backend/tests/api/test_app.py -q`

Expected: PASS for the new normalization and preview cases.

- [ ] **Step 6: Commit**

```bash
git add backend/src/argus/api/contracts.py backend/src/argus/api/v1/camera_setup.py backend/src/argus/api/v1/cameras.py backend/src/argus/services/app.py backend/tests/services/test_camera_service.py backend/tests/api/test_app.py
git commit -m "feat: add normalized zone contracts and setup preview api"
```

### Task 2: Build the reusable boundary authoring canvas

**Files:**
- Create: `frontend/src/components/cameras/BoundaryAuthoringCanvas.tsx`
- Create: `frontend/src/components/cameras/boundary-geometry.ts`
- Modify: `frontend/src/components/cameras/HomographyEditor.tsx`
- Test: `frontend/src/components/cameras/HomographyEditor.test.tsx`

- [ ] **Step 1: Write the failing frontend tests for visual authoring**

```tsx
test("creates a line by clicking two points on the setup canvas", async () => {
  render(<BoundaryAuthoringCanvas mode="line" frameSize={{ width: 1280, height: 720 }} value={null} onChange={onChange} />);

  await user.click(screen.getByLabelText(/setup frame canvas/i), { clientX: 320, clientY: 120 });
  await user.click(screen.getByLabelText(/setup frame canvas/i), { clientX: 320, clientY: 600 });

  expect(onChange).toHaveBeenCalledWith({
    type: "line",
    pointsNormalized: [[0.25, 0.166667], [0.25, 0.833333]],
  });
});
```

- [ ] **Step 2: Run the failing frontend tests**

Run: `corepack pnpm --dir frontend exec vitest run src/components/cameras/HomographyEditor.test.tsx src/components/cameras/CameraWizard.test.tsx`

Expected: FAIL because `BoundaryAuthoringCanvas` and its interactions do not exist.

- [ ] **Step 3: Add geometry helpers for normalization and hit testing**

```ts
export function normalizeCanvasPoint(
  point: { x: number; y: number },
  frameSize: { width: number; height: number },
) {
  return [
    Number((point.x / frameSize.width).toFixed(6)),
    Number((point.y / frameSize.height).toFixed(6)),
  ] as const;
}

export function denormalizePoint(
  point: readonly [number, number],
  frameSize: { width: number; height: number },
) {
  return {
    x: Math.round(point[0] * frameSize.width),
    y: Math.round(point[1] * frameSize.height),
  };
}
```

- [ ] **Step 4: Build the canvas component and swap out the homography placeholder**

```tsx
<div className="space-y-3">
  <div className="flex items-center justify-between">
    <p className="text-xs text-[#9db3d3]">Analytics frame: {frameSize.width}×{frameSize.height}</p>
    <Button onClick={onFreezeFrame}>Freeze for setup</Button>
  </div>
  <BoundaryAuthoringCanvas
    aria-label="Setup frame canvas"
    frameSize={frameSize}
    mode={mode}
    value={value}
    onChange={onChange}
    previewUrl={previewUrl}
  />
</div>
```

- [ ] **Step 5: Re-run the frontend tests**

Run: `corepack pnpm --dir frontend exec vitest run src/components/cameras/HomographyEditor.test.tsx src/components/cameras/CameraWizard.test.tsx`

Expected: PASS for canvas creation and homography point editing.

- [ ] **Step 6: Commit**

```bash
git add frontend/src/components/cameras/BoundaryAuthoringCanvas.tsx frontend/src/components/cameras/boundary-geometry.ts frontend/src/components/cameras/HomographyEditor.tsx frontend/src/components/cameras/HomographyEditor.test.tsx frontend/src/components/cameras/CameraWizard.test.tsx
git commit -m "feat: add reusable setup canvas for boundaries and homography"
```

### Task 3: Replace raw-first boundary entry in the camera wizard

**Files:**
- Modify: `frontend/src/components/cameras/CameraWizard.tsx`
- Modify: `frontend/src/components/cameras/CameraStepSummary.tsx`
- Test: `frontend/src/components/cameras/CameraWizard.test.tsx`
- Test: `frontend/src/pages/Cameras.test.tsx`

- [ ] **Step 1: Write the failing wizard tests for visual-first boundaries**

```tsx
test("creates a boundary without typing raw coordinates by default", async () => {
  renderWizard();

  await user.click(screen.getByRole("button", { name: /add line boundary/i }));
  expect(screen.getByText(/freeze the analytics frame and draw the boundary/i)).toBeInTheDocument();
  expect(screen.queryByLabelText(/boundary 1 x1/i)).not.toBeInTheDocument();
});
```

- [ ] **Step 2: Run the wizard tests to verify they fail**

Run: `corepack pnpm --dir frontend exec vitest run src/components/cameras/CameraWizard.test.tsx src/pages/Cameras.test.tsx`

Expected: FAIL because the wizard still exposes raw coordinate fields immediately.

- [ ] **Step 3: Rework the calibration step to make drawing the default path**

```tsx
<section className="space-y-4 rounded-[1.5rem] border border-white/10 bg-[#0b1320] p-4">
  <div className="flex items-center justify-between">
    <div>
      <h3 className="text-lg font-semibold text-[#f4f8ff]">Count boundaries</h3>
      <p className="text-sm text-[#93a7c5]">Freeze the analytics frame and draw the boundary directly on it.</p>
    </div>
    <Button onClick={() => setShowBoundaryAdvanced((current) => !current)}>
      {showBoundaryAdvanced ? "Hide advanced" : "Advanced"}
    </Button>
  </div>
  <BoundaryAuthoringCanvas ... />
</section>
```

- [ ] **Step 4: Update the review step to summarize operator-facing boundary facts**

```tsx
{ label: "Boundary", value: `${boundary.id} · ${boundary.type} · ${boundary.classNames || "all tracked classes"}` }
```

- [ ] **Step 5: Re-run the wizard and page tests**

Run: `corepack pnpm --dir frontend exec vitest run src/components/cameras/CameraWizard.test.tsx src/pages/Cameras.test.tsx`

Expected: PASS with visual-first setup and preserved review summaries.

- [ ] **Step 6: Commit**

```bash
git add frontend/src/components/cameras/CameraWizard.tsx frontend/src/components/cameras/CameraStepSummary.tsx frontend/src/components/cameras/CameraWizard.test.tsx frontend/src/pages/Cameras.test.tsx
git commit -m "feat: make boundary setup visual-first in camera wizard"
```

### Task 4: End-to-end verification and docs

**Files:**
- Modify: `docs/superpowers/specs/2026-04-26-operator-setup-history-delivery-hardening-design.md`
- Test: `backend/tests/services/test_camera_service.py`
- Test: `backend/tests/api/test_app.py`
- Test: `frontend/src/components/cameras/CameraWizard.test.tsx`
- Test: `frontend/src/components/cameras/HomographyEditor.test.tsx`

- [ ] **Step 1: Run the focused backend and frontend suites**

Run:

```bash
python3 -m uv run pytest backend/tests/services/test_camera_service.py backend/tests/api/test_app.py -q
corepack pnpm --dir frontend exec vitest run src/components/cameras/CameraWizard.test.tsx src/components/cameras/HomographyEditor.test.tsx src/pages/Cameras.test.tsx
```

Expected: PASS in both suites.

- [ ] **Step 2: Build the frontend to verify no canvas/type regressions**

Run: `corepack pnpm --dir frontend build`

Expected: PASS with no TypeScript errors.

- [ ] **Step 3: Commit the final polish**

```bash
git add docs/superpowers/specs/2026-04-26-operator-setup-history-delivery-hardening-design.md
git commit -m "docs: record boundary authoring implementation completion"
```
