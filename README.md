Here’s a clean, developer-friendly **README** you can use as a base template for future observability-enabled FastAPI microservices. It’s structured to explain purpose, setup, and how each component fits together — ideal for a reproducible stack.

---

# 🧩 FastAPI Observability Project Template

A full-stack template to bootstrap new **FastAPI microservices** with **OpenTelemetry**, **Grafana**, **Prometheus**, **Loki**, **Tempo**, and **PostgreSQL** — all containerized with **Docker Compose**.
This template provides a complete setup for **metrics, logs, and traces**, ensuring production-grade observability from day one.

---

## 🚀 Overview

This project demonstrates how to run a **FastAPI service** instrumented with **OpenTelemetry** for distributed tracing, metrics, and structured logging — all collected through **OpenTelemetry Collector** and visualized via **Grafana**.

### Stack Summary

| Component                   | Role                                                                       |
| --------------------------- | -------------------------------------------------------------------------- |
| **FastAPI**                 | Application layer (instrumented with OpenTelemetry SDKs).                  |
| **PostgreSQL**              | Application database for persistence.                                      |
| **OpenTelemetry Collector** | Centralized agent for receiving, processing, and exporting telemetry data. |
| **Prometheus**              | Collects metrics exposed by services and the collector.                    |
| **Loki**                    | Centralized log aggregation system.                                        |
| **Tempo**                   | Distributed tracing backend.                                               |
| **Grafana**                 | Unified observability dashboard (metrics, logs, traces).                   |
| **Docker Compose**          | Simplifies orchestration of all services.                                  |

---

## 🧠 Architecture

```
FastAPI (traces, metrics, logs)
   │
   ├──> OpenTelemetry Collector
   │       ├──→ Prometheus  (metrics)
   │       ├──→ Tempo       (traces)
   │       └──→ Loki        (logs)
   │
   └──> Grafana (single pane of glass)
```

---

## ⚙️ Setup

### 1. Clone the Repository

```bash
git clone https://github.com/your-org/fastapi-otel-template.git
cd fastapi-otel-template
```

### 2. Start the Stack

```bash
docker-compose up --build
```

This launches:

* `fastapi-base` → Example service A
* `fastapi-service-b` → Example service B
* `otel-collector` → Central telemetry router
* `prometheus`, `loki`, `tempo`, `grafana`, and `postgres`

### 3. Access the Tools

| Tool              | URL                                            |
| ----------------- | ---------------------------------------------- |
| FastAPI Service A | [http://localhost:8000](http://localhost:8000) |
| FastAPI Service B | [http://localhost:8001](http://localhost:8001) |
| Grafana           | [http://localhost:3000](http://localhost:3000) |
| Prometheus        | [http://localhost:9090](http://localhost:9090) |
| Loki              | [http://localhost:3100](http://localhost:3100) |
| Tempo             | [http://localhost:3200](http://localhost:3200) |
| PostgreSQL        | `localhost:5432`                               |

---

## 🔍 Observability in Action

### 1. Traces

All request traces flow from FastAPI → OTEL Collector → Tempo.
Visualize traces in Grafana → **Explore → Tempo**.
Traces from `service_a` and `service_b` are linked using `trace_id`.

### 2. Metrics

Prometheus scrapes:

* `otel-collector` metrics (default port `9464`)
* Custom app metrics (e.g., `http.server.request.duration`)

Visualize them in Grafana → **Dashboards → Prometheus**.

### 3. Logs

Logs include `trace_id` and `span_id`, exported to Loki.
Example query in Grafana:

```
{otelServiceName="base"}
```

From a Tempo trace, click **“View logs”** to pivot directly into Loki.

---

## 📦 Directory Structure

```
.
├── docker-compose.yml
├── otel-collector-config.yaml
├── services/
│   ├── base/
│   │   ├── Dockerfile
│   │   └── main.py
│   └── service_b/
│       ├── Dockerfile
│       └── main.py
└── grafana/
    └── dashboards/
```

---

## 🧩 OpenTelemetry Highlights

* **Traces:** Automatically captured for incoming FastAPI requests and outgoing HTTP calls.
* **Metrics:** Custom histograms (e.g., `http.server.request.duration`) with route and status labels.
* **Logs:** Context-aware logs enriched with `trace_id` and `span_id` for correlation.

Example log:

```
2025-10-28 12:57:08 [INFO] trace_id=985ac7a900f21f839c29b3c184e1dd08 span_id=2f9968c648e8c2dc GET /work -> 200 (0.149s)
```

---

## 🧰 Extending the Template

To create a new service:

1. Copy the `services/base` directory.
2. Rename it (e.g., `service_c`).
3. Update:

   * `SERVICE_NAME` in `main.py`
   * Service port in `Dockerfile` and `docker-compose.yml`
4. Restart the stack:

   ```bash
   docker-compose up --build
   ```

Your new service will automatically emit telemetry through the collector.

---

## 🧪 Example Call Chain

```bash
curl http://localhost:8000/external
```

This triggers:

* A span in `service_a`
* An HTTP request to `service_b`
* Both services logging under the same `trace_id`
* Metrics recorded for duration and status
* Trace viewable in Grafana Tempo
* Logs linked via Loki

---

## 🧯 Troubleshooting

| Issue                       | Fix                                                                                  |
| --------------------------- | ------------------------------------------------------------------------------------ |
| Logs not showing in Loki    | Ensure `endpoint: http://loki:3100/loki/api/v1/push` in `otel-collector-config.yaml` |
| 404 from `/otlp`            | Use `/loki/api/v1/push` — Loki’s OTLP ingestion path is not always enabled           |
| Tempo not displaying traces | Confirm `otel-collector` exporter endpoint is `tempo:4317` and `insecure: true`      |

---

## 🪄 Useful Commands

View running containers:

```bash
docker ps
```

Inspect collector logs:

```bash
docker logs otel-collector-1 -f
```

Run a manual log push to Loki:

```bash
curl -X POST "http://localhost:3100/loki/api/v1/push" \
  -H "Content-Type: application/json" \
  -d '{"streams":[{"stream":{"job":"test"},"values":[["'"$(date +%s%N)"'","Hello from Loki!"]]}]}'
```

---

## 🧠 Key Learning

This template illustrates the **three pillars of observability** in practice:

* **Metrics:** Quantitative measurement of system health
* **Logs:** Contextualized, searchable event streams
* **Traces:** End-to-end view of request lifecycles

Combined, they give developers the power to understand *why* systems behave the way they do.

---

Would you like me to make this README “live-ready” — meaning include example dashboards, Grafana provisioning, and a sample query dashboard JSON to auto-load on startup? That would make it clone-and-run observability out of the box.
