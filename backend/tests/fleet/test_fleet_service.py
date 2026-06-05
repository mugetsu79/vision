from __future__ import annotations

from pathlib import Path
from uuid import UUID

import pytest

from argus.fleet.service import FleetService
from argus.fleet.tables import FleetRotationGroup, FleetSiteAssignment, FleetSiteState


@pytest.fixture
def fleet_service() -> FleetService:
    return FleetService()


def test_packless_site_group_hierarchy_and_assignment_flow(
    fleet_service: FleetService,
) -> None:
    tenant_id = UUID("00000000-0000-4000-8000-000000000001")
    site_id = UUID("00000000-0000-4000-8000-000000000002")

    group = fleet_service.create_site_group(
        tenant_id=tenant_id,
        label="Remote sites",
        kind="operator_group",
    )
    fleet_service.replace_hierarchy(
        tenant_id=tenant_id,
        nodes=[
            {"id": "region-eu", "parent_id": None, "label": "Europe", "kind": "region"},
            {
                "id": "site-node",
                "parent_id": "region-eu",
                "site_id": str(site_id),
                "label": "Packless Site",
                "kind": "site",
            },
        ],
    )
    assignment = fleet_service.create_site_assignment(
        tenant_id=tenant_id,
        site_id=site_id,
        assignee_type="support_queue",
        assignee_id="noc-day",
    )

    assert group.pack_id is None
    assert assignment.site_id == site_id
    assert fleet_service.get_hierarchy(tenant_id=tenant_id).nodes[1].kind == "site"


def test_fleet_exceptions_order_by_attention_without_maritime_context(
    fleet_service: FleetService,
) -> None:
    exceptions = fleet_service.compute_exceptions(
        stale_heartbeat=True,
        degraded_link=True,
        evidence_backlog_count=12,
        stopped_worker=True,
        privacy_mismatch=True,
        model_artifact_mismatch=True,
        active_incident_count=1,
    )
    assert [item.kind for item in exceptions] == [
        "active_incident",
        "stopped_worker",
        "privacy_mismatch",
        "model_artifact_mismatch",
        "degraded_link",
        "evidence_backlog",
        "stale_heartbeat",
    ]
    assert all(item.pack_id is None for item in exceptions)


def test_rotation_groups_are_generic_and_pack_label_free(
    fleet_service: FleetService,
) -> None:
    rotation = fleet_service.create_rotation_group(
        tenant_id=UUID("00000000-0000-4000-8000-000000000001"),
        label="NOC day watch",
        member_user_ids=["operator-a", "operator-b"],
    )
    assert rotation.label == "NOC day watch"
    assert rotation.pack_labels == {}


def test_site_state_records_core_runtime_link_and_evidence_fields(
    fleet_service: FleetService,
) -> None:
    state = fleet_service.upsert_site_state(
        tenant_id=UUID("00000000-0000-4000-8000-000000000001"),
        site_id=UUID("00000000-0000-4000-8000-000000000002"),
        heartbeat_status="stale",
        link_state="degraded",
        runtime_status="stopped",
        evidence_backlog_count=12,
        active_incident_count=1,
        privacy_status="mismatch",
        model_artifact_status="mismatch",
    )

    assert state.heartbeat_status == "stale"
    assert state.link_state == "degraded"
    assert state.evidence_backlog_count == 12
    assert fleet_service.get_site_state(
        tenant_id=state.tenant_id,
        site_id=state.site_id,
    ) == state


@pytest.mark.asyncio
async def test_session_backed_fleet_service_persists_site_state_and_assignments() -> None:
    tenant_id = UUID("00000000-0000-4000-8000-000000000001")
    site_id = UUID("00000000-0000-4000-8000-000000000002")
    session_factory = _PersistentFleetSessionFactory()
    service = FleetService(session_factory)

    state = await service.aupsert_site_state(
        tenant_id=tenant_id,
        site_id=site_id,
        heartbeat_status="stale",
        link_state="degraded",
        runtime_status="stopped",
        evidence_backlog_count=12,
        active_incident_count=1,
        privacy_status="mismatch",
        model_artifact_status="mismatch",
    )
    assignment = await service.acreate_site_assignment(
        tenant_id=tenant_id,
        site_id=site_id,
        assignee_type="support_queue",
        assignee_id="noc-day",
    )

    restored = FleetService(session_factory)
    restored_state = await restored.aget_site_state(tenant_id=tenant_id, site_id=site_id)
    restored_assignments = await restored.alist_site_assignments(tenant_id=tenant_id)
    exceptions = await restored.alist_exceptions(tenant_id=tenant_id)

    assert restored_state is not None
    assert restored_state.id == state.id
    assert restored_assignments[0].id == assignment.id
    assert [item.kind for item in exceptions] == [
        "active_incident",
        "stopped_worker",
        "privacy_mismatch",
        "model_artifact_mismatch",
        "degraded_link",
        "evidence_backlog",
        "stale_heartbeat",
    ]


@pytest.mark.asyncio
async def test_assignment_rejects_rotation_group_from_another_tenant() -> None:
    tenant_id = UUID("00000000-0000-4000-8000-000000000001")
    other_tenant_id = UUID("00000000-0000-4000-8000-000000000099")
    session_factory = _PersistentFleetSessionFactory()
    service = FleetService(session_factory)
    rotation = await service.acreate_rotation_group(
        tenant_id=other_tenant_id,
        label="NOC day watch",
        member_user_ids=["operator-a"],
    )

    with pytest.raises(ValueError, match="Rotation group not found"):
        await service.acreate_site_assignment(
            tenant_id=tenant_id,
            site_id=UUID("00000000-0000-4000-8000-000000000002"),
            assignee_type="support_queue",
            assignee_id="noc-day",
            rotation_group_id=rotation.id,
        )

    assert session_factory.rows[FleetSiteAssignment] == []


def test_fleet_tables_and_migration_keep_domain_neutral_constraints() -> None:
    state_constraints = _check_constraint_names(FleetSiteState)
    assignment_constraints = _check_constraint_names(FleetSiteAssignment)
    migration_path = (
        Path(__file__).resolve().parents[2]
        / "src/argus/migrations/versions/0031_core_fleet.py"
    )

    assert "ck_fleet_site_states_heartbeat_status" in state_constraints
    assert "ck_fleet_site_states_link_state" in state_constraints
    assert "ck_fleet_site_states_runtime_status" in state_constraints
    assert "ck_fleet_site_assignments_assignee_type" in assignment_constraints
    assert "uq_fleet_rotation_groups_tenant_id_id" in _unique_constraint_names(
        FleetRotationGroup
    )
    assert "fk_fleet_site_assignments_rotation_group_tenant" in {
        constraint.name for constraint in FleetSiteAssignment.__table__.foreign_key_constraints
    }
    text = migration_path.read_text(encoding="utf-8")
    rotation_group_table = _create_table_block(text, "fleet_rotation_groups")
    site_group_table = _create_table_block(text, "fleet_site_groups")
    assert "ck_fleet_site_states_heartbeat_status" in text
    assert "ck_fleet_site_assignments_assignee_type" in text
    assert "uq_fleet_rotation_groups_tenant_id_id" in rotation_group_table
    assert "uq_fleet_rotation_groups_tenant_id_id" not in site_group_table
    assert "fk_fleet_site_assignments_rotation_group_tenant" in text


class _ScalarResult:
    def __init__(self, rows: list[object]) -> None:
        self.rows = rows

    def all(self) -> list[object]:
        return self.rows

    def first(self) -> object | None:
        return self.rows[0] if self.rows else None


class _Result:
    def __init__(self, rows: list[object]) -> None:
        self.rows = rows

    def scalars(self) -> _ScalarResult:
        return _ScalarResult(self.rows)

    def scalar_one_or_none(self) -> object | None:
        return self.rows[0] if self.rows else None


class _PersistentFleetSession:
    def __init__(self, rows: dict[type[object], list[object]]) -> None:
        self.rows = rows

    async def __aenter__(self) -> _PersistentFleetSession:
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:  # noqa: ANN001
        return None

    def add(self, row: object) -> None:
        self.rows.setdefault(type(row), []).append(row)

    async def commit(self) -> None:
        return None

    async def refresh(self, row: object) -> None:
        return None

    async def execute(self, statement: object) -> _Result:
        entity = statement.column_descriptions[0]["entity"]
        rows = list(self.rows.get(entity, []))
        return _Result(rows)


class _PersistentFleetSessionFactory:
    def __init__(self) -> None:
        from argus.fleet.tables import (
            FleetHierarchyNode,
            FleetRotationGroup,
            FleetSiteAssignment,
            FleetSiteGroup,
            FleetSiteState,
        )

        self.rows: dict[type[object], list[object]] = {
            FleetSiteGroup: [],
            FleetHierarchyNode: [],
            FleetSiteState: [],
            FleetSiteAssignment: [],
            FleetRotationGroup: [],
        }

    def __call__(self) -> _PersistentFleetSession:
        return _PersistentFleetSession(self.rows)


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


def _create_table_block(text: str, table_name: str) -> str:
    start = text.index(f'"{table_name}"')
    next_table = text.find("op.create_table(", start + len(table_name))
    if next_table == -1:
        return text[start:]
    return text[start:next_table]
