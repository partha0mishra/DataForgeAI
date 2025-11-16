"""AWS S3 connector implementation."""

import os
from pathlib import Path
from typing import Any, Dict, List, Optional

import boto3
from botocore.exceptions import ClientError

from dataforge_connectors.base import CloudStorageConnector


class S3Connector(CloudStorageConnector):
    """
    AWS S3 cloud storage connector.

    Provides methods to upload, download, and manage files in S3.

    Example:
        connector = S3Connector(
            aws_access_key_id="your-key",
            aws_secret_access_key="your-secret",
            region_name="us-east-1"
        )

        # Upload file
        connector.upload_file("/local/file.csv", "my-bucket/data/file.csv")

        # Download file
        connector.download_file("my-bucket/data/file.csv", "/local/file.csv")

        # List objects
        objects = connector.list_objects("my-bucket", prefix="data/")
    """

    def __init__(
        self,
        aws_access_key_id: Optional[str] = None,
        aws_secret_access_key: Optional[str] = None,
        region_name: str = "us-east-1",
        **kwargs: Any
    ):
        """
        Initialize S3 connector.

        Args:
            aws_access_key_id: AWS access key
            aws_secret_access_key: AWS secret key
            region_name: AWS region
            **kwargs: Additional boto3 options
        """
        super().__init__(connector_type="s3")

        self.aws_access_key_id = aws_access_key_id
        self.aws_secret_access_key = aws_secret_access_key
        self.region_name = region_name
        self.client_kwargs = kwargs

        self._client: Optional[Any] = None

    def connect(self) -> Any:
        """
        Create S3 client.

        Returns:
            boto3 S3 client
        """
        if self._client is not None:
            return self._client

        self.logger.info("Creating S3 client", region=self.region_name)

        self._client = boto3.client(
            's3',
            aws_access_key_id=self.aws_access_key_id,
            aws_secret_access_key=self.aws_secret_access_key,
            region_name=self.region_name,
            **self.client_kwargs
        )

        self._log_operation("connect")
        self._track_metric("connections_total")

        return self._client

    def disconnect(self) -> None:
        """Close S3 client."""
        if self._client is not None:
            self._client.close()
            self._client = None
            self._log_operation("disconnect")

    def test_connection(self) -> bool:
        """
        Test S3 connection by listing buckets.

        Returns:
            bool: True if connection successful
        """
        try:
            client = self.connect()
            client.list_buckets()
            return True
        except Exception as e:
            self.logger.error(f"Connection test failed: {str(e)}")
            return False

    def upload_file(
        self,
        local_path: str,
        remote_path: str,
        bucket: Optional[str] = None,
        **kwargs: Any
    ) -> bool:
        """
        Upload file to S3.

        Args:
            local_path: Local file path
            remote_path: S3 key (can include bucket: "bucket/key")
            bucket: Bucket name (optional if included in remote_path)
            **kwargs: Additional upload options

        Returns:
            bool: True if successful
        """
        client = self.connect()

        # Parse bucket and key
        if bucket is None:
            parts = remote_path.split('/', 1)
            bucket = parts[0]
            key = parts[1] if len(parts) > 1 else ""
        else:
            key = remote_path

        self._log_operation(
            "upload_file",
            local_path=local_path,
            bucket=bucket,
            key=key
        )

        try:
            file_size = os.path.getsize(local_path)

            client.upload_file(local_path, bucket, key, **kwargs)

            self._track_metric("files_uploaded")
            self._track_metric("bytes_uploaded", value=file_size)

            self.logger.info(
                "File uploaded",
                local_path=local_path,
                bucket=bucket,
                key=key,
                size_bytes=file_size
            )

            return True

        except ClientError as e:
            self.logger.error(
                "Upload failed",
                error=str(e),
                local_path=local_path,
                bucket=bucket,
                key=key
            )
            return False

    def download_file(
        self,
        remote_path: str,
        local_path: str,
        bucket: Optional[str] = None,
        **kwargs: Any
    ) -> bool:
        """
        Download file from S3.

        Args:
            remote_path: S3 key (can include bucket: "bucket/key")
            local_path: Local destination path
            bucket: Bucket name (optional if included in remote_path)
            **kwargs: Additional download options

        Returns:
            bool: True if successful
        """
        client = self.connect()

        # Parse bucket and key
        if bucket is None:
            parts = remote_path.split('/', 1)
            bucket = parts[0]
            key = parts[1] if len(parts) > 1 else ""
        else:
            key = remote_path

        self._log_operation(
            "download_file",
            bucket=bucket,
            key=key,
            local_path=local_path
        )

        try:
            # Create directory if it doesn't exist
            Path(local_path).parent.mkdir(parents=True, exist_ok=True)

            client.download_file(bucket, key, local_path, **kwargs)

            file_size = os.path.getsize(local_path)

            self._track_metric("files_downloaded")
            self._track_metric("bytes_downloaded", value=file_size)

            self.logger.info(
                "File downloaded",
                bucket=bucket,
                key=key,
                local_path=local_path,
                size_bytes=file_size
            )

            return True

        except ClientError as e:
            self.logger.error(
                "Download failed",
                error=str(e),
                bucket=bucket,
                key=key,
                local_path=local_path
            )
            return False

    def list_objects(
        self,
        bucket: str,
        prefix: str = "",
        max_keys: int = 1000,
        **kwargs: Any
    ) -> List[Dict[str, Any]]:
        """
        List objects in S3 bucket.

        Args:
            bucket: Bucket name
            prefix: Key prefix to filter
            max_keys: Maximum number of keys to return
            **kwargs: Additional list options

        Returns:
            list: List of object metadata dictionaries
        """
        client = self.connect()

        self._log_operation(
            "list_objects",
            bucket=bucket,
            prefix=prefix,
            max_keys=max_keys
        )

        try:
            response = client.list_objects_v2(
                Bucket=bucket,
                Prefix=prefix,
                MaxKeys=max_keys,
                **kwargs
            )

            objects = response.get('Contents', [])

            self._track_metric("list_operations")

            self.logger.info(
                "Objects listed",
                bucket=bucket,
                prefix=prefix,
                count=len(objects)
            )

            return objects

        except ClientError as e:
            self.logger.error(
                "List operation failed",
                error=str(e),
                bucket=bucket,
                prefix=prefix
            )
            return []

    def delete_object(self, bucket: str, key: str) -> bool:
        """
        Delete object from S3.

        Args:
            bucket: Bucket name
            key: Object key

        Returns:
            bool: True if successful
        """
        client = self.connect()

        self._log_operation("delete_object", bucket=bucket, key=key)

        try:
            client.delete_object(Bucket=bucket, Key=key)

            self._track_metric("objects_deleted")

            self.logger.info("Object deleted", bucket=bucket, key=key)

            return True

        except ClientError as e:
            self.logger.error(
                "Delete failed",
                error=str(e),
                bucket=bucket,
                key=key
            )
            return False

    def get_object_metadata(self, bucket: str, key: str) -> Optional[Dict[str, Any]]:
        """
        Get object metadata.

        Args:
            bucket: Bucket name
            key: Object key

        Returns:
            dict: Object metadata or None if not found
        """
        client = self.connect()

        try:
            response = client.head_object(Bucket=bucket, Key=key)

            return {
                "key": key,
                "size": response.get("ContentLength"),
                "last_modified": response.get("LastModified"),
                "content_type": response.get("ContentType"),
                "etag": response.get("ETag"),
                "metadata": response.get("Metadata", {})
            }

        except ClientError as e:
            self.logger.error(
                "Get metadata failed",
                error=str(e),
                bucket=bucket,
                key=key
            )
            return None
