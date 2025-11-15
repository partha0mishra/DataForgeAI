"""Data catalog for managing dataset metadata and discovery."""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from dataforge_common.logging import get_logger

logger = get_logger(__name__)


class DatasetType(str, Enum):
    """Dataset type enumeration."""

    TABLE = "table"
    VIEW = "view"
    FILE = "file"
    STREAM = "stream"
    API = "api"


class DatasetStatus(str, Enum):
    """Dataset status."""

    ACTIVE = "active"
    DEPRECATED = "deprecated"
    ARCHIVED = "archived"
    DRAFT = "draft"


@dataclass
class ColumnMetadata:
    """Column metadata."""

    name: str
    data_type: str
    description: str = ""
    nullable: bool = True
    primary_key: bool = False
    foreign_key: Optional[str] = None
    tags: List[str] = field(default_factory=list)
    constraints: List[str] = field(default_factory=list)
    sample_values: List[Any] = field(default_factory=list)
    statistics: Dict[str, Any] = field(default_factory=dict)


@dataclass
class DatasetMetadata:
    """Dataset metadata."""

    dataset_id: str
    name: str
    description: str
    dataset_type: DatasetType
    source: str  # Database, file path, API endpoint
    database: Optional[str] = None
    schema: Optional[str] = None
    table: Optional[str] = None

    # Ownership and governance
    owner: str = "unknown"
    steward: Optional[str] = None
    business_domain: Optional[str] = None

    # Status and lifecycle
    status: DatasetStatus = DatasetStatus.ACTIVE
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    last_accessed: Optional[datetime] = None

    # Schema information
    columns: List[ColumnMetadata] = field(default_factory=list)
    row_count: Optional[int] = None
    size_bytes: Optional[int] = None

    # Classification and tagging
    tags: List[str] = field(default_factory=list)
    labels: Dict[str, str] = field(default_factory=dict)
    sensitivity_level: str = "public"  # public, internal, confidential, restricted

    # Quality and lineage
    quality_score: Optional[float] = None
    upstream_datasets: List[str] = field(default_factory=list)
    downstream_datasets: List[str] = field(default_factory=list)

    # Usage metrics
    access_count: int = 0
    popularity_score: float = 0.0

    # Custom metadata
    custom_properties: Dict[str, Any] = field(default_factory=dict)


class DataCatalog:
    """
    Data catalog for dataset discovery and metadata management.

    Provides:
    - Dataset registration and metadata storage
    - Search and discovery
    - Lineage tracking integration
    - Tags and classification
    - Usage tracking

    Example:
        catalog = DataCatalog()

        # Register dataset
        dataset_id = catalog.register_dataset(
            name="customer_profiles",
            description="Customer profile data from CRM",
            dataset_type=DatasetType.TABLE,
            source="postgres://crm/customers",
            owner="data_team",
            tags=["customer", "pii"]
        )

        # Search datasets
        results = catalog.search_datasets("customer")

        # Get dataset metadata
        metadata = catalog.get_dataset(dataset_id)
    """

    def __init__(self, storage_backend: str = "postgres"):
        """
        Initialize data catalog.

        Args:
            storage_backend: Storage backend (postgres, elasticsearch)
        """
        self.storage_backend = storage_backend
        self.logger = logger

        # In-memory storage (replace with actual DB)
        self.datasets: Dict[str, DatasetMetadata] = {}

        self.logger.info("Data catalog initialized", backend=storage_backend)

    def register_dataset(
        self,
        name: str,
        description: str,
        dataset_type: DatasetType,
        source: str,
        owner: str,
        database: Optional[str] = None,
        schema: Optional[str] = None,
        table: Optional[str] = None,
        columns: Optional[List[ColumnMetadata]] = None,
        tags: Optional[List[str]] = None,
        labels: Optional[Dict[str, str]] = None,
        custom_properties: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        Register a dataset in the catalog.

        Args:
            name: Dataset name
            description: Dataset description
            dataset_type: Type of dataset
            source: Data source location
            owner: Dataset owner
            database: Database name
            schema: Schema name
            table: Table name
            columns: Column metadata
            tags: Tags for classification
            labels: Key-value labels
            custom_properties: Custom metadata

        Returns:
            Dataset ID
        """
        # Generate dataset ID
        if database and schema and table:
            dataset_id = f"{database}.{schema}.{table}"
        else:
            dataset_id = f"{dataset_type.value}_{name}_{datetime.utcnow().timestamp()}"

        # Create metadata
        metadata = DatasetMetadata(
            dataset_id=dataset_id,
            name=name,
            description=description,
            dataset_type=dataset_type,
            source=source,
            database=database,
            schema=schema,
            table=table,
            owner=owner,
            columns=columns or [],
            tags=tags or [],
            labels=labels or {},
            custom_properties=custom_properties or {},
        )

        # Store metadata
        self.datasets[dataset_id] = metadata

        self.logger.info(
            "Dataset registered",
            dataset_id=dataset_id,
            dataset_type=dataset_type.value,
            owner=owner,
        )

        return dataset_id

    def update_dataset(
        self,
        dataset_id: str,
        **updates,
    ) -> None:
        """
        Update dataset metadata.

        Args:
            dataset_id: Dataset identifier
            **updates: Fields to update
        """
        if dataset_id not in self.datasets:
            raise ValueError(f"Dataset not found: {dataset_id}")

        metadata = self.datasets[dataset_id]

        # Update fields
        for key, value in updates.items():
            if hasattr(metadata, key):
                setattr(metadata, key, value)

        metadata.updated_at = datetime.utcnow()

        self.logger.info("Dataset updated", dataset_id=dataset_id)

    def get_dataset(self, dataset_id: str) -> DatasetMetadata:
        """
        Get dataset metadata.

        Args:
            dataset_id: Dataset identifier

        Returns:
            Dataset metadata
        """
        if dataset_id not in self.datasets:
            raise ValueError(f"Dataset not found: {dataset_id}")

        metadata = self.datasets[dataset_id]

        # Update access tracking
        metadata.last_accessed = datetime.utcnow()
        metadata.access_count += 1

        return metadata

    def search_datasets(
        self,
        query: str,
        filters: Optional[Dict[str, Any]] = None,
        limit: int = 100,
    ) -> List[DatasetMetadata]:
        """
        Search datasets by query.

        Args:
            query: Search query (searches name, description, tags)
            filters: Additional filters (owner, tags, dataset_type, etc.)
            limit: Maximum results

        Returns:
            List of matching datasets
        """
        results = []
        query_lower = query.lower()

        for metadata in self.datasets.values():
            # Text search
            if (
                query_lower in metadata.name.lower()
                or query_lower in metadata.description.lower()
                or any(query_lower in tag.lower() for tag in metadata.tags)
            ):
                # Apply filters
                if filters:
                    if not self._matches_filters(metadata, filters):
                        continue

                results.append(metadata)

                if len(results) >= limit:
                    break

        # Sort by popularity and relevance
        results.sort(
            key=lambda x: (x.popularity_score, x.access_count), reverse=True
        )

        self.logger.info("Search completed", query=query, results=len(results))

        return results

    def _matches_filters(
        self,
        metadata: DatasetMetadata,
        filters: Dict[str, Any],
    ) -> bool:
        """Check if dataset matches filters."""
        for key, value in filters.items():
            if key == "owner" and metadata.owner != value:
                return False
            elif key == "dataset_type" and metadata.dataset_type != value:
                return False
            elif key == "tags" and not any(t in metadata.tags for t in value):
                return False
            elif key == "status" and metadata.status != value:
                return False

        return True

    def list_datasets(
        self,
        dataset_type: Optional[DatasetType] = None,
        owner: Optional[str] = None,
        tags: Optional[List[str]] = None,
    ) -> List[DatasetMetadata]:
        """
        List datasets with optional filters.

        Args:
            dataset_type: Filter by dataset type
            owner: Filter by owner
            tags: Filter by tags

        Returns:
            List of datasets
        """
        results = list(self.datasets.values())

        if dataset_type:
            results = [d for d in results if d.dataset_type == dataset_type]

        if owner:
            results = [d for d in results if d.owner == owner]

        if tags:
            results = [d for d in results if any(t in d.tags for t in tags)]

        return results

    def add_tags(self, dataset_id: str, tags: List[str]) -> None:
        """Add tags to dataset."""
        if dataset_id not in self.datasets:
            raise ValueError(f"Dataset not found: {dataset_id}")

        metadata = self.datasets[dataset_id]
        metadata.tags.extend([t for t in tags if t not in metadata.tags])
        metadata.updated_at = datetime.utcnow()

        self.logger.info("Tags added", dataset_id=dataset_id, tags=tags)

    def remove_tags(self, dataset_id: str, tags: List[str]) -> None:
        """Remove tags from dataset."""
        if dataset_id not in self.datasets:
            raise ValueError(f"Dataset not found: {dataset_id}")

        metadata = self.datasets[dataset_id]
        metadata.tags = [t for t in metadata.tags if t not in tags]
        metadata.updated_at = datetime.utcnow()

        self.logger.info("Tags removed", dataset_id=dataset_id, tags=tags)

    def update_lineage(
        self,
        dataset_id: str,
        upstream: Optional[List[str]] = None,
        downstream: Optional[List[str]] = None,
    ) -> None:
        """
        Update dataset lineage.

        Args:
            dataset_id: Dataset identifier
            upstream: Upstream dataset IDs
            downstream: Downstream dataset IDs
        """
        if dataset_id not in self.datasets:
            raise ValueError(f"Dataset not found: {dataset_id}")

        metadata = self.datasets[dataset_id]

        if upstream is not None:
            metadata.upstream_datasets = upstream

        if downstream is not None:
            metadata.downstream_datasets = downstream

        metadata.updated_at = datetime.utcnow()

        self.logger.info("Lineage updated", dataset_id=dataset_id)

    def calculate_popularity(self, dataset_id: str) -> float:
        """
        Calculate popularity score based on access patterns.

        Args:
            dataset_id: Dataset identifier

        Returns:
            Popularity score (0-1)
        """
        if dataset_id not in self.datasets:
            return 0.0

        metadata = self.datasets[dataset_id]

        # Simple popularity calculation
        # Can be enhanced with time decay, user feedback, etc.
        access_score = min(metadata.access_count / 100.0, 1.0)

        # Factor in how recently accessed
        if metadata.last_accessed:
            days_since_access = (datetime.utcnow() - metadata.last_accessed).days
            recency_score = max(0, 1.0 - (days_since_access / 365.0))
        else:
            recency_score = 0.0

        popularity = (access_score * 0.7) + (recency_score * 0.3)

        metadata.popularity_score = popularity
        return popularity

    def delete_dataset(self, dataset_id: str) -> None:
        """Delete dataset from catalog."""
        if dataset_id in self.datasets:
            del self.datasets[dataset_id]

        self.logger.info("Dataset deleted", dataset_id=dataset_id)

    def get_statistics(self) -> Dict[str, Any]:
        """Get catalog statistics."""
        total_datasets = len(self.datasets)

        datasets_by_type = {}
        datasets_by_owner = {}

        for metadata in self.datasets.values():
            # By type
            type_key = metadata.dataset_type.value
            datasets_by_type[type_key] = datasets_by_type.get(type_key, 0) + 1

            # By owner
            datasets_by_owner[metadata.owner] = datasets_by_owner.get(metadata.owner, 0) + 1

        return {
            "total_datasets": total_datasets,
            "datasets_by_type": datasets_by_type,
            "datasets_by_owner": datasets_by_owner,
            "total_tables": sum(1 for d in self.datasets.values() if d.dataset_type == DatasetType.TABLE),
            "total_views": sum(1 for d in self.datasets.values() if d.dataset_type == DatasetType.VIEW),
        }
