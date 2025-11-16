"""Data quality monitoring."""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List
import pandas as pd
from dataforge_common.logging import get_logger

logger = get_logger(__name__)


@dataclass
class QualityMetric:
    """Quality metric snapshot."""
    timestamp: datetime
    table: str
    metric_name: str
    value: float
    threshold: float
    passed: bool


class QualityMonitor:
    """Monitor data quality over time."""

    def __init__(self):
        """Initialize monitor."""
        self.metrics: List[QualityMetric] = []

    def check_freshness(
        self,
        table: str,
        last_update: datetime,
        max_age_hours: float = 24,
    ) -> QualityMetric:
        """Check data freshness."""
        age_hours = (datetime.utcnow() - last_update).total_seconds() / 3600
        passed = age_hours <= max_age_hours

        metric = QualityMetric(
            timestamp=datetime.utcnow(),
            table=table,
            metric_name="freshness_hours",
            value=age_hours,
            threshold=max_age_hours,
            passed=passed,
        )

        self.metrics.append(metric)
        logger.info(f"{table} freshness: {age_hours:.2f}h (threshold: {max_age_hours}h) - {'PASS' if passed else 'FAIL'}")

        return metric

    def check_completeness(
        self,
        table: str,
        df: pd.DataFrame,
        min_completeness: float = 0.95,
    ) -> QualityMetric:
        """Check data completeness (non-null ratio)."""
        completeness = 1.0 - (df.isnull().sum().sum() / (len(df) * len(df.columns)))
        passed = completeness >= min_completeness

        metric = QualityMetric(
            timestamp=datetime.utcnow(),
            table=table,
            metric_name="completeness",
            value=completeness,
            threshold=min_completeness,
            passed=passed,
        )

        self.metrics.append(metric)
        logger.info(f"{table} completeness: {completeness:.2%} (threshold: {min_completeness:.2%}) - {'PASS' if passed else 'FAIL'}")

        return metric

    def get_metrics(
        self,
        table: Optional[str] = None,
        limit: int = 100,
    ) -> List[QualityMetric]:
        """Get quality metrics."""
        metrics = self.metrics

        if table:
            metrics = [m for m in metrics if m.table == table]

        return metrics[-limit:]
