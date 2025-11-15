# Accelerator 2: Data Quality & Governance

Automated data quality validation and governance framework with Great Expectations, PII detection, and audit logging.

## Features

- **Great Expectations**: Data quality validation with custom expectations
- **PII Detection**: Automatic detection and masking of sensitive data
- **Governance Policies**: Data retention, access control, compliance
- **Audit Logging**: Complete audit trail of all data access
- **Quality Dashboard**: Real-time quality metrics
- **REST API**: Quality check management

## Components

### Great Expectations
- Custom expectations for data validation
- Checkpoint configurations
- Data docs generation
- Integration with Airflow

### Governance
- PII detection using pattern matching and ML
- Data masking and anonymization
- Retention policy enforcement
- Access control policies

### API
- Quality check endpoints
- Governance policy management
- Audit log queries
- Metrics and reporting

## Quick Start

### Local Development

```bash
# Install dependencies
cd accelerators/02-data-quality-governance
pip install -r requirements.txt

# Initialize Great Expectations
cd great_expectations
great_expectations init

# Run quality checks
python -m src.run_quality_checks

# Start API
cd api
uvicorn src.main:app --reload --port 8001
```

### Run Quality Checks

```python
from dataforge_quality import DataQualityChecker

checker = DataQualityChecker(
    data_path="s3://my-bucket/data.csv",
    expectations_suite="my_suite"
)

result = checker.validate()
print(f"Quality Score: {result.success_rate}%")
```

### PII Detection

```python
from dataforge_quality.governance import PIIDetector

detector = PIIDetector()
pii_found = detector.detect_in_dataframe(df)
masked_df = detector.mask_pii(df)
```

## Configuration

Edit `config/quality_config.yaml`:

```yaml
quality_thresholds:
  completeness: 0.95
  uniqueness: 0.99
  validity: 0.90

pii_patterns:
  - email
  - phone
  - ssn
  - credit_card

governance_policies:
  retention_days: 365
  require_encryption: true
  audit_enabled: true
```

## Integration with Airflow

Quality checks run automatically as part of data pipelines:

```python
from airflow.operators.python import PythonOperator

quality_check = PythonOperator(
    task_id='quality_check',
    python_callable=run_quality_validation,
    dag=dag
)

ingestion >> quality_check >> transformation
```

## Testing

```bash
pytest tests/ -v
```

## Deployment

```bash
kubectl apply -f k8s/
```
