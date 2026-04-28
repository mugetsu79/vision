from __future__ import annotations

import asyncio
import csv
import io
import logging
import math
import secrets
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING, Any, cast
from uuid import UUID

import httpx
from fastapi import HTTPException, status
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
    CameraUpdate,
    DerivedBrowserProfiles,
    EdgeHeartbeatRequest,
    EdgeHeartbeatResponse,
    EdgeRegisterRequest,
    EdgeRegisterResponse,
    ExportArtifact,
    FrameSize,
    HistoryBucketCoverage,
    HistoryClassesResponse,
    HistoryPoint,
    HistorySeriesResponse,
    HistorySeriesRow,
    HomographyPayload,
    IncidentResponse,
    ModelCreate,
    ModelResponse,
    ModelUpdate,
    NativeAvailability,
    PrivacySettings,
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
    WorkerModelSettings,
    WorkerPrivacySettings,
    WorkerPublishSettings,
    WorkerStreamSettings,
    WorkerTrackerSettings,
)
from argus.core.config import Settings
from argus.core.db import DatabaseManager
from argus.core.events import EventMessage, NatsJetStreamClient
from argus.core.security import decrypt_rtsp_url, encrypt_rtsp_url, hash_api_key
from argus.inference.publisher import TelemetryFrame
from argus.models.enums import (
    CountEventType,
    HistoryCoverageStatus,
    HistoryMetric,
    ModelFormat,
    ModelTask,
    ProcessingMode,
)
from argus.models.tables import (
    APIKey,
    AuditLog,
    Camera,
    EdgeNode,
    Incident,
    Model,
    Site,
    Tenant,
    TrackingEvent,
)
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
from argus.vision.camera import _probe_video_dimensions, capture_still_image
from argus.vision.model_metadata import resolve_model_classes
from argus.vision.source_probe import probe_rtsp_source

HTTP_422_UNPROCESSABLE = getattr(status, "HTTP_422_UNPROCESSABLE_CONTENT", 422)

if TYPE_CHECKING:
    from argus.services.query import QueryService


logger = logging.getLogger(__name__)

_SETUP_PREVIEW_CACHE_TTL = timedelta(minutes=2)


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


@dataclass(slots=True)
class AppServices:
    tenancy: TenancyService
    sites: SiteService
    cameras: CameraService
    models: ModelService
    edge: EdgeService
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

    async def record(
        self,
        *,
        tenant_context: TenantContext,
        action: str,
        target: str,
        meta: dict[str, Any] | None = None,
    ) -> None:
        async with self.session_factory() as session:
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

    async def create_model(self, payload: ModelCreate) -> ModelResponse:
        resolved_classes, _ = resolve_model_classes(payload.path, payload.format, payload.classes)
        async with self.session_factory() as session:
            model = Model(
                name=payload.name,
                version=payload.version,
                task=payload.task,
                path=payload.path,
                format=payload.format,
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
            if any(field_name in update_data for field_name in {"path", "format", "classes"}):
                resolved_format = update_data.get("format", model.format)
                declared_classes = (
                    update_data["classes"]
                    if "classes" in update_data
                    else None
                    if resolved_format is ModelFormat.ONNX
                    else list(model.classes)
                )
                resolved_classes = resolve_model_classes(
                    str(update_data.get("path", model.path)),
                    resolved_format,
                    declared_classes,
                )
                model.classes = resolved_classes[0]
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

        rtsp_url = decrypt_rtsp_url(camera.rtsp_url_encrypted, self.settings)
        return _camera_to_worker_config(
            camera=camera,
            primary_model=primary_model,
            secondary_model=secondary_model,
            settings=self.settings,
            rtsp_url=rtsp_url,
        )

    async def probe_camera_source(
        self,
        tenant_context: TenantContext,
        payload: CameraSourceProbeRequest,
    ) -> CameraSourceProbeResponse:
        rtsp_url = payload.rtsp_url.strip() if payload.rtsp_url is not None else None
        if rtsp_url == "":
            rtsp_url = None

        requested_delivery = payload.browser_delivery or BrowserDeliverySettings()
        requested_privacy = (
            payload.privacy.model_dump(mode="python")
            if payload.privacy is not None
            else PrivacySettings().model_dump(mode="python")
        )
        existing_source_capability: SourceCapability | None = None
        should_persist_probe = False

        if payload.camera_id is not None:
            async with self.session_factory() as session:
                camera = await _load_camera(session, tenant_context.tenant_id, payload.camera_id)
                supplied_rtsp_url = rtsp_url is not None
                if rtsp_url is None:
                    rtsp_url = decrypt_rtsp_url(camera.rtsp_url_encrypted, self.settings)
                    should_persist_probe = True
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

                source_capability = (
                    await _probe_source_capability(rtsp_url, settings=self.settings)
                    if rtsp_url is not None
                    else None
                )
                if source_capability is None:
                    source_capability = existing_source_capability
                elif should_persist_probe and not supplied_rtsp_url:
                    camera.source_capability = source_capability.model_dump(mode="python")
                    await session.commit()
                    await session.refresh(camera)
        else:
            if rtsp_url is None:
                raise HTTPException(
                    status_code=HTTP_422_UNPROCESSABLE,
                    detail="rtsp_url is required when camera_id is not provided.",
                )
            source_capability = await _probe_source_capability(rtsp_url, settings=self.settings)

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
            _validate_active_classes_subset(
                active_classes=payload.active_classes,
                primary_model_classes=primary_model.classes,
            )
            if payload.secondary_model_id is not None:
                secondary_model = await _load_model(session, payload.secondary_model_id)
                if secondary_model.task not in {ModelTask.ATTRIBUTE, ModelTask.CLASSIFY}:
                    raise HTTPException(
                        status_code=HTTP_422_UNPROCESSABLE,
                        detail="Secondary model must be classify or attribute.",
                    )
            privacy = _apply_tenant_privacy_policy(
                settings=self.settings,
                tenant_context=tenant_context,
                privacy=payload.privacy.model_dump(mode="python"),
            )
            source_capability = await _probe_source_capability(
                payload.rtsp_url,
                settings=self.settings,
            )
            browser_delivery = _build_source_aware_browser_delivery(
                requested=payload.browser_delivery,
                source_capability=source_capability,
                privacy=privacy,
            )
            camera = Camera(
                site_id=payload.site_id,
                edge_node_id=None,
                name=payload.name,
                rtsp_url_encrypted=encrypt_rtsp_url(payload.rtsp_url, self.settings),
                processing_mode=payload.processing_mode,
                primary_model_id=payload.primary_model_id,
                secondary_model_id=payload.secondary_model_id,
                tracker_type=payload.tracker_type,
                active_classes=payload.active_classes,
                attribute_rules=payload.attribute_rules,
                zones=_normalize_zones_payload(
                    [zone.model_dump(mode="python") for zone in payload.zones]
                ),
                homography=payload.homography.model_dump(mode="python"),
                privacy=privacy,
                browser_delivery=browser_delivery.model_dump(mode="python"),
                source_capability=(
                    source_capability.model_dump(mode="python")
                    if source_capability is not None
                    else None
                ),
                frame_skip=payload.frame_skip,
                fps_cap=payload.fps_cap,
            )
            session.add(camera)
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
            primary_model_id = update_data.get("primary_model_id", camera.primary_model_id)
            primary_model = await _load_model(session, primary_model_id)
            if primary_model.task is not ModelTask.DETECT:
                raise HTTPException(
                    status_code=HTTP_422_UNPROCESSABLE,
                    detail="Primary model must be a detector.",
                )
            active_classes = update_data.get("active_classes", camera.active_classes)
            _validate_active_classes_subset(
                active_classes=active_classes,
                primary_model_classes=primary_model.classes,
            )
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
            if "rtsp_url" in update_data:
                rtsp_url = str(update_data.pop("rtsp_url"))
                camera.rtsp_url_encrypted = encrypt_rtsp_url(
                    rtsp_url,
                    self.settings,
                )
                source_capability = await _probe_source_capability(
                    rtsp_url,
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
                ).model_dump(mode="python")
            if "homography" in update_data and update_data["homography"] is not None:
                update_data["homography"] = dict(update_data["homography"])
            if "zones" in update_data and update_data["zones"] is not None:
                update_data["zones"] = _normalize_zones_payload(update_data["zones"])

            for field_name, value in update_data.items():
                setattr(camera, field_name, value)

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
        command = CameraCommandPayload(
            active_classes=list(camera.active_classes),
            tracker_type=camera.tracker_type,
            privacy=WorkerPrivacySettings(
                blur_faces=bool(camera.privacy.get("blur_faces", True)),
                blur_plates=bool(camera.privacy.get("blur_plates", True)),
            ),
            attribute_rules=list(camera.attribute_rules),
            zones=cast(Any, [_worker_zone_payload(zone) for zone in camera.zones]),
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

        if metric is HistoryMetric.COUNT_EVENTS:
            if include_speed:
                rows = await self._fetch_series_rows_with_speed_from_count_events(
                    tenant_id=tenant_context.tenant_id,
                    camera_ids=camera_ids,
                    class_names=class_names,
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
                    class_names=class_names,
                    granularity=effective_granularity,
                    starts_at=starts_at,
                    ends_at=ends_at,
                    metric=metric,
                )
            else:
                rows = await self._fetch_series_rows_from_count_events(
                    tenant_id=tenant_context.tenant_id,
                    camera_ids=camera_ids,
                    class_names=class_names,
                    granularity=effective_granularity,
                    starts_at=starts_at,
                    ends_at=ends_at,
                )
        elif include_speed:
            rows = await self._fetch_series_rows_with_speed(
                tenant_id=tenant_context.tenant_id,
                camera_ids=camera_ids,
                class_names=class_names,
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
                class_names=class_names,
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
            status = (
                HistoryCoverageStatus.POPULATED
                if total_count > 0
                else HistoryCoverageStatus.ZERO
            )
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
    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self.session_factory = session_factory

    async def list_incidents(
        self,
        tenant_context: TenantContext,
        *,
        camera_id: UUID | None,
        incident_type: str | None,
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
            incidents = (await session.execute(statement)).all()
        return [
            IncidentResponse(
                id=incident.id,
                camera_id=incident.camera_id,
                camera_name=camera_name,
                ts=incident.ts,
                type=incident.type,
                payload=incident.payload,
                snapshot_url=incident.snapshot_url,
                clip_url=incident.clip_url,
                storage_bytes=incident.storage_bytes,
            )
            for incident, camera_name in incidents
        ]


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
            processed_native=_uses_processed_native_delivery(camera),
        )
        return resolve_stream_access(
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

        nats_subscription = await self.event_client.subscribe("evt.tracking.*", handle_message)
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
    return AppServices(
        tenancy=TenancyService(db.session_factory, settings),
        sites=SiteService(db.session_factory, audit_logger),
        cameras=CameraService(db.session_factory, settings, audit_logger, events),
        models=ModelService(db.session_factory, audit_logger),
        edge=EdgeService(db.session_factory, settings, events, audit_logger),
        history=HistoryService(db.session_factory),
        incidents=IncidentService(db.session_factory),
        streams=StreamService(db.session_factory, mediamtx, settings),
        query=query_service,
        telemetry=NatsTelemetryService(
            session_factory=db.session_factory,
            event_client=events,
            settings=settings,
        ),
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
        classes=list(model.classes),
        input_shape=dict(model.input_shape),
        sha256=model.sha256,
        size_bytes=model.size_bytes,
        license=model.license,
    )


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


def _camera_to_response(camera: Camera) -> CameraResponse:
    if camera.homography is None:
        raise ValueError("Camera homography must be set.")
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
    )
    return CameraResponse(
        id=camera.id,
        site_id=camera.site_id,
        edge_node_id=camera.edge_node_id,
        name=camera.name,
        rtsp_url_masked=_mask_rtsp_url(camera.rtsp_url_encrypted),
        processing_mode=camera.processing_mode,
        primary_model_id=camera.primary_model_id,
        secondary_model_id=camera.secondary_model_id,
        tracker_type=camera.tracker_type,
        active_classes=list(camera.active_classes),
        attribute_rules=list(camera.attribute_rules),
        zones=cast(Any, list(camera.zones)),
        homography=HomographyPayload.model_validate(camera.homography),
        privacy=privacy,
        browser_delivery=browser_delivery,
        source_capability=source_capability,
        frame_skip=camera.frame_skip,
        fps_cap=camera.fps_cap,
        created_at=camera.created_at,
        updated_at=camera.updated_at,
    )


def _camera_to_worker_config(
    *,
    camera: Camera,
    primary_model: Model,
    secondary_model: Model | None,
    settings: Settings,
    rtsp_url: str,
) -> WorkerConfigResponse:
    browser_delivery = BrowserDeliverySettings.model_validate(
        camera.browser_delivery or BrowserDeliverySettings().model_dump(mode="python")
    )
    return WorkerConfigResponse(
        camera_id=camera.id,
        mode=camera.processing_mode,
        camera=WorkerCameraSettings(
            rtsp_url=rtsp_url,
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
            processed_native=_uses_processed_native_delivery(camera),
        ),
        model=_model_to_worker_settings(primary_model),
        secondary_model=(
            _model_to_worker_settings(secondary_model)
            if secondary_model is not None
            else None
        ),
        tracker=WorkerTrackerSettings(
            tracker_type=camera.tracker_type,
            frame_rate=camera.fps_cap,
        ),
        privacy=WorkerPrivacySettings(
            blur_faces=bool(camera.privacy.get("blur_faces", True)),
            blur_plates=bool(camera.privacy.get("blur_plates", True)),
        ),
        active_classes=list(camera.active_classes),
        attribute_rules=list(camera.attribute_rules),
        zones=cast(Any, [_worker_zone_payload(zone) for zone in camera.zones]),
        homography=_homography_to_worker_payload(camera.homography),
    )


def _model_to_worker_settings(model: Model) -> WorkerModelSettings:
    return WorkerModelSettings(
        name=model.name,
        path=model.path,
        classes=list(model.classes),
        input_shape=dict(model.input_shape),
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


def _build_source_aware_browser_delivery(
    *,
    requested: BrowserDeliverySettings,
    source_capability: SourceCapability | None,
    privacy: dict[str, object],
) -> BrowserDeliverySettings:
    derived_profiles = derive_browser_profiles(source_capability)
    allowed_profile_ids = {profile.id for profile in derived_profiles.allowed}
    default_profile = _resolve_default_browser_profile(
        requested.default_profile,
        allowed_profile_ids,
    )
    native_available = (
        requested.allow_native_on_demand
        and not bool(privacy.get("blur_faces", True))
        and not bool(privacy.get("blur_plates", True))
    )
    native_reason = None
    if not requested.allow_native_on_demand:
        native_reason = "native_disabled"
    elif not native_available:
        native_reason = "privacy_filtering_required"

    return BrowserDeliverySettings(
        default_profile=default_profile,
        allow_native_on_demand=requested.allow_native_on_demand,
        profiles=[
            profile.model_dump(exclude_none=True, mode="python")
            for profile in derived_profiles.allowed
        ],
        unsupported_profiles=[
            profile.model_dump(exclude_none=True, mode="python")
            for profile in derived_profiles.unsupported
        ],
        native_status=NativeAvailability(available=native_available, reason=native_reason),
    )


def _resolve_default_browser_profile(
    requested_profile: BrowserDeliveryProfileId,
    allowed_profile_ids: set[BrowserDeliveryProfileId],
) -> BrowserDeliveryProfileId:
    for profile_id in (requested_profile, "720p10", "540p5", "native"):
        if profile_id in allowed_profile_ids:
            return profile_id
    return "native"


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
    processed_native: bool = False,
) -> WorkerStreamSettings:
    profile_payloads = browser_delivery.profiles or BrowserDeliverySettings().profiles
    profiles_by_id = {str(profile["id"]): dict(profile) for profile in profile_payloads}
    if "native" not in profiles_by_id:
        profiles_by_id["native"] = {"id": "native", "kind": "passthrough"}
    selected = profiles_by_id.get(browser_delivery.default_profile)
    if selected is None:
        selected = profiles_by_id["native"]
    if browser_delivery.default_profile == "native" and processed_native:
        return WorkerStreamSettings(
            profile_id="native",
            kind="transcode",
            width=None,
            height=None,
            fps=max(1, fps_cap),
        )
    kind = str(selected.get("kind", "passthrough"))
    if kind == "transcode":
        return WorkerStreamSettings(
            profile_id=browser_delivery.default_profile,
            kind="transcode",
            width=int(selected["w"]),
            height=int(selected["h"]),
            fps=min(max(1, fps_cap), int(selected["fps"])),
        )
    return WorkerStreamSettings(
        profile_id=browser_delivery.default_profile,
        kind="passthrough",
        width=None,
        height=None,
        fps=max(1, fps_cap),
    )


def _uses_processed_native_delivery(camera: Camera) -> bool:
    return camera.processing_mode is ProcessingMode.CENTRAL and camera.edge_node_id is None


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
        processed_native=_uses_processed_native_delivery(camera),
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
