#!/bin/bash
set -e
echo "Feature Store Churn Prediction Pipeline - Test Runner"
python3 -m pytest tests/test_pipeline.py -v && echo "✓ All tests passed!"
