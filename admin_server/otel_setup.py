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
