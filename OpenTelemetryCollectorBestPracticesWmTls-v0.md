# OpenTelemetry Collector TLS/SSL Best Practices

This guide outlines how to securely configure TLS in the OpenTelemetry Collector for both receivers and exporters using OTLP over gRPC and HTTP.

### 🔐 Why Use TLS?

TLS (Transport Layer Security) encrypts telemetry data in transit, protecting it from eavesdropping, tampering, and impersonation. It's essential for production environments handling sensitive observability data.

### ✅ Best Practices :

| Category          | Recommendation                                                          |
| ----------------- | ----------------------------------------------------------------------- |
| TLS Everywhere    | Use TLS for all receivers and exporters (gRPC, HTTP, etc.)              |
| Use mTLS          | Require client certificate verification for added trust (mutual TLS)    |
| Cert Rotation     | Use automation (e.g., cert-manager, Vault) to rotate expiring certs     |
| Secure File Paths | Use volume-mounted secrets for certificate storage                      |
| Harden Network    | Use firewalls, load balancers, or mesh proxies to isolate exposed ports |
| TLS Versions      | Use TLS ≥1.2; disable older versions                                    |

### Example: OTel Collector Configuration:

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

---

## 1. Enable Mutual TLS (mTLS)

> - Enable Mutual TLS to validate clients

#### Secure the Pipeline End-to-End:

- Clients are authenticated by the Collector.
- The Collector is authenticated by clients.

> - Configure a _ca_file_ to verify client certificates.

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

exporters:
  otlp/http:
    endpoint: https://otel-backend.example.com:4318
    tls:
      ca_file: /etc/otel/certs/ca.crt # your backend’s CA
```

_Use it in production and whenever transmitting telemetry over public or shared networks._

---

## 2. Certificates: CN and SAN Configuration

Ensure your TLS certificates have:

- **CN** (Common Name) or **SAN** (Subject Alternative Name) fields that
  match the hostname your clients will use to connect.

#### Example SAN block:

```
X509v3 Subject Alternative Name:
DNS:otel-collector.local, IP Address:192.168.1.10
```

#### 2.1. Rotate Certificates Regularly:

> - Automate renewal using Certbot, HashiCorp Vault, or Kubernetes cert-manager.
>   \*Avoid hardcoding certs that expire—use mounted secrets if running in containers.

#### 2.2. Harden Collector Configuration:

> - Limit exposed ports only to those needed.
> - Use access control at the network level (e.g., firewall, Kubernetes NetworkPolicies).
> - Set minimum TLS version (if supported) to TLS 1.2 or later.

---

## 3. File Permissions and Security

- Secure your certificate files:

| File Type      | Recommended Permission | Description                 |
| -------------- | ---------------------- | --------------------------- |
| Private Key    | `600`                  | Owner read/write only       |
| Certificate    | `644`                  | Readable by system services |
| CA Certificate | `644`                  | Readable by system services |

**Avoid storing credentials inside Docker images or version control.**

---

## 4. TLS Configuration Example in `otel-collector-config.yaml`

```yaml
receivers:
  otlp:
    protocols:
      grpc:
        tls:
          cert_file: /etc/otel/certs/server.crt
          key_file: /etc/otel/certs/server.key
          client_ca_file: /etc/otel/certs/ca.crt # Required for mTLS
      http:
        tls:
          cert_file: /etc/otel/certs/server.crt
          key_file: /etc/otel/certs/server.key
          client_ca_file: /etc/otel/certs/ca.crt
```

## 5. Validate TLS Setup Before Production

> - To verify configuration:

#### Using curl for HTTPS:

```bash

curl --cacert ca.crt https://otel-collector.local:4318
```

#### Using openssl for gRPC:

```bash

openssl s_client -connect otel-collector.local:4317 -CAfile ca.crt
```

#### Look for:

```kotlin

Verify return code: 0 (ok)
```

## 6. Automate Certificate Renewal

> - Use cert automation tools like Let's Encrypt or internal PKI.

> - Ensure hot-reload support or set up restart automation.

> - Periodically test your renewal pipeline before expiry.

## 7. Secure Docker Configuration

> **Example docker-compose.yaml Snippet**

```yaml
version: "3.9"
services:
  otel-collector:
    image: otel/opentelemetry-collector:latest
    command: ["--config=/etc/otel/otel-collector-config.yaml"]
    ports:
      - "4317:4317"
      - "4318:4318"
    volumes:
      - ./otel-collector-config.yaml:/etc/otel/otel-collector-config.yaml:ro
      - ./certs:/etc/otel/certs:ro
```

## 8. Secure Exporter Configuration

> - When exporting telemetry to backends, also configure TLS:

```yaml
exporters:
  otlp:
    endpoint: my-backend:4317
    tls:
      ca_file: /etc/otel/certs/ca.crt
      cert_file: /etc/otel/certs/client.crt
      key_file: /etc/otel/certs/client.key
```

## Summary Checklist

> - Enable TLS or mTLS in both receivers and exporters.

> - Use strong, valid certificates with proper CN/SAN fields.

> - Restrict file access to private keys.

> - Test TLS connectivity before production rollout.

> - Automate certificate renewal.

> - Avoid baking credentials into containers.

License
MIT

---

## Critical Configuration Points to Watch

| Section                          | Key Concern                                      | Example/Reminder                                       |
| -------------------------------- | ------------------------------------------------ | ------------------------------------------------------ |
| `receivers.otlp.protocols.*.tls` | Certificates must match expected hostname / IP   | Mismatches cause connection errors                     |
| `client_auth`                    | Controls whether clients must present certs      | Set to `require_and_verify_client_cert` for mTLS       |
| `exporters.*.tls`                | Must be configured if remote endpoint uses HTTPS | Omitting it causes "connection refused" or "TLS error" |
| Cert File Paths                  | Must be **mounted correctly** inside Docker/K8s  | Use `/etc/otel/certs/...` with volumeMounts            |
| Env Variables                    | Avoid injecting secrets via `env:` in YAML       | Prefer mounted files or Vault integration              |

Link to collector Config Example
