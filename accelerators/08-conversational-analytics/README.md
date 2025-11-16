## Accelerator 8: Conversational Analytics

Ask questions about your data in natural language and get instant SQL-powered answers.

## Overview

The Conversational Analytics accelerator enables natural language querying of databases using advanced NLP and LLM-powered SQL generation. Simply ask questions in plain English and get SQL queries, results, and explanations automatically.

## Features

### Natural Language Processing
- **Intent Detection**: Automatically identifies query intent (select, aggregate, filter, sort, etc.)
- **Entity Extraction**: Extracts tables, columns, values, dates from questions
- **Context Awareness**: Maintains conversation context across multiple questions
- **Confidence Scoring**: Provides confidence scores for query understanding
- **11 Query Intent Types**:
  - SELECT: Retrieve data
  - AGGREGATE: Sum, count, average operations
  - FILTER: Conditional filtering
  - SORT: Ordering and ranking
  - GROUP: Group by operations
  - JOIN: Multi-table queries
  - TIME_SERIES: Time-based analysis
  - COMPARE: Comparisons between entities
  - TOP_N: Top/bottom N results
  - TREND: Trend analysis
  - DISTRIBUTION: Distribution analysis

### LLM-Powered SQL Generation
- **Intelligent Translation**: Converts natural language to syntactically correct SQL
- **Multi-Dialect Support**: PostgreSQL, MySQL, SQLite, and more
- **Schema-Aware**: Uses database schema for accurate table/column references
- **Safety Validation**: Blocks destructive operations (DELETE, DROP, etc.)
- **Query Optimization**: AI-powered SQL optimization suggestions
- **Natural Language Explanations**: Converts SQL back to plain English

### Query Execution
- **Multi-Database Support**: Connect to PostgreSQL, MySQL, SQLite, and more
- **Connection Management**: Named connections with pooling
- **Result Formatting**: Multiple output formats (table, summary, text, JSON, markdown)
- **Performance Tracking**: Execution time monitoring
- **Error Handling**: Clear error messages and recovery

### Conversational Features
- **Session Management**: Maintain conversation state across questions
- **Question History**: Track all questions and results in session
- **Query Suggestions**: Auto-complete and suggestions based on schema
- **Question Validation**: Pre-flight validation before execution
- **Schema Discovery**: Automatic database schema exploration

## Quick Start

### Prerequisites

```bash
# Install dependencies
pip install -r requirements.txt

# Set OpenAI API key (required for SQL generation)
export OPENAI_API_KEY='your-api-key-here'
```

### Run Example

```bash
cd accelerators/08-conversational-analytics
python examples/analytics_example.py
```

This will:
1. Create a sample SQLite sales database
2. Initialize conversational analytics engine
3. Ask 5 natural language questions
4. Generate and execute SQL queries
5. Display results with explanations

### Start API Server

```bash
cd accelerators/08-conversational-analytics
uvicorn src.api.main:app --reload --port 8008
```

Visit http://localhost:8008/docs for interactive API documentation.

## Usage

### Basic Question Answering

```python
from query.query_processor import QueryProcessor
from sql.sql_generator import SQLGenerator
from execution.query_executor import QueryExecutor
from conversational.analytics_engine import ConversationalAnalyticsEngine
import os

# Initialize components
processor = QueryProcessor()
generator = SQLGenerator(llm_api_key=os.getenv("OPENAI_API_KEY"))
executor = QueryExecutor()

engine = ConversationalAnalyticsEngine(
    query_processor=processor,
    sql_generator=generator,
    query_executor=executor,
)

# Connect to database
executor.connect(
    name="default",
    host="localhost",
    port=5432,
    database="mydb",
    username="user",
    password="password",
    dialect="postgresql",
)

# Ask a question
response = engine.ask(
    question="What are the top 10 customers by total sales?",
    connection_name="default",
)

print(f"SQL: {response.sql_query}")
print(f"Explanation: {response.explanation}")
print(f"Results:\n{response.results}")
```

### Using Sessions

```python
# Create session
session_id = engine.create_session()

# Ask questions in context
response1 = engine.ask(
    question="Show me all products",
    session_id=session_id,
)

response2 = engine.ask(
    question="Filter by category Electronics",
    session_id=session_id,  # Maintains context
)

# Get conversation history
history = engine.get_conversation_history(session_id)
```

### Direct SQL Execution

```python
# Execute SQL directly
result = executor.execute_query(
    query="SELECT * FROM customers LIMIT 10",
    connection_name="default",
)

# Format results
formatted = executor.format_result(result, format="markdown")
print(formatted.content)
```

### SQL Optimization

```python
# Optimize existing SQL
original_query = "SELECT * FROM orders WHERE customer_id = 123"

optimized = generator.optimize_sql(
    query=original_query,
    schema=executor.get_schema("default"),
)

print(f"Optimized: {optimized.query}")
```

### Question Validation

```python
# Validate question before execution
validation = engine.validate_question(
    question="Show me the revenue trends",
    connection_name="default",
)

if validation['is_valid']:
    response = engine.ask(question)
else:
    print(f"Issues: {validation['issues']}")
    print(f"Suggestions: {validation['suggestions']}")
```

## API Usage

### Ask a Question

```bash
curl -X POST "http://localhost:8008/ask" \
  -H "Content-Type: application/json" \
  -d '{
    "question": "What are the top 5 products by revenue?",
    "connection_name": "default",
    "result_format": "table"
  }'
```

### Execute SQL Directly

```bash
curl -X POST "http://localhost:8008/sql/execute" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "SELECT * FROM products LIMIT 10",
    "connection_name": "default",
    "result_format": "json"
  }'
```

### Create Database Connection

```bash
curl -X POST "http://localhost:8008/connections" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "mydb",
    "dialect": "postgresql",
    "host": "localhost",
    "port": 5432,
    "database": "mydb",
    "username": "user",
    "password": "password"
  }'
```

### Get Schema

```bash
curl "http://localhost:8008/connections/default/schema"
```

### Get Suggestions

```bash
curl "http://localhost:8008/suggestions?partial_query=show&connection_name=default"
```

## API Endpoints

### Questions
- `POST /ask` - Ask natural language question
- `POST /validate` - Validate question before execution
- `GET /suggestions` - Get query suggestions

### SQL Operations
- `POST /sql/execute` - Execute SQL query
- `POST /sql/explain` - Explain SQL in natural language
- `POST /sql/optimize` - Optimize SQL query

### Database Connections
- `POST /connections` - Create database connection
- `DELETE /connections/{name}` - Delete connection
- `GET /connections/{name}/schema` - Get database schema
- `GET /schema/summary` - Get schema summary

### Sessions
- `POST /sessions` - Create conversation session
- `GET /sessions/{id}/history` - Get session history
- `POST /sessions/{id}/clear` - Clear session history
- `DELETE /sessions/{id}` - Delete session

### Utility
- `GET /health` - Health check

## Configuration

### Query Processor

The query processor uses pattern matching and NLP to understand questions:

```python
processor = QueryProcessor()

parsed = processor.parse_query(
    query="Show me customers from last month",
    schema=schema,  # Optional database schema
)

print(f"Intent: {parsed.intent}")
print(f"Tables: {parsed.tables}")
print(f"Time Range: {parsed.time_range}")
```

### SQL Generator

Configure the LLM-based SQL generator:

```python
generator = SQLGenerator(
    llm_api_key="your-key",
    llm_model="gpt-4",  # or "gpt-3.5-turbo"
    temperature=0.1,    # Low for consistent SQL
)

generated = generator.generate_sql(
    natural_query="Count customers by region",
    schema=schema,
    dialect="postgresql",
    validate=True,  # Validate for safety
)
```

### Query Executor

Configure database connections and execution:

```python
executor = QueryExecutor()

# PostgreSQL
executor.connect(
    name="postgres",
    dialect="postgresql",
    host="localhost",
    port=5432,
    database="mydb",
    username="user",
    password="password",
)

# MySQL
executor.connect(
    name="mysql",
    dialect="mysql",
    host="localhost",
    port=3306,
    database="mydb",
    username="user",
    password="password",
)

# SQLite
executor.connect(
    name="sqlite",
    dialect="sqlite",
    database="/path/to/database.db",
)
```

## Query Intent Types

### SELECT
**Patterns**: show, display, list, get, what, which
**Example**: "Show me all customers"

### AGGREGATE
**Patterns**: total, sum, average, count, how many
**Example**: "What is the total revenue?"

### FILTER
**Patterns**: where, with, having, greater than, less than
**Example**: "Show customers with revenue > 10000"

### SORT
**Patterns**: sort, order, rank, top, bottom, highest, lowest
**Example**: "Show top 10 products by sales"

### GROUP
**Patterns**: group by, per, by, each
**Example**: "Show revenue by region"

### TREND
**Patterns**: trend, over time, growth, decline, increase
**Example**: "Show sales trend over last 6 months"

### COMPARE
**Patterns**: compare, versus, vs, difference
**Example**: "Compare sales between regions"

### TIME_SERIES
**Patterns**: daily, weekly, monthly, by day, by month
**Example**: "Show daily sales for last month"

## Result Formats

### Table
Pandas DataFrame with tabular data
```python
result_format="table"
# Returns: DataFrame with all columns
```

### Summary
Statistical summary with metadata
```python
result_format="summary"
# Returns: Row count, column types, statistics
```

### Text
Plain text table representation
```python
result_format="text"
# Returns: Human-readable text table
```

### JSON
JSON array of records
```python
result_format="json"
# Returns: [{"col1": "val1", "col2": "val2"}, ...]
```

### Markdown
Markdown-formatted table
```python
result_format="markdown"
# Returns: | col1 | col2 |\n|------|------|\n| val1 | val2 |
```

## Architecture

```
src/
├── query/
│   └── query_processor.py       # NLP query understanding
├── sql/
│   └── sql_generator.py         # LLM-powered SQL generation
├── execution/
│   └── query_executor.py        # Multi-database query execution
├── conversational/
│   └── analytics_engine.py      # Main orchestrator
└── api/
    └── main.py                  # FastAPI REST API
```

## Environment Variables

```bash
# Required
OPENAI_API_KEY=your-openai-api-key

# Optional
OPENAI_MODEL=gpt-4              # Default: gpt-4
API_HOST=0.0.0.0                # Default: 0.0.0.0
API_PORT=8008                   # Default: 8008

# Database connections (examples)
DB_HOST=localhost
DB_PORT=5432
DB_NAME=mydb
DB_USER=user
DB_PASSWORD=password
```

## Deployment

### Docker

```bash
docker build -t dataforge-conversational .
docker run -p 8008:8008 \
  -e OPENAI_API_KEY=your-key \
  -e DB_HOST=your-db-host \
  dataforge-conversational
```

### Kubernetes

```bash
kubectl apply -f k8s/
```

## Security

### SQL Safety
- **Whitelist Approach**: Only SELECT queries allowed by default
- **Destructive Operations Blocked**: DELETE, DROP, TRUNCATE, ALTER automatically rejected
- **Parameterized Queries**: Uses SQLAlchemy's parameterization to prevent injection
- **Schema Validation**: Validates table/column names against schema
- **Query Review**: All generated SQL can be reviewed before execution

### API Security
- **Connection Isolation**: Named connections prevent cross-database access
- **Session Management**: Secure session IDs for conversation tracking
- **Rate Limiting**: (TODO) Add rate limiting for production use
- **Authentication**: (TODO) Add OAuth/JWT for production use

## Performance

- **Query Understanding**: ~50-100ms for NLP processing
- **SQL Generation**: ~2-5s (LLM latency, depends on OpenAI response time)
- **Query Execution**: Varies by database and query complexity
- **Total Latency**: Typically 2-10s for end-to-end question → answer

### Optimization Tips
1. Use specific questions (reduces ambiguity)
2. Provide schema context (improves accuracy)
3. Use connection pooling for high throughput
4. Cache frequently asked questions
5. Use gpt-3.5-turbo for faster (but less accurate) SQL generation

## Limitations

- Requires OpenAI API key (LLM dependency)
- SQL generation quality depends on LLM capabilities
- Complex joins and subqueries may require refinement
- Time-series operations depend on date column detection
- Large result sets may impact performance

## Future Enhancements

- Support for additional LLM providers (Anthropic Claude, Cohere)
- Query result caching for repeated questions
- Multi-turn conversation refinement ("Show only Electronics")
- Visualization generation from results
- Query templates and saved questions
- Real-time query suggestions as you type
- Support for NoSQL databases (MongoDB, Cassandra)
- Query performance analysis and indexing recommendations
- Natural language data updates (INSERT, UPDATE)
- Multi-language support (Spanish, French, etc.)

## Examples

### E-commerce Analytics
```python
"What are our top 10 customers by revenue this quarter?"
"Show me products with declining sales over last 3 months"
"Compare revenue between regions for Electronics category"
```

### Sales Analytics
```python
"What is the average deal size by sales rep?"
"Show win rate by product line"
"Which opportunities are likely to close this month?"
```

### Customer Analytics
```python
"How many active customers do we have?"
"What is the churn rate by customer segment?"
"Show customer acquisition trend over last year"
```

## Support

For issues and questions:
- GitHub Issues: https://github.com/your-org/dataforge-ai
- Documentation: https://docs.dataforge.ai
- API Docs: http://localhost:8008/docs (when running)

## License

MIT License - see LICENSE file for details
