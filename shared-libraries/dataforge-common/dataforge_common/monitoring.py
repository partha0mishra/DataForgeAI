"""Monitoring and metrics utilities."""

from typing import Dict, Any, Optional
from datetime import datetime
from collections import defaultdict
import time


class MetricsCollector:
    """Collect and expose application metrics."""

    def __init__(self):
        """Initialize metrics collector."""
        self.counters: Dict[str, int] = defaultdict(int)
        self.gauges: Dict[str, float] = {}
        self.histograms: Dict[str, list] = defaultdict(list)
        self.timers: Dict[str, float] = {}

    def increment_counter(self, name: str, value: int = 1, labels: Optional[Dict[str, str]] = None):
        """Increment a counter metric.

        Args:
            name: Metric name
            value: Increment value
            labels: Optional metric labels
        """
        key = self._make_key(name, labels)
        self.counters[key] += value

    def set_gauge(self, name: str, value: float, labels: Optional[Dict[str, str]] = None):
        """Set a gauge metric.

        Args:
            name: Metric name
            value: Gauge value
            labels: Optional metric labels
        """
        key = self._make_key(name, labels)
        self.gauges[key] = value

    def record_histogram(self, name: str, value: float, labels: Optional[Dict[str, str]] = None):
        """Record a histogram value.

        Args:
            name: Metric name
            value: Value to record
            labels: Optional metric labels
        """
        key = self._make_key(name, labels)
        self.histograms[key].append(value)

    def start_timer(self, name: str) -> str:
        """Start a timer.

        Args:
            name: Timer name

        Returns:
            Timer ID
        """
        timer_id = f"{name}_{time.time()}"
        self.timers[timer_id] = time.time()
        return timer_id

    def stop_timer(self, timer_id: str, metric_name: str, labels: Optional[Dict[str, str]] = None):
        """Stop a timer and record duration.

        Args:
            timer_id: Timer ID from start_timer
            metric_name: Metric name to record duration
            labels: Optional metric labels
        """
        if timer_id in self.timers:
            duration = time.time() - self.timers[timer_id]
            self.record_histogram(metric_name, duration, labels)
            del self.timers[timer_id]

    def get_metrics(self) -> Dict[str, Any]:
        """Get all metrics.

        Returns:
            Dictionary of all metrics
        """
        metrics = {
            "counters": dict(self.counters),
            "gauges": dict(self.gauges),
            "histograms": {
                name: {
                    "count": len(values),
                    "sum": sum(values),
                    "avg": sum(values) / len(values) if values else 0,
                    "min": min(values) if values else 0,
                    "max": max(values) if values else 0,
                }
                for name, values in self.histograms.items()
            },
            "timestamp": datetime.utcnow().isoformat(),
        }
        return metrics

    def reset(self):
        """Reset all metrics."""
        self.counters.clear()
        self.gauges.clear()
        self.histograms.clear()
        self.timers.clear()

    def _make_key(self, name: str, labels: Optional[Dict[str, str]]) -> str:
        """Make metric key with labels.

        Args:
            name: Metric name
            labels: Optional labels

        Returns:
            Metric key
        """
        if not labels:
            return name

        label_str = ",".join(f"{k}={v}" for k, v in sorted(labels.items()))
        return f"{name}{{{label_str}}}"


# Global metrics collector
_metrics_collector = MetricsCollector()


def get_metrics_collector() -> MetricsCollector:
    """Get global metrics collector.

    Returns:
        Global metrics collector instance
    """
    return _metrics_collector
