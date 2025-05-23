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
- [Directory & File Structure](#directory--file-structure)
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

### 6. OpenTelemetry Collector Config (snippet)

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
