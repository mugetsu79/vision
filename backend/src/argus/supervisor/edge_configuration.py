from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from argus.api.contracts import EdgeConfigurationResponse
from argus.models.enums import EdgeConfigurationApplyStatus

SUPERVISOR_EDGE_CONFIGURATION_SUPPORTED_KEYS = {
    "model_store_path",
    "artifact_store_path",
    "service_report_interval_seconds",
    "hardware_report_interval_seconds",
}


@dataclass(frozen=True, slots=True)
class EdgeConfigurationApplyReport:
    revision: int
    status: EdgeConfigurationApplyStatus
    error: str | None = None


@dataclass(frozen=True, slots=True)
class _PlannedEdgeConfiguration:
    model_store_path: Path | None
    artifact_store_path: Path | None
    service_report_interval_seconds: float | None
    hardware_report_interval_seconds: float | None


class EdgeConfigurationApplier:
    def __init__(self) -> None:
        self.model_store_path: Path | None = None
        self.artifact_store_path: Path | None = None
        self.service_report_interval_seconds: float | None = None
        self.hardware_report_interval_seconds: float | None = None

    async def apply(
        self,
        configuration: EdgeConfigurationResponse,
    ) -> EdgeConfigurationApplyReport:
        desired_config = dict(configuration.desired_config or {})
        unsupported_keys = sorted(
            set(desired_config) - SUPERVISOR_EDGE_CONFIGURATION_SUPPORTED_KEYS
        )
        if unsupported_keys:
            return EdgeConfigurationApplyReport(
                revision=configuration.revision,
                status=EdgeConfigurationApplyStatus.FAILED,
                error=_unsupported_key_message(unsupported_keys),
            )

        try:
            planned = self._planned_configuration(desired_config)
            for path in (planned.model_store_path, planned.artifact_store_path):
                if path is not None:
                    path.mkdir(parents=True, exist_ok=True)
        except (OSError, ValueError) as exc:
            return EdgeConfigurationApplyReport(
                revision=configuration.revision,
                status=EdgeConfigurationApplyStatus.FAILED,
                error=str(exc),
            )

        self.model_store_path = planned.model_store_path
        self.artifact_store_path = planned.artifact_store_path
        self.service_report_interval_seconds = planned.service_report_interval_seconds
        self.hardware_report_interval_seconds = planned.hardware_report_interval_seconds
        return EdgeConfigurationApplyReport(
            revision=configuration.revision,
            status=EdgeConfigurationApplyStatus.APPLIED,
            error=None,
        )

    def _planned_configuration(
        self,
        desired_config: dict[str, object],
    ) -> _PlannedEdgeConfiguration:
        return _PlannedEdgeConfiguration(
            model_store_path=_store_directory_or_current(
                desired_config,
                "model_store_path",
                self.model_store_path,
            ),
            artifact_store_path=_store_directory_or_current(
                desired_config,
                "artifact_store_path",
                self.artifact_store_path,
            ),
            service_report_interval_seconds=_interval_or_current(
                desired_config,
                "service_report_interval_seconds",
                self.service_report_interval_seconds,
            ),
            hardware_report_interval_seconds=_interval_or_current(
                desired_config,
                "hardware_report_interval_seconds",
                self.hardware_report_interval_seconds,
            ),
        )


def _store_directory_or_current(
    desired_config: dict[str, object],
    key: str,
    current: Path | None,
) -> Path | None:
    if key not in desired_config:
        return current
    return _validate_store_directory(desired_config[key], key)


def _validate_store_directory(value: object, key: str) -> Path:
    if not isinstance(value, str) or not value:
        raise ValueError(f"Edge configuration {key} must be a non-empty string.")
    path = Path(value).expanduser()
    if not path.is_absolute():
        raise ValueError(f"Edge configuration {key} must be an absolute path.")
    if path.exists() and not path.is_dir():
        raise ValueError(f"Edge configuration {key} exists and is not a directory.")
    return path


def _interval_or_current(
    desired_config: dict[str, object],
    key: str,
    current: float | None,
) -> float | None:
    if key not in desired_config:
        return current
    return _positive_interval(desired_config[key], key)


def _positive_interval(value: object, key: str) -> float:
    if isinstance(value, bool) or not isinstance(value, int | float):
        raise ValueError(f"Edge configuration {key} must be a positive number.")
    if value <= 0:
        raise ValueError(f"Edge configuration {key} must be greater than zero.")
    return float(value)


def _unsupported_key_message(keys: list[str]) -> str:
    joined = ", ".join(keys)
    if len(keys) == 1:
        return f"Unsupported edge configuration key: {joined}."
    return f"Unsupported edge configuration keys: {joined}."
