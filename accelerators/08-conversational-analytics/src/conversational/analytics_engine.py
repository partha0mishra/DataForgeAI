"""Conversational analytics engine - main orchestrator."""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional

from dataforge_common.logging import get_logger

logger = get_logger(__name__)


@dataclass
class Conversation:
    """Conversation session for analytics."""

    session_id: str
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    messages: List[Dict[str, Any]] = field(default_factory=list)
    context: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class AnalyticsResponse:
    """Response from conversational analytics."""

    natural_query: str
    sql_query: str
    explanation: str
    results: Any
    formatted_results: str
    execution_time_ms: float
    confidence: float
    warnings: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


class ConversationalAnalyticsEngine:
    """Main engine for conversational analytics."""

    def __init__(
        self,
        query_processor,
        sql_generator,
        query_executor,
    ):
        """Initialize analytics engine.

        Args:
            query_processor: Natural language query processor
            sql_generator: SQL generation component
            query_executor: Query execution component
        """
        self.query_processor = query_processor
        self.sql_generator = sql_generator
        self.query_executor = query_executor
        self.conversations: Dict[str, Conversation] = {}

    def create_session(self, session_id: Optional[str] = None) -> str:
        """Create new conversation session.

        Args:
            session_id: Optional session ID (generated if not provided)

        Returns:
            Session ID
        """
        if session_id is None:
            session_id = f"session_{datetime.utcnow().timestamp()}"

        conversation = Conversation(session_id=session_id)
        self.conversations[session_id] = conversation

        logger.info(f"Created conversation session: {session_id}")

        return session_id

    def ask(
        self,
        question: str,
        session_id: Optional[str] = None,
        connection_name: str = "default",
        result_format: str = "table",
        execute: bool = True,
    ) -> AnalyticsResponse:
        """Ask a question in natural language.

        Args:
            question: Natural language question
            session_id: Conversation session ID
            connection_name: Database connection name
            result_format: Format for results (table, summary, text, etc.)
            execute: Whether to execute the query (False for SQL generation only)

        Returns:
            Analytics response with SQL, results, and explanation
        """
        start_time = datetime.utcnow()

        logger.info(f"Processing question: {question}")

        # Create session if needed
        if session_id is None:
            session_id = self.create_session()
        elif session_id not in self.conversations:
            self.create_session(session_id)

        conversation = self.conversations[session_id]

        # Get database schema
        schema = self.query_executor.get_schema(connection_name)

        # Step 1: Parse natural language query
        parsed_query = self.query_processor.parse_query(question, schema)

        # Step 2: Generate SQL
        generated_sql = self.sql_generator.generate_sql(
            natural_query=question,
            schema=schema,
            dialect="postgresql",  # TODO: Make configurable
        )

        # Step 3: Execute query (if requested)
        if execute:
            query_result = self.query_executor.execute_query(
                query=generated_sql.query,
                connection_name=connection_name,
            )

            # Format results
            formatted = self.query_executor.format_result(
                result=query_result,
                format=result_format,
            )
        else:
            query_result = None
            formatted = None

        # Calculate execution time
        end_time = datetime.utcnow()
        execution_time = (end_time - start_time).total_seconds() * 1000

        # Build response
        response = AnalyticsResponse(
            natural_query=question,
            sql_query=generated_sql.query,
            explanation=generated_sql.explanation,
            results=query_result.data if query_result and query_result.success else None,
            formatted_results=formatted.content if formatted else "",
            execution_time_ms=execution_time,
            confidence=min(parsed_query.confidence, 1.0),
            warnings=generated_sql.warnings,
            metadata={
                "parsed_intent": parsed_query.intent.value,
                "tables_used": generated_sql.tables,
                "columns_used": generated_sql.columns,
                "operations": generated_sql.operations,
                "is_safe": generated_sql.is_safe,
            },
        )

        # Add to conversation history
        conversation.messages.append({
            "timestamp": datetime.utcnow().isoformat(),
            "question": question,
            "sql": generated_sql.query,
            "success": query_result.success if query_result else None,
            "row_count": query_result.row_count if query_result else 0,
        })
        conversation.updated_at = datetime.utcnow()

        logger.info(
            f"Question processed successfully: "
            f"{query_result.row_count if query_result else 0} rows, "
            f"{execution_time:.2f}ms"
        )

        return response

    def explain_query(self, query: str) -> str:
        """Explain a SQL query in natural language.

        Args:
            query: SQL query to explain

        Returns:
            Natural language explanation
        """
        return self.sql_generator.explain_sql(query)

    def optimize_query(
        self,
        query: str,
        connection_name: str = "default",
    ) -> str:
        """Optimize a SQL query.

        Args:
            query: SQL query to optimize
            connection_name: Database connection name

        Returns:
            Optimized SQL query
        """
        schema = self.query_executor.get_schema(connection_name)

        optimized = self.sql_generator.optimize_sql(
            query=query,
            schema=schema,
            dialect="postgresql",
        )

        return optimized.query

    def get_conversation_history(self, session_id: str) -> List[Dict[str, Any]]:
        """Get conversation history.

        Args:
            session_id: Session ID

        Returns:
            List of messages in conversation
        """
        if session_id not in self.conversations:
            return []

        return self.conversations[session_id].messages

    def clear_conversation(self, session_id: str) -> None:
        """Clear conversation history.

        Args:
            session_id: Session ID
        """
        if session_id in self.conversations:
            self.conversations[session_id].messages = []
            self.conversations[session_id].updated_at = datetime.utcnow()
            logger.info(f"Cleared conversation: {session_id}")

    def delete_session(self, session_id: str) -> None:
        """Delete conversation session.

        Args:
            session_id: Session ID
        """
        if session_id in self.conversations:
            del self.conversations[session_id]
            logger.info(f"Deleted session: {session_id}")

    def get_suggestions(
        self,
        partial_query: str,
        connection_name: str = "default",
    ) -> List[str]:
        """Get query suggestions based on partial input.

        Args:
            partial_query: Partial natural language query
            connection_name: Database connection name

        Returns:
            List of suggested completions
        """
        # Get schema
        schema = self.query_executor.get_schema(connection_name)

        suggestions = []

        # Suggest tables
        if "tables" in schema:
            for table in schema["tables"].keys():
                if table.lower() in partial_query.lower():
                    suggestions.append(f"Show all data from {table}")
                    suggestions.append(f"Count rows in {table}")

        # Suggest common patterns
        common_patterns = [
            "Show me the top 10 rows",
            "Count the total number of rows",
            "Show me the average",
            "Group by category",
            "Filter by date",
            "Sort by date descending",
        ]

        for pattern in common_patterns:
            if pattern.lower().startswith(partial_query.lower()):
                suggestions.append(pattern)

        return suggestions[:5]  # Limit to 5 suggestions

    def get_schema_summary(self, connection_name: str = "default") -> Dict[str, Any]:
        """Get summary of database schema.

        Args:
            connection_name: Database connection name

        Returns:
            Schema summary with table and column counts
        """
        schema = self.query_executor.get_schema(connection_name)

        summary = {
            "table_count": len(schema.get("tables", {})),
            "tables": [],
        }

        for table_name, table_info in schema.get("tables", {}).items():
            columns = table_info.get("columns", {})
            summary["tables"].append({
                "name": table_name,
                "column_count": len(columns),
                "columns": list(columns.keys()),
            })

        return summary

    def validate_question(
        self,
        question: str,
        connection_name: str = "default",
    ) -> Dict[str, Any]:
        """Validate if a question can be answered.

        Args:
            question: Natural language question
            connection_name: Database connection name

        Returns:
            Validation result with suggestions
        """
        schema = self.query_executor.get_schema(connection_name)

        # Parse query
        parsed = self.query_processor.parse_query(question, schema)

        is_valid = True
        issues = []
        suggestions = []

        # Check if intent was detected
        if parsed.intent.value == "unknown":
            is_valid = False
            issues.append("Could not understand the question intent")
            suggestions.append("Try rephrasing using words like 'show', 'count', 'average', etc.")

        # Check if tables were identified
        if not parsed.tables and "tables" in schema:
            issues.append("No tables identified in the question")
            suggestions.append(f"Available tables: {', '.join(schema['tables'].keys())}")

        # Check confidence
        if parsed.confidence < 0.5:
            is_valid = False
            issues.append("Low confidence in understanding the question")
            suggestions.append("Try being more specific about what you want to know")

        return {
            "is_valid": is_valid,
            "confidence": parsed.confidence,
            "intent": parsed.intent.value,
            "issues": issues,
            "suggestions": suggestions,
        }
