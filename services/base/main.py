import os
import time
import logging
from random import randint

import requests
from fastapi import FastAPI, Request
from opentelemetry.propagate import extract
from opentelemetry.trace import get_current_span, SpanContext

from telemetry import init_telemetry

# =========================================
# Initialization
# =========================================

# Initialize telemetry (traces, metrics, logs)
telemetry = init_telemetry(service_name="base", otel_endpoint="http://otel-collector:4318")
tracer = telemetry["tracer"]
meter = telemetry["meter"]
logger = telemetry["logger"]
request_duration = telemetry["request_duration"]

# =========================================
# FastAPI Application
# =========================================

app = FastAPI(title="PL Base")
service_instance_id = os.getenv("HOSTNAME", "unknown")


# =========================================
# Middleware for Telemetry
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

        # Record request metrics
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


# =========================================
# Routes
# =========================================

@app.get("/")
def root():
    with tracer.start_as_current_span("root_handler"):
        logger.info("Root endpoint hit")
        return {"service": "base", "status": "ok", "host": service_instance_id}


@app.get("/compute")
def compute():
    with tracer.start_as_current_span("compute_operation"):
        delay = randint(1, 3)
        time.sleep(delay)
        value = randint(10, 100)
        logger.info(f"Computed value={value} after {delay}s delay")
        return {"value": value, "delay": delay}


@app.get("/external")
def external_call():
    with tracer.start_as_current_span("external_call") as span:
        resp = requests.get("http://service_b:8000/work")
        span.set_attribute("external.status_code", resp.status_code)
        logger.info(f"Called Service B, status_code={resp.status_code}")
        return {"external_status": resp.status_code}
