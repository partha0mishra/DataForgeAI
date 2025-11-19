#!/usr/bin/env python3
"""
Kafka Mock IoT Event Producer
==============================

Generates realistic IoT device events and publishes them to a Kafka topic.
Simulates multiple devices with varying sensor readings and behaviors.

Features:
    - Configurable event rate (events per second)
    - Realistic sensor data with normal distributions
    - Device lifecycle simulation (battery drain, signal variation)
    - Anomaly injection for testing data quality rules
    - Continuous or limited run modes

Usage:
    # Continuous mode
    python mock_producer.py --bootstrap-servers localhost:9092 --rate 100

    # Generate specific number of events
    python mock_producer.py --events 10000 --rate 50

    # With anomalies for testing
    python mock_producer.py --rate 100 --anomaly-rate 0.05

Author: DataForgeAI Team
Version: 1.0.0
"""

import json
import time
import random
import argparse
import logging
import signal
import sys
from datetime import datetime, timezone
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, asdict
from kafka import KafkaProducer
from kafka.errors import KafkaError
import numpy as np

# ============================================================================
# CONFIGURATION
# ============================================================================

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Device configuration
DEVICE_COUNT = 50
DEVICE_LOCATIONS = [
    {"lat": 37.7749, "lon": -122.4194, "name": "San Francisco"},
    {"lat": 40.7128, "lon": -74.0060, "name": "New York"},
    {"lat": 51.5074, "lon": -0.1278, "name": "London"},
    {"lat": 35.6762, "lon": 139.6503, "name": "Tokyo"},
    {"lat": -33.8688, "lon": 151.2093, "name": "Sydney"}
]

EVENT_TYPES = [
    "heartbeat",
    "sensor_reading",
    "alert",
    "status_update",
    "config_change"
]


# ============================================================================
# DATA MODELS
# ============================================================================

@dataclass
class Device:
    """IoT device model with state tracking."""
    device_id: str
    location_lat: float
    location_lon: float
    location_name: str
    battery_level: float = 100.0
    signal_strength: int = -60
    temperature_baseline: float = 22.0
    humidity_baseline: float = 50.0
    pressure_baseline: float = 1013.25

    def drain_battery(self) -> None:
        """Simulate battery drain over time."""
        # Random drain between 0.001% and 0.01% per event
        drain = random.uniform(0.001, 0.01)
        self.battery_level = max(0.0, self.battery_level - drain)

        # Recharge when battery is low (simulate charging)
        if self.battery_level < 20.0 and random.random() < 0.1:
            self.battery_level = min(100.0, self.battery_level + random.uniform(5, 15))

    def update_signal(self) -> None:
        """Simulate signal strength variation."""
        # Signal typically varies between -50 and -100 dBm
        variation = random.randint(-10, 10)
        self.signal_strength = max(-100, min(-50, self.signal_strength + variation))

    def generate_temperature(self, anomaly: bool = False) -> float:
        """Generate temperature reading."""
        if anomaly:
            # Generate anomalous temperature
            return random.uniform(-60, 200)

        # Normal temperature with slight variation
        variation = np.random.normal(0, 2)
        return round(self.temperature_baseline + variation, 2)

    def generate_humidity(self, anomaly: bool = False) -> float:
        """Generate humidity reading."""
        if anomaly:
            # Generate anomalous humidity
            return random.uniform(-10, 150)

        # Normal humidity with slight variation
        variation = np.random.normal(0, 5)
        humidity = self.humidity_baseline + variation
        return round(max(0, min(100, humidity)), 2)

    def generate_pressure(self) -> float:
        """Generate atmospheric pressure reading."""
        variation = np.random.normal(0, 5)
        return round(self.pressure_baseline + variation, 2)


@dataclass
class IoTEvent:
    """IoT event data structure."""
    device_id: str
    timestamp: str
    temperature: float
    humidity: float
    pressure: float
    battery_level: float
    signal_strength: int
    location_lat: float
    location_lon: float
    event_type: str

    def to_json(self) -> str:
        """Convert event to JSON string."""
        return json.dumps(asdict(self), indent=None)

    def to_dict(self) -> Dict[str, Any]:
        """Convert event to dictionary."""
        return asdict(self)


# ============================================================================
# KAFKA PRODUCER
# ============================================================================

class IoTEventProducer:
    """Kafka producer for IoT events."""

    def __init__(
        self,
        bootstrap_servers: str,
        topic: str,
        num_devices: int = DEVICE_COUNT,
        anomaly_rate: float = 0.0
    ):
        """
        Initialize IoT event producer.

        Args:
            bootstrap_servers: Kafka bootstrap servers
            topic: Kafka topic name
            num_devices: Number of devices to simulate
            anomaly_rate: Probability of generating anomalous data (0.0 to 1.0)
        """
        self.bootstrap_servers = bootstrap_servers
        self.topic = topic
        self.num_devices = num_devices
        self.anomaly_rate = anomaly_rate
        self.running = False
        self.events_produced = 0

        # Initialize Kafka producer
        self.producer = KafkaProducer(
            bootstrap_servers=self.bootstrap_servers,
            value_serializer=lambda v: v.encode('utf-8'),
            key_serializer=lambda k: k.encode('utf-8') if k else None,
            acks='all',
            retries=3,
            max_in_flight_requests_per_connection=1,
            compression_type='gzip'
        )

        # Initialize devices
        self.devices = self._create_devices()

        logger.info(f"Initialized producer with {len(self.devices)} devices")
        logger.info(f"Target topic: {self.topic}")
        logger.info(f"Bootstrap servers: {self.bootstrap_servers}")

    def _create_devices(self) -> List[Device]:
        """Create simulated devices."""
        devices = []

        for i in range(self.num_devices):
            location = random.choice(DEVICE_LOCATIONS)
            device = Device(
                device_id=f"device_{i:04d}",
                location_lat=location["lat"] + random.uniform(-0.1, 0.1),
                location_lon=location["lon"] + random.uniform(-0.1, 0.1),
                location_name=location["name"],
                battery_level=random.uniform(50, 100),
                signal_strength=random.randint(-80, -50),
                temperature_baseline=random.uniform(18, 28),
                humidity_baseline=random.uniform(40, 60)
            )
            devices.append(device)

        return devices

    def _generate_event(self, device: Device) -> IoTEvent:
        """
        Generate a single IoT event for a device.

        Args:
            device: Device to generate event for

        Returns:
            IoTEvent: Generated event
        """
        # Determine if this should be an anomalous event
        is_anomaly = random.random() < self.anomaly_rate

        # Update device state
        device.drain_battery()
        device.update_signal()

        # Generate event
        event = IoTEvent(
            device_id=device.device_id,
            timestamp=datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z",
            temperature=device.generate_temperature(anomaly=is_anomaly),
            humidity=device.generate_humidity(anomaly=is_anomaly),
            pressure=device.generate_pressure(),
            battery_level=round(device.battery_level, 2),
            signal_strength=device.signal_strength,
            location_lat=device.location_lat,
            location_lon=device.location_lon,
            event_type=random.choice(EVENT_TYPES)
        )

        return event

    def _send_event(self, event: IoTEvent) -> None:
        """
        Send event to Kafka topic.

        Args:
            event: Event to send
        """
        try:
            future = self.producer.send(
                self.topic,
                key=event.device_id,
                value=event.to_json()
            )

            # Wait for acknowledgment (optional, can be async for higher throughput)
            record_metadata = future.get(timeout=10)

            self.events_produced += 1

            if self.events_produced % 100 == 0:
                logger.info(
                    f"Produced {self.events_produced} events "
                    f"(latest: partition={record_metadata.partition}, "
                    f"offset={record_metadata.offset})"
                )

        except KafkaError as e:
            logger.error(f"Failed to send event: {e}")
            raise

    def produce_events(
        self,
        rate: float = 10.0,
        max_events: Optional[int] = None,
        duration: Optional[int] = None
    ) -> None:
        """
        Produce events at specified rate.

        Args:
            rate: Events per second
            max_events: Maximum number of events to produce (None for unlimited)
            duration: Duration in seconds (None for unlimited)
        """
        self.running = True
        start_time = time.time()
        event_interval = 1.0 / rate

        logger.info(f"Starting event production at {rate} events/second")
        if max_events:
            logger.info(f"Will produce {max_events} events")
        if duration:
            logger.info(f"Will run for {duration} seconds")

        try:
            while self.running:
                # Check termination conditions
                if max_events and self.events_produced >= max_events:
                    logger.info(f"Reached max events limit: {max_events}")
                    break

                if duration and (time.time() - start_time) >= duration:
                    logger.info(f"Reached duration limit: {duration} seconds")
                    break

                # Generate and send event
                device = random.choice(self.devices)
                event = self._generate_event(device)
                self._send_event(event)

                # Sleep to maintain target rate
                time.sleep(event_interval)

        except KeyboardInterrupt:
            logger.info("Received interrupt signal, stopping...")
        finally:
            self.stop()

    def stop(self) -> None:
        """Stop the producer and clean up."""
        self.running = False
        logger.info("Flushing remaining messages...")
        self.producer.flush()
        self.producer.close()
        logger.info(f"Producer stopped. Total events produced: {self.events_produced}")


# ============================================================================
# MAIN
# ============================================================================

def signal_handler(signum, frame):
    """Handle interrupt signals."""
    logger.info("Received signal to terminate")
    sys.exit(0)


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Generate and publish mock IoT events to Kafka"
    )

    parser.add_argument(
        "--bootstrap-servers",
        type=str,
        default="localhost:9092",
        help="Kafka bootstrap servers (default: localhost:9092)"
    )

    parser.add_argument(
        "--topic",
        type=str,
        default="iot_events",
        help="Kafka topic name (default: iot_events)"
    )

    parser.add_argument(
        "--rate",
        type=float,
        default=10.0,
        help="Events per second (default: 10)"
    )

    parser.add_argument(
        "--events",
        type=int,
        default=None,
        help="Total number of events to produce (default: unlimited)"
    )

    parser.add_argument(
        "--duration",
        type=int,
        default=None,
        help="Duration in seconds (default: unlimited)"
    )

    parser.add_argument(
        "--devices",
        type=int,
        default=DEVICE_COUNT,
        help=f"Number of devices to simulate (default: {DEVICE_COUNT})"
    )

    parser.add_argument(
        "--anomaly-rate",
        type=float,
        default=0.0,
        help="Probability of generating anomalous data, 0.0-1.0 (default: 0.0)"
    )

    args = parser.parse_args()

    # Set up signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    # Create and run producer
    producer = IoTEventProducer(
        bootstrap_servers=args.bootstrap_servers,
        topic=args.topic,
        num_devices=args.devices,
        anomaly_rate=args.anomaly_rate
    )

    producer.produce_events(
        rate=args.rate,
        max_events=args.events,
        duration=args.duration
    )


if __name__ == "__main__":
    main()
