"""
Unit Tests for Shopify API Client

Comprehensive tests for the Shopify extractor including:
- Mock API responses
- Pagination behavior
- Rate limiting
- Retry logic
- Error handling

Author: DataForgeAI
"""

import unittest
from unittest.mock import Mock, patch, MagicMock
import json
import os
import tempfile
import time
from datetime import datetime
from pathlib import Path

import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scripts.shopify_extractor import (
    ShopifyExtractor,
    ExtractionConfig,
    RateLimiter
)


class TestRateLimiter(unittest.TestCase):
    """Test cases for token bucket rate limiter."""

    def test_rate_limiter_initialization(self):
        """Test rate limiter initializes correctly."""
        limiter = RateLimiter(tokens_per_second=2.0, bucket_size=40)

        self.assertEqual(limiter.tokens_per_second, 2.0)
        self.assertEqual(limiter.bucket_size, 40)
        self.assertEqual(limiter.tokens, 40)

    def test_rate_limiter_acquire_immediate(self):
        """Test acquiring tokens when bucket is full."""
        limiter = RateLimiter(tokens_per_second=10.0, bucket_size=40)

        start_time = time.time()
        limiter.acquire(5)
        elapsed = time.time() - start_time

        # Should be immediate (< 100ms)
        self.assertLess(elapsed, 0.1)
        self.assertEqual(limiter.tokens, 35)

    def test_rate_limiter_acquire_blocking(self):
        """Test acquiring tokens blocks when bucket is empty."""
        limiter = RateLimiter(tokens_per_second=10.0, bucket_size=5)

        # Exhaust bucket
        limiter.acquire(5)

        # Next acquire should block
        start_time = time.time()
        limiter.acquire(1)
        elapsed = time.time() - start_time

        # Should wait approximately 0.1 seconds (1 token at 10 tokens/sec)
        self.assertGreaterEqual(elapsed, 0.09)
        self.assertLess(elapsed, 0.2)

    def test_rate_limiter_refill(self):
        """Test bucket refills over time."""
        limiter = RateLimiter(tokens_per_second=10.0, bucket_size=40)

        # Use some tokens
        limiter.acquire(10)
        self.assertEqual(limiter.tokens, 30)

        # Wait for refill
        time.sleep(0.5)

        # Acquire again (should have refilled ~5 tokens)
        limiter.acquire(1)
        self.assertGreaterEqual(limiter.tokens, 33)


class TestShopifyExtractor(unittest.TestCase):
    """Test cases for Shopify API extractor."""

    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()

        self.config = ExtractionConfig(
            shop_url='test-store.myshopify.com',
            api_key='test-key',
            api_secret='test-secret',
            api_version='2024-01',
            endpoint='orders',
            rate_limit_per_second=100.0,  # Fast for testing
            page_size=10,
            output_format='json',
            output_path=self.temp_dir,
            incremental_state_file=f'{self.temp_dir}/state.json',
        )

    def tearDown(self):
        """Clean up test fixtures."""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    @patch('scripts.shopify_extractor.requests.Session')
    def test_extractor_initialization(self, mock_session):
        """Test extractor initializes correctly."""
        extractor = ShopifyExtractor(self.config)

        self.assertEqual(extractor.config, self.config)
        self.assertIsNotNone(extractor.session)
        self.assertIsNotNone(extractor.rate_limiter)

    @patch('scripts.shopify_extractor.requests.Session')
    def test_make_request_success(self, mock_session_class):
        """Test successful API request."""
        # Mock response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {'orders': [{'id': 1}]}
        mock_response.headers = {
            'X-Shopify-Shop-Api-Call-Limit': '1/40'
        }

        mock_session = Mock()
        mock_session.get.return_value = mock_response
        mock_session_class.return_value = mock_session

        extractor = ShopifyExtractor(self.config)
        result = extractor._make_request('https://test.com/orders.json')

        self.assertEqual(result, {'orders': [{'id': 1}]})
        mock_session.get.assert_called_once()

    @patch('scripts.shopify_extractor.requests.Session')
    def test_make_request_rate_limited(self, mock_session_class):
        """Test handling of rate limit (429) response."""
        # First response: rate limited
        mock_response_429 = Mock()
        mock_response_429.status_code = 429
        mock_response_429.headers = {'Retry-After': '0.1'}

        # Second response: success
        mock_response_200 = Mock()
        mock_response_200.status_code = 200
        mock_response_200.json.return_value = {'orders': [{'id': 1}]}
        mock_response_200.headers = {}

        mock_session = Mock()
        mock_session.get.side_effect = [mock_response_429, mock_response_200]
        mock_session_class.return_value = mock_session

        extractor = ShopifyExtractor(self.config)

        start_time = time.time()
        result = extractor._make_request('https://test.com/orders.json')
        elapsed = time.time() - start_time

        # Should have waited for retry
        self.assertGreaterEqual(elapsed, 0.09)
        self.assertEqual(result, {'orders': [{'id': 1}]})
        self.assertEqual(mock_session.get.call_count, 2)

    @patch('scripts.shopify_extractor.requests.Session')
    def test_pagination(self, mock_session_class):
        """Test cursor-based pagination."""
        # Page 1 response
        page1_data = [{'id': 1}, {'id': 2}]
        mock_response_1 = Mock()
        mock_response_1.json.return_value = {'orders': page1_data}

        # Page 2 response
        page2_data = [{'id': 3}, {'id': 4}]
        mock_response_2 = Mock()
        mock_response_2.json.return_value = {'orders': page2_data}

        # Page 3 response (empty)
        mock_response_3 = Mock()
        mock_response_3.json.return_value = {'orders': []}

        # Mock head requests for Link headers
        mock_head_1 = Mock()
        mock_head_1.headers = {
            'Link': '<https://test.com/orders.json?page=2>; rel="next"'
        }

        mock_head_2 = Mock()
        mock_head_2.headers = {
            'Link': '<https://test.com/orders.json?page=3>; rel="next"'
        }

        mock_head_3 = Mock()
        mock_head_3.headers = {}

        mock_session = Mock()
        mock_session.get.side_effect = [
            mock_response_1,
            mock_response_2,
            mock_response_3
        ]
        mock_session.head.side_effect = [
            mock_head_1,
            mock_head_2,
            mock_head_3
        ]
        mock_session_class.return_value = mock_session

        extractor = ShopifyExtractor(self.config)

        # Collect all pages
        all_data = []
        for page in extractor._paginate('orders'):
            all_data.extend(page)

        # Should have collected all records from 2 pages
        self.assertEqual(len(all_data), 4)
        self.assertEqual(all_data[0]['id'], 1)
        self.assertEqual(all_data[3]['id'], 4)

    @patch('scripts.shopify_extractor.requests.Session')
    def test_save_json(self, mock_session_class):
        """Test saving data as JSON."""
        mock_session_class.return_value = Mock()

        extractor = ShopifyExtractor(self.config)

        test_data = [
            {'id': 1, 'name': 'Order 1'},
            {'id': 2, 'name': 'Order 2'},
        ]

        filepath = f'{self.temp_dir}/test.json'
        extractor._save_json(test_data, filepath)

        # Verify file was created
        self.assertTrue(os.path.exists(filepath))

        # Verify content
        with open(filepath, 'r') as f:
            loaded_data = json.load(f)

        self.assertEqual(loaded_data, test_data)

    @patch('scripts.shopify_extractor.requests.Session')
    def test_flatten_record(self, mock_session_class):
        """Test flattening nested records."""
        mock_session_class.return_value = Mock()

        extractor = ShopifyExtractor(self.config)

        nested_record = {
            'id': 1,
            'customer': {
                'name': 'John Doe',
                'email': 'john@example.com',
                'address': {
                    'city': 'New York',
                    'country': 'USA'
                }
            },
            'line_items': [
                {'product_id': 101, 'quantity': 2}
            ]
        }

        flat = extractor._flatten_record(nested_record)

        # Verify nested fields are flattened
        self.assertEqual(flat['id'], 1)
        self.assertEqual(flat['customer_name'], 'John Doe')
        self.assertEqual(flat['customer_email'], 'john@example.com')
        self.assertEqual(flat['customer_address_city'], 'New York')
        self.assertEqual(flat['customer_address_country'], 'USA')

        # Verify lists are converted to JSON strings
        self.assertIsInstance(flat['line_items'], str)
        self.assertIn('product_id', flat['line_items'])

    @patch('scripts.shopify_extractor.requests.Session')
    def test_watermark_management(self, mock_session_class):
        """Test watermark save and load."""
        mock_session_class.return_value = Mock()

        extractor = ShopifyExtractor(self.config)

        # Initially no watermark
        watermark = extractor._get_watermark()
        self.assertIsNone(watermark)

        # Save watermark
        test_watermark = '2024-11-19T12:00:00Z'
        extractor._save_watermark(test_watermark)

        # Verify watermark was saved
        self.assertTrue(os.path.exists(self.config.incremental_state_file))

        # Load watermark
        loaded_watermark = extractor._get_watermark()
        self.assertEqual(loaded_watermark, test_watermark)

    @patch('scripts.shopify_extractor.requests.Session')
    def test_full_extraction_flow(self, mock_session_class):
        """Test complete extraction flow."""
        # Mock API responses
        mock_data = [
            {'id': 1, 'updated_at': '2024-11-19T10:00:00Z'},
            {'id': 2, 'updated_at': '2024-11-19T11:00:00Z'},
        ]

        mock_response = Mock()
        mock_response.json.return_value = {'orders': mock_data}

        mock_head = Mock()
        mock_head.headers = {}  # No next page

        mock_session = Mock()
        mock_session.get.return_value = mock_response
        mock_session.head.return_value = mock_head
        mock_session_class.return_value = mock_session

        extractor = ShopifyExtractor(self.config)

        # Run extraction
        output_file = extractor.extract(full_refresh=True)

        # Verify output file was created
        self.assertTrue(os.path.exists(output_file))

        # Verify watermark was updated
        watermark = extractor._get_watermark()
        self.assertEqual(watermark, '2024-11-19T11:00:00Z')


class TestExtractionConfig(unittest.TestCase):
    """Test cases for extraction configuration."""

    def test_config_defaults(self):
        """Test configuration default values."""
        config = ExtractionConfig(
            shop_url='test.myshopify.com',
            api_key='key',
            api_secret='secret'
        )

        self.assertEqual(config.api_version, '2024-01')
        self.assertEqual(config.endpoint, 'orders')
        self.assertEqual(config.rate_limit_per_second, 2.0)
        self.assertEqual(config.page_size, 250)
        self.assertEqual(config.output_format, 'parquet')

    def test_config_custom_values(self):
        """Test configuration with custom values."""
        config = ExtractionConfig(
            shop_url='test.myshopify.com',
            api_key='key',
            api_secret='secret',
            api_version='2023-10',
            endpoint='products',
            rate_limit_per_second=1.0,
            page_size=100,
            output_format='json'
        )

        self.assertEqual(config.api_version, '2023-10')
        self.assertEqual(config.endpoint, 'products')
        self.assertEqual(config.rate_limit_per_second, 1.0)
        self.assertEqual(config.page_size, 100)
        self.assertEqual(config.output_format, 'json')


if __name__ == '__main__':
    unittest.main()
