import os
import logging
from opentelemetry import trace, metrics
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.exporter.otlp.proto.grpc.metric_exporter import OTLPMetricExporter
from opentelemetry.instrumentation.grpc import GrpcInstrumentorServer
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
from opentelemetry.sdk.resources import Resource
from opentelemetry.semconv.resource import ResourceAttributes

logger = logging.getLogger(__name__)

class TelemetryManager:
    def __init__(self, service_name: str, service_version: str = "1.0.0"):
        self.service_name = service_name
        self.service_version = service_version
        self.setup_telemetry()
    
    def setup_telemetry(self):
        """Initialize OpenTelemetry instrumentation"""
        try:
            # Resource information
            resource = Resource.create({
                ResourceAttributes.SERVICE_NAME: self.service_name,
                ResourceAttributes.SERVICE_VERSION: self.service_version,
                ResourceAttributes.SERVICE_NAMESPACE: "imageflow",
                "environment": os.getenv("ENVIRONMENT", "production"),
                "k8s.cluster.name": "imageflow-k3s",
                "k8s.namespace.name": os.getenv("K8S_NAMESPACE", "image-processing"),
                "k8s.pod.name": os.getenv("HOSTNAME"),
            })
            
            # Setup tracing
            self.setup_tracing(resource)
            
            # Setup metrics
            self.setup_metrics(resource)
            
            # Instrument gRPC server
            GrpcInstrumentorServer().instrument()
            
            logger.info(f"OpenTelemetry initialized for {self.service_name}")
            
        except Exception as e:
            logger.warning(f"Failed to initialize OpenTelemetry: {e}")
    
    def setup_tracing(self, resource):
        """Setup distributed tracing"""
        otlp_endpoint = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT", "http://otel-collector:4317")
        
        trace_provider = TracerProvider(resource=resource)
        trace_exporter = OTLPSpanExporter(
            endpoint=otlp_endpoint,
            insecure=True
        )
        trace_provider.add_span_processor(
            BatchSpanProcessor(trace_exporter)
        )
        trace.set_tracer_provider(trace_provider)
    
    def setup_metrics(self, resource):
        """Setup metrics collection"""
        otlp_endpoint = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT", "http://otel-collector:4317")
        
        metric_reader = PeriodicExportingMetricReader(
            OTLPMetricExporter(
                endpoint=otlp_endpoint,
                insecure=True
            ),
            export_interval_millis=10000
        )
        metric_provider = MeterProvider(
            resource=resource,
            metric_readers=[metric_reader]
        )
        metrics.set_meter_provider(metric_provider)
    
    def get_tracer(self):
        """Get tracer instance"""
        return trace.get_tracer(self.service_name)
    
    def get_meter(self):
        """Get meter instance"""
        return metrics.get_meter(self.service_name)