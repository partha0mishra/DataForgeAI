"""Real-time stream processing."""

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any, Callable, Dict, List, Optional
from collections import deque
from dataforge_common.logging import get_logger

logger = get_logger(__name__)


@dataclass
class StreamRecord:
    """A record in the stream."""
    timestamp: datetime
    key: str
    value: Any
    metadata: Dict = field(default_factory=dict)


class StreamProcessor:
    """Process streaming data."""

    def __init__(self, buffer_size: int = 10000):
        """Initialize stream processor."""
        self.buffer = deque(maxlen=buffer_size)
        self.transformations: List[Callable] = []
        self.sinks: List[Callable] = []

    def process(self, record: StreamRecord) -> Optional[StreamRecord]:
        """Process a single record."""
        current = record

        # Apply transformations
        for transform in self.transformations:
            current = transform(current)
            if current is None:
                return None

        # Add to buffer
        self.buffer.append(current)

        # Send to sinks
        for sink in self.sinks:
            sink(current)

        return current

    def add_transformation(self, func: Callable):
        """Add transformation function."""
        self.transformations.append(func)

    def add_sink(self, func: Callable):
        """Add sink function."""
        self.sinks.append(func)

    def get_recent(self, n: int = 100) -> List[StreamRecord]:
        """Get recent records."""
        return list(self.buffer)[-n:]
