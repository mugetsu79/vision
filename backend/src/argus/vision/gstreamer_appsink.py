from __future__ import annotations

import importlib
import re
from dataclasses import dataclass
from math import isfinite
from time import perf_counter
from typing import Any, Protocol, cast

import numpy as np
from numpy.typing import NDArray

from argus.compat import StrEnum
from argus.core.logging import redact_url_secrets

Frame = NDArray[np.uint8]


class AppSinkPipelineMode(StrEnum):
    JETSON_NATIVE = "jetson_native"
    GSTREAMER_SOFTWARE = "gstreamer_software"


@dataclass(slots=True, frozen=True)
class AppSinkCapabilities:
    available: bool
    appsink_supports_leaky_type: bool = False
    decoder_supports_disable_dpb: bool = False
    reason: str | None = None


_COMMON_APPSINK_PIPELINE_ELEMENTS = (
    "rtspsrc",
    "rtph264depay",
    "h264parse",
    "queue",
    "appsink",
    "videoconvert",
)
_NATIVE_APPSINK_PIPELINE_ELEMENTS = ("nvv4l2decoder", "nvvidconv")
_SOFTWARE_APPSINK_PIPELINE_ELEMENTS = ("avdec_h264", "videoscale")
_GST_FLAG_VALUE_PATTERN = re.compile(r"^[A-Za-z0-9_+,-]+$")
_GST_LOCATION_PROPERTY_PATTERN = re.compile(
    r"location=(?P<value>\"(?:\\.|[^\"\\])*\"|\S+)",
)


class AppSinkRuntime(Protocol):
    def start(self, pipeline: str) -> None: ...

    def pull_sample(self, timeout_s: float) -> object | None: ...

    def sample_to_bgr(self, sample: object, *, width: int, height: int) -> Frame: ...

    def stop(self) -> None: ...


class _GstMapInfo(Protocol):
    data: bytes | bytearray | memoryview


class _GstBuffer(Protocol):
    def map(self, flags: object) -> tuple[bool, _GstMapInfo]: ...

    def unmap(self, map_info: _GstMapInfo) -> None: ...


class _GstSample(Protocol):
    def get_buffer(self) -> _GstBuffer: ...


def build_rtsp_appsink_pipeline(
    source_uri: str,
    *,
    mode: AppSinkPipelineMode,
    target_width: int | None,
    target_height: int | None,
    protocols: str,
    latency_ms: int,
    drop_on_latency: bool,
    appsink_supports_leaky_type: bool,
    decoder_supports_disable_dpb: bool,
) -> str:
    _validate_gst_flag_value("protocols", protocols)
    drop_value = "true" if drop_on_latency else "false"
    caps = "video/x-raw,format=BGR"
    dimensions = ""
    if target_width is not None and target_height is not None:
        dimensions = f",width={int(target_width)},height={int(target_height)}"

    queue = "queue max-size-buffers=1 max-size-bytes=0 max-size-time=0 leaky=downstream"
    sink = "appsink name=sink sync=false max-buffers=1 drop=true emit-signals=false"
    if appsink_supports_leaky_type:
        sink = f"{sink} leaky-type=downstream"

    if mode is AppSinkPipelineMode.JETSON_NATIVE:
        decoder = "nvv4l2decoder"
        if decoder_supports_disable_dpb:
            decoder = f"{decoder} disable-dpb=true"
        decode_chain = (
            f"{decoder} ! {queue} ! "
            f"nvvidconv ! video/x-raw,format=BGRx{dimensions} ! videoconvert"
        )
    else:
        if dimensions:
            caps = f"{caps}{dimensions}"
            decode_chain = f"avdec_h264 ! {queue} ! videoconvert ! videoscale"
        else:
            decode_chain = f"avdec_h264 ! {queue} ! videoconvert"

    location = _quote_gst_string(source_uri)
    return (
        f"rtspsrc location={location} protocols={protocols} "
        f"latency={int(latency_ms)} drop-on-latency={drop_value} ! "
        f"rtph264depay ! h264parse ! {decode_chain} ! {caps} ! {sink}"
    )


def redact_pipeline(pipeline: str) -> str:
    def replace(match: re.Match[str]) -> str:
        value = match.group("value")
        if value.startswith('"') and value.endswith('"'):
            location = _unquote_gst_string(value)
            return f"location={_quote_gst_string(redact_url_secrets(location))}"
        return f"location={redact_url_secrets(value)}"

    return _GST_LOCATION_PROPERTY_PATTERN.sub(replace, pipeline)


class GStreamerAppSinkCapture:
    def __init__(
        self,
        *,
        runtime: AppSinkRuntime,
        width: int,
        height: int,
        media_pipeline_mode: str,
        read_timeout_s: float,
    ) -> None:
        width = _validate_positive_dimension("width", width)
        height = _validate_positive_dimension("height", height)
        read_timeout_s = _validate_read_timeout(read_timeout_s)
        self._runtime = runtime
        self._width = width
        self._height = height
        self._media_pipeline_mode = media_pipeline_mode
        self._read_timeout_s = read_timeout_s
        self._last_stage_timings: dict[str, float] = {}
        self._released = False

    @classmethod
    def create(
        cls,
        *,
        pipeline: str,
        runtime: AppSinkRuntime,
        width: int,
        height: int,
        media_pipeline_mode: str,
        read_timeout_s: float,
    ) -> GStreamerAppSinkCapture:
        _validate_positive_dimension("width", width)
        _validate_positive_dimension("height", height)
        _validate_read_timeout(read_timeout_s)
        runtime.start(pipeline)
        try:
            return cls(
                runtime=runtime,
                width=width,
                height=height,
                media_pipeline_mode=media_pipeline_mode,
                read_timeout_s=read_timeout_s,
            )
        except Exception:
            runtime.stop()
            raise

    def read(self) -> tuple[bool, Frame | None]:
        started_at = perf_counter()
        sample = self._runtime.pull_sample(self._read_timeout_s)
        pulled_at = perf_counter()
        if sample is None:
            self._last_stage_timings = {
                "wait": max(0.0, pulled_at - started_at),
            }
            return False, None

        frame = self._runtime.sample_to_bgr(
            sample,
            width=self._width,
            height=self._height,
        )
        completed_at = perf_counter()
        self._last_stage_timings = {
            "wait": max(0.0, pulled_at - started_at),
            "decode_read": max(0.0, completed_at - started_at),
        }
        return True, frame

    def release(self) -> None:
        if self._released:
            return
        self._released = True
        self._runtime.stop()

    def last_stage_timings(self) -> dict[str, float]:
        return dict(self._last_stage_timings)

    def media_pipeline_mode(self) -> str:
        return self._media_pipeline_mode

    def media_capture_backend(self) -> str:
        return "gstreamer_appsink"


class PyGObjectAppSinkRuntime:
    def __init__(self) -> None:
        self._gst, self._gst_app = _import_gst_modules()
        self._gst.init(None)
        self._pipeline: Any | None = None
        self._sink: Any | None = None

    def start(self, pipeline: str) -> None:
        self.stop()
        parsed = self._gst.parse_launch(pipeline)
        sink = parsed.get_by_name("sink")
        if sink is None:
            parsed.set_state(self._gst.State.NULL)
            raise RuntimeError(
                "GStreamer appsink pipeline does not contain sink named 'sink'.",
            )

        self._pipeline = parsed
        self._sink = sink
        result = parsed.set_state(self._gst.State.PLAYING)
        if result == self._gst.StateChangeReturn.FAILURE:
            self._pipeline = None
            self._sink = None
            parsed.set_state(self._gst.State.NULL)
            raise RuntimeError(
                "GStreamer appsink pipeline failed to enter PLAYING state.",
            )

    def pull_sample(self, timeout_s: float) -> object | None:
        if self._sink is None:
            return None
        timeout_ns = int(max(0.0, timeout_s) * self._gst.SECOND)
        sample = self._sink.emit("try-pull-sample", timeout_ns)
        return cast(object | None, sample)

    def sample_to_bgr(self, sample: object, *, width: int, height: int) -> Frame:
        buffer = cast(_GstSample, sample).get_buffer()
        success, map_info = buffer.map(self._gst.MapFlags.READ)
        if not success:
            raise RuntimeError("Unable to map GStreamer appsink buffer.")
        try:
            return _mapped_bgr_frame_to_array(
                map_info.data,
                width=width,
                height=height,
            )
        finally:
            buffer.unmap(map_info)

    def stop(self) -> None:
        pipeline = self._pipeline
        self._pipeline = None
        self._sink = None
        if pipeline is not None:
            pipeline.set_state(self._gst.State.NULL)


def probe_appsink_capabilities(
    mode: AppSinkPipelineMode = AppSinkPipelineMode.JETSON_NATIVE,
) -> AppSinkCapabilities:
    try:
        gst, _gst_app = _import_gst_modules()
    except Exception as exc:
        return AppSinkCapabilities(available=False, reason=str(exc))

    try:
        pipeline_mode = AppSinkPipelineMode(mode)
        gst.init(None)
        registry = gst.Registry.get()
        missing = [
            name
            for name in _required_appsink_pipeline_elements(pipeline_mode)
            if registry.find_feature(name, gst.ElementFactory) is None
        ]
        if missing:
            return AppSinkCapabilities(
                available=False,
                reason=f"missing GStreamer elements: {', '.join(missing)}",
            )

        appsink_supports_leaky_type = _element_factory_has_property(
            registry.find_feature("appsink", gst.ElementFactory),
            "leaky-type",
        )
        decoder_supports_disable_dpb = False
        if pipeline_mode is AppSinkPipelineMode.JETSON_NATIVE:
            decoder_supports_disable_dpb = _element_factory_has_property(
                registry.find_feature("nvv4l2decoder", gst.ElementFactory),
                "disable-dpb",
            )
    except Exception as exc:
        return AppSinkCapabilities(available=False, reason=str(exc))

    return AppSinkCapabilities(
        available=True,
        appsink_supports_leaky_type=appsink_supports_leaky_type,
        decoder_supports_disable_dpb=decoder_supports_disable_dpb,
    )


def _import_gst_modules() -> tuple[Any, Any]:
    gi = importlib.import_module("gi")
    gi.require_version("Gst", "1.0")
    gi.require_version("GstApp", "1.0")
    gst = importlib.import_module("gi.repository.Gst")
    gst_app = importlib.import_module("gi.repository.GstApp")
    return gst, gst_app


def _validate_gst_flag_value(name: str, value: str) -> None:
    if not _GST_FLAG_VALUE_PATTERN.fullmatch(value):
        raise ValueError(f"Invalid GStreamer {name} value: {value!r}")


def _quote_gst_string(value: str) -> str:
    if "\x00" in value:
        raise ValueError("GStreamer location value must not contain NUL bytes.")
    replacements = {
        "\\": "\\\\",
        '"': '\\"',
        "\n": "\\n",
        "\r": "\\r",
        "\t": "\\t",
    }
    escaped = "".join(replacements.get(character, character) for character in value)
    return f'"{escaped}"'


def _unquote_gst_string(value: str) -> str:
    if not (value.startswith('"') and value.endswith('"')):
        return value
    body = value[1:-1]
    replacements = {
        "n": "\n",
        "r": "\r",
        "t": "\t",
    }
    result: list[str] = []
    escaped = False
    for character in body:
        if escaped:
            result.append(replacements.get(character, character))
            escaped = False
            continue
        if character == "\\":
            escaped = True
            continue
        result.append(character)
    if escaped:
        result.append("\\")
    return "".join(result)


def _validate_positive_dimension(name: str, value: int) -> int:
    parsed = int(value)
    if parsed <= 0:
        raise ValueError(f"{name} must be positive.")
    return parsed


def _validate_read_timeout(read_timeout_s: float) -> float:
    value = float(read_timeout_s)
    if not isfinite(value) or value < 0.0:
        raise ValueError("read_timeout_s must be a finite non-negative value.")
    return value


def _mapped_bgr_frame_to_array(
    data: bytes | bytearray | memoryview,
    *,
    width: int,
    height: int,
) -> Frame:
    width = _validate_positive_dimension("width", width)
    height = _validate_positive_dimension("height", height)
    row_size = width * 3
    expected_size = row_size * height
    mapped = np.frombuffer(data, dtype=np.uint8)
    if mapped.size == expected_size:
        return mapped.reshape((height, width, 3)).copy()

    if mapped.size % height != 0:
        raise RuntimeError(
            "Unexpected GStreamer appsink buffer size "
            f"{mapped.size}; expected {expected_size} bytes for {width}x{height} BGR.",
        )

    row_stride = mapped.size // height
    if row_stride < row_size:
        raise RuntimeError(
            "Unexpected GStreamer appsink buffer size "
            f"{mapped.size}; expected {expected_size} bytes for {width}x{height} BGR.",
        )

    if mapped.size > expected_size:
        rows = [
            mapped[row_index * row_stride : row_index * row_stride + row_size]
            for row_index in range(height)
        ]
        if all(row.size == row_size for row in rows):
            return cast(Frame, np.concatenate(rows).reshape((height, width, 3)).copy())

    raise RuntimeError(
        "Unexpected GStreamer appsink buffer size "
        f"{mapped.size}; expected {expected_size} bytes for {width}x{height} BGR.",
    )


def _required_appsink_pipeline_elements(
    mode: AppSinkPipelineMode,
) -> tuple[str, ...]:
    if mode is AppSinkPipelineMode.JETSON_NATIVE:
        return (
            *_COMMON_APPSINK_PIPELINE_ELEMENTS,
            *_NATIVE_APPSINK_PIPELINE_ELEMENTS,
        )
    return (
        *_COMMON_APPSINK_PIPELINE_ELEMENTS,
        *_SOFTWARE_APPSINK_PIPELINE_ELEMENTS,
    )


def _element_factory_has_property(factory: object | None, property_name: str) -> bool:
    if factory is None:
        return False
    create = getattr(factory, "create", None)
    if not callable(create):
        return False
    element = create(None)
    if element is None:
        return False
    find_property = getattr(element, "find_property", None)
    if not callable(find_property):
        return False
    return find_property(property_name) is not None
