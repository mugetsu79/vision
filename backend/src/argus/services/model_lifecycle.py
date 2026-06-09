from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from urllib.parse import unquote, urlsplit
from uuid import UUID, uuid4

import anyio
from fastapi import HTTPException
from pydantic import ValidationError
from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from argus.api.contracts import (
    DeploymentModelAssignmentCreate,
    DeploymentModelAssignmentResponse,
    DeploymentModelInventoryItem,
    DeploymentModelInventoryReport,
    DeploymentModelSyncJobResponse,
    EdgeConfigurationResponse,
    EdgeConfigurationUpdate,
    ModelCapabilityConfig,
    ModelImportJobResponse,
    ModelImportRequest,
    RuntimeArtifactBuildJobCreate,
    RuntimeArtifactBuildJobResponse,
    RuntimeArtifactCreate,
    SupervisorModelJobComplete,
    SupervisorModelJobEventCreate,
)
from argus.compat import UTC
from argus.models.enums import (
    DeploymentModelAssignmentStatus,
    DeploymentNodeKind,
    DetectorCapability,
    EdgeConfigurationApplyStatus,
    ModelFormat,
    ModelImportSource,
    ModelLifecycleJobStatus,
    ModelTask,
    RuntimeArtifactBuildFormat,
    RuntimeArtifactScope,
    RuntimeArtifactValidationStatus,
)
from argus.models.tables import (
    Camera,
    DeploymentModelAssignment,
    DeploymentModelInventory,
    DeploymentModelSyncJob,
    DeploymentNode,
    EdgeConfigurationAssignment,
    EdgeNodeHardwareReport,
    Model,
    ModelImportJob,
    RuntimeArtifactBuildJob,
    SupervisorModelJobEvent,
)
from argus.services.model_catalog import (
    ModelCatalogEntry,
    get_model_catalog_entry,
    resolve_catalog_artifact_path,
)
from argus.services.runtime_artifacts import create_runtime_artifacts_for_model_in_session
from argus.vision.vocabulary import hash_vocabulary, normalize_vocabulary_terms

_TERMINAL_MODEL_LIFECYCLE_JOB_STATUSES = {
    ModelLifecycleJobStatus.SUCCEEDED,
    ModelLifecycleJobStatus.FAILED,
    ModelLifecycleJobStatus.CANCELLED,
}

EDGE_CONFIGURATION_ALLOWED_KEYS = {
    "model_store_path",
    "artifact_store_path",
    "model_store_max_bytes",
    "artifact_store_max_bytes",
    "worker_concurrency",
    "runtime_preference",
    "fallback_policy",
    "service_report_interval_seconds",
    "hardware_report_interval_seconds",
    "stream_delivery_profile",
    "webrtc_additional_hosts",
    "webrtc_allowed_origins",
    "operations_mode",
    "support_bundle_policy",
    "evidence_retention_profile",
    "privacy_profile",
}


@dataclass(frozen=True, slots=True)
class ModelAssetDownload:
    path: Path
    filename: str
    sha256: str
    size_bytes: int


class ModelLifecycleService:
    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession],
        model_store_path: Path | None = None,
    ) -> None:
        self.session_factory = session_factory
        self.model_store_path = model_store_path

    async def get_edge_configuration(
        self,
        *,
        tenant_id: UUID,
        deployment_node_id: UUID,
    ) -> EdgeConfigurationResponse:
        async with self.session_factory() as session:
            await _load_deployment_node(
                session=session,
                tenant_id=tenant_id,
                deployment_node_id=deployment_node_id,
            )
            assignment = await _load_edge_configuration_assignment(
                session=session,
                tenant_id=tenant_id,
                deployment_node_id=deployment_node_id,
            )
            if assignment is None:
                raise ValueError("Edge configuration assignment not found.")
        return _edge_configuration_to_response(assignment)

    async def update_edge_configuration(
        self,
        *,
        tenant_id: UUID,
        deployment_node_id: UUID,
        payload: EdgeConfigurationUpdate,
        actor_subject: str,
    ) -> EdgeConfigurationResponse:
        desired_config = _validated_edge_configuration(payload.desired_config)
        async with self.session_factory() as session:
            node = await _load_deployment_node(
                session=session,
                tenant_id=tenant_id,
                deployment_node_id=deployment_node_id,
            )
            _require_assignable_deployment_node(node)
            assignment = await _load_edge_configuration_assignment(
                session=session,
                tenant_id=tenant_id,
                deployment_node_id=deployment_node_id,
                for_update=True,
            )
            if assignment is None:
                assignment = EdgeConfigurationAssignment(
                    tenant_id=tenant_id,
                    deployment_node_id=deployment_node_id,
                    revision=1,
                    desired_config=desired_config,
                    apply_status=EdgeConfigurationApplyStatus.PENDING,
                    actor_subject=actor_subject,
                    error=None,
                )
                session.add(assignment)
            else:
                assignment.revision += 1
                assignment.desired_config = desired_config
                assignment.apply_status = EdgeConfigurationApplyStatus.PENDING
                assignment.actor_subject = actor_subject
                assignment.error = None
            try:
                await session.commit()
            except IntegrityError:
                await session.rollback()
                assignment = await _load_edge_configuration_assignment(
                    session=session,
                    tenant_id=tenant_id,
                    deployment_node_id=deployment_node_id,
                    for_update=True,
                )
                if assignment is None:
                    raise
                assignment.revision += 1
                assignment.desired_config = desired_config
                assignment.apply_status = EdgeConfigurationApplyStatus.PENDING
                assignment.actor_subject = actor_subject
                assignment.error = None
                await session.commit()
            await session.refresh(assignment)
        return _edge_configuration_to_response(assignment)

    async def get_supervisor_edge_configuration(
        self,
        *,
        tenant_id: UUID,
        supervisor_id: str,
        authenticated_node_id: UUID | None,
    ) -> EdgeConfigurationResponse:
        async with self.session_factory() as session:
            node = await _load_supervisor_edge_configuration_node(
                session=session,
                tenant_id=tenant_id,
                supervisor_id=supervisor_id,
                authenticated_node_id=authenticated_node_id,
            )
            assignment = await _load_edge_configuration_assignment(
                session=session,
                tenant_id=tenant_id,
                deployment_node_id=node.id,
            )
            if assignment is None:
                raise ValueError("Edge configuration assignment not found.")
        return _edge_configuration_to_response(assignment)

    async def record_edge_configuration_apply_report(
        self,
        *,
        tenant_id: UUID,
        supervisor_id: str,
        authenticated_node_id: UUID | None,
        revision: int,
        status: EdgeConfigurationApplyStatus,
        error: str | None,
    ) -> EdgeConfigurationResponse:
        apply_status = _edge_configuration_apply_status(status)
        if apply_status is EdgeConfigurationApplyStatus.PENDING:
            raise ValueError("Edge configuration apply report status must be applied or failed.")
        async with self.session_factory() as session:
            node = await _load_supervisor_edge_configuration_node(
                session=session,
                tenant_id=tenant_id,
                supervisor_id=supervisor_id,
                authenticated_node_id=authenticated_node_id,
            )
            assignment = await _load_edge_configuration_assignment(
                session=session,
                tenant_id=tenant_id,
                deployment_node_id=node.id,
                for_update=True,
            )
            if assignment is None:
                raise ValueError("Edge configuration assignment not found.")
            if assignment.revision != revision:
                raise ValueError(
                    "Edge configuration apply report revision does not match current revision."
                )
            if apply_status is EdgeConfigurationApplyStatus.APPLIED:
                assignment.applied_revision = revision
                assignment.apply_status = EdgeConfigurationApplyStatus.APPLIED
                assignment.last_applied_at = datetime.now(tz=UTC)
                assignment.error = None
            else:
                assignment.apply_status = EdgeConfigurationApplyStatus.FAILED
                assignment.error = error or "Edge configuration apply failed."
            await session.commit()
            await session.refresh(assignment)
        return _edge_configuration_to_response(assignment)

    async def import_model_from_request(
        self,
        *,
        tenant_id: UUID,
        actor_subject: str,
        payload: ModelImportRequest,
    ) -> ModelImportJobResponse:
        if payload.source is ModelImportSource.URL:
            return await self._queue_url_import(
                tenant_id=tenant_id,
                actor_subject=actor_subject,
                payload=payload,
                catalog_id=None,
            )
        if payload.source is ModelImportSource.MASTER_PATH:
            return await self._register_file_import(
                tenant_id=tenant_id,
                actor_subject=actor_subject,
                source=payload.source,
                source_uri=payload.source_uri or "",
                target_path=payload.source_uri or "",
                expected_sha256=payload.expected_sha256,
                name=payload.name,
                version=payload.version,
                task=payload.task,
                format=payload.format,
                capability=payload.capability,
                capability_config=payload.capability_config,
                input_shape=payload.input_shape,
                classes=payload.classes,
                license=payload.license,
                catalog_id=None,
            )
        return await self._failed_import_job(
            tenant_id=tenant_id,
            actor_subject=actor_subject,
            source=payload.source,
            source_uri=payload.source_uri,
            target_path=payload.source_uri or "",
            expected_sha256=payload.expected_sha256,
            error=f"Model import source {payload.source.value!r} is not supported yet.",
            catalog_id=None,
        )

    async def register_catalog_entry(
        self,
        *,
        tenant_id: UUID,
        actor_subject: str,
        catalog_id: str,
    ) -> ModelImportJobResponse:
        entry = _find_catalog_entry(catalog_id)
        artifact_path = str(resolve_catalog_artifact_path(entry.path_hint))
        declared_classes: list[str] | None
        if entry.capability is DetectorCapability.FIXED_VOCAB and not entry.classes:
            declared_classes = None
        else:
            declared_classes = list(entry.classes)
        capability_config = entry.capability_config.model_copy()
        return await self._register_file_import(
            tenant_id=tenant_id,
            actor_subject=actor_subject,
            source=ModelImportSource.CATALOG,
            source_uri=artifact_path,
            target_path=artifact_path,
            expected_sha256=None,
            name=entry.name,
            version=entry.version,
            task=entry.task,
            format=entry.format,
            capability=entry.capability,
            capability_config=capability_config,
            input_shape=entry.input_shape,
            classes=declared_classes,
            license=entry.license,
            catalog_id=entry.id,
        )

    async def queue_catalog_download(
        self,
        *,
        tenant_id: UUID,
        actor_subject: str,
        catalog_id: str,
    ) -> ModelImportJobResponse:
        entry = _find_catalog_entry(catalog_id)
        source_url = entry.capability_config.source_url
        expected_sha256 = entry.capability_config.source_sha256
        if source_url is None or expected_sha256 is None:
            raise ValueError(
                "Model artifact is expected to be bundled or mounted at "
                f"{entry.path_hint}; no trusted download source is configured."
            )
        payload = ModelImportRequest(
            source=ModelImportSource.URL,
            source_uri=source_url,
            expected_sha256=expected_sha256,
            name=entry.name,
            version=entry.version,
            task=entry.task,
            format=entry.format,
            capability=entry.capability,
            capability_config=entry.capability_config,
            input_shape=entry.input_shape,
            classes=list(entry.classes),
            license=entry.license,
        )
        return await self._queue_url_import(
            tenant_id=tenant_id,
            actor_subject=actor_subject,
            payload=payload,
            catalog_id=entry.id,
        )

    async def list_import_jobs(self, tenant_id: UUID) -> list[ModelImportJobResponse]:
        async with self.session_factory() as session:
            statement = (
                select(ModelImportJob)
                .where(ModelImportJob.tenant_id == tenant_id)
                .order_by(ModelImportJob.created_at.desc())
            )
            jobs = (await session.execute(statement)).scalars().all()
        return [_model_to_import_job_response(job) for job in jobs]

    async def get_model_asset_download(
        self,
        *,
        tenant_id: UUID,
        asset_id: UUID,
        authenticated_node_id: UUID | None,
    ) -> ModelAssetDownload:
        async with self.session_factory() as session:
            model = await session.get(Model, asset_id)
            if not isinstance(model, Model):
                raise ValueError("Model asset not found.")
            if authenticated_node_id is not None:
                await _load_deployment_node(
                    session=session,
                    tenant_id=tenant_id,
                    deployment_node_id=authenticated_node_id,
                )
                assignment = await _load_model_assignment(
                    session=session,
                    tenant_id=tenant_id,
                    deployment_node_id=authenticated_node_id,
                    model_id=asset_id,
                )
                assignment_removed = (
                    assignment is None
                    or assignment.status is DeploymentModelAssignmentStatus.REMOVED
                )
                if assignment_removed:
                    raise PermissionError(
                        "Model asset is not assigned to this deployment node."
                    )
            path = Path(model.path)
            if not await anyio.to_thread.run_sync(path.is_file):
                raise ValueError("Model asset file not found.")
            return ModelAssetDownload(
                path=path,
                filename=path.name,
                sha256=model.sha256,
                size_bytes=model.size_bytes,
            )

    async def list_model_assignments(
        self,
        *,
        tenant_id: UUID,
        deployment_node_id: UUID,
    ) -> list[DeploymentModelAssignmentResponse]:
        async with self.session_factory() as session:
            await _load_deployment_node(
                session=session,
                tenant_id=tenant_id,
                deployment_node_id=deployment_node_id,
            )
            statement = (
                select(DeploymentModelAssignment)
                .where(DeploymentModelAssignment.tenant_id == tenant_id)
                .where(DeploymentModelAssignment.deployment_node_id == deployment_node_id)
                .order_by(DeploymentModelAssignment.created_at.asc())
            )
            assignments = (await session.execute(statement)).scalars().all()
        return [
            _model_to_assignment_response(assignment)
            for assignment in assignments
            if isinstance(assignment, DeploymentModelAssignment)
        ]

    async def assign_model_to_node(
        self,
        *,
        tenant_id: UUID,
        deployment_node_id: UUID,
        payload: DeploymentModelAssignmentCreate,
        actor_subject: str,
    ) -> DeploymentModelAssignmentResponse:
        async with self.session_factory() as session:
            node = await _load_deployment_node(
                session=session,
                tenant_id=tenant_id,
                deployment_node_id=deployment_node_id,
            )
            _require_assignable_deployment_node(node)
            model = await session.get(Model, payload.model_id)
            if not isinstance(model, Model):
                raise ValueError("Model not found.")

            existing = await _load_model_assignment(
                session=session,
                tenant_id=tenant_id,
                deployment_node_id=deployment_node_id,
                model_id=payload.model_id,
            )
            if existing is not None:
                if existing.status is DeploymentModelAssignmentStatus.REMOVED:
                    existing.status = DeploymentModelAssignmentStatus.DESIRED
                    existing.desired_path = payload.desired_path
                    existing.actor_subject = actor_subject
                    existing.error = None
                    await session.commit()
                    await session.refresh(existing)
                return _model_to_assignment_response(existing)

            assignment = DeploymentModelAssignment(
                tenant_id=tenant_id,
                deployment_node_id=deployment_node_id,
                model_id=payload.model_id,
                status=DeploymentModelAssignmentStatus.DESIRED,
                desired_path=payload.desired_path,
                actor_subject=actor_subject,
                error=None,
            )
            session.add(assignment)
            try:
                await session.commit()
            except IntegrityError:
                await session.rollback()
                existing = await _load_model_assignment(
                    session=session,
                    tenant_id=tenant_id,
                    deployment_node_id=deployment_node_id,
                    model_id=payload.model_id,
                )
                if existing is None:
                    raise
                return _model_to_assignment_response(existing)
            await session.refresh(assignment)
        return _model_to_assignment_response(assignment)

    async def remove_model_assignment(
        self,
        *,
        tenant_id: UUID,
        deployment_node_id: UUID,
        assignment_id: UUID,
        actor_subject: str,
    ) -> DeploymentModelAssignmentResponse:
        async with self.session_factory() as session:
            await _load_deployment_node(
                session=session,
                tenant_id=tenant_id,
                deployment_node_id=deployment_node_id,
            )
            assignment = await _load_assignment_by_id(
                session=session,
                tenant_id=tenant_id,
                deployment_node_id=deployment_node_id,
                assignment_id=assignment_id,
            )
            if assignment is None:
                raise ValueError("Deployment model assignment not found.")
            assignment.status = DeploymentModelAssignmentStatus.REMOVED
            assignment.actor_subject = actor_subject
            assignment.error = None
            await session.commit()
            await session.refresh(assignment)
        return _model_to_assignment_response(assignment)

    async def list_model_inventory(
        self,
        *,
        tenant_id: UUID,
        deployment_node_id: UUID,
    ) -> DeploymentModelInventoryReport:
        async with self.session_factory() as session:
            await _load_deployment_node(
                session=session,
                tenant_id=tenant_id,
                deployment_node_id=deployment_node_id,
            )
            inventory_rows = await _load_inventory_rows(
                session=session,
                tenant_id=tenant_id,
                deployment_node_id=deployment_node_id,
            )
        return DeploymentModelInventoryReport(
            items=[
                _model_to_inventory_item(row)
                for row in inventory_rows
                if isinstance(row, DeploymentModelInventory)
            ]
        )

    async def record_model_inventory(
        self,
        *,
        tenant_id: UUID,
        supervisor_id: str,
        authenticated_node_id: UUID | None,
        payload: DeploymentModelInventoryReport,
    ) -> DeploymentModelInventoryReport:
        async with self.session_factory() as session:
            node = await _load_deployment_node_by_supervisor(
                session=session,
                tenant_id=tenant_id,
                supervisor_id=supervisor_id,
            )
            if node is None:
                raise ValueError("Deployment node not found.")
            if authenticated_node_id is not None and authenticated_node_id != node.id:
                raise PermissionError(
                    "Supervisor credential cannot report inventory for another deployment node."
                )

            inventory_rows: list[DeploymentModelInventory] = []
            for item in payload.items:
                inventory_rows.append(
                    await _upsert_inventory_item(
                        session=session,
                        tenant_id=tenant_id,
                        deployment_node_id=node.id,
                        item=item,
                    )
                )

            await _mark_synced_assignments(
                session=session,
                tenant_id=tenant_id,
                deployment_node_id=node.id,
                items=payload.items,
            )
            await session.commit()
            for row in inventory_rows:
                await session.refresh(row)
        return DeploymentModelInventoryReport(
            items=[_model_to_inventory_item(row) for row in inventory_rows]
        )

    async def create_model_sync_job(
        self,
        *,
        tenant_id: UUID,
        deployment_node_id: UUID,
        actor_subject: str,
    ) -> DeploymentModelSyncJobResponse:
        async with self.session_factory() as session:
            node = await _load_deployment_node(
                session=session,
                tenant_id=tenant_id,
                deployment_node_id=deployment_node_id,
            )
            _require_assignable_deployment_node(node)
            assignment = await _load_next_desired_model_assignment(
                session=session,
                tenant_id=tenant_id,
                deployment_node_id=deployment_node_id,
            )
            if assignment is None:
                raise ValueError("Active deployment model assignment not found.")

            model = await session.get(Model, assignment.model_id)
            if not isinstance(model, Model):
                raise ValueError("Model not found.")
            edge_configuration = await _load_edge_configuration_assignment(
                session=session,
                tenant_id=tenant_id,
                deployment_node_id=deployment_node_id,
            )

            job = DeploymentModelSyncJob(
                id=uuid4(),
                tenant_id=tenant_id,
                deployment_node_id=deployment_node_id,
                assignment_id=assignment.id,
                model_id=model.id,
                status=ModelLifecycleJobStatus.QUEUED,
                payload=_model_sync_job_payload(
                    deployment_node_id=deployment_node_id,
                    assignment=assignment,
                    model=model,
                    edge_configuration=edge_configuration,
                ),
                actor_subject=actor_subject,
                error=None,
            )
            session.add(job)
            await session.flush()
            assignment.status = DeploymentModelAssignmentStatus.SYNCING
            assignment.last_sync_job_id = job.id
            assignment.error = None
            await session.commit()
            await session.refresh(job)
            await session.refresh(assignment)
        return _model_to_sync_job_response(job)

    async def create_runtime_artifact_build_job(
        self,
        tenant_id: UUID,
        model_id: UUID,
        payload: RuntimeArtifactBuildJobCreate,
        actor_subject: str,
    ) -> RuntimeArtifactBuildJobResponse:
        async with self.session_factory() as session:
            node = await _load_deployment_node(
                session=session,
                tenant_id=tenant_id,
                deployment_node_id=payload.deployment_node_id,
            )
            _require_assignable_deployment_node(node)
            await _require_target_profile_supported(
                session=session,
                tenant_id=tenant_id,
                node=node,
                target_profile=payload.target_profile,
            )
            model = await session.get(Model, model_id)
            if not isinstance(model, Model):
                raise ValueError("Model not found.")

            camera: Camera | None = None
            runtime_vocabulary: list[str] = []
            vocabulary_hash: str | None = None
            vocabulary_version: int | None = None
            if _model_capability(model) is DetectorCapability.OPEN_VOCAB:
                if payload.camera_id is None:
                    raise ValueError("camera_id is required for open-vocab artifact builds.")
                camera = await session.get(Camera, payload.camera_id)
                if not isinstance(camera, Camera):
                    raise ValueError("Camera not found.")
                if camera.primary_model_id != model_id and camera.secondary_model_id != model_id:
                    raise ValueError("Camera does not use model.")
                runtime_vocabulary = normalize_vocabulary_terms(camera.runtime_vocabulary)
                if not runtime_vocabulary:
                    raise ValueError("Open-vocab artifact builds require camera vocabulary.")
                vocabulary_hash = hash_vocabulary(runtime_vocabulary)
                vocabulary_version = camera.runtime_vocabulary_version
            else:
                if payload.build_format is not RuntimeArtifactBuildFormat.TENSORRT_ENGINE:
                    raise ValueError("Fixed-vocab artifact builds require TensorRT engine format.")
                assignment = await _load_model_assignment(
                    session=session,
                    tenant_id=tenant_id,
                    deployment_node_id=payload.deployment_node_id,
                    model_id=model_id,
                )
                if (
                    assignment is None
                    or assignment.status is DeploymentModelAssignmentStatus.REMOVED
                ):
                    raise ValueError("Fixed-vocab TensorRT jobs require a model assignment.")

            export_formats = [
                export_format.value for export_format in (payload.export_formats or [])
            ]
            if not export_formats:
                export_formats = [payload.build_format.value]
            edge_configuration = await _load_edge_configuration_assignment(
                session=session,
                tenant_id=tenant_id,
                deployment_node_id=payload.deployment_node_id,
            )
            output_dir = _artifact_output_dir(
                model=model,
                payload=payload,
                edge_configuration=edge_configuration,
            )
            job = RuntimeArtifactBuildJob(
                id=uuid4(),
                tenant_id=tenant_id,
                deployment_node_id=payload.deployment_node_id,
                model_id=model_id,
                camera_id=payload.camera_id,
                artifact_id=None,
                status=ModelLifecycleJobStatus.QUEUED,
                build_format=payload.build_format,
                target_profile=payload.target_profile,
                precision=payload.precision,
                payload={
                    "job_type": "artifact_build",
                    "schema_version": 1,
                    "deployment_node_id": str(payload.deployment_node_id),
                    "model_id": str(model_id),
                    "camera_id": str(payload.camera_id) if payload.camera_id is not None else None,
                    "source_model_sha256": model.sha256,
                    "source_model_path": model.path,
                    "build_format": payload.build_format.value,
                    "export_formats": export_formats,
                    "target_profile": payload.target_profile,
                    "precision": payload.precision.value,
                    "input_shape": dict(payload.input_shape),
                    "classes": list(model.classes or []),
                    "runtime_vocabulary": runtime_vocabulary,
                    "vocabulary_hash": vocabulary_hash,
                    "vocabulary_version": vocabulary_version,
                    "output_dir": output_dir,
                    "builder_options": dict(payload.builder_options),
                },
                actor_subject=actor_subject,
                error=None,
            )
            session.add(job)
            await session.commit()
            await session.refresh(job)
        return _model_to_artifact_build_job_response(job)

    async def list_runtime_artifact_build_jobs(
        self,
        tenant_id: UUID,
        model_id: UUID,
    ) -> list[RuntimeArtifactBuildJobResponse]:
        async with self.session_factory() as session:
            statement = (
                select(RuntimeArtifactBuildJob)
                .where(RuntimeArtifactBuildJob.tenant_id == tenant_id)
                .where(RuntimeArtifactBuildJob.model_id == model_id)
                .order_by(RuntimeArtifactBuildJob.created_at.desc())
            )
            jobs = (await session.execute(statement)).scalars().all()
        return [
            _model_to_artifact_build_job_response(job)
            for job in jobs
            if isinstance(job, RuntimeArtifactBuildJob)
        ]

    async def complete_runtime_artifact_build_job(
        self,
        tenant_id: UUID,
        authenticated_node_id: UUID | None,
        job_id: UUID,
        result: SupervisorModelJobComplete,
    ) -> RuntimeArtifactBuildJobResponse:
        if result.status not in {
            ModelLifecycleJobStatus.SUCCEEDED,
            ModelLifecycleJobStatus.FAILED,
        }:
            raise ValueError("Runtime artifact build completion must be succeeded or failed.")

        async with self.session_factory() as session:
            job = await _load_runtime_artifact_build_job(
                session=session,
                tenant_id=tenant_id,
                job_id=job_id,
                for_update=True,
            )
            if (
                authenticated_node_id is not None
                and authenticated_node_id != job.deployment_node_id
            ):
                raise PermissionError(
                    "Supervisor credential cannot complete artifact build for another node."
                )
            if job.status in _TERMINAL_MODEL_LIFECYCLE_JOB_STATUSES:
                return _model_to_artifact_build_job_response(job)
            if result.status is ModelLifecycleJobStatus.FAILED:
                job.status = ModelLifecycleJobStatus.FAILED
                job.error = result.error or "Runtime artifact build failed."
                job.completed_at = datetime.now(tz=UTC)
                await session.commit()
                await session.refresh(job)
                return _model_to_artifact_build_job_response(job)

            try:
                artifact_payloads = _completion_runtime_artifact_payloads(job, result)
                artifact_payloads = await _reconcile_runtime_artifact_payloads_with_inventory(
                    session=session,
                    tenant_id=tenant_id,
                    deployment_node_id=job.deployment_node_id,
                    model_id=job.model_id,
                    artifact_payloads=artifact_payloads,
                )
                _, created_artifacts = await create_runtime_artifacts_for_model_in_session(
                    session,
                    job.model_id,
                    artifact_payloads,
                )
            except (HTTPException, ValidationError, ValueError) as exc:
                job.status = ModelLifecycleJobStatus.FAILED
                job.error = _artifact_build_completion_error(exc)
                job.completed_at = datetime.now(tz=UTC)
                await session.commit()
                await session.refresh(job)
                return _model_to_artifact_build_job_response(job)
            created_artifact_ids = [artifact.id for artifact in created_artifacts]
            job.status = ModelLifecycleJobStatus.SUCCEEDED
            job.artifact_id = created_artifact_ids[0] if created_artifact_ids else None
            job.error = None
            job.completed_at = datetime.now(tz=UTC)
            await session.commit()
            await session.refresh(job)
            return _model_to_artifact_build_job_response(job)

    async def poll_supervisor_model_jobs(
        self,
        *,
        tenant_id: UUID,
        supervisor_id: str,
        authenticated_node_id: UUID | None,
        limit: int,
    ) -> list[DeploymentModelSyncJobResponse]:
        bounded_limit = max(1, min(limit, 100))
        async with self.session_factory() as session:
            node = await _load_supervisor_model_job_node(
                session=session,
                tenant_id=tenant_id,
                supervisor_id=supervisor_id,
                authenticated_node_id=authenticated_node_id,
            )
            sync_statement = (
                select(DeploymentModelSyncJob)
                .where(DeploymentModelSyncJob.tenant_id == tenant_id)
                .where(DeploymentModelSyncJob.deployment_node_id == node.id)
                .where(
                    DeploymentModelSyncJob.status.in_(
                        [
                            ModelLifecycleJobStatus.QUEUED,
                            ModelLifecycleJobStatus.ACCEPTED,
                            ModelLifecycleJobStatus.RUNNING,
                        ]
                    )
                )
                .order_by(DeploymentModelSyncJob.created_at.asc())
                .limit(bounded_limit)
            )
            rows = (await session.execute(sync_statement)).scalars().all()
            jobs = [
                row
                for row in rows
                if isinstance(row, DeploymentModelSyncJob)
                and row.claimed_by_supervisor_id in {None, supervisor_id}
            ]
            now = datetime.now(tz=UTC)
            for job in jobs:
                if job.claimed_by_supervisor_id is None:
                    job.claimed_by_supervisor_id = supervisor_id
                    job.claimed_at = now
                if job.status is ModelLifecycleJobStatus.QUEUED:
                    job.status = ModelLifecycleJobStatus.ACCEPTED
            await session.commit()
            for job in jobs:
                await session.refresh(job)

            remaining_limit = max(0, bounded_limit - len(jobs))
            artifact_jobs: list[RuntimeArtifactBuildJob] = []
            if remaining_limit:
                artifact_statement = (
                    select(RuntimeArtifactBuildJob)
                    .where(RuntimeArtifactBuildJob.tenant_id == tenant_id)
                    .where(RuntimeArtifactBuildJob.deployment_node_id == node.id)
                    .where(RuntimeArtifactBuildJob.status == ModelLifecycleJobStatus.QUEUED)
                    .where(RuntimeArtifactBuildJob.claimed_by_supervisor_id.is_(None))
                    .order_by(RuntimeArtifactBuildJob.created_at.asc())
                    .limit(remaining_limit)
                    .with_for_update(skip_locked=True)
                )
                artifact_rows = (await session.execute(artifact_statement)).scalars().all()
                artifact_jobs = [
                    row for row in artifact_rows if isinstance(row, RuntimeArtifactBuildJob)
                ]
                for artifact_job in artifact_jobs:
                    artifact_job.claimed_by_supervisor_id = supervisor_id
                    artifact_job.claimed_at = now
                    artifact_job.status = ModelLifecycleJobStatus.ACCEPTED
                await session.commit()
                for artifact_job in artifact_jobs:
                    await session.refresh(artifact_job)
        return [
            *[_model_to_sync_job_response(job) for job in jobs],
            *[_artifact_build_job_to_supervisor_response(job) for job in artifact_jobs],
        ]

    async def record_supervisor_model_job_event(
        self,
        *,
        tenant_id: UUID,
        supervisor_id: str,
        authenticated_node_id: UUID | None,
        job_id: UUID,
        payload: SupervisorModelJobEventCreate,
    ) -> DeploymentModelSyncJobResponse:
        if payload.job_kind not in {"model_sync", "artifact_build"}:
            raise ValueError("Unsupported supervisor model job event kind.")
        if payload.job_kind == "artifact_build":
            async with self.session_factory() as session:
                job = await _load_runtime_artifact_build_job(
                    session=session,
                    tenant_id=tenant_id,
                    job_id=job_id,
                    for_update=True,
                )
                await _require_supervisor_model_job_scope(
                    session=session,
                    tenant_id=tenant_id,
                    supervisor_id=supervisor_id,
                    authenticated_node_id=authenticated_node_id,
                    deployment_node_id=job.deployment_node_id,
                )
                event = SupervisorModelJobEvent(
                    id=uuid4(),
                    tenant_id=tenant_id,
                    deployment_node_id=job.deployment_node_id,
                    job_kind=payload.job_kind,
                    job_id=job.id,
                    status=payload.status,
                    message=payload.message,
                    payload=dict(payload.payload),
                )
                session.add(event)
                _apply_artifact_build_job_event_status(job, payload)
                await session.commit()
                await session.refresh(job)
            return _artifact_build_job_to_supervisor_response(job)

        async with self.session_factory() as session:
            job = await _load_model_sync_job(
                session=session,
                tenant_id=tenant_id,
                job_id=job_id,
            )
            await _require_supervisor_model_job_scope(
                session=session,
                tenant_id=tenant_id,
                supervisor_id=supervisor_id,
                authenticated_node_id=authenticated_node_id,
                deployment_node_id=job.deployment_node_id,
            )
            event = SupervisorModelJobEvent(
                id=uuid4(),
                tenant_id=tenant_id,
                deployment_node_id=job.deployment_node_id,
                job_kind=payload.job_kind,
                job_id=job.id,
                status=payload.status,
                message=payload.message,
                payload=dict(payload.payload),
            )
            session.add(event)
            _apply_model_job_event_status(job, payload)
            await session.commit()
            await session.refresh(job)
        return _model_to_sync_job_response(job)

    async def complete_supervisor_model_job(
        self,
        *,
        tenant_id: UUID,
        supervisor_id: str,
        authenticated_node_id: UUID | None,
        job_id: UUID,
        payload: SupervisorModelJobComplete,
    ) -> DeploymentModelSyncJobResponse:
        if payload.status not in {
            ModelLifecycleJobStatus.SUCCEEDED,
            ModelLifecycleJobStatus.FAILED,
        }:
            raise ValueError("Supervisor model job completion status must be succeeded or failed.")

        async with self.session_factory() as session:
            job = await _try_load_model_sync_job(
                session=session,
                tenant_id=tenant_id,
                job_id=job_id,
            )
            if job is None:
                artifact_job = await _load_runtime_artifact_build_job(
                    session=session,
                    tenant_id=tenant_id,
                    job_id=job_id,
                )
                await _require_supervisor_model_job_scope(
                    session=session,
                    tenant_id=tenant_id,
                    supervisor_id=supervisor_id,
                    authenticated_node_id=authenticated_node_id,
                    deployment_node_id=artifact_job.deployment_node_id,
                )
                completed_artifact_job = await self.complete_runtime_artifact_build_job(
                    tenant_id=tenant_id,
                    authenticated_node_id=authenticated_node_id,
                    job_id=job_id,
                    result=payload,
                )
                return _artifact_build_job_response_to_supervisor_response(
                    completed_artifact_job
                )
            await _require_supervisor_model_job_scope(
                session=session,
                tenant_id=tenant_id,
                supervisor_id=supervisor_id,
                authenticated_node_id=authenticated_node_id,
                deployment_node_id=job.deployment_node_id,
            )
            assignment = await _load_assignment_by_id(
                session=session,
                tenant_id=tenant_id,
                deployment_node_id=job.deployment_node_id,
                assignment_id=job.assignment_id,
            )
            if (
                payload.status is ModelLifecycleJobStatus.SUCCEEDED
                and not _completion_matches_sync_job(job, payload)
            ):
                raise ValueError(
                    "Supervisor model job completion does not match expected path/hash."
                )
            now = datetime.now(tz=UTC)
            job.status = payload.status
            job.completed_at = now
            job.error = payload.error if payload.status is ModelLifecycleJobStatus.FAILED else None
            if payload.status is ModelLifecycleJobStatus.SUCCEEDED:
                if assignment is not None:
                    assignment.status = DeploymentModelAssignmentStatus.SYNCED
                    assignment.error = None
            elif assignment is not None:
                assignment.status = DeploymentModelAssignmentStatus.FAILED
                assignment.error = payload.error
            await session.commit()
            await session.refresh(job)
            if assignment is not None:
                await session.refresh(assignment)
        return _model_to_sync_job_response(job)

    async def _queue_url_import(
        self,
        *,
        tenant_id: UUID,
        actor_subject: str,
        payload: ModelImportRequest,
        catalog_id: str | None,
    ) -> ModelImportJobResponse:
        try:
            target_path = _target_path_for_url(payload.source_uri or "", self.model_store_path)
        except ValueError as exc:
            return await self._failed_import_job(
                tenant_id=tenant_id,
                actor_subject=actor_subject,
                source=ModelImportSource.URL,
                source_uri=payload.source_uri,
                target_path=str(self.model_store_path or ""),
                expected_sha256=payload.expected_sha256,
                error=f"Unsafe model URL filename: {exc}",
                catalog_id=catalog_id,
            )

        async with self.session_factory() as session:
            job = ModelImportJob(
                tenant_id=tenant_id,
                catalog_id=catalog_id,
                source=ModelImportSource.URL,
                status=ModelLifecycleJobStatus.QUEUED,
                actor_subject=actor_subject,
                source_uri=payload.source_uri,
                target_path=target_path,
                expected_sha256=payload.expected_sha256,
                progress={},
            )
            session.add(job)
            await session.commit()
            await session.refresh(job)
        return _model_to_import_job_response(job)

    async def _register_file_import(
        self,
        *,
        tenant_id: UUID,
        actor_subject: str,
        source: ModelImportSource,
        source_uri: str,
        target_path: str,
        expected_sha256: str | None,
        name: str,
        version: str,
        task: ModelTask,
        format: ModelFormat,
        capability: DetectorCapability,
        capability_config: ModelCapabilityConfig,
        input_shape: dict[str, int],
        classes: list[str] | None,
        license: str | None,
        catalog_id: str | None,
    ) -> ModelImportJobResponse:
        if catalog_id is not None:
            existing_response = await self._register_existing_catalog_model(
                tenant_id=tenant_id,
                actor_subject=actor_subject,
                source=source,
                source_uri=source_uri,
                expected_sha256=expected_sha256,
                catalog_id=catalog_id,
            )
            if existing_response is not None:
                return existing_response

        path = Path(source_uri)
        try:
            source_exists = await anyio.to_thread.run_sync(path.exists)
            source_is_file = await anyio.to_thread.run_sync(path.is_file)
        except OSError as exc:
            return await self._failed_import_job(
                tenant_id=tenant_id,
                actor_subject=actor_subject,
                source=source,
                source_uri=source_uri,
                target_path=target_path,
                expected_sha256=expected_sha256,
                error=f"Could not inspect model artifact: {exc}",
                catalog_id=catalog_id,
            )
        if not source_exists:
            return await self._failed_import_job(
                tenant_id=tenant_id,
                actor_subject=actor_subject,
                source=source,
                source_uri=source_uri,
                target_path=target_path,
                expected_sha256=expected_sha256,
                error=f"Model artifact does not exist: {source_uri}",
                catalog_id=catalog_id,
            )
        if not source_is_file:
            return await self._failed_import_job(
                tenant_id=tenant_id,
                actor_subject=actor_subject,
                source=source,
                source_uri=source_uri,
                target_path=target_path,
                expected_sha256=expected_sha256,
                error=f"Model artifact must be a regular file: {source_uri}",
                catalog_id=catalog_id,
            )

        try:
            observed_sha256 = await anyio.to_thread.run_sync(_hash_file, path)
            size_bytes = (await anyio.to_thread.run_sync(path.stat)).st_size
        except OSError as exc:
            return await self._failed_import_job(
                tenant_id=tenant_id,
                actor_subject=actor_subject,
                source=source,
                source_uri=source_uri,
                target_path=target_path,
                expected_sha256=expected_sha256,
                error=f"Could not read model artifact: {exc}",
                catalog_id=catalog_id,
            )
        if expected_sha256 is not None and observed_sha256 != expected_sha256:
            return await self._failed_import_job(
                tenant_id=tenant_id,
                actor_subject=actor_subject,
                source=source,
                source_uri=source_uri,
                target_path=target_path,
                expected_sha256=expected_sha256,
                observed_sha256=observed_sha256,
                size_bytes=size_bytes,
                error=(
                    "Model artifact sha256 mismatch: "
                    f"expected {expected_sha256}, got {observed_sha256}."
                ),
                catalog_id=catalog_id,
            )

        model_id = uuid4()
        config_data = capability_config.model_dump(mode="python")
        if catalog_id is not None:
            config_data["catalog_id"] = catalog_id
        try:
            resolved_classes = _resolve_model_classes_for_import(
                capability=capability,
                path=target_path,
                format=format,
                classes=None if classes is None else list(classes),
                capability_config=config_data,
            )
        except HTTPException as exc:
            return await self._failed_import_job(
                tenant_id=tenant_id,
                actor_subject=actor_subject,
                source=source,
                source_uri=source_uri,
                target_path=target_path,
                expected_sha256=expected_sha256,
                observed_sha256=observed_sha256,
                size_bytes=size_bytes,
                error=str(exc.detail),
                catalog_id=catalog_id,
            )
        async with self.session_factory() as session:
            model = Model(
                id=model_id,
                name=name,
                version=version,
                task=task,
                path=target_path,
                format=format,
                capability=capability,
                capability_config=config_data,
                classes=resolved_classes,
                input_shape=dict(input_shape),
                sha256=observed_sha256,
                size_bytes=size_bytes,
                license=license,
            )
            job = ModelImportJob(
                tenant_id=tenant_id,
                catalog_id=catalog_id,
                source=source,
                status=ModelLifecycleJobStatus.SUCCEEDED,
                actor_subject=actor_subject,
                model_id=model_id,
                source_uri=source_uri,
                target_path=target_path,
                expected_sha256=expected_sha256,
                observed_sha256=observed_sha256,
                size_bytes=size_bytes,
                progress={},
            )
            session.add(model)
            session.add(job)
            try:
                await session.commit()
            except IntegrityError:
                await session.rollback()
                if catalog_id is None:
                    raise
                existing_response = await self._register_existing_catalog_model(
                    tenant_id=tenant_id,
                    actor_subject=actor_subject,
                    source=source,
                    source_uri=source_uri,
                    expected_sha256=expected_sha256,
                    catalog_id=catalog_id,
                )
                if existing_response is None:
                    raise
                return existing_response
            await session.refresh(job)
        return _model_to_import_job_response(job)

    async def _register_existing_catalog_model(
        self,
        *,
        tenant_id: UUID,
        actor_subject: str,
        source: ModelImportSource,
        source_uri: str,
        expected_sha256: str | None,
        catalog_id: str,
    ) -> ModelImportJobResponse | None:
        async with self.session_factory() as session:
            existing_model = await _find_existing_catalog_model(session, catalog_id)
            if existing_model is None:
                return None
            job = ModelImportJob(
                tenant_id=tenant_id,
                catalog_id=catalog_id,
                source=source,
                status=ModelLifecycleJobStatus.SUCCEEDED,
                actor_subject=actor_subject,
                model_id=existing_model.id,
                source_uri=source_uri,
                target_path=existing_model.path,
                expected_sha256=expected_sha256,
                observed_sha256=existing_model.sha256,
                size_bytes=existing_model.size_bytes,
                progress={},
            )
            session.add(job)
            await session.commit()
            await session.refresh(job)
        return _model_to_import_job_response(job)

    async def _failed_import_job(
        self,
        *,
        tenant_id: UUID,
        actor_subject: str,
        source: ModelImportSource,
        source_uri: str | None,
        target_path: str,
        expected_sha256: str | None,
        error: str,
        catalog_id: str | None,
        observed_sha256: str | None = None,
        size_bytes: int | None = None,
    ) -> ModelImportJobResponse:
        async with self.session_factory() as session:
            job = ModelImportJob(
                tenant_id=tenant_id,
                catalog_id=catalog_id,
                source=source,
                status=ModelLifecycleJobStatus.FAILED,
                actor_subject=actor_subject,
                source_uri=source_uri,
                target_path=target_path,
                expected_sha256=expected_sha256,
                observed_sha256=observed_sha256,
                size_bytes=size_bytes,
                progress={},
                error=error,
            )
            session.add(job)
            await session.commit()
            await session.refresh(job)
        return _model_to_import_job_response(job)


def _hash_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as model_file:
        for chunk in iter(lambda: model_file.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _model_to_import_job_response(job: ModelImportJob) -> ModelImportJobResponse:
    return ModelImportJobResponse(
        id=job.id,
        tenant_id=job.tenant_id,
        catalog_id=job.catalog_id,
        source=job.source,
        status=job.status,
        actor_subject=job.actor_subject,
        model_id=job.model_id,
        source_uri=job.source_uri,
        target_path=job.target_path,
        expected_sha256=job.expected_sha256,
        observed_sha256=job.observed_sha256,
        size_bytes=job.size_bytes,
        progress=dict(job.progress or {}),
        error=job.error,
        created_at=job.created_at,
        updated_at=job.updated_at,
    )


def _edge_configuration_to_response(
    assignment: EdgeConfigurationAssignment,
) -> EdgeConfigurationResponse:
    return EdgeConfigurationResponse(
        id=assignment.id,
        tenant_id=assignment.tenant_id,
        deployment_node_id=assignment.deployment_node_id,
        revision=assignment.revision,
        desired_config=dict(assignment.desired_config or {}),
        applied_revision=assignment.applied_revision,
        apply_status=assignment.apply_status,
        last_applied_at=assignment.last_applied_at,
        error=assignment.error,
        created_at=assignment.created_at,
        updated_at=assignment.updated_at,
    )


async def _load_edge_configuration_assignment(
    *,
    session: AsyncSession,
    tenant_id: UUID,
    deployment_node_id: UUID,
    for_update: bool = False,
) -> EdgeConfigurationAssignment | None:
    statement = (
        select(EdgeConfigurationAssignment)
        .where(EdgeConfigurationAssignment.tenant_id == tenant_id)
        .where(EdgeConfigurationAssignment.deployment_node_id == deployment_node_id)
    )
    if for_update:
        statement = statement.with_for_update()
    row = (await session.execute(statement)).scalars().first()
    return row if isinstance(row, EdgeConfigurationAssignment) else None


async def _load_supervisor_edge_configuration_node(
    *,
    session: AsyncSession,
    tenant_id: UUID,
    supervisor_id: str,
    authenticated_node_id: UUID | None,
) -> DeploymentNode:
    node = await _load_deployment_node_by_supervisor(
        session=session,
        tenant_id=tenant_id,
        supervisor_id=supervisor_id,
    )
    if node is None:
        raise ValueError("Deployment node not found.")
    if authenticated_node_id is not None and authenticated_node_id != node.id:
        raise PermissionError(
            "Supervisor credential cannot manage edge configuration for another deployment node."
        )
    return node


def _validated_edge_configuration(config: dict[str, object]) -> dict[str, object]:
    unsupported_keys = sorted(set(config) - EDGE_CONFIGURATION_ALLOWED_KEYS)
    if unsupported_keys:
        joined = ", ".join(unsupported_keys)
        raise ValueError(f"Unsupported edge configuration key: {joined}.")
    return dict(config)


def _edge_configuration_apply_status(
    status: EdgeConfigurationApplyStatus | str,
) -> EdgeConfigurationApplyStatus:
    if isinstance(status, EdgeConfigurationApplyStatus):
        return status
    return EdgeConfigurationApplyStatus(str(status))


async def _load_next_desired_model_assignment(
    *,
    session: AsyncSession,
    tenant_id: UUID,
    deployment_node_id: UUID,
) -> DeploymentModelAssignment | None:
    statement = (
        select(DeploymentModelAssignment)
        .where(DeploymentModelAssignment.tenant_id == tenant_id)
        .where(DeploymentModelAssignment.deployment_node_id == deployment_node_id)
        .where(DeploymentModelAssignment.status == DeploymentModelAssignmentStatus.DESIRED)
        .order_by(DeploymentModelAssignment.created_at.asc())
        .limit(1)
    )
    row = (await session.execute(statement)).scalars().first()
    return row if isinstance(row, DeploymentModelAssignment) else None


async def _load_model_sync_job(
    *,
    session: AsyncSession,
    tenant_id: UUID,
    job_id: UUID,
) -> DeploymentModelSyncJob:
    statement = (
        select(DeploymentModelSyncJob)
        .where(DeploymentModelSyncJob.tenant_id == tenant_id)
        .where(DeploymentModelSyncJob.id == job_id)
    )
    row = (await session.execute(statement)).scalars().first()
    if not isinstance(row, DeploymentModelSyncJob):
        raise ValueError("Deployment model sync job not found.")
    return row


async def _try_load_model_sync_job(
    *,
    session: AsyncSession,
    tenant_id: UUID,
    job_id: UUID,
) -> DeploymentModelSyncJob | None:
    statement = (
        select(DeploymentModelSyncJob)
        .where(DeploymentModelSyncJob.tenant_id == tenant_id)
        .where(DeploymentModelSyncJob.id == job_id)
    )
    row = (await session.execute(statement)).scalars().first()
    return row if isinstance(row, DeploymentModelSyncJob) else None


async def _load_runtime_artifact_build_job(
    *,
    session: AsyncSession,
    tenant_id: UUID,
    job_id: UUID,
    for_update: bool = False,
) -> RuntimeArtifactBuildJob:
    statement = (
        select(RuntimeArtifactBuildJob)
        .where(RuntimeArtifactBuildJob.tenant_id == tenant_id)
        .where(RuntimeArtifactBuildJob.id == job_id)
    )
    if for_update:
        statement = statement.with_for_update()
    row = (await session.execute(statement)).scalars().first()
    if not isinstance(row, RuntimeArtifactBuildJob):
        raise ValueError("Runtime artifact build job not found.")
    return row


async def _load_supervisor_model_job_node(
    *,
    session: AsyncSession,
    tenant_id: UUID,
    supervisor_id: str,
    authenticated_node_id: UUID | None,
) -> DeploymentNode:
    node = await _load_deployment_node_by_supervisor(
        session=session,
        tenant_id=tenant_id,
        supervisor_id=supervisor_id,
    )
    if node is None:
        raise ValueError("Deployment node not found.")
    if authenticated_node_id is not None and authenticated_node_id != node.id:
        raise PermissionError(
            "Supervisor credential cannot manage model jobs for another deployment node."
        )
    return node


async def _require_supervisor_model_job_scope(
    *,
    session: AsyncSession,
    tenant_id: UUID,
    supervisor_id: str,
    authenticated_node_id: UUID | None,
    deployment_node_id: UUID,
) -> None:
    node = await _load_supervisor_model_job_node(
        session=session,
        tenant_id=tenant_id,
        supervisor_id=supervisor_id,
        authenticated_node_id=authenticated_node_id,
    )
    if node.id != deployment_node_id:
        raise PermissionError(
            "Supervisor credential cannot manage model jobs for another deployment node."
        )


def _model_sync_job_payload(
    *,
    deployment_node_id: UUID,
    assignment: DeploymentModelAssignment,
    model: Model,
    edge_configuration: EdgeConfigurationAssignment | None = None,
) -> dict[str, object]:
    target_path = assignment.desired_path or _configured_store_path(
        edge_configuration=edge_configuration,
        key="model_store_path",
        source_path=model.path,
    ) or model.path
    return {
        "job_type": "model_sync",
        "schema_version": 1,
        "deployment_node_id": str(deployment_node_id),
        "model_id": str(model.id),
        "model_name": model.name,
        "source_path": model.path,
        "expected_sha256": model.sha256,
        "size_bytes": model.size_bytes,
        "target_path": target_path,
    }


def _model_to_artifact_build_job_response(
    job: RuntimeArtifactBuildJob,
) -> RuntimeArtifactBuildJobResponse:
    return RuntimeArtifactBuildJobResponse(
        id=job.id,
        tenant_id=job.tenant_id,
        deployment_node_id=job.deployment_node_id,
        model_id=job.model_id,
        camera_id=job.camera_id,
        artifact_id=job.artifact_id,
        status=job.status,
        build_format=job.build_format,
        target_profile=job.target_profile,
        precision=job.precision,
        payload=dict(job.payload or {}),
        claimed_by_supervisor_id=job.claimed_by_supervisor_id,
        claimed_at=job.claimed_at,
        completed_at=job.completed_at,
        error=job.error,
        created_at=job.created_at,
        updated_at=job.updated_at,
    )


def _model_to_sync_job_response(job: DeploymentModelSyncJob) -> DeploymentModelSyncJobResponse:
    return DeploymentModelSyncJobResponse(
        id=job.id,
        tenant_id=job.tenant_id,
        deployment_node_id=job.deployment_node_id,
        assignment_id=job.assignment_id,
        model_id=job.model_id,
        status=job.status,
        payload=dict(job.payload or {}),
        claimed_by_supervisor_id=job.claimed_by_supervisor_id,
        claimed_at=job.claimed_at,
        completed_at=job.completed_at,
        error=job.error,
        created_at=job.created_at,
        updated_at=job.updated_at,
    )


def _artifact_build_job_to_supervisor_response(
    job: RuntimeArtifactBuildJob,
) -> DeploymentModelSyncJobResponse:
    return DeploymentModelSyncJobResponse(
        id=job.id,
        tenant_id=job.tenant_id,
        deployment_node_id=job.deployment_node_id,
        assignment_id=job.id,
        model_id=job.model_id,
        status=job.status,
        payload=dict(job.payload or {}),
        claimed_by_supervisor_id=job.claimed_by_supervisor_id,
        claimed_at=job.claimed_at,
        completed_at=job.completed_at,
        error=job.error,
        created_at=job.created_at,
        updated_at=job.updated_at,
    )


def _artifact_build_job_response_to_supervisor_response(
    job: RuntimeArtifactBuildJobResponse,
) -> DeploymentModelSyncJobResponse:
    return DeploymentModelSyncJobResponse(
        id=job.id,
        tenant_id=job.tenant_id,
        deployment_node_id=job.deployment_node_id,
        assignment_id=job.id,
        model_id=job.model_id,
        status=job.status,
        payload=dict(job.payload or {}),
        claimed_by_supervisor_id=job.claimed_by_supervisor_id,
        claimed_at=job.claimed_at,
        completed_at=job.completed_at,
        error=job.error,
        created_at=job.created_at,
        updated_at=job.updated_at,
    )


def _apply_model_job_event_status(
    job: DeploymentModelSyncJob,
    payload: SupervisorModelJobEventCreate,
) -> None:
    if payload.status in {
        ModelLifecycleJobStatus.ACCEPTED,
        ModelLifecycleJobStatus.RUNNING,
    }:
        job.status = payload.status
        job.error = None


def _apply_artifact_build_job_event_status(
    job: RuntimeArtifactBuildJob,
    payload: SupervisorModelJobEventCreate,
) -> None:
    if job.status in _TERMINAL_MODEL_LIFECYCLE_JOB_STATUSES:
        return
    if payload.status in {
        ModelLifecycleJobStatus.ACCEPTED,
        ModelLifecycleJobStatus.RUNNING,
    }:
        job.status = payload.status
        job.error = None


def _completion_matches_sync_job(
    job: DeploymentModelSyncJob,
    payload: SupervisorModelJobComplete,
) -> bool:
    expected_sha256 = job.payload.get("expected_sha256") if job.payload else None
    expected_path = job.payload.get("target_path") if job.payload else None
    expected_size = job.payload.get("size_bytes") if job.payload else None
    reported_sha256 = payload.sha256
    if reported_sha256 is None:
        payload_sha256 = payload.payload.get("sha256")
        if isinstance(payload_sha256, str):
            reported_sha256 = payload_sha256

    reported_path = payload.local_path or payload.path
    if reported_path is None:
        for key in ("local_path", "path"):
            payload_path = payload.payload.get(key)
            if isinstance(payload_path, str):
                reported_path = payload_path
                break

    reported_size = payload.size_bytes
    if reported_size is None:
        payload_size = payload.payload.get("size_bytes")
        if isinstance(payload_size, int):
            reported_size = payload_size

    return (
        isinstance(expected_sha256, str)
        and reported_sha256 == expected_sha256
        and isinstance(expected_path, str)
        and reported_path == expected_path
        and isinstance(expected_size, int)
        and reported_size == expected_size
    )


async def _require_target_profile_supported(
    *,
    session: AsyncSession,
    tenant_id: UUID,
    node: DeploymentNode,
    target_profile: str,
) -> None:
    if getattr(node, "host_profile", None) == target_profile:
        return
    statement = (
        select(EdgeNodeHardwareReport)
        .where(EdgeNodeHardwareReport.tenant_id == tenant_id)
        .where(EdgeNodeHardwareReport.supervisor_id == node.supervisor_id)
        .order_by(EdgeNodeHardwareReport.reported_at.desc())
        .limit(1)
    )
    latest = (await session.execute(statement)).scalars().first()
    if isinstance(latest, EdgeNodeHardwareReport) and latest.host_profile == target_profile:
        return
    raise ValueError("Runtime artifact target profile does not match deployment node.")


def _artifact_output_dir(
    *,
    model: Model,
    payload: RuntimeArtifactBuildJobCreate,
    edge_configuration: EdgeConfigurationAssignment | None = None,
) -> str:
    output_dir = payload.builder_options.get("output_dir")
    if isinstance(output_dir, str) and output_dir:
        return output_dir
    artifact_store = _configured_directory(edge_configuration, "artifact_store_path")
    if artifact_store is not None:
        return str(artifact_store / str(model.id))
    return str(Path(model.path).parent / "runtime-artifacts" / str(model.id))


def _configured_store_path(
    *,
    edge_configuration: EdgeConfigurationAssignment | None,
    key: str,
    source_path: str,
) -> str | None:
    directory = _configured_directory(edge_configuration, key)
    if directory is None:
        return None
    filename = Path(source_path).name
    if not filename:
        return None
    return str(directory / filename)


def _configured_directory(
    edge_configuration: EdgeConfigurationAssignment | None,
    key: str,
) -> Path | None:
    if edge_configuration is None:
        return None
    value = dict(edge_configuration.desired_config or {}).get(key)
    if not isinstance(value, str) or not value:
        return None
    return Path(value)


def _completion_artifact_payloads(
    result: SupervisorModelJobComplete,
) -> list[dict[str, object]]:
    artifacts = result.payload.get("artifacts")
    if isinstance(artifacts, list):
        payloads = [artifact for artifact in artifacts if isinstance(artifact, dict)]
    else:
        artifact = result.payload.get("artifact")
        if isinstance(artifact, dict):
            payloads = [artifact]
        elif "scope" in result.payload:
            payloads = [result.payload]
        else:
            payloads = []
    if not payloads:
        raise ValueError("Successful artifact build completion must include artifact payload.")
    return [dict(payload) for payload in payloads]


def _completion_runtime_artifact_payloads(
    job: RuntimeArtifactBuildJob,
    result: SupervisorModelJobComplete,
) -> list[RuntimeArtifactCreate]:
    artifacts = [
        RuntimeArtifactCreate.model_validate(payload)
        for payload in _completion_artifact_payloads(result)
    ]
    for artifact in artifacts:
        _validate_runtime_artifact_matches_build_job(job, artifact)
    return artifacts


async def _reconcile_runtime_artifact_payloads_with_inventory(
    *,
    session: AsyncSession,
    tenant_id: UUID,
    deployment_node_id: UUID,
    model_id: UUID,
    artifact_payloads: list[RuntimeArtifactCreate],
) -> list[RuntimeArtifactCreate]:
    inventory_rows = await _load_inventory_rows(
        session=session,
        tenant_id=tenant_id,
        deployment_node_id=deployment_node_id,
    )
    reconciled: list[RuntimeArtifactCreate] = []
    for artifact in artifact_payloads:
        match = _matching_runtime_artifact_inventory(
            inventory_rows,
            model_id=model_id,
            artifact=artifact,
        )
        if match is None:
            reconciled.append(
                artifact.model_copy(
                    update={
                        "validation_status": RuntimeArtifactValidationStatus.UNVALIDATED,
                        "validation_error": "Runtime artifact not confirmed by edge inventory.",
                        "validated_at": None,
                    }
                )
            )
            continue
        reconciled.append(
            artifact.model_copy(
                update={
                    "validation_status": RuntimeArtifactValidationStatus.VALID,
                    "validation_error": None,
                    "validated_at": match.reported_at,
                }
            )
        )
    return reconciled


def _matching_runtime_artifact_inventory(
    inventory_rows: list[DeploymentModelInventory],
    *,
    model_id: UUID,
    artifact: RuntimeArtifactCreate,
) -> DeploymentModelInventory | None:
    for row in inventory_rows:
        if row.asset_kind != "runtime_artifact":
            continue
        if row.asset_id != model_id:
            continue
        if row.local_path != artifact.path:
            continue
        if row.sha256 != artifact.sha256:
            continue
        if row.size_bytes != artifact.size_bytes:
            continue
        if row.target_profile != artifact.target_profile:
            continue
        return row
    return None


def _validate_runtime_artifact_matches_build_job(
    job: RuntimeArtifactBuildJob,
    artifact: RuntimeArtifactCreate,
) -> None:
    if artifact.target_profile != job.target_profile:
        raise ValueError("Runtime artifact target_profile must match build job target_profile.")
    if artifact.precision is not job.precision:
        raise ValueError("Runtime artifact precision must match build job precision.")
    expected_input_shape = _mapping_or_none(job.payload.get("input_shape")) or {}
    if dict(artifact.input_shape) != dict(expected_input_shape):
        raise ValueError("Runtime artifact input_shape must match build job input_shape.")
    if artifact.scope is RuntimeArtifactScope.SCENE and artifact.camera_id != job.camera_id:
        raise ValueError("Runtime artifact camera_id must match build job camera_id.")
    expected_source_hash = _optional_string(job.payload.get("source_model_sha256"))
    if expected_source_hash is not None and artifact.source_model_sha256 != expected_source_hash:
        raise ValueError(
            "Runtime artifact source_model_sha256 must match build job source_model_sha256."
        )
    expected_vocabulary_hash = _optional_string(job.payload.get("vocabulary_hash"))
    if (
        expected_vocabulary_hash is not None
        and artifact.vocabulary_hash != expected_vocabulary_hash
    ):
        raise ValueError(
            "Runtime artifact vocabulary_hash must match build job vocabulary_hash."
        )
    allowed_kinds = _string_list(job.payload.get("export_formats"))
    if not allowed_kinds:
        allowed_kinds = [job.build_format.value]
    if artifact.kind.value not in allowed_kinds:
        raise ValueError("Runtime artifact kind must match a build job export format.")


def _optional_string(value: object) -> str | None:
    return value if isinstance(value, str) and value else None


def _string_list(value: object) -> list[str]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, str)]


def _mapping_or_none(value: object) -> dict[str, object] | None:
    return dict(value) if isinstance(value, dict) else None


def _artifact_build_completion_error(exc: Exception) -> str:
    if isinstance(exc, HTTPException):
        detail = exc.detail
        if isinstance(detail, str):
            return detail
        return str(detail)
    return str(exc) or exc.__class__.__name__


def _model_capability(model: Model) -> DetectorCapability:
    capability = getattr(model, "capability", None)
    if isinstance(capability, DetectorCapability):
        return capability
    if capability is None:
        return DetectorCapability.FIXED_VOCAB
    return DetectorCapability(str(capability))


async def _load_deployment_node(
    *,
    session: AsyncSession,
    tenant_id: UUID,
    deployment_node_id: UUID,
) -> DeploymentNode:
    node = await session.get(DeploymentNode, deployment_node_id)
    if not isinstance(node, DeploymentNode) or node.tenant_id != tenant_id:
        raise ValueError("Deployment node not found.")
    return node


async def _load_deployment_node_by_supervisor(
    *,
    session: AsyncSession,
    tenant_id: UUID,
    supervisor_id: str,
) -> DeploymentNode | None:
    statement = (
        select(DeploymentNode)
        .where(DeploymentNode.tenant_id == tenant_id)
        .where(DeploymentNode.supervisor_id == supervisor_id)
    )
    row = (await session.execute(statement)).scalars().first()
    return row if isinstance(row, DeploymentNode) else None


def _require_assignable_deployment_node(node: DeploymentNode) -> None:
    if node.node_kind not in {DeploymentNodeKind.CENTRAL, DeploymentNodeKind.EDGE}:
        raise ValueError("Deployment node must be a central or edge node.")
    if node.node_kind is DeploymentNodeKind.CENTRAL and node.edge_node_id is not None:
        raise ValueError("Central deployment node must not reference an edge node.")
    if node.node_kind is DeploymentNodeKind.EDGE and node.edge_node_id is None:
        raise ValueError("Edge deployment node must reference an edge node.")


async def _load_model_assignment(
    *,
    session: AsyncSession,
    tenant_id: UUID,
    deployment_node_id: UUID,
    model_id: UUID,
) -> DeploymentModelAssignment | None:
    statement = (
        select(DeploymentModelAssignment)
        .where(DeploymentModelAssignment.tenant_id == tenant_id)
        .where(DeploymentModelAssignment.deployment_node_id == deployment_node_id)
        .where(DeploymentModelAssignment.model_id == model_id)
    )
    row = (await session.execute(statement)).scalars().first()
    return row if isinstance(row, DeploymentModelAssignment) else None


async def _load_assignment_by_id(
    *,
    session: AsyncSession,
    tenant_id: UUID,
    deployment_node_id: UUID,
    assignment_id: UUID,
) -> DeploymentModelAssignment | None:
    statement = (
        select(DeploymentModelAssignment)
        .where(DeploymentModelAssignment.tenant_id == tenant_id)
        .where(DeploymentModelAssignment.deployment_node_id == deployment_node_id)
        .where(DeploymentModelAssignment.id == assignment_id)
    )
    row = (await session.execute(statement)).scalars().first()
    return row if isinstance(row, DeploymentModelAssignment) else None


async def _load_inventory_rows(
    *,
    session: AsyncSession,
    tenant_id: UUID,
    deployment_node_id: UUID,
) -> list[DeploymentModelInventory]:
    statement = (
        select(DeploymentModelInventory)
        .where(DeploymentModelInventory.tenant_id == tenant_id)
        .where(DeploymentModelInventory.deployment_node_id == deployment_node_id)
        .order_by(
            DeploymentModelInventory.asset_kind.asc(),
            DeploymentModelInventory.reported_at.desc(),
        )
    )
    rows = (await session.execute(statement)).scalars().all()
    return [row for row in rows if isinstance(row, DeploymentModelInventory)]


async def _upsert_inventory_item(
    *,
    session: AsyncSession,
    tenant_id: UUID,
    deployment_node_id: UUID,
    item: DeploymentModelInventoryItem,
) -> DeploymentModelInventory:
    insert_statement = pg_insert(DeploymentModelInventory).values(
        id=uuid4(),
        tenant_id=tenant_id,
        deployment_node_id=deployment_node_id,
        asset_kind=item.asset_kind,
        asset_id=item.asset_id,
        local_path=item.local_path,
        sha256=item.sha256,
        size_bytes=item.size_bytes,
        target_profile=item.target_profile,
        runtime_versions=dict(item.runtime_versions),
        reported_at=item.reported_at,
    )
    statement = insert_statement.on_conflict_do_update(
        constraint="uq_deployment_model_inventory_asset",
        set_={
            "local_path": insert_statement.excluded.local_path,
            "sha256": insert_statement.excluded.sha256,
            "size_bytes": insert_statement.excluded.size_bytes,
            "target_profile": insert_statement.excluded.target_profile,
            "runtime_versions": insert_statement.excluded.runtime_versions,
            "reported_at": insert_statement.excluded.reported_at,
            "updated_at": func.now(),
        },
    ).returning(DeploymentModelInventory)
    row = (await session.execute(statement)).scalars().first()
    if not isinstance(row, DeploymentModelInventory):
        raise RuntimeError("Deployment model inventory upsert did not return a row.")
    return row


async def _mark_synced_assignments(
    *,
    session: AsyncSession,
    tenant_id: UUID,
    deployment_node_id: UUID,
    items: list[DeploymentModelInventoryItem],
) -> None:
    for item in items:
        if item.asset_kind != "model":
            continue
        model = await session.get(Model, item.asset_id)
        if not isinstance(model, Model) or model.sha256 != item.sha256:
            continue
        assignment = await _load_model_assignment(
            session=session,
            tenant_id=tenant_id,
            deployment_node_id=deployment_node_id,
            model_id=item.asset_id,
        )
        if assignment is None or assignment.status is DeploymentModelAssignmentStatus.REMOVED:
            continue
        expected_path = assignment.desired_path or model.path
        if item.local_path != expected_path or item.size_bytes != model.size_bytes:
            continue
        assignment.status = DeploymentModelAssignmentStatus.SYNCED
        assignment.error = None


def _model_to_assignment_response(
    assignment: DeploymentModelAssignment,
) -> DeploymentModelAssignmentResponse:
    return DeploymentModelAssignmentResponse(
        id=assignment.id,
        tenant_id=assignment.tenant_id,
        deployment_node_id=assignment.deployment_node_id,
        model_id=assignment.model_id,
        status=assignment.status,
        desired_path=assignment.desired_path,
        last_sync_job_id=assignment.last_sync_job_id,
        error=assignment.error,
        created_at=assignment.created_at,
        updated_at=assignment.updated_at,
    )


def _model_to_inventory_item(row: DeploymentModelInventory) -> DeploymentModelInventoryItem:
    return DeploymentModelInventoryItem(
        asset_kind=row.asset_kind,  # type: ignore[arg-type]
        asset_id=row.asset_id,
        local_path=row.local_path,
        sha256=row.sha256,
        size_bytes=row.size_bytes,
        target_profile=row.target_profile,
        runtime_versions=dict(row.runtime_versions or {}),
        reported_at=row.reported_at,
    )


def _find_catalog_entry(catalog_id: str) -> ModelCatalogEntry:
    entry = get_model_catalog_entry(catalog_id)
    if entry is not None:
        return entry
    raise ValueError(f"Model catalog entry not found: {catalog_id}")


async def _find_existing_catalog_model(
    session: AsyncSession,
    catalog_id: str,
) -> Model | None:
    statement = select(Model).where(Model.capability_config["catalog_id"].astext == catalog_id)
    result = await session.execute(statement)
    return result.scalars().first()


def _resolve_model_classes_for_import(
    *,
    capability: DetectorCapability,
    path: str,
    format: ModelFormat,
    classes: list[str] | None,
    capability_config: dict[str, object],
) -> list[str]:
    from argus.services import app as app_services

    return app_services._resolve_model_classes_for_capability(
        capability=capability,
        path=path,
        format=format,
        classes=classes,
        capability_config=capability_config,
    )


def _target_path_for_url(source_uri: str, model_store_path: Path | None) -> str:
    filename = _safe_url_target_filename(source_uri)
    if model_store_path is None:
        return source_uri
    return str(model_store_path / filename)


def _safe_url_target_filename(source_uri: str) -> str:
    raw_path = urlsplit(source_uri).path
    raw_basename = raw_path.rsplit("/", 1)[-1]
    filename = unquote(raw_basename)
    if filename in {"", ".", ".."} or "/" in filename or "\\" in filename:
        raise ValueError(f"{filename!r} is not a safe filename.")
    return filename
