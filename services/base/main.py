import os
import time
import logging
from random import randint

import requests
from fastapi import FastAPI, Request
from opentelemetry import trace, metrics
from opentelemetry.exporter.otlp.proto.http.metric_exporter import OTLPMetricExporter
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.logging import LoggingInstrumentor
from opentelemetry.instrumentation.requests import RequestsInstrumentor
from opentelemetry.propagate import extract
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
from opentelemetry.sdk.resources import SERVICE_NAME, Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.trace import get_current_span, SpanContext

# ---- Logging (OTLP Exporter) ----
from opentelemetry.sdk._logs import LoggerProvider, LoggingHandler
from opentelemetry.sdk._logs.export import BatchLogRecordProcessor
from opentelemetry.exporter.otlp.proto.http._log_exporter import OTLPLogExporter

# =========================================
# OpenTelemetry Setup
# =========================================

resource = Resource(attributes={SERVICE_NAME: "base"})

# --- Traces ---
trace_provider = TracerProvider(resource=resource)
trace_exporter = OTLPSpanExporter(endpoint="http://otel-collector:4318/v1/traces")
trace_provider.add_span_processor(BatchSpanProcessor(trace_exporter))
trace.set_tracer_provider(trace_provider)
tracer = trace.get_tracer(__name__)

# --- Metrics ---
metric_exporter = OTLPMetricExporter(endpoint="http://otel-collector:4318/v1/metrics")
metric_reader = PeriodicExportingMetricReader(metric_exporter)
meter_provider = MeterProvider(resource=resource, metric_readers=[metric_reader])
metrics.set_meter_provider(meter_provider)
meter = metrics.get_meter(__name__)
request_duration = meter.create_histogram("http.server.request.duration", "Request duration in seconds", "s")

# --- Logs ---
logger_provider = LoggerProvider(resource=resource)
log_exporter = OTLPLogExporter(endpoint="http://otel-collector:4318/v1/logs")
logger_provider.add_log_record_processor(BatchLogRecordProcessor(log_exporter))
handler = LoggingHandler(level=logging.INFO, logger_provider=logger_provider)
logging.getLogger().addHandler(handler)
logging.getLogger().setLevel(logging.INFO)

# --- Trace/Span correlation in logs ---
old_factory = logging.getLogRecordFactory()
def record_factory(*args, **kwargs):
    record = old_factory(*args, **kwargs)
    span = get_current_span()
    if span and isinstance(span.get_span_context(), SpanContext):
        ctx = span.get_span_context()
        record.trace_id = format(ctx.trace_id, "032x")
        record.span_id = format(ctx.span_id, "016x")
    else:
        record.trace_id = None
        record.span_id = None
    return record

logging.setLogRecordFactory(record_factory)

logging.basicConfig(
    format="%(asctime)s [%(levelname)s] trace_id=%(trace_id)s span_id=%(span_id)s %(message)s",
    level=logging.INFO,
)

logger = logging.getLogger("base_logger")

# =========================================
# FastAPI App
# =========================================

app = FastAPI(title="PL Base")

# Enable context propagation and logging
RequestsInstrumentor().instrument(tracer_provider=trace_provider)
LoggingInstrumentor().instrument(set_logging_format=True)

service_instance_id = os.getenv("HOSTNAME", "unknown")

@app.middleware("http")
async def telemetry_middleware(request: Request, call_next):
    ctx = extract(request.headers)
    start_time = time.time()

    with tracer.start_as_current_span(f"{request.method} {request.url.path}", context=ctx) as span:
        span.set_attribute("http.method", request.method)
        span.set_attribute("http.route", request.url.path)
        span.set_attribute("service.instance.id", service_instance_id)

        response = await call_next(request)
        duration = time.time() - start_time

        request_duration.record(duration, {
            "http.route": request.url.path,
            "http.status_code": response.status_code,
            "http.method": request.method,
            "http.service.instance.id": service_instance_id
        })

        span.set_attribute("http.status_code", response.status_code)
        span.set_attribute("http.duration", duration)
        logger.info(f"{request.method} {request.url.path} -> {response.status_code} ({duration:.3f}s)")

        return response


@app.get("/")
def root():
    with tracer.start_as_current_span("home_handler"):
        logger.info("Service A Root endpoint hit")
        return {"service": "A", "status": "ok", "host": service_instance_id}


@app.get("/compute")
def compute():
    with tracer.start_as_current_span("compute_operation"):
        t = randint(1, 3)
        time.sleep(t)
        value = randint(10, 100)
        logger.info(f"Service A computed value={value} after {t}s delay")
        return {"value": value, "delay": t}


@app.get("/external")
def external_call():
    with tracer.start_as_current_span("external_call") as span:
        resp = requests.get("http://service_b:8000/work")
        span.set_attribute("external.status_code", resp.status_code)
        logger.info(f"Service A called Service B, status_code={resp.status_code}")
        return {"external_status": resp.status_code}
