"""FastAPI REST API for Streaming Analytics."""

from fastapi import FastAPI, HTTPException, Request, Depends
from pydantic import BaseModel
from datetime import datetime
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from streaming.processor import StreamProcessor, StreamRecord
from streaming.kafka_processor import KafkaStreamProcessor
from windowing.windows import TumblingWindow

# Import authentication
try:
    from dataforge_common import (
        get_current_user,
        get_optional_user,
        require_roles,
        create_auth_router,
        User,
    )
    AUTH_ENABLED = True
except ImportError:
    print("Warning: dataforge-common not installed. Authentication disabled.")
    AUTH_ENABLED = False


app = FastAPI(title="DataForge Streaming Analytics", version="0.1.0", description="DataForge AI Accelerator")
# Include authentication router if available
if AUTH_ENABLED:
    auth_router = create_auth_router()
    app.include_router(auth_router)


processor = StreamProcessor()
window = TumblingWindow(duration_seconds=60)


class StreamEvent(BaseModel):
    """Streaming event."""
    key: str
    value: float
    timestamp: Optional[str] = None


@app.get("/health")
async def health_check():
    return {"status": "healthy"}


@app.post("/stream/ingest")
async def ingest_event(event: StreamEvent):
    """Ingest streaming event."""
    timestamp = datetime.fromisoformat(event.timestamp) if event.timestamp else datetime.utcnow()

    record = StreamRecord(
        timestamp=timestamp,
        key=event.key,
        value=event.value,
    )

    processor.process(record)
    window.add(timestamp, event.value)

    return {"status": "ingested", "timestamp": timestamp.isoformat()}


@app.get("/stream/recent")
async def get_recent(limit: int = 100):
    """Get recent records."""
    recent = processor.get_recent(limit)

    return {
        "count": len(recent),
        "records": [
            {
                "timestamp": r.timestamp.isoformat(),
                "key": r.key,
                "value": r.value,
            }
            for r in recent
        ],
    }


@app.get("/windows/current")
async def get_current_window():
    """Get current window stats."""
    result = window.get_window(datetime.utcnow())

    return {
        "window_start": result.window_start.isoformat(),
        "window_end": result.window_end.isoformat(),
        "count": result.count,
        "sum": sum(result.values) if result.values else 0,
        "avg": sum(result.values) / len(result.values) if result.values else 0,
    }


# Kafka Streaming Endpoints
kafka_processor = None


class KafkaStreamConfig(BaseModel):
    """Kafka stream configuration."""
    input_topics: list[str]
    output_topic: str
    consumer_group: str = "dataforge-stream-processor"


class KafkaTransformationConfig(BaseModel):
    """Kafka transformation configuration."""
    type: str  # filter, enrich, aggregate
    params: dict = {}


@app.post("/kafka/stream/create")
async def create_kafka_stream(config: KafkaStreamConfig):
    """Create Kafka stream processor."""
    global kafka_processor

    try:
        kafka_processor = KafkaStreamProcessor(
            input_topics=config.input_topics,
            output_topic=config.output_topic,
            consumer_group=config.consumer_group,
            enable_kafka=True,
        )

        return {
            "status": "created",
            "input_topics": config.input_topics,
            "output_topic": config.output_topic,
            "mode": "kafka" if kafka_processor.enable_kafka else "in-memory",
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/kafka/stream/transform")
async def add_transformation(config: KafkaTransformationConfig):
    """Add transformation to stream processor."""
    if kafka_processor is None:
        raise HTTPException(status_code=400, detail="Stream processor not created")

    try:
        from streaming.kafka_processor import filter_by_threshold, enrich_with_metadata, aggregate_by_key

        if config.type == "filter":
            threshold = config.params.get("threshold", 0)
            kafka_processor.add_transformation(filter_by_threshold(threshold))

        elif config.type == "enrich":
            metadata = config.params.get("metadata", {})
            kafka_processor.add_transformation(enrich_with_metadata(metadata))

        elif config.type == "aggregate":
            window_size = config.params.get("window_size", 100)
            kafka_processor.add_transformation(aggregate_by_key(window_size))

        else:
            raise HTTPException(status_code=400, detail=f"Unknown transformation type: {config.type}")

        return {"status": "added", "transformation": config.type}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/kafka/stream/metrics")
async def get_stream_metrics():
    """Get stream processor metrics."""
    if kafka_processor is None:
        raise HTTPException(status_code=400, detail="Stream processor not created")

    return {
        "metrics": kafka_processor.get_metrics(),
        "mode": "kafka" if kafka_processor.enable_kafka else "in-memory",
    }


@app.post("/kafka/stream/stop")
async def stop_stream():
    """Stop stream processor."""
    global kafka_processor

    if kafka_processor is None:
        raise HTTPException(status_code=400, detail="Stream processor not created")

    try:
        kafka_processor.close()
        kafka_processor = None

        return {"status": "stopped"}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8013)
