# Cost Analysis: Serverless ETL Pipeline

## Executive Summary

This document provides a detailed cost breakdown for processing 10TB of data monthly using AWS serverless services. The architecture is optimized for cost-efficiency while maintaining performance and reliability.

**Monthly Estimate: $642.50**
**Per-GB Processing Cost: $0.064**

---

## Scenario Parameters

- **Monthly Data Volume**: 10 TB (10,240 GB)
- **Average File Size**: 100 MB
- **Number of Files**: ~102,400 files/month
- **Processing Frequency**: Daily (30 days/month)
- **Average Glue Job Duration**: 30 minutes per run
- **Glue Workers**: 2 workers (G.1X = 1 DPU each)
- **Athena Query Volume**: 1000 queries/month
- **Average Query Scans**: 50 GB/query
- **Retention Period**: 90 days for processed data

---

## Detailed Cost Breakdown

### 1. AWS Glue ETL Processing

#### Glue Job Execution
- **DPU Capacity**: 2 DPU (G.1X workers)
- **Duration per Run**: 30 minutes (0.5 hours)
- **Runs per Month**: 30 daily runs
- **Total DPU Hours**: 2 DPU × 0.5 hours × 30 runs = 30 DPU-hours
- **Cost per DPU-hour**: $0.44 (us-east-1)
- **Monthly Cost**: 30 × $0.44 = **$13.20**

#### Glue Data Catalog
- **Objects Stored**: ~500 tables/partitions
- **First 1M objects**: Free
- **Monthly Cost**: **$0.00**

#### Glue Crawler (Run 30 times/month)
- **Duration per Run**: ~5 minutes (0.083 hours)
- **DPU Capacity**: 2 DPU
- **Total DPU Hours**: 2 × 0.083 × 30 = 5 DPU-hours
- **Monthly Cost**: 5 × $0.44 = **$2.20**

**Glue Total: $15.40**

---

### 2. Amazon S3 Storage

#### Raw Data Bucket
- **Data Stored**: 10 TB/month (transient)
- **Average Storage**: 5 TB (with lifecycle transitions)
- **Standard Storage**: 2 TB × $0.023/GB = $46.00
- **Standard-IA**: 2 TB × $0.0125/GB = $25.00
- **Glacier Instant Retrieval**: 1 TB × $0.004/GB = $4.00
- **Monthly Cost**: **$75.00**

#### Processed Data Bucket (Parquet, compressed)
- **Compression Ratio**: 5:1 (Parquet with Snappy)
- **Storage Size**: 2 TB (10 TB / 5)
- **Intelligent Tiering**: 2 TB × $0.023/GB = **$46.00**
- **Storage Class Analysis**: $0.10 per million objects analyzed
- **Monthly Cost**: **$46.10**

#### Athena Results Bucket
- **Query Results**: ~100 GB
- **Lifecycle**: 30-day expiration
- **Monthly Cost**: 100 GB × $0.023 = **$2.30**

#### Scripts Bucket
- **Size**: < 1 GB
- **Monthly Cost**: **$0.02**

#### S3 Request Costs
- **PUT Requests**: 102,400 files × $0.005/1000 = $0.51
- **GET Requests**: 102,400 reads × $0.0004/1000 = $0.04
- **LIST Requests**: Negligible
- **Monthly Cost**: **$0.55**

**S3 Total: $123.97**

---

### 3. Amazon Athena

#### Query Execution
- **Queries per Month**: 1,000
- **Data Scanned per Query**: 50 GB average
- **Total Data Scanned**: 1,000 × 50 GB = 50 TB
- **Cost per TB Scanned**: $5.00
- **Monthly Cost**: 50 × $5.00 = **$250.00**

**Optimization Note**: Partitioning and Parquet format reduce scans by 80% compared to unpartitioned CSV. Without optimization, this would be $1,250/month.

**Athena Total: $250.00**

---

### 4. AWS Step Functions

#### State Transitions
- **Executions per Month**: 30
- **Average Transitions per Execution**: 15 states
- **Total Transitions**: 30 × 15 = 450
- **First 4,000 Transitions**: Free
- **Monthly Cost**: **$0.00**

**Step Functions Total: $0.00**

---

### 5. AWS Lambda (Cost Calculator)

#### Function Invocations
- **Invocations per Month**: 30
- **Duration**: 1 second average
- **Memory**: 512 MB
- **Compute GB-seconds**: 30 × 0.5 GB × 1s = 15 GB-seconds
- **First 400,000 GB-seconds**: Free
- **Monthly Cost**: **$0.00**

**Lambda Total: $0.00**

---

### 6. Amazon SNS (Notifications)

#### Notifications
- **Messages per Month**: 60 (success + failure notifications)
- **Email Delivery**: 60 emails
- **First 1,000 Publishes**: Free
- **Email Deliveries**: Free for first 1,000
- **Monthly Cost**: **$0.00**

**SNS Total: $0.00**

---

### 7. Amazon EventBridge

#### Event Processing
- **Events per Month**: 102,400 (one per file)
- **Custom Events**: $1.00 per million events
- **Monthly Cost**: 0.1024 × $1.00 = **$0.10**

**EventBridge Total: $0.10**

---

### 8. Amazon CloudWatch

#### Logs
- **Glue Job Logs**: 30 runs × 50 MB = 1.5 GB
- **Step Functions Logs**: 30 runs × 10 MB = 0.3 GB
- **Total Ingestion**: 1.8 GB
- **Ingestion Cost**: 1.8 GB × $0.50 = $0.90
- **Storage Cost**: 1.8 GB × $0.03 = $0.05
- **Monthly Cost**: **$0.95**

#### Metrics
- **Custom Metrics**: 10 metrics
- **First 10 Metrics**: Free
- **Monthly Cost**: **$0.00**

#### Alarms
- **Alarms**: 3 (budget, errors, performance)
- **First 10 Alarms**: Free
- **Monthly Cost**: **$0.00**

**CloudWatch Total: $0.95**

---

### 9. Data Transfer

#### Within AWS Region
- **S3 to Glue**: Free
- **Glue to S3**: Free
- **S3 to Athena**: Free

#### Internet Egress (if any)
- **Athena Results Download**: 10 GB/month
- **First 100 GB**: $0.09/GB
- **Monthly Cost**: 10 × $0.09 = **$0.90**

**Data Transfer Total: $0.90**

---

## Monthly Cost Summary

| Service | Monthly Cost | Percentage |
|---------|--------------|------------|
| Amazon Athena | $250.00 | 38.9% |
| Amazon S3 Storage | $123.97 | 19.3% |
| AWS Glue ETL | $15.40 | 2.4% |
| AWS Step Functions | $0.00 | 0.0% |
| AWS Lambda | $0.00 | 0.0% |
| Amazon SNS | $0.00 | 0.0% |
| Amazon EventBridge | $0.10 | 0.0% |
| Amazon CloudWatch | $0.95 | 0.1% |
| Data Transfer | $0.90 | 0.1% |
| **Total** | **$642.50** | **100%** |

---

## Cost Optimization Strategies

### 1. Reduce Athena Query Costs (Potential Savings: 50-80%)

#### Strategy A: Query Optimization
- **Partition Pruning**: Ensure queries filter by partition keys
- **Columnar Selection**: Use `SELECT column1, column2` instead of `SELECT *`
- **Compression**: Already using Parquet with Snappy compression
- **File Size**: Maintain 128-256 MB files for optimal performance
- **Estimated Savings**: $125/month (50%)

#### Strategy B: Materialized Views
- Create pre-aggregated tables for common queries
- Update incrementally to reduce scan volumes
- **Estimated Savings**: $150/month (60%)

#### Strategy C: Use Amazon Athena Federated Queries Sparingly
- Direct S3 queries are more cost-effective
- Cache frequent query results
- **Estimated Savings**: Variable

### 2. Optimize S3 Storage (Potential Savings: 30-40%)

#### Lifecycle Policies
- **Implementation**: Already configured
  - Move to Standard-IA after 30 days
  - Move to Glacier IR after 90 days
  - Delete raw data after 365 days
- **Current Savings**: $100/month vs. all Standard storage

#### Intelligent Tiering
- Automatically move data between access tiers
- No retrieval fees for Frequent/Infrequent tiers
- **Additional Savings**: $20/month

### 3. Glue Job Optimization (Potential Savings: 20-30%)

#### Auto-Scaling
- Use Glue's auto-scaling feature
- Start with 2 workers, scale up to 10 as needed
- **Implementation**: Already configured
- **Estimated Savings**: $3-5/month

#### Job Bookmarks
- Process only new/changed data
- Avoid reprocessing entire datasets
- **Implementation**: Already enabled
- **Current Savings**: $10-15/month

#### Worker Type Selection
- G.1X (1 DPU): General purpose
- G.2X (2 DPU): Memory-intensive workloads
- **Right-sizing Savings**: $5/month if optimized

### 4. Schedule Optimization (Potential Savings: Variable)

#### Batch Processing
- Process multiple files in single Glue run
- Reduce number of executions
- **Estimated Savings**: $5-10/month

#### Off-Peak Processing
- Run non-critical jobs during off-peak hours
- Take advantage of potential future pricing tiers
- **Estimated Savings**: Not currently available on AWS

### 5. Reserved Capacity (Not Applicable)
- Glue does not offer reserved capacity
- Consider AWS Savings Plans for overall account optimization

### 6. Data Retention Policies (Potential Savings: 20-30%)

#### Aggressive Lifecycle
- Reduce raw data retention from 365 to 90 days
- **Savings**: $25/month
- **Trade-off**: Less historical raw data availability

#### Processed Data Archival
- Archive data older than 1 year to Glacier Deep Archive
- **Savings**: $15/month after year 1
- **Trade-off**: Higher retrieval costs and latency

---

## Comparison: Serverless vs. Always-On Alternatives

### Alternative 1: Amazon EMR (Always-On Cluster)

#### EMR Configuration
- **Cluster**: 1 master + 2 core nodes
- **Instance Type**: m5.xlarge (4 vCPU, 16 GB RAM)
- **Running 24/7**

#### Monthly Cost Breakdown
- **EC2 Instances**: 3 × $0.192/hour × 730 hours = $420.48
- **EMR Service Fee**: 3 × $0.048/hour × 730 hours = $105.12
- **EBS Storage**: 3 × 100 GB × $0.10 = $30.00
- **S3 Storage**: $123.97 (same as serverless)
- **Total**: **$679.57/month**

**Comparison**:
- Serverless: $642.50
- EMR Always-On: $679.57
- **Serverless Savings**: $37.07/month (5.4%)

**Note**: For intermittent workloads (< 50% utilization), serverless saves significantly more.

### Alternative 2: Amazon EMR (On-Demand, Auto-Terminating)

#### EMR Configuration (Same as above, but auto-terminating)
- **Usage**: 15 hours/month (30 runs × 30 minutes)

#### Monthly Cost Breakdown
- **EC2 Instances**: 3 × $0.192 × 15 = $8.64
- **EMR Service Fee**: 3 × $0.048 × 15 = $2.16
- **EBS Storage**: $30.00 (allocated even when cluster off)
- **S3 Storage**: $123.97
- **Total**: **$164.77/month**

**Comparison**:
- Serverless: $642.50
- EMR On-Demand: $164.77
- **EMR Savings**: $477.73/month (74.4%)

**However**: EMR requires more operational overhead, and the high Athena costs (not required with EMR) skew this comparison. If Athena usage is optimized or eliminated, serverless becomes competitive.

### Alternative 3: Self-Managed Spark on EC2

#### Configuration
- **Instances**: 3 × m5.xlarge (spot instances)
- **Spot Pricing**: ~70% discount ($0.058/hour)
- **Usage**: 15 hours/month

#### Monthly Cost Breakdown
- **Spot Instances**: 3 × $0.058 × 15 = $2.61
- **EBS Storage**: $30.00
- **S3 Storage**: $123.97
- **Operational Overhead**: High (manual setup, monitoring)
- **Total**: **$156.58/month**

**Comparison**:
- Serverless: $642.50
- Self-Managed Spot: $156.58
- **Spot Savings**: $485.92/month (75.6%)

**Trade-offs**:
- Significantly higher operational complexity
- Spot instance interruptions
- No managed services (Glue catalog, Step Functions)
- Not recommended unless cost is paramount

---

## Cost Optimization Recommendations

### Immediate Actions (Implement Now)

1. **Optimize Athena Queries**
   - Review top 10 queries by data scanned
   - Add partition filters to all queries
   - Use columnar selection (avoid `SELECT *`)
   - **Expected Savings**: $125/month (50% reduction)

2. **Enable S3 Intelligent Tiering**
   - Automatically optimize storage costs
   - No performance impact
   - **Expected Savings**: $20/month

3. **Review Athena Query Volume**
   - Identify redundant or unnecessary queries
   - Cache results for repeated queries
   - **Expected Savings**: $50/month (20% reduction)

### Medium-Term Actions (1-3 months)

1. **Create Materialized Views**
   - Pre-aggregate common analytics
   - Reduce Athena scan volumes
   - **Expected Savings**: $100/month

2. **Implement Query Result Caching**
   - Use application-level caching (Redis, DynamoDB)
   - Cache frequent query results for 1-24 hours
   - **Expected Savings**: $75/month

3. **Optimize Data Partitioning**
   - Review partition strategy (currently year/month/day)
   - Consider hour-level partitions for high-volume data
   - **Expected Savings**: $25/month

### Long-Term Actions (3-6 months)

1. **Evaluate Amazon Redshift Spectrum**
   - For high-volume analytical queries
   - Fixed-cost alternative to Athena
   - **Break-even**: ~1,000+ queries/month with similar scan volumes

2. **Implement Data Lake Analytics Patterns**
   - Use AWS Lake Formation for centralized governance
   - Optimize with Glue DataBrew for profiling
   - **Expected Savings**: Variable, with improved data quality

3. **Consider Amazon QuickSight SPICE**
   - In-memory analytics for dashboards
   - Reduce Athena query frequency
   - **Expected Savings**: $100/month if 40% of queries eliminated

---

## Projected Costs with Optimizations

| Scenario | Monthly Cost | Annual Cost | Savings vs. Baseline |
|----------|--------------|-------------|----------------------|
| **Baseline (Current)** | $642.50 | $7,710.00 | - |
| **Immediate Optimizations** | $447.50 | $5,370.00 | $2,340/year (30%) |
| **Medium-Term Optimizations** | $272.50 | $3,270.00 | $4,440/year (58%) |
| **Full Optimization** | $192.50 | $2,310.00 | $5,400/year (70%) |

---

## Cost Per Unit Metrics

- **Cost per GB Processed**: $0.064
- **Cost per File Processed**: $0.0063
- **Cost per Glue Job Run**: $21.42
- **Cost per Athena Query**: $0.25
- **Cost per Million Records** (estimated): $6.43

---

## Budget Alerts and Monitoring

### Recommended CloudWatch Alarms

1. **Monthly Budget Alert (80% threshold)**
   - Trigger: Estimated charges > $514 ($642.50 × 0.8)
   - Action: SNS notification to data engineering team

2. **Daily Cost Anomaly Detection**
   - Trigger: Daily spend > $30 ($642.50 / 30 days + 50% margin)
   - Action: Investigate for unexpected job failures or runaway queries

3. **Athena Query Cost Monitoring**
   - Trigger: Single query scans > 500 GB
   - Action: Alert and auto-kill expensive queries

4. **Glue Job Duration Alert**
   - Trigger: Job runtime > 1 hour (2x expected)
   - Action: Investigate for data quality issues or performance degradation

### Cost Allocation Tags

Implement the following tags for detailed cost tracking:

```hcl
tags = {
  Project     = "DataForgeAI"
  Accelerator = "pipeline-automation"
  Example     = "cost-optimized-serverless"
  Environment = "production"
  CostCenter  = "engineering"
  DataOwner   = "data-team"
}
```

Use AWS Cost Explorer with these tags to:
- Track costs by project/team
- Identify cost trends
- Forecast future spending
- Allocate costs to business units

---

## Conclusion

The serverless ETL pipeline provides a cost-effective solution for processing 10TB of data monthly at approximately $642.50/month. The largest cost driver is Amazon Athena query execution (39% of total), which can be significantly reduced through query optimization and caching strategies.

**Key Takeaways**:
1. Serverless is cost-competitive for intermittent workloads
2. Athena optimization offers the highest ROI for cost reduction
3. With full optimizations, costs can be reduced by 70% to ~$192/month
4. Always-on alternatives (EMR) are more expensive for this usage pattern
5. Proper partitioning, compression, and query patterns are critical

**Next Steps**:
1. Implement immediate cost optimizations (estimated 30% savings)
2. Monitor actual usage patterns for 30 days
3. Adjust Glue job configurations based on observed performance
4. Evaluate Athena query patterns and optimize top offenders
5. Review cost allocations monthly and adjust budget alerts

---

## Appendix: Cost Calculator

Use this formula to estimate costs for different data volumes:

```
Monthly Cost =
  (Glue_Runs × 2_DPU × 0.5_hours × $0.44) +
  (Data_Volume_TB × 0.2 × $23/TB) +  # S3 storage (compressed)
  (Athena_Queries × Avg_Scan_GB × $5/TB / 1000) +
  (Data_Volume_TB × 1.024 × $0.023)  # Raw storage (transient)
```

**Example for 50TB/month**:
- Glue: (30 × 2 × 0.5 × $0.44) = $13.20
- S3 Processed: (50 × 0.2 × $23) = $230.00
- Athena: (1000 × 50 × $5 / 1000) = $250.00
- S3 Raw: (50 × 1.024 × $23) = $1,177.60
- **Total**: ~$1,670.80/month

**Scaling Factor**: Approximately linear with data volume, with S3 storage dominating at higher scales.
