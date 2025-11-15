"""Example: Using RAG for question answering."""

from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent / "backend/src"))

from indexing.document_processor import DocumentProcessor
from retrieval.rag_engine import RAGEngine


def create_sample_documents():
    """Create sample documentation for testing."""
    docs_dir = Path("sample_docs")
    docs_dir.mkdir(exist_ok=True)

    # Sample document 1: Airflow guide
    (docs_dir / "airflow_guide.md").write_text("""
# Airflow DAGs Guide

## What is a DAG?

A DAG (Directed Acyclic Graph) is a collection of tasks you want to run, organized in a way that reflects their relationships and dependencies.

## Creating a DAG

To create a DAG in Airflow:

```python
from airflow import DAG
from datetime import datetime

dag = DAG(
    dag_id='my_dag',
    start_date=datetime(2025, 1, 1),
    schedule='@daily'
)
```

## Adding Tasks

Tasks are added to the DAG using operators:

```python
from airflow.operators.python import PythonOperator

task = PythonOperator(
    task_id='my_task',
    python_callable=my_function,
    dag=dag
)
```

## Task Dependencies

Define dependencies using >> operator:

```python
task1 >> task2 >> task3
```
""")

    # Sample document 2: dbt guide
    (docs_dir / "dbt_guide.md").write_text("""
# dbt Transformations Guide

## What is dbt?

dbt (data build tool) enables data analysts and engineers to transform data in their warehouses by simply writing select statements.

## Creating Models

Create a SQL file in models/ directory:

```sql
-- models/staging/stg_customers.sql
select
    id as customer_id,
    first_name,
    last_name,
    email
from {{ source('raw', 'customers') }}
```

## Running dbt

Execute transformations:

```bash
dbt run
dbt test
```

## Model Materialization

Configure materialization in dbt_project.yml:

```yaml
models:
  my_project:
    staging:
      +materialized: view
    marts:
      +materialized: table
```
""")

    # Sample document 3: Quality checks
    (docs_dir / "quality_guide.md").write_text("""
# Data Quality Guide

## Running Quality Checks

Use Great Expectations for data quality:

```python
from great_expectations.data_context import DataContext

context = DataContext()
result = context.run_checkpoint("my_checkpoint")
```

## Defining Expectations

Create expectations in Great Expectations:

```python
suite = context.get_expectation_suite("my_suite")
suite.add_expectation({
    "expectation_type": "expect_column_values_to_not_be_null",
    "kwargs": {"column": "customer_id"}
})
```

## PII Detection

Detect sensitive data:

```python
from dataforge_quality.governance import PIIDetector

detector = PIIDetector()
pii_found = detector.detect_in_dataframe(df)
masked_df = detector.mask_pii(df)
```
""")

    print(f"Created sample documents in {docs_dir}/")
    return docs_dir


def main():
    """Run RAG example."""
    print("=" * 70)
    print("DataForge Knowledge Repository - RAG Example")
    print("=" * 70)
    print()

    # Step 1: Create sample documentation
    print("1. Creating sample documentation...")
    docs_dir = create_sample_documents()
    print()

    # Step 2: Index documents
    print("2. Indexing documents...")
    processor = DocumentProcessor(chunk_size=512, chunk_overlap=50)
    chunks = processor.process_directory(str(docs_dir))
    print(f"   Indexed {len(chunks)} chunks from {docs_dir}")
    print()

    # Step 3: Initialize RAG engine
    print("3. Initializing RAG engine...")
    rag = RAGEngine(
        llm_provider="openai",
        llm_api_key=None,  # Set your API key or use env var
    )

    # Convert chunks to documents
    documents = [chunk.to_dict() for chunk in chunks]
    rag.index_documents(documents)
    print(f"   RAG engine initialized with {len(documents)} documents")
    print()

    # Step 4: Ask questions
    print("4. Asking questions with RAG...")
    print()

    questions = [
        "How do I create an Airflow DAG?",
        "What is dbt and how do I run it?",
        "How can I detect PII in my data?",
        "How do I set up task dependencies in Airflow?",
    ]

    for i, question in enumerate(questions, 1):
        print(f"Question {i}: {question}")
        print("-" * 70)

        # Query RAG engine (Note: requires OpenAI API key)
        try:
            response = rag.query(question)

            print(f"Answer: {response.answer}")
            print()
            print(f"Confidence: {response.confidence:.2%}")
            print(f"Sources ({len(response.sources)}):")
            for j, source in enumerate(response.sources, 1):
                filename = source["metadata"].get("filename", "Unknown")
                score = source["score"]
                print(f"  {j}. {filename} (relevance: {score:.2%})")
            print()

        except Exception as e:
            print(f"Error: {str(e)}")
            print("Note: This example requires an OpenAI API key.")
            print("Set OPENAI_API_KEY environment variable to run.")
            print()

        print()

    # Step 5: Show indexed content
    print("5. Indexed Content Summary:")
    print()
    sources = set(doc["metadata"].get("source", "unknown") for doc in documents)
    print(f"   Total unique documents: {len(sources)}")
    print(f"   Total chunks: {len(documents)}")
    print()
    print("   Files:")
    for source in sources:
        chunk_count = sum(1 for d in documents if d["metadata"].get("source") == source)
        print(f"     - {Path(source).name}: {chunk_count} chunks")
    print()

    print("=" * 70)
    print("Example complete!")
    print("=" * 70)
    print()
    print("Next steps:")
    print("  1. Set OPENAI_API_KEY to enable LLM responses")
    print("  2. Add your own documentation to sample_docs/")
    print("  3. Start the API: uvicorn backend.src.api.main:app --reload")
    print()


if __name__ == "__main__":
    main()
