# Verified Model Metadata And COCO-First Deployment Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make standard COCO-style ONNX models the safe default deployment path by verifying embedded class metadata at model registration time, preserving full model truth in `Model.classes`, and exposing persistent per-camera `active_classes` narrowing in the camera setup flow and docs.

**Architecture:** Add a small ONNX metadata extraction utility, route all model create/update writes through it, and reject mismatched operator-declared classes with a `422`. Keep query scope and worker filtering unchanged conceptually, but make them trustworthy by feeding them verified model inventories. Surface persistent `active_classes` in the camera wizard so deployments can be configured correctly without post-hoc API tweaks.

**Tech Stack:** FastAPI, Pydantic, SQLAlchemy service layer, ONNX Runtime, React, TanStack Query, Vitest, pytest, OpenAPI-generated TypeScript.

---

## File Structure

- Create: `backend/src/argus/vision/model_metadata.py`
  Purpose: Read embedded ONNX class metadata and resolve the final verified/declared class inventory.
- Create: `backend/tests/vision/test_model_metadata.py`
  Purpose: Unit-test metadata extraction and resolution behavior without a real ONNX file.
- Create: `backend/tests/services/test_model_service.py`
  Purpose: Verify `ModelService.create_model()` and `ModelService.update_model()` use metadata resolution correctly.
- Modify: `backend/src/argus/api/contracts.py`
  Purpose: Make `ModelCreate.classes` optional and keep `ModelUpdate.classes` optional for partial updates.
- Modify: `backend/src/argus/services/app.py`
  Purpose: Integrate model metadata resolution into `ModelService`; validate `Camera.active_classes` against the selected primary model inventory.
- Modify: `backend/tests/api/test_prompt5_routes.py`
  Purpose: Keep the route fakes aligned with optional model classes and route-level acceptance of self-describing models.
- Modify: `backend/tests/services/test_camera_service.py`
  Purpose: Cover `active_classes` subset validation on camera create/update.
- Modify: `backend/tests/services/test_camera_worker_config.py`
  Purpose: Preserve the invariant that worker config carries full model classes plus separate narrowed `active_classes`.
- Modify: `frontend/src/components/cameras/CameraWizard.tsx`
  Purpose: Add an operator-facing active-class picker tied to the selected primary model.
- Modify: `frontend/src/components/cameras/CameraStepSummary.tsx`
  Purpose: Show the chosen persistent class scope in the review step.
- Modify: `frontend/src/pages/Cameras.tsx`
  Purpose: Pass model class inventories into the wizard.
- Modify: `frontend/src/components/cameras/CameraWizard.test.tsx`
  Purpose: Cover active-class selection, submission, and review summary behavior.
- Modify: `frontend/src/pages/Cameras.test.tsx`
  Purpose: Cover the create flow with model inventories available to the wizard.
- Modify: `frontend/src/lib/api.generated.ts`
  Purpose: Regenerate client types after backend contract changes.
- Modify: `README.md`
  Purpose: Document the verified COCO-first registration contract.
- Modify: `docs/runbook.md`
  Purpose: Clarify that `models/` is just the file location and that ONNX metadata drives class truth.
- Modify: `docs/imac-master-orin-lab-test-guide.md`
  Purpose: Rewrite the default lab path around COCO-base registration plus camera `active_classes`, and move custom reduced-class models into an advanced section.

## Task 1: Add ONNX Metadata Extraction And Resolution

**Files:**
- Create: `backend/src/argus/vision/model_metadata.py`
- Test: `backend/tests/vision/test_model_metadata.py`

- [ ] **Step 1: Write the failing tests for embedded class extraction**

```python
from __future__ import annotations

import pytest
from fastapi import HTTPException

from argus.models.enums import ModelFormat
from argus.vision.model_metadata import extract_onnx_classes, resolve_model_classes


class _FakeModelMeta:
    def __init__(self, custom_metadata_map: dict[str, str]) -> None:
        self.custom_metadata_map = custom_metadata_map


class _FakeSession:
    def __init__(self, metadata: dict[str, str]) -> None:
        self._meta = _FakeModelMeta(metadata)

    def get_modelmeta(self) -> _FakeModelMeta:
        return self._meta


class _FakeRuntime:
    def __init__(self, metadata: dict[str, str]) -> None:
        self._metadata = metadata

    def InferenceSession(self, path: str, providers: list[str]) -> _FakeSession:  # noqa: N802
        assert path == "/models/yolo12n.onnx"
        assert providers == ["CPUExecutionProvider"]
        return _FakeSession(self._metadata)


def test_extract_onnx_classes_reads_embedded_dict_metadata() -> None:
    runtime = _FakeRuntime({"names": "{0: 'person', 1: 'bicycle', 2: 'car'}"})
    assert extract_onnx_classes("/models/yolo12n.onnx", runtime=runtime) == [
        "person",
        "bicycle",
        "car",
    ]


def test_extract_onnx_classes_returns_none_without_names() -> None:
    runtime = _FakeRuntime({})
    assert extract_onnx_classes("/models/yolo12n.onnx", runtime=runtime) is None


def test_resolve_model_classes_rejects_mismatch_for_self_describing_onnx() -> None:
    runtime = _FakeRuntime({"names": "{0: 'person', 1: 'bicycle', 2: 'car'}"})
    with pytest.raises(HTTPException) as exc_info:
        resolve_model_classes(
            path="/models/yolo12n.onnx",
            format=ModelFormat.ONNX,
            declared_classes=["person", "car"],
            runtime=runtime,
        )

    assert exc_info.value.status_code == 422
```

- [ ] **Step 2: Run the new test file to verify it fails**

Run:

```bash
cd /Users/yann.moren/vision/backend
python3 -m uv run pytest tests/vision/test_model_metadata.py -q
```

Expected: FAIL because `argus.vision.model_metadata` does not exist yet.

- [ ] **Step 3: Implement metadata extraction and resolution**

```python
from __future__ import annotations

import ast
import json
from typing import Any

from fastapi import HTTPException, status

from argus.models.enums import ModelFormat
from argus.vision.runtime import import_onnxruntime


def extract_onnx_classes(path: str, *, runtime: Any | None = None) -> list[str] | None:
    ort = runtime or import_onnxruntime()
    session = ort.InferenceSession(path, providers=["CPUExecutionProvider"])
    raw_names = session.get_modelmeta().custom_metadata_map.get("names")
    if not raw_names:
        return None

    parsed = _parse_names(raw_names)
    if isinstance(parsed, dict):
        return [str(parsed[index]) for index in sorted(parsed)]
    if isinstance(parsed, list):
        return [str(item) for item in parsed]
    return None


def resolve_model_classes(
    *,
    path: str,
    format: ModelFormat,
    declared_classes: list[str] | None,
    runtime: Any | None = None,
) -> tuple[list[str], str]:
    if format is not ModelFormat.ONNX:
        if declared_classes:
            return list(declared_classes), "declared"
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="classes are required for non-ONNX models.",
        )

    embedded_classes = extract_onnx_classes(path, runtime=runtime)
    if embedded_classes is None:
        if declared_classes:
            return list(declared_classes), "declared"
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="classes are required because this ONNX model does not expose embedded class metadata.",
        )

    if declared_classes is None:
        return embedded_classes, "embedded"
    if list(declared_classes) != embedded_classes:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Declared classes do not match the embedded ONNX class metadata.",
        )
    return embedded_classes, "embedded"


def _parse_names(raw_names: str) -> object:
    for parser in (json.loads, ast.literal_eval):
        try:
            return parser(raw_names)
        except Exception:
            continue
    return raw_names
```

- [ ] **Step 4: Run the tests again**

Run:

```bash
cd /Users/yann.moren/vision/backend
python3 -m uv run pytest tests/vision/test_model_metadata.py -q
```

Expected: PASS with `3 passed`.

- [ ] **Step 5: Commit**

```bash
git add backend/src/argus/vision/model_metadata.py backend/tests/vision/test_model_metadata.py
git commit -m "feat: extract verified onnx model metadata"
```

## Task 2: Enforce Verified Model Metadata In The Backend

**Files:**
- Modify: `backend/src/argus/api/contracts.py`
- Modify: `backend/src/argus/services/app.py`
- Create: `backend/tests/services/test_model_service.py`
- Modify: `backend/tests/api/test_prompt5_routes.py`
- Modify: `backend/tests/services/test_camera_service.py`
- Modify: `backend/tests/services/test_camera_worker_config.py`

- [ ] **Step 1: Write failing tests for model auto-population, mismatch rejection, and camera class validation**

```python
@pytest.mark.asyncio
async def test_create_model_uses_embedded_classes_when_request_omits_classes(monkeypatch):
    monkeypatch.setattr(app_services, "resolve_model_classes", lambda **_: (["person", "car"], "embedded"))
    service = ModelService(session_factory=_FakeSessionFactory(), audit_logger=_FakeAuditLogger())

    response = await service.create_model(
        ModelCreate(
            name="YOLO12n COCO iMac",
            version="lab-imac",
            task=ModelTask.DETECT,
            path="/models/yolo12n.onnx",
            format=ModelFormat.ONNX,
            classes=None,
            input_shape={"width": 640, "height": 640},
            sha256="a" * 64,
            size_bytes=1024,
            license="lab",
        )
    )

    assert response.classes == ["person", "car"]


@pytest.mark.asyncio
async def test_update_model_raises_when_declared_classes_disagree_with_embedded_metadata(monkeypatch):
    monkeypatch.setattr(
        app_services,
        "resolve_model_classes",
        lambda **_: (_ for _ in ()).throw(HTTPException(status_code=422, detail="Declared classes do not match the embedded ONNX class metadata.")),
    )
    with pytest.raises(HTTPException) as exc_info:
        await service.update_model(model_id, ModelUpdate(classes=["person", "car"]))

    assert exc_info.value.status_code == 422


@pytest.mark.asyncio
async def test_create_camera_rejects_active_classes_outside_primary_model_inventory(monkeypatch):
    payload = CameraCreate(..., active_classes=["car", "zebra"], ...)
    with pytest.raises(HTTPException) as exc_info:
        await service.create_camera(tenant_context, payload)

    assert exc_info.value.status_code == 422
```

- [ ] **Step 2: Run the backend tests to verify the new cases fail**

Run:

```bash
cd /Users/yann.moren/vision/backend
python3 -m uv run pytest tests/services/test_model_service.py tests/services/test_camera_service.py tests/api/test_prompt5_routes.py -q
```

Expected: FAIL because `ModelCreate.classes` is still required, `ModelService` does not resolve classes, and camera `active_classes` are not validated.

- [ ] **Step 3: Make `classes` optional in the contracts**

```python
class ModelCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    version: str = Field(min_length=1, max_length=64)
    task: ModelTask
    path: str = Field(min_length=1)
    format: ModelFormat
    classes: list[str] | None = Field(default=None, min_length=1)
    input_shape: dict[str, int]
    sha256: str = Field(min_length=64, max_length=64)
    size_bytes: int = Field(gt=0)
    license: str | None = Field(default=None, max_length=255)


class ModelUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    version: str | None = Field(default=None, min_length=1, max_length=64)
    task: ModelTask | None = None
    path: str | None = Field(default=None, min_length=1)
    format: ModelFormat | None = None
    classes: list[str] | None = Field(default=None, min_length=1)
```

- [ ] **Step 4: Integrate model resolution into `ModelService` and validate camera active classes**

```python
from argus.vision.model_metadata import resolve_model_classes


class ModelService:
    async def create_model(self, payload: ModelCreate) -> ModelResponse:
        resolved_classes, _ = resolve_model_classes(
            path=payload.path,
            format=payload.format,
            declared_classes=payload.classes,
        )
        async with self.session_factory() as session:
            model = Model(
                name=payload.name,
                version=payload.version,
                task=payload.task,
                path=payload.path,
                format=payload.format,
                classes=resolved_classes,
                input_shape=payload.input_shape,
                sha256=payload.sha256,
                size_bytes=payload.size_bytes,
                license=payload.license,
            )
            session.add(model)
            await session.commit()
            await session.refresh(model)
        return _model_to_response(model)

    async def update_model(self, model_id: UUID, payload: ModelUpdate) -> ModelResponse:
        async with self.session_factory() as session:
            model = await session.get(Model, model_id)
            if model is None:
                raise HTTPException(status_code=404, detail="Model not found.")

            update_data = payload.model_dump(exclude_unset=True)
            if {"path", "format", "classes"} & update_data.keys():
                resolved_classes, _ = resolve_model_classes(
                    path=update_data.get("path", model.path),
                    format=update_data.get("format", model.format),
                    declared_classes=update_data.get("classes", list(model.classes)),
                )
                update_data["classes"] = resolved_classes

            for field_name, value in update_data.items():
                setattr(model, field_name, value)
            await session.commit()
            await session.refresh(model)
        return _model_to_response(model)


def _validate_camera_active_classes(active_classes: list[str], allowed_classes: list[str]) -> None:
    invalid = [class_name for class_name in active_classes if class_name not in allowed_classes]
    if invalid:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"active_classes must be a subset of the primary model classes. Invalid values: {', '.join(invalid)}",
        )
```

Call `_validate_camera_active_classes(...)` from both `create_camera()` and `update_camera()` immediately after loading the primary model.

- [ ] **Step 5: Update the route fakes and worker-config coverage**

```python
class FakeModelService:
    async def create_model(self, payload: ModelCreate) -> ModelResponse:
        resolved_classes = payload.classes or ["person", "bicycle", "car"]
        model = ModelResponse(
            id=uuid4(),
            name=payload.name,
            version=payload.version,
            task=payload.task,
            path=payload.path,
            format=payload.format,
            classes=resolved_classes,
            input_shape=payload.input_shape,
            sha256=payload.sha256,
            size_bytes=payload.size_bytes,
            license=payload.license,
        )
        self.models[model.id] = model
        return model
```

Add one route test that omits `classes` from `POST /api/v1/models` and asserts `201`, and one worker-config test that confirms:

```python
assert config.model.classes == ["person", "bicycle", "car", "motorcycle"]
assert config.active_classes == ["car", "motorcycle"]
```

- [ ] **Step 6: Run the backend verification again**

Run:

```bash
cd /Users/yann.moren/vision/backend
python3 -m uv run pytest tests/vision/test_model_metadata.py tests/services/test_model_service.py tests/services/test_camera_service.py tests/services/test_camera_worker_config.py tests/api/test_prompt5_routes.py -q
python3 -m uv run ruff check src/argus/vision/model_metadata.py src/argus/services/app.py tests/vision/test_model_metadata.py tests/services/test_model_service.py tests/services/test_camera_service.py tests/services/test_camera_worker_config.py tests/api/test_prompt5_routes.py
```

Expected:
- pytest: PASS
- ruff: no findings

- [ ] **Step 7: Commit**

```bash
git add backend/src/argus/api/contracts.py backend/src/argus/services/app.py backend/tests/services/test_model_service.py backend/tests/services/test_camera_service.py backend/tests/services/test_camera_worker_config.py backend/tests/api/test_prompt5_routes.py
git commit -m "feat: verify model metadata during registration"
```

## Task 3: Expose Persistent Camera `active_classes` In The Wizard

**Files:**
- Modify: `frontend/src/pages/Cameras.tsx`
- Modify: `frontend/src/components/cameras/CameraWizard.tsx`
- Modify: `frontend/src/components/cameras/CameraStepSummary.tsx`
- Modify: `frontend/src/components/cameras/CameraWizard.test.tsx`
- Modify: `frontend/src/pages/Cameras.test.tsx`
- Modify: `frontend/src/lib/api.generated.ts`

- [ ] **Step 1: Write failing frontend tests for active-class selection**

```tsx
test("submits selected active classes with the create payload", async () => {
  const user = userEvent.setup();
  const onSubmit = vi.fn().mockResolvedValue(undefined);

  renderWizard({
    onSubmit,
    models: [
      {
        id: "model-1",
        name: "YOLO12n COCO",
        version: "lab-imac",
        classes: ["person", "car", "bus"],
      },
    ],
  });

  await user.type(screen.getByLabelText(/camera name/i), "Dock Camera");
  await user.selectOptions(screen.getByLabelText(/site/i), "site-1");
  await user.type(screen.getByLabelText(/rtsp url/i), "rtsp://camera.local/live");
  await user.click(screen.getByRole("button", { name: /next/i }));
  await user.selectOptions(screen.getByLabelText(/primary model/i), "model-1");
  await user.click(screen.getByLabelText(/car/i));
  await user.click(screen.getByLabelText(/bus/i));
  await user.click(screen.getByRole("button", { name: /next/i }));
  await user.click(screen.getByRole("button", { name: /next/i }));
  await user.click(screen.getByRole("button", { name: /next/i }));
  await user.click(screen.getByRole("button", { name: /create camera/i }));

  expect(onSubmit.mock.calls[0][0].active_classes).toEqual(["car", "bus"]);
});
```

- [ ] **Step 2: Run the wizard/page tests to verify they fail**

Run:

```bash
cd /Users/yann.moren/vision
corepack pnpm --dir frontend exec vitest run src/components/cameras/CameraWizard.test.tsx src/pages/Cameras.test.tsx
```

Expected: FAIL because the wizard model options do not carry `classes`, the wizard has no active-class picker, and the payload still hardcodes `active_classes: []`.

- [ ] **Step 3: Add the active-class picker and payload wiring**

```tsx
export type ModelOption = {
  id: string;
  name: string;
  version: string;
  classes: string[];
};

export type CameraWizardData = {
  // existing fields...
  activeClasses: string[];
};

function toCreatePayload(data: CameraWizardData): CreateCameraInput {
  return {
    // existing fields...
    active_classes: data.activeClasses,
  };
}

function toUpdatePayload(data: CameraWizardData): UpdateCameraInput {
  return {
    // existing fields...
    active_classes: data.activeClasses,
  };
}
```

Render the control in the “Models & Tracking” step using the selected primary model:

```tsx
const selectedPrimaryModel = models.find((model) => model.id === data.primaryModelId) ?? null;

<fieldset className="grid gap-3 text-sm text-[#d8e2f2]">
  <legend className="text-[11px] font-semibold uppercase tracking-[0.2em] text-[#8ea8cf]">
    Operational classes
  </legend>
  <p className="text-sm text-[#93a7c5]">
    Leave every box unchecked to use the full model inventory. Select classes to keep this camera focused on the operational categories you care about most.
  </p>
  <div className="grid gap-2 sm:grid-cols-2">
    {selectedPrimaryModel?.classes.map((className) => {
      const checked = data.activeClasses.includes(className);
      return (
        <label key={className} className="flex items-center gap-3 rounded-[1rem] border border-white/8 bg-[#0c1522] px-3 py-2">
          <input
            checked={checked}
            type="checkbox"
            aria-label={className}
            onChange={() =>
              updateData(
                "activeClasses",
                checked
                  ? data.activeClasses.filter((value) => value !== className)
                  : [...data.activeClasses, className],
              )
            }
          />
          <span>{className}</span>
        </label>
      );
    })}
  </div>
</fieldset>
```

Prune invalid selections when the primary model changes:

```tsx
useEffect(() => {
  if (!selectedPrimaryModel) {
    return;
  }
  setData((current) => ({
    ...current,
    activeClasses: current.activeClasses.filter((className) =>
      selectedPrimaryModel.classes.includes(className),
    ),
  }));
}, [selectedPrimaryModel]);
```

- [ ] **Step 4: Surface the selection in the review summary and pass classes through the page**

```tsx
// frontend/src/pages/Cameras.tsx
models={models.map((model) => ({
  id: model.id,
  name: model.name,
  version: model.version,
  classes: model.classes,
}))}

// frontend/src/components/cameras/CameraStepSummary.tsx
{ label: "Operational classes", value: data.activeClasses.length > 0 ? data.activeClasses.join(", ") : "all model classes" }
```

- [ ] **Step 5: Regenerate the API client after the backend contract change**

Run:

```bash
cd /Users/yann.moren/vision/frontend
corepack pnpm generate:api
```

Expected: `openapi-typescript ... -> src/lib/api.generated.ts`

- [ ] **Step 6: Run the frontend verification**

Run:

```bash
cd /Users/yann.moren/vision
corepack pnpm --dir frontend exec vitest run src/components/cameras/CameraWizard.test.tsx src/pages/Cameras.test.tsx
corepack pnpm --dir frontend lint
```

Expected:
- vitest: PASS
- eslint: no findings

- [ ] **Step 7: Commit**

```bash
git add frontend/src/components/cameras/CameraWizard.tsx frontend/src/components/cameras/CameraStepSummary.tsx frontend/src/components/cameras/CameraWizard.test.tsx frontend/src/pages/Cameras.tsx frontend/src/pages/Cameras.test.tsx frontend/src/lib/api.generated.ts
git commit -m "feat: configure camera active classes in setup"
```

## Task 4: Rewrite The Default Deployment Docs Around COCO-First Registration

**Files:**
- Modify: `README.md`
- Modify: `docs/runbook.md`
- Modify: `docs/imac-master-orin-lab-test-guide.md`

- [ ] **Step 1: Write the documentation changes as failing review criteria**

Document the acceptance criteria in the changed files:

```md
- standard `yolo12n.onnx` is described as a COCO model, not a six-class custom model
- model registration examples omit `classes` for self-describing ONNX models
- camera setup examples show persistent operational narrowing via `active_classes`
- custom six-class models are moved into an advanced optional section
```

- [ ] **Step 2: Update README and runbook language**

Use snippets like:

```md
- `models/`: local model file location for lab and development use. Standard ONNX detection models may embed their own class inventory; Vezor validates embedded metadata during model registration instead of assuming a reduced custom class list.
```

```md
1. Place the edge model weights under `/Users/yann.moren/vision/models/`.
2. Register the model with Vezor. For self-describing ONNX models, omit `classes` and let Vezor persist the embedded class inventory automatically.
3. Configure camera-level `active_classes` if the site should focus on a smaller operational subset than the full model inventory.
```

- [ ] **Step 3: Rewrite the iMac and Jetson model registration examples**

Replace the current model payloads with COCO-first examples:

```bash
IMAC_MODEL_ID="$(
  curl -s \
    -H "Authorization: Bearer $TOKEN" \
    -H "Content-Type: application/json" \
    -X POST \
    http://127.0.0.1:8000/api/v1/models \
    -d "{
      \"name\": \"YOLO12n COCO iMac\",
      \"version\": \"lab-imac\",
      \"task\": \"detect\",
      \"path\": \"$MODEL_PATH\",
      \"format\": \"onnx\",
      \"input_shape\": {\"width\": 640, \"height\": 640},
      \"sha256\": \"$MODEL_SHA\",
      \"size_bytes\": $MODEL_SIZE,
      \"license\": \"lab\"
    }" |
  python3 -c 'import json,sys; print(json.load(sys.stdin)[\"id\"])'
)"
```

```bash
EDGE_MODEL_ID="$(
  curl -s \
    -H "Authorization: Bearer $TOKEN" \
    -H "Content-Type: application/json" \
    -X POST \
    http://127.0.0.1:8000/api/v1/models \
    -d "{
      \"name\": \"YOLO12n COCO Edge\",
      \"version\": \"lab-edge\",
      \"task\": \"detect\",
      \"path\": \"/models/yolo12n.onnx\",
      \"format\": \"onnx\",
      \"input_shape\": {\"width\": 640, \"height\": 640},
      \"sha256\": \"$MODEL_SHA\",
      \"size_bytes\": $MODEL_SIZE,
      \"license\": \"lab\"
    }" |
  python3 -c 'import json,sys; print(json.load(sys.stdin)[\"id\"])'
)"
```

- [ ] **Step 4: Update the camera setup walkthrough to choose operational classes**

Replace the “Models & Tracking” instructions with:

```md
5. In **Models & Tracking**:
   - Primary model: `YOLO12n COCO iMac`
   - Tracker type: keep `botsort`
   - Secondary model: leave empty
   - Operational classes: select `person`, `car`, `bus`, `truck`, `motorcycle`, `bicycle`
```

Add an advanced section near the end:

```md
## Advanced: Registering A Custom Reduced-Class ONNX Model

Use this only if your team already has a custom-trained ONNX export whose embedded metadata matches the reduced class inventory you want to deploy. Do not treat a generic `yolo12n.onnx` file as a custom six-class model.
```

Add troubleshooting text:

```md
- If the model file is a standard COCO ONNX export but the model record was registered with a reduced class list, detections, query scope, and live overlays may fail or look nonsensical. Re-register the model or patch it so the stored model classes match the ONNX metadata.
```

- [ ] **Step 5: Run the focused verification and review the diff**

Run:

```bash
cd /Users/yann.moren/vision
git diff -- README.md docs/runbook.md docs/imac-master-orin-lab-test-guide.md
```

Expected: the diff removes manual six-class declarations from standard `yolo12n.onnx` model registration and moves them into an explicit advanced/custom section.

- [ ] **Step 6: Commit**

```bash
git add README.md docs/runbook.md docs/imac-master-orin-lab-test-guide.md
git commit -m "docs: make coco-first deployment the default"
```

## Task 5: Final Verification And Handoff

**Files:**
- Modify: none
- Verify: backend + frontend + docs from previous tasks

- [ ] **Step 1: Run the final backend verification set**

Run:

```bash
cd /Users/yann.moren/vision/backend
python3 -m uv run pytest tests/vision/test_model_metadata.py tests/services/test_model_service.py tests/services/test_camera_service.py tests/services/test_camera_worker_config.py tests/api/test_prompt5_routes.py -q
python3 -m uv run ruff check src/argus/api/contracts.py src/argus/services/app.py src/argus/vision/model_metadata.py tests/vision/test_model_metadata.py tests/services/test_model_service.py tests/services/test_camera_service.py tests/services/test_camera_worker_config.py tests/api/test_prompt5_routes.py
```

Expected: all tests pass and ruff is clean.

- [ ] **Step 2: Run the final frontend verification set**

Run:

```bash
cd /Users/yann.moren/vision
corepack pnpm --dir frontend generate:api
corepack pnpm --dir frontend exec vitest run src/components/cameras/CameraWizard.test.tsx src/pages/Cameras.test.tsx
corepack pnpm --dir frontend lint
```

Expected:
- OpenAPI client regeneration succeeds
- targeted vitest files pass
- lint is clean

- [ ] **Step 3: Sanity-check the documentation flow**

Review that the guide now supports this operator story:

```md
1. copy `yolo12n.onnx` into `models/`
2. register it without manually declaring a reduced class list
3. create/edit the camera
4. choose the six operational classes in the wizard
5. use Query Vezor later for temporary runtime narrowing
```

- [ ] **Step 4: Create the final completion commit**

```bash
git add backend frontend README.md docs
git commit -m "feat: verify coco metadata and narrow cameras by class"
```

## Self-Review

- Spec coverage: backend verification contract, camera class narrowing, COCO-first docs, and advanced custom-model separation are all covered.
- Placeholder scan: no `TBD`/`TODO`/“fill this in later” language remains.
- Type consistency: the plan consistently uses `active_classes` for camera narrowing and `classes` for model inventory, with `ModelCreate.classes` and `ModelUpdate.classes` changing to optional.
