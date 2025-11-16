# DataForge Connectors Library

Universal data source connectors for the DataForge AI Platform.

## Features

- **Databases**: PostgreSQL, MySQL, Oracle, MongoDB, Cassandra
- **Cloud Storage**: AWS S3, Azure Blob Storage, Google Cloud Storage
- **Data Warehouses**: Snowflake, BigQuery, Redshift, Synapse Analytics
- **Streaming**: Kafka, AWS Kinesis

## Installation

```bash
pip install dataforge-connectors
```

### Optional Dependencies

```bash
# For MongoDB support
pip install dataforge-connectors[mongodb]

# For Cassandra support
pip install dataforge-connectors[cassandra]

# For Oracle support
pip install dataforge-connectors[oracle]
```

## Usage

### PostgreSQL Connector

```python
from dataforge_connectors.databases import PostgreSQLConnector

# Connect to database
connector = PostgreSQLConnector(
    host="localhost",
    port=5432,
    database="mydb",
    user="user",
    password="password"
)

# Execute query
results = connector.execute_query("SELECT * FROM users LIMIT 10")

# Read to DataFrame
df = connector.read_table("users", limit=1000)
```

### S3 Connector

```python
from dataforge_connectors.cloud_storage import S3Connector

# Initialize connector
s3 = S3Connector(
    aws_access_key_id="your-key",
    aws_secret_access_key="your-secret",
    region_name="us-east-1"
)

# Upload file
s3.upload_file("/local/path/file.csv", "my-bucket", "data/file.csv")

# Download file
s3.download_file("my-bucket", "data/file.csv", "/local/path/file.csv")

# List objects
objects = s3.list_objects("my-bucket", prefix="data/")
```

### Snowflake Connector

```python
from dataforge_connectors.warehouses import SnowflakeConnector

# Connect to Snowflake
connector = SnowflakeConnector(
    account="your-account",
    user="your-user",
    password="your-password",
    warehouse="your-warehouse",
    database="your-database",
    schema="your-schema"
)

# Execute query
results = connector.execute_query("SELECT * FROM sales")

# Load data from DataFrame
connector.write_dataframe(df, table="sales_new", if_exists="replace")
```

### Kafka Connector

```python
from dataforge_connectors.streaming import KafkaConnector

# Initialize producer
producer = KafkaConnector(
    bootstrap_servers=["localhost:9092"],
    mode="producer"
)

# Send message
producer.send_message("my-topic", {"event": "user_signup", "user_id": "123"})

# Initialize consumer
consumer = KafkaConnector(
    bootstrap_servers=["localhost:9092"],
    mode="consumer",
    topic="my-topic",
    group_id="my-consumer-group"
)

# Consume messages
for message in consumer.consume_messages():
    print(message)
```

## Development

```bash
# Install development dependencies
pip install -e ".[dev]"

# Run tests
pytest

# Test with Docker databases
docker-compose up -d postgres mysql
pytest tests/
```
