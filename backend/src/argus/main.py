from __future__ import annotations

import time
from collections.abc import AsyncIterator, Callable
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI, Request, Response
from prometheus_client import (
    CONTENT_TYPE_LATEST,
    Counter,
    Gauge,
    Histogram,
    generate_latest,
)

from argus.api.v1 import router as api_router
from argus.core.config import Settings
from argus.core.db import DatabaseManager
from argus.core.events import NatsJetStreamClient
from argus.core.logging import (
    bind_request_context,
    clear_request_context,
    configure_logging,
)
from argus.core.security import EdgeKeyMiddleware, SecurityService
from argus.core.tracing import TracingManager
from argus.llm.parser import ClassFilterParser
from argus.services.app import DatabaseAuditLogger, build_app_services
from argus.services.query import QueryService, SQLCameraClassInventory

REQUEST_COUNT = Counter(
    "argus_http_requests_total",
    "Total number of HTTP requests handled by the backend.",
    ["method", "path", "status_code"],
)
REQUEST_DURATION = Histogram(
    "argus_http_request_duration_seconds",
    "Latency of HTTP requests handled by the backend.",
    ["method", "path"],
)
APP_INFO = Gauge(
    "argus_app_info",
    "Argus application metadata.",
    ["app_name", "environment"],
)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    settings_object: Settings = app.state.settings

    if settings_object.enable_startup_services:
        configure_logging(settings_object)
        APP_INFO.labels(
            app_name=settings_object.app_name,
            environment=settings_object.environment,
        ).set(1)
        if settings_object.enable_nats:
            await app.state.events.connect()
        app.state.tracing.configure(app, engine=app.state.db.engine)

    try:
        yield
    finally:
        if settings_object.enable_startup_services and settings_object.enable_nats:
            await app.state.events.close()
        await app.state.security.close()
        await app.state.db.dispose()


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or Settings()
    app = FastAPI(title=settings.app_name, lifespan=lifespan)
    app.state.settings = settings
    app.state.db = DatabaseManager(settings)
    app.state.events = NatsJetStreamClient(settings)
    app.state.security = SecurityService.from_settings(settings)
    app.state.tracing = TracingManager(settings)
    audit_logger = DatabaseAuditLogger(app.state.db.session_factory)
    query_service = QueryService(
        inventory=SQLCameraClassInventory(app.state.db.session_factory),
        parser=ClassFilterParser(settings),
        events=app.state.events,
        audit_logger=audit_logger,
    )
    app.state.services = build_app_services(
        settings=settings,
        db=app.state.db,
        events=app.state.events,
        query_service=query_service,
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
            REQUEST_COUNT.labels(
                method=request.method,
                path=request.url.path,
                status_code=str(status_code),
            ).inc()
            REQUEST_DURATION.labels(
                method=request.method,
                path=request.url.path,
            ).observe(duration)
            clear_request_context()

    app.include_router(api_router)
    return app


app = create_app()
