# Example 05: Real-time Streaming with Windowed Aggregations

**Prove data lakes aren't slow**

## Overview

Real-time fraud detection pipeline: ingest from Kinesis stream, apply 5-minute tumbling window aggregations, join with static customer risk table in Redis, and alert via Slack if fraud score > 0.8.

## Architecture

```
┌──────────────┐     ┌────────────────┐     ┌──────────────┐     ┌─────────────┐
│ AWS Kinesis  │────▶│ Spark Streaming│────▶│ Risk Scoring │────▶│ Slack Alert │
│ transactions │     │ 5-min window   │     │ + Redis Join │     │ if score>.8 │
└──────────────┘     └────────────────┘     └──────────────┘     └─────────────┘
                              │
                              ▼
                     ┌────────────────┐
                     │ Delta Lake     │
                     │ fraud_events   │
                     └────────────────┘
```

## Use Case

Real-time anomaly detection, fraud prevention, alerting. Shows:
- Sub-minute latency processing
- Tumbling/sliding window operations
- Stream-static joins (Kinesis + Redis)
- Real-time alerting
- Watermarking for late data
- Exactly-once semantics

## Prerequisites

- **AWS Kinesis:** Stream created
- **Redis:** For customer risk data
- **Spark Cluster:** With Structured Streaming
- **Slack Webhook:** For alerts

## Quick Start

```bash
# Start Spark Streaming job
spark-submit \
  --packages org.apache.spark:spark-sql-kafka-0-10_2.12:3.5.0 \
  spark/streaming_fraud_detection.py

# Load customer risk data to Redis
python redis/customer_risk_loader.py

# Simulate transactions
python scripts/transaction_generator.py --rate 100  # 100 TPS
```

## Expected Results

- Processing latency: < 30 seconds end-to-end
- Windowed metrics every 5 minutes
- Slack alerts for high-risk transactions
- Fraud events persisted to Delta Lake

## What You'll Learn

- ✅ Spark Structured Streaming
- ✅ Window functions (tumbling, sliding, session)
- ✅ Watermarking for late events
- ✅ Stream-static joins
- ✅ Exactly-once processing
- ✅ Real-time alerting
- ✅ Monitoring streaming metrics

## File Structure

```
05-realtime-streaming/
├── README.md
├── config.yaml
├── spark/
│   └── streaming_fraud_detection.py    # Spark job
├── redis/
│   └── customer_risk_loader.py         # Load risk scores
└── alerts/
    └── slack_notifier.py               # Alert handler
```

## Configuration

```yaml
streaming:
  source:
    type: kinesis
    stream_name: transactions
    region: us-east-1
    checkpoint_location: s3://bucket/checkpoints

  window:
    type: tumbling
    duration: 5 minutes
    watermark: 10 minutes

  sink:
    type: delta
    path: s3://bucket/fraud-events
    output_mode: append

alerting:
  threshold: 0.8
  slack_webhook: https://hooks.slack.com/...
```

## Implementation Status

🚧 **Coming Soon** - This example is under development.

**Planned components:**
- [ ] Kinesis consumer with checkpointing
- [ ] Windowed aggregation logic
- [ ] Redis connection pooling
- [ ] Fraud scoring algorithm
- [ ] Slack alerting
- [ ] Grafana dashboard

## Troubleshooting

**High latency?**
- Increase parallelism: `spark.streaming.kafka.maxOffsetsPerTrigger`
- Reduce window size
- Check Redis latency

**Missing events?**
- Review watermark settings
- Check for late data in metrics

## Next Steps

- Try **Example 06** for Snowflake-native streaming
- Add **Observability** from Accelerator 14

## Resources

- [Structured Streaming Guide](https://spark.apache.org/docs/latest/structured-streaming-programming-guide.html)
- [Kinesis Connector](https://github.com/qubole/kinesis-sql)
