from __future__ import annotations

from enum import StrEnum


class RoleEnum(StrEnum):
    VIEWER = "viewer"
    OPERATOR = "operator"
    ADMIN = "admin"
    SUPERADMIN = "superadmin"


class ProcessingMode(StrEnum):
    CENTRAL = "central"
    EDGE = "edge"
    HYBRID = "hybrid"


class TrackerType(StrEnum):
    BOTSORT = "botsort"
    BYTETRACK = "bytetrack"
    OCSORT = "ocsort"


class ModelTask(StrEnum):
    DETECT = "detect"
    CLASSIFY = "classify"
    ATTRIBUTE = "attribute"


class HistoryMetric(StrEnum):
    OCCUPANCY = "occupancy"
    COUNT_EVENTS = "count_events"
    OBSERVATIONS = "observations"


class CountEventType(StrEnum):
    LINE_CROSS = "line_cross"
    ZONE_ENTER = "zone_enter"
    ZONE_EXIT = "zone_exit"


class ModelFormat(StrEnum):
    ONNX = "onnx"
    ENGINE = "engine"


class RuleAction(StrEnum):
    COUNT = "count"
    ALERT = "alert"
    RECORD_CLIP = "record_clip"
    WEBHOOK = "webhook"
