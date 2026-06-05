# One-Pack SceneOps Pack Boundary Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a read-only SceneOps pack registry that loads repo manifests, exposes pack status through the API, and protects the core engine from maritime or traffic/public-space noun drift.

**Architecture:** Pack manifests live under `packs/*/pack.yaml` and are loaded as static data by `argus.services.pack_registry`. The backend exposes read-only `/api/v1/packs` routes through the existing `AppServices` dependency pattern, while governance tests keep vertical entities out of core contracts.

**Tech Stack:** Python 3.12, FastAPI, Pydantic v2, PyYAML, pytest, pytest-asyncio, httpx ASGI transport, uv.

---

## Scope

This plan implements the pack registry boundary only. It does not implement
maritime runtime entities, AIS/NMEA adapters, traffic/public-space runtime
entities, billing refactors, or UI surfaces.

The implementation must preserve existing runtime semantics. A read-only pack
registry is allowed; new scene execution behavior is not.

## Files

Create:

- `backend/src/argus/services/pack_registry.py`
- `backend/src/argus/api/v1/packs.py`
- `backend/tests/services/test_pack_registry.py`
- `backend/tests/api/test_pack_routes.py`
- `backend/tests/core/test_pack_boundaries.py`

Modify:

- `backend/pyproject.toml`
- `backend/uv.lock`
- `backend/src/argus/api/contracts.py`
- `backend/src/argus/api/v1/__init__.py`
- `backend/src/argus/services/app.py`

Existing strategy artifacts used as input:

- `docs/strategy/2026-06-05-vezor-fleetops-wedge-and-scene-engine-blueprint.md`
- `docs/superpowers/specs/2026-06-05-one-pack-sceneops-engine-pack-boundary-design.md`
- `packs/README.md`
- `packs/maritime-fleet/pack.yaml`
- `packs/traffic-public-space/pack.yaml`

## Data Model

The registry treats each manifest as static configuration. It should return
typed Pydantic objects to the route layer.

Allowed statuses:

- `planned_mvp`
- `designed_not_implemented`
- `active`
- `retired`

Runtime-enabled statuses:

- `planned_mvp`
- `active`

Designed-only status:

- `designed_not_implemented`

## Task 1: Declare YAML Dependencies

**Files:**

- Modify: `backend/pyproject.toml`
- Modify: `backend/uv.lock`

- [ ] **Step 1: Add direct runtime and typing dependencies**

Edit `backend/pyproject.toml` so the dependency groups include direct YAML
support:

```toml
runtime = [
  "fastapi>=0.115",
  "uvicorn[standard]>=0.32",
  "pydantic>=2",
  "pydantic-settings>=2",
  "sqlalchemy[asyncio]>=2.0",
  "asyncpg>=0.30",
  "alembic>=1.14",
  "redis>=5.2",
  "nats-py>=2.9",
  "httpx>=0.28",
  "structlog>=24.4",
  "opentelemetry-api>=1.28",
  "opentelemetry-sdk>=1.28",
  "opentelemetry-exporter-otlp>=1.28",
  "opentelemetry-instrumentation-fastapi>=0.49b0",
  "opentelemetry-instrumentation-httpx>=0.49b0",
  "opentelemetry-instrumentation-sqlalchemy>=0.49b0",
  "python-jose[cryptography]>=3.3",
  "passlib[argon2]>=1.7",
  "cryptography>=43",
  "prometheus-client>=0.21",
  "pyarrow>=23.0.1",
  "minio>=7.2.20",
  "opencv-python-headless>=4.10",
  "PyYAML>=6.0",
]
dev = [
  "ruff>=0.8",
  "mypy>=1.13",
  "pytest>=8.3",
  "pytest-asyncio>=0.24",
  "testcontainers[postgres,redis,nats]>=4.8",
  "playwright>=1.49",
  "types-PyYAML>=6.0",
]
```

- [ ] **Step 2: Refresh the backend lock file**

Run:

```bash
cd /Users/yann.moren/vision/backend
uv lock
```

Expected:

- `backend/uv.lock` remains valid.
- PyYAML is retained as a direct runtime dependency.
- `types-PyYAML` is added for type checking.

- [ ] **Step 3: Commit**

```bash
cd /Users/yann.moren/vision
git add backend/pyproject.toml backend/uv.lock
git commit -m "chore: declare pack manifest yaml dependencies"
```

## Task 2: Write Pack Registry Service Tests

**Files:**

- Create: `backend/tests/services/test_pack_registry.py`
- Input: `packs/maritime-fleet/pack.yaml`
- Input: `packs/traffic-public-space/pack.yaml`

- [ ] **Step 1: Add failing service tests**

Create `backend/tests/services/test_pack_registry.py`:

```python
from __future__ import annotations

from pathlib import Path

import pytest

from argus.services.pack_registry import (
    PackRegistry,
    PackRegistryError,
    default_packs_root,
    load_pack_manifest,
    load_pack_manifests,
)


REPO_ROOT = Path(__file__).resolve().parents[3]
PACKS_ROOT = REPO_ROOT / "packs"


def test_default_packs_root_points_to_repo_packs_directory() -> None:
    assert default_packs_root() == PACKS_ROOT


def test_load_pack_manifests_returns_expected_repo_packs() -> None:
    manifests = load_pack_manifests(PACKS_ROOT)

    ids = {manifest.metadata.id for manifest in manifests}

    assert ids == {"maritime-fleet", "traffic-public-space"}


def test_maritime_pack_is_planned_mvp() -> None:
    manifest = load_pack_manifest(PACKS_ROOT / "maritime-fleet" / "pack.yaml")

    assert manifest.metadata.id == "maritime-fleet"
    assert manifest.metadata.status == "planned_mvp"
    assert manifest.metadata.implementation_commitment is True
    assert manifest.is_runtime_enabled is True
    assert {entity.name for entity in manifest.entities} >= {"Vessel", "Voyage", "PortCall"}


def test_traffic_pack_is_designed_not_implemented() -> None:
    manifest = load_pack_manifest(PACKS_ROOT / "traffic-public-space" / "pack.yaml")

    assert manifest.metadata.id == "traffic-public-space"
    assert manifest.metadata.status == "designed_not_implemented"
    assert manifest.metadata.implementation_commitment is False
    assert manifest.metadata.sales_motion == "none"
    assert manifest.is_runtime_enabled is False
    assert manifest.activation_conditions
    assert {entity.name for entity in manifest.entities} >= {
        "Intersection",
        "CurbZone",
        "TrafficStudy",
    }


def test_designed_only_pack_cannot_claim_implemented_integrations(tmp_path: Path) -> None:
    manifest_path = tmp_path / "pack.yaml"
    manifest_path.write_text(
        """
api_version: vezor.io/v1alpha1
kind: Pack
metadata:
  id: invalid-designed-pack
  name: Invalid Designed Pack
  product_name: Invalid Pack
  owner: product
  status: designed_not_implemented
  wedge: invalid
  sales_motion: none
  implementation_commitment: false
activation_conditions:
  - activation requires a dated decision
engine:
  min_version: 0.1.0
  required_capabilities: [scenes, pack_registry]
entities: []
scene_templates: []
model_presets:
  fixed_vocab: []
  open_vocab: []
integrations:
  - id: invalid-live-adapter
    status: planned_mvp
    protocol: API
evidence_context:
  fields: []
billing:
  status: design_artifact_only
  meters: []
ui_extensions:
  status: design_artifact_only
  panels: []
allowed_core_dependencies: [Scene]
forbidden_dependencies: [invalid_dependency]
""".strip(),
        encoding="utf-8",
    )

    with pytest.raises(PackRegistryError, match="designed-only integrations"):
        load_pack_manifest(manifest_path)


def test_registry_get_pack_returns_by_id_and_raises_for_unknown_pack() -> None:
    registry = PackRegistry(PACKS_ROOT)

    assert registry.get_pack("maritime-fleet").metadata.name == "Maritime Fleet Pack"

    with pytest.raises(KeyError):
        registry.get_pack("missing-pack")


def test_registry_lists_runtime_enabled_packs() -> None:
    registry = PackRegistry(PACKS_ROOT)

    runtime_ids = {manifest.metadata.id for manifest in registry.list_runtime_enabled_packs()}

    assert runtime_ids == {"maritime-fleet"}
```

- [ ] **Step 2: Run the tests and verify failure**

Run:

```bash
cd /Users/yann.moren/vision/backend
uv run pytest tests/services/test_pack_registry.py -q
```

Expected:

- Fail with `ModuleNotFoundError: No module named 'argus.services.pack_registry'`.

- [ ] **Step 3: Commit the failing tests**

```bash
cd /Users/yann.moren/vision
git add backend/tests/services/test_pack_registry.py
git commit -m "test: describe pack manifest registry behavior"
```

## Task 3: Implement Pack Registry Service

**Files:**

- Create: `backend/src/argus/services/pack_registry.py`
- Test: `backend/tests/services/test_pack_registry.py`

- [ ] **Step 1: Add the registry implementation**

Create `backend/src/argus/services/pack_registry.py`:

```python
from __future__ import annotations

from pathlib import Path
from typing import Any, Literal

import yaml
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

PackStatus = Literal["planned_mvp", "designed_not_implemented", "active", "retired"]
RuntimePackStatus = Literal["planned_mvp", "active"]

RUNTIME_ENABLED_STATUSES: set[str] = {"planned_mvp", "active"}
DESIGNED_ONLY_STATUSES: set[str] = {"designed_not_implemented"}
DESIGNED_ONLY_INTEGRATION_STATUSES: set[str] = {"design_only", "research_only"}


class PackRegistryError(ValueError):
    """Raised when pack manifests cannot be loaded or validated."""


class PackMetadata(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str = Field(min_length=1, pattern=r"^[a-z0-9][a-z0-9-]*[a-z0-9]$")
    name: str = Field(min_length=1)
    product_name: str = Field(min_length=1)
    owner: str = Field(min_length=1)
    status: PackStatus
    wedge: str = Field(min_length=1)
    sales_motion: str = Field(min_length=1)
    implementation_commitment: bool


class PackEngineRequirements(BaseModel):
    model_config = ConfigDict(extra="forbid")

    min_version: str = Field(min_length=1)
    required_capabilities: list[str] = Field(default_factory=list)

    @field_validator("required_capabilities")
    @classmethod
    def validate_capabilities(cls, value: list[str]) -> list[str]:
        return _unique_non_empty(value, "required_capabilities")


class PackEntity(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1)
    extends: str = Field(min_length=1)
    storage: Literal["pack"]
    purpose: str = Field(min_length=1)


class PackSceneTemplate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str = Field(min_length=1, pattern=r"^[a-z0-9][a-z0-9-]*[a-z0-9]$")
    name: str = Field(min_length=1)
    outcome: str = Field(min_length=1)
    primitives: list[str] = Field(default_factory=list)

    @field_validator("primitives")
    @classmethod
    def validate_primitives(cls, value: list[str]) -> list[str]:
        return _unique_non_empty(value, "primitives")


class PackModelPreset(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str = Field(min_length=1, pattern=r"^[a-z0-9][a-z0-9-]*[a-z0-9]$")
    status: str | None = None
    classes: list[str] = Field(default_factory=list)
    scenes: list[str] = Field(default_factory=list)
    max_terms: int | None = Field(default=None, gt=0)
    terms: list[str] = Field(default_factory=list)

    @field_validator("classes", "scenes", "terms")
    @classmethod
    def validate_string_lists(cls, value: list[str]) -> list[str]:
        return _unique_non_empty(value, "preset values")


class PackModelPresets(BaseModel):
    model_config = ConfigDict(extra="forbid")

    fixed_vocab: list[PackModelPreset] = Field(default_factory=list)
    open_vocab: list[PackModelPreset] = Field(default_factory=list)


class PackIntegration(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str = Field(min_length=1, pattern=r"^[a-z0-9][a-z0-9-]*[a-z0-9]$")
    status: str = Field(min_length=1)
    protocol: str = Field(min_length=1)


class PackEvidenceContext(BaseModel):
    model_config = ConfigDict(extra="forbid")

    fields: list[str] = Field(default_factory=list)

    @field_validator("fields")
    @classmethod
    def validate_fields(cls, value: list[str]) -> list[str]:
        return _unique_non_empty(value, "fields")


class PackBilling(BaseModel):
    model_config = ConfigDict(extra="allow")

    hierarchy_labels: list[str] = Field(default_factory=list)
    meters: list[str] = Field(default_factory=list)

    @field_validator("hierarchy_labels", "meters")
    @classmethod
    def validate_billing_lists(cls, value: list[str]) -> list[str]:
        return _unique_non_empty(value, "billing values")


class PackUiExtensions(BaseModel):
    model_config = ConfigDict(extra="allow")

    navigation_labels: dict[str, str] = Field(default_factory=dict)
    panels: list[str] = Field(default_factory=list)

    @field_validator("panels")
    @classmethod
    def validate_panels(cls, value: list[str]) -> list[str]:
        return _unique_non_empty(value, "panels")


class PackManifest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    api_version: Literal["vezor.io/v1alpha1"]
    kind: Literal["Pack"]
    metadata: PackMetadata
    activation_conditions: list[str] = Field(default_factory=list)
    engine: PackEngineRequirements
    entities: list[PackEntity] = Field(default_factory=list)
    scene_templates: list[PackSceneTemplate] = Field(default_factory=list)
    model_presets: PackModelPresets
    integrations: list[PackIntegration] = Field(default_factory=list)
    privacy_defaults: dict[str, Any] = Field(default_factory=dict)
    evidence_context: PackEvidenceContext
    billing: PackBilling
    ui_extensions: PackUiExtensions
    allowed_core_dependencies: list[str] = Field(default_factory=list)
    forbidden_dependencies: list[str] = Field(default_factory=list)

    @property
    def is_runtime_enabled(self) -> bool:
        return self.metadata.status in RUNTIME_ENABLED_STATUSES

    @field_validator("activation_conditions", "allowed_core_dependencies", "forbidden_dependencies")
    @classmethod
    def validate_unique_strings(cls, value: list[str]) -> list[str]:
        return _unique_non_empty(value, "manifest values")

    @model_validator(mode="after")
    def validate_status_semantics(self) -> PackManifest:
        if self.metadata.status in DESIGNED_ONLY_STATUSES:
            if self.metadata.implementation_commitment:
                raise PackRegistryError("designed-only packs cannot commit to implementation")
            if self.metadata.sales_motion != "none":
                raise PackRegistryError("designed-only packs must have sales_motion set to none")
            if not self.activation_conditions:
                raise PackRegistryError("designed-only packs must declare activation conditions")
            invalid_integrations = [
                integration.id
                for integration in self.integrations
                if integration.status not in DESIGNED_ONLY_INTEGRATION_STATUSES
            ]
            if invalid_integrations:
                joined = ", ".join(sorted(invalid_integrations))
                raise PackRegistryError(
                    f"designed-only integrations must be design_only or research_only: {joined}"
                )
        if self.metadata.status in RUNTIME_ENABLED_STATUSES and not self.metadata.implementation_commitment:
            raise PackRegistryError("runtime-enabled packs must commit to implementation")
        return self


class PackRegistry:
    def __init__(self, packs_root: Path | None = None) -> None:
        self.packs_root = packs_root or default_packs_root()
        self._manifests = tuple(load_pack_manifests(self.packs_root))
        self._by_id = {manifest.metadata.id: manifest for manifest in self._manifests}
        if len(self._by_id) != len(self._manifests):
            raise PackRegistryError("pack manifest ids must be unique")

    def list_packs(self) -> list[PackManifest]:
        return list(self._manifests)

    def list_runtime_enabled_packs(self) -> list[PackManifest]:
        return [manifest for manifest in self._manifests if manifest.is_runtime_enabled]

    def get_pack(self, pack_id: str) -> PackManifest:
        return self._by_id[pack_id]


def default_packs_root() -> Path:
    return Path(__file__).resolve().parents[4] / "packs"


def load_pack_manifests(packs_root: Path) -> list[PackManifest]:
    if not packs_root.exists():
        raise PackRegistryError(f"pack root does not exist: {packs_root}")
    manifest_paths = sorted(packs_root.glob("*/pack.yaml"))
    manifests = [load_pack_manifest(path) for path in manifest_paths]
    ids = [manifest.metadata.id for manifest in manifests]
    if len(ids) != len(set(ids)):
        raise PackRegistryError("pack manifest ids must be unique")
    return manifests


def load_pack_manifest(manifest_path: Path) -> PackManifest:
    try:
        raw = yaml.safe_load(manifest_path.read_text(encoding="utf-8"))
    except OSError as exc:
        raise PackRegistryError(f"could not read pack manifest: {manifest_path}") from exc
    except yaml.YAMLError as exc:
        raise PackRegistryError(f"could not parse pack manifest: {manifest_path}") from exc
    if not isinstance(raw, dict):
        raise PackRegistryError(f"pack manifest must be a mapping: {manifest_path}")
    try:
        return PackManifest.model_validate(raw)
    except ValueError as exc:
        raise PackRegistryError(f"invalid pack manifest {manifest_path}: {exc}") from exc


def _unique_non_empty(values: list[str], field_name: str) -> list[str]:
    normalized = [value.strip() for value in values]
    if any(not value for value in normalized):
        raise ValueError(f"{field_name} cannot contain empty strings")
    if len(normalized) != len(set(normalized)):
        raise ValueError(f"{field_name} cannot contain duplicates")
    return normalized
```

- [ ] **Step 2: Run the service tests**

Run:

```bash
cd /Users/yann.moren/vision/backend
uv run pytest tests/services/test_pack_registry.py -q
```

Expected:

- All tests pass.

- [ ] **Step 3: Run lint and type checks for the new service**

Run:

```bash
cd /Users/yann.moren/vision/backend
uv run ruff check src/argus/services/pack_registry.py tests/services/test_pack_registry.py
uv run mypy src/argus/services/pack_registry.py
```

Expected:

- Ruff reports no issues.
- Mypy reports success.

- [ ] **Step 4: Commit**

```bash
cd /Users/yann.moren/vision
git add backend/src/argus/services/pack_registry.py backend/tests/services/test_pack_registry.py
git commit -m "feat: add read-only pack manifest registry"
```

## Task 4: Add API Response Contracts

**Files:**

- Modify: `backend/src/argus/api/contracts.py`

- [ ] **Step 1: Add pack response models near the model catalog responses**

In `backend/src/argus/api/contracts.py`, add this block after
`ModelCatalogEntryResponse`:

```python
class PackStatus(StrEnum):
    PLANNED_MVP = "planned_mvp"
    DESIGNED_NOT_IMPLEMENTED = "designed_not_implemented"
    ACTIVE = "active"
    RETIRED = "retired"


class PackMetadataResponse(BaseModel):
    id: str
    name: str
    product_name: str
    owner: str
    status: PackStatus
    wedge: str
    sales_motion: str
    implementation_commitment: bool


class PackEngineRequirementsResponse(BaseModel):
    min_version: str
    required_capabilities: list[str] = Field(default_factory=list)


class PackEntityResponse(BaseModel):
    name: str
    extends: str
    storage: str
    purpose: str


class PackSceneTemplateResponse(BaseModel):
    id: str
    name: str
    outcome: str
    primitives: list[str] = Field(default_factory=list)


class PackModelPresetResponse(BaseModel):
    id: str
    status: str | None = None
    classes: list[str] = Field(default_factory=list)
    scenes: list[str] = Field(default_factory=list)
    max_terms: int | None = None
    terms: list[str] = Field(default_factory=list)


class PackModelPresetsResponse(BaseModel):
    fixed_vocab: list[PackModelPresetResponse] = Field(default_factory=list)
    open_vocab: list[PackModelPresetResponse] = Field(default_factory=list)


class PackIntegrationResponse(BaseModel):
    id: str
    status: str
    protocol: str


class PackEvidenceContextResponse(BaseModel):
    fields: list[str] = Field(default_factory=list)


class PackBillingResponse(BaseModel):
    hierarchy_labels: list[str] = Field(default_factory=list)
    meters: list[str] = Field(default_factory=list)
    status: str | None = None


class PackUiExtensionsResponse(BaseModel):
    navigation_labels: dict[str, str] = Field(default_factory=dict)
    panels: list[str] = Field(default_factory=list)
    status: str | None = None


class PackManifestResponse(BaseModel):
    api_version: str
    kind: str
    metadata: PackMetadataResponse
    activation_conditions: list[str] = Field(default_factory=list)
    engine: PackEngineRequirementsResponse
    entities: list[PackEntityResponse] = Field(default_factory=list)
    scene_templates: list[PackSceneTemplateResponse] = Field(default_factory=list)
    model_presets: PackModelPresetsResponse
    integrations: list[PackIntegrationResponse] = Field(default_factory=list)
    privacy_defaults: dict[str, Any] = Field(default_factory=dict)
    evidence_context: PackEvidenceContextResponse
    billing: PackBillingResponse
    ui_extensions: PackUiExtensionsResponse
    allowed_core_dependencies: list[str] = Field(default_factory=list)
    forbidden_dependencies: list[str] = Field(default_factory=list)
    is_runtime_enabled: bool


class PackListResponse(BaseModel):
    packs: list[PackManifestResponse]
```

- [ ] **Step 2: Run contract checks**

Run:

```bash
cd /Users/yann.moren/vision/backend
uv run ruff check src/argus/api/contracts.py
uv run mypy src/argus/api/contracts.py
```

Expected:

- Ruff reports no issues.
- Mypy reports success.

- [ ] **Step 3: Commit**

```bash
cd /Users/yann.moren/vision
git add backend/src/argus/api/contracts.py
git commit -m "feat: add pack manifest API contracts"
```

## Task 5: Write Pack API Route Tests

**Files:**

- Create: `backend/tests/api/test_pack_routes.py`

- [ ] **Step 1: Add failing API tests**

Create `backend/tests/api/test_pack_routes.py`:

```python
from __future__ import annotations

from types import SimpleNamespace
from uuid import uuid4

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from argus.api.contracts import TenantContext
from argus.api.v1 import router
from argus.core.security import AuthenticatedUser
from argus.models.enums import RoleEnum
from argus.services.pack_registry import PackRegistry


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
        explicit_tenant_id=None,  # noqa: ANN001
    ) -> TenantContext:
        return self.context


class _FakeSecurity:
    def __init__(self, user: AuthenticatedUser) -> None:
        self.user = user

    async def authenticate_request(self, request) -> AuthenticatedUser:  # noqa: ANN001
        return self.user


def _create_app(context: TenantContext) -> FastAPI:
    app = FastAPI()
    app.include_router(router)
    app.state.services = SimpleNamespace(
        tenancy=_FakeTenancyService(context),
        packs=PackRegistry(),
    )
    app.state.security = _FakeSecurity(context.user)
    return app


@pytest.mark.asyncio
async def test_pack_list_route_returns_manifest_statuses() -> None:
    context = _tenant_context()
    app = _create_app(context)

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        response = await client.get(
            "/api/v1/packs",
            headers={"Authorization": "Bearer token"},
        )

    assert response.status_code == 200
    body = response.json()
    statuses = {pack["metadata"]["id"]: pack["metadata"]["status"] for pack in body["packs"]}
    runtime_enabled = {
        pack["metadata"]["id"]: pack["is_runtime_enabled"] for pack in body["packs"]
    }

    assert statuses == {
        "maritime-fleet": "planned_mvp",
        "traffic-public-space": "designed_not_implemented",
    }
    assert runtime_enabled == {
        "maritime-fleet": True,
        "traffic-public-space": False,
    }


@pytest.mark.asyncio
async def test_pack_detail_route_returns_traffic_manifest_without_enabling_runtime() -> None:
    context = _tenant_context()
    app = _create_app(context)

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        response = await client.get(
            "/api/v1/packs/traffic-public-space",
            headers={"Authorization": "Bearer token"},
        )

    assert response.status_code == 200
    body = response.json()

    assert body["metadata"]["id"] == "traffic-public-space"
    assert body["metadata"]["implementation_commitment"] is False
    assert body["is_runtime_enabled"] is False
    assert body["activation_conditions"]


@pytest.mark.asyncio
async def test_pack_detail_route_returns_404_for_unknown_pack() -> None:
    context = _tenant_context()
    app = _create_app(context)

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        response = await client.get(
            "/api/v1/packs/not-a-pack",
            headers={"Authorization": "Bearer token"},
        )

    assert response.status_code == 404
    assert response.json()["detail"] == "Pack not found."
```

- [ ] **Step 2: Run the tests and verify route failure**

Run:

```bash
cd /Users/yann.moren/vision/backend
uv run pytest tests/api/test_pack_routes.py -q
```

Expected:

- Fail with HTTP 404 for `/api/v1/packs`, because the route is not registered yet.

- [ ] **Step 3: Commit the failing route tests**

```bash
cd /Users/yann.moren/vision
git add backend/tests/api/test_pack_routes.py
git commit -m "test: describe pack manifest API routes"
```

## Task 6: Implement Pack API Routes And Wire Services

**Files:**

- Create: `backend/src/argus/api/v1/packs.py`
- Modify: `backend/src/argus/api/v1/__init__.py`
- Modify: `backend/src/argus/services/app.py`
- Test: `backend/tests/api/test_pack_routes.py`

- [ ] **Step 1: Add the route module**

Create `backend/src/argus/api/v1/packs.py`:

```python
from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status

from argus.api.contracts import PackListResponse, PackManifestResponse
from argus.api.dependencies import get_app_services
from argus.core.security import AuthenticatedUser, require
from argus.models.enums import RoleEnum
from argus.services.app import AppServices
from argus.services.pack_registry import PackManifest

router = APIRouter(prefix="/api/v1/packs", tags=["packs"])
ViewerUser = Annotated[AuthenticatedUser, Depends(require(RoleEnum.VIEWER))]
ServicesDependency = Annotated[AppServices, Depends(get_app_services)]


@router.get("", response_model=PackListResponse)
async def list_packs(
    current_user: ViewerUser,
    services: ServicesDependency,
) -> PackListResponse:
    return PackListResponse(
        packs=[_manifest_response(manifest) for manifest in services.packs.list_packs()]
    )


@router.get("/{pack_id}", response_model=PackManifestResponse)
async def get_pack(
    pack_id: str,
    current_user: ViewerUser,
    services: ServicesDependency,
) -> PackManifestResponse:
    try:
        manifest = services.packs.get_pack(pack_id)
    except KeyError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Pack not found.",
        ) from exc
    return _manifest_response(manifest)


def _manifest_response(manifest: PackManifest) -> PackManifestResponse:
    data = manifest.model_dump(mode="python")
    data["is_runtime_enabled"] = manifest.is_runtime_enabled
    return PackManifestResponse.model_validate(data)
```

- [ ] **Step 2: Register the router**

Modify `backend/src/argus/api/v1/__init__.py`.

Add `packs` to the import group:

```python
from argus.api.v1 import (
    cameras,
    configuration,
    deployment,
    edge,
    export,
    history,
    incident_rules,
    incidents,
    model_catalog,
    models,
    operations,
    packs,
    policy_drafts,
    query,
    runtime_artifacts,
    runtime_soak,
    sites,
    streams,
    system,
    telemetry_ws,
)
```

Add this include after the model catalog router:

```python
router.include_router(packs.router)
```

- [ ] **Step 3: Wire the pack registry into `AppServices`**

Modify `backend/src/argus/services/app.py`.

Add this import near the existing service imports:

```python
from argus.services.pack_registry import PackRegistry
```

Add a field to `AppServices`:

```python
@dataclass(slots=True)
class AppServices:
    tenancy: TenancyService
    sites: SiteService
    cameras: CameraService
    models: ModelService
    packs: PackRegistry
    runtime_artifacts: RuntimeArtifactService
    runtime_soak: RuntimeSoakService
    privacy_manifests: PrivacyManifestService
    scene_contracts: SceneContractService
    incident_rules: IncidentRuleService
    policy_drafts: PolicyDraftService
    configuration: OperatorConfigurationService
    local_first_sync: LocalFirstEvidenceSyncService
    edge: EdgeService
    deployment: DeploymentNodeService
    operations: OperationsService
    history: HistoryService
    incidents: IncidentService
    streams: StreamService
    query: QueryService
    telemetry: NatsTelemetryService
```

Add the service to `build_app_services()`:

```python
    return AppServices(
        tenancy=TenancyService(db.session_factory, settings),
        sites=SiteService(db.session_factory, audit_logger),
        cameras=camera_service,
        models=ModelService(db.session_factory, audit_logger),
        packs=PackRegistry(),
        runtime_artifacts=RuntimeArtifactService(db.session_factory),
        runtime_soak=RuntimeSoakService(db.session_factory),
        privacy_manifests=PrivacyManifestService(db.session_factory),
```

- [ ] **Step 4: Run route tests**

Run:

```bash
cd /Users/yann.moren/vision/backend
uv run pytest tests/api/test_pack_routes.py -q
```

Expected:

- All route tests pass.

- [ ] **Step 5: Run service and route checks together**

Run:

```bash
cd /Users/yann.moren/vision/backend
uv run pytest tests/services/test_pack_registry.py tests/api/test_pack_routes.py -q
uv run ruff check src/argus/services/pack_registry.py src/argus/api/v1/packs.py src/argus/api/v1/__init__.py src/argus/services/app.py tests/services/test_pack_registry.py tests/api/test_pack_routes.py
uv run mypy src/argus/services/pack_registry.py src/argus/api/v1/packs.py
```

Expected:

- Tests pass.
- Ruff reports no issues.
- Mypy reports success.

- [ ] **Step 6: Commit**

```bash
cd /Users/yann.moren/vision
git add backend/src/argus/api/v1/packs.py backend/src/argus/api/v1/__init__.py backend/src/argus/services/app.py backend/tests/api/test_pack_routes.py
git commit -m "feat: expose read-only pack manifest routes"
```

## Task 7: Add Core Boundary Governance Test

**Files:**

- Create: `backend/tests/core/test_pack_boundaries.py`

- [ ] **Step 1: Add the boundary test**

Create `backend/tests/core/test_pack_boundaries.py`:

```python
from __future__ import annotations

from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]

CORE_FILES = [
    REPO_ROOT / "backend/src/argus/api/contracts.py",
    REPO_ROOT / "backend/src/argus/services/app.py",
    REPO_ROOT / "backend/src/argus/models/tables.py",
]

FORBIDDEN_VERTICAL_NOUNS = [
    "Vessel",
    "Voyage",
    "PortCall",
    "AISPosition",
    "NMEAReading",
    "CarrierTerminal",
    "Intersection",
    "Approach",
    "Movement",
    "CurbZone",
    "SignalPhase",
    "TrafficStudy",
    "ConflictEvent",
]


def test_core_contracts_do_not_define_pack_vertical_nouns() -> None:
    offenders: list[str] = []
    for path in CORE_FILES:
        text = path.read_text(encoding="utf-8")
        for noun in FORBIDDEN_VERTICAL_NOUNS:
            if noun in text:
                offenders.append(f"{path.relative_to(REPO_ROOT)} contains {noun}")

    assert offenders == []
```

- [ ] **Step 2: Run the governance test**

Run:

```bash
cd /Users/yann.moren/vision/backend
uv run pytest tests/core/test_pack_boundaries.py -q
```

Expected:

- The test passes.

- [ ] **Step 3: Run targeted backend tests**

Run:

```bash
cd /Users/yann.moren/vision/backend
uv run pytest tests/services/test_pack_registry.py tests/api/test_pack_routes.py tests/core/test_pack_boundaries.py -q
```

Expected:

- All targeted tests pass.

- [ ] **Step 4: Commit**

```bash
cd /Users/yann.moren/vision
git add backend/tests/core/test_pack_boundaries.py
git commit -m "test: protect core from pack vertical nouns"
```

## Task 8: Final Verification And Documentation Check

**Files:**

- Verify: `docs/strategy/2026-06-05-vezor-fleetops-wedge-and-scene-engine-blueprint.md`
- Verify: `docs/superpowers/specs/2026-06-05-one-pack-sceneops-engine-pack-boundary-design.md`
- Verify: `docs/superpowers/plans/2026-06-05-one-pack-sceneops-pack-boundary.md`
- Verify: `packs/README.md`
- Verify: `packs/maritime-fleet/pack.yaml`
- Verify: `packs/traffic-public-space/pack.yaml`
- Verify: backend registry and route files from earlier tasks

- [ ] **Step 1: Run targeted tests**

Run:

```bash
cd /Users/yann.moren/vision/backend
uv run pytest tests/services/test_pack_registry.py tests/api/test_pack_routes.py tests/core/test_pack_boundaries.py -q
```

Expected:

- All targeted tests pass.

- [ ] **Step 2: Run lint on changed backend files**

Run:

```bash
cd /Users/yann.moren/vision/backend
uv run ruff check src/argus/services/pack_registry.py src/argus/api/v1/packs.py src/argus/api/v1/__init__.py src/argus/services/app.py src/argus/api/contracts.py tests/services/test_pack_registry.py tests/api/test_pack_routes.py tests/core/test_pack_boundaries.py
```

Expected:

- Ruff reports no issues.

- [ ] **Step 3: Run type checks on the new service and route**

Run:

```bash
cd /Users/yann.moren/vision/backend
uv run mypy src/argus/services/pack_registry.py src/argus/api/v1/packs.py
```

Expected:

- Mypy reports success.

- [ ] **Step 4: Inspect the API output manually**

Run:

```bash
cd /Users/yann.moren/vision/backend
uv run python - <<'PY'
from argus.services.pack_registry import PackRegistry

registry = PackRegistry()
for manifest in registry.list_packs():
    print(manifest.metadata.id, manifest.metadata.status, manifest.is_runtime_enabled)
PY
```

Expected:

```text
maritime-fleet planned_mvp True
traffic-public-space designed_not_implemented False
```

- [ ] **Step 5: Confirm no accidental traffic or maritime runtime modules were added**

Run:

```bash
cd /Users/yann.moren/vision
find backend/src/argus -maxdepth 2 -type d \( -name 'maritime*' -o -name 'traffic*' \) -print
```

Expected:

- No output.

- [ ] **Step 6: Review staged scope before final commit**

Run:

```bash
cd /Users/yann.moren/vision
git status --short
git diff --stat HEAD
```

Expected:

- Only pack registry, pack routes, tests, dependency lock, and documentation
  files from this plan are present.
- Do not stage `taste-skill/`, scratch screenshots, `.claude/`, `.codex/`, or
  unrelated untracked files.

- [ ] **Step 7: Commit final documentation updates if they changed during implementation**

```bash
cd /Users/yann.moren/vision
git add docs/strategy/2026-06-05-vezor-fleetops-wedge-and-scene-engine-blueprint.md docs/superpowers/specs/2026-06-05-one-pack-sceneops-engine-pack-boundary-design.md docs/superpowers/plans/2026-06-05-one-pack-sceneops-pack-boundary.md packs/README.md packs/maritime-fleet/pack.yaml packs/traffic-public-space/pack.yaml
git commit -m "docs: lock one-pack SceneOps pack boundary"
```

## Completion Criteria

- `GET /api/v1/packs` returns Maritime as `planned_mvp` and Traffic/Public-Space
  as `designed_not_implemented`.
- `GET /api/v1/packs/traffic-public-space` returns the manifest but
  `is_runtime_enabled` is false.
- The pack registry loads YAML manifests as data and imports no pack runtime
  module.
- Core API contracts, service container, and database models do not define
  vertical pack nouns.
- The strategy blueprint, design spec, implementation plan, and pack manifests
  agree on one commercial pack and one designed-only future target.

## Execution Notes For Subagents

- Keep one task per subagent when possible.
- Review `git diff --stat` after each task.
- Stage only files named in the task.
- Do not create `argus.maritime`, `argus.traffic_public_space`, traffic UI
  routes, public-space pricing, or maritime entity database migrations in this
  plan.
- If a test requires adding a vertical noun to `backend/src/argus/api/contracts.py`,
  stop and revise the registry design instead.

## Self-Review

- Spec coverage: every spec acceptance criterion maps to Task 1 through Task 8.
- Placeholder scan: every task has concrete files, code, commands, and expected
  outcomes.
- Type consistency: service names, response model names, and route paths are
  consistent across tests, implementation, and API contracts.
