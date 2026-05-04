from __future__ import annotations

import json
import math
import subprocess
from fractions import Fraction

from argus.api.contracts import SourceCapability
from argus.core.config import Settings
from argus.core.logging import redact_url_secrets

_FFPROBE_TIMEOUT_SECONDS = 8.0
_RTSP_TIMEOUT_US = "5000000"
_ANALYZE_DURATION_US = "5000000"
_PROBE_SIZE = "5000000"


def probe_rtsp_source(
    rtsp_url: str,
    *,
    settings: Settings | None = None,
) -> SourceCapability:
    _ = settings
    command = [
        "ffprobe",
        "-v",
        "error",
        "-rtsp_transport",
        "tcp",
        "-rw_timeout",
        _RTSP_TIMEOUT_US,
        "-analyzeduration",
        _ANALYZE_DURATION_US,
        "-probesize",
        _PROBE_SIZE,
        "-select_streams",
        "v:0",
        "-show_entries",
        "stream=width,height,codec_name,r_frame_rate,avg_frame_rate",
        "-of",
        "json",
        rtsp_url,
    ]
    try:
        completed = subprocess.run(
            command,
            check=True,
            capture_output=True,
            text=True,
            timeout=_FFPROBE_TIMEOUT_SECONDS,
        )
    except subprocess.TimeoutExpired as exc:
        raise RuntimeError(
            "ffprobe timed out while probing source capability for "
            f"{redact_url_secrets(rtsp_url)}."
        ) from exc
    except subprocess.CalledProcessError as exc:
        raise RuntimeError(
            "ffprobe failed while probing source capability for "
            f"{redact_url_secrets(rtsp_url)}: {exc.stderr[-500:]}"
        ) from exc
    except OSError as exc:
        raise RuntimeError(
            "ffprobe is not available while probing source capability for "
            f"{redact_url_secrets(rtsp_url)}."
        ) from exc

    payload = json.loads(completed.stdout)
    streams = payload.get("streams", [])
    if not streams:
        raise RuntimeError(
            "ffprobe did not return a video stream while probing source capability for "
            f"{redact_url_secrets(rtsp_url)}."
        )

    stream = streams[0]
    width = _positive_int(stream.get("width"), "width")
    height = _positive_int(stream.get("height"), "height")
    fps = _parse_fps(stream.get("avg_frame_rate")) or _parse_fps(stream.get("r_frame_rate"))
    codec = stream.get("codec_name")

    return SourceCapability(
        width=width,
        height=height,
        fps=fps,
        codec=str(codec) if codec else None,
        aspect_ratio=_aspect_ratio(width, height),
    )


def _positive_int(value: object, field_name: str) -> int:
    try:
        if value is None:
            parsed = 0
        elif isinstance(value, int | str | bytes | bytearray):
            parsed = int(value)
        else:
            raise TypeError
    except (TypeError, ValueError):
        raise RuntimeError(f"ffprobe returned non-numeric source {field_name}: {value!r}") from None
    if parsed <= 0:
        raise RuntimeError(f"ffprobe returned invalid source {field_name}: {parsed}")
    return parsed


def _parse_fps(value: object) -> int | None:
    if not value or not isinstance(value, str) or value == "0/0":
        return None
    try:
        rate = Fraction(value)
    except (ValueError, ZeroDivisionError):
        return None
    if rate <= 0:
        return None
    return max(1, round(float(rate)))


def _aspect_ratio(width: int, height: int) -> str:
    divisor = math.gcd(width, height)
    return f"{width // divisor}:{height // divisor}"
