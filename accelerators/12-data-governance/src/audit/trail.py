"""Audit trail for data access."""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional
from dataforge_common.logging import get_logger

logger = get_logger(__name__)


@dataclass
class AuditEvent:
    """An audit trail event."""
    event_id: str
    timestamp: datetime
    user_id: str
    action: str  # read, write, delete, export
    resource_type: str
    resource_id: str
    ip_address: Optional[str] = None
    metadata: Dict = field(default_factory=dict)


class AuditTrail:
    """Track data access for compliance."""

    def __init__(self):
        """Initialize audit trail."""
        self.events: List[AuditEvent] = []

    def log_access(
        self,
        user_id: str,
        action: str,
        resource_type: str,
        resource_id: str,
        ip_address: Optional[str] = None,
        **metadata,
    ) -> AuditEvent:
        """Log a data access event.

        Args:
            user_id: User performing action
            action: Action type
            resource_type: Type of resource
            resource_id: Resource identifier
            ip_address: Optional IP address
            **metadata: Additional metadata

        Returns:
            Created audit event
        """
        event_id = f"audit_{len(self.events) + 1}_{datetime.utcnow().timestamp()}"

        event = AuditEvent(
            event_id=event_id,
            timestamp=datetime.utcnow(),
            user_id=user_id,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            ip_address=ip_address,
            metadata=metadata,
        )

        self.events.append(event)
        logger.info(f"Audit: {user_id} {action} {resource_type}:{resource_id}")

        return event

    def get_events(
        self,
        user_id: Optional[str] = None,
        resource_id: Optional[str] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
    ) -> List[AuditEvent]:
        """Query audit events.

        Args:
            user_id: Filter by user
            resource_id: Filter by resource
            start_time: Filter start time
            end_time: Filter end time

        Returns:
            Filtered audit events
        """
        filtered = self.events

        if user_id:
            filtered = [e for e in filtered if e.user_id == user_id]

        if resource_id:
            filtered = [e for e in filtered if e.resource_id == resource_id]

        if start_time:
            filtered = [e for e in filtered if e.timestamp >= start_time]

        if end_time:
            filtered = [e for e in filtered if e.timestamp <= end_time]

        return filtered
