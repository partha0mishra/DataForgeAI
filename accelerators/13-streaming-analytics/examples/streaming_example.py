"""Example: Real-time streaming analytics."""

import sys
from pathlib import Path
import time
from datetime import datetime, timedelta
import random

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from streaming.processor import StreamProcessor, StreamRecord
from windowing.windows import TumblingWindow


def main():
    """Run streaming analytics example."""
    print("=" * 80)
    print(" DataForge Streaming Analytics - Example")
    print("=" * 80)

    # Initialize components
    processor = StreamProcessor()
    window = TumblingWindow(duration_seconds=5)  # 5-second windows

    print("\n1. Simulating Real-time Stream...")
    print("   Generating 100 events over 10 seconds...")

    # Simulate stream
    for i in range(100):
        timestamp = datetime.utcnow()
        value = random.uniform(10, 100)

        record = StreamRecord(
            timestamp=timestamp,
            key=f"sensor_{i % 5}",
            value=value,
        )

        processor.process(record)
        window.add(timestamp, value)

        if (i + 1) % 10 == 0:
            print(f"   Processed {i + 1} events...")

        time.sleep(0.1)  # 100ms between events

    print(f"\n✓ Processed {len(processor.buffer)} events")

    # Window analysis
    print("\n2. Window Analysis (5-second tumbling windows):")
    current_window = window.get_window(datetime.utcnow())
    print(f"   Current Window: {current_window.window_start.strftime('%H:%M:%S')} - {current_window.window_end.strftime('%H:%M:%S')}")
    print(f"   Events: {current_window.count}")
    if current_window.values:
        print(f"   Sum: {sum(current_window.values):.2f}")
        print(f"   Avg: {sum(current_window.values) / len(current_window.values):.2f}")
        print(f"   Min: {min(current_window.values):.2f}")
        print(f"   Max: {max(current_window.values):.2f}")

    # Recent events
    print("\n3. Recent Events (last 10):")
    recent = processor.get_recent(10)
    for r in recent:
        print(f"   [{r.timestamp.strftime('%H:%M:%S')}] {r.key}: {r.value:.2f}")

    print("\n" + "=" * 80)
    print(" Streaming Example Complete!")
    print("=" * 80)


if __name__ == "__main__":
    main()
