# 📊 FastAPI OpenTelemetry Demo with mTLS

This project demonstrates secure telemetry collection using **OpenTelemetry** in a Python FastAPI app, exporting **metrics and traces** to an OpenTelemetry Collector over **mutual TLS (mTLS)**.

- It also shows how to enrich metrics with tags using the Collector’s transform processor.

---

## Table of Contents

- [Project Structure (Key Files)](#️-project-structure-key-files)
- [Prerequisites](#1-prerequisites)
- [Clone & Setup](#2-clone--setup)
- [Directory & File Structure](#️-project-structure-key-files)
- [Docker Compose Setup](#docker-compose-setup)
- [Collector mTLS Configuration](#5--collector-config-used-in-this-demo)
- [Run the OTel Collector (with mTLS)](#6-run-the-otel-collector-with-mtls)
- [Python OTel SDK Example](#python-otel-sdk-example)
- [Environment Variables](#3-environment-variables)
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

### 4. Docker Compose Setup

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

### 5. Collector Config (used in this demo)

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

---

### 🐍 Python OTel SDK Example

Here's how to configure a Python service to send telemetry securely to the collector using mTLS:

**1. Set required environment variables** (in your `.env`):

```env
OTEL_EXPORTER_OTLP_METRICS_ENDPOINT=https://otel-collector:4318/v1/metrics
OTEL_EXPORTER_OTLP_TRACES_ENDPOINT=https://otel-collector:4318/v1/traces
OTEL_EXPORTER_OTLP_CERTIFICATE=certs/ca.crt
OTEL_EXPORTER_OTLP_CLIENT_CERTIFICATE=certs/client.crt
OTEL_EXPORTER_OTLP_CLIENT_KEY=certs/client.key
```

> **Note:**  
> When running both your Python service and the OTel Collector in the same `docker-compose` network, you can use the collector's service name as the hostname (e.g., `otel-collector:4318` as above).

> If your Python service runs outside Docker, use `localhost:4318` instead, since `otel-collector` will not resolve as a DNS name on your local machine.

- .env for running locally(This actual example):

```env

OTEL_EXPORTER_OTLP_METRICS_ENDPOINT=https://localhost:4318/v1/metrics
OTEL_EXPORTER_OTLP_TRACES_ENDPOINT=https://localhost:4318/v1/traces
OTEL_EXPORTER_OTLP_ENDPOINT=https://localhost:4318


OTEL_EXPORTER_OTLP_CERTIFICATE=certs/ca.crt
OTEL_EXPORTER_OTLP_CLIENT_CERTIFICATE=certs/client.crt
OTEL_EXPORTER_OTLP_CLIENT_KEY=certs/client.key
OTEL_EXPORTER_OTLP_INSECURE=false

```

\*\*2. Python setup code:

```python
import os
from dotenv import load_dotenv
from opentelemetry import trace, metrics
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
from opentelemetry.exporter.otlp.proto.http.metric_exporter import OTLPMetricExporter
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter

load_dotenv()  # Load env vars

resource = Resource.create({"service.name": "py-app-for-otel-collectors-example"})
cert = os.environ["OTEL_EXPORTER_OTLP_CERTIFICATE"]
client_cert = os.environ["OTEL_EXPORTER_OTLP_CLIENT_CERTIFICATE"]
client_key = os.environ["OTEL_EXPORTER_OTLP_CLIENT_KEY"]

metrics.set_meter_provider(MeterProvider(
    resource=resource,
    metric_readers=[
        PeriodicExportingMetricReader(OTLPMetricExporter(
            endpoint=os.environ["OTEL_EXPORTER_OTLP_METRICS_ENDPOINT"],
            certificate_file=cert,
            client_certificate_file=client_cert,
            client_key_file=client_key,
        ))
    ]
))

trace.set_tracer_provider(TracerProvider(
    resource=resource,
    active_span_processor=BatchSpanProcessor(OTLPSpanExporter(
        endpoint=os.environ["OTEL_EXPORTER_OTLP_TRACES_ENDPOINT"],
        certificate_file=cert,
        client_certificate_file=client_cert,
        client_key_file=client_key,
    ))
))

meter = metrics.get_meter("example-meter")
tracer = trace.get_tracer("example-tracer")

```

---

### 6. Run the OTel Collector (with mTLS)

```bash

docker compose up --build -d
```

#### 6.1. Check the logs:

```bash

docker logs otel-collector
```

### 7. Run the FastAPI App

```bash
uvicorn admin_server.app:app --reload
```

- If you see errors about certificates or connection refused, double-check your cert paths, SAN config, and collector status.

### 8. Test collector manually **Push Test Metric:**

```bash
curl -k https://localhost:4318/v1/metrics \
--cert certs/client.crt --key certs/client.key \
--cacert certs/ca.crt \
-H "Content-Type: application/json" \
--data-binary @docs/otel-collector/test-metric.json
```

### 9. **Inspect Output:**

- 1. file: `cat logs/tagged_metrics.json | jq .`
- Confirm both static `org_name` and dynamic `client_id` are present.

### 9.2. Expected Output with Static and Dynamic Tagging

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

### . Use jq to pretty json

`jq . collector/logs/tagged_metrics.json > collector/logs/tagged_metrics_pretty.json`

> 2. checkout metric output in `collector/logs/tagged_metrics_pretty.json`

> 3. All spans are printed in the collector logs (since debug exporter is used).
>    Look for your custom tags or metrics to confirm the full pipeline.

### . Common Pitfalls

SSLError: Hostname mismatch: Your server cert must have localhost or the actual OTLP endpoint hostname in its SAN field.

Permission denied: Double-check cert file permissions in Docker.

Collector not running: Ensure container is up and listening on 4318.

### 8. Best Practices & Recommendations

- Rotate certificates regularly.

- Use strong keys and CAs. Prefer at least RSA 2048 or ECC certificates.

- Store keys securely: Restrict read permissions.

- Separate test and production certificates/authorities.

- Document certificate generation and renewal.

- Add environment/tenant/application attributes to telemetry early in the pipeline (via transform processor or SDK).

- Monitor collector logs for certificate errors, especially after renewal.

## 9. Critical Configuration Points to Watch

| Section                          | Key Concern                                      | Example/Reminder                                       |
| -------------------------------- | ------------------------------------------------ | ------------------------------------------------------ |
| `receivers.otlp.protocols.*.tls` | Certificates must match expected hostname / IP   | Mismatches cause connection errors                     |
| `client_auth`                    | Controls whether clients must present certs      | Set to `require_and_verify_client_cert` for mTLS       |
| `exporters.*.tls`                | Must be configured if remote endpoint uses HTTPS | Omitting it causes "connection refused" or "TLS error" |
| Cert File Paths                  | Must be **mounted correctly** inside Docker/K8s  | Use `/etc/otel/certs/...` with volumeMounts            |
| Env Variables                    | Avoid injecting secrets via `env:` in YAML       | Prefer mounted files or Vault integration              |

### 9. References

OpenTelemetry Python Docs

OpenTelemetry Collector Docs

SSL/TLS SAN Info

Debugging Python SSL

### 10. Attributions

This demo was inspired by real-world need for secure observability pipelines.
Feel free to use as a starting point for production-grade OTel setups!

---

### **Hardening & Cleanup:**

- Run collector under a non-root UID/GID.
- Drop unnecessary Linux capabilities.
- Set `logging.level` to `info` or `error`.

---

## 📌 6. Next Steps

- Add remote `otlp` exporter for production telemetry.
- Integrate Helm/Kubernetes manifests with `Secret` volumes for TLS.
- Automate cert rotation with a vault or certificate manager.
