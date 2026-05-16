from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any, Literal
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from argus.api.contracts import (
    EdgeNodeHardwareReportCreate,
    EdgeNodeHardwareReportResponse,
    HardwarePerformanceSample,
    OperationsLifecycleRequestCreate,
    OperationsLifecycleRequestResponse,
    OperationsModeProfileConfig,
    SupervisorPollResponse,
    SupervisorRuntimeReportCreate,
    SupervisorRuntimeReportResponse,
    WorkerAssignmentCreate,
    WorkerAssignmentResponse,
    WorkerDesiredState,
    WorkerModelAdmissionRequest,
    WorkerModelAdmissionResponse,
    WorkerRuntimeStatus,
)
from argus.compat import UTC
from argus.models.enums import (
    ModelAdmissionStatus,
    OperationsLifecycleAction,
    OperationsLifecycleStatus,
    SupervisorMode,
    WorkerRuntimeState,
)
from argus.models.tables import (
    EdgeNodeHardwareReport,
    OperationsLifecycleRequest,
    WorkerAssignment,
    WorkerModelAdmissionReport,
    WorkerRuntimeReport,
)
from argus.services.model_admission import ModelAdmissionDecision

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
            await self._apply_lifecycle_desired_state(
                session=session,
                tenant_id=tenant_id,
                payload=payload,
            )
            session.add(row)
            await session.commit()
            await session.refresh(row)
        return row

    async def _apply_lifecycle_desired_state(
        self,
        *,
        session: AsyncSession,
        tenant_id: UUID,
        payload: OperationsLifecycleRequestCreate,
    ) -> None:
        desired_state = _desired_state_for_lifecycle_action(payload.action)
        if desired_state is None:
            return
        statement = (
            select(WorkerAssignment)
            .where(WorkerAssignment.tenant_id == tenant_id)
            .where(WorkerAssignment.camera_id == payload.camera_id)
            .where(WorkerAssignment.active.is_(True))
            .order_by(WorkerAssignment.created_at.desc())
        )
        if payload.assignment_id is not None:
            statement = statement.where(WorkerAssignment.id == payload.assignment_id)
        rows = list((await session.execute(statement)).scalars().all())
        assignment = next((row for row in rows if isinstance(row, WorkerAssignment)), None)
        if assignment is not None:
            assignment.desired_state = desired_state.value

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

    async def poll_lifecycle_requests(
        self,
        *,
        tenant_id: UUID,
        supervisor_id: str,
        edge_node_id: UUID | None,
        limit: int,
    ) -> list[OperationsLifecycleRequest]:
        del supervisor_id
        async with self.session_factory() as session:
            statement = (
                select(OperationsLifecycleRequest)
                .where(OperationsLifecycleRequest.tenant_id == tenant_id)
                .order_by(OperationsLifecycleRequest.requested_at.asc())
            )
            rows = list((await session.execute(statement)).scalars().all())
        rows = [row for row in rows if isinstance(row, OperationsLifecycleRequest)]
        pending = [
            row
            for row in rows
            if row.status is OperationsLifecycleStatus.REQUESTED
            and _request_matches_supervisor_scope(row, edge_node_id)
        ]
        return pending[:limit]

    async def claim_lifecycle_request(
        self,
        *,
        tenant_id: UUID,
        request_id: UUID,
        supervisor_id: str,
        edge_node_id: UUID | None,
    ) -> OperationsLifecycleRequest:
        async with self.session_factory() as session:
            row = await self._load_lifecycle_request(
                session=session,
                tenant_id=tenant_id,
                request_id=request_id,
            )
            if row.status is not OperationsLifecycleStatus.REQUESTED:
                return row
            if not _request_matches_supervisor_scope(row, edge_node_id):
                msg = "Lifecycle request is not scoped to this supervisor."
                raise ValueError(msg)
            now = datetime.now(tz=UTC)
            row.status = OperationsLifecycleStatus.ACKNOWLEDGED
            row.claimed_by_supervisor = supervisor_id
            row.claimed_at = now
            row.acknowledged_at = now
            await session.commit()
            await session.refresh(row)
            return row

    async def complete_lifecycle_request(
        self,
        *,
        tenant_id: UUID,
        request_id: UUID,
        supervisor_id: str,
        status: OperationsLifecycleStatus,
        admission_report_id: UUID | None = None,
        error: str | None = None,
    ) -> OperationsLifecycleRequest:
        async with self.session_factory() as session:
            row = await self._load_lifecycle_request(
                session=session,
                tenant_id=tenant_id,
                request_id=request_id,
            )
            if row.claimed_by_supervisor not in {None, supervisor_id}:
                msg = "Lifecycle request is claimed by another supervisor."
                raise ValueError(msg)
            row.status = status
            row.completed_at = datetime.now(tz=UTC)
            row.error = error
            row.admission_report_id = admission_report_id
            await session.commit()
            await session.refresh(row)
            return row

    async def record_hardware_report(
        self,
        *,
        tenant_id: UUID,
        supervisor_id: str,
        payload: EdgeNodeHardwareReportCreate,
    ) -> EdgeNodeHardwareReport:
        row = EdgeNodeHardwareReport(
            tenant_id=tenant_id,
            edge_node_id=payload.edge_node_id,
            supervisor_id=supervisor_id,
            reported_at=payload.reported_at,
            host_profile=payload.host_profile,
            os_name=payload.os_name,
            machine_arch=payload.machine_arch,
            cpu_model=payload.cpu_model,
            cpu_cores=payload.cpu_cores,
            memory_total_mb=payload.memory_total_mb,
            accelerators=list(payload.accelerators),
            provider_capabilities=dict(payload.provider_capabilities),
            observed_performance=[
                sample.model_dump(mode="json") for sample in payload.observed_performance
            ],
            thermal_state=payload.thermal_state,
            report_hash=_hardware_report_hash(supervisor_id, payload),
        )
        async with self.session_factory() as session:
            session.add(row)
            await session.commit()
            await session.refresh(row)
        return row

    async def latest_hardware_reports_by_edge_node(
        self,
        *,
        tenant_id: UUID,
        edge_node_ids: list[UUID],
    ) -> dict[UUID, EdgeNodeHardwareReport]:
        edge_node_set = set(edge_node_ids)
        async with self.session_factory() as session:
            statement = (
                select(EdgeNodeHardwareReport)
                .where(EdgeNodeHardwareReport.tenant_id == tenant_id)
                .order_by(EdgeNodeHardwareReport.reported_at.desc())
            )
            rows = list((await session.execute(statement)).scalars().all())
        latest: dict[UUID, EdgeNodeHardwareReport] = {}
        for row in rows:
            if not isinstance(row, EdgeNodeHardwareReport) or row.edge_node_id is None:
                continue
            if row.edge_node_id in edge_node_set and row.edge_node_id not in latest:
                latest[row.edge_node_id] = row
        return latest

    async def latest_hardware_report_for_supervisor(
        self,
        *,
        tenant_id: UUID,
        supervisor_id: str,
    ) -> EdgeNodeHardwareReport | None:
        async with self.session_factory() as session:
            statement = (
                select(EdgeNodeHardwareReport)
                .where(EdgeNodeHardwareReport.tenant_id == tenant_id)
                .order_by(EdgeNodeHardwareReport.reported_at.desc())
            )
            rows = list((await session.execute(statement)).scalars().all())
        for row in rows:
            if isinstance(row, EdgeNodeHardwareReport) and row.supervisor_id == supervisor_id:
                return row
        return None

    async def latest_hardware_report_for_central(
        self,
        *,
        tenant_id: UUID,
    ) -> EdgeNodeHardwareReport | None:
        async with self.session_factory() as session:
            statement = (
                select(EdgeNodeHardwareReport)
                .where(EdgeNodeHardwareReport.tenant_id == tenant_id)
                .order_by(EdgeNodeHardwareReport.reported_at.desc())
            )
            rows = list((await session.execute(statement)).scalars().all())
        for row in rows:
            if isinstance(row, EdgeNodeHardwareReport) and row.edge_node_id is None:
                return row
        return None

    async def record_model_admission(
        self,
        *,
        tenant_id: UUID,
        payload: WorkerModelAdmissionRequest,
        hardware_report_id: UUID | None,
        status: ModelAdmissionStatus,
        rationale: str,
        constraints: dict[str, Any] | None = None,
        recommended_model_id: UUID | None = None,
        recommended_model_name: str | None = None,
        recommended_runtime_profile_id: UUID | None = None,
        recommended_backend: str | None = None,
    ) -> WorkerModelAdmissionReport:
        row = WorkerModelAdmissionReport(
            tenant_id=tenant_id,
            camera_id=payload.camera_id,
            edge_node_id=payload.edge_node_id,
            assignment_id=payload.assignment_id,
            hardware_report_id=hardware_report_id,
            model_id=payload.model_id,
            model_name=payload.model_name,
            model_capability=payload.model_capability,
            runtime_artifact_id=payload.runtime_artifact_id,
            runtime_selection_profile_id=payload.runtime_selection_profile_id,
            stream_profile=dict(payload.stream_profile),
            status=status,
            selected_backend=payload.selected_backend,
            recommended_model_id=recommended_model_id,
            recommended_model_name=recommended_model_name,
            recommended_runtime_profile_id=recommended_runtime_profile_id,
            recommended_backend=recommended_backend,
            rationale=rationale,
            constraints=dict(constraints or {}),
            evaluated_at=datetime.now(tz=UTC),
        )
        async with self.session_factory() as session:
            session.add(row)
            await session.commit()
            await session.refresh(row)
        return row

    async def record_model_admission_decision(
        self,
        *,
        tenant_id: UUID,
        payload: WorkerModelAdmissionRequest,
        hardware_report_id: UUID | None,
        decision: ModelAdmissionDecision,
    ) -> WorkerModelAdmissionReport:
        return await self.record_model_admission(
            tenant_id=tenant_id,
            payload=payload,
            hardware_report_id=hardware_report_id,
            status=decision.status,
            rationale=decision.rationale,
            constraints=decision.constraints,
            recommended_model_id=decision.recommended_model_id,
            recommended_model_name=decision.recommended_model_name,
            recommended_runtime_profile_id=decision.recommended_runtime_profile_id,
            recommended_backend=decision.recommended_backend,
        )

    async def latest_model_admissions_by_camera(
        self,
        *,
        tenant_id: UUID,
        camera_ids: list[UUID],
    ) -> dict[UUID, WorkerModelAdmissionReport]:
        camera_id_set = set(camera_ids)
        async with self.session_factory() as session:
            statement = (
                select(WorkerModelAdmissionReport)
                .where(WorkerModelAdmissionReport.tenant_id == tenant_id)
                .order_by(WorkerModelAdmissionReport.evaluated_at.desc())
            )
            rows = list((await session.execute(statement)).scalars().all())
        latest: dict[UUID, WorkerModelAdmissionReport] = {}
        for row in rows:
            if not isinstance(row, WorkerModelAdmissionReport):
                continue
            if row.camera_id in camera_id_set and row.camera_id not in latest:
                latest[row.camera_id] = row
        return latest

    async def _load_lifecycle_request(
        self,
        *,
        session: AsyncSession,
        tenant_id: UUID,
        request_id: UUID,
    ) -> OperationsLifecycleRequest:
        statement = select(OperationsLifecycleRequest).where(
            OperationsLifecycleRequest.tenant_id == tenant_id,
            OperationsLifecycleRequest.id == request_id,
        )
        row = (await session.execute(statement)).scalar_one_or_none()
        if isinstance(row, OperationsLifecycleRequest):
            return row
        msg = "Lifecycle request not found."
        raise ValueError(msg)

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
    lifecycle_owner = profile.lifecycle_owner
    edge_assignment_overrode_central = False
    if assigned_edge_node_id is not None and lifecycle_owner == "central_supervisor":
        lifecycle_owner = "edge_supervisor"
        edge_assignment_overrode_central = True

    if lifecycle_owner == "manual":
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
            lifecycle_owner=lifecycle_owner,
            supervisor_mode=supervisor_mode,
            restart_policy=profile.restart_policy,
            allowed_actions=[],
            detail="Supervisor mode is disabled.",
        )
    if lifecycle_owner == "edge_supervisor" and assigned_edge_node_id is None:
        return WorkerOperationsControls(
            lifecycle_owner=lifecycle_owner,
            supervisor_mode=supervisor_mode,
            restart_policy=profile.restart_policy,
            allowed_actions=[],
            detail="Edge supervisor ownership requires an assigned edge node.",
        )
    if not supervisor_healthy:
        return WorkerOperationsControls(
            lifecycle_owner=lifecycle_owner,
            supervisor_mode=supervisor_mode,
            restart_policy=profile.restart_policy,
            allowed_actions=[],
            detail="Supervisor has not reported healthy runtime state.",
        )
    return WorkerOperationsControls(
        lifecycle_owner=lifecycle_owner,
        supervisor_mode=supervisor_mode,
        restart_policy=profile.restart_policy,
        allowed_actions=[
            OperationsLifecycleAction.START,
            OperationsLifecycleAction.STOP,
            OperationsLifecycleAction.RESTART,
            OperationsLifecycleAction.DRAIN,
        ],
        detail=(
            "Assigned edge node overrides central supervisor ownership; "
            "edge supervisor owns this worker process."
            if edge_assignment_overrode_central
            else f"{lifecycle_owner.replace('_', ' ').title()} owns this worker process."
        ),
    )


def worker_assignment_response(row: WorkerAssignment) -> WorkerAssignmentResponse:
    return WorkerAssignmentResponse(
        id=row.id,
        tenant_id=row.tenant_id,
        camera_id=row.camera_id,
        edge_node_id=row.edge_node_id,
        desired_state=WorkerDesiredState(row.desired_state),
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
        claimed_by_supervisor=row.claimed_by_supervisor,
        claimed_at=row.claimed_at,
        completed_at=row.completed_at,
        admission_report_id=row.admission_report_id,
        error=row.error,
        request_payload=dict(row.request_payload),
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


def edge_node_hardware_report_response(
    row: EdgeNodeHardwareReport,
) -> EdgeNodeHardwareReportResponse:
    return EdgeNodeHardwareReportResponse(
        id=row.id,
        tenant_id=row.tenant_id,
        edge_node_id=row.edge_node_id,
        supervisor_id=row.supervisor_id,
        reported_at=row.reported_at,
        host_profile=row.host_profile,
        os_name=row.os_name,
        machine_arch=row.machine_arch,
        cpu_model=row.cpu_model,
        cpu_cores=row.cpu_cores,
        memory_total_mb=row.memory_total_mb,
        accelerators=list(row.accelerators),
        provider_capabilities={
            str(key): bool(value) for key, value in dict(row.provider_capabilities).items()
        },
        observed_performance=_hardware_performance_samples(row.observed_performance),
        thermal_state=row.thermal_state,
        report_hash=row.report_hash,
        created_at=row.created_at,
    )


def _hardware_performance_samples(values: object) -> list[HardwarePerformanceSample]:
    if not isinstance(values, list):
        return []
    samples: list[HardwarePerformanceSample] = []
    for value in values:
        if isinstance(value, HardwarePerformanceSample):
            samples.append(value)
        elif isinstance(value, dict):
            samples.append(HardwarePerformanceSample.model_validate(value))
    return samples


def worker_model_admission_response(
    row: WorkerModelAdmissionReport,
) -> WorkerModelAdmissionResponse:
    return WorkerModelAdmissionResponse(
        id=row.id,
        tenant_id=row.tenant_id,
        camera_id=row.camera_id,
        edge_node_id=row.edge_node_id,
        assignment_id=row.assignment_id,
        hardware_report_id=row.hardware_report_id,
        model_id=row.model_id,
        model_name=row.model_name,
        model_capability=row.model_capability,
        runtime_artifact_id=row.runtime_artifact_id,
        runtime_selection_profile_id=row.runtime_selection_profile_id,
        stream_profile=dict(row.stream_profile),
        status=row.status,
        selected_backend=row.selected_backend,
        recommended_model_id=row.recommended_model_id,
        recommended_model_name=row.recommended_model_name,
        recommended_runtime_profile_id=row.recommended_runtime_profile_id,
        recommended_backend=row.recommended_backend,
        rationale=row.rationale,
        constraints=dict(row.constraints),
        evaluated_at=row.evaluated_at,
        created_at=row.created_at,
    )


def supervisor_poll_response(
    *,
    supervisor_id: str,
    edge_node_id: UUID | None,
    rows: list[OperationsLifecycleRequest],
) -> SupervisorPollResponse:
    return SupervisorPollResponse(
        supervisor_id=supervisor_id,
        edge_node_id=edge_node_id,
        requests=[operations_lifecycle_request_response(row) for row in rows],
    )


def _request_matches_supervisor_scope(
    row: OperationsLifecycleRequest,
    edge_node_id: UUID | None,
) -> bool:
    if edge_node_id is None:
        return row.edge_node_id is None
    return row.edge_node_id == edge_node_id


def _desired_state_for_lifecycle_action(
    action: OperationsLifecycleAction,
) -> WorkerDesiredState | None:
    if action in {OperationsLifecycleAction.STOP, OperationsLifecycleAction.DRAIN}:
        return WorkerDesiredState.NOT_DESIRED
    if action in {OperationsLifecycleAction.START, OperationsLifecycleAction.RESTART}:
        return WorkerDesiredState.SUPERVISED
    return None


def _hardware_report_hash(
    supervisor_id: str,
    payload: EdgeNodeHardwareReportCreate,
) -> str:
    material = {
        "supervisor_id": supervisor_id,
        **payload.model_dump(mode="json"),
    }
    encoded = json.dumps(material, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(encoded).hexdigest()
