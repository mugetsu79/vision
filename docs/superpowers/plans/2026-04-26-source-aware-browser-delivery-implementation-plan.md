# Source-Aware Browser Delivery Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make browser delivery truthful by probing source capability, suppressing invalid profiles like `1080p15` above a `720p` source, and clearly separating analytics ingest from browser native and browser rendition modes.

**Architecture:** Persist discovered source capability on the camera record, derive delivery profiles from those facts, and update the camera/live UI to explain native availability and degraded/fallback states instead of presenting a static profile catalog.

**Tech Stack:** FastAPI, SQLAlchemy, Alembic, Pydantic, React, TypeScript, Vitest, pytest.

---

## File Structure

- Create: `backend/src/argus/vision/source_probe.py`
  - Probe RTSP source width/height/fps/codec safely.
- Modify: `backend/src/argus/api/contracts.py`
  - Add `SourceCapability` and source-aware browser-delivery responses.
- Modify: `backend/src/argus/models/tables.py`
  - Add `source_capability` JSONB to `Camera`.
- Create: `backend/src/argus/migrations/versions/0005_source_capability.py`
  - Persist source capability metadata.
- Modify: `backend/src/argus/services/app.py`
  - Probe on create/update, derive allowed profiles, and expose native availability reasons.
- Test: `backend/tests/services/test_camera_worker_config.py`
  - Validate profile derivation and worker config selection.
- Test: `backend/tests/services/test_camera_service.py`
  - Validate source capability persistence.
- Modify: `frontend/src/components/cameras/CameraWizard.tsx`
  - Replace hardcoded profile options with API-driven capabilities.
- Modify: `frontend/src/pages/Cameras.tsx`
  - Show analytics ingest, browser native, and rendition capability separately.
- Modify: `frontend/src/pages/Live.tsx`
  - Explain native availability/fallback in the operator surface.
- Test: `frontend/src/components/cameras/CameraWizard.test.tsx`
- Test: `frontend/src/pages/Live.test.tsx`
- Test: `frontend/src/pages/Cameras.test.tsx`

### Task 1: Persist source capability and derive allowed profiles

**Files:**
- Create: `backend/src/argus/vision/source_probe.py`
- Modify: `backend/src/argus/models/tables.py`
- Create: `backend/src/argus/migrations/versions/0005_source_capability.py`
- Modify: `backend/src/argus/api/contracts.py`
- Modify: `backend/src/argus/services/app.py`
- Test: `backend/tests/services/test_camera_service.py`
- Test: `backend/tests/services/test_camera_worker_config.py`

- [ ] **Step 1: Write the failing backend tests for profile suppression**

```python
def test_source_capability_hides_1080p_above_720p_source():
    source = SourceCapability(width=1280, height=720, fps=20, codec="h264")

    profiles = derive_browser_profiles(source)

    assert [profile.id for profile in profiles.allowed] == ["native", "720p10", "540p5"]
    assert profiles.unsupported[0].id == "1080p15"
    assert profiles.unsupported[0].reason == "source_resolution_too_small"
```

- [ ] **Step 2: Run the backend tests to verify they fail**

Run: `python3 -m uv run pytest backend/tests/services/test_camera_service.py backend/tests/services/test_camera_worker_config.py -q`

Expected: FAIL because source capability and derived profiles do not exist yet.

- [ ] **Step 3: Add the source capability model, migration, and derivation helper**

```python
class SourceCapability(BaseModel):
    width: int = Field(gt=0)
    height: int = Field(gt=0)
    fps: int | None = Field(default=None, ge=1)
    codec: str | None = None
    aspect_ratio: str | None = None
```

```python
def derive_browser_profiles(source: SourceCapability) -> DerivedBrowserProfiles:
    allowed = [{"id": "native", "kind": "passthrough"}]
    unsupported = []
    for candidate in _default_browser_delivery_profiles():
      if candidate["id"] == "native":
          continue
      if candidate["w"] <= source.width and candidate["h"] <= source.height:
          allowed.append(candidate)
      else:
          unsupported.append({**candidate, "reason": "source_resolution_too_small"})
    return DerivedBrowserProfiles(allowed=allowed, unsupported=unsupported)
```

- [ ] **Step 4: Probe source capability during camera create/update**

```python
source_capability = await probe_rtsp_source(payload.rtsp_url, settings=self.settings)
camera.source_capability = source_capability.model_dump(mode="python")
camera.browser_delivery = build_browser_delivery_settings(source_capability, payload.browser_delivery)
```

- [ ] **Step 5: Re-run the backend tests**

Run: `python3 -m uv run pytest backend/tests/services/test_camera_service.py backend/tests/services/test_camera_worker_config.py -q`

Expected: PASS with derived profile filtering and source metadata persistence.

- [ ] **Step 6: Commit**

```bash
git add backend/src/argus/vision/source_probe.py backend/src/argus/models/tables.py backend/src/argus/migrations/versions/0005_source_capability.py backend/src/argus/api/contracts.py backend/src/argus/services/app.py backend/tests/services/test_camera_service.py backend/tests/services/test_camera_worker_config.py
git commit -m "feat: persist source capability and derive valid delivery profiles"
```

### Task 2: Replace static delivery options in the camera wizard

**Files:**
- Modify: `frontend/src/components/cameras/CameraWizard.tsx`
- Modify: `frontend/src/pages/Cameras.tsx`
- Test: `frontend/src/components/cameras/CameraWizard.test.tsx`
- Test: `frontend/src/pages/Cameras.test.tsx`

- [ ] **Step 1: Write the failing frontend tests for disabled unsupported profiles**

```tsx
test("does not offer 1080p when source capability is only 1280x720", async () => {
  renderWizard({
    initialCamera: {
      ...camera,
      source_capability: { width: 1280, height: 720, fps: 20, codec: "h264" },
      browser_delivery: {
        default_profile: "720p10",
        allowed_profiles: ["native", "720p10", "540p5"],
        unsupported_profiles: [{ id: "1080p15", reason: "source_resolution_too_small" }],
      },
    },
  });

  expect(screen.queryByRole("option", { name: "1080p15" })).not.toBeInTheDocument();
  expect(screen.getByText(/source is 1280×720, so 1080p is unavailable/i)).toBeInTheDocument();
});
```

- [ ] **Step 2: Run the frontend tests to verify they fail**

Run: `corepack pnpm --dir frontend exec vitest run src/components/cameras/CameraWizard.test.tsx src/pages/Cameras.test.tsx`

Expected: FAIL because the wizard still uses a static union of four profiles.

- [ ] **Step 3: Replace the static profile union with API-driven profile lists**

```tsx
const availableProfiles = data.browserDelivery.profiles.filter((profile) => profile.supported);

<Select
  aria-label="Browser delivery profile"
  value={data.browserDeliveryProfile}
  onChange={(event) => updateBrowserDeliveryProfile(event.target.value)}
>
  {availableProfiles.map((profile) => (
    <option key={profile.id} value={profile.id}>
      {profile.id}
    </option>
  ))}
</Select>
```

- [ ] **Step 4: Surface source capability on the cameras index**

```tsx
<TD>
  <div className="text-[#eef4ff]">{camera.browser_delivery?.default_profile ?? "720p10"}</div>
  <div className="text-xs text-[#93a7c5]">
    source {camera.source_capability?.width}×{camera.source_capability?.height}
  </div>
</TD>
```

- [ ] **Step 5: Re-run the frontend tests**

Run: `corepack pnpm --dir frontend exec vitest run src/components/cameras/CameraWizard.test.tsx src/pages/Cameras.test.tsx`

Expected: PASS with source-aware profile rendering.

- [ ] **Step 6: Commit**

```bash
git add frontend/src/components/cameras/CameraWizard.tsx frontend/src/pages/Cameras.tsx frontend/src/components/cameras/CameraWizard.test.tsx frontend/src/pages/Cameras.test.tsx
git commit -m "feat: make browser delivery options source-aware"
```

### Task 3: Explain native availability and fallback states in live operations

**Files:**
- Modify: `frontend/src/pages/Live.tsx`
- Modify: `backend/src/argus/api/contracts.py`
- Modify: `backend/src/argus/services/app.py`
- Test: `frontend/src/pages/Live.test.tsx`

- [ ] **Step 1: Write the failing live-page test for native availability reasons**

```tsx
test("shows why native is unavailable for a processed stream", async () => {
  mockCamera({
    browser_delivery: {
      default_profile: "720p10",
      native_status: { available: false, reason: "processed_stream_only" },
    },
  });

  renderLivePage();

  expect(screen.getByText(/native unavailable: processed stream only/i)).toBeInTheDocument();
});
```

- [ ] **Step 2: Run the live-page tests to verify they fail**

Run: `corepack pnpm --dir frontend exec vitest run src/pages/Live.test.tsx`

Expected: FAIL because live tiles do not expose native status reasons.

- [ ] **Step 3: Add native availability metadata and render it**

```python
class NativeAvailability(BaseModel):
    available: bool
    reason: str | None = None
```

```tsx
{camera.browser_delivery?.native_status?.available === false ? (
  <p className="text-xs text-[#ffd28a]">
    Native unavailable: {camera.browser_delivery.native_status.reason.replaceAll("_", " ")}
  </p>
) : null}
```

- [ ] **Step 4: Re-run the live-page tests**

Run: `corepack pnpm --dir frontend exec vitest run src/pages/Live.test.tsx`

Expected: PASS with explicit native/fallback copy.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/pages/Live.tsx frontend/src/pages/Live.test.tsx backend/src/argus/api/contracts.py backend/src/argus/services/app.py
git commit -m "feat: explain native delivery availability in live ui"
```

### Task 4: Migration and verification

**Files:**
- Test: `backend/tests/services/test_camera_service.py`
- Test: `backend/tests/services/test_camera_worker_config.py`
- Test: `frontend/src/components/cameras/CameraWizard.test.tsx`
- Test: `frontend/src/pages/Cameras.test.tsx`
- Test: `frontend/src/pages/Live.test.tsx`

- [ ] **Step 1: Run the migration locally**

Run: `python3 -m uv run alembic upgrade head`

Expected: PASS with the new `source_capability` column present.

- [ ] **Step 2: Run focused verification**

Run:

```bash
python3 -m uv run pytest backend/tests/services/test_camera_service.py backend/tests/services/test_camera_worker_config.py -q
corepack pnpm --dir frontend exec vitest run src/components/cameras/CameraWizard.test.tsx src/pages/Cameras.test.tsx src/pages/Live.test.tsx
```

Expected: PASS.

- [ ] **Step 3: Build the frontend**

Run: `corepack pnpm --dir frontend build`

Expected: PASS.

- [ ] **Step 4: Commit final polish**

```bash
git add docs/superpowers/specs/2026-04-26-operator-setup-history-delivery-hardening-design.md
git commit -m "docs: record source-aware delivery implementation completion"
```
