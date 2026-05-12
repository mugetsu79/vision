# Accountable Scene Intelligence And Evidence Recording Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement the full still-pertinent handoff runway: accountable scene evidence, Evidence Desk polish, runtime passports, per-worker incident rules, operational memory, prompt-to-policy, identity-light cross-camera intelligence, Fleet/Operations hardening, Jetson runtime soak, and gated DeepStream.

**Architecture:** Land immutable scene/privacy snapshots, first-class evidence artifacts, and incident-scoped ledger entries first, then add a UI-managed configuration control plane before introducing more runtime behavior. The worker continues to emit short event clips; storage becomes provider-aware and the per-camera recording policy selects a UI-managed runtime route so edge local, central MinIO, S3-compatible/cloud, and local-first deployments share one review contract. Before Operational Memory starts, per-worker incident rules must become UI/API-managed scene policy that production workers load and report. Later tasks must derive runtime, policy, memory, cross-camera, and supervisor views from the same contract, artifact, ledger, configuration-profile, rule, and runtime-report data instead of adding parallel case-history systems.

**Tech Stack:** FastAPI, Pydantic, SQLAlchemy async, Alembic, PostgreSQL JSONB, OpenCV MJPEG clip encoding, local filesystem storage, MinIO/S3-compatible object storage, React 19, Vite 6, TypeScript 5.7, Tailwind v4, Vitest, pytest, Ruff, mypy.

**Spec source:** `/Users/yann.moren/vision/docs/superpowers/specs/2026-05-11-accountable-scene-intelligence-and-evidence-recording-design.md`

---

## Execution Protocol

Execute one task at a time. After each task:

1. run the task verification commands
2. commit only the files for that task
3. push the branch
4. report the result before continuing

Do not stage unrelated untracked scratch files. Keep WebGL off. Execute the
tasks in order. Runtime Passport, per-worker incident rules, Operational
Memory, Prompt-To-Policy, Identity-Light Cross-Camera Intelligence,
Fleet/Operations hardening, and runtime soak are now part of this plan after
the accountable evidence foundation. Track C / DeepStream remains a late gated
task and must not start until the runtime soak task proves Track A/B readiness
on target Jetson hardware.

After Task 13C, no new operator-facing product behavior may rely only on
environment variables, command-line flags, or hand-edited backend files. A task
that introduces configurable product behavior must either consume an existing
operator configuration profile or add the UI/API/profile support in that same
task. Environment variables are reserved for bootstrap-only infrastructure and
break-glass support.

After Task 13D, no configuration tab may be treated as complete because it only
persists data. The plan must either implement runtime consumption for that
profile kind, or name the later task and test that will consume it. This applies
to evidence storage, stream delivery, runtime selection, privacy policy,
LLM provider, and operations mode.

## Implementation Progress As Of 2026-05-12

Completed and pushed on `codex/omnisight-ui-spec-implementation`:

- Tasks `1-13`: accountable data foundation, capture/storage/ledger/API,
  operator-facing Evidence Desk foundation, and accountable evidence polish.
- Tasks `13A-13C`: UI-managed configuration profile data model, API,
  validation/resolution service, and Settings workspace.
- Task `13D`: evidence recording storage profile runtime routing for local,
  MinIO/S3-compatible, cloud, edge-local, and local-first policies.
- Tasks `13E-13J`: local-first upload sync, effective runtime configuration
  diagnostics, stream delivery profile routing, runtime-selection profile
  consumption, privacy-policy runtime consumption, and LLM-provider runtime
  consumption.
- Task `14`: optional still snapshot evidence artifacts.
- Tasks `15-16`: runtime passport snapshots, incident attachment, incident API,
  and Operations/Evidence UI surfacing.

Current migration head after the Task 16 checkpoint is
`0016_runtime_passports`. The next planned migration in this plan is
`0017_detection_rule_incident_metadata.py`.

Next task:

```text
Task 16A: Incident Rule Data Contract, Service, And API
```

## Validation Bands

The plan is executable task-by-task, but validation should happen in bands. Each
task still requires its own focused tests, commit, and push. At the end of each
band, pause and report the band result before continuing.

### Band 1: Accountable Data Foundation

Tasks: `1-3`

Status: completed and pushed.

Validation goal:

- migrations apply cleanly
- camera source and recording policy contracts are stable
- privacy manifest hashes are deterministic
- scene contract hashes are deterministic
- snapshot dedupe works

Band gate: confirm the durable primitives are correct before attaching them to
capture, APIs, and UI.

### Band 2: Capture, Storage, Ledger, API

Tasks: `4-8`

Status: completed and pushed.

Validation goal:

- USB/UVC source contracts and worker config work
- local edge storage works
- MinIO/S3-compatible storage still works
- artifact-aware clip capture works
- evidence ledger entries are emitted for incident, artifact, review, and
  failure paths
- authenticated artifact content routes serve or redirect reviewable clips

Band gate: create an incident with scene contract, privacy manifest, evidence
artifact, ledger entries, and a clip that can be opened through the API.

### Band 3: Operator-Facing Evidence Foundation

Tasks: `9-13`

Status: completed and pushed.

Validation goal:

- Evidence Desk shows accountability strip, artifact status, ledger summary,
  scene contract, and privacy manifest context
- Camera Wizard exposes source and recording controls without implying
  continuous recording
- docs explain local edge, central, and cloud storage
- focused verification sweep passes or records pre-existing unrelated failures
- Evidence Timeline and Case Context polish are retuned around accountable
  evidence

Band gate: a reviewer can understand what happened, which contract produced it,
which privacy posture governed it, and where the evidence clip lives.

### Pre-Band 4: UI-Managed Configuration Control Plane

Tasks: `13A-13C`

Status: completed and pushed.

Validation goal:

- operator-facing configuration has a database/API/UI control plane
- product configuration profiles can be created, updated, tested, audited,
  bound to tenants/sites/edge nodes/cameras, and resolved without shell edits
- secrets are write-only in browser responses and encrypted at rest
- Evidence storage, stream delivery, runtime selection, privacy/retention, LLM
  provider, and operations-mode categories exist in the UI configuration
  catalog, and each category has an explicit runtime-consumer task named below
- storage profiles are fully configurable from the UI before runtime routing is
  tested

Band gate: a normal admin can configure product behavior from Settings without
editing backend env files, except for documented bootstrap-only infrastructure.

### Pre-Band 4.5: Recording Storage Routing Gate

Task: `13D`

Status: completed and pushed.

Validation goal:

- `EvidenceRecordingPolicy.storage_profile` and the selected UI-managed storage
  profile are honored by incident capture at runtime
- `edge_local`, `central`, `cloud`, and `local_first` resolve to the expected
  provider, scope, and artifact status
- local-first writes a reviewable local artifact and records `upload_pending`
  instead of pretending a remote copy exists
- the Evidence Desk labels upload-pending clips correctly

Band gate: before optional snapshot media is added, prove the storage selector
and configured storage profile are not only UI metadata and that clip review
still works in edge mode.

### Pre-Band 4.6: UI-Managed Runtime Consumption Gate

Tasks: `13E-13J`

Status: completed and pushed.

Validation goal:

- local-first evidence sync retries pending uploads and promotes artifacts only
  after confirmed remote upload
- effective configuration diagnostics show which profile wins for every
  category at tenant/site/edge/camera scope
- stream delivery and browser playback URLs are driven by the selected
  `stream_delivery` profile
- runtime artifact selection honors the selected `runtime_selection` profile
  before runtime passports are built
- privacy manifests, clip quota, and retention/expiry behavior honor the
  selected `privacy_policy` profile
- LLM-backed policy draft code resolves the selected `llm_provider` profile and
  never exposes secrets to the browser

Band gate: a normal admin can save, bind, test, and then observe the runtime
effect of every Settings category that exists before the next evidence-media
task starts. `operations_mode` is allowed to wait for supervisor tasks, but
Tasks 20-22 must explicitly consume it.

### Band 4: Evidence Media Completion

Task: `14`

Status: completed and pushed.

Validation goal:

- optional still snapshots can be captured as evidence artifacts
- `snapshot_url` remains nullable when snapshots are disabled or unavailable
- snapshot failures do not break clip capture
- snapshot artifact ledger entries are emitted

Band gate: clips remain the primary evidence path, with snapshots available as
optional first-class evidence.

### Band 5: Runtime Passport

Tasks: `15-16`

Status: completed and pushed.

Validation goal:

- runtime passport snapshots are deterministic
- incidents and Operations rows can show selected backend, model hash, runtime
  artifact id/hash, target profile, precision, validation time, and fallback
  reason
- fixed-vocab, TensorRT, compiled open-vocab, and dynamic fallback cases are
  represented honestly

Band gate: model/runtime accountability is visible without needing to inspect
worker logs.

### Pre-Band 6: Per-Worker Incident Rules

Tasks: `16A-16E`

Validation goal:

- operators can define enabled/disabled incident rules per scene from
  Control -> Scenes
- rule predicates validate against scene classes, vocabulary, zones,
  confidence, and supported non-biometric attributes
- worker config and camera commands carry enabled rules to production workers
- workers load and hot-reload persisted rules without requiring shell edits or
  process restarts
- non-count rule events create incidents whose type comes from the
  operator-defined incident type slug
- Evidence Desk shows the trigger rule summary and Operations shows effective
  worker rule count/hash/load status
- scene contracts and incident payloads carry deterministic rule hashes

Band gate: a normal admin can define what counts as an incident for a scene
worker, the worker can emit a real incident from that rule, and a reviewer can
see the rule that caused the evidence record.

### Band 6: Product Differentiators

Tasks: `17-19`

Validation goal:

- Operational Memory shows observed patterns with source incident citations
- Prompt-To-Policy creates reviewable drafts and never applies changes without
  approval
- Identity-Light Cross-Camera Intelligence links incidents only with
  privacy-allowed non-biometric signals

Band gate: pause after each task in this band for product-direction review, not
only test review.

### Band 7: Edge-First Production Operations

Tasks: `20-22`

Validation goal:

- persistent worker assignments and reassignment work
- supervisors can report per-worker runtime truth, heartbeat, restart count,
  last error, runtime backend, and scene contract hash
- Operations lifecycle buttons create Start/Stop/Restart/Drain requests instead
  of shelling out
- edge credential rotation returns one-time material and does not persist
  plaintext secrets

Band gate: Operations can be used as a production control surface without
pretending the backend API owns host processes.

### Band 8: Real Jetson Runtime Validation

Task: `23`

Validation goal:

- Linux master plus Jetson edge topology is documented and exercised
- chosen fixed-vocab TensorRT artifact, for example YOLO26n, is built,
  registered, validated, selected, restarted, and rolled back
- compiled YOLOE S/open-vocab scene artifacts are built, registered, validated,
  selected, restarted, and rolled back
- evidence clip review, Operations worker truth, credential rotation, and
  fallback behavior are validated in the real topology

Band gate: record actual hardware soak evidence before opening the DeepStream
lane.

### Band 9: DeepStream Gate

Task: `24`

Validation goal:

- DeepStream starts only after Band 8 passes, unless the user explicitly accepts
  the risk
- DeepStream metadata maps into the existing track lifecycle
- Operations reports DeepStream pipeline health
- fallback to non-DeepStream runtimes remains available

Band gate: DeepStream is treated as a separate runtime lane, not a rewrite of
the accountability system.

### Band 10: Final Hardening

Task: `25`

Validation goal:

- full focused backend suite passes or records exact unrelated failures
- focused frontend suite passes
- frontend build/lint and backend Ruff/mypy results are recorded
- docs and handoff match the implemented state
- next-chat prompt is updated

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

If dev DB errors mention `cameras.vision_profile`, `cameras.detection_regions`,
`model_runtime_artifacts`, `scene_contract_snapshots`,
`operator_config_profiles`, `operator_config_secrets`,
`operator_config_bindings`, `runtime_passport_snapshots`,
`detection_rules.enabled`, `detection_rules.incident_type`,
`detection_rules.rule_hash`, `worker_assignments`, or any table created by this
plan, run:

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
| `backend/src/argus/migrations/versions/0012_operator_configuration_profiles.py` | create | UI-managed configuration profile, secret, and binding tables |
| `backend/src/argus/migrations/versions/0013_local_first_sync_state.py` | create | local-first upload retry and promotion state |
| `backend/src/argus/services/operator_configuration.py` | create | configuration profile CRUD, secret handling, validation, binding, and resolution |
| `backend/src/argus/services/runtime_configuration.py` | create | worker/service-safe resolved configuration packet for all UI-managed profile kinds |
| `backend/src/argus/services/local_first_sync.py` | create | retry and promote upload-pending local-first evidence artifacts |
| `backend/src/argus/services/privacy_policy_runtime.py` | create | apply UI-managed privacy policy profiles to manifests, quotas, and retention |
| `backend/src/argus/services/llm_provider_runtime.py` | create | resolve LLM provider profiles and secrets for policy draft services |
| `backend/src/argus/api/v1/configuration.py` | create | configuration catalog, profile, test, binding, and resolved-config routes |
| `backend/src/argus/vision/camera.py` | modify | resolve USB/UVC source URIs to edge V4L2/OpenCV capture |
| `backend/src/argus/vision/source_probe.py` | modify | probe USB/UVC source capability without treating it as RTSP |
| `backend/src/argus/inference/engine.py` | modify | carry camera source, recording policy, and scene contract context into capture |
| `frontend/src/lib/api.generated.ts` | regenerate | OpenAPI types |
| `frontend/src/hooks/use-configuration.ts` | create | configuration profile and binding API hooks |
| `frontend/src/components/configuration/ConfigurationWorkspace.tsx` | create | Settings configuration control plane |
| `frontend/src/components/configuration/ProfileEditor.tsx` | create | category-aware profile editors and validation actions |
| `frontend/src/components/configuration/ProfileBindingPanel.tsx` | create | bind profiles to tenant, site, edge node, and camera scopes |
| `frontend/src/components/configuration/EffectiveConfigurationPanel.tsx` | create | show the resolved runtime profile for each category and target |
| `frontend/src/hooks/use-incidents.ts` | modify | incident response type usage for accountability fields |
| `frontend/src/pages/Incidents.tsx` | modify | display contract, manifest, artifact, and ledger status |
| `frontend/src/pages/Incidents.test.tsx` | modify | UI coverage |
| `frontend/src/components/evidence/AccountabilityStrip.tsx` | create | compact contract, privacy, artifact, and ledger strip |
| `frontend/src/components/evidence/AccountabilityStrip.test.tsx` | create | accountability strip rendering tests |
| `frontend/src/components/cameras/CameraWizard.tsx` | modify | RTSP/USB source selection and recording policy controls |
| `frontend/src/components/cameras/CameraWizard.test.tsx` | modify | camera source and recording policy tests |
| `backend/src/argus/migrations/versions/0015_snapshot_ledger_actions.py` | created | snapshot evidence ledger actions |
| `backend/src/argus/migrations/versions/0016_runtime_passports.py` | created | runtime passport table and incident attachment columns |
| `backend/src/argus/migrations/versions/0017_detection_rule_incident_metadata.py` | create | detection rule incident metadata, deterministic rule hashes, and indexes |
| `backend/src/argus/migrations/versions/0018_operational_memory_patterns.py` | create | operational memory pattern table |
| `backend/src/argus/migrations/versions/0019_policy_drafts.py` | create | prompt-to-policy draft table |
| `backend/src/argus/migrations/versions/0020_cross_camera_threads.py` | create | identity-light cross-camera thread table |
| `backend/src/argus/migrations/versions/0021_supervisor_operations.py` | create | worker assignment, runtime report, and lifecycle request tables |
| `backend/src/argus/migrations/versions/0022_runtime_artifact_soak_runs.py` | create | runtime artifact soak run table |
| `backend/src/argus/services/runtime_passports.py` | create | runtime passport snapshot builder and incident attachment |
| `backend/src/argus/services/incident_rules.py` | create | per-camera incident rule CRUD, validation, hashing, and command publication |
| `backend/src/argus/services/rule_events.py` | create | persistent rule event store for workers |
| `backend/src/argus/services/operational_memory.py` | create | pattern detection over incidents, artifacts, contracts, and ledgers |
| `backend/src/argus/services/policy_drafts.py` | create | prompt-to-policy draft, diff, approval, rejection, and application service |
| `backend/src/argus/services/cross_camera_threads.py` | create | identity-light non-biometric incident correlation |
| `backend/src/argus/services/supervisor_operations.py` | create | worker assignments, supervisor reports, lifecycle requests, credential rotation |
| `backend/src/argus/services/runtime_soak.py` | create | runtime artifact soak run recorder and validation summary |
| `backend/src/argus/vision/deepstream_runtime.py` | create late | DeepStream backend adapter after soak gate |
| `backend/src/argus/vision/deepstream_metadata.py` | create late | DeepStream metadata bridge into track lifecycle |
| `backend/src/argus/api/v1/policy_drafts.py` | create | prompt-to-policy draft and decision routes |
| `backend/src/argus/api/v1/incident_rules.py` | create | camera-scoped incident rule routes |
| `backend/src/argus/api/v1/runtime_soak.py` | create | runtime artifact soak routes |
| `frontend/src/components/evidence/EvidenceTimeline.tsx` | create | accountable timeline density strip |
| `frontend/src/components/evidence/CaseContextStrip.tsx` | create | selected incident context strip |
| `frontend/src/components/evidence/RuntimePassportPanel.tsx` | create | runtime passport details |
| `frontend/src/hooks/use-incident-rules.ts` | create | camera incident rule API hooks |
| `frontend/src/components/cameras/IncidentRulesPanel.tsx` | create | Control -> Scenes rule builder |
| `frontend/src/components/evidence/IncidentRuleSummary.tsx` | create | trigger rule summary for evidence review |
| `frontend/src/components/evidence/OperationalMemoryPanel.tsx` | create | cited operational patterns |
| `frontend/src/components/evidence/CrossCameraThreadPanel.tsx` | create | privacy-aware thread context |
| `frontend/src/components/policy/PolicyDraftReview.tsx` | create | prompt-to-policy draft diff and approval UI |
| `frontend/src/components/operations/SupervisorLifecycleControls.tsx` | create | Start/Stop/Restart/Drain request controls |
| `docs/runbook.md` | modify | storage and recording configuration |
| `docs/operator-deployment-playbook.md` | modify | edge USB camera, local evidence, and remote/cloud evidence guidance |
| `docs/imac-master-orin-lab-test-guide.md` | modify | Linux master plus Jetson soak validation and rollback |
| `docs/model-loading-and-configuration-guide.md` | modify | runtime artifact soak and DeepStream gate notes |

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

If verification required fixes, inspect the changed files and stage only the
files owned by Tasks 1-12. Do not use `git add -A`.

```bash
git status --short
git add backend/src/argus/models/enums.py \
  backend/src/argus/models/tables.py \
  backend/src/argus/api/contracts.py \
  backend/src/argus/services/camera_sources.py \
  backend/src/argus/services/scene_contracts.py \
  backend/src/argus/services/privacy_manifests.py \
  backend/src/argus/services/evidence_ledger.py \
  backend/src/argus/services/evidence_storage.py \
  backend/src/argus/services/incident_capture.py \
  backend/src/argus/services/app.py \
  backend/src/argus/api/v1/incidents.py \
  backend/src/argus/vision/camera.py \
  backend/src/argus/vision/source_probe.py \
  backend/src/argus/inference/engine.py \
  frontend/src/lib/api.generated.ts \
  frontend/src/hooks/use-incidents.ts \
  frontend/src/pages/Incidents.tsx \
  frontend/src/components/evidence/AccountabilityStrip.tsx \
  frontend/src/components/cameras/CameraWizard.tsx \
  docs/runbook.md \
  docs/operator-deployment-playbook.md \
  docs/scene-vision-profile-configuration-guide.md
git commit -m "fix(evidence): address accountable evidence verification"
git push origin codex/omnisight-ui-spec-implementation
```

## Task 13: Evidence Desk Timeline And Case Context Polish

**Files:**

- Create: `frontend/src/components/evidence/evidence-signals.ts`
- Create: `frontend/src/components/evidence/evidence-signals.test.ts`
- Create: `frontend/src/components/evidence/EvidenceTimeline.tsx`
- Create: `frontend/src/components/evidence/EvidenceTimeline.test.tsx`
- Create: `frontend/src/components/evidence/CaseContextStrip.tsx`
- Create: `frontend/src/components/evidence/CaseContextStrip.test.tsx`
- Modify: `frontend/src/pages/Incidents.tsx`
- Modify: `frontend/src/pages/Incidents.test.tsx`

- [ ] **Step 1: Add failing signal and UI tests**

Cover:

- timeline buckets over the loaded incident set
- selected incident bucket marker
- clip-only, snapshot-only, clip-plus-snapshot, and metadata-only evidence states
- contract, manifest, artifact, and ledger status in the Case Context Strip
- type-colored queue accents
- raw payload disclosure collapsed behind an accessible button

- [ ] **Step 2: Run failing tests**

```bash
cd /Users/yann.moren/vision
corepack pnpm --dir frontend exec vitest run \
  src/components/evidence/evidence-signals.test.ts \
  src/components/evidence/EvidenceTimeline.test.tsx \
  src/components/evidence/CaseContextStrip.test.tsx \
  src/pages/Incidents.test.tsx
```

Expected: fail until the new components and signal model exist.

- [ ] **Step 3: Implement the retuned Evidence Desk polish**

Implement the old Evidence Desk polish scope around accountable fields from
Tasks 1-9:

- `Evidence Timeline` density strip between filters and the desk layout
- `Case Context Strip` in the selected incident hero
- type-colored review queue accents
- raw payload disclosure that stays below decision facts
- no WebGL, no decorative dashboards, no continuous animation

- [ ] **Step 4: Run tests**

```bash
cd /Users/yann.moren/vision
corepack pnpm --dir frontend exec vitest run \
  src/components/evidence/evidence-signals.test.ts \
  src/components/evidence/EvidenceTimeline.test.tsx \
  src/components/evidence/CaseContextStrip.test.tsx \
  src/pages/Incidents.test.tsx
```

Expected: pass.

- [ ] **Step 5: Commit and push**

```bash
git add frontend/src/components/evidence/evidence-signals.ts \
  frontend/src/components/evidence/evidence-signals.test.ts \
  frontend/src/components/evidence/EvidenceTimeline.tsx \
  frontend/src/components/evidence/EvidenceTimeline.test.tsx \
  frontend/src/components/evidence/CaseContextStrip.tsx \
  frontend/src/components/evidence/CaseContextStrip.test.tsx \
  frontend/src/pages/Incidents.tsx \
  frontend/src/pages/Incidents.test.tsx
git commit -m "feat(evidence): add accountable timeline and case context"
git push origin codex/omnisight-ui-spec-implementation
```

## Task 13A: Operator Configuration Data Foundation

**Files:**

- Modify: `backend/src/argus/core/config.py`
- Modify: `backend/src/argus/core/security.py`
- Modify: `backend/src/argus/models/enums.py`
- Modify: `backend/src/argus/models/tables.py`
- Create: `backend/src/argus/migrations/versions/0012_operator_configuration_profiles.py`
- Modify: `backend/src/argus/api/contracts.py`
- Test: `backend/tests/core/test_db.py`
- Test: `backend/tests/services/test_operator_configuration.py`

This task creates the product rule in code: operator-facing configuration is a
database-backed control-plane object. Environment variables can seed defaults,
but they are not the normal operator interface.

- [ ] **Step 1: Add failing model and contract tests**

Create `backend/tests/services/test_operator_configuration.py` with tests for:

- profile kind enum values:
  `evidence_storage`, `stream_delivery`, `runtime_selection`, `privacy_policy`,
  `llm_provider`, `operations_mode`
- profile scope enum values: `tenant`, `site`, `edge_node`, `camera`
- validation status values: `unvalidated`, `valid`, `invalid`
- `OperatorConfigProfileResponse` redacts secrets by exposing
  `secret_state={"access_key": "present", "secret_key": "present"}` rather than
  plaintext
- `OperatorConfigProfileCreate` accepts category-specific storage config:

```python
{
    "kind": "evidence_storage",
    "scope": "tenant",
    "name": "Dev MinIO",
    "slug": "dev-minio",
    "is_default": True,
    "config": {
        "provider": "minio",
        "storage_scope": "central",
        "endpoint": "localhost:9000",
        "bucket": "incidents",
        "secure": False,
        "path_prefix": "dev",
    },
    "secrets": {
        "access_key": "argus",
        "secret_key": "argus-dev-secret",
    },
}
```

Extend `backend/tests/core/test_db.py` so `Base.metadata.create_all` includes:

- `operator_config_profiles`
- `operator_config_secrets`
- `operator_config_bindings`

- [ ] **Step 2: Run failing tests**

```bash
cd /Users/yann.moren/vision/backend
python3 -m uv run pytest \
  tests/services/test_operator_configuration.py \
  tests/core/test_db.py \
  -q
```

Expected: fail because the models, contracts, and migration do not exist.

- [ ] **Step 3: Add configuration enums**

In `backend/src/argus/models/enums.py`, add:

```python
class OperatorConfigProfileKind(StrEnum):
    EVIDENCE_STORAGE = "evidence_storage"
    STREAM_DELIVERY = "stream_delivery"
    RUNTIME_SELECTION = "runtime_selection"
    PRIVACY_POLICY = "privacy_policy"
    LLM_PROVIDER = "llm_provider"
    OPERATIONS_MODE = "operations_mode"


class OperatorConfigScope(StrEnum):
    TENANT = "tenant"
    SITE = "site"
    EDGE_NODE = "edge_node"
    CAMERA = "camera"


class OperatorConfigValidationStatus(StrEnum):
    UNVALIDATED = "unvalidated"
    VALID = "valid"
    INVALID = "invalid"
```

- [ ] **Step 4: Add configuration tables and migration**

In `backend/src/argus/models/tables.py`, add:

```python
class OperatorConfigProfile(UUIDPrimaryKeyMixin, TimestampMixin, UpdatedAtMixin, Base):
    __tablename__ = "operator_config_profiles"

    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False)
    site_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("sites.id"), nullable=True)
    edge_node_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("edge_nodes.id"), nullable=True)
    camera_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("cameras.id"), nullable=True)
    kind: Mapped[OperatorConfigProfileKind] = mapped_column(enum_column(OperatorConfigProfileKind, "operator_config_profile_kind_enum"), nullable=False)
    scope: Mapped[OperatorConfigScope] = mapped_column(enum_column(OperatorConfigScope, "operator_config_scope_enum"), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(String(255), nullable=False)
    enabled: Mapped[bool] = mapped_column(nullable=False, default=True)
    is_default: Mapped[bool] = mapped_column(nullable=False, default=False)
    config: Mapped[dict[str, object]] = mapped_column(JSONB, nullable=False, default=dict)
    validation_status: Mapped[OperatorConfigValidationStatus] = mapped_column(enum_column(OperatorConfigValidationStatus, "operator_config_validation_status_enum"), nullable=False, default=OperatorConfigValidationStatus.UNVALIDATED)
    validation_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    validated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    config_hash: Mapped[str] = mapped_column(String(64), nullable=False)
```

Add `OperatorConfigSecret` and `OperatorConfigBinding` with the fields from the
spec. The migration must use short constraint names and indexes:

- `uq_op_cfg_profile_slug`
- `ix_op_cfg_profile_tenant_kind`
- `uq_op_cfg_secret_key`
- `uq_op_cfg_binding_scope`

- [ ] **Step 5: Add generic secret encryption helpers**

In `backend/src/argus/core/config.py`, add:

```python
config_encryption_key: SecretStr = SecretStr("argus-dev-config-key")
```

In `backend/src/argus/core/security.py`, add:

```python
def encrypt_config_secret(plaintext: str, settings: Settings) -> str:
    key = _derive_encryption_key(settings.config_encryption_key.get_secret_value())
    aesgcm = AESGCM(key)
    nonce = os.urandom(12)
    ciphertext = aesgcm.encrypt(nonce, plaintext.encode("utf-8"), None)
    return base64.urlsafe_b64encode(nonce + ciphertext).decode("utf-8")


def decrypt_config_secret(ciphertext: str, settings: Settings) -> str:
    key = _derive_encryption_key(settings.config_encryption_key.get_secret_value())
    decoded = base64.urlsafe_b64decode(ciphertext.encode("utf-8"))
    nonce = decoded[:12]
    encrypted_payload = decoded[12:]
    aesgcm = AESGCM(key)
    try:
        plaintext = aesgcm.decrypt(nonce, encrypted_payload, None)
    except (InvalidTag, ValueError, TypeError) as exc:
        raise ValueError("Unable to decrypt configuration secret.") from exc
    return plaintext.decode("utf-8")
```

- [ ] **Step 6: Add API contracts**

In `backend/src/argus/api/contracts.py`, add:

- `EvidenceStorageProfileConfig`
- `StreamDeliveryProfileConfig`
- `RuntimeSelectionProfileConfig`
- `PrivacyPolicyProfileConfig`
- `LLMProviderProfileConfig`
- `OperationsModeProfileConfig`
- `OperatorConfigProfileCreate`
- `OperatorConfigProfileUpdate`
- `OperatorConfigProfileResponse`
- `OperatorConfigBindingRequest`
- `OperatorConfigBindingResponse`
- `OperatorConfigTestResponse`
- `ResolvedOperatorConfigResponse`

Responses must include `secret_state` and must not include plaintext `secrets`.

- [ ] **Step 7: Run tests**

```bash
cd /Users/yann.moren/vision/backend
python3 -m uv run pytest \
  tests/services/test_operator_configuration.py \
  tests/core/test_db.py \
  -q
```

Expected: pass.

- [ ] **Step 8: Commit and push**

```bash
git add backend/src/argus/core/config.py \
  backend/src/argus/core/security.py \
  backend/src/argus/models/enums.py \
  backend/src/argus/models/tables.py \
  backend/src/argus/migrations/versions/0012_operator_configuration_profiles.py \
  backend/src/argus/api/contracts.py \
  backend/tests/services/test_operator_configuration.py \
  backend/tests/core/test_db.py
git commit -m "feat(config): add operator configuration profiles"
git push origin codex/omnisight-ui-spec-implementation
```

## Task 13B: Configuration Service, API, Validation, And Resolution

**Files:**

- Create: `backend/src/argus/services/operator_configuration.py`
- Create: `backend/src/argus/api/v1/configuration.py`
- Modify: `backend/src/argus/api/v1/__init__.py`
- Modify: `backend/src/argus/services/app.py`
- Modify: `backend/src/argus/services/evidence_storage.py`
- Test: `backend/tests/services/test_operator_configuration.py`
- Test: `backend/tests/api/test_configuration_routes.py`

- [ ] **Step 1: Add failing service and route tests**

Extend `backend/tests/services/test_operator_configuration.py` and create
`backend/tests/api/test_configuration_routes.py` covering:

- creating a profile writes non-secret config and encrypted secrets
- listing profiles returns redacted secret state
- patching a profile can rotate one secret without clearing untouched secrets
- setting `is_default=True` clears the previous default for the same tenant and
  kind
- binding a profile to a camera returns the selected profile from resolution
- resolution order is camera, edge node, site, tenant default, bootstrap default
- `POST /api/v1/configuration/profiles/{profile_id}/test` validates local
  filesystem and S3-compatible evidence storage config
- audit action names:
  - `configuration.profile.create`
  - `configuration.profile.update`
  - `configuration.profile.delete`
  - `configuration.profile.test`
  - `configuration.binding.upsert`

- [ ] **Step 2: Run failing tests**

```bash
cd /Users/yann.moren/vision/backend
python3 -m uv run pytest \
  tests/services/test_operator_configuration.py \
  tests/api/test_configuration_routes.py \
  -q
```

Expected: fail because service and routes do not exist.

- [ ] **Step 3: Implement `OperatorConfigurationService`**

Create `backend/src/argus/services/operator_configuration.py` with:

- `list_catalog`
- `list_profiles`
- `create_profile`
- `update_profile`
- `delete_profile`
- `test_profile`
- `upsert_binding`
- `resolve_profile`
- `resolve_all_for_camera`
- `seed_bootstrap_defaults`

The service must:

- hash profile config with canonical JSON
- encrypt secrets with `encrypt_config_secret`
- decrypt secrets only for worker/service resolution paths
- keep browser/API responses redacted
- use `DatabaseAuditLogger`
- reject profile bindings across tenant boundaries
- reject disabled profiles as defaults or bindings

- [ ] **Step 4: Add profile validators**

In `operator_configuration.py`, implement:

- evidence storage local validator:
  - requires `local_root`
  - verifies path is absolute or under the configured dev storage root
  - returns `valid` when the path can be created/written in local validation
    mode
- evidence storage S3-compatible validator:
  - requires `endpoint`, `bucket`, `access_key`, and `secret_key`
  - uses the existing MinIO/S3-compatible client interface
  - returns `invalid` with a redacted message when the bucket check/upload check
    fails
- stream delivery validator:
  - validates endpoint URL shape and selected delivery mode
- runtime selection validator:
  - validates requested backend/artifact preference shape
- privacy/retention validator:
  - validates quota and retention values are non-negative and residency is one
    of `edge`, `central`, `cloud`, or `local_first`
- LLM provider validator:
  - validates provider/model/base URL shape without calling a paid remote API
- operations-mode validator:
  - validates lifecycle owner and supervisor mode values

- [ ] **Step 5: Add API routes**

Create `backend/src/argus/api/v1/configuration.py`:

```text
GET /api/v1/configuration/catalog
GET /api/v1/configuration/profiles
POST /api/v1/configuration/profiles
PATCH /api/v1/configuration/profiles/{profile_id}
DELETE /api/v1/configuration/profiles/{profile_id}
POST /api/v1/configuration/profiles/{profile_id}/test
POST /api/v1/configuration/bindings
GET /api/v1/configuration/resolved
```

Include the router from `backend/src/argus/api/v1/__init__.py`.

- [ ] **Step 6: Seed bootstrap defaults as UI-visible profiles**

In `OperatorConfigurationService.seed_bootstrap_defaults`, create development
defaults from existing settings when no tenant profile exists:

- `Dev MinIO` from `minio_endpoint`, `minio_incidents_bucket`,
  `minio_access_key`, `minio_secret_key`, `minio_secure`
- `Dev local evidence` from `incident_local_storage_root`
- `Default native stream delivery` from current MediaMTX/browser delivery
  settings
- `Default runtime selection` from current inference/runtime settings

Seeded profiles are normal UI-managed profiles after creation. They can be
edited, tested, disabled, or replaced from Settings.

- [ ] **Step 7: Run tests**

```bash
cd /Users/yann.moren/vision/backend
python3 -m uv run pytest \
  tests/services/test_operator_configuration.py \
  tests/api/test_configuration_routes.py \
  tests/services/test_camera_worker_config.py \
  -q
```

Expected: pass.

- [ ] **Step 8: Commit and push**

```bash
git add backend/src/argus/services/operator_configuration.py \
  backend/src/argus/api/v1/configuration.py \
  backend/src/argus/api/v1/__init__.py \
  backend/src/argus/services/app.py \
  backend/src/argus/services/evidence_storage.py \
  backend/tests/services/test_operator_configuration.py \
  backend/tests/api/test_configuration_routes.py
git commit -m "feat(config): expose UI-managed configuration API"
git push origin codex/omnisight-ui-spec-implementation
```

## Task 13C: Configuration Workspace UI

**Files:**

- Create: `frontend/src/hooks/use-configuration.ts`
- Create: `frontend/src/components/configuration/ConfigurationWorkspace.tsx`
- Create: `frontend/src/components/configuration/ProfileEditor.tsx`
- Create: `frontend/src/components/configuration/ProfileBindingPanel.tsx`
- Create: `frontend/src/components/configuration/configuration-copy.ts`
- Create: `frontend/src/components/configuration/ConfigurationWorkspace.test.tsx`
- Create: `frontend/src/components/configuration/ProfileEditor.test.tsx`
- Modify: `frontend/src/pages/Settings.tsx`
- Modify: `frontend/src/pages/Settings.test.tsx`
- Regenerate: `frontend/src/lib/api.generated.ts`

- [ ] **Step 1: Add failing UI tests**

Create tests covering:

- Settings shows a `Configuration` section before worker diagnostics
- category tabs or segmented controls for:
  - Evidence storage
  - Streams
  - Runtime
  - Privacy and retention
  - LLM and policy
  - Operations
- creating a cloud S3-compatible evidence storage profile submits endpoint,
  bucket, region, secure flag, and write-only access/secret keys
- saved secret fields render as `Stored` or `Replace secret`, never plaintext
- `Test profile` calls the profile test endpoint and renders valid/invalid
  status
- setting a profile as default renders a single default badge for that category
- profile binding panel can bind a profile to a camera, site, edge node, or
  tenant scope

- [ ] **Step 2: Run failing tests**

```bash
cd /Users/yann.moren/vision
corepack pnpm --dir frontend exec vitest run \
  src/components/configuration/ConfigurationWorkspace.test.tsx \
  src/components/configuration/ProfileEditor.test.tsx \
  src/pages/Settings.test.tsx
```

Expected: fail because configuration UI does not exist.

- [ ] **Step 3: Regenerate OpenAPI types**

```bash
cd /Users/yann.moren/vision
python3 -m uv run --project backend python -c 'import json; from argus.main import create_app; from argus.core.config import Settings; app = create_app(Settings(enable_startup_services=False, enable_nats=False)); print(json.dumps(app.openapi()))' > /private/tmp/argus-openapi.json
corepack pnpm --dir frontend exec openapi-typescript /private/tmp/argus-openapi.json -o src/lib/api.generated.ts
```

- [ ] **Step 4: Add configuration hooks**

Create `frontend/src/hooks/use-configuration.ts` with hooks for:

- `useConfigurationCatalog`
- `useConfigurationProfiles`
- `useCreateConfigurationProfile`
- `useUpdateConfigurationProfile`
- `useDeleteConfigurationProfile`
- `useTestConfigurationProfile`
- `useUpsertConfigurationBinding`
- `useResolvedConfiguration`

Use the existing API client pattern in `frontend/src/lib/api.ts`.

- [ ] **Step 5: Build the Settings configuration workspace**

Add `ConfigurationWorkspace` above the existing Operations rails in
`frontend/src/pages/Settings.tsx`.

Design rules:

- compact operations UI, not a marketing page
- no nested cards
- no WebGL
- no visible instructions that substitute for controls
- category-specific controls instead of raw JSON
- icons from `lucide-react`
- secrets are write-only fields with explicit `Replace` behavior

- [ ] **Step 6: Implement category editors**

`ProfileEditor` must have concrete controls for:

- Evidence storage:
  - provider: local filesystem, MinIO, S3-compatible, local-first
  - scope: edge, central, cloud
  - local root
  - endpoint
  - region
  - bucket
  - secure/TLS toggle
  - path prefix
  - access key and secret key write-only fields
- Streams:
  - delivery mode
  - native/WebRTC/HLS preference
  - public base URL
  - edge override URL
- Runtime:
  - preferred backend
  - artifact preference
  - fallback allowed toggle
- Privacy and retention:
  - retention days
  - storage quota
  - plaintext plate posture
  - residency guardrail
- LLM and policy:
  - provider
  - model
  - base URL
  - API key write-only field
- Operations:
  - lifecycle owner
  - supervisor mode
  - restart policy

- [ ] **Step 7: Run UI tests**

```bash
cd /Users/yann.moren/vision
corepack pnpm --dir frontend exec vitest run \
  src/components/configuration/ConfigurationWorkspace.test.tsx \
  src/components/configuration/ProfileEditor.test.tsx \
  src/pages/Settings.test.tsx
```

Expected: pass.

- [ ] **Step 8: Commit and push**

```bash
git add frontend/src/hooks/use-configuration.ts \
  frontend/src/components/configuration/ConfigurationWorkspace.tsx \
  frontend/src/components/configuration/ProfileEditor.tsx \
  frontend/src/components/configuration/ProfileBindingPanel.tsx \
  frontend/src/components/configuration/configuration-copy.ts \
  frontend/src/components/configuration/ConfigurationWorkspace.test.tsx \
  frontend/src/components/configuration/ProfileEditor.test.tsx \
  frontend/src/pages/Settings.tsx \
  frontend/src/pages/Settings.test.tsx \
  frontend/src/lib/api.generated.ts
git commit -m "feat(config): add configuration workspace"
git push origin codex/omnisight-ui-spec-implementation
```

## Task 13D: Recording Storage Profile Runtime Routing

**Files:**

- Modify: `backend/src/argus/api/contracts.py`
- Modify: `backend/src/argus/services/operator_configuration.py`
- Modify: `backend/src/argus/services/evidence_storage.py`
- Modify: `backend/src/argus/services/incident_capture.py`
- Modify: `backend/src/argus/inference/engine.py`
- Modify: `backend/tests/services/test_evidence_storage.py`
- Modify: `backend/tests/services/test_incident_capture.py`
- Modify: `backend/tests/inference/test_engine.py`
- Modify: `backend/tests/services/test_camera_worker_config.py`
- Modify: `frontend/src/components/cameras/CameraWizard.tsx`
- Modify: `frontend/src/components/cameras/CameraWizard.test.tsx`
- Modify: `frontend/src/components/evidence/AccountabilityStrip.tsx`
- Modify: `frontend/src/components/evidence/AccountabilityStrip.test.tsx`
- Modify: `frontend/src/components/evidence/CaseContextStrip.test.tsx`

Do this task after Task 13C and before Task 13E. Task 14 adds a second media
kind later; this task proves the existing event-clip path writes to the selected
UI-managed storage profile before local-first sync and the other runtime
configuration consumers are added.

- [ ] **Step 1: Add failing storage route tests**

Extend `backend/tests/services/test_evidence_storage.py` with route resolution
coverage using resolved `evidence_storage` operator configuration profiles:

- an `edge_local` profile with `provider="local_filesystem"` and
  `storage_scope="edge"` returns local filesystem storage and no status override
- a `central` profile with `provider="minio"` and `storage_scope="central"`
  returns remote storage with provider `EvidenceStorageProvider.MINIO`
- a `cloud` profile with `provider="s3_compatible"` and
  `storage_scope="cloud"` returns remote storage with provider
  `EvidenceStorageProvider.S3_COMPATIBLE`
- a `local_first` profile returns local filesystem storage and
  `EvidenceArtifactStatus.UPLOAD_PENDING`
- `EvidenceRecordingPolicy(storage_profile="cloud", storage_profile_id=<central-profile>)`
  fails validation because profile residency does not match policy intent
- the legacy `build_evidence_store(settings)` remains available only as a
  bootstrap/default compatibility path

- [ ] **Step 2: Add failing incident capture routing tests**

Extend `backend/tests/services/test_incident_capture.py` with:

- a fake resolver receiving an event policy with `storage_profile_id` for a
  cloud profile and selecting a cloud fake object store
- a second event policy with `storage_profile_id` for an edge-local profile and
  selecting a local fake object store in the same service instance
- a local-first event producing an artifact with status `upload_pending`,
  provider `local_filesystem`, and scope `edge`
- a selected storage route whose store raises during `put_object`, proving the
  incident is still created with no `clip_url`, `storage_bytes=0`, a
  `capture_failed` artifact for the intended object key, and a payload field
  `evidence_storage_error`

- [ ] **Step 3: Add failing UI status tests**

Extend `frontend/src/components/cameras/CameraWizard.test.tsx` so the recording
section loads configured evidence storage profiles and submits
`recording_policy.storage_profile_id` with the selected profile. Extend
`frontend/src/components/evidence/AccountabilityStrip.test.tsx` and
`frontend/src/components/evidence/CaseContextStrip.test.tsx` so an artifact with
`status: "upload_pending"` renders `Upload pending` rather than falling through
to an expired or unavailable label.

- [ ] **Step 4: Run failing tests**

```bash
cd /Users/yann.moren/vision/backend
python3 -m uv run pytest \
  tests/services/test_evidence_storage.py \
  tests/services/test_incident_capture.py \
  tests/inference/test_engine.py \
  -q
cd /Users/yann.moren/vision
corepack pnpm --dir frontend exec vitest run \
  src/components/cameras/CameraWizard.test.tsx \
  src/components/evidence/AccountabilityStrip.test.tsx \
  src/components/evidence/CaseContextStrip.test.tsx
```

Expected: fail because storage is still built from process settings rather than
the resolved UI-managed profile, Camera Wizard does not submit a profile id, and
`AccountabilityStrip` does not yet label `upload_pending`.

- [ ] **Step 5: Implement policy-to-storage routing**

In `backend/src/argus/services/evidence_storage.py`, add a route object and
resolver:

```python
@dataclass(frozen=True, slots=True)
class EvidenceStorageRoute:
    store: EvidenceObjectStore
    provider: EvidenceStorageProvider
    scope: EvidenceStorageScope
    status_override: EvidenceArtifactStatus | None = None


def resolve_evidence_storage_route(
    settings: Settings,
    *,
    recording_policy: EvidenceRecordingPolicy,
    profile: ResolvedOperatorConfigProfile,
) -> EvidenceStorageRoute: ...
```

Implement the route mapping from the resolved UI-managed profile:

- profile provider `minio` and scope `central`: `S3CompatibleEvidenceStore`,
  provider `minio`, scope `central`
- profile provider `s3_compatible` and scope `cloud`:
  `S3CompatibleEvidenceStore`, provider `s3_compatible`, scope `cloud`
- profile provider `local_filesystem` and scope `edge`:
  `LocalFilesystemEvidenceStore`, provider `local_filesystem`, scope `edge`
- profile provider `local_first`: `LocalFilesystemEvidenceStore`, provider
  `local_filesystem`, scope `edge`, status override `upload_pending`

Reject mismatches between `recording_policy.storage_profile` and the resolved
profile residency. The UI can show friendly validation before save, but runtime
must also guard the invariant.

Update `LocalFilesystemEvidenceStore` and `S3CompatibleEvidenceStore` so their
constructors can receive explicit provider/scope values instead of reading only
`settings.incident_storage_provider` and `settings.incident_storage_scope`.
Allow the S3-compatible store to receive endpoint, bucket, access key, secret
key, region, secure flag, and path prefix from the decrypted configuration
profile. Keep `build_evidence_store(settings)` as a bootstrap compatibility
wrapper only.

- [ ] **Step 6: Wire route selection into clip capture**

In `backend/src/argus/services/incident_capture.py`:

- add an `EvidenceStorageResolver` protocol that returns an
  `EvidenceStorageRoute` from camera id plus `EvidenceRecordingPolicy`
- keep the existing `object_store` constructor argument as the fallback for
  tests and legacy callers
- after resolving `recording_policy` in `_finalize_pending`, select the storage
  route from the resolver when present; the resolver must use
  `recording_policy.storage_profile_id` or the camera/site/edge/tenant binding
  resolution order from Task 13B
- pass `route.status_override` into `_event_clip_artifact_payload`; if present,
  use it instead of deriving status only from provider/scope
- when `put_object` raises, create the incident with `clip_url=None`,
  `storage_bytes=0`, payload key `evidence_storage_error`, and a failed artifact
  payload:

```python
{
    "kind": EvidenceArtifactKind.EVENT_CLIP,
    "status": EvidenceArtifactStatus.CAPTURE_FAILED,
    "storage_provider": route.provider,
    "storage_scope": route.scope,
    "bucket": None,
    "object_key": key,
    "content_type": "video/x-motion-jpeg",
    "sha256": hashlib.sha256(clip_bytes).hexdigest(),
    "size_bytes": clip_size,
    "clip_started_at": ...,
    "triggered_at": pending.event.ts,
    "clip_ended_at": ...,
    "duration_seconds": ...,
    "fps": self.fps,
    "scene_contract_hash": pending.event.scene_contract_hash,
    "privacy_manifest_hash": pending.event.privacy_manifest_hash,
}
```

Do not silently fall back to another profile when the selected route fails.

- [ ] **Step 7: Wire worker config and runtime**

In `backend/src/argus/api/contracts.py`, extend `EvidenceRecordingPolicy` with:

```python
storage_profile_id: UUID | None = None
```

Add a worker-only resolved storage contract:

```python
class WorkerEvidenceStorageSettings(BaseModel):
    profile_id: UUID | None = None
    profile_name: str | None = None
    profile_hash: str | None = None
    provider: EvidenceStorageProvider
    storage_scope: EvidenceStorageScope
    config: dict[str, object] = Field(default_factory=dict)
    secrets: dict[str, str] = Field(default_factory=dict)
```

In `CameraService.get_worker_config`, include
`WorkerEvidenceStorageSettings` resolved by `OperatorConfigurationService`.
Browser-facing configuration routes remain redacted; the worker config route is
the only path that may include decrypted runtime secrets.

In `backend/src/argus/inference/engine.py`, construct the incident capture
service with a resolver based on worker config, not local env settings:

```python
incident_capture=IncidentClipCaptureService(
    object_store=build_evidence_store(resolved_settings),
    storage_resolver=ResolvedEvidenceStorageResolver(
        settings=resolved_settings,
        evidence_storage=config.evidence_storage,
    ),
    repository=SQLIncidentRepository(db_manager.session_factory),
    recording_policy=config.recording_policy,
)
```

Add or adjust the corresponding `tests/inference/test_engine.py` assertion so
worker startup proves the resolver is present and the selected UI-managed
profile is used.

- [ ] **Step 8: Update Camera Wizard and upload-pending UI labels**

In `frontend/src/components/cameras/CameraWizard.tsx`, use
`useConfigurationProfiles({kind: "evidence_storage"})` to show named storage
profiles in the recording section. Submitting a camera should include both:

- `recording_policy.storage_profile`: the profile's residency intent
- `recording_policy.storage_profile_id`: the selected profile id

In `frontend/src/components/evidence/AccountabilityStrip.tsx`, update
`artifactStatusLabel` so `upload_pending` returns `Upload pending`. Keep
`CaseContextStrip` aligned with the same copy.

- [ ] **Step 9: Run focused verification**

```bash
cd /Users/yann.moren/vision/backend
python3 -m uv run pytest \
  tests/services/test_operator_configuration.py \
  tests/services/test_evidence_storage.py \
  tests/services/test_incident_capture.py \
  tests/services/test_camera_worker_config.py \
  tests/inference/test_engine.py \
  -q
cd /Users/yann.moren/vision
corepack pnpm --dir frontend exec vitest run \
  src/components/cameras/CameraWizard.test.tsx \
  src/components/evidence/AccountabilityStrip.test.tsx \
  src/components/evidence/CaseContextStrip.test.tsx \
  src/pages/Incidents.test.tsx
```

Expected: pass.

- [ ] **Step 10: Commit and push**

```bash
git add backend/src/argus/services/evidence_storage.py \
  backend/src/argus/api/contracts.py \
  backend/src/argus/services/operator_configuration.py \
  backend/src/argus/services/incident_capture.py \
  backend/src/argus/inference/engine.py \
  backend/tests/services/test_evidence_storage.py \
  backend/tests/services/test_incident_capture.py \
  backend/tests/services/test_camera_worker_config.py \
  backend/tests/inference/test_engine.py \
  frontend/src/components/cameras/CameraWizard.tsx \
  frontend/src/components/cameras/CameraWizard.test.tsx \
  frontend/src/components/evidence/AccountabilityStrip.tsx \
  frontend/src/components/evidence/AccountabilityStrip.test.tsx \
  frontend/src/components/evidence/CaseContextStrip.test.tsx
git commit -m "feat(evidence): route recording storage profiles"
git push origin codex/omnisight-ui-spec-implementation
```

## Task 13E: Local-First Evidence Upload Sync

**Files:**

- Modify: `backend/src/argus/models/enums.py`
- Modify: `backend/src/argus/models/tables.py`
- Create: `backend/src/argus/migrations/versions/0013_local_first_sync_state.py`
- Create: `backend/src/argus/services/local_first_sync.py`
- Modify: `backend/src/argus/services/evidence_storage.py`
- Modify: `backend/src/argus/services/evidence_ledger.py`
- Modify: `backend/src/argus/services/app.py`
- Test: `backend/tests/services/test_local_first_sync.py`
- Test: `backend/tests/services/test_evidence_storage.py`
- Modify: `frontend/src/components/evidence/AccountabilityStrip.tsx`
- Modify: `frontend/src/components/evidence/AccountabilityStrip.test.tsx`

This task makes `local_first` a usable deployment option, not just a local write
with a label. It must run before optional snapshot media so both clip and future
snapshot artifacts share the same promotion path.

- [ ] **Step 1: Add failing sync tests**

Create `backend/tests/services/test_local_first_sync.py` covering:

- an artifact with status `upload_pending`, provider `local_filesystem`, and a
  local object key is retried against a configured remote profile
- successful upload updates the artifact to `remote_available`, provider
  `minio` or `s3_compatible`, scope `central` or `cloud`, bucket, object key,
  and review URL metadata
- the original local checksum and object key are retained in ledger payload
- failed upload leaves the artifact reviewable locally, increments retry count,
  records latest error, and keeps status `upload_pending`
- sync is idempotent when the same artifact is processed twice

- [ ] **Step 2: Run failing tests**

```bash
cd /Users/yann.moren/vision/backend
python3 -m uv run pytest tests/services/test_local_first_sync.py -q
```

Expected: fail because durable local-first sync state and service do not exist.

- [ ] **Step 3: Add sync state and ledger actions**

Add ledger actions:

```python
EVIDENCE_UPLOAD_STARTED = "evidence.upload.started"
EVIDENCE_UPLOAD_AVAILABLE = "evidence.upload.available"
EVIDENCE_UPLOAD_FAILED = "evidence.upload.failed"
```

Create `local_first_sync_attempts` with artifact id, tenant id, remote profile
id, attempt count, latest status, latest error, last attempted at, and completed
at. Keep revision ids under 32 characters.

- [ ] **Step 4: Implement sync service**

Create `LocalFirstEvidenceSyncService` that:

- loads pending local-first artifacts by tenant/site/edge/camera scope
- resolves the remote profile from `EvidenceStorageProfileConfig.remote_profile_id`
  or a central/cloud evidence-storage binding
- reads the local artifact through the authenticated local storage resolver
- uploads through `S3CompatibleEvidenceStore`
- updates artifact metadata only after confirmed upload
- writes upload started/available/failed ledger entries

Do not delete the local file in this task. Retention cleanup is handled by the
privacy/retention task.

- [ ] **Step 5: Add operator-visible status**

Update Evidence Desk status copy so `upload_pending` can include the latest sync
attempt status when present: `Upload pending`, `Retrying upload`, or
`Upload failed; local copy available`.

- [ ] **Step 6: Run focused verification**

```bash
cd /Users/yann.moren/vision/backend
python3 -m uv run pytest \
  tests/services/test_local_first_sync.py \
  tests/services/test_evidence_storage.py \
  tests/services/test_evidence_ledger.py \
  -q
cd /Users/yann.moren/vision
corepack pnpm --dir frontend exec vitest run \
  src/components/evidence/AccountabilityStrip.test.tsx \
  src/pages/Incidents.test.tsx
```

Expected: pass.

- [ ] **Step 7: Commit and push**

```bash
git add backend/src/argus/models/enums.py \
  backend/src/argus/models/tables.py \
  backend/src/argus/migrations/versions/0013_local_first_sync_state.py \
  backend/src/argus/services/local_first_sync.py \
  backend/src/argus/services/evidence_storage.py \
  backend/src/argus/services/evidence_ledger.py \
  backend/src/argus/services/app.py \
  backend/tests/services/test_local_first_sync.py \
  backend/tests/services/test_evidence_storage.py \
  frontend/src/components/evidence/AccountabilityStrip.tsx \
  frontend/src/components/evidence/AccountabilityStrip.test.tsx \
  frontend/src/pages/Incidents.test.tsx
git commit -m "feat(evidence): sync local-first artifacts"
git push origin codex/omnisight-ui-spec-implementation
```

## Task 13F: Effective Configuration Runtime Diagnostics

**Files:**

- Modify: `backend/src/argus/api/contracts.py`
- Create: `backend/src/argus/services/runtime_configuration.py`
- Modify: `backend/src/argus/services/operator_configuration.py`
- Modify: `backend/src/argus/api/v1/configuration.py`
- Test: `backend/tests/services/test_runtime_configuration.py`
- Test: `backend/tests/api/test_configuration_routes.py`
- Modify: `frontend/src/hooks/use-configuration.ts`
- Create: `frontend/src/components/configuration/EffectiveConfigurationPanel.tsx`
- Create: `frontend/src/components/configuration/EffectiveConfigurationPanel.test.tsx`
- Modify: `frontend/src/components/configuration/ConfigurationWorkspace.tsx`
- Modify: `frontend/src/components/configuration/ConfigurationWorkspace.test.tsx`
- Modify: `frontend/src/lib/api.generated.ts`

- [ ] **Step 1: Add failing diagnostics tests**

Cover:

- `GET /api/v1/configuration/resolved?camera_id=<id>` returns all profile
  kinds with profile id, name, slug, scope winner, config hash, validation
  status, and redacted secret state
- camera binding wins over edge-node, site, tenant default, and bootstrap seed
- disabled or invalid profiles are reported as `unresolved` with an operator
  message instead of silently falling back
- browser responses never include decrypted secrets
- UI renders an "Effective configuration" panel for the selected target

- [ ] **Step 2: Run failing tests**

```bash
cd /Users/yann.moren/vision/backend
python3 -m uv run pytest \
  tests/services/test_runtime_configuration.py \
  tests/api/test_configuration_routes.py \
  -q
cd /Users/yann.moren/vision
corepack pnpm --dir frontend exec vitest run \
  src/components/configuration/EffectiveConfigurationPanel.test.tsx \
  src/components/configuration/ConfigurationWorkspace.test.tsx
```

Expected: fail because resolved configuration is not yet a complete runtime
diagnostic surface.

- [ ] **Step 3: Implement resolved runtime packet**

Create a service that returns a typed resolved configuration packet for:

- `evidence_storage`
- `stream_delivery`
- `runtime_selection`
- `privacy_policy`
- `llm_provider`
- `operations_mode`

Each entry must include `kind`, `profile_id`, `profile_name`, `profile_hash`,
`winner_scope`, `winner_scope_key`, `validation_status`, `applies_to_runtime`,
and redacted secret state. Add a service-only method that can include decrypted
secrets for LLM/storage consumers, but do not expose that method through browser
routes.

- [ ] **Step 4: Add Effective Configuration UI**

Add a compact Settings panel that lets an admin choose tenant/site/edge/camera
scope and see which profile is actually applied for every category. Include
clear copy for "runtime-wired now" versus "runtime-wired in Task 20" for
operations mode until supervisors land.

- [ ] **Step 5: Run focused verification**

```bash
cd /Users/yann.moren/vision
corepack pnpm generate:api
cd /Users/yann.moren/vision/backend
python3 -m uv run pytest \
  tests/services/test_runtime_configuration.py \
  tests/api/test_configuration_routes.py \
  -q
cd /Users/yann.moren/vision
corepack pnpm --dir frontend exec vitest run \
  src/components/configuration/EffectiveConfigurationPanel.test.tsx \
  src/components/configuration/ConfigurationWorkspace.test.tsx \
  src/pages/Settings.test.tsx
```

Expected: pass.

- [ ] **Step 6: Commit and push**

```bash
git add backend/src/argus/api/contracts.py \
  backend/src/argus/services/runtime_configuration.py \
  backend/src/argus/services/operator_configuration.py \
  backend/src/argus/api/v1/configuration.py \
  backend/tests/services/test_runtime_configuration.py \
  backend/tests/api/test_configuration_routes.py \
  frontend/src/hooks/use-configuration.ts \
  frontend/src/components/configuration/EffectiveConfigurationPanel.tsx \
  frontend/src/components/configuration/EffectiveConfigurationPanel.test.tsx \
  frontend/src/components/configuration/ConfigurationWorkspace.tsx \
  frontend/src/components/configuration/ConfigurationWorkspace.test.tsx \
  frontend/src/lib/api.generated.ts \
  frontend/src/pages/Settings.test.tsx
git commit -m "feat(config): show effective runtime configuration"
git push origin codex/omnisight-ui-spec-implementation
```

## Task 13G: Stream Delivery And Browser Playback Runtime Routing

**Files:**

- Modify: `backend/src/argus/api/contracts.py`
- Modify: `backend/src/argus/services/operator_configuration.py`
- Modify: `backend/src/argus/services/app.py`
- Modify: `backend/src/argus/inference/engine.py`
- Test: `backend/tests/services/test_camera_worker_config.py`
- Test: `backend/tests/api/test_prompt5_routes.py`
- Modify: `frontend/src/components/cameras/CameraWizard.tsx`
- Modify: `frontend/src/components/cameras/CameraWizard.test.tsx`
- Modify: `frontend/src/pages/Live.tsx`
- Modify: `frontend/src/pages/Incidents.tsx`
- Test: `frontend/src/pages/Live.test.tsx`
- Test: `frontend/src/pages/Incidents.test.tsx`
- Modify: `frontend/src/lib/api.generated.ts`

- [ ] **Step 1: Add failing stream delivery tests**

Cover:

- worker config includes the resolved `stream_delivery` profile id/hash and
  delivery mode
- Live playback URL generation uses the selected profile's public base URL,
  edge override URL, and delivery mode
- USB/UVC processed streams use the same browser delivery route as RTSP-backed
  processed streams
- Camera Wizard can select a named stream delivery profile when creating or
  editing a camera

- [ ] **Step 2: Run failing tests**

```bash
cd /Users/yann.moren/vision/backend
python3 -m uv run pytest \
  tests/services/test_camera_worker_config.py \
  tests/api/test_prompt5_routes.py \
  -q
cd /Users/yann.moren/vision
corepack pnpm --dir frontend exec vitest run \
  src/components/cameras/CameraWizard.test.tsx \
  src/pages/Live.test.tsx \
  src/pages/Incidents.test.tsx
```

Expected: fail until stream delivery profiles drive worker/browser routes.

- [ ] **Step 3: Implement stream delivery runtime fields**

Add `WorkerStreamDeliverySettings` to worker config with `profile_id`,
`profile_name`, `profile_hash`, `delivery_mode`, `public_base_url`, and
`edge_override_url`. Resolve it through the runtime configuration service.
Update playback URL builders so the profile controls WebRTC/HLS/MJPEG/native
selection and base URL, with bootstrap settings used only when no profile
exists.

- [ ] **Step 4: Wire UI selection and playback**

Camera Wizard should show named stream profiles and store the selected profile
reference in camera browser delivery/source configuration. Live and Evidence
Desk playback links should use API-provided URLs instead of re-deriving
environment-specific URLs in the browser.

- [ ] **Step 5: Run focused verification**

```bash
cd /Users/yann.moren/vision
corepack pnpm generate:api
cd /Users/yann.moren/vision/backend
python3 -m uv run pytest \
  tests/services/test_camera_worker_config.py \
  tests/api/test_prompt5_routes.py \
  -q
cd /Users/yann.moren/vision
corepack pnpm --dir frontend exec vitest run \
  src/components/cameras/CameraWizard.test.tsx \
  src/pages/Live.test.tsx \
  src/pages/Incidents.test.tsx
```

Expected: pass.

- [ ] **Step 6: Commit and push**

```bash
git add backend/src/argus/api/contracts.py \
  backend/src/argus/services/operator_configuration.py \
  backend/src/argus/services/app.py \
  backend/src/argus/inference/engine.py \
  backend/tests/services/test_camera_worker_config.py \
  backend/tests/api/test_prompt5_routes.py \
  frontend/src/components/cameras/CameraWizard.tsx \
  frontend/src/components/cameras/CameraWizard.test.tsx \
  frontend/src/pages/Live.tsx \
  frontend/src/pages/Live.test.tsx \
  frontend/src/pages/Incidents.tsx \
  frontend/src/pages/Incidents.test.tsx \
  frontend/src/lib/api.generated.ts
git commit -m "feat(streams): route browser delivery profiles"
git push origin codex/omnisight-ui-spec-implementation
```

## Task 13H: Runtime Selection Profile Consumption

**Files:**

- Modify: `backend/src/argus/api/contracts.py`
- Modify: `backend/src/argus/services/operator_configuration.py`
- Modify: `backend/src/argus/services/app.py`
- Modify: `backend/src/argus/vision/runtime_selection.py`
- Modify: `backend/src/argus/inference/engine.py`
- Test: `backend/tests/vision/test_runtime_selection.py`
- Test: `backend/tests/services/test_camera_worker_config.py`
- Test: `backend/tests/inference/test_engine.py`

- [ ] **Step 1: Add failing runtime selection tests**

Cover:

- a camera-bound profile with `preferred_backend="tensorrt_engine"` selects a
  compatible TensorRT artifact when present
- `artifact_preference="onnx_first"` prefers ONNX even when TensorRT exists
- `fallback_allowed=False` returns a worker startup error instead of silently
  falling back to dynamic `.pt`
- profile id/hash and fallback reason are included in runtime selection logs and
  worker config

- [ ] **Step 2: Run failing tests**

```bash
cd /Users/yann.moren/vision/backend
python3 -m uv run pytest \
  tests/vision/test_runtime_selection.py \
  tests/services/test_camera_worker_config.py \
  tests/inference/test_engine.py \
  -q
```

Expected: fail because runtime selection still follows existing artifact logic
without the UI-managed profile.

- [ ] **Step 3: Implement profile-aware runtime selection**

Add `WorkerRuntimeSelectionSettings` to worker config and pass it into
`select_runtime_artifact`. Keep existing automatic selection as the bootstrap
default. Enforce `fallback_allowed=False` at the selection boundary and return a
clear operator-visible error that names the profile and missing artifact.

- [ ] **Step 4: Run focused verification**

```bash
cd /Users/yann.moren/vision/backend
python3 -m uv run pytest \
  tests/vision/test_runtime_selection.py \
  tests/services/test_camera_worker_config.py \
  tests/inference/test_engine.py \
  -q
```

Expected: pass.

- [ ] **Step 5: Commit and push**

```bash
git add backend/src/argus/api/contracts.py \
  backend/src/argus/services/operator_configuration.py \
  backend/src/argus/services/app.py \
  backend/src/argus/vision/runtime_selection.py \
  backend/src/argus/inference/engine.py \
  backend/tests/vision/test_runtime_selection.py \
  backend/tests/services/test_camera_worker_config.py \
  backend/tests/inference/test_engine.py
git commit -m "feat(runtime): consume runtime selection profiles"
git push origin codex/omnisight-ui-spec-implementation
```

## Task 13I: Privacy Policy Runtime Consumption

**Files:**

- Create: `backend/src/argus/services/privacy_policy_runtime.py`
- Modify: `backend/src/argus/services/privacy_manifests.py`
- Modify: `backend/src/argus/services/incident_capture.py`
- Modify: `backend/src/argus/services/app.py`
- Modify: `backend/src/argus/api/contracts.py`
- Test: `backend/tests/services/test_privacy_manifests.py`
- Test: `backend/tests/services/test_incident_capture.py`
- Test: `backend/tests/services/test_operator_configuration.py`
- Modify: `frontend/src/components/configuration/ProfileEditor.tsx`
- Modify: `frontend/src/components/configuration/ProfileEditor.test.tsx`

- [ ] **Step 1: Add failing privacy runtime tests**

Cover:

- privacy manifest includes selected privacy profile id/hash
- retention days, storage quota bytes, plaintext plate posture, and residency
  come from the resolved `privacy_policy` profile
- `plaintext_plate_storage="blocked"` overrides tenant plaintext plate allowance
  for new incidents
- clip quota uses the privacy profile quota when present
- residency mismatch between privacy policy and evidence storage profile fails
  worker config with a clear error

- [ ] **Step 2: Run failing tests**

```bash
cd /Users/yann.moren/vision/backend
python3 -m uv run pytest \
  tests/services/test_privacy_manifests.py \
  tests/services/test_incident_capture.py \
  tests/services/test_operator_configuration.py \
  -q
cd /Users/yann.moren/vision
corepack pnpm --dir frontend exec vitest run src/components/configuration/ProfileEditor.test.tsx
```

Expected: fail until privacy profiles are consumed by manifests and capture.

- [ ] **Step 3: Implement privacy policy runtime resolver**

Create a resolver that turns the selected `privacy_policy` profile into a
runtime policy object. Feed it into privacy manifest generation and incident
capture quota checks. Store profile id/hash in the manifest JSON and scene
contract. Keep tenant settings as bootstrap defaults only.

- [ ] **Step 4: Add retention/expiry behavior**

Add a service method that marks expired artifacts as `expired` and writes an
evidence ledger entry when retention days are exceeded. Do not delete bytes in
the first pass; physical cleanup can be a separate operator action after expiry
is visible.

- [ ] **Step 5: Run focused verification**

```bash
cd /Users/yann.moren/vision/backend
python3 -m uv run pytest \
  tests/services/test_privacy_manifests.py \
  tests/services/test_incident_capture.py \
  tests/services/test_operator_configuration.py \
  -q
cd /Users/yann.moren/vision
corepack pnpm --dir frontend exec vitest run src/components/configuration/ProfileEditor.test.tsx
```

Expected: pass.

- [ ] **Step 6: Commit and push**

```bash
git add backend/src/argus/services/privacy_policy_runtime.py \
  backend/src/argus/services/privacy_manifests.py \
  backend/src/argus/services/incident_capture.py \
  backend/src/argus/services/app.py \
  backend/src/argus/api/contracts.py \
  backend/tests/services/test_privacy_manifests.py \
  backend/tests/services/test_incident_capture.py \
  backend/tests/services/test_operator_configuration.py \
  frontend/src/components/configuration/ProfileEditor.tsx \
  frontend/src/components/configuration/ProfileEditor.test.tsx
git commit -m "feat(privacy): consume privacy policy profiles"
git push origin codex/omnisight-ui-spec-implementation
```

## Task 13J: LLM Provider Runtime Consumption

**Files:**

- Create: `backend/src/argus/services/llm_provider_runtime.py`
- Modify: `backend/src/argus/services/operator_configuration.py`
- Modify: `backend/src/argus/llm/parser.py`
- Modify: `backend/src/argus/api/contracts.py`
- Test: `backend/tests/services/test_llm_provider_runtime.py`
- Test: `backend/tests/api/test_configuration_routes.py`
- Modify: `docs/runbook.md`

- [ ] **Step 1: Add failing LLM provider tests**

Cover:

- resolving an `llm_provider` profile returns provider, model, base URL, profile
  id/hash, and decrypted API key only to service code
- browser configuration responses expose only secret presence
- existing LLM parser construction uses the selected profile when a tenant or
  camera binding exists
- missing required API key returns a validation error before a prompt request is
  sent

- [ ] **Step 2: Run failing tests**

```bash
cd /Users/yann.moren/vision/backend
python3 -m uv run pytest \
  tests/services/test_llm_provider_runtime.py \
  tests/api/test_configuration_routes.py \
  -q
```

Expected: fail until LLM provider profiles are runtime-consumed.

- [ ] **Step 3: Implement LLM provider resolver**

Create a service-only resolver that converts `llm_provider` profiles into the
settings needed by `argus.llm.parser`. Keep environment values as bootstrap
defaults. Ensure Prompt-To-Policy in Task 18 calls this resolver instead of
reading provider/model/API key from process settings.

- [ ] **Step 4: Update docs**

Document that LLM provider configuration is UI-managed after bootstrap, secrets
are write-only in browser responses, and prompt workflows fail closed when the
selected provider is invalid.

- [ ] **Step 5: Run focused verification**

```bash
cd /Users/yann.moren/vision/backend
python3 -m uv run pytest \
  tests/services/test_llm_provider_runtime.py \
  tests/api/test_configuration_routes.py \
  -q
git diff --check -- docs/runbook.md
```

Expected: pass.

- [ ] **Step 6: Commit and push**

```bash
git add backend/src/argus/services/llm_provider_runtime.py \
  backend/src/argus/services/operator_configuration.py \
  backend/src/argus/llm/parser.py \
  backend/src/argus/api/contracts.py \
  backend/tests/services/test_llm_provider_runtime.py \
  backend/tests/api/test_configuration_routes.py \
  docs/runbook.md
git commit -m "feat(llm): consume provider configuration profiles"
git push origin codex/omnisight-ui-spec-implementation
```

## Task 14: Optional Still Snapshot Evidence Artifacts

**Files:**

- Modify: `backend/src/argus/api/contracts.py`
- Modify: `backend/src/argus/models/enums.py`
- Modify: `backend/src/argus/services/incident_capture.py`
- Modify: `backend/src/argus/services/evidence_storage.py`
- Modify: `backend/src/argus/services/evidence_ledger.py`
- Modify: `backend/src/argus/services/app.py`
- Modify: `backend/tests/services/test_incident_capture.py`
- Modify: `backend/tests/services/test_evidence_storage.py`
- Modify: `frontend/src/pages/Incidents.tsx`
- Modify: `frontend/src/pages/Incidents.test.tsx`

- [ ] **Step 1: Add failing backend tests**

Cover:

- `EvidenceRecordingPolicy(snapshot_enabled=True)` produces a `snapshot`
  artifact when a frame is available
- disabled snapshots leave `snapshot_url` null and create no snapshot artifact
- snapshot quota and encode failures write ledger entries
- clip capture still succeeds when snapshot capture fails

- [ ] **Step 2: Run failing backend tests**

```bash
cd /Users/yann.moren/vision/backend
python3 -m uv run pytest \
  tests/services/test_incident_capture.py \
  tests/services/test_evidence_storage.py \
  -q
```

Expected: fail until snapshot policy/artifacts are implemented.

- [ ] **Step 3: Implement snapshot artifacts**

Add policy fields:

- `snapshot_enabled: bool = False`
- `snapshot_offset_seconds: float = 0.0`
- `snapshot_quality: int = 85`

Add evidence artifact kind `snapshot`. On incident finalize, write one JPEG
snapshot artifact only when enabled. Keep `incidents.snapshot_url` nullable and
preserve clip behavior.

- [ ] **Step 4: Add frontend coverage**

Update Evidence Desk to display snapshot artifact availability as optional
evidence, not as a missing-data error when disabled.

- [ ] **Step 5: Run tests**

```bash
cd /Users/yann.moren/vision/backend
python3 -m uv run pytest tests/services/test_incident_capture.py tests/services/test_evidence_storage.py -q
cd /Users/yann.moren/vision
corepack pnpm --dir frontend exec vitest run src/pages/Incidents.test.tsx
```

Expected: pass.

- [ ] **Step 6: Commit and push**

```bash
git add backend/src/argus/api/contracts.py \
  backend/src/argus/models/enums.py \
  backend/src/argus/services/incident_capture.py \
  backend/src/argus/services/evidence_storage.py \
  backend/src/argus/services/evidence_ledger.py \
  backend/src/argus/services/app.py \
  backend/tests/services/test_incident_capture.py \
  backend/tests/services/test_evidence_storage.py \
  frontend/src/pages/Incidents.tsx \
  frontend/src/pages/Incidents.test.tsx
git commit -m "feat(evidence): support optional snapshot artifacts"
git push origin codex/omnisight-ui-spec-implementation
```

## Task 15: Runtime Passport Snapshots

**Files:**

- Modify: `backend/src/argus/models/enums.py`
- Modify: `backend/src/argus/models/tables.py`
- Create: `backend/src/argus/migrations/versions/0016_runtime_passports.py`
- Create: `backend/src/argus/services/runtime_passports.py`
- Modify: `backend/src/argus/services/scene_contracts.py`
- Modify: `backend/src/argus/services/app.py`
- Test: `backend/tests/services/test_runtime_passports.py`
- Test: `backend/tests/core/test_db.py`

- [ ] **Step 1: Add failing passport tests**

Cover deterministic passport hashes for:

- fixed-vocab ONNX selection
- fixed-vocab TensorRT artifact selection
- compiled open-vocab scene artifact selection
- dynamic `.pt` fallback with `fallback_reason`
- provider/library version changes
- selected `runtime_selection` profile id/hash from Task 13H

- [ ] **Step 2: Run failing tests**

```bash
cd /Users/yann.moren/vision/backend
python3 -m uv run pytest tests/services/test_runtime_passports.py tests/core/test_db.py -q
```

Expected: fail until passport model and service exist.

- [ ] **Step 3: Implement runtime passport snapshots**

Create `runtime_passport_snapshots` with immutable JSON and `passport_hash`.
Build passports from scene contract runtime sections, runtime artifact records,
worker selection reports, selected runtime-selection profile id/hash, and model
metadata. Attach passport ids/hashes to incidents when runtime context is
available.

- [ ] **Step 4: Run tests**

```bash
cd /Users/yann.moren/vision/backend
python3 -m uv run pytest tests/services/test_runtime_passports.py tests/core/test_db.py -q
```

Expected: pass.

- [ ] **Step 5: Commit and push**

```bash
git add backend/src/argus/models/enums.py \
  backend/src/argus/models/tables.py \
  backend/src/argus/migrations/versions/0016_runtime_passports.py \
  backend/src/argus/services/runtime_passports.py \
  backend/src/argus/services/scene_contracts.py \
  backend/src/argus/services/app.py \
  backend/tests/services/test_runtime_passports.py \
  backend/tests/core/test_db.py
git commit -m "feat(runtime): add incident runtime passports"
git push origin codex/omnisight-ui-spec-implementation
```

## Task 16: Runtime Passport API And UI

**Files:**

- Modify: `backend/src/argus/api/contracts.py`
- Modify: `backend/src/argus/api/v1/incidents.py`
- Modify: `backend/src/argus/api/v1/operations.py`
- Modify: `backend/tests/api/test_prompt9_routes.py`
- Modify: `backend/tests/api/test_operations_endpoints.py`
- Modify: `frontend/src/lib/api.generated.ts`
- Create: `frontend/src/components/evidence/RuntimePassportPanel.tsx`
- Create: `frontend/src/components/evidence/RuntimePassportPanel.test.tsx`
- Modify: `frontend/src/pages/Incidents.tsx`
- Modify: `frontend/src/pages/Settings.tsx`

- [ ] **Step 1: Add failing API/UI tests**

Cover:

- `GET /api/v1/incidents/{incident_id}/runtime-passport`
- incident response passport summary
- Operations camera row passport status
- UI renders backend, model hash, runtime artifact hash, target profile,
  precision, validation timestamp, selected runtime profile, and fallback reason

- [ ] **Step 2: Run failing tests**

```bash
cd /Users/yann.moren/vision/backend
python3 -m uv run pytest tests/api/test_prompt9_routes.py tests/api/test_operations_endpoints.py -q
cd /Users/yann.moren/vision
corepack pnpm --dir frontend exec vitest run src/components/evidence/RuntimePassportPanel.test.tsx
```

Expected: fail until API and UI are wired.

- [ ] **Step 3: Implement passport routes and UI**

Expose passport summaries in incident and operations payloads. Generate OpenAPI
types and add `RuntimePassportPanel` to Evidence Desk and Operations without
adding decorative cards inside cards.

- [ ] **Step 4: Run tests and type generation**

```bash
cd /Users/yann.moren/vision
corepack pnpm generate:api
cd /Users/yann.moren/vision/backend
python3 -m uv run pytest tests/api/test_prompt9_routes.py tests/api/test_operations_endpoints.py -q
cd /Users/yann.moren/vision
corepack pnpm --dir frontend exec vitest run src/components/evidence/RuntimePassportPanel.test.tsx src/pages/Incidents.test.tsx src/pages/Settings.test.tsx
```

Expected: pass.

- [ ] **Step 5: Commit and push**

```bash
git add backend/src/argus/api/contracts.py \
  backend/src/argus/api/v1/incidents.py \
  backend/src/argus/api/v1/operations.py \
  backend/tests/api/test_prompt9_routes.py \
  backend/tests/api/test_operations_endpoints.py \
  frontend/src/lib/api.generated.ts \
  frontend/src/components/evidence/RuntimePassportPanel.tsx \
  frontend/src/components/evidence/RuntimePassportPanel.test.tsx \
  frontend/src/pages/Incidents.tsx \
  frontend/src/pages/Settings.tsx \
  frontend/src/pages/Incidents.test.tsx \
  frontend/src/pages/Settings.test.tsx
git commit -m "feat(ui): surface runtime passports"
git push origin codex/omnisight-ui-spec-implementation
```

## Task 16A: Incident Rule Data Contract, Service, And API

**Files:**

- Modify: `backend/src/argus/models/enums.py`
- Modify: `backend/src/argus/models/tables.py`
- Create: `backend/src/argus/migrations/versions/0017_detection_rule_incident_metadata.py`
- Modify: `backend/src/argus/api/contracts.py`
- Create: `backend/src/argus/services/incident_rules.py`
- Create: `backend/src/argus/api/v1/incident_rules.py`
- Modify: `backend/src/argus/main.py`
- Test: `backend/tests/services/test_incident_rules.py`
- Test: `backend/tests/api/test_incident_rule_routes.py`
- Test: `backend/tests/core/test_db.py`

- [ ] **Step 1: Add failing service, route, and DB tests**

Cover:

- migration adds `enabled`, `incident_type`, `severity`, `description`,
  `rule_hash`, `created_at`, and `updated_at` to `detection_rules`
- existing rows are backfilled with enabled rules, warning severity, stable
  incident type slugs, and deterministic hashes
- admin can list/create/update/delete incident rules for a camera in their
  tenant
- viewer cannot mutate rules
- cross-tenant camera/rule access returns `404`
- rule names and incident type slugs are unique per camera
- rule predicates reject unknown classes, unknown zones, invalid confidence, and
  unsupported attribute values
- validation/dry-run evaluates a sample detection against the candidate rule
- browser responses and audit entries redact webhook URL secrets while still
  exposing webhook presence

- [ ] **Step 2: Run failing tests**

```bash
cd /Users/yann.moren/vision/backend
python3 -m uv run pytest \
  tests/services/test_incident_rules.py \
  tests/api/test_incident_rule_routes.py \
  tests/core/test_db.py \
  -q
```

Expected: fail until contracts, service, routes, and migration exist.

- [ ] **Step 3: Add incident rule contracts and migration**

Add contracts:

- `IncidentRulePredicate`
- `IncidentRuleCreate`
- `IncidentRuleUpdate`
- `IncidentRuleResponse`
- `IncidentRuleValidationRequest`
- `IncidentRuleValidationResponse`

Extend `DetectionRule` with:

- `enabled: bool`
- `incident_type: str`
- `severity: str`
- `description: str | None`
- `rule_hash: str`
- timestamps

Keep the existing `predicate`, `action`, `zone_id`, `webhook_url`, and
`cooldown_seconds` columns so old rows and the current rule engine shape migrate
forward instead of moving to a second table.

- [ ] **Step 4: Implement service and routes**

Create camera-scoped routes:

```text
GET /api/v1/cameras/{camera_id}/incident-rules
POST /api/v1/cameras/{camera_id}/incident-rules
GET /api/v1/cameras/{camera_id}/incident-rules/{rule_id}
PATCH /api/v1/cameras/{camera_id}/incident-rules/{rule_id}
DELETE /api/v1/cameras/{camera_id}/incident-rules/{rule_id}
POST /api/v1/cameras/{camera_id}/incident-rules/validate
```

Service behavior:

- load cameras through the tenant-owned site relationship
- validate predicates against camera `active_classes`, runtime vocabulary
  terms, `zones`, and supported attribute keys
- normalize incident type slugs to lowercase snake-case
- compute deterministic rule hashes from enabled state, incident type, severity,
  predicate, action, cooldown, webhook presence, and zone id
- redact webhook URLs from browser responses and audit payloads
- audit `incident_rule.create`, `incident_rule.update`, and
  `incident_rule.delete`

- [ ] **Step 5: Run migration and tests**

```bash
cd /Users/yann.moren/vision/backend
python3 -m uv run alembic upgrade head
python3 -m uv run pytest \
  tests/services/test_incident_rules.py \
  tests/api/test_incident_rule_routes.py \
  tests/core/test_db.py \
  -q
python3 -m uv run ruff check src/argus/services/incident_rules.py src/argus/api/v1/incident_rules.py tests/services/test_incident_rules.py tests/api/test_incident_rule_routes.py
```

Expected: pass.

- [ ] **Step 6: Commit and push**

```bash
git add backend/src/argus/models/enums.py \
  backend/src/argus/models/tables.py \
  backend/src/argus/migrations/versions/0017_detection_rule_incident_metadata.py \
  backend/src/argus/api/contracts.py \
  backend/src/argus/services/incident_rules.py \
  backend/src/argus/api/v1/incident_rules.py \
  backend/src/argus/main.py \
  backend/tests/services/test_incident_rules.py \
  backend/tests/api/test_incident_rule_routes.py \
  backend/tests/core/test_db.py
git commit -m "feat(rules): add per-scene incident rule API"
git push origin codex/omnisight-ui-spec-implementation
```

## Task 16B: Worker Incident Rule Runtime Consumption

**Files:**

- Modify: `backend/src/argus/api/contracts.py`
- Modify: `backend/src/argus/services/app.py`
- Modify: `backend/src/argus/services/scene_contracts.py`
- Modify: `backend/src/argus/inference/engine.py`
- Modify: `backend/src/argus/vision/rules.py`
- Create: `backend/src/argus/services/rule_events.py`
- Test: `backend/tests/services/test_camera_worker_config.py`
- Test: `backend/tests/services/test_scene_contracts.py`
- Test: `backend/tests/vision/test_rules.py`
- Test: `backend/tests/inference/test_engine.py`
- Test: `backend/tests/inference/test_engine_config_loading.py`

- [ ] **Step 1: Add failing worker/runtime tests**

Cover:

- `WorkerConfigResponse` includes only enabled incident rules for the camera
- scene contracts include deterministic enabled rule summaries and rule hashes
- worker config JSON validates into `EngineConfig.incident_rules`
- `RuleEngine` emits event records containing rule id, incident type, severity,
  action, cooldown, rule hash, predicate, and detection payload
- `InferenceEngine` converts non-count rule events into
  `IncidentTriggeredEvent(type=f"rule.{incident_type}")`
- generated incident payloads include trigger rule name, id, severity, action,
  cooldown, predicate, detection, and rule hash
- camera command messages hot-reload incident rules in a running worker
- disabled rules and `count` actions do not create incidents

- [ ] **Step 2: Run failing tests**

```bash
cd /Users/yann.moren/vision/backend
python3 -m uv run pytest \
  tests/services/test_camera_worker_config.py \
  tests/services/test_scene_contracts.py \
  tests/vision/test_rules.py \
  tests/inference/test_engine_config_loading.py \
  tests/inference/test_engine.py \
  -q
```

Expected: fail until worker config and rule runtime are wired.

- [ ] **Step 3: Add worker contracts and command payloads**

Add:

- `WorkerIncidentRulePredicate`
- `WorkerIncidentRule`
- `TriggerRuleSummary`

Extend:

- `WorkerConfigResponse.incident_rules`
- `CameraCommandPayload.incident_rules`
- `EngineConfig.incident_rules`
- `CameraCommand.incident_rules`

Keep rule payloads redacted: webhook URL may be present only where the worker
needs it; browser responses should expose webhook presence, not secrets.

- [ ] **Step 4: Build runtime rule engine from persisted rules**

Update worker startup so `run_engine_for_camera` builds a real `RuleEngine`
from `config.incident_rules` when no test rule engine is injected. Add a
database-backed rule event store that writes `rule_events` rows without blocking
the frame loop.

Update `RuleEngine` with:

- `replace_rules(rules: list[RuleDefinition])`
- `RuleDefinition.incident_type`
- `RuleDefinition.severity`
- `RuleDefinition.rule_hash`
- event payloads that include trigger rule metadata

Update camera command handling so rule edits hot-reload without a process
restart.

- [ ] **Step 5: Attach rule hashes to contracts and incidents**

Update scene contract compilation to include enabled incident rules as a stable
ordered list of rule hashes and redacted summaries. Update
`_rule_events_to_incidents` so Evidence receives the operator-defined incident
type and trigger rule summary.

- [ ] **Step 6: Run backend validation**

```bash
cd /Users/yann.moren/vision/backend
python3 -m uv run alembic upgrade head
python3 -m uv run pytest \
  tests/services/test_camera_worker_config.py \
  tests/services/test_scene_contracts.py \
  tests/vision/test_rules.py \
  tests/inference/test_engine_config_loading.py \
  tests/inference/test_engine.py \
  -q
python3 -m uv run ruff check src/argus/inference/engine.py src/argus/vision/rules.py src/argus/services/app.py src/argus/services/rule_events.py
```

Expected: pass.

- [ ] **Step 7: Commit and push**

```bash
git add backend/src/argus/api/contracts.py \
  backend/src/argus/services/app.py \
  backend/src/argus/services/scene_contracts.py \
  backend/src/argus/inference/engine.py \
  backend/src/argus/vision/rules.py \
  backend/src/argus/services/rule_events.py \
  backend/tests/services/test_camera_worker_config.py \
  backend/tests/services/test_scene_contracts.py \
  backend/tests/vision/test_rules.py \
  backend/tests/inference/test_engine.py \
  backend/tests/inference/test_engine_config_loading.py
git commit -m "feat(worker): consume per-scene incident rules"
git push origin codex/omnisight-ui-spec-implementation
```

## Task 16C: Control Scenes Incident Rule Builder

**Files:**

- Modify: `frontend/src/lib/api.generated.ts`
- Create: `frontend/src/hooks/use-incident-rules.ts`
- Create: `frontend/src/components/cameras/IncidentRulesPanel.tsx`
- Create: `frontend/src/components/cameras/IncidentRulesPanel.test.tsx`
- Modify: `frontend/src/pages/Cameras.tsx`
- Modify: `frontend/src/pages/Cameras.test.tsx`

- [ ] **Step 1: Add failing UI tests**

Cover:

- Scenes inventory exposes a `Rules` action per scene row
- selecting `Rules` opens a camera-scoped rule builder in Control -> Scenes
- rule list shows enabled state, incident type, severity, action, cooldown, and
  rule hash prefix
- form can create and edit class, zone, confidence, severity, action, cooldown,
  webhook presence, and enabled state
- validation errors use `role="alert"` and are not color-only
- dry-run/validate shows match/no-match feedback
- successful save invalidates the camera rule query and leaves unrelated camera
  edits untouched

- [ ] **Step 2: Run failing UI tests**

```bash
cd /Users/yann.moren/vision
corepack pnpm generate:api
corepack pnpm --dir frontend exec vitest run \
  src/components/cameras/IncidentRulesPanel.test.tsx \
  src/pages/Cameras.test.tsx
```

Expected: fail until hooks and UI exist.

- [ ] **Step 3: Implement hooks and rule builder**

Use the UI/UX placement decision:

- primary authoring lives in Control -> Scenes
- Operations remains read-only runtime truth
- Evidence remains review and provenance

Build `IncidentRulesPanel` with a dense operational layout:

- class multi-select seeded from camera active classes and runtime vocabulary
- zone selector seeded from camera zones
- confidence slider/input with stable dimensions
- severity select
- action segmented control for `alert`, `record_clip`, and `webhook`
- cooldown number input
- enabled toggle
- validate button with loading state
- create, save, and delete actions with accessible labels

Use lucide icons where actions benefit from icons. Keep text compact; this is a
control surface, not a landing page.

- [ ] **Step 4: Integrate into Scenes page**

Add a `Rules` action next to `Edit` and `Delete` in the scene table. Opening it
should select that camera and render the rule builder below the table, using the
same workspace surface language as the existing scene wizard.

If a scene has no saved zones or active classes, keep the panel usable and show
validation feedback from the API instead of blocking the route client-side.

- [ ] **Step 5: Run frontend validation**

```bash
cd /Users/yann.moren/vision
corepack pnpm generate:api
corepack pnpm --dir frontend exec vitest run \
  src/components/cameras/IncidentRulesPanel.test.tsx \
  src/pages/Cameras.test.tsx
corepack pnpm --dir frontend exec tsc -b
```

Expected: pass.

- [ ] **Step 6: Commit and push**

```bash
git add frontend/src/lib/api.generated.ts \
  frontend/src/hooks/use-incident-rules.ts \
  frontend/src/components/cameras/IncidentRulesPanel.tsx \
  frontend/src/components/cameras/IncidentRulesPanel.test.tsx \
  frontend/src/pages/Cameras.tsx \
  frontend/src/pages/Cameras.test.tsx
git commit -m "feat(ui): add scene incident rule builder"
git push origin codex/omnisight-ui-spec-implementation
```

## Task 16D: Evidence And Operations Rule Provenance

**Files:**

- Modify: `backend/src/argus/api/contracts.py`
- Modify: `backend/src/argus/api/v1/incidents.py`
- Modify: `backend/src/argus/api/v1/operations.py`
- Modify: `backend/src/argus/services/app.py`
- Modify: `backend/src/argus/services/evidence_ledger.py`
- Modify: `frontend/src/lib/api.generated.ts`
- Create: `frontend/src/components/evidence/IncidentRuleSummary.tsx`
- Create: `frontend/src/components/evidence/IncidentRuleSummary.test.tsx`
- Modify: `frontend/src/pages/Incidents.tsx`
- Modify: `frontend/src/pages/Incidents.test.tsx`
- Modify: `frontend/src/components/operations/SceneIntelligenceMatrix.tsx`
- Modify: `frontend/src/components/operations/SceneIntelligenceMatrix.test.tsx`
- Modify: `frontend/src/pages/Settings.tsx`
- Modify: `frontend/src/pages/Settings.test.tsx`
- Test: `backend/tests/api/test_prompt9_routes.py`
- Test: `backend/tests/api/test_operations_endpoints.py`
- Test: `backend/tests/services/test_evidence_ledger.py`

- [ ] **Step 1: Add failing API and UI tests**

Cover:

- incident responses expose `trigger_rule` when the payload contains rule
  metadata
- incident ledger writes an `incident_rule.attached` entry with rule hash,
  incident type, action, and severity for rule-generated incidents
- Operations rows show active rule count, effective rule hash, and latest rule
  load status when known
- Evidence Desk shows rule name, type, severity, action, cooldown, rule hash,
  detection class, zone, and confidence
- Evidence filter still uses incident type values such as
  `rule.restricted_person`

- [ ] **Step 2: Run failing tests**

```bash
cd /Users/yann.moren/vision/backend
python3 -m uv run pytest \
  tests/api/test_prompt9_routes.py \
  tests/api/test_operations_endpoints.py \
  tests/services/test_evidence_ledger.py \
  -q
cd /Users/yann.moren/vision
corepack pnpm generate:api
corepack pnpm --dir frontend exec vitest run \
  src/components/evidence/IncidentRuleSummary.test.tsx \
  src/components/operations/SceneIntelligenceMatrix.test.tsx \
  src/pages/Incidents.test.tsx \
  src/pages/Settings.test.tsx
```

Expected: fail until provenance fields and UI surfaces are wired.

- [ ] **Step 3: Add trigger rule summaries**

Add a `TriggerRuleSummary` response contract and populate it from incident
payloads. Do not require a live join for old incidents; if the payload has a
rule summary, render it. If the rule was later deleted, Evidence should still
show the captured summary.

Add `incident_rule.attached` to the evidence ledger enum and write it during
incident finalize when trigger rule metadata exists.

- [ ] **Step 4: Add Operations runtime rule truth**

Operations should show read-only truth:

- configured active rule count
- effective combined rule hash
- last rule event timestamp when available
- rule-load status: `loaded`, `stale`, `unknown`, or `not_configured`

This belongs in Operations because it answers whether the worker is running the
rules, not because Operations owns rule authoring.

- [ ] **Step 5: Add Evidence trigger rule UI**

Add `IncidentRuleSummary` to Evidence Desk near the Case Context Strip or
accountability details. Keep it compact and factual. The user should be able to
see what rule created the incident without opening raw payload JSON.

- [ ] **Step 6: Run validation**

```bash
cd /Users/yann.moren/vision/backend
python3 -m uv run alembic upgrade head
python3 -m uv run pytest \
  tests/api/test_prompt9_routes.py \
  tests/api/test_operations_endpoints.py \
  tests/services/test_evidence_ledger.py \
  -q
cd /Users/yann.moren/vision
corepack pnpm generate:api
corepack pnpm --dir frontend exec vitest run \
  src/components/evidence/IncidentRuleSummary.test.tsx \
  src/components/operations/SceneIntelligenceMatrix.test.tsx \
  src/pages/Incidents.test.tsx \
  src/pages/Settings.test.tsx
corepack pnpm --dir frontend exec tsc -b
```

Expected: pass.

- [ ] **Step 7: Commit and push**

```bash
git add backend/src/argus/api/contracts.py \
  backend/src/argus/api/v1/incidents.py \
  backend/src/argus/api/v1/operations.py \
  backend/src/argus/services/app.py \
  backend/src/argus/services/evidence_ledger.py \
  backend/tests/api/test_prompt9_routes.py \
  backend/tests/api/test_operations_endpoints.py \
  backend/tests/services/test_evidence_ledger.py \
  frontend/src/lib/api.generated.ts \
  frontend/src/components/evidence/IncidentRuleSummary.tsx \
  frontend/src/components/evidence/IncidentRuleSummary.test.tsx \
  frontend/src/pages/Incidents.tsx \
  frontend/src/pages/Incidents.test.tsx \
  frontend/src/components/operations/SceneIntelligenceMatrix.tsx \
  frontend/src/components/operations/SceneIntelligenceMatrix.test.tsx \
  frontend/src/pages/Settings.tsx \
  frontend/src/pages/Settings.test.tsx
git commit -m "feat(evidence): show incident rule provenance"
git push origin codex/omnisight-ui-spec-implementation
```

## Task 16E: Incident Rule Band Validation And Docs

**Files:**

- Modify: `docs/runbook.md`
- Modify: `docs/operator-deployment-playbook.md`
- Modify: `docs/superpowers/specs/2026-05-11-accountable-scene-intelligence-and-evidence-recording-design.md`
- Modify: `docs/superpowers/plans/2026-05-11-accountable-scene-intelligence-and-evidence-recording-implementation-plan.md`
- Modify: `docs/superpowers/status/2026-05-12-next-chat-accountable-scene-task14-handoff.md`

- [ ] **Step 1: Update operator docs**

Document:

- incident rules live in Control -> Scenes
- Operations shows worker rule consumption and readiness
- Evidence shows the trigger rule summary after a rule fires
- `record_clip` is the default incident action for reviewable evidence, while
  recording policy and storage profile still decide which artifacts are
  captured and where they are stored
- edge/local-first deployments remain reviewable when recording is enabled
- Prompt-To-Policy may propose rule changes later, but rules are not auto-applied

- [ ] **Step 2: Run full targeted backend validation for the band**

```bash
cd /Users/yann.moren/vision/backend
python3 -m uv run alembic upgrade head
python3 -m uv run pytest \
  tests/services/test_incident_rules.py \
  tests/api/test_incident_rule_routes.py \
  tests/services/test_camera_worker_config.py \
  tests/services/test_scene_contracts.py \
  tests/vision/test_rules.py \
  tests/inference/test_engine_config_loading.py \
  tests/inference/test_engine.py \
  tests/api/test_prompt9_routes.py \
  tests/api/test_operations_endpoints.py \
  tests/services/test_evidence_ledger.py \
  tests/core/test_db.py \
  -q
python3 -m uv run ruff check src tests
```

Expected: pass, or record exact unrelated pre-existing failures in the handoff.

- [ ] **Step 3: Run full targeted frontend validation for the band**

```bash
cd /Users/yann.moren/vision
corepack pnpm generate:api
corepack pnpm --dir frontend exec vitest run \
  src/components/cameras/IncidentRulesPanel.test.tsx \
  src/components/evidence/IncidentRuleSummary.test.tsx \
  src/components/operations/SceneIntelligenceMatrix.test.tsx \
  src/pages/Cameras.test.tsx \
  src/pages/Incidents.test.tsx \
  src/pages/Settings.test.tsx
corepack pnpm --dir frontend exec tsc -b
```

Expected: pass.

- [ ] **Step 4: Refresh handoff**

Update the handoff so the next chat starts with Task 17 only after Task 16A-16E
are implemented, validated, committed, and pushed.

- [ ] **Step 5: Commit and push**

```bash
git add docs/runbook.md \
  docs/operator-deployment-playbook.md \
  docs/superpowers/specs/2026-05-11-accountable-scene-intelligence-and-evidence-recording-design.md \
  docs/superpowers/plans/2026-05-11-accountable-scene-intelligence-and-evidence-recording-implementation-plan.md \
  docs/superpowers/status/2026-05-12-next-chat-accountable-scene-task14-handoff.md
git commit -m "docs(rules): document per-worker incident rule validation"
git push origin codex/omnisight-ui-spec-implementation
```

## Task 17: Operational Memory

**Files:**

- Modify: `backend/src/argus/models/tables.py`
- Create: `backend/src/argus/migrations/versions/0018_operational_memory_patterns.py`
- Create: `backend/src/argus/services/operational_memory.py`
- Modify: `backend/src/argus/api/contracts.py`
- Modify: `backend/src/argus/api/v1/operations.py`
- Test: `backend/tests/services/test_operational_memory.py`
- Test: `backend/tests/api/test_operations_endpoints.py`
- Create: `frontend/src/components/evidence/OperationalMemoryPanel.tsx`
- Create: `frontend/src/components/evidence/OperationalMemoryPanel.test.tsx`
- Modify: `frontend/src/pages/Incidents.tsx`
- Modify: `frontend/src/pages/Settings.tsx`

- [ ] **Step 1: Add failing memory tests**

Cover:

- repeated event bursts by site/camera/zone/class/time window
- repeated clip/storage failures by provider and edge node
- zone hot spots after scene contract changes
- pattern records cite source incident ids and contract hashes

- [ ] **Step 2: Run failing backend tests**

```bash
cd /Users/yann.moren/vision/backend
python3 -m uv run pytest tests/services/test_operational_memory.py -q
```

Expected: fail until the service exists.

- [ ] **Step 3: Implement pattern detection and API**

Persist `operational_memory_patterns` with `pattern_hash`, source incident ids,
source contract hashes, time window, severity, and summary. Expose current
patterns through Operations and selected incident context.

- [ ] **Step 4: Implement UI cards**

Show observed patterns with source citations in Evidence Desk and Operations.
Avoid predictive wording; use "observed pattern" language.

- [ ] **Step 5: Run tests**

```bash
cd /Users/yann.moren/vision/backend
python3 -m uv run pytest tests/services/test_operational_memory.py tests/api/test_operations_endpoints.py -q
cd /Users/yann.moren/vision
corepack pnpm generate:api
corepack pnpm --dir frontend exec vitest run \
  src/components/evidence/OperationalMemoryPanel.test.tsx \
  src/pages/Incidents.test.tsx \
  src/pages/Settings.test.tsx
```

Expected: pass.

- [ ] **Step 6: Commit and push**

```bash
git add backend/src/argus/models/tables.py \
  backend/src/argus/migrations/versions/0018_operational_memory_patterns.py \
  backend/src/argus/services/operational_memory.py \
  backend/src/argus/api/contracts.py \
  backend/src/argus/api/v1/operations.py \
  backend/tests/services/test_operational_memory.py \
  backend/tests/api/test_operations_endpoints.py \
  frontend/src/lib/api.generated.ts \
  frontend/src/components/evidence/OperationalMemoryPanel.tsx \
  frontend/src/components/evidence/OperationalMemoryPanel.test.tsx \
  frontend/src/pages/Incidents.tsx \
  frontend/src/pages/Settings.tsx \
  frontend/src/pages/Incidents.test.tsx \
  frontend/src/pages/Settings.test.tsx
git commit -m "feat(operations): add operational memory patterns"
git push origin codex/omnisight-ui-spec-implementation
```

## Task 18: Prompt-To-Policy Drafts

**Files:**

- Modify: `backend/src/argus/models/enums.py`
- Modify: `backend/src/argus/models/tables.py`
- Create: `backend/src/argus/migrations/versions/0019_policy_drafts.py`
- Create: `backend/src/argus/services/policy_drafts.py`
- Modify: `backend/src/argus/services/llm_provider_runtime.py`
- Create: `backend/src/argus/api/v1/policy_drafts.py`
- Modify: `backend/src/argus/main.py`
- Test: `backend/tests/services/test_policy_drafts.py`
- Test: `backend/tests/api/test_policy_draft_routes.py`
- Create: `frontend/src/components/policy/PolicyDraftReview.tsx`
- Create: `frontend/src/components/policy/PolicyDraftReview.test.tsx`

- [ ] **Step 1: Add failing policy draft tests**

Cover:

- prompt creates a draft, not an applied camera change
- draft includes scene contract, privacy manifest, recording policy, vocabulary,
  detection region, and rule diffs when requested
- draft compilation resolves the selected `llm_provider` profile from Task 13J
  and records provider/model/profile hash in draft metadata
- approval applies through existing camera/scene update paths
- rejection does not apply changes
- proposal, approval, rejection, and application write ledger entries

- [ ] **Step 2: Run failing tests**

```bash
cd /Users/yann.moren/vision/backend
python3 -m uv run pytest tests/services/test_policy_drafts.py tests/api/test_policy_draft_routes.py -q
```

Expected: fail until policy draft service and routes exist.

- [ ] **Step 3: Implement backend draft workflow**

Create `policy_drafts` records with `status` values `draft`, `approved`,
`rejected`, and `applied`. The compiler must use `LLMProviderRuntimeResolver`
from Task 13J when LLM assistance is enabled, fail closed when the selected
provider is invalid, and keep deterministic rule-based parsing as the local
fallback. It must return a structured diff and require approval before applying.

- [ ] **Step 4: Implement draft review UI**

Add a prompt field and diff review surface in the relevant scene/camera workflow.
Use explicit Approve and Reject actions. Do not auto-apply prompt output.

- [ ] **Step 5: Run tests**

```bash
cd /Users/yann.moren/vision/backend
python3 -m uv run pytest tests/services/test_policy_drafts.py tests/api/test_policy_draft_routes.py -q
cd /Users/yann.moren/vision
corepack pnpm generate:api
corepack pnpm --dir frontend exec vitest run src/components/policy/PolicyDraftReview.test.tsx
```

Expected: pass.

- [ ] **Step 6: Commit and push**

```bash
git add backend/src/argus/models/enums.py \
  backend/src/argus/models/tables.py \
  backend/src/argus/migrations/versions/0019_policy_drafts.py \
  backend/src/argus/services/policy_drafts.py \
  backend/src/argus/services/llm_provider_runtime.py \
  backend/src/argus/api/v1/policy_drafts.py \
  backend/src/argus/main.py \
  backend/tests/services/test_policy_drafts.py \
  backend/tests/api/test_policy_draft_routes.py \
  frontend/src/lib/api.generated.ts \
  frontend/src/components/policy/PolicyDraftReview.tsx \
  frontend/src/components/policy/PolicyDraftReview.test.tsx
git commit -m "feat(policy): add prompt-to-policy drafts"
git push origin codex/omnisight-ui-spec-implementation
```

## Task 19: Identity-Light Cross-Camera Intelligence

**Files:**

- Modify: `backend/src/argus/models/tables.py`
- Create: `backend/src/argus/migrations/versions/0020_cross_camera_threads.py`
- Create: `backend/src/argus/services/cross_camera_threads.py`
- Modify: `backend/src/argus/api/contracts.py`
- Modify: `backend/src/argus/api/v1/incidents.py`
- Test: `backend/tests/services/test_cross_camera_threads.py`
- Test: `backend/tests/api/test_prompt9_routes.py`
- Create: `frontend/src/components/evidence/CrossCameraThreadPanel.tsx`
- Create: `frontend/src/components/evidence/CrossCameraThreadPanel.test.tsx`
- Modify: `frontend/src/pages/Incidents.tsx`

- [ ] **Step 1: Add failing correlation tests**

Cover:

- class, zone, direction, time, and topology correlation
- privacy manifest blocks disallowed non-biometric attributes
- no face ID, biometric identity, or persistent person id fields are produced
- thread records cite source incidents, manifest hashes, confidence, and
  rationale

- [ ] **Step 2: Run failing tests**

```bash
cd /Users/yann.moren/vision/backend
python3 -m uv run pytest tests/services/test_cross_camera_threads.py -q
```

Expected: fail until the thread service exists.

- [ ] **Step 3: Implement identity-light threads**

Create `cross_camera_threads` from privacy-allowed incident metadata only. Store
thread hash, source incident ids, privacy manifest hashes, confidence, and
rationale. Expose thread context on incident routes.

- [ ] **Step 4: Implement Evidence Desk panel**

Show thread context as a support panel with source incident citations and
privacy labels. Never label a thread as a person identity.

- [ ] **Step 5: Run tests**

```bash
cd /Users/yann.moren/vision/backend
python3 -m uv run pytest tests/services/test_cross_camera_threads.py tests/api/test_prompt9_routes.py -q
cd /Users/yann.moren/vision
corepack pnpm generate:api
corepack pnpm --dir frontend exec vitest run \
  src/components/evidence/CrossCameraThreadPanel.test.tsx \
  src/pages/Incidents.test.tsx
```

Expected: pass.

- [ ] **Step 6: Commit and push**

```bash
git add backend/src/argus/models/tables.py \
  backend/src/argus/migrations/versions/0020_cross_camera_threads.py \
  backend/src/argus/services/cross_camera_threads.py \
  backend/src/argus/api/contracts.py \
  backend/src/argus/api/v1/incidents.py \
  backend/tests/services/test_cross_camera_threads.py \
  backend/tests/api/test_prompt9_routes.py \
  frontend/src/lib/api.generated.ts \
  frontend/src/components/evidence/CrossCameraThreadPanel.tsx \
  frontend/src/components/evidence/CrossCameraThreadPanel.test.tsx \
  frontend/src/pages/Incidents.tsx \
  frontend/src/pages/Incidents.test.tsx
git commit -m "feat(evidence): add identity-light cross-camera threads"
git push origin codex/omnisight-ui-spec-implementation
```

## Task 20: Supervisor Operations Data Contract

**Files:**

- Modify: `backend/src/argus/models/enums.py`
- Modify: `backend/src/argus/models/tables.py`
- Create: `backend/src/argus/migrations/versions/0021_supervisor_operations.py`
- Create: `backend/src/argus/services/supervisor_operations.py`
- Modify: `backend/src/argus/services/runtime_configuration.py`
- Modify: `backend/src/argus/api/contracts.py`
- Modify: `backend/src/argus/api/v1/operations.py`
- Test: `backend/tests/services/test_supervisor_operations.py`
- Test: `backend/tests/api/test_operations_endpoints.py`
- Test: `backend/tests/core/test_db.py`

- [ ] **Step 1: Add failing supervisor contract tests**

Cover:

- persistent worker assignment/reassignment records
- per-worker runtime reports with heartbeat, runtime state, restart count,
  last error, runtime artifact id, and scene contract hash
- lifecycle request creation for Start, Stop, Restart, and Drain
- resolved `operations_mode` profile controls lifecycle owner, supervisor mode,
  and restart policy for each worker assignment
- no lifecycle route shells out from the API process
- stale/missing supervisor reports render honest `unknown` or `not_reported`
  states

- [ ] **Step 2: Run failing tests**

```bash
cd /Users/yann.moren/vision/backend
python3 -m uv run pytest \
  tests/services/test_supervisor_operations.py \
  tests/api/test_operations_endpoints.py \
  tests/core/test_db.py \
  -q
```

Expected: fail until the supervisor data contract exists.

- [ ] **Step 3: Implement assignments, reports, and requests**

Add `worker_assignments`, `worker_runtime_reports`, and
`operations_lifecycle_requests`. Extend Operations fleet responses to include
desired assignment, latest runtime truth, lifecycle request state, and last
error. Resolve `operations_mode` profiles through the runtime configuration
service so `manual`, `edge_supervisor`, and `central_supervisor` ownership
produce different allowed lifecycle actions.

- [ ] **Step 4: Run tests**

```bash
cd /Users/yann.moren/vision/backend
python3 -m uv run pytest \
  tests/services/test_supervisor_operations.py \
  tests/api/test_operations_endpoints.py \
  tests/core/test_db.py \
  -q
```

Expected: pass.

- [ ] **Step 5: Commit and push**

```bash
git add backend/src/argus/models/enums.py \
  backend/src/argus/models/tables.py \
  backend/src/argus/migrations/versions/0021_supervisor_operations.py \
  backend/src/argus/services/supervisor_operations.py \
  backend/src/argus/services/runtime_configuration.py \
  backend/src/argus/api/contracts.py \
  backend/src/argus/api/v1/operations.py \
  backend/tests/services/test_supervisor_operations.py \
  backend/tests/api/test_operations_endpoints.py \
  backend/tests/core/test_db.py
git commit -m "feat(operations): add supervisor runtime contract"
git push origin codex/omnisight-ui-spec-implementation
```

## Task 21: Operations Lifecycle And Assignment UI

**Files:**

- Modify: `frontend/src/hooks/use-operations.ts`
- Modify: `frontend/src/hooks/use-operations.test.ts`
- Create: `frontend/src/components/operations/SupervisorLifecycleControls.tsx`
- Create: `frontend/src/components/operations/SupervisorLifecycleControls.test.tsx`
- Modify: `frontend/src/pages/Settings.tsx`
- Modify: `frontend/src/pages/Settings.test.tsx`

- [ ] **Step 1: Add failing UI tests**

Cover:

- Start, Stop, Restart, and Drain buttons create lifecycle requests
- lifecycle controls are disabled when no supervisor owns the worker
- controls obey the resolved `operations_mode` profile: manual mode shows dev
  guidance only, disabled supervisor mode hides lifecycle requests, and
  supervisor-owned modes enable request buttons when a supervisor is healthy
- assignment/reassignment controls update desired worker location
- runtime heartbeat, restart count, last error, runtime backend, and scene
  contract hash render in Operations

- [ ] **Step 2: Run failing tests**

```bash
cd /Users/yann.moren/vision
corepack pnpm --dir frontend exec vitest run \
  src/hooks/use-operations.test.ts \
  src/components/operations/SupervisorLifecycleControls.test.tsx \
  src/pages/Settings.test.tsx
```

Expected: fail until the controls are implemented.

- [ ] **Step 3: Implement Operations controls**

Use API mutations that create lifecycle requests and assignment changes. Do not
show shell-command semantics for production controls. Keep manual dev command
copy for unsupervised local mode and label it as manual-mode guidance from the
resolved operations profile.

- [ ] **Step 4: Run tests**

```bash
cd /Users/yann.moren/vision
corepack pnpm generate:api
corepack pnpm --dir frontend exec vitest run \
  src/hooks/use-operations.test.ts \
  src/components/operations/SupervisorLifecycleControls.test.tsx \
  src/pages/Settings.test.tsx
```

Expected: pass.

- [ ] **Step 5: Commit and push**

```bash
git add frontend/src/lib/api.generated.ts \
  frontend/src/hooks/use-operations.ts \
  frontend/src/hooks/use-operations.test.ts \
  frontend/src/components/operations/SupervisorLifecycleControls.tsx \
  frontend/src/components/operations/SupervisorLifecycleControls.test.tsx \
  frontend/src/pages/Settings.tsx \
  frontend/src/pages/Settings.test.tsx
git commit -m "feat(operations): add supervisor lifecycle controls"
git push origin codex/omnisight-ui-spec-implementation
```

## Task 22: Edge Credential Rotation And Bootstrap Hardening

**Files:**

- Modify: `backend/src/argus/services/supervisor_operations.py`
- Modify: `backend/src/argus/services/app.py`
- Modify: `backend/src/argus/api/contracts.py`
- Modify: `backend/src/argus/api/v1/operations.py`
- Test: `backend/tests/services/test_supervisor_operations.py`
- Test: `backend/tests/api/test_operations_endpoints.py`
- Modify: `frontend/src/pages/Settings.tsx`
- Modify: `frontend/src/pages/Settings.test.tsx`
- Modify: `docs/operator-deployment-playbook.md`
- Modify: `docs/runbook.md`

- [ ] **Step 1: Add failing rotation tests**

Cover:

- edge credential rotation invalidates prior bootstrap material
- new credential material is returned once and not persisted in plaintext
- rotation writes an operations lifecycle/audit record
- UI warns that connected edge nodes must pick up the rotated credential

- [ ] **Step 2: Run failing tests**

```bash
cd /Users/yann.moren/vision/backend
python3 -m uv run pytest tests/services/test_supervisor_operations.py tests/api/test_operations_endpoints.py -q
cd /Users/yann.moren/vision
corepack pnpm --dir frontend exec vitest run src/pages/Settings.test.tsx
```

Expected: fail until rotation is implemented.

- [ ] **Step 3: Implement rotation and docs**

Add `POST /api/v1/operations/edge-nodes/{edge_node_id}/credentials/rotate`.
Return one-time secret material only in the response. Document the production
rotation sequence and local lab limitations.

- [ ] **Step 4: Run tests and docs check**

```bash
cd /Users/yann.moren/vision/backend
python3 -m uv run pytest tests/services/test_supervisor_operations.py tests/api/test_operations_endpoints.py -q
cd /Users/yann.moren/vision
corepack pnpm generate:api
corepack pnpm --dir frontend exec vitest run src/pages/Settings.test.tsx
git diff --check -- docs/operator-deployment-playbook.md docs/runbook.md
```

Expected: pass and no diff-check output.

- [ ] **Step 5: Commit and push**

```bash
git add backend/src/argus/services/supervisor_operations.py \
  backend/src/argus/services/app.py \
  backend/src/argus/api/contracts.py \
  backend/src/argus/api/v1/operations.py \
  backend/tests/services/test_supervisor_operations.py \
  backend/tests/api/test_operations_endpoints.py \
  frontend/src/lib/api.generated.ts \
  frontend/src/pages/Settings.tsx \
  frontend/src/pages/Settings.test.tsx \
  docs/operator-deployment-playbook.md \
  docs/runbook.md
git commit -m "feat(operations): rotate edge credentials"
git push origin codex/omnisight-ui-spec-implementation
```

## Task 23: Production Linux And Jetson Runtime Artifact Soak

**Files:**

- Modify: `backend/src/argus/models/tables.py`
- Create: `backend/src/argus/migrations/versions/0022_runtime_artifact_soak_runs.py`
- Create: `backend/src/argus/services/runtime_soak.py`
- Create: `backend/src/argus/api/v1/runtime_soak.py`
- Modify: `backend/src/argus/main.py`
- Test: `backend/tests/services/test_runtime_soak.py`
- Test: `backend/tests/api/test_runtime_soak_routes.py`
- Modify: `docs/imac-master-orin-lab-test-guide.md`
- Modify: `docs/model-loading-and-configuration-guide.md`
- Modify: `docs/runbook.md`

- [ ] **Step 1: Add failing soak tests**

Cover:

- soak run records for fixed-vocab TensorRT artifacts such as YOLO26n
- soak run records for compiled YOLOE S/open-vocab scene artifacts
- pass/fail status, metrics, target profile, runtime artifact id, and edge node
  id
- fallback reason captured when optimized runtime is unavailable
- selected `runtime_selection` profile id/hash and operations assignment id are
  recorded with the soak run

- [ ] **Step 2: Run failing tests**

```bash
cd /Users/yann.moren/vision/backend
python3 -m uv run pytest tests/services/test_runtime_soak.py tests/api/test_runtime_soak_routes.py -q
```

Expected: fail until soak run service/routes exist.

- [ ] **Step 3: Implement soak run recording**

Add `runtime_artifact_soak_runs`, service helpers, and routes to record target
Jetson validation results. Include the runtime profile selected by Task 13H and
the worker assignment selected by Tasks 20-21. Do not fake hardware validation
in code; unit tests cover the control-plane record, and docs define the physical
soak procedure.

- [ ] **Step 4: Document the first-site validation procedure**

Document:

- Linux master deployment validation
- Jetson edge worker validation
- fixed-vocab TensorRT build/register/validate/select sequence
- compiled YOLOE S/open-vocab build/register/validate/select sequence
- restart recovery, evidence clip review, credential rotation, fallback, and
  rollback checks

- [ ] **Step 5: Run tests and docs check**

```bash
cd /Users/yann.moren/vision/backend
python3 -m uv run pytest tests/services/test_runtime_soak.py tests/api/test_runtime_soak_routes.py -q
cd /Users/yann.moren/vision
git diff --check -- docs/imac-master-orin-lab-test-guide.md docs/model-loading-and-configuration-guide.md docs/runbook.md
```

Expected: pass and no diff-check output.

- [ ] **Step 6: Commit and push**

```bash
git add backend/src/argus/models/tables.py \
  backend/src/argus/migrations/versions/0022_runtime_artifact_soak_runs.py \
  backend/src/argus/services/runtime_soak.py \
  backend/src/argus/api/v1/runtime_soak.py \
  backend/src/argus/main.py \
  backend/tests/services/test_runtime_soak.py \
  backend/tests/api/test_runtime_soak_routes.py \
  docs/imac-master-orin-lab-test-guide.md \
  docs/model-loading-and-configuration-guide.md \
  docs/runbook.md
git commit -m "feat(runtime): record Jetson artifact soak runs"
git push origin codex/omnisight-ui-spec-implementation
```

## Task 24: Track C DeepStream Runtime Lane

**Gate:** Start this task only after Task 23 has recorded passing first-site
Jetson soak evidence for the Track A/B runtime artifacts, or after the user
explicitly accepts implementing DeepStream before that evidence exists.

**Files:**

- Create: `backend/src/argus/vision/deepstream_runtime.py`
- Create: `backend/src/argus/vision/deepstream_metadata.py`
- Modify: `backend/src/argus/vision/runtime.py`
- Modify: `backend/src/argus/vision/runtime_selection.py`
- Modify: `backend/src/argus/inference/engine.py`
- Create: `infra/deepstream/README.md`
- Create: `infra/deepstream/docker-compose.jetson.yml`
- Test: `backend/tests/vision/test_deepstream_runtime.py`
- Test: `backend/tests/vision/test_runtime_selection.py`
- Test: `backend/tests/inference/test_engine.py`
- Modify: `docs/model-loading-and-configuration-guide.md`
- Modify: `docs/runbook.md`

- [ ] **Step 1: Verify the gate**

Check for a passing Task 23 soak record or a user message explicitly accepting
the risk:

```bash
cd /Users/yann.moren/vision
rg -n "DeepStream gate|soak run|YOLO26n|YOLOE S" docs/runbook.md docs/model-loading-and-configuration-guide.md
```

Expected: docs identify the soak evidence or the accepted exception.

- [ ] **Step 2: Add failing DeepStream tests**

Cover:

- DeepStream runtime backend contract
- metadata bridge into existing track lifecycle fields
- DeepStream runtime selection only on supported Jetson target profiles
- DeepStream can be selected only through a UI-managed runtime profile after
  the soak gate is satisfied
- fallback to existing non-DeepStream runtime when unavailable

- [ ] **Step 3: Run failing tests**

```bash
cd /Users/yann.moren/vision/backend
python3 -m uv run pytest \
  tests/vision/test_deepstream_runtime.py \
  tests/vision/test_runtime_selection.py \
  tests/inference/test_engine.py \
  -q
```

Expected: fail until DeepStream runtime adapter exists.

- [ ] **Step 4: Implement DeepStream adapter and packaging**

Add a Jetson-only adapter that produces the same detection/track metadata shape
as existing runtimes. Add `infra/deepstream/` packaging docs and keep fallback
to existing runtime paths explicit. Wire DeepStream selection through the
runtime-selection profile machinery from Task 13H; do not add a parallel
environment-only switch.

- [ ] **Step 5: Run tests and docs check**

```bash
cd /Users/yann.moren/vision/backend
python3 -m uv run pytest \
  tests/vision/test_deepstream_runtime.py \
  tests/vision/test_runtime_selection.py \
  tests/inference/test_engine.py \
  -q
cd /Users/yann.moren/vision
git diff --check -- infra/deepstream/README.md infra/deepstream/docker-compose.jetson.yml docs/model-loading-and-configuration-guide.md docs/runbook.md
```

Expected: pass and no diff-check output.

- [ ] **Step 6: Commit and push**

```bash
git add backend/src/argus/vision/deepstream_runtime.py \
  backend/src/argus/vision/deepstream_metadata.py \
  backend/src/argus/vision/runtime.py \
  backend/src/argus/vision/runtime_selection.py \
  backend/src/argus/inference/engine.py \
  backend/tests/vision/test_deepstream_runtime.py \
  backend/tests/vision/test_runtime_selection.py \
  backend/tests/inference/test_engine.py \
  infra/deepstream/README.md \
  infra/deepstream/docker-compose.jetson.yml \
  docs/model-loading-and-configuration-guide.md \
  docs/runbook.md
git commit -m "feat(runtime): add DeepStream runtime lane"
git push origin codex/omnisight-ui-spec-implementation
```

## Task 25: Full Runway Verification And Handoff Refresh

**Files:**

- Modify: `docs/superpowers/status/2026-05-11-next-chat-accountable-scene-intelligence-handoff.md`
- Modify: `docs/runbook.md`
- Modify: `docs/operator-deployment-playbook.md`
- Modify: `docs/model-loading-and-configuration-guide.md`

- [ ] **Step 1: Backend focused suite**

```bash
cd /Users/yann.moren/vision/backend
python3 -m uv run pytest \
  tests/services/test_scene_contracts.py \
  tests/services/test_privacy_manifests.py \
  tests/services/test_evidence_ledger.py \
  tests/services/test_evidence_storage.py \
  tests/services/test_local_first_sync.py \
  tests/services/test_runtime_configuration.py \
  tests/services/test_incident_capture.py \
  tests/services/test_camera_worker_config.py \
  tests/services/test_runtime_passports.py \
  tests/services/test_operational_memory.py \
  tests/services/test_llm_provider_runtime.py \
  tests/services/test_policy_drafts.py \
  tests/services/test_cross_camera_threads.py \
  tests/services/test_supervisor_operations.py \
  tests/services/test_runtime_soak.py \
  tests/api/test_prompt9_routes.py \
  tests/api/test_prompt5_routes.py \
  tests/api/test_configuration_routes.py \
  tests/api/test_operations_endpoints.py \
  tests/api/test_policy_draft_routes.py \
  tests/api/test_runtime_soak_routes.py \
  tests/vision/test_camera_source.py \
  tests/vision/test_runtime_selection.py \
  tests/inference/test_engine.py \
  tests/core/test_db.py \
  -q
```

- [ ] **Step 2: Frontend focused suite**

```bash
cd /Users/yann.moren/vision
corepack pnpm --dir frontend exec vitest run \
  src/components/evidence/evidence-signals.test.ts \
  src/components/evidence/EvidenceTimeline.test.tsx \
  src/components/evidence/CaseContextStrip.test.tsx \
  src/components/evidence/AccountabilityStrip.test.tsx \
  src/components/evidence/RuntimePassportPanel.test.tsx \
  src/components/evidence/OperationalMemoryPanel.test.tsx \
  src/components/evidence/CrossCameraThreadPanel.test.tsx \
  src/components/configuration/EffectiveConfigurationPanel.test.tsx \
  src/components/configuration/ConfigurationWorkspace.test.tsx \
  src/components/policy/PolicyDraftReview.test.tsx \
  src/components/operations/SupervisorLifecycleControls.test.tsx \
  src/pages/Live.test.tsx \
  src/pages/Incidents.test.tsx \
  src/pages/Settings.test.tsx \
  src/components/cameras/CameraWizard.test.tsx
```

- [ ] **Step 3: Full frontend and backend checks**

```bash
cd /Users/yann.moren/vision
CI=1 corepack pnpm --dir frontend test -- --run
corepack pnpm --dir frontend build
corepack pnpm --dir frontend lint
cd /Users/yann.moren/vision/backend
python3 -m uv run ruff check src tests
python3 -m uv run mypy src
```

Record exact unrelated pre-existing failures if any remain.

- [ ] **Step 4: Refresh docs and handoff**

Update the handoff with:

- completed task list and commit hashes
- verification results
- any blocked hardware soak or DeepStream gate notes
- next recommended branch/chat prompt

- [ ] **Step 5: Commit and push docs**

```bash
git add docs/superpowers/specs/2026-05-11-accountable-scene-intelligence-and-evidence-recording-design.md \
  docs/superpowers/plans/2026-05-11-accountable-scene-intelligence-and-evidence-recording-implementation-plan.md \
  docs/superpowers/status/2026-05-11-next-chat-accountable-scene-intelligence-handoff.md \
  docs/runbook.md \
  docs/operator-deployment-playbook.md \
  docs/model-loading-and-configuration-guide.md
git commit -m "docs(handoff): refresh full accountable runtime runway"
git push origin codex/omnisight-ui-spec-implementation
```

## Self-Review

- Spec coverage: Tasks 1-12 cover accountable scene contracts, privacy
  manifests, evidence ledger, artifact-aware clips, edge USB/UVC, storage, API,
  UI, and docs. Tasks 13-13D cover the Evidence Desk polish, configuration
  control plane, and storage routing. Tasks 13E-13J cover the missing runtime
  consumption for local-first sync, effective configuration diagnostics, stream
  delivery, runtime selection, privacy policy, and LLM provider profiles. Task
  14 covers optional still snapshots. Tasks 15-16 cover Runtime Passport.
  Tasks 16A-16E cover per-worker incident rule definition, runtime consumption,
  UI authoring, and Evidence/Operations provenance. Tasks 17-19 cover
  Operational Memory, Prompt-To-Policy, and Identity-Light Cross-Camera
  Intelligence. Tasks 20-22 cover Fleet/Operations supervisor hardening,
  operations-mode consumption, and credential rotation. Task 23 covers Linux
  master plus Jetson TensorRT/open-vocab soak validation. Task 24 covers gated
  Track C / DeepStream through UI-managed runtime selection. Task 25 refreshes
  verification and handoff.
- Placeholder scan: no follow-up queue remains; all handoff items are expressed
  as executable tasks with owned files, verification commands, commit messages,
  and push steps.
- Gate consistency: DeepStream remains in the one-go runway, but it is gated
  behind first-site Track A/B Jetson soak evidence or explicit user acceptance
  of the risk.
