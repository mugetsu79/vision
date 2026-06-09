# Protected Control Plane Site And Model Management UI Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Protect the `Vezor Master` control-plane target from normal Sites CRUD and add an admin model-management UI so bundled/catalog models can be registered without CLI commands.

**Architecture:** Use existing `SiteResponse.site_kind === "control_plane"` as the source of truth for protected system target behavior. Use the existing model catalog as the operator-facing registry, adding a backend catalog registration action that computes file metadata server-side so the UI does not require operators to type SHA256 or size fields.

**Tech Stack:** FastAPI, SQLAlchemy, Pydantic, React, TypeScript, TanStack Query, Vitest, pytest, Tailwind.

---

## Product Decisions

- `Vezor Master` remains a control-plane target, not a physical camera/deployment site.
- Control-plane sites are read-only in the Sites workspace: no edit, no delete.
- Backend rejects control-plane site PATCH and DELETE even if a user bypasses the UI.
- Real camera scenes belong to physical/operator sites such as `Office`, `Warehouse`, or vessel-linked sites.
- Model UI MVP registers curated catalog entries whose artifacts exist on the server/container filesystem.
- Raw upload of model bytes is out of scope for the first implementation. Operators can register bundled files and visible server paths; full browser upload can be a later storage/security feature.

---

### Task 1: Protect Control-Plane Sites In Backend

**Files:**
- Modify: `backend/src/argus/services/app.py`
- Modify: `backend/tests/services/test_site_service.py`

- [ ] **Step 1: Add failing service tests for control-plane update and delete**

Add this helper session near the existing fake sessions in `backend/tests/services/test_site_service.py`:

```python
class _NoopSiteSession:
    async def __aenter__(self) -> "_NoopSiteSession":
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:  # noqa: ANN001
        return None

    async def commit(self) -> None:
        return None

    async def rollback(self) -> None:
        return None

    async def refresh(self, item: object) -> None:
        del item

    async def delete(self, item: object) -> None:
        del item


class _NoopSiteSessionFactory:
    def __call__(self) -> _NoopSiteSession:
        return _NoopSiteSession()
```

Add these tests:

Update the existing contracts import first:

```python
from argus.api.contracts import SiteUpdate, TenantContext
```

```python
@pytest.mark.asyncio
async def test_update_control_plane_site_is_forbidden(monkeypatch: pytest.MonkeyPatch) -> None:
    tenant_id = uuid4()
    site_id = uuid4()
    site = Site(
        id=site_id,
        tenant_id=tenant_id,
        name="Vezor Master",
        description="Vezor control-plane probe target",
        tz="UTC",
        geo_point=None,
        site_kind="control_plane",
        created_at=datetime(2026, 6, 8, tzinfo=UTC),
    )

    async def fake_load_site(session, tenant_id_arg, site_id_arg):  # noqa: ANN001
        del session, tenant_id_arg, site_id_arg
        return site

    monkeypatch.setattr(app_services, "_load_site", fake_load_site)
    service = SiteService(
        session_factory=_NoopSiteSessionFactory(),
        audit_logger=_AuditLogger(),
    )

    with pytest.raises(HTTPException) as exc_info:
        await service.update_site(
            _tenant_context(tenant_id),
            site_id,
            SiteUpdate(name="Renamed Master"),
        )

    assert exc_info.value.status_code == status.HTTP_403_FORBIDDEN
    assert "control-plane target" in str(exc_info.value.detail)


@pytest.mark.asyncio
async def test_delete_control_plane_site_is_forbidden(monkeypatch: pytest.MonkeyPatch) -> None:
    tenant_id = uuid4()
    site_id = uuid4()
    site = Site(
        id=site_id,
        tenant_id=tenant_id,
        name="Vezor Master",
        description="Vezor control-plane probe target",
        tz="UTC",
        geo_point=None,
        site_kind="control_plane",
        created_at=datetime(2026, 6, 8, tzinfo=UTC),
    )

    async def fake_load_site(session, tenant_id_arg, site_id_arg):  # noqa: ANN001
        del session, tenant_id_arg, site_id_arg
        return site

    monkeypatch.setattr(app_services, "_load_site", fake_load_site)
    service = SiteService(
        session_factory=_NoopSiteSessionFactory(),
        audit_logger=_AuditLogger(),
    )

    with pytest.raises(HTTPException) as exc_info:
        await service.delete_site(_tenant_context(tenant_id), site_id)

    assert exc_info.value.status_code == status.HTTP_403_FORBIDDEN
    assert "protected" in str(exc_info.value.detail)
```

- [ ] **Step 2: Run the new backend tests and confirm they fail**

Run:

```bash
cd backend
python3 -m uv run pytest \
  tests/services/test_site_service.py::test_update_control_plane_site_is_forbidden \
  tests/services/test_site_service.py::test_delete_control_plane_site_is_forbidden -q
```

Expected: both tests fail because `SiteService` currently allows PATCH/DELETE for `site_kind == "control_plane"`.

- [ ] **Step 3: Implement backend protection**

In `backend/src/argus/services/app.py`, add this helper near the site helpers:

```python
def _site_is_control_plane(site: Site) -> bool:
    return _site_kind_value(site) == CONTROL_PLANE_SITE_KIND
```

In `SiteService.update_site`, immediately after loading the site:

```python
if _site_is_control_plane(site):
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="The Vezor Master control-plane target is managed by deployment and link services and cannot be edited from Sites.",
    )
```

In `SiteService.delete_site`, immediately after loading the site:

```python
if _site_is_control_plane(site):
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="The Vezor Master control-plane target is protected and cannot be deleted.",
    )
```

- [ ] **Step 4: Verify backend protection**

Run:

```bash
cd backend
python3 -m uv run pytest tests/services/test_site_service.py -q
python3 -m uv run ruff check src/argus/services/app.py tests/services/test_site_service.py
```

Expected: all site service tests pass and ruff reports no issues.

---

### Task 2: Mark Control-Plane Sites As Protected In Sites UI

**Files:**
- Modify: `frontend/src/pages/Sites.tsx`
- Modify: `frontend/src/pages/Sites.test.tsx`

- [ ] **Step 1: Add failing UI test**

In `frontend/src/pages/Sites.test.tsx`, add a control-plane fixture:

```ts
const masterSite = {
  id: "44444444-4444-4444-4444-444444444444",
  tenant_id: "22222222-2222-2222-2222-222222222222",
  name: "Vezor Master",
  description: "Vezor control-plane probe target",
  tz: "UTC",
  geo_point: null,
  site_kind: "control_plane",
  created_at: "2026-06-08T10:00:00Z",
};
```

Add this test:

```ts
test("marks the Vezor Master control-plane target as protected", async () => {
  mockSitesApi({
    sites: [masterSite, { ...hqSite, site_kind: "edge" }],
    cameras: [dockScene],
  });

  renderSitesPage();

  const grid = await screen.findByTestId("site-context-grid");
  const masterRow = within(grid)
    .getByRole("rowheader", { name: "Vezor Master" })
    .closest("tr");
  expect(masterRow).not.toBeNull();
  expect(within(masterRow as HTMLElement).getByText(/control-plane target/i)).toBeInTheDocument();
  expect(within(masterRow as HTMLElement).getByText(/protected/i)).toBeInTheDocument();
  expect(
    within(masterRow as HTMLElement).queryByRole("button", { name: /delete/i }),
  ).toBeNull();
  expect(
    within(masterRow as HTMLElement).queryByRole("button", { name: /edit/i }),
  ).toBeNull();

  const hqRow = within(grid).getByRole("rowheader", { name: "HQ" }).closest("tr");
  expect(hqRow).not.toBeNull();
  expect(within(hqRow as HTMLElement).getByRole("button", { name: /delete site/i })).toBeInTheDocument();
});
```

- [ ] **Step 2: Run the UI test and confirm it fails**

Run:

```bash
cd frontend
./node_modules/.bin/vitest run src/pages/Sites.test.tsx -t "control-plane target"
```

Expected: fails because the Sites page still renders normal Edit/Delete actions for control-plane sites.

- [ ] **Step 3: Implement protected site presentation**

In `frontend/src/pages/Sites.tsx`, add helpers near `filterSites`:

```ts
function isProtectedControlPlaneSite(site: Site) {
  return site.site_kind === "control_plane";
}

function protectedSiteBadge(site: Site) {
  return isProtectedControlPlaneSite(site) ? "Control-plane target" : null;
}
```

In the desktop site name cell, render the badge under the name:

```tsx
const protectedLabel = protectedSiteBadge(site);
```

```tsx
<div className="grid gap-1">
  <span>{site.name}</span>
  {protectedLabel ? (
    <span className="inline-flex w-fit rounded-full border border-[#35598d] bg-[#0b1624] px-2 py-0.5 text-[11px] font-medium text-[#b9d7ff]">
      {protectedLabel}
    </span>
  ) : null}
</div>
```

Replace the desktop action buttons with:

```tsx
{isProtectedControlPlaneSite(site) ? (
  <span className="inline-flex rounded-full border border-[#35598d] bg-[#0b1624] px-3 py-1.5 text-xs font-medium text-[#b9d7ff]">
    Protected
  </span>
) : (
  <>
    <button
      aria-label={`Edit ${site.name}`}
      className="rounded-full border border-white/10 bg-white/[0.04] px-3 py-1.5 text-xs font-medium text-[#d8e2f2] transition hover:bg-white/[0.08]"
      type="button"
      onClick={() => setDialogState({ mode: "edit", site })}
    >
      Edit
    </button>
    <button
      className="rounded-full border border-[#5a2330] bg-[#241118] px-3 py-1.5 text-xs font-medium text-[#ffc2cd] transition hover:bg-[#311722] disabled:cursor-not-allowed disabled:opacity-60"
      disabled={deleteSite.isPending}
      type="button"
      onClick={() => void handleDeleteSite(site)}
    >
      Delete site
    </button>
  </>
)}
```

Apply the same `protectedLabel` and action replacement to the mobile card.

- [ ] **Step 4: Verify Sites UI**

Run:

```bash
cd frontend
./node_modules/.bin/vitest run src/pages/Sites.test.tsx
./node_modules/.bin/eslint src/pages/Sites.tsx src/pages/Sites.test.tsx
./node_modules/.bin/tsc -b
```

Expected: Sites tests, eslint, and TypeScript build pass.

---

### Task 3: Add Backend Catalog Registration Action

**Files:**
- Modify: `backend/src/argus/api/v1/model_catalog.py`
- Modify: `backend/src/argus/services/app.py`
- Modify: `backend/src/argus/services/model_catalog.py`
- Modify: `backend/tests/api/test_model_catalog_routes.py`
- Create or modify: `backend/tests/services/test_model_catalog_registration.py`

- [ ] **Step 1: Add helper tests for catalog lookup and server file metadata**

Create `backend/tests/services/test_model_catalog_registration.py`:

```python
from __future__ import annotations

import hashlib
from pathlib import Path

from argus.services import app as app_services
from argus.services.model_catalog import get_model_catalog_entry


def test_get_model_catalog_entry_returns_known_entry() -> None:
    entry = get_model_catalog_entry("yolo26n-coco-onnx")

    assert entry is not None
    assert entry.name == "YOLO26n COCO"
    assert entry.path_hint == "models/yolo26n.onnx"


def test_file_sha256_reads_artifact_bytes(tmp_path: Path) -> None:
    artifact = tmp_path / "yolo26n.onnx"
    artifact.write_bytes(b"fake-onnx")

    assert app_services._file_sha256(artifact) == hashlib.sha256(b"fake-onnx").hexdigest()


def test_resolve_existing_model_artifact_path_accepts_absolute_file(tmp_path: Path) -> None:
    artifact = tmp_path / "yolo26n.onnx"
    artifact.write_bytes(b"fake-onnx")

    assert app_services._resolve_existing_model_artifact_path(str(artifact)) == artifact


def test_resolve_existing_model_artifact_path_returns_none_for_missing_file(tmp_path: Path) -> None:
    assert app_services._resolve_existing_model_artifact_path(str(tmp_path / "missing.onnx")) is None
```

- [ ] **Step 2: Add catalog registration route test**

Extend `backend/tests/api/test_model_catalog_routes.py`:

```python
from argus.api.contracts import ModelResponse


class _FakeModelService:
    def __init__(self) -> None:
        self.registered_catalog_id: str | None = None

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
                artifact_exists=True,
                note="Default fast detector.",
            )
        ]

    async def register_catalog_entry(self, catalog_id: str) -> ModelResponse:
        self.registered_catalog_id = catalog_id
        return ModelResponse(
            id=uuid4(),
            name="YOLO26n COCO",
            version="2026.1",
            task=ModelTask.DETECT,
            path="/models/yolo26n.onnx",
            format=ModelFormat.ONNX,
            capability=DetectorCapability.FIXED_VOCAB,
            capability_config={
                "runtime_backend": "onnxruntime",
                "readiness": "ready",
                "catalog_id": catalog_id,
            },
            classes=["person", "car"],
            input_shape={"width": 640, "height": 640},
            sha256="a" * 64,
            size_bytes=1234,
            license="AGPL-3.0",
        )
```

Update `_create_app` so it keeps the fake model service:

```python
def _create_app(context: TenantContext) -> FastAPI:
    app = FastAPI()
    app.include_router(router)
    app.state.model_service = _FakeModelService()
    app.state.services = SimpleNamespace(
        tenancy=_FakeTenancyService(context),
        models=app.state.model_service,
    )
    app.state.security = _FakeSecurity(context.user)
    return app
```

Add the route test:

```python
@pytest.mark.asyncio
async def test_register_model_catalog_entry_route_returns_model(client: AsyncClient) -> None:
    context = _tenant_context()
    app = _create_app(context)

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        response = await client.post(
            "/api/v1/model-catalog/yolo26n-coco-onnx/register",
            headers={"Authorization": "Bearer token"},
        )

    assert response.status_code == 201
    assert response.json()["name"] == "YOLO26n COCO"
    assert app.state.model_service.registered_catalog_id == "yolo26n-coco-onnx"
```

- [ ] **Step 3: Implement catalog lookup and artifact metadata helpers**

In `backend/src/argus/services/model_catalog.py`, add:

```python
def get_model_catalog_entry(catalog_id: str) -> ModelCatalogEntry | None:
    return next(
        (entry for entry in list_model_catalog_entries() if entry.id == catalog_id),
        None,
    )
```

In `backend/src/argus/services/app.py`, add:

```python
def _candidate_model_artifact_paths(path_hint: str) -> list[Path]:
    hinted = Path(path_hint)
    candidates = [hinted]
    if not hinted.is_absolute():
        candidates.append(Path.cwd() / hinted)
        candidates.append(Path("/models") / hinted.name)
    return list(dict.fromkeys(candidates))


def _resolve_existing_model_artifact_path(path_hint: str) -> Path | None:
    for candidate in _candidate_model_artifact_paths(path_hint):
        if candidate.exists() and candidate.is_file():
            return candidate
    return None


def _file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()
```

- [ ] **Step 4: Implement idempotent catalog registration**

In `ModelService`, add:

```python
async def register_catalog_entry(self, catalog_id: str) -> ModelResponse:
    entry = get_model_catalog_entry(catalog_id)
    if entry is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Model catalog entry not found.")
    if entry.capability_config.readiness == "planned":
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Planned model artifacts cannot be registered as camera models.")

    artifact_path = _resolve_existing_model_artifact_path(entry.path_hint)
    if artifact_path is None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Model artifact is not available on this server.")

    async with self.session_factory() as session:
        existing = (
            await session.execute(
                select(Model).where(Model.capability_config["catalog_id"].as_string() == entry.id)
            )
        ).scalar_one_or_none()
        if existing is not None:
            return _model_to_response(existing)

        capability_config = entry.capability_config.model_dump(mode="python")
        capability_config["catalog_id"] = entry.id
        model = Model(
            name=entry.name,
            version=entry.version,
            task=entry.task,
            path=str(artifact_path),
            format=entry.format,
            capability=entry.capability,
            capability_config=capability_config,
            classes=_resolve_model_classes_for_capability(
                capability=entry.capability,
                path=str(artifact_path),
                format=entry.format,
                classes=list(entry.classes),
                capability_config=capability_config,
            ),
            input_shape=entry.input_shape,
            sha256=_file_sha256(artifact_path),
            size_bytes=artifact_path.stat().st_size,
            license=entry.license,
        )
        session.add(model)
        await session.commit()
        await session.refresh(model)
    return _model_to_response(model)
```

If JSON-path querying is not portable in the current SQLAlchemy setup, replace the `existing` lookup with `select(Model)` and filter in Python by `(model.capability_config or {}).get("catalog_id") == entry.id`.

- [ ] **Step 5: Add API route**

In `backend/src/argus/api/v1/model_catalog.py`, import `ModelResponse`, `status`, and admin dependency, then add:

```python
AdminUser = Annotated[AuthenticatedUser, Depends(require(RoleEnum.ADMIN))]


@router.post("/{catalog_id}/register", response_model=ModelResponse, status_code=status.HTTP_201_CREATED)
async def register_model_catalog_entry(
    catalog_id: str,
    current_user: AdminUser,
    services: ServicesDependency,
) -> ModelResponse:
    return await services.models.register_catalog_entry(catalog_id)
```

- [ ] **Step 6: Verify backend model registration**

Run:

```bash
cd backend
python3 -m uv run pytest tests/api/test_model_catalog_routes.py tests/services/test_model_catalog_registration.py -q
python3 -m uv run ruff check src/argus/api/v1/model_catalog.py src/argus/services/app.py src/argus/services/model_catalog.py tests/api/test_model_catalog_routes.py tests/services/test_model_catalog_registration.py
```

Expected: tests pass and ruff reports no issues.

---

### Task 4: Add Frontend Model Management Hooks

**Files:**
- Modify: `frontend/src/hooks/use-model-catalog.ts`
- Modify: `frontend/src/hooks/use-models.ts`
- Regenerate: `frontend/src/lib/api.generated.ts`

- [ ] **Step 1: Regenerate OpenAPI types after backend route is added**

Run the repo's API generation command:

```bash
cd frontend
npm run generate:api
```

Expected: `frontend/src/lib/api.generated.ts` includes `POST /api/v1/model-catalog/{catalog_id}/register`.

- [ ] **Step 2: Add catalog registration hook**

In `frontend/src/hooks/use-model-catalog.ts`, add:

```ts
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
```

Then add:

```ts
export function useRegisterModelCatalogEntry() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (catalogId: string) => {
      const { data, error } = await apiClient.POST(
        "/api/v1/model-catalog/{catalog_id}/register",
        {
          params: { path: { catalog_id: catalogId } },
        },
      );

      if (error) {
        throw toApiError(error, "Failed to register model.");
      }

      return data;
    },
    onSuccess: async () => {
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ["model-catalog"] }),
        queryClient.invalidateQueries({ queryKey: ["models"] }),
      ]);
    },
  });
}
```

- [ ] **Step 3: Add model create/update hooks for later custom forms**

In `frontend/src/hooks/use-models.ts`, extend imports:

```ts
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
```

Add:

```ts
export type CreateModelInput = components["schemas"]["ModelCreate"];
export type UpdateModelInput = components["schemas"]["ModelUpdate"];

export function useCreateModel() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (payload: CreateModelInput) => {
      const { data, error } = await apiClient.POST("/api/v1/models", { body: payload });

      if (error) {
        throw toApiError(error, "Failed to create model.");
      }

      return data;
    },
    onSuccess: async () => {
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ["models"] }),
        queryClient.invalidateQueries({ queryKey: ["model-catalog"] }),
      ]);
    },
  });
}

export function useUpdateModel() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async ({ modelId, payload }: { modelId: string; payload: UpdateModelInput }) => {
      const { data, error } = await apiClient.PATCH("/api/v1/models/{model_id}", {
        params: { path: { model_id: modelId } },
        body: payload,
      });

      if (error) {
        throw toApiError(error, "Failed to update model.");
      }

      return data;
    },
    onSuccess: async () => {
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ["models"] }),
        queryClient.invalidateQueries({ queryKey: ["model-catalog"] }),
      ]);
    },
  });
}
```

- [ ] **Step 4: Verify hooks compile**

Run:

```bash
cd frontend
./node_modules/.bin/tsc -b
```

Expected: TypeScript build passes.

---

### Task 5: Build Models Admin Page

**Files:**
- Create: `frontend/src/pages/Models.tsx`
- Create: `frontend/src/pages/Models.test.tsx`
- Modify: `frontend/src/app/router.tsx`
- Modify: `frontend/src/copy/omnisight.ts`
- Modify: `frontend/src/copy/omnisight.test.ts`
- Modify: `frontend/src/components/layout/workspace-nav.ts`
- Modify: `frontend/src/components/layout/AppShell.test.tsx`

- [ ] **Step 1: Add failing Models page test**

Create `frontend/src/pages/Models.test.tsx` with these cases:

```ts
import { QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, test, vi } from "vitest";

import { createQueryClient } from "@/app/query-client";
import type { components } from "@/lib/api.generated";
import { ModelsPage } from "@/pages/Models";

type ModelCatalogEntry = components["schemas"]["ModelCatalogEntryResponse"];
type ModelResponse = components["schemas"]["ModelResponse"];

function catalogEntry(overrides: Partial<ModelCatalogEntry>): ModelCatalogEntry {
  return {
    id: "yolo26n-coco-onnx",
    name: "YOLO26n COCO",
    version: "2026.1",
    task: "detect",
    path_hint: "models/yolo26n.onnx",
    format: "onnx",
    capability: "fixed_vocab",
    capability_config: { runtime_backend: "onnxruntime", readiness: "ready" },
    classes: [],
    input_shape: { width: 640, height: 640 },
    sha256: null,
    size_bytes: null,
    license: "AGPL-3.0",
    registration_state: "unregistered",
    registered_model_id: null,
    artifact_exists: true,
    note: "Default fast detector.",
    ...overrides,
  };
}

function modelResponse(overrides: Partial<ModelResponse>): ModelResponse {
  return {
    id: "model-26n",
    name: "YOLO26n COCO",
    version: "2026.1",
    task: "detect",
    path: "/models/yolo26n.onnx",
    format: "onnx",
    capability: "fixed_vocab",
    capability_config: { runtime_backend: "onnxruntime", readiness: "ready" },
    classes: ["person", "car"],
    input_shape: { width: 640, height: 640 },
    sha256: "a".repeat(64),
    size_bytes: 1234,
    license: "AGPL-3.0",
    ...overrides,
  };
}

function mockModelsApi({
  catalog,
  models,
}: {
  catalog: ModelCatalogEntry[];
  models: ModelResponse[];
}) {
  return vi.spyOn(global, "fetch").mockImplementation(async (input) => {
    const request = input instanceof Request ? input : new Request(String(input));
    const url = new URL(request.url);

    if (url.pathname === "/api/v1/model-catalog" && request.method === "GET") {
      return new Response(JSON.stringify(catalog), {
        status: 200,
        headers: { "Content-Type": "application/json" },
      });
    }

    if (url.pathname === "/api/v1/models" && request.method === "GET") {
      return new Response(JSON.stringify(models), {
        status: 200,
        headers: { "Content-Type": "application/json" },
      });
    }

    if (
      url.pathname === "/api/v1/model-catalog/yolo26n-coco-onnx/register" &&
      request.method === "POST"
    ) {
      return new Response(JSON.stringify(modelResponse({ id: "model-26n" })), {
        status: 201,
        headers: { "Content-Type": "application/json" },
      });
    }

    return new Response("Not found", { status: 404 });
  });
}

function renderModelsPage() {
  return render(
    <QueryClientProvider client={createQueryClient()}>
      <ModelsPage />
    </QueryClientProvider>,
  );
}

test("shows catalog registration status and registers an available bundled model", async () => {
  const user = userEvent.setup();
  const fetchMock = mockModelsApi({
    catalog: [
      catalogEntry({ id: "yolo26n-coco-onnx", name: "YOLO26n COCO", registration_state: "unregistered", artifact_exists: true }),
      catalogEntry({ id: "yolo26s-coco-onnx", name: "YOLO26s COCO", registration_state: "registered", artifact_exists: true, registered_model_id: "model-26s" }),
      catalogEntry({ id: "yoloe-26n-open-vocab-pt", name: "YOLOE-26N Open Vocab", registration_state: "missing_artifact", artifact_exists: false }),
      catalogEntry({ id: "yolo26n-coco-tensorrt-engine", name: "YOLO26n COCO TensorRT Engine", registration_state: "planned", artifact_exists: false }),
    ],
    models: [modelResponse({ id: "model-26s", name: "YOLO26s COCO" })],
  });

  renderModelsPage();

  expect(await screen.findByRole("heading", { name: /model registry/i })).toBeInTheDocument();
  expect(screen.getByText("YOLO26n COCO")).toBeInTheDocument();
  expect(screen.getByText(/missing artifact/i)).toBeInTheDocument();
  expect(screen.getByText(/planned/i)).toBeInTheDocument();

  await user.click(screen.getByRole("button", { name: /register yolo26n coco/i }));

  await waitFor(() =>
    expect(fetchMock).toHaveBeenCalledWith(
      expect.objectContaining({ method: "POST" }),
    ),
  );
});
```

Also test that registered/planned/missing catalog entries do not render an enabled register button.

- [ ] **Step 2: Implement Models page shell**

Create `frontend/src/pages/Models.tsx`:

```tsx
import { RequireRole } from "@/components/auth/RequireRole";
import { WorkspaceBand, WorkspaceSurface } from "@/components/layout/workspace-surfaces";
import { Button } from "@/components/ui/button";
import { useModelCatalog, useRegisterModelCatalogEntry } from "@/hooks/use-model-catalog";
import { useModels, useRuntimeArtifactsByModelId } from "@/hooks/use-models";

export function ModelsPage() {
  return (
    <RequireRole role="admin">
      <ModelsContent />
    </RequireRole>
  );
}
```

Implement `ModelsContent` with:

```tsx
function ModelsContent() {
  const catalog = useModelCatalog();
  const models = useModels();
  const registerCatalogEntry = useRegisterModelCatalogEntry();
  const runtimeArtifacts = useRuntimeArtifactsByModelId((models.data ?? []).map((model) => model.id));

  return (
    <div data-testid="models-workspace" className="space-y-5 p-4 sm:p-6">
      <WorkspaceBand
        eyebrow="Models"
        title="Model Registry"
        description="Register bundled detector models, inspect runtime readiness, and keep scene setup out of the CLI."
      />
      <CatalogSection
        catalog={catalog.data ?? []}
        isLoading={catalog.isLoading}
        pendingCatalogId={registerCatalogEntry.variables ?? null}
        onRegister={(catalogId) => registerCatalogEntry.mutate(catalogId)}
      />
      <RegisteredModelsSection
        models={models.data ?? []}
        artifactsByModelId={runtimeArtifacts.data ?? {}}
      />
    </div>
  );
}
```

Use page sections, not nested cards. Catalog rows should show:

- model name and version
- format/capability
- path hint
- registration state badge
- one `Register <model name>` button only when `registration_state === "unregistered" && artifact_exists`

- [ ] **Step 3: Add route and navigation**

In `frontend/src/app/router.tsx`, add a child route:

```tsx
{
  path: "models",
  lazy: async () => ({
    Component: (await import("@/pages/Models")).ModelsPage,
  }),
},
```

In `frontend/src/copy/omnisight.ts`, add Models to the Control group:

```ts
{ label: "Models", to: "/models" },
```

In `frontend/src/components/layout/workspace-nav.ts`, import `BrainCircuit` or `Cpu` from `lucide-react`, map `/models` to that icon, and add route prefetch:

```ts
if (route === "/models") {
  void import("@/pages/Models");
}
```

- [ ] **Step 4: Update navigation tests**

Update `frontend/src/copy/omnisight.test.ts` expected Control navigation to include:

```ts
{ label: "Models", to: "/models" },
```

Update `frontend/src/components/layout/AppShell.test.tsx` to expect the Models link in the Control nav.

- [ ] **Step 5: Verify Models page**

Run:

```bash
cd frontend
./node_modules/.bin/vitest run src/pages/Models.test.tsx src/copy/omnisight.test.ts src/components/layout/AppShell.test.tsx
./node_modules/.bin/eslint src/pages/Models.tsx src/pages/Models.test.tsx src/hooks/use-model-catalog.ts src/hooks/use-models.ts src/app/router.tsx src/copy/omnisight.ts src/components/layout/workspace-nav.ts
./node_modules/.bin/tsc -b
```

Expected: all targeted frontend tests, lint, and TypeScript build pass.

---

### Task 6: Documentation And Smoke Path

**Files:**
- Modify: `docs/model-loading-and-configuration-guide.md`
- Modify: `docs/product-installer-and-first-run-guide.md`
- Modify: `docs/operator-deployment-playbook.md`
- Modify: `docs/core-link-performance-guide.md`

- [ ] **Step 1: Update model docs to prefer UI registration**

In `docs/model-loading-and-configuration-guide.md`, add a section before CLI registration:

```md
## Register Bundled Models From The UI

For installed systems, prefer the Models workspace:

1. Sign in as an admin.
2. Open Control -> Models.
3. Register `YOLO26n COCO` and `YOLO26s COCO` when their artifact status is available.
4. Confirm both rows move to Registered.
5. Return to Scenes and select the registered model when creating or editing a scene.

The CLI remains available for automation and advanced custom model registration.
```

- [ ] **Step 2: Update site docs to explain protected Vezor Master**

In `docs/core-link-performance-guide.md`, update the target-only section:

```md
The `Vezor Master` site is a protected control-plane target. It appears in Sites for operator orientation and in Core Link as a target, but it is not a physical deployment location and cannot be edited or deleted from normal Sites management.
```

- [ ] **Step 3: Verify docs and final targeted checks**

Run:

```bash
cd backend
python3 -m uv run pytest tests/services/test_site_service.py tests/api/test_model_catalog_routes.py tests/services/test_model_catalog_registration.py -q
python3 -m uv run ruff check src/argus/services/app.py src/argus/api/v1/model_catalog.py src/argus/services/model_catalog.py tests/services/test_site_service.py tests/api/test_model_catalog_routes.py tests/services/test_model_catalog_registration.py

cd ../frontend
./node_modules/.bin/vitest run src/pages/Sites.test.tsx src/pages/Models.test.tsx src/copy/omnisight.test.ts src/components/layout/AppShell.test.tsx
./node_modules/.bin/eslint src/pages/Sites.tsx src/pages/Sites.test.tsx src/pages/Models.tsx src/pages/Models.test.tsx src/hooks/use-model-catalog.ts src/hooks/use-models.ts src/app/router.tsx src/copy/omnisight.ts src/components/layout/workspace-nav.ts
./node_modules/.bin/tsc -b
```

Expected: all commands pass.

---

## Execution Recommendation

Do this in two commits:

1. `fix: protect control-plane sites`
2. `feat: add model registry management UI`

This keeps the safe, obvious `Vezor Master` protection separate from the larger model-management workflow.
