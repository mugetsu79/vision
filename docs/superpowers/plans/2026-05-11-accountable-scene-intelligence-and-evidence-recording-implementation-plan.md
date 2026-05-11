# Accountable Scene Intelligence And Evidence Recording Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement the first Vezor differentiator slice: Scene Contract Compiler, Evidence Ledger, Privacy Manifest, and artifact-aware short incident recording for local edge and remote/cloud storage.

**Architecture:** Keep existing incident capture and Evidence Desk flows, but add immutable scene/privacy snapshots, first-class evidence artifacts, and incident-scoped ledger entries. The worker continues to emit short event clips; storage becomes provider-aware so edge local, central MinIO, and S3-compatible/cloud deployments share one review contract.

**Tech Stack:** FastAPI, Pydantic, SQLAlchemy async, Alembic, PostgreSQL JSONB, OpenCV MJPEG clip encoding, local filesystem storage, MinIO/S3-compatible object storage, React 19, Vite 6, TypeScript 5.7, Tailwind v4, Vitest, pytest, Ruff, mypy.

**Spec source:** `/Users/yann.moren/vision/docs/superpowers/specs/2026-05-11-accountable-scene-intelligence-and-evidence-recording-design.md`

---

## Execution Protocol

Execute one task at a time. After each task:

1. run the task verification commands
2. commit only the files for that task
3. push the branch
4. report the result before continuing

Do not stage unrelated untracked scratch files. Keep WebGL off. Do not implement
Runtime Passport, Operational Memory, Prompt-To-Policy, Identity-Light
Cross-Camera Intelligence, or DeepStream in this plan.

## Pre-Flight

Run:

```bash
cd /Users/yann.moren/vision
git fetch origin
git switch codex/omnisight-ui-spec-implementation
git pull --ff-only origin codex/omnisight-ui-spec-implementation
git status --short
git log --oneline -12
```

Expected:

- branch is `codex/omnisight-ui-spec-implementation`
- no unrelated scratch files are staged
- untracked scratch files may exist and must stay unstaged

If dev DB errors mention `cameras.vision_profile` or
`cameras.detection_regions`, run:

```bash
docker compose -f infra/docker-compose.dev.yml exec backend python -m uv run alembic upgrade head
```

## File Structure

| Path | Action | Responsibility |
|---|---|---|
| `backend/src/argus/models/enums.py` | modify | evidence artifact, storage, and ledger enum values |
| `backend/src/argus/models/tables.py` | modify | scene contract, privacy manifest, artifact, ledger tables and incident/camera columns |
| `backend/src/argus/migrations/versions/0011_accountable_scene_evidence.py` | create | schema migration |
| `backend/src/argus/api/contracts.py` | modify | camera source, recording, contract, manifest, artifact, ledger API contracts |
| `backend/src/argus/services/camera_sources.py` | create | source normalization, redaction, validation, and probe dispatch |
| `backend/src/argus/services/scene_contracts.py` | create | deterministic scene contract compiler and snapshot service |
| `backend/src/argus/services/privacy_manifests.py` | create | deterministic privacy manifest builder and snapshot service |
| `backend/src/argus/services/evidence_ledger.py` | create | append-only ledger writer and reader |
| `backend/src/argus/services/evidence_storage.py` | create | local filesystem and S3-compatible artifact storage abstraction |
| `backend/src/argus/services/incident_capture.py` | modify | artifact-aware short event clip recording |
| `backend/src/argus/services/object_store.py` | modify | compatibility wrapper or S3-compatible implementation reuse |
| `backend/src/argus/services/app.py` | modify | worker config, incident responses, review ledger, new services |
| `backend/src/argus/api/v1/incidents.py` | modify | contract, manifest, ledger, artifact content routes |
| `backend/src/argus/vision/camera.py` | modify | resolve USB/UVC source URIs to edge V4L2/OpenCV capture |
| `backend/src/argus/vision/source_probe.py` | modify | probe USB/UVC source capability without treating it as RTSP |
| `backend/src/argus/inference/engine.py` | modify | carry camera source, recording policy, and scene contract context into capture |
| `frontend/src/lib/api.generated.ts` | regenerate | OpenAPI types |
| `frontend/src/hooks/use-incidents.ts` | modify | incident response type usage for accountability fields |
| `frontend/src/pages/Incidents.tsx` | modify | display contract, manifest, artifact, and ledger status |
| `frontend/src/pages/Incidents.test.tsx` | modify | UI coverage |
| `frontend/src/components/evidence/AccountabilityStrip.tsx` | create | compact contract, privacy, artifact, and ledger strip |
| `frontend/src/components/evidence/AccountabilityStrip.test.tsx` | create | accountability strip rendering tests |
| `frontend/src/components/cameras/CameraWizard.tsx` | modify | RTSP/USB source selection and recording policy controls |
| `frontend/src/components/cameras/CameraWizard.test.tsx` | modify | camera source and recording policy tests |
| `docs/runbook.md` | modify | storage and recording configuration |
| `docs/operator-deployment-playbook.md` | modify | edge USB camera, local evidence, and remote/cloud evidence guidance |

## Task 1: Data Contract And Migration

**Files:**

- Modify: `backend/src/argus/models/enums.py`
- Modify: `backend/src/argus/models/tables.py`
- Create: `backend/src/argus/migrations/versions/0011_accountable_scene_evidence.py`
- Modify: `backend/src/argus/api/contracts.py`
- Test: `backend/tests/services/test_scene_contracts.py`
- Test: `backend/tests/services/test_evidence_ledger.py`
- Test: `backend/tests/core/test_db.py`

- [ ] **Step 1: Add failing contract tests**

Create `backend/tests/services/test_scene_contracts.py` with tests that import
the new contracts and verify defaults:

```python
from __future__ import annotations

from argus.api.contracts import CameraSourceSettings, EvidenceRecordingPolicy


def test_camera_source_settings_support_usb_edge_source() -> None:
    source = CameraSourceSettings(kind="usb", uri="usb:///dev/video0", label="Dock Door USB")

    assert source.kind == "usb"
    assert source.uri == "usb:///dev/video0"
    assert source.label == "Dock Door USB"


def test_evidence_recording_policy_defaults_to_short_event_clip() -> None:
    policy = EvidenceRecordingPolicy()

    assert policy.enabled is True
    assert policy.mode == "event_clip"
    assert policy.pre_seconds == 4
    assert policy.post_seconds == 8
    assert policy.fps == 10
    assert policy.max_duration_seconds == 15
    assert policy.storage_profile == "central"
```

Create `backend/tests/services/test_evidence_ledger.py` with enum import tests:

```python
from __future__ import annotations

from argus.models.enums import (
    CameraSourceKind,
    EvidenceArtifactKind,
    EvidenceArtifactStatus,
    EvidenceLedgerAction,
    EvidenceStorageProvider,
    EvidenceStorageScope,
)


def test_evidence_enums_expose_accountability_values() -> None:
    assert CameraSourceKind.USB.value == "usb"
    assert EvidenceArtifactKind.EVENT_CLIP.value == "event_clip"
    assert EvidenceArtifactStatus.LOCAL_ONLY.value == "local_only"
    assert EvidenceStorageProvider.LOCAL_FILESYSTEM.value == "local_filesystem"
    assert EvidenceStorageScope.EDGE.value == "edge"
    assert EvidenceLedgerAction.INCIDENT_TRIGGERED.value == "incident.triggered"
```

- [ ] **Step 2: Run failing tests**

Run:

```bash
cd /Users/yann.moren/vision/backend
python3 -m uv run pytest tests/services/test_scene_contracts.py tests/services/test_evidence_ledger.py -q
```

Expected: fail because contracts and enums do not exist.

- [ ] **Step 3: Add enums**

In `backend/src/argus/models/enums.py`, add:

```python
class EvidenceArtifactKind(StrEnum):
    EVENT_CLIP = "event_clip"
    SNAPSHOT = "snapshot"
    MANIFEST_EXPORT = "manifest_export"
    CASE_EXPORT = "case_export"


class EvidenceArtifactStatus(StrEnum):
    AVAILABLE = "available"
    LOCAL_ONLY = "local_only"
    REMOTE_AVAILABLE = "remote_available"
    UPLOAD_PENDING = "upload_pending"
    QUOTA_EXCEEDED = "quota_exceeded"
    CAPTURE_FAILED = "capture_failed"
    EXPIRED = "expired"


class EvidenceStorageProvider(StrEnum):
    LOCAL_FILESYSTEM = "local_filesystem"
    MINIO = "minio"
    S3_COMPATIBLE = "s3_compatible"


class EvidenceStorageScope(StrEnum):
    EDGE = "edge"
    CENTRAL = "central"
    CLOUD = "cloud"


class EvidenceLedgerAction(StrEnum):
    INCIDENT_TRIGGERED = "incident.triggered"
    SCENE_CONTRACT_ATTACHED = "scene_contract.attached"
    PRIVACY_MANIFEST_ATTACHED = "privacy_manifest.attached"
    CLIP_CAPTURE_STARTED = "evidence.clip.capture_started"
    CLIP_AVAILABLE = "evidence.clip.available"
    CLIP_QUOTA_EXCEEDED = "evidence.clip.quota_exceeded"
    CLIP_CAPTURE_FAILED = "evidence.clip.capture_failed"
    INCIDENT_REVIEWED = "incident.reviewed"
    INCIDENT_REOPENED = "incident.reopened"
```

Also add:

```python
class CameraSourceKind(StrEnum):
    RTSP = "rtsp"
    USB = "usb"
    JETSON_CSI = "jetson_csi"
```

- [ ] **Step 4: Add API contracts**

In `backend/src/argus/api/contracts.py`, import the enums and add:

```python
EvidenceStorageProfile = Literal["edge_local", "central", "cloud", "local_first"]


class CameraSourceSettings(BaseModel):
    kind: CameraSourceKind = CameraSourceKind.RTSP
    uri: str = Field(min_length=1)
    label: str | None = None

    @model_validator(mode="after")
    def validate_source_uri(self) -> CameraSourceSettings:
        if self.kind is CameraSourceKind.RTSP and not self.uri.startswith(
            ("rtsp://", "rtsps://")
        ):
            raise ValueError("RTSP sources must use rtsp:// or rtsps://.")
        if self.kind is CameraSourceKind.USB and not self.uri.startswith("usb://"):
            raise ValueError("USB sources must use usb:///dev/videoN.")
        if self.kind is CameraSourceKind.JETSON_CSI and not self.uri.startswith("csi://"):
            raise ValueError("Jetson CSI sources must use csi://N.")
        return self


class EvidenceRecordingPolicy(BaseModel):
    enabled: bool = True
    mode: Literal["event_clip"] = "event_clip"
    pre_seconds: int = Field(default=4, ge=0, le=30)
    post_seconds: int = Field(default=8, ge=1, le=60)
    fps: int = Field(default=10, ge=1, le=30)
    max_duration_seconds: int = Field(default=15, ge=1, le=90)
    storage_profile: EvidenceStorageProfile = "central"

    @model_validator(mode="after")
    def validate_window(self) -> EvidenceRecordingPolicy:
        if self.pre_seconds + self.post_seconds > self.max_duration_seconds:
            raise ValueError("pre_seconds plus post_seconds must fit max_duration_seconds.")
        return self


class EvidenceArtifactResponse(BaseModel):
    id: UUID
    incident_id: UUID
    camera_id: UUID
    kind: EvidenceArtifactKind
    status: EvidenceArtifactStatus
    storage_provider: EvidenceStorageProvider
    storage_scope: EvidenceStorageScope
    bucket: str | None = None
    object_key: str
    content_type: str
    sha256: str = Field(min_length=64, max_length=64)
    size_bytes: int = Field(ge=0)
    clip_started_at: datetime | None = None
    triggered_at: datetime | None = None
    clip_ended_at: datetime | None = None
    duration_seconds: float | None = None
    fps: int | None = None
    scene_contract_hash: str | None = Field(default=None, min_length=64, max_length=64)
    privacy_manifest_hash: str | None = Field(default=None, min_length=64, max_length=64)
    review_url: str | None = None


class EvidenceLedgerSummary(BaseModel):
    entry_count: int = 0
    latest_action: EvidenceLedgerAction | None = None
    latest_at: datetime | None = None


class EvidenceLedgerEntryResponse(BaseModel):
    id: UUID
    incident_id: UUID
    camera_id: UUID
    sequence: int
    action: EvidenceLedgerAction
    actor_type: str
    actor_subject: str | None = None
    occurred_at: datetime
    payload: dict[str, Any] = Field(default_factory=dict)
    previous_entry_hash: str | None = Field(default=None, min_length=64, max_length=64)
    entry_hash: str = Field(min_length=64, max_length=64)


class SceneContractSnapshotResponse(BaseModel):
    id: UUID
    camera_id: UUID
    schema_version: int
    contract_hash: str = Field(min_length=64, max_length=64)
    contract: dict[str, Any]
    created_at: datetime | None = None


class PrivacyManifestSnapshotResponse(BaseModel):
    id: UUID
    camera_id: UUID
    schema_version: int
    manifest_hash: str = Field(min_length=64, max_length=64)
    manifest: dict[str, Any]
    created_at: datetime | None = None
```

Extend `IncidentResponse`:

```python
scene_contract_hash: str | None = None
scene_contract_id: UUID | None = None
privacy_manifest_hash: str | None = None
privacy_manifest_id: UUID | None = None
recording_policy: EvidenceRecordingPolicy | None = None
evidence_artifacts: list[EvidenceArtifactResponse] = Field(default_factory=list)
ledger_summary: EvidenceLedgerSummary | None = None
```

- [ ] **Step 5: Add SQLAlchemy tables**

In `backend/src/argus/models/tables.py`, add the four new tables and incident
columns from the spec. Use JSONB for `contract`, `manifest`, `payload`, and
`recording_policy`. Use the existing `UUIDPrimaryKeyMixin`, `TimestampMixin`,
and `UpdatedAtMixin` patterns.

Also add camera source columns:

```python
source_kind: Mapped[str | None] = mapped_column(String(32), nullable=True)
source_config: Mapped[dict[str, object] | None] = mapped_column(JSONB, nullable=True)
evidence_recording_policy: Mapped[dict[str, object] | None] = mapped_column(
    JSONB,
    nullable=True,
)
```

- [ ] **Step 6: Add migration**

Create `backend/src/argus/migrations/versions/0011_accountable_scene_evidence.py`
with:

- PostgreSQL enum creation for the new enums
- `scene_contract_snapshots`
- `privacy_manifest_snapshots`
- `evidence_artifacts`
- `evidence_ledger_entries`
- incident columns for contract, manifest, and recording policy
- camera columns `source_kind`, `source_config`, and `evidence_recording_policy`
- indexes listed in the spec

Backfill existing cameras:

```python
op.execute(
    "UPDATE cameras SET source_kind = 'rtsp', source_config = '{\"kind\":\"rtsp\"}'::jsonb "
    "WHERE source_kind IS NULL"
)
```

- [ ] **Step 7: Run focused tests**

Run:

```bash
cd /Users/yann.moren/vision/backend
python3 -m uv run pytest tests/services/test_scene_contracts.py tests/services/test_evidence_ledger.py tests/core/test_db.py -q
```

Expected: pass.

- [ ] **Step 8: Commit and push**

```bash
git add backend/src/argus/models/enums.py \
  backend/src/argus/models/tables.py \
  backend/src/argus/migrations/versions/0011_accountable_scene_evidence.py \
  backend/src/argus/api/contracts.py \
  backend/tests/services/test_scene_contracts.py \
  backend/tests/services/test_evidence_ledger.py
git commit -m "feat(evidence): add accountable scene data contract"
git push origin codex/omnisight-ui-spec-implementation
```

## Task 2: Privacy Manifest Builder

**Files:**

- Create: `backend/src/argus/services/privacy_manifests.py`
- Modify: `backend/src/argus/services/app.py`
- Test: `backend/tests/services/test_privacy_manifests.py`

- [ ] **Step 1: Write failing manifest tests**

Create `backend/tests/services/test_privacy_manifests.py`:

```python
from __future__ import annotations

from uuid import uuid4

from argus.api.contracts import EvidenceRecordingPolicy
from argus.services.privacy_manifests import (
    build_privacy_manifest,
    hash_manifest,
)


def test_privacy_manifest_is_deterministic_and_disables_biometrics_by_default() -> None:
    camera_id = uuid4()
    tenant_id = uuid4()
    policy = EvidenceRecordingPolicy(storage_profile="edge_local")

    first = build_privacy_manifest(
        tenant_id=tenant_id,
        camera_id=camera_id,
        deployment_mode="edge",
        recording_policy=policy,
        allow_plaintext_plates=False,
        plaintext_justification=None,
    )
    second = build_privacy_manifest(
        tenant_id=tenant_id,
        camera_id=camera_id,
        deployment_mode="edge",
        recording_policy=policy,
        allow_plaintext_plates=False,
        plaintext_justification=None,
    )

    assert first == second
    assert first["identity"]["face_identification"] == "disabled"
    assert first["identity"]["biometric_identification"] == "disabled"
    assert first["plates"]["plaintext_storage"] == "blocked"
    assert first["storage"]["residency"] == "edge"
    assert hash_manifest(first) == hash_manifest(second)
```

- [ ] **Step 2: Run failing tests**

```bash
cd /Users/yann.moren/vision/backend
python3 -m uv run pytest tests/services/test_privacy_manifests.py -q
```

Expected: fail because the module does not exist.

- [ ] **Step 3: Implement manifest builder**

Create `backend/src/argus/services/privacy_manifests.py` with:

- `canonical_json(value: object) -> str`
- `hash_manifest(manifest: Mapping[str, object]) -> str`
- `build_privacy_manifest(...) -> dict[str, object]`
- `PrivacyManifestService.get_or_create_snapshot(...)`

The manifest must include:

```python
{
    "schema_version": 1,
    "tenant_id": str(tenant_id),
    "camera_id": str(camera_id),
    "deployment_mode": deployment_mode,
    "identity": {
        "face_identification": "disabled",
        "biometric_identification": "disabled",
    },
    "plates": {
        "plaintext_storage": "allowed" if allow_plaintext_plates else "blocked",
        "plaintext_justification": plaintext_justification,
    },
    "recording": recording_policy.model_dump(mode="json"),
    "storage": {
        "residency": _residency_for_storage_profile(recording_policy.storage_profile),
        "profile": recording_policy.storage_profile,
    },
    "review": {
        "human_review_required": True,
    },
}
```

- [ ] **Step 4: Add snapshot service tests**

Extend `test_privacy_manifests.py` with a database-backed service test following
the existing async service test patterns. Verify that identical manifests reuse
the same `manifest_hash` and do not create duplicate snapshots.

- [ ] **Step 5: Run tests**

```bash
cd /Users/yann.moren/vision/backend
python3 -m uv run pytest tests/services/test_privacy_manifests.py -q
```

Expected: pass.

- [ ] **Step 6: Commit and push**

```bash
git add backend/src/argus/services/privacy_manifests.py \
  backend/src/argus/services/app.py \
  backend/tests/services/test_privacy_manifests.py
git commit -m "feat(evidence): build scene privacy manifests"
git push origin codex/omnisight-ui-spec-implementation
```

## Task 3: Scene Contract Compiler

**Files:**

- Create: `backend/src/argus/services/scene_contracts.py`
- Modify: `backend/src/argus/services/app.py`
- Modify: `backend/src/argus/inference/engine.py`
- Test: `backend/tests/services/test_scene_contracts.py`
- Test: `backend/tests/services/test_camera_worker_config.py`

- [ ] **Step 1: Add failing compiler tests**

Append to `backend/tests/services/test_scene_contracts.py`:

```python
from argus.api.contracts import EvidenceRecordingPolicy
from argus.services.scene_contracts import build_scene_contract, hash_contract


def test_scene_contract_hash_changes_when_runtime_vocabulary_changes() -> None:
    base = build_scene_contract(
        tenant_id="tenant-a",
        site_id="site-a",
        camera_id="camera-a",
        camera_name="Gate A",
        camera_source={"kind": "usb", "uri": "usb:///dev/video0", "redacted_uri": "usb://***"},
        deployment_mode="edge",
        model={"id": "model-a", "format": "onnx", "capability": "fixed_vocab"},
        runtime_vocabulary={"terms": ["person"], "version": 1, "hash": "a" * 64},
        runtime_selection={"backend": "onnxruntime", "fallback_reason": None},
        vision_profile={"preset": "industrial-yard"},
        detection_regions=[],
        candidate_quality={"min_confidence": 0.25},
        recording_policy=EvidenceRecordingPolicy(),
        privacy_manifest_hash="b" * 64,
    )
    changed = build_scene_contract(
        tenant_id="tenant-a",
        site_id="site-a",
        camera_id="camera-a",
        camera_name="Gate A",
        camera_source={"kind": "usb", "uri": "usb:///dev/video0", "redacted_uri": "usb://***"},
        deployment_mode="edge",
        model={"id": "model-a", "format": "onnx", "capability": "fixed_vocab"},
        runtime_vocabulary={"terms": ["person", "forklift"], "version": 2, "hash": "c" * 64},
        runtime_selection={"backend": "onnxruntime", "fallback_reason": None},
        vision_profile={"preset": "industrial-yard"},
        detection_regions=[],
        candidate_quality={"min_confidence": 0.25},
        recording_policy=EvidenceRecordingPolicy(),
        privacy_manifest_hash="b" * 64,
    )

    assert hash_contract(base) != hash_contract(changed)
```

- [ ] **Step 2: Run failing tests**

```bash
cd /Users/yann.moren/vision/backend
python3 -m uv run pytest tests/services/test_scene_contracts.py -q
```

Expected: fail because compiler functions do not exist.

- [ ] **Step 3: Implement compiler**

Create `backend/src/argus/services/scene_contracts.py` with:

- `canonical_json`
- `hash_contract`
- `build_scene_contract`
- `SceneContractService.get_or_create_snapshot`

The contract must include `schema_version=1`, model, runtime vocabulary,
runtime selection, vision profile, detection regions, candidate quality,
recording policy, camera source, and privacy manifest hash.

- [ ] **Step 4: Attach contract to worker config**

In `backend/src/argus/services/app.py`, when building worker config:

- resolve `EvidenceRecordingPolicy` from `camera.evidence_recording_policy` or settings defaults
- build or load the privacy manifest snapshot
- build or load the scene contract snapshot
- include the recording policy and contract hash in the worker-facing config

Carry these fields in the worker-facing config:

```python
scene_contract_hash: str | None
privacy_manifest_hash: str | None
recording_policy: EvidenceRecordingPolicy
```

- [ ] **Step 5: Add worker config tests**

Extend `backend/tests/services/test_camera_worker_config.py`:

- worker config includes recording policy
- worker config includes scene contract hash
- worker config includes privacy manifest hash
- default recording policy uses short event clip values

- [ ] **Step 6: Run tests**

```bash
cd /Users/yann.moren/vision/backend
python3 -m uv run pytest tests/services/test_scene_contracts.py tests/services/test_camera_worker_config.py -q
```

Expected: pass.

- [ ] **Step 7: Commit and push**

```bash
git add backend/src/argus/services/scene_contracts.py \
  backend/src/argus/services/app.py \
  backend/src/argus/inference/engine.py \
  backend/tests/services/test_scene_contracts.py \
  backend/tests/services/test_camera_worker_config.py
git commit -m "feat(evidence): compile scene contracts"
git push origin codex/omnisight-ui-spec-implementation
```

## Task 4: Edge USB Camera Source Support

**Files:**

- Modify: `backend/src/argus/models/enums.py`
- Modify: `backend/src/argus/api/contracts.py`
- Create: `backend/src/argus/services/camera_sources.py`
- Modify: `backend/src/argus/services/app.py`
- Modify: `backend/src/argus/vision/camera.py`
- Modify: `backend/src/argus/vision/source_probe.py`
- Modify: `backend/src/argus/inference/engine.py`
- Create: `backend/tests/services/test_camera_sources.py`
- Create: `backend/tests/vision/test_camera_source.py`
- Test: `backend/tests/services/test_camera_worker_config.py`
- Create: `backend/tests/api/test_camera_setup_routes.py`

- [ ] **Step 1: Add failing source contract tests**

Create `backend/tests/services/test_camera_sources.py`:

```python
from __future__ import annotations

from uuid import uuid4

import pytest
from fastapi import HTTPException

from argus.api.contracts import CameraSourceSettings
from argus.models.enums import CameraSourceKind, ProcessingMode
from argus.services.camera_sources import (
    normalize_camera_source,
    redact_camera_source_uri,
    validate_camera_source_assignment,
)


def test_normalizes_usb_source_to_edge_device_path() -> None:
    source = normalize_camera_source(
        CameraSourceSettings(kind=CameraSourceKind.USB, uri="usb:///dev/video0")
    )

    assert source.kind is CameraSourceKind.USB
    assert source.uri == "usb:///dev/video0"
    assert source.capture_uri == "/dev/video0"
    assert redact_camera_source_uri(source) == "usb://***"


def test_usb_source_requires_edge_processing_and_edge_node() -> None:
    with pytest.raises(HTTPException) as exc:
        validate_camera_source_assignment(
            source=CameraSourceSettings(kind=CameraSourceKind.USB, uri="usb:///dev/video0"),
            processing_mode=ProcessingMode.CENTRAL,
            edge_node_id=None,
        )

    assert exc.value.status_code == 422
    assert "USB sources require edge processing and an edge node" in str(exc.value.detail)


def test_usb_source_accepts_edge_processing_with_edge_node() -> None:
    validate_camera_source_assignment(
        source=CameraSourceSettings(kind=CameraSourceKind.USB, uri="usb:///dev/video0"),
        processing_mode=ProcessingMode.EDGE,
        edge_node_id=uuid4(),
    )
```

- [ ] **Step 2: Add failing capture resolution tests**

Create `backend/tests/vision/test_camera_source.py`:

```python
from __future__ import annotations

import cv2

from argus.vision.camera import CameraSourceMode, PlatformInfo, _resolve_capture_spec


def test_resolves_usb_uri_to_v4l2_device_path() -> None:
    mode, source, backend = _resolve_capture_spec(
        "usb:///dev/video0",
        PlatformInfo(machine="aarch64", jetson=True),
    )

    assert mode is CameraSourceMode.LINUX_USB
    assert source == "/dev/video0"
    assert backend == cv2.CAP_V4L2
```

- [ ] **Step 3: Run failing tests**

```bash
cd /Users/yann.moren/vision/backend
python3 -m uv run pytest tests/services/test_camera_sources.py tests/vision/test_camera_source.py -q
```

Expected: fail because camera source service and USB capture mode do not exist.

- [ ] **Step 4: Implement camera source service**

Create `backend/src/argus/services/camera_sources.py`:

```python
from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from fastapi import HTTPException, status

from argus.api.contracts import CameraSourceSettings
from argus.models.enums import CameraSourceKind, ProcessingMode


@dataclass(frozen=True, slots=True)
class NormalizedCameraSource:
    kind: CameraSourceKind
    uri: str
    capture_uri: str
    redacted_uri: str
    label: str | None = None


def normalize_camera_source(source: CameraSourceSettings) -> NormalizedCameraSource:
    if source.kind is CameraSourceKind.USB:
        path = source.uri.removeprefix("usb://")
        if not path.startswith("/dev/video"):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="USB sources must use usb:///dev/videoN.",
            )
        return NormalizedCameraSource(
            kind=source.kind,
            uri=source.uri,
            capture_uri=path,
            redacted_uri="usb://***",
            label=source.label,
        )
    if source.kind is CameraSourceKind.JETSON_CSI:
        return NormalizedCameraSource(
            kind=source.kind,
            uri=source.uri,
            capture_uri=source.uri,
            redacted_uri="csi://***",
            label=source.label,
        )
    return NormalizedCameraSource(
        kind=source.kind,
        uri=source.uri,
        capture_uri=source.uri,
        redacted_uri="rtsp://***",
        label=source.label,
    )


def redact_camera_source_uri(source: NormalizedCameraSource | CameraSourceSettings) -> str:
    normalized = source if isinstance(source, NormalizedCameraSource) else normalize_camera_source(source)
    return normalized.redacted_uri


def validate_camera_source_assignment(
    *,
    source: CameraSourceSettings,
    processing_mode: ProcessingMode,
    edge_node_id: UUID | None,
) -> None:
    if source.kind is CameraSourceKind.USB and (
        processing_mode is not ProcessingMode.EDGE or edge_node_id is None
    ):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="USB sources require edge processing and an edge node.",
        )
```

- [ ] **Step 5: Add USB capture mode**

In `backend/src/argus/vision/camera.py`:

- add `LINUX_USB = "linux-usb"` to `CameraSourceMode`
- update `_resolve_capture_spec` so `usb:///dev/video0` returns
  `(CameraSourceMode.LINUX_USB, "/dev/video0", cv2.CAP_V4L2)`
- keep existing RTSP and CSI behavior unchanged

- [ ] **Step 6: Update API and app service contracts**

In `backend/src/argus/api/contracts.py`:

- add `CameraSourceSettings`
- add `camera_source: CameraSourceSettings | None = None` to create/update
- add `edge_node_id: UUID | None = None` to `CameraCreate` and `CameraUpdate`
- make `rtsp_url` optional for create when `camera_source` is provided
- add `camera_source` to `CameraResponse`, `CameraSourceProbeRequest`,
  `WorkerCameraSettings`, and `WorkerConfigResponse`

In `backend/src/argus/services/app.py`:

- resolve `payload.camera_source` or legacy `payload.rtsp_url`
- validate USB source assignment
- persist `camera.source_kind` and `camera.source_config`
- keep encrypting `rtsp_url_encrypted` only for RTSP
- return `rtsp_url_masked` for compatibility and `camera_source` for the new UI
- disable native passthrough browser delivery for USB
- worker config should send `camera.source_uri` equal to `/dev/videoN` for USB
  and `rtsp://...` for RTSP

- [ ] **Step 7: Update source probing**

In `backend/src/argus/vision/source_probe.py`, add a USB probe path that opens
the local device through OpenCV/V4L2 and returns `SourceCapability`.

In the source probe API:

- RTSP continues to probe centrally as today
- USB probe only succeeds from an edge-reachable worker context or a fake test
  capture
- if USB is not reachable, return a clear source probe error rather than trying
  RTSP fallback

- [ ] **Step 8: Update worker runtime engine**

In `backend/src/argus/inference/engine.py`:

- replace RTSP-only camera setting usage with source-aware settings
- pass USB `source_uri` into `CameraSourceConfig`
- register MediaMTX browser delivery as worker-published processed stream for
  USB
- keep RTSP passthrough/transcode behavior unchanged

- [ ] **Step 9: Run focused tests**

```bash
cd /Users/yann.moren/vision/backend
python3 -m uv run pytest \
  tests/services/test_camera_sources.py \
  tests/vision/test_camera_source.py \
  tests/services/test_camera_worker_config.py \
  tests/api/test_camera_setup_routes.py \
  tests/inference/test_engine.py \
  -q
```

Expected: pass.

- [ ] **Step 10: Commit and push**

```bash
git add backend/src/argus/models/enums.py \
  backend/src/argus/api/contracts.py \
  backend/src/argus/services/camera_sources.py \
  backend/src/argus/services/app.py \
  backend/src/argus/vision/camera.py \
  backend/src/argus/vision/source_probe.py \
  backend/src/argus/inference/engine.py \
  backend/tests/services/test_camera_sources.py \
  backend/tests/vision/test_camera_source.py \
  backend/tests/services/test_camera_worker_config.py \
  backend/tests/api/test_camera_setup_routes.py
git commit -m "feat(cameras): support edge usb camera sources"
git push origin codex/omnisight-ui-spec-implementation
```

## Task 5: Evidence Storage Providers

**Files:**

- Create: `backend/src/argus/services/evidence_storage.py`
- Modify: `backend/src/argus/services/object_store.py`
- Modify: `backend/src/argus/core/config.py`
- Test: `backend/tests/services/test_evidence_storage.py`

- [ ] **Step 1: Add failing storage tests**

Create `backend/tests/services/test_evidence_storage.py` covering:

- local filesystem store writes bytes under a configured root
- local store returns sha256, size, provider, scope, key, and content type
- S3-compatible wrapper preserves existing MinIO behavior and returns metadata

- [ ] **Step 2: Run failing tests**

```bash
cd /Users/yann.moren/vision/backend
python3 -m uv run pytest tests/services/test_evidence_storage.py -q
```

Expected: fail because storage abstraction does not exist.

- [ ] **Step 3: Add settings**

In `backend/src/argus/core/config.py`, add:

```python
incident_storage_provider: Literal["local_filesystem", "minio", "s3_compatible"] = "minio"
incident_storage_scope: Literal["edge", "central", "cloud"] = "central"
incident_local_storage_root: str = "./var/evidence"
```

Keep existing MinIO settings for dev and S3-compatible deployments.

- [ ] **Step 4: Implement storage abstraction**

Create:

```python
@dataclass(frozen=True, slots=True)
class StoredEvidenceObject:
    provider: EvidenceStorageProvider
    scope: EvidenceStorageScope
    bucket: str | None
    object_key: str
    content_type: str
    sha256: str
    size_bytes: int
    review_url: str | None = None


class EvidenceObjectStore(Protocol):
    async def put_object(self, *, key: str, data: bytes, content_type: str) -> StoredEvidenceObject: ...
```

Implement:

- `LocalFilesystemEvidenceStore`
- `S3CompatibleEvidenceStore`
- `build_evidence_store(settings: Settings) -> EvidenceObjectStore`

The S3-compatible implementation may reuse the MinIO client and existing
settings.

- [ ] **Step 5: Run tests**

```bash
cd /Users/yann.moren/vision/backend
python3 -m uv run pytest tests/services/test_evidence_storage.py tests/services/test_incident_capture.py -q
```

Expected: pass.

- [ ] **Step 6: Commit and push**

```bash
git add backend/src/argus/services/evidence_storage.py \
  backend/src/argus/services/object_store.py \
  backend/src/argus/core/config.py \
  backend/tests/services/test_evidence_storage.py
git commit -m "feat(evidence): support local and remote artifact storage"
git push origin codex/omnisight-ui-spec-implementation
```

## Task 6: Artifact-Aware Incident Clip Capture

**Files:**

- Modify: `backend/src/argus/services/incident_capture.py`
- Modify: `backend/src/argus/inference/engine.py`
- Modify: `backend/src/argus/services/app.py`
- Test: `backend/tests/services/test_incident_capture.py`
- Test: `backend/tests/inference/test_engine.py`

- [ ] **Step 1: Add failing capture tests**

Extend `backend/tests/services/test_incident_capture.py` with:

- local-only clip creates an evidence artifact
- captured artifact records clip start, trigger, end, fps, sha256, provider, and scope
- quota exceeded writes an artifact with status `quota_exceeded` or a ledger-only failure state
- capture failure creates an incident and ledger entry

- [ ] **Step 2: Run failing tests**

```bash
cd /Users/yann.moren/vision/backend
python3 -m uv run pytest tests/services/test_incident_capture.py -q
```

Expected: fail because repository and capture service do not create artifacts.

- [ ] **Step 3: Extend repository protocol**

In `incident_capture.py`, extend `IncidentRepository.create_incident` so it can
accept:

- `scene_contract_snapshot_id`
- `scene_contract_hash`
- `privacy_manifest_snapshot_id`
- `privacy_manifest_hash`
- `recording_policy`
- `artifact_payload`
- initial ledger payloads

Keep compatibility in tests by updating fakes explicitly.

- [ ] **Step 4: Persist incident and artifact together**

In `SQLIncidentRepository.create_incident`, create:

- `Incident`
- `EvidenceArtifact` when clip metadata is present
- ledger entries for trigger, contract attached, manifest attached, and clip
  result

Use one database transaction.

- [ ] **Step 5: Use policy-based recording windows**

Thread `EvidenceRecordingPolicy` into `IncidentClipCaptureService`.

For one worker per camera, initialize:

```python
pre_seconds=recording_policy.pre_seconds
post_seconds=recording_policy.post_seconds
fps=recording_policy.fps
```

If `recording_policy.enabled` is false, create incidents without clip artifacts
and append a ledger entry explaining that recording was disabled by policy.

- [ ] **Step 6: Run tests**

```bash
cd /Users/yann.moren/vision/backend
python3 -m uv run pytest tests/services/test_incident_capture.py tests/inference/test_engine.py -q
```

Expected: pass.

- [ ] **Step 7: Commit and push**

```bash
git add backend/src/argus/services/incident_capture.py \
  backend/src/argus/inference/engine.py \
  backend/src/argus/services/app.py \
  backend/tests/services/test_incident_capture.py \
  backend/tests/inference/test_engine.py
git commit -m "feat(evidence): record accountable incident clips"
git push origin codex/omnisight-ui-spec-implementation
```

## Task 7: Evidence Ledger Service And Review Integration

**Files:**

- Create: `backend/src/argus/services/evidence_ledger.py`
- Modify: `backend/src/argus/services/app.py`
- Test: `backend/tests/services/test_evidence_ledger.py`
- Test: `backend/tests/services/test_incident_service.py`

- [ ] **Step 1: Add failing ledger tests**

Extend `backend/tests/services/test_evidence_ledger.py`:

- appending two entries increments sequence
- second entry references first `entry_hash`
- changing payload changes entry hash
- listing entries returns ordered rows

- [ ] **Step 2: Run failing tests**

```bash
cd /Users/yann.moren/vision/backend
python3 -m uv run pytest tests/services/test_evidence_ledger.py -q
```

Expected: fail because service does not exist.

- [ ] **Step 3: Implement ledger service**

Create `backend/src/argus/services/evidence_ledger.py` with:

- `canonical_json`
- `compute_entry_hash`
- `EvidenceLedgerService.append_entry`
- `EvidenceLedgerService.list_for_incident`
- `EvidenceLedgerService.summary_for_incident`

Hash input must include:

- incident id
- sequence
- action
- occurred_at ISO string
- actor type
- actor subject
- payload
- previous hash

- [ ] **Step 4: Integrate review/reopen ledger**

In `IncidentService.update_review_state`, append:

- `incident.reviewed` when status changes to reviewed
- `incident.reopened` when status changes to pending

Keep the existing audit log behavior.

- [ ] **Step 5: Run tests**

```bash
cd /Users/yann.moren/vision/backend
python3 -m uv run pytest tests/services/test_evidence_ledger.py tests/services/test_incident_service.py -q
```

Expected: pass.

- [ ] **Step 6: Commit and push**

```bash
git add backend/src/argus/services/evidence_ledger.py \
  backend/src/argus/services/app.py \
  backend/tests/services/test_evidence_ledger.py \
  backend/tests/services/test_incident_service.py
git commit -m "feat(evidence): append incident evidence ledger"
git push origin codex/omnisight-ui-spec-implementation
```

## Task 8: Incident API And Artifact Content Routes

**Files:**

- Modify: `backend/src/argus/services/app.py`
- Modify: `backend/src/argus/api/v1/incidents.py` or the existing incident router file
- Modify: `backend/src/argus/api/contracts.py`
- Test: `backend/tests/api/test_prompt9_routes.py`

- [ ] **Step 1: Add failing API tests**

Extend incident route tests to cover:

- list incidents includes `scene_contract_hash`, `privacy_manifest_hash`,
  `evidence_artifacts`, and `ledger_summary`
- `GET /api/v1/incidents/{id}/scene-contract`
- `GET /api/v1/incidents/{id}/privacy-manifest`
- `GET /api/v1/incidents/{id}/ledger`
- `GET /api/v1/incidents/{id}/artifacts/{artifact_id}/content`

- [ ] **Step 2: Run failing tests**

```bash
cd /Users/yann.moren/vision/backend
python3 -m uv run pytest tests/api/test_prompt9_routes.py -q
```

Expected: fail because routes and response fields are missing.

- [ ] **Step 3: Extend incident response mapping**

Update `_incident_response` and incident listing queries to load:

- artifact rows for each incident
- ledger summary
- scene contract ids/hashes
- privacy manifest ids/hashes
- recording policy

Avoid N+1 queries by batching artifacts and summaries for list endpoints.

- [ ] **Step 4: Add detail routes**

Add authenticated routes that enforce tenant scope:

```text
GET /api/v1/incidents/{incident_id}/scene-contract
GET /api/v1/incidents/{incident_id}/privacy-manifest
GET /api/v1/incidents/{incident_id}/ledger
GET /api/v1/incidents/{incident_id}/artifacts/{artifact_id}/content
```

For artifact content:

- local filesystem: stream bytes with content type
- remote object store: redirect to a short-lived signed URL when available
- missing/expired artifact: `404`

- [ ] **Step 5: Regenerate OpenAPI types**

Run the local OpenAPI generation command used on this branch:

```bash
cd /Users/yann.moren/vision
python3 -m uv run --project backend python -c 'import json; from argus.main import create_app; from argus.core.config import Settings; app = create_app(Settings(enable_startup_services=False, enable_nats=False)); print(json.dumps(app.openapi()))' > /private/tmp/argus-openapi.json
corepack pnpm --dir frontend exec openapi-typescript /private/tmp/argus-openapi.json -o src/lib/api.generated.ts
```

- [ ] **Step 6: Run tests**

```bash
cd /Users/yann.moren/vision/backend
python3 -m uv run pytest tests/api/test_prompt9_routes.py tests/services/test_incident_service.py -q
```

Expected: pass.

- [ ] **Step 7: Commit and push**

```bash
git add backend/src/argus/services/app.py \
  backend/src/argus/api/v1/incidents.py \
  backend/src/argus/api/contracts.py \
  backend/tests/api/test_prompt9_routes.py \
  frontend/src/lib/api.generated.ts
git commit -m "feat(api): expose accountable evidence details"
git push origin codex/omnisight-ui-spec-implementation
```

## Task 9: Evidence Desk Accountability UI

**Files:**

- Modify: `frontend/src/pages/Incidents.tsx`
- Modify: `frontend/src/pages/Incidents.test.tsx`
- Create: `frontend/src/components/evidence/AccountabilityStrip.tsx`
- Create: `frontend/src/components/evidence/AccountabilityStrip.test.tsx`

- [ ] **Step 1: Add failing UI tests**

Extend `frontend/src/pages/Incidents.test.tsx` to assert that an incident with
accountability metadata renders:

- `Scene contract`
- hash prefix
- `Privacy manifest`
- `Face ID disabled`
- `Biometric ID disabled`
- `Evidence clip`
- `Local evidence`, `Central evidence`, or `Cloud evidence`
- `Ledger`
- artifact-aware `Open clip` link

- [ ] **Step 2: Run failing tests**

```bash
cd /Users/yann.moren/vision
corepack pnpm --dir frontend exec vitest run src/pages/Incidents.test.tsx
```

Expected: fail because the UI does not render the new fields.

- [ ] **Step 3: Implement accountability strip**

Add a compact strip in the selected evidence hero:

- Scene contract cell
- Privacy manifest cell
- Evidence clip cell
- Ledger cell

Use existing page styling. Do not add nested cards. Keep text compact and
readable on mobile.

- [ ] **Step 4: Implement details panel**

In the facts rail, add a disclosure for:

- scene contract details
- privacy manifest details
- ledger entries

Keep raw payload inspectable and separate from accountability details.

- [ ] **Step 5: Run frontend tests**

```bash
cd /Users/yann.moren/vision
corepack pnpm --dir frontend exec vitest run src/pages/Incidents.test.tsx
```

Expected: pass.

- [ ] **Step 6: Commit and push**

```bash
git add frontend/src/pages/Incidents.tsx \
  frontend/src/pages/Incidents.test.tsx \
  frontend/src/components/evidence/AccountabilityStrip.tsx \
  frontend/src/components/evidence/AccountabilityStrip.test.tsx
git commit -m "feat(ui): show accountable evidence context"
git push origin codex/omnisight-ui-spec-implementation
```

## Task 10: Camera Source And Recording Policy UI

**Files:**

- Modify: `frontend/src/components/cameras/CameraWizard.tsx`
- Modify: `frontend/src/components/cameras/CameraWizard.test.tsx`
- Modify: `frontend/src/pages/Settings.tsx`

- [ ] **Step 1: Add failing UI tests**

Add tests that verify camera setup can display and submit:

- source type: RTSP
- source type: USB edge camera
- USB device URI such as `usb:///dev/video0`
- edge-only validation text for USB sources
- event clip recording enabled
- pre seconds
- post seconds
- fps
- storage profile: edge local, central, cloud, local first

- [ ] **Step 2: Run failing tests**

```bash
cd /Users/yann.moren/vision
corepack pnpm --dir frontend exec vitest run src/components/cameras/CameraWizard.test.tsx
```

Expected: fail because camera wizard does not expose USB camera sources or
recording policy.

- [ ] **Step 3: Implement controls**

Add restrained controls:

- segmented control or select for source type: RTSP or USB edge camera
- RTSP URL field only for RTSP sources
- USB device field only for USB sources, with placeholder `usb:///dev/video0`
- edge processing and edge node requirement copy for USB
- toggle for event clip recording
- numeric fields or steppers for pre/post/fps
- select for storage profile

Do not imply continuous recording. Use `Event clip` language. Do not present USB
as a central-processing source.

- [ ] **Step 4: Run tests**

```bash
cd /Users/yann.moren/vision
corepack pnpm --dir frontend exec vitest run src/components/cameras/CameraWizard.test.tsx src/pages/Incidents.test.tsx
```

Expected: pass.

- [ ] **Step 5: Commit and push**

```bash
git add frontend/src/components/cameras/CameraWizard.tsx \
  frontend/src/components/cameras/CameraWizard.test.tsx \
  frontend/src/pages/Settings.tsx
git commit -m "feat(ui): configure camera source and recording policy"
git push origin codex/omnisight-ui-spec-implementation
```

## Task 11: Documentation

**Files:**

- Modify: `docs/runbook.md`
- Modify: `docs/operator-deployment-playbook.md`
- Modify: `docs/scene-vision-profile-configuration-guide.md`

- [ ] **Step 1: Update runbook**

Add sections for:

- edge USB/UVC camera source setup
- scene contracts
- privacy manifests
- evidence ledger
- local filesystem evidence storage
- central MinIO evidence storage
- remote/cloud S3-compatible evidence storage
- edge-mode local clips
- short event clip policy

- [ ] **Step 2: Update deployment playbook**

Add deployment guidance:

- when to choose USB/UVC edge cameras
- how to map stable device references such as `/dev/video0`
- when to choose edge local storage
- when to choose central MinIO
- when to choose cloud/S3-compatible storage
- backup/retention implications
- how Evidence Desk reviews local-only clips

- [ ] **Step 3: Update scene guide**

Explain that scene setup now compiles into an accountability contract attached
to incidents.

- [ ] **Step 4: Verify docs**

```bash
cd /Users/yann.moren/vision
git diff --check -- docs/runbook.md docs/operator-deployment-playbook.md docs/scene-vision-profile-configuration-guide.md
```

Expected: no output.

- [ ] **Step 5: Commit and push**

```bash
git add docs/runbook.md \
  docs/operator-deployment-playbook.md \
  docs/scene-vision-profile-configuration-guide.md
git commit -m "docs(evidence): explain accountable scene recording"
git push origin codex/omnisight-ui-spec-implementation
```

## Task 12: Focused Verification Sweep

**Files:**

- No source edits unless verification reveals a task-owned failure.

- [ ] **Step 1: Backend focused tests**

```bash
cd /Users/yann.moren/vision/backend
python3 -m uv run pytest \
  tests/services/test_scene_contracts.py \
  tests/services/test_privacy_manifests.py \
  tests/services/test_evidence_ledger.py \
  tests/services/test_evidence_storage.py \
  tests/services/test_camera_sources.py \
  tests/services/test_incident_capture.py \
  tests/services/test_incident_service.py \
  tests/services/test_camera_worker_config.py \
  tests/vision/test_camera_source.py \
  tests/api/test_camera_setup_routes.py \
  tests/api/test_prompt9_routes.py \
  tests/inference/test_engine.py \
  tests/core/test_db.py \
  -q
```

- [ ] **Step 2: Frontend focused tests**

```bash
cd /Users/yann.moren/vision
corepack pnpm --dir frontend exec vitest run \
  src/pages/Incidents.test.tsx \
  src/components/cameras/CameraWizard.test.tsx
```

- [ ] **Step 3: Frontend full test/build/lint**

```bash
cd /Users/yann.moren/vision
CI=1 corepack pnpm --dir frontend test -- --run
corepack pnpm --dir frontend build
corepack pnpm --dir frontend lint
```

- [ ] **Step 4: Backend lint/type checks**

```bash
cd /Users/yann.moren/vision/backend
python3 -m uv run ruff check src tests
python3 -m uv run mypy src
```

If unrelated pre-existing failures remain, record exact file/line details and do
not hide them.

- [ ] **Step 5: Commit fixes and push**

If verification required fixes:

```bash
git add <task-owned-files>
git commit -m "fix(evidence): address accountable evidence verification"
git push origin codex/omnisight-ui-spec-implementation
```

## Follow-Up Queue After This Plan

Do not start these until Tasks 1-11 are complete and the user approves the next
direction.

### 4. Runtime Passport

Create a dedicated runtime passport from data already captured in scene
contracts:

- model hash
- runtime artifact id/hash
- selected backend
- target profile
- precision
- provider versions
- validation time
- fallback reason

### 5. Operational Memory

Use evidence ledger and contracts to identify repeated operational patterns:

- repeated event bursts
- zone hot spots
- clip/storage failures by site
- incident changes after scene contract changes

### 6. Prompt-To-Policy

Compile operator language into proposed scene contracts and recording/privacy
policy. Require approval before applying changes.

### 7. Identity-Light Cross-Camera Intelligence

Build cross-camera reasoning that uses class, zone, motion, timing, and
non-biometric attributes only when the privacy manifest allows it. Keep face ID
and biometric identity off by default.
