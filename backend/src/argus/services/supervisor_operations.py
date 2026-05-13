from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Literal
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from argus.api.contracts import (
    OperationsLifecycleRequestCreate,
    OperationsLifecycleRequestResponse,
    OperationsModeProfileConfig,
    SupervisorRuntimeReportCreate,
    SupervisorRuntimeReportResponse,
    WorkerAssignmentCreate,
    WorkerAssignmentResponse,
    WorkerRuntimeStatus,
)
from argus.compat import UTC
from argus.models.enums import (
    OperationsLifecycleAction,
    OperationsLifecycleStatus,
    SupervisorMode,
    WorkerRuntimeState,
)
from argus.models.tables import (
    OperationsLifecycleRequest,
    WorkerAssignment,
    WorkerRuntimeReport,
)

REPORT_STALE_AFTER = timedelta(minutes=15)


@dataclass(frozen=True, slots=True)
class WorkerOperationsControls:
    lifecycle_owner: Literal["manual", "edge_supervisor", "central_supervisor"]
    supervisor_mode: SupervisorMode
    restart_policy: Literal["never", "on_failure", "always"]
    allowed_actions: list[OperationsLifecycleAction]
    detail: str


class SupervisorOperationsService:
    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self.session_factory = session_factory

    async def list_assignments(
        self,
        *,
        tenant_id: UUID,
        active_only: bool = False,
    ) -> list[WorkerAssignment]:
        async with self.session_factory() as session:
            statement = (
                select(WorkerAssignment)
                .where(WorkerAssignment.tenant_id == tenant_id)
                .order_by(WorkerAssignment.created_at.asc())
            )
            rows = list((await session.execute(statement)).scalars().all())
        rows = [row for row in rows if isinstance(row, WorkerAssignment)]
        if active_only:
            rows = [row for row in rows if row.active]
        return rows

    async def latest_assignments_by_camera(
        self,
        *,
        tenant_id: UUID,
        camera_ids: list[UUID],
    ) -> dict[UUID, WorkerAssignment]:
        rows = await self.list_assignments(tenant_id=tenant_id, active_only=True)
        camera_id_set = set(camera_ids)
        latest: dict[UUID, WorkerAssignment] = {}
        for row in rows:
            if row.camera_id in camera_id_set:
                latest[row.camera_id] = row
        return latest

    async def create_assignment(
        self,
        *,
        tenant_id: UUID,
        payload: WorkerAssignmentCreate,
        actor_subject: str | None,
    ) -> WorkerAssignment:
        async with self.session_factory() as session:
            statement = (
                select(WorkerAssignment)
                .where(WorkerAssignment.tenant_id == tenant_id)
                .where(WorkerAssignment.camera_id == payload.camera_id)
                .order_by(WorkerAssignment.created_at.desc())
            )
            existing_rows = list((await session.execute(statement)).scalars().all())
            active_existing = next((row for row in existing_rows if row.active), None)
            if active_existing is not None:
                active_existing.active = False
            row = WorkerAssignment(
                tenant_id=tenant_id,
                camera_id=payload.camera_id,
                edge_node_id=payload.edge_node_id,
                desired_state=payload.desired_state.value,
                active=True,
                supersedes_assignment_id=(
                    active_existing.id if active_existing is not None else None
                ),
                assigned_by_subject=actor_subject,
            )
            session.add(row)
            await session.commit()
            await session.refresh(row)
        return row

    async def record_runtime_report(
        self,
        *,
        tenant_id: UUID,
        payload: SupervisorRuntimeReportCreate,
    ) -> WorkerRuntimeReport:
        row = WorkerRuntimeReport(
            tenant_id=tenant_id,
            camera_id=payload.camera_id,
            edge_node_id=payload.edge_node_id,
            assignment_id=payload.assignment_id,
            heartbeat_at=payload.heartbeat_at,
            runtime_state=payload.runtime_state,
            restart_count=payload.restart_count,
            last_error=payload.last_error,
            runtime_artifact_id=payload.runtime_artifact_id,
            scene_contract_hash=payload.scene_contract_hash,
        )
        async with self.session_factory() as session:
            session.add(row)
            await session.commit()
            await session.refresh(row)
        return row

    async def latest_runtime_reports_by_camera(
        self,
        *,
        tenant_id: UUID,
        camera_ids: list[UUID],
    ) -> dict[UUID, WorkerRuntimeReport]:
        camera_id_set = set(camera_ids)
        async with self.session_factory() as session:
            statement = (
                select(WorkerRuntimeReport)
                .where(WorkerRuntimeReport.tenant_id == tenant_id)
                .order_by(WorkerRuntimeReport.heartbeat_at.desc())
            )
            rows = list((await session.execute(statement)).scalars().all())
        rows = [row for row in rows if isinstance(row, WorkerRuntimeReport)]
        latest: dict[UUID, WorkerRuntimeReport] = {}
        for row in rows:
            if row.camera_id not in camera_id_set or row.camera_id in latest:
                continue
            latest[row.camera_id] = row
        return latest

    async def create_lifecycle_request(
        self,
        *,
        tenant_id: UUID,
        payload: OperationsLifecycleRequestCreate,
        actor_subject: str | None,
    ) -> OperationsLifecycleRequest:
        now = datetime.now(tz=UTC)
        row = OperationsLifecycleRequest(
            tenant_id=tenant_id,
            camera_id=payload.camera_id,
            edge_node_id=payload.edge_node_id,
            assignment_id=payload.assignment_id,
            action=payload.action,
            status=OperationsLifecycleStatus.REQUESTED,
            requested_by_subject=actor_subject,
            requested_at=now,
            request_payload=dict(payload.request_payload),
        )
        async with self.session_factory() as session:
            session.add(row)
            await session.commit()
            await session.refresh(row)
        return row

    async def latest_lifecycle_requests_by_camera(
        self,
        *,
        tenant_id: UUID,
        camera_ids: list[UUID],
    ) -> dict[UUID, OperationsLifecycleRequest]:
        camera_id_set = set(camera_ids)
        async with self.session_factory() as session:
            statement = (
                select(OperationsLifecycleRequest)
                .where(OperationsLifecycleRequest.tenant_id == tenant_id)
                .order_by(OperationsLifecycleRequest.requested_at.desc())
            )
            rows = list((await session.execute(statement)).scalars().all())
        rows = [row for row in rows if isinstance(row, OperationsLifecycleRequest)]
        latest: dict[UUID, OperationsLifecycleRequest] = {}
        for row in rows:
            if row.camera_id not in camera_id_set or row.camera_id in latest:
                continue
            latest[row.camera_id] = row
        return latest

    def runtime_status_for_report(
        self,
        report: WorkerRuntimeReport | object | None,
        *,
        now: datetime,
    ) -> WorkerRuntimeStatus:
        if report is None:
            return WorkerRuntimeStatus.NOT_REPORTED
        heartbeat_at = getattr(report, "heartbeat_at", None)
        if not isinstance(heartbeat_at, datetime) or now - heartbeat_at > REPORT_STALE_AFTER:
            return WorkerRuntimeStatus.UNKNOWN
        runtime_state = getattr(report, "runtime_state", WorkerRuntimeState.UNKNOWN)
        if runtime_state in {
            WorkerRuntimeState.STARTING,
            WorkerRuntimeState.RUNNING,
            WorkerRuntimeState.DRAINING,
        }:
            return WorkerRuntimeStatus.RUNNING
        if runtime_state in {WorkerRuntimeState.STOPPED, WorkerRuntimeState.ERROR}:
            return WorkerRuntimeStatus.OFFLINE
        return WorkerRuntimeStatus.UNKNOWN


def resolve_worker_operations_controls(
    config: dict[str, object] | OperationsModeProfileConfig,
    *,
    assigned_edge_node_id: UUID | None,
    supervisor_healthy: bool,
) -> WorkerOperationsControls:
    profile = (
        config
        if isinstance(config, OperationsModeProfileConfig)
        else OperationsModeProfileConfig.model_validate(config)
    )
    if profile.lifecycle_owner == "manual":
        return WorkerOperationsControls(
            lifecycle_owner="manual",
            supervisor_mode=SupervisorMode(profile.supervisor_mode),
            restart_policy=profile.restart_policy,
            allowed_actions=[],
            detail="Manual mode requires operator-started worker processes.",
        )
    supervisor_mode = SupervisorMode(profile.supervisor_mode)
    if supervisor_mode is SupervisorMode.DISABLED:
        return WorkerOperationsControls(
            lifecycle_owner=profile.lifecycle_owner,
            supervisor_mode=supervisor_mode,
            restart_policy=profile.restart_policy,
            allowed_actions=[],
            detail="Supervisor mode is disabled.",
        )
    if profile.lifecycle_owner == "edge_supervisor" and assigned_edge_node_id is None:
        return WorkerOperationsControls(
            lifecycle_owner=profile.lifecycle_owner,
            supervisor_mode=supervisor_mode,
            restart_policy=profile.restart_policy,
            allowed_actions=[],
            detail="Edge supervisor ownership requires an assigned edge node.",
        )
    if not supervisor_healthy:
        return WorkerOperationsControls(
            lifecycle_owner=profile.lifecycle_owner,
            supervisor_mode=supervisor_mode,
            restart_policy=profile.restart_policy,
            allowed_actions=[],
            detail="Supervisor has not reported healthy runtime state.",
        )
    return WorkerOperationsControls(
        lifecycle_owner=profile.lifecycle_owner,
        supervisor_mode=supervisor_mode,
        restart_policy=profile.restart_policy,
        allowed_actions=[
            OperationsLifecycleAction.START,
            OperationsLifecycleAction.STOP,
            OperationsLifecycleAction.RESTART,
            OperationsLifecycleAction.DRAIN,
        ],
        detail=f"{profile.lifecycle_owner.replace('_', ' ').title()} owns this worker process.",
    )


def worker_assignment_response(row: WorkerAssignment) -> WorkerAssignmentResponse:
    return WorkerAssignmentResponse(
        id=row.id,
        tenant_id=row.tenant_id,
        camera_id=row.camera_id,
        edge_node_id=row.edge_node_id,
        desired_state=row.desired_state,
        active=row.active,
        supersedes_assignment_id=row.supersedes_assignment_id,
        assigned_by_subject=row.assigned_by_subject,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


def supervisor_runtime_report_response(
    row: WorkerRuntimeReport,
) -> SupervisorRuntimeReportResponse:
    return SupervisorRuntimeReportResponse(
        id=row.id,
        tenant_id=row.tenant_id,
        camera_id=row.camera_id,
        edge_node_id=row.edge_node_id,
        assignment_id=row.assignment_id,
        heartbeat_at=row.heartbeat_at,
        runtime_state=row.runtime_state,
        restart_count=row.restart_count,
        last_error=row.last_error,
        runtime_artifact_id=row.runtime_artifact_id,
        scene_contract_hash=row.scene_contract_hash,
        created_at=row.created_at,
    )


def operations_lifecycle_request_response(
    row: OperationsLifecycleRequest,
) -> OperationsLifecycleRequestResponse:
    return OperationsLifecycleRequestResponse(
        id=row.id,
        tenant_id=row.tenant_id,
        camera_id=row.camera_id,
        edge_node_id=row.edge_node_id,
        assignment_id=row.assignment_id,
        action=row.action,
        status=row.status,
        requested_by_subject=row.requested_by_subject,
        requested_at=row.requested_at,
        acknowledged_at=row.acknowledged_at,
        completed_at=row.completed_at,
        error=row.error,
        request_payload=dict(row.request_payload),
        created_at=row.created_at,
        updated_at=row.updated_at,
    )
