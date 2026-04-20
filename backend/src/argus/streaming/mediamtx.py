from __future__ import annotations

import subprocess
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from typing import Any, Protocol
from uuid import UUID

import httpx
from pydantic import BaseModel, ConfigDict


class Frame(Protocol):
    shape: tuple[int, ...]


type CommandRunner = Callable[[list[str]], str]


class PublishProfile(StrEnum):
    JETSON_NANO = "jetson-nano"
    CENTRAL_GPU = "central-gpu"


class StreamMode(StrEnum):
    PASSTHROUGH = "passthrough"
    FILTERED_PREVIEW = "filtered-preview"
    ANNOTATED_WHIP = "annotated-whip"


class PrivacyPolicy(BaseModel):
    model_config = ConfigDict(frozen=True)

    blur_faces: bool = True
    blur_plates: bool = True

    @property
    def requires_filtering(self) -> bool:
        return self.blur_faces or self.blur_plates


@dataclass(slots=True, frozen=True)
class StreamRegistration:
    camera_id: UUID
    mode: StreamMode
    read_path: str
    publish_path: str | None = None
    path_name: str | None = None
    managed_path_config: bool = False


class MediaMTXClient:
    def __init__(
        self,
        *,
        api_base_url: str,
        rtsp_base_url: str,
        whip_base_url: str,
        username: str | None = None,
        password: str | None = None,
        http_client: httpx.AsyncClient | None = None,
    ) -> None:
        self.api_base_url = api_base_url.rstrip("/")
        self.rtsp_base_url = rtsp_base_url.rstrip("/")
        self.whip_base_url = whip_base_url.rstrip("/")
        self._owned_client = http_client is None
        self._http_client = http_client or httpx.AsyncClient(
            auth=(username, password) if username and password else None
        )
        self._registrations: dict[UUID, StreamRegistration] = {}
        self._pushed_frames: dict[UUID, dict[str, Any]] = {}

    async def close(self) -> None:
        if self._owned_client:
            await self._http_client.aclose()

    async def register_stream(
        self,
        *,
        camera_id: UUID,
        rtsp_url: str,
        profile: PublishProfile,
        privacy: PrivacyPolicy,
    ) -> StreamRegistration:
        previous = self._registrations.get(camera_id)
        registration = await self._build_registration(
            camera_id=camera_id,
            rtsp_url=rtsp_url,
            profile=profile,
            privacy=privacy,
        )
        if (
            previous is not None
            and previous.managed_path_config
            and previous.path_name is not None
            and previous.path_name != registration.path_name
        ):
            await self._request(
                "DELETE",
                f"/v3/config/paths/delete/{previous.path_name}",
            )
        self._registrations[camera_id] = registration
        return registration

    async def push_frame(
        self,
        registration: StreamRegistration,
        frame: Frame,
        *,
        ts: datetime,
    ) -> None:
        self._pushed_frames[registration.camera_id] = {
            "mode": registration.mode,
            "shape": tuple(int(value) for value in frame.shape),
            "ts": ts.isoformat(),
        }

    async def create_webrtc_offer(self, *, camera_id: UUID, sdp_offer: str) -> str:
        response = await self._http_client.post(
            f"{self.api_base_url}/v3/webrtc/offer/{camera_id}",
            json={"sdp_offer": sdp_offer},
        )
        response.raise_for_status()
        payload = response.json()
        return str(
            payload.get("sdp_answer")
            or payload.get("answer")
            or payload.get("sdpAnswer")
            or ""
        )

    async def _build_registration(
        self,
        *,
        camera_id: UUID,
        rtsp_url: str,
        profile: PublishProfile,
        privacy: PrivacyPolicy,
    ) -> StreamRegistration:
        if profile is PublishProfile.CENTRAL_GPU:
            path_name = f"cameras/{camera_id}/annotated"
            return StreamRegistration(
                camera_id=camera_id,
                mode=StreamMode.ANNOTATED_WHIP,
                path_name=path_name,
                read_path=f"{self.rtsp_base_url}/{path_name}",
                publish_path=f"{self.whip_base_url}/{path_name}/whip",
            )

        if privacy.requires_filtering:
            path_name = f"cameras/{camera_id}/preview"
            return StreamRegistration(
                camera_id=camera_id,
                mode=StreamMode.FILTERED_PREVIEW,
                path_name=path_name,
                read_path=f"{self.rtsp_base_url}/{path_name}",
                publish_path=f"{self.rtsp_base_url}/{path_name}",
            )

        path_name = f"cameras/{camera_id}/passthrough"
        await self._ensure_path(path_name, source=rtsp_url, source_on_demand=True)
        return StreamRegistration(
            camera_id=camera_id,
            mode=StreamMode.PASSTHROUGH,
            path_name=path_name,
            read_path=f"{self.rtsp_base_url}/{path_name}",
            managed_path_config=True,
        )

    async def _ensure_path(self, path_name: str, *, source: str, source_on_demand: bool) -> None:
        await self._request(
            "POST",
            f"/v3/config/paths/add/{path_name}",
            json={
                "name": path_name,
                "source": source,
                "sourceOnDemand": source_on_demand,
            },
        )

    async def _request(
        self,
        method: str,
        path: str,
        *,
        json: dict[str, Any] | None = None,
    ) -> None:
        response = await self._http_client.request(
            method,
            f"{self.api_base_url}{path}",
            json=json,
        )
        response.raise_for_status()


def probe_publish_profile(
    *,
    explicit_override: str | None = None,
    machine: str | None = None,
    command_runner: CommandRunner | None = None,
) -> PublishProfile:
    if explicit_override is not None:
        return PublishProfile(explicit_override)

    resolved_machine = (machine or "").lower()
    if command_runner is None:
        if resolved_machine in {"aarch64", "arm64"}:
            return PublishProfile.JETSON_NANO
        return PublishProfile.CENTRAL_GPU

    try:
        output = command_runner(
            [
                "nvidia-smi",
                "--query-gpu=encoder.stats.sessionCount",
                "--format=csv,noheader,nounits",
            ]
        )
    except FileNotFoundError:
        return (
            PublishProfile.JETSON_NANO
            if resolved_machine in {"aarch64", "arm64"}
            else PublishProfile.CENTRAL_GPU
        )

    normalized = str(output).strip().lower()
    if "n/a" in normalized or "not supported" in normalized:
        return PublishProfile.JETSON_NANO
    if resolved_machine in {"aarch64", "arm64"} and normalized in {"", "0"}:
        return PublishProfile.JETSON_NANO
    return PublishProfile.CENTRAL_GPU


def default_profile_probe(command: list[str]) -> str:
    completed = subprocess.run(
        command,
        check=True,
        capture_output=True,
        text=True,
    )
    return completed.stdout
