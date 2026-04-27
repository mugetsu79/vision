# Open-Vocab Hybrid Detector Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add hybrid fixed-vocab and open-vocab detector support across central and edge workers, preserve normalized analytics/history/incidents behavior, and redesign Incidents into an evidence-first review workspace.

**Architecture:** Evolve the existing closed-label model/camera contract into a capability-aware system. Fixed-vocab detectors keep the current `classes` plus `active_classes` path; open-vocab detectors add persisted runtime vocabulary state, capability-aware query commands, and a detector abstraction that can hot-swap vocabulary without restarting the worker. Keep downstream analytics stable by preserving normalized `Detection(class_name, ...)` output and attributing vocabulary snapshots through lightweight version/hash references.

**Tech Stack:** FastAPI, Pydantic, SQLAlchemy, Alembic, PostgreSQL/TimescaleDB, NATS, ONNX Runtime / hardware-specific runtimes, React, TypeScript, TanStack Query, Vite, Vitest.

---

## File Map

- `backend/src/argus/models/enums.py`
  - Add capability and runtime-vocabulary enums shared by API, DB, and worker code.
- `backend/src/argus/models/tables.py`
  - Add model capability metadata, camera runtime vocabulary state, vocabulary snapshot storage, and event attribution columns.
- `backend/src/argus/migrations/versions/0005_open_vocab_hybrid_detector.py`
  - Create the DB migration for the new columns and tables.
- `backend/src/argus/api/contracts.py`
  - Extend model, camera, worker-config, query, and edge-capability contracts.
- `backend/src/argus/services/app.py`
  - Make model and camera persistence capability-aware; include runtime vocabulary in worker config and camera responses.
- `backend/src/argus/services/query.py`
  - Make query resolution and `cmd.camera.<id>` publishing capability-aware.
- `backend/src/argus/vision/detector.py`
  - Keep the fixed-vocab detector path, but conform it to the new detector interface.
- `backend/src/argus/vision/open_vocab_detector.py`
  - New open-vocab detector adapter that owns runtime vocabulary state.
- `backend/src/argus/vision/detector_factory.py`
  - New capability-aware factory that builds fixed-vocab or open-vocab detectors.
- `backend/src/argus/inference/engine.py`
  - Teach the worker to track capability, runtime vocabulary, and detector hot-swaps while preserving normalized output.
- `backend/src/argus/core/db.py`
  - Persist vocabulary snapshot references alongside tracking/count events.
- `backend/tests/models/test_schema.py`
  - Assert schema coverage for the new tables/columns.
- `backend/tests/api/test_prompt5_routes.py`
  - Extend model/camera create-update route validation for fixed-vocab and open-vocab contracts.
- `backend/tests/api/test_query_nats_route.py`
  - Extend query route expectations for capability-aware responses and command payloads.
- `backend/tests/inference/test_engine.py`
  - Cover fixed-vocab and open-vocab runtime behavior, including hot vocabulary updates.
- `backend/tests/services/test_history_service.py`
  - Preserve analytics behavior after event attribution changes.
- `backend/tests/services/test_incident_capture.py`
  - Ensure incidents still persist correctly after runtime attribution changes.
- `frontend/src/lib/api.generated.ts`
  - Regenerated client types after OpenAPI changes.
- `frontend/src/hooks/use-models.ts`
  - Surface capability metadata to the UI.
- `frontend/src/hooks/use-cameras.ts`
  - Surface runtime vocabulary state to the UI.
- `frontend/src/components/cameras/CameraWizard.tsx`
  - Branch setup flow between fixed-vocab and open-vocab models.
- `frontend/src/components/cameras/CameraWizard.test.tsx`
  - Cover the capability-aware wizard behavior.
- `frontend/src/components/live/AgentInput.tsx`
  - Make query results explicit about `fixed_filter` vs `open_vocab`.
- `frontend/src/components/live/AgentInput.test.tsx`
  - Cover capability-aware query result rendering.
- `frontend/src/pages/Incidents.tsx`
  - Redesign to the approved Evidence Desk layout.
- `frontend/src/pages/Incidents.test.tsx`
  - Verify the new evidence-first interaction model.
- `frontend/e2e/prompt9-history-and-incidents.spec.ts`
  - Update incidents assertions for the new queue + hero-evidence layout.
- `README.md`
  - Document hybrid detector capability semantics.
- `product-spec-v4.md`
  - Synchronize product-level vocabulary/query/incident behavior.
- `ai-coder-prompt-v4.md`
  - Sync agent prompts with the new capability-aware contracts.

## Task 1: Add Capability-Aware Schema And Contracts

**Files:**
- Modify: `backend/src/argus/models/enums.py`
- Modify: `backend/src/argus/models/tables.py`
- Modify: `backend/src/argus/api/contracts.py`
- Create: `backend/src/argus/migrations/versions/0005_open_vocab_hybrid_detector.py`
- Test: `backend/tests/models/test_schema.py`

- [ ] **Step 1: Write the failing schema tests**

Create/extend `backend/tests/models/test_schema.py` with assertions for the new model, camera, and snapshot schema:

```python
def test_schema_exposes_open_vocab_tables_and_columns() -> None:
    from argus.models.tables import Camera, CountEvent, Model, TrackingEvent

    assert "capability" in Model.__table__.c
    assert "capability_config" in Model.__table__.c
    assert "runtime_vocabulary" in Camera.__table__.c
    assert "runtime_vocabulary_source" in Camera.__table__.c
    assert "runtime_vocabulary_version" in Camera.__table__.c
    assert "runtime_vocabulary_updated_at" in Camera.__table__.c
    assert "vocabulary_version" in TrackingEvent.__table__.c
    assert "vocabulary_hash" in TrackingEvent.__table__.c
    assert "vocabulary_version" in CountEvent.__table__.c
    assert "vocabulary_hash" in CountEvent.__table__.c

def test_schema_registers_camera_vocabulary_snapshots_table() -> None:
    from argus.models.tables import CameraVocabularySnapshot

    assert CameraVocabularySnapshot.__tablename__ == "camera_vocabulary_snapshots"
    assert "camera_id" in CameraVocabularySnapshot.__table__.c
    assert "version" in CameraVocabularySnapshot.__table__.c
    assert "vocabulary_hash" in CameraVocabularySnapshot.__table__.c
    assert "terms" in CameraVocabularySnapshot.__table__.c
```

- [ ] **Step 2: Run the test to verify it fails**

Run:

```bash
cd /Users/yann.moren/vision/backend
python3 -m uv run pytest tests/models/test_schema.py -q
```

Expected: failure because the new enums, columns, and table do not exist yet.

- [ ] **Step 3: Add enums, DB columns, and contracts**

Update `backend/src/argus/models/enums.py`:

```python
class DetectorCapability(StrEnum):
    FIXED_VOCAB = "fixed_vocab"
    OPEN_VOCAB = "open_vocab"


class RuntimeVocabularySource(StrEnum):
    DEFAULT = "default"
    QUERY = "query"
    MANUAL = "manual"


class QueryResolutionMode(StrEnum):
    FIXED_FILTER = "fixed_filter"
    OPEN_VOCAB = "open_vocab"
```

Add the new persistence fields in `backend/src/argus/models/tables.py`:

```python
class Model(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "models"
    ...
    capability: Mapped[DetectorCapability] = mapped_column(
        enum_column(DetectorCapability, "detector_capability_enum"),
        nullable=False,
        default=DetectorCapability.FIXED_VOCAB,
    )
    capability_config: Mapped[dict[str, object]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
    )


class Camera(UUIDPrimaryKeyMixin, TimestampMixin, UpdatedAtMixin, Base):
    __tablename__ = "cameras"
    ...
    runtime_vocabulary: Mapped[list[str]] = mapped_column(JSONB, nullable=False, default=list)
    runtime_vocabulary_source: Mapped[RuntimeVocabularySource] = mapped_column(
        enum_column(RuntimeVocabularySource, "runtime_vocabulary_source_enum"),
        nullable=False,
        default=RuntimeVocabularySource.DEFAULT,
    )
    runtime_vocabulary_version: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    runtime_vocabulary_updated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )


class CameraVocabularySnapshot(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "camera_vocabulary_snapshots"
    camera_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("cameras.id"), nullable=False)
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    vocabulary_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    source: Mapped[RuntimeVocabularySource] = mapped_column(
        enum_column(RuntimeVocabularySource, "camera_vocabulary_snapshot_source_enum"),
        nullable=False,
    )
    terms: Mapped[list[str]] = mapped_column(JSONB, nullable=False, default=list)
```

Add vocabulary attribution columns:

```python
class TrackingEvent(UUIDPrimaryKeyMixin, Base):
    ...
    vocabulary_version: Mapped[int | None] = mapped_column(Integer, nullable=True)
    vocabulary_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)


class CountEvent(UUIDPrimaryKeyMixin, Base):
    ...
    vocabulary_version: Mapped[int | None] = mapped_column(Integer, nullable=True)
    vocabulary_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
```

Extend `backend/src/argus/api/contracts.py` with capability-aware models:

```python
class ModelCapabilityConfig(BaseModel):
    supports_runtime_vocabulary_updates: bool = False
    max_runtime_terms: int | None = None
    prompt_format: Literal["labels", "phrases"] | None = None
    execution_profiles: list[str] = Field(default_factory=list)


class RuntimeVocabularyState(BaseModel):
    terms: list[str] = Field(default_factory=list)
    source: RuntimeVocabularySource = RuntimeVocabularySource.DEFAULT
    version: int = 0
    updated_at: datetime | None = None
```

Use those in `ModelCreate`, `ModelUpdate`, `ModelResponse`, `CameraResponse`, `WorkerModelSettings`, `WorkerConfigResponse`, and `QueryResponse`.

Create `backend/src/argus/migrations/versions/0005_open_vocab_hybrid_detector.py` with the matching Alembic operations.

- [ ] **Step 4: Run the schema tests**

Run:

```bash
cd /Users/yann.moren/vision/backend
python3 -m uv run pytest tests/models/test_schema.py -q
python3 -m uv run python -m compileall src/argus
```

Expected: the schema test passes and `compileall` completes without syntax errors.

- [ ] **Step 5: Commit**

```bash
git add backend/src/argus/models/enums.py \
        backend/src/argus/models/tables.py \
        backend/src/argus/api/contracts.py \
        backend/src/argus/migrations/versions/0005_open_vocab_hybrid_detector.py \
        backend/tests/models/test_schema.py
git commit -m "feat(models): add hybrid detector capability schema"
```

## Task 2: Make Model And Camera Persistence Capability-Aware

**Files:**
- Modify: `backend/src/argus/services/app.py`
- Test: `backend/tests/api/test_prompt5_routes.py`

- [ ] **Step 1: Write failing route/service tests for model and camera validation**

Extend `backend/tests/api/test_prompt5_routes.py` with cases like:

```python
async def test_create_fixed_vocab_model_still_requires_classes(async_client):
    response = await async_client.post(
        "/api/v1/models",
        json={
            "name": "COCO detector",
            "version": "1",
            "task": "detect",
            "path": "/models/coco.onnx",
            "format": "onnx",
            "capability": "fixed_vocab",
            "classes": None,
            "input_shape": {"width": 640, "height": 640},
            "sha256": "a" * 64,
            "size_bytes": 1,
        },
    )
    assert response.status_code == 422


async def test_create_open_vocab_model_allows_empty_static_classes(async_client):
    response = await async_client.post(
        "/api/v1/models",
        json={
            "name": "YOLO World",
            "version": "1",
            "task": "detect",
            "path": "/models/yolo-world.onnx",
            "format": "onnx",
            "capability": "open_vocab",
            "classes": [],
            "capability_config": {
                "supports_runtime_vocabulary_updates": True,
                "max_runtime_terms": 32,
                "prompt_format": "labels",
                "execution_profiles": ["x86_64_gpu", "arm64_jetson"],
            },
            "input_shape": {"width": 640, "height": 640},
            "sha256": "b" * 64,
            "size_bytes": 1,
        },
    )
    assert response.status_code == 201
    assert response.json()["capability"] == "open_vocab"


async def test_create_open_vocab_camera_persists_runtime_vocabulary(async_client, open_vocab_model_id):
    response = await async_client.post(
        "/api/v1/cameras",
        json={
            ...
            "primary_model_id": open_vocab_model_id,
            "active_classes": [],
            "runtime_vocabulary": {
                "terms": ["forklift", "pallet jack"],
                "source": "manual",
                "version": 1,
            },
        },
    )
    assert response.status_code == 201
    assert response.json()["runtime_vocabulary"]["terms"] == ["forklift", "pallet jack"]
```

- [ ] **Step 2: Run the route tests to verify they fail**

Run:

```bash
cd /Users/yann.moren/vision/backend
python3 -m uv run pytest tests/api/test_prompt5_routes.py -q
```

Expected: failures because the API does not yet accept `capability`, `capability_config`, or `runtime_vocabulary`.

- [ ] **Step 3: Implement capability-aware model and camera persistence**

Update `backend/src/argus/services/app.py` in `ModelService.create_model()` and `ModelService.update_model()`:

```python
if payload.capability is DetectorCapability.FIXED_VOCAB:
    resolved_classes, _ = resolve_model_classes(payload.path, payload.format, payload.classes)
else:
    resolved_classes = list(payload.classes or [])
    if payload.capability_config.get("supports_runtime_vocabulary_updates") is not True:
        raise HTTPException(status_code=422, detail="open_vocab models must declare runtime vocabulary support")
```

Add helper validation in `backend/src/argus/services/app.py`:

```python
def _validate_runtime_vocabulary(
    *,
    terms: list[str],
    primary_model: Model,
) -> None:
    max_terms = int(primary_model.capability_config.get("max_runtime_terms") or 0)
    if max_terms > 0 and len(terms) > max_terms:
        raise HTTPException(
            status_code=HTTP_422_UNPROCESSABLE,
            detail=f"runtime_vocabulary exceeds max_runtime_terms={max_terms}.",
        )
```

Make `CameraService.create_camera()` and `update_camera()` branch by model capability:

```python
if primary_model.capability is DetectorCapability.FIXED_VOCAB:
    _validate_active_classes_subset(
        active_classes=payload.active_classes,
        primary_model_classes=primary_model.classes,
    )
    runtime_vocabulary_terms = list(primary_model.classes)
    runtime_vocabulary_source = RuntimeVocabularySource.DEFAULT
else:
    _validate_runtime_vocabulary(
        terms=payload.runtime_vocabulary.terms,
        primary_model=primary_model,
    )
    runtime_vocabulary_terms = list(payload.runtime_vocabulary.terms)
    runtime_vocabulary_source = payload.runtime_vocabulary.source
```

Persist `runtime_vocabulary_*` fields and include them in `_camera_to_response()` and `_camera_to_worker_config()`.

- [ ] **Step 4: Run the route tests**

Run:

```bash
cd /Users/yann.moren/vision/backend
python3 -m uv run pytest tests/api/test_prompt5_routes.py -q
```

Expected: open-vocab model/camera cases pass and fixed-vocab regressions remain green.

- [ ] **Step 5: Commit**

```bash
git add backend/src/argus/services/app.py \
        backend/tests/api/test_prompt5_routes.py
git commit -m "feat(cameras): persist runtime vocabulary for open-vocab models"
```

## Task 3: Make Query Resolution, Worker Config, And Edge Capability Reporting Capability-Aware

**Files:**
- Modify: `backend/src/argus/services/query.py`
- Modify: `backend/src/argus/api/contracts.py`
- Modify: `backend/src/argus/services/app.py`
- Test: `backend/tests/api/test_query_nats_route.py`
- Test: `backend/tests/inference/test_engine.py`

- [ ] **Step 1: Write the failing query tests**

Extend `backend/tests/api/test_query_nats_route.py`:

```python
async def test_query_response_reports_fixed_filter_mode(async_client):
    response = await async_client.post(
        "/api/v1/query",
        json={"prompt": "only show cars", "camera_ids": [FIXED_CAMERA_ID]},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["resolution_mode"] == "fixed_filter"
    assert body["resolved_classes"] == ["car"]
    assert body["resolved_vocabulary"] == []


async def test_query_response_reports_open_vocab_mode(async_client):
    response = await async_client.post(
        "/api/v1/query",
        json={"prompt": "forklifts and pallet jacks", "camera_ids": [OPEN_CAMERA_ID]},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["resolution_mode"] == "open_vocab"
    assert body["resolved_vocabulary"] == ["forklift", "pallet jack"]
```

Add a command payload assertion:

```python
assert published_payload == {
    "active_classes": None,
    "runtime_vocabulary": ["forklift", "pallet jack"],
    "runtime_vocabulary_source": "query",
    "runtime_vocabulary_version": 2,
}
```

- [ ] **Step 2: Run the query tests to verify they fail**

Run:

```bash
cd /Users/yann.moren/vision/backend
python3 -m uv run pytest tests/api/test_query_nats_route.py -q
```

Expected: failures because the route and publisher only know about `active_classes`.

- [ ] **Step 3: Update query service and worker-config contracts**

Update `backend/src/argus/services/query.py`:

```python
class CameraCommandPayload(BaseModel):
    active_classes: list[str] | None = None
    runtime_vocabulary: list[str] | None = None
    runtime_vocabulary_source: RuntimeVocabularySource | None = None
    runtime_vocabulary_version: int | None = None


@dataclass(slots=True, frozen=True)
class QueryServiceResult:
    resolution_mode: QueryResolutionMode
    resolved_classes: list[str]
    resolved_vocabulary: list[str]
    provider: str
    model: str
    latency_ms: int
```

Branch in `QueryService.resolve_query()`:

```python
if all(camera.capability is DetectorCapability.FIXED_VOCAB for camera in cameras):
    ...
    command = CameraCommandPayload(active_classes=result.resolved_classes)
else:
    ...
    command = CameraCommandPayload(
        runtime_vocabulary=result.resolved_vocabulary,
        runtime_vocabulary_source=RuntimeVocabularySource.QUERY,
        runtime_vocabulary_version=next_version,
    )
```

Update `backend/src/argus/services/app.py` and `backend/src/argus/api/contracts.py` so worker config and edge capability reporting include:

```python
class WorkerRuntimeCapability(BaseModel):
    execution_profiles: list[str] = Field(default_factory=list)
    detector_capabilities: list[DetectorCapability] = Field(default_factory=list)
    hot_runtime_vocabulary_updates: bool = False
    max_runtime_terms: int | None = None
```

Populate that structure in `WorkerConfigResponse`.

- [ ] **Step 4: Run the query and targeted engine tests**

Run:

```bash
cd /Users/yann.moren/vision/backend
python3 -m uv run pytest tests/api/test_query_nats_route.py tests/inference/test_engine.py -q
```

Expected: query route tests pass; some engine tests may still fail until Task 4/5 lands.

- [ ] **Step 5: Commit**

```bash
git add backend/src/argus/services/query.py \
        backend/src/argus/api/contracts.py \
        backend/src/argus/services/app.py \
        backend/tests/api/test_query_nats_route.py
git commit -m "feat(query): add capability-aware runtime vocabulary commands"
```

## Task 4: Introduce A Capability-Aware Detector Interface And Preserve The Fixed-Vocab Path

**Files:**
- Modify: `backend/src/argus/vision/detector.py`
- Create: `backend/src/argus/vision/detector_factory.py`
- Modify: `backend/src/argus/inference/engine.py`
- Test: `backend/tests/inference/test_engine.py`

- [ ] **Step 1: Write the failing engine tests for detector capability abstraction**

Extend `backend/tests/inference/test_engine.py`:

```python
async def test_engine_uses_fixed_vocab_detector_for_fixed_vocab_models() -> None:
    engine, detector = build_engine_with_fake_detector(capability="fixed_vocab")
    await engine.process_frame(TEST_FRAME)
    assert detector.capability == DetectorCapability.FIXED_VOCAB
    assert detector.last_visible_classes == ["car"]


async def test_engine_reads_runtime_vocabulary_from_state_for_open_vocab_models() -> None:
    engine, detector = build_engine_with_fake_detector(
        capability="open_vocab",
        runtime_vocabulary=["forklift", "pallet jack"],
    )
    await engine.process_frame(TEST_FRAME)
    assert detector.capability == DetectorCapability.OPEN_VOCAB
    assert detector.last_runtime_vocabulary == ["forklift", "pallet jack"]
```

- [ ] **Step 2: Run the engine tests to verify they fail**

Run:

```bash
cd /Users/yann.moren/vision/backend
python3 -m uv run pytest tests/inference/test_engine.py -q
```

Expected: failure because `engine.py` still hard-codes `YoloDetector`.

- [ ] **Step 3: Add the detector interface and factory**

Keep the existing fixed-vocab implementation in `backend/src/argus/vision/detector.py`, but add a shared protocol:

```python
class RuntimeDetector(Protocol):
    capability: DetectorCapability

    def detect(
        self,
        frame: NDArray[np.uint8],
        visible_classes: Iterable[str] | None = None,
    ) -> list[Detection]: ...

    def update_runtime_vocabulary(self, vocabulary: list[str]) -> None: ...

    def describe_runtime_state(self) -> dict[str, object]: ...
```

Add `backend/src/argus/vision/detector_factory.py`:

```python
def build_detector(
    *,
    model: WorkerModelSettings,
    runtime: Any,
    runtime_policy: RuntimeExecutionPolicy,
) -> RuntimeDetector:
    if model.capability is DetectorCapability.FIXED_VOCAB:
        return YoloDetector(...)
    if model.capability is DetectorCapability.OPEN_VOCAB:
        return OpenVocabDetector(...)
    raise ValueError(f"Unsupported detector capability: {model.capability}")
```

Update `backend/src/argus/inference/engine.py` to use `build_detector(...)` instead of directly instantiating `YoloDetector`.

- [ ] **Step 4: Run the engine tests**

Run:

```bash
cd /Users/yann.moren/vision/backend
python3 -m uv run pytest tests/inference/test_engine.py -q
```

Expected: fixed-vocab detector tests pass; open-vocab update behavior may still need Task 5.

- [ ] **Step 5: Commit**

```bash
git add backend/src/argus/vision/detector.py \
        backend/src/argus/vision/detector_factory.py \
        backend/src/argus/inference/engine.py \
        backend/tests/inference/test_engine.py
git commit -m "refactor(engine): add capability-aware detector factory"
```

## Task 5: Implement Open-Vocab Runtime Vocabulary Hot-Swap Across Central And Edge Workers

**Files:**
- Create: `backend/src/argus/vision/open_vocab_detector.py`
- Modify: `backend/src/argus/inference/engine.py`
- Test: `backend/tests/inference/test_engine.py`

- [ ] **Step 1: Write the failing hot-swap tests**

Add tests like:

```python
async def test_engine_applies_runtime_vocabulary_command_without_restart() -> None:
    engine, detector = build_engine_with_fake_open_vocab_detector(
        runtime_vocabulary=["forklift"],
    )

    await engine.apply_command(
        CameraCommand(
            runtime_vocabulary=["forklift", "pallet jack"],
            runtime_vocabulary_source="query",
            runtime_vocabulary_version=2,
        )
    )

    assert detector.update_calls == [["forklift", "pallet jack"]]
    assert engine.runtime_vocabulary == ["forklift", "pallet jack"]


async def test_engine_preserves_normalized_detection_shape_for_open_vocab() -> None:
    engine, detector = build_engine_with_fake_open_vocab_detector(
        detections=[Detection(class_name="forklift", confidence=0.9, bbox=(0, 0, 10, 10))]
    )
    telemetry = await engine.process_frame(TEST_FRAME)
    assert telemetry.counts == {"forklift": 1}
```

- [ ] **Step 2: Run the hot-swap tests to verify they fail**

Run:

```bash
cd /Users/yann.moren/vision/backend
python3 -m uv run pytest tests/inference/test_engine.py -q
```

Expected: failure because the worker state and detector do not yet understand `runtime_vocabulary`.

- [ ] **Step 3: Implement the open-vocab detector adapter and engine state updates**

Create `backend/src/argus/vision/open_vocab_detector.py` with a capability-aware adapter:

```python
@dataclass(slots=True)
class OpenVocabModelConfig:
    name: str
    path: str
    input_shape: dict[str, int]
    capability_config: dict[str, object]
    default_vocabulary: list[str]


class OpenVocabDetector:
    capability = DetectorCapability.OPEN_VOCAB

    def __init__(self, model_config: OpenVocabModelConfig, runtime: Any, runtime_policy: RuntimeExecutionPolicy) -> None:
        self.model_config = model_config
        self.runtime = runtime
        self.runtime_policy = runtime_policy
        self._runtime_vocabulary = list(model_config.default_vocabulary)
        self._session = self._build_session()

    def update_runtime_vocabulary(self, vocabulary: list[str]) -> None:
        self._runtime_vocabulary = list(vocabulary)
        self._refresh_prompt_state()

    def detect(self, frame: NDArray[np.uint8], visible_classes: Iterable[str] | None = None) -> list[Detection]:
        detections = self._run_open_vocab_inference(frame, self._runtime_vocabulary)
        if visible_classes is None:
            return detections
        allowed = set(visible_classes)
        return [d for d in detections if d.class_name in allowed]
```

In `backend/src/argus/inference/engine.py`, update command handling:

```python
if command.runtime_vocabulary is not None:
    self._state.runtime_vocabulary = list(command.runtime_vocabulary)
    self._state.runtime_vocabulary_source = command.runtime_vocabulary_source
    self._state.runtime_vocabulary_version = command.runtime_vocabulary_version or self._state.runtime_vocabulary_version
    self.detector.update_runtime_vocabulary(self._state.runtime_vocabulary)
```

Expose runtime vocabulary in engine properties:

```python
@property
def runtime_vocabulary(self) -> list[str]:
    if self._state.runtime_vocabulary:
        return list(self._state.runtime_vocabulary)
    return list(self.config.model.classes)
```

- [ ] **Step 4: Run engine tests again**

Run:

```bash
cd /Users/yann.moren/vision/backend
python3 -m uv run pytest tests/inference/test_engine.py -q
```

Expected: hot-swap tests and normalized-output tests pass.

- [ ] **Step 5: Commit**

```bash
git add backend/src/argus/vision/open_vocab_detector.py \
        backend/src/argus/inference/engine.py \
        backend/tests/inference/test_engine.py
git commit -m "feat(engine): add open-vocab runtime vocabulary hot-swap"
```

## Task 6: Persist Vocabulary Snapshots And Attribute Tracking/Count Events

**Files:**
- Modify: `backend/src/argus/core/db.py`
- Modify: `backend/src/argus/inference/engine.py`
- Modify: `backend/src/argus/services/app.py`
- Test: `backend/tests/services/test_history_service.py`
- Test: `backend/tests/services/test_incident_capture.py`

- [ ] **Step 1: Write the failing persistence tests**

Add/extend tests:

```python
async def test_tracking_events_store_vocabulary_version_and_hash(...) -> None:
    ...
    assert recorded_row["vocabulary_version"] == 2
    assert recorded_row["vocabulary_hash"] == expected_hash


async def test_count_events_store_vocabulary_version_and_hash(...) -> None:
    ...
    assert recorded_event["vocabulary_version"] == 2
    assert recorded_event["vocabulary_hash"] == expected_hash
```

Add a snapshot test:

```python
async def test_query_updates_create_camera_vocabulary_snapshot(...) -> None:
    snapshots = await load_camera_snapshots(camera_id)
    assert snapshots[-1]["terms"] == ["forklift", "pallet jack"]
    assert snapshots[-1]["version"] == 2
```

- [ ] **Step 2: Run the service tests to verify they fail**

Run:

```bash
cd /Users/yann.moren/vision/backend
python3 -m uv run pytest tests/services/test_history_service.py tests/services/test_incident_capture.py -q
```

Expected: failures because the persistence layer does not write vocabulary references yet.

- [ ] **Step 3: Add snapshot hashing and event attribution**

Update `backend/src/argus/inference/engine.py` with helper functions:

```python
def _normalize_vocabulary_terms(terms: list[str]) -> list[str]:
    return [term.strip() for term in terms if term.strip()]


def _hash_vocabulary(terms: list[str]) -> str:
    payload = json.dumps(_normalize_vocabulary_terms(terms), separators=(",", ":"), ensure_ascii=True)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()
```

When persisting tracking and count events, pass:

```python
vocabulary_version=self._state.runtime_vocabulary_version,
vocabulary_hash=_hash_vocabulary(self.runtime_vocabulary),
```

Update `backend/src/argus/core/db.py` recorders to store the extra fields.

In `backend/src/argus/services/app.py`, add snapshot persistence helpers used when:

- creating/updating an open-vocab camera
- applying a successful open-vocab query

Use a small helper like:

```python
async def _record_camera_vocabulary_snapshot(...):
    snapshot = CameraVocabularySnapshot(
        camera_id=camera_id,
        version=version,
        vocabulary_hash=vocabulary_hash,
        source=source,
        terms=terms,
    )
```

- [ ] **Step 4: Run the service tests**

Run:

```bash
cd /Users/yann.moren/vision/backend
python3 -m uv run pytest tests/services/test_history_service.py tests/services/test_incident_capture.py tests/inference/test_engine.py -q
```

Expected: snapshot and attribution tests pass; history/count behavior remains intact.

- [ ] **Step 5: Commit**

```bash
git add backend/src/argus/core/db.py \
        backend/src/argus/inference/engine.py \
        backend/src/argus/services/app.py \
        backend/tests/services/test_history_service.py \
        backend/tests/services/test_incident_capture.py
git commit -m "feat(history): attribute events to runtime vocabulary snapshots"
```

## Task 7: Update Camera Setup And Live Query UI For Capability Awareness

**Files:**
- Modify: `frontend/src/hooks/use-models.ts`
- Modify: `frontend/src/hooks/use-cameras.ts`
- Modify: `frontend/src/components/cameras/CameraWizard.tsx`
- Modify: `frontend/src/components/cameras/CameraWizard.test.tsx`
- Modify: `frontend/src/components/live/AgentInput.tsx`
- Modify: `frontend/src/components/live/AgentInput.test.tsx`
- Modify: `frontend/src/lib/api.generated.ts`

- [ ] **Step 1: Write the failing frontend tests**

Extend `frontend/src/components/cameras/CameraWizard.test.tsx`:

```tsx
test("shows runtime vocabulary editor for open-vocab models", async () => {
  renderWizard({
    models: [
      {
        id: "open-model",
        name: "YOLO World",
        version: "1",
        capability: "open_vocab",
        classes: [],
        capability_config: { max_runtime_terms: 32, supports_runtime_vocabulary_updates: true },
      },
    ],
  });

  await user.selectOptions(screen.getByLabelText(/primary model/i), ["open-model"]);
  expect(screen.getByLabelText(/runtime vocabulary/i)).toBeInTheDocument();
  expect(screen.queryByLabelText(/active classes/i)).not.toBeInTheDocument();
});
```

Extend `frontend/src/components/live/AgentInput.test.tsx`:

```tsx
test("renders open-vocab query results as applied detector vocabulary", async () => {
  mockQueryResponse({
    resolution_mode: "open_vocab",
    resolved_classes: [],
    resolved_vocabulary: ["forklift", "pallet jack"],
  });
  renderAgentInput();
  await user.type(screen.getByLabelText(/query/i), "forklifts and pallet jacks");
  await user.click(screen.getByRole("button", { name: /apply query/i }));
  expect(await screen.findByText(/applied detector vocabulary/i)).toBeInTheDocument();
  expect(screen.getByText(/forklift, pallet jack/i)).toBeInTheDocument();
});
```

- [ ] **Step 2: Run the frontend tests to verify they fail**

Run:

```bash
cd /Users/yann.moren/vision
corepack pnpm --dir frontend exec vitest run \
  src/components/cameras/CameraWizard.test.tsx \
  src/components/live/AgentInput.test.tsx
```

Expected: failures because the generated API types and components do not yet expose capability-aware fields.

- [ ] **Step 3: Implement the capability-aware UI**

Regenerate `frontend/src/lib/api.generated.ts` after backend contract changes.

Update `frontend/src/components/cameras/CameraWizard.tsx`:

```tsx
const selectedPrimaryModelCapability = selectedPrimaryModel?.capability ?? "fixed_vocab";

const showsRuntimeVocabulary = selectedPrimaryModelCapability === "open_vocab";

{showsRuntimeVocabulary ? (
  <label className="space-y-2 text-sm text-[#d9e5f7]">
    <span className="text-[11px] font-semibold uppercase tracking-[0.2em] text-[#8ea8cf]">
      Runtime vocabulary
    </span>
    <Input
      aria-label="Runtime vocabulary"
      placeholder="forklift, pallet jack"
      value={data.runtimeVocabulary.join(", ")}
      onChange={(event) =>
        setData((current) => ({
          ...current,
          runtimeVocabulary: event.target.value.split(",").map((item) => item.trim()).filter(Boolean),
        }))
      }
    />
  </label>
) : (
  <FixedVocabClassPicker ... />
)}
```

Update `frontend/src/components/live/AgentInput.tsx`:

```tsx
{resolution ? (
  <div className="flex flex-wrap items-center gap-2 border-t border-white/8 pt-4">
    <Badge className="border-[#31538b] bg-[#101a2a] text-[#dce9ff]">
      {resolution.resolution_mode === "open_vocab"
        ? resolution.resolved_vocabulary.join(", ")
        : resolution.resolved_classes.join(", ")}
    </Badge>
    <span className="text-sm text-[#b8c9e2]">
      {resolution.resolution_mode === "open_vocab"
        ? "Applied detector vocabulary"
        : "Resolved classes"}
    </span>
  </div>
) : null}
```

- [ ] **Step 4: Run the frontend tests**

Run:

```bash
cd /Users/yann.moren/vision
corepack pnpm --dir frontend exec vitest run \
  src/components/cameras/CameraWizard.test.tsx \
  src/components/live/AgentInput.test.tsx
```

Expected: both tests pass and no type errors remain.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/hooks/use-models.ts \
        frontend/src/hooks/use-cameras.ts \
        frontend/src/components/cameras/CameraWizard.tsx \
        frontend/src/components/cameras/CameraWizard.test.tsx \
        frontend/src/components/live/AgentInput.tsx \
        frontend/src/components/live/AgentInput.test.tsx \
        frontend/src/lib/api.generated.ts
git commit -m "feat(frontend): add capability-aware camera and query UX"
```

## Task 8: Redesign Incidents Into The Evidence Desk And Finish Verification

**Files:**
- Modify: `frontend/src/pages/Incidents.tsx`
- Modify: `frontend/src/pages/Incidents.test.tsx`
- Modify: `frontend/e2e/prompt9-history-and-incidents.spec.ts`
- Modify: `README.md`
- Modify: `product-spec-v4.md`
- Modify: `ai-coder-prompt-v4.md`

- [ ] **Step 1: Write the failing incidents tests**

Extend `frontend/src/pages/Incidents.test.tsx`:

```tsx
test("renders an evidence desk with queue, hero preview, and signed actions", async () => {
  renderIncidentsPage();
  expect(await screen.findByRole("img", { name: /incident preview/i })).toBeInTheDocument();
  expect(screen.getByRole("button", { name: /review/i })).toBeInTheDocument();
  expect(screen.getByRole("link", { name: /open clip/i })).toBeInTheDocument();
  expect(screen.getByText(/incident facts/i)).toBeInTheDocument();
  expect(screen.getByText(/queue/i)).toBeInTheDocument();
});
```

Add a Playwright expectation update in `frontend/e2e/prompt9-history-and-incidents.spec.ts`:

```ts
await expect(page.getByText(/incident facts/i)).toBeVisible();
await expect(page.getByRole("link", { name: /open clip/i })).toBeVisible();
await expect(page.getByText(/queue/i)).toBeVisible();
```

- [ ] **Step 2: Run the incidents tests to verify they fail**

Run:

```bash
cd /Users/yann.moren/vision
corepack pnpm --dir frontend exec vitest run src/pages/Incidents.test.tsx
```

Expected: failure because the page still renders equal-weight incident cards.

- [ ] **Step 3: Implement the Evidence Desk layout and doc updates**

Refactor `frontend/src/pages/Incidents.tsx` into:

```tsx
export function IncidentsPage() {
  const [selectedIncidentId, setSelectedIncidentId] = useState<string | null>(null);
  ...
  const selectedIncident = incidents.find((incident) => incident.id === selectedIncidentId) ?? incidents[0] ?? null;

  return (
    <div className="space-y-6">
      <section className="overflow-hidden rounded-[2rem] border border-white/10 ...">
        <div className="border-b border-white/8 px-6 py-5">
          ...
        </div>

        <div className="grid gap-5 px-6 py-6 xl:grid-cols-[360px_minmax(0,1fr)_320px]">
          <IncidentQueue incidents={incidents} selectedId={selectedIncident?.id ?? null} onSelect={setSelectedIncidentId} />
          <IncidentEvidenceHero incident={selectedIncident} />
          <IncidentFactsPanel incident={selectedIncident} />
        </div>
      </section>
    </div>
  );
}
```

Update docs:

- `README.md` — mention the evidence-first Incidents desk and hybrid detector capability.
- `product-spec-v4.md` — align Incidents, open-vocab semantics, and runtime vocabulary behavior.
- `ai-coder-prompt-v4.md` — align prompts/contracts with capability-aware detectors and Evidence Desk.

- [ ] **Step 4: Run final focused verification**

Run:

```bash
cd /Users/yann.moren/vision/backend
python3 -m uv run pytest \
  tests/models/test_schema.py \
  tests/api/test_prompt5_routes.py \
  tests/api/test_query_nats_route.py \
  tests/inference/test_engine.py \
  tests/services/test_history_service.py \
  tests/services/test_incident_capture.py -q

cd /Users/yann.moren/vision
corepack pnpm --dir frontend exec vitest run \
  src/components/cameras/CameraWizard.test.tsx \
  src/components/live/AgentInput.test.tsx \
  src/pages/Incidents.test.tsx

corepack pnpm --dir frontend build
```

Expected:

- backend tests pass
- frontend tests pass
- production build succeeds

- [ ] **Step 5: Commit**

```bash
git add frontend/src/pages/Incidents.tsx \
        frontend/src/pages/Incidents.test.tsx \
        frontend/e2e/prompt9-history-and-incidents.spec.ts \
        README.md \
        product-spec-v4.md \
        ai-coder-prompt-v4.md
git commit -m "feat(incidents): redesign incidents as evidence desk"
```

