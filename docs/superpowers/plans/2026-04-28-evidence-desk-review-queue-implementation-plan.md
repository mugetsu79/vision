# Evidence Desk Review Queue Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Redesign `/incidents` into a triage-first Evidence Desk with persisted pending/reviewed state for captured incident records.

**Architecture:** Add a small incident review state to the existing incident model, expose it through the incident API, and refactor the frontend page into queue, evidence hero, and facts panel units. The worker capture path remains unchanged: clips are the current real evidence artifact, snapshots are optional when present.

**Tech Stack:** FastAPI, SQLAlchemy/Alembic, Pydantic, PostgreSQL/Timescale, React, TanStack Query, openapi-fetch, Vitest, Playwright.

---

## File Map

- `backend/src/argus/models/enums.py` — add `IncidentReviewStatus`.
- `backend/src/argus/models/tables.py` — add incident review columns.
- `backend/src/argus/migrations/versions/0007_incident_review_state.py` — add review enum and incident columns.
- `backend/src/argus/api/contracts.py` — add review request contract and response fields.
- `backend/src/argus/api/v1/incidents.py` — add review-status filtering and review mutation route.
- `backend/src/argus/services/app.py` — extend `IncidentService` with filtering, review mutation, response mapping, and audit logging.
- `backend/tests/models/test_schema.py` — assert incident review columns and enum values.
- `backend/tests/api/test_prompt9_routes.py` — cover route-level query forwarding, review mutation, and role permission.
- `backend/tests/services/test_incident_service.py` — cover service-level review persistence, idempotence, tenant scoping, and audit metadata.
- `frontend/src/hooks/use-incidents.ts` — add review-status filter and review mutation hook.
- `frontend/src/lib/api.generated.ts` — regenerate from OpenAPI after backend contract changes.
- `frontend/src/pages/Incidents.tsx` — refactor into Evidence Desk layout.
- `frontend/src/pages/Incidents.test.tsx` — cover queue, clip-only evidence, filters, and review mutation.
- `frontend/e2e/prompt9-history-and-incidents.spec.ts` — update mocked incidents route and assertions for Evidence Desk.

Do not update README, product spec, runbook, playbook, or lab guide docs in this task unless implementation creates a narrow contract note that is otherwise absent. Those broader docs were already updated in earlier work.

---

### Task 1: Backend Schema And Contracts

**Files:**
- Modify: `backend/src/argus/models/enums.py`
- Modify: `backend/src/argus/models/tables.py`
- Create: `backend/src/argus/migrations/versions/0007_incident_review_state.py`
- Modify: `backend/src/argus/api/contracts.py`
- Modify: `backend/tests/models/test_schema.py`

- [ ] **Step 1: Write failing schema tests**

In `backend/tests/models/test_schema.py`, extend `test_sqlalchemy_enums_use_database_values_not_member_names` and add an incident review column test:

```python
def test_sqlalchemy_enums_use_database_values_not_member_names() -> None:
    camera_columns = Base.metadata.tables["cameras"].columns
    model_columns = Base.metadata.tables["models"].columns
    incident_columns = Base.metadata.tables["incidents"].columns

    assert list(camera_columns["processing_mode"].type.enums) == ["central", "edge", "hybrid"]
    assert list(camera_columns["tracker_type"].type.enums) == ["botsort", "bytetrack", "ocsort"]
    assert list(model_columns["task"].type.enums) == ["detect", "classify", "attribute"]
    assert list(incident_columns["review_status"].type.enums) == ["pending", "reviewed"]
```

Add:

```python
def test_incidents_table_tracks_review_state() -> None:
    incident_columns = Base.metadata.tables["incidents"].columns.keys()

    assert "review_status" in incident_columns
    assert "reviewed_at" in incident_columns
    assert "reviewed_by_subject" in incident_columns
```

- [ ] **Step 2: Run schema tests to verify failure**

Run:

```bash
cd /Users/yann.moren/vision/backend
python3 -m uv run pytest tests/models/test_schema.py -q
```

Expected: fail with missing `review_status` on `incidents`.

- [ ] **Step 3: Add the backend enum**

In `backend/src/argus/models/enums.py`, add this enum after `HistoryCoverageStatus`:

```python
class IncidentReviewStatus(StrEnum):
    PENDING = "pending"
    REVIEWED = "reviewed"
```

- [ ] **Step 4: Add review columns to the `Incident` table**

In `backend/src/argus/models/tables.py`, import the enum:

```python
from argus.models.enums import (
    CountEventType,
    DetectorCapability,
    IncidentReviewStatus,
    ModelFormat,
    ModelTask,
    ProcessingMode,
    RoleEnum,
    RuleAction,
    RuntimeVocabularySource,
    TrackerType,
)
```

Then update `class Incident`:

```python
class Incident(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "incidents"

    camera_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("cameras.id"),
        nullable=False,
    )
    ts: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    type: Mapped[str] = mapped_column(String(255), nullable=False)
    payload: Mapped[dict[str, object]] = mapped_column(JSONB, nullable=False)
    snapshot_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    clip_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    storage_bytes: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    review_status: Mapped[IncidentReviewStatus] = mapped_column(
        enum_column(IncidentReviewStatus, "incident_review_status_enum"),
        nullable=False,
        default=IncidentReviewStatus.PENDING,
    )
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    reviewed_by_subject: Mapped[str | None] = mapped_column(String(255), nullable=True)
```

- [ ] **Step 5: Add the Alembic migration**

Create `backend/src/argus/migrations/versions/0007_incident_review_state.py`:

```python
"""Add incident review state."""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0007_incident_review_state"
down_revision = "0006_open_vocab_hybrid_detector"
branch_labels = None
depends_on = None

incident_review_status_enum = sa.Enum(
    "pending",
    "reviewed",
    name="incident_review_status_enum",
)


def upgrade() -> None:
    bind = op.get_bind()
    incident_review_status_enum.create(bind, checkfirst=True)
    op.add_column(
        "incidents",
        sa.Column(
            "review_status",
            incident_review_status_enum,
            nullable=False,
            server_default="pending",
        ),
    )
    op.add_column("incidents", sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("incidents", sa.Column("reviewed_by_subject", sa.String(length=255), nullable=True))
    op.alter_column("incidents", "review_status", server_default=None)


def downgrade() -> None:
    bind = op.get_bind()
    op.drop_column("incidents", "reviewed_by_subject")
    op.drop_column("incidents", "reviewed_at")
    op.drop_column("incidents", "review_status")
    incident_review_status_enum.drop(bind, checkfirst=True)
```

- [ ] **Step 6: Add API contracts**

In `backend/src/argus/api/contracts.py`, import `IncidentReviewStatus` from `argus.models.enums`.

Update `IncidentResponse` and add `IncidentReviewUpdate` immediately after it:

```python
class IncidentResponse(BaseModel):
    id: UUID
    camera_id: UUID
    camera_name: str | None = None
    ts: datetime
    type: str
    payload: dict[str, Any]
    snapshot_url: str | None = None
    clip_url: str | None = None
    storage_bytes: int = 0
    review_status: IncidentReviewStatus = IncidentReviewStatus.PENDING
    reviewed_at: datetime | None = None
    reviewed_by_subject: str | None = None


class IncidentReviewUpdate(BaseModel):
    review_status: IncidentReviewStatus
```

- [ ] **Step 7: Run schema tests to verify pass**

Run:

```bash
cd /Users/yann.moren/vision/backend
python3 -m uv run pytest tests/models/test_schema.py -q
```

Expected: pass.

- [ ] **Step 8: Commit schema and contract work**

Run:

```bash
cd /Users/yann.moren/vision
git add backend/src/argus/models/enums.py \
        backend/src/argus/models/tables.py \
        backend/src/argus/migrations/versions/0007_incident_review_state.py \
        backend/src/argus/api/contracts.py \
        backend/tests/models/test_schema.py
git commit -m "feat(incidents): add review state schema"
```

---

### Task 2: Backend Review API And Service

**Files:**
- Modify: `backend/src/argus/api/v1/incidents.py`
- Modify: `backend/src/argus/services/app.py`
- Modify: `backend/tests/api/test_prompt9_routes.py`
- Create: `backend/tests/services/test_incident_service.py`

- [ ] **Step 1: Write failing route tests**

In `backend/tests/api/test_prompt9_routes.py`, update imports:

```python
from argus.api.contracts import (
    ExportArtifact,
    HistoryPoint,
    IncidentResponse,
    TenantContext,
)
from argus.models.enums import IncidentReviewStatus, RoleEnum
```

Change `_sample_user` to accept a role:

```python
def _sample_user(role: RoleEnum = RoleEnum.VIEWER) -> AuthenticatedUser:
    return AuthenticatedUser(
        subject="user-1",
        email="analyst@argus.local",
        role=role,
        issuer="http://localhost:8080/realms/argus-dev",
        realm="argus-dev",
        is_superadmin=False,
        tenant_context=str(uuid4()),
        claims={},
    )
```

Update `RecordingIncidentService`:

```python
class RecordingIncidentService:
    def __init__(self) -> None:
        self.last_query: dict[str, object] | None = None
        self.review_calls: list[dict[str, object]] = []

    async def list_incidents(
        self,
        context: TenantContext,
        *,
        camera_id: UUID | None,
        incident_type: str | None,
        review_status: IncidentReviewStatus | None,
        limit: int,
    ) -> list[IncidentResponse]:
        self.last_query = {
            "tenant_id": context.tenant_id,
            "camera_id": camera_id,
            "incident_type": incident_type,
            "review_status": review_status,
            "limit": limit,
        }
        return [
            IncidentResponse(
                id=uuid4(),
                camera_id=camera_id or uuid4(),
                ts=datetime.now(tz=UTC),
                type=incident_type or "ppe-missing",
                payload={"severity": "high"},
                snapshot_url="https://minio.local/signed/incidents/1.jpg",
                clip_url="https://minio.local/signed/incidents/1.mjpeg",
                storage_bytes=2_097_152,
                review_status=review_status or IncidentReviewStatus.PENDING,
            )
        ]

    async def update_review_state(
        self,
        context: TenantContext,
        *,
        incident_id: UUID,
        review_status: IncidentReviewStatus,
    ) -> IncidentResponse:
        self.review_calls.append(
            {
                "tenant_id": context.tenant_id,
                "incident_id": incident_id,
                "review_status": review_status,
                "subject": context.user.subject,
            }
        )
        reviewed_at = datetime.now(tz=UTC) if review_status == IncidentReviewStatus.REVIEWED else None
        reviewed_by_subject = (
            context.user.subject if review_status == IncidentReviewStatus.REVIEWED else None
        )
        return IncidentResponse(
            id=incident_id,
            camera_id=uuid4(),
            ts=datetime.now(tz=UTC),
            type="ppe-missing",
            payload={"severity": "high"},
            snapshot_url=None,
            clip_url="https://minio.local/signed/incidents/1.mjpeg",
            storage_bytes=2_097_152,
            review_status=review_status,
            reviewed_at=reviewed_at,
            reviewed_by_subject=reviewed_by_subject,
        )
```

Update `test_incidents_route_passes_camera_type_and_limit_filters` to include `review_status`:

```python
@pytest.mark.asyncio
async def test_incidents_route_passes_camera_type_limit_and_review_status_filters() -> None:
    user = _sample_user()
    incidents = RecordingIncidentService()
    app = _create_test_app(user=user, history=RecordingHistoryService(), incidents=incidents)
    camera_id = uuid4()

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://testserver",
    ) as client:
        response = await client.get(
            "/api/v1/incidents",
            params={
                "camera_id": str(camera_id),
                "type": "ppe-missing",
                "review_status": "pending",
                "limit": "25",
            },
        )

    assert response.status_code == 200
    assert response.json()[0]["type"] == "ppe-missing"
    assert response.json()[0]["clip_url"] == "https://minio.local/signed/incidents/1.mjpeg"
    assert response.json()[0]["storage_bytes"] == 2_097_152
    assert response.json()[0]["review_status"] == "pending"
    assert incidents.last_query == {
        "tenant_id": UUID(str(user.tenant_context)),
        "camera_id": camera_id,
        "incident_type": "ppe-missing",
        "review_status": IncidentReviewStatus.PENDING,
        "limit": 25,
    }
```

Add:

```python
@pytest.mark.asyncio
async def test_incident_review_route_requires_operator_and_calls_service() -> None:
    user = _sample_user(role=RoleEnum.OPERATOR)
    incidents = RecordingIncidentService()
    app = _create_test_app(user=user, history=RecordingHistoryService(), incidents=incidents)
    incident_id = uuid4()

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://testserver",
    ) as client:
        response = await client.patch(
            f"/api/v1/incidents/{incident_id}/review",
            json={"review_status": "reviewed"},
        )

    assert response.status_code == 200
    assert response.json()["id"] == str(incident_id)
    assert response.json()["review_status"] == "reviewed"
    assert response.json()["reviewed_by_subject"] == "user-1"
    assert incidents.review_calls == [
        {
            "tenant_id": UUID(str(user.tenant_context)),
            "incident_id": incident_id,
            "review_status": IncidentReviewStatus.REVIEWED,
            "subject": "user-1",
        }
    ]
```

Add:

```python
@pytest.mark.asyncio
async def test_incident_review_route_rejects_viewer() -> None:
    user = _sample_user(role=RoleEnum.VIEWER)
    incidents = RecordingIncidentService()
    app = _create_test_app(user=user, history=RecordingHistoryService(), incidents=incidents)

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://testserver",
    ) as client:
        response = await client.patch(
            f"/api/v1/incidents/{uuid4()}/review",
            json={"review_status": "reviewed"},
        )

    assert response.status_code == 403
    assert incidents.review_calls == []
```

- [ ] **Step 2: Run route tests to verify failure**

Run:

```bash
cd /Users/yann.moren/vision/backend
python3 -m uv run pytest tests/api/test_prompt9_routes.py -q
```

Expected: fail because `review_status` is not forwarded and review route does not exist.

- [ ] **Step 3: Write failing service tests**

Create `backend/tests/services/test_incident_service.py`:

```python
from __future__ import annotations

from datetime import UTC, datetime
from types import SimpleNamespace
from uuid import uuid4

import pytest
from fastapi import HTTPException

from argus.api.contracts import TenantContext
from argus.core.security import AuthenticatedUser
from argus.models.enums import IncidentReviewStatus, RoleEnum
from argus.models.tables import Incident
from argus.services.app import IncidentService


class _ScalarResult:
    def __init__(self, row: tuple[Incident, str] | None) -> None:
        self.row = row

    def all(self) -> list[tuple[Incident, str]]:
        return [self.row] if self.row is not None else []

    def one_or_none(self) -> tuple[Incident, str] | None:
        return self.row


class _FakeSession:
    def __init__(self, state: dict[str, object]) -> None:
        self.state = state
        self.commits = 0
        self.refreshes = 0

    async def __aenter__(self) -> _FakeSession:
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        return None

    async def execute(self, statement):  # noqa: ANN001
        self.state["last_statement"] = statement
        return _ScalarResult(self.state.get("row"))  # type: ignore[arg-type]

    async def commit(self) -> None:
        self.commits += 1
        self.state["commits"] = int(self.state.get("commits", 0)) + 1

    async def refresh(self, obj: object) -> None:
        self.refreshes += 1
        self.state["refreshes"] = int(self.state.get("refreshes", 0)) + 1


class _FakeSessionFactory:
    def __init__(self, row: tuple[Incident, str] | None) -> None:
        self.state: dict[str, object] = {"row": row}

    def __call__(self) -> _FakeSession:
        return _FakeSession(self.state)


class _FakeAuditLogger:
    def __init__(self) -> None:
        self.calls: list[dict[str, object]] = []

    async def record(self, **kwargs: object) -> None:
        self.calls.append(kwargs)


def _tenant_context(tenant_id=None) -> TenantContext:  # noqa: ANN001
    tenant_uuid = tenant_id or uuid4()
    return TenantContext(
        tenant_id=tenant_uuid,
        tenant_slug="test-tenant",
        user=AuthenticatedUser(
            subject="operator-1",
            email="operator@argus.local",
            role=RoleEnum.OPERATOR,
            issuer="http://localhost:8080/realms/argus-dev",
            realm="argus-dev",
            is_superadmin=False,
            tenant_context=str(tenant_uuid),
            claims={},
        ),
    )


def _incident() -> Incident:
    return Incident(
        id=uuid4(),
        camera_id=uuid4(),
        ts=datetime(2026, 4, 28, 10, 0, tzinfo=UTC),
        type="ppe-missing",
        payload={"severity": "high"},
        snapshot_url=None,
        clip_url="https://minio.local/signed/incidents/1.mjpeg",
        storage_bytes=2_097_152,
        review_status=IncidentReviewStatus.PENDING,
        reviewed_at=None,
        reviewed_by_subject=None,
    )


@pytest.mark.asyncio
async def test_update_review_state_marks_incident_reviewed_and_audits() -> None:
    incident = _incident()
    audit = _FakeAuditLogger()
    service = IncidentService(
        _FakeSessionFactory((incident, "Forklift Gate")),
        audit_logger=audit,
    )
    context = _tenant_context()

    response = await service.update_review_state(
        context,
        incident_id=incident.id,
        review_status=IncidentReviewStatus.REVIEWED,
    )

    assert response.review_status == IncidentReviewStatus.REVIEWED
    assert response.reviewed_at is not None
    assert response.reviewed_by_subject == "operator-1"
    assert incident.review_status == IncidentReviewStatus.REVIEWED
    assert incident.reviewed_at is not None
    assert incident.reviewed_by_subject == "operator-1"
    assert audit.calls[0]["action"] == "incident.review"
    assert audit.calls[0]["target"] == f"incident:{incident.id}"
    assert audit.calls[0]["tenant_context"] == context
    assert audit.calls[0]["meta"] == {
        "review_status": "reviewed",
        "previous_review_status": "pending",
        "camera_id": str(incident.camera_id),
        "incident_type": "ppe-missing",
        "user_subject": "operator-1",
    }


@pytest.mark.asyncio
async def test_update_review_state_reopens_incident_and_clears_reviewer() -> None:
    incident = _incident()
    incident.review_status = IncidentReviewStatus.REVIEWED
    incident.reviewed_at = datetime(2026, 4, 28, 10, 5, tzinfo=UTC)
    incident.reviewed_by_subject = "operator-1"
    service = IncidentService(_FakeSessionFactory((incident, "Forklift Gate")), audit_logger=None)

    response = await service.update_review_state(
        _tenant_context(),
        incident_id=incident.id,
        review_status=IncidentReviewStatus.PENDING,
    )

    assert response.review_status == IncidentReviewStatus.PENDING
    assert response.reviewed_at is None
    assert response.reviewed_by_subject is None
    assert incident.review_status == IncidentReviewStatus.PENDING
    assert incident.reviewed_at is None
    assert incident.reviewed_by_subject is None


@pytest.mark.asyncio
async def test_update_review_state_is_idempotent() -> None:
    incident = _incident()
    audit = _FakeAuditLogger()
    session_factory = _FakeSessionFactory((incident, "Forklift Gate"))
    service = IncidentService(session_factory, audit_logger=audit)

    response = await service.update_review_state(
        _tenant_context(),
        incident_id=incident.id,
        review_status=IncidentReviewStatus.PENDING,
    )

    assert response.review_status == IncidentReviewStatus.PENDING
    assert audit.calls == []
    assert session_factory.state.get("commits", 0) == 0


@pytest.mark.asyncio
async def test_update_review_state_raises_404_when_incident_not_in_tenant_scope() -> None:
    service = IncidentService(_FakeSessionFactory(None), audit_logger=None)

    with pytest.raises(HTTPException) as exc_info:
        await service.update_review_state(
            _tenant_context(),
            incident_id=uuid4(),
            review_status=IncidentReviewStatus.REVIEWED,
        )

    assert exc_info.value.status_code == 404
    assert exc_info.value.detail == "Incident not found."
```

- [ ] **Step 4: Run service tests to verify failure**

Run:

```bash
cd /Users/yann.moren/vision/backend
python3 -m uv run pytest tests/services/test_incident_service.py -q
```

Expected: fail because `IncidentService` does not accept `audit_logger` and has no `update_review_state`.

- [ ] **Step 5: Update the incident route**

In `backend/src/argus/api/v1/incidents.py`, update imports and aliases:

```python
from argus.api.contracts import IncidentResponse, IncidentReviewUpdate, TenantContext
from argus.models.enums import IncidentReviewStatus, RoleEnum

OperatorUser = Annotated[AuthenticatedUser, Depends(require(RoleEnum.OPERATOR))]
ReviewStatusQuery = Annotated[IncidentReviewStatus | None, Query()]
```

Update `list_incidents`:

```python
@router.get("", response_model=list[IncidentResponse])
async def list_incidents(
    current_user: ViewerUser,
    tenant_context: TenantDependency,
    services: ServicesDependency,
    camera_id: CameraIdQuery = None,
    incident_type: IncidentTypeQuery = None,
    review_status: ReviewStatusQuery = None,
    limit: LimitQuery = 50,
) -> list[IncidentResponse]:
    return await services.incidents.list_incidents(
        tenant_context,
        camera_id=camera_id,
        incident_type=incident_type,
        review_status=review_status,
        limit=limit,
    )
```

Add the mutation route below it:

```python
@router.patch("/{incident_id}/review", response_model=IncidentResponse)
async def update_incident_review(
    incident_id: UUID,
    payload: IncidentReviewUpdate,
    current_user: OperatorUser,
    tenant_context: TenantDependency,
    services: ServicesDependency,
) -> IncidentResponse:
    return await services.incidents.update_review_state(
        tenant_context,
        incident_id=incident_id,
        review_status=payload.review_status,
    )
```

- [ ] **Step 6: Update `IncidentService`**

In `backend/src/argus/services/app.py`, import `IncidentReviewStatus` from `argus.models.enums`.

Replace the current `IncidentService` with:

```python
class IncidentService:
    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession],
        audit_logger: DatabaseAuditLogger | None = None,
    ) -> None:
        self.session_factory = session_factory
        self.audit_logger = audit_logger

    async def list_incidents(
        self,
        tenant_context: TenantContext,
        *,
        camera_id: UUID | None,
        incident_type: str | None,
        review_status: IncidentReviewStatus | None,
        limit: int,
    ) -> list[IncidentResponse]:
        async with self.session_factory() as session:
            if camera_id is not None:
                await _load_camera(session, tenant_context.tenant_id, camera_id)
            statement = (
                select(Incident, Camera.name)
                .join(Camera, Camera.id == Incident.camera_id)
                .join(Site, Site.id == Camera.site_id)
                .where(Site.tenant_id == tenant_context.tenant_id)
                .order_by(Incident.ts.desc())
                .limit(limit)
            )
            if camera_id is not None:
                statement = statement.where(Incident.camera_id == camera_id)
            if incident_type is not None:
                statement = statement.where(Incident.type == incident_type)
            if review_status is not None:
                statement = statement.where(Incident.review_status == review_status)
            incidents = (await session.execute(statement)).all()
        return [
            _incident_response(incident, camera_name)
            for incident, camera_name in incidents
        ]

    async def update_review_state(
        self,
        tenant_context: TenantContext,
        *,
        incident_id: UUID,
        review_status: IncidentReviewStatus,
    ) -> IncidentResponse:
        async with self.session_factory() as session:
            statement = (
                select(Incident, Camera.name)
                .join(Camera, Camera.id == Incident.camera_id)
                .join(Site, Site.id == Camera.site_id)
                .where(Site.tenant_id == tenant_context.tenant_id)
                .where(Incident.id == incident_id)
            )
            row = (await session.execute(statement)).one_or_none()
            if row is None:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Incident not found.")

            incident, camera_name = row
            previous_review_status = incident.review_status
            changed = previous_review_status != review_status
            if changed:
                incident.review_status = review_status
                if review_status == IncidentReviewStatus.REVIEWED:
                    incident.reviewed_at = datetime.now(tz=UTC)
                    incident.reviewed_by_subject = tenant_context.user.subject
                else:
                    incident.reviewed_at = None
                    incident.reviewed_by_subject = None
                await session.commit()
                await session.refresh(incident)

            response = _incident_response(incident, camera_name)

        if changed and self.audit_logger is not None:
            await self.audit_logger.record(
                tenant_context=tenant_context,
                action="incident.review",
                target=f"incident:{incident_id}",
                meta={
                    "review_status": review_status.value,
                    "previous_review_status": previous_review_status.value,
                    "camera_id": str(response.camera_id),
                    "incident_type": response.type,
                    "user_subject": tenant_context.user.subject,
                },
            )

        return response
```

Add this helper near `IncidentService`:

```python
def _incident_response(incident: Incident, camera_name: str | None) -> IncidentResponse:
    return IncidentResponse(
        id=incident.id,
        camera_id=incident.camera_id,
        camera_name=camera_name,
        ts=incident.ts,
        type=incident.type,
        payload=incident.payload,
        snapshot_url=incident.snapshot_url,
        clip_url=incident.clip_url,
        storage_bytes=incident.storage_bytes,
        review_status=incident.review_status,
        reviewed_at=incident.reviewed_at,
        reviewed_by_subject=incident.reviewed_by_subject,
    )
```

Update `build_app_services` so incidents receives the audit logger:

```python
incidents=IncidentService(db.session_factory, audit_logger),
```

- [ ] **Step 7: Run backend route and service tests**

Run:

```bash
cd /Users/yann.moren/vision/backend
python3 -m uv run pytest tests/api/test_prompt9_routes.py tests/services/test_incident_service.py -q
```

Expected: pass.

- [ ] **Step 8: Run backend lint/type check for changed backend files**

Run:

```bash
cd /Users/yann.moren/vision/backend
python3 -m uv run ruff check src/argus/models/enums.py \
  src/argus/models/tables.py \
  src/argus/api/contracts.py \
  src/argus/api/v1/incidents.py \
  src/argus/services/app.py \
  tests/models/test_schema.py \
  tests/api/test_prompt9_routes.py \
  tests/services/test_incident_service.py
python3 -m uv run mypy src/argus/models/enums.py \
  src/argus/models/tables.py \
  src/argus/api/contracts.py \
  src/argus/api/v1/incidents.py \
  src/argus/services/app.py
```

Expected: both commands pass. If ruff reports the intentional `Camera` import in the service test is unused, remove it.

- [ ] **Step 9: Commit backend API and service work**

Run:

```bash
cd /Users/yann.moren/vision
git add backend/src/argus/api/v1/incidents.py \
        backend/src/argus/services/app.py \
        backend/tests/api/test_prompt9_routes.py \
        backend/tests/services/test_incident_service.py
git commit -m "feat(incidents): persist evidence review state"
```

---

### Task 3: Frontend API Hook And Generated Types

**Files:**
- Modify: `frontend/src/hooks/use-incidents.ts`
- Modify: `frontend/src/lib/api.generated.ts`

- [ ] **Step 1: Generate API types from backend contracts**

Run:

```bash
cd /Users/yann.moren/vision
corepack pnpm --dir frontend generate:api
```

Expected: `frontend/src/lib/api.generated.ts` includes:

- `IncidentReviewStatus`
- `IncidentReviewUpdate`
- `review_status`, `reviewed_at`, `reviewed_by_subject` on `IncidentResponse`
- `patch` operation for `/api/v1/incidents/{incident_id}/review`

- [ ] **Step 2: Update the incidents hook**

Replace `frontend/src/hooks/use-incidents.ts` with:

```ts
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import type { components } from "@/lib/api.generated";
import { apiClient, toApiError } from "@/lib/api";

export type Incident = components["schemas"]["IncidentResponse"];
export type IncidentReviewStatus = Incident["review_status"];

export function useIncidents({
  cameraId,
  incidentType,
  reviewStatus,
  limit = 50,
}: {
  cameraId: string | null;
  incidentType: string | null;
  reviewStatus: IncidentReviewStatus | null;
  limit?: number;
}) {
  return useQuery({
    queryKey: ["incidents", cameraId, incidentType, reviewStatus, limit],
    queryFn: async () => {
      const { data, error } = await apiClient.GET("/api/v1/incidents", {
        params: {
          query: {
            camera_id: cameraId ?? undefined,
            type: incidentType ?? undefined,
            review_status: reviewStatus ?? undefined,
            limit,
          },
        },
      });

      if (error) {
        throw toApiError(error, "Failed to load incidents.");
      }

      return data ?? [];
    },
  });
}

export function useUpdateIncidentReview() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async ({
      incidentId,
      reviewStatus,
    }: {
      incidentId: string;
      reviewStatus: IncidentReviewStatus;
    }) => {
      const { data, error } = await apiClient.PATCH(
        "/api/v1/incidents/{incident_id}/review",
        {
          params: { path: { incident_id: incidentId } },
          body: { review_status: reviewStatus },
        },
      );

      if (error) {
        throw toApiError(error, "Failed to update incident review state.");
      }

      return data;
    },
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ["incidents"] });
    },
  });
}
```

- [ ] **Step 3: Run TypeScript check through frontend tests**

Run:

```bash
cd /Users/yann.moren/vision
corepack pnpm --dir frontend exec vitest run src/pages/Incidents.test.tsx
```

Expected: fail because the page still calls `useIncidents` without `reviewStatus`. This verifies the hook contract is wired.

- [ ] **Step 4: Commit generated types and hook**

Run:

```bash
cd /Users/yann.moren/vision
git add frontend/src/hooks/use-incidents.ts frontend/src/lib/api.generated.ts
git commit -m "feat(frontend): add incident review api hooks"
```

---

### Task 4: Evidence Desk Frontend Tests And Layout

**Files:**
- Modify: `frontend/src/pages/Incidents.tsx`
- Modify: `frontend/src/pages/Incidents.test.tsx`

- [ ] **Step 1: Replace the page test with Evidence Desk coverage**

In `frontend/src/pages/Incidents.test.tsx`, keep the auth setup and `jsonResponse`, but replace the test body with two tests.

Use this shared mock payload:

```ts
function cameraPayload() {
  return {
    id: "11111111-1111-1111-1111-111111111111",
    site_id: "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
    edge_node_id: null,
    name: "Forklift Gate",
    rtsp_url_masked: "rtsp://***",
    processing_mode: "central",
    primary_model_id: "bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb",
    secondary_model_id: null,
    tracker_type: "botsort",
    active_classes: ["person"],
    attribute_rules: [],
    zones: [],
    homography: null,
    privacy: {
      blur_faces: true,
      blur_plates: true,
      method: "gaussian",
      strength: 7,
    },
    browser_delivery: {
      default_profile: "720p10",
      allow_native_on_demand: true,
      profiles: [],
    },
    frame_skip: 1,
    fps_cap: 25,
    created_at: "2026-04-18T10:00:00Z",
    updated_at: "2026-04-18T10:00:00Z",
  };
}

function incidentPayload(overrides: Record<string, unknown> = {}) {
  return {
    id: "99999999-9999-9999-9999-999999999999",
    camera_id: "11111111-1111-1111-1111-111111111111",
    camera_name: "Forklift Gate",
    ts: "2026-04-18T10:15:00Z",
    type: "ppe-missing",
    payload: { hard_hat: false, severity: "high" },
    snapshot_url: null,
    clip_url: "https://minio.local/signed/incidents/forklift-gate.mjpeg",
    storage_bytes: 2097152,
    review_status: "pending",
    reviewed_at: null,
    reviewed_by_subject: null,
    ...overrides,
  };
}
```

Add:

```tsx
test("renders evidence desk queue, clip-only hero, facts, and filters", async () => {
  const user = userEvent.setup();
  const requests: Request[] = [];

  vi.spyOn(global, "fetch").mockImplementation((input, init) => {
    const request = input instanceof Request ? input : new Request(String(input), init);
    requests.push(request);
    const url = new URL(request.url);

    if (url.pathname === "/api/v1/cameras") {
      return Promise.resolve(jsonResponse([cameraPayload()]));
    }

    if (url.pathname === "/api/v1/incidents") {
      return Promise.resolve(jsonResponse([incidentPayload({ type: url.searchParams.get("type") ?? "ppe-missing" })]));
    }

    return Promise.resolve(new Response("Not found", { status: 404 }));
  });

  render(
    <QueryClientProvider client={createQueryClient()}>
      <IncidentsPage />
    </QueryClientProvider>,
  );

  expect(await screen.findByText(/queue/i)).toBeInTheDocument();
  expect(screen.getByText(/incident facts/i)).toBeInTheDocument();
  expect(screen.getByText(/clip-only evidence/i)).toBeInTheDocument();
  expect(screen.getByRole("link", { name: /open clip/i })).toHaveAttribute(
    "href",
    "https://minio.local/signed/incidents/forklift-gate.mjpeg",
  );
  expect(screen.getByRole("button", { name: /review/i })).toBeInTheDocument();
  expect(screen.getByText("2.0 MB secured")).toBeInTheDocument();

  await user.selectOptions(screen.getByLabelText(/camera filter/i), [
    "11111111-1111-1111-1111-111111111111",
  ]);
  await user.selectOptions(screen.getByLabelText(/incident type/i), ["ppe-missing"]);
  await user.selectOptions(screen.getByLabelText(/review status/i), ["reviewed"]);

  await waitFor(() => {
    const incidentRequests = requests.filter(
      (request) => new URL(request.url).pathname === "/api/v1/incidents",
    );
    expect(incidentRequests.length).toBeGreaterThan(1);

    const latestUrl = new URL((incidentRequests.at(-1) as Request).url);
    expect(latestUrl.searchParams.get("camera_id")).toBe(
      "11111111-1111-1111-1111-111111111111",
    );
    expect(latestUrl.searchParams.get("type")).toBe("ppe-missing");
    expect(latestUrl.searchParams.get("review_status")).toBe("reviewed");
  });
});
```

Add:

```tsx
test("persists review state from the evidence hero", async () => {
  const user = userEvent.setup();
  const requests: Request[] = [];
  let incident = incidentPayload();

  vi.spyOn(global, "fetch").mockImplementation(async (input, init) => {
    const request = input instanceof Request ? input : new Request(String(input), init);
    requests.push(request);
    const url = new URL(request.url);

    if (url.pathname === "/api/v1/cameras") {
      return jsonResponse([cameraPayload()]);
    }

    if (url.pathname === "/api/v1/incidents") {
      return jsonResponse([incident]);
    }

    if (url.pathname === "/api/v1/incidents/99999999-9999-9999-9999-999999999999/review") {
      const body = (await request.json()) as { review_status: string };
      incident = incidentPayload({
        review_status: body.review_status,
        reviewed_at: "2026-04-18T10:20:00Z",
        reviewed_by_subject: "analyst-1",
      });
      return jsonResponse(incident);
    }

    return new Response("Not found", { status: 404 });
  });

  render(
    <QueryClientProvider client={createQueryClient()}>
      <IncidentsPage />
    </QueryClientProvider>,
  );

  await screen.findByText(/clip-only evidence/i);
  await user.click(screen.getByRole("button", { name: /review/i }));

  await waitFor(() => {
    expect(screen.getByRole("button", { name: /reopen/i })).toBeInTheDocument();
  });

  const reviewRequest = requests.find(
    (request) =>
      new URL(request.url).pathname ===
      "/api/v1/incidents/99999999-9999-9999-9999-999999999999/review",
  );
  expect(reviewRequest?.method).toBe("PATCH");
});
```

- [ ] **Step 2: Run frontend page tests to verify failure**

Run:

```bash
cd /Users/yann.moren/vision
corepack pnpm --dir frontend exec vitest run src/pages/Incidents.test.tsx
```

Expected: fail because the page is still equal-weight cards and has no review status filter/mutation.

- [ ] **Step 3: Refactor `Incidents.tsx` into Evidence Desk**

Replace `frontend/src/pages/Incidents.tsx` with this implementation:

```tsx
import { useEffect, useMemo, useState } from "react";

import { Badge } from "@/components/ui/badge";
import { Select } from "@/components/ui/select";
import { useCameras } from "@/hooks/use-cameras";
import {
  type Incident,
  type IncidentReviewStatus,
  useIncidents,
  useUpdateIncidentReview,
} from "@/hooks/use-incidents";

type ReviewFilter = IncidentReviewStatus | "all";

export function IncidentsPage() {
  const { data: cameras = [] } = useCameras();
  const cameraNamesById = useMemo(
    () => new Map(cameras.map((camera) => [camera.id, camera.name])),
    [cameras],
  );
  const [selectedCameraId, setSelectedCameraId] = useState<string | null>(null);
  const [selectedType, setSelectedType] = useState<string | null>(null);
  const [selectedReviewStatus, setSelectedReviewStatus] = useState<ReviewFilter>("pending");
  const [selectedIncidentId, setSelectedIncidentId] = useState<string | null>(null);
  const reviewStatusFilter = selectedReviewStatus === "all" ? null : selectedReviewStatus;
  const { data: incidents = [], isLoading, error } = useIncidents({
    cameraId: selectedCameraId,
    incidentType: selectedType,
    reviewStatus: reviewStatusFilter,
    limit: 50,
  });
  const reviewMutation = useUpdateIncidentReview();

  const incidentTypes = useMemo(
    () => Array.from(new Set(incidents.map((incident) => incident.type))).sort(),
    [incidents],
  );
  const selectedIncident =
    incidents.find((incident) => incident.id === selectedIncidentId) ?? incidents[0] ?? null;

  useEffect(() => {
    if (incidents.length === 0) {
      if (selectedIncidentId !== null) setSelectedIncidentId(null);
      return;
    }
    if (!selectedIncidentId || !incidents.some((incident) => incident.id === selectedIncidentId)) {
      setSelectedIncidentId(incidents[0].id);
    }
  }, [incidents, selectedIncidentId]);

  const selectedCameraName =
    selectedIncident?.camera_name ??
    (selectedIncident ? cameraNamesById.get(selectedIncident.camera_id) : null) ??
    null;

  return (
    <div className="space-y-6">
      <section className="overflow-hidden rounded-[2rem] border border-white/10 bg-[linear-gradient(180deg,rgba(13,18,29,0.98),rgba(5,8,14,0.96))] shadow-[0_36px_100px_-62px_rgba(53,107,255,0.42)]">
        <div className="border-b border-white/8 px-6 py-5">
          <div className="flex flex-wrap items-start justify-between gap-4">
            <div>
              <p className="text-[11px] font-semibold uppercase tracking-[0.26em] text-[#9db3d3]">
                Evidence Desk
              </p>
              <h2 className="mt-3 text-3xl font-semibold tracking-[0.01em] text-[#f4f8ff]">
                Review captured incidents and clear the evidence queue.
              </h2>
              <p className="mt-3 max-w-3xl text-sm text-[#93a7c5]">
                These incidents were already matched by rules or inference. Open the signed clip,
                inspect the facts, and persist the review decision.
              </p>
            </div>

            <Badge className="border-[#29436f] bg-[#08111d]/80 text-[#d7e4ff]">
              {incidents.length} in queue
            </Badge>
          </div>
        </div>

        <div className="grid gap-5 border-b border-white/8 px-6 py-5 md:grid-cols-3">
          <IncidentFilters
            cameras={cameras}
            incidentTypes={incidentTypes}
            selectedCameraId={selectedCameraId}
            selectedType={selectedType}
            selectedReviewStatus={selectedReviewStatus}
            onCameraChange={setSelectedCameraId}
            onTypeChange={setSelectedType}
            onReviewStatusChange={setSelectedReviewStatus}
          />
        </div>

        {isLoading ? (
          <div className="px-6 py-6 text-sm text-[#93a7c5]">Loading evidence desk...</div>
        ) : error ? (
          <div className="px-6 py-6 text-sm text-[#f0b7c1]">
            {error instanceof Error ? error.message : "Failed to load incidents."}
          </div>
        ) : incidents.length === 0 ? (
          <div className="px-6 py-6 text-sm text-[#93a7c5]">
            No incidents matched the current camera, type, and review filters.
          </div>
        ) : (
          <div className="grid gap-5 px-6 py-6 xl:grid-cols-[320px_minmax(0,1fr)_320px]">
            <IncidentQueue
              incidents={incidents}
              cameraNamesById={cameraNamesById}
              selectedId={selectedIncident?.id ?? null}
              onSelect={setSelectedIncidentId}
            />
            <IncidentEvidenceHero
              incident={selectedIncident}
              cameraName={selectedCameraName}
              isUpdating={reviewMutation.isPending}
              error={reviewMutation.error}
              onReviewToggle={(incident) => {
                reviewMutation.mutate({
                  incidentId: incident.id,
                  reviewStatus: incident.review_status === "reviewed" ? "pending" : "reviewed",
                });
              }}
            />
            <IncidentFactsPanel incident={selectedIncident} cameraName={selectedCameraName} />
          </div>
        )}
      </section>
    </div>
  );
}
```

Then add helper components below the page in the same file:

```tsx
function IncidentFilters({
  cameras,
  incidentTypes,
  selectedCameraId,
  selectedType,
  selectedReviewStatus,
  onCameraChange,
  onTypeChange,
  onReviewStatusChange,
}: {
  cameras: { id: string; name: string }[];
  incidentTypes: string[];
  selectedCameraId: string | null;
  selectedType: string | null;
  selectedReviewStatus: ReviewFilter;
  onCameraChange: (cameraId: string | null) => void;
  onTypeChange: (incidentType: string | null) => void;
  onReviewStatusChange: (status: ReviewFilter) => void;
}) {
  return (
    <>
      <label className="space-y-2 text-sm text-[#d9e5f7]">
        <span className="text-[11px] font-semibold uppercase tracking-[0.2em] text-[#8ea8cf]">
          Camera filter
        </span>
        <Select
          aria-label="Camera filter"
          value={selectedCameraId ?? ""}
          onChange={(event) => onCameraChange(event.target.value || null)}
        >
          <option value="">All cameras</option>
          {cameras.map((camera) => (
            <option key={camera.id} value={camera.id}>
              {camera.name}
            </option>
          ))}
        </Select>
      </label>

      <label className="space-y-2 text-sm text-[#d9e5f7]">
        <span className="text-[11px] font-semibold uppercase tracking-[0.2em] text-[#8ea8cf]">
          Incident type
        </span>
        <Select
          aria-label="Incident type"
          value={selectedType ?? ""}
          onChange={(event) => onTypeChange(event.target.value || null)}
        >
          <option value="">All types</option>
          {incidentTypes.map((incidentType) => (
            <option key={incidentType} value={incidentType}>
              {incidentType}
            </option>
          ))}
        </Select>
      </label>

      <label className="space-y-2 text-sm text-[#d9e5f7]">
        <span className="text-[11px] font-semibold uppercase tracking-[0.2em] text-[#8ea8cf]">
          Review status
        </span>
        <Select
          aria-label="Review status"
          value={selectedReviewStatus}
          onChange={(event) => onReviewStatusChange(event.target.value as ReviewFilter)}
        >
          <option value="pending">Pending</option>
          <option value="reviewed">Reviewed</option>
          <option value="all">All</option>
        </Select>
      </label>
    </>
  );
}
```

Add queue, hero, and facts helpers:

```tsx
function IncidentQueue({
  incidents,
  cameraNamesById,
  selectedId,
  onSelect,
}: {
  incidents: Incident[];
  cameraNamesById: Map<string, string>;
  selectedId: string | null;
  onSelect: (incidentId: string) => void;
}) {
  return (
    <aside className="rounded-[1.4rem] border border-white/10 bg-[#060b13] p-4">
      <div className="flex items-center justify-between gap-3">
        <h3 className="text-[11px] font-semibold uppercase tracking-[0.22em] text-[#8ea8cf]">
          Queue
        </h3>
        <span className="text-xs text-[#7e95ba]">{incidents.length} incidents</span>
      </div>
      <div className="mt-4 space-y-2">
        {incidents.map((incident) => {
          const cameraName = incident.camera_name ?? cameraNamesById.get(incident.camera_id) ?? "Camera";
          const isSelected = incident.id === selectedId;
          return (
            <button
              key={incident.id}
              type="button"
              onClick={() => onSelect(incident.id)}
              className={`w-full rounded-[1rem] border px-3 py-3 text-left transition ${
                isSelected
                  ? "border-[#5e8cff] bg-[#10213d] text-white"
                  : "border-white/8 bg-white/[0.03] text-[#d8e2f2] hover:border-[#35538a]"
              }`}
            >
              <span className="block text-sm font-semibold">{cameraName}</span>
              <span className="mt-1 block text-xs text-[#9db3d3]">{incident.type}</span>
              <span className="mt-2 flex items-center justify-between gap-2 text-[11px] uppercase tracking-[0.16em] text-[#7e95ba]">
                <span>{formatIncidentTime(incident.ts)}</span>
                <span>{incident.review_status}</span>
              </span>
            </button>
          );
        })}
      </div>
    </aside>
  );
}

function IncidentEvidenceHero({
  incident,
  cameraName,
  isUpdating,
  error,
  onReviewToggle,
}: {
  incident: Incident | null;
  cameraName: string | null;
  isUpdating: boolean;
  error: Error | null;
  onReviewToggle: (incident: Incident) => void;
}) {
  if (!incident) {
    return null;
  }

  const clipStorageLabel = storageLabel(incident);
  const reviewAction = incident.review_status === "reviewed" ? "Reopen" : "Review";

  return (
    <section className="rounded-[1.4rem] border border-white/10 bg-[#060b13] p-4">
      <div className="overflow-hidden rounded-[1.2rem] border border-white/8 bg-[#03070d]">
        {incident.snapshot_url ? (
          <img
            src={incident.snapshot_url}
            alt={`Incident preview for ${cameraName ?? "camera"}`}
            className="aspect-video h-full w-full object-cover"
          />
        ) : (
          <div className="flex aspect-video flex-col items-center justify-center gap-2 px-6 text-center">
            <p className="text-sm font-semibold text-[#e8f0ff]">Clip-only evidence</p>
            <p className="max-w-md text-sm text-[#8ea8cf]">
              This incident has recorded clip evidence but no still preview yet.
            </p>
          </div>
        )}
      </div>

      <div className="mt-4 flex flex-wrap items-center justify-between gap-3">
        <div>
          <Badge className="border-[#29436f] bg-[#08111d]/80 text-[#d7e4ff]">
            {incident.type}
          </Badge>
          <p className="mt-2 text-sm text-[#8ea8cf]">{cameraName ?? incident.camera_id}</p>
          {clipStorageLabel ? <p className="mt-1 text-xs text-[#7e95ba]">{clipStorageLabel}</p> : null}
        </div>

        <div className="flex flex-wrap items-center gap-2">
          {incident.clip_url ? (
            <a
              href={incident.clip_url}
              target="_blank"
              rel="noreferrer"
              className="inline-flex items-center rounded-full border border-[#33528a] bg-[#08111d]/85 px-3 py-1.5 text-xs font-semibold uppercase tracking-[0.18em] text-[#dce8ff] transition hover:border-[#5c7dd0] hover:text-white"
            >
              Open clip
            </a>
          ) : (
            <Badge className="border-[#2d3748] bg-[#0b1018] text-[#9cb0cf]">
              Clip unavailable
            </Badge>
          )}
          <button
            type="button"
            onClick={() => onReviewToggle(incident)}
            disabled={isUpdating}
            className="inline-flex items-center rounded-full border border-[#5e8cff] bg-[#1b3f84] px-3 py-1.5 text-xs font-semibold uppercase tracking-[0.18em] text-white transition hover:bg-[#2553a8] disabled:cursor-not-allowed disabled:opacity-60"
          >
            {isUpdating ? "Saving" : reviewAction}
          </button>
        </div>
      </div>

      {error ? (
        <p className="mt-3 text-sm text-[#f0b7c1]">
          {error.message}
        </p>
      ) : null}
    </section>
  );
}

function IncidentFactsPanel({
  incident,
  cameraName,
}: {
  incident: Incident | null;
  cameraName: string | null;
}) {
  if (!incident) {
    return null;
  }

  const facts = [
    ["Camera", cameraName ?? incident.camera_id],
    ["Incident type", incident.type],
    ["Timestamp", formatIncidentTime(incident.ts)],
    ["Review status", incident.review_status],
    ["Reviewed at", incident.reviewed_at ? formatIncidentTime(incident.reviewed_at) : "Not reviewed"],
    ["Reviewed by", incident.reviewed_by_subject ?? "Not reviewed"],
    ["Storage", storageLabel(incident) ?? "No clip stored"],
  ];

  return (
    <aside className="rounded-[1.4rem] border border-white/10 bg-[#060b13] p-4">
      <h3 className="text-[11px] font-semibold uppercase tracking-[0.22em] text-[#8ea8cf]">
        Incident facts
      </h3>
      <dl className="mt-4 space-y-3">
        {facts.map(([label, value]) => (
          <div key={label} className="rounded-[1rem] border border-white/8 bg-white/[0.03] px-3 py-2">
            <dt className="text-[11px] font-semibold uppercase tracking-[0.18em] text-[#6f84a6]">
              {label}
            </dt>
            <dd className="mt-1 break-words text-sm text-[#d8e2f2]">{value}</dd>
          </div>
        ))}
        {Object.entries(incident.payload).map(([key, value]) => (
          <div key={key} className="rounded-[1rem] border border-white/8 bg-white/[0.03] px-3 py-2">
            <dt className="text-[11px] font-semibold uppercase tracking-[0.18em] text-[#6f84a6]">
              {key}
            </dt>
            <dd className="mt-1 break-words text-sm text-[#d8e2f2]">{String(value)}</dd>
          </div>
        ))}
      </dl>
    </aside>
  );
}

function storageLabel(incident: Incident) {
  return incident.storage_bytes > 0
    ? `${(incident.storage_bytes / (1024 * 1024)).toFixed(1)} MB secured`
    : null;
}

function formatIncidentTime(value: string) {
  return new Date(value).toLocaleString("en-GB", {
    year: "numeric",
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}
```

- [ ] **Step 4: Run frontend page tests**

Run:

```bash
cd /Users/yann.moren/vision
corepack pnpm --dir frontend exec vitest run src/pages/Incidents.test.tsx
```

Expected: pass.

- [ ] **Step 5: Commit frontend Evidence Desk layout**

Run:

```bash
cd /Users/yann.moren/vision
git add frontend/src/pages/Incidents.tsx frontend/src/pages/Incidents.test.tsx
git commit -m "feat(incidents): add evidence desk review UI"
```

---

### Task 5: Playwright Coverage And Final Verification

**Files:**
- Modify: `frontend/e2e/prompt9-history-and-incidents.spec.ts`

- [ ] **Step 1: Update the Playwright incident mock**

In `frontend/e2e/prompt9-history-and-incidents.spec.ts`, replace the `page.route("**/api/v1/incidents**"...` block in the first test with:

```ts
let incident = {
  id: "99999999-9999-9999-9999-999999999999",
  camera_id: "11111111-1111-1111-1111-111111111111",
  camera_name: "Forklift Gate",
  ts: "2026-04-18T10:15:00Z",
  type: "ppe-missing",
  payload: { hard_hat: false, severity: "high" },
  snapshot_url: null,
  clip_url: "https://minio.local/signed/incidents/forklift-gate.mjpeg",
  storage_bytes: 2097152,
  review_status: "pending",
  reviewed_at: null,
  reviewed_by_subject: null,
};

await page.route("**/api/v1/incidents**", async (route) => {
  const request = route.request();
  const url = new URL(request.url());

  if (request.method() === "PATCH" && url.pathname.endsWith("/review")) {
    const body = request.postDataJSON() as { review_status: string };
    incident = {
      ...incident,
      review_status: body.review_status,
      reviewed_at: body.review_status === "reviewed" ? "2026-04-18T10:20:00Z" : null,
      reviewed_by_subject: body.review_status === "reviewed" ? "admin-dev" : null,
    };
    await route.fulfill({
      contentType: "application/json",
      body: JSON.stringify(incident),
    });
    return;
  }

  await route.fulfill({
    contentType: "application/json",
    body: JSON.stringify([incident]),
  });
});
```

- [ ] **Step 2: Update Playwright assertions**

Replace the final incidents assertions in the first Playwright test with:

```ts
await operationsLink(page, "Incidents").click();
await expect(page).toHaveURL(/\/incidents$/);
await expect(page.getByText(/queue/i)).toBeVisible();
await expect(page.getByText(/incident facts/i)).toBeVisible();
await expect(page.getByText(/clip-only evidence/i)).toBeVisible();
await expect(page.getByRole("link", { name: /open clip/i })).toBeVisible();
await page.getByRole("button", { name: /^review$/i }).click();
await expect(page.getByRole("button", { name: /^reopen$/i })).toBeVisible();
```

- [ ] **Step 3: Run Playwright incident/history spec**

Run:

```bash
cd /Users/yann.moren/vision
corepack pnpm --dir frontend exec playwright test e2e/prompt9-history-and-incidents.spec.ts
```

Expected: pass.

- [ ] **Step 4: Run focused backend verification**

Run:

```bash
cd /Users/yann.moren/vision/backend
python3 -m uv run pytest \
  tests/models/test_schema.py \
  tests/api/test_prompt9_routes.py \
  tests/services/test_incident_service.py \
  tests/services/test_incident_capture.py -q
```

Expected: pass.

- [ ] **Step 5: Run focused frontend verification**

Run:

```bash
cd /Users/yann.moren/vision
corepack pnpm --dir frontend exec vitest run src/pages/Incidents.test.tsx
corepack pnpm --dir frontend build
```

Expected: tests pass and production build succeeds.

- [ ] **Step 6: Run lint and type checks for changed backend files**

Run:

```bash
cd /Users/yann.moren/vision/backend
python3 -m uv run ruff check src/argus/models/enums.py \
  src/argus/models/tables.py \
  src/argus/api/contracts.py \
  src/argus/api/v1/incidents.py \
  src/argus/services/app.py \
  tests/models/test_schema.py \
  tests/api/test_prompt9_routes.py \
  tests/services/test_incident_service.py
python3 -m uv run mypy src/argus/models/enums.py \
  src/argus/models/tables.py \
  src/argus/api/contracts.py \
  src/argus/api/v1/incidents.py \
  src/argus/services/app.py
```

Expected: pass.

- [ ] **Step 7: Commit E2E and final verification changes**

Run:

```bash
cd /Users/yann.moren/vision
git add frontend/e2e/prompt9-history-and-incidents.spec.ts
git commit -m "test(incidents): cover evidence desk review flow"
```

- [ ] **Step 8: Push the branch**

Run:

```bash
cd /Users/yann.moren/vision
git push origin codex/source-aware-delivery-calibration-fixes
```

Expected: branch pushes successfully.
