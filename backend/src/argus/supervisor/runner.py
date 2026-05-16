from __future__ import annotations

import argparse
import asyncio
import json
import logging
import os
import platform
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol, cast
from uuid import UUID

from argus.api.contracts import (
    EdgeNodeHardwareReportCreate,
    FleetOverviewResponse,
    HardwarePerformanceSample,
    SupervisorServiceReportCreate,
)
from argus.models.enums import (
    DeploymentCredentialStatus,
    DeploymentInstallStatus,
    DeploymentNodeKind,
    DeploymentServiceManager,
)
from argus.streaming.mediamtx import MediaMTXClient, PublishProfile
from argus.supervisor.credential_store import FileCredentialStore
from argus.supervisor.hardware_probe import HostCapabilityProbe
from argus.supervisor.metrics_probe import MetricsSnapshot, WorkerMetricsContext, WorkerMetricsProbe
from argus.supervisor.operations_client import (
    BearerTokenProvider,
    PasswordGrantTokenProvider,
    SupervisorOperationsClient,
)
from argus.supervisor.process_adapter import LocalWorkerProcessAdapter, WorkerLaunchConfig
from argus.supervisor.reconciler import SupervisorReconciler
from argus.supervisor.stream_provisioner import SupervisorStreamProvisioner

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
        worker_contexts: Iterable[WorkerMetricsContext],
        previous_snapshot: MetricsSnapshot | None = None,
    ) -> list[HardwarePerformanceSample]: ...


class StreamProvisioner(Protocol):
    async def ensure_fleet_streams(self, fleet: FleetOverviewResponse | None) -> None: ...


@dataclass(frozen=True, slots=True)
class RunnerConfig:
    supervisor_id: str
    role: str
    api_base_url: str
    bearer_token: str | None = None
    credential_store_path: Path | None = None
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
    product_mode: bool = False
    auth_mode: str = "static_bearer_dev"
    service_manager: DeploymentServiceManager = DeploymentServiceManager.DIRECT_CHILD
    supervisor_version: str | None = None
    hostname: str | None = None
    public_mediamtx_rtsp_url: str | None = None
    mediamtx_api_url: str | None = None
    mediamtx_rtsp_base_url: str | None = None
    mediamtx_whip_base_url: str | None = None
    mediamtx_username: str | None = None
    mediamtx_password: str | None = None
    publish_profile: str | None = None
    healthcheck: bool = False


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
        service_manager: DeploymentServiceManager = DeploymentServiceManager.DIRECT_CHILD,
        supervisor_version: str | None = None,
        hostname: str | None = None,
        public_mediamtx_rtsp_url: str | None = None,
        product_mode: bool = False,
        auth_mode: str = "static_bearer_dev",
        stream_provisioner: StreamProvisioner | None = None,
    ) -> None:
        self.supervisor_id = supervisor_id
        self.edge_node_id = edge_node_id
        self.node_kind = (
            DeploymentNodeKind.EDGE if edge_node_id is not None else DeploymentNodeKind.CENTRAL
        )
        self.hardware_probe = hardware_probe
        self.metrics_probe = metrics_probe
        self.operations = operations
        self.service_manager = service_manager
        self.supervisor_version = supervisor_version
        self.hostname = hostname or platform.node() or supervisor_id
        self.public_mediamtx_rtsp_url = public_mediamtx_rtsp_url
        self.product_mode = product_mode
        self.auth_mode = auth_mode
        self.stream_provisioner = stream_provisioner
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
        await self._ensure_stream_paths(fleet)
        worker_contexts = _worker_contexts_from_fleet(fleet)
        observed_performance = await self._performance_samples(worker_contexts)
        report = self.hardware_probe.build_hardware_report(
            edge_node_id=self.edge_node_id,
            observed_performance=observed_performance,
        )
        await self._record_service_report(report)
        try:
            await self.operations.record_hardware_report(report)  # type: ignore[attr-defined]
        except Exception as exc:
            LOGGER.warning("Supervisor hardware report post failed: %s", exc)
            return 0
        LOGGER.info(
            "Supervisor hardware report posted supervisor_id=%s edge_node_id=%s "
            "host_profile=%s performance_samples=%s",
            self.supervisor_id,
            self.edge_node_id,
            report.host_profile,
            len(report.observed_performance),
        )
        return await self._reconcile_once(fleet=fleet)

    async def _record_service_report(self, report: EdgeNodeHardwareReportCreate) -> None:
        recorder = getattr(self.operations, "record_service_report", None)
        if recorder is None:
            return
        payload = SupervisorServiceReportCreate(
            node_kind=self.node_kind,
            edge_node_id=self.edge_node_id,
            hostname=self.hostname,
            service_manager=self.service_manager,
            service_status="running",
            install_status=DeploymentInstallStatus.HEALTHY,
            credential_status=DeploymentCredentialStatus.ACTIVE,
            version=self.supervisor_version,
            os_name=report.os_name,
            host_profile=report.host_profile,
            heartbeat_at=report.reported_at,
            diagnostics={
                "auth_mode": self.auth_mode,
                "product_mode": self.product_mode,
                **(
                    {"stream_rtsp_base_url": self.public_mediamtx_rtsp_url}
                    if self.public_mediamtx_rtsp_url
                    else {}
                ),
            },
        )
        try:
            await recorder(payload)
        except Exception as exc:
            LOGGER.warning("Supervisor service report post failed: %s", exc)
            return
        LOGGER.info(
            "Supervisor service report posted supervisor_id=%s edge_node_id=%s "
            "service_manager=%s",
            self.supervisor_id,
            self.edge_node_id,
            self.service_manager.value,
        )

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
                await self._reconcile_once()
            await asyncio.sleep(poll_interval_seconds)

    async def _fetch_fleet_overview(self) -> FleetOverviewResponse | None:
        fetch = getattr(self.operations, "fetch_fleet_overview", None)
        if fetch is None:
            return None
        try:
            return cast(FleetOverviewResponse, await fetch())
        except Exception as exc:
            LOGGER.warning("Supervisor fleet overview fetch failed: %s", exc)
            return None

    async def _reconcile_once(self, *, fleet: FleetOverviewResponse | None = None) -> int:
        try:
            return await self.reconciler.reconcile_once(fleet=fleet)
        except Exception as exc:
            LOGGER.warning("Supervisor reconciliation failed: %s", exc)
            return 0

    async def _ensure_stream_paths(self, fleet: FleetOverviewResponse | None) -> None:
        if self.stream_provisioner is None:
            return
        try:
            await self.stream_provisioner.ensure_fleet_streams(fleet)
        except Exception as exc:
            LOGGER.warning("Supervisor stream provisioning failed: %s", exc)

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
    credential_store = (
        FileCredentialStore(config.credential_store_path)
        if config.credential_store_path is not None
        else None
    )
    operations = SupervisorOperationsClient(
        api_base_url=config.api_base_url,
        supervisor_id=config.supervisor_id,
        bearer_token=config.bearer_token,
        token_provider=token_provider,
        credential_store=credential_store,
    )
    stream_provisioner = _build_stream_provisioner(config, operations=operations)
    worker_token_provider = token_provider or _credential_store_token_provider(credential_store)
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
                bearer_token_provider=worker_token_provider,
                edge_node_id=config.edge_node_id,
            )
        ),
        tenant_id=config.tenant_id,
        service_manager=config.service_manager,
        supervisor_version=config.supervisor_version,
        hostname=config.hostname,
        public_mediamtx_rtsp_url=config.public_mediamtx_rtsp_url,
        product_mode=config.product_mode,
        auth_mode=config.auth_mode,
        stream_provisioner=stream_provisioner,
    )


def _build_stream_provisioner(
    config: RunnerConfig,
    *,
    operations: SupervisorOperationsClient,
) -> SupervisorStreamProvisioner | None:
    mediamtx_api_url = config.mediamtx_api_url or os.getenv("ARGUS_MEDIAMTX_API_URL")
    mediamtx_rtsp_base_url = (
        config.mediamtx_rtsp_base_url or os.getenv("ARGUS_MEDIAMTX_RTSP_BASE_URL")
    )
    mediamtx_whip_base_url = (
        config.mediamtx_whip_base_url or os.getenv("ARGUS_MEDIAMTX_WHIP_BASE_URL")
    )
    if not mediamtx_api_url or not mediamtx_rtsp_base_url or not mediamtx_whip_base_url:
        return None
    try:
        publish_profile = PublishProfile(
            config.publish_profile or os.getenv("ARGUS_PUBLISH_PROFILE", "central-gpu")
        )
    except ValueError:
        publish_profile = PublishProfile.CENTRAL_GPU
    stream_client = MediaMTXClient(
        api_base_url=mediamtx_api_url,
        rtsp_base_url=mediamtx_rtsp_base_url,
        whip_base_url=mediamtx_whip_base_url,
        username=config.mediamtx_username or os.getenv("ARGUS_MEDIAMTX_USERNAME"),
        password=config.mediamtx_password or os.getenv("ARGUS_MEDIAMTX_PASSWORD"),
    )
    return SupervisorStreamProvisioner(
        operations=operations,
        stream_client=stream_client,
        edge_node_id=config.edge_node_id,
        publish_profile=publish_profile,
    )


def parse_args(argv: list[str] | None = None) -> RunnerConfig:
    parser = argparse.ArgumentParser(description="Run a Vezor worker supervisor.")
    parser.add_argument("--config")
    parser.add_argument("--supervisor-id")
    parser.add_argument("--role", choices=["central", "edge"])
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
    parser.add_argument(
        "--public-mediamtx-rtsp-url",
        default=os.getenv("ARGUS_PUBLIC_MEDIAMTX_RTSP_URL"),
    )
    parser.add_argument("--mediamtx-api-url", default=os.getenv("ARGUS_MEDIAMTX_API_URL"))
    parser.add_argument(
        "--mediamtx-rtsp-base-url",
        default=os.getenv("ARGUS_MEDIAMTX_RTSP_BASE_URL"),
    )
    parser.add_argument(
        "--mediamtx-whip-base-url",
        default=os.getenv("ARGUS_MEDIAMTX_WHIP_BASE_URL"),
    )
    parser.add_argument("--mediamtx-username", default=os.getenv("ARGUS_MEDIAMTX_USERNAME"))
    parser.add_argument("--mediamtx-password", default=os.getenv("ARGUS_MEDIAMTX_PASSWORD"))
    parser.add_argument("--publish-profile", default=os.getenv("ARGUS_PUBLISH_PROFILE"))
    parser.add_argument("--hardware-report-interval-seconds", type=float, default=60.0)
    parser.add_argument("--poll-interval-seconds", type=float, default=5.0)
    parser.add_argument("--once", action="store_true")
    parser.add_argument("--healthcheck", action="store_true")
    args = parser.parse_args(argv)

    if args.config:
        return _parse_config_file(args, parser)

    if not args.api_base_url:
        parser.error("--api-base-url or ARGUS_API_BASE_URL is required")
    if not args.supervisor_id:
        parser.error("--supervisor-id is required")
    if not args.role:
        parser.error("--role is required")
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
        product_mode=False,
        auth_mode="password_grant_dev" if has_refreshable_token else "static_bearer_dev",
        service_manager=DeploymentServiceManager.DIRECT_CHILD,
        public_mediamtx_rtsp_url=args.public_mediamtx_rtsp_url,
        mediamtx_api_url=args.mediamtx_api_url,
        mediamtx_rtsp_base_url=args.mediamtx_rtsp_base_url,
        mediamtx_whip_base_url=args.mediamtx_whip_base_url,
        mediamtx_username=args.mediamtx_username,
        mediamtx_password=args.mediamtx_password,
        publish_profile=args.publish_profile,
        healthcheck=args.healthcheck,
    )


def _parse_config_file(args: argparse.Namespace, parser: argparse.ArgumentParser) -> RunnerConfig:
    config_path = Path(args.config).expanduser().resolve()
    try:
        payload = json.loads(config_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        parser.error(f"unable to read supervisor config: {exc}")
    if not isinstance(payload, dict):
        parser.error("supervisor config must be a JSON object")

    supervisor_id = _required_string(payload, "supervisor_id", parser)
    role = _required_string(payload, "role", parser)
    if role not in {"central", "edge"}:
        parser.error("config role must be central or edge")
    api_base_url = _required_string(payload, "api_base_url", parser)
    edge_node_id = _optional_uuid(payload.get("edge_node_id"), parser, "edge_node_id")
    if role == "edge" and edge_node_id is None:
        parser.error("edge supervisor config requires edge_node_id")
    if role == "central" and edge_node_id is not None:
        parser.error("central supervisor config cannot include edge_node_id")
    credential_store_path = _config_path(
        payload.get("credential_store_path"),
        base_dir=config_path.parent,
        parser=parser,
    )
    if credential_store_path is None:
        parser.error("product supervisor config requires credential_store_path")
    return RunnerConfig(
        supervisor_id=supervisor_id,
        role=role,
        api_base_url=api_base_url,
        bearer_token=None,
        credential_store_path=credential_store_path,
        edge_node_id=edge_node_id,
        worker_metrics_url=_optional_string(payload.get("worker_metrics_url")),
        hardware_report_interval_seconds=float(
            payload.get(
                "hardware_report_interval_seconds",
                args.hardware_report_interval_seconds,
            )
        ),
        poll_interval_seconds=float(
            payload.get("poll_interval_seconds", args.poll_interval_seconds)
        ),
        once=args.once or bool(payload.get("once", False)),
        product_mode=True,
        auth_mode="credential_store",
        service_manager=_service_manager(payload.get("service_manager")),
        supervisor_version=_optional_string(payload.get("version")),
        hostname=_optional_string(payload.get("hostname")),
        public_mediamtx_rtsp_url=_optional_string(payload.get("public_mediamtx_rtsp_url")),
        mediamtx_api_url=(
            _optional_string(payload.get("mediamtx_api_url")) or args.mediamtx_api_url
        ),
        mediamtx_rtsp_base_url=(
            _optional_string(payload.get("mediamtx_rtsp_base_url"))
            or args.mediamtx_rtsp_base_url
        ),
        mediamtx_whip_base_url=(
            _optional_string(payload.get("mediamtx_whip_base_url"))
            or args.mediamtx_whip_base_url
        ),
        mediamtx_username=(
            _optional_string(payload.get("mediamtx_username")) or args.mediamtx_username
        ),
        mediamtx_password=(
            _optional_string(payload.get("mediamtx_password")) or args.mediamtx_password
        ),
        publish_profile=(
            _optional_string(payload.get("publish_profile")) or args.publish_profile
        ),
        healthcheck=args.healthcheck,
    )


def _required_string(
    payload: dict[str, object],
    key: str,
    parser: argparse.ArgumentParser,
) -> str:
    value = _optional_string(payload.get(key))
    if value is None:
        parser.error(f"supervisor config requires {key}")
    return value


def _optional_string(value: object) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _optional_uuid(
    value: object,
    parser: argparse.ArgumentParser,
    key: str,
) -> UUID | None:
    text = _optional_string(value)
    if text is None:
        return None
    try:
        return UUID(text)
    except ValueError:
        parser.error(f"supervisor config {key} must be a UUID")


def _config_path(
    value: object,
    *,
    base_dir: Path,
    parser: argparse.ArgumentParser,
) -> Path | None:
    text = _optional_string(value)
    if text is None:
        return None
    path = Path(text).expanduser()
    if not path.is_absolute():
        path = base_dir / path
    return path.resolve()


def _service_manager(value: object) -> DeploymentServiceManager:
    text = _optional_string(value)
    if text is None:
        return DeploymentServiceManager.UNKNOWN
    try:
        return DeploymentServiceManager(text)
    except ValueError:
        return DeploymentServiceManager.UNKNOWN


async def async_main(argv: list[str] | None = None) -> int:
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    config = parse_args(argv)
    if config.healthcheck:
        return 0
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


def _credential_store_token_provider(
    credential_store: FileCredentialStore | None,
) -> BearerTokenProvider | None:
    if credential_store is None:
        return None

    def load_credential() -> str:
        return credential_store.load() or ""

    return load_credential


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
    if not isinstance(value, (str, bytes, bytearray, int, float)):
        return fallback
    try:
        number = int(value)
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
