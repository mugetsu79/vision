from __future__ import annotations

from datetime import datetime
from uuid import uuid4

import pytest

from argus.api.contracts import EdgeConfigurationResponse
from argus.compat import UTC
from argus.models.enums import EdgeConfigurationApplyStatus
from argus.supervisor.edge_configuration import EdgeConfigurationApplier


@pytest.mark.asyncio
async def test_edge_configuration_applies_store_paths_and_intervals(tmp_path) -> None:
    model_store = tmp_path / "models"
    artifact_store = tmp_path / "artifacts"
    applier = EdgeConfigurationApplier()

    report = await applier.apply(
        _configuration(
            revision=1,
            desired_config={
                "model_store_path": str(model_store),
                "artifact_store_path": str(artifact_store),
                "service_report_interval_seconds": 20,
                "hardware_report_interval_seconds": 45,
            },
        )
    )

    assert report.status is EdgeConfigurationApplyStatus.APPLIED
    assert report.error is None
    assert model_store.is_dir()
    assert artifact_store.is_dir()
    assert applier.model_store_path == model_store
    assert applier.artifact_store_path == artifact_store
    assert applier.service_report_interval_seconds == 20
    assert applier.hardware_report_interval_seconds == 45


@pytest.mark.asyncio
async def test_edge_configuration_rejects_unsupported_key() -> None:
    applier = EdgeConfigurationApplier()

    report = await applier.apply(
        _configuration(
            revision=2,
            desired_config={"shell_command": "rm -rf /"},
        )
    )

    assert report.revision == 2
    assert report.status is EdgeConfigurationApplyStatus.FAILED
    assert report.error is not None
    assert "Unsupported edge configuration key" in report.error
    assert "shell_command" in report.error


@pytest.mark.asyncio
async def test_edge_configuration_failure_does_not_partially_update_state(tmp_path) -> None:
    original_store = tmp_path / "original"
    next_store = tmp_path / "next"
    applier = EdgeConfigurationApplier()
    await applier.apply(
        _configuration(
            revision=1,
            desired_config={"model_store_path": str(original_store)},
        )
    )

    report = await applier.apply(
        _configuration(
            revision=2,
            desired_config={
                "model_store_path": str(next_store),
                "service_report_interval_seconds": 0,
            },
        )
    )

    assert report.status is EdgeConfigurationApplyStatus.FAILED
    assert applier.model_store_path == original_store
    assert not next_store.exists()


@pytest.mark.asyncio
async def test_edge_configuration_reports_applied_revision(tmp_path) -> None:
    applier = EdgeConfigurationApplier()

    report = await applier.apply(
        _configuration(
            revision=3,
            desired_config={"model_store_path": str(tmp_path / "models")},
        )
    )

    assert report.revision == 3
    assert report.status is EdgeConfigurationApplyStatus.APPLIED
    assert report.error is None


def _configuration(
    *,
    revision: int,
    desired_config: dict[str, object],
) -> EdgeConfigurationResponse:
    now = datetime(2026, 6, 8, 9, 0, tzinfo=UTC)
    return EdgeConfigurationResponse(
        id=uuid4(),
        tenant_id=uuid4(),
        deployment_node_id=uuid4(),
        revision=revision,
        desired_config=desired_config,
        applied_revision=None,
        apply_status=EdgeConfigurationApplyStatus.PENDING,
        last_applied_at=None,
        error=None,
        created_at=now,
        updated_at=now,
    )
