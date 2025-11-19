/*
 * Data Quality Tests for Sales Data
 *
 * This file contains custom dbt tests that validate data quality rules
 * for the sales pipeline. These tests run after model materialization
 * and will fail the pipeline if quality issues are detected.
 *
 * Test Types:
 * 1. Uniqueness tests
 * 2. Null checks on critical fields
 * 3. Value range validations
 * 4. Referential integrity checks
 * 5. Temporal consistency checks
 *
 * Usage: dbt test --models sales_clean
 */

-- Test 1: Check for duplicate sale_ids in silver layer
-- Should return 0 rows
{{ config(severity='error') }}

WITH duplicate_check AS (
    SELECT
        sale_id,
        COUNT(*) as occurrence_count
    FROM {{ ref('sales_clean') }}
    GROUP BY sale_id
    HAVING COUNT(*) > 1
)

SELECT
    sale_id,
    occurrence_count,
    'Duplicate sale_id found' as error_message
FROM duplicate_check

UNION ALL

-- Test 2: Check for null critical fields
-- sale_id should never be null
SELECT
    COALESCE(sale_id, 'NULL') as sale_id,
    1 as occurrence_count,
    'Null sale_id detected' as error_message
FROM {{ ref('sales_clean') }}
WHERE sale_id IS NULL

UNION ALL

-- Test 3: Check for null customer_id
SELECT
    sale_id,
    1 as occurrence_count,
    'Null customer_id detected' as error_message
FROM {{ ref('sales_clean') }}
WHERE customer_id IS NULL

UNION ALL

-- Test 4: Check for negative or zero amounts
-- All amounts should be positive
SELECT
    sale_id,
    1 as occurrence_count,
    'Invalid amount (<=0): ' || amount as error_message
FROM {{ ref('sales_clean') }}
WHERE amount <= 0

UNION ALL

-- Test 5: Check for negative or zero quantities
SELECT
    sale_id,
    1 as occurrence_count,
    'Invalid quantity (<=0): ' || quantity as error_message
FROM {{ ref('sales_clean') }}
WHERE quantity <= 0

UNION ALL

-- Test 6: Check for future dates
-- sale_date should not be in the future
SELECT
    sale_id,
    1 as occurrence_count,
    'Future sale_date detected: ' || sale_date as error_message
FROM {{ ref('sales_clean') }}
WHERE sale_date > CURRENT_DATE()

UNION ALL

-- Test 7: Check for very old dates (likely data quality issue)
-- sale_date should be within last 10 years
SELECT
    sale_id,
    1 as occurrence_count,
    'Sale date too old (>10 years): ' || sale_date as error_message
FROM {{ ref('sales_clean') }}
WHERE sale_date < DATEADD(year, -10, CURRENT_DATE())

UNION ALL

-- Test 8: Check for unrealistic amounts
-- Amount should be less than 1 million (adjust threshold as needed)
SELECT
    sale_id,
    1 as occurrence_count,
    'Unrealistic amount (>1M): ' || amount as error_message
FROM {{ ref('sales_clean') }}
WHERE amount > 1000000

UNION ALL

-- Test 9: Check for unrealistic quantities
-- Quantity should be less than 10,000 (adjust threshold as needed)
SELECT
    sale_id,
    1 as occurrence_count,
    'Unrealistic quantity (>10K): ' || quantity as error_message
FROM {{ ref('sales_clean') }}
WHERE quantity > 10000

UNION ALL

-- Test 10: Check total_value calculation
-- total_value should equal amount * quantity
SELECT
    sale_id,
    1 as occurrence_count,
    'Incorrect total_value calculation' as error_message
FROM {{ ref('sales_clean') }}
WHERE ABS(total_value - (amount * quantity)) > 0.01

-- This query should return 0 rows if all tests pass
-- If any test fails, dbt will report it with the error message
