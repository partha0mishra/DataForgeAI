"""Kafka-based stream processing."""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional
from collections import defaultdict

from dataforge_common.logging import get_logger

logger = get_logger(__name__)


@dataclass
class StreamRecord:
    """A record in the stream."""
    timestamp: datetime
    key: str
    value: Any
    metadata: Dict = field(default_factory=dict)


class KafkaStreamProcessor:
    """Process streaming data using Kafka."""

    def __init__(
        self,
        input_topics: List[str],
        output_topic: str,
        consumer_group: str = "dataforge-stream-processor",
        enable_kafka: bool = True,
    ):
        """Initialize Kafka stream processor.

        Args:
            input_topics: Topics to consume from
            output_topic: Topic to produce to
            consumer_group: Consumer group ID
            enable_kafka: Whether to use Kafka (False = in-memory mode)
        """
        self.input_topics = input_topics
        self.output_topic = output_topic
        self.consumer_group = consumer_group
        self.enable_kafka = enable_kafka

        self.transformations: List[Callable] = []
        self.metrics = defaultdict(int)

        # Try to initialize Kafka components
        if self.enable_kafka:
            try:
                from dataforge_common.kafka import KafkaProducer, KafkaConsumer, KafkaConfig

                config = KafkaConfig.from_env()
                config.group_id = consumer_group

                self.producer = KafkaProducer(config)
                self.consumer = KafkaConsumer(input_topics, config)

                logger.info(f"Kafka stream processor initialized: {input_topics} -> {output_topic}")

            except Exception as e:
                logger.warning(f"Failed to initialize Kafka, falling back to in-memory mode: {e}")
                self.enable_kafka = False

        # Fallback to in-memory mode
        if not self.enable_kafka:
            from collections import deque
            self.in_memory_buffer = deque(maxlen=10000)
            logger.info("Running in in-memory mode (Kafka not available)")

    def add_transformation(self, func: Callable[[StreamRecord], Optional[StreamRecord]]):
        """Add transformation function.

        Args:
            func: Transformation function (return None to filter out record)
        """
        self.transformations.append(func)

    def process_record(self, record: StreamRecord) -> Optional[StreamRecord]:
        """Process a single record through transformations.

        Args:
            record: Input record

        Returns:
            Processed record or None if filtered out
        """
        current = record
        self.metrics["received"] += 1

        try:
            # Apply transformations
            for transform in self.transformations:
                current = transform(current)
                if current is None:
                    self.metrics["filtered"] += 1
                    return None

            self.metrics["processed"] += 1
            return current

        except Exception as e:
            logger.error(f"Error processing record: {e}")
            self.metrics["errors"] += 1
            return None

    def send_output(self, record: StreamRecord) -> None:
        """Send processed record to output.

        Args:
            record: Processed record
        """
        if self.enable_kafka:
            try:
                message = {
                    "timestamp": record.timestamp.isoformat(),
                    "key": record.key,
                    "value": record.value,
                    "metadata": record.metadata,
                }
                self.producer.send(self.output_topic, message, key=record.key)
                self.metrics["output"] += 1
            except Exception as e:
                logger.error(f"Error sending to Kafka: {e}")
                self.metrics["send_errors"] += 1
        else:
            # In-memory mode
            self.in_memory_buffer.append(record)
            self.metrics["output"] += 1

    def run(self, max_messages: Optional[int] = None):
        """Run stream processor.

        Args:
            max_messages: Maximum messages to process (None = infinite)
        """
        if not self.enable_kafka:
            logger.warning("Cannot run in Kafka mode - Kafka not available")
            return

        logger.info(f"Starting stream processor (max messages: {max_messages or 'unlimited'})")

        processed = 0

        try:
            for message in self.consumer.consumer:
                # Convert Kafka message to StreamRecord
                record = StreamRecord(
                    timestamp=datetime.fromtimestamp(message.timestamp / 1000),
                    key=message.key or "",
                    value=message.value,
                    metadata={
                        "topic": message.topic,
                        "partition": message.partition,
                        "offset": message.offset,
                    },
                )

                # Process record
                result = self.process_record(record)

                # Send to output if not filtered
                if result is not None:
                    self.send_output(result)

                processed += 1

                if processed % 1000 == 0:
                    logger.info(f"Processed {processed} messages. Metrics: {dict(self.metrics)}")

                if max_messages and processed >= max_messages:
                    logger.info(f"Reached max messages limit: {max_messages}")
                    break

        except KeyboardInterrupt:
            logger.info("Stream processor interrupted by user")

        finally:
            logger.info(f"Stream processor stopped. Final metrics: {dict(self.metrics)}")
            self.close()

    def process_batch_in_memory(self, records: List[StreamRecord]) -> List[StreamRecord]:
        """Process batch of records in memory mode.

        Args:
            records: List of input records

        Returns:
            List of processed records
        """
        results = []

        for record in records:
            result = self.process_record(record)
            if result is not None:
                results.append(result)
                if not self.enable_kafka:
                    self.in_memory_buffer.append(result)

        return results

    def get_metrics(self) -> Dict[str, int]:
        """Get processing metrics.

        Returns:
            Dictionary of metrics
        """
        return dict(self.metrics)

    def reset_metrics(self):
        """Reset metrics counters."""
        self.metrics.clear()

    def close(self):
        """Close processor and cleanup resources."""
        if self.enable_kafka:
            try:
                self.consumer.close()
                self.producer.close()
                logger.info("Kafka connections closed")
            except Exception as e:
                logger.error(f"Error closing Kafka connections: {e}")


# Example transformations
def filter_by_threshold(threshold: float) -> Callable:
    """Create filter transformation based on value threshold.

    Args:
        threshold: Minimum value threshold

    Returns:
        Filter function
    """
    def transform(record: StreamRecord) -> Optional[StreamRecord]:
        if isinstance(record.value, (int, float)):
            if record.value < threshold:
                return None
        return record

    return transform


def enrich_with_metadata(metadata: Dict) -> Callable:
    """Create enrichment transformation.

    Args:
        metadata: Metadata to add to each record

    Returns:
        Enrichment function
    """
    def transform(record: StreamRecord) -> StreamRecord:
        record.metadata.update(metadata)
        return record

    return transform


def aggregate_by_key(window_size: int = 100) -> Callable:
    """Create aggregation transformation.

    Args:
        window_size: Number of records to aggregate

    Returns:
        Aggregation function
    """
    buffer = {}

    def transform(record: StreamRecord) -> Optional[StreamRecord]:
        key = record.key

        if key not in buffer:
            buffer[key] = []

        buffer[key].append(record.value)

        # Emit aggregated result when window is full
        if len(buffer[key]) >= window_size:
            aggregated_value = sum(buffer[key]) / len(buffer[key])
            buffer[key].clear()

            return StreamRecord(
                timestamp=datetime.utcnow(),
                key=key,
                value=aggregated_value,
                metadata={"type": "aggregated", "window_size": window_size},
            )

        return None

    return transform
