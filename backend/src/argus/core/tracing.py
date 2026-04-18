from __future__ import annotations

from typing import Any

from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor
from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from sqlalchemy.ext.asyncio import AsyncEngine

from argus.core.config import Settings


class TracingManager:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self._configured = False

    def configure(self, app: Any, engine: AsyncEngine | None = None) -> None:
        if self._configured or not self.settings.enable_tracing:
            return

        resource = Resource.create({"service.name": self.settings.otel_service_name})
        tracer_provider = TracerProvider(resource=resource)
        tracer_provider.add_span_processor(
            BatchSpanProcessor(
                OTLPSpanExporter(endpoint=f"{self.settings.otlp_endpoint.rstrip('/')}/v1/traces")
            )
        )
        trace.set_tracer_provider(tracer_provider)

        FastAPIInstrumentor.instrument_app(app, tracer_provider=tracer_provider)
        HTTPXClientInstrumentor().instrument(tracer_provider=tracer_provider)
        if engine is not None:
            SQLAlchemyInstrumentor().instrument(
                engine=engine.sync_engine,
                tracer_provider=tracer_provider,
            )

        self._configured = True
