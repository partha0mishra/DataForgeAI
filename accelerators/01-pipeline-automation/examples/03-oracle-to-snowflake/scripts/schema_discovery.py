"""
Oracle Schema Discovery and DDL Generation

Production-ready script for discovering Oracle database schemas and generating
Snowflake DDL with:
- Automatic schema introspection
- Data type mapping (Oracle → Snowflake)
- Primary key and index discovery
- Table statistics and row counts
- Generated DDL export to YAML and SQL

Author: DataForgeAI
"""

import logging
import argparse
import yaml
import os
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, asdict
from datetime import datetime

import cx_Oracle

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


# Data type mapping from Oracle to Snowflake
ORACLE_TO_SNOWFLAKE_TYPE_MAPPING = {
    'VARCHAR2': 'VARCHAR',
    'NVARCHAR2': 'VARCHAR',
    'CHAR': 'CHAR',
    'NCHAR': 'CHAR',
    'NUMBER': 'NUMBER',
    'FLOAT': 'FLOAT',
    'BINARY_FLOAT': 'FLOAT',
    'BINARY_DOUBLE': 'DOUBLE',
    'DATE': 'DATE',
    'TIMESTAMP': 'TIMESTAMP_NTZ',
    'TIMESTAMP WITH TIME ZONE': 'TIMESTAMP_TZ',
    'TIMESTAMP WITH LOCAL TIME ZONE': 'TIMESTAMP_LTZ',
    'CLOB': 'VARCHAR',
    'NCLOB': 'VARCHAR',
    'BLOB': 'BINARY',
    'RAW': 'BINARY',
    'LONG': 'VARCHAR',
    'LONG RAW': 'BINARY',
    'ROWID': 'VARCHAR',
    'UROWID': 'VARCHAR',
}


@dataclass
class ColumnMetadata:
    """Metadata for a database column."""
    column_name: str
    data_type: str
    data_length: Optional[int]
    data_precision: Optional[int]
    data_scale: Optional[int]
    nullable: str
    data_default: Optional[str]
    column_id: int


@dataclass
class TableMetadata:
    """Metadata for a database table."""
    owner: str
    table_name: str
    num_rows: Optional[int]
    columns: List[ColumnMetadata]
    primary_key: Optional[List[str]]
    indexes: List[Dict[str, Any]]


class OracleSchemaDiscovery:
    """
    Discover Oracle database schemas and generate migration artifacts.
    """

    def __init__(
        self,
        host: str,
        port: int,
        service_name: str,
        username: str,
        password: str
    ):
        """
        Initialize Oracle connection.

        Args:
            host: Oracle host
            port: Oracle port (default 1521)
            service_name: Oracle service name
            username: Database username
            password: Database password
        """
        self.host = host
        self.port = port
        self.service_name = service_name
        self.username = username
        self.password = password
        self.connection = None

    def connect(self) -> None:
        """Establish connection to Oracle database."""
        try:
            dsn = cx_Oracle.makedsn(self.host, self.port, service_name=self.service_name)
            self.connection = cx_Oracle.connect(
                user=self.username,
                password=self.password,
                dsn=dsn
            )
            logger.info(f"Connected to Oracle: {self.host}:{self.port}/{self.service_name}")

        except cx_Oracle.Error as e:
            logger.error(f"Failed to connect to Oracle: {e}")
            raise

    def disconnect(self) -> None:
        """Close Oracle connection."""
        if self.connection:
            self.connection.close()
            logger.info("Disconnected from Oracle")

    def discover_schemas(self, schema_filter: Optional[List[str]] = None) -> List[str]:
        """
        Discover available schemas in database.

        Args:
            schema_filter: List of schema names to include (optional)

        Returns:
            List of schema names
        """
        logger.info("Discovering schemas...")

        query = """
            SELECT DISTINCT owner
            FROM dba_tables
            WHERE owner NOT IN (
                'SYS', 'SYSTEM', 'OUTLN', 'DIP', 'ORACLE_OCM',
                'DBSNMP', 'APPQOSSYS', 'WMSYS', 'EXFSYS', 'CTXSYS',
                'XDB', 'ANONYMOUS', 'MDSYS', 'ORDSYS', 'ORDDATA',
                'SI_INFORMTN_SCHEMA', 'OLAPSYS', 'FLOWS_FILES', 'APEX_PUBLIC_USER'
            )
            ORDER BY owner
        """

        cursor = self.connection.cursor()
        cursor.execute(query)

        schemas = [row[0] for row in cursor.fetchall()]

        # Apply filter if provided
        if schema_filter:
            schemas = [s for s in schemas if s in schema_filter]

        logger.info(f"Found {len(schemas)} schemas: {', '.join(schemas)}")

        cursor.close()
        return schemas

    def discover_tables(self, schema: str) -> List[str]:
        """
        Discover tables in a schema.

        Args:
            schema: Schema name

        Returns:
            List of table names
        """
        logger.info(f"Discovering tables in schema: {schema}")

        query = """
            SELECT table_name
            FROM all_tables
            WHERE owner = :schema
            ORDER BY table_name
        """

        cursor = self.connection.cursor()
        cursor.execute(query, schema=schema)

        tables = [row[0] for row in cursor.fetchall()]

        logger.info(f"Found {len(tables)} tables in {schema}")

        cursor.close()
        return tables

    def get_table_metadata(self, schema: str, table: str) -> TableMetadata:
        """
        Get complete metadata for a table.

        Args:
            schema: Schema name
            table: Table name

        Returns:
            Table metadata
        """
        logger.info(f"Getting metadata for {schema}.{table}")

        # Get columns
        columns = self._get_columns(schema, table)

        # Get row count and statistics
        num_rows = self._get_row_count(schema, table)

        # Get primary key
        primary_key = self._get_primary_key(schema, table)

        # Get indexes
        indexes = self._get_indexes(schema, table)

        return TableMetadata(
            owner=schema,
            table_name=table,
            num_rows=num_rows,
            columns=columns,
            primary_key=primary_key,
            indexes=indexes
        )

    def _get_columns(self, schema: str, table: str) -> List[ColumnMetadata]:
        """Get column metadata for a table."""
        query = """
            SELECT
                column_name,
                data_type,
                data_length,
                data_precision,
                data_scale,
                nullable,
                data_default,
                column_id
            FROM all_tab_columns
            WHERE owner = :schema
              AND table_name = :table
            ORDER BY column_id
        """

        cursor = self.connection.cursor()
        cursor.execute(query, schema=schema, table=table)

        columns = []
        for row in cursor.fetchall():
            columns.append(ColumnMetadata(
                column_name=row[0],
                data_type=row[1],
                data_length=row[2],
                data_precision=row[3],
                data_scale=row[4],
                nullable=row[5],
                data_default=row[6],
                column_id=row[7]
            ))

        cursor.close()
        return columns

    def _get_row_count(self, schema: str, table: str) -> Optional[int]:
        """Get estimated row count from statistics."""
        query = """
            SELECT num_rows
            FROM all_tables
            WHERE owner = :schema
              AND table_name = :table
        """

        cursor = self.connection.cursor()
        cursor.execute(query, schema=schema, table=table)

        result = cursor.fetchone()
        cursor.close()

        return result[0] if result else None

    def _get_primary_key(self, schema: str, table: str) -> Optional[List[str]]:
        """Get primary key columns."""
        query = """
            SELECT acc.column_name
            FROM all_constraints ac
            JOIN all_cons_columns acc
              ON ac.owner = acc.owner
             AND ac.constraint_name = acc.constraint_name
            WHERE ac.owner = :schema
              AND ac.table_name = :table
              AND ac.constraint_type = 'P'
            ORDER BY acc.position
        """

        cursor = self.connection.cursor()
        cursor.execute(query, schema=schema, table=table)

        pk_columns = [row[0] for row in cursor.fetchall()]

        cursor.close()
        return pk_columns if pk_columns else None

    def _get_indexes(self, schema: str, table: str) -> List[Dict[str, Any]]:
        """Get indexes for a table."""
        query = """
            SELECT
                ai.index_name,
                ai.index_type,
                ai.uniqueness,
                LISTAGG(aic.column_name, ',') WITHIN GROUP (ORDER BY aic.column_position) as columns
            FROM all_indexes ai
            JOIN all_ind_columns aic
              ON ai.owner = aic.index_owner
             AND ai.index_name = aic.index_name
            WHERE ai.table_owner = :schema
              AND ai.table_name = :table
            GROUP BY ai.index_name, ai.index_type, ai.uniqueness
            ORDER BY ai.index_name
        """

        cursor = self.connection.cursor()
        cursor.execute(query, schema=schema, table=table)

        indexes = []
        for row in cursor.fetchall():
            indexes.append({
                'index_name': row[0],
                'index_type': row[1],
                'uniqueness': row[2],
                'columns': row[3].split(',') if row[3] else []
            })

        cursor.close()
        return indexes

    def map_oracle_type_to_snowflake(self, column: ColumnMetadata) -> str:
        """
        Map Oracle data type to Snowflake data type.

        Args:
            column: Column metadata

        Returns:
            Snowflake data type string
        """
        oracle_type = column.data_type

        # Get base Snowflake type
        snowflake_type = ORACLE_TO_SNOWFLAKE_TYPE_MAPPING.get(oracle_type, 'VARCHAR')

        # Add precision/scale for NUMBER types
        if oracle_type == 'NUMBER':
            if column.data_precision is not None:
                if column.data_scale is not None and column.data_scale > 0:
                    snowflake_type = f"NUMBER({column.data_precision},{column.data_scale})"
                else:
                    snowflake_type = f"NUMBER({column.data_precision})"
            else:
                snowflake_type = "NUMBER(38,0)"  # Default precision

        # Add length for VARCHAR types
        elif oracle_type in ('VARCHAR2', 'NVARCHAR2', 'CHAR', 'NCHAR'):
            if column.data_length:
                # Snowflake VARCHAR max is 16MB
                length = min(column.data_length, 16777216)
                snowflake_type = f"{snowflake_type}({length})"

        return snowflake_type

    def generate_snowflake_ddl(self, metadata: TableMetadata) -> str:
        """
        Generate Snowflake DDL for a table.

        Args:
            metadata: Table metadata

        Returns:
            Snowflake CREATE TABLE statement
        """
        ddl_parts = []

        # Table creation
        ddl_parts.append(f"CREATE TABLE IF NOT EXISTS {metadata.owner.lower()}.{metadata.table_name.lower()} (")

        # Columns
        column_defs = []
        for col in metadata.columns:
            sf_type = self.map_oracle_type_to_snowflake(col)
            nullable = "" if col.nullable == 'Y' else " NOT NULL"

            column_def = f"    {col.column_name.lower()} {sf_type}{nullable}"
            column_defs.append(column_def)

        # Primary key
        if metadata.primary_key:
            pk_cols = ", ".join([c.lower() for c in metadata.primary_key])
            column_defs.append(f"    PRIMARY KEY ({pk_cols})")

        ddl_parts.append(",\n".join(column_defs))
        ddl_parts.append(");")

        return "\n".join(ddl_parts)

    def export_to_yaml(
        self,
        tables_metadata: List[TableMetadata],
        output_file: str
    ) -> None:
        """
        Export table metadata to YAML manifest.

        Args:
            tables_metadata: List of table metadata
            output_file: Output YAML file path
        """
        logger.info(f"Exporting metadata to {output_file}")

        manifest = {
            'discovery_date': datetime.utcnow().isoformat(),
            'tables': []
        }

        for metadata in tables_metadata:
            table_dict = {
                'source_schema': metadata.owner,
                'source_table': metadata.table_name,
                'target_schema': metadata.owner.lower(),
                'target_table': metadata.table_name.lower(),
                'num_rows': metadata.num_rows,
                'primary_key': metadata.primary_key,
                'columns': [
                    {
                        'name': col.column_name,
                        'oracle_type': col.data_type,
                        'snowflake_type': self.map_oracle_type_to_snowflake(col),
                        'nullable': col.nullable == 'Y'
                    }
                    for col in metadata.columns
                ]
            }
            manifest['tables'].append(table_dict)

        with open(output_file, 'w') as f:
            yaml.dump(manifest, f, default_flow_style=False, sort_keys=False)

        logger.info(f"Exported {len(tables_metadata)} tables to {output_file}")

    def export_to_sql(
        self,
        tables_metadata: List[TableMetadata],
        output_file: str
    ) -> None:
        """
        Export Snowflake DDL to SQL file.

        Args:
            tables_metadata: List of table metadata
            output_file: Output SQL file path
        """
        logger.info(f"Exporting DDL to {output_file}")

        with open(output_file, 'w') as f:
            f.write("-- Snowflake DDL Generated from Oracle Schema Discovery\n")
            f.write(f"-- Generated: {datetime.utcnow().isoformat()}\n")
            f.write("-- " + "=" * 70 + "\n\n")

            # Create schemas
            schemas = set(m.owner for m in tables_metadata)
            for schema in sorted(schemas):
                f.write(f"CREATE SCHEMA IF NOT EXISTS {schema.lower()};\n")

            f.write("\n")

            # Create tables
            for metadata in tables_metadata:
                f.write(f"\n-- Table: {metadata.owner}.{metadata.table_name}\n")
                f.write(f"-- Rows: {metadata.num_rows or 'Unknown'}\n")
                f.write(self.generate_snowflake_ddl(metadata))
                f.write("\n\n")

        logger.info(f"Exported DDL for {len(tables_metadata)} tables to {output_file}")


def main():
    """Main entry point for schema discovery."""
    parser = argparse.ArgumentParser(
        description='Discover Oracle schemas and generate Snowflake DDL'
    )
    parser.add_argument('--host', required=True, help='Oracle host')
    parser.add_argument('--port', type=int, default=1521, help='Oracle port')
    parser.add_argument('--service-name', required=True, help='Oracle service name')
    parser.add_argument('--username', required=True, help='Database username')
    parser.add_argument('--password', required=True, help='Database password')
    parser.add_argument('--schemas', nargs='+', help='Schemas to discover (default: all)')
    parser.add_argument('--tables', nargs='+', help='Tables to discover (default: all)')
    parser.add_argument('--output-yaml', default='schema_manifest.yaml', help='Output YAML file')
    parser.add_argument('--output-sql', default='snowflake_ddl.sql', help='Output SQL file')

    args = parser.parse_args()

    # Create discoverer
    discoverer = OracleSchemaDiscovery(
        host=args.host,
        port=args.port,
        service_name=args.service_name,
        username=args.username,
        password=args.password
    )

    try:
        # Connect to Oracle
        discoverer.connect()

        # Discover schemas
        schemas = discoverer.discover_schemas(schema_filter=args.schemas)

        # Discover tables in each schema
        all_tables_metadata = []

        for schema in schemas:
            tables = discoverer.discover_tables(schema)

            # Filter tables if specified
            if args.tables:
                tables = [t for t in tables if t in args.tables]

            # Get metadata for each table
            for table in tables:
                try:
                    metadata = discoverer.get_table_metadata(schema, table)
                    all_tables_metadata.append(metadata)
                except Exception as e:
                    logger.error(f"Failed to get metadata for {schema}.{table}: {e}")

        # Export results
        discoverer.export_to_yaml(all_tables_metadata, args.output_yaml)
        discoverer.export_to_sql(all_tables_metadata, args.output_sql)

        logger.info("=" * 80)
        logger.info("Schema discovery completed successfully")
        logger.info(f"Total tables discovered: {len(all_tables_metadata)}")
        logger.info(f"YAML manifest: {args.output_yaml}")
        logger.info(f"SQL DDL: {args.output_sql}")
        logger.info("=" * 80)

    except Exception as e:
        logger.error(f"Schema discovery failed: {e}")
        exit(1)

    finally:
        discoverer.disconnect()


if __name__ == "__main__":
    main()
