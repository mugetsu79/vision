from __future__ import annotations

import json
from collections.abc import Callable
from uuid import uuid4

import pytest
from httpx import AsyncClient, Request, Response

from argus.streaming.mediamtx import (
    MediaMTXClient,
    PrivacyPolicy,
    PublishProfile,
    StreamMode,
    probe_publish_profile,
)


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
        == f"http://mediamtx.internal:8889/cameras/{camera_id}/annotated/whip"
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


def _transport(handler: Callable[[Request], Response | object]):
    async def wrapped(request: Request) -> Response:
        response = handler(request)
        if isinstance(response, Response):
            return response
        return await response

    from httpx import MockTransport

    return MockTransport(wrapped)
