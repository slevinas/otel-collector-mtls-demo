## 📖 Secure OpenTelemetry Collector Integration with mTLS: Best Practices & Example

This document demonstrates best practices for securing OpenTelemetry (OTel) data transfer between your instrumented application and the OpenTelemetry Collector using TLS/mTLS. It also shows how to enrich metrics with tags using the Collector’s transform processor.

## Table of contents

### 1. [Why Secure the Collector?](#-why-use-tls)

### 2. [Best Practices mini table](#-best-practices-)

### 3. [Environment Variables (.env)](#3-environment-variables)

### 4. [OpenTelemetry Collector mTLS Configuration (mtls-collector-config.yaml)](#4-example-otel-collector-configuration)

### 5. [Docker Compose Example (Collector)]()

### 6. [Enriching Metrics with an Attribute and Transform Processors](#7-enriching-metrics-with-a-transform-processor)

### 7. [Best Practices & Recommendations](#7-best-practices--recommendations)

### 8. [Link to Working Example]()

---

### 🔐 Why Use TLS?

TLS (Transport Layer Security) encrypts telemetry data in transit, protecting it from eavesdropping, tampering, and impersonation. It's essential for production environments handling sensitive observability data.

---

### ✅ Best Practices :

| Category          | Recommendation                                                          |
| ----------------- | ----------------------------------------------------------------------- |
| TLS Everywhere    | Use TLS for all receivers and exporters (gRPC, HTTP, etc.)              |
| Use mTLS          | Require client certificate verification for added trust (mutual TLS)    |
| Cert Rotation     | Use automation (e.g., cert-manager, Vault) to rotate expiring certs     |
| Secure File Paths | Use volume-mounted secrets for certificate storage                      |
| Harden Network    | Use firewalls, load balancers, or mesh proxies to isolate exposed ports |
| TLS Versions      | Use TLS ≥1.2; disable older versions                                    |

File Permissions and Security

- Secure your certificate files:

| File Type      | Recommended Permission | Description                 |
| -------------- | ---------------------- | --------------------------- |
| Private Key    | `600`                  | Owner read/write only       |
| Certificate    | `644`                  | Readable by system services |
| CA Certificate | `644`                  | Readable by system services |

**Avoid storing credentials inside Docker images or version control.**

---

### 3. Environment Variables

- [env variables for OTel python sdk:](https://opentelemetry-python.readthedocs.io/en/latest/sdk/environment_variables.html#opentelemetry.sdk.environment_variables.OTEL_EXPORTER_OTLP_CERTIFICATE)

```env

OTEL_EXPORTER_OTLP_METRICS_ENDPOINT=https://localhost:4318/v1/metrics
OTEL_EXPORTER_OTLP_TRACES_ENDPOINT=https://localhost:4318/v1/traces


OTEL_EXPORTER_OTLP_ENDPOINT=https://localhost:4318


OTEL_EXPORTER_OTLP_CERTIFICATE=certs/ca.crt
OTEL_EXPORTER_OTLP_CLIENT_CERTIFICATE=certs/client.crt
OTEL_EXPORTER_OTLP_CLIENT_KEY=certs/client.key
OTEL_EXPORTER_OTLP_INSECURE=false

```

---

### 4. Example: OTel Collector Configuration:

```yaml
receivers:
  otlp:
    protocols:
      grpc:
        endpoint: 0.0.0.0:4317
        tls:
          cert_file: /etc/otel/certs/server.crt
          key_file: /etc/otel/certs/server.key
          client_ca_file: /etc/otel/certs/ca.crt # Enables mTLS

      http:
        endpoint: 0.0.0.0:4318
        tls:
          cert_file: /etc/otel/certs/server.crt
          key_file: /etc/otel/certs/server.key
          client_ca_file: /etc/otel/certs/ca.crt # ← tells the Collector, “require a client cert signed by this CA” (i.e. mTLS).

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

---

### 5. Example docker-compose.yaml:

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

---

### 6. Enriching Metrics with a Transform Processor

The transform processor in the Collector allows you to add tags (attributes) to metrics before exporting.

Tagging Strategy

### 6.1 Goal

Attach dynamic metadata such as `client_id`, `source`, or `org_name` to incoming telemetry based on client info or trace context.

### 6.2 Approach A: Static Tagging with `attributes` Processor

```yaml
processors:
  attributes/add_client_tag:
    actions:
      - key: org_name
        value: XPLG-benchmarker-dev-tag-test
        action: insert
```

**Explanation:** This inserts a static `org_name` into all resource attributes if not already present.

### 6.3 Approach B: Dynamic Tagging with `transform` Processor

```yaml
processors:
  transform/tag_metrics:
    metric_statements:
      - context: datapoint
        statements:
          - set(datapoint.attributes["client_id"], resource.attributes["service.name"])
```

**Explanation:** This dynamically copies the `service.name` from the resource section into each datapoint as `client_id`.

### 2.4 Field Mapping

| Source Field                    | Target Tag      | Example Value     |
| ------------------------------- | --------------- | ----------------- |
| `resource.service.name`         | `client_id`     | "admin-api"       |
| `resource.custom_id`            | `org_name`      | "XPLG"            |
| `datapoint.attributes.endpoint` | `endpoint_flat` | "run_vector_math" |

```yaml
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
```

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

### 10. Further Reading & References

[OpenTelemetry Collector TLS/mTLS Authentication (official docs)]()

[OpenTelemetry Collector Processors: transform]()

[OpenTelemetry Python SDK: OTLP Exporter]()

[Best Practices for Telemetry Security (OpenTelemetry Blog)]()

### 11. Full Working Example

[Link to collector Config Example](https://github.com/slevinas/xplg-api-benchmaker-runner/blob/demo/otel-collector-mtls-taging-processor-file-exporter/README.md)
