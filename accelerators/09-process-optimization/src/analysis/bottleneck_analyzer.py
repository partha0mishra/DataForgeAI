"""Bottleneck detection and analysis."""

import pandas as pd
import numpy as np
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from dataforge_common.logging import get_logger

logger = get_logger(__name__)


@dataclass
class Bottleneck:
    """A detected bottleneck in the process."""

    activity: str
    bottleneck_type: str  # duration, frequency, resource, waiting
    severity: float  # 0-1, higher is more severe
    impact: str
    evidence: Dict[str, Any]
    recommendations: List[str] = field(default_factory=list)


@dataclass
class BottleneckAnalysis:
    """Complete bottleneck analysis."""

    bottlenecks: List[Bottleneck]
    total_bottlenecks: int
    high_severity_count: int
    medium_severity_count: int
    low_severity_count: int
    overall_health_score: float  # 0-100
    metadata: Dict[str, Any] = field(default_factory=dict)


class BottleneckAnalyzer:
    """Analyze processes to detect bottlenecks."""

    def __init__(
        self,
        duration_threshold_percentile: float = 0.75,
        frequency_threshold_std: float = 2.0,
        waiting_time_threshold_hours: float = 24.0,
    ):
        """Initialize bottleneck analyzer.

        Args:
            duration_threshold_percentile: Percentile for duration outliers
            frequency_threshold_std: Standard deviations for frequency outliers
            waiting_time_threshold_hours: Threshold for waiting time bottlenecks
        """
        self.duration_threshold_percentile = duration_threshold_percentile
        self.frequency_threshold_std = frequency_threshold_std
        self.waiting_time_threshold_hours = waiting_time_threshold_hours

    def analyze(
        self,
        discovered_process,
        event_log: pd.DataFrame,
        case_id_column: str = "case_id",
        activity_column: str = "activity",
        timestamp_column: str = "timestamp",
        resource_column: Optional[str] = None,
    ) -> BottleneckAnalysis:
        """Analyze process for bottlenecks.

        Args:
            discovered_process: Discovered process from ProcessMiner
            event_log: Event log DataFrame
            case_id_column: Column name for case ID
            activity_column: Column name for activity
            timestamp_column: Column name for timestamp
            resource_column: Optional column name for resource

        Returns:
            Bottleneck analysis results
        """
        logger.info("Analyzing process for bottlenecks")

        bottlenecks = []

        # Detect duration bottlenecks
        duration_bottlenecks = self._detect_duration_bottlenecks(discovered_process)
        bottlenecks.extend(duration_bottlenecks)

        # Detect frequency bottlenecks
        frequency_bottlenecks = self._detect_frequency_bottlenecks(discovered_process)
        bottlenecks.extend(frequency_bottlenecks)

        # Detect waiting time bottlenecks
        waiting_bottlenecks = self._detect_waiting_bottlenecks(
            event_log,
            case_id_column,
            activity_column,
            timestamp_column,
        )
        bottlenecks.extend(waiting_bottlenecks)

        # Detect resource bottlenecks
        if resource_column:
            resource_bottlenecks = self._detect_resource_bottlenecks(
                event_log,
                activity_column,
                resource_column,
            )
            bottlenecks.extend(resource_bottlenecks)

        # Detect path bottlenecks
        path_bottlenecks = self._detect_path_bottlenecks(discovered_process)
        bottlenecks.extend(path_bottlenecks)

        # Sort by severity
        bottlenecks.sort(key=lambda x: x.severity, reverse=True)

        # Count by severity
        high_severity = sum(1 for b in bottlenecks if b.severity >= 0.7)
        medium_severity = sum(1 for b in bottlenecks if 0.4 <= b.severity < 0.7)
        low_severity = sum(1 for b in bottlenecks if b.severity < 0.4)

        # Calculate health score (100 - weighted severity)
        if bottlenecks:
            total_severity = sum(b.severity for b in bottlenecks)
            health_score = max(0, 100 - (total_severity / len(bottlenecks) * 100))
        else:
            health_score = 100.0

        analysis = BottleneckAnalysis(
            bottlenecks=bottlenecks,
            total_bottlenecks=len(bottlenecks),
            high_severity_count=high_severity,
            medium_severity_count=medium_severity,
            low_severity_count=low_severity,
            overall_health_score=health_score,
        )

        logger.info(
            f"Found {len(bottlenecks)} bottlenecks "
            f"({high_severity} high, {medium_severity} medium, {low_severity} low)"
        )

        return analysis

    def _detect_duration_bottlenecks(self, discovered_process) -> List[Bottleneck]:
        """Detect activities with excessive duration."""
        bottlenecks = []

        # Get duration statistics
        durations = [step.avg_duration for step in discovered_process.steps.values()]

        if not durations:
            return bottlenecks

        threshold = np.percentile(durations, self.duration_threshold_percentile * 100)

        for activity, step in discovered_process.steps.items():
            if step.avg_duration > threshold and step.avg_duration > 1.0:  # At least 1 hour
                # Calculate severity based on how much it exceeds threshold
                severity = min(step.avg_duration / (threshold * 2), 1.0)

                bottleneck = Bottleneck(
                    activity=activity,
                    bottleneck_type="duration",
                    severity=severity,
                    impact=f"Average duration of {step.avg_duration:.2f} hours is significantly higher than typical",
                    evidence={
                        "avg_duration_hours": step.avg_duration,
                        "min_duration_hours": step.min_duration,
                        "max_duration_hours": step.max_duration,
                        "threshold_hours": threshold,
                        "excess_percentage": ((step.avg_duration - threshold) / threshold) * 100,
                    },
                    recommendations=[
                        "Investigate why this activity takes longer than others",
                        "Consider parallelization or automation",
                        "Check if resources are adequately allocated",
                        "Look for unnecessary waiting or approval steps",
                    ],
                )
                bottlenecks.append(bottleneck)

        return bottlenecks

    def _detect_frequency_bottlenecks(self, discovered_process) -> List[Bottleneck]:
        """Detect activities with unusual frequency."""
        bottlenecks = []

        # Get frequency statistics
        counts = [step.count for step in discovered_process.steps.values()]

        if not counts:
            return bottlenecks

        mean_count = np.mean(counts)
        std_count = np.std(counts)

        if std_count == 0:
            return bottlenecks

        for activity, step in discovered_process.steps.items():
            # Check for both high and low frequency outliers
            z_score = abs(step.count - mean_count) / std_count

            if z_score > self.frequency_threshold_std:
                if step.count > mean_count:
                    severity = min(z_score / 5, 1.0)

                    bottleneck = Bottleneck(
                        activity=activity,
                        bottleneck_type="frequency",
                        severity=severity,
                        impact=f"Activity occurs {step.count} times, much higher than average ({mean_count:.0f})",
                        evidence={
                            "count": step.count,
                            "average_count": mean_count,
                            "z_score": z_score,
                            "excess_percentage": ((step.count - mean_count) / mean_count) * 100,
                        },
                        recommendations=[
                            "Investigate why this activity is repeated frequently",
                            "Look for rework or loops in the process",
                            "Consider consolidating or optimizing this step",
                            "Check if this indicates a quality issue upstream",
                        ],
                    )
                    bottlenecks.append(bottleneck)

        return bottlenecks

    def _detect_waiting_bottlenecks(
        self,
        event_log: pd.DataFrame,
        case_id_column: str,
        activity_column: str,
        timestamp_column: str,
    ) -> List[Bottleneck]:
        """Detect excessive waiting times between activities."""
        bottlenecks = []

        # Ensure timestamp is datetime
        if not pd.api.types.is_datetime64_any_dtype(event_log[timestamp_column]):
            event_log = event_log.copy()
            event_log[timestamp_column] = pd.to_datetime(event_log[timestamp_column])

        # Calculate waiting times
        waiting_times = {}

        for case_id in event_log[case_id_column].unique():
            case_events = event_log[event_log[case_id_column] == case_id].sort_values(
                timestamp_column
            )

            for i in range(len(case_events) - 1):
                current_activity = case_events.iloc[i][activity_column]
                next_activity = case_events.iloc[i + 1][activity_column]

                waiting_time = (
                    case_events.iloc[i + 1][timestamp_column]
                    - case_events.iloc[i][timestamp_column]
                ).total_seconds() / 3600  # Hours

                transition = f"{current_activity} → {next_activity}"

                if transition not in waiting_times:
                    waiting_times[transition] = []

                waiting_times[transition].append(waiting_time)

        # Identify bottlenecks
        for transition, times in waiting_times.items():
            avg_waiting = np.mean(times)

            if avg_waiting > self.waiting_time_threshold_hours:
                severity = min(avg_waiting / (self.waiting_time_threshold_hours * 3), 1.0)

                bottleneck = Bottleneck(
                    activity=transition,
                    bottleneck_type="waiting",
                    severity=severity,
                    impact=f"Average waiting time of {avg_waiting:.2f} hours between activities",
                    evidence={
                        "avg_waiting_hours": avg_waiting,
                        "min_waiting_hours": min(times),
                        "max_waiting_hours": max(times),
                        "threshold_hours": self.waiting_time_threshold_hours,
                        "occurrences": len(times),
                    },
                    recommendations=[
                        "Reduce waiting time between these activities",
                        "Implement automatic handoff mechanisms",
                        "Add notifications or alerts for pending items",
                        "Consider process redesign to eliminate waiting",
                    ],
                )
                bottlenecks.append(bottleneck)

        return bottlenecks

    def _detect_resource_bottlenecks(
        self,
        event_log: pd.DataFrame,
        activity_column: str,
        resource_column: str,
    ) -> List[Bottleneck]:
        """Detect resource-related bottlenecks."""
        bottlenecks = []

        # Analyze resource workload
        resource_counts = event_log.groupby(resource_column)[activity_column].count()

        if len(resource_counts) == 0:
            return bottlenecks

        mean_workload = resource_counts.mean()
        std_workload = resource_counts.std()

        if std_workload == 0:
            return bottlenecks

        # Find overloaded resources
        for resource, workload in resource_counts.items():
            z_score = (workload - mean_workload) / std_workload

            if z_score > 2.0:  # Significantly overloaded
                severity = min(z_score / 4, 1.0)

                bottleneck = Bottleneck(
                    activity=f"Resource: {resource}",
                    bottleneck_type="resource",
                    severity=severity,
                    impact=f"Resource handles {workload} events, {((workload/mean_workload - 1) * 100):.0f}% above average",
                    evidence={
                        "workload": int(workload),
                        "average_workload": mean_workload,
                        "z_score": z_score,
                    },
                    recommendations=[
                        "Balance workload across resources",
                        "Add additional capacity for this resource",
                        "Implement workload distribution mechanisms",
                        "Consider skill-based routing",
                    ],
                )
                bottlenecks.append(bottleneck)

        return bottlenecks

    def _detect_path_bottlenecks(self, discovered_process) -> List[Bottleneck]:
        """Detect problematic process paths."""
        bottlenecks = []

        # Find paths with low success rates
        for path in discovered_process.paths:
            if path.success_rate < 0.7 and path.count > 5:  # At least 5 occurrences
                severity = 1.0 - path.success_rate

                bottleneck = Bottleneck(
                    activity=f"Path: {' → '.join(path.steps[:3])}{'...' if len(path.steps) > 3 else ''}",
                    bottleneck_type="path",
                    severity=severity,
                    impact=f"Process path has only {path.success_rate:.0%} success rate",
                    evidence={
                        "path_steps": path.steps,
                        "success_rate": path.success_rate,
                        "count": path.count,
                        "avg_duration_hours": path.avg_total_duration,
                    },
                    recommendations=[
                        "Investigate why this path has low success rate",
                        "Identify failure points in this variant",
                        "Consider process redesign for this scenario",
                        "Add quality checks earlier in the process",
                    ],
                )
                bottlenecks.append(bottleneck)

        return bottlenecks
