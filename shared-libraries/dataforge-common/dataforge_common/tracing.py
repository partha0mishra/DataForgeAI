"""Distributed tracing with OpenTelemetry and Jaeger for DataForge AI.

This module provides comprehensive distributed tracing capabilities including:
- Automatic instrumentation for FastAPI, SQLAlchemy, Redis, HTTP clients
- Custom span creation and attributes
- Context propagation across services
- Integration with Jaeger, Zipkin, and other backends
"""

import os
from typing import Optional, Dict, Any, Callable
from contextlib import contextmanager
from functools import wraps

try:
    from opentelemetry import trace
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter
    from opentelemetry.sdk.resources import Resource, SERVICE_NAME, SERVICE_VERSION
    from opentelemetry.exporter.jaeger.thrift import JaegerExporter
    from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
    from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
    from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor
    from opentelemetry.instrumentation.redis import RedisInstrumentor
    from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor
    from opentelemetry.instrumentation.requests import RequestsInstrumentor
    from opentelemetry.trace import Status, StatusCode, Span
    from opentelemetry.trace.propagation.tracecontext import TraceContextTextMapPropagator
except ImportError:
    raise ImportError(
        "Tracing requires OpenTelemetry. Install with: "
        "pip install opentelemetry-api opentelemetry-sdk opentelemetry-instrumentation-fastapi "
        "opentelemetry-instrumentation-sqlalchemy opentelemetry-instrumentation-redis "
        "opentelemetry-instrumentation-httpx opentelemetry-exporter-jaeger "
        "opentelemetry-exporter-otlp"
    )

from .logging import get_logger
from .settings import get_settings

logger = get_logger(__name__)


class TracingConfig:
    """Configuration for distributed tracing."""

    def __init__(
        self,
        service_name: str = "dataforge-ai",
        service_version: str = "0.1.0",
        environment: str = "development",
        jaeger_host: Optional[str] = None,
        jaeger_port: int = 6831,
        otlp_endpoint: Optional[str] = None,
        enable_console: bool = False,
        sample_rate: float = 1.0,
    ):
        """Initialize tracing configuration.

        Args:
            service_name: Name of the service
            service_version: Version of the service
            environment: Environment (dev, staging, prod)
            jaeger_host: Jaeger agent host
            jaeger_port: Jaeger agent port
            otlp_endpoint: OTLP exporter endpoint (e.g., localhost:4317)
            enable_console: Enable console exporter for debugging
            sample_rate: Sampling rate (0.0 to 1.0)
        """
        self.service_name = service_name
        self.service_version = service_version
        self.environment = environment
        self.jaeger_host = jaeger_host
        self.jaeger_port = jaeger_port
        self.otlp_endpoint = otlp_endpoint
        self.enable_console = enable_console
        self.sample_rate = sample_rate


class DistributedTracing:
    """Manager for distributed tracing."""

    def __init__(self, config: Optional[TracingConfig] = None):
        """Initialize distributed tracing.

        Args:
            config: Tracing configuration
        """
        self.config = config or self._load_config_from_env()
        self.tracer_provider: Optional[TracerProvider] = None
        self.tracer: Optional[trace.Tracer] = None
        self.initialized = False

    def _load_config_from_env(self) -> TracingConfig:
        """Load configuration from environment variables."""
        settings = get_settings()

        return TracingConfig(
            service_name=os.getenv("OTEL_SERVICE_NAME", settings.otel_service_name),
            service_version=os.getenv("SERVICE_VERSION", "0.1.0"),
            environment=settings.environment,
            jaeger_host=os.getenv("JAEGER_AGENT_HOST", "localhost"),
            jaeger_port=int(os.getenv("JAEGER_AGENT_PORT", "6831")),
            otlp_endpoint=settings.otel_exporter_otlp_endpoint,
            enable_console=os.getenv("OTEL_CONSOLE_EXPORTER", "false").lower() == "true",
            sample_rate=float(os.getenv("OTEL_TRACE_SAMPLE_RATE", "1.0")),
        )

    def initialize(self) -> None:
        """Initialize OpenTelemetry tracing."""
        if self.initialized:
            logger.warning("Tracing already initialized")
            return

        # Create resource with service information
        resource = Resource.create({
            SERVICE_NAME: self.config.service_name,
            SERVICE_VERSION: self.config.service_version,
            "environment": self.config.environment,
            "service.instance.id": os.getenv("HOSTNAME", "unknown"),
        })

        # Create tracer provider
        self.tracer_provider = TracerProvider(resource=resource)

        # Add exporters
        if self.config.jaeger_host:
            self._add_jaeger_exporter()

        if self.config.otlp_endpoint:
            self._add_otlp_exporter()

        if self.config.enable_console:
            self._add_console_exporter()

        # Set global tracer provider
        trace.set_tracer_provider(self.tracer_provider)

        # Get tracer
        self.tracer = trace.get_tracer(
            __name__,
            self.config.service_version,
        )

        self.initialized = True
        logger.info(
            f"Distributed tracing initialized for {self.config.service_name} "
            f"(env={self.config.environment})"
        )

    def _add_jaeger_exporter(self) -> None:
        """Add Jaeger exporter."""
        try:
            jaeger_exporter = JaegerExporter(
                agent_host_name=self.config.jaeger_host,
                agent_port=self.config.jaeger_port,
            )

            span_processor = BatchSpanProcessor(jaeger_exporter)
            self.tracer_provider.add_span_processor(span_processor)

            logger.info(
                f"Jaeger exporter configured: {self.config.jaeger_host}:{self.config.jaeger_port}"
            )
        except Exception as e:
            logger.error(f"Failed to configure Jaeger exporter: {str(e)}")

    def _add_otlp_exporter(self) -> None:
        """Add OTLP exporter."""
        try:
            otlp_exporter = OTLPSpanExporter(
                endpoint=self.config.otlp_endpoint,
                insecure=True,  # Use TLS in production
            )

            span_processor = BatchSpanProcessor(otlp_exporter)
            self.tracer_provider.add_span_processor(span_processor)

            logger.info(f"OTLP exporter configured: {self.config.otlp_endpoint}")
        except Exception as e:
            logger.error(f"Failed to configure OTLP exporter: {str(e)}")

    def _add_console_exporter(self) -> None:
        """Add console exporter for debugging."""
        console_exporter = ConsoleSpanExporter()
        span_processor = BatchSpanProcessor(console_exporter)
        self.tracer_provider.add_span_processor(span_processor)
        logger.info("Console exporter configured")

    def instrument_fastapi(self, app):
        """Instrument FastAPI application.

        Args:
            app: FastAPI application instance
        """
        if not self.initialized:
            self.initialize()

        try:
            FastAPIInstrumentor.instrument_app(app)
            logger.info("FastAPI instrumentation enabled")
        except Exception as e:
            logger.error(f"Failed to instrument FastAPI: {str(e)}")

    def instrument_sqlalchemy(self, engine):
        """Instrument SQLAlchemy engine.

        Args:
            engine: SQLAlchemy engine instance
        """
        if not self.initialized:
            self.initialize()

        try:
            SQLAlchemyInstrumentor().instrument(
                engine=engine,
                enable_commenter=True,
            )
            logger.info("SQLAlchemy instrumentation enabled")
        except Exception as e:
            logger.error(f"Failed to instrument SQLAlchemy: {str(e)}")

    def instrument_redis(self):
        """Instrument Redis client."""
        if not self.initialized:
            self.initialize()

        try:
            RedisInstrumentor().instrument()
            logger.info("Redis instrumentation enabled")
        except Exception as e:
            logger.error(f"Failed to instrument Redis: {str(e)}")

    def instrument_http_clients(self):
        """Instrument HTTP clients (httpx and requests)."""
        if not self.initialized:
            self.initialize()

        try:
            HTTPXClientInstrumentor().instrument()
            RequestsInstrumentor().instrument()
            logger.info("HTTP client instrumentation enabled")
        except Exception as e:
            logger.error(f"Failed to instrument HTTP clients: {str(e)}")

    @contextmanager
    def start_span(
        self,
        name: str,
        attributes: Optional[Dict[str, Any]] = None,
        kind: trace.SpanKind = trace.SpanKind.INTERNAL,
    ):
        """Create a new span as context manager.

        Args:
            name: Span name
            attributes: Optional span attributes
            kind: Span kind (INTERNAL, SERVER, CLIENT, PRODUCER, CONSUMER)

        Yields:
            Active span
        """
        if not self.initialized:
            # If tracing not initialized, use no-op span
            yield trace.INVALID_SPAN
            return

        with self.tracer.start_as_current_span(
            name,
            kind=kind,
            attributes=attributes or {},
        ) as span:
            yield span

    def add_span_attributes(self, attributes: Dict[str, Any]) -> None:
        """Add attributes to current span.

        Args:
            attributes: Attributes to add
        """
        current_span = trace.get_current_span()
        if current_span and current_span.is_recording():
            for key, value in attributes.items():
                current_span.set_attribute(key, value)

    def add_span_event(self, name: str, attributes: Optional[Dict[str, Any]] = None) -> None:
        """Add event to current span.

        Args:
            name: Event name
            attributes: Optional event attributes
        """
        current_span = trace.get_current_span()
        if current_span and current_span.is_recording():
            current_span.add_event(name, attributes=attributes or {})

    def record_exception(self, exception: Exception) -> None:
        """Record exception in current span.

        Args:
            exception: Exception to record
        """
        current_span = trace.get_current_span()
        if current_span and current_span.is_recording():
            current_span.record_exception(exception)
            current_span.set_status(Status(StatusCode.ERROR, str(exception)))

    def get_trace_context(self) -> Dict[str, str]:
        """Get current trace context for propagation.

        Returns:
            Trace context headers
        """
        propagator = TraceContextTextMapPropagator()
        carrier = {}
        propagator.inject(carrier)
        return carrier

    def set_trace_context(self, context: Dict[str, str]) -> None:
        """Set trace context from headers.

        Args:
            context: Trace context headers
        """
        propagator = TraceContextTextMapPropagator()
        propagator.extract(context)


# Global tracing instance
_tracing: Optional[DistributedTracing] = None


def get_tracing() -> DistributedTracing:
    """Get global tracing instance.

    Returns:
        Distributed tracing instance
    """
    global _tracing
    if _tracing is None:
        _tracing = DistributedTracing()
        _tracing.initialize()
    return _tracing


def init_tracing(config: Optional[TracingConfig] = None) -> DistributedTracing:
    """Initialize global tracing.

    Args:
        config: Optional tracing configuration

    Returns:
        Distributed tracing instance
    """
    global _tracing
    _tracing = DistributedTracing(config)
    _tracing.initialize()
    return _tracing


# Decorators

def trace_function(
    name: Optional[str] = None,
    attributes: Optional[Dict[str, Any]] = None,
):
    """Decorator to trace a function.

    Args:
        name: Optional span name (defaults to function name)
        attributes: Optional span attributes

    Returns:
        Decorated function
    """
    def decorator(func: Callable) -> Callable:
        span_name = name or func.__name__

        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            tracing = get_tracing()
            with tracing.start_span(span_name, attributes=attributes):
                try:
                    result = await func(*args, **kwargs)
                    return result
                except Exception as e:
                    tracing.record_exception(e)
                    raise

        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            tracing = get_tracing()
            with tracing.start_span(span_name, attributes=attributes):
                try:
                    result = func(*args, **kwargs)
                    return result
                except Exception as e:
                    tracing.record_exception(e)
                    raise

        # Return appropriate wrapper based on function type
        import inspect
        if inspect.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper

    return decorator


def trace_method(name: Optional[str] = None):
    """Decorator to trace a class method.

    Args:
        name: Optional span name

    Returns:
        Decorated method
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def async_wrapper(self, *args, **kwargs):
            span_name = name or f"{self.__class__.__name__}.{func.__name__}"
            tracing = get_tracing()

            with tracing.start_span(span_name):
                try:
                    result = await func(self, *args, **kwargs)
                    return result
                except Exception as e:
                    tracing.record_exception(e)
                    raise

        @wraps(func)
        def sync_wrapper(self, *args, **kwargs):
            span_name = name or f"{self.__class__.__name__}.{func.__name__}"
            tracing = get_tracing()

            with tracing.start_span(span_name):
                try:
                    result = func(self, *args, **kwargs)
                    return result
                except Exception as e:
                    tracing.record_exception(e)
                    raise

        import inspect
        if inspect.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper

    return decorator


# Helper functions for common operations

@contextmanager
def trace_operation(operation_name: str, **attributes):
    """Trace an operation with custom attributes.

    Args:
        operation_name: Name of the operation
        **attributes: Additional attributes

    Yields:
        Active span
    """
    tracing = get_tracing()
    with tracing.start_span(operation_name, attributes=attributes) as span:
        yield span


def trace_database_query(query: str, **attributes):
    """Trace a database query.

    Args:
        query: SQL query
        **attributes: Additional attributes

    Returns:
        Context manager
    """
    attrs = {
        "db.statement": query,
        "db.system": "postgresql",
        **attributes
    }
    return trace_operation("database.query", **attrs)


def trace_cache_operation(operation: str, key: str, **attributes):
    """Trace a cache operation.

    Args:
        operation: Operation type (get, set, delete)
        key: Cache key
        **attributes: Additional attributes

    Returns:
        Context manager
    """
    attrs = {
        "cache.operation": operation,
        "cache.key": key,
        **attributes
    }
    return trace_operation("cache.operation", **attrs)


def trace_external_call(service: str, endpoint: str, **attributes):
    """Trace an external service call.

    Args:
        service: Service name
        endpoint: Endpoint being called
        **attributes: Additional attributes

    Returns:
        Context manager
    """
    attrs = {
        "peer.service": service,
        "http.url": endpoint,
        **attributes
    }
    return trace_operation("external.call", **attrs)
