import logging

from opentelemetry import trace, metrics
from opentelemetry.exporter.otlp.proto.http._log_exporter import OTLPLogExporter
from opentelemetry.exporter.otlp.proto.http.metric_exporter import OTLPMetricExporter
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.logging import LoggingInstrumentor
from opentelemetry.instrumentation.requests import RequestsInstrumentor
# --- Logging (OTLP Exporter) ---
from opentelemetry.sdk._logs import LoggerProvider, LoggingHandler
from opentelemetry.sdk._logs.export import BatchLogRecordProcessor
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
from opentelemetry.sdk.resources import SERVICE_NAME, Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.trace import get_current_span, SpanContext


def init_telemetry(service_name: str, otel_endpoint: str):
    """Initialize OpenTelemetry tracing, metrics, and logging."""

    # ---- Resource ----
    resource = Resource(attributes={SERVICE_NAME: service_name})

    # =========================================
    # 1. Traces
    # =========================================
    tracer_provider = TracerProvider(resource=resource)
    trace_exporter = OTLPSpanExporter(endpoint=f"{otel_endpoint}/v1/traces")
    tracer_provider.add_span_processor(BatchSpanProcessor(trace_exporter))
    trace.set_tracer_provider(tracer_provider)
    tracer = trace.get_tracer(__name__)

    # =========================================
    # 2. Metrics
    # =========================================
    metric_exporter = OTLPMetricExporter(endpoint=f"{otel_endpoint}/v1/metrics")
    metric_reader = PeriodicExportingMetricReader(metric_exporter)
    meter_provider = MeterProvider(resource=resource, metric_readers=[metric_reader])
    metrics.set_meter_provider(meter_provider)
    meter = metrics.get_meter(__name__)

    request_duration = meter.create_histogram("http.server.request.duration", "Request duration in seconds", "s", )

    # =========================================
    # 3. Logs
    # =========================================
    logger_provider = LoggerProvider(resource=resource)
    log_exporter = OTLPLogExporter(endpoint=f"{otel_endpoint}/v1/logs")
    logger_provider.add_log_record_processor(BatchLogRecordProcessor(log_exporter))

    handler = LoggingHandler(level=logging.INFO, logger_provider=logger_provider)
    logging.getLogger().addHandler(handler)
    logging.getLogger().setLevel(logging.INFO)

    # ---- Trace correlation in logs ----
    _enable_trace_correlation()

    # ---- Instrumentations ----
    RequestsInstrumentor().instrument(tracer_provider=tracer_provider)
    LoggingInstrumentor().instrument(set_logging_format=True)

    logger = logging.getLogger(f"{service_name}_logger")

    return {"tracer": tracer, "meter": meter, "logger": logger, "request_duration": request_duration, }


def _enable_trace_correlation():
    """Attach trace_id and span_id to log records for correlation."""

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
    logging.basicConfig(format="%(asctime)s [%(levelname)s] trace_id=%(trace_id)s span_id=%(span_id)s %(message)s",
        level=logging.INFO, )
