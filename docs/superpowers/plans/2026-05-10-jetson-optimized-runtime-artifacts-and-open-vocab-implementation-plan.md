# Jetson Optimized Runtime Artifacts And Open-Vocab Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

> **Status:** Track A, Track B, UI visibility, docs, and artifact validation
> hardening are implemented on `codex/omnisight-ui-spec-implementation`.
> This plan is now historical scaffolding for that completed runtime stage.
> Do not start Track C/DeepStream from this file unless the user explicitly
> reopens that lane after Jetson soak validation.

**Goal:** Make fixed-vocab Jetson TensorRT artifacts and compiled per-scene open-vocab artifacts real runtime options, while keeping the later DeepStream tracking lane planned but separate.

**Architecture:** Keep `Model` rows as canonical camera choices. Add runtime artifacts as validated, target-specific acceleration records selected by the worker at startup. Dynamic open vocab remains the fallback/exploration path; compiled open vocab is scene-scoped and selected only when the vocabulary hash matches.

**Tech Stack:** FastAPI, Pydantic, SQLAlchemy async, Alembic, PostgreSQL JSONB, ONNX Runtime, Ultralytics YOLO/YOLOE, TensorRT engine artifacts on Jetson, pytest, Ruff, mypy.

---

## Execution Order

Implement and commit one task at a time.

Run A and B first:

1. Tasks 1-8: Track A fixed-vocab runtime artifacts.
2. Tasks 9-13: Track B compiled open-vocab artifacts.
3. Tasks 14-15: UI/Operations visibility and docs.

Do not implement Track C until A/B have passed Jetson validation. Task 16 is the
future DeepStream preparation task and should stay unstarted for this round.

Keep WebGL off. Do not reopen RTSP or unrelated Jetson debugging unless new logs
prove it is necessary.

## File Structure

### Backend Model/API

- Modify: `backend/src/argus/models/enums.py`
  - add runtime artifact enums.
- Modify: `backend/src/argus/models/tables.py`
  - add `ModelRuntimeArtifact`.
- Create: `backend/src/argus/migrations/versions/0010_model_runtime_artifacts.py`
  - add table and indexes.
- Modify: `backend/src/argus/api/contracts.py`
  - add artifact request/response/settings contracts.
- Create: `backend/src/argus/services/runtime_artifacts.py`
  - service logic for listing, create/update, validation state, worker candidate
    selection.
- Modify: `backend/src/argus/services/app.py`
  - wire `RuntimeArtifactService` into `AppServices` and worker config.
- Create: `backend/src/argus/api/v1/runtime_artifacts.py`
  - nested routes under `/api/v1/models/{model_id}/runtime-artifacts`.
- Modify: `backend/src/argus/api/v1/__init__.py`
  - include runtime artifact router.

### Worker Runtime

- Create: `backend/src/argus/vision/runtime_selection.py`
  - pure runtime artifact selection.
- Create: `backend/src/argus/vision/ultralytics_engine_detector.py`
  - normalized detector wrapper for Ultralytics `.engine` artifacts.
- Modify: `backend/src/argus/vision/detector_factory.py`
  - accept selected runtime artifact and route to engine detector.
- Modify: `backend/src/argus/inference/engine.py`
  - carry runtime artifact settings and log selected backend/fallback.

### CLI

- Create: `backend/src/argus/scripts/build_runtime_artifact.py`
  - build/register fixed-vocab TensorRT and open-vocab compiled artifacts.
- Create: `backend/src/argus/scripts/validate_runtime_artifact.py`
  - validate artifact structure and mark status.

### Tests

- Create: `backend/tests/services/test_runtime_artifacts.py`
- Create: `backend/tests/api/test_runtime_artifact_routes.py`
- Create: `backend/tests/vision/test_runtime_selection.py`
- Create: `backend/tests/vision/test_ultralytics_engine_detector.py`
- Modify: `backend/tests/services/test_camera_worker_config.py`
- Modify: `backend/tests/inference/test_engine.py`
- Create: `backend/tests/scripts/test_runtime_artifact_scripts.py`

### Frontend/Docs

- Modify: `frontend/src/lib/api.generated.ts`
  - regenerate from OpenAPI.
- Modify: `frontend/src/pages/Operations.tsx` or relevant Operations component.
- Modify: `frontend/src/pages/Cameras.tsx` / camera wizard details if model
  artifact status is shown there.
- Modify: `docs/runbook.md`
- Modify: `docs/imac-master-orin-lab-test-guide.md`
- Modify: `docs/scene-vision-profile-configuration-guide.md`

---

## Task 1: Runtime Artifact Data Contract

**Files:**

- Modify: `backend/src/argus/models/enums.py`
- Modify: `backend/src/argus/models/tables.py`
- Create: `backend/src/argus/migrations/versions/0010_model_runtime_artifacts.py`
- Modify: `backend/src/argus/api/contracts.py`
- Test: `backend/tests/services/test_runtime_artifacts.py`

- [ ] **Step 1: Add failing contract tests**

Create `backend/tests/services/test_runtime_artifacts.py`:

```python
from __future__ import annotations

from uuid import uuid4

from argus.api.contracts import RuntimeArtifactCreate, RuntimeArtifactResponse
from argus.models.enums import (
    DetectorCapability,
    RuntimeArtifactKind,
    RuntimeArtifactPrecision,
    RuntimeArtifactScope,
    RuntimeArtifactValidationStatus,
)


def test_runtime_artifact_create_supports_fixed_vocab_model_scope() -> None:
    payload = RuntimeArtifactCreate(
        scope=RuntimeArtifactScope.MODEL,
        kind=RuntimeArtifactKind.TENSORRT_ENGINE,
        capability=DetectorCapability.FIXED_VOCAB,
        runtime_backend="tensorrt_engine",
        path="/models/yolo26n.jetson.fp16.engine",
        target_profile="linux-aarch64-nvidia-jetson",
        precision=RuntimeArtifactPrecision.FP16,
        input_shape={"width": 640, "height": 640},
        classes=["person", "car"],
        source_model_sha256="a" * 64,
        sha256="b" * 64,
        size_bytes=1234,
    )

    assert payload.scope is RuntimeArtifactScope.MODEL
    assert payload.camera_id is None
    assert payload.validation_status is RuntimeArtifactValidationStatus.UNVALIDATED


def test_runtime_artifact_create_requires_camera_for_scene_scope() -> None:
    try:
        RuntimeArtifactCreate(
            scope=RuntimeArtifactScope.SCENE,
            kind=RuntimeArtifactKind.ONNX_EXPORT,
            capability=DetectorCapability.OPEN_VOCAB,
            runtime_backend="onnxruntime",
            path="/models/camera-a/person-chair.onnx",
            target_profile="linux-aarch64-nvidia-jetson",
            precision=RuntimeArtifactPrecision.FP16,
            input_shape={"width": 640, "height": 640},
            classes=["person", "chair"],
            vocabulary_hash="c" * 64,
            source_model_sha256="a" * 64,
            sha256="b" * 64,
            size_bytes=1234,
        )
    except ValueError as exc:
        assert "camera_id is required for scene-scoped artifacts" in str(exc)
    else:
        raise AssertionError("scene-scoped artifact without camera_id should fail")


def test_runtime_artifact_response_round_trips_scene_vocab_hash() -> None:
    camera_id = uuid4()
    artifact = RuntimeArtifactResponse(
        id=uuid4(),
        model_id=uuid4(),
        camera_id=camera_id,
        scope=RuntimeArtifactScope.SCENE,
        kind=RuntimeArtifactKind.TENSORRT_ENGINE,
        capability=DetectorCapability.OPEN_VOCAB,
        runtime_backend="tensorrt_engine",
        path="/models/camera-a/open-vocab.engine",
        target_profile="linux-aarch64-nvidia-jetson",
        precision=RuntimeArtifactPrecision.FP16,
        input_shape={"width": 640, "height": 640},
        classes=["person", "chair"],
        vocabulary_hash="d" * 64,
        vocabulary_version=7,
        source_model_sha256="a" * 64,
        sha256="b" * 64,
        size_bytes=1234,
        validation_status=RuntimeArtifactValidationStatus.VALID,
    )

    assert artifact.camera_id == camera_id
    assert artifact.vocabulary_hash == "d" * 64
    assert artifact.vocabulary_version == 7
```

- [ ] **Step 2: Run the failing tests**

Run:

```bash
cd /Users/yann.moren/vision/backend
python3 -m uv run pytest tests/services/test_runtime_artifacts.py -q
```

Expected: fails because artifact enums and contracts do not exist.

- [ ] **Step 3: Add enums**

In `backend/src/argus/models/enums.py`, add:

```python
class RuntimeArtifactScope(StrEnum):
    MODEL = "model"
    SCENE = "scene"


class RuntimeArtifactKind(StrEnum):
    ONNX_EXPORT = "onnx_export"
    TENSORRT_ENGINE = "tensorrt_engine"


class RuntimeArtifactPrecision(StrEnum):
    FP32 = "fp32"
    FP16 = "fp16"
    INT8 = "int8"


class RuntimeArtifactValidationStatus(StrEnum):
    UNVALIDATED = "unvalidated"
    VALID = "valid"
    INVALID = "invalid"
    STALE = "stale"
    MISSING_ARTIFACT = "missing_artifact"
    TARGET_MISMATCH = "target_mismatch"
```

- [ ] **Step 4: Add contracts**

In `backend/src/argus/api/contracts.py`, import the new enums and add:

```python
RuntimeBackend = Literal[
    "onnxruntime",
    "ultralytics_yolo_world",
    "ultralytics_yoloe",
    "tensorrt_engine",
]


class RuntimeArtifactBase(BaseModel):
    camera_id: UUID | None = None
    scope: RuntimeArtifactScope
    kind: RuntimeArtifactKind
    capability: DetectorCapability
    runtime_backend: RuntimeBackend
    path: str = Field(min_length=1)
    target_profile: str = Field(min_length=1)
    precision: RuntimeArtifactPrecision
    input_shape: dict[str, int]
    classes: list[str] = Field(default_factory=list)
    vocabulary_hash: str | None = Field(default=None, min_length=64, max_length=64)
    vocabulary_version: int | None = None
    source_model_sha256: str = Field(min_length=64, max_length=64)
    sha256: str = Field(min_length=64, max_length=64)
    size_bytes: int = Field(gt=0)
    builder: dict[str, Any] = Field(default_factory=dict)
    runtime_versions: dict[str, Any] = Field(default_factory=dict)
    validation_status: RuntimeArtifactValidationStatus = (
        RuntimeArtifactValidationStatus.UNVALIDATED
    )
    validation_error: str | None = None
    build_duration_seconds: float | None = None
    validation_duration_seconds: float | None = None
    validated_at: datetime | None = None

    @model_validator(mode="after")
    def validate_scope(self) -> RuntimeArtifactBase:
        if self.scope is RuntimeArtifactScope.SCENE and self.camera_id is None:
            raise ValueError("camera_id is required for scene-scoped artifacts.")
        if self.scope is RuntimeArtifactScope.MODEL and self.camera_id is not None:
            raise ValueError("camera_id must be null for model-scoped artifacts.")
        if self.capability is DetectorCapability.OPEN_VOCAB and not self.vocabulary_hash:
            raise ValueError("vocabulary_hash is required for open-vocab artifacts.")
        return self


class RuntimeArtifactCreate(RuntimeArtifactBase):
    pass


class RuntimeArtifactUpdate(BaseModel):
    validation_status: RuntimeArtifactValidationStatus | None = None
    validation_error: str | None = None
    sha256: str | None = Field(default=None, min_length=64, max_length=64)
    size_bytes: int | None = Field(default=None, gt=0)
    builder: dict[str, Any] | None = None
    runtime_versions: dict[str, Any] | None = None
    build_duration_seconds: float | None = None
    validation_duration_seconds: float | None = None
    validated_at: datetime | None = None


class RuntimeArtifactResponse(RuntimeArtifactBase):
    id: UUID
    model_id: UUID
    created_at: datetime | None = None
    updated_at: datetime | None = None
```

Keep the exact placement near model contracts.

- [ ] **Step 5: Add SQLAlchemy table**

In `backend/src/argus/models/tables.py`, import the new enums and add:

```python
class ModelRuntimeArtifact(UUIDPrimaryKeyMixin, TimestampMixin, UpdatedAtMixin, Base):
    __tablename__ = "model_runtime_artifacts"

    model_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("models.id"),
        nullable=False,
    )
    camera_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("cameras.id"),
        nullable=True,
    )
    scope: Mapped[RuntimeArtifactScope] = mapped_column(
        enum_column(RuntimeArtifactScope, "runtime_artifact_scope_enum"),
        nullable=False,
    )
    kind: Mapped[RuntimeArtifactKind] = mapped_column(
        enum_column(RuntimeArtifactKind, "runtime_artifact_kind_enum"),
        nullable=False,
    )
    capability: Mapped[DetectorCapability] = mapped_column(
        enum_column(DetectorCapability, "runtime_artifact_detector_capability_enum"),
        nullable=False,
    )
    runtime_backend: Mapped[str] = mapped_column(String(64), nullable=False)
    path: Mapped[str] = mapped_column(Text, nullable=False)
    target_profile: Mapped[str] = mapped_column(String(128), nullable=False)
    precision: Mapped[RuntimeArtifactPrecision] = mapped_column(
        enum_column(RuntimeArtifactPrecision, "runtime_artifact_precision_enum"),
        nullable=False,
    )
    input_shape: Mapped[dict[str, int]] = mapped_column(JSONB, nullable=False)
    classes: Mapped[list[str]] = mapped_column(JSONB, nullable=False, default=list)
    vocabulary_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    vocabulary_version: Mapped[int | None] = mapped_column(Integer, nullable=True)
    source_model_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    size_bytes: Mapped[int] = mapped_column(BigInteger, nullable=False)
    builder: Mapped[dict[str, object]] = mapped_column(JSONB, nullable=False, default=dict)
    runtime_versions: Mapped[dict[str, object]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
    )
    validation_status: Mapped[RuntimeArtifactValidationStatus] = mapped_column(
        enum_column(
            RuntimeArtifactValidationStatus,
            "runtime_artifact_validation_status_enum",
        ),
        nullable=False,
        default=RuntimeArtifactValidationStatus.UNVALIDATED,
    )
    validation_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    build_duration_seconds: Mapped[float | None] = mapped_column(Float, nullable=True)
    validation_duration_seconds: Mapped[float | None] = mapped_column(Float, nullable=True)
    validated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
```

- [ ] **Step 6: Add migration**

Create `backend/src/argus/migrations/versions/0010_model_runtime_artifacts.py`
with enum creation, table creation, and indexes:

```python
"""Add model runtime artifacts."""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0010_model_runtime_artifacts"
down_revision = "0009_scene_vision_profiles"
branch_labels = None
depends_on = None


def upgrade() -> None:
    scope_enum = postgresql.ENUM("model", "scene", name="runtime_artifact_scope_enum")
    kind_enum = postgresql.ENUM(
        "onnx_export",
        "tensorrt_engine",
        name="runtime_artifact_kind_enum",
    )
    precision_enum = postgresql.ENUM(
        "fp32",
        "fp16",
        "int8",
        name="runtime_artifact_precision_enum",
    )
    capability_enum = postgresql.ENUM(
        "fixed_vocab",
        "open_vocab",
        name="runtime_artifact_detector_capability_enum",
    )
    status_enum = postgresql.ENUM(
        "unvalidated",
        "valid",
        "invalid",
        "stale",
        "missing_artifact",
        "target_mismatch",
        name="runtime_artifact_validation_status_enum",
    )
    for enum in (scope_enum, kind_enum, precision_enum, capability_enum, status_enum):
        enum.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "model_runtime_artifacts",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("model_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("camera_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("scope", scope_enum, nullable=False),
        sa.Column("kind", kind_enum, nullable=False),
        sa.Column("capability", capability_enum, nullable=False),
        sa.Column("runtime_backend", sa.String(length=64), nullable=False),
        sa.Column("path", sa.Text(), nullable=False),
        sa.Column("target_profile", sa.String(length=128), nullable=False),
        sa.Column("precision", precision_enum, nullable=False),
        sa.Column("input_shape", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("classes", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("vocabulary_hash", sa.String(length=64), nullable=True),
        sa.Column("vocabulary_version", sa.Integer(), nullable=True),
        sa.Column("source_model_sha256", sa.String(length=64), nullable=False),
        sa.Column("sha256", sa.String(length=64), nullable=False),
        sa.Column("size_bytes", sa.BigInteger(), nullable=False),
        sa.Column("builder", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("runtime_versions", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("validation_status", status_enum, nullable=False),
        sa.Column("validation_error", sa.Text(), nullable=True),
        sa.Column("build_duration_seconds", sa.Float(), nullable=True),
        sa.Column("validation_duration_seconds", sa.Float(), nullable=True),
        sa.Column("validated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["camera_id"], ["cameras.id"]),
        sa.ForeignKeyConstraint(["model_id"], ["models.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_model_runtime_artifacts_model_target",
        "model_runtime_artifacts",
        ["model_id", "target_profile", "validation_status"],
    )
    op.create_index(
        "ix_model_runtime_artifacts_scene_vocab",
        "model_runtime_artifacts",
        ["camera_id", "vocabulary_hash", "target_profile", "validation_status"],
    )


def downgrade() -> None:
    op.drop_index("ix_model_runtime_artifacts_scene_vocab", table_name="model_runtime_artifacts")
    op.drop_index("ix_model_runtime_artifacts_model_target", table_name="model_runtime_artifacts")
    op.drop_table("model_runtime_artifacts")
    for name in (
        "runtime_artifact_validation_status_enum",
        "runtime_artifact_detector_capability_enum",
        "runtime_artifact_precision_enum",
        "runtime_artifact_kind_enum",
        "runtime_artifact_scope_enum",
    ):
        postgresql.ENUM(name=name).drop(op.get_bind(), checkfirst=True)
```

- [ ] **Step 7: Run focused tests**

Run:

```bash
cd /Users/yann.moren/vision/backend
python3 -m uv run pytest tests/services/test_runtime_artifacts.py tests/core/test_db.py -q
```

Expected: runtime artifact contract tests pass; DB tests still pass.

- [ ] **Step 8: Commit**

```bash
git add backend/src/argus/models/enums.py \
  backend/src/argus/models/tables.py \
  backend/src/argus/migrations/versions/0010_model_runtime_artifacts.py \
  backend/src/argus/api/contracts.py \
  backend/tests/services/test_runtime_artifacts.py
git commit -m "feat(models): add runtime artifact contract"
```

---

## Task 2: Runtime Artifact Service And API

**Files:**

- Create: `backend/src/argus/services/runtime_artifacts.py`
- Create: `backend/src/argus/api/v1/runtime_artifacts.py`
- Modify: `backend/src/argus/api/v1/__init__.py`
- Modify: `backend/src/argus/services/app.py`
- Test: `backend/tests/services/test_runtime_artifacts.py`
- Test: `backend/tests/api/test_runtime_artifact_routes.py`

- [ ] **Step 1: Add service tests**

Append tests covering:

- create artifact for existing model
- list artifacts by model
- reject scene artifact for another model/camera mismatch
- patch validation status
- mark stale by source model hash mismatch

Use existing test session factory patterns from
`backend/tests/services/test_model_service.py`.

- [ ] **Step 2: Add route tests**

Create `backend/tests/api/test_runtime_artifact_routes.py` with admin-only create
and viewer list tests. Reuse route test fake service patterns from
`backend/tests/api/test_prompt5_routes.py`.

- [ ] **Step 3: Implement service**

Create `RuntimeArtifactService` with:

```python
class RuntimeArtifactService:
    async def list_for_model(self, model_id: UUID) -> list[RuntimeArtifactResponse]: ...
    async def create_for_model(
        self,
        model_id: UUID,
        payload: RuntimeArtifactCreate,
    ) -> RuntimeArtifactResponse: ...
    async def update_artifact(
        self,
        model_id: UUID,
        artifact_id: UUID,
        payload: RuntimeArtifactUpdate,
    ) -> RuntimeArtifactResponse: ...
    async def validation_candidates_for_camera(
        self,
        *,
        camera: Camera,
        model: Model,
    ) -> list[RuntimeArtifactResponse]: ...
```

Use helper functions:

- `_artifact_to_response(artifact: ModelRuntimeArtifact)`
- `_validate_artifact_matches_model(model, payload)`
- `_artifact_is_stale(model, artifact)`

- [ ] **Step 4: Implement routes**

Create router:

```python
router = APIRouter(
    prefix="/api/v1/models/{model_id}/runtime-artifacts",
    tags=["runtime-artifacts"],
)
```

Routes:

- `GET ""`
- `POST ""`
- `PATCH "/{artifact_id}"`
- `POST "/{artifact_id}/validate"` initially marks `unvalidated` unless the
  local path exists and hash matches; full target validation is CLI-owned.

- [ ] **Step 5: Wire services**

Add `runtime_artifacts: RuntimeArtifactService` to `AppServices` and instantiate
it in `build_app_services`.

- [ ] **Step 6: Include router**

Add `runtime_artifacts` import and `router.include_router(runtime_artifacts.router)`.

- [ ] **Step 7: Run tests**

```bash
cd /Users/yann.moren/vision/backend
python3 -m uv run pytest \
  tests/services/test_runtime_artifacts.py \
  tests/api/test_runtime_artifact_routes.py \
  -q
```

- [ ] **Step 8: Commit**

```bash
git add backend/src/argus/services/runtime_artifacts.py \
  backend/src/argus/api/v1/runtime_artifacts.py \
  backend/src/argus/api/v1/__init__.py \
  backend/src/argus/services/app.py \
  backend/tests/services/test_runtime_artifacts.py \
  backend/tests/api/test_runtime_artifact_routes.py
git commit -m "feat(api): manage model runtime artifacts"
```

---

## Task 3: Worker Config Carries Runtime Artifact Candidates

**Files:**

- Modify: `backend/src/argus/api/contracts.py`
- Modify: `backend/src/argus/services/app.py`
- Modify: `backend/tests/services/test_camera_worker_config.py`

- [ ] **Step 1: Add failing worker config tests**

Add tests:

- valid fixed-vocab model artifact appears in worker config
- invalid/stale artifact does not appear
- open-vocab scene artifact appears only for same camera and vocabulary hash

- [ ] **Step 2: Add worker contract**

In `contracts.py`:

```python
class WorkerRuntimeArtifact(BaseModel):
    id: UUID
    scope: RuntimeArtifactScope
    kind: RuntimeArtifactKind
    capability: DetectorCapability
    runtime_backend: RuntimeBackend
    path: str
    target_profile: str
    precision: RuntimeArtifactPrecision
    input_shape: dict[str, int]
    classes: list[str] = Field(default_factory=list)
    vocabulary_hash: str | None = None
    vocabulary_version: int | None = None
    source_model_sha256: str
    sha256: str
    size_bytes: int
```

Add `runtime_artifacts: list[WorkerRuntimeArtifact] = Field(default_factory=list)`
to `WorkerConfigResponse`.

- [ ] **Step 3: Query artifacts in worker config**

In `CameraService.get_worker_config`, load valid artifacts for:

- `primary_model.id`
- `camera.id`
- `camera.runtime_vocabulary` hash

Pass them into `_camera_to_worker_config`.

- [ ] **Step 4: Map DB artifacts to worker artifacts**

Add `_runtime_artifact_to_worker_payload(...)`.

Only include `validation_status == valid`.

- [ ] **Step 5: Run tests**

```bash
cd /Users/yann.moren/vision/backend
python3 -m uv run pytest tests/services/test_camera_worker_config.py -q
```

- [ ] **Step 6: Commit**

```bash
git add backend/src/argus/api/contracts.py \
  backend/src/argus/services/app.py \
  backend/tests/services/test_camera_worker_config.py
git commit -m "feat(worker): include runtime artifact candidates"
```

---

## Task 4: Pure Runtime Artifact Selector

**Files:**

- Create: `backend/src/argus/vision/runtime_selection.py`
- Create: `backend/tests/vision/test_runtime_selection.py`
- Modify: `backend/src/argus/inference/engine.py`

- [ ] **Step 1: Write failing selector tests**

Create tests for:

- exact valid TensorRT target profile wins
- target mismatch falls back
- open-vocab vocabulary mismatch falls back to dynamic
- ONNX export beats `.pt` only when vocabulary hash matches
- fallback reason is explicit

- [ ] **Step 2: Implement selector**

Create:

```python
@dataclass(frozen=True, slots=True)
class RuntimeSelection:
    selected_backend: str
    artifact: RuntimeArtifactSettings | None
    fallback: bool
    fallback_reason: str | None


def select_runtime_artifact(
    *,
    model: ModelSettings,
    host_profile: str,
    artifacts: Iterable[RuntimeArtifactSettings],
    runtime_vocabulary_hash: str | None,
) -> RuntimeSelection:
    ...
```

Preference order:

1. valid TensorRT exact target, exact vocabulary hash if open vocab
2. valid ONNX export exact vocabulary hash if open vocab
3. canonical model runtime

- [ ] **Step 3: Add engine config model**

In `engine.py`, add `RuntimeArtifactSettings` mirroring worker contract and add
`runtime_artifacts: list[RuntimeArtifactSettings]` to `EngineConfig`.

- [ ] **Step 4: Run tests**

```bash
cd /Users/yann.moren/vision/backend
python3 -m uv run pytest tests/vision/test_runtime_selection.py -q
```

- [ ] **Step 5: Commit**

```bash
git add backend/src/argus/vision/runtime_selection.py \
  backend/src/argus/inference/engine.py \
  backend/tests/vision/test_runtime_selection.py
git commit -m "feat(runtime): select validated artifacts"
```

---

## Task 5: Ultralytics Engine Detector

**Files:**

- Create: `backend/src/argus/vision/ultralytics_engine_detector.py`
- Modify: `backend/src/argus/vision/detector_factory.py`
- Create: `backend/tests/vision/test_ultralytics_engine_detector.py`
- Modify: `backend/tests/vision/test_detector_factory.py`

- [ ] **Step 1: Write fake detector tests**

Use a fake loader returning an object with `predict(...)` and Ultralytics-shaped
results. Assert:

- engine detector maps boxes to `Detection`
- class names come from result names or artifact classes
- empty results return `[]`
- `describe_runtime_state()` includes artifact id/backend/path

- [ ] **Step 2: Implement detector**

Create `UltralyticsEngineDetector`:

```python
class UltralyticsEngineDetector:
    capability: DetectorCapability

    def __init__(
        self,
        artifact: RuntimeArtifactSettings,
        *,
        model_loader: Callable[[str], Any] | None = None,
    ) -> None: ...

    def detect(self, frame, allowed_classes=None) -> list[Detection]: ...
    def update_runtime_vocabulary(self, vocabulary: list[str]) -> None: return None
    def describe_runtime_state(self) -> dict[str, object]: ...
```

Use `ultralytics.YOLO(path)` for `.engine` artifacts in the default loader.

- [ ] **Step 3: Modify factory**

Add optional `runtime_selection` or `runtime_artifact` parameter to
`build_detector`. When `selected_backend == "tensorrt_engine"`, return
`UltralyticsEngineDetector`.

- [ ] **Step 4: Run tests**

```bash
cd /Users/yann.moren/vision/backend
python3 -m uv run pytest \
  tests/vision/test_ultralytics_engine_detector.py \
  tests/vision/test_detector_factory.py \
  -q
```

- [ ] **Step 5: Commit**

```bash
git add backend/src/argus/vision/ultralytics_engine_detector.py \
  backend/src/argus/vision/detector_factory.py \
  backend/tests/vision/test_ultralytics_engine_detector.py \
  backend/tests/vision/test_detector_factory.py
git commit -m "feat(vision): load TensorRT engine artifacts"
```

---

## Task 6: Worker Runtime Selection Integration

**Files:**

- Modify: `backend/src/argus/inference/engine.py`
- Modify: `backend/tests/inference/test_engine.py`

- [ ] **Step 1: Add failing engine tests**

Add tests:

- build runtime engine passes selected TensorRT artifact to detector factory
- fallback logs/selects ONNX when artifact target mismatches
- open-vocab vocabulary change switches back to dynamic `.pt`

- [ ] **Step 2: Integrate selector**

In `build_inference_engine`, after resolving `runtime_policy`, call:

```python
selection = select_runtime_artifact(
    model=config.model,
    host_profile=runtime_policy.profile.value,
    artifacts=config.runtime_artifacts,
    runtime_vocabulary_hash=hash_vocabulary(config.model.runtime_vocabulary.terms)
    if config.model.capability is DetectorCapability.OPEN_VOCAB
    else None,
)
```

Pass selection to `build_detector`.

- [ ] **Step 3: Log structured runtime selection**

Log:

- camera id
- model name
- selected backend
- artifact id
- host profile
- fallback
- fallback reason

- [ ] **Step 4: Handle vocabulary changes**

When a command updates open-vocab runtime vocabulary:

- update detector vocabulary only for dynamic `.pt`
- if current detector uses compiled artifact, rebuild detector from canonical
  open-vocab model or mark runtime selection dynamic until next worker restart

Keep this first pass simple: command vocabulary changes rebuild the detector via
existing `.pt` open-vocab model path and log `fallback_reason=vocabulary_changed`.

- [ ] **Step 5: Run tests**

```bash
cd /Users/yann.moren/vision/backend
python3 -m uv run pytest tests/inference/test_engine.py -q
```

- [ ] **Step 6: Commit**

```bash
git add backend/src/argus/inference/engine.py backend/tests/inference/test_engine.py
git commit -m "feat(worker): select optimized runtime artifacts"
```

---

## Task 7: Fixed-Vocab Build And Validate CLI

**Files:**

- Create: `backend/src/argus/scripts/build_runtime_artifact.py`
- Create: `backend/src/argus/scripts/validate_runtime_artifact.py`
- Create: `backend/tests/scripts/test_runtime_artifact_scripts.py`
- Modify: `docs/runbook.md`

- [ ] **Step 1: Add CLI tests with fake subprocess/model loader**

Test:

- fixed-vocab build command computes hash and posts artifact
- validate command patches artifact valid when file exists and hash matches
- validate command patches invalid when file is missing

- [ ] **Step 2: Implement shared helpers**

Implement:

```python
def sha256_file(path: Path) -> str: ...
def file_size(path: Path) -> int: ...
def post_json(url: str, token: str, payload: dict[str, object]) -> dict[str, object]: ...
def patch_json(url: str, token: str, payload: dict[str, object]) -> dict[str, object]: ...
```

- [ ] **Step 3: Implement fixed-vocab build**

For `--kind tensorrt_engine` and ONNX source:

- verify source exists
- call Ultralytics export only when source is `.pt`; for existing ONNX, call
  `trtexec` if available or require `--prebuilt-engine`
- first pass should support `--prebuilt-engine` because Vezor should not guess
  TensorRT builder flags silently
- register artifact with measured build duration

- [ ] **Step 4: Implement validation**

Validation checks:

- artifact file exists
- sha256 matches
- host profile matches requested target profile when provided
- Ultralytics can load engine and run sample image when sample is provided
- patch status to `valid` or `invalid`

- [ ] **Step 5: Run tests**

```bash
cd /Users/yann.moren/vision/backend
python3 -m uv run pytest tests/scripts/test_runtime_artifact_scripts.py -q
```

- [ ] **Step 6: Commit**

```bash
git add backend/src/argus/scripts/build_runtime_artifact.py \
  backend/src/argus/scripts/validate_runtime_artifact.py \
  backend/tests/scripts/test_runtime_artifact_scripts.py \
  docs/runbook.md
git commit -m "feat(scripts): register and validate runtime artifacts"
```

---

## Task 8: Fixed-Vocab Jetson Manual Validation Docs

**Files:**

- Modify: `docs/imac-master-orin-lab-test-guide.md`
- Modify: `docs/runbook.md`

- [ ] **Step 1: Add fixed-vocab Jetson artifact workflow**

Document:

- build/validate commands
- expected provider/runtime logs
- fallback behavior
- metrics to compare

- [ ] **Step 2: Run markdown sanity**

```bash
git diff --check -- docs/imac-master-orin-lab-test-guide.md docs/runbook.md
```

- [ ] **Step 3: Commit**

```bash
git add docs/imac-master-orin-lab-test-guide.md docs/runbook.md
git commit -m "docs(jetson): document fixed-vocab runtime artifacts"
```

---

## Task 9: Open-Vocab Scene Artifact Contract

**Files:**

- Modify: `backend/src/argus/api/contracts.py`
- Modify: `backend/src/argus/services/runtime_artifacts.py`
- Modify: `backend/tests/services/test_runtime_artifacts.py`
- Modify: `backend/tests/services/test_camera_worker_config.py`

- [ ] **Step 1: Add failing tests**

Tests:

- open-vocab scene artifact requires camera id
- open-vocab scene artifact requires vocabulary hash
- artifact vocabulary hash must match camera runtime vocabulary hash to appear
  in worker config
- stale artifact is excluded when camera vocabulary version/hash changes

- [ ] **Step 2: Add helper**

In `runtime_artifacts.py`:

```python
def artifact_matches_camera_vocabulary(
    *,
    artifact: ModelRuntimeArtifact,
    camera: Camera,
) -> bool:
    expected_hash = hash_vocabulary(camera.runtime_vocabulary or [])
    return artifact.vocabulary_hash == expected_hash
```

- [ ] **Step 3: Filter worker candidates**

Only include open-vocab artifacts with:

- `camera_id == camera.id`
- `vocabulary_hash == hash_vocabulary(camera.runtime_vocabulary)`
- `validation_status == valid`

- [ ] **Step 4: Run tests**

```bash
cd /Users/yann.moren/vision/backend
python3 -m uv run pytest \
  tests/services/test_runtime_artifacts.py \
  tests/services/test_camera_worker_config.py \
  -q
```

- [ ] **Step 5: Commit**

```bash
git add backend/src/argus/api/contracts.py \
  backend/src/argus/services/runtime_artifacts.py \
  backend/tests/services/test_runtime_artifacts.py \
  backend/tests/services/test_camera_worker_config.py
git commit -m "feat(open-vocab): scope artifacts to scene vocabulary"
```

---

## Task 10: Open-Vocab Compile CLI

**Files:**

- Modify: `backend/src/argus/scripts/build_runtime_artifact.py`
- Modify: `backend/tests/scripts/test_runtime_artifact_scripts.py`
- Modify: `docs/runbook.md`

- [ ] **Step 1: Add fake YOLOE export tests**

Use a fake YOLOE loader with:

- `set_classes([...])`
- `export(format="onnx")`
- `export(format="engine")`

Assert:

- `set_classes` is called before export
- ONNX scene artifact payload includes `vocabulary_hash`
- TensorRT scene artifact payload includes same vocabulary hash
- build duration is recorded

- [ ] **Step 2: Add CLI arguments**

Extend `build_runtime_artifact.py`:

```bash
--camera-id
--runtime-vocabulary person,chair,backpack
--open-vocab-source-pt /models/yoloe-26n-seg.pt
--export-format onnx
--export-format engine
```

- [ ] **Step 3: Implement YOLOE build**

Flow:

1. Normalize terms with existing vocabulary helper.
2. Compute vocabulary hash.
3. Load `YOLOE(source_pt)`.
4. Call `set_classes(terms)`.
5. Export ONNX.
6. Optionally export engine.
7. Register scene-scoped artifacts.

- [ ] **Step 4: Run tests**

```bash
cd /Users/yann.moren/vision/backend
python3 -m uv run pytest tests/scripts/test_runtime_artifact_scripts.py -q
```

- [ ] **Step 5: Commit**

```bash
git add backend/src/argus/scripts/build_runtime_artifact.py \
  backend/tests/scripts/test_runtime_artifact_scripts.py \
  docs/runbook.md
git commit -m "feat(open-vocab): build compiled scene artifacts"
```

---

## Task 11: Open-Vocab Runtime Selection And Hot Vocabulary Fallback

**Files:**

- Modify: `backend/src/argus/vision/runtime_selection.py`
- Modify: `backend/src/argus/inference/engine.py`
- Modify: `backend/tests/vision/test_runtime_selection.py`
- Modify: `backend/tests/inference/test_engine.py`

- [ ] **Step 1: Add tests**

Tests:

- compiled open-vocab TensorRT artifact selected when hash matches
- compiled open-vocab artifact ignored when hash differs
- hot vocabulary command causes fallback to dynamic `.pt`
- fallback reason is `vocabulary_changed`

- [ ] **Step 2: Implement selector logic**

Make open-vocab artifact selection require `runtime_vocabulary_hash`.

- [ ] **Step 3: Implement engine fallback**

When command updates vocabulary and current detector runtime state says
`selected_backend=tensorrt_engine` or compiled ONNX:

- rebuild detector from canonical `.pt` model using `build_detector`
- apply `update_runtime_vocabulary`
- log fallback

- [ ] **Step 4: Run tests**

```bash
cd /Users/yann.moren/vision/backend
python3 -m uv run pytest \
  tests/vision/test_runtime_selection.py \
  tests/inference/test_engine.py \
  -q
```

- [ ] **Step 5: Commit**

```bash
git add backend/src/argus/vision/runtime_selection.py \
  backend/src/argus/inference/engine.py \
  backend/tests/vision/test_runtime_selection.py \
  backend/tests/inference/test_engine.py
git commit -m "feat(open-vocab): select compiled scene runtimes"
```

---

## Task 12: API Generation And Frontend Artifact Visibility

**Files:**

- Modify: `frontend/src/lib/api.generated.ts`
- Modify: `frontend/src/pages/Operations.tsx`
- Modify: `frontend/src/pages/Cameras.tsx` or camera wizard component
- Add/modify frontend tests near touched components

- [ ] **Step 1: Regenerate API client**

Run:

```bash
cd /Users/yann.moren/vision
corepack pnpm --dir frontend generate:api
```

- [ ] **Step 2: Add UI tests**

Tests should assert:

- model details can show `TensorRT artifact: valid`
- open-vocab scene can show `compiled stale` when vocabulary hash mismatch
- no artifact means UI says dynamic/fallback, not failure

- [ ] **Step 3: Implement minimal UI**

Keep it restrained:

- Operations/model card shows artifact count and best valid target.
- Camera wizard selected model summary shows dynamic vs compiled availability.
- Do not add a complex artifact builder UI in the first pass.

- [ ] **Step 4: Run frontend tests**

```bash
cd /Users/yann.moren/vision
CI=1 corepack pnpm --dir frontend test -- --run
```

- [ ] **Step 5: Commit**

```bash
git add frontend/src/lib/api.generated.ts frontend/src/pages frontend/src/components
git commit -m "feat(ui): show runtime artifact status"
```

---

## Task 13: A/B Documentation And Manual Validation

**Files:**

- Modify: `docs/imac-master-orin-lab-test-guide.md`
- Modify: `docs/runbook.md`
- Modify: `docs/scene-vision-profile-configuration-guide.md`

- [ ] **Step 1: Document compile timing expectations**

Add:

- per-scene compile is background
- dynamic `.pt` is for exploration
- compiled artifacts are for saved production scenes
- real timing is recorded from build metadata

- [ ] **Step 2: Add A/B validation checklist**

Checklist:

- fixed-vocab ONNX baseline
- fixed-vocab TensorRT artifact
- open-vocab dynamic `.pt`
- open-vocab compiled ONNX
- open-vocab compiled TensorRT
- vocabulary change fallback

- [ ] **Step 3: Run doc diff check**

```bash
git diff --check -- docs
```

- [ ] **Step 4: Commit**

```bash
git add docs/imac-master-orin-lab-test-guide.md docs/runbook.md docs/scene-vision-profile-configuration-guide.md
git commit -m "docs(runtime): explain optimized open-vocab artifacts"
```

---

## Task 14: Backend Verification Sweep

**Files:** no planned edits unless tests expose issues.

- [ ] **Step 1: Run focused backend suite**

```bash
cd /Users/yann.moren/vision/backend
python3 -m uv run pytest \
  tests/services/test_runtime_artifacts.py \
  tests/api/test_runtime_artifact_routes.py \
  tests/services/test_camera_worker_config.py \
  tests/vision/test_runtime_selection.py \
  tests/vision/test_ultralytics_engine_detector.py \
  tests/vision/test_detector_factory.py \
  tests/inference/test_engine.py \
  tests/scripts/test_runtime_artifact_scripts.py \
  -q
```

- [ ] **Step 2: Run lint/type checks for touched backend**

```bash
cd /Users/yann.moren/vision/backend
python3 -m uv run ruff check src/argus tests
python3 -m uv run mypy src/argus
```

- [ ] **Step 3: Fix only task-related failures**

Do not refactor unrelated modules.

- [ ] **Step 4: Commit fixes if needed**

```bash
git add backend/src/argus backend/tests
git commit -m "fix(runtime): harden artifact verification"
```

---

## Task 15: Push A/B Branch

**Files:** no edits.

- [ ] **Step 1: Check status**

```bash
git status --short
```

Expected: only intentional committed changes or unrelated untracked scratch files
left unstaged.

- [ ] **Step 2: Push**

```bash
git push origin codex/omnisight-ui-spec-implementation
```

- [ ] **Step 3: Report**

Report:

- commits
- tests run
- what to validate on Jetson
- known limitations

---

## Task 16: Track C DeepStream Runtime Lane, Future Only

**Do not execute in the A/B implementation round.**

**Files, later:**

- Create: `backend/src/argus/vision/deepstream_runtime.py`
- Create: `backend/src/argus/vision/deepstream_metadata.py`
- Create: `infra/deepstream/`
- Create: `docs/superpowers/specs/YYYY-MM-DD-deepstream-jetson-runtime-design.md`
- Create: `docs/superpowers/plans/YYYY-MM-DD-deepstream-jetson-runtime-implementation-plan.md`

Future task outline:

- Define DeepStream backend contract.
- Add NvDCF/NvDeepSORT profile presets.
- Add metadata bridge into existing track lifecycle.
- Add Jetson-only Compose/runtime packaging.
- Add Operations visibility for DeepStream pipeline health.

Acceptance for Track C should be separate from A/B.

---

## Self-Review

- Spec coverage: A fixed-vocab artifacts are covered by Tasks 1-8; B compiled
  open vocab is covered by Tasks 9-13; C is deliberately parked in Task 16.
- Placeholder scan: no TBD/TODO placeholders remain.
- Type consistency: artifact enum, contract, table, worker config, selector, and
  detector names match across tasks.
- Scope control: A/B can ship without implementing DeepStream or a native
  TensorRT binding.
