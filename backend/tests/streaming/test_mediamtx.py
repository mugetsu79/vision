from __future__ import annotations

import json
from collections.abc import Callable
from datetime import UTC, datetime
from uuid import uuid4

import numpy as np
import pytest
from httpx import AsyncClient, Request, Response
from jose import jwt

from argus.streaming.mediamtx import (
    MediaMTXClient,
    PrivacyPolicy,
    PublishProfile,
    StreamMode,
    probe_publish_profile,
)
from argus.streaming.webrtc import MediaMTXTokenIssuer


def test_probe_publish_profile_prefers_explicit_override() -> None:
    profile = probe_publish_profile(
        explicit_override="central-gpu",
        machine="aarch64",
        command_runner=lambda command: "",
    )

    assert profile is PublishProfile.CENTRAL_GPU


def test_probe_publish_profile_defaults_to_jetson_on_arm_without_encoder() -> None:
    profile = probe_publish_profile(
        machine="aarch64",
        command_runner=lambda command: (_ for _ in ()).throw(FileNotFoundError("nvidia-smi")),
    )

    assert profile is PublishProfile.JETSON_NANO


def test_probe_publish_profile_defaults_to_central_gpu_on_x86_without_probe() -> None:
    profile = probe_publish_profile(machine="x86_64", command_runner=None)

    assert profile is PublishProfile.CENTRAL_GPU


@pytest.mark.asyncio
async def test_mediamtx_client_registers_passthrough_for_privacy_off_jetson() -> None:
    requests: list[tuple[str, str, dict[str, object] | None]] = []

    async def handler(request: Request) -> Response:
        requests.append(
            (
                request.method,
                str(request.url),
                json.loads(request.content.decode("utf-8")),
            )
        )
        return Response(200, json={"ok": True})

    camera_id = uuid4()
    client = MediaMTXClient(
        api_base_url="http://mediamtx.internal:9997",
        rtsp_base_url="rtsp://mediamtx.internal:8554",
        whip_base_url="http://mediamtx.internal:8889",
        http_client=AsyncClient(transport=_transport(handler)),
    )

    registration = await client.register_stream(
        camera_id=camera_id,
        rtsp_url="rtsp://camera.internal/live",
        profile=PublishProfile.JETSON_NANO,
        privacy=PrivacyPolicy(blur_faces=False, blur_plates=False),
    )

    assert registration.mode is StreamMode.PASSTHROUGH
    assert (
        registration.read_path
        == f"rtsp://mediamtx.internal:8554/cameras/{camera_id}/passthrough"
    )
    assert requests == [
        (
            "POST",
            f"http://mediamtx.internal:9997/v3/config/paths/add/cameras/{camera_id}/passthrough",
            {
                "name": f"cameras/{camera_id}/passthrough",
                "source": "rtsp://camera.internal/live",
                "sourceOnDemand": True,
            },
        )
    ]

    await client.close()


@pytest.mark.asyncio
async def test_mediamtx_client_registers_filtered_preview_and_deletes_passthrough_when_privacy_turns_on(  # noqa: E501
) -> None:
    requests: list[tuple[str, str, dict[str, object] | None]] = []

    async def handler(request: Request) -> Response:
        requests.append(
            (
                request.method,
                str(request.url),
                json.loads(request.content.decode("utf-8")) if request.content else None,
            )
        )
        return Response(200, json={"ok": True})

    camera_id = uuid4()
    client = MediaMTXClient(
        api_base_url="http://mediamtx.internal:9997",
        rtsp_base_url="rtsp://mediamtx.internal:8554",
        whip_base_url="http://mediamtx.internal:8889",
        http_client=AsyncClient(transport=_transport(handler)),
    )

    await client.register_stream(
        camera_id=camera_id,
        rtsp_url="rtsp://camera.internal/live",
        profile=PublishProfile.JETSON_NANO,
        privacy=PrivacyPolicy(blur_faces=False, blur_plates=False),
    )
    registration = await client.register_stream(
        camera_id=camera_id,
        rtsp_url="rtsp://camera.internal/live",
        profile=PublishProfile.JETSON_NANO,
        privacy=PrivacyPolicy(blur_faces=True, blur_plates=False),
    )

    assert registration.mode is StreamMode.FILTERED_PREVIEW
    assert registration.publish_path == f"rtsp://mediamtx.internal:8554/cameras/{camera_id}/preview"
    assert registration.path_name == f"cameras/{camera_id}/preview"
    assert (
        "DELETE",
        f"http://mediamtx.internal:9997/v3/config/paths/delete/cameras/{camera_id}/passthrough",
        None,
    ) in requests
    assert all(
        request[:2]
        != (
            "POST",
            f"http://mediamtx.internal:9997/v3/config/paths/add/cameras/{camera_id}/preview",
        )
        for request in requests
    )

    await client.close()


@pytest.mark.asyncio
async def test_mediamtx_client_registers_whip_target_for_central_profile() -> None:
    requests: list[tuple[str, str, dict[str, object] | None]] = []

    async def handler(request: Request) -> Response:
        requests.append(
            (
                request.method,
                str(request.url),
                json.loads(request.content.decode("utf-8")) if request.content else None,
            )
        )
        return Response(200, json={"ok": True})

    camera_id = uuid4()
    client = MediaMTXClient(
        api_base_url="http://mediamtx.internal:9997",
        rtsp_base_url="rtsp://mediamtx.internal:8554",
        whip_base_url="http://mediamtx.internal:8889",
        http_client=AsyncClient(transport=_transport(handler)),
    )

    registration = await client.register_stream(
        camera_id=camera_id,
        rtsp_url="rtsp://camera.internal/live",
        profile=PublishProfile.CENTRAL_GPU,
        privacy=PrivacyPolicy(blur_faces=True, blur_plates=True),
    )

    assert registration.mode is StreamMode.ANNOTATED_WHIP
    assert (
        registration.publish_path
        == f"rtsp://mediamtx.internal:8554/cameras/{camera_id}/annotated"
    )
    assert registration.path_name == f"cameras/{camera_id}/annotated"
    assert requests == []

    await client.close()


@pytest.mark.asyncio
async def test_mediamtx_client_does_not_delete_preconfigured_preview_when_switching_back_to_passthrough() -> None:
    requests: list[tuple[str, str, dict[str, object] | None]] = []

    async def handler(request: Request) -> Response:
        requests.append(
            (
                request.method,
                str(request.url),
                json.loads(request.content.decode("utf-8")) if request.content else None,
            )
        )
        return Response(200, json={"ok": True})

    camera_id = uuid4()
    client = MediaMTXClient(
        api_base_url="http://mediamtx.internal:9997",
        rtsp_base_url="rtsp://mediamtx.internal:8554",
        whip_base_url="http://mediamtx.internal:8889",
        http_client=AsyncClient(transport=_transport(handler)),
    )

    await client.register_stream(
        camera_id=camera_id,
        rtsp_url="rtsp://camera.internal/live",
        profile=PublishProfile.JETSON_NANO,
        privacy=PrivacyPolicy(blur_faces=True, blur_plates=False),
    )
    registration = await client.register_stream(
        camera_id=camera_id,
        rtsp_url="rtsp://camera.internal/live",
        profile=PublishProfile.JETSON_NANO,
        privacy=PrivacyPolicy(blur_faces=False, blur_plates=False),
    )

    assert registration.mode is StreamMode.PASSTHROUGH
    assert requests == [
        (
            "POST",
            f"http://mediamtx.internal:9997/v3/config/paths/add/cameras/{camera_id}/passthrough",
            {
                "name": f"cameras/{camera_id}/passthrough",
                "source": "rtsp://camera.internal/live",
                "sourceOnDemand": True,
            },
        )
    ]

    await client.close()


@pytest.mark.asyncio
async def test_mediamtx_client_push_frame_starts_and_reuses_publisher() -> None:
    created_publishers: list[_FakeFramePublisher] = []
    published_urls: list[str] = []
    camera_id = uuid4()
    issuer = MediaMTXTokenIssuer()

    async def publisher_factory(
        *,
        registration,
        frame: np.ndarray,
        publish_url: str,
    ) -> _FakeFramePublisher:
        published_urls.append(publish_url)
        publisher = _FakeFramePublisher()
        created_publishers.append(publisher)
        return publisher

    client = MediaMTXClient(
        api_base_url="http://mediamtx.internal:9997",
        rtsp_base_url="rtsp://mediamtx.internal:8554",
        whip_base_url="http://mediamtx.internal:8889",
        publisher_factory=publisher_factory,
        publish_token_factory=lambda camera_id, path_name: issuer.issue_publish_token(
            subject="worker-1",
            camera_id=camera_id,
            path_name=path_name,
        ),
    )
    registration = await client.register_stream(
        camera_id=camera_id,
        rtsp_url="rtsp://camera.internal/live",
        profile=PublishProfile.CENTRAL_GPU,
        privacy=PrivacyPolicy(blur_faces=True, blur_plates=True),
    )
    frame = np.zeros((12, 16, 3), dtype=np.uint8)

    await client.push_frame(registration, frame, ts=datetime(2026, 4, 20, 18, 0, tzinfo=UTC))
    await client.push_frame(registration, frame, ts=datetime(2026, 4, 20, 18, 0, 1, tzinfo=UTC))

    assert len(created_publishers) == 1
    assert len(created_publishers[0].frames) == 2
    token = published_urls[0].split("token=", maxsplit=1)[1]
    claims = jwt.get_unverified_claims(token)
    assert claims["mediamtx_permissions"] == [
        {"action": "publish", "path": f"cameras/{camera_id}/annotated"}
    ]

    await client.close()


@pytest.mark.asyncio
async def test_mediamtx_client_replaces_publisher_when_path_changes() -> None:
    created_publishers: list[_FakeFramePublisher] = []
    camera_id = uuid4()

    async def publisher_factory(
        *,
        registration,
        frame: np.ndarray,
        publish_url: str,
    ) -> _FakeFramePublisher:
        publisher = _FakeFramePublisher()
        created_publishers.append(publisher)
        return publisher

    client = MediaMTXClient(
        api_base_url="http://mediamtx.internal:9997",
        rtsp_base_url="rtsp://mediamtx.internal:8554",
        whip_base_url="http://mediamtx.internal:8889",
        publisher_factory=publisher_factory,
    )
    first_registration = await client.register_stream(
        camera_id=camera_id,
        rtsp_url="rtsp://camera.internal/live",
        profile=PublishProfile.CENTRAL_GPU,
        privacy=PrivacyPolicy(blur_faces=True, blur_plates=True),
    )
    frame = np.zeros((12, 16, 3), dtype=np.uint8)
    await client.push_frame(first_registration, frame, ts=datetime(2026, 4, 20, 18, 1, tzinfo=UTC))

    second_registration = await client.register_stream(
        camera_id=camera_id,
        rtsp_url="rtsp://camera.internal/live",
        profile=PublishProfile.JETSON_NANO,
        privacy=PrivacyPolicy(blur_faces=True, blur_plates=False),
    )
    await client.push_frame(second_registration, frame, ts=datetime(2026, 4, 20, 18, 1, 1, tzinfo=UTC))

    assert len(created_publishers) == 2
    assert created_publishers[0].closed is True
    assert created_publishers[1].closed is False

    await client.close()


@pytest.mark.asyncio
async def test_mediamtx_client_close_shuts_down_active_publishers() -> None:
    created_publishers: list[_FakeFramePublisher] = []
    camera_id = uuid4()

    async def publisher_factory(
        *,
        registration,
        frame: np.ndarray,
        publish_url: str,
    ) -> _FakeFramePublisher:
        publisher = _FakeFramePublisher()
        created_publishers.append(publisher)
        return publisher

    client = MediaMTXClient(
        api_base_url="http://mediamtx.internal:9997",
        rtsp_base_url="rtsp://mediamtx.internal:8554",
        whip_base_url="http://mediamtx.internal:8889",
        publisher_factory=publisher_factory,
    )
    registration = await client.register_stream(
        camera_id=camera_id,
        rtsp_url="rtsp://camera.internal/live",
        profile=PublishProfile.CENTRAL_GPU,
        privacy=PrivacyPolicy(blur_faces=True, blur_plates=True),
    )

    await client.push_frame(
        registration,
        np.zeros((12, 16, 3), dtype=np.uint8),
        ts=datetime(2026, 4, 20, 18, 2, tzinfo=UTC),
    )
    await client.close()

    assert created_publishers[0].closed is True


def _transport(handler: Callable[[Request], Response | object]):
    async def wrapped(request: Request) -> Response:
        response = handler(request)
        if isinstance(response, Response):
            return response
        return await response

    from httpx import MockTransport

    return MockTransport(wrapped)


class _FakeFramePublisher:
    def __init__(self) -> None:
        self.frames: list[tuple[int, ...]] = []
        self.closed = False

    async def push_frame(self, frame: np.ndarray, *, ts: datetime) -> None:
        self.frames.append(tuple(int(value) for value in frame.shape))

    def is_alive(self) -> bool:
        return not self.closed

    async def close(self) -> None:
        self.closed = True
