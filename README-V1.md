# FastAPI OpenTelemetry mTLS Example

This project demonstrates **exporting OpenTelemetry metrics and traces** from a Python FastAPI service to the OpenTelemetry Collector using **mutual TLS (mTLS)**.

- It also shows how to use a basic transform processor in the Collector to add tags to incoming metrics.

---

## Features

- Minimal FastAPI app emitting example metrics and traces.
- OpenTelemetry Python SDK configured for mTLS over OTLP/HTTP.
- OpenTelemetry Collector enforcing mTLS for both HTTP and gRPC.
- Example Collector transform processor adding a custom tag to all metrics.
- All configuration managed via environment variables and Docker Compose.

---

## Table of Contents

- [Overview](#overview)
- [Best Practices](#best-practices)
- [Why Use TLS](#why-use-tls)
- [Example Collector Configuration](#example-configuration)
- [Example Docker-Compose for Collector](#docker-compose)
- [Directory & File Structure](#directory--file-structure)
- [Environment Variables](#environment-variables)
- [Collector mTLS Configuration](#collector-mtls-configuration)
- [Docker Compose Setup](#docker-compose-setup)
- [Python OTel SDK Example](#python-otel-sdk-example)
- [Enriching Metrics with the Transform Processor](#enriching-metrics-with-the-transform-processor)

- [Troubleshooting](#troubleshooting)
- [References](#references)
- [Running the Demo](#run-dem)

---

## Overview

Securing your OpenTelemetry Collector with TLS/mTLS ensures encrypted telemetry and strong client authentication. You can further enrich your metrics with custom tags for better observability and data filtering.

---

### 🔐 Why Use TLS?

**TLS (Transport Layer Security) encrypts telemetry data in transit**, protecting it from eavesdropping, tampering, and impersonation. It's essential for production environments handling sensitive observability data.

### ✅ Best Practices

| Category          | Recommendation                                                          |
| ----------------- | ----------------------------------------------------------------------- |
| TLS Everywhere    | Use TLS for all receivers and exporters (gRPC, HTTP, etc.)              |
| Use mTLS          | Require client certificate verification for added trust (mutual TLS)    |
| Cert Rotation     | Use automation (e.g., cert-manager, Vault) to rotate expiring certs     |
| Secure File Paths | Use volume-mounted secrets for certificate storage                      |
| Harden Network    | Use firewalls, load balancers, or mesh proxies to isolate exposed ports |
| TLS Versions      | Use TLS ≥1.2; disable older versions                                    |

#### 🔧 Example Configuration

This YAML enables TLS for both OTLP receiver and exporter with optional mTLS:

```yaml
receivers:
  otlp:
    protocols:
      grpc:
        endpoint: 0.0.0.0:4317
        tls:
          cert_file: /etc/otel/certs/server.crt
          key_file: /etc/otel/certs/server.key
          ca_file: /etc/otel/certs/ca.crt # Enables mTLS
          client_auth: require_and_verify_client_cert
      http:
        endpoint: 0.0.0.0:4318
        tls:
          cert_file: /etc/otel/certs/server.crt
          key_file: /etc/otel/certs/server.key

exporters:
  otlp/http:
    endpoint: https://otel-backend.example.com:4318
    tls:
      ca_file: /etc/otel/certs/backend_ca.crt

service:
  pipelines:
    traces:
      receivers: [otlp]
      exporters: [otlp/http]
    metrics:
      receivers: [otlp]
      exporters: [otlp/http]
```

- #### client_auth: require_and_verify_client_cert: enforces that every client must present a cert the CA signed.
- #### The Collector uses the same server.crt/key for both gRPC and HTTP listeners.

---
### Docker Compose
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
      - ./collector/mtls-collector-config.yaml:/etc/otel/config.yaml:ro
      - ./certs:/etc/otel/certs:ro
    restart: unless-stopped


```
---
## Directory Structure

```
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
│ └── mtls-collector-config.yaml
├── .env
├── docker-compose.yaml
└── README.md
```

---

## 🛡️ Step 1: Generate CA, Server, and Client Certificates

### (A) Generate a Root CA Key/Certificate

```bash

mkdir -p certs
cd certs

# 1. Generate CA private key
openssl genrsa -out ca.key 4096

# 2. Generate self-signed CA certificate (change "MyRootCA" if you wish)
openssl req -x509 -new -nodes -key ca.key -sha256 -days 3650 \
  -out ca.crt -subj "/CN=MyRootCA"
```

### (B) Generate a Server Key/CSR/Certificate (for OTel Collector)

**IMPORTANT**: The CN and SANs must match the **_service name used in Docker Compose (otel-collector)_** and any hostnames/addresses the client will use to reach the collector.

> - For local development, include both otel-collector and localhost.

### B1. Create an OpenSSL config for SAN

```bash

cat > server-openssl.cnf <<EOF
[ req ]
default_bits       = 4096
prompt             = no
default_md         = sha256
distinguished_name = dn
req_extensions     = req_ext

[ dn ]
CN = otel-collector

[ req_ext ]
subjectAltName = @alt_names

[ alt_names ]
DNS.1 = otel-collector
DNS.2 = localhost
IP.1 = 127.0.0.1
EOF
```

### B2. Generate server key and CSR, and sign the certificate

```bash

openssl genrsa -out server.key 4096
openssl req -new -key server.key -out server.csr -config server-openssl.cnf

openssl x509 -req -in server.csr -CA ca.crt -CAkey ca.key -CAcreateserial \
  -out server.crt -days 365 -sha256 -extensions req_ext -extfile server-openssl.cnf
```

### (C) Generate a Client Key/Cert for the Python app (for mTLS)

Repeat similar steps for a client cert. This is the cert your Python exporter will use for mTLS.

#### C1. **Create a simple openssl config for the client**

```bash

cat > client-openssl.cnf <<EOF
[ req ]
default_bits       = 4096
prompt             = no
default_md         = sha256
distinguished_name = dn
req_extensions     = req_ext

[ dn ]
CN = admin_server-client

[ req_ext ]
subjectAltName = @alt_names

[ alt_names ]
DNS.1 = admin_server-client
EOF
```

#### C2. **Generate client key and CSR**

```bash
openssl genrsa -out client.key 4096
openssl req -new -key client.key -out client.csr -config client-openssl.cnf
```

#### C3. **Sign client CSR with CA**

```bash
openssl x509 -req -in client.csr -CA ca.crt -CAkey ca.key \
 -CAcreateserial -out client.crt -days 365 -sha256 \
 -extensions req_ext -extfile client-openssl.cnf

```

### 🔒 Tips and Gotchas

Always add all hostnames you’ll use for the collector (e.g., otel-collector, localhost, and 127.0.0.1) to the SAN field.

For Docker Compose, the service name is used for internal DNS; for your host machine, you probably use localhost.

Your client (client.crt) can have any CN; the collector just checks that it’s signed by the CA (if using mTLS).

Keep your private keys secure and .gitignore the _.key, _.csr, and \*.srl files.

You can use the same CA for both client and server certs for local testing.

---

### 1. How to run this Python demo, a quick one-liner is always appreciated:

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 2. Set Up Environment Variables

Create a .env file (see example below):

```ini

OTEL_EXPORTER_OTLP_METRICS_ENDPOINT=https://localhost:4318/v1/metrics
OTEL_EXPORTER_OTLP_TRACES_ENDPOINT=https://localhost:4318/v1/traces

OTEL_EXPORTER_OTLP_CERTIFICATE=certs/ca.crt
OTEL_EXPORTER_OTLP_CLIENT_CERTIFICATE=certs/client.crt
OTEL_EXPORTER_OTLP_CLIENT_KEY=certs/client.key
```

### 3. Run the OpenTelemetry Collector

```sh

docker-compose up --build
```

This starts the OTel Collector on ports 4317 (gRPC) and 4318 (HTTP), enforcing mTLS using your provided certs.

### 4. Run the FastAPI Example App

```sh

cd admin_server
python app.py
```

#### or from root use: uvicorn app:app --reload

```bash
 uvicorn admin_server.app:app --reload
```

### 5. See Telemetry in Collector Logs

The Collector will print all received metrics and traces (debug exporter). You should see your custom tag added by the transform processor.

#### **Example**: _**FastAPI App with OpenTelemetry mTLS**_

admin_server/app.py:

```python

import uvicorn
from fastapi import FastAPI
from otel_setup import setup_otel, meter, tracer

app = FastAPI()
setup_otel() # initializes OpenTelemetry

@app.get("/hello")
def hello():
with tracer.start_as_current_span("hello-span"):
meter.create_counter("hello_requests").add(1)
return {"message": "Hello, world!"}

if **name** == "**main**":
uvicorn.run(app, host="0.0.0.0", port=8000)
```

### Example: OpenTelemetry Setup with mTLS

admin_server/otel_setup.py:

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

def setup_otel():
load_dotenv()
resource = Resource.create({"service.name": "admin-server"})
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

### Example: Collector Config with mTLS and Transform Processor

> - collector/mtls-collector-config.yaml:

```yaml
receivers:
  otlp:
    protocols:
      grpc:
        endpoint: 0.0.0.0:4317
        tls:
          cert_file: /etc/otel/certs/server.crt
          key_file: /etc/otel/certs/server.key
          # client_ca_file: /etc/otel/certs/ca.crt # ← this enables mTLS(tells the Collector, “require a client cert signed by this CA” (i.e. mTLS).)
      http:
        endpoint: 0.0.0.0:4318
        tls:
          cert_file: /etc/otel/certs/server.crt
          key_file: /etc/otel/certs/server.key
          client_ca_file: /etc/otel/certs/ca.crt # ← tells the Collector, “require a client cert signed by this CA” (i.e. mTLS).

exporters:
  # otlp/http:
  #   endpoint: https://otel-backend.example.com:4318
  #   tls:
  #     ca_file: /etc/otel/certs/ca.crt # your backend’s CA
  debug:
    verbosity: detailed

service:
  pipelines:
    traces:
      receivers: [otlp]
      exporters: [debug]
    metrics:
      receivers: [otlp]
      exporters: [debug]
```

```yaml

receivers:
otlp:
protocols:
grpc:
endpoint: 0.0.0.0:4317
tls:
cert_file: /etc/otel/certs/server.crt
key_file: /etc/otel/certs/server.key
client_ca_file: /etc/otel/certs/ca.crt
http:
endpoint: 0.0.0.0:4318
tls:
cert_file: /etc/otel/certs/server.crt
key_file: /etc/otel/certs/server.key
client_ca_file: /etc/otel/certs/ca.crt

processors:
transform/add_tags:
metric_statements: - context: metric
statements: - set(attributes["env"], "dev")

exporters:
debug:
verbosity: detailed

service:
pipelines:
traces:
receivers: [otlp]
processors: []
exporters: [debug]
metrics:
receivers: [otlp]
processors: [transform/add_tags]
exporters: [debug]
```

## Tips & Best Practices
- Rotate certificates regularly.

- Always use strong certificates and protect your CA private key. Prefer at least RSA 2048 or ECC certificates.

- Never commit private keys to public repositories.

- Parameterize all endpoints and file paths using environment variables.

- Use transform processors for custom tagging and data enrichment.

- Use a minimal, reproducible example for docs and onboarding.

8. Best Practices & Recommendations
Rotate certificates regularly.

Use strong keys and CAs. Prefer at least RSA 2048 or ECC certificates.

Store keys securely: Restrict read permissions.

Separate test and production certificates/authorities.

Document certificate generation and renewal.

Add environment/tenant/application attributes to telemetry early in the pipeline (via transform processor or SDK).

Monitor collector logs for certificate errors, especially after renewal.

9. Troubleshooting
400: Client sent an HTTP request to an HTTPS server – Check endpoints, protocols, and that you use https:// for endpoints when TLS is enabled.

mTLS handshake failures: Confirm both sides present the right certificates and CA files.

No data in exporter: Validate that attributes, processors, and pipelines are correct, and check for SDK/Collector version mismatches.

License
MIT (or your choice)

Credits
OpenTelemetry Python

OpenTelemetry Collector

FastAPI

```yaml

```

---

### How to run this Python demo, a quick one-liner is always appreciated:

python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

```

```
