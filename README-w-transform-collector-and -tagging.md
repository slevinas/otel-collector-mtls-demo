# OpenTelemetry Collector: Secure Configuration & Tagging Strategy

## 🔐 1. Security Best Practices

### 1.1 TLS/SSL Configuration

#### Receiver Security

Use HTTPS (TLS) for the OTLP receiver to ensure encrypted transport:

```yaml
receivers:
  otlp:
    protocols:
      http:
        endpoint: 0.0.0.0:4318
        tls:
          cert_file: /etc/otel/certs/server.crt
          key_file: /etc/otel/certs/server.key
```

#### Exporter Security

Secure outbound communication with the backend:

```yaml
exporters:
  otlp:
    endpoint: https://your-backend:4318
    tls:
      ca_file: /etc/otel/certs/ca.crt
      insecure: false
```

#### Mutual TLS (mTLS)

Optionally enforce mutual TLS using:

```yaml
tls:
  cert_file: /etc/otel/certs/client.crt
  key_file: /etc/otel/certs/client.key
  ca_file: /etc/otel/certs/ca.crt
```

### 1.2 Collector Runtime Security

- Run collector as a non-root user
- Drop unused Linux capabilities (if running in a container)
- Reduce verbosity of logs in production

---

## 🏷 2. Tagging Strategy

### 2.1 Goal

Attach dynamic metadata such as `client_id`, `source`, or `org_name` to incoming telemetry based on client info or trace context.

### 2.2 Approach A: Static Tagging with `attributes` Processor

```yaml
processors:
  attributes/add_client_tag:
    actions:
      - key: org_name
        value: XPLG-benchmarker-dev-tag-test
        action: insert
```

**Explanation:** This inserts a static `org_name` into all resource attributes if not already present.

### 2.3 Approach B: Dynamic Tagging with `transform` Processor

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

---

## 🧪 3. Test Scenario

### 3.1 Input Metrics

```json
{
  "resource": {
    "attributes": {
      "service.name": "admin-api"
    }
  },
  "metrics": [
    {
      "name": "operation_success_count",
      "data": {
        "data_points": [
          {
            "attributes": {
              "endpoint": "run_vector_math"
            },
            "value": 10
          }
        ]
      }
    }
  ]
}
```

### 3.1.1 Submit via `curl`

```bash
curl -X POST https://localhost:4318/v1/metrics \
  --cert /etc/otel/certs/client.crt \
  --key /etc/otel/certs/client.key \
  --cacert /etc/otel/certs/ca.crt \
  -H "Content-Type: application/json" \
  --data-binary @path/to/test-metric.json
```

> 💡 Ensure your client cert is signed by the same CA as the server and that mTLS is enabled.

### 3.2 Output with Static and Dynamic Tagging

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

---

## 📂 4. Sample Collector Config

```yaml
receivers:
  otlp:
    protocols:
      http:
        endpoint: 0.0.0.0:4318
        tls:
          cert_file: /etc/otel/certs/server.crt
          key_file: /etc/otel/certs/server.key

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
```

---

## 🚀 5. Implementation Plan (mTLS & Tagging)

### 5.1. **Generate Certificates:**

- Create a self-signed CA.
- Issue server cert/key: `server.crt` & `server.key`.
- Issue client cert/key: `client.crt` & `client.key`.
- Place all in `/etc/otel/certs/` on your host.

### 5.2. **Update Docker Compose:**

```yaml
volumes:
  - ./certs:/etc/otel/certs:ro
  - ./logs:/otel-logs
```

### 5.3. **Deploy Collector:**

```bash
docker-compose -f docker-compose.otelcollector.yaml up -d
```

### 5.4. **Verify mTLS Connectivity:**

```bash
curl -v https://localhost:4318/v1/metrics \
--cert certs/client.crt --key certs/client.key --cacert certs/ca.crt
```

### 5.5. **Push Test Metric:**

```bash
curl -k https://localhost:4318/v1/metrics \
--cert certs/client.crt --key certs/client.key \
--cacert certs/ca.crt \
-H "Content-Type: application/json" \
--data-binary @docs/otel-collector/test-metric.json
```

### 5.6. **Inspect Output:**

- `cat logs/tagged_metrics.json | jq .`
- Confirm both static `org_name` and dynamic `client_id` are present.

### 5.7. **Hardening & Cleanup:**

- Run collector under a non-root UID/GID.
- Drop unnecessary Linux capabilities.
- Set `logging.level` to `info` or `error`.

---

## 📌 6. Next Steps

- Add remote `otlp` exporter for production telemetry.
- Integrate Helm/Kubernetes manifests with `Secret` volumes for TLS.
- Automate cert rotation with a vault or certificate manager.
