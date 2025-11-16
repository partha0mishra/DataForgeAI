"""Query engine for fetching data from various sources."""

from typing import Any, Dict, List, Optional

import pandas as pd

from dataforge_common.logging import get_logger
from dataforge_connectors.databases.postgresql import PostgreSQLConnector

logger = get_logger(__name__)


class QueryEngine:
    """
    Query engine for dashboard data sources.

    Provides:
    - Database query execution
    - Data transformation
    - Caching
    - Parameter substitution

    Example:
        engine = QueryEngine()

        # Execute SQL query
        df = engine.execute_query(
            source_type="database",
            connection_string="postgresql://...",
            query="SELECT * FROM sales WHERE date >= :start_date",
            parameters={"start_date": "2025-01-01"}
        )

        # Fetch from API
        df = engine.fetch_from_api(
            endpoint="https://api.example.com/data",
            params={"limit": 100}
        )
    """

    def __init__(self, cache_enabled: bool = True):
        """
        Initialize query engine.

        Args:
            cache_enabled: Enable query result caching
        """
        self.cache_enabled = cache_enabled
        self.logger = logger

        # Simple in-memory cache
        self.cache: Dict[str, pd.DataFrame] = {}

        self.logger.info("Query engine initialized", cache_enabled=cache_enabled)

    def execute_query(
        self,
        source_type: str,
        query: Optional[str] = None,
        connection_string: Optional[str] = None,
        file_path: Optional[str] = None,
        api_endpoint: Optional[str] = None,
        parameters: Optional[Dict[str, Any]] = None,
        use_cache: bool = True,
    ) -> pd.DataFrame:
        """
        Execute query based on source type.

        Args:
            source_type: Type of data source (database, file, api)
            query: SQL query or filter expression
            connection_string: Database connection string
            file_path: Path to file
            api_endpoint: API endpoint URL
            parameters: Query parameters
            use_cache: Use cached results if available

        Returns:
            DataFrame with results
        """
        # Generate cache key
        cache_key = self._generate_cache_key(
            source_type, query, connection_string, file_path, api_endpoint, parameters
        )

        # Check cache
        if use_cache and self.cache_enabled and cache_key in self.cache:
            self.logger.debug("Cache hit", cache_key=cache_key[:50])
            return self.cache[cache_key].copy()

        # Execute query based on source type
        if source_type == "database":
            df = self._query_database(connection_string, query, parameters)
        elif source_type == "file":
            df = self._read_file(file_path, parameters)
        elif source_type == "api":
            df = self._fetch_from_api(api_endpoint, parameters)
        else:
            raise ValueError(f"Unsupported source type: {source_type}")

        # Cache result
        if self.cache_enabled:
            self.cache[cache_key] = df.copy()

        self.logger.info(
            "Query executed",
            source_type=source_type,
            rows=len(df),
            columns=len(df.columns),
        )

        return df

    def _query_database(
        self,
        connection_string: str,
        query: str,
        parameters: Optional[Dict[str, Any]] = None,
    ) -> pd.DataFrame:
        """Query database and return DataFrame."""
        # Substitute parameters in query
        if parameters:
            for key, value in parameters.items():
                placeholder = f":{key}"
                if isinstance(value, str):
                    query = query.replace(placeholder, f"'{value}'")
                else:
                    query = query.replace(placeholder, str(value))

        # Determine database type from connection string
        if "postgresql" in connection_string or "postgres" in connection_string:
            return self._query_postgresql(connection_string, query)
        else:
            # Generic SQL query using pandas
            import sqlalchemy

            engine = sqlalchemy.create_engine(connection_string)
            df = pd.read_sql(query, engine)
            engine.dispose()
            return df

    def _query_postgresql(self, connection_string: str, query: str) -> pd.DataFrame:
        """Query PostgreSQL database."""
        # Parse connection string
        # Format: postgresql://user:password@host:port/database
        parts = connection_string.replace("postgresql://", "").split("@")
        user_pass = parts[0].split(":")
        host_db = parts[1].split("/")
        host_port = host_db[0].split(":")

        connector = PostgreSQLConnector(
            host=host_port[0],
            port=int(host_port[1]) if len(host_port) > 1 else 5432,
            database=host_db[1] if len(host_db) > 1 else "postgres",
            user=user_pass[0],
            password=user_pass[1] if len(user_pass) > 1 else "",
        )

        with connector:
            df = connector.execute_query(query)

        return df

    def _read_file(
        self,
        file_path: str,
        parameters: Optional[Dict[str, Any]] = None,
    ) -> pd.DataFrame:
        """Read data from file."""
        # Determine file type
        if file_path.endswith(".csv"):
            df = pd.read_csv(file_path)
        elif file_path.endswith(".parquet"):
            df = pd.read_parquet(file_path)
        elif file_path.endswith(".json"):
            df = pd.read_json(file_path)
        elif file_path.endswith((".xlsx", ".xls")):
            df = pd.read_excel(file_path)
        else:
            raise ValueError(f"Unsupported file type: {file_path}")

        # Apply filters from parameters
        if parameters:
            for column, value in parameters.items():
                if column in df.columns:
                    df = df[df[column] == value]

        return df

    def _fetch_from_api(
        self,
        endpoint: str,
        parameters: Optional[Dict[str, Any]] = None,
    ) -> pd.DataFrame:
        """Fetch data from API."""
        import requests

        response = requests.get(endpoint, params=parameters)
        response.raise_for_status()

        data = response.json()

        # Convert to DataFrame
        if isinstance(data, list):
            df = pd.DataFrame(data)
        elif isinstance(data, dict):
            # Try to find the data array
            for key in ["data", "results", "items"]:
                if key in data and isinstance(data[key], list):
                    df = pd.DataFrame(data[key])
                    break
            else:
                # Use the dict as-is
                df = pd.DataFrame([data])
        else:
            raise ValueError(f"Unexpected API response format: {type(data)}")

        return df

    def _generate_cache_key(self, *args) -> str:
        """Generate cache key from arguments."""
        import hashlib

        key_str = str(args)
        return hashlib.md5(key_str.encode()).hexdigest()

    def clear_cache(self) -> None:
        """Clear query cache."""
        self.cache.clear()
        self.logger.info("Cache cleared")

    def transform_data(
        self,
        df: pd.DataFrame,
        transformations: List[Dict[str, Any]],
    ) -> pd.DataFrame:
        """
        Apply transformations to DataFrame.

        Args:
            df: Input DataFrame
            transformations: List of transformation definitions

        Returns:
            Transformed DataFrame
        """
        result = df.copy()

        for transform in transformations:
            transform_type = transform.get("type")

            if transform_type == "filter":
                # Filter rows
                column = transform["column"]
                operator = transform.get("operator", "==")
                value = transform["value"]

                if operator == "==":
                    result = result[result[column] == value]
                elif operator == "!=":
                    result = result[result[column] != value]
                elif operator == ">":
                    result = result[result[column] > value]
                elif operator == ">=":
                    result = result[result[column] >= value]
                elif operator == "<":
                    result = result[result[column] < value]
                elif operator == "<=":
                    result = result[result[column] <= value]

            elif transform_type == "aggregate":
                # Aggregate data
                group_by = transform.get("group_by", [])
                agg_func = transform.get("function", "sum")
                agg_column = transform.get("column")

                if group_by:
                    result = result.groupby(group_by)[agg_column].agg(agg_func).reset_index()
                else:
                    result = pd.DataFrame({agg_column: [result[agg_column].agg(agg_func)]})

            elif transform_type == "sort":
                # Sort data
                column = transform["column"]
                ascending = transform.get("ascending", True)
                result = result.sort_values(by=column, ascending=ascending)

            elif transform_type == "limit":
                # Limit rows
                n = transform["n"]
                result = result.head(n)

            elif transform_type == "select":
                # Select columns
                columns = transform["columns"]
                result = result[columns]

            elif transform_type == "rename":
                # Rename columns
                mapping = transform["mapping"]
                result = result.rename(columns=mapping)

        self.logger.debug(
            "Data transformed",
            transformations=len(transformations),
            rows=len(result),
        )

        return result

    def preview_data(
        self,
        source_type: str,
        n: int = 10,
        **kwargs,
    ) -> pd.DataFrame:
        """
        Preview data from source.

        Args:
            source_type: Type of data source
            n: Number of rows to preview
            **kwargs: Source parameters

        Returns:
            Preview DataFrame
        """
        df = self.execute_query(source_type=source_type, use_cache=False, **kwargs)
        return df.head(n)

    def get_schema(
        self,
        source_type: str,
        **kwargs,
    ) -> Dict[str, str]:
        """
        Get schema (column names and types) from source.

        Args:
            source_type: Type of data source
            **kwargs: Source parameters

        Returns:
            Dictionary mapping column names to types
        """
        df = self.preview_data(source_type=source_type, n=1, **kwargs)

        schema = {col: str(dtype) for col, dtype in df.dtypes.items()}

        return schema
