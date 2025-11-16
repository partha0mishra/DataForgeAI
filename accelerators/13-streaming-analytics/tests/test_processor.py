"""Tests for stream processor."""

import pytest
from datetime import datetime
from streaming.processor import StreamProcessor, StreamRecord


def test_process_record():
    """Test record processing."""
    processor = StreamProcessor()

    record = StreamRecord(
        timestamp=datetime.utcnow(),
        key="test",
        value=42,
    )

    result = processor.process(record)
    assert result is not None
    assert len(processor.buffer) == 1


def test_transformations():
    """Test transformations."""
    processor = StreamProcessor()

    # Add transformation that doubles the value
    processor.add_transformation(
        lambda r: StreamRecord(r.timestamp, r.key, r.value * 2, r.metadata)
    )

    record = StreamRecord(
        timestamp=datetime.utcnow(),
        key="test",
        value=10,
    )

    result = processor.process(record)
    assert result.value == 20


def test_get_recent():
    """Test getting recent records."""
    processor = StreamProcessor()

    for i in range(10):
        record = StreamRecord(
            timestamp=datetime.utcnow(),
            key=f"key_{i}",
            value=i,
        )
        processor.process(record)

    recent = processor.get_recent(5)
    assert len(recent) == 5
