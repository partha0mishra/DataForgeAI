"""FastAPI REST API for Streaming Analytics."""

from fastapi import FastAPI, HTTPException, Request, Depends
from pydantic import BaseModel
from datetime import datetime
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__, Request, Depends).parent.parent))

from streaming.processor import StreamProcessor, StreamRecord
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


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8013)
