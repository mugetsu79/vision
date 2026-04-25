from __future__ import annotations

import asyncio
import contextlib
import importlib
import subprocess
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from logging import getLogger
from typing import Any, Protocol
from urllib.parse import urlencode, urlsplit, urlunsplit
from uuid import UUID

import httpx
from pydantic import BaseModel, ConfigDict


class Frame(Protocol):
    shape: tuple[int, ...]


type CommandRunner = Callable[[list[str]], str]
type PublishTokenFactory = Callable[[UUID, str], str]
type ReadTokenFactory = Callable[[UUID, str], str]

LOGGER = getLogger(__name__)


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
    target_fps: int = 25
    target_width: int | None = None
    target_height: int | None = None
    ingest_path: str = ""


class FramePublisher(Protocol):
    async def push_frame(self, frame: Frame, *, ts: datetime) -> None: ...

    def is_alive(self) -> bool: ...

    async def close(self) -> None: ...


type PublisherFactory = Callable[..., Awaitable[FramePublisher]]


@dataclass(slots=True)
class _PublisherState:
    path_name: str
    publish_path: str
    frame_shape: tuple[int, ...]
    publisher: FramePublisher
    last_published_at: datetime | None = None


class _PublisherRestartRequired(RuntimeError):
    pass


class _FFmpegFramePublisher:
    def __init__(
        self,
        *,
        process: asyncio.subprocess.Process,
        frame_shape: tuple[int, ...],
        camera_id: UUID,
        path_name: str,
        stderr_task: asyncio.Task[None] | None,
    ) -> None:
        self._process = process
        self._frame_shape = frame_shape
        self._camera_id = camera_id
        self._path_name = path_name
        self._stderr_task = stderr_task

    @classmethod
    async def create(
        cls,
        *,
        registration: StreamRegistration,
        frame: Frame,
        publish_url: str,
    ) -> _FFmpegFramePublisher:
        width, height = _frame_dimensions(frame)
        frame_shape = tuple(int(value) for value in frame.shape)
        keyframe_interval = max(1, registration.target_fps)
        command = [
            "ffmpeg",
            "-loglevel",
            "error",
            "-f",
            "rawvideo",
            "-pixel_format",
            "bgr24",
            "-video_size",
            f"{width}x{height}",
            "-framerate",
            str(max(1, registration.target_fps)),
            "-i",
            "pipe:0",
            "-an",
            "-c:v",
            "libx264",
            "-preset",
            "veryfast",
            "-tune",
            "zerolatency",
            "-g",
            str(keyframe_interval),
            "-keyint_min",
            str(keyframe_interval),
            "-sc_threshold",
            "0",
            "-pix_fmt",
            "yuv420p",
            "-rtsp_transport",
            "tcp",
            "-f",
            "rtsp",
            publish_url,
        ]
        try:
            process = await asyncio.create_subprocess_exec(
                *command,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.DEVNULL,
                stderr=asyncio.subprocess.PIPE,
            )
        except FileNotFoundError as exc:
            raise RuntimeError(
                "ffmpeg is required to publish processed live streams into MediaMTX."
            ) from exc
        stderr_task = None
        stderr_stream = getattr(process, "stderr", None)
        if stderr_stream is not None:
            stderr_task = asyncio.create_task(
                cls._drain_stderr(
                    stderr_stream,
                    camera_id=registration.camera_id,
                    path_name=registration.path_name or "<unknown>",
                )
            )
        return cls(
            process=process,
            frame_shape=frame_shape,
            camera_id=registration.camera_id,
            path_name=registration.path_name or "<unknown>",
            stderr_task=stderr_task,
        )

    async def push_frame(self, frame: Frame, *, ts: datetime) -> None:
        del ts
        if tuple(int(value) for value in frame.shape) != self._frame_shape:
            raise _PublisherRestartRequired("frame shape changed")
        if not self.is_alive() or self._process.stdin is None:
            raise _PublisherRestartRequired("publisher process is not running")
        try:
            self._process.stdin.write(frame.tobytes())
            await self._process.stdin.drain()
        except (BrokenPipeError, ConnectionResetError) as exc:
            raise _PublisherRestartRequired("publisher process closed its stdin") from exc

    def is_alive(self) -> bool:
        return self._process.returncode is None

    async def close(self) -> None:
        if self._process.stdin is not None and not self._process.stdin.is_closing():
            self._process.stdin.close()
        with contextlib.suppress(asyncio.TimeoutError):
            await asyncio.wait_for(self._process.wait(), timeout=2.0)
        if self._process.returncode is None:
            self._process.kill()
            await self._process.wait()
        if self._stderr_task is not None:
            if not self._stderr_task.done():
                self._stderr_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._stderr_task

    @staticmethod
    async def _drain_stderr(
        stream: asyncio.StreamReader,
        *,
        camera_id: UUID,
        path_name: str,
    ) -> None:
        while True:
            line = await stream.readline()
            if line == b"":
                return
            message = line.decode("utf-8", errors="replace").strip()
            if message:
                LOGGER.warning(
                    "MediaMTX publisher ffmpeg stderr: %s",
                    message,
                    extra={
                        "camera_id": str(camera_id),
                        "path_name": path_name,
                    },
                )


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
        publisher_factory: PublisherFactory | None = None,
        publish_token_factory: PublishTokenFactory | None = None,
        read_token_factory: ReadTokenFactory | None = None,
        publisher_push_timeout_seconds: float = 1.0,
        publisher_idle_restart_seconds: float = 15.0,
    ) -> None:
        self.api_base_url = api_base_url.rstrip("/")
        self.rtsp_base_url = rtsp_base_url.rstrip("/")
        self.whip_base_url = whip_base_url.rstrip("/")
        self._owned_client = http_client is None
        self._http_client = http_client or httpx.AsyncClient(
            auth=(username, password) if username and password else None
        )
        self._publisher_factory = publisher_factory or _default_publisher_factory
        self._publish_token_factory = publish_token_factory
        self._read_token_factory = read_token_factory
        self._publisher_push_timeout_seconds = max(0.0, publisher_push_timeout_seconds)
        self._publisher_idle_restart_seconds = max(0.0, publisher_idle_restart_seconds)
        self._registrations: dict[UUID, StreamRegistration] = {}
        self._publishers: dict[UUID, _PublisherState] = {}
        self._pushed_frames: dict[UUID, dict[str, Any]] = {}

    async def close(self) -> None:
        for state in list(self._publishers.values()):
            await state.publisher.close()
        self._publishers.clear()
        if self._owned_client:
            await self._http_client.aclose()

    async def register_stream(
        self,
        *,
        camera_id: UUID,
        rtsp_url: str,
        profile: PublishProfile,
        stream_kind: str,
        privacy: PrivacyPolicy,
        target_fps: int = 25,
        target_width: int | None = None,
        target_height: int | None = None,
    ) -> StreamRegistration:
        previous = self._registrations.get(camera_id)
        registration = await self._build_registration(
            camera_id=camera_id,
            rtsp_url=rtsp_url,
            profile=profile,
            stream_kind=stream_kind,
            privacy=privacy,
            target_fps=target_fps,
            target_width=target_width,
            target_height=target_height,
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
        publisher_state = self._publishers.get(camera_id)
        if (
            publisher_state is not None
            and registration.path_name is not None
            and publisher_state.path_name != registration.path_name
        ):
            await publisher_state.publisher.close()
            self._publishers.pop(camera_id, None)
        self._registrations[camera_id] = registration
        return registration

    async def push_frame(
        self,
        registration: StreamRegistration,
        frame: Frame,
        *,
        ts: datetime,
    ) -> None:
        if registration.mode is StreamMode.PASSTHROUGH:
            return
        prepared_frame = _prepare_frame_for_publish(registration=registration, frame=frame)
        publisher_state = await self._ensure_publisher(
            registration=registration,
            frame=prepared_frame,
        )
        if not _should_publish_frame(
            last_published_at=publisher_state.last_published_at,
            ts=ts,
            target_fps=registration.target_fps,
        ):
            return
        if self._should_restart_idle_publisher(publisher_state=publisher_state, ts=ts):
            LOGGER.warning(
                "Recycling MediaMTX publisher after a long frame gap",
                extra={
                    "camera_id": str(registration.camera_id),
                    "path_name": registration.path_name,
                    "silence_seconds": self._publisher_silence_seconds(
                        publisher_state=publisher_state,
                        ts=ts,
                    ),
                    "threshold_seconds": self._publisher_idle_restart_seconds,
                },
            )
            await publisher_state.publisher.close()
            self._publishers.pop(registration.camera_id, None)
            publisher_state = await self._ensure_publisher(
                registration=registration,
                frame=prepared_frame,
            )
        publisher = publisher_state.publisher
        try:
            await self._push_frame_with_timeout(
                publisher=publisher,
                frame=prepared_frame,
                ts=ts,
            )
        except TimeoutError:
            LOGGER.warning(
                (
                    "Timed out pushing frame to MediaMTX publisher; "
                    "dropping frame and recycling publisher"
                ),
                extra={
                    "camera_id": str(registration.camera_id),
                    "path_name": registration.path_name,
                    "timeout_seconds": self._publisher_push_timeout_seconds,
                },
            )
            await publisher.close()
            self._publishers.pop(registration.camera_id, None)
            return
        except _PublisherRestartRequired:
            await publisher.close()
            self._publishers.pop(registration.camera_id, None)
            publisher_state = await self._ensure_publisher(
                registration=registration,
                frame=prepared_frame,
            )
            publisher = publisher_state.publisher
            await self._push_frame_with_timeout(
                publisher=publisher,
                frame=prepared_frame,
                ts=ts,
            )
        publisher_state.last_published_at = ts
        self._pushed_frames[registration.camera_id] = {
            "mode": registration.mode,
            "shape": tuple(int(value) for value in prepared_frame.shape),
            "ts": ts.isoformat(),
        }

    async def _push_frame_with_timeout(
        self,
        *,
        publisher: FramePublisher,
        frame: Frame,
        ts: datetime,
    ) -> None:
        if self._publisher_push_timeout_seconds <= 0:
            await publisher.push_frame(frame, ts=ts)
            return
        await asyncio.wait_for(
            publisher.push_frame(frame, ts=ts),
            timeout=self._publisher_push_timeout_seconds,
        )

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

    def _authenticated_read_url(self, camera_id: UUID, base_url: str, path_name: str) -> str:
        """Append a read JWT to a MediaMTX RTSP URL when a read token factory is configured.

        Used to build the worker's ingest URL — MediaMTX's `authMethod: jwt`
        rejects unauthenticated DESCRIBE on protected paths, so the worker
        cannot read from `cameras/<id>/passthrough` without a token.
        """
        if self._read_token_factory is None:
            return base_url
        token = self._read_token_factory(camera_id, path_name)
        separator = "&" if "?" in base_url else "?"
        return f"{base_url}{separator}jwt={token}"

    async def _build_registration(
        self,
        *,
        camera_id: UUID,
        rtsp_url: str,
        profile: PublishProfile,
        stream_kind: str,
        privacy: PrivacyPolicy,
        target_fps: int,
        target_width: int | None,
        target_height: int | None,
    ) -> StreamRegistration:
        passthrough_name = f"cameras/{camera_id}/passthrough"
        passthrough_read = f"{self.rtsp_base_url}/{passthrough_name}"
        ingest_path = self._authenticated_read_url(
            camera_id, passthrough_read, passthrough_name
        )
        await self._ensure_path(
            passthrough_name,
            source=rtsp_url,
            source_on_demand=True,
        )

        requested_passthrough = stream_kind == StreamMode.PASSTHROUGH.value
        if requested_passthrough and privacy.requires_filtering:
            LOGGER.warning(
                (
                    "Passthrough stream requested, but privacy filtering is enabled; "
                    "using a processed stream instead."
                ),
                extra={
                    "camera_id": str(camera_id),
                    "profile": profile.value,
                    "requested_stream_kind": stream_kind,
                },
            )

        effective_passthrough = requested_passthrough and not privacy.requires_filtering

        if effective_passthrough:
            return StreamRegistration(
                camera_id=camera_id,
                mode=StreamMode.PASSTHROUGH,
                path_name=passthrough_name,
                read_path=passthrough_read,
                managed_path_config=True,
                target_fps=max(1, target_fps),
                target_width=target_width,
                target_height=target_height,
                ingest_path=ingest_path,
            )

        if profile is PublishProfile.CENTRAL_GPU:
            annotated_name = f"cameras/{camera_id}/annotated"
            annotated_path = f"{self.rtsp_base_url}/{annotated_name}"
            await self._ensure_path(
                annotated_name,
                source="publisher",
                source_on_demand=False,
            )
            return StreamRegistration(
                camera_id=camera_id,
                mode=StreamMode.ANNOTATED_WHIP,
                path_name=annotated_name,
                read_path=annotated_path,
                publish_path=annotated_path,
                managed_path_config=True,
                target_fps=max(1, target_fps),
                target_width=target_width,
                target_height=target_height,
                ingest_path=ingest_path,
            )

        if privacy.requires_filtering:
            preview_name = f"cameras/{camera_id}/preview"
            preview_path = f"{self.rtsp_base_url}/{preview_name}"
            return StreamRegistration(
                camera_id=camera_id,
                mode=StreamMode.FILTERED_PREVIEW,
                path_name=preview_name,
                read_path=preview_path,
                publish_path=preview_path,
                target_fps=max(1, target_fps),
                target_width=target_width,
                target_height=target_height,
                ingest_path=ingest_path,
            )

        return StreamRegistration(
            camera_id=camera_id,
            mode=StreamMode.PASSTHROUGH,
            path_name=passthrough_name,
            read_path=passthrough_read,
            managed_path_config=True,
            target_fps=max(1, target_fps),
            target_width=target_width,
            target_height=target_height,
            ingest_path=ingest_path,
        )

    async def _ensure_publisher(
        self,
        *,
        registration: StreamRegistration,
        frame: Frame,
    ) -> _PublisherState:
        if registration.publish_path is None or registration.path_name is None:
            raise RuntimeError("stream registration is missing publish path details")
        frame_shape = tuple(int(value) for value in frame.shape)
        existing = self._publishers.get(registration.camera_id)
        if (
            existing is not None
            and (
                existing.path_name != registration.path_name
                or existing.publish_path != registration.publish_path
                or existing.frame_shape != frame_shape
                or not existing.publisher.is_alive()
            )
        ):
            await existing.publisher.close()
            self._publishers.pop(registration.camera_id, None)
            existing = None
        if existing is not None:
            return existing

        publish_url = registration.publish_path
        if self._publish_token_factory is not None:
            publish_url = _append_query_parameter(
                publish_url,
                key="jwt",
                value=self._publish_token_factory(registration.camera_id, registration.path_name),
            )
        publisher = await self._publisher_factory(
            registration=registration,
            frame=frame,
            publish_url=publish_url,
        )
        state = _PublisherState(
            path_name=registration.path_name,
            publish_path=registration.publish_path,
            frame_shape=frame_shape,
            publisher=publisher,
        )
        self._publishers[registration.camera_id] = state
        return state

    def _should_restart_idle_publisher(
        self,
        *,
        publisher_state: _PublisherState,
        ts: datetime,
    ) -> bool:
        if self._publisher_idle_restart_seconds <= 0:
            return False
        return (
            self._publisher_silence_seconds(publisher_state=publisher_state, ts=ts)
            >= self._publisher_idle_restart_seconds
        )

    @staticmethod
    def _publisher_silence_seconds(
        *,
        publisher_state: _PublisherState,
        ts: datetime,
    ) -> float:
        if publisher_state.last_published_at is None:
            return 0.0
        return max(0.0, (ts - publisher_state.last_published_at).total_seconds())

    async def _ensure_path(self, path_name: str, *, source: str, source_on_demand: bool) -> None:
        await self._request(
            "POST",
            f"/v3/config/paths/replace/{path_name}",
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


async def _default_publisher_factory(
    *,
    registration: StreamRegistration,
    frame: Frame,
    publish_url: str,
) -> FramePublisher:
    return await _FFmpegFramePublisher.create(
        registration=registration,
        frame=frame,
        publish_url=publish_url,
    )


def _frame_dimensions(frame: Frame) -> tuple[int, int]:
    if len(frame.shape) != 3 or int(frame.shape[2]) != 3:
        raise RuntimeError("only BGR uint8 frames are supported for live publishing")
    return int(frame.shape[1]), int(frame.shape[0])


def _prepare_frame_for_publish(*, registration: StreamRegistration, frame: Frame) -> Any:
    if registration.target_width is None or registration.target_height is None:
        return frame
    current_width, current_height = _frame_dimensions(frame)
    if (
        current_width == registration.target_width
        and current_height == registration.target_height
    ):
        return frame
    cv2 = _load_cv2()
    return cv2.resize(
        frame,
        (registration.target_width, registration.target_height),
        interpolation=cv2.INTER_LINEAR,
    )


def _load_cv2() -> Any:
    try:
        return importlib.import_module("cv2")
    except ModuleNotFoundError as exc:
        raise RuntimeError(
            "OpenCV is required for browser-delivery transcode resizing. "
            "Install the backend vision dependencies before starting the worker."
        ) from exc


def _should_publish_frame(
    *,
    last_published_at: datetime | None,
    ts: datetime,
    target_fps: int,
) -> bool:
    if last_published_at is None:
        return True
    delta = (ts - last_published_at).total_seconds()
    if delta < 0:
        return True
    return delta >= (1.0 / max(1, target_fps))


def _append_query_parameter(url: str, *, key: str, value: str) -> str:
    split_url = urlsplit(url)
    query = split_url.query
    suffix = urlencode({key: value})
    combined = suffix if query == "" else f"{query}&{suffix}"
    return urlunsplit(
        (split_url.scheme, split_url.netloc, split_url.path, combined, split_url.fragment)
    )
