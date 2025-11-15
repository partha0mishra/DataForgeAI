"""SQL generation from natural language queries using LLM."""

import re
import sqlparse
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from dataforge_ai_core.llm import LLMClient
from dataforge_common.logging import get_logger

logger = get_logger(__name__)


@dataclass
class GeneratedSQL:
    """Generated SQL query with metadata."""

    query: str
    explanation: str
    tables: List[str] = field(default_factory=list)
    columns: List[str] = field(default_factory=list)
    operations: List[str] = field(default_factory=list)
    is_safe: bool = True
    warnings: List[str] = field(default_factory=list)
    confidence: float = 1.0
    metadata: Dict[str, Any] = field(default_factory=dict)


class SQLGenerator:
    """Generate SQL from natural language using LLM."""

    def __init__(
        self,
        llm_api_key: str,
        llm_model: str = "gpt-4",
        temperature: float = 0.1,  # Low temperature for consistent SQL
    ):
        """Initialize SQL generator.

        Args:
            llm_api_key: API key for LLM
            llm_model: LLM model name
            temperature: Generation temperature
        """
        self.llm_client = LLMClient(api_key=llm_api_key, model=llm_model)
        self.temperature = temperature

    def generate_sql(
        self,
        natural_query: str,
        schema: Dict[str, Any],
        dialect: str = "postgresql",
        validate: bool = True,
    ) -> GeneratedSQL:
        """Generate SQL from natural language query.

        Args:
            natural_query: Natural language query
            schema: Database schema information
            dialect: SQL dialect (postgresql, mysql, sqlite, etc.)
            validate: Whether to validate generated SQL

        Returns:
            Generated SQL with metadata
        """
        logger.info(f"Generating SQL for query: {natural_query}")

        # Build prompt
        prompt = self._build_sql_prompt(natural_query, schema, dialect)

        # Generate SQL using LLM
        response = self.llm_client.generate_chat(
            messages=[
                {
                    "role": "system",
                    "content": self._get_system_prompt(dialect),
                },
                {
                    "role": "user",
                    "content": prompt,
                },
            ],
            temperature=self.temperature,
        )

        # Parse response
        generated_sql = self._parse_sql_response(response, dialect)

        # Validate if requested
        if validate:
            validation = self._validate_sql(generated_sql, schema)
            generated_sql.is_safe = validation["is_safe"]
            generated_sql.warnings = validation["warnings"]

        logger.info(f"Generated SQL: {generated_sql.query[:100]}...")

        return generated_sql

    def _get_system_prompt(self, dialect: str) -> str:
        """Get system prompt for SQL generation."""
        return f"""You are an expert SQL query generator specializing in {dialect}.

Your task is to convert natural language questions into precise SQL queries.

Guidelines:
1. Generate syntactically correct {dialect} SQL
2. Use only the tables and columns provided in the schema
3. Use appropriate JOINs when querying multiple tables
4. Add WHERE clauses for filters and conditions
5. Use GROUP BY for aggregations
6. Add ORDER BY and LIMIT when appropriate
7. Include meaningful column aliases
8. Avoid SELECT * - specify columns explicitly
9. Never generate DELETE, DROP, TRUNCATE, or other destructive operations
10. Always include an explanation of the query

Response format:
SQL:
<your SQL query here>

EXPLANATION:
<explanation of what the query does>

TABLES: table1, table2
COLUMNS: column1, column2
OPERATIONS: SELECT, JOIN, WHERE, GROUP BY
"""

    def _build_sql_prompt(
        self,
        natural_query: str,
        schema: Dict[str, Any],
        dialect: str,
    ) -> str:
        """Build prompt for SQL generation."""
        # Format schema for prompt
        schema_str = self._format_schema(schema)

        prompt = f"""Convert the following natural language question into a {dialect} SQL query.

DATABASE SCHEMA:
{schema_str}

QUESTION:
{natural_query}

Generate the SQL query following the response format specified in the system prompt.
"""
        return prompt

    def _format_schema(self, schema: Dict[str, Any]) -> str:
        """Format schema for prompt."""
        schema_lines = []

        if "tables" in schema:
            for table_name, table_info in schema["tables"].items():
                schema_lines.append(f"\nTable: {table_name}")

                if isinstance(table_info, dict) and "columns" in table_info:
                    schema_lines.append("Columns:")
                    for col_name, col_type in table_info["columns"].items():
                        schema_lines.append(f"  - {col_name} ({col_type})")

                    if "description" in table_info:
                        schema_lines.append(f"Description: {table_info['description']}")

        return "\n".join(schema_lines)

    def _parse_sql_response(self, response: str, dialect: str) -> GeneratedSQL:
        """Parse LLM response to extract SQL and metadata."""
        # Extract SQL query
        sql_match = re.search(
            r"SQL:\s*```(?:sql)?\s*(.*?)\s*```",
            response,
            re.DOTALL | re.IGNORECASE,
        )

        if not sql_match:
            sql_match = re.search(
                r"SQL:\s*\n(.*?)(?:\n\nEXPLANATION|\n\nTABLES|$)",
                response,
                re.DOTALL | re.IGNORECASE,
            )

        query = sql_match.group(1).strip() if sql_match else response.strip()

        # Extract explanation
        explanation_match = re.search(
            r"EXPLANATION:\s*\n(.*?)(?:\n\nTABLES|\n\nCOLUMNS|$)",
            response,
            re.DOTALL | re.IGNORECASE,
        )
        explanation = explanation_match.group(1).strip() if explanation_match else ""

        # Extract tables
        tables_match = re.search(
            r"TABLES:\s*([^\n]+)",
            response,
            re.IGNORECASE,
        )
        tables = []
        if tables_match:
            tables = [t.strip() for t in tables_match.group(1).split(",")]

        # Extract columns
        columns_match = re.search(
            r"COLUMNS:\s*([^\n]+)",
            response,
            re.IGNORECASE,
        )
        columns = []
        if columns_match:
            columns = [c.strip() for c in columns_match.group(1).split(",")]

        # Extract operations
        operations_match = re.search(
            r"OPERATIONS:\s*([^\n]+)",
            response,
            re.IGNORECASE,
        )
        operations = []
        if operations_match:
            operations = [o.strip() for o in operations_match.group(1).split(",")]

        # Format SQL
        formatted_query = sqlparse.format(
            query,
            reindent=True,
            keyword_case="upper",
        )

        return GeneratedSQL(
            query=formatted_query,
            explanation=explanation,
            tables=tables,
            columns=columns,
            operations=operations,
        )

    def _validate_sql(
        self,
        generated_sql: GeneratedSQL,
        schema: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Validate generated SQL for safety and correctness."""
        warnings = []
        is_safe = True

        query_upper = generated_sql.query.upper()

        # Check for destructive operations
        destructive_keywords = [
            "DELETE",
            "DROP",
            "TRUNCATE",
            "ALTER",
            "CREATE",
            "INSERT",
            "UPDATE",
        ]

        for keyword in destructive_keywords:
            if keyword in query_upper:
                warnings.append(f"Destructive operation detected: {keyword}")
                is_safe = False

        # Check for SELECT *
        if "SELECT *" in query_upper:
            warnings.append("Using SELECT * - consider specifying columns explicitly")

        # Parse SQL to validate syntax
        try:
            parsed = sqlparse.parse(generated_sql.query)
            if not parsed:
                warnings.append("Failed to parse SQL query")
                is_safe = False
        except Exception as e:
            warnings.append(f"SQL parsing error: {str(e)}")
            is_safe = False

        # Validate tables exist in schema
        if "tables" in schema and generated_sql.tables:
            schema_tables = set(schema["tables"].keys())
            for table in generated_sql.tables:
                if table not in schema_tables:
                    warnings.append(f"Table '{table}' not found in schema")

        return {
            "is_safe": is_safe,
            "warnings": warnings,
        }

    def explain_sql(self, query: str) -> str:
        """Generate natural language explanation of SQL query.

        Args:
            query: SQL query to explain

        Returns:
            Natural language explanation
        """
        logger.info("Generating explanation for SQL query")

        prompt = f"""Explain the following SQL query in simple, non-technical language:

```sql
{query}
```

Provide a clear explanation of:
1. What data is being retrieved
2. What filters or conditions are applied
3. How the data is grouped or sorted
4. What the results will show
"""

        response = self.llm_client.generate_chat(
            messages=[
                {
                    "role": "system",
                    "content": "You are an expert at explaining SQL queries in simple terms.",
                },
                {
                    "role": "user",
                    "content": prompt,
                },
            ],
            temperature=0.7,
        )

        return response.strip()

    def optimize_sql(
        self,
        query: str,
        schema: Dict[str, Any],
        dialect: str = "postgresql",
    ) -> GeneratedSQL:
        """Optimize SQL query for performance.

        Args:
            query: SQL query to optimize
            schema: Database schema
            dialect: SQL dialect

        Returns:
            Optimized SQL query
        """
        logger.info("Optimizing SQL query")

        # Format schema
        schema_str = self._format_schema(schema)

        prompt = f"""Optimize the following {dialect} SQL query for better performance.

DATABASE SCHEMA:
{schema_str}

ORIGINAL QUERY:
```sql
{query}
```

Provide an optimized version considering:
1. Index usage
2. JOIN optimization
3. Subquery elimination
4. Column selection
5. WHERE clause optimization

Use the same response format: SQL, EXPLANATION, TABLES, COLUMNS, OPERATIONS.
"""

        response = self.llm_client.generate_chat(
            messages=[
                {
                    "role": "system",
                    "content": f"You are an expert at optimizing {dialect} SQL queries.",
                },
                {
                    "role": "user",
                    "content": prompt,
                },
            ],
            temperature=0.1,
        )

        return self._parse_sql_response(response, dialect)
