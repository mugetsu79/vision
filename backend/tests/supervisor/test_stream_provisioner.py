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
            "profile_id": "native",
            "stream_kind": "passthrough",
            "target_fps": 25,
            "target_width": 1280,
            "target_height": 720,
            "privacy_requires_filtering": False,
        }
    ]


@pytest.mark.asyncio
async def test_provisioner_skips_repeat_edge_registration_for_identical_config(
    caplog: pytest.LogCaptureFixture,
) -> None:
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
    fleet = _fleet_overview(
        _fleet_worker(
            camera_id=camera_id,
            edge_node_id=edge_node_id,
            desired_state=WorkerDesiredState.SUPERVISED,
        )
    )

    with caplog.at_level("INFO", logger="argus.supervisor.stream_provisioner"):
        await provisioner.ensure_fleet_streams(fleet)
        await provisioner.ensure_fleet_streams(fleet)

    assert len(stream_client.calls) == 1
    assert caplog.messages.count(
        "Provisioned MediaMTX stream path "
        f"camera_id={camera_id} "
        f"path=cameras/{camera_id}/passthrough "
        "mode=passthrough"
    ) == 1


@pytest.mark.asyncio
async def test_provisioner_skips_repeat_central_registration_for_identical_config(
    caplog: pytest.LogCaptureFixture,
) -> None:
    camera_id = uuid4()
    config = _worker_config(camera_id)
    operations = _FakeOperations({camera_id: config})
    stream_client = _FakeStreamClient()
    provisioner = SupervisorStreamProvisioner(
        operations=operations,
        stream_client=stream_client,
        edge_node_id=None,
        publish_profile=PublishProfile.CENTRAL_GPU,
    )
    fleet = _fleet_overview(
        _fleet_worker(
            camera_id=camera_id,
            edge_node_id=None,
            desired_state=WorkerDesiredState.SUPERVISED,
            lifecycle_owner="central_supervisor",
            processing_mode=ProcessingMode.CENTRAL,
        )
    )

    with caplog.at_level("INFO", logger="argus.supervisor.stream_provisioner"):
        await provisioner.ensure_fleet_streams(fleet)
        await provisioner.ensure_fleet_streams(fleet)

    assert len(stream_client.calls) == 1
    assert caplog.messages.count(
        "Provisioned MediaMTX stream path "
        f"camera_id={camera_id} "
        f"path=cameras/{camera_id}/passthrough "
        "mode=passthrough"
    ) == 1


@pytest.mark.asyncio
async def test_provisioner_revalidates_identical_config_after_cache_expiry(
    caplog: pytest.LogCaptureFixture,
) -> None:
    now = 100.0
    camera_id = uuid4()
    config = _worker_config(camera_id)
    operations = _FakeOperations({camera_id: config})
    stream_client = _FakeStreamClient()
    provisioner = SupervisorStreamProvisioner(
        operations=operations,
        stream_client=stream_client,
        edge_node_id=None,
        publish_profile=PublishProfile.CENTRAL_GPU,
        stream_revalidate_seconds=10.0,
        clock=lambda: now,
    )
    fleet = _fleet_overview(
        _fleet_worker(
            camera_id=camera_id,
            edge_node_id=None,
            desired_state=WorkerDesiredState.SUPERVISED,
            lifecycle_owner="central_supervisor",
            processing_mode=ProcessingMode.CENTRAL,
        )
    )

    with caplog.at_level("INFO", logger="argus.supervisor.stream_provisioner"):
        await provisioner.ensure_fleet_streams(fleet)
        await provisioner.ensure_fleet_streams(fleet)
        now = 111.0
        await provisioner.ensure_fleet_streams(fleet)

    assert len(stream_client.calls) == 2
    assert caplog.messages.count(
        "Provisioned MediaMTX stream path "
        f"camera_id={camera_id} "
        f"path=cameras/{camera_id}/passthrough "
        "mode=passthrough"
    ) == 1


@pytest.mark.asyncio
async def test_provisioner_redacts_credentials_in_registration_errors(
    caplog: pytest.LogCaptureFixture,
) -> None:
    edge_node_id = uuid4()
    camera_id = uuid4()
    config = _worker_config(camera_id, rtsp_url="rtsp://user:secret@camera.local/live?token=abc123")
    operations = _FakeOperations({camera_id: config})
    stream_client = _FailingStreamClient(
        "pull failed for rtsp://user:secret@camera.local/live?token=abc123"
    )
    provisioner = SupervisorStreamProvisioner(
        operations=operations,
        stream_client=stream_client,
        edge_node_id=edge_node_id,
        publish_profile=PublishProfile.JETSON_NANO,
    )

    with caplog.at_level("WARNING", logger="argus.supervisor.stream_provisioner"):
        await provisioner.ensure_fleet_streams(
            _fleet_overview(
                _fleet_worker(
                    camera_id=camera_id,
                    edge_node_id=edge_node_id,
                    desired_state=WorkerDesiredState.SUPERVISED,
                )
            )
        )

    assert "rtsp://***:***@camera.local/live?token=***" in caplog.text
    assert "rtsp://user:secret@" not in caplog.text
    assert "token=abc123" not in caplog.text


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
        profile_id: str | None = None,
        target_width: int | None = None,
        target_height: int | None = None,
    ) -> StreamRegistration:
        self.calls.append(
            {
                "camera_id": camera_id,
                "rtsp_url": rtsp_url,
                "profile": profile,
                "profile_id": profile_id,
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
            path_name=f"cameras/{camera_id}/passthrough",
            read_path=f"rtsp://mediamtx.internal:8554/cameras/{camera_id}/passthrough",
        )


class _FailingStreamClient:
    def __init__(self, message: str) -> None:
        self.message = message

    async def register_stream(
        self,
        *,
        camera_id: UUID,
        rtsp_url: str,
        profile: PublishProfile,
        stream_kind: str,
        privacy,
        target_fps: int = 25,
        profile_id: str | None = None,
        target_width: int | None = None,
        target_height: int | None = None,
    ) -> StreamRegistration:
        del (
            camera_id,
            rtsp_url,
            profile,
            stream_kind,
            privacy,
            target_fps,
            profile_id,
            target_width,
            target_height,
        )
        raise RuntimeError(self.message)


def _worker_config(
    camera_id: UUID,
    *,
    rtsp_url: str = "rtsp://camera.local/live",
) -> WorkerConfigResponse:
    return WorkerConfigResponse(
        camera_id=camera_id,
        mode=ProcessingMode.EDGE,
        camera=WorkerCameraSettings(rtsp_url=rtsp_url),
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
    edge_node_id: UUID | None,
    desired_state: WorkerDesiredState,
    lifecycle_owner: str = "edge_supervisor",
    processing_mode: ProcessingMode = ProcessingMode.EDGE,
) -> FleetCameraWorkerSummary:
    return FleetCameraWorkerSummary(
        camera_id=camera_id,
        camera_name="Room1",
        site_id=uuid4(),
        node_id=edge_node_id,
        processing_mode=processing_mode,
        desired_state=desired_state,
        runtime_status=WorkerRuntimeStatus.OFFLINE,
        lifecycle_owner=lifecycle_owner,
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
