"""Monitoring and observability utilities using OpenTelemetry and Prometheus."""

import functools
import time
from contextlib import contextmanager
from typing import Any, Callable, Dict, Generator, Optional

from opentelemetry import metrics, trace
from opentelemetry.exporter.otlp.proto.grpc.metric_exporter import OTLPMetricExporter
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.metrics import Counter, Histogram, Meter
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.trace import Span, Tracer
from prometheus_client import Counter as PromCounter
from prometheus_client import Histogram as PromHistogram
from prometheus_client import start_http_server


class MonitoringManager:
    """
    Centralized monitoring manager for OpenTelemetry and Prometheus.

    Example:
        monitor = MonitoringManager(service_name="my-service")
        monitor.initialize()

        counter = monitor.get_counter("requests_total")
        counter.add(1, {"endpoint": "/api/data"})
    """

    def __init__(
        self,
        service_name: str,
        service_version: str = "0.1.0",
        otel_endpoint: Optional[str] = None,
        prometheus_port: int = 8000,
    ):
        """
        Initialize monitoring manager.

        Args:
            service_name: Name of the service
            service_version: Version of the service
            otel_endpoint: OpenTelemetry collector endpoint
            prometheus_port: Port for Prometheus metrics endpoint
        """
        self.service_name = service_name
        self.service_version = service_version
        self.otel_endpoint = otel_endpoint or "http://localhost:4317"
        self.prometheus_port = prometheus_port

        self._tracer: Optional[Tracer] = None
        self._meter: Optional[Meter] = None
        self._initialized = False

        # Prometheus metrics registry
        self._prom_counters: Dict[str, PromCounter] = {}
        self._prom_histograms: Dict[str, PromHistogram] = {}

        # OpenTelemetry metrics registry
        self._otel_counters: Dict[str, Counter] = {}
        self._otel_histograms: Dict[str, Histogram] = {}

    def initialize(self) -> None:
        """Initialize OpenTelemetry and Prometheus."""
        if self._initialized:
            return

        # Set up resource attributes
        resource = Resource.create({
            "service.name": self.service_name,
            "service.version": self.service_version,
        })

        # Initialize tracing
        trace_provider = TracerProvider(resource=resource)
        trace_exporter = OTLPSpanExporter(endpoint=self.otel_endpoint, insecure=True)
        trace_provider.add_span_processor(BatchSpanProcessor(trace_exporter))
        trace.set_tracer_provider(trace_provider)
        self._tracer = trace.get_tracer(self.service_name)

        # Initialize metrics
        metric_exporter = OTLPMetricExporter(endpoint=self.otel_endpoint, insecure=True)
        metric_reader = PeriodicExportingMetricReader(metric_exporter)
        meter_provider = MeterProvider(resource=resource, metric_readers=[metric_reader])
        metrics.set_meter_provider(meter_provider)
        self._meter = metrics.get_meter(self.service_name)

        # Start Prometheus HTTP server
        try:
            start_http_server(self.prometheus_port)
        except OSError:
            # Port already in use (likely in tests or multi-process environment)
            pass

        self._initialized = True

    def get_tracer(self) -> Tracer:
        """Get OpenTelemetry tracer."""
        if not self._initialized:
            self.initialize()
        return self._tracer

    def get_meter(self) -> Meter:
        """Get OpenTelemetry meter."""
        if not self._initialized:
            self.initialize()
        return self._meter

    def get_counter(
        self,
        name: str,
        description: str = "",
        unit: str = "1",
    ) -> Counter:
        """
        Get or create OpenTelemetry counter.

        Args:
            name: Counter name
            description: Counter description
            unit: Measurement unit

        Returns:
            Counter: OpenTelemetry counter
        """
        if name not in self._otel_counters:
            meter = self.get_meter()
            self._otel_counters[name] = meter.create_counter(
                name=name,
                description=description,
                unit=unit,
            )
        return self._otel_counters[name]

    def get_histogram(
        self,
        name: str,
        description: str = "",
        unit: str = "ms",
    ) -> Histogram:
        """
        Get or create OpenTelemetry histogram.

        Args:
            name: Histogram name
            description: Histogram description
            unit: Measurement unit

        Returns:
            Histogram: OpenTelemetry histogram
        """
        if name not in self._otel_histograms:
            meter = self.get_meter()
            self._otel_histograms[name] = meter.create_histogram(
                name=name,
                description=description,
                unit=unit,
            )
        return self._otel_histograms[name]

    def get_prom_counter(
        self,
        name: str,
        description: str = "",
        labelnames: Optional[list[str]] = None,
    ) -> PromCounter:
        """
        Get or create Prometheus counter.

        Args:
            name: Counter name
            description: Counter description
            labelnames: Label names for the counter

        Returns:
            PromCounter: Prometheus counter
        """
        if name not in self._prom_counters:
            self._prom_counters[name] = PromCounter(
                name,
                description,
                labelnames=labelnames or [],
            )
        return self._prom_counters[name]

    def get_prom_histogram(
        self,
        name: str,
        description: str = "",
        labelnames: Optional[list[str]] = None,
        buckets: Optional[tuple] = None,
    ) -> PromHistogram:
        """
        Get or create Prometheus histogram.

        Args:
            name: Histogram name
            description: Histogram description
            labelnames: Label names
            buckets: Histogram buckets

        Returns:
            PromHistogram: Prometheus histogram
        """
        if name not in self._prom_histograms:
            kwargs = {
                "name": name,
                "documentation": description,
                "labelnames": labelnames or [],
            }
            if buckets:
                kwargs["buckets"] = buckets

            self._prom_histograms[name] = PromHistogram(**kwargs)
        return self._prom_histograms[name]


# Global monitoring manager instance
_monitoring_manager: Optional[MonitoringManager] = None


def get_monitoring_manager(
    service_name: str = "dataforge",
    **kwargs: Any,
) -> MonitoringManager:
    """
    Get global monitoring manager (singleton).

    Args:
        service_name: Service name
        **kwargs: Additional arguments for MonitoringManager

    Returns:
        MonitoringManager: Global monitoring manager
    """
    global _monitoring_manager
    if _monitoring_manager is None:
        _monitoring_manager = MonitoringManager(service_name, **kwargs)
        _monitoring_manager.initialize()
    return _monitoring_manager


def track_duration(metric_name: str, labels: Optional[Dict[str, str]] = None):
    """
    Decorator to track function execution duration.

    Args:
        metric_name: Name of the duration metric
        labels: Additional labels for the metric

    Example:
        @track_duration("pipeline_execution_duration")
        def run_pipeline():
            # Pipeline code
            pass
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            start_time = time.time()
            manager = get_monitoring_manager()
            histogram = manager.get_histogram(
                metric_name,
                description=f"Duration of {func.__name__}",
                unit="seconds",
            )

            try:
                result = func(*args, **kwargs)
                duration = time.time() - start_time
                attributes = {"function": func.__name__, "status": "success"}
                if labels:
                    attributes.update(labels)
                histogram.record(duration, attributes=attributes)
                return result

            except Exception as e:
                duration = time.time() - start_time
                attributes = {
                    "function": func.__name__,
                    "status": "error",
                    "error_type": type(e).__name__,
                }
                if labels:
                    attributes.update(labels)
                histogram.record(duration, attributes=attributes)
                raise

        return wrapper

    return decorator


def increment_counter(
    counter_name: str,
    value: int = 1,
    labels: Optional[Dict[str, str]] = None,
) -> None:
    """
    Increment a counter metric.

    Args:
        counter_name: Name of the counter
        value: Value to increment by
        labels: Labels for the counter

    Example:
        increment_counter("pipeline_runs", labels={"pipeline": "etl-001"})
    """
    manager = get_monitoring_manager()
    counter = manager.get_counter(counter_name)
    counter.add(value, attributes=labels or {})


@contextmanager
def trace_span(
    span_name: str,
    attributes: Optional[Dict[str, Any]] = None,
) -> Generator[Span, None, None]:
    """
    Context manager for creating a traced span.

    Args:
        span_name: Name of the span
        attributes: Span attributes

    Example:
        with trace_span("process_data", {"data_id": "123"}):
            # Process data
            pass
    """
    manager = get_monitoring_manager()
    tracer = manager.get_tracer()

    with tracer.start_as_current_span(span_name) as span:
        if attributes:
            for key, value in attributes.items():
                span.set_attribute(key, value)
        yield span


def traced(span_name: Optional[str] = None):
    """
    Decorator to automatically trace function execution.

    Args:
        span_name: Custom span name (uses function name if None)

    Example:
        @traced()
        def process_data(data_id: str):
            # Function code
            pass
    """
    def decorator(func: Callable) -> Callable:
        name = span_name or func.__name__

        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            with trace_span(name, {"function": func.__name__}):
                return func(*args, **kwargs)

        return wrapper

    return decorator
