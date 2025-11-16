"""Process mining from event logs."""

import pandas as pd
import networkx as nx
from collections import defaultdict, Counter
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple

from dataforge_common.logging import get_logger

logger = get_logger(__name__)


@dataclass
class ProcessStep:
    """A step in a business process."""

    activity: str
    count: int
    avg_duration: float
    min_duration: float
    max_duration: float
    resources: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ProcessPath:
    """A path through the process."""

    steps: List[str]
    count: int
    avg_total_duration: float
    success_rate: float
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class DiscoveredProcess:
    """A discovered business process."""

    process_name: str
    total_cases: int
    unique_activities: int
    start_activities: List[str]
    end_activities: List[str]
    steps: Dict[str, ProcessStep]
    paths: List[ProcessPath]
    graph: nx.DiGraph
    statistics: Dict[str, Any] = field(default_factory=dict)


class ProcessMiner:
    """Mine business processes from event logs."""

    def __init__(self):
        """Initialize process miner."""
        pass

    def discover_process(
        self,
        event_log: pd.DataFrame,
        case_id_column: str = "case_id",
        activity_column: str = "activity",
        timestamp_column: str = "timestamp",
        resource_column: Optional[str] = None,
        outcome_column: Optional[str] = None,
    ) -> DiscoveredProcess:
        """Discover process from event log.

        Args:
            event_log: Event log DataFrame
            case_id_column: Column name for case ID
            activity_column: Column name for activity
            timestamp_column: Column name for timestamp
            resource_column: Optional column name for resource
            outcome_column: Optional column name for outcome

        Returns:
            Discovered process model
        """
        logger.info(f"Discovering process from {len(event_log)} events")

        # Ensure timestamp is datetime
        if not pd.api.types.is_datetime64_any_dtype(event_log[timestamp_column]):
            event_log[timestamp_column] = pd.to_datetime(event_log[timestamp_column])

        # Sort by case and timestamp
        event_log = event_log.sort_values([case_id_column, timestamp_column])

        # Extract process name (use first activity as proxy)
        process_name = f"Process_{event_log[activity_column].iloc[0]}"

        # Count total cases
        total_cases = event_log[case_id_column].nunique()

        # Get unique activities
        unique_activities = event_log[activity_column].nunique()

        # Find start and end activities
        start_activities = self._find_start_activities(
            event_log, case_id_column, activity_column
        )
        end_activities = self._find_end_activities(
            event_log, case_id_column, activity_column
        )

        # Analyze steps
        steps = self._analyze_steps(
            event_log,
            case_id_column,
            activity_column,
            timestamp_column,
            resource_column,
        )

        # Discover paths
        paths = self._discover_paths(
            event_log,
            case_id_column,
            activity_column,
            timestamp_column,
            outcome_column,
        )

        # Build process graph
        graph = self._build_process_graph(event_log, case_id_column, activity_column)

        # Calculate statistics
        statistics = self._calculate_statistics(
            event_log,
            case_id_column,
            activity_column,
            timestamp_column,
        )

        discovered = DiscoveredProcess(
            process_name=process_name,
            total_cases=total_cases,
            unique_activities=unique_activities,
            start_activities=start_activities,
            end_activities=end_activities,
            steps=steps,
            paths=paths,
            graph=graph,
            statistics=statistics,
        )

        logger.info(
            f"Discovered process: {total_cases} cases, "
            f"{unique_activities} activities, "
            f"{len(paths)} paths"
        )

        return discovered

    def _find_start_activities(
        self,
        event_log: pd.DataFrame,
        case_id_column: str,
        activity_column: str,
    ) -> List[str]:
        """Find activities that start cases."""
        first_activities = (
            event_log.groupby(case_id_column)[activity_column].first().value_counts()
        )
        return first_activities.index.tolist()

    def _find_end_activities(
        self,
        event_log: pd.DataFrame,
        case_id_column: str,
        activity_column: str,
    ) -> List[str]:
        """Find activities that end cases."""
        last_activities = (
            event_log.groupby(case_id_column)[activity_column].last().value_counts()
        )
        return last_activities.index.tolist()

    def _analyze_steps(
        self,
        event_log: pd.DataFrame,
        case_id_column: str,
        activity_column: str,
        timestamp_column: str,
        resource_column: Optional[str],
    ) -> Dict[str, ProcessStep]:
        """Analyze individual process steps."""
        steps = {}

        for activity in event_log[activity_column].unique():
            activity_events = event_log[event_log[activity_column] == activity]

            # Calculate duration (time to next event in same case)
            durations = []
            for case_id in activity_events[case_id_column].unique():
                case_events = event_log[event_log[case_id_column] == case_id].sort_values(
                    timestamp_column
                )

                activity_indices = case_events[
                    case_events[activity_column] == activity
                ].index

                for idx in activity_indices:
                    idx_pos = case_events.index.get_loc(idx)
                    if idx_pos < len(case_events) - 1:
                        next_idx = case_events.index[idx_pos + 1]
                        duration = (
                            case_events.loc[next_idx, timestamp_column]
                            - case_events.loc[idx, timestamp_column]
                        ).total_seconds() / 3600  # Convert to hours

                        if duration > 0:  # Only positive durations
                            durations.append(duration)

            # Get resources
            resources = []
            if resource_column and resource_column in event_log.columns:
                resources = activity_events[resource_column].unique().tolist()

            # Create step
            count = len(activity_events)
            avg_duration = sum(durations) / len(durations) if durations else 0
            min_duration = min(durations) if durations else 0
            max_duration = max(durations) if durations else 0

            steps[activity] = ProcessStep(
                activity=activity,
                count=count,
                avg_duration=avg_duration,
                min_duration=min_duration,
                max_duration=max_duration,
                resources=resources,
            )

        return steps

    def _discover_paths(
        self,
        event_log: pd.DataFrame,
        case_id_column: str,
        activity_column: str,
        timestamp_column: str,
        outcome_column: Optional[str],
    ) -> List[ProcessPath]:
        """Discover common paths through the process."""
        # Extract paths for each case
        case_paths = []
        case_durations = []
        case_outcomes = []

        for case_id in event_log[case_id_column].unique():
            case_events = event_log[event_log[case_id_column] == case_id].sort_values(
                timestamp_column
            )

            # Path is sequence of activities
            path = case_events[activity_column].tolist()
            case_paths.append(tuple(path))

            # Total duration
            if len(case_events) > 1:
                duration = (
                    case_events[timestamp_column].iloc[-1]
                    - case_events[timestamp_column].iloc[0]
                ).total_seconds() / 3600
                case_durations.append(duration)
            else:
                case_durations.append(0)

            # Outcome
            if outcome_column and outcome_column in case_events.columns:
                outcome = case_events[outcome_column].iloc[-1]
                case_outcomes.append(outcome)
            else:
                case_outcomes.append(None)

        # Count path frequencies
        path_counts = Counter(case_paths)

        # Aggregate by path
        paths = []
        for path, count in path_counts.most_common(20):  # Top 20 paths
            # Get durations for this path
            path_durations = [
                case_durations[i]
                for i, p in enumerate(case_paths)
                if p == path
            ]

            # Get outcomes for this path
            path_outcomes = [
                case_outcomes[i]
                for i, p in enumerate(case_paths)
                if p == path
            ]

            # Calculate success rate
            if outcome_column and any(o is not None for o in path_outcomes):
                successful = sum(
                    1 for o in path_outcomes if o in ["success", "completed", "approved"]
                )
                success_rate = successful / len(path_outcomes)
            else:
                success_rate = 1.0  # Assume success if no outcome

            avg_duration = sum(path_durations) / len(path_durations)

            paths.append(
                ProcessPath(
                    steps=list(path),
                    count=count,
                    avg_total_duration=avg_duration,
                    success_rate=success_rate,
                )
            )

        return paths

    def _build_process_graph(
        self,
        event_log: pd.DataFrame,
        case_id_column: str,
        activity_column: str,
    ) -> nx.DiGraph:
        """Build directed graph of process flow."""
        graph = nx.DiGraph()

        # Add nodes for each activity
        for activity in event_log[activity_column].unique():
            graph.add_node(activity)

        # Add edges for activity transitions
        edge_counts = defaultdict(int)

        for case_id in event_log[case_id_column].unique():
            case_events = event_log[event_log[case_id_column] == case_id].sort_values(
                "timestamp" if "timestamp" in event_log.columns else event_log.columns[0]
            )

            activities = case_events[activity_column].tolist()

            for i in range(len(activities) - 1):
                edge = (activities[i], activities[i + 1])
                edge_counts[edge] += 1

        # Add edges with weights
        for (source, target), count in edge_counts.items():
            graph.add_edge(source, target, weight=count)

        return graph

    def _calculate_statistics(
        self,
        event_log: pd.DataFrame,
        case_id_column: str,
        activity_column: str,
        timestamp_column: str,
    ) -> Dict[str, Any]:
        """Calculate process statistics."""
        stats = {}

        # Case duration statistics
        case_durations = []
        for case_id in event_log[case_id_column].unique():
            case_events = event_log[event_log[case_id_column] == case_id]
            if len(case_events) > 1:
                duration = (
                    case_events[timestamp_column].max()
                    - case_events[timestamp_column].min()
                ).total_seconds() / 3600
                case_durations.append(duration)

        if case_durations:
            stats["avg_case_duration_hours"] = sum(case_durations) / len(case_durations)
            stats["min_case_duration_hours"] = min(case_durations)
            stats["max_case_duration_hours"] = max(case_durations)
            stats["median_case_duration_hours"] = sorted(case_durations)[
                len(case_durations) // 2
            ]

        # Activity frequency
        stats["total_events"] = len(event_log)
        stats["avg_events_per_case"] = len(event_log) / event_log[case_id_column].nunique()

        # Temporal statistics
        stats["first_event"] = event_log[timestamp_column].min().isoformat()
        stats["last_event"] = event_log[timestamp_column].max().isoformat()
        stats["timespan_days"] = (
            event_log[timestamp_column].max() - event_log[timestamp_column].min()
        ).days

        return stats

    def export_bpmn(self, process: DiscoveredProcess) -> str:
        """Export process as BPMN XML (simplified).

        Args:
            process: Discovered process

        Returns:
            BPMN XML string
        """
        # Simplified BPMN export
        bpmn = f"""<?xml version="1.0" encoding="UTF-8"?>
<definitions xmlns="http://www.omg.org/spec/BPMN/20100524/MODEL"
             targetNamespace="http://dataforge.ai/bpmn">
  <process id="{process.process_name}" name="{process.process_name}">
"""

        # Add tasks
        for activity in process.steps.keys():
            activity_id = activity.replace(" ", "_")
            bpmn += f'    <task id="{activity_id}" name="{activity}" />\n'

        # Add sequence flows
        flow_id = 1
        for source, target in process.graph.edges():
            source_id = source.replace(" ", "_")
            target_id = target.replace(" ", "_")
            bpmn += f'    <sequenceFlow id="flow_{flow_id}" sourceRef="{source_id}" targetRef="{target_id}" />\n'
            flow_id += 1

        bpmn += """  </process>
</definitions>"""

        return bpmn
