#!/bin/bash
set -e
echo "Secure SQL Server to Synapse Pipeline - Test Runner"
python3 -m pytest tests/test_pipeline.py -v && echo "✓ Tests passed!"
