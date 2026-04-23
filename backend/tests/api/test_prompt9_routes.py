from __future__ import annotations

from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from uuid import UUID, uuid4

import pytest
from httpx import ASGITransport, AsyncClient

from argus.api.contracts import ExportArtifact, HistoryPoint, IncidentResponse, TenantContext
from argus.core.config import Settings
from argus.core.security import AuthenticatedUser, get_current_user
from argus.main import create_app
from argus.models.enums import RoleEnum


def _sample_user() -> AuthenticatedUser:
    return AuthenticatedUser(
        subject="user-1",
        email="analyst@argus.local",
        role=RoleEnum.VIEWER,
        issuer="http://localhost:8080/realms/argus-dev",
        realm="argus-dev",
        is_superadmin=False,
        tenant_context=str(uuid4()),
        claims={},
    )


def _tenant_context(user: AuthenticatedUser) -> TenantContext:
    return TenantContext(
        tenant_id=UUID(str(user.tenant_context)),
        tenant_slug=user.realm,
        user=user,
    )


class RecordingTenancyService:
    def __init__(self, context: TenantContext) -> None:
        self.context = context

    async def resolve_context(
        self,
        *,
        user: AuthenticatedUser,
        explicit_tenant_id: UUID | None = None,
    ) -> TenantContext:
        return TenantContext(
            tenant_id=explicit_tenant_id or self.context.tenant_id,
            tenant_slug=self.context.tenant_slug,
            user=user,
        )


class RecordingHistoryService:
    def __init__(self) -> None:
        self.last_query: dict[str, object] | None = None
        self.last_series_query: dict[str, object] | None = None
        self.last_export: dict[str, object] | None = None

    async def query_history(
        self,
        context: TenantContext,
        *,
        camera_ids: list[UUID] | None,
        class_names: list[str] | None,
        granularity: str,
        starts_at: datetime,
        ends_at: datetime,
    ) -> list[HistoryPoint]:
        self.last_query = {
            "tenant_id": context.tenant_id,
            "camera_ids": camera_ids,
            "class_names": class_names,
            "granularity": granularity,
            "starts_at": starts_at,
            "ends_at": ends_at,
        }
        return [
            HistoryPoint(
                bucket=starts_at,
                camera_id=camera_ids[0] if camera_ids else None,
                class_name="car",
                event_count=18,
                granularity=granularity,
            )
        ]

    async def query_series(
        self,
        context: TenantContext,
        *,
        camera_ids: list[UUID] | None,
        class_names: list[str] | None,
        granularity: str,
        starts_at: datetime,
        ends_at: datetime,
    ) -> dict[str, object]:
        self.last_series_query = {
            "tenant_id": context.tenant_id,
            "camera_ids": camera_ids,
            "class_names": class_names,
            "granularity": granularity,
            "starts_at": starts_at,
            "ends_at": ends_at,
        }
        return {
            "granularity": granularity,
            "class_names": class_names or ["car", "bus"],
            "rows": [
                {
                    "bucket": starts_at.isoformat(),
                    "values": {"car": 18, "bus": 4},
                    "total_count": 22,
                }
            ],
        }

    async def export_history(
        self,
        context: TenantContext,
        *,
        camera_ids: list[UUID] | None,
        class_names: list[str] | None,
        granularity: str,
        starts_at: datetime,
        ends_at: datetime,
        format_name: str,
    ) -> ExportArtifact:
        self.last_export = {
            "tenant_id": context.tenant_id,
            "camera_ids": camera_ids,
            "class_names": class_names,
            "granularity": granularity,
            "starts_at": starts_at,
            "ends_at": ends_at,
            "format_name": format_name,
        }
        return ExportArtifact(
            filename=f"history.{format_name}",
            media_type="text/csv; charset=utf-8",
            content=b"bucket,class_name,event_count\n2026-04-12T00:00:00Z,car,18\n",
        )


class RecordingIncidentService:
    def __init__(self) -> None:
        self.last_query: dict[str, object] | None = None

    async def list_incidents(
        self,
        context: TenantContext,
        *,
        camera_id: UUID | None,
        incident_type: str | None,
        limit: int,
    ) -> list[IncidentResponse]:
        self.last_query = {
            "tenant_id": context.tenant_id,
            "camera_id": camera_id,
            "incident_type": incident_type,
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
            )
        ]


def _create_test_app(
    *,
    user: AuthenticatedUser,
    history: RecordingHistoryService,
    incidents: RecordingIncidentService,
) -> object:
    context = _tenant_context(user)
    app = create_app(
        Settings(
            _env_file=None,
            enable_startup_services=False,
            enable_nats=False,
            enable_tracing=False,
            rtsp_encryption_key="argus-dev-rtsp-key",
        )
    )
    app.state.services = SimpleNamespace(
        tenancy=RecordingTenancyService(context),
        history=history,
        incidents=incidents,
    )
    app.dependency_overrides[get_current_user] = lambda: user
    return app


@pytest.mark.asyncio
async def test_history_route_accepts_multi_filters_and_extended_granularity() -> None:
    user = _sample_user()
    history = RecordingHistoryService()
    app = _create_test_app(user=user, history=history, incidents=RecordingIncidentService())
    camera_a = uuid4()
    camera_b = uuid4()
    starts_at = datetime(2026, 4, 12, 0, 0, tzinfo=UTC)
    ends_at = starts_at + timedelta(days=1)

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://testserver",
    ) as client:
        response = await client.get(
            "/api/v1/history",
            params=[
                ("camera_ids", str(camera_a)),
                ("camera_ids", str(camera_b)),
                ("class_names", "car"),
                ("class_names", "bus"),
                ("granularity", "5m"),
                ("from", starts_at.isoformat()),
                ("to", ends_at.isoformat()),
            ],
        )

    assert response.status_code == 200
    assert response.json()[0]["granularity"] == "5m"
    assert history.last_query == {
        "tenant_id": UUID(str(user.tenant_context)),
        "camera_ids": [camera_a, camera_b],
        "class_names": ["car", "bus"],
        "granularity": "5m",
        "starts_at": starts_at,
        "ends_at": ends_at,
    }


@pytest.mark.asyncio
async def test_history_series_route_returns_chart_ready_rows() -> None:
    user = _sample_user()
    history = RecordingHistoryService()
    app = _create_test_app(user=user, history=history, incidents=RecordingIncidentService())
    starts_at = datetime(2026, 4, 12, 0, 0, tzinfo=UTC)
    ends_at = starts_at + timedelta(days=7)

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://testserver",
    ) as client:
        response = await client.get(
            "/api/v1/history/series",
            params=[
                ("class_names", "car"),
                ("class_names", "bus"),
                ("granularity", "1d"),
                ("from", starts_at.isoformat()),
                ("to", ends_at.isoformat()),
            ],
        )

    assert response.status_code == 200
    assert response.json() == {
        "granularity": "1d",
        "class_names": ["car", "bus"],
        "rows": [
            {
                "bucket": "2026-04-12T00:00:00Z",
                "values": {"car": 18, "bus": 4},
                "total_count": 22,
                "speed_p50": None,
                "speed_p95": None,
                "speed_sample_count": None,
                "over_threshold_count": None,
            }
        ],
        "granularity_adjusted": False,
        "speed_classes_capped": False,
        "speed_classes_used": None,
    }
    assert history.last_series_query == {
        "tenant_id": UUID(str(user.tenant_context)),
        "camera_ids": None,
        "class_names": ["car", "bus"],
        "granularity": "1d",
        "starts_at": starts_at,
        "ends_at": ends_at,
    }


@pytest.mark.asyncio
async def test_export_route_accepts_multi_filters_and_extended_granularity() -> None:
    user = _sample_user()
    history = RecordingHistoryService()
    app = _create_test_app(user=user, history=history, incidents=RecordingIncidentService())
    camera_id = uuid4()
    starts_at = datetime(2026, 4, 12, 0, 0, tzinfo=UTC)
    ends_at = starts_at + timedelta(days=1)

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://testserver",
    ) as client:
        response = await client.get(
            "/api/v1/export",
            params=[
                ("camera_ids", str(camera_id)),
                ("class_names", "car"),
                ("granularity", "1d"),
                ("from", starts_at.isoformat()),
                ("to", ends_at.isoformat()),
                ("format", "csv"),
            ],
        )

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/csv")
    assert history.last_export == {
        "tenant_id": UUID(str(user.tenant_context)),
        "camera_ids": [camera_id],
        "class_names": ["car"],
        "granularity": "1d",
        "starts_at": starts_at,
        "ends_at": ends_at,
        "format_name": "csv",
    }


@pytest.mark.asyncio
async def test_incidents_route_passes_camera_type_and_limit_filters() -> None:
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
                "limit": "25",
            },
        )

    assert response.status_code == 200
    assert response.json()[0]["type"] == "ppe-missing"
    assert response.json()[0]["clip_url"] == "https://minio.local/signed/incidents/1.mjpeg"
    assert response.json()[0]["storage_bytes"] == 2_097_152
    assert incidents.last_query == {
        "tenant_id": UUID(str(user.tenant_context)),
        "camera_id": camera_id,
        "incident_type": "ppe-missing",
        "limit": 25,
    }
