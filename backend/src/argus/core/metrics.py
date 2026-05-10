from __future__ import annotations

from prometheus_client import Counter, Gauge, Histogram

HTTP_REQUESTS_TOTAL = Counter(
    "argus_http_requests_total",
    "Total number of HTTP requests handled by the backend.",
    ["method", "path", "status_code"],
)
HTTP_REQUEST_DURATION_SECONDS = Histogram(
    "argus_http_request_duration_seconds",
    "Latency of HTTP requests handled by the backend.",
    ["method", "path"],
)
APP_INFO = Gauge(
    "argus_app_info",
    "Argus application metadata.",
    ["app_name", "environment"],
)
WEBSOCKET_CONNECTIONS = Gauge(
    "argus_websocket_connections",
    "Active telemetry websocket connections.",
    ["tenant"],
)
WEBSOCKET_DISCONNECTS_TOTAL = Counter(
    "argus_websocket_disconnects_total",
    "Telemetry websocket disconnects observed by the backend.",
    ["tenant"],
)
INFERENCE_FRAMES_PROCESSED_TOTAL = Counter(
    "argus_inference_frames_processed_total",
    "Frames processed by an inference worker.",
    ["camera_id", "profile", "stream_mode"],
)
INFERENCE_FRAME_DURATION_SECONDS = Histogram(
    "argus_inference_frame_duration_seconds",
    "Per-frame inference duration.",
    ["camera_id"],
)
INFERENCE_STAGE_DURATION_SECONDS = Histogram(
    "argus_inference_stage_duration_seconds",
    "Per-stage inference duration.",
    ["camera_id", "stage"],
)
CANDIDATE_REJECTED_TOTAL = Counter(
    "argus_candidate_rejected_total",
    "Candidate detections rejected by the quality gate.",
    ["camera_id", "class_name", "reason"],
)
CANDIDATE_PASSED_TOTAL = Counter(
    "argus_candidate_passed_total",
    "Candidate detections accepted by the quality gate.",
    ["camera_id", "class_name", "reason"],
)
DETECTION_REGION_FILTERED_TOTAL = Counter(
    "argus_detection_region_filtered_total",
    "Detections removed by detection-region policy filtering.",
    ["camera_id", "class_name", "reason", "mode"],
)
MOTION_SPEED_SAMPLES_TOTAL = Counter(
    "argus_motion_speed_samples_total",
    "Motion speed samples produced by calibrated inference.",
    ["camera_id", "class_name"],
)
MOTION_SPEED_DISABLED_TOTAL = Counter(
    "argus_motion_speed_disabled_total",
    "Frames where motion speed metrics were disabled or unavailable.",
    ["camera_id", "mode", "reason"],
)
PRIVACY_FILTER_OPERATIONS_TOTAL = Counter(
    "argus_privacy_filter_operations_total",
    "Privacy filter operations by result.",
    ["result"],
)
TRACKING_EVENT_WRITE_FAILURES_TOTAL = Counter(
    "argus_tracking_event_write_failures_total",
    "Tracking event persistence failures.",
    ["store"],
)
