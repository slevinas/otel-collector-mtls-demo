# 📊 FastAPI + OpenTelemetry Collector mTLS Example

A minimal working example for securely exporting **traces and metrics** from a Python FastAPI service to an OpenTelemetry Collector using **mutual TLS (mTLS)**.

---

## 🏗️ Architecture

[ FastAPI App (Python) ]
|
| (mTLS - cert auth, encrypted)
v
[ OpenTelemetry Collector ]
|
| (exporters, transform processors)
v
[ Backend: Debug/Files, ClickHouse, Jaeger, etc ]

markdown
Copy
Edit

- **This repo demonstrates:**
  - Secure mTLS setup (CA, server, client certs)
  - Minimal working FastAPI service emitting metrics/traces
  - Example OTel Collector config for mTLS + a transform processor
  - Step-by-step local dev workflow

---

## 🚦 Quick Start

### 1. **Generate CA, Server, and Client Certificates**

> **IMPORTANT:**  
> The **server certificate’s CN/SAN** must match the OTel Collector’s hostname as seen by clients (`otel-collector` for Docker Compose).  
> The **client certificate** should have a unique CN for identification.

**A. Create CA**

```bash
mkdir -p certs && cd certs
openssl genrsa -out ca.key 4096
openssl req -x509 -new -nodes -key ca.key -sha256 -days 3650 -out ca.crt -subj "/CN=MyRootCA"
```

**B. Create Server Key & CSR with SANs**

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
EOF


openssl genrsa -out server.key 4096
openssl req -new -key server.key -out server.csr -config server-openssl.cnf
openssl x509 -req -in server.csr -CA ca.crt -CAkey ca.key -CAcreateserial -out server.crt -days 365 -sha256 -extfile server-openssl.cnf -extensions req_ext
```

**C. Create Client Key & CSR**


```bash

cat > client-openssl.cnf <<EOF
[ req ]
default_bits       = 4096
prompt             = no
default_md         = sha256
distinguished_name = dn
req_extensions     = req_ext
[ dn ]
CN = client-app
[ req_ext ]
subjectAltName = @alt_names
[ alt_names ]
DNS.1 = client-app
EOF

openssl genrsa -out client.key 4096
openssl req -new -key client.key -out client.csr -config client-openssl.cnf
openssl x509 -req -in client.csr -CA ca.crt -CAkey ca.key -CAcreateserial -out client.crt -days 365 -sha256 -extfile client-openssl.cnf -extensions req_ext
```

2. Set Environment Variables
Create a .env file in your project root:

dotenv
Copy
Edit
OTEL_EXPORTER_OTLP_METRICS_ENDPOINT=https://localhost:4318/v1/metrics
OTEL_EXPORTER_OTLP_TRACES_ENDPOINT=https://localhost:4318/v1/traces
OTEL_EXPORTER_OTLP_CERTIFICATE=certs/ca.crt
OTEL_EXPORTER_OTLP_CLIENT_CERTIFICATE=certs/client.crt
OTEL_EXPORTER_OTLP_CLIENT_KEY=certs/client.key
OTEL_EXPORTER_OTLP_INSECURE=false
3. Configure and Run the OTel Collector
Example docker-compose.yaml:

yaml
Copy
Edit
services:
  otel-collector:
    image: otel/opentelemetry-collector-contrib:latest
    container_name: otel-collector
    command: ["--config=/etc/otel/config.yaml"]
    ports:
      - "4317:4317"
      - "4318:4318"
    volumes:
      - ./otel-collector-config.yaml:/etc/otel/config.yaml:ro
      - ./certs:/etc/otel/certs:ro
    restart: unless-stopped
Example otel-collector-config.yaml:

yaml
Copy
Edit
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

exporters:
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
Tip:
To add a custom tag to all metrics (e.g., env=dev), use a transform processor in your pipeline.

4. Run Everything
bash
Copy
Edit
# Start Collector
docker compose up --build -d

# In another shell, run your FastAPI app
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
uvicorn admin_server.app:app --reload
Check your collector logs for incoming telemetry data.

📖 How mTLS Secures Telemetry
mTLS ensures both the FastAPI client and the OTel Collector server authenticate each other, using certificates signed by a trusted CA.

Only trusted services (with valid client certs) can send telemetry.

The server certificate’s SAN must include the hostname/IP used by clients (e.g., otel-collector, localhost).

The client certificate’s CN/SAN is used for audit/identification, not hostname matching.

⚠️ Troubleshooting
certificate verify failed: CA, SAN, or certificate files do not match—double-check hostnames and file paths.

bad record MAC: Usually a key/cert mismatch or wrong format (use PEM).

hostname mismatch: Python client is connecting to localhost, but server cert SAN doesn’t include localhost.

Unable to load certificate: Wrong file paths or permissions.

🔐 Rotating Certificates
Issue new certs (CA, server, client as needed).

Replace files on both collector and client sides.

Restart affected containers/services.

⚙️ ENVIRONMENT VARIABLES REFERENCE
Variable	Purpose
OTEL_EXPORTER_OTLP_METRICS_ENDPOINT	OTel metrics HTTPS endpoint
OTEL_EXPORTER_OTLP_TRACES_ENDPOINT	OTel traces HTTPS endpoint
OTEL_EXPORTER_OTLP_CERTIFICATE	CA cert path
OTEL_EXPORTER_OTLP_CLIENT_CERTIFICATE	Client cert path
OTEL_EXPORTER_OTLP_CLIENT_KEY	Client key path
OTEL_EXPORTER_OTLP_INSECURE	Set false for TLS/mTLS

💡 Best Practices for Internal Use
Always use mTLS for sensitive telemetry flows (prevents spoofing and eavesdropping).

Rotate certs regularly, automate issuance/rotation if possible.

Never share private keys; keep cert permissions tight (600 or 400).

Use unique client certs per service for better traceability and revocation.

📋 Resources
OpenTelemetry Collector Docs

OpenTelemetry Python

Transform Processor

OpenSSL Cookbook

Maintainer: Your Name/Team
**Contributions and questions welcome!_

yaml
Copy
Edit

---

### **How to Commit**

1. **Branch name suggestion:**
docs/otel-mtls-demo

markdown
Copy
Edit

2. **Commit message suggestion:**
docs: Add complete OpenTelemetry Collector mTLS demo and best practices README

pgsql
Copy
Edit

3. **How to push:**
```bash
git checkout -b docs/otel-mtls-demo
git add README.md docker-compose.yaml otel-collector-config.yaml certs/
git commit -m "docs: Add complete OpenTelemetry Collector mTLS demo and best practices README"
git push origin docs/otel-mtls-demo
````
