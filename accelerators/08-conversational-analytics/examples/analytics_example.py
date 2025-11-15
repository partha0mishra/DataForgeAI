"""Example: Complete conversational analytics workflow."""

import os
import sys
from pathlib import Path

import pandas as pd
import numpy as np
from sqlalchemy import create_engine, text

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from query.query_processor import QueryProcessor
from sql.sql_generator import SQLGenerator
from execution.query_executor import QueryExecutor
from conversational.analytics_engine import ConversationalAnalyticsEngine


def print_section(title: str):
    """Print section header."""
    print()
    print("=" * 80)
    print(f" {title}")
    print("=" * 80)
    print()


def create_sample_database():
    """Create sample SQLite database with sales data."""
    print("Creating sample sales database...")

    # Create SQLite database
    db_path = Path(__file__).parent / "sample_sales.db"
    engine = create_engine(f"sqlite:///{db_path}")

    # Generate sample data
    np.random.seed(42)

    # Create customers table
    customers_df = pd.DataFrame({
        "customer_id": range(1, 101),
        "name": [f"Customer {i}" for i in range(1, 101)],
        "email": [f"customer{i}@example.com" for i in range(1, 101)],
        "region": np.random.choice(["North", "South", "East", "West"], 100),
        "segment": np.random.choice(["Enterprise", "SMB", "Startup"], 100),
    })

    # Create products table
    products_df = pd.DataFrame({
        "product_id": range(1, 51),
        "name": [f"Product {i}" for i in range(1, 51)],
        "category": np.random.choice(["Software", "Hardware", "Services"], 50),
        "price": np.random.uniform(50, 5000, 50).round(2),
    })

    # Create sales table
    sales_data = []
    for i in range(1, 501):
        sales_data.append({
            "sale_id": i,
            "customer_id": np.random.randint(1, 101),
            "product_id": np.random.randint(1, 51),
            "sale_date": pd.Timestamp("2024-01-01") + pd.Timedelta(days=np.random.randint(0, 365)),
            "quantity": np.random.randint(1, 20),
            "discount": np.random.uniform(0, 0.3).round(2),
        })

    sales_df = pd.DataFrame(sales_data)

    # Calculate total amount
    sales_df = sales_df.merge(products_df[["product_id", "price"]], on="product_id")
    sales_df["total_amount"] = (sales_df["quantity"] * sales_df["price"] * (1 - sales_df["discount"])).round(2)
    sales_df = sales_df.drop(columns=["price"])

    # Write to database
    customers_df.to_sql("customers", engine, if_exists="replace", index=False)
    products_df.to_sql("products", engine, if_exists="replace", index=False)
    sales_df.to_sql("sales", engine, if_exists="replace", index=False)

    print(f"✓ Created database with 3 tables:")
    print(f"  - customers: {len(customers_df)} rows")
    print(f"  - products: {len(products_df)} rows")
    print(f"  - sales: {len(sales_df)} rows")
    print(f"✓ Database saved to: {db_path}")

    return str(db_path)


def main():
    """Run complete conversational analytics example."""
    print("=" * 80)
    print(" DataForge Conversational Analytics - Complete Example")
    print("=" * 80)

    # Check for OpenAI API key
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print()
        print("WARNING: OPENAI_API_KEY not set!")
        print("SQL generation requires an OpenAI API key.")
        print("Set API key with: export OPENAI_API_KEY='your-key'")
        print()
        return

    # Step 1: Create sample database
    print_section("1. Create Sample Sales Database")
    db_path = create_sample_database()

    # Step 2: Initialize components
    print_section("2. Initialize Conversational Analytics Components")

    query_processor = QueryProcessor()
    print("✓ Query processor initialized")

    sql_generator = SQLGenerator(llm_api_key=api_key, llm_model="gpt-4")
    print("✓ SQL generator initialized")

    query_executor = QueryExecutor()
    print("✓ Query executor initialized")

    analytics_engine = ConversationalAnalyticsEngine(
        query_processor=query_processor,
        sql_generator=sql_generator,
        query_executor=query_executor,
    )
    print("✓ Analytics engine initialized")

    # Step 3: Connect to database
    print_section("3. Connect to Database")

    query_executor.connect(
        name="default",
        connection_string=f"sqlite:///{db_path}",
        dialect="sqlite",
    )
    print("✓ Connected to sales database")

    # Get schema
    schema = query_executor.get_schema("default")
    print(f"✓ Retrieved schema with {len(schema['tables'])} tables")

    # Step 4: Create conversation session
    print_section("4. Create Conversation Session")

    session_id = analytics_engine.create_session()
    print(f"✓ Created session: {session_id}")

    # Step 5: Ask natural language questions
    print_section("5. Ask Natural Language Questions")

    questions = [
        "Show me the top 10 customers by total sales amount",
        "What is the average sale amount by region?",
        "How many products are in each category?",
        "Which product has the highest total revenue?",
        "Show me sales trends over time by month",
    ]

    for i, question in enumerate(questions, 1):
        print(f"\nQuestion {i}: {question}")
        print("-" * 80)

        try:
            response = analytics_engine.ask(
                question=question,
                session_id=session_id,
                result_format="table",
            )

            print(f"\nGenerated SQL:")
            print(response.sql_query)

            print(f"\nExplanation:")
            print(response.explanation)

            print(f"\nResults ({response.metadata.get('is_safe', True) and 'SAFE' or 'UNSAFE'}):")
            if response.results is not None:
                print(response.results.head(10).to_string(index=False))
                if len(response.results) > 10:
                    print(f"... and {len(response.results) - 10} more rows")
            else:
                print("No results")

            print(f"\nMetadata:")
            print(f"  Confidence: {response.confidence:.0%}")
            print(f"  Execution Time: {response.execution_time_ms:.2f}ms")
            print(f"  Tables Used: {', '.join(response.metadata.get('tables_used', []))}")
            print(f"  Operations: {', '.join(response.metadata.get('operations', []))}")

            if response.warnings:
                print(f"\nWarnings:")
                for warning in response.warnings:
                    print(f"  ⚠ {warning}")

        except Exception as e:
            print(f"Error: {str(e)}")

        print()

    # Step 6: Get conversation history
    print_section("6. Conversation History")

    history = analytics_engine.get_conversation_history(session_id)
    print(f"Conversation contains {len(history)} messages")
    print()

    for i, msg in enumerate(history, 1):
        print(f"{i}. {msg['question']}")
        print(f"   SQL: {msg['sql'][:60]}...")
        print(f"   Success: {msg['success']}, Rows: {msg['row_count']}")
        print()

    # Step 7: Validate questions
    print_section("7. Question Validation")

    test_questions = [
        "Show me all customers",  # Valid
        "foo bar baz",  # Invalid
        "Count the widgets",  # Ambiguous
    ]

    for question in test_questions:
        print(f"\nValidating: {question}")
        validation = analytics_engine.validate_question(
            question=question,
            connection_name="default",
        )

        print(f"  Valid: {validation['is_valid']}")
        print(f"  Confidence: {validation['confidence']:.0%}")
        print(f"  Intent: {validation['intent']}")

        if validation['issues']:
            print("  Issues:")
            for issue in validation['issues']:
                print(f"    - {issue}")

        if validation['suggestions']:
            print("  Suggestions:")
            for suggestion in validation['suggestions']:
                print(f"    - {suggestion}")

    # Step 8: SQL optimization
    print_section("8. SQL Query Optimization")

    original_query = """
        SELECT customers.name, SUM(sales.total_amount)
        FROM sales, customers
        WHERE sales.customer_id = customers.customer_id
        GROUP BY customers.name
        ORDER BY SUM(sales.total_amount) DESC
    """

    print("Original Query:")
    print(original_query)

    try:
        optimized_query = analytics_engine.optimize_query(
            query=original_query,
            connection_name="default",
        )

        print("\nOptimized Query:")
        print(optimized_query)

    except Exception as e:
        print(f"Optimization error: {str(e)}")

    # Step 9: Schema summary
    print_section("9. Database Schema Summary")

    summary = analytics_engine.get_schema_summary("default")

    print(f"Tables: {summary['table_count']}")
    for table in summary['tables']:
        print(f"\n  {table['name']}:")
        print(f"    Columns: {table['column_count']}")
        print(f"    Fields: {', '.join(table['columns'])}")

    # Step 10: Query suggestions
    print_section("10. Query Suggestions")

    partial_queries = [
        "show",
        "count",
        "sales",
    ]

    for partial in partial_queries:
        suggestions = analytics_engine.get_suggestions(
            partial_query=partial,
            connection_name="default",
        )

        print(f"\nSuggestions for '{partial}':")
        for suggestion in suggestions:
            print(f"  • {suggestion}")

    # Final summary
    print_section("Example Complete!")

    print("Summary:")
    print(f"  ✓ Created sample database with 3 tables")
    print(f"  ✓ Connected to SQLite database")
    print(f"  ✓ Asked {len(questions)} natural language questions")
    print(f"  ✓ Generated and executed SQL queries")
    print(f"  ✓ Maintained conversation history")
    print(f"  ✓ Validated questions and provided suggestions")
    print()
    print("Next steps:")
    print("  1. Start API: uvicorn src.api.main:app --reload --port 8008")
    print("  2. Try API at http://localhost:8008/docs")
    print("  3. Connect to your own database")
    print("  4. Ask questions in natural language!")
    print()

    # Cleanup
    query_executor.disconnect("default")
    print("✓ Disconnected from database")


if __name__ == "__main__":
    main()
