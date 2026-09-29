"""OpenTelemetry + Sentry setup for the Veridata backend.

Exports traces to Langfuse over OTLP/HTTP with Basic auth. Reads config from the
environment (loaded from .env by main). If Langfuse keys are missing the app
still boots; it just doesn't export.
"""

from __future__ import annotations

import base64
import logging
import os

import sentry_sdk
from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor

log = logging.getLogger(__name__)

SERVICE_NAME = "veridata-backend"


def _langfuse_endpoint() -> str | None:
    """Full OTLP traces URL, from LANGFUSE_OTEL_ENDPOINT or derived from base URL."""
    explicit = os.getenv("LANGFUSE_OTEL_ENDPOINT")
    if explicit:
        return explicit
    base = os.getenv("LANGFUSE_BASE_URL")
    if base:
        return f"{base.rstrip('/')}/api/public/otel/v1/traces"
    return None


def init_telemetry(app) -> None:
    provider = TracerProvider(resource=Resource.create({"service.name": SERVICE_NAME}))

    endpoint = _langfuse_endpoint()
    public, secret = os.getenv("LANGFUSE_PUBLIC_KEY"), os.getenv("LANGFUSE_SECRET_KEY")
    if endpoint and public and secret:
        auth = base64.b64encode(f"{public}:{secret}".encode()).decode()
        exporter = OTLPSpanExporter(endpoint=endpoint, headers={"Authorization": f"Basic {auth}"})
        provider.add_span_processor(BatchSpanProcessor(exporter))
        log.info("OTLP trace export enabled -> %s", endpoint)
    else:
        log.warning("Langfuse config incomplete; traces will not be exported.")

    trace.set_tracer_provider(provider)

    dsn = os.getenv("SENTRY_DSN")
    if dsn:
        sentry_sdk.init(dsn=dsn, traces_sample_rate=1.0)
        log.info("Sentry error tracking enabled.")

    FastAPIInstrumentor.instrument_app(app)
