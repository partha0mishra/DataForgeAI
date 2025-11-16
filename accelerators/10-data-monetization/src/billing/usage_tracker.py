"""Usage tracking and billing."""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List

from dataforge_common.logging import get_logger

logger = get_logger(__name__)


@dataclass
class UsageRecord:
    """API usage record."""
    customer_id: str
    product_id: str
    timestamp: datetime
    requests: int = 1
    cost: float = 0.0


class UsageTracker:
    """Track API usage for billing."""

    def __init__(self):
        """Initialize usage tracker."""
        self.usage_records: List[UsageRecord] = []

    def record_usage(
        self,
        customer_id: str,
        product_id: str,
        requests: int = 1,
        cost: float = 0.0,
    ) -> UsageRecord:
        """Record API usage."""
        record = UsageRecord(
            customer_id=customer_id,
            product_id=product_id,
            timestamp=datetime.utcnow(),
            requests=requests,
            cost=cost,
        )

        self.usage_records.append(record)
        return record

    def get_usage(
        self,
        customer_id: str,
        start_date: datetime,
        end_date: datetime,
    ) -> List[UsageRecord]:
        """Get usage records for a customer."""
        return [
            r for r in self.usage_records
            if r.customer_id == customer_id
            and start_date <= r.timestamp <= end_date
        ]

    def calculate_bill(
        self,
        customer_id: str,
        start_date: datetime,
        end_date: datetime,
    ) -> Dict[str, float]:
        """Calculate bill for a customer."""
        usage = self.get_usage(customer_id, start_date, end_date)

        total_requests = sum(r.requests for r in usage)
        total_cost = sum(r.cost for r in usage)

        return {
            "total_requests": total_requests,
            "total_cost": total_cost,
        }
