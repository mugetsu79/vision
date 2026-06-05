from __future__ import annotations

import subprocess
import sys
from pathlib import Path
from uuid import UUID

import pytest

from argus.maritime.service import (
    MaritimeConflictError,
    MaritimeRuntimeService,
    MaritimeStateError,
)
from argus.maritime.tables import MaritimePortCall, MaritimeVessel, MaritimeVoyage
from argus.services.pack_registry import PackRegistry

REPO_ROOT = Path(__file__).resolve().parents[3]
PACKS_ROOT = REPO_ROOT / "packs"
TENANT_ID = UUID("00000000-0000-4000-8000-000000000001")
SITE_ID = UUID("00000000-0000-4000-8000-000000000002")


@pytest.fixture
def maritime_service() -> MaritimeRuntimeService:
    return MaritimeRuntimeService(pack_registry=PackRegistry(PACKS_ROOT))


def test_create_vessel_records_site_projection(
    maritime_service: MaritimeRuntimeService,
) -> None:
    vessel = maritime_service.create_vessel(
        tenant_id=TENANT_ID,
        site_id=SITE_ID,
        name="MV Resolute",
        mmsi="235012345",
    )

    assert vessel.name == "MV Resolute"
    assert vessel.site_id == SITE_ID
    assert vessel.active is True


def test_vessel_identifiers_are_unique_per_tenant(
    maritime_service: MaritimeRuntimeService,
) -> None:
    maritime_service.create_vessel(
        tenant_id=TENANT_ID,
        site_id=SITE_ID,
        name="MV Duplicate",
        mmsi="235012345",
    )

    with pytest.raises(MaritimeConflictError, match="mmsi"):
        maritime_service.create_vessel(
            tenant_id=TENANT_ID,
            site_id=UUID("00000000-0000-4000-8000-000000000003"),
            name="MV Duplicate 2",
            mmsi="235012345",
        )


def test_only_one_active_voyage_per_vessel(
    maritime_service: MaritimeRuntimeService,
) -> None:
    vessel = maritime_service.create_vessel(
        tenant_id=TENANT_ID,
        site_id=SITE_ID,
        name="MV Resolute",
    )
    first = maritime_service.create_voyage(
        tenant_id=TENANT_ID,
        vessel_id=vessel.id,
        name="Leg 1",
    )
    second = maritime_service.create_voyage(
        tenant_id=TENANT_ID,
        vessel_id=vessel.id,
        name="Leg 2",
    )

    maritime_service.activate_voyage(tenant_id=TENANT_ID, voyage_id=first.id)
    with pytest.raises(MaritimeConflictError, match="active voyage"):
        maritime_service.activate_voyage(tenant_id=TENANT_ID, voyage_id=second.id)


def test_voyage_completion_requires_departure(
    maritime_service: MaritimeRuntimeService,
) -> None:
    vessel = maritime_service.create_vessel(
        tenant_id=TENANT_ID,
        site_id=SITE_ID,
        name="MV Resolute",
    )
    voyage = maritime_service.create_voyage(
        tenant_id=TENANT_ID,
        vessel_id=vessel.id,
        name="Leg 1",
    )

    with pytest.raises(MaritimeStateError, match="departure"):
        maritime_service.complete_voyage(tenant_id=TENANT_ID, voyage_id=voyage.id)
    activated = maritime_service.activate_voyage(tenant_id=TENANT_ID, voyage_id=voyage.id)
    completed = maritime_service.complete_voyage(tenant_id=TENANT_ID, voyage_id=voyage.id)

    assert activated.actual_departure_at is not None
    assert completed.status == "completed"
    assert completed.actual_arrival_at is not None


def test_port_call_state_transitions_are_validated(
    maritime_service: MaritimeRuntimeService,
) -> None:
    vessel = maritime_service.create_vessel(
        tenant_id=TENANT_ID,
        site_id=SITE_ID,
        name="MV Resolute",
    )
    voyage = maritime_service.create_voyage(
        tenant_id=TENANT_ID,
        vessel_id=vessel.id,
        name="Leg 1",
    )
    port_call = maritime_service.create_port_call(
        tenant_id=TENANT_ID,
        voyage_id=voyage.id,
        port_name="Rotterdam",
        un_locode="NLRTM",
    )

    with pytest.raises(MaritimeStateError, match="arrived or alongside"):
        maritime_service.depart_port_call(tenant_id=TENANT_ID, port_call_id=port_call.id)
    arrived = maritime_service.arrive_port_call(tenant_id=TENANT_ID, port_call_id=port_call.id)
    departed = maritime_service.depart_port_call(tenant_id=TENANT_ID, port_call_id=port_call.id)

    assert arrived.status == "arrived"
    assert departed.status == "departed"


def test_tables_and_migration_constrain_maritime_entity_state() -> None:
    migration_path = (
        REPO_ROOT / "backend/src/argus/migrations/versions/0032_maritime_pack.py"
    )

    assert "ck_maritime_voyages_status" in _check_constraint_names(MaritimeVoyage)
    assert "ck_maritime_port_calls_status" in _check_constraint_names(MaritimePortCall)
    assert "uq_maritime_vessels_tenant_mmsi" in _unique_constraint_names(MaritimeVessel)
    text = migration_path.read_text(encoding="utf-8")
    assert 'revision = "0032_maritime_pack"' in text
    assert 'down_revision = "0031_core_fleet"' in text
    assert "ck_maritime_voyages_status" in text
    assert "ix_maritime_voyages_one_active_per_vessel" in text


def test_maritime_tables_are_registered_by_models_metadata_import() -> None:
    result = subprocess.run(
        [
            sys.executable,
            "-c",
            (
                "from argus.models import Base; "
                "print('maritime_vessels' in Base.metadata.tables)"
            ),
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    assert result.stdout.strip() == "True"


def _check_constraint_names(model: type[object]) -> set[str]:
    from sqlalchemy import CheckConstraint

    return {
        constraint.name
        for constraint in model.__table__.constraints
        if isinstance(constraint, CheckConstraint)
    }


def _unique_constraint_names(model: type[object]) -> set[str]:
    from sqlalchemy import UniqueConstraint

    return {
        constraint.name
        for constraint in model.__table__.constraints
        if isinstance(constraint, UniqueConstraint)
    }
