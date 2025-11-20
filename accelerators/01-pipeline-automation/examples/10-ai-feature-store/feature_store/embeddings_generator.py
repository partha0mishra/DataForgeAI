"""
Text Embeddings Generator for Support Ticket Analysis

This script generates vector embeddings for support ticket text using either:
1. Snowflake Cortex AI (recommended for Snowflake users)
2. OpenAI API (requires API key)

Embeddings are used for:
- Semantic similarity search
- Topic clustering
- Churn signal detection from support ticket patterns
"""

import os
import sys
from typing import List, Optional, Tuple
import logging
from datetime import datetime

import pandas as pd
import numpy as np
from snowflake.connector import connect
from snowflake.connector.pandas_tools import write_pandas
import openai
from tqdm import tqdm


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class EmbeddingsGenerator:
    """
    Generate text embeddings for support ticket descriptions and comments.
    """

    def __init__(
        self,
        snowflake_account: str,
        snowflake_user: str,
        snowflake_password: str,
        snowflake_warehouse: str,
        snowflake_database: str,
        snowflake_schema: str,
        embedding_method: str = 'snowflake_cortex',  # or 'openai'
        openai_api_key: Optional[str] = None,
        batch_size: int = 100,
    ):
        """
        Initialize embeddings generator.

        Args:
            snowflake_account: Snowflake account identifier
            snowflake_user: Snowflake username
            snowflake_password: Snowflake password
            snowflake_warehouse: Snowflake warehouse name
            snowflake_database: Snowflake database name
            snowflake_schema: Snowflake schema name
            embedding_method: Method to use ('snowflake_cortex' or 'openai')
            openai_api_key: OpenAI API key (required if method='openai')
            batch_size: Number of records to process in each batch
        """
        self.snowflake_config = {
            'account': snowflake_account,
            'user': snowflake_user,
            'password': snowflake_password,
            'warehouse': snowflake_warehouse,
            'database': snowflake_database,
            'schema': snowflake_schema,
        }
        self.embedding_method = embedding_method
        self.batch_size = batch_size

        if embedding_method == 'openai':
            if not openai_api_key:
                raise ValueError("OpenAI API key required for 'openai' method")
            openai.api_key = openai_api_key

        self.conn = None

    def connect_snowflake(self) -> None:
        """Establish connection to Snowflake."""
        try:
            self.conn = connect(**self.snowflake_config)
            logger.info(f"Connected to Snowflake: {self.snowflake_config['account']}")
        except Exception as e:
            logger.error(f"Failed to connect to Snowflake: {e}")
            raise

    def close_connection(self) -> None:
        """Close Snowflake connection."""
        if self.conn:
            self.conn.close()
            logger.info("Snowflake connection closed")

    def fetch_support_tickets(self, limit: Optional[int] = None) -> pd.DataFrame:
        """
        Fetch support tickets that need embeddings.

        Args:
            limit: Maximum number of tickets to process (None for all)

        Returns:
            DataFrame with ticket_id, customer_id, and text content
        """
        query = """
        SELECT
            ticket_id,
            customer_id,
            created_date,
            -- Combine title and description for richer embeddings
            title || ' ' || description AS text_content,
            priority,
            category
        FROM analytics.support_tickets
        WHERE created_date >= DATEADD(day, -90, CURRENT_DATE())
        AND text_content IS NOT NULL
        AND LENGTH(text_content) > 10
        ORDER BY created_date DESC
        """

        if limit:
            query += f" LIMIT {limit}"

        logger.info("Fetching support tickets from Snowflake...")
        df = pd.read_sql(query, self.conn)
        logger.info(f"Fetched {len(df)} support tickets")

        return df

    def generate_embeddings_snowflake_cortex(
        self,
        texts: List[str],
    ) -> np.ndarray:
        """
        Generate embeddings using Snowflake Cortex AI.

        Snowflake Cortex provides native text embedding functions without
        needing to export data or call external APIs.

        Args:
            texts: List of text strings to embed

        Returns:
            numpy array of shape (n_texts, embedding_dim)
        """
        logger.info(f"Generating embeddings for {len(texts)} texts using Snowflake Cortex")

        # Create temporary table with texts
        temp_table = f"temp_embeddings_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

        cursor = self.conn.cursor()

        try:
            # Create temp table
            cursor.execute(f"""
                CREATE TEMPORARY TABLE {temp_table} (
                    row_id INT,
                    text_content VARCHAR
                )
            """)

            # Insert texts
            insert_values = [(i, text) for i, text in enumerate(texts)]
            cursor.executemany(
                f"INSERT INTO {temp_table} VALUES (%s, %s)",
                insert_values
            )

            # Generate embeddings using Cortex
            # Note: EMBED_TEXT_768 generates 768-dimensional embeddings
            cursor.execute(f"""
                SELECT
                    row_id,
                    SNOWFLAKE.CORTEX.EMBED_TEXT_768('e5-base-v2', text_content) AS embedding
                FROM {temp_table}
                ORDER BY row_id
            """)

            results = cursor.fetchall()

            # Convert to numpy array
            embeddings = np.array([row[1] for row in results])

            logger.info(f"Generated embeddings shape: {embeddings.shape}")

            return embeddings

        except Exception as e:
            logger.error(f"Failed to generate Snowflake Cortex embeddings: {e}")
            raise

        finally:
            cursor.close()

    def generate_embeddings_openai(
        self,
        texts: List[str],
        model: str = 'text-embedding-ada-002',
    ) -> np.ndarray:
        """
        Generate embeddings using OpenAI API.

        Args:
            texts: List of text strings to embed
            model: OpenAI embedding model to use

        Returns:
            numpy array of shape (n_texts, embedding_dim)
        """
        logger.info(f"Generating embeddings for {len(texts)} texts using OpenAI {model}")

        embeddings = []

        # Process in batches to avoid rate limits
        for i in tqdm(range(0, len(texts), self.batch_size)):
            batch = texts[i:i + self.batch_size]

            try:
                response = openai.Embedding.create(
                    input=batch,
                    model=model
                )

                batch_embeddings = [item['embedding'] for item in response['data']]
                embeddings.extend(batch_embeddings)

            except Exception as e:
                logger.error(f"Failed to generate OpenAI embeddings for batch {i}: {e}")
                raise

        embeddings_array = np.array(embeddings)
        logger.info(f"Generated embeddings shape: {embeddings_array.shape}")

        return embeddings_array

    def save_embeddings_to_snowflake(
        self,
        df: pd.DataFrame,
        embeddings: np.ndarray,
    ) -> None:
        """
        Save embeddings back to Snowflake.

        Args:
            df: DataFrame with ticket metadata
            embeddings: numpy array of embeddings
        """
        logger.info("Saving embeddings to Snowflake...")

        # Add embeddings to DataFrame
        df['embedding_vector'] = embeddings.tolist()
        df['embedding_generated_at'] = datetime.now()

        # Prepare data for Snowflake
        embeddings_df = df[[
            'ticket_id',
            'customer_id',
            'created_date',
            'priority',
            'category',
            'embedding_vector',
            'embedding_generated_at'
        ]]

        # Create or replace embeddings table
        cursor = self.conn.cursor()

        try:
            # Create table if not exists
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS analytics.support_ticket_embeddings (
                    ticket_id INT,
                    customer_id INT,
                    created_date TIMESTAMP,
                    priority VARCHAR,
                    category VARCHAR,
                    embedding_vector ARRAY,
                    embedding_generated_at TIMESTAMP,
                    PRIMARY KEY (ticket_id)
                )
            """)

            # Use write_pandas for efficient bulk insert
            success, num_chunks, num_rows, output = write_pandas(
                conn=self.conn,
                df=embeddings_df,
                table_name='SUPPORT_TICKET_EMBEDDINGS',
                database=self.snowflake_config['database'],
                schema=self.snowflake_config['schema'],
                auto_create_table=False,
                overwrite=False,  # Use INSERT instead of TRUNCATE
            )

            if success:
                logger.info(f"Successfully saved {num_rows} embeddings to Snowflake")
            else:
                logger.error(f"Failed to save embeddings: {output}")
                raise Exception("Failed to save embeddings")

        except Exception as e:
            logger.error(f"Error saving embeddings: {e}")
            raise

        finally:
            cursor.close()

    def compute_customer_aggregates(self) -> None:
        """
        Compute customer-level aggregates from ticket embeddings.

        This creates features like:
        - Average embedding vector per customer
        - Embedding diversity (variance)
        - Similarity to known churn patterns
        """
        logger.info("Computing customer-level embedding aggregates...")

        cursor = self.conn.cursor()

        try:
            # Compute average embedding per customer
            cursor.execute("""
                CREATE OR REPLACE TABLE analytics.customer_support_embeddings AS
                SELECT
                    customer_id,
                    -- Average all embeddings for this customer
                    ARRAY_AGG(embedding_vector) AS all_embeddings,
                    -- This would require a UDF to compute mean across arrays
                    -- For now, we'll store all embeddings
                    COUNT(*) AS ticket_count_with_embeddings,
                    MAX(embedding_generated_at) AS last_embedding_generated_at
                FROM analytics.support_ticket_embeddings
                GROUP BY customer_id
            """)

            logger.info("Customer embedding aggregates computed successfully")

        except Exception as e:
            logger.error(f"Failed to compute customer aggregates: {e}")
            raise

        finally:
            cursor.close()

    def run(self, limit: Optional[int] = None) -> None:
        """
        Execute the complete embeddings generation pipeline.

        Args:
            limit: Maximum number of tickets to process
        """
        try:
            # Connect to Snowflake
            self.connect_snowflake()

            # Fetch tickets
            df = self.fetch_support_tickets(limit=limit)

            if len(df) == 0:
                logger.warning("No tickets found to process")
                return

            # Generate embeddings
            texts = df['text_content'].tolist()

            if self.embedding_method == 'snowflake_cortex':
                embeddings = self.generate_embeddings_snowflake_cortex(texts)
            elif self.embedding_method == 'openai':
                embeddings = self.generate_embeddings_openai(texts)
            else:
                raise ValueError(f"Unknown embedding method: {self.embedding_method}")

            # Save embeddings
            self.save_embeddings_to_snowflake(df, embeddings)

            # Compute customer aggregates
            self.compute_customer_aggregates()

            logger.info("Embeddings generation pipeline completed successfully")

        except Exception as e:
            logger.error(f"Embeddings generation failed: {e}")
            raise

        finally:
            self.close_connection()


def main():
    """Main entry point for embeddings generation."""
    # Load configuration from environment variables
    config = {
        'snowflake_account': os.getenv('SNOWFLAKE_ACCOUNT'),
        'snowflake_user': os.getenv('SNOWFLAKE_USER'),
        'snowflake_password': os.getenv('SNOWFLAKE_PASSWORD'),
        'snowflake_warehouse': os.getenv('SNOWFLAKE_WAREHOUSE', 'FEAST_WH'),
        'snowflake_database': os.getenv('SNOWFLAKE_DATABASE', 'ANALYTICS'),
        'snowflake_schema': os.getenv('SNOWFLAKE_SCHEMA', 'PUBLIC'),
        'embedding_method': os.getenv('EMBEDDING_METHOD', 'snowflake_cortex'),
        'openai_api_key': os.getenv('OPENAI_API_KEY'),
        'batch_size': int(os.getenv('BATCH_SIZE', '100')),
    }

    # Validate required configuration
    required_fields = ['snowflake_account', 'snowflake_user', 'snowflake_password']
    missing_fields = [field for field in required_fields if not config[field]]

    if missing_fields:
        logger.error(f"Missing required configuration: {', '.join(missing_fields)}")
        sys.exit(1)

    # Initialize and run generator
    generator = EmbeddingsGenerator(**config)

    # Process all tickets (or set a limit for testing)
    limit = int(os.getenv('LIMIT', '0')) or None

    generator.run(limit=limit)


if __name__ == '__main__':
    main()
