"""Base connector class for all data sources."""

from abc import ABC, abstractmethod
from typing import Any, Dict, Optional

from dataforge_common.logging import get_logger
from dataforge_common.monitoring import increment_counter, track_duration


class BaseConnector(ABC):
    """
    Abstract base class for all data connectors.

    Provides common functionality for connection management,
    logging, and monitoring across all connector types.
    """

    def __init__(self, connector_type: str, **config: Any):
        """
        Initialize base connector.

        Args:
            connector_type: Type of connector (e.g., 'postgresql', 's3')
            **config: Connector-specific configuration
        """
        self.connector_type = connector_type
        self.config = config
        self.logger = get_logger(
            __name__,
            connector_type=connector_type
        )
        self._connection: Optional[Any] = None

    @abstractmethod
    def connect(self) -> Any:
        """
        Establish connection to data source.

        Returns:
            Connection object
        """
        pass

    @abstractmethod
    def disconnect(self) -> None:
        """Close connection to data source."""
        pass

    @abstractmethod
    def test_connection(self) -> bool:
        """
        Test if connection is valid.

        Returns:
            bool: True if connection is valid
        """
        pass

    def __enter__(self):
        """Context manager entry."""
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.disconnect()

    def _log_operation(self, operation: str, **metadata: Any) -> None:
        """
        Log connector operation.

        Args:
            operation: Operation name
            **metadata: Additional metadata to log
        """
        self.logger.info(
            f"Connector operation: {operation}",
            connector_type=self.connector_type,
            operation=operation,
            **metadata
        )

    def _track_metric(self, metric_name: str, value: float = 1.0, **labels: Any) -> None:
        """
        Track connector metric.

        Args:
            metric_name: Name of metric
            value: Metric value
            **labels: Additional labels
        """
        increment_counter(
            f"connector_{metric_name}",
            value=int(value),
            labels={
                "connector_type": self.connector_type,
                **labels
            }
        )


class DatabaseConnector(BaseConnector):
    """Base class for database connectors."""

    @abstractmethod
    def execute_query(self, query: str, params: Optional[Dict] = None) -> Any:
        """
        Execute SQL query.

        Args:
            query: SQL query string
            params: Query parameters

        Returns:
            Query results
        """
        pass

    @abstractmethod
    def read_table(self, table: str, **kwargs: Any) -> Any:
        """
        Read table into DataFrame.

        Args:
            table: Table name
            **kwargs: Additional options

        Returns:
            DataFrame with table data
        """
        pass


class CloudStorageConnector(BaseConnector):
    """Base class for cloud storage connectors."""

    @abstractmethod
    def upload_file(self, local_path: str, remote_path: str, **kwargs: Any) -> bool:
        """
        Upload file to cloud storage.

        Args:
            local_path: Local file path
            remote_path: Remote destination path
            **kwargs: Additional options

        Returns:
            bool: True if successful
        """
        pass

    @abstractmethod
    def download_file(self, remote_path: str, local_path: str, **kwargs: Any) -> bool:
        """
        Download file from cloud storage.

        Args:
            remote_path: Remote file path
            local_path: Local destination path
            **kwargs: Additional options

        Returns:
            bool: True if successful
        """
        pass

    @abstractmethod
    def list_objects(self, prefix: str = "", **kwargs: Any) -> list:
        """
        List objects in storage.

        Args:
            prefix: Path prefix to filter
            **kwargs: Additional options

        Returns:
            list: List of object paths
        """
        pass
