import os
import time
import logging
from random import randint
import uvicorn

from fastapi import FastAPI, Request
from starlette.responses import Response
from opentelemetry.propagate import extract
from opentelemetry import trace

from telemetry import init_telemetry

# =========================================
# Initialization
# =========================================

telemetry = init_telemetry(service_name="service_b", otel_endpoint="http://otel-collector:4318")
tracer = telemetry["tracer"]
meter = telemetry["meter"]
logger = telemetry["logger"]
request_duration = telemetry["request_duration"]

app = FastAPI(title="Service B")
service_instance_id = os.getenv("HOSTNAME", "unknown")

# =========================================
# Middleware for telemetry
# =========================================

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

        # Record request latency metric
        request_duration.record(
            duration,
            {
                "http.route": request.url.path,
                "http.status_code": response.status_code,
                "http.method": request.method,
                "service.instance.id": service_instance_id,
            },
        )

        span.set_attribute("http.status_code", response.status_code)
        span.set_attribute("http.duration", duration)
        logger.info(f"{request.method} {request.url.path} -> {response.status_code} ({duration:.3f}s)")

        return response


# =========================================
# Routes
# =========================================

@app.get("/work")
def work():
    """Simulate some work, occasionally fail if too slow."""
    with tracer.start_as_current_span("work-span") as span:
        work_time = randint(50, 200) / 1000.0  # seconds

        # Mark span as error if work is slow
        if work_time > 0.15:
            span.set_status(trace.status.Status(trace.status.StatusCode.ERROR, "Work took too long"))
            logger.warning(f"Service B work slow: {work_time:.3f}s")
            return Response(status_code=500, content="Work took too long")

        time.sleep(work_time)
        logger.info(f"Service B completed work in {work_time:.3f}s")
        return {"status": "work completed", "duration": work_time}


if __name__ == "__main__":
    uvicorn.run("main:app", reload=True, host="0.0.0.0", port=8000)
