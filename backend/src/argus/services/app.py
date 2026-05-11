from __future__ import annotations

import asyncio
import csv
import io
import logging
import math
import secrets
import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path, PurePosixPath
from typing import TYPE_CHECKING, Any, Literal, cast
from urllib.parse import urlsplit, urlunsplit
from uuid import UUID

import httpx
from fastapi import HTTPException, status
from nats.js import api as js_api
from sqlalchemy import bindparam, select, text, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from argus.api.contracts import (
    BrowserDeliveryProfile,
    BrowserDeliveryProfileId,
    BrowserDeliverySettings,
    CameraCommandPayload,
    CameraCreate,
    CameraResponse,
    CameraSetupPreviewResponse,
    CameraSourceProbeRequest,
    CameraSourceProbeResponse,
    CameraSourceSettings,
    CameraUpdate,
    DerivedBrowserProfiles,
    DetectionRegion,
    EdgeHeartbeatRequest,
    EdgeHeartbeatResponse,
    EdgeRegisterRequest,
    EdgeRegisterResponse,
    EvidenceArtifactResponse,
    EvidenceLedgerEntryResponse,
    EvidenceLedgerSummary,
    EvidenceRecordingPolicy,
    ExportArtifact,
    FleetBootstrapRequest,
    FleetBootstrapResponse,
    FleetCameraWorkerSummary,
    FleetDeliveryDiagnostic,
    FleetLifecycleMode,
    FleetNodeStatus,
    FleetNodeSummary,
    FleetOverviewResponse,
    FleetSummary,
    FrameSize,
    HistoryBucketCoverage,
    HistoryClassesResponse,
    HistoryPoint,
    HistorySeriesResponse,
    HistorySeriesRow,
    HomographyPayload,
    IncidentResponse,
    ModelCapabilityConfig,
    ModelCatalogEntryResponse,
    ModelCreate,
    ModelResponse,
    ModelUpdate,
    NativeAvailability,
    PrivacyManifestSnapshotResponse,
    PrivacySettings,
    RuntimeBackend,
    RuntimeVocabularyState,
    SceneContractSnapshotResponse,
    SceneVisionProfile,
    SiteCreate,
    SiteResponse,
    SiteUpdate,
    SourceCapability,
    StreamOfferRequest,
    StreamOfferResponse,
    TelemetryEnvelope,
    TenantContext,
    WorkerCameraSettings,
    WorkerConfigResponse,
    WorkerDesiredState,
    WorkerModelSettings,
    WorkerPrivacySettings,
    WorkerPublishSettings,
    WorkerRuntimeArtifact,
    WorkerRuntimeCapability,
    WorkerRuntimeStatus,
    WorkerStreamSettings,
    WorkerTrackerSettings,
)
from argus.compat import UTC
from argus.core.config import Settings
from argus.core.db import DatabaseManager
from argus.core.events import EventMessage, NatsJetStreamClient
from argus.core.logging import redact_url_secrets
from argus.core.security import decrypt_rtsp_url, encrypt_rtsp_url, hash_api_key
from argus.inference.publisher import TelemetryFrame
from argus.models.enums import (
    CameraSourceKind,
    CountEventType,
    DetectorCapability,
    EvidenceLedgerAction,
    EvidenceStorageProvider,
    HistoryCoverageStatus,
    HistoryMetric,
    IncidentReviewStatus,
    ModelFormat,
    ModelTask,
    ProcessingMode,
    RuntimeArtifactScope,
    RuntimeArtifactValidationStatus,
    RuntimeVocabularySource,
)
from argus.models.tables import (
    APIKey,
    AuditLog,
    Camera,
    CameraVocabularySnapshot,
    EdgeNode,
    EvidenceArtifact,
    EvidenceLedgerEntry,
    Incident,
    Model,
    ModelRuntimeArtifact,
    PrivacyManifestSnapshot,
    SceneContractSnapshot,
    Site,
    Tenant,
    TrackingEvent,
)
from argus.services.camera_sources import (
    NormalizedCameraSource,
    normalize_camera_source,
    validate_camera_source_assignment,
)
from argus.services.evidence_ledger import EvidenceLedgerService
from argus.services.model_catalog import resolve_catalog_status
from argus.services.privacy_manifests import PrivacyManifestService, build_privacy_manifest
from argus.services.runtime_artifacts import (
    RuntimeArtifactService,
    artifact_matches_camera_vocabulary,
)
from argus.services.scene_contracts import SceneContractService, build_scene_contract
from argus.streaming.mediamtx import MediaMTXClient
from argus.streaming.webrtc import (
    ConcurrencyLimitExceeded,
    MediaMTXTokenIssuer,
    StreamAccess,
    UpstreamProxyStream,
    UserConcurrencyLimiter,
    WebRTCNegotiator,
    resolve_stream_access,
)
from argus.vision.model_metadata import resolve_model_classes
from argus.vision.source_probe import probe_rtsp_source, probe_usb_source
from argus.vision.vocabulary import hash_vocabulary, normalize_vocabulary_terms

HTTP_422_UNPROCESSABLE = getattr(status, "HTTP_422_UNPROCESSABLE_CONTENT", 422)

if TYPE_CHECKING:
    from argus.services.query import QueryService


logger = logging.getLogger(__name__)

_SETUP_PREVIEW_CACHE_TTL = timedelta(minutes=2)


def capture_still_image(rtsp_url: str) -> tuple[bytes, int, int]:
    from argus.vision.camera import capture_still_image as _capture_still_image

    return _capture_still_image(rtsp_url)


def _probe_video_dimensions(rtsp_url: str) -> tuple[int, int]:
    from argus.vision.camera import _probe_video_dimensions as _probe_dimensions

    return _probe_dimensions(rtsp_url)


@dataclass(slots=True)
class _SetupPreviewSnapshot:
    image_bytes: bytes
    frame_size: FrameSize
    captured_at: datetime
    content_type: str = "image/jpeg"


@dataclass(slots=True)
class _SetupPreviewCacheEntry:
    snapshot: _SetupPreviewSnapshot
    camera_updated_at: datetime
    expires_at: datetime


@dataclass(frozen=True, slots=True)
class IncidentArtifactContent:
    content_type: str
    file_path: Path | None = None
    redirect_url: str | None = None


@dataclass(slots=True)
class AppServices:
    tenancy: TenancyService
    sites: SiteService
    cameras: CameraService
    models: ModelService
    runtime_artifacts: RuntimeArtifactService
    privacy_manifests: PrivacyManifestService
    scene_contracts: SceneContractService
    edge: EdgeService
    operations: OperationsService
    history: HistoryService
    incidents: IncidentService
    streams: StreamService
    query: QueryService
    telemetry: NatsTelemetryService

    async def close(self) -> None:
        await self.streams.close()


class DatabaseAuditLogger:
    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self.session_factory = session_factory

    def add_to_session(
        self,
        session: AsyncSession,
        *,
        tenant_context: TenantContext,
        action: str,
        target: str,
        meta: dict[str, Any] | None = None,
    ) -> None:
        session.add(
            AuditLog(
                tenant_id=tenant_context.tenant_id,
                actor_id=None,
                action=action,
                target=target,
                meta=meta,
                ts=datetime.now(tz=UTC),
            )
        )

    async def record(
        self,
        *,
        tenant_context: TenantContext,
        action: str,
        target: str,
        meta: dict[str, Any] | None = None,
    ) -> None:
        async with self.session_factory() as session:
            self.add_to_session(
                session,
                tenant_context=tenant_context,
                action=action,
                target=target,
                meta=meta,
            )
            await session.commit()

    async def record_query(
        self,
        *,
        tenant_context: TenantContext,
        prompt: str,
        resolved_classes: list[str],
        provider: str,
        model: str,
        latency_ms: int,
    ) -> None:
        await self.record(
            tenant_context=tenant_context,
            action="query.resolve",
            target="query",
            meta={
                "prompt": prompt,
                "resolved_classes": resolved_classes,
                "provider": provider,
                "model": model,
                "latency_ms": latency_ms,
            },
        )


class TenancyService:
    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession],
        settings: Settings,
    ) -> None:
        self.session_factory = session_factory
        self.settings = settings

    async def resolve_context(
        self,
        *,
        user: Any,
        explicit_tenant_id: UUID | None = None,
    ) -> TenantContext:
        if user.is_superadmin:
            tenant_id = explicit_tenant_id or _parse_optional_uuid(user.tenant_context)
            if tenant_id is None:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Superadmin requests must include an explicit tenant context.",
                )
            tenant = await self._load_tenant_by_id(tenant_id)
            return TenantContext(tenant_id=tenant.id, tenant_slug=tenant.slug, user=user)

        tenant_id = _parse_optional_uuid(user.tenant_context)
        if tenant_id is not None:
            tenant = await self._load_tenant_by_id(tenant_id)
            if explicit_tenant_id is not None and explicit_tenant_id != tenant.id:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Tenant users cannot switch tenant context.",
                )
            return TenantContext(tenant_id=tenant.id, tenant_slug=tenant.slug, user=user)

        tenant = await self._load_or_bootstrap_tenant_by_slug(user.realm)
        return TenantContext(tenant_id=tenant.id, tenant_slug=tenant.slug, user=user)

    async def _load_tenant_by_id(self, tenant_id: UUID) -> Tenant:
        async with self.session_factory() as session:
            tenant = await session.get(Tenant, tenant_id)
        if tenant is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tenant not found.")
        return tenant

    async def _load_tenant_by_slug(self, slug: str) -> Tenant:
        async with self.session_factory() as session:
            statement = select(Tenant).where(Tenant.slug == slug)
            tenant = (await session.execute(statement)).scalar_one_or_none()
        if tenant is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tenant not found.")
        return tenant

    async def _load_or_bootstrap_tenant_by_slug(self, slug: str) -> Tenant:
        try:
            return await self._load_tenant_by_slug(slug)
        except HTTPException as exc:
            if exc.status_code != status.HTTP_404_NOT_FOUND:
                raise
            if self.settings.environment != "development":
                raise

        async with self.session_factory() as session:
            tenant = Tenant(name=_tenant_name_from_slug(slug), slug=slug)
            session.add(tenant)
            try:
                await session.commit()
            except IntegrityError:
                await session.rollback()
            else:
                await session.refresh(tenant)
                return tenant

        return await self._load_tenant_by_slug(slug)


class SiteService:
    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession],
        audit_logger: DatabaseAuditLogger,
    ) -> None:
        self.session_factory = session_factory
        self.audit_logger = audit_logger

    async def list_sites(self, tenant_context: TenantContext) -> list[SiteResponse]:
        async with self.session_factory() as session:
            statement = (
                select(Site)
                .where(Site.tenant_id == tenant_context.tenant_id)
                .order_by(Site.name)
            )
            sites = (await session.execute(statement)).scalars().all()
        return [_site_to_response(site) for site in sites]

    async def get_site(self, tenant_context: TenantContext, site_id: UUID) -> SiteResponse:
        site = await _get_site(
            session_factory=self.session_factory,
            tenant_context=tenant_context,
            site_id=site_id,
        )
        return _site_to_response(site)

    async def create_site(self, tenant_context: TenantContext, payload: SiteCreate) -> SiteResponse:
        async with self.session_factory() as session:
            site = Site(
                tenant_id=tenant_context.tenant_id,
                name=payload.name,
                description=payload.description,
                tz=payload.tz,
                geo_point=payload.geo_point,
            )
            session.add(site)
            await session.commit()
            await session.refresh(site)
        await self.audit_logger.record(
            tenant_context=tenant_context,
            action="site.create",
            target=f"site:{site.id}",
            meta={"name": site.name},
        )
        return _site_to_response(site)

    async def update_site(
        self,
        tenant_context: TenantContext,
        site_id: UUID,
        payload: SiteUpdate,
    ) -> SiteResponse:
        async with self.session_factory() as session:
            site = await _load_site(session, tenant_context.tenant_id, site_id)
            for field_name, value in payload.model_dump(exclude_unset=True).items():
                setattr(site, field_name, value)
            await session.commit()
            await session.refresh(site)
        await self.audit_logger.record(
            tenant_context=tenant_context,
            action="site.update",
            target=f"site:{site.id}",
            meta=payload.model_dump(exclude_unset=True),
        )
        return _site_to_response(site)

    async def delete_site(self, tenant_context: TenantContext, site_id: UUID) -> None:
        async with self.session_factory() as session:
            site = await _load_site(session, tenant_context.tenant_id, site_id)
            await session.delete(site)
            await session.commit()
        await self.audit_logger.record(
            tenant_context=tenant_context,
            action="site.delete",
            target=f"site:{site_id}",
        )


class ModelService:
    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession],
        audit_logger: DatabaseAuditLogger,
    ) -> None:
        self.session_factory = session_factory
        self.audit_logger = audit_logger

    async def list_models(self) -> list[ModelResponse]:
        async with self.session_factory() as session:
            statement = select(Model).order_by(Model.name, Model.version)
            models = (await session.execute(statement)).scalars().all()
        return [_model_to_response(model) for model in models]

    async def list_catalog_status(self) -> list[ModelCatalogEntryResponse]:
        async with self.session_factory() as session:
            models = (await session.execute(select(Model))).scalars().all()
        return resolve_catalog_status(list(models))

    async def create_model(self, payload: ModelCreate) -> ModelResponse:
        capability_config = payload.capability_config.model_dump(mode="python")
        resolved_classes = _resolve_model_classes_for_capability(
            capability=payload.capability,
            path=payload.path,
            format=payload.format,
            classes=payload.classes,
            capability_config=capability_config,
        )
        async with self.session_factory() as session:
            model = Model(
                name=payload.name,
                version=payload.version,
                task=payload.task,
                path=payload.path,
                format=payload.format,
                capability=payload.capability,
                capability_config=capability_config,
                classes=resolved_classes,
                input_shape=payload.input_shape,
                sha256=payload.sha256,
                size_bytes=payload.size_bytes,
                license=payload.license,
            )
            session.add(model)
            await session.commit()
            await session.refresh(model)
        return _model_to_response(model)

    async def update_model(self, model_id: UUID, payload: ModelUpdate) -> ModelResponse:
        async with self.session_factory() as session:
            model = await session.get(Model, model_id)
            if model is None:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Model not found.",
                )
            update_data = payload.model_dump(exclude_unset=True, mode="python")
            if any(
                field_name in update_data
                for field_name in {"path", "format", "classes", "capability", "capability_config"}
            ):
                resolved_capability = update_data.get("capability", _model_capability(model))
                resolved_config = dict(
                    update_data.get("capability_config", model.capability_config or {})
                )
                resolved_format = update_data.get("format", model.format)
                declared_classes = (
                    update_data["classes"]
                    if "classes" in update_data
                    else None
                    if resolved_format is ModelFormat.ONNX
                    else list(model.classes)
                )
                if (
                    resolved_capability is DetectorCapability.OPEN_VOCAB
                    and "classes" not in update_data
                ):
                    declared_classes = list(model.classes)
                model.classes = _resolve_model_classes_for_capability(
                    capability=resolved_capability,
                    path=str(update_data.get("path", model.path)),
                    format=resolved_format,
                    classes=declared_classes,
                    capability_config=resolved_config,
                )
            for field_name, value in update_data.items():
                if field_name == "classes":
                    continue
                setattr(model, field_name, value)
            await session.commit()
            await session.refresh(model)
        return _model_to_response(model)


class CameraService:
    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession],
        settings: Settings,
        audit_logger: DatabaseAuditLogger,
        events: NatsJetStreamClient | None = None,
    ) -> None:
        self.session_factory = session_factory
        self.settings = settings
        self.audit_logger = audit_logger
        self.events = events
        self._setup_preview_cache: dict[UUID, _SetupPreviewCacheEntry] = {}
        self._setup_preview_lock = asyncio.Lock()

    async def list_cameras(
        self,
        tenant_context: TenantContext,
        *,
        site_id: UUID | None = None,
    ) -> list[CameraResponse]:
        async with self.session_factory() as session:
            statement = select(Camera).join(Site, Site.id == Camera.site_id).where(
                Site.tenant_id == tenant_context.tenant_id
            )
            if site_id is not None:
                statement = statement.where(Camera.site_id == site_id)
            statement = statement.order_by(Camera.name)
            cameras = (await session.execute(statement)).scalars().all()
        return [_camera_to_response(camera) for camera in cameras]

    async def get_camera(self, tenant_context: TenantContext, camera_id: UUID) -> CameraResponse:
        async with self.session_factory() as session:
            camera = await _load_camera(session, tenant_context.tenant_id, camera_id)
        return _camera_to_response(camera)

    async def get_worker_config(
        self,
        tenant_context: TenantContext,
        camera_id: UUID,
    ) -> WorkerConfigResponse:
        async with self.session_factory() as session:
            camera = await _load_camera(session, tenant_context.tenant_id, camera_id)
            primary_model = await _load_model(session, camera.primary_model_id)
            secondary_model = None
            if camera.secondary_model_id is not None:
                secondary_model = await _load_model(session, camera.secondary_model_id)
            runtime_artifacts = await _load_worker_runtime_artifacts(
                session=session,
                camera=camera,
                model=primary_model,
            )
            tenant = await session.get(Tenant, tenant_context.tenant_id)

        rtsp_url = decrypt_rtsp_url(camera.rtsp_url_encrypted, self.settings)
        recording_policy = _recording_policy_from_camera(camera)
        base_config = _camera_to_worker_config(
            camera=camera,
            primary_model=primary_model,
            secondary_model=secondary_model,
            settings=self.settings,
            rtsp_url=rtsp_url,
            runtime_artifacts=runtime_artifacts,
            recording_policy=recording_policy,
        )
        privacy_manifest = build_privacy_manifest(
            tenant_id=tenant_context.tenant_id,
            camera_id=camera.id,
            deployment_mode=camera.processing_mode.value,
            recording_policy=recording_policy,
            allow_plaintext_plates=bool(
                getattr(tenant, "anpr_store_plaintext", False)
            ),
            plaintext_justification=getattr(tenant, "anpr_plaintext_justification", None),
        )
        privacy_snapshot = await PrivacyManifestService(
            self.session_factory
        ).get_or_create_snapshot(
            tenant_id=tenant_context.tenant_id,
            camera_id=camera.id,
            manifest=privacy_manifest,
        )
        scene_contract = build_scene_contract(
            tenant_id=tenant_context.tenant_id,
            site_id=camera.site_id,
            camera_id=camera.id,
            camera_name=camera.name,
            camera_source=_camera_source_contract_payload(camera, rtsp_url),
            deployment_mode=camera.processing_mode.value,
            model=_model_contract_payload(primary_model),
            runtime_vocabulary=_runtime_vocabulary_contract_payload(camera),
            runtime_selection=_runtime_selection_contract_payload(
                primary_model,
                runtime_artifacts=runtime_artifacts,
            ),
            vision_profile=base_config.vision_profile.model_dump(mode="json"),
            detection_regions=[
                region.model_dump(mode="json") for region in base_config.detection_regions
            ],
            candidate_quality=base_config.vision_profile.candidate_quality,
            recording_policy=recording_policy,
            privacy_manifest_hash=privacy_snapshot.manifest_hash,
        )
        contract_snapshot = await SceneContractService(
            self.session_factory
        ).get_or_create_snapshot(
            tenant_id=tenant_context.tenant_id,
            camera_id=camera.id,
            contract=scene_contract,
        )
        return base_config.model_copy(
            update={
                "scene_contract_hash": contract_snapshot.contract_hash,
                "privacy_manifest_hash": privacy_snapshot.manifest_hash,
            }
        )

    async def probe_camera_source(
        self,
        tenant_context: TenantContext,
        payload: CameraSourceProbeRequest,
    ) -> CameraSourceProbeResponse:
        source_settings = _source_settings_from_payload(
            rtsp_url=payload.rtsp_url,
            camera_source=payload.camera_source,
        )

        requested_delivery = payload.browser_delivery or BrowserDeliverySettings()
        requested_privacy = (
            payload.privacy.model_dump(mode="python")
            if payload.privacy is not None
            else PrivacySettings().model_dump(mode="python")
        )
        existing_source_capability: SourceCapability | None = None
        source_capability: SourceCapability | None
        processing_mode = payload.processing_mode
        edge_node_id = payload.edge_node_id
        should_persist_probe = False

        if payload.camera_id is not None:
            async with self.session_factory() as session:
                camera = await _load_camera(session, tenant_context.tenant_id, payload.camera_id)
                processing_mode = camera.processing_mode
                edge_node_id = camera.edge_node_id
                supplied_source = source_settings is not None
                if payload.browser_delivery is None:
                    stored_browser_delivery = (
                        camera.browser_delivery
                        or BrowserDeliverySettings().model_dump(mode="python")
                    )
                    requested_delivery = BrowserDeliverySettings.model_validate(
                        stored_browser_delivery
                    )
                if payload.privacy is None:
                    requested_privacy = dict(camera.privacy)
                if camera.source_capability is not None:
                    existing_source_capability = SourceCapability.model_validate(
                        camera.source_capability
                    )

                if not supplied_source and existing_source_capability is not None:
                    source_capability = existing_source_capability
                else:
                    if source_settings is None:
                        source_settings = _camera_source_settings_from_camera(
                            camera,
                            rtsp_url=decrypt_rtsp_url(camera.rtsp_url_encrypted, self.settings),
                            for_worker=True,
                        )
                        should_persist_probe = True
                    normalized_source = normalize_camera_source(source_settings)
                    source_capability = await _probe_camera_source_capability(
                        normalized_source,
                        settings=self.settings,
                    )
                    if source_capability is None:
                        source_capability = existing_source_capability
                    elif should_persist_probe and not supplied_source:
                        camera.source_capability = source_capability.model_dump(mode="python")
                        await session.commit()
                        await session.refresh(camera)
        else:
            if source_settings is None:
                raise HTTPException(
                    status_code=HTTP_422_UNPROCESSABLE,
                    detail="rtsp_url or camera_source is required when camera_id is not provided.",
                )
            validate_camera_source_assignment(
                source=source_settings,
                processing_mode=processing_mode,
                edge_node_id=edge_node_id,
            )
            source_capability = await _probe_camera_source_capability(
                normalize_camera_source(source_settings),
                settings=self.settings,
            )

        privacy = _apply_tenant_privacy_policy(
            settings=self.settings,
            tenant_context=tenant_context,
            privacy=requested_privacy,
        )
        return CameraSourceProbeResponse(
            source_capability=source_capability,
            browser_delivery=_build_source_aware_browser_delivery(
                requested=requested_delivery,
                source_capability=source_capability,
                privacy=privacy,
                processing_mode=processing_mode,
                edge_node_id=edge_node_id,
                source_kind=(
                    source_settings.kind if source_settings is not None else CameraSourceKind.RTSP
                ),
            ),
        )

    async def get_setup_preview(
        self,
        tenant_context: TenantContext,
        camera_id: UUID,
        *,
        force_refresh: bool = False,
    ) -> CameraSetupPreviewResponse:
        async with self.session_factory() as session:
            camera = await _load_camera(session, tenant_context.tenant_id, camera_id)

        try:
            snapshot = await self._get_or_capture_setup_preview_snapshot(
                camera,
                force_refresh=force_refresh,
            )
        except RuntimeError as exc:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=(
                    "Unable to capture an analytics still from the camera source right now. "
                    "Retry the capture after confirming the camera stream is reachable."
                ),
            ) from exc
        return CameraSetupPreviewResponse(
            camera_id=camera.id,
            preview_url=(
                f"/api/v1/cameras/{camera.id}/setup-preview/image"
                f"?rev={int(snapshot.captured_at.timestamp() * 1000)}"
            ),
            frame_size=snapshot.frame_size,
            captured_at=snapshot.captured_at,
        )

    async def get_setup_preview_image(
        self,
        tenant_context: TenantContext,
        camera_id: UUID,
    ) -> _SetupPreviewSnapshot:
        async with self.session_factory() as session:
            camera = await _load_camera(session, tenant_context.tenant_id, camera_id)
        try:
            return await self._get_or_capture_setup_preview_snapshot(camera, force_refresh=False)
        except RuntimeError as exc:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=(
                    "Unable to load the analytics still for this camera right now. "
                    "Retry the capture after confirming the camera stream is reachable."
                ),
            ) from exc

    async def _get_or_capture_setup_preview_snapshot(
        self,
        camera: Camera,
        *,
        force_refresh: bool,
    ) -> _SetupPreviewSnapshot:
        now = datetime.now(tz=UTC)
        cached_entry = self._setup_preview_cache.get(camera.id)
        if (
            not force_refresh
            and cached_entry is not None
            and cached_entry.expires_at > now
            and cached_entry.camera_updated_at == camera.updated_at
        ):
            return cached_entry.snapshot

        async with self._setup_preview_lock:
            now = datetime.now(tz=UTC)
            cached_entry = self._setup_preview_cache.get(camera.id)
            if (
                not force_refresh
                and cached_entry is not None
                and cached_entry.expires_at > now
                and cached_entry.camera_updated_at == camera.updated_at
            ):
                return cached_entry.snapshot

            try:
                snapshot = await asyncio.to_thread(
                    _capture_setup_preview_snapshot,
                    camera,
                    self.settings,
                )
            except RuntimeError:
                if cached_entry is not None and cached_entry.camera_updated_at == camera.updated_at:
                    logger.warning(
                        "Setup preview refresh failed; reusing cached still for camera %s",
                        camera.id,
                    )
                    return cached_entry.snapshot
                raise
            self._setup_preview_cache[camera.id] = _SetupPreviewCacheEntry(
                snapshot=snapshot,
                camera_updated_at=camera.updated_at,
                expires_at=now + _SETUP_PREVIEW_CACHE_TTL,
            )
            return snapshot

    async def create_camera(
        self,
        tenant_context: TenantContext,
        payload: CameraCreate,
    ) -> CameraResponse:
        async with self.session_factory() as session:
            await _load_site(session, tenant_context.tenant_id, payload.site_id)
            primary_model = await _load_model(session, payload.primary_model_id)
            if primary_model.task is not ModelTask.DETECT:
                raise HTTPException(
                    status_code=HTTP_422_UNPROCESSABLE,
                    detail="Primary model must be a detector.",
                )
            active_classes, runtime_vocabulary = _resolve_camera_detector_state(
                active_classes=payload.active_classes,
                runtime_vocabulary=payload.runtime_vocabulary,
                primary_model=primary_model,
            )
            if payload.secondary_model_id is not None:
                secondary_model = await _load_model(session, payload.secondary_model_id)
                if secondary_model.task not in {ModelTask.ATTRIBUTE, ModelTask.CLASSIFY}:
                    raise HTTPException(
                        status_code=HTTP_422_UNPROCESSABLE,
                        detail="Secondary model must be classify or attribute.",
                    )
            source_settings = _source_settings_from_payload(
                rtsp_url=payload.rtsp_url,
                camera_source=payload.camera_source,
            )
            if source_settings is None:
                raise HTTPException(
                    status_code=HTTP_422_UNPROCESSABLE,
                    detail="Either rtsp_url or camera_source is required.",
                )
            validate_camera_source_assignment(
                source=source_settings,
                processing_mode=payload.processing_mode,
                edge_node_id=payload.edge_node_id,
            )
            normalized_source = normalize_camera_source(source_settings)
            privacy = _apply_tenant_privacy_policy(
                settings=self.settings,
                tenant_context=tenant_context,
                privacy=payload.privacy.model_dump(mode="python"),
            )
            source_capability = await _probe_camera_source_capability(
                normalized_source,
                settings=self.settings,
            )
            browser_delivery = _build_source_aware_browser_delivery(
                requested=payload.browser_delivery,
                source_capability=source_capability,
                privacy=privacy,
                processing_mode=payload.processing_mode,
                edge_node_id=payload.edge_node_id,
                source_kind=normalized_source.kind,
            )
            camera = Camera(
                site_id=payload.site_id,
                edge_node_id=payload.edge_node_id,
                name=payload.name,
                rtsp_url_encrypted=encrypt_rtsp_url(normalized_source.uri, self.settings),
                source_kind=normalized_source.kind.value,
                source_config=_source_config_payload(normalized_source),
                processing_mode=payload.processing_mode,
                primary_model_id=payload.primary_model_id,
                secondary_model_id=payload.secondary_model_id,
                tracker_type=payload.tracker_type,
                active_classes=active_classes,
                runtime_vocabulary=runtime_vocabulary.terms,
                runtime_vocabulary_source=runtime_vocabulary.source,
                runtime_vocabulary_version=runtime_vocabulary.version,
                runtime_vocabulary_updated_at=runtime_vocabulary.updated_at,
                attribute_rules=payload.attribute_rules,
                zones=_normalize_zones_payload(
                    [zone.model_dump(mode="python") for zone in payload.zones]
                ),
                vision_profile=payload.vision_profile.model_dump(mode="python"),
                detection_regions=_camera_detection_regions_payload(payload.detection_regions),
                homography=(
                    payload.homography.model_dump(mode="python")
                    if payload.homography is not None
                    else None
                ),
                privacy=privacy,
                browser_delivery=browser_delivery.model_dump(mode="python"),
                source_capability=(
                    source_capability.model_dump(mode="python")
                    if source_capability is not None
                    else None
                ),
                evidence_recording_policy=payload.recording_policy.model_dump(
                    mode="python"
                ),
                frame_skip=payload.frame_skip,
                fps_cap=payload.fps_cap,
            )
            session.add(camera)
            if _model_capability(primary_model) is DetectorCapability.OPEN_VOCAB:
                _record_camera_vocabulary_snapshot(
                    session=session,
                    camera=camera,
                    runtime_vocabulary=runtime_vocabulary,
                )
            await session.commit()
            await session.refresh(camera)
        await self.audit_logger.record(
            tenant_context=tenant_context,
            action="camera.create",
            target=f"camera:{camera.id}",
            meta={"name": camera.name},
        )
        return _camera_to_response(camera)

    async def update_camera(
        self,
        tenant_context: TenantContext,
        camera_id: UUID,
        payload: CameraUpdate,
    ) -> CameraResponse:
        async with self.session_factory() as session:
            camera = await _load_camera(session, tenant_context.tenant_id, camera_id)
            update_data = payload.model_dump(exclude_unset=True, mode="python")
            runtime_vocabulary_was_provided = "runtime_vocabulary" in update_data
            primary_model_id = update_data.get("primary_model_id", camera.primary_model_id)
            primary_model_changed = primary_model_id != camera.primary_model_id
            primary_model = await _load_model(session, primary_model_id)
            if primary_model.task is not ModelTask.DETECT:
                raise HTTPException(
                    status_code=HTTP_422_UNPROCESSABLE,
                    detail="Primary model must be a detector.",
                )
            active_classes = update_data.get("active_classes", camera.active_classes)
            runtime_vocabulary_payload = (
                RuntimeVocabularyState.model_validate(update_data["runtime_vocabulary"])
                if "runtime_vocabulary" in update_data
                else _runtime_vocabulary_state_from_camera(camera)
            )
            active_classes, runtime_vocabulary = _resolve_camera_detector_state(
                active_classes=active_classes,
                runtime_vocabulary=runtime_vocabulary_payload,
                primary_model=primary_model,
            )
            update_data["active_classes"] = active_classes
            update_data["runtime_vocabulary"] = runtime_vocabulary.terms
            update_data["runtime_vocabulary_source"] = runtime_vocabulary.source
            update_data["runtime_vocabulary_version"] = runtime_vocabulary.version
            update_data["runtime_vocabulary_updated_at"] = runtime_vocabulary.updated_at
            if update_data.get("secondary_model_id") is not None:
                secondary_model = await _load_model(session, update_data["secondary_model_id"])
                if secondary_model.task not in {ModelTask.ATTRIBUTE, ModelTask.CLASSIFY}:
                    raise HTTPException(
                        status_code=HTTP_422_UNPROCESSABLE,
                        detail="Secondary model must be classify or attribute.",
                    )
            if "site_id" in update_data:
                await _load_site(session, tenant_context.tenant_id, update_data["site_id"])
            source_capability_changed = False
            source_settings = _source_settings_from_update(camera, update_data)
            if source_settings is not None:
                update_data.pop("rtsp_url", None)
                update_data.pop("camera_source", None)
                normalized_source = normalize_camera_source(source_settings)
                validate_camera_source_assignment(
                    source=source_settings,
                    processing_mode=update_data.get("processing_mode", camera.processing_mode),
                    edge_node_id=update_data.get("edge_node_id", camera.edge_node_id),
                )
                camera.rtsp_url_encrypted = encrypt_rtsp_url(normalized_source.uri, self.settings)
                update_data["source_kind"] = normalized_source.kind.value
                update_data["source_config"] = _source_config_payload(normalized_source)
                source_capability = await _probe_camera_source_capability(
                    normalized_source,
                    settings=self.settings,
                )
                update_data["source_capability"] = (
                    source_capability.model_dump(mode="python")
                    if source_capability is not None
                    else None
                )
                source_capability_changed = True
            if "privacy" in update_data:
                update_data["privacy"] = _apply_tenant_privacy_policy(
                    settings=self.settings,
                    tenant_context=tenant_context,
                    privacy=dict(update_data["privacy"]),
                )
            if (
                ("browser_delivery" in update_data and update_data["browser_delivery"] is not None)
                or "privacy" in update_data
                or source_capability_changed
            ):
                requested_delivery = BrowserDeliverySettings.model_validate(
                    update_data.get(
                        "browser_delivery",
                        camera.browser_delivery
                        or BrowserDeliverySettings().model_dump(mode="python"),
                    )
                )
                source_payload = update_data.get("source_capability", camera.source_capability)
                update_data["browser_delivery"] = _build_source_aware_browser_delivery(
                    requested=requested_delivery,
                    source_capability=(
                        SourceCapability.model_validate(source_payload)
                        if source_payload is not None
                        else None
                    ),
                    privacy=dict(update_data.get("privacy", camera.privacy)),
                    processing_mode=update_data.get(
                        "processing_mode",
                        camera.processing_mode,
                    ),
                    edge_node_id=update_data.get("edge_node_id", camera.edge_node_id),
                    source_kind=_source_kind_from_update(camera, update_data),
                ).model_dump(mode="python")
            if "homography" in update_data and update_data["homography"] is not None:
                update_data["homography"] = dict(update_data["homography"])
            if "zones" in update_data and update_data["zones"] is not None:
                update_data["zones"] = _normalize_zones_payload(update_data["zones"])
            if "detection_regions" in update_data and update_data["detection_regions"] is not None:
                update_data["detection_regions"] = _camera_detection_regions_payload(
                    payload.detection_regions or []
                )
            if "recording_policy" in update_data:
                recording_policy = update_data.pop("recording_policy")
                if recording_policy is not None:
                    update_data["evidence_recording_policy"] = (
                        EvidenceRecordingPolicy.model_validate(
                            recording_policy
                        ).model_dump(mode="python")
                    )
            _validate_effective_camera_motion_metrics(camera, update_data)

            for field_name, value in update_data.items():
                setattr(camera, field_name, value)

            if (
                _model_capability(primary_model) is DetectorCapability.OPEN_VOCAB
                and (runtime_vocabulary_was_provided or primary_model_changed)
            ):
                _record_camera_vocabulary_snapshot(
                    session=session,
                    camera=camera,
                    runtime_vocabulary=runtime_vocabulary,
                )
            await session.commit()
            await session.refresh(camera)
        await self.audit_logger.record(
            tenant_context=tenant_context,
            action="camera.update",
            target=f"camera:{camera.id}",
            meta=payload.model_dump(exclude_unset=True, mode="json"),
        )
        await self._publish_camera_command(camera)
        return _camera_to_response(camera)

    async def delete_camera(self, tenant_context: TenantContext, camera_id: UUID) -> None:
        async with self.session_factory() as session:
            camera = await _load_camera(session, tenant_context.tenant_id, camera_id)
            await session.delete(camera)
            await session.commit()
        await self.audit_logger.record(
            tenant_context=tenant_context,
            action="camera.delete",
            target=f"camera:{camera_id}",
        )

    async def _publish_camera_command(self, camera: Camera) -> None:
        if self.events is None:
            return
        runtime_vocabulary = _runtime_vocabulary_state_from_camera(camera)
        command = CameraCommandPayload(
            active_classes=list(camera.active_classes),
            runtime_vocabulary=runtime_vocabulary.terms,
            runtime_vocabulary_source=runtime_vocabulary.source,
            runtime_vocabulary_version=runtime_vocabulary.version,
            tracker_type=camera.tracker_type,
            privacy=_worker_privacy_settings(camera.privacy),
            stream=_resolve_worker_stream_settings(
                browser_delivery=BrowserDeliverySettings.model_validate(
                    camera.browser_delivery
                    or BrowserDeliverySettings().model_dump(mode="python")
                ),
                fps_cap=int(camera.fps_cap or 25),
            ),
            attribute_rules=list(camera.attribute_rules),
            zones=cast(Any, [_worker_zone_payload(zone) for zone in camera.zones]),
            vision_profile=SceneVisionProfile.model_validate(camera.vision_profile or {}),
            detection_regions=[
                DetectionRegion.model_validate(_worker_detection_region_payload(region))
                for region in (camera.detection_regions or [])
            ],
            homography=_homography_to_worker_payload(camera.homography),
        )
        try:
            await self.events.publish(f"cmd.camera.{camera.id}", command)
        except Exception:
            logger.exception("Failed to publish camera command update for camera %s", camera.id)


class EdgeService:
    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession],
        settings: Settings,
        events: NatsJetStreamClient,
        audit_logger: DatabaseAuditLogger,
    ) -> None:
        self.session_factory = session_factory
        self.settings = settings
        self.events = events
        self.audit_logger = audit_logger

    async def register_edge_node(
        self,
        tenant_context: TenantContext,
        payload: EdgeRegisterRequest,
    ) -> EdgeRegisterResponse:
        async with self.session_factory() as session:
            site = await _load_site(session, tenant_context.tenant_id, payload.site_id)
            api_key_plaintext = _generate_secret("edge")
            nats_seed = _generate_secret("nats")
            edge_node = EdgeNode(
                site_id=site.id,
                hostname=payload.hostname,
                public_key=nats_seed,
                version=payload.version,
                last_seen_at=datetime.now(tz=UTC),
            )
            api_key = APIKey(
                tenant_id=tenant_context.tenant_id,
                name=f"edge:{payload.hostname}",
                hashed_key=hash_api_key(api_key_plaintext),
                scope={"paths": ["/api/v1/edge/*"]},
                expires_at=None,
            )
            session.add(edge_node)
            session.add(api_key)
            await session.commit()
            await session.refresh(edge_node)

        await self.audit_logger.record(
            tenant_context=tenant_context,
            action="edge.register",
            target=f"edge:{edge_node.id}",
            meta={"site_id": str(site.id), "hostname": payload.hostname},
        )
        return EdgeRegisterResponse(
            edge_node_id=edge_node.id,
            api_key=api_key_plaintext,
            nats_nkey_seed=nats_seed,
            subjects=[
                f"evt.tracking.{edge_node.id}",
                f"edge.heartbeat.{edge_node.id}",
            ],
            mediamtx_url=self.settings.mediamtx_url,
            mediamtx_username=self.settings.mediamtx_username,
            mediamtx_password=(
                self.settings.mediamtx_password.get_secret_value()
                if self.settings.mediamtx_password is not None
                else None
            ),
            overlay_network_hints={
                "nats_url": self.settings.nats_url,
                "mediamtx_rtsp": self.settings.mediamtx_rtsp_base_url,
            },
        )

    async def ingest_telemetry(self, payload: TelemetryEnvelope) -> dict[str, int]:
        inserted = 0
        async with self.session_factory() as session:
            for frame in payload.events:
                rows = []
                for track in frame.tracks:
                    rows.append(
                        {
                            "id": uuid.uuid5(
                                uuid.NAMESPACE_URL,
                                f"{frame.camera_id}:{frame.ts.isoformat()}:{track.track_id}",
                            ),
                            "ts": frame.ts,
                            "camera_id": frame.camera_id,
                            "class_name": track.class_name,
                            "track_id": track.track_id,
                            "confidence": track.confidence,
                            "speed_kph": track.speed_kph,
                            "direction_deg": track.direction_deg,
                            "zone_id": track.zone_id,
                            "attributes": track.attributes,
                            "bbox": track.bbox,
                        }
                    )
                if rows:
                    statement = insert(TrackingEvent).values(rows)
                    returning_statement = statement.on_conflict_do_nothing(
                        index_elements=["id", "ts"]
                    ).returning(TrackingEvent.id)
                    result = await session.execute(returning_statement)
                    inserted += len(result.scalars().all())
                await self.events.publish(f"evt.tracking.{frame.camera_id}", frame)
            await session.commit()
        return {"inserted": inserted}

    async def record_heartbeat(self, payload: EdgeHeartbeatRequest) -> EdgeHeartbeatResponse:
        async with self.session_factory() as session:
            await session.execute(
                update(EdgeNode)
                .where(EdgeNode.id == payload.node_id)
                .values(last_seen_at=datetime.now(tz=UTC), version=payload.version)
            )
            await session.commit()
        return EdgeHeartbeatResponse(status="ok", received_at=datetime.now(tz=UTC))


class OperationsService:
    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession],
        settings: Settings,
        edge_service: EdgeService | None = None,
    ) -> None:
        self.session_factory = session_factory
        self.settings = settings
        self.edge_service = edge_service

    async def get_fleet_overview(self, tenant_context: TenantContext) -> FleetOverviewResponse:
        now = datetime.now(tz=UTC)
        async with self.session_factory() as session:
            edge_rows = (
                await session.execute(
                    select(EdgeNode, Site)
                    .join(Site, Site.id == EdgeNode.site_id)
                    .where(Site.tenant_id == tenant_context.tenant_id)
                    .order_by(EdgeNode.hostname)
                )
            ).all()
            camera_rows = (
                await session.execute(
                    select(Camera, Site)
                    .join(Site, Site.id == Camera.site_id)
                    .where(Site.tenant_id == tenant_context.tenant_id)
                    .order_by(Camera.name)
                )
            ).all()

        edge_by_id = {edge.id: edge for edge, _site in edge_rows}
        assigned_camera_ids: dict[UUID, list[UUID]] = {edge.id: [] for edge, _site in edge_rows}
        for camera, _site in camera_rows:
            if camera.edge_node_id in assigned_camera_ids:
                assigned_camera_ids[camera.edge_node_id].append(camera.id)

        nodes: list[FleetNodeSummary] = [
            FleetNodeSummary(
                id=None,
                kind="central",
                hostname="central",
                status=FleetNodeStatus.UNKNOWN,
                assigned_camera_ids=[
                    camera.id
                    for camera, _site in camera_rows
                    if camera.edge_node_id is None
                    and camera.processing_mode in {ProcessingMode.CENTRAL, ProcessingMode.HYBRID}
                ],
            )
        ]
        for edge, site in edge_rows:
            node_status = _fleet_node_status(edge.last_seen_at, now)
            nodes.append(
                FleetNodeSummary(
                    id=edge.id,
                    kind="edge",
                    hostname=edge.hostname,
                    site_id=site.id,
                    status=node_status,
                    version=edge.version,
                    last_seen_at=edge.last_seen_at,
                    assigned_camera_ids=assigned_camera_ids.get(edge.id, []),
                    reported_camera_count=None,
                )
            )

        camera_workers: list[FleetCameraWorkerSummary] = []
        delivery_diagnostics: list[FleetDeliveryDiagnostic] = []
        for camera, site in camera_rows:
            desired, runtime, owner, detail = _derive_worker_lifecycle(
                camera=camera,
                edge_by_id=edge_by_id,
                now=now,
            )
            camera_workers.append(
                FleetCameraWorkerSummary(
                    camera_id=camera.id,
                    camera_name=camera.name,
                    site_id=site.id,
                    node_id=camera.edge_node_id,
                    node_hostname=(
                        edge_by_id[camera.edge_node_id].hostname
                        if camera.edge_node_id in edge_by_id
                        else None
                    ),
                    processing_mode=camera.processing_mode,
                    desired_state=desired,
                    runtime_status=runtime,
                    lifecycle_owner=owner,
                    dev_run_command=(
                        _central_dev_run_command(camera.id) if owner == "manual_dev" else None
                    ),
                    detail=detail,
                )
            )
            delivery_diagnostics.append(_camera_delivery_diagnostic(camera))

        summary = FleetSummary(
            desired_workers=sum(
                1
                for worker in camera_workers
                if worker.desired_state
                in {
                    WorkerDesiredState.DESIRED,
                    WorkerDesiredState.MANUAL,
                    WorkerDesiredState.SUPERVISED,
                }
            ),
            running_workers=sum(
                1
                for worker in camera_workers
                if worker.runtime_status == WorkerRuntimeStatus.RUNNING
            ),
            stale_nodes=sum(1 for node in nodes if node.status == FleetNodeStatus.STALE),
            offline_nodes=sum(1 for node in nodes if node.status == FleetNodeStatus.OFFLINE),
            native_unavailable_cameras=sum(
                1
                for diagnostic in delivery_diagnostics
                if diagnostic.native_status.available is False
            ),
        )
        return FleetOverviewResponse(
            mode=FleetLifecycleMode.MANUAL_DEV,
            generated_at=now,
            summary=summary,
            nodes=nodes,
            camera_workers=camera_workers,
            delivery_diagnostics=delivery_diagnostics,
        )

    async def create_bootstrap_material(
        self,
        tenant_context: TenantContext,
        payload: FleetBootstrapRequest,
    ) -> FleetBootstrapResponse:
        if self.edge_service is None:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Edge registration service is unavailable.",
            )
        edge_response = await self.edge_service.register_edge_node(
            tenant_context,
            EdgeRegisterRequest(
                site_id=payload.site_id,
                hostname=payload.hostname,
                version=payload.version,
            ),
        )
        return FleetBootstrapResponse(
            **edge_response.model_dump(),
            dev_compose_command=_edge_dev_compose_command(edge_response.edge_node_id),
            supervisor_environment={
                "ARGUS_API_BASE_URL": self.settings.api_base_url,
                "ARGUS_EDGE_NODE_ID": str(edge_response.edge_node_id),
                "ARGUS_EDGE_API_KEY": edge_response.api_key,
            },
        )


class HistoryService:
    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self.session_factory = session_factory

    async def query_history(
        self,
        tenant_context: TenantContext,
        *,
        camera_ids: list[UUID] | None,
        class_names: list[str] | None,
        granularity: str,
        starts_at: datetime,
        ends_at: datetime,
        metric: HistoryMetric = HistoryMetric.OCCUPANCY,
    ) -> list[HistoryPoint]:
        _ensure_history_window(starts_at, ends_at)
        await self._ensure_camera_access(tenant_context, camera_ids)
        rows = await self._fetch_history_rows(
            tenant_id=tenant_context.tenant_id,
            camera_ids=camera_ids,
            class_names=class_names,
            granularity=granularity,
            starts_at=starts_at,
            ends_at=ends_at,
            metric=metric,
        )
        return [
            HistoryPoint(
                bucket=row["bucket"],
                camera_id=row["camera_id"],
                class_name=row["class_name"],
                event_count=int(row["event_count"]),
                granularity=granularity,
                metric=metric,
            )
            for row in rows
        ]

    async def query_series(
        self,
        tenant_context: TenantContext,
        *,
        camera_ids: list[UUID] | None,
        class_names: list[str] | None,
        granularity: str,
        starts_at: datetime,
        ends_at: datetime,
        metric: HistoryMetric = HistoryMetric.OCCUPANCY,
        include_speed: bool = False,
        speed_threshold: float | None = None,
    ) -> HistorySeriesResponse:
        _ensure_history_window(starts_at, ends_at)
        await self._ensure_camera_access(tenant_context, camera_ids)

        effective_granularity, granularity_adjusted = _effective_granularity(
            granularity,
            starts_at=starts_at,
            ends_at=ends_at,
        )

        # Coverage needs unfiltered class evidence so selected-class empty buckets can
        # be distinguished from buckets with no telemetry.
        fetch_class_names: list[str] | None = None

        if metric is HistoryMetric.COUNT_EVENTS:
            if include_speed:
                rows = await self._fetch_series_rows_with_speed_from_count_events(
                    tenant_id=tenant_context.tenant_id,
                    camera_ids=camera_ids,
                    class_names=fetch_class_names,
                    granularity=effective_granularity,
                    starts_at=starts_at,
                    ends_at=ends_at,
                    speed_threshold=speed_threshold,
                )
            elif _history_window_aligned_to_granularity(
                starts_at,
                ends_at,
                effective_granularity,
            ):
                rows = await self._fetch_series_rows_aggregate(
                    tenant_id=tenant_context.tenant_id,
                    camera_ids=camera_ids,
                    class_names=fetch_class_names,
                    granularity=effective_granularity,
                    starts_at=starts_at,
                    ends_at=ends_at,
                    metric=metric,
                )
            else:
                rows = await self._fetch_series_rows_from_count_events(
                    tenant_id=tenant_context.tenant_id,
                    camera_ids=camera_ids,
                    class_names=fetch_class_names,
                    granularity=effective_granularity,
                    starts_at=starts_at,
                    ends_at=ends_at,
                )
        elif include_speed:
            rows = await self._fetch_series_rows_with_speed(
                tenant_id=tenant_context.tenant_id,
                camera_ids=camera_ids,
                class_names=fetch_class_names,
                granularity=effective_granularity,
                starts_at=starts_at,
                ends_at=ends_at,
                metric=metric,
                speed_threshold=speed_threshold,
            )
        else:
            rows = await self._fetch_series_rows_from_events(
                tenant_id=tenant_context.tenant_id,
                camera_ids=camera_ids,
                class_names=fetch_class_names,
                granularity=effective_granularity,
                starts_at=starts_at,
                ends_at=ends_at,
                metric=metric,
            )

        buckets: dict[datetime, dict[str, int]] = {}
        speed_p50: dict[datetime, dict[str, float]] = {}
        speed_p95: dict[datetime, dict[str, float]] = {}
        speed_samples: dict[datetime, dict[str, int]] = {}
        violations: dict[datetime, dict[str, int]] = {}
        class_event_counts: dict[str, int] = {}
        class_has_speed: set[str] = set()
        ordered_classes: list[str] = []
        seen_classes: set[str] = set()

        for row in rows:
            bucket = cast(datetime, row["bucket"])
            class_name = cast(str, row["class_name"])
            event_count = int(row["event_count"])
            buckets.setdefault(bucket, {})[class_name] = event_count
            class_event_counts[class_name] = class_event_counts.get(class_name, 0) + event_count

            if class_name not in seen_classes:
                seen_classes.add(class_name)
                ordered_classes.append(class_name)

            if include_speed:
                p50 = row.get("speed_p50")
                p95 = row.get("speed_p95")
                sample_count = int(row.get("speed_sample_count") or 0)
                if sample_count > 0:
                    class_has_speed.add(class_name)
                    if p50 is not None:
                        speed_p50.setdefault(bucket, {})[class_name] = float(p50)
                    if p95 is not None:
                        speed_p95.setdefault(bucket, {})[class_name] = float(p95)
                    speed_samples.setdefault(bucket, {})[class_name] = sample_count
                if speed_threshold is not None and row.get("over_threshold_count") is not None:
                    violations.setdefault(bucket, {})[class_name] = int(
                        row["over_threshold_count"]
                    )

        if class_names:
            selected_classes = list(class_names)
        else:
            selected_classes = ordered_classes

        speed_classes_capped = False
        speed_classes_used: list[str] | None = None
        if include_speed:
            eligible = [c for c in selected_classes if c in class_has_speed]
            eligible_sorted = sorted(
                eligible,
                key=lambda c: class_event_counts.get(c, 0),
                reverse=True,
            )
            if len(eligible_sorted) > _MAX_SPEED_CLASSES:
                speed_classes_capped = True
                speed_classes_used = eligible_sorted[:_MAX_SPEED_CLASSES]
            else:
                speed_classes_used = eligible_sorted

        def _project_speed(
            source: dict[datetime, dict[str, float]],
            bucket: datetime,
        ) -> dict[str, float] | None:
            if not include_speed:
                return None
            chosen = speed_classes_used or []
            per_bucket = source.get(bucket, {})
            return {c: per_bucket[c] for c in chosen if c in per_bucket}

        def _project_int(
            source: dict[datetime, dict[str, int]],
            bucket: datetime,
        ) -> dict[str, int] | None:
            if not include_speed:
                return None
            chosen = speed_classes_used or []
            per_bucket = source.get(bucket, {})
            return {c: per_bucket[c] for c in chosen if c in per_bucket}

        result_rows: list[HistorySeriesRow] = []
        coverage_by_bucket: list[HistoryBucketCoverage] = []
        materialized_buckets = _history_bucket_range(
            starts_at,
            ends_at,
            effective_granularity,
        )
        for bucket in materialized_buckets:
            values = buckets.get(bucket, {})
            projected_values = {c: values.get(c, 0) for c in selected_classes}
            total_count = sum(projected_values.values())
            if not selected_classes and values:
                total_count = sum(values.values())
            if total_count > 0:
                status = HistoryCoverageStatus.POPULATED
            elif values:
                status = HistoryCoverageStatus.ZERO
            else:
                status = HistoryCoverageStatus.NO_TELEMETRY
            series_row = HistorySeriesRow(
                bucket=bucket,
                values=projected_values,
                total_count=total_count,
                speed_p50=_project_speed(speed_p50, bucket),
                speed_p95=_project_speed(speed_p95, bucket),
                speed_sample_count=_project_int(speed_samples, bucket),
                over_threshold_count=(
                    _project_int(violations, bucket) if speed_threshold is not None else None
                ),
            )
            result_rows.append(series_row)
            coverage_by_bucket.append(HistoryBucketCoverage(bucket=bucket, status=status))

        coverage_status = _summarize_history_coverage(coverage_by_bucket)

        return HistorySeriesResponse(
            granularity=effective_granularity,
            metric=metric,
            class_names=selected_classes,
            rows=result_rows,
            granularity_adjusted=granularity_adjusted,
            speed_classes_capped=speed_classes_capped,
            speed_classes_used=speed_classes_used if include_speed else None,
            effective_from=starts_at,
            effective_to=ends_at,
            bucket_count=len(materialized_buckets),
            bucket_span=effective_granularity,
            coverage_status=coverage_status,
            coverage_by_bucket=coverage_by_bucket,
        )

    async def list_classes(
        self,
        tenant_context: TenantContext,
        *,
        camera_ids: list[UUID] | None,
        starts_at: datetime,
        ends_at: datetime,
        metric: HistoryMetric = HistoryMetric.OCCUPANCY,
    ) -> HistoryClassesResponse:
        _ensure_history_window(starts_at, ends_at)
        await self._ensure_camera_access(tenant_context, camera_ids)

        if metric is HistoryMetric.COUNT_EVENTS:
            rows = await self._fetch_class_rows_from_count_events(
                tenant_id=tenant_context.tenant_id,
                camera_ids=camera_ids,
                starts_at=starts_at,
                ends_at=ends_at,
            )
            boundaries = await self._fetch_count_event_boundary_summaries(
                tenant_id=tenant_context.tenant_id,
                camera_ids=camera_ids,
                starts_at=starts_at,
                ends_at=ends_at,
            )
        else:
            rows = await self._fetch_class_rows_from_tracking_events(
                tenant_id=tenant_context.tenant_id,
                camera_ids=camera_ids,
                starts_at=starts_at,
                ends_at=ends_at,
                metric=metric,
            )
            boundaries = []

        return HistoryClassesResponse.model_validate(
            {
                "from": starts_at,
                "to": ends_at,
                "metric": metric,
                "boundaries": boundaries,
                "classes": [
                    {
                        "class_name": row["class_name"],
                        "event_count": int(row["event_count"]),
                        "has_speed_data": bool(row["has_speed_data"]),
                    }
                    for row in rows
                ],
            }
        )

    async def export_history(
        self,
        tenant_context: TenantContext,
        *,
        camera_ids: list[UUID] | None,
        class_names: list[str] | None,
        granularity: str,
        starts_at: datetime,
        ends_at: datetime,
        format_name: str,
        metric: HistoryMetric = HistoryMetric.OCCUPANCY,
    ) -> ExportArtifact:
        series = await self.query_series(
            tenant_context,
            camera_ids=camera_ids,
            class_names=class_names,
            granularity=granularity,
            starts_at=starts_at,
            ends_at=ends_at,
            metric=metric,
        )
        rows = _series_response_to_history_points(series)
        if format_name == "parquet":
            return ExportArtifact(
                filename="history.parquet",
                media_type="application/x-parquet",
                content=_serialize_parquet(rows),
            )
        return ExportArtifact(
            filename="history.csv",
            media_type="text/csv; charset=utf-8",
            content=_serialize_csv(rows),
        )

    async def _ensure_camera_access(
        self,
        tenant_context: TenantContext,
        camera_ids: list[UUID] | None,
    ) -> None:
        if not camera_ids:
            return
        async with self.session_factory() as session:
            for camera_id in camera_ids:
                await _load_camera(session, tenant_context.tenant_id, camera_id)

    async def _fetch_history_rows(
        self,
        *,
        tenant_id: UUID | None = None,
        camera_ids: list[UUID] | None,
        class_names: list[str] | None,
        granularity: str,
        starts_at: datetime,
        ends_at: datetime,
        metric: HistoryMetric = HistoryMetric.OCCUPANCY,
    ) -> list[dict[str, Any]]:
        interval = _GRANULARITY_INTERVAL[granularity]
        parameters: dict[str, Any] = {
            "starts_at": starts_at,
            "ends_at": ends_at,
        }
        filters = _history_camera_filters(
            parameters,
            tenant_id=tenant_id,
            camera_ids=camera_ids,
        )
        if class_names:
            filters.append("AND class_name IN :class_names")
            parameters["class_names"] = class_names

        if metric is HistoryMetric.COUNT_EVENTS:
            statement = text(
                f"""
                SELECT
                  time_bucket(INTERVAL '{interval}', ts) AS bucket,
                  camera_id,
                  class_name,
                  count(*)::bigint AS event_count
                FROM count_events
                WHERE ts >= :starts_at
                  AND ts < :ends_at
                  {' '.join(filters)}
                GROUP BY 1, 2, 3
                ORDER BY 1 ASC, 3 ASC, 2 ASC
                """
            )
        elif metric is HistoryMetric.OCCUPANCY:
            statement = text(
                f"""
                WITH active_by_ts AS (
                  SELECT
                    time_bucket(INTERVAL '{interval}', ts) AS bucket,
                    camera_id,
                    class_name,
                    ts,
                    count(*)::bigint AS active_count
                  FROM tracking_events
                  WHERE ts >= :starts_at
                    AND ts < :ends_at
                    {' '.join(filters)}
                  GROUP BY 1, 2, 3, 4
                )
                SELECT
                  bucket,
                  camera_id,
                  class_name,
                  MAX(active_count)::bigint AS event_count
                FROM active_by_ts
                GROUP BY 1, 2, 3
                ORDER BY 1 ASC, 3 ASC, 2 ASC
                """
            )
        else:
            count_expr = (
                "count(*)::bigint"
            )
            statement = text(
                f"""
                SELECT
                  time_bucket(INTERVAL '{interval}', ts) AS bucket,
                  camera_id,
                  class_name,
                  {count_expr} AS event_count
                FROM tracking_events
                WHERE ts >= :starts_at
                  AND ts < :ends_at
                  {' '.join(filters)}
                GROUP BY 1, 2, 3
                  ORDER BY 1 ASC, 3 ASC, 2 ASC
                """
            )
        if camera_ids:
            statement = statement.bindparams(bindparam("camera_ids", expanding=True))
        if class_names:
            statement = statement.bindparams(bindparam("class_names", expanding=True))

        async with self.session_factory() as session:
            rows = (await session.execute(statement, parameters)).mappings().all()
        return [dict(row) for row in rows]

    async def _fetch_series_rows_aggregate(
        self,
        *,
        tenant_id: UUID | None = None,
        camera_ids: list[UUID] | None,
        class_names: list[str] | None,
        granularity: str,
        starts_at: datetime,
        ends_at: datetime,
        metric: HistoryMetric = HistoryMetric.COUNT_EVENTS,
    ) -> list[dict[str, Any]]:
        if metric is HistoryMetric.COUNT_EVENTS:
            view_name, bucket_expr = _count_event_view_and_bucket_expr(granularity)
        else:
            view_name, bucket_expr = _history_view_and_bucket_expr(granularity)
        parameters: dict[str, Any] = {
            "starts_at": starts_at,
            "ends_at": ends_at,
        }
        filters = _history_camera_filters(
            parameters,
            tenant_id=tenant_id,
            camera_ids=camera_ids,
        )
        if class_names:
            filters.append("AND class_name IN :class_names")
            parameters["class_names"] = class_names

        statement = text(
            f"""
            SELECT
              {bucket_expr} AS bucket,
              class_name,
              SUM(event_count)::bigint AS event_count
            FROM {view_name}
            WHERE bucket >= :starts_at
              AND bucket < :ends_at
              {' '.join(filters)}
            GROUP BY 1, 2
            ORDER BY 1 ASC, 2 ASC
            """
        )
        if camera_ids:
            statement = statement.bindparams(bindparam("camera_ids", expanding=True))
        if class_names:
            statement = statement.bindparams(bindparam("class_names", expanding=True))

        async with self.session_factory() as session:
            rows = (await session.execute(statement, parameters)).mappings().all()
        return [dict(row) for row in rows]

    async def _fetch_series_rows_from_events(
        self,
        *,
        tenant_id: UUID | None = None,
        camera_ids: list[UUID] | None,
        class_names: list[str] | None,
        granularity: str,
        starts_at: datetime,
        ends_at: datetime,
        metric: HistoryMetric = HistoryMetric.OCCUPANCY,
    ) -> list[dict[str, Any]]:
        interval = _GRANULARITY_INTERVAL[granularity]
        parameters: dict[str, Any] = {
            "starts_at": starts_at,
            "ends_at": ends_at,
        }
        filters = _history_camera_filters(
            parameters,
            tenant_id=tenant_id,
            camera_ids=camera_ids,
        )
        if class_names:
            filters.append("AND class_name IN :class_names")
            parameters["class_names"] = class_names

        if metric is HistoryMetric.OCCUPANCY:
            statement = text(
                f"""
                WITH active_by_ts AS (
                  SELECT
                    time_bucket(INTERVAL '{interval}', ts) AS bucket,
                    camera_id,
                    class_name,
                    ts,
                    count(*)::bigint AS active_count
                  FROM tracking_events
                  WHERE ts >= :starts_at
                    AND ts < :ends_at
                    {' '.join(filters)}
                  GROUP BY 1, 2, 3, 4
                ),
                occupancy_by_camera AS (
                  SELECT
                    bucket,
                    camera_id,
                    class_name,
                    MAX(active_count)::bigint AS event_count
                  FROM active_by_ts
                  GROUP BY 1, 2, 3
                )
                SELECT
                  bucket,
                  class_name,
                  SUM(event_count)::bigint AS event_count
                FROM occupancy_by_camera
                GROUP BY 1, 2
                ORDER BY 1 ASC, 2 ASC
                """
            )
        else:
            statement = text(
                f"""
                SELECT
                  time_bucket(INTERVAL '{interval}', ts) AS bucket,
                  class_name,
                  count(*)::bigint AS event_count
                FROM tracking_events
                WHERE ts >= :starts_at
                  AND ts < :ends_at
                  {' '.join(filters)}
                GROUP BY 1, 2
                ORDER BY 1 ASC, 2 ASC
                """
            )
        if camera_ids:
            statement = statement.bindparams(bindparam("camera_ids", expanding=True))
        if class_names:
            statement = statement.bindparams(bindparam("class_names", expanding=True))

        async with self.session_factory() as session:
            rows = (await session.execute(statement, parameters)).mappings().all()
        return [dict(row) for row in rows]

    async def _fetch_series_rows_from_count_events(
        self,
        *,
        tenant_id: UUID | None = None,
        camera_ids: list[UUID] | None,
        class_names: list[str] | None,
        granularity: str,
        starts_at: datetime,
        ends_at: datetime,
    ) -> list[dict[str, Any]]:
        interval = _GRANULARITY_INTERVAL[granularity]
        parameters: dict[str, Any] = {
            "starts_at": starts_at,
            "ends_at": ends_at,
        }
        filters = _history_camera_filters(
            parameters,
            tenant_id=tenant_id,
            camera_ids=camera_ids,
        )
        if class_names:
            filters.append("AND class_name IN :class_names")
            parameters["class_names"] = class_names

        statement = text(
            f"""
            SELECT
              time_bucket(INTERVAL '{interval}', ts) AS bucket,
              class_name,
              count(*)::bigint AS event_count
            FROM count_events
            WHERE ts >= :starts_at
              AND ts < :ends_at
              {' '.join(filters)}
            GROUP BY 1, 2
            ORDER BY 1 ASC, 2 ASC
            """
        )
        if camera_ids:
            statement = statement.bindparams(bindparam("camera_ids", expanding=True))
        if class_names:
            statement = statement.bindparams(bindparam("class_names", expanding=True))

        async with self.session_factory() as session:
            rows = (await session.execute(statement, parameters)).mappings().all()
        return [dict(row) for row in rows]

    async def _fetch_series_rows_with_speed(
        self,
        *,
        tenant_id: UUID | None = None,
        camera_ids: list[UUID] | None,
        class_names: list[str] | None,
        granularity: str,
        starts_at: datetime,
        ends_at: datetime,
        metric: HistoryMetric = HistoryMetric.OCCUPANCY,
        speed_threshold: float | None,
    ) -> list[dict[str, Any]]:
        interval = _GRANULARITY_INTERVAL[granularity]
        parameters: dict[str, Any] = {
            "starts_at": starts_at,
            "ends_at": ends_at,
        }
        filters = _history_camera_filters(
            parameters,
            tenant_id=tenant_id,
            camera_ids=camera_ids,
        )
        if class_names:
            filters.append("AND class_name IN :class_names")
            parameters["class_names"] = class_names

        count_expr = (
            "count(*)::bigint"
        )
        threshold_expr = (
            "count(*) FILTER (WHERE speed_kph IS NOT NULL AND speed_kph > :speed_threshold)::bigint"
            if speed_threshold is not None
            else "NULL::bigint"
        )
        if speed_threshold is not None:
            parameters["speed_threshold"] = float(speed_threshold)

        if metric is HistoryMetric.OCCUPANCY:
            statement = text(
                f"""
                WITH active_by_ts AS (
                  SELECT
                    time_bucket(INTERVAL '{interval}', ts) AS bucket,
                    camera_id,
                    class_name,
                    ts,
                    count(*)::bigint AS active_count
                  FROM tracking_events
                  WHERE ts >= :starts_at
                    AND ts < :ends_at
                    {' '.join(filters)}
                  GROUP BY 1, 2, 3, 4
                ),
                occupancy_by_camera AS (
                  SELECT
                    bucket,
                    camera_id,
                    class_name,
                    MAX(active_count)::bigint AS event_count
                  FROM active_by_ts
                  GROUP BY 1, 2, 3
                ),
                speed_by_bucket AS (
                  SELECT
                    time_bucket(INTERVAL '{interval}', ts) AS bucket,
                    class_name,
                    count(*)::bigint AS event_count,
                    percentile_cont(0.5) WITHIN GROUP (ORDER BY speed_kph)
                        FILTER (WHERE speed_kph IS NOT NULL) AS speed_p50,
                    percentile_cont(0.95) WITHIN GROUP (ORDER BY speed_kph)
                        FILTER (WHERE speed_kph IS NOT NULL) AS speed_p95,
                    count(speed_kph)::bigint AS speed_sample_count,
                    {threshold_expr} AS over_threshold_count
                  FROM tracking_events
                  WHERE ts >= :starts_at
                    AND ts < :ends_at
                    {' '.join(filters)}
                  GROUP BY 1, 2
                )
                SELECT
                  occupancy_by_camera.bucket,
                  occupancy_by_camera.class_name,
                  SUM(occupancy_by_camera.event_count)::bigint AS event_count,
                  speed_by_bucket.speed_p50,
                  speed_by_bucket.speed_p95,
                  speed_by_bucket.speed_sample_count,
                  speed_by_bucket.over_threshold_count
                FROM occupancy_by_camera
                LEFT JOIN speed_by_bucket
                  ON speed_by_bucket.bucket = occupancy_by_camera.bucket
                 AND speed_by_bucket.class_name = occupancy_by_camera.class_name
                GROUP BY
                  occupancy_by_camera.bucket,
                  occupancy_by_camera.class_name,
                  speed_by_bucket.speed_p50,
                  speed_by_bucket.speed_p95,
                  speed_by_bucket.speed_sample_count,
                  speed_by_bucket.over_threshold_count
                ORDER BY 1 ASC, 2 ASC
                """
            )
        else:
            statement = text(
                f"""
                SELECT
                  time_bucket(INTERVAL '{interval}', ts) AS bucket,
                  class_name,
                  {count_expr} AS event_count,
                  percentile_cont(0.5) WITHIN GROUP (ORDER BY speed_kph)
                      FILTER (WHERE speed_kph IS NOT NULL) AS speed_p50,
                  percentile_cont(0.95) WITHIN GROUP (ORDER BY speed_kph)
                      FILTER (WHERE speed_kph IS NOT NULL) AS speed_p95,
                  count(speed_kph)::bigint AS speed_sample_count,
                  {threshold_expr} AS over_threshold_count
                FROM tracking_events
                WHERE ts >= :starts_at
                  AND ts < :ends_at
                  {' '.join(filters)}
                GROUP BY 1, 2
                ORDER BY 1 ASC, 2 ASC
                """
            )
        if camera_ids:
            statement = statement.bindparams(bindparam("camera_ids", expanding=True))
        if class_names:
            statement = statement.bindparams(bindparam("class_names", expanding=True))

        async with self.session_factory() as session:
            rows = (await session.execute(statement, parameters)).mappings().all()
        return [dict(row) for row in rows]

    async def _fetch_series_rows_with_speed_from_count_events(
        self,
        *,
        tenant_id: UUID | None = None,
        camera_ids: list[UUID] | None,
        class_names: list[str] | None,
        granularity: str,
        starts_at: datetime,
        ends_at: datetime,
        speed_threshold: float | None,
    ) -> list[dict[str, Any]]:
        interval = _GRANULARITY_INTERVAL[granularity]
        parameters: dict[str, Any] = {
            "starts_at": starts_at,
            "ends_at": ends_at,
        }
        filters = _history_camera_filters(
            parameters,
            tenant_id=tenant_id,
            camera_ids=camera_ids,
        )
        if class_names:
            filters.append("AND class_name IN :class_names")
            parameters["class_names"] = class_names

        threshold_expr = (
            "count(*) FILTER (WHERE speed_kph IS NOT NULL AND speed_kph > :speed_threshold)::bigint"
            if speed_threshold is not None
            else "NULL::bigint"
        )
        if speed_threshold is not None:
            parameters["speed_threshold"] = float(speed_threshold)

        statement = text(
            f"""
            SELECT
              time_bucket(INTERVAL '{interval}', ts) AS bucket,
              class_name,
              count(*)::bigint AS event_count,
              percentile_cont(0.5) WITHIN GROUP (ORDER BY speed_kph)
                  FILTER (WHERE speed_kph IS NOT NULL) AS speed_p50,
              percentile_cont(0.95) WITHIN GROUP (ORDER BY speed_kph)
                  FILTER (WHERE speed_kph IS NOT NULL) AS speed_p95,
              count(speed_kph)::bigint AS speed_sample_count,
              {threshold_expr} AS over_threshold_count
            FROM count_events
            WHERE ts >= :starts_at
              AND ts < :ends_at
              {' '.join(filters)}
            GROUP BY 1, 2
            ORDER BY 1 ASC, 2 ASC
            """
        )
        if camera_ids:
            statement = statement.bindparams(bindparam("camera_ids", expanding=True))
        if class_names:
            statement = statement.bindparams(bindparam("class_names", expanding=True))

        async with self.session_factory() as session:
            rows = (await session.execute(statement, parameters)).mappings().all()
        return [dict(row) for row in rows]

    async def _fetch_class_rows_from_tracking_events(
        self,
        *,
        tenant_id: UUID | None = None,
        camera_ids: list[UUID] | None,
        starts_at: datetime,
        ends_at: datetime,
        metric: HistoryMetric,
    ) -> list[dict[str, Any]]:
        parameters: dict[str, Any] = {
            "starts_at": starts_at,
            "ends_at": ends_at,
        }
        filters = _history_camera_filters(
            parameters,
            tenant_id=tenant_id,
            camera_ids=camera_ids,
        )

        count_expr = (
            "count(DISTINCT (camera_id, ts))::bigint"
            if metric is HistoryMetric.OCCUPANCY
            else "count(*)::bigint"
        )
        statement = text(
            f"""
            SELECT
              class_name,
              {count_expr} AS event_count,
              bool_or(speed_kph IS NOT NULL) AS has_speed_data
            FROM tracking_events
            WHERE ts >= :starts_at
              AND ts < :ends_at
              {' '.join(filters)}
            GROUP BY class_name
            ORDER BY event_count DESC, class_name ASC
            """
        )
        if camera_ids:
            statement = statement.bindparams(bindparam("camera_ids", expanding=True))

        async with self.session_factory() as session:
            rows = (await session.execute(statement, parameters)).mappings().all()
        return [dict(row) for row in rows]

    async def _fetch_class_rows_from_count_events(
        self,
        *,
        tenant_id: UUID | None = None,
        camera_ids: list[UUID] | None,
        starts_at: datetime,
        ends_at: datetime,
    ) -> list[dict[str, Any]]:
        parameters: dict[str, Any] = {
            "starts_at": starts_at,
            "ends_at": ends_at,
        }
        filters = _history_camera_filters(
            parameters,
            tenant_id=tenant_id,
            camera_ids=camera_ids,
        )

        statement = text(
            f"""
            SELECT
              class_name,
              count(*)::bigint AS event_count,
              bool_or(speed_kph IS NOT NULL) AS has_speed_data
            FROM count_events
            WHERE ts >= :starts_at
              AND ts < :ends_at
              {' '.join(filters)}
            GROUP BY class_name
            ORDER BY event_count DESC, class_name ASC
            """
        )
        if camera_ids:
            statement = statement.bindparams(bindparam("camera_ids", expanding=True))

        async with self.session_factory() as session:
            rows = (await session.execute(statement, parameters)).mappings().all()
        return [dict(row) for row in rows]

    async def _fetch_count_event_boundary_summaries(
        self,
        *,
        tenant_id: UUID | None = None,
        camera_ids: list[UUID] | None,
        starts_at: datetime,
        ends_at: datetime,
    ) -> list[dict[str, Any]]:
        parameters: dict[str, Any] = {
            "starts_at": starts_at,
            "ends_at": ends_at,
        }
        filters = _history_camera_filters(
            parameters,
            tenant_id=tenant_id,
            camera_ids=camera_ids,
        )

        statement = text(
            f"""
            SELECT
              boundary_id,
              array_agg(DISTINCT event_type ORDER BY event_type) AS event_types
            FROM count_events
            WHERE ts >= :starts_at
              AND ts < :ends_at
              {' '.join(filters)}
            GROUP BY boundary_id
            ORDER BY boundary_id ASC
            """
        )
        if camera_ids:
            statement = statement.bindparams(bindparam("camera_ids", expanding=True))

        async with self.session_factory() as session:
            rows = (await session.execute(statement, parameters)).mappings().all()
        return [
            {
                "boundary_id": row["boundary_id"],
                "event_types": [CountEventType(event_type) for event_type in row["event_types"]],
            }
            for row in rows
        ]


def _history_camera_filters(
    parameters: dict[str, Any],
    *,
    tenant_id: UUID | None,
    camera_ids: list[UUID] | None,
) -> list[str]:
    filters: list[str] = []
    if tenant_id is not None:
        parameters["tenant_id"] = tenant_id
        filters.append(
            """
            AND camera_id IN (
              SELECT cameras.id
              FROM cameras
              JOIN sites ON sites.id = cameras.site_id
              WHERE sites.tenant_id = :tenant_id
            )
            """
        )
    if camera_ids:
        filters.append("AND camera_id IN :camera_ids")
        parameters["camera_ids"] = camera_ids
    return filters


class IncidentService:
    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession],
        audit_logger: DatabaseAuditLogger | None = None,
        evidence_ledger: EvidenceLedgerService | None = None,
        settings: Settings | None = None,
    ) -> None:
        self.session_factory = session_factory
        self.audit_logger = audit_logger
        self.evidence_ledger = evidence_ledger
        self.settings = settings

    async def list_incidents(
        self,
        tenant_context: TenantContext,
        *,
        camera_id: UUID | None,
        incident_type: str | None,
        review_status: IncidentReviewStatus | None,
        limit: int,
    ) -> list[IncidentResponse]:
        async with self.session_factory() as session:
            if camera_id is not None:
                await _load_camera(session, tenant_context.tenant_id, camera_id)
            statement = (
                select(Incident, Camera.name)
                .join(Camera, Camera.id == Incident.camera_id)
                .join(Site, Site.id == Camera.site_id)
                .where(Site.tenant_id == tenant_context.tenant_id)
                .order_by(Incident.ts.desc())
                .limit(limit)
            )
            if camera_id is not None:
                statement = statement.where(Incident.camera_id == camera_id)
            if incident_type is not None:
                statement = statement.where(Incident.type == incident_type)
            if review_status is not None:
                statement = statement.where(Incident.review_status == review_status)
            incidents = list((await session.execute(statement)).all())
            incident_ids = [incident.id for incident, _camera_name in incidents]
            artifacts_by_incident = await _load_artifacts_by_incident_ids(
                session,
                incident_ids,
            )
            ledger_summary_by_incident = await _load_ledger_summaries_by_incident_ids(
                session,
                incident_ids,
            )
        return [
            _incident_response(
                incident,
                camera_name,
                evidence_artifacts=artifacts_by_incident.get(incident.id, []),
                ledger_summary=ledger_summary_by_incident.get(incident.id),
            )
            for incident, camera_name in incidents
        ]

    async def update_review_state(
        self,
        tenant_context: TenantContext,
        *,
        incident_id: UUID,
        review_status: IncidentReviewStatus,
    ) -> IncidentResponse:
        async with self.session_factory() as session:
            statement = (
                select(Incident, Camera.name)
                .join(Camera, Camera.id == Incident.camera_id)
                .join(Site, Site.id == Camera.site_id)
                .where(Site.tenant_id == tenant_context.tenant_id)
                .where(Incident.id == incident_id)
            )
            row = (await session.execute(statement)).one_or_none()
            if row is None:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Incident not found.",
                )

            incident, camera_name = row
            previous_review_status = incident.review_status
            changed = previous_review_status != review_status
            if changed:
                incident.review_status = review_status
                if review_status == IncidentReviewStatus.REVIEWED:
                    incident.reviewed_at = datetime.now(tz=UTC)
                    incident.reviewed_by_subject = tenant_context.user.subject
                else:
                    incident.reviewed_at = None
                    incident.reviewed_by_subject = None
                if self.audit_logger is not None:
                    self.audit_logger.add_to_session(
                        session,
                        tenant_context=tenant_context,
                        action="incident.review",
                        target=f"incident:{incident_id}",
                        meta={
                            "review_status": review_status.value,
                            "previous_review_status": previous_review_status.value,
                            "camera_id": str(incident.camera_id),
                            "incident_type": incident.type,
                            "user_subject": tenant_context.user.subject,
                        },
                    )
                await session.commit()
                await session.refresh(incident)
                await self._append_review_ledger_entry(
                    tenant_context=tenant_context,
                    incident=incident,
                    review_status=review_status,
                    previous_review_status=previous_review_status,
                )

            return _incident_response(incident, camera_name)

    async def get_scene_contract(
        self,
        tenant_context: TenantContext,
        *,
        incident_id: UUID,
    ) -> SceneContractSnapshotResponse:
        async with self.session_factory() as session:
            statement = (
                select(SceneContractSnapshot)
                .join(
                    Incident,
                    Incident.scene_contract_snapshot_id == SceneContractSnapshot.id,
                )
                .join(Camera, Camera.id == Incident.camera_id)
                .join(Site, Site.id == Camera.site_id)
                .where(Site.tenant_id == tenant_context.tenant_id)
                .where(Incident.id == incident_id)
            )
            snapshot = (await session.execute(statement)).scalar_one_or_none()
        if snapshot is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Scene contract not found.",
            )
        return _scene_contract_snapshot_response(snapshot)

    async def get_privacy_manifest(
        self,
        tenant_context: TenantContext,
        *,
        incident_id: UUID,
    ) -> PrivacyManifestSnapshotResponse:
        async with self.session_factory() as session:
            statement = (
                select(PrivacyManifestSnapshot)
                .join(
                    Incident,
                    Incident.privacy_manifest_snapshot_id == PrivacyManifestSnapshot.id,
                )
                .join(Camera, Camera.id == Incident.camera_id)
                .join(Site, Site.id == Camera.site_id)
                .where(Site.tenant_id == tenant_context.tenant_id)
                .where(Incident.id == incident_id)
            )
            snapshot = (await session.execute(statement)).scalar_one_or_none()
        if snapshot is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Privacy manifest not found.",
            )
        return _privacy_manifest_snapshot_response(snapshot)

    async def list_ledger_entries(
        self,
        tenant_context: TenantContext,
        *,
        incident_id: UUID,
    ) -> list[EvidenceLedgerEntryResponse]:
        async with self.session_factory() as session:
            await _ensure_incident_in_tenant(
                session,
                tenant_id=tenant_context.tenant_id,
                incident_id=incident_id,
            )
            statement = (
                select(EvidenceLedgerEntry)
                .where(EvidenceLedgerEntry.incident_id == incident_id)
                .order_by(EvidenceLedgerEntry.sequence.asc())
            )
            entries = list((await session.execute(statement)).scalars().all())
        return [_ledger_entry_response(entry) for entry in entries]

    async def get_artifact_content(
        self,
        tenant_context: TenantContext,
        *,
        incident_id: UUID,
        artifact_id: UUID,
    ) -> IncidentArtifactContent:
        async with self.session_factory() as session:
            statement = (
                select(EvidenceArtifact, Incident.clip_url)
                .join(Incident, Incident.id == EvidenceArtifact.incident_id)
                .join(Camera, Camera.id == Incident.camera_id)
                .join(Site, Site.id == Camera.site_id)
                .where(Site.tenant_id == tenant_context.tenant_id)
                .where(Incident.id == incident_id)
                .where(EvidenceArtifact.id == artifact_id)
            )
            row = (await session.execute(statement)).one_or_none()
        if row is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Evidence artifact not found.",
            )
        artifact, clip_url = row
        if artifact.storage_provider is EvidenceStorageProvider.LOCAL_FILESYSTEM:
            file_path = _resolve_local_artifact_path(self.settings, artifact.object_key)
            if not file_path.is_file():
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Evidence artifact content not found.",
                )
            return IncidentArtifactContent(
                content_type=artifact.content_type,
                file_path=file_path,
            )
        if clip_url:
            return IncidentArtifactContent(
                content_type=artifact.content_type,
                redirect_url=clip_url,
            )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Evidence artifact content not available.",
        )

    async def _append_review_ledger_entry(
        self,
        *,
        tenant_context: TenantContext,
        incident: Incident,
        review_status: IncidentReviewStatus,
        previous_review_status: IncidentReviewStatus,
    ) -> None:
        if self.evidence_ledger is None:
            return
        action = (
            EvidenceLedgerAction.INCIDENT_REVIEWED
            if review_status == IncidentReviewStatus.REVIEWED
            else EvidenceLedgerAction.INCIDENT_REOPENED
        )
        occurred_at = (
            incident.reviewed_at
            if review_status == IncidentReviewStatus.REVIEWED
            and incident.reviewed_at is not None
            else datetime.now(tz=UTC)
        )
        await self.evidence_ledger.append_entry(
            tenant_id=tenant_context.tenant_id,
            incident_id=incident.id,
            camera_id=incident.camera_id,
            action=action,
            actor_type="user",
            actor_subject=tenant_context.user.subject,
            occurred_at=occurred_at,
            payload={
                "review_status": review_status.value,
                "previous_review_status": previous_review_status.value,
                "incident_type": incident.type,
            },
        )


def _incident_response(
    incident: Incident,
    camera_name: str | None,
    *,
    evidence_artifacts: list[EvidenceArtifact] | None = None,
    ledger_summary: EvidenceLedgerSummary | None = None,
) -> IncidentResponse:
    return IncidentResponse(
        id=incident.id,
        camera_id=incident.camera_id,
        camera_name=camera_name,
        ts=incident.ts,
        type=incident.type,
        payload=incident.payload,
        snapshot_url=incident.snapshot_url,
        clip_url=incident.clip_url,
        storage_bytes=incident.storage_bytes,
        review_status=incident.review_status,
        reviewed_at=incident.reviewed_at,
        reviewed_by_subject=incident.reviewed_by_subject,
        scene_contract_hash=incident.scene_contract_hash,
        scene_contract_id=incident.scene_contract_snapshot_id,
        privacy_manifest_hash=incident.privacy_manifest_hash,
        privacy_manifest_id=incident.privacy_manifest_snapshot_id,
        recording_policy=(
            EvidenceRecordingPolicy.model_validate(incident.recording_policy)
            if incident.recording_policy is not None
            else None
        ),
        evidence_artifacts=[
            _artifact_response(artifact, review_url=incident.clip_url)
            for artifact in evidence_artifacts or []
        ],
        ledger_summary=ledger_summary,
    )


async def _load_artifacts_by_incident_ids(
    session: AsyncSession,
    incident_ids: list[UUID],
) -> dict[UUID, list[EvidenceArtifact]]:
    if not incident_ids:
        return {}
    statement = (
        select(EvidenceArtifact)
        .where(EvidenceArtifact.incident_id.in_(incident_ids))
        .order_by(EvidenceArtifact.incident_id.asc(), EvidenceArtifact.created_at.asc())
    )
    artifacts = list((await session.execute(statement)).scalars().all())
    by_incident: dict[UUID, list[EvidenceArtifact]] = {
        incident_id: [] for incident_id in incident_ids
    }
    for artifact in artifacts:
        by_incident.setdefault(artifact.incident_id, []).append(artifact)
    return by_incident


async def _load_ledger_summaries_by_incident_ids(
    session: AsyncSession,
    incident_ids: list[UUID],
) -> dict[UUID, EvidenceLedgerSummary]:
    if not incident_ids:
        return {}
    statement = (
        select(EvidenceLedgerEntry)
        .where(EvidenceLedgerEntry.incident_id.in_(incident_ids))
        .order_by(EvidenceLedgerEntry.incident_id.asc(), EvidenceLedgerEntry.sequence.asc())
    )
    entries = list((await session.execute(statement)).scalars().all())
    counts: dict[UUID, int] = {}
    latest_by_incident: dict[UUID, EvidenceLedgerEntry] = {}
    for entry in entries:
        counts[entry.incident_id] = counts.get(entry.incident_id, 0) + 1
        latest_by_incident[entry.incident_id] = entry
    return {
        incident_id: EvidenceLedgerSummary(
            entry_count=counts[incident_id],
            latest_action=entry.action,
            latest_at=entry.occurred_at,
        )
        for incident_id, entry in latest_by_incident.items()
    }


async def _ensure_incident_in_tenant(
    session: AsyncSession,
    *,
    tenant_id: UUID,
    incident_id: UUID,
) -> None:
    statement = (
        select(Incident.id)
        .join(Camera, Camera.id == Incident.camera_id)
        .join(Site, Site.id == Camera.site_id)
        .where(Site.tenant_id == tenant_id)
        .where(Incident.id == incident_id)
    )
    if (await session.execute(statement)).scalar_one_or_none() is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Incident not found.",
        )


def _scene_contract_snapshot_response(
    snapshot: SceneContractSnapshot,
) -> SceneContractSnapshotResponse:
    return SceneContractSnapshotResponse(
        id=snapshot.id,
        camera_id=snapshot.camera_id,
        schema_version=snapshot.schema_version,
        contract_hash=snapshot.contract_hash,
        contract=snapshot.contract,
        created_at=snapshot.created_at,
    )


def _privacy_manifest_snapshot_response(
    snapshot: PrivacyManifestSnapshot,
) -> PrivacyManifestSnapshotResponse:
    return PrivacyManifestSnapshotResponse(
        id=snapshot.id,
        camera_id=snapshot.camera_id,
        schema_version=snapshot.schema_version,
        manifest_hash=snapshot.manifest_hash,
        manifest=snapshot.manifest,
        created_at=snapshot.created_at,
    )


def _artifact_response(
    artifact: EvidenceArtifact,
    *,
    review_url: str | None,
) -> EvidenceArtifactResponse:
    return EvidenceArtifactResponse(
        id=artifact.id,
        incident_id=artifact.incident_id,
        camera_id=artifact.camera_id,
        kind=artifact.kind,
        status=artifact.status,
        storage_provider=artifact.storage_provider,
        storage_scope=artifact.storage_scope,
        bucket=artifact.bucket,
        object_key=artifact.object_key,
        content_type=artifact.content_type,
        sha256=artifact.sha256,
        size_bytes=artifact.size_bytes,
        clip_started_at=artifact.clip_started_at,
        triggered_at=artifact.triggered_at,
        clip_ended_at=artifact.clip_ended_at,
        duration_seconds=artifact.duration_seconds,
        fps=artifact.fps,
        scene_contract_hash=artifact.scene_contract_hash,
        privacy_manifest_hash=artifact.privacy_manifest_hash,
        review_url=review_url,
    )


def _ledger_entry_response(entry: EvidenceLedgerEntry) -> EvidenceLedgerEntryResponse:
    return EvidenceLedgerEntryResponse(
        id=entry.id,
        incident_id=entry.incident_id,
        camera_id=entry.camera_id,
        sequence=entry.sequence,
        action=entry.action,
        actor_type=entry.actor_type,
        actor_subject=entry.actor_subject,
        occurred_at=entry.occurred_at,
        payload=entry.payload,
        previous_entry_hash=entry.previous_entry_hash,
        entry_hash=entry.entry_hash,
    )


def _resolve_local_artifact_path(
    settings: Settings | None,
    object_key: str,
) -> Path:
    if settings is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Local evidence storage is not configured.",
        )
    object_path = PurePosixPath(object_key)
    if object_path.is_absolute() or any(
        part in {"", ".", ".."} for part in object_path.parts
    ):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Evidence artifact content not found.",
        )
    root = Path(settings.incident_local_storage_root).expanduser().resolve()
    candidate = root.joinpath(*object_path.parts).resolve()
    if candidate != root and root not in candidate.parents:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Evidence artifact content not found.",
        )
    return candidate


class StreamService:
    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession],
        mediamtx: MediaMTXClient,
        settings: Settings,
        negotiator: WebRTCNegotiator | None = None,
        token_issuer: MediaMTXTokenIssuer | None = None,
    ) -> None:
        self.session_factory = session_factory
        self.mediamtx = mediamtx
        self.settings = settings
        self.token_issuer = token_issuer or MediaMTXTokenIssuer.from_settings(settings)
        self.negotiator = negotiator or WebRTCNegotiator(token_issuer=self.token_issuer)
        self.video_feed_limiter = UserConcurrencyLimiter(
            limit=settings.video_feed_max_concurrent_per_user
        )
        self._edge_relay_refresh_after: dict[tuple[UUID, str, str], datetime] = {}

    async def close(self) -> None:
        await self.negotiator.close()
        await self.mediamtx.close()

    async def create_offer(
        self,
        tenant_context: TenantContext,
        *,
        camera_id: UUID,
        offer: StreamOfferRequest,
    ) -> StreamOfferResponse:
        access = await self._resolve_stream_access(tenant_context, camera_id)
        sdp_answer = await self.negotiator.negotiate_offer(
            access=access,
            camera_id=camera_id,
            subject=tenant_context.user.subject,
            sdp_offer=offer.sdp_offer,
        )
        return StreamOfferResponse(camera_id=camera_id, sdp_answer=sdp_answer)

    async def get_hls_playlist_url(
        self,
        tenant_context: TenantContext,
        *,
        camera_id: UUID,
    ) -> str:
        access = await self._resolve_stream_access(tenant_context, camera_id)
        return self.token_issuer.build_hls_url(
            subject=tenant_context.user.subject,
            camera_id=camera_id,
            access=access,
        )

    async def open_mjpeg_proxy(
        self,
        tenant_context: TenantContext,
        *,
        camera_id: UUID,
        user: Any,
    ) -> UpstreamProxyStream:
        access = await self._resolve_stream_access(tenant_context, camera_id)
        try:
            await self.video_feed_limiter.acquire(user.subject)
        except ConcurrencyLimitExceeded as exc:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Too many concurrent MJPEG feeds for this user.",
            ) from exc

        try:
            upstream = await self.negotiator.open_mjpeg_stream(
                access=access,
                camera_id=camera_id,
                subject=user.subject,
            )
        except (httpx.HTTPError, RuntimeError) as exc:
            await self.video_feed_limiter.release(user.subject)
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="Unable to open MediaMTX MJPEG stream.",
            ) from exc

        upstream.headers.setdefault("Cache-Control", "no-store")
        upstream.on_close = self._release_video_feed_slot(user.subject, upstream.on_close)
        return upstream

    def jwks(self) -> dict[str, list[dict[str, str]]]:
        return self.token_issuer.jwks()

    async def _resolve_stream_access(
        self,
        tenant_context: TenantContext,
        camera_id: UUID,
    ) -> StreamAccess:
        async with self.session_factory() as session:
            camera = await _load_camera(session, tenant_context.tenant_id, camera_id)
        browser_delivery = BrowserDeliverySettings.model_validate(
            camera.browser_delivery or BrowserDeliverySettings().model_dump(mode="python")
        )
        stream_settings = _resolve_worker_stream_settings(
            browser_delivery=browser_delivery,
            fps_cap=camera.fps_cap,
        )
        access = resolve_stream_access(
            camera_id=camera.id,
            processing_mode=camera.processing_mode,
            edge_node_id=camera.edge_node_id,
            stream_kind=stream_settings.kind,
            privacy=camera.privacy,
            rtsp_base_url=self.settings.mediamtx_rtsp_base_url,
            webrtc_base_url=self.settings.mediamtx_webrtc_base_url,
            hls_base_url=self.settings.mediamtx_hls_base_url,
            mjpeg_base_url=self.settings.mediamtx_mjpeg_base_url,
            mjpeg_path_template=self.settings.mediamtx_mjpeg_path_template,
        )
        await self._ensure_edge_stream_relay(camera=camera, access=access)
        return access

    async def _ensure_edge_stream_relay(
        self,
        *,
        camera: Camera,
        access: StreamAccess,
    ) -> None:
        if (
            camera.edge_node_id is None
            and camera.processing_mode is not ProcessingMode.EDGE
        ):
            return
        edge_rtsp_base = self._edge_mediamtx_rtsp_base_url(camera.edge_node_id)
        if edge_rtsp_base is None:
            return
        edge_rtsp_base = edge_rtsp_base.rstrip("/")
        cache_key = (camera.id, access.path_name, edge_rtsp_base)
        now = datetime.now(tz=UTC)
        refresh_after = self._edge_relay_refresh_after.get(cache_key)
        if refresh_after is not None and refresh_after > now:
            return

        edge_rtsp_url = f"{edge_rtsp_base}/{access.path_name}"
        source = self.token_issuer.build_internal_rtsp_url(
            camera_id=camera.id,
            path_name=access.path_name,
            rtsp_url=edge_rtsp_url,
            ttl_seconds=self.settings.mediamtx_jwt_worker_ttl_seconds,
        )
        await self.mediamtx.ensure_path(
            access.path_name,
            source=source,
            source_on_demand=True,
        )
        ttl_seconds = max(1, self.settings.mediamtx_jwt_worker_ttl_seconds)
        self._edge_relay_refresh_after[cache_key] = now + timedelta(
            seconds=max(1, int(ttl_seconds * 0.8))
        )

    def _edge_mediamtx_rtsp_base_url(self, edge_node_id: UUID | None) -> str | None:
        base_urls = self.settings.edge_mediamtx_rtsp_base_urls
        return (
            (base_urls.get(str(edge_node_id)) if edge_node_id is not None else None)
            or base_urls.get("*")
            or base_urls.get("default")
        )

    def _release_video_feed_slot(
        self,
        subject: str,
        next_callback: Any,
    ) -> Any:
        async def callback() -> None:
            try:
                if next_callback is not None:
                    await next_callback()
            finally:
                await self.video_feed_limiter.release(subject)

        return callback


class NatsTelemetrySubscription:
    def __init__(
        self,
        *,
        event_client: NatsJetStreamClient,
        queue: asyncio.Queue[TelemetryFrame],
        nats_subscription: Any,
    ) -> None:
        self.event_client = event_client
        self.queue = queue
        self.nats_subscription = nats_subscription

    async def receive(self) -> TelemetryFrame:
        return await self.queue.get()

    async def close(self) -> None:
        unsubscribe = getattr(self.nats_subscription, "unsubscribe", None)
        if callable(unsubscribe):
            await unsubscribe()


class NatsTelemetryService:
    def __init__(
        self,
        *,
        session_factory: async_sessionmaker[AsyncSession],
        event_client: NatsJetStreamClient,
        settings: Settings,
    ) -> None:
        self.session_factory = session_factory
        self.event_client = event_client
        self.settings = settings

    async def subscribe(self, tenant_context: TenantContext) -> NatsTelemetrySubscription:
        allowed_camera_ids = await self._camera_ids_for_tenant(tenant_context)
        queue: asyncio.Queue[TelemetryFrame] = asyncio.Queue(
            maxsize=self.settings.websocket_telemetry_buffer_size
        )

        async def handle_message(message: EventMessage) -> None:
            frame = TelemetryFrame.model_validate_json(message.data)
            if frame.camera_id not in allowed_camera_ids:
                return
            if queue.full():
                queue.get_nowait()
            queue.put_nowait(frame)

        nats_subscription = await self.event_client.subscribe(
            "evt.tracking.*",
            handle_message,
            deliver_policy=js_api.DeliverPolicy.NEW,
        )
        return NatsTelemetrySubscription(
            event_client=self.event_client,
            queue=queue,
            nats_subscription=nats_subscription,
        )

    async def _camera_ids_for_tenant(self, tenant_context: TenantContext) -> set[UUID]:
        async with self.session_factory() as session:
            statement = (
                select(Camera.id)
                .join(Site, Site.id == Camera.site_id)
                .where(Site.tenant_id == tenant_context.tenant_id)
            )
            rows = (await session.execute(statement)).all()
        return {row[0] for row in rows}


def build_app_services(
    *,
    settings: Settings,
    db: DatabaseManager,
    events: NatsJetStreamClient,
    query_service: QueryService,
) -> AppServices:
    audit_logger = DatabaseAuditLogger(db.session_factory)
    mediamtx = MediaMTXClient(
        api_base_url=settings.mediamtx_api_url,
        rtsp_base_url=settings.mediamtx_rtsp_base_url,
        whip_base_url=settings.mediamtx_whip_base_url,
        username=settings.mediamtx_username,
        password=(
            settings.mediamtx_password.get_secret_value()
            if settings.mediamtx_password is not None
            else None
        ),
    )
    edge_service = EdgeService(db.session_factory, settings, events, audit_logger)
    return AppServices(
        tenancy=TenancyService(db.session_factory, settings),
        sites=SiteService(db.session_factory, audit_logger),
        cameras=CameraService(db.session_factory, settings, audit_logger, events),
        models=ModelService(db.session_factory, audit_logger),
        runtime_artifacts=RuntimeArtifactService(db.session_factory),
        privacy_manifests=PrivacyManifestService(db.session_factory),
        scene_contracts=SceneContractService(db.session_factory),
        edge=edge_service,
        operations=OperationsService(
            db.session_factory,
            settings,
            edge_service=edge_service,
        ),
        history=HistoryService(db.session_factory),
        incidents=IncidentService(
            db.session_factory,
            audit_logger,
            EvidenceLedgerService(db.session_factory),
            settings,
        ),
        streams=StreamService(db.session_factory, mediamtx, settings),
        query=query_service,
        telemetry=NatsTelemetryService(
            session_factory=db.session_factory,
            event_client=events,
            settings=settings,
        ),
    )


def _fleet_node_status(last_seen_at: datetime | None, now: datetime) -> FleetNodeStatus:
    if last_seen_at is None:
        return FleetNodeStatus.OFFLINE
    age = now - last_seen_at
    if age <= timedelta(minutes=2):
        return FleetNodeStatus.HEALTHY
    if age <= timedelta(minutes=15):
        return FleetNodeStatus.STALE
    return FleetNodeStatus.OFFLINE


def _derive_worker_lifecycle(
    *,
    camera: Camera,
    edge_by_id: dict[UUID, EdgeNode],
    now: datetime,
) -> tuple[
    WorkerDesiredState,
    WorkerRuntimeStatus,
    Literal["manual_dev", "central_supervisor", "edge_supervisor", "none"],
    str,
]:
    if camera.processing_mode is ProcessingMode.EDGE and camera.edge_node_id is None:
        return (
            WorkerDesiredState.NOT_DESIRED,
            WorkerRuntimeStatus.UNKNOWN,
            "none",
            "Edge processing requires an assigned edge node.",
        )
    if camera.edge_node_id is not None:
        edge = edge_by_id.get(camera.edge_node_id)
        if edge is None:
            return (
                WorkerDesiredState.SUPERVISED,
                WorkerRuntimeStatus.OFFLINE,
                "edge_supervisor",
                "Assigned edge node is missing.",
            )
        node_status = _fleet_node_status(edge.last_seen_at, now)
        runtime = (
            WorkerRuntimeStatus.STALE
            if node_status is FleetNodeStatus.STALE
            else WorkerRuntimeStatus.OFFLINE
            if node_status is FleetNodeStatus.OFFLINE
            else WorkerRuntimeStatus.NOT_REPORTED
        )
        return (
            WorkerDesiredState.SUPERVISED,
            runtime,
            "edge_supervisor",
            "Edge supervisor owns this worker process.",
        )
    if camera.processing_mode in {ProcessingMode.CENTRAL, ProcessingMode.HYBRID}:
        return (
            WorkerDesiredState.MANUAL,
            WorkerRuntimeStatus.NOT_REPORTED,
            "manual_dev",
            "Start this worker manually in local development.",
        )
    return (
        WorkerDesiredState.NOT_DESIRED,
        WorkerRuntimeStatus.NOT_REPORTED,
        "none",
        "No worker is desired for this camera.",
    )


def _central_dev_run_command(camera_id: UUID) -> str:
    return (
        f"{_local_dev_token_command()}\n\n"
        'cd "${ARGUS_REPO_DIR:-$HOME/vision}/backend" && \\\n'
        'ARGUS_API_BASE_URL="http://127.0.0.1:8000" \\\n'
        'ARGUS_API_BEARER_TOKEN="$TOKEN" \\\n'
        f'python3 -m uv run python -m argus.inference.engine --camera-id "{camera_id}"'
    )


def _edge_dev_compose_command(edge_node_id: UUID) -> str:
    return (
        f"{_local_dev_token_command()}\n\n"
        'ARGUS_EDGE_NODE_ID="'
        f'{edge_node_id}" \\\n'
        'ARGUS_EDGE_CAMERA_ID="${ARGUS_EDGE_CAMERA_ID:?'
        'Set ARGUS_EDGE_CAMERA_ID to the camera UUID}" \\\n'
        'ARGUS_API_BASE_URL="${ARGUS_API_BASE_URL:?'
        'Set ARGUS_API_BASE_URL to the master API URL}" \\\n'
        'ARGUS_API_BEARER_TOKEN="$TOKEN" \\\n'
        'ARGUS_DB_URL="${ARGUS_DB_URL:?Set ARGUS_DB_URL to the master Postgres URL}" \\\n'
        'ARGUS_MINIO_ENDPOINT="${ARGUS_MINIO_ENDPOINT:?'
        'Set ARGUS_MINIO_ENDPOINT to the master MinIO endpoint}" \\\n'
        "docker compose -f infra/docker-compose.edge.yml up inference-worker"
    )


def _local_dev_token_command() -> str:
    return (
        'TOKEN="$(\n'
        "  curl -fsS \\\n"
        "    --data "
        "'grant_type=password&client_id=argus-cli&username=admin-dev&password=argus-admin-pass' "
        "\\\n"
        "    http://127.0.0.1:8080/realms/argus-dev/protocol/openid-connect/token |\n"
        '  python3 -c \'import json,sys; print(json.load(sys.stdin)["access_token"])\'\n'
        ')"'
    )


def _camera_delivery_diagnostic(camera: Camera) -> FleetDeliveryDiagnostic:
    source_capability = (
        SourceCapability.model_validate(camera.source_capability)
        if camera.source_capability is not None
        else None
    )
    requested = BrowserDeliverySettings.model_validate(camera.browser_delivery or {})
    resolved = _build_source_aware_browser_delivery(
        requested=requested,
        privacy=camera.privacy,
        source_capability=source_capability,
        processing_mode=camera.processing_mode,
        edge_node_id=camera.edge_node_id,
    )
    selected = _resolve_worker_stream_settings(
        browser_delivery=resolved,
        fps_cap=camera.fps_cap,
    )
    return FleetDeliveryDiagnostic(
        camera_id=camera.id,
        camera_name=camera.name,
        processing_mode=camera.processing_mode,
        assigned_node_id=camera.edge_node_id,
        source_capability=source_capability,
        default_profile=resolved.default_profile,
        available_profiles=[
            BrowserDeliveryProfile.model_validate(profile) for profile in resolved.profiles
        ],
        native_status=resolved.native_status,
        selected_stream_mode=selected.kind,
    )


async def _load_site(session: AsyncSession, tenant_id: UUID, site_id: UUID) -> Site:
    statement = select(Site).where(Site.id == site_id, Site.tenant_id == tenant_id)
    site = (await session.execute(statement)).scalar_one_or_none()
    if site is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Site not found.")
    return site


async def _load_model(session: AsyncSession, model_id: UUID) -> Model:
    model = await session.get(Model, model_id)
    if model is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Model not found.",
        )
    return model


async def _load_camera(session: AsyncSession, tenant_id: UUID, camera_id: UUID) -> Camera:
    statement = (
        select(Camera)
        .join(Site, Site.id == Camera.site_id)
        .where(Camera.id == camera_id, Site.tenant_id == tenant_id)
    )
    camera = (await session.execute(statement)).scalar_one_or_none()
    if camera is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Camera not found.")
    return camera


async def _load_worker_runtime_artifacts(
    *,
    session: AsyncSession,
    camera: Camera,
    model: Model,
) -> list[ModelRuntimeArtifact]:
    statement = select(ModelRuntimeArtifact).where(ModelRuntimeArtifact.model_id == model.id)
    artifacts = (await session.execute(statement)).scalars().all()
    runtime_vocabulary_hash = (
        hash_vocabulary(getattr(camera, "runtime_vocabulary", None) or [])
        if _model_capability(model) is DetectorCapability.OPEN_VOCAB
        else None
    )
    return [
        artifact
        for artifact in artifacts
        if _runtime_artifact_matches_worker(
            artifact=artifact,
            camera=camera,
            model=model,
            runtime_vocabulary_hash=runtime_vocabulary_hash,
        )
    ]


async def _get_site(
    *,
    session_factory: async_sessionmaker[AsyncSession],
    tenant_context: TenantContext,
    site_id: UUID,
) -> Site:
    async with session_factory() as session:
        return await _load_site(session, tenant_context.tenant_id, site_id)


def _site_to_response(site: Site) -> SiteResponse:
    geo_point = None
    if site.geo_point is not None:
        geo_point = {
            str(key): float(cast(int | float | str, value))
            for key, value in site.geo_point.items()
        }
    return SiteResponse(
        id=site.id,
        tenant_id=site.tenant_id,
        name=site.name,
        description=site.description,
        tz=site.tz,
        geo_point=geo_point,
        created_at=site.created_at,
    )


def _model_to_response(model: Model) -> ModelResponse:
    return ModelResponse(
        id=model.id,
        name=model.name,
        version=model.version,
        task=model.task,
        path=model.path,
        format=model.format,
        capability=_model_capability(model),
        capability_config=ModelCapabilityConfig.model_validate(_model_capability_config(model)),
        classes=list(model.classes),
        input_shape=dict(model.input_shape),
        sha256=model.sha256,
        size_bytes=model.size_bytes,
        license=model.license,
    )


def _model_capability(model: Model) -> DetectorCapability:
    capability = getattr(model, "capability", None)
    if capability is None:
        return DetectorCapability.FIXED_VOCAB
    if isinstance(capability, DetectorCapability):
        return capability
    return DetectorCapability(str(capability))


def _model_capability_config(model: Model) -> dict[str, object]:
    return dict(getattr(model, "capability_config", None) or {})


def _runtime_artifact_matches_worker(
    *,
    artifact: ModelRuntimeArtifact,
    camera: Camera,
    model: Model,
    runtime_vocabulary_hash: str | None,
) -> bool:
    if artifact.validation_status is not RuntimeArtifactValidationStatus.VALID:
        return False
    if artifact.source_model_sha256 != model.sha256:
        return False
    if artifact.capability is not _model_capability(model):
        return False
    if artifact.scope is RuntimeArtifactScope.MODEL:
        return artifact.camera_id is None and _artifact_vocabulary_matches(
            artifact,
            runtime_vocabulary_hash,
        )
    if artifact.scope is RuntimeArtifactScope.SCENE:
        if artifact.camera_id != camera.id:
            return False
        if artifact.capability is DetectorCapability.OPEN_VOCAB:
            return artifact_matches_camera_vocabulary(artifact=artifact, camera=camera)
        return _artifact_vocabulary_matches(artifact, runtime_vocabulary_hash)
    return False


def _artifact_vocabulary_matches(
    artifact: ModelRuntimeArtifact,
    runtime_vocabulary_hash: str | None,
) -> bool:
    if artifact.capability is not DetectorCapability.OPEN_VOCAB:
        return True
    return bool(artifact.vocabulary_hash) and artifact.vocabulary_hash == runtime_vocabulary_hash


def _validate_model_runtime_backend(
    *,
    capability: DetectorCapability,
    format: ModelFormat,
    capability_config: dict[str, object],
) -> None:
    backend_value = capability_config.get("runtime_backend")
    if backend_value is None:
        return

    backend = str(backend_value)
    readiness = str(capability_config.get("readiness") or "ready")

    if backend == "onnxruntime" and format is not ModelFormat.ONNX:
        raise HTTPException(
            status_code=HTTP_422_UNPROCESSABLE,
            detail="runtime_backend=onnxruntime requires format=onnx.",
        )

    if backend in {"ultralytics_yolo_world", "ultralytics_yoloe"}:
        if capability is not DetectorCapability.OPEN_VOCAB:
            raise HTTPException(
                status_code=HTTP_422_UNPROCESSABLE,
                detail=f"runtime_backend={backend} requires capability=open_vocab.",
            )
        if format is not ModelFormat.PT:
            raise HTTPException(
                status_code=HTTP_422_UNPROCESSABLE,
                detail=f"runtime_backend={backend} requires format=pt.",
            )

    if backend == "tensorrt_engine" and readiness == "ready":
        raise HTTPException(
            status_code=HTTP_422_UNPROCESSABLE,
            detail="TensorRT engine detector is not implemented; use readiness=planned.",
        )


def _resolve_model_classes_for_capability(
    *,
    capability: DetectorCapability,
    path: str,
    format: ModelFormat,
    classes: list[str] | None,
    capability_config: dict[str, object],
) -> list[str]:
    _validate_model_runtime_backend(
        capability=capability,
        format=format,
        capability_config=capability_config,
    )
    if capability is DetectorCapability.OPEN_VOCAB:
        if capability_config.get("supports_runtime_vocabulary_updates") is not True:
            raise HTTPException(
                status_code=HTTP_422_UNPROCESSABLE,
                detail="open_vocab models must declare runtime vocabulary support.",
            )
        return list(classes or [])

    resolved_classes, _ = resolve_model_classes(path, format, classes)
    return resolved_classes


def _validate_active_classes_subset(
    *,
    active_classes: list[str] | None,
    primary_model_classes: list[str],
) -> None:
    if active_classes is None:
        raise HTTPException(
            status_code=HTTP_422_UNPROCESSABLE,
            detail="active_classes cannot be null.",
        )
    allowed_classes = set(primary_model_classes)
    invalid_classes = sorted(
        {
            class_name
            for class_name in active_classes
            if class_name not in allowed_classes
        }
    )
    if invalid_classes:
        raise HTTPException(
            status_code=HTTP_422_UNPROCESSABLE,
            detail=(
                "active_classes must be a subset of the selected primary model classes. "
                f"Unknown classes: {', '.join(invalid_classes)}."
            ),
        )


def _validate_runtime_vocabulary(
    *,
    terms: list[str],
    primary_model: Model,
) -> None:
    max_terms = int(
        cast(Any, _model_capability_config(primary_model).get("max_runtime_terms") or 0)
    )
    if max_terms > 0 and len(terms) > max_terms:
        raise HTTPException(
            status_code=HTTP_422_UNPROCESSABLE,
            detail=f"runtime_vocabulary exceeds max_runtime_terms={max_terms}.",
        )


def _runtime_vocabulary_state_from_camera(camera: Camera) -> RuntimeVocabularyState:
    return RuntimeVocabularyState(
        terms=list(getattr(camera, "runtime_vocabulary", None) or []),
        source=(
            getattr(camera, "runtime_vocabulary_source", None)
            or RuntimeVocabularySource.DEFAULT
        ),
        version=int(getattr(camera, "runtime_vocabulary_version", None) or 0),
        updated_at=getattr(camera, "runtime_vocabulary_updated_at", None),
    )


def _record_camera_vocabulary_snapshot(
    *,
    session: AsyncSession,
    camera: Camera,
    runtime_vocabulary: RuntimeVocabularyState,
) -> None:
    if camera.id is None:
        camera.id = uuid.uuid4()
    terms = normalize_vocabulary_terms(runtime_vocabulary.terms)
    session.add(
        CameraVocabularySnapshot(
            camera_id=camera.id,
            version=runtime_vocabulary.version,
            vocabulary_hash=hash_vocabulary(terms),
            source=runtime_vocabulary.source,
            terms=terms,
        )
    )


def _resolve_camera_detector_state(
    *,
    active_classes: list[str] | None,
    runtime_vocabulary: RuntimeVocabularyState,
    primary_model: Model,
) -> tuple[list[str], RuntimeVocabularyState]:
    if _model_capability(primary_model) is DetectorCapability.FIXED_VOCAB:
        _validate_active_classes_subset(
            active_classes=active_classes,
            primary_model_classes=primary_model.classes,
        )
        return list(active_classes or []), RuntimeVocabularyState(
            terms=list(primary_model.classes),
            source=RuntimeVocabularySource.DEFAULT,
            version=0,
            updated_at=None,
        )

    _validate_runtime_vocabulary(
        terms=runtime_vocabulary.terms,
        primary_model=primary_model,
    )
    return list(active_classes or []), runtime_vocabulary.model_copy(
        update={"terms": normalize_vocabulary_terms(runtime_vocabulary.terms)}
    )


def _camera_to_response(camera: Camera) -> CameraResponse:
    privacy = PrivacySettings.model_validate(camera.privacy)
    source_capability = (
        SourceCapability.model_validate(camera.source_capability)
        if camera.source_capability is not None
        else None
    )
    browser_delivery = _build_source_aware_browser_delivery(
        requested=BrowserDeliverySettings.model_validate(
            camera.browser_delivery or BrowserDeliverySettings().model_dump(mode="python")
        ),
        source_capability=source_capability,
        privacy=privacy.model_dump(mode="python"),
        processing_mode=camera.processing_mode,
        edge_node_id=camera.edge_node_id,
        source_kind=_source_kind_from_camera(camera),
    )
    return CameraResponse(
        id=camera.id,
        site_id=camera.site_id,
        edge_node_id=camera.edge_node_id,
        name=camera.name,
        rtsp_url_masked=_mask_camera_source_url(camera),
        camera_source=_camera_source_settings_from_camera(camera),
        processing_mode=camera.processing_mode,
        primary_model_id=camera.primary_model_id,
        secondary_model_id=camera.secondary_model_id,
        tracker_type=camera.tracker_type,
        active_classes=list(camera.active_classes),
        runtime_vocabulary=_runtime_vocabulary_state_from_camera(camera),
        attribute_rules=list(camera.attribute_rules),
        zones=cast(Any, list(camera.zones)),
        vision_profile=SceneVisionProfile.model_validate(camera.vision_profile or {}),
        detection_regions=cast(Any, list(camera.detection_regions or [])),
        homography=(
            HomographyPayload.model_validate(camera.homography)
            if camera.homography is not None
            else None
        ),
        privacy=privacy,
        browser_delivery=browser_delivery,
        source_capability=source_capability,
        frame_skip=camera.frame_skip,
        fps_cap=camera.fps_cap,
        recording_policy=_recording_policy_from_camera(camera),
        created_at=camera.created_at,
        updated_at=camera.updated_at,
    )


def _worker_privacy_settings(
    privacy_payload: PrivacySettings | dict[str, Any],
) -> WorkerPrivacySettings:
    privacy = (
        privacy_payload
        if isinstance(privacy_payload, PrivacySettings)
        else PrivacySettings.model_validate(privacy_payload)
    )
    return WorkerPrivacySettings(
        blur_faces=privacy.blur_faces,
        blur_plates=privacy.blur_plates,
        method=privacy.method,
        strength=privacy.strength,
    )


def _camera_to_worker_config(
    *,
    camera: Camera,
    primary_model: Model,
    secondary_model: Model | None,
    settings: Settings,
    rtsp_url: str,
    runtime_artifacts: list[ModelRuntimeArtifact] | None = None,
    recording_policy: EvidenceRecordingPolicy | None = None,
    scene_contract_hash: str | None = None,
    privacy_manifest_hash: str | None = None,
) -> WorkerConfigResponse:
    resolved_recording_policy = recording_policy or _recording_policy_from_camera(camera)
    privacy = PrivacySettings.model_validate(camera.privacy)
    requested_browser_delivery = BrowserDeliverySettings.model_validate(
        camera.browser_delivery or BrowserDeliverySettings().model_dump(mode="python")
    )
    source_capability = (
        SourceCapability.model_validate(camera.source_capability)
        if camera.source_capability is not None
        else None
    )
    browser_delivery = _build_source_aware_browser_delivery(
        requested=requested_browser_delivery,
        source_capability=source_capability,
        privacy=privacy.model_dump(mode="python"),
        processing_mode=camera.processing_mode,
        edge_node_id=camera.edge_node_id,
        source_kind=_source_kind_from_camera(camera),
    )
    source_uri, camera_source, worker_rtsp_url = _worker_camera_source_payload(
        camera,
        rtsp_url=rtsp_url,
    )
    vision_profile = SceneVisionProfile.model_validate(camera.vision_profile or {})
    if vision_profile.motion_metrics.speed_enabled and camera.homography is None:
        raise HTTPException(
            status_code=HTTP_422_UNPROCESSABLE,
            detail="Homography is required when speed metrics are enabled.",
        )
    detection_regions = [
        DetectionRegion.model_validate(_worker_detection_region_payload(region))
        for region in (camera.detection_regions or [])
    ]
    return WorkerConfigResponse(
        camera_id=camera.id,
        mode=camera.processing_mode,
        scene_contract_hash=scene_contract_hash,
        privacy_manifest_hash=privacy_manifest_hash,
        recording_policy=resolved_recording_policy,
        camera=WorkerCameraSettings(
            rtsp_url=worker_rtsp_url,
            source_uri=source_uri,
            camera_source=camera_source,
            frame_skip=camera.frame_skip,
            fps_cap=camera.fps_cap,
        ),
        publish=WorkerPublishSettings(
            subject_prefix="evt.tracking",
            http_fallback_url=None,
        ),
        stream=_resolve_worker_stream_settings(
            browser_delivery=browser_delivery,
            fps_cap=camera.fps_cap,
        ),
        model=_model_to_worker_settings(
            primary_model,
            runtime_vocabulary=_runtime_vocabulary_state_from_camera(camera),
        ),
        secondary_model=(
            _model_to_worker_settings(secondary_model)
            if secondary_model is not None
            else None
        ),
        tracker=WorkerTrackerSettings(
            tracker_type=camera.tracker_type,
            frame_rate=camera.fps_cap,
        ),
        privacy=_worker_privacy_settings(privacy),
        active_classes=list(camera.active_classes),
        runtime_vocabulary=_runtime_vocabulary_state_from_camera(camera),
        runtime_capability=_worker_runtime_capability(primary_model),
        runtime_artifacts=[
            _runtime_artifact_to_worker_payload(artifact)
            for artifact in (runtime_artifacts or [])
        ],
        attribute_rules=list(camera.attribute_rules),
        zones=cast(Any, [_worker_zone_payload(zone) for zone in camera.zones]),
        vision_profile=vision_profile,
        detection_regions=detection_regions,
        homography=_homography_to_worker_payload(camera.homography),
    )


def _recording_policy_from_camera(camera: Camera) -> EvidenceRecordingPolicy:
    return EvidenceRecordingPolicy.model_validate(camera.evidence_recording_policy or {})


def _source_settings_from_payload(
    *,
    rtsp_url: str | None,
    camera_source: CameraSourceSettings | None,
) -> CameraSourceSettings | None:
    if camera_source is not None:
        return camera_source
    if rtsp_url is None or rtsp_url.strip() == "":
        return None
    return CameraSourceSettings(kind=CameraSourceKind.RTSP, uri=rtsp_url.strip())


def _source_settings_from_update(
    camera: Camera,
    update_data: dict[str, Any],
) -> CameraSourceSettings | None:
    camera_source = update_data.get("camera_source")
    if camera_source is not None:
        return (
            camera_source
            if isinstance(camera_source, CameraSourceSettings)
            else CameraSourceSettings.model_validate(camera_source)
        )
    if "rtsp_url" in update_data and update_data["rtsp_url"] is not None:
        return CameraSourceSettings(
            kind=CameraSourceKind.RTSP,
            uri=str(update_data["rtsp_url"]).strip(),
        )
    del camera
    return None


def _source_kind_from_camera(camera: Camera) -> CameraSourceKind:
    try:
        return CameraSourceKind(camera.source_kind or CameraSourceKind.RTSP.value)
    except ValueError:
        return CameraSourceKind.RTSP


def _source_kind_from_update(camera: Camera, update_data: dict[str, Any]) -> CameraSourceKind:
    source_kind = update_data.get("source_kind")
    if source_kind is None:
        return _source_kind_from_camera(camera)
    try:
        return CameraSourceKind(str(source_kind))
    except ValueError:
        return CameraSourceKind.RTSP


def _source_config_payload(source: NormalizedCameraSource) -> dict[str, object]:
    payload: dict[str, object] = {
        "kind": source.kind.value,
        "redacted_uri": source.redacted_uri,
        "capture_uri": source.capture_uri,
    }
    if source.label is not None:
        payload["label"] = source.label
    if source.kind is not CameraSourceKind.RTSP:
        payload["uri"] = source.uri
    return payload


def _camera_source_settings_from_camera(
    camera: Camera,
    *,
    rtsp_url: str | None = None,
    for_worker: bool = False,
) -> CameraSourceSettings:
    source_kind = _source_kind_from_camera(camera)
    source_config = dict(camera.source_config or {})
    label = source_config.get("label")
    if not isinstance(label, str):
        label = None

    if source_kind is CameraSourceKind.RTSP:
        uri = rtsp_url if for_worker and rtsp_url is not None else None
        uri = uri or _rtsp_response_uri_from_source_config(source_config)
        return CameraSourceSettings(kind=CameraSourceKind.RTSP, uri=uri, label=label)

    configured_uri = source_config.get("uri")
    if isinstance(configured_uri, str) and configured_uri:
        return CameraSourceSettings(kind=source_kind, uri=configured_uri, label=label)
    capture_uri = source_config.get("capture_uri")
    if source_kind is CameraSourceKind.USB and isinstance(capture_uri, str):
        return CameraSourceSettings(kind=source_kind, uri=f"usb://{capture_uri}", label=label)
    if source_kind is CameraSourceKind.JETSON_CSI and isinstance(capture_uri, str):
        return CameraSourceSettings(kind=source_kind, uri=capture_uri, label=label)
    return CameraSourceSettings(kind=CameraSourceKind.RTSP, uri=rtsp_url or "rtsp://***")


def _rtsp_response_uri_from_source_config(source_config: dict[str, object]) -> str:
    redacted_uri = source_config.get("redacted_uri")
    if isinstance(redacted_uri, str) and redacted_uri.startswith(("rtsp://", "rtsps://")):
        return redacted_uri
    uri = source_config.get("uri")
    if isinstance(uri, str) and uri.startswith(("rtsp://", "rtsps://")):
        return redact_url_secrets(uri)
    return "rtsp://***"


def _worker_camera_source_payload(
    camera: Camera,
    *,
    rtsp_url: str,
) -> tuple[str, CameraSourceSettings, str | None]:
    source_kind = _source_kind_from_camera(camera)
    if source_kind is CameraSourceKind.RTSP:
        camera_source = CameraSourceSettings(kind=CameraSourceKind.RTSP, uri=rtsp_url)
        return rtsp_url, camera_source, rtsp_url

    camera_source = _camera_source_settings_from_camera(camera, rtsp_url=rtsp_url, for_worker=True)
    normalized = normalize_camera_source(camera_source)
    return normalized.capture_uri, camera_source, None


def _mask_camera_source_url(camera: Camera) -> str:
    if _source_kind_from_camera(camera) is not CameraSourceKind.RTSP:
        redacted_uri = dict(camera.source_config or {}).get("redacted_uri")
        return redacted_uri if isinstance(redacted_uri, str) and redacted_uri else "usb://***"
    return _mask_rtsp_url(camera.rtsp_url_encrypted)


def _camera_source_contract_payload(camera: Camera, rtsp_url: str) -> dict[str, object]:
    source_kind = _source_kind_from_camera(camera)
    source_config = dict(camera.source_config or {})
    source_uri = str(
        source_config.get("redacted_uri")
        or source_config.get("uri")
        or rtsp_url
    )
    redacted_uri = (
        source_uri
        if source_uri in {"usb://***", "csi://***"}
        else _redact_scene_contract_source_uri(source_uri)
    )
    return {
        "kind": source_kind.value,
        "uri": redacted_uri,
        "redacted_uri": redacted_uri,
        "capture_mode": camera.processing_mode.value,
    }


def _redact_scene_contract_source_uri(uri: str) -> str:
    parts = urlsplit(uri)
    if parts.scheme in {"rtsp", "rtsps", "http", "https"}:
        host = parts.hostname or ""
        if ":" in host and not host.startswith("["):
            host = f"[{host}]"
        netloc = host
        if parts.port is not None:
            netloc = f"{netloc}:{parts.port}"
        return urlunsplit((parts.scheme, netloc, parts.path, "", ""))
    return redact_url_secrets(uri)


def _model_contract_payload(model: Model) -> dict[str, object]:
    return {
        "id": str(model.id),
        "name": model.name,
        "version": model.version,
        "format": model.format.value if hasattr(model.format, "value") else str(model.format),
        "capability": _model_capability(model).value,
        "classes": list(model.classes),
        "sha256": model.sha256,
    }


def _runtime_vocabulary_contract_payload(camera: Camera) -> dict[str, object]:
    terms = normalize_vocabulary_terms(getattr(camera, "runtime_vocabulary", None) or [])
    return {
        "terms": terms,
        "source": _runtime_vocabulary_source_value(camera),
        "version": camera.runtime_vocabulary_version,
        "hash": hash_vocabulary(terms),
    }


def _runtime_selection_contract_payload(
    model: Model,
    *,
    runtime_artifacts: list[ModelRuntimeArtifact] | None,
) -> dict[str, object]:
    artifacts = runtime_artifacts or []
    if artifacts:
        first = artifacts[0]
        return {
            "backend": first.runtime_backend,
            "candidate_artifact_ids": [str(artifact.id) for artifact in artifacts],
            "selected_artifact_id": str(first.id),
            "target_profile": first.target_profile,
            "precision": first.precision.value,
            "fallback_reason": None,
        }
    capability_config = _model_capability_config(model)
    return {
        "backend": capability_config.get("runtime_backend") or "onnxruntime",
        "candidate_artifact_ids": [],
        "selected_artifact_id": None,
        "target_profile": None,
        "precision": None,
        "fallback_reason": "no_validated_runtime_artifact",
    }


def _runtime_vocabulary_source_value(camera: Camera) -> str:
    source = camera.runtime_vocabulary_source
    return source.value if hasattr(source, "value") else str(source)


def _runtime_artifact_to_worker_payload(artifact: ModelRuntimeArtifact) -> WorkerRuntimeArtifact:
    return WorkerRuntimeArtifact(
        id=artifact.id,
        scope=artifact.scope,
        kind=artifact.kind,
        capability=artifact.capability,
        runtime_backend=cast(RuntimeBackend, artifact.runtime_backend),
        path=artifact.path,
        target_profile=artifact.target_profile,
        precision=artifact.precision,
        input_shape=dict(artifact.input_shape),
        classes=list(artifact.classes),
        vocabulary_hash=artifact.vocabulary_hash,
        vocabulary_version=artifact.vocabulary_version,
        source_model_sha256=artifact.source_model_sha256,
        sha256=artifact.sha256,
        size_bytes=artifact.size_bytes,
    )


def _model_to_worker_settings(
    model: Model,
    *,
    runtime_vocabulary: RuntimeVocabularyState | None = None,
) -> WorkerModelSettings:
    return WorkerModelSettings(
        name=model.name,
        path=model.path,
        capability=_model_capability(model),
        capability_config=ModelCapabilityConfig.model_validate(_model_capability_config(model)),
        classes=list(model.classes),
        input_shape=dict(model.input_shape),
        runtime_vocabulary=runtime_vocabulary or RuntimeVocabularyState(),
    )


def _worker_runtime_capability(model: Model) -> WorkerRuntimeCapability:
    capability_config = _model_capability_config(model)
    execution_profiles = capability_config.get("execution_profiles")
    return WorkerRuntimeCapability(
        execution_profiles=(
            list(execution_profiles)
            if isinstance(execution_profiles, list)
            else []
        ),
        detector_capabilities=[_model_capability(model)],
        hot_runtime_vocabulary_updates=bool(
            capability_config.get("supports_runtime_vocabulary_updates", False)
        ),
        max_runtime_terms=(
            int(cast(Any, capability_config["max_runtime_terms"]))
            if capability_config.get("max_runtime_terms") is not None
            else None
        ),
    )


def derive_browser_profiles(source: SourceCapability | None) -> DerivedBrowserProfiles:
    candidates = [
        BrowserDeliveryProfile.model_validate(profile)
        for profile in BrowserDeliverySettings().profiles
    ]
    if source is None:
        return DerivedBrowserProfiles(allowed=candidates, unsupported=[])

    allowed: list[BrowserDeliveryProfile] = []
    unsupported: list[BrowserDeliveryProfile] = []
    for candidate in candidates:
        if candidate.kind == "passthrough":
            allowed.append(candidate)
            continue
        if candidate.w is None and candidate.h is None:
            allowed.append(candidate)
            continue
        if (
            candidate.w is not None
            and candidate.h is not None
            and candidate.w <= source.width
            and candidate.h <= source.height
        ):
            allowed.append(candidate)
            continue
        unsupported.append(
            candidate.model_copy(update={"reason": "source_resolution_too_small"})
        )
    return DerivedBrowserProfiles(allowed=allowed, unsupported=unsupported)


def _is_edge_delivery_context(
    *,
    processing_mode: ProcessingMode,
    edge_node_id: UUID | None,
) -> bool:
    return processing_mode is ProcessingMode.EDGE or edge_node_id is not None


def _decorate_browser_delivery_profile(
    profile: BrowserDeliveryProfile,
    *,
    processing_mode: ProcessingMode,
    edge_node_id: UUID | None,
) -> BrowserDeliveryProfile:
    is_edge = _is_edge_delivery_context(
        processing_mode=processing_mode,
        edge_node_id=edge_node_id,
    )
    if profile.id == "native":
        return profile.model_copy(
            update={
                "label": "Native edge passthrough" if is_edge else "Native camera",
                "description": (
                    "Clean edge MediaMTX passthrough relayed to the browser."
                    if is_edge
                    else "Clean camera passthrough through master MediaMTX."
                ),
            }
        )
    if profile.id == "annotated":
        return profile.model_copy(
            update={
                "label": "Annotated edge stream" if is_edge else "Annotated",
                "description": (
                    "Full-rate processed stream published by the edge worker."
                    if is_edge
                    else "Full-rate processed stream published by the central worker."
                ),
            }
        )
    if is_edge:
        return profile.model_copy(
            update={
                "label": f"{profile.id} edge bandwidth saver",
                "description": "Downscaled on the edge node before remote browser delivery.",
            }
        )
    return profile.model_copy(
        update={
            "label": f"{profile.id} viewer preview",
            "description": (
                "Reduces master-to-browser bandwidth only; central inference still ingests "
                "the native camera stream."
            ),
        }
    )


def _build_source_aware_browser_delivery(
    *,
    requested: BrowserDeliverySettings,
    source_capability: SourceCapability | None,
    privacy: dict[str, object],
    processing_mode: ProcessingMode,
    edge_node_id: UUID | None,
    source_kind: CameraSourceKind = CameraSourceKind.RTSP,
) -> BrowserDeliverySettings:
    derived_profiles = derive_browser_profiles(source_capability)
    native_available = (
        requested.allow_native_on_demand
        and not bool(privacy.get("blur_faces", True))
        and not bool(privacy.get("blur_plates", True))
        and source_kind is CameraSourceKind.RTSP
    )
    blocked_profile_ids: set[BrowserDeliveryProfileId] = set()
    native_reason = None
    if not requested.allow_native_on_demand:
        native_reason = "native_disabled"
        blocked_profile_ids.add("native")
    elif not native_available:
        native_reason = (
            "local_source_requires_processed_stream"
            if source_kind is not CameraSourceKind.RTSP
            else "privacy_filtering_required"
        )
        blocked_profile_ids.add("native")

    allowed_profile_ids = {
        profile.id for profile in derived_profiles.allowed if profile.id not in blocked_profile_ids
    }
    default_profile = _resolve_default_browser_profile(
        requested.default_profile,
        allowed_profile_ids,
    )
    decorated_allowed = [
        _decorate_browser_delivery_profile(
            profile,
            processing_mode=processing_mode,
            edge_node_id=edge_node_id,
        )
        for profile in derived_profiles.allowed
    ]
    decorated_unsupported = [
        _decorate_browser_delivery_profile(
            profile,
            processing_mode=processing_mode,
            edge_node_id=edge_node_id,
        )
        for profile in derived_profiles.unsupported
    ]

    return BrowserDeliverySettings(
        default_profile=default_profile,
        allow_native_on_demand=requested.allow_native_on_demand,
        profiles=[
            profile.model_dump(exclude_none=True, mode="python")
            for profile in decorated_allowed
        ],
        unsupported_profiles=[
            profile.model_dump(exclude_none=True, mode="python")
            for profile in decorated_unsupported
        ],
        native_status=NativeAvailability(available=native_available, reason=native_reason),
    )


def _resolve_default_browser_profile(
    requested_profile: BrowserDeliveryProfileId,
    allowed_profile_ids: set[BrowserDeliveryProfileId],
) -> BrowserDeliveryProfileId:
    fallback_order: tuple[BrowserDeliveryProfileId, ...]
    if requested_profile == "native":
        fallback_order = ("native", "annotated", "720p10", "540p5")
    else:
        fallback_order = (requested_profile, "720p10", "540p5", "annotated", "native")
    for profile_id in fallback_order:
        if profile_id in allowed_profile_ids:
            return profile_id
    return "annotated" if "annotated" in allowed_profile_ids else "native"


async def _probe_source_capability(
    rtsp_url: str,
    *,
    settings: Settings,
) -> SourceCapability | None:
    if not settings.enable_startup_services:
        return None
    try:
        return await asyncio.to_thread(probe_rtsp_source, rtsp_url, settings=settings)
    except RuntimeError:
        logger.warning(
            "ffprobe source capability probe failed; falling back to still capture.",
            exc_info=True,
        )
    try:
        return await asyncio.to_thread(_probe_source_capability_from_still, rtsp_url)
    except RuntimeError:
        logger.exception("Failed to probe source capability for camera source.")
        return None


async def _probe_camera_source_capability(
    source: NormalizedCameraSource,
    *,
    settings: Settings,
) -> SourceCapability | None:
    if source.kind is CameraSourceKind.RTSP:
        return await _probe_source_capability(source.capture_uri, settings=settings)
    if not settings.enable_startup_services:
        return None
    if source.kind is CameraSourceKind.USB:
        try:
            return await asyncio.to_thread(probe_usb_source, source.capture_uri)
        except RuntimeError:
            logger.exception("Failed to probe USB camera source capability.")
            return None
    return None


def _probe_source_capability_from_still(rtsp_url: str) -> SourceCapability:
    _image_bytes, width, height = capture_still_image(rtsp_url)
    return SourceCapability(
        width=width,
        height=height,
        aspect_ratio=_aspect_ratio(width, height),
    )


def _aspect_ratio(width: int, height: int) -> str:
    divisor = math.gcd(width, height)
    return f"{width // divisor}:{height // divisor}"


def _resolve_worker_stream_settings(
    *,
    browser_delivery: BrowserDeliverySettings,
    fps_cap: int,
) -> WorkerStreamSettings:
    profile_payloads = browser_delivery.profiles or BrowserDeliverySettings().profiles
    profiles_by_id = {str(profile["id"]): dict(profile) for profile in profile_payloads}
    if "native" not in profiles_by_id:
        profiles_by_id["native"] = {"id": "native", "kind": "passthrough"}
    if "annotated" not in profiles_by_id:
        profiles_by_id["annotated"] = {"id": "annotated", "kind": "transcode"}
    selected = profiles_by_id.get(browser_delivery.default_profile)
    if selected is None:
        selected = profiles_by_id["native"]
    kind = str(selected.get("kind", "passthrough"))
    if kind == "transcode":
        target_width = selected.get("w")
        target_height = selected.get("h")
        target_fps = selected.get("fps")
        return WorkerStreamSettings(
            profile_id=browser_delivery.default_profile,
            kind="transcode",
            width=int(target_width) if target_width is not None else None,
            height=int(target_height) if target_height is not None else None,
            fps=(
                min(max(1, fps_cap), int(target_fps))
                if target_fps is not None
                else max(1, fps_cap)
            ),
        )
    return WorkerStreamSettings(
        profile_id=browser_delivery.default_profile,
        kind="passthrough",
        width=None,
        height=None,
        fps=max(1, fps_cap),
    )


def _normalize_points(
    points: list[list[float]],
    frame_size: FrameSize,
) -> list[list[float]]:
    return [
        [
            round(float(point[0]) / frame_size.width, 6),
            round(float(point[1]) / frame_size.height, 6),
        ]
        for point in points
    ]


def _denormalize_points(
    points: list[list[float]],
    frame_size: FrameSize,
) -> list[list[int]]:
    return [
        [
            round(float(point[0]) * frame_size.width),
            round(float(point[1]) * frame_size.height),
        ]
        for point in points
    ]


def _normalize_zone_payload(zone: dict[str, object]) -> dict[str, object]:
    payload = {key: value for key, value in zone.items() if value is not None}
    frame_size_payload = payload.get("frame_size")
    points = payload.get("points") or payload.get("polygon")
    if frame_size_payload is None or not isinstance(points, list):
        return payload

    frame_size = FrameSize.model_validate(frame_size_payload)
    _validate_points_within_frame(points, frame_size)
    payload["frame_size"] = frame_size.model_dump(mode="python")
    payload["points_normalized"] = _normalize_points(points, frame_size)
    return payload


def _normalize_zones_payload(zones: list[dict[str, object]]) -> list[dict[str, object]]:
    return [_normalize_zone_payload(zone) for zone in zones]


def _camera_detection_regions_payload(regions: list[Any]) -> list[dict[str, object]]:
    return [region.model_dump(exclude_none=True, mode="python") for region in regions]


def _validate_effective_camera_motion_metrics(
    camera: Camera,
    update_data: dict[str, Any],
) -> None:
    vision_profile = SceneVisionProfile.model_validate(
        update_data.get("vision_profile", camera.vision_profile or {})
    )
    homography = update_data["homography"] if "homography" in update_data else camera.homography
    if vision_profile.motion_metrics.speed_enabled and homography is None:
        raise HTTPException(
            status_code=HTTP_422_UNPROCESSABLE,
            detail="Homography is required when speed metrics are enabled.",
        )


def _worker_zone_payload(zone: dict[str, object]) -> dict[str, object]:
    frame_size_payload = zone.get("frame_size")
    points_normalized = zone.get("points_normalized")
    payload = {
        key: value
        for key, value in zone.items()
        if key not in {"frame_size", "points_normalized"}
    }
    if frame_size_payload is None or not isinstance(points_normalized, list):
        return payload

    frame_size = FrameSize.model_validate(frame_size_payload)
    geometry_key = "points" if payload.get("type") == "line" else "polygon"
    payload[geometry_key] = _denormalize_points(points_normalized, frame_size)
    return payload


def _worker_detection_region_payload(region: dict[str, object]) -> dict[str, object]:
    payload = {key: value for key, value in region.items() if value is not None}
    frame_size_payload = payload.get("frame_size")
    points_normalized = payload.get("points_normalized")
    if frame_size_payload is None or not isinstance(points_normalized, list):
        return payload

    frame_size = FrameSize.model_validate(frame_size_payload)
    payload["frame_size"] = frame_size.model_dump(mode="python")
    payload["polygon"] = _denormalize_points(points_normalized, frame_size)
    return payload


def _capture_setup_preview_snapshot(
    camera: Camera,
    settings: Settings,
) -> _SetupPreviewSnapshot:
    rtsp_url = decrypt_rtsp_url(camera.rtsp_url_encrypted, settings)
    image_bytes, width, height = capture_still_image(rtsp_url)
    return _SetupPreviewSnapshot(
        image_bytes=image_bytes,
        frame_size=FrameSize(width=width, height=height),
        captured_at=datetime.now(tz=UTC),
    )


async def _camera_setup_frame_size(camera: Camera, settings: Settings) -> FrameSize:
    probed_frame_size = await asyncio.to_thread(_probe_camera_frame_size, camera, settings)
    if probed_frame_size is not None:
        return probed_frame_size

    for zone in camera.zones:
        frame_size_payload = zone.get("frame_size")
        if frame_size_payload is not None:
            return FrameSize.model_validate(frame_size_payload)

    browser_delivery = BrowserDeliverySettings.model_validate(
        camera.browser_delivery or BrowserDeliverySettings().model_dump(mode="python")
    )
    stream_settings = _resolve_worker_stream_settings(
        browser_delivery=browser_delivery,
        fps_cap=camera.fps_cap,
    )
    if stream_settings.width is not None and stream_settings.height is not None:
        return FrameSize(width=stream_settings.width, height=stream_settings.height)

    return FrameSize(width=1280, height=720)


def _probe_camera_frame_size(camera: Camera, settings: Settings) -> FrameSize | None:
    try:
        rtsp_url = decrypt_rtsp_url(camera.rtsp_url_encrypted, settings)
        width, height = _probe_video_dimensions(rtsp_url)
    except Exception:
        logger.warning(
            "Failed to probe camera frame size for setup preview; falling back to default.",
            exc_info=True,
        )
        return None

    if width <= 0 or height <= 0:
        return None

    return FrameSize(width=width, height=height)


def _validate_points_within_frame(
    points: list[list[float]],
    frame_size: FrameSize,
) -> None:
    for point in points:
        x = float(point[0])
        y = float(point[1])
        if x < 0 or x > frame_size.width or y < 0 or y > frame_size.height:
            raise HTTPException(
                status_code=HTTP_422_UNPROCESSABLE,
                detail="Zone coordinates must fall within the declared frame_size.",
            )


def _homography_to_worker_payload(
    homography: dict[str, object] | None,
) -> dict[str, object] | None:
    if homography is None:
        return None
    src_points = homography.get("src")
    dst_points = homography.get("dst")
    ref_distance_m = homography.get("ref_distance_m")
    if src_points is None or dst_points is None or ref_distance_m is None:
        return None
    return {
        "src_points": src_points,
        "dst_points": dst_points,
        "ref_distance_m": ref_distance_m,
    }


def _mask_rtsp_url(ciphertext: str) -> str:
    if not ciphertext:
        return ""
    return "rtsp://***"


def _apply_tenant_privacy_policy(
    *,
    settings: Settings,
    tenant_context: TenantContext,
    privacy: dict[str, Any],
) -> dict[str, Any]:
    policy = settings.tenant_privacy_policies.get(str(tenant_context.tenant_id))
    if policy is None:
        policy = settings.tenant_privacy_policies.get(tenant_context.tenant_slug)

    if policy is None:
        return privacy

    if bool(policy.get("force_blur_faces")) and not bool(privacy.get("blur_faces")):
        raise HTTPException(
            status_code=HTTP_422_UNPROCESSABLE,
            detail="Tenant policy requires blur_faces=true.",
        )
    if bool(policy.get("force_blur_plates")) and not bool(privacy.get("blur_plates")):
        raise HTTPException(
            status_code=HTTP_422_UNPROCESSABLE,
            detail="Tenant policy requires blur_plates=true.",
        )
    return privacy


def _serialize_csv(rows: list[HistoryPoint]) -> bytes:
    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(["bucket", "camera_id", "class_name", "event_count", "granularity"])
    for row in rows:
        writer.writerow(
            [
                row.bucket.isoformat(),
                row.camera_id,
                row.class_name,
                row.event_count,
                row.granularity,
            ]
        )
    return buffer.getvalue().encode("utf-8")


def _series_response_to_history_points(
    response: HistorySeriesResponse,
) -> list[HistoryPoint]:
    rows: list[HistoryPoint] = []
    for series_row in response.rows:
        if response.class_names:
            for class_name in response.class_names:
                rows.append(
                    HistoryPoint(
                        bucket=series_row.bucket,
                        camera_id=None,
                        class_name=class_name,
                        event_count=series_row.values.get(class_name, 0),
                        granularity=response.granularity,
                        metric=response.metric,
                    )
                )
        else:
            rows.append(
                HistoryPoint(
                    bucket=series_row.bucket,
                    camera_id=None,
                    class_name="total",
                    event_count=series_row.total_count,
                    granularity=response.granularity,
                    metric=response.metric,
                )
            )
    return rows


def _serialize_parquet(rows: list[HistoryPoint]) -> bytes:
    try:
        import pyarrow as pa  # type: ignore[import-untyped]
        import pyarrow.parquet as pq  # type: ignore[import-untyped]
    except ImportError:
        payload = _serialize_csv(rows)
        return b"PAR1" + payload + b"PAR1"

    table = pa.table(
        {
            "bucket": [row.bucket.isoformat() for row in rows],
            "camera_id": [
                str(row.camera_id) if row.camera_id is not None else None
                for row in rows
            ],
            "class_name": [row.class_name for row in rows],
            "event_count": [row.event_count for row in rows],
            "granularity": [row.granularity for row in rows],
        }
    )
    buffer = io.BytesIO()
    pq.write_table(table, buffer)
    return buffer.getvalue()


def _history_view_and_bucket_expr(granularity: str) -> tuple[str, str]:
    if granularity == "1m":
        return ("events_1m", "bucket")
    if granularity == "5m":
        return ("events_1m", "time_bucket(INTERVAL '5 minutes', bucket)")
    if granularity == "1h":
        return ("events_1h", "bucket")
    if granularity == "1d":
        return ("events_1h", "time_bucket(INTERVAL '1 day', bucket)")
    raise ValueError(f"Unsupported history granularity: {granularity}")


def _count_event_view_and_bucket_expr(granularity: str) -> tuple[str, str]:
    if granularity == "1m":
        return ("count_events_1m", "bucket")
    if granularity == "5m":
        return ("count_events_1m", "time_bucket(INTERVAL '5 minutes', bucket)")
    if granularity == "1h":
        return ("count_events_1h", "bucket")
    if granularity == "1d":
        return ("count_events_1h", "time_bucket(INTERVAL '1 day', bucket)")
    raise ValueError(f"Unsupported history granularity: {granularity}")


_GRANULARITY_SECONDS: dict[str, int] = {
    "1m": 60,
    "5m": 300,
    "1h": 3600,
    "1d": 86400,
}
_GRANULARITY_ORDER: tuple[str, ...] = ("1m", "5m", "1h", "1d")
_GRANULARITY_INTERVAL: dict[str, str] = {
    "1m": "1 minute",
    "5m": "5 minutes",
    "1h": "1 hour",
    "1d": "1 day",
}
_MAX_HISTORY_WINDOW = timedelta(days=31)
_MAX_HISTORY_BUCKETS = 500
_MAX_SPEED_CLASSES = 20


def _ensure_history_window(starts_at: datetime, ends_at: datetime) -> None:
    if ends_at - starts_at > _MAX_HISTORY_WINDOW:
        raise HTTPException(status_code=400, detail="Window exceeds 31 days")


def _history_bucket_delta(granularity: str) -> timedelta:
    if granularity == "1m":
        return timedelta(minutes=1)
    if granularity == "5m":
        return timedelta(minutes=5)
    if granularity == "1h":
        return timedelta(hours=1)
    if granularity == "1d":
        return timedelta(days=1)
    raise ValueError(f"Unsupported history granularity: {granularity}")


def _align_history_bucket_start(value: datetime, granularity: str) -> datetime:
    value = value.astimezone(UTC)
    if granularity == "1m":
        return value.replace(second=0, microsecond=0)
    if granularity == "5m":
        minute = value.minute - (value.minute % 5)
        return value.replace(minute=minute, second=0, microsecond=0)
    if granularity == "1h":
        return value.replace(minute=0, second=0, microsecond=0)
    if granularity == "1d":
        return value.replace(hour=0, minute=0, second=0, microsecond=0)
    raise ValueError(f"Unsupported history granularity: {granularity}")


def _history_window_aligned_to_granularity(
    starts_at: datetime,
    ends_at: datetime,
    granularity: str,
) -> bool:
    return (
        _align_history_bucket_start(starts_at, granularity) == starts_at.astimezone(UTC)
        and _align_history_bucket_start(ends_at, granularity) == ends_at.astimezone(UTC)
    )


def _history_bucket_range(
    starts_at: datetime,
    ends_at: datetime,
    granularity: str,
) -> list[datetime]:
    delta = _history_bucket_delta(granularity)
    buckets: list[datetime] = []
    current = _align_history_bucket_start(starts_at, granularity)
    aligned_ends_at = ends_at.astimezone(UTC)
    while current < aligned_ends_at:
        buckets.append(current)
        current += delta
    return buckets


def _summarize_history_coverage(
    coverage_by_bucket: list[HistoryBucketCoverage],
) -> HistoryCoverageStatus:
    statuses = {entry.status for entry in coverage_by_bucket}
    if HistoryCoverageStatus.POPULATED in statuses:
        return HistoryCoverageStatus.POPULATED
    if statuses == {HistoryCoverageStatus.ZERO}:
        return HistoryCoverageStatus.ZERO
    if not statuses:
        return HistoryCoverageStatus.ZERO
    if len(statuses) == 1:
        return next(iter(statuses))
    return HistoryCoverageStatus.NO_TELEMETRY


def _effective_granularity(
    requested: str,
    *,
    starts_at: datetime,
    ends_at: datetime,
) -> tuple[str, bool]:
    span_seconds = max(1.0, (ends_at - starts_at).total_seconds())
    try:
        start_index = _GRANULARITY_ORDER.index(requested)
    except ValueError as exc:
        raise ValueError(f"Unsupported granularity: {requested}") from exc
    for candidate in _GRANULARITY_ORDER[start_index:]:
        if span_seconds / _GRANULARITY_SECONDS[candidate] <= _MAX_HISTORY_BUCKETS:
            return candidate, candidate != requested
    return _GRANULARITY_ORDER[-1], _GRANULARITY_ORDER[-1] != requested


def _tenant_name_from_slug(slug: str) -> str:
    tokens = [token for token in slug.replace("_", "-").split("-") if token]
    if not tokens:
        return "Tenant"
    return " ".join(token.capitalize() for token in tokens)


def _parse_optional_uuid(raw_value: str | None) -> UUID | None:
    if raw_value is None:
        return None
    try:
        return UUID(raw_value)
    except ValueError:
        return None


def _generate_secret(prefix: str) -> str:
    return f"{prefix}_{secrets.token_urlsafe(24)}"
