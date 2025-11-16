"""Tests for monitoring module."""

import pytest
from dataforge_common.monitoring import MetricsCollector, get_metrics_collector


def test_increment_counter():
    """Test counter incrementation."""
    collector = MetricsCollector()
    collector.increment_counter("requests", 5)
    collector.increment_counter("requests", 3)

    metrics = collector.get_metrics()
    assert metrics["counters"]["requests"] == 8


def test_set_gauge():
    """Test gauge setting."""
    collector = MetricsCollector()
    collector.set_gauge("temperature", 23.5)

    metrics = collector.get_metrics()
    assert metrics["gauges"]["temperature"] == 23.5


def test_record_histogram():
    """Test histogram recording."""
    collector = MetricsCollector()
    collector.record_histogram("latency", 100)
    collector.record_histogram("latency", 200)
    collector.record_histogram("latency", 300)

    metrics = collector.get_metrics()
    assert metrics["histograms"]["latency"]["count"] == 3
    assert metrics["histograms"]["latency"]["avg"] == 200
    assert metrics["histograms"]["latency"]["min"] == 100
    assert metrics["histograms"]["latency"]["max"] == 300


def test_timer():
    """Test timer functionality."""
    collector = MetricsCollector()
    timer_id = collector.start_timer("operation")
    assert timer_id in collector.timers

    collector.stop_timer(timer_id, "operation_duration")
    assert timer_id not in collector.timers
    assert "operation_duration" in collector.histograms


def test_metrics_with_labels():
    """Test metrics with labels."""
    collector = MetricsCollector()
    collector.increment_counter("requests", labels={"method": "GET"})
    collector.increment_counter("requests", labels={"method": "POST"})

    metrics = collector.get_metrics()
    assert "requests{method=GET}" in metrics["counters"]
    assert "requests{method=POST}" in metrics["counters"]
