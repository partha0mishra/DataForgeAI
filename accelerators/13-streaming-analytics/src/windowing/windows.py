"""Windowing operations for streaming data."""

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any, Dict, List
from collections import defaultdict


@dataclass
class WindowResult:
    """Result of windowed aggregation."""
    window_start: datetime
    window_end: datetime
    count: int
    values: List[Any]


class TumblingWindow:
    """Fixed-size non-overlapping windows."""

    def __init__(self, duration_seconds: int):
        """Initialize tumbling window."""
        self.duration = timedelta(seconds=duration_seconds)
        self.windows: Dict[datetime, List[Any]] = defaultdict(list)

    def add(self, timestamp: datetime, value: Any):
        """Add value to window."""
        window_start = self._get_window_start(timestamp)
        self.windows[window_start].append(value)

    def get_window(self, timestamp: datetime) -> WindowResult:
        """Get window for timestamp."""
        window_start = self._get_window_start(timestamp)
        values = self.windows.get(window_start, [])

        return WindowResult(
            window_start=window_start,
            window_end=window_start + self.duration,
            count=len(values),
            values=values,
        )

    def _get_window_start(self, timestamp: datetime) -> datetime:
        """Get window start time for timestamp."""
        epoch = datetime(1970, 1, 1)
        seconds_since_epoch = (timestamp - epoch).total_seconds()
        window_number = int(seconds_since_epoch // self.duration.total_seconds())
        return epoch + timedelta(seconds=window_number * self.duration.total_seconds())
