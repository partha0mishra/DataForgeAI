"""Natural language query processor."""

import re
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from dataforge_common.logging import get_logger

logger = get_logger(__name__)


class QueryIntent(Enum):
    """Query intent types."""

    SELECT = "select"  # Retrieve data
    AGGREGATE = "aggregate"  # Aggregate/summarize
    FILTER = "filter"  # Filter data
    SORT = "sort"  # Sort/order data
    GROUP = "group"  # Group by
    JOIN = "join"  # Join tables
    TIME_SERIES = "time_series"  # Time-based analysis
    COMPARE = "compare"  # Comparison
    TOP_N = "top_n"  # Top N results
    TREND = "trend"  # Trend analysis
    DISTRIBUTION = "distribution"  # Distribution analysis
    UNKNOWN = "unknown"


class AggregationType(Enum):
    """Aggregation function types."""

    COUNT = "count"
    SUM = "sum"
    AVG = "avg"
    MIN = "min"
    MAX = "max"
    STDDEV = "stddev"
    MEDIAN = "median"


class TimeGranularity(Enum):
    """Time granularity for time series."""

    SECOND = "second"
    MINUTE = "minute"
    HOUR = "hour"
    DAY = "day"
    WEEK = "week"
    MONTH = "month"
    QUARTER = "quarter"
    YEAR = "year"


@dataclass
class QueryEntity:
    """Extracted entity from query."""

    type: str  # column, table, value, date, etc.
    value: str
    confidence: float = 1.0
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ParsedQuery:
    """Parsed natural language query."""

    original_query: str
    intent: QueryIntent
    entities: List[QueryEntity] = field(default_factory=list)
    columns: List[str] = field(default_factory=list)
    tables: List[str] = field(default_factory=list)
    filters: List[Dict[str, Any]] = field(default_factory=list)
    aggregations: List[Dict[str, Any]] = field(default_factory=list)
    group_by: List[str] = field(default_factory=list)
    order_by: List[Dict[str, str]] = field(default_factory=list)
    limit: Optional[int] = None
    time_range: Optional[Dict[str, Any]] = None
    time_granularity: Optional[TimeGranularity] = None
    confidence: float = 1.0
    metadata: Dict[str, Any] = field(default_factory=dict)


class QueryProcessor:
    """Process natural language queries into structured format."""

    def __init__(self):
        """Initialize query processor."""
        self.intent_patterns = self._build_intent_patterns()
        self.aggregation_keywords = self._build_aggregation_keywords()
        self.comparison_keywords = self._build_comparison_keywords()
        self.time_keywords = self._build_time_keywords()

    def _build_intent_patterns(self) -> Dict[QueryIntent, List[str]]:
        """Build intent detection patterns."""
        return {
            QueryIntent.SELECT: [
                r"\b(show|display|list|get|retrieve|fetch|find)\b",
                r"\b(what|which)\b",
            ],
            QueryIntent.AGGREGATE: [
                r"\b(total|sum|average|mean|count|number of)\b",
                r"\b(how many|how much)\b",
            ],
            QueryIntent.FILTER: [
                r"\b(where|with|having|that)\b",
                r"\b(greater than|less than|equal to|between)\b",
            ],
            QueryIntent.SORT: [
                r"\b(sort|order|rank|arrange)\b",
                r"\b(top|bottom|highest|lowest|best|worst)\b",
            ],
            QueryIntent.GROUP: [
                r"\b(group by|grouped by|per|by)\b",
                r"\b(each|every)\b",
            ],
            QueryIntent.TREND: [
                r"\b(trend|trending|over time|growth|decline)\b",
                r"\b(increase|decrease|change)\b",
            ],
            QueryIntent.COMPARE: [
                r"\b(compare|comparison|versus|vs|difference)\b",
            ],
            QueryIntent.TOP_N: [
                r"\b(top \d+|bottom \d+|first \d+|last \d+)\b",
            ],
            QueryIntent.TIME_SERIES: [
                r"\b(daily|weekly|monthly|yearly)\b",
                r"\b(by day|by week|by month|by year)\b",
            ],
            QueryIntent.DISTRIBUTION: [
                r"\b(distribution|spread|range|histogram)\b",
            ],
        }

    def _build_aggregation_keywords(self) -> Dict[str, AggregationType]:
        """Build aggregation keyword mapping."""
        return {
            "count": AggregationType.COUNT,
            "number": AggregationType.COUNT,
            "total": AggregationType.SUM,
            "sum": AggregationType.SUM,
            "average": AggregationType.AVG,
            "avg": AggregationType.AVG,
            "mean": AggregationType.AVG,
            "minimum": AggregationType.MIN,
            "min": AggregationType.MIN,
            "lowest": AggregationType.MIN,
            "maximum": AggregationType.MAX,
            "max": AggregationType.MAX,
            "highest": AggregationType.MAX,
            "stddev": AggregationType.STDDEV,
            "std": AggregationType.STDDEV,
            "median": AggregationType.MEDIAN,
        }

    def _build_comparison_keywords(self) -> Dict[str, str]:
        """Build comparison operator mapping."""
        return {
            "greater than": ">",
            "more than": ">",
            "above": ">",
            "less than": "<",
            "below": "<",
            "fewer than": "<",
            "equal to": "=",
            "equals": "=",
            "is": "=",
            "not equal to": "!=",
            "not": "!=",
            "between": "BETWEEN",
            "in": "IN",
            "like": "LIKE",
            "contains": "LIKE",
        }

    def _build_time_keywords(self) -> Dict[str, TimeGranularity]:
        """Build time granularity keywords."""
        return {
            "second": TimeGranularity.SECOND,
            "secondly": TimeGranularity.SECOND,
            "minute": TimeGranularity.MINUTE,
            "minutely": TimeGranularity.MINUTE,
            "hour": TimeGranularity.HOUR,
            "hourly": TimeGranularity.HOUR,
            "day": TimeGranularity.DAY,
            "daily": TimeGranularity.DAY,
            "week": TimeGranularity.WEEK,
            "weekly": TimeGranularity.WEEK,
            "month": TimeGranularity.MONTH,
            "monthly": TimeGranularity.MONTH,
            "quarter": TimeGranularity.QUARTER,
            "quarterly": TimeGranularity.QUARTER,
            "year": TimeGranularity.YEAR,
            "yearly": TimeGranularity.YEAR,
            "annually": TimeGranularity.YEAR,
        }

    def parse_query(
        self,
        query: str,
        schema: Optional[Dict[str, Any]] = None,
    ) -> ParsedQuery:
        """Parse natural language query.

        Args:
            query: Natural language query
            schema: Optional database schema for entity resolution

        Returns:
            Parsed query structure
        """
        logger.info(f"Parsing query: {query}")

        # Normalize query
        normalized = query.lower().strip()

        # Detect intent
        intent = self._detect_intent(normalized)

        # Extract entities
        entities = self._extract_entities(normalized, schema)

        # Extract columns
        columns = self._extract_columns(normalized, entities, schema)

        # Extract tables
        tables = self._extract_tables(normalized, entities, schema)

        # Extract filters
        filters = self._extract_filters(normalized, entities)

        # Extract aggregations
        aggregations = self._extract_aggregations(normalized, entities)

        # Extract group by
        group_by = self._extract_group_by(normalized, entities)

        # Extract order by
        order_by = self._extract_order_by(normalized, entities)

        # Extract limit
        limit = self._extract_limit(normalized)

        # Extract time range
        time_range = self._extract_time_range(normalized)

        # Extract time granularity
        time_granularity = self._extract_time_granularity(normalized)

        # Calculate confidence
        confidence = self._calculate_confidence(
            intent,
            entities,
            columns,
            tables,
        )

        parsed = ParsedQuery(
            original_query=query,
            intent=intent,
            entities=entities,
            columns=columns,
            tables=tables,
            filters=filters,
            aggregations=aggregations,
            group_by=group_by,
            order_by=order_by,
            limit=limit,
            time_range=time_range,
            time_granularity=time_granularity,
            confidence=confidence,
        )

        logger.info(f"Parsed query with intent: {intent.value}, confidence: {confidence:.2f}")

        return parsed

    def _detect_intent(self, query: str) -> QueryIntent:
        """Detect query intent."""
        intent_scores = {}

        for intent, patterns in self.intent_patterns.items():
            score = 0
            for pattern in patterns:
                if re.search(pattern, query, re.IGNORECASE):
                    score += 1
            if score > 0:
                intent_scores[intent] = score

        if not intent_scores:
            return QueryIntent.UNKNOWN

        # Return intent with highest score
        return max(intent_scores.items(), key=lambda x: x[1])[0]

    def _extract_entities(
        self,
        query: str,
        schema: Optional[Dict[str, Any]] = None,
    ) -> List[QueryEntity]:
        """Extract entities from query."""
        entities = []

        # Extract numbers
        for match in re.finditer(r"\b\d+\.?\d*\b", query):
            entities.append(
                QueryEntity(
                    type="number",
                    value=match.group(),
                    confidence=0.9,
                )
            )

        # Extract dates
        date_patterns = [
            r"\d{4}-\d{2}-\d{2}",
            r"\d{2}/\d{2}/\d{4}",
            r"(yesterday|today|tomorrow)",
            r"last (week|month|year|quarter)",
            r"this (week|month|year|quarter)",
        ]

        for pattern in date_patterns:
            for match in re.finditer(pattern, query, re.IGNORECASE):
                entities.append(
                    QueryEntity(
                        type="date",
                        value=match.group(),
                        confidence=0.8,
                    )
                )

        # Extract quoted strings
        for match in re.finditer(r"['\"]([^'\"]+)['\"]", query):
            entities.append(
                QueryEntity(
                    type="string",
                    value=match.group(1),
                    confidence=1.0,
                )
            )

        return entities

    def _extract_columns(
        self,
        query: str,
        entities: List[QueryEntity],
        schema: Optional[Dict[str, Any]] = None,
    ) -> List[str]:
        """Extract column names from query."""
        columns = []

        if schema and "columns" in schema:
            # Match against schema columns
            for column in schema["columns"]:
                # Direct match
                if column.lower() in query:
                    columns.append(column)
                # Match with underscores replaced by spaces
                elif column.replace("_", " ").lower() in query:
                    columns.append(column)

        return columns

    def _extract_tables(
        self,
        query: str,
        entities: List[QueryEntity],
        schema: Optional[Dict[str, Any]] = None,
    ) -> List[str]:
        """Extract table names from query."""
        tables = []

        if schema and "tables" in schema:
            for table in schema["tables"]:
                if table.lower() in query:
                    tables.append(table)

        return tables

    def _extract_filters(
        self,
        query: str,
        entities: List[QueryEntity],
    ) -> List[Dict[str, Any]]:
        """Extract filter conditions."""
        filters = []

        # Look for comparison patterns
        for keyword, operator in self.comparison_keywords.items():
            pattern = rf"(\w+)\s+{re.escape(keyword)}\s+(['\"]?[\w\d\s]+['\"]?)"
            for match in re.finditer(pattern, query, re.IGNORECASE):
                column = match.group(1)
                value = match.group(2).strip("'\"")

                filters.append({
                    "column": column,
                    "operator": operator,
                    "value": value,
                })

        return filters

    def _extract_aggregations(
        self,
        query: str,
        entities: List[QueryEntity],
    ) -> List[Dict[str, Any]]:
        """Extract aggregation functions."""
        aggregations = []

        for keyword, agg_type in self.aggregation_keywords.items():
            if keyword in query:
                # Try to find column after keyword
                pattern = rf"{keyword}\s+(?:of\s+)?(\w+)"
                match = re.search(pattern, query, re.IGNORECASE)

                if match:
                    column = match.group(1)
                    aggregations.append({
                        "function": agg_type.value,
                        "column": column,
                    })
                else:
                    # Aggregation without specific column
                    aggregations.append({
                        "function": agg_type.value,
                        "column": "*",
                    })

        return aggregations

    def _extract_group_by(
        self,
        query: str,
        entities: List[QueryEntity],
    ) -> List[str]:
        """Extract group by columns."""
        group_by = []

        # Look for "group by" or "by" patterns
        patterns = [
            r"group by\s+(\w+)",
            r"grouped by\s+(\w+)",
            r"\s+by\s+(\w+)",
            r"\s+per\s+(\w+)",
        ]

        for pattern in patterns:
            match = re.search(pattern, query, re.IGNORECASE)
            if match:
                group_by.append(match.group(1))

        return group_by

    def _extract_order_by(
        self,
        query: str,
        entities: List[QueryEntity],
    ) -> List[Dict[str, str]]:
        """Extract order by clauses."""
        order_by = []

        # Look for sort/order patterns
        patterns = [
            r"(sort|order)\s+by\s+(\w+)\s+(asc|desc)?",
            r"(highest|lowest|best|worst)\s+(\w+)",
        ]

        for pattern in patterns:
            match = re.search(pattern, query, re.IGNORECASE)
            if match:
                if "highest" in match.group(0) or "best" in match.group(0):
                    direction = "DESC"
                    column = match.group(2)
                elif "lowest" in match.group(0) or "worst" in match.group(0):
                    direction = "ASC"
                    column = match.group(2)
                else:
                    column = match.group(2)
                    direction = match.group(3).upper() if match.lastindex >= 3 else "ASC"

                order_by.append({
                    "column": column,
                    "direction": direction,
                })

        return order_by

    def _extract_limit(self, query: str) -> Optional[int]:
        """Extract result limit."""
        # Look for top/bottom N patterns
        patterns = [
            r"top\s+(\d+)",
            r"first\s+(\d+)",
            r"limit\s+(\d+)",
            r"(\d+)\s+results?",
        ]

        for pattern in patterns:
            match = re.search(pattern, query, re.IGNORECASE)
            if match:
                return int(match.group(1))

        return None

    def _extract_time_range(self, query: str) -> Optional[Dict[str, Any]]:
        """Extract time range filters."""
        time_range = {}

        # Relative time patterns
        if "last" in query:
            match = re.search(r"last\s+(\d+)?\s*(day|week|month|year)s?", query, re.IGNORECASE)
            if match:
                count = int(match.group(1)) if match.group(1) else 1
                unit = match.group(2).lower()
                time_range = {
                    "type": "relative",
                    "count": count,
                    "unit": unit,
                }

        # Absolute date patterns
        elif re.search(r"\d{4}-\d{2}-\d{2}", query):
            dates = re.findall(r"\d{4}-\d{2}-\d{2}", query)
            if len(dates) >= 2:
                time_range = {
                    "type": "absolute",
                    "start": dates[0],
                    "end": dates[1],
                }
            elif len(dates) == 1:
                time_range = {
                    "type": "absolute",
                    "date": dates[0],
                }

        return time_range if time_range else None

    def _extract_time_granularity(self, query: str) -> Optional[TimeGranularity]:
        """Extract time granularity."""
        for keyword, granularity in self.time_keywords.items():
            if keyword in query:
                return granularity

        return None

    def _calculate_confidence(
        self,
        intent: QueryIntent,
        entities: List[QueryEntity],
        columns: List[str],
        tables: List[str],
    ) -> float:
        """Calculate confidence score for parsed query."""
        confidence = 0.5  # Base confidence

        # Boost for non-unknown intent
        if intent != QueryIntent.UNKNOWN:
            confidence += 0.2

        # Boost for extracted entities
        if entities:
            confidence += min(0.1 * len(entities), 0.2)

        # Boost for identified columns
        if columns:
            confidence += 0.1

        # Boost for identified tables
        if tables:
            confidence += 0.1

        return min(confidence, 1.0)
