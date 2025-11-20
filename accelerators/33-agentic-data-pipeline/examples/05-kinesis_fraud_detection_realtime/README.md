# Kinesis Real-Time Fraud Detection Pipeline

## Overview
Low-latency streaming pipeline for fraud detection with 5-minute tumbling windows and real-time alerting.

## Use Case
Financial services fraud detection with sub-minute latency requirements.

## Key Features
- ✅ Stream processing with Apache Flink or Spark Structured Streaming
- ✅ 5-minute tumbling windows for aggregation
- ✅ Join with Redis for customer risk scores
- ✅ Slack/PagerDuty alerts for high-risk transactions
- ✅ Lambda architecture (real-time + batch)

## Tech Stack
- Streaming: AWS Kinesis Data Streams
- Processing: Apache Flink on Kinesis Data Analytics
- Lookup: Redis for low-latency joins
- Alerting: Slack Webhooks + PagerDuty

## Estimated Cost
~$600-800/month (Kinesis shards, Flink processing, Redis)

## Example Prompt
```
Real-time fraud detection pipeline: ingest from Kinesis stream, 5-minute tumbling
window, join with static customer_risk table in Redis, alert if score > 0.8 via Slack.
```
