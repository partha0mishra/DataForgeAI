# Example 08: Cost-Optimized Serverless Pipeline

**CFO-friendly architecture**

## Overview

Build a serverless pipeline using only AWS Glue + Athena + Step Functions: trigger on S3 put event, auto-scale Spark jobs, shut down after completion. Process 10TB/month for under $50.

## Architecture

```
┌─────────────┐     ┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│ S3 Put Event│────▶│ Step Function│────▶│ Glue Job     │────▶│ Athena Tables│
│ (EventBridge│     │ (Orchestrate)│     │ (Auto-scale) │     │ (Query)      │
└─────────────┘     └──────────────┘     └──────────────┘     └──────────────┘
                                                 │
                                                 ▼
                                          Shuts down after
                                          completion (no idle cost)
```

## Use Case

Cost-conscious deployments. Shows:
- Event-driven architecture (S3 → Lambda → Glue)
- Auto-scaling Glue jobs (pay only for run time)
- Athena for ad-hoc queries (serverless)
- Step Functions for orchestration
- Cost under $50/month for 10TB processed

## Prerequisites

- **AWS Account:** With Glue, Athena, Step Functions
- **S3 Bucket:** For data storage
- **IAM Roles:** For service permissions

## Quick Start

```bash
# Deploy infrastructure
cd terraform/
terraform init
terraform apply

# Upload test data (triggers pipeline automatically)
aws s3 cp sample_data/test.csv s3://your-bucket/raw/

# Query results with Athena
aws athena start-query-execution \
  --query-string "SELECT * FROM processed_data LIMIT 10" \
  --result-configuration "OutputLocation=s3://your-bucket/athena-results/"
```

## Expected Results

- S3 event triggers pipeline automatically
- Glue job processes data in 5-10 minutes
- Athena table updated
- Total cost: ~$0.10 per TB processed

## What You'll Learn

- ✅ Event-driven serverless architecture
- ✅ AWS Glue auto-scaling
- ✅ Athena serverless queries
- ✅ Step Functions orchestration
- ✅ Cost optimization techniques
- ✅ Infrastructure as Code (Terraform)

## File Structure

```
08-cost-optimized-serverless/
├── README.md
├── config.yaml
├── glue/
│   └── spark_job.py                   # Glue Spark job
├── step_functions/
│   └── orchestration.json             # State machine
├── terraform/
│   └── infrastructure.tf              # IaC for all resources
└── cost_analysis/
    └── estimate.md                    # Detailed cost breakdown
```

## Configuration

```yaml
glue:
  job_name: cost-optimized-etl
  worker_type: G.1X  # $0.44/DPU-hour
  number_of_workers: 2  # Auto-scales up to 10
  max_concurrent_runs: 5

athena:
  database: analytics
  workgroup: cost-optimized
  encryption: SSE_S3

s3:
  raw_bucket: s3://data-raw
  processed_bucket: s3://data-processed
  lifecycle_policy: enabled  # Move to IA after 30 days
```

## Cost Breakdown

**Monthly costs for 10TB processed:**

| Service | Usage | Unit Cost | Total |
|---------|-------|-----------|-------|
| Glue | 2 DPUs × 20 hours | $0.44/DPU-hour | $17.60 |
| Athena | 500 GB scanned | $5/TB | $2.50 |
| S3 Standard | 10 TB stored | $0.023/GB | $230 |
| S3 Intelligent Tiering | 10 TB (optimized) | $0.0125/GB | $125 |
| Step Functions | 1000 transitions | $0.025/1000 | $0.03 |
| **Total (optimized)** | | | **$145** |
| **With IA/Glacier** | | | **~$40-50** |

**Cost Optimization Tips:**
- Use S3 Intelligent Tiering (saves 50%)
- Compress data (Parquet/ORC - saves 70-80%)
- Partition Athena tables (query less data)
- Use Glue job bookmarks (avoid reprocessing)

## Implementation Status

🚧 **Coming Soon** - This example is under development.

**Planned components:**
- [ ] Complete Terraform infrastructure
- [ ] Glue job with partitioning
- [ ] Step Functions state machine
- [ ] Cost monitoring dashboard
- [ ] S3 lifecycle policies
- [ ] Budget alerts

## Performance Tuning

```yaml
# For faster processing (higher cost)
glue:
  worker_type: G.2X  # Double the memory/CPU
  number_of_workers: 10

# For lower cost (slower processing)
glue:
  worker_type: G.1X
  number_of_workers: 2
  timeout: 2880  # 48 hours max
```

## Next Steps

- Try **Example 09** for adding security/governance
- Set up **Cost Monitoring** with AWS Cost Explorer
- Add **Data Quality** checks from Accelerator 02

## Resources

- [AWS Glue Pricing](https://aws.amazon.com/glue/pricing/)
- [Athena Cost Optimization](https://aws.amazon.com/blogs/big-data/top-10-performance-tuning-tips-for-amazon-athena/)
- [S3 Intelligent Tiering](https://aws.amazon.com/s3/storage-classes/intelligent-tiering/)
