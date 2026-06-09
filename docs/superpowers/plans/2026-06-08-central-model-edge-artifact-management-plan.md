# Central Model, Artifact, and Edge Configuration Management Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build UI-driven model download/registration, edge model distribution, TensorRT/open-vocab runtime artifact creation, and central post-install edge configuration so normal Jetson setup no longer needs edge CLI after installer pairing.

**Architecture:** Extend the existing model catalog, runtime artifact registry, deployment node pairing, supervisor service-report, and worker lifecycle systems with typed desired-state jobs. The master stores model import jobs, node model assignments, artifact build jobs, edge inventory, and edge configuration revisions; the supervisor polls bounded jobs, performs node-local downloads/builds/validation, and reports results. TensorRT engines remain runtime artifacts for a target profile, not primary camera models.

**Tech Stack:** FastAPI, Pydantic, SQLAlchemy, Alembic-style migrations in `backend/src/argus/migrations/versions`, pytest, React, TypeScript, TanStack Query, Vitest, existing OpenAPI generation, Jetson/Linux supervisor services.

---

## Scope

This plan is intentionally larger than the earlier protected-control-plane/model-page plan. Keep that earlier plan focused on protecting the Vezor Master site and adding a basic local model admin surface. Use this plan for the complete central-to-edge model/artifact/config lifecycle.

Ship in phases:

1. Central model catalog registration and model import jobs.
2. Deployment node model assignments and supervisor-reported inventory.
3. Supervisor model sync jobs.
4. Runtime artifact build jobs for TensorRT and open-vocab exports.
5. Edge configuration profiles and applied revision reporting.
6. UI integration and docs/live validation.

## File Structure

### Backend contracts and routes

- Modify `backend/src/argus/api/contracts.py`: add request/response models for model imports, node assignments, inventory, model sync jobs, artifact build jobs, supervisor job events, and edge configuration revisions.
- Modify `backend/src/argus/api/v1/model_catalog.py`: add catalog register/download endpoints.
- Modify `backend/src/argus/api/v1/models.py`: add custom model import endpoint and model import job list endpoint.
- Modify `backend/src/argus/api/v1/runtime_artifacts.py`: add artifact build job endpoints under the existing model runtime artifact route.
- Modify `backend/src/argus/api/v1/deployment.py`: add deployment-node model assignment, inventory, model sync, supervisor job polling, supervisor job event, supervisor job completion, and edge configuration endpoints.
- Modify `backend/src/argus/api/v1/__init__.py`: register any new router if model lifecycle routes are split into a new file.

### Backend services and persistence

- Modify `backend/src/argus/models/enums.py`: add job status, model import source, model distribution status, artifact build status, artifact build format, and edge configuration status enums.
- Modify `backend/src/argus/models/tables.py`: add tables for model import jobs, deployment model assignments, deployment model sync jobs, deployment model inventory, runtime artifact build jobs, supervisor model job events, and edge configuration assignments.
- Create `backend/src/argus/migrations/versions/0042_central_model_edge_lifecycle.py`: migration for the new tables/enums/indexes.
- Create `backend/src/argus/services/model_lifecycle.py`: central service for catalog registration/download/import, node assignments, inventory, model sync jobs, artifact build jobs, and supervisor job state transitions.
- Modify `backend/src/argus/services/app.py`: instantiate `ModelLifecycleService`.
- Modify `backend/src/argus/services/model_catalog.py`: add trusted source/checksum metadata for bundled catalog entries where available and expose action readiness.
- Modify `backend/src/argus/services/runtime_artifacts.py`: add helper for creating artifacts from validated supervisor build results.
- Refactor `backend/src/argus/scripts/build_runtime_artifact.py`: move reusable payload/build helpers into `backend/src/argus/vision/runtime_artifact_builder.py` while keeping the CLI wrapper.

### Supervisor

- Modify `backend/src/argus/supervisor/operations_client.py`: add methods to poll model jobs, send job events, complete jobs, download assets, report inventory, fetch edge configuration, and report applied config.
- Create `backend/src/argus/supervisor/model_jobs.py`: execute model sync and artifact build jobs with bounded job types.
- Create `backend/src/argus/supervisor/model_inventory.py`: scan/report local model and artifact files with hash/size/profile metadata.
- Modify `backend/src/argus/supervisor/runner.py`: call model job reconciliation and edge configuration reconciliation on the existing supervisor loop.
- Modify `backend/src/argus/supervisor/reconciler.py`: block worker starts when required model sync or artifact build readiness is not satisfied.

### Frontend

- Modify `frontend/src/hooks/use-model-catalog.ts`: add catalog register/download mutations.
- Modify `frontend/src/hooks/use-models.ts`: add import job and artifact build job queries/mutations.
- Create `frontend/src/hooks/use-model-lifecycle.ts`: central hooks for node assignments, sync jobs, inventory, artifact build jobs, and edge configuration.
- Create `frontend/src/pages/Models.tsx`: model catalog/registered/imports/artifacts/edge distribution workspace.
- Create `frontend/src/pages/Models.test.tsx`: page tests for catalog actions, import progress, artifact build actions, and edge assignment state.
- Modify `frontend/src/App.tsx` and the navigation component files found by `rg -n "Deployment|Settings|FleetOps" frontend/src`: add the Models route/nav entry.
- Modify `frontend/src/pages/Deployment.tsx`: add node detail panels for model inventory, assignments, artifact jobs, and edge configuration.
- Modify `frontend/src/pages/Deployment.test.tsx`: verify the new node panels and actions.
- Modify `frontend/src/pages/Cameras.tsx` and `frontend/src/pages/Cameras.test.tsx`: surface missing/stale artifact readiness and direct build action from scene setup.

### Docs

- Modify `docs/product-installer-and-first-run-guide.md`: explain installer minimums and UI-driven post-install configuration.
- Modify `docs/operator-deployment-playbook.md`: add central model/artifact/edge configuration workflows.
- Modify `docs/runbook.md`: add model sync, TensorRT build, inventory, and edge config troubleshooting.
- Modify `docs/core-link-performance-guide.md` only if model distribution or edge config affects Core Link validation posture.
- Create or modify `docs/model-loading-and-configuration-guide.md`: make UI-driven model lifecycle the canonical process.

---

## Task 1: Add Lifecycle Enums, Tables, and Migration

**Files:**
- Modify: `backend/src/argus/models/enums.py`
- Modify: `backend/src/argus/models/tables.py`
- Create: `backend/src/argus/migrations/versions/0042_central_model_edge_lifecycle.py`
- Test: `backend/tests/models/test_model_edge_lifecycle_tables.py`

- [ ] **Step 1: Write the failing model/table test**

Create `backend/tests/models/test_model_edge_lifecycle_tables.py` with assertions that the new tables and enums are present in metadata:

```python
from argus.models.base import Base


def test_model_edge_lifecycle_tables_are_registered() -> None:
    table_names = set(Base.metadata.tables)
    assert "model_import_jobs" in table_names
    assert "deployment_model_assignments" in table_names
    assert "deployment_model_sync_jobs" in table_names
    assert "deployment_model_inventory" in table_names
    assert "runtime_artifact_build_jobs" in table_names
    assert "supervisor_model_job_events" in table_names
    assert "edge_configuration_assignments" in table_names
```

- [ ] **Step 2: Run the failing test**

Run:

```bash
python3 -m uv run --project backend pytest backend/tests/models/test_model_edge_lifecycle_tables.py -q
```

Expected: FAIL because the tables do not exist.

- [ ] **Step 3: Add enums**

Add these enums to `backend/src/argus/models/enums.py`:

```python
class ModelImportSource(StrEnum):
    CATALOG = "catalog"
    URL = "url"
    MASTER_PATH = "master_path"
    UPLOAD = "upload"


class ModelLifecycleJobStatus(StrEnum):
    QUEUED = "queued"
    ACCEPTED = "accepted"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    CANCELLED = "cancelled"


class DeploymentModelAssignmentStatus(StrEnum):
    DESIRED = "desired"
    SYNCING = "syncing"
    SYNCED = "synced"
    FAILED = "failed"
    REMOVED = "removed"


class RuntimeArtifactBuildFormat(StrEnum):
    ONNX_EXPORT = "onnx_export"
    TENSORRT_ENGINE = "tensorrt_engine"


class EdgeConfigurationApplyStatus(StrEnum):
    PENDING = "pending"
    APPLIED = "applied"
    FAILED = "failed"
```

- [ ] **Step 4: Add SQLAlchemy tables**

In `backend/src/argus/models/tables.py`, import the new enums and add focused table classes after `DeploymentNode`. Use JSONB for job payloads/events so the first implementation can stay schema-versioned without overfitting.

```python
class ModelImportJob(UUIDPrimaryKeyMixin, TimestampMixin, UpdatedAtMixin, Base):
    __tablename__ = "model_import_jobs"
    __table_args__ = (
        Index("ix_model_import_jobs_status", "status", "created_at"),
        Index("ix_model_import_jobs_catalog", "catalog_id"),
    )

    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False)
    catalog_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    source: Mapped[ModelImportSource] = mapped_column(enum_column(ModelImportSource, "model_import_source_enum"), nullable=False)
    status: Mapped[ModelLifecycleJobStatus] = mapped_column(enum_column(ModelLifecycleJobStatus, "model_lifecycle_job_status_enum"), nullable=False)
    actor_subject: Mapped[str] = mapped_column(String(255), nullable=False)
    model_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("models.id"), nullable=True)
    source_uri: Mapped[str | None] = mapped_column(Text, nullable=True)
    target_path: Mapped[str] = mapped_column(Text, nullable=False)
    expected_sha256: Mapped[str | None] = mapped_column(String(64), nullable=True)
    observed_sha256: Mapped[str | None] = mapped_column(String(64), nullable=True)
    size_bytes: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    progress: Mapped[dict[str, object]] = mapped_column(JSONB, nullable=False, default=dict)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
```

```python
class DeploymentModelAssignment(UUIDPrimaryKeyMixin, TimestampMixin, UpdatedAtMixin, Base):
    __tablename__ = "deployment_model_assignments"
    __table_args__ = (
        UniqueConstraint("deployment_node_id", "model_id", name="uq_deployment_model_assignment"),
        Index("ix_deployment_model_assignment_node", "deployment_node_id"),
    )

    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False)
    deployment_node_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("deployment_nodes.id"), nullable=False)
    model_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("models.id"), nullable=False)
    status: Mapped[DeploymentModelAssignmentStatus] = mapped_column(enum_column(DeploymentModelAssignmentStatus, "deployment_model_assignment_status_enum"), nullable=False)
    desired_path: Mapped[str | None] = mapped_column(Text, nullable=True)
    last_sync_job_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    actor_subject: Mapped[str] = mapped_column(String(255), nullable=False)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
```

```python
class DeploymentModelSyncJob(UUIDPrimaryKeyMixin, TimestampMixin, UpdatedAtMixin, Base):
    __tablename__ = "deployment_model_sync_jobs"
    __table_args__ = (
        Index("ix_deployment_model_sync_jobs_node", "deployment_node_id", "status"),
        Index("ix_deployment_model_sync_jobs_assignment", "assignment_id"),
    )

    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False)
    deployment_node_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("deployment_nodes.id"), nullable=False)
    assignment_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("deployment_model_assignments.id"), nullable=False)
    model_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("models.id"), nullable=False)
    status: Mapped[ModelLifecycleJobStatus] = mapped_column(enum_column(ModelLifecycleJobStatus, "deployment_model_sync_job_status_enum"), nullable=False)
    payload: Mapped[dict[str, object]] = mapped_column(JSONB, nullable=False, default=dict)
    actor_subject: Mapped[str] = mapped_column(String(255), nullable=False)
    claimed_by_supervisor_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    claimed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
```

```python
class DeploymentModelInventory(UUIDPrimaryKeyMixin, TimestampMixin, UpdatedAtMixin, Base):
    __tablename__ = "deployment_model_inventory"
    __table_args__ = (
        UniqueConstraint("deployment_node_id", "asset_kind", "asset_id", "sha256", name="uq_deployment_model_inventory_asset"),
        Index("ix_deployment_model_inventory_node", "deployment_node_id"),
    )

    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False)
    deployment_node_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("deployment_nodes.id"), nullable=False)
    asset_kind: Mapped[str] = mapped_column(String(32), nullable=False)
    asset_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    local_path: Mapped[str] = mapped_column(Text, nullable=False)
    sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    size_bytes: Mapped[int] = mapped_column(BigInteger, nullable=False)
    target_profile: Mapped[str | None] = mapped_column(String(128), nullable=True)
    runtime_versions: Mapped[dict[str, object]] = mapped_column(JSONB, nullable=False, default=dict)
    reported_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
```

```python
class RuntimeArtifactBuildJob(UUIDPrimaryKeyMixin, TimestampMixin, UpdatedAtMixin, Base):
    __tablename__ = "runtime_artifact_build_jobs"
    __table_args__ = (
        Index("ix_runtime_artifact_build_jobs_node", "deployment_node_id", "status"),
        Index("ix_runtime_artifact_build_jobs_model", "model_id", "created_at"),
    )

    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False)
    deployment_node_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("deployment_nodes.id"), nullable=False)
    model_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("models.id"), nullable=False)
    camera_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("cameras.id"), nullable=True)
    artifact_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("model_runtime_artifacts.id"), nullable=True)
    status: Mapped[ModelLifecycleJobStatus] = mapped_column(enum_column(ModelLifecycleJobStatus, "runtime_artifact_build_job_status_enum"), nullable=False)
    build_format: Mapped[RuntimeArtifactBuildFormat] = mapped_column(enum_column(RuntimeArtifactBuildFormat, "runtime_artifact_build_format_enum"), nullable=False)
    target_profile: Mapped[str] = mapped_column(String(128), nullable=False)
    precision: Mapped[RuntimeArtifactPrecision] = mapped_column(enum_column(RuntimeArtifactPrecision, "runtime_artifact_build_precision_enum"), nullable=False)
    payload: Mapped[dict[str, object]] = mapped_column(JSONB, nullable=False, default=dict)
    actor_subject: Mapped[str] = mapped_column(String(255), nullable=False)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
```

```python
class SupervisorModelJobEvent(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "supervisor_model_job_events"
    __table_args__ = (
        Index("ix_supervisor_model_job_events_job", "job_kind", "job_id", "created_at"),
    )

    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False)
    deployment_node_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("deployment_nodes.id"), nullable=False)
    job_kind: Mapped[str] = mapped_column(String(64), nullable=False)
    job_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    status: Mapped[ModelLifecycleJobStatus] = mapped_column(enum_column(ModelLifecycleJobStatus, "supervisor_model_job_event_status_enum"), nullable=False)
    message: Mapped[str | None] = mapped_column(Text, nullable=True)
    payload: Mapped[dict[str, object]] = mapped_column(JSONB, nullable=False, default=dict)
```

```python
class EdgeConfigurationAssignment(UUIDPrimaryKeyMixin, TimestampMixin, UpdatedAtMixin, Base):
    __tablename__ = "edge_configuration_assignments"
    __table_args__ = (
        UniqueConstraint("deployment_node_id", name="uq_edge_configuration_assignment_node"),
    )

    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False)
    deployment_node_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("deployment_nodes.id"), nullable=False)
    revision: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    desired_config: Mapped[dict[str, object]] = mapped_column(JSONB, nullable=False, default=dict)
    applied_revision: Mapped[int | None] = mapped_column(Integer, nullable=True)
    apply_status: Mapped[EdgeConfigurationApplyStatus] = mapped_column(enum_column(EdgeConfigurationApplyStatus, "edge_configuration_apply_status_enum"), nullable=False)
    last_applied_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    actor_subject: Mapped[str] = mapped_column(String(255), nullable=False)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
```

- [ ] **Step 5: Add migration**

Create `backend/src/argus/migrations/versions/0042_central_model_edge_lifecycle.py` following the style of adjacent migrations. Include enum creation where existing migrations create SQL enums manually, all seven tables, indexes, unique constraints, and downgrade drops in reverse dependency order.

- [ ] **Step 6: Run tests**

Run:

```bash
python3 -m uv run --project backend pytest backend/tests/models/test_model_edge_lifecycle_tables.py -q
```

Expected: PASS.

- [ ] **Step 7: Commit**

```bash
git add backend/src/argus/models/enums.py backend/src/argus/models/tables.py backend/src/argus/migrations/versions/0042_central_model_edge_lifecycle.py backend/tests/models/test_model_edge_lifecycle_tables.py
git commit -m "feat: add central model lifecycle tables"
```

## Task 2: Add API Contracts for Model Lifecycle

**Files:**
- Modify: `backend/src/argus/api/contracts.py`
- Test: `backend/tests/api/test_model_lifecycle_contracts.py`

- [ ] **Step 1: Write failing contract tests**

Create `backend/tests/api/test_model_lifecycle_contracts.py`:

```python
from uuid import uuid4

from argus.api.contracts import (
    EdgeConfigurationUpdate,
    ModelImportRequest,
    RuntimeArtifactBuildJobCreate,
)


def test_model_import_request_requires_checksum_for_url() -> None:
    payload = ModelImportRequest(
        source="url",
        source_uri="https://models.example/weights/yolo26n.onnx",
        expected_sha256="a" * 64,
        name="YOLO26n COCO",
        version="2026.1",
        task="detect",
        format="onnx",
        capability="fixed_vocab",
        input_shape={"width": 640, "height": 640},
        classes=[],
        license="AGPL-3.0",
    )
    assert payload.expected_sha256 == "a" * 64


def test_artifact_build_job_accepts_tensorrt_target_node() -> None:
    payload = RuntimeArtifactBuildJobCreate(
        deployment_node_id=uuid4(),
        build_format="tensorrt_engine",
        target_profile="linux-aarch64-nvidia-jetson",
        precision="fp16",
        input_shape={"width": 640, "height": 640},
        export_formats=["tensorrt_engine"],
    )
    assert payload.build_format == "tensorrt_engine"


def test_edge_configuration_update_contains_post_install_settings() -> None:
    payload = EdgeConfigurationUpdate(
        desired_config={
            "model_store_path": "/var/lib/vezor/models",
            "artifact_store_path": "/var/lib/vezor/artifacts",
            "worker_concurrency": 1,
            "runtime_preference": "tensorrt_first",
            "service_report_interval_seconds": 30,
            "stream_delivery_profile": "native",
        }
    )
    assert payload.desired_config["worker_concurrency"] == 1
```

- [ ] **Step 2: Run the failing test**

```bash
python3 -m uv run --project backend pytest backend/tests/api/test_model_lifecycle_contracts.py -q
```

Expected: FAIL because the contract models are missing.

- [ ] **Step 3: Add Pydantic contracts**

Add these models to `backend/src/argus/api/contracts.py` near existing model/runtime-artifact contracts. Use existing enum imports where available.

```python
class ModelImportRequest(BaseModel):
    source: ModelImportSource
    source_uri: str | None = Field(default=None, min_length=1)
    expected_sha256: str | None = Field(default=None, min_length=64, max_length=64)
    name: str = Field(min_length=1, max_length=255)
    version: str = Field(min_length=1, max_length=64)
    task: ModelTask
    format: ModelFormat
    capability: DetectorCapability = DetectorCapability.FIXED_VOCAB
    capability_config: ModelCapabilityConfig = Field(default_factory=ModelCapabilityConfig)
    input_shape: dict[str, int]
    classes: list[str] = Field(default_factory=list)
    license: str | None = Field(default=None, max_length=255)

    @model_validator(mode="after")
    def validate_source(self) -> "ModelImportRequest":
        if self.source in {ModelImportSource.URL, ModelImportSource.MASTER_PATH} and not self.source_uri:
            raise ValueError("source_uri is required for URL and master path imports.")
        if self.source is ModelImportSource.URL and not self.expected_sha256:
            raise ValueError("expected_sha256 is required for URL imports.")
        return self
```

```python
class ModelImportJobResponse(BaseModel):
    id: UUID
    tenant_id: UUID
    catalog_id: str | None = None
    source: ModelImportSource
    status: ModelLifecycleJobStatus
    actor_subject: str
    model_id: UUID | None = None
    source_uri: str | None = None
    target_path: str
    expected_sha256: str | None = None
    observed_sha256: str | None = None
    size_bytes: int | None = None
    progress: dict[str, Any] = Field(default_factory=dict)
    error: str | None = None
    created_at: datetime
    updated_at: datetime
```

```python
class DeploymentModelAssignmentCreate(BaseModel):
    model_id: UUID
    desired_path: str | None = None


class DeploymentModelAssignmentResponse(BaseModel):
    id: UUID
    tenant_id: UUID
    deployment_node_id: UUID
    model_id: UUID
    status: DeploymentModelAssignmentStatus
    desired_path: str | None = None
    last_sync_job_id: UUID | None = None
    error: str | None = None
    created_at: datetime
    updated_at: datetime
```

```python
class DeploymentModelSyncJobResponse(BaseModel):
    id: UUID
    tenant_id: UUID
    deployment_node_id: UUID
    assignment_id: UUID
    model_id: UUID
    status: ModelLifecycleJobStatus
    payload: dict[str, Any] = Field(default_factory=dict)
    claimed_by_supervisor_id: str | None = None
    claimed_at: datetime | None = None
    completed_at: datetime | None = None
    error: str | None = None
    created_at: datetime
    updated_at: datetime
```

```python
class DeploymentModelInventoryItem(BaseModel):
    asset_kind: Literal["model", "runtime_artifact"]
    asset_id: UUID
    local_path: str = Field(min_length=1)
    sha256: str = Field(min_length=64, max_length=64)
    size_bytes: int = Field(gt=0)
    target_profile: str | None = None
    runtime_versions: dict[str, Any] = Field(default_factory=dict)
    reported_at: datetime


class DeploymentModelInventoryReport(BaseModel):
    items: list[DeploymentModelInventoryItem] = Field(default_factory=list)
```

```python
class RuntimeArtifactBuildJobCreate(BaseModel):
    deployment_node_id: UUID
    camera_id: UUID | None = None
    build_format: RuntimeArtifactBuildFormat
    target_profile: str = Field(min_length=1, max_length=128)
    precision: RuntimeArtifactPrecision
    input_shape: dict[str, int]
    export_formats: list[RuntimeArtifactBuildFormat] = Field(default_factory=list)
    builder_options: dict[str, Any] = Field(default_factory=dict)


class RuntimeArtifactBuildJobResponse(BaseModel):
    id: UUID
    tenant_id: UUID
    deployment_node_id: UUID
    model_id: UUID
    camera_id: UUID | None = None
    artifact_id: UUID | None = None
    status: ModelLifecycleJobStatus
    build_format: RuntimeArtifactBuildFormat
    target_profile: str
    precision: RuntimeArtifactPrecision
    payload: dict[str, Any] = Field(default_factory=dict)
    error: str | None = None
    created_at: datetime
    updated_at: datetime
```

```python
class SupervisorModelJobEventCreate(BaseModel):
    job_kind: Literal["model_sync", "artifact_build"]
    status: ModelLifecycleJobStatus
    message: str | None = None
    payload: dict[str, Any] = Field(default_factory=dict)


class EdgeConfigurationUpdate(BaseModel):
    desired_config: dict[str, Any] = Field(default_factory=dict)


class EdgeConfigurationResponse(BaseModel):
    id: UUID
    tenant_id: UUID
    deployment_node_id: UUID
    revision: int
    desired_config: dict[str, Any]
    applied_revision: int | None = None
    apply_status: EdgeConfigurationApplyStatus
    last_applied_at: datetime | None = None
    error: str | None = None
    created_at: datetime
    updated_at: datetime
```

- [ ] **Step 4: Run contract tests**

```bash
python3 -m uv run --project backend pytest backend/tests/api/test_model_lifecycle_contracts.py -q
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/src/argus/api/contracts.py backend/tests/api/test_model_lifecycle_contracts.py
git commit -m "feat: add model lifecycle api contracts"
```

## Task 3: Central Model Import and Catalog Registration Service

**Files:**
- Create: `backend/src/argus/services/model_lifecycle.py`
- Modify: `backend/src/argus/services/app.py`
- Modify: `backend/src/argus/services/model_catalog.py`
- Modify: `backend/src/argus/api/v1/model_catalog.py`
- Modify: `backend/src/argus/api/v1/models.py`
- Test: `backend/tests/services/test_model_lifecycle_imports.py`
- Test: `backend/tests/api/test_model_lifecycle_routes.py`

- [ ] **Step 1: Write service tests**

Create `backend/tests/services/test_model_lifecycle_imports.py` with tests that create a temporary `.onnx` file, compute its hash, register a catalog-backed model, and reject URL imports without matching hash.

```python
import hashlib

import pytest

from argus.api.contracts import ModelImportRequest
from argus.models.enums import DetectorCapability, ModelFormat, ModelImportSource, ModelTask


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


@pytest.mark.asyncio
async def test_register_master_path_import_creates_model(model_lifecycle_service, tmp_path) -> None:
    model_path = tmp_path / "yolo26n.onnx"
    model_path.write_bytes(b"fake-onnx")
    response = await model_lifecycle_service.import_model_from_request(
        tenant_id=model_lifecycle_service.test_tenant_id,
        actor_subject="admin@example.test",
        payload=ModelImportRequest(
            source=ModelImportSource.MASTER_PATH,
            source_uri=str(model_path),
            expected_sha256=_sha256(b"fake-onnx"),
            name="YOLO26n COCO",
            version="2026.1",
            task=ModelTask.DETECT,
            format=ModelFormat.ONNX,
            capability=DetectorCapability.FIXED_VOCAB,
            input_shape={"width": 640, "height": 640},
            classes=[],
            license="AGPL-3.0",
        ),
    )
    assert response.status == "succeeded"
    assert response.model_id is not None
    assert response.observed_sha256 == _sha256(b"fake-onnx")
```

- [ ] **Step 2: Run the failing service test**

```bash
python3 -m uv run --project backend pytest backend/tests/services/test_model_lifecycle_imports.py -q
```

Expected: FAIL because `ModelLifecycleService` does not exist.

- [ ] **Step 3: Implement import service**

Create `backend/src/argus/services/model_lifecycle.py` with:

- `ModelLifecycleService.__init__(session_factory, model_store_path: Path | None = None)`
- `import_model_from_request(tenant_id, actor_subject, payload) -> ModelImportJobResponse`
- `register_catalog_entry(tenant_id, actor_subject, catalog_id) -> ModelImportJobResponse`
- helper `_hash_file(path: Path) -> str`
- helper `_model_to_import_job_response(job: ModelImportJob) -> ModelImportJobResponse`

Rules:

- `MASTER_PATH` imports require file existence and hash verification when `expected_sha256` is provided.
- `URL` imports create a queued job in this task and do not download yet.
- catalog registration uses `list_model_catalog_entries()` and the entry `path_hint`.
- successful file-backed imports create a `Model` row and a succeeded `ModelImportJob`.
- failed imports create a failed job with `error`.

- [ ] **Step 4: Wire service into `AppServices`**

Modify `backend/src/argus/services/app.py` so `services.model_lifecycle` is available beside `services.models`, `services.deployment`, and `services.runtime_artifacts`.

- [ ] **Step 5: Add route tests**

Create route tests in `backend/tests/api/test_model_lifecycle_routes.py`:

```python
import pytest


@pytest.mark.asyncio
async def test_catalog_register_requires_admin(api_client, admin_headers, catalog_model_file) -> None:
    response = await api_client.post(
        "/api/v1/model-catalog/yolo26n-coco-onnx/register",
        headers=admin_headers,
    )
    assert response.status_code == 201
    assert response.json()["status"] == "succeeded"


@pytest.mark.asyncio
async def test_models_import_url_requires_admin(api_client, viewer_headers) -> None:
    response = await api_client.post(
        "/api/v1/models/import-url",
        headers=viewer_headers,
        json={
            "source": "url",
            "source_uri": "https://models.example/yolo26n.onnx",
            "expected_sha256": "a" * 64,
            "name": "YOLO26n COCO",
            "version": "2026.1",
            "task": "detect",
            "format": "onnx",
            "capability": "fixed_vocab",
            "input_shape": {"width": 640, "height": 640},
            "classes": [],
            "license": "AGPL-3.0",
        },
    )
    assert response.status_code == 403
```

- [ ] **Step 6: Implement routes**

Add admin endpoints:

- `POST /api/v1/model-catalog/{catalog_id}/register`
- `POST /api/v1/model-catalog/{catalog_id}/download`
- `GET /api/v1/model-import-jobs`
- `POST /api/v1/models/import-url`

For `download`, create a queued `ModelImportJob` when the catalog entry has a trusted source URL/checksum. If the catalog entry only has a bundled `path_hint`, return 409 with a message that the artifact is expected to be bundled or mounted.

- [ ] **Step 7: Run tests**

```bash
python3 -m uv run --project backend pytest backend/tests/services/test_model_lifecycle_imports.py backend/tests/api/test_model_lifecycle_routes.py -q
```

Expected: PASS.

- [ ] **Step 8: Commit**

```bash
git add backend/src/argus/services/model_lifecycle.py backend/src/argus/services/app.py backend/src/argus/services/model_catalog.py backend/src/argus/api/v1/model_catalog.py backend/src/argus/api/v1/models.py backend/tests/services/test_model_lifecycle_imports.py backend/tests/api/test_model_lifecycle_routes.py
git commit -m "feat: add central model import lifecycle"
```

## Task 4: Deployment Node Model Assignments and Inventory API

**Files:**
- Modify: `backend/src/argus/services/model_lifecycle.py`
- Modify: `backend/src/argus/api/v1/deployment.py`
- Test: `backend/tests/services/test_deployment_model_inventory.py`
- Test: `backend/tests/api/test_deployment_model_lifecycle_routes.py`

- [ ] **Step 1: Write service tests**

Create tests for:

- assigning a model to a deployment node;
- duplicate assignment returning the existing assignment;
- supervisor inventory upsert replacing stale records for the node;
- node credential cannot report inventory for a different deployment node.

Write these exact tests and assertions:

- `test_assign_model_to_deployment_node_creates_desired_assignment`: create a tenant, model, and deployment node; call `assign_model_to_node`; assert status is `DESIRED`, `model_id` matches, and `deployment_node_id` matches.
- `test_duplicate_model_assignment_reuses_existing_assignment`: call `assign_model_to_node` twice for the same model/node; assert the second response has the same assignment id and there is one assignment row.
- `test_inventory_report_upserts_node_assets`: report one model asset twice with the same SHA-256 and different `reported_at`; assert one inventory row remains and `reported_at` is updated.
- `test_inventory_report_rejects_wrong_authenticated_node`: authenticate as node A and report inventory for node B; assert the service raises a permission error or route returns 403.

- [ ] **Step 2: Run failing tests**

```bash
python3 -m uv run --project backend pytest backend/tests/services/test_deployment_model_inventory.py -q
```

Expected: FAIL because assignment/inventory methods are missing.

- [ ] **Step 3: Implement service methods**

Add methods to `ModelLifecycleService`:

- `list_model_assignments(tenant_id, deployment_node_id)`
- `assign_model_to_node(tenant_id, deployment_node_id, payload, actor_subject)`
- `remove_model_assignment(tenant_id, deployment_node_id, assignment_id, actor_subject)`
- `list_model_inventory(tenant_id, deployment_node_id)`
- `record_model_inventory(tenant_id, supervisor_id, authenticated_node_id, payload)`

Rules:

- assignments require the deployment node and model to exist;
- only edge nodes and central nodes with valid deployment rows can receive assignments;
- inventory reports require `authenticated_node_id == deployment_node_id` unless the caller is admin;
- inventory reports upsert by `(deployment_node_id, asset_kind, asset_id, sha256)`;
- when inventory contains a model matching an assignment hash, assignment status becomes `synced`.

- [ ] **Step 4: Add API route tests**

Create these route tests:

- `test_admin_can_assign_model_to_node`: POST a model assignment as admin and assert HTTP 201 plus returned `model_id`.
- `test_admin_can_list_node_inventory`: GET inventory as admin and assert HTTP 200 with the reported asset.
- `test_supervisor_can_report_own_inventory`: POST inventory with a node credential for the matching node and assert HTTP 201.
- `test_supervisor_cannot_report_other_node_inventory`: POST inventory with a node credential for a different node and assert HTTP 403.

- [ ] **Step 5: Implement deployment routes**

Add to `backend/src/argus/api/v1/deployment.py`:

- `GET /nodes/{node_id}/model-assignments`
- `POST /nodes/{node_id}/model-assignments`
- `DELETE /nodes/{node_id}/model-assignments/{assignment_id}`
- `GET /nodes/{node_id}/model-inventory`
- `POST /supervisors/{supervisor_id}/model-inventory`

- [ ] **Step 6: Run tests**

```bash
python3 -m uv run --project backend pytest backend/tests/services/test_deployment_model_inventory.py backend/tests/api/test_deployment_model_lifecycle_routes.py -q
```

Expected: PASS.

- [ ] **Step 7: Commit**

```bash
git add backend/src/argus/services/model_lifecycle.py backend/src/argus/api/v1/deployment.py backend/tests/services/test_deployment_model_inventory.py backend/tests/api/test_deployment_model_lifecycle_routes.py
git commit -m "feat: add deployment model assignments"
```

## Task 5: Supervisor Model Sync Jobs

**Files:**
- Modify: `backend/src/argus/services/model_lifecycle.py`
- Modify: `backend/src/argus/api/v1/deployment.py`
- Modify: `backend/src/argus/supervisor/operations_client.py`
- Create: `backend/src/argus/supervisor/model_jobs.py`
- Create: `backend/src/argus/supervisor/model_inventory.py`
- Test: `backend/tests/services/test_supervisor_model_jobs.py`
- Test: `backend/tests/supervisor/test_model_jobs.py`
- Test: `backend/tests/supervisor/test_model_inventory.py`

- [ ] **Step 1: Write central job tests**

Create `backend/tests/services/test_supervisor_model_jobs.py` with these tests:

- `test_create_model_sync_job_for_assigned_model_sets_assignment_syncing`: create an assignment, start a sync job, assert job status is `QUEUED` and assignment status is `SYNCING`.
- `test_poll_model_jobs_returns_only_jobs_for_authenticated_node`: create jobs for two nodes, poll as node A, assert only node A jobs are returned.
- `test_job_event_updates_status_and_records_event`: record a `RUNNING` event, assert job status is `RUNNING` and an event row exists.
- `test_complete_model_sync_job_marks_assignment_synced`: complete a job with matching hash/path, assert job status is `SUCCEEDED` and assignment status is `SYNCED`.

- [ ] **Step 2: Run failing central job tests**

```bash
python3 -m uv run --project backend pytest backend/tests/services/test_supervisor_model_jobs.py -q
```

Expected: FAIL because model sync job methods are missing.

- [ ] **Step 3: Implement central model sync jobs**

Use the dedicated `DeploymentModelSyncJob` table from Task 1 for model distribution jobs. Use `RuntimeArtifactBuildJob` only for runtime artifact builds.

Central methods:

- `create_model_sync_job(tenant_id, deployment_node_id, actor_subject)`
- `poll_supervisor_model_jobs(tenant_id, supervisor_id, authenticated_node_id, limit)`
- `record_supervisor_model_job_event(tenant_id, supervisor_id, authenticated_node_id, job_id, payload)`
- `complete_supervisor_model_job(tenant_id, supervisor_id, authenticated_node_id, job_id, payload)`

Model sync job payload must include:

```json
{
  "job_type": "model_sync",
  "schema_version": 1,
  "deployment_node_id": "<uuid>",
  "model_id": "<uuid>",
  "model_name": "YOLO26n COCO",
  "source_path": "models/yolo26n.onnx",
  "expected_sha256": "<64 hex chars>",
  "size_bytes": 123,
  "target_path": "/var/lib/vezor/models/yolo26n.onnx"
}
```

- [ ] **Step 4: Write supervisor executor tests**

Create `backend/tests/supervisor/test_model_jobs.py` with these tests:

- `test_model_sync_job_copies_file_and_reports_inventory`: create a source file, run a model sync job, assert destination exists and inventory report contains matching SHA-256.
- `test_model_sync_job_rejects_hash_mismatch`: provide an expected hash that differs from the source file, run the job, assert a failed event is reported and no destination file is accepted.
- `test_model_job_executor_ignores_unknown_job_type`: pass a job with `job_type="unknown"`, assert the executor reports failure with `Unsupported model job type`.

Create `backend/tests/supervisor/test_model_inventory.py` with these tests:

- `test_inventory_scanner_reports_hash_size_and_path`: scan a configured model path and assert hash, size, and path are present.
- `test_inventory_scanner_skips_missing_paths`: scan a missing path and assert the result list is empty.

- [ ] **Step 5: Implement supervisor model sync**

Create `backend/src/argus/supervisor/model_jobs.py` with:

- `SupervisorModelJobExecutor`
- `execute_once()`
- `execute_model_sync(job)`
- bounded local copy/download helper;
- SHA-256 verification;
- event reporting at accepted, running, succeeded, failed.

Create `backend/src/argus/supervisor/model_inventory.py` with:

- `InventoryScanner`
- `scan_models(assignments_or_paths)`
- `_sha256_file(path)`

Use existing `SupervisorOperationsClient._request()` for HTTP calls and credentials.

- [ ] **Step 6: Add supervisor API client methods**

In `backend/src/argus/supervisor/operations_client.py`, add:

- `poll_model_jobs(limit: int)`
- `record_model_job_event(job_id, event)`
- `complete_model_job(job_id, result)`
- `download_model_asset(asset_id, destination_path)`
- `record_model_inventory(report)`

- [ ] **Step 7: Wire routes**

Add deployment API endpoints:

- `POST /nodes/{node_id}/model-sync-jobs`
- `POST /supervisors/{supervisor_id}/model-jobs/poll`
- `POST /supervisors/{supervisor_id}/model-jobs/{job_id}/events`
- `POST /supervisors/{supervisor_id}/model-jobs/{job_id}/complete`
- `GET /model-assets/{asset_id}/download` with admin-or-owning-supervisor authorization.

- [ ] **Step 8: Run tests**

```bash
python3 -m uv run --project backend pytest backend/tests/services/test_supervisor_model_jobs.py backend/tests/supervisor/test_model_jobs.py backend/tests/supervisor/test_model_inventory.py -q
```

Expected: PASS.

- [ ] **Step 9: Commit**

```bash
git add backend/src/argus/services/model_lifecycle.py backend/src/argus/api/v1/deployment.py backend/src/argus/supervisor/operations_client.py backend/src/argus/supervisor/model_jobs.py backend/src/argus/supervisor/model_inventory.py backend/tests/services/test_supervisor_model_jobs.py backend/tests/supervisor/test_model_jobs.py backend/tests/supervisor/test_model_inventory.py
git commit -m "feat: sync models to deployment nodes"
```

## Task 6: Runtime Artifact Build Jobs

**Files:**
- Create: `backend/src/argus/vision/runtime_artifact_builder.py`
- Modify: `backend/src/argus/scripts/build_runtime_artifact.py`
- Modify: `backend/src/argus/services/model_lifecycle.py`
- Modify: `backend/src/argus/services/runtime_artifacts.py`
- Modify: `backend/src/argus/api/v1/runtime_artifacts.py`
- Modify: `backend/src/argus/supervisor/model_jobs.py`
- Test: `backend/tests/vision/test_runtime_artifact_builder.py`
- Test: `backend/tests/services/test_runtime_artifact_build_jobs.py`
- Test: `backend/tests/supervisor/test_artifact_build_jobs.py`

- [ ] **Step 1: Write builder tests**

Create `backend/tests/vision/test_runtime_artifact_builder.py` by moving coverage from CLI behavior into reusable builder tests:

Write these tests:

- `test_fixed_vocab_tensorrt_payload_includes_source_and_engine_hash`: create source and engine files, build the payload, assert source SHA-256, engine SHA-256, size, `kind="tensorrt_engine"`, and `runtime_backend="tensorrt_engine"`.
- `test_open_vocab_payload_requires_runtime_vocabulary`: call open-vocab payload builder with an empty vocabulary and assert `ValueError`.
- `test_open_vocab_payload_uses_vocabulary_hash`: use a fake YOLOE loader, export an artifact, and assert payload `vocabulary_hash` equals the hash returned by `hash_vocabulary(normalize_vocabulary_terms(["person", "laptop"]))`.

- [ ] **Step 2: Extract builder library**

Move reusable functions from `backend/src/argus/scripts/build_runtime_artifact.py` into `backend/src/argus/vision/runtime_artifact_builder.py`:

- `sha256_file`
- `file_size`
- `build_fixed_vocab_artifact_payload`
- `build_open_vocab_scene_artifact_payloads`

Keep CLI argument parsing and `post_json()` in the script.

- [ ] **Step 3: Write central artifact build job tests**

Create `backend/tests/services/test_runtime_artifact_build_jobs.py` with these tests:

- `test_create_tensorrt_build_job_requires_assigned_model_on_node`: request a TensorRT job before node assignment and assert 409 or service conflict.
- `test_create_open_vocab_build_job_requires_camera_vocabulary`: request open-vocab export for a camera with empty vocabulary and assert validation error.
- `test_complete_artifact_build_job_registers_runtime_artifact`: complete a job with a valid artifact payload and assert `artifact_id` is set and a `ModelRuntimeArtifact` row exists.
- `test_artifact_build_job_rejects_source_hash_mismatch`: complete a job with a mismatched `source_model_sha256` and assert failure with no artifact row.

- [ ] **Step 4: Implement central artifact build jobs**

Add `ModelLifecycleService` methods:

- `create_runtime_artifact_build_job(tenant_id, model_id, payload, actor_subject)`
- `list_runtime_artifact_build_jobs(tenant_id, model_id)`
- `complete_runtime_artifact_build_job(tenant_id, authenticated_node_id, job_id, result)`

Build job payload must include:

```json
{
  "job_type": "artifact_build",
  "schema_version": 1,
  "model_id": "<uuid>",
  "camera_id": "<uuid-or-null>",
  "source_model_sha256": "<64 hex chars>",
  "source_model_path": "/var/lib/vezor/models/yolo26n.onnx",
  "build_format": "tensorrt_engine",
  "target_profile": "linux-aarch64-nvidia-jetson",
  "precision": "fp16",
  "input_shape": {"width": 640, "height": 640},
  "runtime_vocabulary": [],
  "vocabulary_hash": null,
  "vocabulary_version": null,
  "output_dir": "/var/lib/vezor/artifacts"
}
```

Rules:

- fixed-vocab TensorRT jobs require a model assignment for the target node;
- open-vocab jobs require `camera_id`, camera uses the model, and camera vocabulary is non-empty;
- target profile must match the deployment node `host_profile` or be explicitly allowed by the latest hardware report;
- completing a successful job calls runtime artifact creation using the supervisor-provided payload and marks the build job succeeded;
- completing a failed job records concrete error and leaves no valid artifact.

- [ ] **Step 5: Add API routes**

Add to `backend/src/argus/api/v1/runtime_artifacts.py`:

- `POST /api/v1/models/{model_id}/runtime-artifact-build-jobs`
- `GET /api/v1/models/{model_id}/runtime-artifact-build-jobs`

- [ ] **Step 6: Add supervisor artifact build executor tests**

Create `backend/tests/supervisor/test_artifact_build_jobs.py` with these tests:

- `test_tensorrt_build_job_invokes_engine_builder_with_bounded_options`: use a fake `TensorRTEngineBuilder`, execute a TensorRT job, and assert the fake received source path, output path, input shape, and precision.
- `test_open_vocab_build_job_exports_requested_formats`: use a fake YOLOE loader, request ONNX and TensorRT outputs, and assert two artifact payloads are reported.
- `test_artifact_build_job_reports_failure_when_source_model_missing`: execute a job with a missing source path and assert a failed completion event.
- `test_artifact_build_job_reports_runtime_versions`: execute a successful fake build and assert completion payload includes TensorRT/CUDA/provider versions.

- [ ] **Step 7: Implement supervisor artifact builds**

Extend `backend/src/argus/supervisor/model_jobs.py`:

- dispatch `artifact_build`;
- for fixed-vocab TensorRT, call a bounded builder wrapper that can use `trtexec` or Ultralytics export according to model format and configured runtime;
- for open-vocab scene artifacts, call `build_open_vocab_scene_artifact_payloads`;
- report build events;
- complete with artifact payload matching `RuntimeArtifactCreate`.

The first engine builder wrapper can be implemented as a small protocol so tests use a fake:

```python
class TensorRTEngineBuilder(Protocol):
    def build(
        self,
        *,
        source_path: Path,
        output_path: Path,
        input_shape: dict[str, int],
        precision: str,
    ) -> Path:
        raise NotImplementedError
```

- [ ] **Step 8: Run tests**

```bash
python3 -m uv run --project backend pytest backend/tests/vision/test_runtime_artifact_builder.py backend/tests/services/test_runtime_artifact_build_jobs.py backend/tests/supervisor/test_artifact_build_jobs.py -q
```

Expected: PASS.

- [ ] **Step 9: Commit**

```bash
git add backend/src/argus/vision/runtime_artifact_builder.py backend/src/argus/scripts/build_runtime_artifact.py backend/src/argus/services/model_lifecycle.py backend/src/argus/services/runtime_artifacts.py backend/src/argus/api/v1/runtime_artifacts.py backend/src/argus/supervisor/model_jobs.py backend/tests/vision/test_runtime_artifact_builder.py backend/tests/services/test_runtime_artifact_build_jobs.py backend/tests/supervisor/test_artifact_build_jobs.py
git commit -m "feat: build runtime artifacts from central jobs"
```

## Task 7: Central Edge Configuration Assignments

**Files:**
- Modify: `backend/src/argus/services/model_lifecycle.py`
- Modify: `backend/src/argus/api/v1/deployment.py`
- Modify: `backend/src/argus/supervisor/operations_client.py`
- Create: `backend/src/argus/supervisor/edge_configuration.py`
- Modify: `backend/src/argus/supervisor/runner.py`
- Test: `backend/tests/services/test_edge_configuration_assignments.py`
- Test: `backend/tests/supervisor/test_edge_configuration.py`

- [ ] **Step 1: Write service tests**

Create these tests:

- `test_put_edge_configuration_increments_revision`: update a node config twice and assert revision changes from 1 to 2.
- `test_supervisor_fetches_only_own_edge_configuration`: create configs for two nodes, fetch as node A, and assert node B config is not returned.
- `test_apply_report_marks_revision_applied`: report revision 2 as applied and assert `applied_revision == 2`, `apply_status == APPLIED`, and `error is None`.
- `test_apply_report_with_error_marks_failed`: report an error for revision 2 and assert `apply_status == FAILED` and error text is preserved.

- [ ] **Step 2: Implement edge configuration service**

Add methods:

- `get_edge_configuration(tenant_id, deployment_node_id)`
- `update_edge_configuration(tenant_id, deployment_node_id, payload, actor_subject)`
- `get_supervisor_edge_configuration(tenant_id, supervisor_id, authenticated_node_id)`
- `record_edge_configuration_apply_report(tenant_id, supervisor_id, authenticated_node_id, revision, status, error)`

Validate `desired_config` keys against an allowlist:

```python
EDGE_CONFIGURATION_ALLOWED_KEYS = {
    "model_store_path",
    "artifact_store_path",
    "model_store_max_bytes",
    "artifact_store_max_bytes",
    "worker_concurrency",
    "runtime_preference",
    "fallback_policy",
    "service_report_interval_seconds",
    "hardware_report_interval_seconds",
    "stream_delivery_profile",
    "webrtc_additional_hosts",
    "webrtc_allowed_origins",
    "operations_mode",
    "support_bundle_policy",
    "evidence_retention_profile",
    "privacy_profile",
}
```

- [ ] **Step 3: Add deployment routes**

Add:

- `GET /nodes/{node_id}/edge-configuration`
- `PUT /nodes/{node_id}/edge-configuration`
- `GET /supervisors/{supervisor_id}/edge-configuration`
- `POST /supervisors/{supervisor_id}/edge-configuration/apply-report`

- [ ] **Step 4: Write supervisor configuration tests**

Create `backend/tests/supervisor/test_edge_configuration.py` with these tests:

- `test_edge_configuration_applies_store_paths_and_intervals`: apply store path and interval settings, assert directories are created and interval values are stored.
- `test_edge_configuration_rejects_unsupported_key`: include `shell_command` and assert the applier reports a failed unsupported-key result.
- `test_edge_configuration_reports_applied_revision`: apply revision 3 and assert the report contains revision 3 with status `applied`.

- [ ] **Step 5: Implement supervisor config applier**

Create `backend/src/argus/supervisor/edge_configuration.py` with:

- `EdgeConfigurationApplier`
- allowlisted apply methods for model/artifact store directories and interval values;
- a report object containing revision, status, and error.

Do not rewrite arbitrary system files in this task. For MediaMTX/NATS/service manager changes, store desired values and report `failed` with a specific unsupported message unless the existing installer/service-artifact renderer already has a safe update helper.

- [ ] **Step 6: Wire runner loop**

Modify `backend/src/argus/supervisor/runner.py` so the supervisor fetches edge configuration and applies new revisions before model jobs and worker lifecycle reconciliation.

- [ ] **Step 7: Run tests**

```bash
python3 -m uv run --project backend pytest backend/tests/services/test_edge_configuration_assignments.py backend/tests/supervisor/test_edge_configuration.py -q
```

Expected: PASS.

- [ ] **Step 8: Commit**

```bash
git add backend/src/argus/services/model_lifecycle.py backend/src/argus/api/v1/deployment.py backend/src/argus/supervisor/operations_client.py backend/src/argus/supervisor/edge_configuration.py backend/src/argus/supervisor/runner.py backend/tests/services/test_edge_configuration_assignments.py backend/tests/supervisor/test_edge_configuration.py
git commit -m "feat: manage edge configuration from central"
```

## Task 8: Frontend Hooks for Model Lifecycle

**Files:**
- Modify: `frontend/src/hooks/use-model-catalog.ts`
- Modify: `frontend/src/hooks/use-models.ts`
- Modify: `frontend/src/hooks/use-deployment.ts`
- Create: `frontend/src/hooks/use-model-lifecycle.ts`
- Test: `frontend/src/hooks/use-model-lifecycle.test.tsx`

- [ ] **Step 1: Write hook tests**

Create `frontend/src/hooks/use-model-lifecycle.test.tsx` with API-client mocks that verify:

```typescript
it("registers catalog models and invalidates catalog plus model queries", async () => {});
it("assigns a model to a deployment node and invalidates node assignment queries", async () => {});
it("starts an artifact build job and invalidates artifact job queries", async () => {});
it("updates edge configuration and invalidates deployment node config", async () => {});
```

- [ ] **Step 2: Run failing hook tests**

```bash
npm --prefix frontend run test -- use-model-lifecycle.test.tsx
```

Expected: FAIL because hooks are missing.

- [ ] **Step 3: Implement hooks**

Create `frontend/src/hooks/use-model-lifecycle.ts` with:

- `useRegisterCatalogModel()`
- `useDownloadCatalogModel()`
- `useImportModelFromUrl()`
- `useModelImportJobs()`
- `useDeploymentModelAssignments(nodeId)`
- `useAssignDeploymentModel(nodeId)`
- `useRemoveDeploymentModelAssignment(nodeId)`
- `useCreateModelSyncJob(nodeId)`
- `useDeploymentModelInventory(nodeId)`
- `useRuntimeArtifactBuildJobs(modelId)`
- `useCreateRuntimeArtifactBuildJob(modelId)`
- `useEdgeConfiguration(nodeId)`
- `useUpdateEdgeConfiguration(nodeId)`

Each mutation must call `toApiError()` and invalidate the smallest relevant query keys.

- [ ] **Step 4: Run hook tests**

```bash
npm --prefix frontend run test -- use-model-lifecycle.test.tsx
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/hooks/use-model-catalog.ts frontend/src/hooks/use-models.ts frontend/src/hooks/use-deployment.ts frontend/src/hooks/use-model-lifecycle.ts frontend/src/hooks/use-model-lifecycle.test.tsx
git commit -m "feat: add model lifecycle frontend hooks"
```

## Task 9: Models UI Workspace

**Files:**
- Create: `frontend/src/pages/Models.tsx`
- Create: `frontend/src/pages/Models.test.tsx`
- Modify: `frontend/src/App.tsx`
- Modify: navigation component files that define sidebar/topnav routes.

- [ ] **Step 1: Write page tests**

Create `frontend/src/pages/Models.test.tsx` with tests:

```typescript
it("shows yolo26 catalog entries with register actions", async () => {});
it("shows missing artifact state without marking it passed", async () => {});
it("starts an edge model assignment from the edge distribution tab", async () => {});
it("starts a TensorRT artifact build for a Jetson target", async () => {});
it("shows failed import and failed build errors with concrete text", async () => {});
```

- [ ] **Step 2: Run failing page tests**

```bash
npm --prefix frontend run test -- Models.test.tsx
```

Expected: FAIL because the page is missing.

- [ ] **Step 3: Build `ModelsPage`**

Create `frontend/src/pages/Models.tsx` with tabs:

- `Catalog`
- `Registered`
- `Imports`
- `Runtime artifacts`
- `Edge distribution`

Use existing `WorkspaceBand`, `WorkspaceSurface`, `StatusToneBadge`, `Button`, pagination, and lucide icons. Keep the interface operational and dense; avoid a landing-page hero.

Required actions:

- register catalog model;
- download catalog model when available;
- create URL import;
- assign model to node;
- start sync job;
- start TensorRT artifact build;
- start open-vocab scene artifact build when camera vocabulary is provided by the selected scene/camera context.

- [ ] **Step 4: Add route/nav entry**

Add `/models` route and navigation label `Models`. Keep route protected by existing auth flow.

- [ ] **Step 5: Run tests**

```bash
npm --prefix frontend run test -- Models.test.tsx
```

Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add frontend/src/pages/Models.tsx frontend/src/pages/Models.test.tsx frontend/src/App.tsx frontend/src/components
git commit -m "feat: add central model management page"
```

## Task 10: Deployment and Scene Setup Integration

**Files:**
- Modify: `frontend/src/pages/Deployment.tsx`
- Modify: `frontend/src/pages/Deployment.test.tsx`
- Modify: `frontend/src/pages/Cameras.tsx`
- Modify: `frontend/src/pages/Cameras.test.tsx`
- Modify: `backend/src/argus/services/app.py` or existing worker-config/runtime-selection service if readiness payloads need extension.
- Test: relevant backend runtime-selection tests if readiness response changes.

- [ ] **Step 1: Write Deployment page tests**

Add tests to `frontend/src/pages/Deployment.test.tsx`:

```typescript
it("shows model inventory and assignment controls for an edge node", async () => {});
it("shows edge configuration revision and apply status", async () => {});
it("starts model sync from the node detail panel", async () => {});
```

- [ ] **Step 2: Write Cameras page readiness tests**

Add tests to `frontend/src/pages/Cameras.test.tsx`:

```typescript
it("distinguishes missing model from missing runtime artifact", async () => {});
it("shows stale open-vocab artifact when vocabulary hash changed", async () => {});
it("offers artifact build action for the selected camera and edge node", async () => {});
```

- [ ] **Step 3: Implement Deployment node detail panels**

In `frontend/src/pages/Deployment.tsx`, add expandable node detail with:

- assignments table;
- inventory table;
- model sync action;
- runtime artifact build action;
- edge configuration form for the allowlisted fields.

- [ ] **Step 4: Implement scene readiness messaging**

In `frontend/src/pages/Cameras.tsx`, use existing models/runtime-artifacts hooks plus new node inventory hooks to display:

- `Model not registered`;
- `Model not synced to edge node`;
- `No TensorRT artifact for linux-aarch64-nvidia-jetson`;
- `Open-vocab artifact stale: vocabulary changed`;
- `Ready`.

Do not label a camera ready if the selected runtime preference requires a missing or stale artifact.

- [ ] **Step 5: Run tests**

```bash
npm --prefix frontend run test -- Deployment.test.tsx Cameras.test.tsx
```

Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add frontend/src/pages/Deployment.tsx frontend/src/pages/Deployment.test.tsx frontend/src/pages/Cameras.tsx frontend/src/pages/Cameras.test.tsx
git commit -m "feat: surface edge model readiness in deployment"
```

## Task 11: Docs and Installer Posture

**Files:**
- Modify: `docs/product-installer-and-first-run-guide.md`
- Modify: `docs/operator-deployment-playbook.md`
- Modify: `docs/runbook.md`
- Modify: `docs/model-loading-and-configuration-guide.md`
- Modify: `docs/core-link-performance-guide.md` only if validation instructions mention model distribution or edge config.
- Modify: `installer/linux/install-edge.sh` only if the installer currently asks for model/artifact configuration values that can now be controlled centrally.
- Test: `installer/tests/test_edge_installer_artifacts.py` if installer output changes.

- [ ] **Step 1: Write docs checklist**

Create a checklist section in `docs/model-loading-and-configuration-guide.md`:

```markdown
## UI-Driven Model Lifecycle Checklist

- Register or download the source model from Models > Catalog.
- Assign the model to each deployment node that will run it.
- Start a model sync job and wait for synced inventory.
- Create TensorRT or open-vocab runtime artifacts from Models > Runtime artifacts.
- Confirm the artifact is valid for the target profile.
- Return to scene setup and confirm readiness is Ready.
```

- [ ] **Step 2: Update installer guide**

In `docs/product-installer-and-first-run-guide.md`, state that edge installers only perform:

- prerequisite checks;
- service installation;
- pairing claim;
- supervisor startup.

Move model registration, model sync, TensorRT build, stream settings, worker concurrency, and support bundle posture to UI-driven post-install steps.

- [ ] **Step 3: Update operator playbook and runbook**

Add troubleshooting sections:

- model import job failed hash check;
- model assigned but not synced;
- TensorRT build failed on Jetson;
- open-vocab artifact stale after vocabulary edit;
- edge configuration revision failed to apply;
- node credential cannot poll jobs.

- [ ] **Step 4: Inspect installer prompts and update when model/runtime prompts exist**

Inspect `installer/linux/install-edge.sh` for prompts or required flags for model paths, engine paths, worker concurrency, runtime preference, or stream profile. Remove any of those prompts and write defaults consumed by the supervisor. Keep API URL, pairing token, and service identity inputs.

- [ ] **Step 5: Run docs and installer tests**

```bash
python3 -m pytest installer/tests/test_edge_installer_artifacts.py -q
```

Expected: PASS when installer output changes. When the inspection finds no installer prompt changes, record "installer unchanged after inspection" in the task notes.

- [ ] **Step 6: Commit**

```bash
git add docs/product-installer-and-first-run-guide.md docs/operator-deployment-playbook.md docs/runbook.md docs/model-loading-and-configuration-guide.md docs/core-link-performance-guide.md installer/linux/install-edge.sh installer/tests/test_edge_installer_artifacts.py
git commit -m "docs: centralize model and edge configuration workflows"
```

## Task 12: End-to-End Verification on MacBook + Jetson

**Files:**
- Modify: no code files unless a blocker is found and fixed with a failing regression test first.
- Evidence: write a status handoff under `docs/superpowers/status/`.

- [ ] **Step 1: Rebuild and start from clean stack**

Use the approved destructive validation-stack reset only for Vezor/dev validation containers and volumes. Do not run global Docker prune and do not delete model files.

- [ ] **Step 2: Complete first-run**

Verify:

- auth;
- tenant claims;
- Vezor Master protected control-plane site remains protected;
- deployment nodes list shows central and Jetson when paired.

- [ ] **Step 3: Register bundled models**

From the UI:

- register `YOLO26n COCO`;
- register `YOLO26s COCO`;
- verify hash, size, path, and catalog state.

- [ ] **Step 4: Pair and configure Jetson edge**

From the UI:

- pair Jetson;
- assign it to the intended site;
- set edge configuration revision with model/artifact store paths and runtime preference;
- confirm supervisor reports applied revision.

- [ ] **Step 5: Sync models to Jetson**

From the UI:

- assign `YOLO26n COCO` to Jetson;
- start model sync;
- confirm inventory shows the model with matching SHA-256.

- [ ] **Step 6: Build TensorRT engine**

From the UI:

- create TensorRT artifact for `YOLO26n COCO`;
- target `linux-aarch64-nvidia-jetson`;
- confirm the build job completes;
- confirm runtime artifact is valid and target-specific.

- [ ] **Step 7: Validate Office RTSP scene**

Use:

```text
rtsp://[redacted]@192.168.1.165:8554/ch2
```

Verify:

- Office scene camera can use the registered model;
- Live native mode is available when stream is reachable;
- annotated mode works when worker is running;
- readiness distinguishes missing artifact, stale artifact, and ready states correctly.

- [ ] **Step 8: Write smoke handoff**

Create `docs/superpowers/status/2026-06-08-central-model-edge-artifact-management-smoke.md` with PASS/FAIL/BLOCKED/NOT RUN rows for:

- model catalog register;
- model import job;
- Jetson model assignment;
- Jetson model inventory;
- TensorRT build;
- runtime artifact validation;
- edge configuration apply;
- Office RTSP live native;
- Office RTSP annotated;
- worker lifecycle.

- [ ] **Step 9: Final verification commands**

Run:

```bash
python3 -m uv run --project backend pytest backend/tests/services/test_model_lifecycle_imports.py backend/tests/services/test_deployment_model_inventory.py backend/tests/services/test_supervisor_model_jobs.py backend/tests/services/test_runtime_artifact_build_jobs.py backend/tests/services/test_edge_configuration_assignments.py backend/tests/supervisor/test_model_jobs.py backend/tests/supervisor/test_artifact_build_jobs.py -q
npm --prefix frontend run test -- Models.test.tsx Deployment.test.tsx Cameras.test.tsx use-model-lifecycle.test.tsx
```

Expected: PASS.

- [ ] **Step 10: Commit smoke evidence**

```bash
git add docs/superpowers/status/2026-06-08-central-model-edge-artifact-management-smoke.md
git commit -m "docs: record central model lifecycle smoke"
```

---

## Acceptance Criteria Mapping

- UI can register/download `yolo26n` and `yolo26s`: Tasks 3, 8, 9, 12.
- UI can add custom models: Tasks 3, 8, 9.
- UI can assign models to Jetson: Tasks 4, 5, 8, 9, 10, 12.
- Edge supervisor reports inventory: Tasks 4, 5, 12.
- UI can create TensorRT engines: Tasks 6, 8, 9, 10, 12.
- UI can create open-vocab scene artifacts: Tasks 6, 9, 10.
- Runtime selection keeps TensorRT as runtime artifact, not primary model: Tasks 6, 10.
- Central config covers routine post-install edge settings: Tasks 7, 10, 11, 12.
- Docs and installer posture are consistent: Task 11.
- No generic remote shell: Tasks 5, 6, 7.

## Self-Review Notes

- This plan intentionally keeps engine creation target-local through supervisor jobs; it does not register raw `.engine` catalog entries as primary models.
- The plan preserves the existing `ModelRuntimeArtifact` table and extends how artifacts are created, validated, and surfaced.
- The largest implementation risk is schema size. If execution feels too large, split after Task 5 and ship model registration/distribution before artifact builds.
- If a real Jetson TensorRT build fails because the environment lacks TensorRT tooling, mark that validation row BLOCKED with exact command/job evidence rather than PASS.
