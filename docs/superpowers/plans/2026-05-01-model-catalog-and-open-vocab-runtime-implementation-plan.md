# Model Catalog And Open-Vocab Runtime Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

> **Status:** Completed on 2026-05-02 on branch `model-catalog-open-vocab-runtime`. This file is now historical implementation scaffolding; unchecked boxes below reflect the original plan format, not remaining Stream 1 work. The validated Jetson TensorRT artifact and compiled scene open-vocab follow-up has also landed in `docs/superpowers/plans/2026-05-10-jetson-optimized-runtime-artifacts-and-open-vocab-implementation-plan.md`.

**Goal:** Add recommended model catalog options, Jetson-aware runtime selection, and a true Ultralytics-backed open-vocabulary detector path while preserving the current fixed-vocab video pipeline.

**Architecture:** Keep registered `Model` rows as the canonical selectable inventory. Add a typed catalog as a registration aid, extend model capability config enough to validate runtime backends, add Jetson NVIDIA host classification, and introduce an Ultralytics open-vocab detector adapter selected by `DetectorCapability.OPEN_VOCAB` plus `runtime_backend`.

**Tech Stack:** FastAPI, Pydantic, SQLAlchemy async, Alembic, PostgreSQL, ONNX Runtime, Ultralytics, OpenCV, React, TypeScript, TanStack Query, Vitest, Playwright.

---

## File Map

- `backend/src/argus/models/enums.py`
  - Add `ModelFormat.PT` and Jetson execution profile enum support.
- `backend/src/argus/migrations/versions/0008_model_catalog_open_vocab_runtime.py`
  - Add `pt` to the Postgres `model_format_enum`.
- `backend/src/argus/api/contracts.py`
  - Add model catalog response contracts and structured runtime backend metadata.
- `backend/src/argus/services/app.py`
  - Validate model format, capability, and runtime backend combinations during create/update.
- `backend/src/argus/services/model_catalog.py`
  - Create typed recommended model catalog and status resolution against registered models.
- `backend/src/argus/api/v1/model_catalog.py`
  - Add `GET /api/v1/model-catalog`.
- `backend/src/argus/api/v1/__init__.py`
  - Include the model catalog router.
- `backend/src/argus/vision/runtime.py`
  - Add Jetson ARM64 NVIDIA host classification and provider priority.
- `backend/src/argus/vision/open_vocab_detector.py`
  - Replace the current YOLO-wrapper behavior with an Ultralytics-backed adapter.
- `backend/src/argus/vision/detector_factory.py`
  - Select fixed-vocab ONNX Runtime or open-vocab Ultralytics backend.
- `backend/src/argus/inference/engine.py`
  - Preserve hot runtime vocabulary updates and add runtime state logging for open-vocab backends.
- `backend/scripts/register_model_preset.py`
  - Create an API helper to register a catalog preset using a local model artifact.
- `backend/tests/services/test_model_service.py`
  - Cover model validation rules.
- `backend/tests/services/test_model_catalog.py`
  - Cover catalog shape and registered status.
- `backend/tests/api/test_model_catalog_routes.py`
  - Cover catalog endpoint authorization and response shape.
- `backend/tests/vision/test_runtime.py`
  - Cover Jetson runtime classification.
- `backend/tests/vision/test_open_vocab_detector.py`
  - Cover fake Ultralytics detector load, vocabulary updates, and normalized output.
- `backend/tests/vision/test_detector_factory.py`
  - Cover backend selection by capability/config.
- `backend/tests/inference/test_engine.py`
  - Cover runtime vocabulary command hot-swap with the real detector protocol.
- `frontend/src/lib/api.generated.ts`
  - Regenerate after backend OpenAPI changes.
- `frontend/src/hooks/use-model-catalog.ts`
  - Fetch catalog entries for model inventory hints.
- `frontend/src/pages/Cameras.tsx`
  - Pass model capability/config through and optionally show catalog status near setup.
- `frontend/src/components/cameras/CameraWizard.tsx`
  - Display capability/backend/readiness badges and keep open-vocab vocabulary editor behavior.
- `frontend/src/components/cameras/CameraWizard.test.tsx`
  - Cover fixed-vocab versus open-vocab UI states.
- `frontend/src/pages/Cameras.test.tsx`
  - Cover model catalog inventory hints and registered model metadata passthrough.
- `docs/imac-master-orin-lab-test-guide.md`
  - Update from YOLO12-only guidance to recommended YOLO26/YOLO11/YOLO12 catalog choices.
- `docs/runbook.md`
  - Document catalog, local artifacts, open-vocab readiness, and raw TensorRT engine limits.

## Task 1: Extend Model Contracts And Validation

**Files:**
- Modify: `backend/src/argus/models/enums.py`
- Create: `backend/src/argus/migrations/versions/0008_model_catalog_open_vocab_runtime.py`
- Modify: `backend/src/argus/api/contracts.py`
- Modify: `backend/src/argus/services/app.py`
- Test: `backend/tests/services/test_model_service.py`

- [ ] **Step 1: Write failing model validation tests**

Add these tests to `backend/tests/services/test_model_service.py`:

```python
@pytest.mark.asyncio
async def test_create_open_vocab_ultralytics_model_requires_pt_format() -> None:
    service = ModelService(session_factory=_FakeSessionFactory(), audit_logger=_FakeAuditLogger())

    with pytest.raises(HTTPException) as exc_info:
        await service.create_model(
            ModelCreate(
                name="YOLOE-26N Open Vocab",
                version="2026.1",
                task=ModelTask.DETECT,
                path="/models/yoloe-26n-seg.onnx",
                format=ModelFormat.ONNX,
                capability=DetectorCapability.OPEN_VOCAB,
                capability_config={
                    "supports_runtime_vocabulary_updates": True,
                    "max_runtime_terms": 32,
                    "prompt_format": "labels",
                    "runtime_backend": "ultralytics_yoloe",
                    "model_family": "yoloe",
                    "readiness": "experimental",
                    "requires_gpu": True,
                },
                classes=[],
                input_shape={"width": 640, "height": 640},
                sha256="b" * 64,
                size_bytes=123456,
                license="AGPL-3.0",
            )
        )

    assert exc_info.value.status_code == 422
    assert "requires format=pt" in str(exc_info.value.detail)


@pytest.mark.asyncio
async def test_create_open_vocab_ultralytics_model_accepts_pt_format() -> None:
    session_factory = _FakeSessionFactory()
    service = ModelService(session_factory=session_factory, audit_logger=_FakeAuditLogger())

    response = await service.create_model(
        ModelCreate(
            name="YOLOE-26N Open Vocab",
            version="2026.1",
            task=ModelTask.DETECT,
            path="/models/yoloe-26n-seg.pt",
            format=ModelFormat.PT,
            capability=DetectorCapability.OPEN_VOCAB,
            capability_config={
                "supports_runtime_vocabulary_updates": True,
                "max_runtime_terms": 32,
                "prompt_format": "labels",
                "runtime_backend": "ultralytics_yoloe",
                "model_family": "yoloe",
                "readiness": "experimental",
                "requires_gpu": True,
                "execution_profiles": ["linux-aarch64-nvidia-jetson", "linux-x86_64-nvidia"],
            },
            classes=[],
            input_shape={"width": 640, "height": 640},
            sha256="c" * 64,
            size_bytes=123456,
            license="AGPL-3.0",
        )
    )

    assert response.format == ModelFormat.PT
    assert response.capability == DetectorCapability.OPEN_VOCAB
    assert response.capability_config.runtime_backend == "ultralytics_yoloe"
    assert session_factory.state["model"].classes == []


@pytest.mark.asyncio
async def test_create_engine_model_rejects_ready_tensorrt_backend_until_supported() -> None:
    service = ModelService(session_factory=_FakeSessionFactory(), audit_logger=_FakeAuditLogger())

    with pytest.raises(HTTPException) as exc_info:
        await service.create_model(
            ModelCreate(
                name="YOLO26n TensorRT",
                version="2026.1",
                task=ModelTask.DETECT,
                path="/models/yolo26n.engine",
                format=ModelFormat.ENGINE,
                capability=DetectorCapability.FIXED_VOCAB,
                capability_config={
                    "runtime_backend": "tensorrt_engine",
                    "readiness": "ready",
                    "model_family": "yolo26",
                },
                classes=["person", "car"],
                input_shape={"width": 640, "height": 640},
                sha256="d" * 64,
                size_bytes=123456,
                license="AGPL-3.0",
            )
        )

    assert exc_info.value.status_code == 422
    assert "TensorRT engine detector is not implemented" in str(exc_info.value.detail)
```

- [ ] **Step 2: Run the focused tests and confirm failure**

Run:

```bash
cd /Users/yann.moren/vision/backend
python3 -m uv run pytest tests/services/test_model_service.py -q -k "open_vocab_ultralytics or engine_model"
```

Expected: tests fail because `ModelFormat.PT` and runtime backend validation do not exist.

- [ ] **Step 3: Add `pt` model format**

Modify `backend/src/argus/models/enums.py`:

```python
class ModelFormat(StrEnum):
    ONNX = "onnx"
    ENGINE = "engine"
    PT = "pt"
```

Create `backend/src/argus/migrations/versions/0008_model_catalog_open_vocab_runtime.py`:

```python
"""model catalog open vocab runtime

Revision ID: 0008_model_catalog_open_vocab_runtime
Revises: 0007_incident_review_state
Create Date: 2026-05-01
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op

revision = "0008_model_catalog_open_vocab_runtime"
down_revision = "0007_incident_review_state"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    op.execute("ALTER TYPE model_format_enum ADD VALUE IF NOT EXISTS 'pt'")


def downgrade() -> None:
    # PostgreSQL enum value removal is intentionally not attempted.
    pass
```

- [ ] **Step 4: Extend capability config contract**

Modify `backend/src/argus/api/contracts.py`:

```python
class ModelCapabilityConfig(BaseModel):
    supports_runtime_vocabulary_updates: bool = False
    max_runtime_terms: int | None = None
    prompt_format: Literal["labels", "phrases"] | None = None
    execution_profiles: list[str] = Field(default_factory=list)
    model_family: Literal["yolo11", "yolo12", "yolo26", "yolo_world", "yoloe"] | None = None
    runtime_backend: (
        Literal["onnxruntime", "ultralytics_yolo_world", "ultralytics_yoloe", "tensorrt_engine"]
        | None
    ) = None
    readiness: Literal["ready", "experimental", "planned"] | None = None
    recommended_profiles: list[str] = Field(default_factory=list)
    requires_gpu: bool = False
    supports_masks: bool = False
    source_url: str | None = None
```

- [ ] **Step 5: Add runtime backend validation**

In `backend/src/argus/services/app.py`, add a helper near `_resolve_model_classes_for_capability`:

```python
def _validate_model_runtime_backend(
    *,
    capability: DetectorCapability,
    format: ModelFormat,
    capability_config: dict[str, object],
) -> None:
    backend = str(capability_config.get("runtime_backend") or "onnxruntime")
    readiness = str(capability_config.get("readiness") or "ready")

    if backend == "onnxruntime" and format is not ModelFormat.ONNX:
        raise HTTPException(
            status_code=HTTP_422_UNPROCESSABLE,
            detail="runtime_backend=onnxruntime requires format=onnx.",
        )

    if backend in {"ultralytics_yolo_world", "ultralytics_yoloe"}:
        if capability is not DetectorCapability.OPEN_VOCAB:
            raise HTTPException(
                status_code=HTTP_422_UNPROCESSABLE,
                detail=f"runtime_backend={backend} requires capability=open_vocab.",
            )
        if format is not ModelFormat.PT:
            raise HTTPException(
                status_code=HTTP_422_UNPROCESSABLE,
                detail=f"runtime_backend={backend} requires format=pt.",
            )

    if backend == "tensorrt_engine" and readiness == "ready":
        raise HTTPException(
            status_code=HTTP_422_UNPROCESSABLE,
            detail="TensorRT engine detector is not implemented; use readiness=planned.",
        )
```

Call this helper at the top of `_resolve_model_classes_for_capability(...)`:

```python
_validate_model_runtime_backend(
    capability=capability,
    format=format,
    capability_config=capability_config,
)
```

- [ ] **Step 6: Run model service tests**

Run:

```bash
cd /Users/yann.moren/vision/backend
python3 -m uv run pytest tests/services/test_model_service.py -q
```

Expected: all model service tests pass.

- [ ] **Step 7: Commit Task 1**

Run:

```bash
git add backend/src/argus/models/enums.py \
  backend/src/argus/migrations/versions/0008_model_catalog_open_vocab_runtime.py \
  backend/src/argus/api/contracts.py \
  backend/src/argus/services/app.py \
  backend/tests/services/test_model_service.py
git commit -m "feat(models): validate open vocab runtime backends"
```

## Task 2: Add Recommended Model Catalog API

**Files:**
- Create: `backend/src/argus/services/model_catalog.py`
- Create: `backend/src/argus/api/v1/model_catalog.py`
- Modify: `backend/src/argus/api/v1/__init__.py`
- Modify: `backend/src/argus/api/contracts.py`
- Modify: `backend/src/argus/services/app.py`
- Test: `backend/tests/services/test_model_catalog.py`
- Test: `backend/tests/api/test_model_catalog_routes.py`

- [ ] **Step 1: Write catalog service tests**

Create `backend/tests/services/test_model_catalog.py`:

```python
from __future__ import annotations

from uuid import uuid4

from argus.models.enums import DetectorCapability, ModelFormat, ModelTask
from argus.models.tables import Model
from argus.services.model_catalog import list_model_catalog_entries, resolve_catalog_status


def test_catalog_contains_recommended_fixed_vocab_models() -> None:
    entries = list_model_catalog_entries()
    ids = {entry.id for entry in entries}

    assert "yolo26n-coco-onnx" in ids
    assert "yolo26s-coco-onnx" in ids
    assert "yolo11n-coco-onnx" in ids
    assert "yolo11s-coco-onnx" in ids
    assert "yolo12n-coco-onnx" in ids


def test_catalog_marks_open_vocab_presets_experimental() -> None:
    entries = {entry.id: entry for entry in list_model_catalog_entries()}

    assert entries["yoloe-26n-open-vocab-pt"].capability is DetectorCapability.OPEN_VOCAB
    assert entries["yoloe-26n-open-vocab-pt"].format is ModelFormat.PT
    assert entries["yoloe-26n-open-vocab-pt"].capability_config.readiness == "experimental"
    assert entries["yolov8s-worldv2-open-vocab-pt"].capability_config.runtime_backend == (
        "ultralytics_yolo_world"
    )


def test_catalog_status_matches_registered_model_by_catalog_id(tmp_path) -> None:
    model_path = tmp_path / "yolo26n.onnx"
    model_path.write_bytes(b"fake")
    registered_model = Model(
        id=uuid4(),
        name="YOLO26n COCO",
        version="2026.1",
        task=ModelTask.DETECT,
        path=str(model_path),
        format=ModelFormat.ONNX,
        capability=DetectorCapability.FIXED_VOCAB,
        capability_config={
            "catalog_id": "yolo26n-coco-onnx",
            "runtime_backend": "onnxruntime",
            "readiness": "ready",
        },
        classes=["person", "car"],
        input_shape={"width": 640, "height": 640},
        sha256="a" * 64,
        size_bytes=4,
        license="AGPL-3.0",
    )

    status = resolve_catalog_status([registered_model])
    yolo26n = next(entry for entry in status if entry.id == "yolo26n-coco-onnx")

    assert yolo26n.registered_model_id == registered_model.id
    assert yolo26n.artifact_exists is True
    assert yolo26n.registration_state == "registered"
```

- [ ] **Step 2: Run catalog tests and confirm failure**

Run:

```bash
cd /Users/yann.moren/vision/backend
python3 -m uv run pytest tests/services/test_model_catalog.py -q
```

Expected: import failure because the catalog service does not exist.

- [ ] **Step 3: Add catalog response contracts**

In `backend/src/argus/api/contracts.py`, add:

```python
class ModelCatalogRegistrationState(StrEnum):
    UNREGISTERED = "unregistered"
    REGISTERED = "registered"
    MISSING_ARTIFACT = "missing_artifact"
    PLANNED = "planned"


class ModelCatalogEntryResponse(BaseModel):
    id: str
    name: str
    version: str
    task: ModelTask
    path_hint: str
    format: ModelFormat
    capability: DetectorCapability
    capability_config: ModelCapabilityConfig
    classes: list[str] = Field(default_factory=list)
    input_shape: dict[str, int]
    sha256: str | None = None
    size_bytes: int | None = None
    license: str | None = None
    registration_state: ModelCatalogRegistrationState
    registered_model_id: UUID | None = None
    artifact_exists: bool = False
    note: str
```

Move the new enum import if the file needs `StrEnum`:

```python
from enum import StrEnum
```

- [ ] **Step 4: Implement catalog service**

Create `backend/src/argus/services/model_catalog.py`:

```python
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from uuid import UUID

from argus.api.contracts import ModelCapabilityConfig, ModelCatalogEntryResponse
from argus.models.enums import DetectorCapability, ModelFormat, ModelTask
from argus.models.tables import Model


@dataclass(frozen=True, slots=True)
class ModelCatalogEntry:
    id: str
    name: str
    version: str
    task: ModelTask
    path_hint: str
    format: ModelFormat
    capability: DetectorCapability
    capability_config: ModelCapabilityConfig
    classes: tuple[str, ...]
    input_shape: dict[str, int]
    license: str
    note: str


def list_model_catalog_entries() -> list[ModelCatalogEntry]:
    return [
        _fixed("yolo26n-coco-onnx", "YOLO26n COCO", "2026.1", "yolo26", "models/yolo26n.onnx", "Default fast detector."),
        _fixed("yolo26s-coco-onnx", "YOLO26s COCO", "2026.1", "yolo26", "models/yolo26s.onnx", "Balanced accuracy and speed."),
        _fixed("yolo11n-coco-onnx", "YOLO11n COCO", "2024.9", "yolo11", "models/yolo11n.onnx", "Stable fast fallback."),
        _fixed("yolo11s-coco-onnx", "YOLO11s COCO", "2024.9", "yolo11", "models/yolo11s.onnx", "Stable balanced fallback."),
        _fixed("yolo12n-coco-onnx", "YOLO12n COCO", "2025.2", "yolo12", "models/yolo12n.onnx", "Current lab compatibility option."),
        _open_vocab(
            "yoloe-26n-open-vocab-pt",
            "YOLOE-26N Open Vocab",
            "2026.1",
            "yoloe",
            "models/yoloe-26n-seg.pt",
            "ultralytics_yoloe",
            "Preferred experimental open-vocab lab path.",
        ),
        _open_vocab(
            "yoloe-26s-open-vocab-pt",
            "YOLOE-26S Open Vocab",
            "2026.1",
            "yoloe",
            "models/yoloe-26s-seg.pt",
            "ultralytics_yoloe",
            "Higher quality experimental open-vocab path.",
        ),
        _open_vocab(
            "yolov8s-worldv2-open-vocab-pt",
            "YOLOv8s-Worldv2 Open Vocab",
            "2024.1",
            "yolo_world",
            "models/yolov8s-worldv2.pt",
            "ultralytics_yolo_world",
            "Smaller experimental open-vocab fallback.",
        ),
    ]


def resolve_catalog_status(models: list[Model]) -> list[ModelCatalogEntryResponse]:
    registered_by_catalog_id = {
        str((model.capability_config or {}).get("catalog_id")): model
        for model in models
        if (model.capability_config or {}).get("catalog_id")
    }
    responses: list[ModelCatalogEntryResponse] = []
    for entry in list_model_catalog_entries():
        registered = registered_by_catalog_id.get(entry.id)
        artifact_path = Path(registered.path if registered is not None else entry.path_hint)
        readiness = entry.capability_config.readiness or "ready"
        if readiness == "planned":
            state = "planned"
        elif registered is None:
            state = "unregistered"
        elif artifact_path.exists():
            state = "registered"
        else:
            state = "missing_artifact"
        responses.append(
            ModelCatalogEntryResponse(
                id=entry.id,
                name=entry.name,
                version=entry.version,
                task=entry.task,
                path_hint=entry.path_hint,
                format=entry.format,
                capability=entry.capability,
                capability_config=entry.capability_config,
                classes=list(entry.classes),
                input_shape=entry.input_shape,
                license=entry.license,
                registration_state=state,
                registered_model_id=UUID(str(registered.id)) if registered is not None else None,
                artifact_exists=artifact_path.exists(),
                note=entry.note,
            )
        )
    return responses


def _fixed(
    id: str,
    name: str,
    version: str,
    family: str,
    path_hint: str,
    note: str,
) -> ModelCatalogEntry:
    return ModelCatalogEntry(
        id=id,
        name=name,
        version=version,
        task=ModelTask.DETECT,
        path_hint=path_hint,
        format=ModelFormat.ONNX,
        capability=DetectorCapability.FIXED_VOCAB,
        capability_config=ModelCapabilityConfig(
            model_family=family,
            runtime_backend="onnxruntime",
            readiness="ready",
            execution_profiles=[
                "linux-x86_64-nvidia",
                "linux-aarch64-nvidia-jetson",
                "linux-x86_64-intel",
                "macos-x86_64-intel",
                "macos-arm64-apple-silicon",
            ],
        ),
        classes=(),
        input_shape={"width": 640, "height": 640},
        license="AGPL-3.0",
        note=note,
    )


def _open_vocab(
    id: str,
    name: str,
    version: str,
    family: str,
    path_hint: str,
    backend: str,
    note: str,
) -> ModelCatalogEntry:
    return ModelCatalogEntry(
        id=id,
        name=name,
        version=version,
        task=ModelTask.DETECT,
        path_hint=path_hint,
        format=ModelFormat.PT,
        capability=DetectorCapability.OPEN_VOCAB,
        capability_config=ModelCapabilityConfig(
            supports_runtime_vocabulary_updates=True,
            max_runtime_terms=32,
            prompt_format="labels",
            model_family=family,
            runtime_backend=backend,
            readiness="experimental",
            requires_gpu=True,
            supports_masks=family == "yoloe",
            execution_profiles=["linux-x86_64-nvidia", "linux-aarch64-nvidia-jetson"],
        ),
        classes=(),
        input_shape={"width": 640, "height": 640},
        license="AGPL-3.0",
        note=note,
    )
```

- [ ] **Step 5: Add catalog route**

Add a method to `ModelService` in `backend/src/argus/services/app.py`:

```python
async def list_catalog_status(self) -> list[ModelCatalogEntryResponse]:
    async with self.session_factory() as session:
        models = (await session.execute(select(Model))).scalars().all()
    return resolve_catalog_status(list(models))
```

Add imports near the existing model imports:

```python
from argus.api.contracts import ModelCatalogEntryResponse
from argus.services.model_catalog import resolve_catalog_status
```

Create `backend/src/argus/api/v1/model_catalog.py`:

```python
from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends

from argus.api.contracts import ModelCatalogEntryResponse
from argus.api.dependencies import get_app_services
from argus.core.security import AuthenticatedUser, require
from argus.models.enums import RoleEnum
from argus.services.app import AppServices

router = APIRouter(prefix="/api/v1/model-catalog", tags=["model-catalog"])
ViewerUser = Annotated[AuthenticatedUser, Depends(require(RoleEnum.VIEWER))]
ServicesDependency = Annotated[AppServices, Depends(get_app_services)]


@router.get("", response_model=list[ModelCatalogEntryResponse])
async def list_model_catalog(
    current_user: ViewerUser,
    services: ServicesDependency,
) -> list[ModelCatalogEntryResponse]:
    return await services.models.list_catalog_status()
```

- [ ] **Step 6: Include route**

Modify `backend/src/argus/api/v1/__init__.py`:

```python
from argus.api.v1 import (
    cameras,
    edge,
    export,
    history,
    incidents,
    model_catalog,
    models,
    operations,
    query,
    sites,
    streams,
    system,
    telemetry_ws,
)

router.include_router(model_catalog.router)
```

- [ ] **Step 7: Write route test**

Create `backend/tests/api/test_model_catalog_routes.py`:

```python
from __future__ import annotations

from types import SimpleNamespace
from uuid import uuid4

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from argus.api.contracts import ModelCatalogEntryResponse, TenantContext
from argus.api.v1 import router
from argus.core.security import AuthenticatedUser
from argus.models.enums import DetectorCapability, ModelFormat, ModelTask, RoleEnum


def _tenant_context() -> TenantContext:
    return TenantContext(
        tenant_id=uuid4(),
        tenant_slug="argus-dev",
        user=AuthenticatedUser(
            subject="admin-1",
            email="admin@argus.local",
            role=RoleEnum.ADMIN,
            issuer="http://issuer",
            realm="argus-dev",
            is_superadmin=False,
            tenant_context=None,
            claims={},
        ),
    )


class _FakeTenancyService:
    def __init__(self, context: TenantContext) -> None:
        self.context = context

    async def resolve_context(
        self,
        *,
        user: AuthenticatedUser,
        explicit_tenant_id=None,
    ) -> TenantContext:
        return self.context


class _FakeSecurity:
    def __init__(self, user: AuthenticatedUser) -> None:
        self.user = user

    async def authenticate_request(self, request) -> AuthenticatedUser:  # noqa: ANN001
        return self.user


class _FakeModelService:
    async def list_catalog_status(self) -> list[ModelCatalogEntryResponse]:
        return [
            ModelCatalogEntryResponse(
                id="yolo26n-coco-onnx",
                name="YOLO26n COCO",
                version="2026.1",
                task=ModelTask.DETECT,
                path_hint="models/yolo26n.onnx",
                format=ModelFormat.ONNX,
                capability=DetectorCapability.FIXED_VOCAB,
                capability_config={"runtime_backend": "onnxruntime", "readiness": "ready"},
                classes=[],
                input_shape={"width": 640, "height": 640},
                registration_state="unregistered",
                registered_model_id=None,
                artifact_exists=False,
                note="Default fast detector.",
            )
        ]


def _create_app(context: TenantContext) -> FastAPI:
    app = FastAPI()
    app.include_router(router)
    app.state.services = SimpleNamespace(
        tenancy=_FakeTenancyService(context),
        models=_FakeModelService(),
    )
    app.state.security = _FakeSecurity(context.user)
    return app


@pytest.mark.asyncio
async def test_model_catalog_route_returns_entries() -> None:
    context = _tenant_context()
    app = _create_app(context)

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        response = await client.get(
            "/api/v1/model-catalog",
            headers={"Authorization": "Bearer token"},
        )

    assert response.status_code == 200
    body = response.json()
    assert body[0]["id"] == "yolo26n-coco-onnx"
    assert body[0]["capability"] == "fixed_vocab"
```

- [ ] **Step 8: Run backend catalog tests**

Run:

```bash
cd /Users/yann.moren/vision/backend
python3 -m uv run pytest tests/services/test_model_catalog.py tests/api/test_model_catalog_routes.py -q
```

Expected: tests pass.

- [ ] **Step 9: Commit Task 2**

Run:

```bash
git add backend/src/argus/services/model_catalog.py \
  backend/src/argus/api/v1/model_catalog.py \
  backend/src/argus/api/v1/__init__.py \
  backend/src/argus/api/contracts.py \
  backend/src/argus/services/app.py \
  backend/tests/services/test_model_catalog.py \
  backend/tests/api/test_model_catalog_routes.py
git commit -m "feat(models): add recommended model catalog"
```

## Task 3: Add Jetson NVIDIA Runtime Profile

**Files:**
- Modify: `backend/src/argus/vision/runtime.py`
- Test: `backend/tests/vision/test_runtime.py`

- [ ] **Step 1: Write failing Jetson profile tests**

Add to `backend/tests/vision/test_runtime.py`:

```python
def test_runtime_policy_prefers_tensorrt_for_linux_aarch64_jetson_hosts() -> None:
    policy = resolve_execution_policy(
        _FakeRuntime(
            providers=[
                ExecutionProvider.CPU.value,
                ExecutionProvider.CUDA.value,
                ExecutionProvider.TENSORRT.value,
            ]
        ),
        system="Linux",
        machine="aarch64",
        cpu_vendor=CpuVendor.UNKNOWN,
    )

    assert policy.profile is ExecutionProfile.LINUX_AARCH64_NVIDIA_JETSON
    assert policy.provider == ExecutionProvider.TENSORRT.value


def test_runtime_policy_prefers_cuda_for_linux_arm64_jetson_without_tensorrt() -> None:
    policy = resolve_execution_policy(
        _FakeRuntime(
            providers=[
                ExecutionProvider.CPU.value,
                ExecutionProvider.CUDA.value,
            ]
        ),
        system="Linux",
        machine="arm64",
        cpu_vendor=CpuVendor.UNKNOWN,
    )

    assert policy.profile is ExecutionProfile.LINUX_AARCH64_NVIDIA_JETSON
    assert policy.provider == ExecutionProvider.CUDA.value
```

- [ ] **Step 2: Run tests and confirm failure**

Run:

```bash
cd /Users/yann.moren/vision/backend
python3 -m uv run pytest tests/vision/test_runtime.py -q -k jetson
```

Expected: failure because `LINUX_AARCH64_NVIDIA_JETSON` does not exist.

- [ ] **Step 3: Implement Jetson profile**

Modify `backend/src/argus/vision/runtime.py`:

```python
class ExecutionProfile(StrEnum):
    NVIDIA_LINUX_X86_64 = "linux-x86_64-nvidia"
    LINUX_AARCH64_NVIDIA_JETSON = "linux-aarch64-nvidia-jetson"
    MACOS_APPLE_SILICON = "macos-arm64-apple-silicon"
    LINUX_X86_64_INTEL = "linux-x86_64-intel"
    LINUX_X86_64_AMD = "linux-x86_64-amd"
    MACOS_X86_64_INTEL = "macos-x86_64-intel"
    CPU_FALLBACK = "cpu-fallback"
```

Add provider priority:

```python
ExecutionProfile.LINUX_AARCH64_NVIDIA_JETSON: (
    ExecutionProvider.TENSORRT,
    ExecutionProvider.CUDA,
    ExecutionProvider.CPU,
),
```

Add classification before generic fallbacks:

```python
elif (
    resolved_system == "linux"
    and resolved_machine in {"aarch64", "arm64"}
    and any(
        provider in available_providers
        for provider in (
            ExecutionProvider.TENSORRT.value,
            ExecutionProvider.CUDA.value,
        )
    )
):
    profile = ExecutionProfile.LINUX_AARCH64_NVIDIA_JETSON
    profile_overridden = False
```

- [ ] **Step 4: Run runtime tests**

Run:

```bash
cd /Users/yann.moren/vision/backend
python3 -m uv run pytest tests/vision/test_runtime.py -q
```

Expected: all runtime tests pass.

- [ ] **Step 5: Commit Task 3**

Run:

```bash
git add backend/src/argus/vision/runtime.py backend/tests/vision/test_runtime.py
git commit -m "feat(runtime): classify Jetson NVIDIA workers"
```

## Task 4: Build True Open-Vocab Detector Adapter

**Files:**
- Modify: `backend/src/argus/vision/open_vocab_detector.py`
- Test: `backend/tests/vision/test_open_vocab_detector.py`

- [ ] **Step 1: Write fake Ultralytics adapter tests**

Create `backend/tests/vision/test_open_vocab_detector.py`:

```python
from __future__ import annotations

import numpy as np

from argus.vision.open_vocab_detector import OpenVocabDetector, OpenVocabModelConfig
from argus.vision.runtime import ExecutionProvider, RuntimeExecutionPolicy, HostClassification, ExecutionProfile, CpuVendor


class _FakeBoxes:
    def __init__(self) -> None:
        self.xyxy = np.array([[10.0, 20.0, 50.0, 80.0]], dtype=np.float32)
        self.conf = np.array([0.91], dtype=np.float32)
        self.cls = np.array([0], dtype=np.float32)


class _FakeResult:
    names = {0: "forklift"}

    def __init__(self) -> None:
        self.boxes = _FakeBoxes()


class _FakeUltralyticsModel:
    def __init__(self, path: str) -> None:
        self.path = path
        self.classes: list[str] = []
        self.predict_calls: list[dict[str, object]] = []

    def set_classes(self, classes: list[str]) -> None:
        self.classes = list(classes)

    def predict(self, frame, verbose: bool = False, conf: float = 0.25, iou: float = 0.45):  # noqa: ANN001
        self.predict_calls.append({"shape": frame.shape, "conf": conf, "iou": iou, "verbose": verbose})
        return [_FakeResult()]


def _policy() -> RuntimeExecutionPolicy:
    return RuntimeExecutionPolicy(
        host=HostClassification(
            system="linux",
            machine="aarch64",
            cpu_vendor=CpuVendor.UNKNOWN,
            available_providers=(ExecutionProvider.CUDA.value,),
            profile=ExecutionProfile.LINUX_AARCH64_NVIDIA_JETSON,
        ),
        provider=ExecutionProvider.CUDA.value,
        available_providers=(ExecutionProvider.CUDA.value,),
        provider_overridden=False,
    )


def test_open_vocab_detector_sets_initial_vocabulary_and_normalizes_detections() -> None:
    loaded: list[_FakeUltralyticsModel] = []

    def loader(path: str, backend: str) -> _FakeUltralyticsModel:
        model = _FakeUltralyticsModel(path)
        loaded.append(model)
        return model

    detector = OpenVocabDetector(
        OpenVocabModelConfig(
            name="YOLOE-26N",
            path="/models/yoloe-26n-seg.pt",
            input_shape={"width": 640, "height": 640},
            capability_config={"runtime_backend": "ultralytics_yoloe"},
            default_vocabulary=["forklift", "pallet jack"],
            confidence_threshold=0.4,
            iou_threshold=0.5,
        ),
        runtime=None,
        runtime_policy=_policy(),
        model_loader=loader,
    )

    detections = detector.detect(np.zeros((100, 200, 3), dtype=np.uint8))

    assert loaded[0].classes == ["forklift", "pallet jack"]
    assert detections[0].class_name == "forklift"
    assert detections[0].confidence == 0.91
    assert detections[0].bbox == (10.0, 20.0, 50.0, 80.0)


def test_open_vocab_detector_hot_updates_runtime_vocabulary() -> None:
    model = _FakeUltralyticsModel("/models/yoloe-26n-seg.pt")

    detector = OpenVocabDetector(
        OpenVocabModelConfig(
            name="YOLOE-26N",
            path="/models/yoloe-26n-seg.pt",
            input_shape={"width": 640, "height": 640},
            capability_config={"runtime_backend": "ultralytics_yoloe"},
            default_vocabulary=["person"],
        ),
        runtime=None,
        runtime_policy=_policy(),
        model_loader=lambda path, backend: model,
    )

    detector.update_runtime_vocabulary(["forklift", "forklift", ""])

    assert model.classes == ["forklift"]
    assert detector.describe_runtime_state()["runtime_vocabulary"] == ["forklift"]
```

- [ ] **Step 2: Run tests and confirm failure**

Run:

```bash
cd /Users/yann.moren/vision/backend
python3 -m uv run pytest tests/vision/test_open_vocab_detector.py -q
```

Expected: failure because `OpenVocabDetector` does not accept `model_loader` and still wraps `YoloDetector`.

- [ ] **Step 3: Implement Ultralytics-backed adapter**

Replace `backend/src/argus/vision/open_vocab_detector.py` with an adapter that keeps the existing public class names:

```python
class OpenVocabDetector:
    capability = DetectorCapability.OPEN_VOCAB

    def __init__(
        self,
        model_config: OpenVocabModelConfig,
        runtime: Any,
        runtime_policy: RuntimeExecutionPolicy,
        model_loader: Callable[[str, str], Any] | None = None,
    ) -> None:
        self.model_config = model_config
        self.runtime = runtime
        self.runtime_policy = runtime_policy
        self._runtime_backend = str(
            model_config.capability_config.get("runtime_backend") or "ultralytics_yoloe"
        )
        self._runtime_vocabulary = _normalize_vocabulary(model_config.default_vocabulary)
        self._model = (model_loader or _load_ultralytics_model)(
            model_config.path,
            self._runtime_backend,
        )
        self._apply_vocabulary()

    def update_runtime_vocabulary(self, vocabulary: list[str]) -> None:
        self._runtime_vocabulary = _normalize_vocabulary(vocabulary)
        self._apply_vocabulary()

    def detect(
        self,
        frame: NDArray[np.uint8],
        allowed_classes: Iterable[str] | None = None,
    ) -> list[Detection]:
        visible_classes = (
            _normalize_vocabulary(allowed_classes)
            if allowed_classes is not None
            else list(self._runtime_vocabulary)
        )
        if not visible_classes:
            return []
        if visible_classes != self._runtime_vocabulary:
            self._runtime_vocabulary = visible_classes
            self._apply_vocabulary()
        results = self._model.predict(
            frame,
            verbose=False,
            conf=self.model_config.confidence_threshold,
            iou=self.model_config.iou_threshold,
        )
        return _detections_from_ultralytics_results(results)

    def describe_runtime_state(self) -> dict[str, object]:
        return {
            "capability": self.capability,
            "runtime_backend": self._runtime_backend,
            "runtime_vocabulary": list(self._runtime_vocabulary),
            "selected_provider": self.runtime_policy.provider,
        }

    def _apply_vocabulary(self) -> None:
        set_classes = getattr(self._model, "set_classes", None)
        if not callable(set_classes):
            raise RuntimeError(
                f"Open-vocab backend {self._runtime_backend!r} does not support set_classes."
            )
        set_classes(list(self._runtime_vocabulary))
```

Add loader and result normalization:

```python
def _load_ultralytics_model(path: str, backend: str) -> Any:
    if backend == "ultralytics_yolo_world":
        from ultralytics import YOLOWorld

        return YOLOWorld(path)
    if backend == "ultralytics_yoloe":
        from ultralytics import YOLOE

        return YOLOE(path)
    raise RuntimeError(f"Unsupported open-vocab runtime backend: {backend}")


def _detections_from_ultralytics_results(results: Iterable[Any]) -> list[Detection]:
    detections: list[Detection] = []
    for result in results:
        names = getattr(result, "names", {}) or {}
        boxes = getattr(result, "boxes", None)
        if boxes is None:
            continue
        xyxy = np.asarray(getattr(boxes, "xyxy", []), dtype=np.float32)
        confidences = np.asarray(getattr(boxes, "conf", []), dtype=np.float32)
        class_ids = np.asarray(getattr(boxes, "cls", []), dtype=np.float32)
        for bbox, confidence, class_id_value in zip(
            xyxy,
            confidences.tolist(),
            class_ids.tolist(),
            strict=False,
        ):
            class_id = int(class_id_value)
            class_name = str(names.get(class_id, class_id))
            detections.append(
                Detection(
                    class_name=class_name,
                    class_id=class_id,
                    confidence=float(confidence),
                    bbox=tuple(float(value) for value in bbox),
                )
            )
    return detections
```

- [ ] **Step 4: Run open-vocab detector tests**

Run:

```bash
cd /Users/yann.moren/vision/backend
python3 -m uv run pytest tests/vision/test_open_vocab_detector.py -q
```

Expected: tests pass.

- [ ] **Step 5: Commit Task 4**

Run:

```bash
git add backend/src/argus/vision/open_vocab_detector.py backend/tests/vision/test_open_vocab_detector.py
git commit -m "feat(vision): add Ultralytics open vocab detector"
```

## Task 5: Wire Detector Factory Backend Selection

**Files:**
- Modify: `backend/src/argus/vision/detector_factory.py`
- Test: `backend/tests/vision/test_detector_factory.py`
- Test: `backend/tests/inference/test_engine.py`

- [ ] **Step 1: Write detector factory tests**

Create `backend/tests/vision/test_detector_factory.py`:

```python
from __future__ import annotations

from types import SimpleNamespace

from argus.models.enums import DetectorCapability
from argus.vision.detector_factory import build_detector


class _FakeFixedDetector:
    def __init__(self, config, runtime, runtime_policy) -> None:  # noqa: ANN001
        self.config = config


class _FakeOpenDetector:
    def __init__(self, config, runtime, runtime_policy) -> None:  # noqa: ANN001
        self.config = config


def test_factory_builds_open_vocab_detector_with_runtime_backend(monkeypatch) -> None:
    import argus.vision.open_vocab_detector as open_vocab_module

    monkeypatch.setattr(open_vocab_module, "OpenVocabDetector", _FakeOpenDetector)
    model = SimpleNamespace(
        name="YOLOE-26N",
        path="/models/yoloe-26n-seg.pt",
        capability=DetectorCapability.OPEN_VOCAB,
        capability_config={"runtime_backend": "ultralytics_yoloe"},
        classes=[],
        input_shape={"width": 640, "height": 640},
        runtime_vocabulary=SimpleNamespace(terms=["forklift"]),
        confidence_threshold=0.25,
        iou_threshold=0.45,
    )

    detector = build_detector(
        model=model,
        runtime=object(),
        runtime_policy=object(),
        yolo_detector_cls=_FakeFixedDetector,
    )

    assert isinstance(detector, _FakeOpenDetector)
    assert detector.config.default_vocabulary == ["forklift"]
    assert detector.config.capability_config["runtime_backend"] == "ultralytics_yoloe"
```

- [ ] **Step 2: Run factory tests**

Run:

```bash
cd /Users/yann.moren/vision/backend
python3 -m uv run pytest tests/vision/test_detector_factory.py -q
```

Expected: tests pass if the current factory already carries config through; otherwise update imports to support monkeypatching.

- [ ] **Step 3: Add engine hot-swap coverage**

Extend the existing open-vocab command test in `backend/tests/inference/test_engine.py` so it asserts the detector receives `update_runtime_vocabulary(["forklift"])` when a camera command carries a runtime vocabulary update.

Use the existing fake detector pattern and assert:

```python
assert detector.runtime_vocabulary_updates[-1] == ["forklift"]
assert engine.runtime_vocabulary == ["forklift"]
```

- [ ] **Step 4: Run engine open-vocab focused tests**

Run:

```bash
cd /Users/yann.moren/vision/backend
python3 -m uv run pytest tests/inference/test_engine.py -q -k "runtime_vocabulary or open_vocab"
```

Expected: focused engine tests pass.

- [ ] **Step 5: Commit Task 5**

Run:

```bash
git add backend/src/argus/vision/detector_factory.py \
  backend/tests/vision/test_detector_factory.py \
  backend/tests/inference/test_engine.py
git commit -m "test(engine): cover open vocab detector hot swap"
```

## Task 6: Add Catalog Registration Helper

**Files:**
- Create: `backend/scripts/register_model_preset.py`
- Test: `backend/tests/scripts/test_register_model_preset.py`

- [ ] **Step 1: Write registration helper tests**

Create `backend/tests/scripts/test_register_model_preset.py`:

```python
from __future__ import annotations

import hashlib

from argus.scripts.register_model_preset import build_model_create_payload


def test_build_model_create_payload_uses_catalog_defaults(tmp_path) -> None:
    artifact = tmp_path / "yolo26n.onnx"
    artifact.write_bytes(b"model")

    payload = build_model_create_payload(
        catalog_id="yolo26n-coco-onnx",
        artifact_path=artifact,
        classes=["person", "car"],
    )

    assert payload["name"] == "YOLO26n COCO"
    assert payload["format"] == "onnx"
    assert payload["capability"] == "fixed_vocab"
    assert payload["capability_config"]["catalog_id"] == "yolo26n-coco-onnx"
    assert payload["sha256"] == hashlib.sha256(b"model").hexdigest()
    assert payload["size_bytes"] == 5
    assert payload["classes"] == ["person", "car"]
```

- [ ] **Step 2: Run script tests and confirm failure**

Run:

```bash
cd /Users/yann.moren/vision/backend
python3 -m uv run pytest tests/scripts/test_register_model_preset.py -q
```

Expected: import failure until the helper exists.

- [ ] **Step 3: Implement helper as an importable module**

Create package path `backend/src/argus/scripts/__init__.py` and `backend/src/argus/scripts/register_model_preset.py`:

```python
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

from argus.services.model_catalog import list_model_catalog_entries


def build_model_create_payload(
    *,
    catalog_id: str,
    artifact_path: Path,
    classes: list[str] | None,
) -> dict[str, Any]:
    entry = next(item for item in list_model_catalog_entries() if item.id == catalog_id)
    data = artifact_path.read_bytes()
    capability_config = entry.capability_config.model_dump(mode="json")
    capability_config["catalog_id"] = entry.id
    return {
        "name": entry.name,
        "version": entry.version,
        "task": entry.task.value,
        "path": str(artifact_path),
        "format": entry.format.value,
        "capability": entry.capability.value,
        "capability_config": capability_config,
        "classes": classes if classes is not None else list(entry.classes),
        "input_shape": entry.input_shape,
        "sha256": hashlib.sha256(data).hexdigest(),
        "size_bytes": len(data),
        "license": entry.license,
    }
```

Create CLI wrapper `backend/scripts/register_model_preset.py`:

```python
from argus.scripts.register_model_preset import main

if __name__ == "__main__":
    main()
```

Implement `main()` to print JSON by default and optionally POST to `/api/v1/models` when `--api-base-url` and `--bearer-token` are provided:

```python
def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--catalog-id", required=True)
    parser.add_argument("--artifact-path", required=True)
    parser.add_argument("--class", dest="classes", action="append")
    parser.add_argument("--api-base-url")
    parser.add_argument("--bearer-token")
    args = parser.parse_args()
    payload = build_model_create_payload(
        catalog_id=args.catalog_id,
        artifact_path=Path(args.artifact_path),
        classes=args.classes,
    )
    if not args.api_base_url:
        print(json.dumps(payload, indent=2, sort_keys=True))
        return

    import httpx

    response = httpx.post(
        f"{args.api_base_url.rstrip('/')}/api/v1/models",
        headers={"Authorization": f"Bearer {args.bearer_token}"},
        json=payload,
        timeout=30,
    )
    response.raise_for_status()
    print(json.dumps(response.json(), indent=2, sort_keys=True))
```

- [ ] **Step 4: Run registration helper tests**

Run:

```bash
cd /Users/yann.moren/vision/backend
python3 -m uv run pytest tests/scripts/test_register_model_preset.py -q
```

Expected: tests pass.

- [ ] **Step 5: Commit Task 6**

Run:

```bash
git add backend/src/argus/scripts/__init__.py \
  backend/src/argus/scripts/register_model_preset.py \
  backend/scripts/register_model_preset.py \
  backend/tests/scripts/test_register_model_preset.py
git commit -m "feat(models): add preset registration helper"
```

## Task 7: Surface Model Catalog And Badges In Frontend

**Files:**
- Modify: `frontend/src/lib/api.generated.ts`
- Create: `frontend/src/hooks/use-model-catalog.ts`
- Modify: `frontend/src/pages/Cameras.tsx`
- Modify: `frontend/src/components/cameras/CameraWizard.tsx`
- Test: `frontend/src/pages/Cameras.test.tsx`
- Test: `frontend/src/components/cameras/CameraWizard.test.tsx`

- [ ] **Step 1: Regenerate API types**

Run:

```bash
corepack pnpm --dir frontend generate:api
```

Expected: `frontend/src/lib/api.generated.ts` includes `ModelCatalogEntryResponse`, `ModelCatalogRegistrationState`, `pt`, and new capability config fields.

- [ ] **Step 2: Add catalog hook**

Create `frontend/src/hooks/use-model-catalog.ts`:

```typescript
import { useQuery } from "@tanstack/react-query";

import { apiClient, toApiError } from "@/lib/api";
import { useAuthStore } from "@/stores/auth-store";

export function useModelCatalog() {
  const accessToken = useAuthStore((state) => state.accessToken);

  return useQuery({
    queryKey: ["model-catalog", accessToken ? "authenticated" : "anonymous"],
    enabled: Boolean(accessToken),
    staleTime: 30_000,
    queryFn: async () => {
      const { data, error } = await apiClient.GET("/api/v1/model-catalog");

      if (error) {
        throw toApiError(error, "Failed to load model catalog.");
      }

      return data ?? [];
    },
  });
}
```

- [ ] **Step 3: Pass full model metadata into CameraWizard**

In `frontend/src/pages/Cameras.tsx`, keep the existing dynamic list but include capability/config:

```typescript
models={models.map((model) => ({
  id: model.id,
  name: model.name,
  version: model.version,
  classes: model.classes,
  capability: model.capability,
  capability_config: model.capability_config,
}))}
```

- [ ] **Step 4: Add model badges in wizard option labels**

In `frontend/src/components/cameras/CameraWizard.tsx`, add a small formatter:

```typescript
function formatModelOptionLabel(model: ModelOption) {
  const capability = model.capability === "open_vocab" ? "open vocab" : "fixed vocab";
  const backend = model.capability_config?.runtime_backend ?? "onnxruntime";
  const readiness = model.capability_config?.readiness;
  return `${model.name} ${model.version} - ${capability} - ${backend}${
    readiness ? ` - ${readiness}` : ""
  }`;
}
```

Use it in both primary and secondary select options:

```tsx
<option key={model.id} value={model.id}>
  {formatModelOptionLabel(model)}
</option>
```

- [ ] **Step 5: Add frontend tests**

Extend `frontend/src/components/cameras/CameraWizard.test.tsx`:

```typescript
test("labels model options with capability and backend", async () => {
  const user = userEvent.setup();

  renderWizard({
    models: [
      {
        id: "open-model",
        name: "YOLOE-26N",
        version: "2026.1",
        classes: [],
        capability: "open_vocab",
        capability_config: {
          supports_runtime_vocabulary_updates: true,
          max_runtime_terms: 32,
          runtime_backend: "ultralytics_yoloe",
          readiness: "experimental",
        },
      },
    ],
  });

  await user.type(screen.getByLabelText(/camera name/i), "Dock Camera");
  await user.selectOptions(screen.getByLabelText(/site/i), "site-1");
  await user.type(screen.getByLabelText(/rtsp url/i), "rtsp://camera.local/live");
  await user.click(screen.getByRole("button", { name: /next/i }));

  expect(screen.getByRole("option", { name: /open vocab - ultralytics_yoloe/i })).toBeInTheDocument();
});
```

- [ ] **Step 6: Run frontend tests**

Run:

```bash
corepack pnpm --dir frontend exec vitest run src/components/cameras/CameraWizard.test.tsx src/pages/Cameras.test.tsx
```

Expected: tests pass.

- [ ] **Step 7: Commit Task 7**

Run:

```bash
git add frontend/src/lib/api.generated.ts \
  frontend/src/hooks/use-model-catalog.ts \
  frontend/src/pages/Cameras.tsx \
  frontend/src/components/cameras/CameraWizard.tsx \
  frontend/src/pages/Cameras.test.tsx \
  frontend/src/components/cameras/CameraWizard.test.tsx
git commit -m "feat(frontend): show model capability metadata"
```

## Task 8: Update Lab Docs And Verification

**Files:**
- Modify: `docs/imac-master-orin-lab-test-guide.md`
- Modify: `docs/runbook.md`

- [ ] **Step 1: Update model guidance in lab guide**

In `docs/imac-master-orin-lab-test-guide.md`, replace the YOLO12-only language with:

```markdown
Recommended fixed-vocab model order for this lab:

1. `YOLO26n COCO` from `models/yolo26n.onnx` for the default fast path.
2. `YOLO26s COCO` from `models/yolo26s.onnx` when you want more accuracy.
3. `YOLO11n COCO` from `models/yolo11n.onnx` as the stable fallback.
4. `YOLO12n COCO` from `models/yolo12n.onnx` only when comparing against the older lab baseline.

Open-vocab lab models are experimental:

1. `YOLOE-26N Open Vocab` from `models/yoloe-26n-seg.pt`.
2. `YOLOv8s-Worldv2 Open Vocab` from `models/yolov8s-worldv2.pt`.

Do not register raw `.engine` files as ready camera models until the TensorRT engine detector adapter lands. ONNX models can still use TensorRT or CUDA through ONNX Runtime providers when those providers are installed.
```

- [ ] **Step 2: Add registration examples**

Add a short registration example:

```bash
cd "$HOME/vision/backend"
python3 -m uv run python backend/scripts/register_model_preset.py \
  --catalog-id yolo26n-coco-onnx \
  --artifact-path "$HOME/vision/models/yolo26n.onnx" \
  --api-base-url http://127.0.0.1:8000 \
  --bearer-token "$TOKEN"
```

Add open-vocab example:

```bash
cd "$HOME/vision/backend"
python3 -m uv run python backend/scripts/register_model_preset.py \
  --catalog-id yoloe-26n-open-vocab-pt \
  --artifact-path "$HOME/vision/models/yoloe-26n-seg.pt" \
  --api-base-url http://127.0.0.1:8000 \
  --bearer-token "$TOKEN"
```

- [ ] **Step 3: Update runbook limitations**

In `docs/runbook.md`, add:

```markdown
### Model Catalog And Open-Vocab Runtime

`/api/v1/model-catalog` lists recommended local model presets. It does not download model files and does not replace registered `Model` rows. A camera can only select models that are registered in `/api/v1/models`.

Fixed-vocab ONNX models use ONNX Runtime. Provider selection can choose TensorRT, CUDA, OpenVINO, CoreML, or CPU depending on host support.

Open-vocab models use the Ultralytics adapter and are marked experimental until validated on the target central GPU and Jetson runtime. The supported first-pass formats are `.pt` model files for YOLOE and YOLO-World.

Raw TensorRT `.engine` files are cataloged as planned only. They require a dedicated TensorRT engine detector adapter before they can be marked ready.
```

- [ ] **Step 4: Run full verification**

Run:

```bash
cd /Users/yann.moren/vision/backend
python3 -m uv run pytest tests/services/test_model_service.py tests/services/test_model_catalog.py tests/vision/test_runtime.py tests/vision/test_open_vocab_detector.py tests/vision/test_detector_factory.py tests/inference/test_engine.py -q
python3 -m uv run ruff check src tests
python3 -m uv run mypy src
cd /Users/yann.moren/vision
corepack pnpm --dir frontend build
corepack pnpm --dir frontend exec vitest run src/components/cameras/CameraWizard.test.tsx src/pages/Cameras.test.tsx
```

Expected: all backend tests, lint, mypy, frontend build, and focused frontend tests pass.

- [ ] **Step 5: Commit Task 8**

Run:

```bash
git add docs/imac-master-orin-lab-test-guide.md docs/runbook.md
git commit -m "docs(models): document recommended model catalog"
```

## Task 9: Final Manual Validation

**Files:**
- No code changes expected.

- [ ] **Step 1: Register a fixed-vocab model**

Run with a real local model artifact:

```bash
cd /Users/yann.moren/vision/backend
python3 -m uv run python backend/scripts/register_model_preset.py \
  --catalog-id yolo26n-coco-onnx \
  --artifact-path /Users/yann.moren/vision/models/yolo26n.onnx \
  --api-base-url http://127.0.0.1:8000 \
  --bearer-token "$TOKEN"
```

Expected: API returns a `ModelResponse` with `capability=fixed_vocab`.

- [ ] **Step 2: Register an open-vocab model**

Run with a real local model artifact:

```bash
cd /Users/yann.moren/vision/backend
python3 -m uv run python backend/scripts/register_model_preset.py \
  --catalog-id yoloe-26n-open-vocab-pt \
  --artifact-path /Users/yann.moren/vision/models/yoloe-26n-seg.pt \
  --api-base-url http://127.0.0.1:8000 \
  --bearer-token "$TOKEN"
```

Expected: API returns a `ModelResponse` with `capability=open_vocab`, `format=pt`, and `runtime_backend=ultralytics_yoloe`.

- [ ] **Step 3: Confirm catalog status**

Run:

```bash
curl -s -H "Authorization: Bearer $TOKEN" http://127.0.0.1:8000/api/v1/model-catalog
```

Expected: registered presets show `registration_state=registered`.

- [ ] **Step 4: Validate worker startup**

Create one fixed-vocab camera and one open-vocab camera in the UI. Start each worker from Operations.

Expected fixed-vocab log includes:

```text
Loaded detection model YOLO26n COCO with provider
```

Expected open-vocab log includes:

```text
runtime_backend=ultralytics_yoloe
runtime_vocabulary
```

- [ ] **Step 5: Validate open-vocab hot update**

In Live, ask for a new vocabulary such as:

```text
show forklifts and pallet jacks
```

Expected:

- the query response reports `open_vocab`
- worker receives a runtime vocabulary command
- detector state reports the new vocabulary
- detections continue to publish as normalized class names

## Plan Self-Review

- Spec coverage: model catalog, registration, Jetson profile, open-vocab adapter, UI metadata, docs, and raw TensorRT limitations are each mapped to tasks.
- Placeholder scan: no unresolved placeholder markers remain.
- Type consistency: `ModelFormat.PT`, `runtime_backend`, `readiness`, and Jetson profile names are used consistently.
- Risk handling: raw TensorRT `.engine` support is intentionally blocked as ready until a dedicated adapter exists.
