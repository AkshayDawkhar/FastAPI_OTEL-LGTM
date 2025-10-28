import os
import time
import logging
from random import randint

from fastapi import FastAPI, Request
from starlette.responses import Response

from opentelemetry import trace, metrics
from opentelemetry.propagate import extract
from opentelemetry.sdk.resources import SERVICE_NAME, Resource

from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter

from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
from opentelemetry.exporter.otlp.proto.http.metric_exporter import OTLPMetricExporter

from opentelemetry.trace import get_current_span, SpanContext
from opentelemetry.instrumentation.requests import RequestsInstrumentor
from opentelemetry.instrumentation.logging import LoggingInstrumentor

# ---- Logging (OTLP Exporter) ----
from opentelemetry.sdk._logs import LoggerProvider, LoggingHandler
from opentelemetry.sdk._logs.export import BatchLogRecordProcessor
from opentelemetry.exporter.otlp.proto.http._log_exporter import OTLPLogExporter


# =========================================
# OpenTelemetry Setup
# =========================================

resource = Resource(attributes={
    SERVICE_NAME: "service_b"
})

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
request_duration = meter.create_histogram(
    "http.server.request.duration",
    "Request duration in seconds",
    "s"
)

# --- Logs ---
logger_provider = LoggerProvider(resource=resource)
log_exporter = OTLPLogExporter(endpoint="http://otel-collector:4318/v1/logs")
logger_provider.add_log_record_processor(BatchLogRecordProcessor(log_exporter))
handler = LoggingHandler(level=logging.INFO, logger_provider=logger_provider)
logging.getLogger().addHandler(handler)
logging.getLogger().setLevel(logging.INFO)

# --- Enrich logs with trace/span IDs ---
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

logger = logging.getLogger("service_b_logger")

# =========================================
# FastAPI App
# =========================================
app = FastAPI(title="Service B")
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

        request_duration.record(
            duration,
            {
                "http.route": request.url.path,
                "http.status_code": response.status_code,
                "http.method": request.method,
                "service.instance.id": service_instance_id
            }
        )

        span.set_attribute("http.status_code", response.status_code)
        span.set_attribute("http.duration", duration)
        logger.info(f"{request.method} {request.url.path} -> {response.status_code} ({duration:.3f}s)")

        return response


@app.get("/work")
def work():
    with tracer.start_as_current_span("work-span") as span:
        work_time = randint(50, 200) / 1000.0

        if work_time > 0.15:
            span.set_status(trace.status.Status(trace.status.StatusCode.ERROR, "Work took too long"))
            logger.warning(f"Service B work slow: {work_time:.3f}s")
            return Response(status_code=500, content="Work took too long")

        time.sleep(work_time)
        logger.info(f"Service B completed work in {work_time:.3f}s")
        return {"status": "work completed", "duration": work_time}
