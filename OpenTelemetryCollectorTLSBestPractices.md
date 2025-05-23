## 📦 OpenTelemetry Collector TLS/SSl Best Practices

This document outlines how to securely configure TLS in the OpenTelemetry Collector for both receivers and exporters using OTLP over gRPC and HTTP.

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
  otlphttp:
    endpoint: https://otel-backend.example.com:4318
    tls:
      ca_file: /etc/otel/certs/backend_ca.crt

service:
  pipelines:
    traces:
      receivers: [otlp]
      exporters: [otlphttp]
    metrics:
      receivers: [otlp]
      exporters: [otlphttp]
```
* #### client_auth: require_and_verify_client_cert: enforces that every client must present a cert the CA signed.
* #### The Collector uses the same server.crt/key for both gRPC and HTTP listeners.



#### 📁 Folder Structure for Certificates

Place these in your container or host:

/etc/otel/certs/
├── server.crt # Server certificate
├── server.key # Private key
├── ca.crt # (Optional) Client CA cert for mTLS
├── backend_ca.crt # Used to verify upstream HTTPS endpoint

#### 🚨 Critical Notes

- Ensure the server certificate’s CN/SAN matches the collector’s public hostname.

- Set file permissions properly (e.g., 600 for private keys).

- Validate TLS handshakes during deployment (e.g., with curl or OpenSSL).

- Test renewal pipelines before expiration dates.

#### Expanding on these critical Notes:

1. Ensure the server certificate’s CN/SAN matches the collector’s public hostname
   What it means:

The Common Name (CN) and especially the Subject Alternative Name (SAN) in your server.crt must exactly match the DNS name (or IP) clients use to connect to the collector (e.g., otel-collector.local or collector.example.com).

If the client connects to localhost but your cert is for otel-collector.local, you’ll get hostname mismatch errors (like you just saw with curl).

For your setup:

Your cert was generated for CN=otel-collector.local, but your test client was connecting to localhost.

Best practice:

Either always connect to the name on the cert (otel-collector.local), mapping it to 127.0.0.1 in /etc/hosts (for local dev),

Or re-issue your cert with a SAN that includes all names you’ll use (e.g., both otel-collector.local and localhost).

Production tip: Use SAN, not just CN; SAN is the standard for TLS hostname validation.

2. Set file permissions properly (e.g., 600 for private keys)
   What it means:

The .key files (for both server and client) should only be readable by the owner—never group/world readable.

600 means “owner can read/write, no one else can do anything.”

How to do this:

bash
Copy
Edit
chmod 600 certs/server.key certs/client.key
Otherwise, someone else with access to the machine (or container) could steal your private key and impersonate your service.

For your setup:

Set all _.key files (and even _.crt if you like) to 600.

If mounting into Docker, ensure the host files have 600 permissions before mounting. Docker preserves the file mode.

3. Validate TLS handshakes during deployment (e.g., with curl or OpenSSL)
   What it means:

Before trusting your system is secure, manually check that the TLS (and mTLS) handshake actually works and fails as expected for the wrong certs.

This catches misconfiguration before a real client tries to send telemetry.

For your setup:

You already did this!

You used openssl s_client to verify both sides of the handshake, and

curl to check an actual HTTP request with mTLS.

Best practice:

Run these tests whenever you deploy, change certs, or rotate the CA.

Also, try intentionally connecting without a client cert—make sure the Collector rejects the request. This proves mTLS is enforced.

4. Test renewal pipelines before expiration dates
   What it means:

Certificates expire (usually in 1 year or less).

You need a plan (and preferably automation) for generating new certs, signing with the CA, and updating them in your running Collector(s) before the old ones expire.

“Test the pipeline” means do a dry-run: swap in a new cert, restart Collector, and make sure telemetry still flows.

For your setup:

If you’re just developing, set yourself a calendar reminder to rotate/reissue the certs before expiry.

If you automate, use a script or tool (like cert-manager for Kubernetes, or a shell script with openssl for Docker).

Test your process: Don’t just generate certs and forget them; practice renewing (swap out files, restart Collector, verify with curl).

Why? Because if the cert expires and the Collector restarts, all clients will fail mTLS and telemetry will stop flowing.

Summary Table
Best Practice What You Should Do How You Do It in Your Setup
CN/SAN matches hostname CN/SAN on cert = hostname in URL Use otel-collector.local, or add SAN for localhost
File permissions (600 for private keys) Only owner can read private key files chmod 600 certs/\*.key
Validate TLS handshakes Test mTLS with curl/openssl on every deploy Run curl and openssl s_client to check handshake
Test renewal pipelines Practice swapping in new certs and restarting Collector Replace certs, restart, re-test curl/otel exporter

If you follow all four, you’ll have:
Fewer “it works on my machine but not in prod” issues,

Less risk of keys leaking,

Fewer outages from expired certs,

Better overall observability reliability.
