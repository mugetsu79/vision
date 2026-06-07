from __future__ import annotations

import logging
import time
from collections.abc import AsyncIterator, Callable
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest

from argus.api.v1 import router as api_router
from argus.core.config import Settings
from argus.core.db import DatabaseManager
from argus.core.events import NatsJetStreamClient
from argus.core.logging import (
    bind_request_context,
    clear_request_context,
    configure_logging,
)
from argus.core.metrics import APP_INFO, HTTP_REQUEST_DURATION_SECONDS, HTTP_REQUESTS_TOTAL
from argus.core.security import EdgeKeyMiddleware, SecurityService
from argus.core.tracing import TracingManager
from argus.link.reflector import ReflectorRuntime, start_reflector, stop_reflector
from argus.llm.parser import ClassFilterParser
from argus.services.app import DatabaseAuditLogger, build_app_services
from argus.services.operator_configuration import OperatorConfigurationService
from argus.services.query import QueryService, SQLCameraClassInventory, SQLQueryQuotaEnforcer

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    settings_object: Settings = app.state.settings
    app.state.link_reflector_runtime = await start_link_reflector_for_startup(settings_object)

    if settings_object.enable_startup_services:
        configure_logging(settings_object)
        APP_INFO.labels(
            app_name=settings_object.app_name,
            environment=settings_object.environment,
        ).set(1)
        if settings_object.enable_nats:
            await app.state.events.connect()
        app.state.tracing.configure(app, engine=app.state.db.engine)
        await reconcile_identity_provider_for_startup(app)

    try:
        yield
    finally:
        stop_reflector(app.state.link_reflector_runtime)
        app.state.link_reflector_runtime = None
        if settings_object.enable_startup_services and settings_object.enable_nats:
            await app.state.events.close()
        close_services = getattr(app.state.services, "close", None)
        if callable(close_services):
            await close_services()
        await app.state.security.close()
        await app.state.db.dispose()


async def reconcile_identity_provider_for_startup(app: FastAPI) -> None:
    try:
        await app.state.services.deployment.reconcile_identity_provider()
    except Exception:
        logger.warning("Failed to reconcile identity provider frontend client.", exc_info=True)


async def start_link_reflector_for_startup(settings: Settings) -> ReflectorRuntime | None:
    if not settings.link_reflector_enabled:
        return None
    if settings.link_reflector_secret is None:
        logger.warning("Link reflector enabled without ARGUS_LINK_REFLECTOR_SECRET.")
        return None
    return await start_reflector(
        bind_host=settings.link_reflector_bind_address,
        port=settings.link_reflector_port,
        secret=settings.link_reflector_secret.get_secret_value().encode("utf-8"),
        key_id=settings.link_reflector_key_id,
        rate_limit_pps=settings.link_reflector_rate_limit_pps,
    )


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or Settings()
    app = FastAPI(title=settings.app_name, lifespan=lifespan)
    app.state.settings = settings
    app.state.link_reflector_runtime = None
    app.state.db = DatabaseManager(settings)
    app.state.events = NatsJetStreamClient(settings)
    app.state.security = SecurityService.from_settings(settings)
    app.state.tracing = TracingManager(settings)
    audit_logger = DatabaseAuditLogger(app.state.db.session_factory)
    configuration_service = OperatorConfigurationService(
        app.state.db.session_factory,
        settings,
        audit_logger,
    )
    query_service = QueryService(
        inventory=SQLCameraClassInventory(app.state.db.session_factory),
        parser=ClassFilterParser(
            settings,
            llm_provider_resolver=configuration_service.llm_provider_runtime,
        ),
        events=app.state.events,
        audit_logger=audit_logger,
        quota_enforcer=SQLQueryQuotaEnforcer(app.state.db.session_factory),
    )
    app.state.services = build_app_services(
        settings=settings,
        db=app.state.db,
        events=app.state.events,
        query_service=query_service,
        configuration_service=configuration_service,
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=list(settings.cors_allowed_origins),
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.add_middleware(EdgeKeyMiddleware)

    @app.get("/healthz")
    async def healthcheck() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/readyz")
    async def readiness() -> dict[str, bool]:
        database_ready = await app.state.db.ping()
        nats_ready = True
        if settings.enable_nats:
            nats_ready = app.state.events.is_connected
        return {"ready": database_ready and nats_ready}

    @app.get("/metrics")
    async def metrics() -> Response:
        return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)

    @app.middleware("http")
    async def request_metrics_middleware(
        request: Request,
        call_next: Callable[[Request], Any],
    ) -> Response:
        bind_request_context()
        started_at = time.perf_counter()
        response: Response | None = None
        try:
            response = await call_next(request)
            return response
        finally:
            duration = time.perf_counter() - started_at
            status_code = response.status_code if response is not None else 500
            HTTP_REQUESTS_TOTAL.labels(
                method=request.method,
                path=request.url.path,
                status_code=str(status_code),
            ).inc()
            HTTP_REQUEST_DURATION_SECONDS.labels(
                method=request.method,
                path=request.url.path,
            ).observe(duration)
            clear_request_context()

    app.include_router(api_router)
    return app


app = create_app()
