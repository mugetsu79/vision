from __future__ import annotations

from collections.abc import AsyncIterator
from datetime import UTC, datetime
from pathlib import Path
from types import SimpleNamespace
from uuid import UUID

import httpx
import pytest
import pytest_asyncio
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy import CheckConstraint, UniqueConstraint
from sqlalchemy.exc import IntegrityError

from argus.api.contracts import TenantContext
from argus.api.v1 import router
from argus.core.security import AuthenticatedUser
from argus.maritime.service import MaritimeRuntimeService
from argus.maritime.tables import (
    MaritimeAISPosition,
    MaritimeCarrierTerminal,
    MaritimeTelemetryIngestEvent,
    MaritimeVessel,
)
from argus.maritime.telemetry import (
    AisCsvFileAdapter,
    AISJsonAdapter,
    CarrierFileImportAdapter,
    CarrierHttpPollingAdapter,
    CarrierWebhookAdapter,
    Nmea0183Adapter,
    Nmea0183FileAdapter,
    select_transfer_lane,
)
from argus.models.enums import RoleEnum
from argus.services.pack_registry import PackRegistry

REPO_ROOT = Path(__file__).resolve().parents[3]
PACKS_ROOT = REPO_ROOT / "packs"
TENANT_ID = UUID("00000000-0000-4000-8000-000000000001")
SITE_ID = UUID("00000000-0000-4000-8000-000000000002")


def test_ais_json_adapter_normalizes_position() -> None:
    result = AISJsonAdapter().parse(
        {
            "mmsi": "235012345",
            "lat": 51.95,
            "lon": 4.14,
            "sog": 12.4,
            "cog": 84.2,
            "reported_at": "2026-06-05T09:15:00Z",
        }
    )

    assert result.mmsi == "235012345"
    assert result.latitude == 51.95
    assert result.longitude == 4.14
    assert result.raw_payload["sog"] == 12.4


def test_ais_json_adapter_rejects_non_finite_position() -> None:
    with pytest.raises(ValueError, match="finite"):
        AISJsonAdapter().parse(
            {
                "mmsi": "235012345",
                "lat": "NaN",
                "lon": 4.14,
                "reported_at": "2026-06-05T09:15:00Z",
            }
        )


def test_ais_csv_adapter_imports_common_export() -> None:
    csv_payload = (
        "mmsi,lat,lon,sog,cog,heading,reported_at\n"
        "235012345,51.95,4.14,12.4,84.2,90,2026-06-05T09:15:00Z\n"
    )

    result = AisCsvFileAdapter().parse(csv_payload)

    assert len(result.positions) == 1
    assert result.failures == []
    assert result.positions[0].heading == 90


def test_nmea_0183_adapter_parses_position_heading_and_speed() -> None:
    readings = Nmea0183Adapter().parse_lines(
        [
            "$GPRMC,091500,A,5157.000,N,00408.400,E,012.4,084.2,050626,,,A*68",
            "$HEHDT,090.0,T*1B",
        ]
    )

    assert readings.position.latitude_decimal == pytest.approx(51.95, rel=0.01)
    assert readings.speed_over_ground == pytest.approx(12.4)
    assert readings.heading == pytest.approx(90.0)


def test_nmea_0183_adapter_rejects_non_finite_numbers() -> None:
    with pytest.raises(ValueError, match="finite"):
        Nmea0183Adapter().parse_lines(["$HEHDT,NaN,T*00"])


def test_carrier_webhook_adapter_preserves_raw_payload() -> None:
    payload = {
        "terminal_id": "starlink-a",
        "status": "online",
        "downlink_mbps": 120,
        "vendor_extra": {"beam": "eu-west"},
    }

    result = CarrierWebhookAdapter().parse(payload)

    assert result.terminal_id == "starlink-a"
    assert result.provider == "generic"
    assert result.raw_payload["vendor_extra"]["beam"] == "eu-west"


def test_carrier_webhook_adapter_rejects_non_finite_metrics() -> None:
    with pytest.raises(ValueError, match="finite"):
        CarrierWebhookAdapter().parse(
            {
                "terminal_id": "starlink-a",
                "status": "online",
                "downlink_mbps": "NaN",
            }
        )


@pytest.mark.asyncio
async def test_carrier_http_polling_uses_secret_profile_not_plain_table_secret() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.headers["authorization"] == "Bearer redacted"
        return httpx.Response(200, json={"terminal_id": "sat-1", "status": "online"})

    adapter = CarrierHttpPollingAdapter(
        secret_profile_id="carrier-profile-1",
        endpoint_url="https://carrier.example/state",
        transport=httpx.MockTransport(handler),
    )

    assert adapter.plaintext_secret is None
    result = await adapter.poll(
        secret_resolver=lambda profile_id: {"authorization": "Bearer redacted"}
    )

    assert result.terminal_id == "sat-1"


def test_carrier_file_import_reports_parse_failures() -> None:
    result = CarrierFileImportAdapter().parse_json_lines(
        '{"terminal_id":"sat-1","status":"online"}\nnot-json\n'
    )

    assert len(result.terminals) == 1
    assert result.failures[0].line_number == 2


def test_nmea_file_import_reports_parse_failures() -> None:
    result = Nmea0183FileAdapter().parse_lines(
        [
            "$HEHDT,090.0,T*1B",
            "not-nmea",
        ]
    )

    assert len(result.readings.sentences) == 1
    assert result.failures[0].line_number == 2


def test_carrier_aware_selection_chooses_port_wifi_when_available() -> None:
    decision = select_transfer_lane(
        link_state="port_wifi",
        terminal_status="online",
        priority_lane="bulk",
        remaining_budget_bytes=100_000_000,
    )

    assert decision.transport == "port_wifi"
    assert decision.defer is False


def test_carrier_aware_selection_defers_bulk_on_degraded_satellite() -> None:
    decision = select_transfer_lane(
        link_state="satellite_degraded",
        terminal_status="degraded",
        priority_lane="bulk",
        remaining_budget_bytes=10_000,
    )

    assert decision.transport == "deferred"
    assert decision.defer is True


def test_maritime_telemetry_tables_and_migration_are_registered() -> None:
    migration_text = (
        REPO_ROOT / "backend/src/argus/migrations/versions/0033_maritime_telemetry.py"
    ).read_text(encoding="utf-8")

    assert "ck_maritime_carrier_terminals_status" in _check_constraint_names(
        MaritimeCarrierTerminal
    )
    assert "ck_maritime_ais_positions_latitude" in _check_constraint_names(
        MaritimeAISPosition
    )
    assert "uq_maritime_carrier_terminals_tenant_terminal" in _unique_constraint_names(
        MaritimeCarrierTerminal
    )
    assert 'revision = "0033_maritime_telemetry"' in migration_text
    assert 'down_revision = "0032_maritime_pack"' in migration_text


def test_carrier_terminal_updates_record_telemetry_events() -> None:
    service = MaritimeRuntimeService(pack_registry=PackRegistry(PACKS_ROOT))
    vessel = service.create_vessel(
        tenant_id=TENANT_ID,
        site_id=SITE_ID,
        name="MV Evented",
    )

    service.upsert_carrier_terminal(
        tenant_id=TENANT_ID,
        vessel_id=vessel.id,
        reading=CarrierWebhookAdapter().parse(
            {"terminal_id": "starlink-a", "status": "online"}
        ),
    )
    service.upsert_carrier_terminal(
        tenant_id=TENANT_ID,
        vessel_id=vessel.id,
        reading=CarrierWebhookAdapter().parse(
            {"terminal_id": "starlink-a", "status": "degraded"}
        ),
    )

    events = service.list_telemetry_ingest_events(
        tenant_id=TENANT_ID,
        vessel_id=vessel.id,
    )
    assert [event.event_type for event in events] == [
        "carrier_terminal_state",
        "carrier_terminal_state",
    ]
    assert events[-1].raw_payload["status"] == "degraded"


@pytest.mark.asyncio
async def test_carrier_terminal_db_conflict_applies_latest_reading() -> None:
    vessel_id = UUID("00000000-0000-4000-8000-000000000020")
    session_factory = _CarrierConflictSessionFactory(vessel_id=vessel_id)
    service = MaritimeRuntimeService(
        pack_registry=PackRegistry(PACKS_ROOT),
        session_factory=session_factory,
    )

    terminal = await service.aupsert_carrier_terminal(
        tenant_id=TENANT_ID,
        vessel_id=vessel_id,
        reading=CarrierWebhookAdapter().parse(
            {
                "terminal_id": "starlink-a",
                "status": "degraded",
                "link_state": "satellite_degraded",
            }
        ),
    )

    assert terminal.status == "degraded"
    assert session_factory.rows[MaritimeCarrierTerminal][0].status == "degraded"
    assert session_factory.rollback_count == 1
    assert session_factory.commit_count == 2


@pytest.mark.asyncio
async def test_maritime_telemetry_ingest_and_selection_routes(client: AsyncClient) -> None:
    vessel_id = await _create_vessel_for_api(client)

    ais_response = await client.post(
        "/api/v1/maritime/ingest/ais",
        json={
            "vessel_id": str(vessel_id),
            "payload": {
                "mmsi": "235012345",
                "lat": 51.95,
                "lon": 4.14,
                "sog": 12.4,
                "cog": 84.2,
                "reported_at": "2026-06-05T09:15:00Z",
            },
        },
    )
    carrier_response = await client.post(
        "/api/v1/maritime/ingest/carrier-terminal",
        json={
            "vessel_id": str(vessel_id),
            "payload": {
                "terminal_id": "starlink-a",
                "status": "online",
                "link_state": "port_wifi",
                "downlink_mbps": 120,
            },
        },
    )
    telemetry_response = await client.get(
        f"/api/v1/maritime/vessels/{vessel_id}/telemetry"
    )
    selection_response = await client.get(
        f"/api/v1/maritime/vessels/{vessel_id}/carrier-selection",
        params={"priority_lane": "bulk", "remaining_budget_bytes": 100_000_000},
    )

    assert ais_response.status_code == 201
    assert carrier_response.status_code == 201
    telemetry = telemetry_response.json()
    assert telemetry["latest_ais_position"]["mmsi"] == "235012345"
    assert telemetry["carrier_terminal"]["terminal_id"] == "starlink-a"
    assert selection_response.json()["transport"] == "port_wifi"


@pytest.mark.asyncio
async def test_nmea_file_import_route_returns_parse_failures(client: AsyncClient) -> None:
    vessel_id = await _create_vessel_for_api(client)

    response = await client.post(
        "/api/v1/maritime/import/nmea-file",
        json={
            "vessel_id": str(vessel_id),
            "content": "$HEHDT,090.0,T*1B\nnot-nmea\n",
        },
    )

    assert response.status_code == 201
    payload = response.json()
    assert len(payload["readings"]) == 1
    assert payload["failures"][0]["line_number"] == 2


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


class _FakeSiteResponse:
    id = SITE_ID

    def model_dump(self, *, mode: str = "python") -> dict[str, str]:
        return {
            "id": str(SITE_ID),
            "tenant_id": str(TENANT_ID),
            "name": "Maritime Test Site",
        }


class _FakeSiteService:
    async def get_site(
        self,
        tenant_context: TenantContext,
        site_id: UUID,
    ) -> _FakeSiteResponse:
        return _FakeSiteResponse()


class _ScalarResult:
    def __init__(self, rows: list[object]) -> None:
        self.rows = rows

    def all(self) -> list[object]:
        return self.rows


class _Result:
    def __init__(self, rows: list[object]) -> None:
        self.rows = rows

    def scalars(self) -> _ScalarResult:
        return _ScalarResult(self.rows)

    def scalar_one_or_none(self) -> object | None:
        return self.rows[0] if self.rows else None


class _CarrierConflictSession:
    def __init__(self, factory: _CarrierConflictSessionFactory) -> None:
        self.factory = factory
        self.pending: list[object] = []

    async def __aenter__(self) -> _CarrierConflictSession:
        return self

    async def __aexit__(self, exc_type: object, exc: object, tb: object) -> None:
        return None

    def add(self, row: object) -> None:
        self.pending.append(row)

    async def commit(self) -> None:
        self.factory.commit_count += 1
        if self.factory.raise_conflict_once:
            self.factory.raise_conflict_once = False
            self.pending.clear()
            self.factory.rows[MaritimeCarrierTerminal] = [self.factory.concurrent_terminal]
            raise IntegrityError("insert", {}, Exception("duplicate"))
        for row in self.pending:
            self.factory.rows.setdefault(type(row), []).append(row)
        self.pending.clear()

    async def rollback(self) -> None:
        self.factory.rollback_count += 1
        self.pending.clear()

    async def refresh(self, row: object) -> None:
        return None

    async def execute(self, statement: object) -> _Result:
        entity = statement.column_descriptions[0]["entity"]
        if entity is MaritimeCarrierTerminal:
            self.factory.carrier_lookup_count += 1
            if self.factory.carrier_lookup_count == 1:
                return _Result([])
        return _Result(list(self.factory.rows.get(entity, [])))


class _CarrierConflictSessionFactory:
    def __init__(self, *, vessel_id: UUID) -> None:
        now = datetime(2026, 6, 5, 9, 15, tzinfo=UTC)
        self.raise_conflict_once = True
        self.rollback_count = 0
        self.commit_count = 0
        self.carrier_lookup_count = 0
        self.concurrent_terminal = MaritimeCarrierTerminal(
            id=UUID("00000000-0000-4000-8000-000000000099"),
            tenant_id=TENANT_ID,
            vessel_id=vessel_id,
            terminal_id="starlink-a",
            provider="generic",
            status="online",
            link_state="satellite_good",
            last_seen_at=now,
            raw_payload={"terminal_id": "starlink-a", "status": "online"},
            created_at=now,
            updated_at=now,
        )
        self.rows: dict[type[object], list[object]] = {
            MaritimeVessel: [
                MaritimeVessel(
                    id=vessel_id,
                    tenant_id=TENANT_ID,
                    site_id=SITE_ID,
                    name="MV Conflict",
                    active=True,
                    attributes={},
                    created_at=now,
                    updated_at=now,
                )
            ],
            MaritimeCarrierTerminal: [],
            MaritimeTelemetryIngestEvent: [],
        }

    def __call__(self) -> _CarrierConflictSession:
        return _CarrierConflictSession(self)


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


def _create_app(user: AuthenticatedUser) -> FastAPI:
    app = FastAPI()
    app.include_router(router)
    app.state.services = SimpleNamespace(
        tenancy=_FakeTenancyService(user),
        packs=PackRegistry(PACKS_ROOT),
        sites=_FakeSiteService(),
        maritime=MaritimeRuntimeService(pack_registry=PackRegistry(PACKS_ROOT)),
    )
    app.state.security = _FakeSecurity(user)
    return app


@pytest_asyncio.fixture
async def client() -> AsyncIterator[AsyncClient]:
    app = _create_app(_user(RoleEnum.ADMIN))
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as http_client:
        yield http_client


async def _create_vessel_for_api(client: AsyncClient) -> UUID:
    response = await client.post(
        "/api/v1/maritime/vessels",
        json={
            "site_id": str(SITE_ID),
            "name": "MV Resolute",
            "mmsi": "235012345",
        },
    )
    assert response.status_code == 201
    return UUID(response.json()["id"])


def _check_constraint_names(model: type[object]) -> set[str]:
    return {
        constraint.name
        for constraint in model.__table__.constraints
        if isinstance(constraint, CheckConstraint)
    }


def _unique_constraint_names(model: type[object]) -> set[str]:
    return {
        constraint.name
        for constraint in model.__table__.constraints
        if isinstance(constraint, UniqueConstraint)
    }
