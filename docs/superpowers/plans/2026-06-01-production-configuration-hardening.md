# Production Configuration Hardening Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make every visible Control Plane -> Configuration option either enforce real runtime behavior, validate its prerequisites, or render as blocked with a precise operator reason.

**Architecture:** Implement a shared backend truth model first: capability catalog, binding inventory, impact previews, safe default rules, and desired/applied configuration summaries. After that foundation lands, harden each runtime kind behind the same contracts: evidence/privacy, transport routing, runtime selection, LLM provider execution, and Operations lifecycle modes.

**Tech Stack:** FastAPI, SQLAlchemy, Pydantic, NATS JetStream, existing supervisor services, React, TanStack Query, OpenAPI generated TypeScript, Vitest, pytest, Playwright/manual browser QA.

---

## Scope Check

The approved spec covers multiple independent runtime subsystems. Treat this as
a master implementation plan with phase gates:

- Tasks 1-5 are the shared foundation and must be implemented sequentially.
- Tasks 6-10 can be implemented by separate workers after Task 5 lands because
  they own disjoint runtime areas.
- Task 11 integrates UI polish, documentation, and final verification after all
  runtime tracks are merged.

Do not start Tasks 6-10 before the generated frontend API types include the
Task 1-5 shared contracts.

## File Structure And Ownership

Shared backend contracts:

- Modify `backend/src/argus/api/contracts.py`: capability, impact, binding
  inventory, applied configuration, and diagnostics response schemas.
- Modify `backend/src/argus/api/v1/configuration.py`: new profile impact and
  binding list/delete endpoints.
- Modify `backend/src/argus/services/operator_configuration.py`: catalog,
  default protection, profile impact, binding validation, binding list/delete.
- Modify `backend/src/argus/services/runtime_configuration.py`: richer resolved
  entries and helper methods for affected target counts.
- Create `backend/src/argus/services/configuration_capabilities.py`: single
  backend source of truth for field support states and service prerequisites.
- Test `backend/tests/services/test_operator_configuration.py`.
- Test `backend/tests/api/test_configuration_endpoints.py`.

Applied runtime reporting:

- Modify `backend/src/argus/api/contracts.py`: applied configuration summary
  schemas in worker config, runtime passport, and fleet summaries.
- Modify `backend/src/argus/services/app.py`: build desired/applied summaries.
- Modify `backend/src/argus/services/runtime_passports.py`: include applied
  configuration in passport payload and summaries.
- Modify `backend/src/argus/services/supervisor_operations.py`: persist applied
  configuration reported by workers when present.
- Test `backend/tests/services/test_camera_worker_config.py`.
- Test `backend/tests/services/test_operations_service.py`.

Frontend shared UX:

- Modify `frontend/src/hooks/use-configuration.ts`: capability, impact,
  binding inventory, and delete binding hooks.
- Regenerate `frontend/src/lib/api.generated.ts`.
- Modify `frontend/src/components/configuration/ConfigurationWorkspace.tsx`.
- Modify `frontend/src/components/configuration/ProfileEditor.tsx`.
- Modify `frontend/src/components/configuration/ProfileBindingPanel.tsx`.
- Modify `frontend/src/components/configuration/EffectiveConfigurationPanel.tsx`.
- Create `frontend/src/components/configuration/ProfileInventory.tsx`.
- Create `frontend/src/components/configuration/ProfileImpactDialog.tsx`.
- Create `frontend/src/components/configuration/RuntimeImpactPanel.tsx`.
- Create `frontend/src/components/configuration/configuration-capabilities.ts`.
- Test `frontend/src/components/configuration/*.test.tsx`.
- Test `frontend/src/hooks/use-configuration.test.ts`.

Runtime hardening tracks:

- Evidence/privacy: `backend/src/argus/services/evidence_storage.py`,
  `backend/src/argus/services/privacy_policy_runtime.py`,
  `backend/src/argus/services/incident_capture.py`,
  `backend/src/argus/services/privacy_manifests.py`.
- Transport: `backend/src/argus/services/app.py`, stream endpoints under
  `backend/src/argus/api/v1/streams.py`, Live player utilities under
  `frontend/src/pages/Live.tsx` and `frontend/src/lib/hls.ts`.
- Runtime selection: `backend/src/argus/services/model_admission.py`,
  `backend/src/argus/services/runtime_passports.py`,
  `backend/src/argus/services/runtime_soak.py`.
- LLM provider: `backend/src/argus/services/llm_provider_runtime.py`,
  `backend/src/argus/services/policy_drafts.py`.
- Operations: `backend/src/argus/services/supervisor_operations.py`,
  supervisor runner modules, `frontend/src/components/operations/*`.

## Task 1: Capability Catalog Contracts

**Files:**

- Modify: `backend/src/argus/api/contracts.py`
- Create: `backend/src/argus/services/configuration_capabilities.py`
- Modify: `backend/src/argus/services/operator_configuration.py`
- Test: `backend/tests/services/test_operator_configuration.py`

- [ ] **Step 1: Write failing service test for capability catalog**

Add this test to `backend/tests/services/test_operator_configuration.py`:

```python
async def test_configuration_catalog_exposes_field_support_states(configuration_service):
    catalog = await configuration_service.list_catalog()

    kinds = {entry["kind"]: entry for entry in catalog["kinds"]}
    operations = kinds["operations_mode"]
    supervisor_mode = next(
        field for field in operations["fields"] if field["name"] == "supervisor_mode"
    )

    values = {item["value"]: item for item in supervisor_mode["values"]}
    assert operations["runtime_support"] == "active"
    assert values["polling"]["support"] == "active"
    assert values["push"]["support"] in {"active", "requires_service"}
    assert values["push"]["operator_message"]
```

- [ ] **Step 2: Run the failing test**

Run:

```bash
python3 -m uv run --project backend pytest backend/tests/services/test_operator_configuration.py::test_configuration_catalog_exposes_field_support_states -q
```

Expected: FAIL because `fields`, `runtime_support`, and support-state metadata
are not returned yet.

- [ ] **Step 3: Add capability response models**

In `backend/src/argus/api/contracts.py`, add:

```python
OperatorConfigSupportState = Literal["active", "advisory", "requires_service", "unsupported"]


class OperatorConfigValueCapability(BaseModel):
    value: str
    support: OperatorConfigSupportState
    requires: list[str] = Field(default_factory=list)
    operator_message: str | None = None


class OperatorConfigFieldCapability(BaseModel):
    name: str
    label: str
    support: OperatorConfigSupportState
    requires: list[str] = Field(default_factory=list)
    operator_message: str | None = None
    values: list[OperatorConfigValueCapability] = Field(default_factory=list)


class OperatorConfigKindCapability(BaseModel):
    kind: OperatorConfigProfileKind
    label: str
    runtime_support: OperatorConfigSupportState
    operator_summary: str
    fields: list[OperatorConfigFieldCapability] = Field(default_factory=list)
```

Update the catalog response type documentation in the same file if the OpenAPI
generator exposes an anonymous object for `list_configuration_catalog`.

- [ ] **Step 4: Create backend capability source**

Create `backend/src/argus/services/configuration_capabilities.py`:

```python
from __future__ import annotations

from argus.api.contracts import (
    OperatorConfigFieldCapability,
    OperatorConfigKindCapability,
    OperatorConfigValueCapability,
)
from argus.models.enums import OperatorConfigProfileKind


def configuration_capabilities(*, nats_enabled: bool) -> list[OperatorConfigKindCapability]:
    push_support = "active" if nats_enabled else "requires_service"
    push_message = (
        "Push lifecycle requests require NATS supervisor acknowledgement."
        if nats_enabled
        else "Enable NATS supervisor push before binding push operations profiles."
    )
    return [
        OperatorConfigKindCapability(
            kind=OperatorConfigProfileKind.EVIDENCE_STORAGE,
            label="Evidence storage",
            runtime_support="active",
            operator_summary="Routes incident evidence to local, central, cloud, or local-first storage.",
            fields=[
                OperatorConfigFieldCapability(
                    name="provider",
                    label="Provider",
                    support="active",
                    values=[
                        OperatorConfigValueCapability(value="local_filesystem", support="active"),
                        OperatorConfigValueCapability(value="minio", support="active"),
                        OperatorConfigValueCapability(value="s3_compatible", support="active"),
                        OperatorConfigValueCapability(value="local_first", support="active"),
                    ],
                )
            ],
        ),
        OperatorConfigKindCapability(
            kind=OperatorConfigProfileKind.STREAM_DELIVERY,
            label="Transport profile",
            runtime_support="active",
            operator_summary="Selects the browser stream route and stream service prerequisites.",
            fields=[
                OperatorConfigFieldCapability(
                    name="delivery_mode",
                    label="Transport mode",
                    support="active",
                    values=[
                        OperatorConfigValueCapability(value="native", support="active"),
                        OperatorConfigValueCapability(value="webrtc", support="active"),
                        OperatorConfigValueCapability(value="hls", support="active"),
                        OperatorConfigValueCapability(value="mjpeg", support="active"),
                        OperatorConfigValueCapability(
                            value="transcode",
                            support="unsupported",
                            operator_message="Use camera live rendition profiles for transcoding.",
                        ),
                    ],
                )
            ],
        ),
        OperatorConfigKindCapability(
            kind=OperatorConfigProfileKind.RUNTIME_SELECTION,
            label="Runtime selection",
            runtime_support="active",
            operator_summary="Ranks runtime backends and model artifacts before worker start.",
        ),
        OperatorConfigKindCapability(
            kind=OperatorConfigProfileKind.PRIVACY_POLICY,
            label="Privacy policy",
            runtime_support="active",
            operator_summary="Controls residency, plaintext plate posture, quota, and retention.",
        ),
        OperatorConfigKindCapability(
            kind=OperatorConfigProfileKind.LLM_PROVIDER,
            label="LLM provider",
            runtime_support="active",
            operator_summary="Provides model and credential settings for policy draft assistance.",
        ),
        OperatorConfigKindCapability(
            kind=OperatorConfigProfileKind.OPERATIONS_MODE,
            label="Operations mode",
            runtime_support="active",
            operator_summary="Controls worker lifecycle ownership, supervisor mode, and restart policy.",
            fields=[
                OperatorConfigFieldCapability(
                    name="supervisor_mode",
                    label="Supervisor mode",
                    support="active",
                    values=[
                        OperatorConfigValueCapability(value="disabled", support="active"),
                        OperatorConfigValueCapability(value="polling", support="active"),
                        OperatorConfigValueCapability(
                            value="push",
                            support=push_support,
                            requires=["nats"],
                            operator_message=push_message,
                        ),
                    ],
                )
            ],
        ),
    ]
```

- [ ] **Step 5: Wire catalog through configuration service**

In `OperatorConfigurationService.list_catalog`, replace the current static
catalog list with:

```python
from argus.services.configuration_capabilities import configuration_capabilities

async def list_catalog(self) -> dict[str, object]:
    return {
        "kinds": [
            item.model_dump(mode="json")
            for item in configuration_capabilities(nats_enabled=self.settings.enable_nats)
        ]
    }
```

- [ ] **Step 6: Run capability catalog tests**

Run:

```bash
python3 -m uv run --project backend pytest backend/tests/services/test_operator_configuration.py::test_configuration_catalog_exposes_field_support_states -q
```

Expected: PASS.

## Task 2: Binding Inventory, Unbind, Impact, And Default Safety

**Files:**

- Modify: `backend/src/argus/api/contracts.py`
- Modify: `backend/src/argus/api/v1/configuration.py`
- Modify: `backend/src/argus/services/operator_configuration.py`
- Modify: `backend/src/argus/services/runtime_configuration.py`
- Test: `backend/tests/services/test_operator_configuration.py`
- Test: `backend/tests/api/test_configuration_endpoints.py`

- [ ] **Step 1: Write failing tests for safe delete and unbind**

Add service tests:

```python
async def test_delete_default_profile_requires_replacement(configuration_service, tenant_context):
    profiles = await configuration_service.list_profiles(tenant_context, kind=OperatorConfigProfileKind.OPERATIONS_MODE)
    default_profile = next(profile for profile in profiles if profile.is_default)

    with pytest.raises(HTTPException) as exc_info:
        await configuration_service.delete_profile(tenant_context, default_profile.id)

    assert exc_info.value.status_code == 409
    assert "replacement default" in str(exc_info.value.detail).lower()


async def test_list_and_delete_configuration_binding(configuration_service, tenant_context, camera):
    profiles = await configuration_service.list_profiles(tenant_context, kind=OperatorConfigProfileKind.OPERATIONS_MODE)
    profile = next(profile for profile in profiles if profile.enabled)
    binding = await configuration_service.upsert_binding(
        tenant_context,
        OperatorConfigBindingRequest(
            kind=OperatorConfigProfileKind.OPERATIONS_MODE,
            scope=OperatorConfigScope.CAMERA,
            scope_key=str(camera.id),
            profile_id=profile.id,
        ),
    )

    bindings = await configuration_service.list_bindings(tenant_context, kind=OperatorConfigProfileKind.OPERATIONS_MODE)
    assert any(item.id == binding.id for item in bindings)

    await configuration_service.delete_binding(tenant_context, binding.id)
    bindings_after = await configuration_service.list_bindings(tenant_context, kind=OperatorConfigProfileKind.OPERATIONS_MODE)
    assert all(item.id != binding.id for item in bindings_after)
```

- [ ] **Step 2: Run failing tests**

Run:

```bash
python3 -m uv run --project backend pytest backend/tests/services/test_operator_configuration.py -k "default_profile_requires_replacement or list_and_delete_configuration_binding" -q
```

Expected: FAIL because binding inventory/delete and replacement-default
protection are not implemented.

- [ ] **Step 3: Add response/request schemas**

In `backend/src/argus/api/contracts.py`, add:

```python
class OperatorConfigBindingListResponse(BaseModel):
    bindings: list[OperatorConfigBindingResponse] = Field(default_factory=list)


class OperatorConfigProfileImpactResponse(BaseModel):
    profile_id: UUID
    kind: OperatorConfigProfileKind
    is_default: bool
    direct_bindings: list[OperatorConfigBindingResponse] = Field(default_factory=list)
    affected_targets_count: int = 0
    requires_replacement_default: bool = False
    secret_state: dict[str, OperatorSecretState] = Field(default_factory=dict)


class OperatorConfigProfileDeleteRequest(BaseModel):
    replacement_default_profile_id: UUID | None = None
```

- [ ] **Step 4: Implement binding service methods**

Add to `OperatorConfigurationService`:

```python
async def list_bindings(
    self,
    tenant_context: TenantContext,
    *,
    kind: OperatorConfigProfileKind | None = None,
) -> list[OperatorConfigBindingResponse]:
    async with self.session_factory() as session:
        rows = await self._load_bindings(session, tenant_context.tenant_id, kind=kind)
    return [_binding_to_response(row) for row in rows]


async def delete_binding(self, tenant_context: TenantContext, binding_id: UUID) -> None:
    async with self.session_factory() as session:
        bindings = await self._load_bindings(session, tenant_context.tenant_id)
        binding = next((row for row in bindings if row.id == binding_id), None)
        if binding is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Configuration binding not found.")
        await session.delete(binding)
        await session.commit()
    await self._record(
        tenant_context,
        action="configuration.binding.delete",
        target=f"configuration-binding:{binding_id}",
        meta={"kind": binding.kind.value, "scope": binding.scope.value, "scope_key": binding.scope_key},
    )
```

- [ ] **Step 5: Add impact and safe default deletion**

Update `delete_profile` signature:

```python
async def delete_profile(
    self,
    tenant_context: TenantContext,
    profile_id: UUID,
    *,
    replacement_default_profile_id: UUID | None = None,
) -> None:
```

Before deleting the profile, enforce:

```python
if profile.is_default:
    if replacement_default_profile_id is None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Deleting a default profile requires a replacement default profile.",
        )
    replacement = await self._get_profile(session, tenant_context.tenant_id, replacement_default_profile_id)
    if replacement.kind != profile.kind or not replacement.enabled or replacement.id == profile.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Replacement default profile must be an enabled profile of the same kind.",
        )
    replacement.is_default = True
```

Add `profile_impact` that returns direct bindings, secret state, and
`requires_replacement_default`.

- [ ] **Step 6: Wire API endpoints**

In `backend/src/argus/api/v1/configuration.py`, add:

```python
@router.get("/profiles/{profile_id}/impact", response_model=OperatorConfigProfileImpactResponse)
async def get_configuration_profile_impact(
    profile_id: UUID,
    current_user: ViewerUser,
    tenant_context: TenantDependency,
    services: ServicesDependency,
) -> OperatorConfigProfileImpactResponse:
    return await services.configuration.profile_impact(tenant_context, profile_id)


@router.get("/bindings", response_model=OperatorConfigBindingListResponse)
async def list_configuration_bindings(
    current_user: ViewerUser,
    tenant_context: TenantDependency,
    services: ServicesDependency,
    kind: ConfigKindQuery = None,
) -> OperatorConfigBindingListResponse:
    return OperatorConfigBindingListResponse(
        bindings=await services.configuration.list_bindings(tenant_context, kind=kind)
    )


@router.delete("/bindings/{binding_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_configuration_binding(
    binding_id: UUID,
    current_user: AdminUser,
    tenant_context: TenantDependency,
    services: ServicesDependency,
) -> Response:
    await services.configuration.delete_binding(tenant_context, binding_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
```

Update profile delete to accept `OperatorConfigProfileDeleteRequest | None`.

- [ ] **Step 7: Run backend configuration tests**

Run:

```bash
python3 -m uv run --project backend pytest backend/tests/services/test_operator_configuration.py backend/tests/api/test_configuration_endpoints.py -q
```

Expected: PASS.

## Task 3: Binding Validation And Resolution Messages

**Files:**

- Modify: `backend/src/argus/services/operator_configuration.py`
- Modify: `backend/src/argus/services/runtime_configuration.py`
- Test: `backend/tests/services/test_operator_configuration.py`

- [ ] **Step 1: Write failing tests for invalid binding cases**

Add tests:

```python
async def test_binding_rejects_unvalidated_profile(configuration_service, tenant_context, camera):
    profile = await configuration_service.create_profile(
        tenant_context,
        OperatorConfigProfileCreate(
            kind=OperatorConfigProfileKind.OPERATIONS_MODE,
            scope=OperatorConfigScope.TENANT,
            name="Unvalidated edge push",
            slug="unvalidated-edge-push",
            config={"lifecycle_owner": "edge_supervisor", "supervisor_mode": "push", "restart_policy": "on_failure"},
            enabled=True,
            is_default=False,
        ),
    )

    with pytest.raises(HTTPException) as exc_info:
        await configuration_service.upsert_binding(
            tenant_context,
            OperatorConfigBindingRequest(
                kind=OperatorConfigProfileKind.OPERATIONS_MODE,
                scope=OperatorConfigScope.CAMERA,
                scope_key=str(camera.id),
                profile_id=profile.id,
            ),
        )

    assert exc_info.value.status_code == 400
    assert "test profile" in str(exc_info.value.detail).lower()
```

- [ ] **Step 2: Run failing validation test**

Run:

```bash
python3 -m uv run --project backend pytest backend/tests/services/test_operator_configuration.py::test_binding_rejects_unvalidated_profile -q
```

Expected: FAIL because unvalidated profiles can still be bound.

- [ ] **Step 3: Add `_assert_profile_bindable`**

In `OperatorConfigurationService`, add:

```python
def _assert_profile_bindable(self, profile: OperatorConfigProfile) -> None:
    if not profile.enabled:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Disabled configuration profiles cannot be bound.")
    if profile.validation_status is not OperatorConfigValidationStatus.VALID:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Test profile successfully before binding it.")
```

Call it from `upsert_binding` after kind validation.

- [ ] **Step 4: Add target existence validation**

Add a service helper:

```python
async def _assert_binding_target_exists(
    self,
    session: AsyncSession,
    tenant_id: UUID,
    scope: OperatorConfigScope,
    scope_key: str,
) -> None:
    if scope is OperatorConfigScope.TENANT:
        return
    target_id = UUID(scope_key)
    if scope is OperatorConfigScope.CAMERA:
        await _load_camera(session, tenant_id, target_id)
        return
    if scope is OperatorConfigScope.SITE:
        await _load_site(session, tenant_id, target_id)
        return
    if scope is OperatorConfigScope.EDGE_NODE:
        await _load_edge_node(session, tenant_id, target_id)
        return
```

Use existing local loader equivalents where names differ; keep the helper in
`operator_configuration.py` so binding validation remains centralized.

- [ ] **Step 5: Run binding validation tests**

Run:

```bash
python3 -m uv run --project backend pytest backend/tests/services/test_operator_configuration.py -k "binding" -q
```

Expected: PASS.

## Task 4: Applied Configuration Summaries

**Files:**

- Modify: `backend/src/argus/api/contracts.py`
- Modify: `backend/src/argus/services/app.py`
- Modify: `backend/src/argus/services/runtime_passports.py`
- Modify: `backend/src/argus/services/supervisor_operations.py`
- Test: `backend/tests/services/test_camera_worker_config.py`
- Test: `backend/tests/services/test_operations_service.py`

- [ ] **Step 1: Write failing worker config test**

Add:

```python
async def test_worker_config_includes_applied_configuration_summary(camera_service, tenant_context, camera):
    config = await camera_service.get_worker_config(tenant_context, camera.id)

    assert config.configuration.evidence_storage.profile_hash
    assert config.configuration.stream_delivery.profile_hash
    assert config.configuration.runtime_selection.profile_hash
    assert config.configuration.privacy_policy.profile_hash
```

- [ ] **Step 2: Run failing worker config test**

Run:

```bash
python3 -m uv run --project backend pytest backend/tests/services/test_camera_worker_config.py::test_worker_config_includes_applied_configuration_summary -q
```

Expected: FAIL because `WorkerConfigResponse.configuration` does not exist.

- [ ] **Step 3: Add summary schemas**

In `contracts.py`, add:

```python
class AppliedOperatorConfigRef(BaseModel):
    profile_id: UUID | None = None
    profile_name: str | None = None
    profile_hash: str | None = None
    support: OperatorConfigSupportState = "active"
    operator_message: str | None = None


class AppliedRuntimeSelectionConfigRef(AppliedOperatorConfigRef):
    selected_backend: str | None = None
    selected_artifact_id: UUID | None = None
    fallback_reason: str | None = None


class AppliedOperatorConfigurationSummary(BaseModel):
    evidence_storage: AppliedOperatorConfigRef = Field(default_factory=AppliedOperatorConfigRef)
    stream_delivery: AppliedOperatorConfigRef = Field(default_factory=AppliedOperatorConfigRef)
    runtime_selection: AppliedRuntimeSelectionConfigRef = Field(default_factory=AppliedRuntimeSelectionConfigRef)
    privacy_policy: AppliedOperatorConfigRef = Field(default_factory=AppliedOperatorConfigRef)
    llm_provider: AppliedOperatorConfigRef = Field(default_factory=AppliedOperatorConfigRef)
    operations_mode: AppliedOperatorConfigRef = Field(default_factory=AppliedOperatorConfigRef)
```

Add `configuration: AppliedOperatorConfigurationSummary` to
`WorkerConfigResponse`, runtime passport summary contracts, and fleet worker
summary where applicable.

- [ ] **Step 4: Build summary in `app.py`**

Add helper:

```python
def _operator_config_ref(profile: object | None) -> AppliedOperatorConfigRef:
    return AppliedOperatorConfigRef(
        profile_id=getattr(profile, "profile_id", None),
        profile_name=getattr(profile, "profile_name", None),
        profile_hash=getattr(profile, "profile_hash", None),
    )
```

When building `WorkerConfigResponse`, set:

```python
configuration=AppliedOperatorConfigurationSummary(
    evidence_storage=_operator_config_ref(evidence_storage),
    stream_delivery=_operator_config_ref(stream_delivery),
    runtime_selection=AppliedRuntimeSelectionConfigRef(
        profile_id=runtime_selection.profile_id if runtime_selection else None,
        profile_name=runtime_selection.profile_name if runtime_selection else None,
        profile_hash=runtime_selection.profile_hash if runtime_selection else None,
        selected_backend=runtime_selection.preferred_backend if runtime_selection else None,
    ),
    privacy_policy=_operator_config_ref(privacy_policy),
)
```

- [ ] **Step 5: Pass summary into runtime passports**

Update `build_runtime_passport` to accept
`configuration: Mapping[str, object] | None` and store it under a stable
`configuration` key. Existing callers pass `config.configuration.model_dump(mode="json")`.

- [ ] **Step 6: Run applied configuration tests**

Run:

```bash
python3 -m uv run --project backend pytest backend/tests/services/test_camera_worker_config.py backend/tests/services/test_operations_service.py -q
```

Expected: PASS.

## Task 5: Frontend Shared Configuration UX

**Files:**

- Modify: `frontend/src/hooks/use-configuration.ts`
- Modify: `frontend/src/components/configuration/ConfigurationWorkspace.tsx`
- Modify: `frontend/src/components/configuration/ProfileEditor.tsx`
- Modify: `frontend/src/components/configuration/ProfileBindingPanel.tsx`
- Modify: `frontend/src/components/configuration/EffectiveConfigurationPanel.tsx`
- Create: `frontend/src/components/configuration/ProfileInventory.tsx`
- Create: `frontend/src/components/configuration/ProfileImpactDialog.tsx`
- Create: `frontend/src/components/configuration/RuntimeImpactPanel.tsx`
- Create: `frontend/src/components/configuration/configuration-capabilities.ts`
- Test: `frontend/src/hooks/use-configuration.test.ts`
- Test: `frontend/src/components/configuration/ConfigurationWorkspace.test.tsx`
- Test: `frontend/src/components/configuration/ProfileEditor.test.tsx`
- Test: `frontend/src/components/configuration/EffectiveConfigurationPanel.test.tsx`

- [ ] **Step 1: Regenerate API types**

Run:

```bash
corepack pnpm generate:api
```

Expected: `frontend/src/lib/api.generated.ts` contains capability, impact, and
binding inventory schemas.

- [ ] **Step 2: Add hook tests**

Create `frontend/src/hooks/use-configuration.test.ts` with tests that mock:

```ts
GET /api/v1/configuration/bindings
DELETE /api/v1/configuration/bindings/{binding_id}
GET /api/v1/configuration/profiles/{profile_id}/impact
DELETE /api/v1/configuration/profiles/{profile_id}
```

Assert each hook invalidates `["configuration"]`.

- [ ] **Step 3: Add hooks**

In `use-configuration.ts`, add:

```ts
export function useConfigurationBindings(kind?: OperatorConfigKind) {
  return useQuery({
    queryKey: ["configuration", "bindings", kind ?? "all"],
    queryFn: async () => {
      const { data, error } = await apiClient.GET("/api/v1/configuration/bindings", {
        params: { query: kind ? { kind } : {} },
      });
      if (error) throw toApiError(error, "Failed to load configuration bindings.");
      return data?.bindings ?? [];
    },
  });
}
```

Add matching `useDeleteConfigurationBinding()` and
`useConfigurationProfileImpact(profileId)`.

- [ ] **Step 4: Build capability helpers**

Create `configuration-capabilities.ts`:

```ts
import type { ConfigurationCatalog, OperatorConfigKind } from "@/hooks/use-configuration";

export function supportForField(
  catalog: ConfigurationCatalog | undefined,
  kind: OperatorConfigKind,
  fieldName: string,
) {
  return catalog?.kinds
    ?.find((entry) => entry.kind === kind)
    ?.fields?.find((field) => field.name === fieldName);
}

export function isUnsupportedValue(
  field: ReturnType<typeof supportForField>,
  value: string,
) {
  return field?.values?.some((option) => option.value === value && option.support === "unsupported") ?? false;
}
```

- [ ] **Step 5: Add profile inventory component**

Create `ProfileInventory.tsx` that renders profile rows with validation,
default, enabled, binding count, duplicate, test, make default, and delete
buttons. Keep row height stable and use existing `StatusToneBadge`.

- [ ] **Step 6: Replace current profile list area**

In `ConfigurationWorkspace.tsx`, compute binding counts from
`useConfigurationBindings(activeKind)` and render `ProfileInventory` in the left
rail. Route delete through `ProfileImpactDialog` before calling profile delete.

- [ ] **Step 7: Add runtime impact panel**

Create `RuntimeImpactPanel.tsx` that receives `kind`, `state`, and `catalog`.
For unsupported fields, render a disabled state and the backend
`operator_message`. Mount it below kind-specific fields in `ProfileEditor`.

- [ ] **Step 8: Expand binding manager**

Update `ProfileBindingPanel` to show existing binding rows plus the current bind
form. Each row has an Unbind button using `useDeleteConfigurationBinding`.

- [ ] **Step 9: Expand effective configuration**

Update `EffectiveConfigurationPanel` to render desired hash, applied hash when
available, support state, drift/aligned badge, and copy-diagnostic JSON action.

- [ ] **Step 10: Run frontend configuration tests**

Run:

```bash
corepack pnpm --dir frontend test src/hooks/use-configuration.test.ts src/components/configuration/ConfigurationWorkspace.test.tsx src/components/configuration/ProfileEditor.test.tsx src/components/configuration/EffectiveConfigurationPanel.test.tsx
```

Expected: PASS.

- [ ] **Step 11: Run frontend build**

Run:

```bash
corepack pnpm --dir frontend build
```

Expected: PASS.

## Task 6: Evidence And Privacy Hardening

**Files:**

- Modify: `backend/src/argus/services/operator_configuration.py`
- Modify: `backend/src/argus/services/evidence_storage.py`
- Modify: `backend/src/argus/services/privacy_policy_runtime.py`
- Modify: `backend/src/argus/services/incident_capture.py`
- Modify: `backend/src/argus/services/privacy_manifests.py`
- Test: `backend/tests/services/test_evidence_storage.py`
- Test: `backend/tests/services/test_privacy_manifests.py`
- Test: `backend/tests/services/test_incident_capture.py`
- Test: `backend/tests/services/test_camera_worker_config.py`

- [ ] **Step 1: Add tests for bind-time evidence/privacy compatibility**

Add a test that creates a privacy profile with `residency: "cloud"` and an
evidence profile resolving to central storage for the same camera. Binding the
second profile must fail with `"Privacy policy residency does not match"`.

- [ ] **Step 2: Add tests for per-camera retention**

Use existing evidence artifact fixtures and create two cameras with privacy
profiles of 1 day and 30 days. Run `PrivacyPolicyRetentionService.mark_expired_artifacts_for_tenant`.
Assert only the 1-day camera's old artifact expires.

- [ ] **Step 3: Add compatibility validator**

In `OperatorConfigurationService.upsert_binding`, after target validation,
resolve the target's complete configuration with the candidate profile
substituted. Call `validate_privacy_policy_residency` with the candidate
evidence/privacy pair before committing.

- [ ] **Step 4: Add retention job entrypoint**

In `privacy_policy_runtime.py`, add:

```python
async def mark_expired_artifacts_for_tenant(
    self,
    *,
    tenant_context: TenantContext,
    runtime_configuration: RuntimeConfigurationService,
    now: datetime | None = None,
) -> PrivacyRetentionRunSummary:
```

The method loads artifact camera IDs, resolves each camera privacy policy, and
calls existing expiration logic per camera policy.

- [ ] **Step 5: Wire retention service startup**

In the backend startup services area, start a bounded interval task only when
startup services are enabled. Store latest run summary in memory and expose it
through configuration diagnostics or catalog metadata.

- [ ] **Step 6: Run evidence/privacy tests**

Run:

```bash
python3 -m uv run --project backend pytest backend/tests/services/test_evidence_storage.py backend/tests/services/test_privacy_manifests.py backend/tests/services/test_incident_capture.py backend/tests/services/test_camera_worker_config.py -q
```

Expected: PASS.

## Task 7: Transport Route Enforcement

**Files:**

- Modify: `backend/src/argus/api/contracts.py`
- Modify: `backend/src/argus/services/operator_configuration.py`
- Modify: `backend/src/argus/services/app.py`
- Modify: `frontend/src/components/configuration/ProfileEditor.tsx`
- Modify: `frontend/src/pages/Live.tsx`
- Test: `backend/tests/services/test_stream_delivery.py`
- Test: `backend/tests/services/test_camera_worker_config.py`
- Test: `frontend/src/pages/Live.test.tsx`

- [ ] **Step 1: Add backend tests for route mode enforcement**

Create `backend/tests/services/test_stream_delivery.py` with cases for `webrtc`,
`hls`, and `mjpeg` profile configs. Assert resolved stream access selects the
matching route and validation fails when required base URLs are empty.

- [ ] **Step 2: Normalize legacy transcode mode**

In `StreamDeliveryProfileConfig`, keep accepting `"transcode"` for existing
stored profiles if needed, but normalize runtime settings to:

```python
delivery_mode = "native" if config.delivery_mode == "transcode" else config.delivery_mode
operator_message = "Transcode route mode was normalized. Use camera live rendition profiles for output size and FPS."
```

- [ ] **Step 3: Enforce route mode in stream URL helpers**

In `app.py`, update browser stream access builders so forced `hls` returns HLS
playlist/resource URLs, forced `mjpeg` returns MJPEG proxy URLs, forced `webrtc`
returns WebRTC/WHEP metadata, and `native` keeps the existing source-aware
choice.

- [ ] **Step 4: Update profile editor route options**

Remove `transcode` from the editable Transport mode select. If an existing
profile contains `delivery_mode: "transcode"`, render a warning and a Normalize
button that saves `delivery_mode: "native"`.

- [ ] **Step 5: Run transport tests**

Run:

```bash
python3 -m uv run --project backend pytest backend/tests/services/test_stream_delivery.py backend/tests/services/test_camera_worker_config.py -q
corepack pnpm --dir frontend test src/pages/Live.test.tsx src/components/configuration/ProfileEditor.test.tsx
```

Expected: PASS.

## Task 8: Runtime Selection Enforcement

**Files:**

- Modify: `backend/src/argus/services/operator_configuration.py`
- Modify: `backend/src/argus/services/model_admission.py`
- Modify: `backend/src/argus/services/runtime_passports.py`
- Modify: `backend/src/argus/services/app.py`
- Test: `backend/tests/services/test_runtime_selection.py`
- Test: `backend/tests/services/test_operations_service.py`

- [ ] **Step 1: Write runtime selection tests**

Create tests that cover:

```python
def test_no_fallback_blocks_when_selected_backend_unavailable(runtime_selector, camera):
    decision = runtime_selector.select_for_camera(
        camera_id=camera.id,
        preferred_backend="tensorrt_engine",
        artifact_preference="tensorrt_first",
        fallback_allowed=False,
        available_artifacts=[],
        available_backends=["onnxruntime"],
    )

    assert decision.selected_backend is None
    assert decision.blocked_reason == (
        "Runtime selection has no compatible artifact and fallback is disabled."
    )


def test_runtime_passport_records_selected_artifact_and_fallback_reason():
    passport = build_runtime_passport(
        camera_id=UUID("11111111-1111-1111-1111-111111111111"),
        model={"id": "model-yolo"},
        stream_profile={"fps": 10},
        runtime_selection={
            "profile_id": "22222222-2222-2222-2222-222222222222",
            "profile_name": "TensorRT first",
            "profile_hash": "a" * 64,
            "backend": "onnxruntime",
            "fallback_reason": "TensorRT artifact unavailable",
        },
    )

    assert passport["selected_runtime"]["backend"] == "onnxruntime"
    assert passport["runtime_selection_profile"]["fallback_reason"] == "TensorRT artifact unavailable"


def test_preferred_backend_changes_model_admission_backend(hardware_report):
    request = WorkerModelAdmissionRequest(
        stream_profile={"fps": 10},
        preferred_backend="tensorrt_engine",
        selected_backend=None,
    )

    decision = evaluate_worker_model_admission(request, hardware_report=hardware_report)

    assert decision.recommended_backend in {"tensorrt_engine", "onnxruntime"}
```

Each test should assert concrete fields on model admission decisions and runtime
passport summaries.

- [ ] **Step 2: Add selection result object**

Create a small dataclass in runtime selection service code:

```python
@dataclass(frozen=True, slots=True)
class RuntimeSelectionDecision:
    selected_backend: str | None
    selected_artifact_id: UUID | None
    fallback_reason: str | None
    blocked_reason: str | None
```

- [ ] **Step 3: Use fallback policy before worker config returns**

When `fallback_allowed` is false and no compatible backend/artifact exists,
raise `HTTPException(status_code=409, detail="Runtime selection has no compatible artifact and fallback is disabled.")`.

- [ ] **Step 4: Propagate decision into applied summary**

Populate `AppliedRuntimeSelectionConfigRef.selected_backend`,
`selected_artifact_id`, and `fallback_reason`.

- [ ] **Step 5: Run runtime selection tests**

Run:

```bash
python3 -m uv run --project backend pytest backend/tests/services/test_runtime_selection.py backend/tests/services/test_operations_service.py -q
```

Expected: PASS.

## Task 9: LLM Provider Runtime

**Files:**

- Modify: `backend/src/argus/services/llm_provider_runtime.py`
- Modify: `backend/src/argus/services/policy_drafts.py`
- Modify: `backend/src/argus/services/operator_configuration.py`
- Test: `backend/tests/services/test_llm_provider_runtime.py`
- Test: `backend/tests/services/test_policy_drafts.py`

- [ ] **Step 1: Add mock-provider tests**

Add tests for:

```python
async def test_policy_draft_uses_resolved_llm_provider(
    policy_draft_service,
    mock_llm_provider,
    tenant_context,
    camera,
):
    mock_llm_provider.queue_response({"rules": [{"name": "High visibility worker near gate"}]})

    draft = await policy_draft_service.create_draft(
        tenant_context=tenant_context,
        camera_id=camera.id,
        payload=PolicyDraftCreate(prompt="alert on workers near gate", use_llm=True),
    )

    assert draft.metadata["llm_assistance"] == "provider_assisted"
    assert draft.metadata["llm_provider"] == "openai"


async def test_missing_required_api_key_blocks_provider_assistance(llm_runtime_service):
    runtime_config = RuntimeOperatorConfig(
        kind=OperatorConfigProfileKind.LLM_PROVIDER,
        profile_id=UUID("11111111-1111-1111-1111-111111111111"),
        profile_name="OpenAI",
        profile_slug="openai",
        profile_hash="a" * 64,
        config={"provider": "openai", "model": "gpt-4.1-mini", "api_key_required": True},
        secrets={},
    )

    with pytest.raises(HTTPException) as exc_info:
        resolved_llm_provider_from_runtime_config(runtime_config)

    assert exc_info.value.status_code == 422


async def test_malformed_provider_output_returns_deterministic_fallback_warning(
    policy_draft_service,
    mock_llm_provider,
    tenant_context,
    camera,
):
    mock_llm_provider.queue_response({"unexpected": "shape"})

    draft = await policy_draft_service.create_draft(
        tenant_context=tenant_context,
        camera_id=camera.id,
        payload=PolicyDraftCreate(prompt="alert on workers near gate", use_llm=True),
    )

    assert draft.metadata["llm_assistance"] == "provider_rejected"
    assert draft.metadata["llm_fallback"] == "deterministic"
```

- [ ] **Step 2: Add provider client protocol**

In `llm_provider_runtime.py`, add:

```python
class LLMProviderClient(Protocol):
    async def create_policy_draft(
        self,
        *,
        resolved: ResolvedLLMProviderSettings,
        prompt: str,
        camera_state: Mapping[str, object],
    ) -> Mapping[str, object]:
        raise NotImplementedError
```

Add an OpenAI-compatible HTTP adapter that posts to `base_url` when present and
uses the profile model/API key.

- [ ] **Step 3: Inject provider client into policy draft compiler**

Change `PolicyDraftCompiler` to accept `llm_provider_client`. If `use_llm` is
true, resolve provider settings, call the client, validate the returned
structured diff, and set metadata to `provider_assisted`.

- [ ] **Step 4: Preserve deterministic fallback safely**

When provider output is malformed, set metadata:

```python
{
    "llm_assistance": "provider_rejected",
    "llm_fallback": "deterministic",
}
```

Do not apply unvalidated provider fields.

- [ ] **Step 5: Run LLM/policy tests**

Run:

```bash
python3 -m uv run --project backend pytest backend/tests/services/test_llm_provider_runtime.py backend/tests/services/test_policy_drafts.py -q
```

Expected: PASS.

## Task 10: Operations Polling, Push, And Restart Policies

**Files:**

- Modify: `backend/src/argus/services/supervisor_operations.py`
- Modify: supervisor runner modules that poll lifecycle requests
- Modify: NATS event client integration around lifecycle requests
- Modify: `frontend/src/components/operations/SupervisorLifecycleControls.tsx`
- Test: `backend/tests/services/test_supervisor_operations.py`
- Test: `backend/tests/api/test_operations_endpoints.py`
- Test: `frontend/src/components/operations/SupervisorLifecycleControls.test.tsx`

- [ ] **Step 1: Add supervisor mode tests**

Cover:

```python
async def test_push_mode_publishes_lifecycle_request_to_nats(
    supervisor_service,
    nats_spy,
    tenant_context,
    camera,
):
    request = await supervisor_service.create_lifecycle_request(
        tenant_context=tenant_context,
        camera_id=camera.id,
        action=OperationsLifecycleAction.START,
        operations_mode={"lifecycle_owner": "edge_supervisor", "supervisor_mode": "push"},
    )

    assert nats_spy.published_subjects == [f"supervisor.{request.node_id}.lifecycle"]


async def test_push_mode_requires_ack_before_marking_request_dispatched(
    supervisor_service,
    nats_spy,
    tenant_context,
    camera,
):
    nats_spy.queue_ack(timeout=True)

    request = await supervisor_service.create_lifecycle_request(
        tenant_context=tenant_context,
        camera_id=camera.id,
        action=OperationsLifecycleAction.RESTART,
        operations_mode={"lifecycle_owner": "edge_supervisor", "supervisor_mode": "push"},
    )

    assert request.dispatch_status == "ack_timeout"


async def test_polling_mode_does_not_publish_push_message(
    supervisor_service,
    nats_spy,
    tenant_context,
    camera,
):
    await supervisor_service.create_lifecycle_request(
        tenant_context=tenant_context,
        camera_id=camera.id,
        action=OperationsLifecycleAction.START,
        operations_mode={"lifecycle_owner": "edge_supervisor", "supervisor_mode": "polling"},
    )

    assert nats_spy.published_subjects == []


def test_restart_policy_always_reconciles_after_supervisor_restart(reconciler):
    actions = reconciler.reconcile_after_restart(
        desired_workers=[{"camera_id": "camera-1", "restart_policy": "always"}],
        running_workers=[],
    )

    assert actions == [{"camera_id": "camera-1", "action": "start"}]
```

- [ ] **Step 2: Add lifecycle dispatch abstraction**

Add:

```python
class LifecycleDispatcher(Protocol):
    async def dispatch(self, request: OperationsLifecycleRequest) -> LifecycleDispatchResult:
        raise NotImplementedError
```

Implement `PollingLifecycleDispatcher` as a no-op dispatch marker and
`NatsPushLifecycleDispatcher` as a publish-and-ack path.

- [ ] **Step 3: Route lifecycle requests by operations profile**

When a lifecycle request is created, resolve operations mode for the camera.
If supervisor mode is `disabled`, return 409. If `polling`, create request for
polling supervisor pickup. If `push`, publish NATS message and record ack state.

- [ ] **Step 4: Enforce restart policy in supervisor reconciliation**

Update supervisor reconciliation:

- `never`: do not restart stopped workers.
- `on_failure`: restart only error exits within retry limits.
- `always`: restart desired workers after supervisor restart and unexpected exit.

- [ ] **Step 5: Update Operations UI disabled reasons**

Render backend-provided `allowed_lifecycle_actions` and `detail` exactly. Add a
push-mode badge when the resolved operations profile uses push.

- [ ] **Step 6: Run operations tests**

Run:

```bash
python3 -m uv run --project backend pytest backend/tests/services/test_supervisor_operations.py backend/tests/api/test_operations_endpoints.py -q
corepack pnpm --dir frontend test src/components/operations/SupervisorLifecycleControls.test.tsx src/pages/Settings.test.tsx
```

Expected: PASS.

## Task 11: Final Documentation, Visual QA, And Full Verification

**Files:**

- Modify: `docs/runbook.md`
- Modify: `docs/operator-deployment-playbook.md`
- Modify: `docs/macbook-jetson-cross-network-reinstall-guide.md`
- Modify: `docs/model-loading-and-configuration-guide.md`
- Modify: `docs/scene-vision-profile-configuration-guide.md`

- [ ] **Step 1: Update operator documentation**

Add a "Configuration validation" section with:

```markdown
1. Create or duplicate the profile.
2. Fill required fields and secrets.
3. Click Test profile.
4. Bind only after validation succeeds.
5. Open Effective configuration for the target.
6. Start or restart the worker.
7. Confirm desired and applied profile hashes are aligned.
```

- [ ] **Step 2: Update MacBook test-build process**

Add exact smoke checks:

```bash
curl -s -H "Authorization: Bearer $TOKEN" "$API/api/v1/configuration/catalog" | jq '.kinds[].kind'
curl -s -H "Authorization: Bearer $TOKEN" "$API/api/v1/configuration/bindings" | jq '.bindings | length'
curl -s -H "Authorization: Bearer $TOKEN" "$API/api/v1/configuration/resolved?camera_id=$CAMERA_ID" | jq '.entries'
curl -s -H "Authorization: Bearer $TOKEN" "$API/api/v1/operations/fleet" | jq '.camera_workers[] | {camera_name, configuration}'
```

- [ ] **Step 3: Run full backend test suite**

Run:

```bash
make test
```

Expected: PASS.

- [ ] **Step 4: Run frontend test and build**

Run:

```bash
corepack pnpm --dir frontend test
corepack pnpm --dir frontend build
```

Expected: PASS.

- [ ] **Step 5: Run installer verification when packaging files changed**

Run:

```bash
make verify-installers
```

Expected: PASS, or no packaging changes were made in this branch.

- [ ] **Step 6: Manual browser QA**

Open the local app and verify:

- every configuration tab renders without overlap at desktop and mobile widths
- unsupported controls are disabled with backend reason text
- profile save/test/delete/bind/unbind flows show loading and result feedback
- effective configuration shows desired/applied/aligned/drift states
- Operations mode templates allow multiple profiles and clear bindings

- [ ] **Step 7: Commit final documentation and QA notes**

Run:

```bash
git add docs/runbook.md docs/operator-deployment-playbook.md docs/macbook-jetson-cross-network-reinstall-guide.md docs/model-loading-and-configuration-guide.md docs/scene-vision-profile-configuration-guide.md
git commit -m "docs: add production configuration validation runbook"
```

## Phase Gate Verification

After Task 5:

```bash
python3 -m uv run --project backend pytest backend/tests/services/test_operator_configuration.py backend/tests/api/test_configuration_endpoints.py backend/tests/services/test_camera_worker_config.py -q
corepack pnpm generate:api
corepack pnpm --dir frontend test src/hooks/use-configuration.test.ts src/components/configuration/ConfigurationWorkspace.test.tsx src/components/configuration/ProfileEditor.test.tsx src/components/configuration/EffectiveConfigurationPanel.test.tsx
corepack pnpm --dir frontend build
```

After Tasks 6-10:

```bash
make test
corepack pnpm --dir frontend test
corepack pnpm --dir frontend build
```

Before pushing:

```bash
git status --short
git log --oneline -5
```

## Execution Choice

Recommended execution:

1. Implement Tasks 1-5 sequentially in this thread or one focused worker.
2. Dispatch Tasks 6-10 to separate workers with disjoint file ownership.
3. Bring results back for Task 11 integration, visual QA, and final verification.

Use subagent-driven development after Task 5. The shared contracts are too
coupled for parallel work before then, but the runtime tracks are independent
once those contracts exist.
