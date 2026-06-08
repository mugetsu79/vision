from __future__ import annotations

import hashlib
from pathlib import Path
from urllib.parse import unquote, urlsplit
from uuid import UUID, uuid4

import anyio
from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from argus.api.contracts import (
    DeploymentModelAssignmentCreate,
    DeploymentModelAssignmentResponse,
    DeploymentModelInventoryItem,
    DeploymentModelInventoryReport,
    ModelCapabilityConfig,
    ModelImportJobResponse,
    ModelImportRequest,
)
from argus.models.enums import (
    DeploymentModelAssignmentStatus,
    DeploymentNodeKind,
    DetectorCapability,
    ModelFormat,
    ModelImportSource,
    ModelLifecycleJobStatus,
    ModelTask,
)
from argus.models.tables import (
    DeploymentModelAssignment,
    DeploymentModelInventory,
    DeploymentNode,
    Model,
    ModelImportJob,
)
from argus.services.model_catalog import ModelCatalogEntry, get_model_catalog_entry


class ModelLifecycleService:
    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession],
        model_store_path: Path | None = None,
    ) -> None:
        self.session_factory = session_factory
        self.model_store_path = model_store_path

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
        capability_config = entry.capability_config.model_copy()
        return await self._register_file_import(
            tenant_id=tenant_id,
            actor_subject=actor_subject,
            source=ModelImportSource.CATALOG,
            source_uri=entry.path_hint,
            target_path=entry.path_hint,
            expected_sha256=None,
            name=entry.name,
            version=entry.version,
            task=entry.task,
            format=entry.format,
            capability=entry.capability,
            capability_config=capability_config,
            input_shape=entry.input_shape,
            classes=list(entry.classes),
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
        classes: list[str],
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
                classes=list(classes),
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
    statement = (
        select(DeploymentModelInventory)
        .where(DeploymentModelInventory.tenant_id == tenant_id)
        .where(DeploymentModelInventory.deployment_node_id == deployment_node_id)
        .where(DeploymentModelInventory.asset_kind == item.asset_kind)
        .where(DeploymentModelInventory.asset_id == item.asset_id)
        .where(DeploymentModelInventory.sha256 == item.sha256)
    )
    existing = (await session.execute(statement)).scalars().first()
    if isinstance(existing, DeploymentModelInventory):
        existing.local_path = item.local_path
        existing.size_bytes = item.size_bytes
        existing.target_profile = item.target_profile
        existing.runtime_versions = dict(item.runtime_versions)
        existing.reported_at = item.reported_at
        return existing

    inventory = DeploymentModelInventory(
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
    session.add(inventory)
    return inventory


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
