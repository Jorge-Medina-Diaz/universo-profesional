"""OpenTelemetry setup — OTLP exporter + resource attributes."""
from __future__ import annotations

import os


def init_otel(service_name: str = "cvs-saas-backend") -> None:
    """Configure the OTLP trace exporter when OTLP_ENDPOINT is set.

    The opentelemetry exporter packages are imported lazily here (not at module
    top) so importing this module never fails when those optional deps are
    absent and no endpoint is configured — the common dev/worker case.
    """
    endpoint = os.getenv("OTLP_ENDPOINT")
    if not endpoint:
        return

    from opentelemetry import trace
    from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
    from opentelemetry.sdk.resources import Resource
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import BatchSpanProcessor

    resource = Resource.create({"service.name": service_name, "service.version": "0.1.0"})
    provider = TracerProvider(resource=resource)
    exporter = OTLPSpanExporter(endpoint=endpoint, insecure=endpoint.startswith("http://"))
    provider.add_span_processor(BatchSpanProcessor(exporter))
    trace.set_tracer_provider(provider)
