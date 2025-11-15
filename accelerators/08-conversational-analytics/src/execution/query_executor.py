"""Query execution engine for conversational analytics."""

import pandas as pd
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional
from urllib.parse import quote_plus

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine

from dataforge_common.logging import get_logger

logger = get_logger(__name__)


@dataclass
class QueryResult:
    """Query execution result."""

    success: bool
    data: Optional[pd.DataFrame] = None
    row_count: int = 0
    column_count: int = 0
    execution_time_ms: float = 0.0
    error: Optional[str] = None
    warnings: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class FormattedResult:
    """Formatted query result for presentation."""

    format: str  # table, chart, summary, text
    content: Any
    title: str = ""
    description: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)


class QueryExecutor:
    """Execute SQL queries and format results."""

    def __init__(self):
        """Initialize query executor."""
        self.engines: Dict[str, Engine] = {}

    def connect(
        self,
        name: str,
        connection_string: Optional[str] = None,
        host: Optional[str] = None,
        port: Optional[int] = None,
        database: Optional[str] = None,
        username: Optional[str] = None,
        password: Optional[str] = None,
        dialect: str = "postgresql",
    ) -> None:
        """Create database connection.

        Args:
            name: Connection name
            connection_string: Full connection string (if provided, other params ignored)
            host: Database host
            port: Database port
            database: Database name
            username: Username
            password: Password
            dialect: SQL dialect
        """
        if connection_string:
            conn_str = connection_string
        else:
            # Build connection string
            if dialect == "postgresql":
                default_port = port or 5432
                conn_str = (
                    f"postgresql://{username}:{quote_plus(password)}"
                    f"@{host}:{default_port}/{database}"
                )
            elif dialect == "mysql":
                default_port = port or 3306
                conn_str = (
                    f"mysql+pymysql://{username}:{quote_plus(password)}"
                    f"@{host}:{default_port}/{database}"
                )
            elif dialect == "sqlite":
                conn_str = f"sqlite:///{database}"
            else:
                raise ValueError(f"Unsupported dialect: {dialect}")

        # Create engine
        engine = create_engine(conn_str, pool_pre_ping=True)
        self.engines[name] = engine

        logger.info(f"Connected to database: {name} ({dialect})")

    def disconnect(self, name: str) -> None:
        """Disconnect from database.

        Args:
            name: Connection name
        """
        if name in self.engines:
            self.engines[name].dispose()
            del self.engines[name]
            logger.info(f"Disconnected from database: {name}")

    def execute_query(
        self,
        query: str,
        connection_name: str = "default",
        params: Optional[Dict[str, Any]] = None,
        timeout: Optional[int] = None,
    ) -> QueryResult:
        """Execute SQL query.

        Args:
            query: SQL query to execute
            connection_name: Name of connection to use
            params: Query parameters
            timeout: Query timeout in seconds

        Returns:
            Query result with data and metadata
        """
        if connection_name not in self.engines:
            return QueryResult(
                success=False,
                error=f"Connection '{connection_name}' not found",
            )

        engine = self.engines[connection_name]

        start_time = datetime.utcnow()

        try:
            # Execute query
            with engine.connect() as conn:
                if timeout:
                    conn = conn.execution_options(timeout=timeout)

                result = conn.execute(text(query), params or {})

                # Fetch results
                if result.returns_rows:
                    df = pd.DataFrame(result.fetchall(), columns=result.keys())
                else:
                    df = pd.DataFrame()

            end_time = datetime.utcnow()
            execution_time = (end_time - start_time).total_seconds() * 1000

            row_count = len(df) if df is not None else 0
            column_count = len(df.columns) if df is not None else 0

            logger.info(
                f"Query executed successfully: {row_count} rows, "
                f"{execution_time:.2f}ms"
            )

            return QueryResult(
                success=True,
                data=df,
                row_count=row_count,
                column_count=column_count,
                execution_time_ms=execution_time,
            )

        except Exception as e:
            logger.error(f"Query execution failed: {str(e)}")

            return QueryResult(
                success=False,
                error=str(e),
            )

    def format_result(
        self,
        result: QueryResult,
        format: str = "table",
        max_rows: int = 100,
    ) -> FormattedResult:
        """Format query result for presentation.

        Args:
            result: Query result to format
            format: Output format (table, summary, text, json, markdown)
            max_rows: Maximum rows to include

        Returns:
            Formatted result
        """
        if not result.success:
            return FormattedResult(
                format="text",
                content=f"Error: {result.error}",
                title="Query Failed",
            )

        if result.data is None or result.data.empty:
            return FormattedResult(
                format="text",
                content="No results found",
                title="Empty Result",
            )

        # Limit rows
        data = result.data.head(max_rows)

        if format == "table":
            return self._format_as_table(data, result)
        elif format == "summary":
            return self._format_as_summary(data, result)
        elif format == "text":
            return self._format_as_text(data, result)
        elif format == "json":
            return self._format_as_json(data, result)
        elif format == "markdown":
            return self._format_as_markdown(data, result)
        else:
            raise ValueError(f"Unsupported format: {format}")

    def _format_as_table(
        self,
        data: pd.DataFrame,
        result: QueryResult,
    ) -> FormattedResult:
        """Format as table."""
        return FormattedResult(
            format="table",
            content=data,
            title="Query Results",
            description=f"{result.row_count} rows × {result.column_count} columns",
            metadata={
                "execution_time_ms": result.execution_time_ms,
                "row_count": result.row_count,
                "column_count": result.column_count,
            },
        )

    def _format_as_summary(
        self,
        data: pd.DataFrame,
        result: QueryResult,
    ) -> FormattedResult:
        """Format as summary statistics."""
        summary_lines = []

        summary_lines.append(f"Query returned {result.row_count} rows")
        summary_lines.append(f"Execution time: {result.execution_time_ms:.2f}ms")
        summary_lines.append("")

        # Column summary
        summary_lines.append("Columns:")
        for col in data.columns:
            dtype = str(data[col].dtype)
            null_count = data[col].isna().sum()
            summary_lines.append(f"  - {col} ({dtype})")
            if null_count > 0:
                summary_lines.append(f"    Null values: {null_count}")

        summary_lines.append("")

        # Numeric column statistics
        numeric_cols = data.select_dtypes(include=["number"]).columns
        if len(numeric_cols) > 0:
            summary_lines.append("Numeric Statistics:")
            for col in numeric_cols:
                summary_lines.append(f"  {col}:")
                summary_lines.append(f"    Min: {data[col].min()}")
                summary_lines.append(f"    Max: {data[col].max()}")
                summary_lines.append(f"    Mean: {data[col].mean():.2f}")
                summary_lines.append(f"    Median: {data[col].median():.2f}")

        return FormattedResult(
            format="summary",
            content="\n".join(summary_lines),
            title="Query Summary",
        )

    def _format_as_text(
        self,
        data: pd.DataFrame,
        result: QueryResult,
    ) -> FormattedResult:
        """Format as plain text."""
        text = data.to_string(index=False)

        return FormattedResult(
            format="text",
            content=text,
            title="Query Results",
            description=f"{result.row_count} rows",
        )

    def _format_as_json(
        self,
        data: pd.DataFrame,
        result: QueryResult,
    ) -> FormattedResult:
        """Format as JSON."""
        json_data = data.to_dict(orient="records")

        return FormattedResult(
            format="json",
            content=json_data,
            title="Query Results",
            metadata={
                "row_count": result.row_count,
                "column_count": result.column_count,
            },
        )

    def _format_as_markdown(
        self,
        data: pd.DataFrame,
        result: QueryResult,
    ) -> FormattedResult:
        """Format as Markdown table."""
        markdown = data.to_markdown(index=False)

        return FormattedResult(
            format="markdown",
            content=markdown,
            title="Query Results",
            description=f"{result.row_count} rows × {result.column_count} columns",
        )

    def get_schema(self, connection_name: str = "default") -> Dict[str, Any]:
        """Get database schema.

        Args:
            connection_name: Name of connection

        Returns:
            Database schema information
        """
        if connection_name not in self.engines:
            raise ValueError(f"Connection '{connection_name}' not found")

        engine = self.engines[connection_name]
        schema = {"tables": {}}

        try:
            # Get table names
            with engine.connect() as conn:
                inspector = conn.dialect.get_table_names(conn)

                for table_name in inspector:
                    # Get column information
                    query = text(
                        f"""
                        SELECT column_name, data_type
                        FROM information_schema.columns
                        WHERE table_name = :table_name
                        ORDER BY ordinal_position
                    """
                    )

                    result = conn.execute(query, {"table_name": table_name})
                    columns = {}

                    for row in result:
                        columns[row[0]] = row[1]

                    schema["tables"][table_name] = {
                        "columns": columns,
                    }

            logger.info(f"Retrieved schema with {len(schema['tables'])} tables")

        except Exception as e:
            logger.warning(f"Could not retrieve full schema: {str(e)}")

            # Fallback: just get table names
            try:
                with engine.connect() as conn:
                    result = conn.execute(
                        text("SELECT tablename FROM pg_tables WHERE schemaname = 'public'")
                    )
                    for row in result:
                        schema["tables"][row[0]] = {"columns": {}}
            except:
                pass

        return schema

    def execute_batch(
        self,
        queries: List[str],
        connection_name: str = "default",
    ) -> List[QueryResult]:
        """Execute multiple queries.

        Args:
            queries: List of SQL queries
            connection_name: Name of connection

        Returns:
            List of query results
        """
        results = []

        for query in queries:
            result = self.execute_query(query, connection_name)
            results.append(result)

            # Stop on first error
            if not result.success:
                logger.warning("Batch execution stopped due to error")
                break

        return results
