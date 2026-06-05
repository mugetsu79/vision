from __future__ import annotations

from collections.abc import AsyncIterator
from datetime import datetime, timedelta
from pathlib import Path
from types import SimpleNamespace
from uuid import UUID

import pytest
import pytest_asyncio
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy import ForeignKeyConstraint, UniqueConstraint

from argus.api.contracts import TenantContext
from argus.api.v1 import router
from argus.compat import UTC
from argus.core.security import AuthenticatedUser
from argus.link.service import LinkService
from argus.maritime.evidence import MaritimeEvidenceNotFoundError, MaritimeEvidenceService
from argus.maritime.service import MaritimeRuntimeService
from argus.maritime.tables import MaritimeEvidenceContext, MaritimeEvidenceExport
from argus.maritime.telemetry import AISJsonAdapter, CarrierWebhookAdapter
from argus.models.enums import RoleEnum
from argus.models.tables import Camera, Incident
from argus.services.pack_registry import PackRegistry

REPO_ROOT = Path(__file__).resolve().parents[3]
PACKS_ROOT = REPO_ROOT / "packs"
TENANT_ID = UUID("00000000-0000-4000-8000-000000000001")
SITE_ID = UUID("00000000-0000-4000-8000-000000000002")
CAMERA_ID = UUID("00000000-0000-4000-8000-000000000003")
INCIDENT_ID = UUID("00000000-0000-4000-8000-000000000004")
ARTIFACT_ID = UUID("00000000-0000-4000-8000-000000000005")
OTHER_TENANT_ID = UUID("00000000-0000-4000-8000-000000000099")
INCIDENT_TIME = datetime(2026, 6, 5, 9, 15, tzinfo=UTC)


@pytest_asyncio.fixture
async def evidence_service() -> MaritimeEvidenceService:
    maritime = MaritimeRuntimeService(pack_registry=PackRegistry(PACKS_ROOT))
    link = LinkService()
    service = MaritimeEvidenceService(
        maritime_service=maritime,
        link_service=link,
        tenant_id=TENANT_ID,
    )
    service.register_camera_site(camera_id=CAMERA_ID, site_id=SITE_ID)
    service.register_incident(
        incident_id=INCIDENT_ID,
        camera_id=CAMERA_ID,
        incident_time=INCIDENT_TIME,
        scene_contract_hash="scene-hash-a",
        privacy_manifest_hash="privacy-hash-a",
        runtime_passport_hash="runtime-hash-a",
        recording_policy={"mode": "event_clip", "retention_days": 30},
        artifact_hashes={ARTIFACT_ID: "abc123"},
        ledger_summary={"entry_count": 2, "latest_action": "evidence_upload_available"},
        time_source={"source": "camera_clock", "synced": True},
    )
    vessel = maritime.create_vessel(
        tenant_id=TENANT_ID,
        site_id=SITE_ID,
        name="MV Resolute",
        mmsi="235012345",
    )
    voyage = maritime.create_voyage(
        tenant_id=TENANT_ID,
        vessel_id=vessel.id,
        name="Rotterdam Approach",
        scheduled_departure_at=INCIDENT_TIME - timedelta(hours=4),
        scheduled_arrival_at=INCIDENT_TIME + timedelta(hours=4),
    )
    maritime.activate_voyage(tenant_id=TENANT_ID, voyage_id=voyage.id)
    maritime.create_port_call(
        tenant_id=TENANT_ID,
        voyage_id=voyage.id,
        port_name="Rotterdam",
        un_locode="NLRTM",
        eta=INCIDENT_TIME - timedelta(hours=1),
        etd=INCIDENT_TIME + timedelta(hours=1),
    )
    maritime.ingest_ais_position(
        tenant_id=TENANT_ID,
        vessel_id=vessel.id,
        reading=AISJsonAdapter().parse(
            {
                "mmsi": "235012345",
                "lat": 51.95,
                "lon": 4.14,
                "reported_at": "2026-06-05T09:14:00Z",
            }
        ),
    )
    maritime.upsert_carrier_terminal(
        tenant_id=TENANT_ID,
        vessel_id=vessel.id,
        reading=CarrierWebhookAdapter().parse(
            {
                "terminal_id": "starlink-a",
                "status": "online",
                "link_state": "satellite_good",
                "last_seen_at": "2026-06-05T09:14:30Z",
            }
        ),
    )
    link.enqueue_transfer(
        tenant_id=TENANT_ID,
        site_id=SITE_ID,
        priority_lane="evidence",
        byte_size=2048,
        source_object_type="evidence_artifact",
        source_object_id=ARTIFACT_ID,
        camera_id=CAMERA_ID,
        incident_id=INCIDENT_ID,
        evidence_artifact_id=ARTIFACT_ID,
    )
    return service


@pytest.fixture
def incident_id() -> UUID:
    return INCIDENT_ID


@pytest.fixture
def camera_id() -> UUID:
    return CAMERA_ID


@pytest.mark.asyncio
async def test_resolves_context_from_explicit_context_row(
    evidence_service: MaritimeEvidenceService,
    incident_id: UUID,
) -> None:
    context = await evidence_service.create_context(
        incident_id=incident_id,
        vessel_id=UUID("00000000-0000-4000-8000-000000000010"),
        voyage_id=UUID("00000000-0000-4000-8000-000000000011"),
        resolution_source="manual",
    )

    resolved = await evidence_service.resolve_context(incident_id=incident_id)

    assert resolved.vessel_id == context.vessel_id
    assert resolved.resolution_source == "manual"


@pytest.mark.asyncio
async def test_resolves_context_from_camera_site_active_voyage_and_port_call(
    evidence_service: MaritimeEvidenceService,
    camera_id: UUID,
) -> None:
    resolved = await evidence_service.resolve_context(
        camera_id=camera_id,
        incident_time=INCIDENT_TIME,
    )

    assert resolved.resolution_source == "camera_site_active_voyage"
    assert resolved.vessel_name == "MV Resolute"
    assert resolved.port_name == "Rotterdam"


@pytest.mark.asyncio
async def test_missing_telemetry_returns_partial_context_with_freshness(
    evidence_service: MaritimeEvidenceService,
    incident_id: UUID,
) -> None:
    empty_incident_id = UUID("00000000-0000-4000-8000-000000000006")
    evidence_service.register_incident(
        incident_id=empty_incident_id,
        camera_id=UUID("00000000-0000-4000-8000-000000000007"),
        incident_time=INCIDENT_TIME,
        artifact_hashes={},
    )

    resolved = await evidence_service.resolve_context(incident_id=empty_incident_id)

    assert resolved.ais_position is None
    assert resolved.telemetry_freshness == {"ais": "missing", "carrier": "missing"}
    assert resolved.partial is True


@pytest.mark.asyncio
async def test_export_adds_maritime_and_link_metadata_without_rehashing_artifacts(
    evidence_service: MaritimeEvidenceService,
    incident_id: UUID,
) -> None:
    before = await evidence_service.core_artifact_hashes(incident_id)

    export = await evidence_service.create_export(
        incident_id=incident_id,
        include_maritime_context=True,
        include_link_passport=True,
    )
    after = await evidence_service.core_artifact_hashes(incident_id)

    assert before == after
    assert export.metadata["maritime_context"]["vessel_name"] == "MV Resolute"
    assert export.metadata["link_passport_hash"].startswith("sha256:")


@pytest.mark.asyncio
async def test_export_includes_scene_runtime_link_passports_and_ledger_summary(
    evidence_service: MaritimeEvidenceService,
    incident_id: UUID,
) -> None:
    export = await evidence_service.create_export(
        incident_id=incident_id,
        include_maritime_context=True,
        include_link_passport=True,
    )

    assert set(export.metadata) >= {
        "scene_contract_hash",
        "privacy_manifest_hash",
        "runtime_passport_hash",
        "link_passport_hash",
        "ledger_summary",
        "retention_policy",
        "time_source",
    }


@pytest.mark.asyncio
async def test_db_incident_lookup_rejects_cross_tenant_camera_site() -> None:
    incident = Incident(
        id=INCIDENT_ID,
        camera_id=CAMERA_ID,
        ts=INCIDENT_TIME,
        type="cargo-intrusion",
        payload={},
        snapshot_url=None,
        clip_url=None,
        storage_bytes=0,
    )
    session_factory = _CrossTenantEvidenceSessionFactory(incident)
    service = MaritimeEvidenceService(
        maritime_service=MaritimeRuntimeService(pack_registry=PackRegistry(PACKS_ROOT)),
        link_service=LinkService(),
        tenant_id=TENANT_ID,
        session_factory=session_factory,  # type: ignore[arg-type]
    )

    with pytest.raises(MaritimeEvidenceNotFoundError):
        await service.core_artifact_hashes(INCIDENT_ID)

    assert any("sites.tenant_id" in sql for sql in session_factory.compiled_statements)


@pytest.mark.asyncio
async def test_db_camera_site_resolution_rejects_cross_tenant_camera_site() -> None:
    incident = Incident(
        id=INCIDENT_ID,
        camera_id=CAMERA_ID,
        ts=INCIDENT_TIME,
        type="cargo-intrusion",
        payload={},
        snapshot_url=None,
        clip_url=None,
        storage_bytes=0,
    )
    session_factory = _CrossTenantEvidenceSessionFactory(incident)
    service = MaritimeEvidenceService(
        maritime_service=MaritimeRuntimeService(pack_registry=PackRegistry(PACKS_ROOT)),
        link_service=LinkService(),
        tenant_id=TENANT_ID,
        session_factory=session_factory,  # type: ignore[arg-type]
    )

    context = await service.resolve_context(
        camera_id=CAMERA_ID,
        incident_time=INCIDENT_TIME,
    )

    assert context.resolution_source == "unresolved"
    assert any("sites.tenant_id" in sql for sql in session_factory.compiled_statements)


def test_maritime_evidence_tables_and_migration_are_registered() -> None:
    migration_text = (
        REPO_ROOT / "backend/src/argus/migrations/versions/0034_maritime_evidence.py"
    ).read_text(encoding="utf-8")

    assert "uq_maritime_evidence_contexts_tenant_incident" in _unique_constraint_names(
        MaritimeEvidenceContext
    )
    assert "fk_maritime_evidence_exports_incident" in _foreign_key_constraint_names(
        MaritimeEvidenceExport
    )
    assert 'revision = "0034_maritime_evidence"' in migration_text
    assert 'down_revision = "0033_maritime_telemetry"' in migration_text


@pytest.mark.asyncio
async def test_maritime_evidence_export_route(client: AsyncClient) -> None:
    response = await client.post(
        "/api/v1/maritime/evidence-exports",
        json={
            "incident_id": str(INCIDENT_ID),
            "include_maritime_context": True,
            "include_link_passport": True,
        },
    )

    assert response.status_code == 201
    payload = response.json()
    assert payload["metadata"]["maritime_context"]["vessel_name"] == "MV Resolute"
    assert payload["metadata"]["link_passport_hash"].startswith("sha256:")


class _FakeTenancyService:
    def __init__(self, user: AuthenticatedUser) -> None:
        self.context = TenantContext(
            tenant_id=TENANT_ID,
            tenant_slug="argus-dev",
            user=user,
        )

    async def resolve_context(
        self,
        *,
        user: AuthenticatedUser,
        explicit_tenant_id: UUID | None = None,
    ) -> TenantContext:
        return self.context


class _FakeSecurity:
    def __init__(self, user: AuthenticatedUser) -> None:
        self.user = user

    async def authenticate_request(self, request: object) -> AuthenticatedUser:
        return self.user


class _EvidenceResult:
    def __init__(self, rows: list[object] | None = None) -> None:
        self.rows = rows or []

    def all(self) -> list[object]:
        return self.rows

    def scalars(self) -> _EvidenceResult:
        return self

    def scalar_one_or_none(self) -> object | None:
        return self.rows[0] if self.rows else None


class _CrossTenantEvidenceSession:
    def __init__(self, factory: _CrossTenantEvidenceSessionFactory) -> None:
        self.factory = factory

    async def __aenter__(self) -> _CrossTenantEvidenceSession:
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:  # noqa: ANN001
        return None

    async def get(self, model: type[object], identifier: object) -> object | None:
        if model is Incident and identifier == self.factory.incident.id:
            return self.factory.incident
        if model is Camera and identifier == self.factory.incident.camera_id:
            return SimpleNamespace(site_id=SITE_ID)
        return None

    async def execute(self, statement: object) -> _EvidenceResult:
        sql = str(statement)
        self.factory.compiled_statements.append(sql)
        if _is_tenant_scoped_incident_lookup(sql):
            return _EvidenceResult([])
        return _EvidenceResult([])


class _CrossTenantEvidenceSessionFactory:
    def __init__(self, incident: Incident) -> None:
        self.incident = incident
        self.site_tenant_id = OTHER_TENANT_ID
        self.compiled_statements: list[str] = []

    def __call__(self) -> _CrossTenantEvidenceSession:
        return _CrossTenantEvidenceSession(self)


def _is_tenant_scoped_incident_lookup(sql: str) -> bool:
    return (
        "FROM incidents" in sql
        and "JOIN cameras" in sql
        and "JOIN sites" in sql
        and "sites.tenant_id" in sql
    )


def _user(role: RoleEnum) -> AuthenticatedUser:
    return AuthenticatedUser(
        subject=f"{role.value}-1",
        email=f"{role.value}@argus.local",
        role=role,
        issuer="http://issuer",
        realm="argus-dev",
        is_superadmin=False,
        tenant_context=str(TENANT_ID),
        claims={},
    )


@pytest_asyncio.fixture
async def client(evidence_service: MaritimeEvidenceService) -> AsyncIterator[AsyncClient]:
    app = FastAPI()
    app.include_router(router)
    app.state.services = SimpleNamespace(
        tenancy=_FakeTenancyService(_user(RoleEnum.ADMIN)),
        maritime=evidence_service.maritime_service,
        link=evidence_service.link_service,
        maritime_evidence=evidence_service,
    )
    app.state.security = _FakeSecurity(_user(RoleEnum.ADMIN))
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as http_client:
        yield http_client


def _unique_constraint_names(model: type[object]) -> set[str]:
    return {
        constraint.name
        for constraint in model.__table__.constraints
        if isinstance(constraint, UniqueConstraint)
    }


def _foreign_key_constraint_names(model: type[object]) -> set[str]:
    return {
        constraint.name
        for constraint in model.__table__.constraints
        if isinstance(constraint, ForeignKeyConstraint)
    }
