from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID, uuid4

import pytest

from argus.api.contracts import (
    FleetCameraWorkerSummary,
    FleetOverviewResponse,
    FleetSummary,
    WorkerCameraSettings,
    WorkerConfigResponse,
    WorkerDesiredState,
    WorkerModelSettings,
    WorkerPrivacySettings,
    WorkerRuntimeStatus,
    WorkerStreamSettings,
    WorkerTrackerSettings,
)
from argus.models.enums import DetectorCapability, ProcessingMode, TrackerType
from argus.streaming.mediamtx import PublishProfile, StreamMode, StreamRegistration
from argus.supervisor.stream_provisioner import SupervisorStreamProvisioner


@pytest.mark.asyncio
async def test_provisioner_registers_edge_stream_paths_even_when_worker_not_desired() -> None:
    edge_node_id = uuid4()
    camera_id = uuid4()
    config = _worker_config(camera_id)
    operations = _FakeOperations({camera_id: config})
    stream_client = _FakeStreamClient()
    provisioner = SupervisorStreamProvisioner(
        operations=operations,
        stream_client=stream_client,
        edge_node_id=edge_node_id,
        publish_profile=PublishProfile.JETSON_NANO,
    )

    await provisioner.ensure_fleet_streams(
        _fleet_overview(
            _fleet_worker(
                camera_id=camera_id,
                edge_node_id=edge_node_id,
                desired_state=WorkerDesiredState.NOT_DESIRED,
            )
        )
    )

    assert operations.requested_camera_ids == [camera_id]
    assert stream_client.calls == [
        {
            "camera_id": camera_id,
            "rtsp_url": "rtsp://camera.local/live",
            "profile": PublishProfile.JETSON_NANO,
            "stream_kind": "passthrough",
            "target_fps": 25,
            "target_width": 1280,
            "target_height": 720,
            "privacy_requires_filtering": False,
        }
    ]


@pytest.mark.asyncio
async def test_provisioner_ignores_workers_owned_by_another_edge_node() -> None:
    camera_id = uuid4()
    operations = _FakeOperations({camera_id: _worker_config(camera_id)})
    stream_client = _FakeStreamClient()
    provisioner = SupervisorStreamProvisioner(
        operations=operations,
        stream_client=stream_client,
        edge_node_id=uuid4(),
        publish_profile=PublishProfile.JETSON_NANO,
    )

    await provisioner.ensure_fleet_streams(
        _fleet_overview(
            _fleet_worker(
                camera_id=camera_id,
                edge_node_id=uuid4(),
                desired_state=WorkerDesiredState.SUPERVISED,
            )
        )
    )

    assert operations.requested_camera_ids == []
    assert stream_client.calls == []


class _FakeOperations:
    def __init__(self, configs: dict[UUID, WorkerConfigResponse]) -> None:
        self.configs = configs
        self.requested_camera_ids: list[UUID] = []

    async def fetch_worker_config(self, camera_id: UUID) -> WorkerConfigResponse:
        self.requested_camera_ids.append(camera_id)
        return self.configs[camera_id]


class _FakeStreamClient:
    def __init__(self) -> None:
        self.calls: list[dict[str, object]] = []

    async def register_stream(
        self,
        *,
        camera_id: UUID,
        rtsp_url: str,
        profile: PublishProfile,
        stream_kind: str,
        privacy,
        target_fps: int = 25,
        target_width: int | None = None,
        target_height: int | None = None,
    ) -> StreamRegistration:
        self.calls.append(
            {
                "camera_id": camera_id,
                "rtsp_url": rtsp_url,
                "profile": profile,
                "stream_kind": stream_kind,
                "target_fps": target_fps,
                "target_width": target_width,
                "target_height": target_height,
                "privacy_requires_filtering": privacy.requires_filtering,
            }
        )
        return StreamRegistration(
            camera_id=camera_id,
            mode=StreamMode.PASSTHROUGH,
            read_path=f"rtsp://mediamtx.internal:8554/cameras/{camera_id}/passthrough",
        )


def _worker_config(camera_id: UUID) -> WorkerConfigResponse:
    return WorkerConfigResponse(
        camera_id=camera_id,
        mode=ProcessingMode.EDGE,
        camera=WorkerCameraSettings(rtsp_url="rtsp://camera.local/live"),
        stream=WorkerStreamSettings(
            profile_id="native",
            kind="passthrough",
            width=1280,
            height=720,
            fps=25,
        ),
        model=WorkerModelSettings(
            name="YOLO11n COCO",
            path="/models/yolo11n.onnx",
            capability=DetectorCapability.FIXED_VOCAB,
            classes=["person"],
            input_shape={"width": 640, "height": 640},
        ),
        tracker=WorkerTrackerSettings(tracker_type=TrackerType.BOTSORT),
        privacy=WorkerPrivacySettings(blur_faces=False, blur_plates=False),
    )


def _fleet_worker(
    *,
    camera_id: UUID,
    edge_node_id: UUID,
    desired_state: WorkerDesiredState,
) -> FleetCameraWorkerSummary:
    return FleetCameraWorkerSummary(
        camera_id=camera_id,
        camera_name="Room1",
        site_id=uuid4(),
        node_id=edge_node_id,
        processing_mode=ProcessingMode.EDGE,
        desired_state=desired_state,
        runtime_status=WorkerRuntimeStatus.OFFLINE,
        lifecycle_owner="edge_supervisor",
    )


def _fleet_overview(worker: FleetCameraWorkerSummary) -> FleetOverviewResponse:
    return FleetOverviewResponse(
        mode="supervised",
        generated_at=datetime(2026, 5, 13, 12, 0, tzinfo=UTC),
        summary=FleetSummary(
            desired_workers=0,
            running_workers=0,
            stale_nodes=0,
            offline_nodes=0,
            native_unavailable_cameras=0,
        ),
        nodes=[],
        camera_workers=[worker],
        delivery_diagnostics=[],
    )
