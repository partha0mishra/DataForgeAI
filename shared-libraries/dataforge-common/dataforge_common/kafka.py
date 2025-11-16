"""Kafka integration for streaming data processing."""

import json
import os
from typing import Any, Callable, Dict, List, Optional
from dataclasses import dataclass
from datetime import datetime

from .logging import get_logger

logger = get_logger(__name__)


@dataclass
class KafkaConfig:
    """Kafka configuration."""

    bootstrap_servers: List[str]
    security_protocol: str = "PLAINTEXT"
    sasl_mechanism: Optional[str] = None
    sasl_username: Optional[str] = None
    sasl_password: Optional[str] = None
    ssl_ca_location: Optional[str] = None
    group_id: str = "dataforge-consumer-group"
    auto_offset_reset: str = "latest"
    enable_auto_commit: bool = True
    max_poll_records: int = 500

    @classmethod
    def from_env(cls) -> "KafkaConfig":
        """Create configuration from environment variables.

        Returns:
            KafkaConfig instance
        """
        bootstrap_servers_str = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")
        bootstrap_servers = [s.strip() for s in bootstrap_servers_str.split(",")]

        return cls(
            bootstrap_servers=bootstrap_servers,
            security_protocol=os.getenv("KAFKA_SECURITY_PROTOCOL", "PLAINTEXT"),
            sasl_mechanism=os.getenv("KAFKA_SASL_MECHANISM"),
            sasl_username=os.getenv("KAFKA_SASL_USERNAME"),
            sasl_password=os.getenv("KAFKA_SASL_PASSWORD"),
            ssl_ca_location=os.getenv("KAFKA_SSL_CA_LOCATION"),
            group_id=os.getenv("KAFKA_GROUP_ID", "dataforge-consumer-group"),
            auto_offset_reset=os.getenv("KAFKA_AUTO_OFFSET_RESET", "latest"),
        )


class KafkaProducer:
    """Kafka message producer."""

    def __init__(self, config: Optional[KafkaConfig] = None):
        """Initialize Kafka producer.

        Args:
            config: Kafka configuration
        """
        self.config = config or KafkaConfig.from_env()

        try:
            from kafka import KafkaProducer as Producer

            producer_config = {
                "bootstrap_servers": self.config.bootstrap_servers,
                "value_serializer": lambda v: json.dumps(v).encode("utf-8"),
                "key_serializer": lambda k: k.encode("utf-8") if k else None,
            }

            # Add authentication if configured
            if self.config.security_protocol != "PLAINTEXT":
                producer_config["security_protocol"] = self.config.security_protocol

            if self.config.sasl_mechanism:
                producer_config["sasl_mechanism"] = self.config.sasl_mechanism
                producer_config["sasl_plain_username"] = self.config.sasl_username
                producer_config["sasl_plain_password"] = self.config.sasl_password

            self.producer = Producer(**producer_config)
            logger.info(f"Kafka producer connected to {self.config.bootstrap_servers}")

        except ImportError:
            raise ImportError(
                "kafka-python required. Install with: pip install kafka-python"
            )
        except Exception as e:
            logger.error(f"Failed to initialize Kafka producer: {e}")
            raise

    def send(
        self,
        topic: str,
        value: Dict[str, Any],
        key: Optional[str] = None,
        partition: Optional[int] = None,
    ) -> None:
        """Send message to Kafka topic.

        Args:
            topic: Topic name
            value: Message value (will be JSON serialized)
            key: Optional message key for partitioning
            partition: Optional explicit partition
        """
        try:
            future = self.producer.send(
                topic=topic,
                value=value,
                key=key,
                partition=partition,
            )

            # Wait for message to be sent
            future.get(timeout=10)

            logger.debug(f"Sent message to topic {topic}: {key}")

        except Exception as e:
            logger.error(f"Failed to send message to Kafka: {e}")
            raise

    def send_batch(
        self,
        topic: str,
        messages: List[Dict[str, Any]],
        key_extractor: Optional[Callable[[Dict], str]] = None,
    ) -> int:
        """Send batch of messages to Kafka topic.

        Args:
            topic: Topic name
            messages: List of messages
            key_extractor: Optional function to extract key from message

        Returns:
            Number of messages sent
        """
        sent = 0

        try:
            for message in messages:
                key = key_extractor(message) if key_extractor else None
                self.send(topic, message, key)
                sent += 1

            # Ensure all messages are sent
            self.producer.flush()

            logger.info(f"Sent {sent} messages to topic {topic}")
            return sent

        except Exception as e:
            logger.error(f"Failed to send batch to Kafka: {e}")
            raise

    def close(self):
        """Close producer and flush pending messages."""
        try:
            self.producer.flush()
            self.producer.close()
            logger.info("Kafka producer closed")
        except Exception as e:
            logger.error(f"Error closing Kafka producer: {e}")


class KafkaConsumer:
    """Kafka message consumer."""

    def __init__(
        self,
        topics: List[str],
        config: Optional[KafkaConfig] = None,
        message_handler: Optional[Callable[[Dict[str, Any]], None]] = None,
    ):
        """Initialize Kafka consumer.

        Args:
            topics: List of topics to consume
            config: Kafka configuration
            message_handler: Optional callback for processing messages
        """
        self.topics = topics
        self.config = config or KafkaConfig.from_env()
        self.message_handler = message_handler

        try:
            from kafka import KafkaConsumer as Consumer

            consumer_config = {
                "bootstrap_servers": self.config.bootstrap_servers,
                "group_id": self.config.group_id,
                "auto_offset_reset": self.config.auto_offset_reset,
                "enable_auto_commit": self.config.enable_auto_commit,
                "max_poll_records": self.config.max_poll_records,
                "value_deserializer": lambda m: json.loads(m.decode("utf-8")),
                "key_deserializer": lambda k: k.decode("utf-8") if k else None,
            }

            # Add authentication if configured
            if self.config.security_protocol != "PLAINTEXT":
                consumer_config["security_protocol"] = self.config.security_protocol

            if self.config.sasl_mechanism:
                consumer_config["sasl_mechanism"] = self.config.sasl_mechanism
                consumer_config["sasl_plain_username"] = self.config.sasl_username
                consumer_config["sasl_plain_password"] = self.config.sasl_password

            self.consumer = Consumer(*topics, **consumer_config)

            logger.info(
                f"Kafka consumer connected to {self.config.bootstrap_servers}, "
                f"subscribed to topics: {topics}"
            )

        except ImportError:
            raise ImportError(
                "kafka-python required. Install with: pip install kafka-python"
            )
        except Exception as e:
            logger.error(f"Failed to initialize Kafka consumer: {e}")
            raise

    def poll(self, timeout_ms: int = 1000, max_records: Optional[int] = None) -> List[Dict[str, Any]]:
        """Poll for messages.

        Args:
            timeout_ms: Timeout in milliseconds
            max_records: Maximum number of records to return

        Returns:
            List of messages
        """
        try:
            messages = []
            records = self.consumer.poll(timeout_ms=timeout_ms, max_records=max_records)

            for topic_partition, msgs in records.items():
                for msg in msgs:
                    message = {
                        "topic": msg.topic,
                        "partition": msg.partition,
                        "offset": msg.offset,
                        "timestamp": datetime.fromtimestamp(msg.timestamp / 1000),
                        "key": msg.key,
                        "value": msg.value,
                    }
                    messages.append(message)

                    # Call message handler if provided
                    if self.message_handler:
                        try:
                            self.message_handler(msg.value)
                        except Exception as e:
                            logger.error(f"Error in message handler: {e}")

            if messages:
                logger.debug(f"Polled {len(messages)} messages")

            return messages

        except Exception as e:
            logger.error(f"Error polling Kafka: {e}")
            raise

    def consume(
        self,
        handler: Callable[[Dict[str, Any]], None],
        max_messages: Optional[int] = None,
    ) -> int:
        """Consume messages and process with handler.

        Args:
            handler: Message processing function
            max_messages: Maximum messages to process (None = infinite)

        Returns:
            Number of messages processed
        """
        processed = 0

        try:
            logger.info(f"Starting message consumption from topics: {self.topics}")

            for message in self.consumer:
                try:
                    handler(message.value)
                    processed += 1

                    if max_messages and processed >= max_messages:
                        logger.info(f"Reached max messages limit: {max_messages}")
                        break

                except Exception as e:
                    logger.error(f"Error processing message: {e}")
                    # Continue processing other messages

            return processed

        except KeyboardInterrupt:
            logger.info("Consumer interrupted by user")
            return processed
        except Exception as e:
            logger.error(f"Error in message consumption: {e}")
            raise

    def commit(self):
        """Manually commit offsets."""
        try:
            self.consumer.commit()
            logger.debug("Committed offsets")
        except Exception as e:
            logger.error(f"Error committing offsets: {e}")

    def close(self):
        """Close consumer."""
        try:
            self.consumer.close()
            logger.info("Kafka consumer closed")
        except Exception as e:
            logger.error(f"Error closing Kafka consumer: {e}")


class StreamProcessor:
    """High-level stream processor using Kafka."""

    def __init__(
        self,
        input_topics: List[str],
        output_topic: str,
        processor: Callable[[Dict[str, Any]], Optional[Dict[str, Any]]],
        config: Optional[KafkaConfig] = None,
    ):
        """Initialize stream processor.

        Args:
            input_topics: Topics to consume from
            output_topic: Topic to produce to
            processor: Function to process messages (return None to filter out)
            config: Kafka configuration
        """
        self.input_topics = input_topics
        self.output_topic = output_topic
        self.processor = processor
        self.config = config or KafkaConfig.from_env()

        self.consumer = KafkaConsumer(input_topics, config=self.config)
        self.producer = KafkaProducer(config=self.config)

        self.processed_count = 0
        self.filtered_count = 0
        self.error_count = 0

    def process_message(self, message: Dict[str, Any]) -> None:
        """Process a single message.

        Args:
            message: Input message
        """
        try:
            # Apply processor
            result = self.processor(message)

            if result is not None:
                # Send to output topic
                self.producer.send(self.output_topic, result)
                self.processed_count += 1
            else:
                # Message was filtered out
                self.filtered_count += 1

        except Exception as e:
            logger.error(f"Error processing message: {e}")
            self.error_count += 1

    def run(self, max_messages: Optional[int] = None):
        """Run stream processor.

        Args:
            max_messages: Maximum messages to process (None = infinite)
        """
        logger.info(
            f"Starting stream processor: {self.input_topics} -> {self.output_topic}"
        )

        try:
            self.consumer.consume(self.process_message, max_messages=max_messages)

        finally:
            self.close()

            logger.info(
                f"Stream processor stopped. "
                f"Processed: {self.processed_count}, "
                f"Filtered: {self.filtered_count}, "
                f"Errors: {self.error_count}"
            )

    def close(self):
        """Close processor."""
        self.consumer.close()
        self.producer.close()


# Global instances
_producer: Optional[KafkaProducer] = None
_config: Optional[KafkaConfig] = None


def get_kafka_producer() -> KafkaProducer:
    """Get global Kafka producer.

    Returns:
        KafkaProducer instance
    """
    global _producer, _config

    if _producer is None:
        _config = KafkaConfig.from_env()
        _producer = KafkaProducer(_config)

    return _producer


def get_kafka_config() -> KafkaConfig:
    """Get global Kafka configuration.

    Returns:
        KafkaConfig instance
    """
    global _config

    if _config is None:
        _config = KafkaConfig.from_env()

    return _config
