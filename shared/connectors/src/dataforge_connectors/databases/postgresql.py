"""PostgreSQL connector implementation."""

from typing import Any, Dict, List, Optional

import pandas as pd
import sqlalchemy
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine

from dataforge_connectors.base import DatabaseConnector


class PostgreSQLConnector(DatabaseConnector):
    """
    PostgreSQL database connector.

    Provides methods to connect, query, and manage PostgreSQL databases.

    Example:
        connector = PostgreSQLConnector(
            host="localhost",
            port=5432,
            database="mydb",
            user="user",
            password="password"
        )

        with connector:
            df = connector.read_table("users", limit=100)
            results = connector.execute_query("SELECT COUNT(*) FROM orders")
    """

    def __init__(
        self,
        host: str,
        port: int = 5432,
        database: str = "postgres",
        user: str = "postgres",
        password: str = "",
        **kwargs: Any
    ):
        """
        Initialize PostgreSQL connector.

        Args:
            host: Database host
            port: Database port
            database: Database name
            user: Username
            password: Password
            **kwargs: Additional SQLAlchemy options
        """
        super().__init__(connector_type="postgresql")

        self.host = host
        self.port = port
        self.database = database
        self.user = user
        self.password = password
        self.engine_kwargs = kwargs

        self._engine: Optional[Engine] = None

    def connect(self) -> Engine:
        """
        Create database engine and establish connection.

        Returns:
            SQLAlchemy Engine object
        """
        if self._engine is not None:
            self.logger.debug("Using existing database engine")
            return self._engine

        connection_string = (
            f"postgresql://{self.user}:{self.password}"
            f"@{self.host}:{self.port}/{self.database}"
        )

        self.logger.info(
            "Connecting to PostgreSQL",
            host=self.host,
            port=self.port,
            database=self.database
        )

        self._engine = create_engine(connection_string, **self.engine_kwargs)

        # Test connection
        with self._engine.connect() as conn:
            conn.execute(text("SELECT 1"))

        self._log_operation("connect")
        self._track_metric("connections_total")

        return self._engine

    def disconnect(self) -> None:
        """Close database connection."""
        if self._engine is not None:
            self._engine.dispose()
            self._engine = None
            self._log_operation("disconnect")

    def test_connection(self) -> bool:
        """
        Test database connection.

        Returns:
            bool: True if connection successful
        """
        try:
            engine = self.connect()
            with engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            return True
        except Exception as e:
            self.logger.error(f"Connection test failed: {str(e)}")
            return False

    def execute_query(
        self,
        query: str,
        params: Optional[Dict] = None
    ) -> List[Dict[str, Any]]:
        """
        Execute SQL query and return results.

        Args:
            query: SQL query string
            params: Query parameters

        Returns:
            List of result rows as dictionaries
        """
        engine = self.connect()

        self._log_operation("execute_query", query=query[:100])
        self._track_metric("queries_executed")

        with engine.connect() as conn:
            result = conn.execute(text(query), params or {})

            # Fetch results if it's a SELECT query
            if result.returns_rows:
                columns = result.keys()
                rows = result.fetchall()
                return [dict(zip(columns, row)) for row in rows]
            else:
                conn.commit()
                return []

    def read_table(
        self,
        table: str,
        schema: Optional[str] = None,
        limit: Optional[int] = None,
        columns: Optional[List[str]] = None,
        **kwargs: Any
    ) -> pd.DataFrame:
        """
        Read table into pandas DataFrame.

        Args:
            table: Table name
            schema: Schema name
            limit: Row limit
            columns: Columns to select
            **kwargs: Additional options

        Returns:
            DataFrame with table data
        """
        engine = self.connect()

        # Build query
        col_str = ", ".join(columns) if columns else "*"
        table_name = f"{schema}.{table}" if schema else table
        query = f"SELECT {col_str} FROM {table_name}"

        if limit:
            query += f" LIMIT {limit}"

        self._log_operation("read_table", table=table_name, limit=limit)
        self._track_metric("tables_read")

        df = pd.read_sql(query, engine, **kwargs)

        self.logger.info(
            "Table read complete",
            table=table_name,
            rows=len(df),
            columns=len(df.columns)
        )

        return df

    def write_dataframe(
        self,
        df: pd.DataFrame,
        table: str,
        schema: Optional[str] = None,
        if_exists: str = "append",
        **kwargs: Any
    ) -> int:
        """
        Write DataFrame to database table.

        Args:
            df: DataFrame to write
            table: Table name
            schema: Schema name
            if_exists: Action if table exists ('fail', 'replace', 'append')
            **kwargs: Additional options

        Returns:
            int: Number of rows written
        """
        engine = self.connect()

        self._log_operation(
            "write_dataframe",
            table=table,
            rows=len(df),
            if_exists=if_exists
        )

        df.to_sql(
            name=table,
            con=engine,
            schema=schema,
            if_exists=if_exists,
            index=False,
            **kwargs
        )

        self._track_metric("rows_written", value=len(df))

        self.logger.info(
            "DataFrame written",
            table=table,
            rows=len(df)
        )

        return len(df)

    def get_table_info(self, table: str, schema: Optional[str] = None) -> Dict[str, Any]:
        """
        Get table metadata.

        Args:
            table: Table name
            schema: Schema name

        Returns:
            dict: Table metadata
        """
        engine = self.connect()

        schema = schema or "public"

        # Get column info
        query = """
        SELECT
            column_name,
            data_type,
            is_nullable,
            column_default
        FROM information_schema.columns
        WHERE table_schema = :schema
        AND table_name = :table
        ORDER BY ordinal_position
        """

        with engine.connect() as conn:
            result = conn.execute(
                text(query),
                {"schema": schema, "table": table}
            )
            columns = [dict(row._mapping) for row in result]

        # Get row count
        count_query = f"SELECT COUNT(*) as count FROM {schema}.{table}"
        with engine.connect() as conn:
            result = conn.execute(text(count_query))
            row_count = result.fetchone()[0]

        return {
            "table": table,
            "schema": schema,
            "columns": columns,
            "row_count": row_count
        }
