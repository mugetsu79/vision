from __future__ import annotations

# Analyze long enough to catch the first H.264 SPS + keyframe even on slow
# streams (e.g. 5 fps with a 60-frame GOP = 12 s between keyframes), plus
# allowance for MediaMTX UDP->TCP renegotiation when first connecting upstream.
# ffmpeg's default 5 s analyzeduration was tripping on such streams and
# returning zero dimensions / empty media-info.
_FFMPEG_ANALYZE_DURATION_US = "60000000"  # 60 seconds
_FFMPEG_PROBE_SIZE = "64000000"  # 64 MB
_FFMPEG_DIMENSION_PROBE_TIMEOUT_S = 20.0
_FFMPEG_FRAME_WAIT_TIMEOUT_S = 20.0
_FFMPEG_RTSP_TIMEOUT_US = str(int(_FFMPEG_FRAME_WAIT_TIMEOUT_S * 1_000_000))
_OPENCV_CAPTURE_OPEN_TIMEOUT_MS = int(_FFMPEG_DIMENSION_PROBE_TIMEOUT_S * 1000)
_OPENCV_CAPTURE_READ_TIMEOUT_MS = int(_FFMPEG_FRAME_WAIT_TIMEOUT_S * 1000)
_OPENCV_FFMPEG_CAPTURE_OPTIONS = (
    f"rtsp_transport;tcp|analyzeduration;{_FFMPEG_ANALYZE_DURATION_US}"
    f"|probesize;{_FFMPEG_PROBE_SIZE}|timeout;{_FFMPEG_RTSP_TIMEOUT_US}"
)
