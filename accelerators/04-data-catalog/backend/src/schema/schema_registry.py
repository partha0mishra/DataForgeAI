"""Schema registry for managing data schemas and contracts."""

import json
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from dataforge_common.logging import get_logger

logger = get_logger(__name__)


class SchemaType(str, Enum):
    """Schema type enumeration."""

    AVRO = "avro"
    JSON_SCHEMA = "json_schema"
    PROTOBUF = "protobuf"
    PARQUET = "parquet"
    SQL = "sql"


class CompatibilityMode(str, Enum):
    """Schema compatibility modes."""

    BACKWARD = "backward"  # New schema can read old data
    FORWARD = "forward"  # Old schema can read new data
    FULL = "full"  # Both backward and forward compatible
    NONE = "none"  # No compatibility checks


@dataclass
class SchemaVersion:
    """Schema version information."""

    version_id: int
    schema_id: str
    schema: Dict[str, Any]
    schema_type: SchemaType
    created_at: datetime
    created_by: str
    metadata: Dict[str, Any]


@dataclass
class SchemaMetadata:
    """Schema metadata."""

    schema_id: str
    name: str
    namespace: str
    description: str
    schema_type: SchemaType
    compatibility_mode: CompatibilityMode
    latest_version: int
    tags: List[str]
    owner: str
    created_at: datetime
    updated_at: datetime


class SchemaRegistry:
    """
    Schema registry for managing and versioning data schemas.

    Provides:
    - Schema registration and versioning
    - Compatibility validation
    - Schema evolution tracking
    - Schema search and discovery

    Example:
        registry = SchemaRegistry()

        # Register new schema
        schema_id = registry.register_schema(
            name="customer_profile",
            namespace="com.dataforge.customer",
            schema=customer_schema,
            schema_type=SchemaType.JSON_SCHEMA
        )

        # Get latest schema
        schema = registry.get_schema(schema_id)

        # Validate compatibility
        is_compatible = registry.validate_compatibility(
            schema_id, new_schema
        )
    """

    def __init__(self, storage_backend: str = "postgres"):
        """
        Initialize schema registry.

        Args:
            storage_backend: Storage backend (postgres, file)
        """
        self.storage_backend = storage_backend
        self.logger = logger

        # In-memory storage (replace with actual DB)
        self.schemas: Dict[str, SchemaMetadata] = {}
        self.versions: Dict[str, List[SchemaVersion]] = {}

        self.logger.info("Schema registry initialized", backend=storage_backend)

    def register_schema(
        self,
        name: str,
        namespace: str,
        schema: Dict[str, Any],
        schema_type: SchemaType,
        description: str = "",
        compatibility_mode: CompatibilityMode = CompatibilityMode.BACKWARD,
        owner: str = "system",
        tags: Optional[List[str]] = None,
    ) -> str:
        """
        Register a new schema or update existing schema with new version.

        Args:
            name: Schema name
            namespace: Schema namespace
            schema: Schema definition
            schema_type: Type of schema
            description: Schema description
            compatibility_mode: Compatibility validation mode
            owner: Schema owner
            tags: Schema tags

        Returns:
            Schema ID
        """
        schema_id = f"{namespace}.{name}"

        # Check if schema exists
        if schema_id in self.schemas:
            # Update existing schema with new version
            return self._add_schema_version(schema_id, schema, schema_type, owner)

        # Create new schema
        metadata = SchemaMetadata(
            schema_id=schema_id,
            name=name,
            namespace=namespace,
            description=description,
            schema_type=schema_type,
            compatibility_mode=compatibility_mode,
            latest_version=1,
            tags=tags or [],
            owner=owner,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )

        # Store metadata
        self.schemas[schema_id] = metadata

        # Create first version
        version = SchemaVersion(
            version_id=1,
            schema_id=schema_id,
            schema=schema,
            schema_type=schema_type,
            created_at=datetime.utcnow(),
            created_by=owner,
            metadata={},
        )

        self.versions[schema_id] = [version]

        self.logger.info(
            "Schema registered",
            schema_id=schema_id,
            version=1,
            schema_type=schema_type.value,
        )

        return schema_id

    def _add_schema_version(
        self,
        schema_id: str,
        schema: Dict[str, Any],
        schema_type: SchemaType,
        created_by: str,
    ) -> str:
        """Add new version to existing schema."""
        if schema_id not in self.schemas:
            raise ValueError(f"Schema not found: {schema_id}")

        metadata = self.schemas[schema_id]

        # Validate compatibility
        if metadata.compatibility_mode != CompatibilityMode.NONE:
            is_compatible = self.validate_compatibility(schema_id, schema)
            if not is_compatible:
                raise ValueError(
                    f"Schema not compatible with mode: {metadata.compatibility_mode}"
                )

        # Create new version
        new_version_id = metadata.latest_version + 1
        version = SchemaVersion(
            version_id=new_version_id,
            schema_id=schema_id,
            schema=schema,
            schema_type=schema_type,
            created_at=datetime.utcnow(),
            created_by=created_by,
            metadata={},
        )

        self.versions[schema_id].append(version)

        # Update metadata
        metadata.latest_version = new_version_id
        metadata.updated_at = datetime.utcnow()

        self.logger.info(
            "Schema version added",
            schema_id=schema_id,
            version=new_version_id,
        )

        return schema_id

    def get_schema(
        self,
        schema_id: str,
        version: Optional[int] = None,
    ) -> SchemaVersion:
        """
        Get schema by ID and optional version.

        Args:
            schema_id: Schema identifier
            version: Specific version (latest if not specified)

        Returns:
            Schema version
        """
        if schema_id not in self.versions:
            raise ValueError(f"Schema not found: {schema_id}")

        versions = self.versions[schema_id]

        if version is None:
            # Return latest version
            return versions[-1]

        # Find specific version
        for v in versions:
            if v.version_id == version:
                return v

        raise ValueError(f"Schema version not found: {schema_id} v{version}")

    def get_schema_metadata(self, schema_id: str) -> SchemaMetadata:
        """Get schema metadata."""
        if schema_id not in self.schemas:
            raise ValueError(f"Schema not found: {schema_id}")

        return self.schemas[schema_id]

    def list_schemas(
        self,
        namespace: Optional[str] = None,
        tags: Optional[List[str]] = None,
    ) -> List[SchemaMetadata]:
        """
        List schemas with optional filters.

        Args:
            namespace: Filter by namespace
            tags: Filter by tags

        Returns:
            List of schema metadata
        """
        results = list(self.schemas.values())

        if namespace:
            results = [s for s in results if s.namespace == namespace]

        if tags:
            results = [s for s in results if any(t in s.tags for t in tags)]

        return results

    def validate_compatibility(
        self,
        schema_id: str,
        new_schema: Dict[str, Any],
    ) -> bool:
        """
        Validate schema compatibility.

        Args:
            schema_id: Existing schema ID
            new_schema: New schema to validate

        Returns:
            True if compatible
        """
        if schema_id not in self.schemas:
            return True  # New schema, always compatible

        metadata = self.schemas[schema_id]
        latest_version = self.get_schema(schema_id)

        mode = metadata.compatibility_mode

        if mode == CompatibilityMode.NONE:
            return True

        # Simple compatibility check (can be enhanced with proper validation)
        old_schema = latest_version.schema
        new_fields = set(new_schema.get("properties", {}).keys())
        old_fields = set(old_schema.get("properties", {}).keys())

        if mode == CompatibilityMode.BACKWARD:
            # New schema can have fewer required fields
            old_required = set(old_schema.get("required", []))
            new_required = set(new_schema.get("required", []))
            return new_required.issubset(old_required)

        elif mode == CompatibilityMode.FORWARD:
            # New schema can have more optional fields
            return old_fields.issubset(new_fields)

        elif mode == CompatibilityMode.FULL:
            # Must be both backward and forward compatible
            return old_fields == new_fields

        return True

    def delete_schema(self, schema_id: str) -> None:
        """Delete schema and all versions."""
        if schema_id in self.schemas:
            del self.schemas[schema_id]
        if schema_id in self.versions:
            del self.versions[schema_id]

        self.logger.info("Schema deleted", schema_id=schema_id)

    def export_schema(self, schema_id: str, version: Optional[int] = None) -> str:
        """Export schema as JSON string."""
        schema_version = self.get_schema(schema_id, version)
        return json.dumps(schema_version.schema, indent=2)
