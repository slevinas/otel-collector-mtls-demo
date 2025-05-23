# 📊 FastAPI OpenTelemetry Demo with mTLS

This project demonstrates secure telemetry collection using **OpenTelemetry** in a Python FastAPI app, exporting **metrics and traces** to an OpenTelemetry Collector over **mutual TLS (mTLS)**.

- It also shows how to enrich metrics with tags using the Collector’s transform processor.

---

## Table of Contents

- [Overview](#overview)
- [Project Structure (Key Files)](#️-project-structure-key-files)
- [Prerequisites](#1-prerequisites)
- [Clone & Setup](#2-clone--setup)
- [Environment Variables](#environment-variables)
- [Directory & File Structure](#️-project-structure-key-files)
- [Collector mTLS Configuration](#collector-mtls-configuration)
- [Docker Compose Setup](#docker-compose-setup)
- [Python OTel SDK Example](#python-otel-sdk-example)
- [Run the OTel Collector (with mTLS)](#4-run-the-otel-collector-with-mtls)
- [Enriching Metrics with the Transform Processor](#enriching-metrics-with-the-transform-processor)

- [Troubleshooting](#troubleshooting)
- [References](#references)
- [Running the Demo](#run-dem)

---

### 🗂️ Project Structure (Key Files)

```bash

.
├── admin_server/
│ ├── app.py # FastAPI app with OpenTelemetry integration
│ └── otel_setup.py # EXPORTER(client) OpenTelemetry configuration (mTLS)
├── certs/
│ ├── ca.crt
│ ├── server.crt
│ ├── server.key
│ ├── client.crt
│ └── client.key
├── collector/
| |__logs/
| |   |--tagged_metrics.json
| |   |--tagged_metrics_pretty.json
│ └── mtls-collector-config.yaml  # Collector config (mTLS enabled)
├── .env
├── docker-compose.yaml
└── README.md

```

### 1. Prerequisites

- Python 3.8+

- Docker

- OpenSSL (for certs)

### 2. Clone & Setup

```bash

git clone <your_repo_url>
cd xplg-api-benchmaker-runner
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
```

### 3. Environment Variables

- .env example (adjust paths as needed):

```env

OTEL_EXPORTER_OTLP_METRICS_ENDPOINT=https://localhost:4318/v1/metrics
OTEL_EXPORTER_OTLP_TRACES_ENDPOINT=https://localhost:4318/v1/traces


OTEL_EXPORTER_OTLP_ENDPOINT=https://localhost:4318


OTEL_EXPORTER_OTLP_CERTIFICATE=certs/ca.crt
OTEL_EXPORTER_OTLP_CLIENT_CERTIFICATE=certs/client.crt
OTEL_EXPORTER_OTLP_CLIENT_KEY=certs/client.key
OTEL_EXPORTER_OTLP_INSECURE=false

```

### Docker Compose Setup

```yaml
version: "3.9"
services:
  otel-collector:
    image: otel/opentelemetry-collector-contrib:latest
    container_name: otel-collector
    command: ["--config=/etc/otel/config.yaml"]
    ports:
      - "4317:4317" # gRPC
      - "4318:4318" # HTTP
    volumes:
      - ./collector/otel-collector-tag-example.yaml:/etc/otel/config.yaml:ro
      # - ./collector/mtls-collector-config.yaml:/etc/otel/config.yaml:ro
      - ./collector/logs:/otel-logs:rw
      - ./certs:/etc/otel/certs:ro
    restart: unless-stopped
```

### 4. Run the OTel Collector (with mTLS)

```bash

docker compose up --build -d
```

#### Check the logs:

```bash

docker logs otel-collector
```

### 5. Run the FastAPI App

```bash
uvicorn admin_server.app:app --reload
```

- If you see errors about certificates or connection refused, double-check your cert paths, SAN config, and collector status.

### 6. OpenTelemetry Collector Config (used in this demo)

```yaml
receivers:
  otlp:
    protocols:
      grpc:
        endpoint: 0.0.0.0:4317
        tls:
          cert_file: /etc/otel/certs/server.crt
          key_file: /etc/otel/certs/server.key
          client_ca_file: /etc/otel/certs/ca.crt # ← this enables mTLS(tells the Collector, “require a client cert signed by this CA” (i.e. mTLS).)
      http:
        endpoint: 0.0.0.0:4318
        tls:
          cert_file: /etc/otel/certs/server.crt
          key_file: /etc/otel/certs/server.key
          client_ca_file: /etc/otel/certs/ca.crt # ← tells the Collector, “require a client cert signed by this CA” (i.e. mTLS).

processors:
  memory_limiter:
    check_interval: 5s
    limit_mib: 200
    spike_limit_mib: 50
  batch:
    timeout: 5s
    send_batch_size: 1024
  attributes/add_client_tag:
    actions:
      - key: org_name
        value: XPLG-benchmarker-dev-tag-test
        action: insert
  transform/tag_metrics:
    metric_statements:
      - context: datapoint
        statements:
          - set(datapoint.attributes["client_id"], resource.attributes["service.name"])

exporters:
  # otlp/http:
  #   endpoint: https://otel-backend.example.com:4318
  #   tls:
  #     ca_file: /etc/otel/certs/ca.crt # your backend’s CA
  debug:
    verbosity: detailed
  file/tagged_metrics:
    path: /otel-logs/tagged_metrics.json

service:
  pipelines:
    metrics:
      receivers: [otlp]
      processors:
        [
          memory_limiter,
          batch,
          attributes/add_client_tag,
          transform/tag_metrics,
        ]
      exporters: [file/tagged_metrics]
    traces:
      receivers: [otlp]
      processors:
        [
          memory_limiter,
          batch,
          attributes/add_client_tag,
          transform/tag_metrics,
        ]
      exporters: [debug]
```

### 7. Output with Static and Dynamic Tagging

```json
{
  "resource": {
    "attributes": {
      "service.name": "admin-api",
      "org_name": "XPLG-benchmarker-dev-tag-test"
    }
  },
  "metrics": [
    {
      "name": "operation_success_count",
      "data": {
        "data_points": [
          {
            "attributes": {
              "endpoint": "run_vector_math",
              "client_id": "admin-api"
            },
            "value": 10
          }
        ]
      }
    }
  ]
}
```

### 7. See Telemetry

All spans and metrics are printed in the collector logs (since debug exporter is used).
Look for your custom tags or metrics to confirm the full pipeline.

### 8. Common Pitfalls

SSLError: Hostname mismatch: Your server cert must have localhost or the actual OTLP endpoint hostname in its SAN field.

Permission denied: Double-check cert file permissions in Docker.

Collector not running: Ensure container is up and listening on 4318.

### 9. References

OpenTelemetry Python Docs

OpenTelemetry Collector Docs

SSL/TLS SAN Info

Debugging Python SSL

### 10. Attributions

This demo was inspired by real-world need for secure observability pipelines.
Feel free to use as a starting point for production-grade OTel setups!

---

**Tips:**

- Keep cert/private key files out of public repos.
- Expand sections as your demo grows (add transform processor details if needed).
