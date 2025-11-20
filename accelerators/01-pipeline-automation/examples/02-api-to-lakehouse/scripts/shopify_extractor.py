"""
Shopify API Data Extractor

A production-ready API client for extracting data from Shopify REST API with:
- OAuth 2.0 and API key authentication
- Token bucket rate limiting algorithm
- Cursor-based pagination
- Exponential backoff retry logic
- Watermark-based incremental extraction
- Support for both JSON and Parquet output formats

Author: DataForgeAI
"""

import time
import logging
import json
import os
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Generator
from dataclasses import dataclass, field
from pathlib import Path
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
import pyarrow as pa
import pyarrow.parquet as pq

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@dataclass
class RateLimiter:
    """
    Token bucket algorithm for rate limiting.

    Allows bursts up to bucket_size while maintaining
    average rate of tokens_per_second.
    """
    tokens_per_second: float
    bucket_size: int = 40
    tokens: float = field(init=False)
    last_update: float = field(init=False)

    def __post_init__(self):
        self.tokens = self.bucket_size
        self.last_update = time.time()

    def acquire(self, tokens: int = 1) -> None:
        """
        Acquire tokens from bucket, blocking if necessary.

        Args:
            tokens: Number of tokens to acquire (default 1)
        """
        while True:
            now = time.time()
            elapsed = now - self.last_update

            # Refill bucket based on elapsed time
            self.tokens = min(
                self.bucket_size,
                self.tokens + elapsed * self.tokens_per_second
            )
            self.last_update = now

            if self.tokens >= tokens:
                self.tokens -= tokens
                return

            # Calculate sleep time needed
            sleep_time = (tokens - self.tokens) / self.tokens_per_second
            logger.debug(f"Rate limit: sleeping {sleep_time:.2f}s")
            time.sleep(sleep_time)


@dataclass
class ExtractionConfig:
    """Configuration for Shopify data extraction."""
    shop_url: str
    api_key: str
    api_secret: str
    api_version: str = "2024-01"
    endpoint: str = "orders"
    rate_limit_per_second: float = 2.0  # Shopify limit is 2 req/sec
    page_size: int = 250
    watermark_column: str = "updated_at"
    output_format: str = "parquet"  # parquet or json
    output_path: str = "./data/shopify"
    incremental_state_file: str = "./state/shopify_watermark.json"
    max_retries: int = 5
    backoff_multiplier: float = 2.0
    timeout: int = 30


class ShopifyExtractor:
    """
    Production-ready Shopify API client with advanced features.
    """

    def __init__(self, config: ExtractionConfig):
        """
        Initialize Shopify API client.

        Args:
            config: Extraction configuration
        """
        self.config = config
        self.base_url = f"https://{config.shop_url}/admin/api/{config.api_version}"
        self.rate_limiter = RateLimiter(
            tokens_per_second=config.rate_limit_per_second
        )

        # Setup session with retry logic
        self.session = self._create_session()

        # Ensure output directories exist
        Path(config.output_path).mkdir(parents=True, exist_ok=True)
        Path(config.incremental_state_file).parent.mkdir(parents=True, exist_ok=True)

    def _create_session(self) -> requests.Session:
        """
        Create requests session with retry logic.

        Returns:
            Configured requests session
        """
        session = requests.Session()

        # Configure retry strategy
        retry_strategy = Retry(
            total=self.config.max_retries,
            backoff_factor=self.config.backoff_multiplier,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["GET", "POST"],
        )

        adapter = HTTPAdapter(max_retries=retry_strategy)
        session.mount("http://", adapter)
        session.mount("https://", adapter)

        # Set authentication headers
        session.headers.update({
            'X-Shopify-Access-Token': self.config.api_key,
            'Content-Type': 'application/json',
        })

        return session

    def _get_watermark(self) -> Optional[str]:
        """
        Get last extraction watermark from state file.

        Returns:
            Last watermark timestamp or None for full extraction
        """
        try:
            if os.path.exists(self.config.incremental_state_file):
                with open(self.config.incremental_state_file, 'r') as f:
                    state = json.load(f)
                    watermark = state.get(self.config.endpoint, {}).get('last_watermark')
                    if watermark:
                        logger.info(f"Resuming from watermark: {watermark}")
                        return watermark
        except Exception as e:
            logger.warning(f"Could not load watermark: {e}")

        logger.info("No watermark found, performing full extraction")
        return None

    def _save_watermark(self, watermark: str) -> None:
        """
        Save extraction watermark to state file.

        Args:
            watermark: Timestamp to save
        """
        try:
            state = {}
            if os.path.exists(self.config.incremental_state_file):
                with open(self.config.incremental_state_file, 'r') as f:
                    state = json.load(f)

            state[self.config.endpoint] = {
                'last_watermark': watermark,
                'last_updated': datetime.utcnow().isoformat()
            }

            with open(self.config.incremental_state_file, 'w') as f:
                json.dump(state, f, indent=2)

            logger.info(f"Watermark saved: {watermark}")
        except Exception as e:
            logger.error(f"Failed to save watermark: {e}")

    def _make_request(
        self,
        url: str,
        params: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Make API request with rate limiting and error handling.

        Args:
            url: API endpoint URL
            params: Query parameters

        Returns:
            API response JSON

        Raises:
            requests.RequestException: On request failure
        """
        # Apply rate limiting
        self.rate_limiter.acquire()

        try:
            logger.debug(f"Requesting: {url} with params: {params}")

            response = self.session.get(
                url,
                params=params,
                timeout=self.config.timeout
            )

            # Check for rate limit headers
            if 'X-Shopify-Shop-Api-Call-Limit' in response.headers:
                call_limit = response.headers['X-Shopify-Shop-Api-Call-Limit']
                logger.debug(f"API call limit: {call_limit}")

            # Handle rate limiting (429)
            if response.status_code == 429:
                retry_after = int(response.headers.get('Retry-After', 5))
                logger.warning(f"Rate limited. Waiting {retry_after}s")
                time.sleep(retry_after)
                return self._make_request(url, params)  # Retry

            response.raise_for_status()
            return response.json()

        except requests.exceptions.Timeout:
            logger.error(f"Request timeout for URL: {url}")
            raise
        except requests.exceptions.RequestException as e:
            logger.error(f"Request failed: {e}")
            raise

    def _paginate(
        self,
        endpoint: str,
        params: Optional[Dict[str, Any]] = None
    ) -> Generator[List[Dict], None, None]:
        """
        Paginate through API results using cursor-based pagination.

        Args:
            endpoint: API endpoint (e.g., 'orders')
            params: Query parameters

        Yields:
            Pages of results
        """
        url = f"{self.base_url}/{endpoint}.json"
        params = params or {}
        params['limit'] = self.config.page_size

        page_count = 0

        while url:
            page_count += 1
            logger.info(f"Fetching page {page_count}")

            response = self._make_request(url, params)

            # Extract data from response
            data = response.get(endpoint, [])
            if not data:
                logger.info("No more data to fetch")
                break

            yield data

            # Get next page URL from Link header (cursor-based pagination)
            link_header = self.session.head(url).headers.get('Link', '')
            next_url = self._parse_link_header(link_header)

            if next_url:
                url = next_url
                params = {}  # Params are in the URL for cursor pagination
            else:
                break

    def _parse_link_header(self, link_header: str) -> Optional[str]:
        """
        Parse Link header for next page URL.

        Args:
            link_header: Link header value

        Returns:
            Next page URL or None
        """
        if not link_header:
            return None

        links = link_header.split(',')
        for link in links:
            if 'rel="next"' in link:
                url = link.split(';')[0].strip('<> ')
                return url

        return None

    def extract(
        self,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        full_refresh: bool = False
    ) -> str:
        """
        Extract data from Shopify API.

        Args:
            start_date: Start date for extraction (ISO format)
            end_date: End date for extraction (ISO format)
            full_refresh: Force full extraction, ignoring watermark

        Returns:
            Output file path
        """
        logger.info(f"Starting Shopify {self.config.endpoint} extraction")

        # Build query parameters
        params = {}

        # Determine start date (watermark or provided)
        if not full_refresh:
            watermark = self._get_watermark()
            if watermark:
                start_date = watermark

        if start_date:
            params[f'{self.config.watermark_column}_min'] = start_date

        if end_date:
            params[f'{self.config.watermark_column}_max'] = end_date

        # Additional filters
        params['status'] = 'any'  # Include all order statuses
        params['fields'] = ','.join([  # Optimize by requesting only needed fields
            'id', 'order_number', 'email', 'created_at', 'updated_at',
            'total_price', 'subtotal_price', 'total_tax', 'currency',
            'financial_status', 'fulfillment_status', 'customer'
        ])

        # Extract all pages
        all_records = []
        max_watermark = None

        try:
            for page_data in self._paginate(self.config.endpoint, params):
                all_records.extend(page_data)

                # Track maximum watermark
                for record in page_data:
                    watermark_value = record.get(self.config.watermark_column)
                    if watermark_value:
                        if not max_watermark or watermark_value > max_watermark:
                            max_watermark = watermark_value

            logger.info(f"Extracted {len(all_records)} records")

            # Save data
            output_file = self._save_data(all_records)

            # Update watermark
            if max_watermark:
                self._save_watermark(max_watermark)

            logger.info(f"Extraction complete: {output_file}")
            return output_file

        except Exception as e:
            logger.error(f"Extraction failed: {e}")
            raise

    def _save_data(self, records: List[Dict]) -> str:
        """
        Save extracted data to file.

        Args:
            records: List of records to save

        Returns:
            Output file path
        """
        if not records:
            logger.warning("No records to save")
            return ""

        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        filename = f"{self.config.endpoint}_{timestamp}"

        if self.config.output_format == 'parquet':
            output_file = f"{self.config.output_path}/{filename}.parquet"
            self._save_parquet(records, output_file)
        else:
            output_file = f"{self.config.output_path}/{filename}.json"
            self._save_json(records, output_file)

        logger.info(f"Saved {len(records)} records to {output_file}")
        return output_file

    def _save_json(self, records: List[Dict], filepath: str) -> None:
        """Save records as JSON."""
        with open(filepath, 'w') as f:
            json.dump(records, f, indent=2, default=str)

    def _save_parquet(self, records: List[Dict], filepath: str) -> None:
        """Save records as Parquet using PyArrow."""
        # Flatten nested structures if needed
        flattened = []
        for record in records:
            flat = self._flatten_record(record)
            flattened.append(flat)

        # Convert to PyArrow table
        table = pa.Table.from_pylist(flattened)

        # Write parquet with compression
        pq.write_table(
            table,
            filepath,
            compression='snappy',
            use_dictionary=True,
        )

    def _flatten_record(self, record: Dict, prefix: str = '') -> Dict:
        """
        Flatten nested dictionary structure.

        Args:
            record: Record to flatten
            prefix: Prefix for nested keys

        Returns:
            Flattened dictionary
        """
        flat = {}
        for key, value in record.items():
            new_key = f"{prefix}{key}" if prefix else key

            if isinstance(value, dict):
                flat.update(self._flatten_record(value, f"{new_key}_"))
            elif isinstance(value, list):
                # Convert lists to JSON strings
                flat[new_key] = json.dumps(value)
            else:
                flat[new_key] = value

        return flat


def main():
    """
    Example usage of Shopify extractor.
    """
    # Configuration from environment variables
    config = ExtractionConfig(
        shop_url=os.getenv('SHOPIFY_SHOP_URL', 'your-store.myshopify.com'),
        api_key=os.getenv('SHOPIFY_API_KEY', 'your-api-key'),
        api_secret=os.getenv('SHOPIFY_API_SECRET', 'your-api-secret'),
        endpoint='orders',
        output_format='parquet',
        output_path=os.getenv('OUTPUT_PATH', './data/shopify'),
    )

    # Create extractor
    extractor = ShopifyExtractor(config)

    # Run incremental extraction
    try:
        output_file = extractor.extract()
        print(f"Extraction successful: {output_file}")
    except Exception as e:
        print(f"Extraction failed: {e}")
        exit(1)


if __name__ == "__main__":
    main()
