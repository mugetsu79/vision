from __future__ import annotations

import logging
from collections.abc import Callable
from time import monotonic
from typing import Protocol
from uuid import UUID

from argus.api.contracts import (
    FleetCameraWorkerSummary,
    FleetOverviewResponse,
    WorkerConfigResponse,
)
from argus.streaming.mediamtx import (
    PrivacyPolicy,
    PublishProfile,
    StreamRegistration,
    sanitize_stream_log_message,
)

LOGGER = logging.getLogger(__name__)
_STREAM_REVALIDATE_SECONDS = 60.0


class WorkerConfigClient(Protocol):
    async def fetch_worker_config(self, camera_id: UUID) -> WorkerConfigResponse: ...


class StreamClient(Protocol):
    async def register_stream(
        self,
        *,
        camera_id: UUID,
        rtsp_url: str,
        profile: PublishProfile,
        stream_kind: str,
        privacy: PrivacyPolicy,
        target_fps: int = 25,
        profile_id: str | None = None,
        target_width: int | None = None,
        target_height: int | None = None,
    ) -> StreamRegistration: ...


class SupervisorStreamProvisioner:
    def __init__(
        self,
        *,
        operations: WorkerConfigClient,
        stream_client: StreamClient,
        edge_node_id: UUID | None,
        publish_profile: PublishProfile,
        stream_revalidate_seconds: float = _STREAM_REVALIDATE_SECONDS,
        clock: Callable[[], float] | None = None,
    ) -> None:
        self.operations = operations
        self.stream_client = stream_client
        self.edge_node_id = edge_node_id
        self.publish_profile = publish_profile
        self._stream_revalidate_seconds = max(0.0, stream_revalidate_seconds)
        self._clock = clock or monotonic
        self._desired_stream_signatures: dict[UUID, tuple[object, ...]] = {}
        self._stream_signatures: dict[UUID, tuple[object, ...]] = {}
        self._stream_signature_checked_at: dict[UUID, float] = {}

    async def ensure_fleet_streams(self, fleet: FleetOverviewResponse | None) -> None:
        if fleet is None:
            return
        for worker in fleet.camera_workers:
            if not _worker_owner_matches_supervisor(worker, edge_node_id=self.edge_node_id):
                continue
            await self._ensure_worker_stream(worker)

    async def _ensure_worker_stream(self, worker: FleetCameraWorkerSummary) -> None:
        try:
            config = await self.operations.fetch_worker_config(worker.camera_id)
            source_uri = config.camera.source_uri or config.camera.rtsp_url
            if source_uri is None:
                LOGGER.warning(
                    "Skipping MediaMTX stream provisioning without a camera source",
                    extra={"camera_id": str(worker.camera_id)},
                )
                return
            desired_signature = (
                source_uri,
                self.publish_profile.value,
                config.stream.kind,
                config.stream.profile_id,
                config.stream.fps,
                config.stream.width,
                config.stream.height,
                config.privacy.model_dump_json(),
            )
            if (
                self._desired_stream_signatures.get(worker.camera_id) == desired_signature
                and worker.camera_id in self._stream_signatures
                and self._stream_signature_cache_fresh(worker.camera_id)
            ):
                return
            registration = await self.stream_client.register_stream(
                camera_id=config.camera_id,
                rtsp_url=source_uri,
                profile=self.publish_profile,
                stream_kind=config.stream.kind,
                privacy=PrivacyPolicy.model_validate(config.privacy.model_dump(mode="python")),
                target_fps=config.stream.fps,
                profile_id=config.stream.profile_id,
                target_width=config.stream.width,
                target_height=config.stream.height,
            )
            stream_signature = (
                *desired_signature,
                registration.path_name,
                registration.mode.value,
                registration.read_path,
                registration.publish_path,
            )
            previous_stream_signature = self._stream_signatures.get(worker.camera_id)
            self._desired_stream_signatures[worker.camera_id] = desired_signature
            self._stream_signatures[worker.camera_id] = stream_signature
            self._stream_signature_checked_at[worker.camera_id] = self._clock()
            if previous_stream_signature != stream_signature:
                LOGGER.info(
                    "Provisioned MediaMTX stream path camera_id=%s path=%s mode=%s",
                    worker.camera_id,
                    registration.path_name,
                    registration.mode.value,
                )
        except Exception as exc:
            LOGGER.warning(
                "Failed to provision MediaMTX stream path camera_id=%s: %s",
                worker.camera_id,
                sanitize_stream_log_message(str(exc)),
            )

    def _stream_signature_cache_fresh(self, camera_id: UUID) -> bool:
        checked_at = self._stream_signature_checked_at.get(camera_id)
        if checked_at is None:
            return False
        return self._clock() - checked_at < self._stream_revalidate_seconds


def _worker_owner_matches_supervisor(
    worker: FleetCameraWorkerSummary,
    *,
    edge_node_id: UUID | None,
) -> bool:
    if edge_node_id is None:
        return worker.lifecycle_owner == "central_supervisor" and worker.node_id is None
    return worker.lifecycle_owner == "edge_supervisor" and worker.node_id == edge_node_id
