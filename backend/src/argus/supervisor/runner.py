from __future__ import annotations

import argparse
import asyncio
import logging
import os
from dataclasses import dataclass
from typing import Protocol
from uuid import UUID

from argus.api.contracts import (
    EdgeNodeHardwareReportCreate,
    FleetOverviewResponse,
    HardwarePerformanceSample,
)
from argus.supervisor.hardware_probe import HostCapabilityProbe
from argus.supervisor.metrics_probe import WorkerMetricsContext, WorkerMetricsProbe
from argus.supervisor.operations_client import (
    BearerTokenProvider,
    PasswordGrantTokenProvider,
    SupervisorOperationsClient,
)
from argus.supervisor.process_adapter import LocalWorkerProcessAdapter, WorkerLaunchConfig
from argus.supervisor.reconciler import SupervisorReconciler

LOGGER = logging.getLogger(__name__)
_NIL_TENANT_ID = UUID(int=0)


class HardwareProbe(Protocol):
    def build_hardware_report(
        self,
        *,
        edge_node_id: UUID | None,
        observed_performance: list[HardwarePerformanceSample],
    ) -> EdgeNodeHardwareReportCreate: ...


class MetricsProbe(Protocol):
    async def build_performance_samples(
        self,
        worker_contexts: object,
        previous_snapshot: object | None = None,
    ) -> list[HardwarePerformanceSample]: ...


@dataclass(frozen=True, slots=True)
class RunnerConfig:
    supervisor_id: str
    role: str
    api_base_url: str
    bearer_token: str | None = None
    edge_node_id: UUID | None = None
    worker_metrics_url: str | None = None
    token_url: str | None = None
    token_client_id: str = "argus-cli"
    token_username: str | None = None
    token_password: str | None = None
    token_client_secret: str | None = None
    token_scope: str | None = None
    hardware_report_interval_seconds: float = 60.0
    poll_interval_seconds: float = 5.0
    once: bool = False
    tenant_id: UUID = _NIL_TENANT_ID


class SupervisorRunner:
    def __init__(
        self,
        *,
        supervisor_id: str,
        edge_node_id: UUID | None,
        hardware_probe: HardwareProbe,
        metrics_probe: MetricsProbe | None,
        operations: object,
        process_adapter: object,
        tenant_id: UUID = _NIL_TENANT_ID,
        limit: int = 10,
    ) -> None:
        self.supervisor_id = supervisor_id
        self.edge_node_id = edge_node_id
        self.hardware_probe = hardware_probe
        self.metrics_probe = metrics_probe
        self.operations = operations
        self.reconciler = SupervisorReconciler(
            operations=operations,  # type: ignore[arg-type]
            process_adapter=process_adapter,  # type: ignore[arg-type]
            tenant_id=tenant_id,
            supervisor_id=supervisor_id,
            edge_node_id=edge_node_id,
            limit=limit,
        )

    async def run_once(self) -> int:
        fleet = await self._fetch_fleet_overview()
        worker_contexts = _worker_contexts_from_fleet(fleet)
        observed_performance = await self._performance_samples(worker_contexts)
        report = self.hardware_probe.build_hardware_report(
            edge_node_id=self.edge_node_id,
            observed_performance=observed_performance,
        )
        await self.operations.record_hardware_report(report)  # type: ignore[attr-defined]
        LOGGER.info(
            "Supervisor hardware report posted supervisor_id=%s edge_node_id=%s "
            "host_profile=%s performance_samples=%s",
            self.supervisor_id,
            self.edge_node_id,
            report.host_profile,
            len(report.observed_performance),
        )
        return await self.reconciler.reconcile_once()

    async def run_forever(
        self,
        *,
        hardware_report_interval_seconds: float,
        poll_interval_seconds: float,
    ) -> None:
        next_hardware_report_after = 0.0
        loop = asyncio.get_running_loop()
        while True:
            now = loop.time()
            if now >= next_hardware_report_after:
                await self.run_once()
                next_hardware_report_after = now + hardware_report_interval_seconds
            else:
                await self.reconciler.reconcile_once()
            await asyncio.sleep(poll_interval_seconds)

    async def _fetch_fleet_overview(self) -> FleetOverviewResponse | None:
        fetch = getattr(self.operations, "fetch_fleet_overview", None)
        if fetch is None:
            return None
        try:
            return await fetch()
        except Exception as exc:
            LOGGER.warning("Supervisor fleet overview fetch failed: %s", exc)
            return None

    async def _performance_samples(
        self,
        worker_contexts: list[WorkerMetricsContext],
    ) -> list[HardwarePerformanceSample]:
        if self.metrics_probe is None:
            return []
        try:
            return await self.metrics_probe.build_performance_samples(worker_contexts)
        except Exception as exc:
            LOGGER.warning("Supervisor metrics scrape failed: %s", exc)
            return []


def build_runner(config: RunnerConfig) -> SupervisorRunner:
    token_provider = _build_token_provider(config)
    operations = SupervisorOperationsClient(
        api_base_url=config.api_base_url,
        supervisor_id=config.supervisor_id,
        bearer_token=config.bearer_token,
        token_provider=token_provider,
    )
    return SupervisorRunner(
        supervisor_id=config.supervisor_id,
        edge_node_id=config.edge_node_id,
        hardware_probe=HostCapabilityProbe(),
        metrics_probe=WorkerMetricsProbe(config.worker_metrics_url),
        operations=operations,
        process_adapter=LocalWorkerProcessAdapter(
            WorkerLaunchConfig(
                api_base_url=config.api_base_url,
                bearer_token=config.bearer_token,
                bearer_token_provider=token_provider,
                edge_node_id=config.edge_node_id,
            )
        ),
        tenant_id=config.tenant_id,
    )


def parse_args(argv: list[str] | None = None) -> RunnerConfig:
    parser = argparse.ArgumentParser(description="Run a Vezor worker supervisor.")
    parser.add_argument("--supervisor-id", required=True)
    parser.add_argument("--role", required=True, choices=["central", "edge"])
    parser.add_argument("--edge-node-id")
    parser.add_argument("--api-base-url", default=os.getenv("ARGUS_API_BASE_URL"))
    parser.add_argument("--bearer-token", default=os.getenv("ARGUS_API_BEARER_TOKEN"))
    parser.add_argument("--token-url", default=os.getenv("ARGUS_API_TOKEN_URL"))
    parser.add_argument(
        "--token-client-id",
        default=os.getenv("ARGUS_API_TOKEN_CLIENT_ID", "argus-cli"),
    )
    parser.add_argument("--token-username", default=os.getenv("ARGUS_API_TOKEN_USERNAME"))
    parser.add_argument("--token-password", default=os.getenv("ARGUS_API_TOKEN_PASSWORD"))
    parser.add_argument(
        "--token-client-secret",
        default=os.getenv("ARGUS_API_TOKEN_CLIENT_SECRET"),
    )
    parser.add_argument("--token-scope", default=os.getenv("ARGUS_API_TOKEN_SCOPE"))
    parser.add_argument("--worker-metrics-url", default=os.getenv("ARGUS_WORKER_METRICS_URL"))
    parser.add_argument("--hardware-report-interval-seconds", type=float, default=60.0)
    parser.add_argument("--poll-interval-seconds", type=float, default=5.0)
    parser.add_argument("--once", action="store_true")
    args = parser.parse_args(argv)
    if not args.api_base_url:
        parser.error("--api-base-url or ARGUS_API_BASE_URL is required")
    has_refreshable_token = bool(args.token_url and args.token_username and args.token_password)
    if not args.bearer_token and not has_refreshable_token:
        parser.error(
            "--bearer-token/ARGUS_API_BEARER_TOKEN or "
            "--token-url plus --token-username plus --token-password is required"
        )
    edge_node_id = UUID(args.edge_node_id) if args.edge_node_id else None
    if args.role == "edge" and edge_node_id is None:
        parser.error("--edge-node-id is required for edge supervisors")
    if args.role == "central" and edge_node_id is not None:
        parser.error("--edge-node-id is only valid for edge supervisors")
    return RunnerConfig(
        supervisor_id=args.supervisor_id,
        role=args.role,
        api_base_url=args.api_base_url,
        bearer_token=args.bearer_token,
        edge_node_id=edge_node_id,
        worker_metrics_url=args.worker_metrics_url,
        token_url=args.token_url,
        token_client_id=args.token_client_id,
        token_username=args.token_username,
        token_password=args.token_password,
        token_client_secret=args.token_client_secret,
        token_scope=args.token_scope,
        hardware_report_interval_seconds=args.hardware_report_interval_seconds,
        poll_interval_seconds=args.poll_interval_seconds,
        once=args.once,
    )


async def async_main(argv: list[str] | None = None) -> int:
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    config = parse_args(argv)
    runner = build_runner(config)
    if config.once:
        await runner.run_once()
    else:
        await runner.run_forever(
            hardware_report_interval_seconds=config.hardware_report_interval_seconds,
            poll_interval_seconds=config.poll_interval_seconds,
        )
    return 0


def _build_token_provider(config: RunnerConfig) -> BearerTokenProvider | None:
    if not (config.token_url and config.token_username and config.token_password):
        return None
    return PasswordGrantTokenProvider(
        token_url=config.token_url,
        client_id=config.token_client_id,
        username=config.token_username,
        password=config.token_password,
        client_secret=config.token_client_secret,
        scope=config.token_scope,
    )


def main() -> None:
    raise SystemExit(asyncio.run(async_main()))


def _worker_contexts_from_fleet(
    fleet: FleetOverviewResponse | None,
) -> list[WorkerMetricsContext]:
    if fleet is None or not hasattr(fleet, "camera_workers"):
        return []
    contexts: list[WorkerMetricsContext] = []
    for worker in fleet.camera_workers:
        latest = worker.latest_model_admission
        passport = worker.runtime_passport
        stream = latest.stream_profile if latest is not None else {}
        backend = (
            (latest.selected_backend if latest is not None else None)
            or (passport.selected_backend if passport is not None else None)
            or (latest.recommended_backend if latest is not None else None)
            or "onnxruntime"
        )
        contexts.append(
            WorkerMetricsContext(
                camera_id=worker.camera_id,
                model_id=latest.model_id if latest is not None else None,
                model_name=latest.model_name if latest is not None else None,
                runtime_backend=backend,
                input_width=_positive_int(stream.get("width") or stream.get("input_width"), 1280),
                input_height=_positive_int(
                    stream.get("height") or stream.get("input_height"),
                    720,
                ),
                target_fps=_positive_float(stream.get("fps") or stream.get("target_fps"), 10.0),
            )
        )
    return contexts


def _positive_int(value: object, fallback: int) -> int:
    try:
        number = int(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return fallback
    return number if number > 0 else fallback


def _positive_float(value: object, fallback: float) -> float:
    try:
        number = float(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return fallback
    return number if number > 0 else fallback


if __name__ == "__main__":
    main()
