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


class ModelFormat(StrEnum):
    ONNX = "onnx"
    ENGINE = "engine"


class RuleAction(StrEnum):
    COUNT = "count"
    ALERT = "alert"
    RECORD_CLIP = "record_clip"
    WEBHOOK = "webhook"
