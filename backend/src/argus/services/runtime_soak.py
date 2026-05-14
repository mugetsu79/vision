from __future__ import annotations

from typing import cast
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from argus.api.contracts import (
    RuntimeArtifactSoakRunCreate,
    RuntimeArtifactSoakRunResponse,
    RuntimeBackend,
)
from argus.models.enums import OperatorConfigProfileKind
from argus.models.tables import (
    EdgeNodeHardwareReport,
    ModelRuntimeArtifact,
    OperatorConfigProfile,
    RuntimeArtifactSoakRun,
    WorkerAssignment,
    WorkerModelAdmissionReport,
)

HTTP_422_UNPROCESSABLE = getattr(status, "HTTP_422_UNPROCESSABLE_CONTENT", 422)


class RuntimeSoakService:
    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self.session_factory = session_factory

    async def record_soak_run(
        self,
        *,
        tenant_id: UUID,
        payload: RuntimeArtifactSoakRunCreate,
    ) -> RuntimeArtifactSoakRunResponse:
        async with self.session_factory() as session:
            artifact = await _load_artifact(session, payload.runtime_artifact_id)
            admission = await _load_model_admission(
                session,
                tenant_id=tenant_id,
                report_id=payload.model_admission_report_id,
            )
            if admission is None:
                admission = await _latest_model_admission(
                    session,
                    tenant_id=tenant_id,
                    runtime_artifact_id=payload.runtime_artifact_id,
                    edge_node_id=payload.edge_node_id,
                )
            _validate_admission_matches_artifact(admission, artifact)

            operations_assignment_id = (
                payload.operations_assignment_id
                or (admission.assignment_id if admission is not None else None)
            )
            runtime_selection_profile_id = (
                payload.runtime_selection_profile_id
                or (admission.runtime_selection_profile_id if admission is not None else None)
            )
            hardware_report_id = (
                payload.hardware_report_id
                or (admission.hardware_report_id if admission is not None else None)
            )

            assignment = await _load_assignment(
                session,
                tenant_id=tenant_id,
                assignment_id=operations_assignment_id,
            )
            runtime_profile = await _load_runtime_profile(
                session,
                tenant_id=tenant_id,
                profile_id=runtime_selection_profile_id,
            )
            hardware_report = await _load_hardware_report(
                session,
                tenant_id=tenant_id,
                report_id=hardware_report_id,
            )

            edge_node_id = (
                payload.edge_node_id
                or (admission.edge_node_id if admission is not None else None)
                or (assignment.edge_node_id if assignment is not None else None)
                or (hardware_report.edge_node_id if hardware_report is not None else None)
            )
            _validate_edge_context(
                edge_node_id=edge_node_id,
                admission=admission,
                assignment=assignment,
                hardware_report=hardware_report,
            )

            run = RuntimeArtifactSoakRun(
                tenant_id=tenant_id,
                edge_node_id=edge_node_id,
                camera_id=artifact.camera_id
                or (admission.camera_id if admission is not None else None),
                runtime_artifact_id=artifact.id,
                runtime_kind=artifact.kind,
                runtime_backend=artifact.runtime_backend,
                model_id=admission.model_id if admission is not None else artifact.model_id,
                model_name=admission.model_name if admission is not None else None,
                model_capability=(
                    admission.model_capability if admission is not None else artifact.capability
                ),
                target_profile=artifact.target_profile,
                status=payload.status,
                started_at=payload.started_at,
                ended_at=payload.ended_at,
                metrics=dict(payload.metrics),
                fallback_reason=payload.fallback_reason,
                notes=payload.notes,
                operations_assignment_id=operations_assignment_id,
                runtime_selection_profile_id=runtime_selection_profile_id,
                runtime_selection_profile_hash=(
                    runtime_profile.config_hash if runtime_profile is not None else None
                ),
                hardware_report_id=hardware_report_id,
                model_admission_report_id=admission.id if admission is not None else None,
                hardware_admission_status=admission.status if admission is not None else None,
                model_recommendation_rationale=(
                    admission.rationale if admission is not None else None
                ),
            )
            session.add(run)
            await session.commit()
            await session.refresh(run)
        return runtime_soak_run_response(run)

    async def list_soak_runs(
        self,
        *,
        tenant_id: UUID,
        runtime_artifact_id: UUID | None = None,
        edge_node_id: UUID | None = None,
        limit: int = 50,
    ) -> list[RuntimeArtifactSoakRunResponse]:
        async with self.session_factory() as session:
            statement = (
                select(RuntimeArtifactSoakRun)
                .where(RuntimeArtifactSoakRun.tenant_id == tenant_id)
                .order_by(RuntimeArtifactSoakRun.started_at.desc())
                .limit(limit)
            )
            if runtime_artifact_id is not None:
                statement = statement.where(
                    RuntimeArtifactSoakRun.runtime_artifact_id == runtime_artifact_id
                )
            if edge_node_id is not None:
                statement = statement.where(RuntimeArtifactSoakRun.edge_node_id == edge_node_id)
            runs = (await session.execute(statement)).scalars().all()
        return [runtime_soak_run_response(run) for run in runs]


async def _load_artifact(session: AsyncSession, artifact_id: UUID) -> ModelRuntimeArtifact:
    artifact = await session.get(ModelRuntimeArtifact, artifact_id)
    if artifact is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Runtime artifact not found.",
        )
    return artifact


async def _load_model_admission(
    session: AsyncSession,
    *,
    tenant_id: UUID,
    report_id: UUID | None,
) -> WorkerModelAdmissionReport | None:
    if report_id is None:
        return None
    report = await session.get(WorkerModelAdmissionReport, report_id)
    if report is None or report.tenant_id != tenant_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Model admission report not found.",
        )
    return report


async def _latest_model_admission(
    session: AsyncSession,
    *,
    tenant_id: UUID,
    runtime_artifact_id: UUID,
    edge_node_id: UUID | None,
) -> WorkerModelAdmissionReport | None:
    statement = (
        select(WorkerModelAdmissionReport)
        .where(
            WorkerModelAdmissionReport.tenant_id == tenant_id,
            WorkerModelAdmissionReport.runtime_artifact_id == runtime_artifact_id,
        )
        .order_by(WorkerModelAdmissionReport.evaluated_at.desc())
        .limit(1)
    )
    if edge_node_id is not None:
        statement = statement.where(WorkerModelAdmissionReport.edge_node_id == edge_node_id)
    result = await session.execute(statement)
    return result.scalar_one_or_none()


async def _load_assignment(
    session: AsyncSession,
    *,
    tenant_id: UUID,
    assignment_id: UUID | None,
) -> WorkerAssignment | None:
    if assignment_id is None:
        return None
    assignment = await session.get(WorkerAssignment, assignment_id)
    if assignment is None or assignment.tenant_id != tenant_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Operations assignment not found.",
        )
    return assignment


async def _load_runtime_profile(
    session: AsyncSession,
    *,
    tenant_id: UUID,
    profile_id: UUID | None,
) -> OperatorConfigProfile | None:
    if profile_id is None:
        return None
    profile = await session.get(OperatorConfigProfile, profile_id)
    if profile is None or profile.tenant_id != tenant_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Runtime selection profile not found.",
        )
    if profile.kind is not OperatorConfigProfileKind.RUNTIME_SELECTION:
        raise HTTPException(
            status_code=HTTP_422_UNPROCESSABLE,
            detail="Profile must be a runtime_selection profile.",
        )
    return profile


async def _load_hardware_report(
    session: AsyncSession,
    *,
    tenant_id: UUID,
    report_id: UUID | None,
) -> EdgeNodeHardwareReport | None:
    if report_id is None:
        return None
    report = await session.get(EdgeNodeHardwareReport, report_id)
    if report is None or report.tenant_id != tenant_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Hardware report not found.",
        )
    return report


def _validate_admission_matches_artifact(
    admission: WorkerModelAdmissionReport | None,
    artifact: ModelRuntimeArtifact,
) -> None:
    if admission is None or admission.runtime_artifact_id is None:
        return
    if admission.runtime_artifact_id != artifact.id:
        raise HTTPException(
            status_code=HTTP_422_UNPROCESSABLE,
            detail="Model admission report does not reference the runtime artifact.",
        )


def _validate_edge_context(
    *,
    edge_node_id: UUID | None,
    admission: WorkerModelAdmissionReport | None,
    assignment: WorkerAssignment | None,
    hardware_report: EdgeNodeHardwareReport | None,
) -> None:
    related_edge_node_ids = [
        candidate
        for candidate in (
            admission.edge_node_id if admission is not None else None,
            assignment.edge_node_id if assignment is not None else None,
            hardware_report.edge_node_id if hardware_report is not None else None,
        )
        if candidate is not None
    ]
    if edge_node_id is None:
        return
    if any(candidate != edge_node_id for candidate in related_edge_node_ids):
        raise HTTPException(
            status_code=HTTP_422_UNPROCESSABLE,
            detail="Soak run edge node does not match referenced operations context.",
        )


def runtime_soak_run_response(run: RuntimeArtifactSoakRun) -> RuntimeArtifactSoakRunResponse:
    return RuntimeArtifactSoakRunResponse(
        id=run.id,
        tenant_id=run.tenant_id,
        edge_node_id=run.edge_node_id,
        camera_id=run.camera_id,
        runtime_artifact_id=run.runtime_artifact_id,
        runtime_kind=run.runtime_kind,
        runtime_backend=cast(RuntimeBackend, run.runtime_backend),
        model_id=run.model_id,
        model_name=run.model_name,
        model_capability=run.model_capability,
        target_profile=run.target_profile,
        status=run.status,
        started_at=run.started_at,
        ended_at=run.ended_at,
        metrics=dict(run.metrics),
        fallback_reason=run.fallback_reason,
        notes=run.notes,
        operations_assignment_id=run.operations_assignment_id,
        runtime_selection_profile_id=run.runtime_selection_profile_id,
        runtime_selection_profile_hash=run.runtime_selection_profile_hash,
        hardware_report_id=run.hardware_report_id,
        model_admission_report_id=run.model_admission_report_id,
        hardware_admission_status=run.hardware_admission_status,
        model_recommendation_rationale=run.model_recommendation_rationale,
        created_at=run.created_at,
    )
