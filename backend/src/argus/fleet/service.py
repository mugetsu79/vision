from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence
from datetime import datetime
from typing import cast
from uuid import UUID, uuid4

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from argus.compat import UTC
from argus.fleet.contracts import (
    EXCEPTION_ATTENTION_ORDER,
    AssignmentAssigneeType,
    FleetException,
    FleetExceptionKind,
    FleetIntegrityStatus,
    FleetLinkState,
    HeartbeatStatus,
    JsonObject,
    RotationGroup,
    RuntimeStatus,
    SiteAssignment,
    SiteGroup,
    SiteHierarchy,
    SiteHierarchyNode,
    SiteState,
)
from argus.fleet.tables import (
    FleetHierarchyNode,
    FleetRotationGroup,
    FleetSiteAssignment,
    FleetSiteGroup,
    FleetSiteState,
)

HEARTBEAT_STATUSES = {"unknown", "healthy", "stale", "offline"}
FLEET_LINK_STATES = {"unknown", "healthy", "degraded", "dark", "recovering", "port_wifi"}
RUNTIME_STATUSES = {"unknown", "running", "degraded", "stopped"}
INTEGRITY_STATUSES = {"unknown", "ok", "mismatch"}
ASSIGNEE_TYPES = {"support_queue", "user", "team", "service_account"}


class FleetService:
    def __init__(self, session_factory: async_sessionmaker[AsyncSession] | None = None) -> None:
        self.session_factory = session_factory
        self._site_groups: dict[UUID, SiteGroup] = {}
        self._hierarchy_nodes: dict[UUID, list[SiteHierarchyNode]] = {}
        self._site_states: dict[tuple[UUID, UUID], SiteState] = {}
        self._site_assignments: dict[UUID, SiteAssignment] = {}
        self._rotation_groups: dict[UUID, RotationGroup] = {}

    def create_site_group(
        self,
        *,
        tenant_id: UUID,
        label: str,
        kind: str,
        pack_id: str | None = None,
        attributes: Mapping[str, object] | None = None,
    ) -> SiteGroup:
        self._ensure_memory_mode()
        now = _now()
        group = SiteGroup(
            id=uuid4(),
            tenant_id=tenant_id,
            label=label,
            kind=kind,
            pack_id=pack_id,
            attributes=_json_object(attributes),
            created_at=now,
            updated_at=now,
        )
        self._site_groups[group.id] = group
        return group

    async def acreate_site_group(
        self,
        *,
        tenant_id: UUID,
        label: str,
        kind: str,
        pack_id: str | None = None,
        attributes: Mapping[str, object] | None = None,
    ) -> SiteGroup:
        if self.session_factory is None:
            return self.create_site_group(
                tenant_id=tenant_id,
                label=label,
                kind=kind,
                pack_id=pack_id,
                attributes=attributes,
            )
        now = _now()
        row = FleetSiteGroup(
            id=uuid4(),
            tenant_id=tenant_id,
            label=label,
            kind=kind,
            pack_id=pack_id,
            attributes=_json_object(attributes),
            created_at=now,
            updated_at=now,
        )
        async with self.session_factory() as session:
            session.add(row)
            await session.commit()
            await session.refresh(row)
        return _site_group_record(row)

    def list_site_groups(self, *, tenant_id: UUID) -> list[SiteGroup]:
        self._ensure_memory_mode()
        return sorted(
            (group for group in self._site_groups.values() if group.tenant_id == tenant_id),
            key=lambda group: (group.label, str(group.id)),
        )

    async def alist_site_groups(self, *, tenant_id: UUID) -> list[SiteGroup]:
        if self.session_factory is None:
            return self.list_site_groups(tenant_id=tenant_id)
        async with self.session_factory() as session:
            result = await session.execute(
                select(FleetSiteGroup)
                .where(FleetSiteGroup.tenant_id == tenant_id)
                .order_by(FleetSiteGroup.label)
            )
        rows = result.scalars().all()
        return [_site_group_record(row) for row in rows if row.tenant_id == tenant_id]

    def replace_hierarchy(
        self,
        *,
        tenant_id: UUID,
        nodes: Sequence[Mapping[str, object]],
    ) -> SiteHierarchy:
        self._ensure_memory_mode()
        parsed = _parse_hierarchy_nodes(tenant_id=tenant_id, nodes=nodes)
        self._hierarchy_nodes[tenant_id] = parsed
        return SiteHierarchy(tenant_id=tenant_id, nodes=list(parsed))

    async def areplace_hierarchy(
        self,
        *,
        tenant_id: UUID,
        nodes: Sequence[Mapping[str, object]],
    ) -> SiteHierarchy:
        if self.session_factory is None:
            return self.replace_hierarchy(tenant_id=tenant_id, nodes=nodes)
        parsed = _parse_hierarchy_nodes(tenant_id=tenant_id, nodes=nodes)
        now = _now()
        async with self.session_factory() as session:
            await session.execute(
                delete(FleetHierarchyNode).where(FleetHierarchyNode.tenant_id == tenant_id)
            )
            for node in parsed:
                session.add(
                    FleetHierarchyNode(
                        id=uuid4(),
                        tenant_id=tenant_id,
                        node_id=node.id,
                        parent_id=node.parent_id,
                        site_id=node.site_id,
                        label=node.label,
                        kind=node.kind,
                        sort_order=node.sort_order,
                        pack_id=node.pack_id,
                        attributes=dict(node.attributes),
                        created_at=now,
                        updated_at=now,
                    )
                )
            await session.commit()
        return SiteHierarchy(tenant_id=tenant_id, nodes=list(parsed))

    def get_hierarchy(self, *, tenant_id: UUID) -> SiteHierarchy:
        self._ensure_memory_mode()
        return SiteHierarchy(
            tenant_id=tenant_id,
            nodes=sorted(
                self._hierarchy_nodes.get(tenant_id, []),
                key=lambda node: node.sort_order,
            ),
        )

    async def aget_hierarchy(self, *, tenant_id: UUID) -> SiteHierarchy:
        if self.session_factory is None:
            return self.get_hierarchy(tenant_id=tenant_id)
        async with self.session_factory() as session:
            result = await session.execute(
                select(FleetHierarchyNode)
                .where(FleetHierarchyNode.tenant_id == tenant_id)
                .order_by(FleetHierarchyNode.sort_order)
            )
        rows = result.scalars().all()
        return SiteHierarchy(
            tenant_id=tenant_id,
            nodes=[
                _hierarchy_node_record(row)
                for row in rows
                if row.tenant_id == tenant_id
            ],
        )

    def upsert_site_state(
        self,
        *,
        tenant_id: UUID,
        site_id: UUID,
        heartbeat_status: str = "unknown",
        link_state: str = "unknown",
        runtime_status: str = "unknown",
        evidence_backlog_count: int = 0,
        active_incident_count: int = 0,
        privacy_status: str = "unknown",
        model_artifact_status: str = "unknown",
        last_heartbeat_at: datetime | None = None,
        pack_id: str | None = None,
        attributes: Mapping[str, object] | None = None,
    ) -> SiteState:
        self._ensure_memory_mode()
        existing = self._site_states.get((tenant_id, site_id))
        state = _make_site_state(
            tenant_id=tenant_id,
            site_id=site_id,
            heartbeat_status=heartbeat_status,
            link_state=link_state,
            runtime_status=runtime_status,
            evidence_backlog_count=evidence_backlog_count,
            active_incident_count=active_incident_count,
            privacy_status=privacy_status,
            model_artifact_status=model_artifact_status,
            last_heartbeat_at=last_heartbeat_at,
            pack_id=pack_id,
            attributes=attributes,
            existing=existing,
        )
        self._site_states[(tenant_id, site_id)] = state
        return state

    async def aupsert_site_state(
        self,
        *,
        tenant_id: UUID,
        site_id: UUID,
        heartbeat_status: str = "unknown",
        link_state: str = "unknown",
        runtime_status: str = "unknown",
        evidence_backlog_count: int = 0,
        active_incident_count: int = 0,
        privacy_status: str = "unknown",
        model_artifact_status: str = "unknown",
        last_heartbeat_at: datetime | None = None,
        pack_id: str | None = None,
        attributes: Mapping[str, object] | None = None,
    ) -> SiteState:
        if self.session_factory is None:
            return self.upsert_site_state(
                tenant_id=tenant_id,
                site_id=site_id,
                heartbeat_status=heartbeat_status,
                link_state=link_state,
                runtime_status=runtime_status,
                evidence_backlog_count=evidence_backlog_count,
                active_incident_count=active_incident_count,
                privacy_status=privacy_status,
                model_artifact_status=model_artifact_status,
                last_heartbeat_at=last_heartbeat_at,
                pack_id=pack_id,
                attributes=attributes,
            )
        async with self.session_factory() as session:
            row = await self._find_site_state_row(
                session,
                tenant_id=tenant_id,
                site_id=site_id,
            )
            now = _now()
            if row is None:
                row = FleetSiteState(
                    id=uuid4(),
                    tenant_id=tenant_id,
                    site_id=site_id,
                    heartbeat_status=_heartbeat_status(heartbeat_status),
                    link_state=_link_state(link_state),
                    runtime_status=_runtime_status(runtime_status),
                    evidence_backlog_count=evidence_backlog_count,
                    active_incident_count=active_incident_count,
                    privacy_status=_integrity_status(privacy_status),
                    model_artifact_status=_integrity_status(model_artifact_status),
                    last_heartbeat_at=last_heartbeat_at,
                    pack_id=pack_id,
                    attributes=_json_object(attributes),
                    created_at=now,
                    updated_at=now,
                )
                session.add(row)
            else:
                row.heartbeat_status = _heartbeat_status(heartbeat_status)
                row.link_state = _link_state(link_state)
                row.runtime_status = _runtime_status(runtime_status)
                row.evidence_backlog_count = evidence_backlog_count
                row.active_incident_count = active_incident_count
                row.privacy_status = _integrity_status(privacy_status)
                row.model_artifact_status = _integrity_status(model_artifact_status)
                row.last_heartbeat_at = last_heartbeat_at
                row.pack_id = pack_id
                row.attributes = _json_object(attributes)
                row.updated_at = now
            await session.commit()
            await session.refresh(row)
        return _site_state_record(row)

    def get_site_state(self, *, tenant_id: UUID, site_id: UUID) -> SiteState | None:
        self._ensure_memory_mode()
        return self._site_states.get((tenant_id, site_id))

    async def aget_site_state(self, *, tenant_id: UUID, site_id: UUID) -> SiteState | None:
        if self.session_factory is None:
            return self.get_site_state(tenant_id=tenant_id, site_id=site_id)
        async with self.session_factory() as session:
            row = await self._find_site_state_row(
                session,
                tenant_id=tenant_id,
                site_id=site_id,
            )
        return _site_state_record(row) if row is not None else None

    def default_site_state(self, *, tenant_id: UUID, site_id: UUID) -> SiteState:
        now = _now()
        return SiteState(
            id=uuid4(),
            tenant_id=tenant_id,
            site_id=site_id,
            heartbeat_status="unknown",
            link_state="unknown",
            runtime_status="unknown",
            evidence_backlog_count=0,
            active_incident_count=0,
            privacy_status="unknown",
            model_artifact_status="unknown",
            created_at=now,
            updated_at=now,
        )

    def create_rotation_group(
        self,
        *,
        tenant_id: UUID,
        label: str,
        member_user_ids: Sequence[str],
        pack_labels: Mapping[str, str] | None = None,
        attributes: Mapping[str, object] | None = None,
    ) -> RotationGroup:
        self._ensure_memory_mode()
        now = _now()
        rotation = RotationGroup(
            id=uuid4(),
            tenant_id=tenant_id,
            label=label,
            member_user_ids=list(member_user_ids),
            pack_labels=_string_map(pack_labels),
            attributes=_json_object(attributes),
            created_at=now,
            updated_at=now,
        )
        self._rotation_groups[rotation.id] = rotation
        return rotation

    async def acreate_rotation_group(
        self,
        *,
        tenant_id: UUID,
        label: str,
        member_user_ids: Sequence[str],
        pack_labels: Mapping[str, str] | None = None,
        attributes: Mapping[str, object] | None = None,
    ) -> RotationGroup:
        if self.session_factory is None:
            return self.create_rotation_group(
                tenant_id=tenant_id,
                label=label,
                member_user_ids=member_user_ids,
                pack_labels=pack_labels,
                attributes=attributes,
            )
        now = _now()
        row = FleetRotationGroup(
            id=uuid4(),
            tenant_id=tenant_id,
            label=label,
            member_user_ids=list(member_user_ids),
            pack_labels=_string_map(pack_labels),
            attributes=_json_object(attributes),
            created_at=now,
            updated_at=now,
        )
        async with self.session_factory() as session:
            session.add(row)
            await session.commit()
            await session.refresh(row)
        return _rotation_group_record(row)

    def list_rotation_groups(self, *, tenant_id: UUID) -> list[RotationGroup]:
        self._ensure_memory_mode()
        return sorted(
            (
                rotation
                for rotation in self._rotation_groups.values()
                if rotation.tenant_id == tenant_id
            ),
            key=lambda rotation: (rotation.label, str(rotation.id)),
        )

    async def alist_rotation_groups(self, *, tenant_id: UUID) -> list[RotationGroup]:
        if self.session_factory is None:
            return self.list_rotation_groups(tenant_id=tenant_id)
        async with self.session_factory() as session:
            result = await session.execute(
                select(FleetRotationGroup)
                .where(FleetRotationGroup.tenant_id == tenant_id)
                .order_by(FleetRotationGroup.label)
            )
        rows = result.scalars().all()
        return [_rotation_group_record(row) for row in rows if row.tenant_id == tenant_id]

    def create_site_assignment(
        self,
        *,
        tenant_id: UUID,
        site_id: UUID,
        assignee_type: str,
        assignee_id: str,
        rotation_group_id: UUID | None = None,
        pack_id: str | None = None,
        attributes: Mapping[str, object] | None = None,
    ) -> SiteAssignment:
        self._ensure_memory_mode()
        self._ensure_rotation_group(
            tenant_id=tenant_id,
            rotation_group_id=rotation_group_id,
        )
        now = _now()
        assignment = SiteAssignment(
            id=uuid4(),
            tenant_id=tenant_id,
            site_id=site_id,
            assignee_type=_assignee_type(assignee_type),
            assignee_id=assignee_id,
            rotation_group_id=rotation_group_id,
            pack_id=pack_id,
            attributes=_json_object(attributes),
            created_at=now,
            updated_at=now,
        )
        self._site_assignments[assignment.id] = assignment
        return assignment

    async def acreate_site_assignment(
        self,
        *,
        tenant_id: UUID,
        site_id: UUID,
        assignee_type: str,
        assignee_id: str,
        rotation_group_id: UUID | None = None,
        pack_id: str | None = None,
        attributes: Mapping[str, object] | None = None,
    ) -> SiteAssignment:
        if self.session_factory is None:
            return self.create_site_assignment(
                tenant_id=tenant_id,
                site_id=site_id,
                assignee_type=assignee_type,
                assignee_id=assignee_id,
                rotation_group_id=rotation_group_id,
                pack_id=pack_id,
                attributes=attributes,
            )
        async with self.session_factory() as session:
            await self._aensure_rotation_group(
                session,
                tenant_id=tenant_id,
                rotation_group_id=rotation_group_id,
            )
            now = _now()
            row = FleetSiteAssignment(
                id=uuid4(),
                tenant_id=tenant_id,
                site_id=site_id,
                assignee_type=_assignee_type(assignee_type),
                assignee_id=assignee_id,
                rotation_group_id=rotation_group_id,
                pack_id=pack_id,
                attributes=_json_object(attributes),
                created_at=now,
                updated_at=now,
            )
            session.add(row)
            await session.commit()
            await session.refresh(row)
        return _site_assignment_record(row)

    def list_site_assignments(
        self,
        *,
        tenant_id: UUID,
        site_id: UUID | None = None,
    ) -> list[SiteAssignment]:
        self._ensure_memory_mode()
        return sorted(
            (
                assignment
                for assignment in self._site_assignments.values()
                if assignment.tenant_id == tenant_id
                and (site_id is None or assignment.site_id == site_id)
            ),
            key=lambda assignment: (str(assignment.site_id), assignment.assignee_id),
        )

    async def alist_site_assignments(
        self,
        *,
        tenant_id: UUID,
        site_id: UUID | None = None,
    ) -> list[SiteAssignment]:
        if self.session_factory is None:
            return self.list_site_assignments(tenant_id=tenant_id, site_id=site_id)
        statement = select(FleetSiteAssignment).where(FleetSiteAssignment.tenant_id == tenant_id)
        if site_id is not None:
            statement = statement.where(FleetSiteAssignment.site_id == site_id)
        async with self.session_factory() as session:
            result = await session.execute(statement.order_by(FleetSiteAssignment.assignee_id))
        rows = result.scalars().all()
        return [
            _site_assignment_record(row)
            for row in rows
            if row.tenant_id == tenant_id and (site_id is None or row.site_id == site_id)
        ]

    def compute_exceptions(
        self,
        *,
        stale_heartbeat: bool,
        degraded_link: bool,
        evidence_backlog_count: int,
        stopped_worker: bool,
        privacy_mismatch: bool,
        model_artifact_mismatch: bool,
        active_incident_count: int,
        tenant_id: UUID | None = None,
        site_id: UUID | None = None,
    ) -> list[FleetException]:
        exceptions: list[FleetException] = []
        if active_incident_count > 0:
            exceptions.append(
                _exception(
                    "active_incident",
                    tenant_id=tenant_id,
                    site_id=site_id,
                    count=active_incident_count,
                )
            )
        if stopped_worker:
            exceptions.append(_exception("stopped_worker", tenant_id=tenant_id, site_id=site_id))
        if privacy_mismatch:
            exceptions.append(_exception("privacy_mismatch", tenant_id=tenant_id, site_id=site_id))
        if model_artifact_mismatch:
            exceptions.append(
                _exception("model_artifact_mismatch", tenant_id=tenant_id, site_id=site_id)
            )
        if degraded_link:
            exceptions.append(_exception("degraded_link", tenant_id=tenant_id, site_id=site_id))
        if evidence_backlog_count > 0:
            exceptions.append(
                _exception(
                    "evidence_backlog",
                    tenant_id=tenant_id,
                    site_id=site_id,
                    count=evidence_backlog_count,
                )
            )
        if stale_heartbeat:
            exceptions.append(_exception("stale_heartbeat", tenant_id=tenant_id, site_id=site_id))
        return sorted(exceptions, key=lambda item: item.attention_rank)

    def list_exceptions(self, *, tenant_id: UUID) -> list[FleetException]:
        self._ensure_memory_mode()
        return self._exceptions_from_states(
            state for state in self._site_states.values() if state.tenant_id == tenant_id
        )

    async def alist_exceptions(self, *, tenant_id: UUID) -> list[FleetException]:
        if self.session_factory is None:
            return self.list_exceptions(tenant_id=tenant_id)
        async with self.session_factory() as session:
            result = await session.execute(
                select(FleetSiteState).where(FleetSiteState.tenant_id == tenant_id)
            )
        rows = result.scalars().all()
        states = [_site_state_record(row) for row in rows if row.tenant_id == tenant_id]
        return self._exceptions_from_states(states)

    async def _find_site_state_row(
        self,
        session: AsyncSession,
        *,
        tenant_id: UUID,
        site_id: UUID,
    ) -> FleetSiteState | None:
        result = await session.execute(
            select(FleetSiteState).where(
                FleetSiteState.tenant_id == tenant_id,
                FleetSiteState.site_id == site_id,
            )
        )
        rows = result.scalars().all()
        return next(
            (row for row in rows if row.tenant_id == tenant_id and row.site_id == site_id),
            None,
        )

    def _ensure_rotation_group(
        self,
        *,
        tenant_id: UUID,
        rotation_group_id: UUID | None,
    ) -> None:
        if rotation_group_id is None:
            return
        rotation = self._rotation_groups.get(rotation_group_id)
        if rotation is None or rotation.tenant_id != tenant_id:
            raise ValueError("Rotation group not found.")

    async def _aensure_rotation_group(
        self,
        session: AsyncSession,
        *,
        tenant_id: UUID,
        rotation_group_id: UUID | None,
    ) -> None:
        if rotation_group_id is None:
            return
        rotation = await self._find_rotation_group_row(
            session,
            tenant_id=tenant_id,
            rotation_group_id=rotation_group_id,
        )
        if rotation is None:
            raise ValueError("Rotation group not found.")

    async def _find_rotation_group_row(
        self,
        session: AsyncSession,
        *,
        tenant_id: UUID,
        rotation_group_id: UUID,
    ) -> FleetRotationGroup | None:
        result = await session.execute(
            select(FleetRotationGroup).where(
                FleetRotationGroup.tenant_id == tenant_id,
                FleetRotationGroup.id == rotation_group_id,
            )
        )
        rows = result.scalars().all()
        return next(
            (row for row in rows if row.tenant_id == tenant_id and row.id == rotation_group_id),
            None,
        )

    def _exceptions_from_states(self, states: Iterable[SiteState]) -> list[FleetException]:
        exceptions: list[FleetException] = []
        for state in states:
            exceptions.extend(
                self.compute_exceptions(
                    tenant_id=state.tenant_id,
                    site_id=state.site_id,
                    stale_heartbeat=state.heartbeat_status in {"stale", "offline"},
                    degraded_link=state.link_state in {"degraded", "dark"},
                    evidence_backlog_count=state.evidence_backlog_count,
                    stopped_worker=state.runtime_status == "stopped",
                    privacy_mismatch=state.privacy_status == "mismatch",
                    model_artifact_mismatch=state.model_artifact_status == "mismatch",
                    active_incident_count=state.active_incident_count,
                )
            )
        return sorted(
            exceptions,
            key=lambda item: (item.attention_rank, str(item.site_id or ""), item.kind),
        )

    def _ensure_memory_mode(self) -> None:
        if self.session_factory is not None:
            raise RuntimeError("Use async FleetService methods when session_factory is configured.")


def _now() -> datetime:
    return datetime.now(tz=UTC)


def _make_site_state(
    *,
    tenant_id: UUID,
    site_id: UUID,
    heartbeat_status: str,
    link_state: str,
    runtime_status: str,
    evidence_backlog_count: int,
    active_incident_count: int,
    privacy_status: str,
    model_artifact_status: str,
    last_heartbeat_at: datetime | None,
    pack_id: str | None,
    attributes: Mapping[str, object] | None,
    existing: SiteState | None,
) -> SiteState:
    now = _now()
    return SiteState(
        id=existing.id if existing is not None else uuid4(),
        tenant_id=tenant_id,
        site_id=site_id,
        heartbeat_status=_heartbeat_status(heartbeat_status),
        link_state=_link_state(link_state),
        runtime_status=_runtime_status(runtime_status),
        evidence_backlog_count=evidence_backlog_count,
        active_incident_count=active_incident_count,
        privacy_status=_integrity_status(privacy_status),
        model_artifact_status=_integrity_status(model_artifact_status),
        last_heartbeat_at=last_heartbeat_at,
        pack_id=pack_id,
        attributes=_json_object(attributes),
        created_at=existing.created_at if existing is not None else now,
        updated_at=now,
    )


def _parse_hierarchy_nodes(
    *,
    tenant_id: UUID,
    nodes: Sequence[Mapping[str, object]],
) -> list[SiteHierarchyNode]:
    parsed = [
        _parse_hierarchy_node(tenant_id=tenant_id, raw=raw, sort_order=index)
        for index, raw in enumerate(nodes)
    ]
    node_ids = {node.id for node in parsed}
    missing_parent_ids = [
        node.parent_id
        for node in parsed
        if node.parent_id is not None and node.parent_id not in node_ids
    ]
    if missing_parent_ids:
        raise ValueError(f"Unknown hierarchy parent_id: {missing_parent_ids[0]}")
    return parsed


def _parse_hierarchy_node(
    *,
    tenant_id: UUID,
    raw: Mapping[str, object],
    sort_order: int,
) -> SiteHierarchyNode:
    node_id = _required_string(raw.get("id"), "id")
    return SiteHierarchyNode(
        id=node_id,
        tenant_id=tenant_id,
        parent_id=_optional_string(raw.get("parent_id"), "parent_id"),
        site_id=_optional_uuid(raw.get("site_id"), "site_id"),
        label=_optional_string(raw.get("label"), "label") or node_id,
        kind=_required_string(raw.get("kind"), "kind"),
        sort_order=sort_order,
        pack_id=_optional_string(raw.get("pack_id"), "pack_id"),
        attributes=_json_object(cast(Mapping[str, object] | None, raw.get("attributes"))),
    )


def _required_string(value: object, field_name: str) -> str:
    if not isinstance(value, str) or not value:
        raise ValueError(f"{field_name} must be a non-empty string")
    return value


def _optional_string(value: object, field_name: str) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str):
        raise ValueError(f"{field_name} must be a string when provided")
    return value


def _optional_uuid(value: object, field_name: str) -> UUID | None:
    if value is None:
        return None
    if isinstance(value, UUID):
        return value
    if isinstance(value, str):
        return UUID(value)
    raise ValueError(f"{field_name} must be a UUID when provided")


def _json_object(value: Mapping[str, object] | None) -> JsonObject:
    if value is None:
        return {}
    return {str(key): item for key, item in value.items()}


def _string_map(value: Mapping[str, str] | None) -> dict[str, str]:
    if value is None:
        return {}
    return {str(key): str(item) for key, item in value.items()}


def _heartbeat_status(value: str) -> HeartbeatStatus:
    _validate_choice(value, HEARTBEAT_STATUSES, "heartbeat_status")
    return cast(HeartbeatStatus, value)


def _link_state(value: str) -> FleetLinkState:
    _validate_choice(value, FLEET_LINK_STATES, "link_state")
    return cast(FleetLinkState, value)


def _runtime_status(value: str) -> RuntimeStatus:
    _validate_choice(value, RUNTIME_STATUSES, "runtime_status")
    return cast(RuntimeStatus, value)


def _integrity_status(value: str) -> FleetIntegrityStatus:
    _validate_choice(value, INTEGRITY_STATUSES, "integrity_status")
    return cast(FleetIntegrityStatus, value)


def _assignee_type(value: str) -> AssignmentAssigneeType:
    _validate_choice(value, ASSIGNEE_TYPES, "assignee_type")
    return cast(AssignmentAssigneeType, value)


def _validate_choice(value: str, choices: set[str], field_name: str) -> None:
    if value not in choices:
        raise ValueError(f"Invalid {field_name}: {value}")


def _exception(
    kind: FleetExceptionKind,
    *,
    tenant_id: UUID | None,
    site_id: UUID | None,
    count: int | None = None,
) -> FleetException:
    site_part = str(site_id) if site_id is not None else "global"
    tenant_part = str(tenant_id) if tenant_id is not None else "none"
    return FleetException(
        id=f"{tenant_part}:{site_part}:{kind}",
        tenant_id=tenant_id,
        site_id=site_id,
        kind=kind,
        attention_rank=EXCEPTION_ATTENTION_ORDER[kind],
        count=count,
    )


def _site_group_record(row: FleetSiteGroup) -> SiteGroup:
    return SiteGroup(
        id=row.id,
        tenant_id=row.tenant_id,
        label=row.label,
        kind=row.kind,
        pack_id=row.pack_id,
        attributes=dict(row.attributes or {}),
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


def _hierarchy_node_record(row: FleetHierarchyNode) -> SiteHierarchyNode:
    return SiteHierarchyNode(
        id=row.node_id,
        tenant_id=row.tenant_id,
        parent_id=row.parent_id,
        site_id=row.site_id,
        label=row.label,
        kind=row.kind,
        sort_order=row.sort_order,
        pack_id=row.pack_id,
        attributes=dict(row.attributes or {}),
    )


def _site_state_record(row: FleetSiteState) -> SiteState:
    return SiteState(
        id=row.id,
        tenant_id=row.tenant_id,
        site_id=row.site_id,
        heartbeat_status=_heartbeat_status(row.heartbeat_status),
        link_state=_link_state(row.link_state),
        runtime_status=_runtime_status(row.runtime_status),
        evidence_backlog_count=row.evidence_backlog_count,
        active_incident_count=row.active_incident_count,
        privacy_status=_integrity_status(row.privacy_status),
        model_artifact_status=_integrity_status(row.model_artifact_status),
        last_heartbeat_at=row.last_heartbeat_at,
        pack_id=row.pack_id,
        attributes=dict(row.attributes or {}),
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


def _site_assignment_record(row: FleetSiteAssignment) -> SiteAssignment:
    return SiteAssignment(
        id=row.id,
        tenant_id=row.tenant_id,
        site_id=row.site_id,
        assignee_type=_assignee_type(row.assignee_type),
        assignee_id=row.assignee_id,
        rotation_group_id=row.rotation_group_id,
        pack_id=row.pack_id,
        attributes=dict(row.attributes or {}),
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


def _rotation_group_record(row: FleetRotationGroup) -> RotationGroup:
    return RotationGroup(
        id=row.id,
        tenant_id=row.tenant_id,
        label=row.label,
        member_user_ids=list(row.member_user_ids or []),
        pack_labels=dict(row.pack_labels or {}),
        attributes=dict(row.attributes or {}),
        created_at=row.created_at,
        updated_at=row.updated_at,
    )
