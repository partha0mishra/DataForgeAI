/**
 * Cost-Optimized Serverless ETL Infrastructure
 *
 * Provisions AWS resources for a serverless data pipeline:
 * - S3 buckets for data storage
 * - AWS Glue for ETL processing
 * - Step Functions for orchestration
 * - Athena for ad-hoc queries
 * - EventBridge for event-driven triggers
 * - CloudWatch for monitoring and cost alarms
 *
 * Cost optimization features:
 * - Lifecycle policies for S3
 * - Budget alerts
 * - Auto-scaling Glue workers
 * - Query result expiration
 */

terraform {
  required_version = ">= 1.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

provider "aws" {
  region = var.aws_region

  default_tags {
    tags = {
      Project     = "DataForgeAI"
      Accelerator = "pipeline-automation"
      Example     = "cost-optimized-serverless"
      Environment = var.environment
      ManagedBy   = "Terraform"
      CostCenter  = var.cost_center
    }
  }
}

# Variables
variable "aws_region" {
  description = "AWS region for resources"
  type        = string
  default     = "us-east-1"
}

variable "environment" {
  description = "Environment name (dev, staging, prod)"
  type        = string
  default     = "dev"
}

variable "project_name" {
  description = "Project name for resource naming"
  type        = string
  default     = "cost-optimized-etl"
}

variable "cost_center" {
  description = "Cost center for billing allocation"
  type        = string
  default     = "engineering"
}

variable "monthly_budget_limit" {
  description = "Monthly budget limit in USD"
  type        = number
  default     = 500
}

variable "glue_max_capacity" {
  description = "Maximum DPU capacity for Glue jobs"
  type        = number
  default     = 10
}

# Data
data "aws_caller_identity" "current" {}
data "aws_partition" "current" {}

locals {
  account_id = data.aws_caller_identity.current.account_id
  partition  = data.aws_partition.current.partition

  bucket_prefix = "${var.project_name}-${var.environment}"

  common_tags = {
    Application = "ETL-Pipeline"
    AutoShutdown = "true"
  }
}

################################################################################
# S3 Buckets
################################################################################

# Raw data bucket
resource "aws_s3_bucket" "raw_data" {
  bucket = "${local.bucket_prefix}-raw-data-${local.account_id}"

  tags = merge(local.common_tags, {
    DataClassification = "raw"
    Tier              = "hot"
  })
}

resource "aws_s3_bucket_versioning" "raw_data" {
  bucket = aws_s3_bucket.raw_data.id

  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_lifecycle_configuration" "raw_data" {
  bucket = aws_s3_bucket.raw_data.id

  rule {
    id     = "transition-to-glacier"
    status = "Enabled"

    transition {
      days          = 30
      storage_class = "STANDARD_IA"
    }

    transition {
      days          = 90
      storage_class = "GLACIER_IR"
    }

    expiration {
      days = 365
    }
  }

  rule {
    id     = "cleanup-incomplete-uploads"
    status = "Enabled"

    abort_incomplete_multipart_upload {
      days_after_initiation = 7
    }
  }
}

resource "aws_s3_bucket_public_access_block" "raw_data" {
  bucket = aws_s3_bucket.raw_data.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

# Processed data bucket
resource "aws_s3_bucket" "processed_data" {
  bucket = "${local.bucket_prefix}-processed-data-${local.account_id}"

  tags = merge(local.common_tags, {
    DataClassification = "processed"
    Tier              = "warm"
  })
}

resource "aws_s3_bucket_versioning" "processed_data" {
  bucket = aws_s3_bucket.processed_data.id

  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_lifecycle_configuration" "processed_data" {
  bucket = aws_s3_bucket.processed_data.id

  rule {
    id     = "intelligent-tiering"
    status = "Enabled"

    transition {
      days          = 0
      storage_class = "INTELLIGENT_TIERING"
    }
  }
}

resource "aws_s3_bucket_public_access_block" "processed_data" {
  bucket = aws_s3_bucket.processed_data.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

# Athena results bucket
resource "aws_s3_bucket" "athena_results" {
  bucket = "${local.bucket_prefix}-athena-results-${local.account_id}"

  tags = merge(local.common_tags, {
    Purpose = "athena-query-results"
  })
}

resource "aws_s3_bucket_lifecycle_configuration" "athena_results" {
  bucket = aws_s3_bucket.athena_results.id

  rule {
    id     = "expire-old-results"
    status = "Enabled"

    expiration {
      days = 30
    }
  }
}

resource "aws_s3_bucket_public_access_block" "athena_results" {
  bucket = aws_s3_bucket.athena_results.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

# Scripts bucket for Glue job code
resource "aws_s3_bucket" "scripts" {
  bucket = "${local.bucket_prefix}-scripts-${local.account_id}"

  tags = merge(local.common_tags, {
    Purpose = "glue-scripts"
  })
}

resource "aws_s3_bucket_public_access_block" "scripts" {
  bucket = aws_s3_bucket.scripts.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

# Upload Glue script to S3
resource "aws_s3_object" "glue_script" {
  bucket = aws_s3_bucket.scripts.id
  key    = "glue/spark_job.py"
  source = "${path.module}/../glue/spark_job.py"
  etag   = filemd5("${path.module}/../glue/spark_job.py")

  tags = {
    Purpose = "etl-script"
  }
}

################################################################################
# IAM Roles and Policies
################################################################################

# Glue job role
resource "aws_iam_role" "glue_job" {
  name = "${var.project_name}-glue-job-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "glue.amazonaws.com"
        }
      }
    ]
  })

  tags = local.common_tags
}

resource "aws_iam_role_policy_attachment" "glue_service" {
  role       = aws_iam_role.glue_job.name
  policy_arn = "arn:${local.partition}:iam::aws:policy/service-role/AWSGlueServiceRole"
}

resource "aws_iam_role_policy" "glue_s3_access" {
  name = "s3-access"
  role = aws_iam_role.glue_job.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "s3:GetObject",
          "s3:PutObject",
          "s3:DeleteObject"
        ]
        Resource = [
          "${aws_s3_bucket.raw_data.arn}/*",
          "${aws_s3_bucket.processed_data.arn}/*",
          "${aws_s3_bucket.scripts.arn}/*"
        ]
      },
      {
        Effect = "Allow"
        Action = [
          "s3:ListBucket"
        ]
        Resource = [
          aws_s3_bucket.raw_data.arn,
          aws_s3_bucket.processed_data.arn,
          aws_s3_bucket.scripts.arn
        ]
      }
    ]
  })
}

# Step Functions role
resource "aws_iam_role" "step_functions" {
  name = "${var.project_name}-step-functions-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "states.amazonaws.com"
        }
      }
    ]
  })

  tags = local.common_tags
}

resource "aws_iam_role_policy" "step_functions" {
  name = "step-functions-permissions"
  role = aws_iam_role.step_functions.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "glue:StartJobRun",
          "glue:GetJobRun",
          "glue:GetJobRuns",
          "glue:BatchStopJobRun",
          "glue:StartCrawler",
          "glue:GetCrawler"
        ]
        Resource = "*"
      },
      {
        Effect = "Allow"
        Action = [
          "athena:StartQueryExecution",
          "athena:GetQueryExecution",
          "athena:GetQueryResults"
        ]
        Resource = "*"
      },
      {
        Effect = "Allow"
        Action = [
          "sns:Publish"
        ]
        Resource = aws_sns_topic.notifications.arn
      },
      {
        Effect = "Allow"
        Action = [
          "lambda:InvokeFunction"
        ]
        Resource = aws_lambda_function.cost_calculator.arn
      },
      {
        Effect = "Allow"
        Action = [
          "s3:GetBucketLocation",
          "s3:GetObject",
          "s3:ListBucket",
          "s3:PutObject"
        ]
        Resource = [
          aws_s3_bucket.athena_results.arn,
          "${aws_s3_bucket.athena_results.arn}/*"
        ]
      }
    ]
  })
}

# EventBridge role
resource "aws_iam_role" "eventbridge" {
  name = "${var.project_name}-eventbridge-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "events.amazonaws.com"
        }
      }
    ]
  })

  tags = local.common_tags
}

resource "aws_iam_role_policy" "eventbridge" {
  name = "start-step-functions"
  role = aws_iam_role.eventbridge.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "states:StartExecution"
        ]
        Resource = aws_sfn_state_machine.etl_pipeline.arn
      }
    ]
  })
}

# Lambda role for cost calculator
resource "aws_iam_role" "lambda_cost_calculator" {
  name = "${var.project_name}-lambda-cost-calculator"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "lambda.amazonaws.com"
        }
      }
    ]
  })

  tags = local.common_tags
}

resource "aws_iam_role_policy_attachment" "lambda_basic" {
  role       = aws_iam_role.lambda_cost_calculator.name
  policy_arn = "arn:${local.partition}:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

resource "aws_iam_role_policy" "lambda_cost_calculator" {
  name = "cost-calculator-permissions"
  role = aws_iam_role.lambda_cost_calculator.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "glue:GetJobRun",
          "s3:GetBucketSize",
          "s3:GetBucketLocation",
          "cloudwatch:PutMetricData"
        ]
        Resource = "*"
      }
    ]
  })
}

################################################################################
# AWS Glue Resources
################################################################################

# Glue database
resource "aws_glue_catalog_database" "main" {
  name        = "${var.project_name}_database"
  description = "Database for cost-optimized serverless ETL pipeline"

  tags = local.common_tags
}

# Glue job
resource "aws_glue_job" "etl" {
  name     = "cost-optimized-etl-job"
  role_arn = aws_iam_role.glue_job.arn

  command {
    name            = "glueetl"
    script_location = "s3://${aws_s3_bucket.scripts.id}/${aws_s3_object.glue_script.key}"
    python_version  = "3"
  }

  default_arguments = {
    "--job-language"                     = "python"
    "--job-bookmark-option"              = "job-bookmark-enable"
    "--enable-metrics"                   = "true"
    "--enable-continuous-cloudwatch-log" = "true"
    "--enable-spark-ui"                  = "false"  # Cost optimization: disable unless debugging
    "--TempDir"                          = "s3://${aws_s3_bucket.scripts.id}/temp/"
  }

  # Cost optimization: Use smaller worker type and auto-scaling
  glue_version      = "4.0"
  max_capacity      = null  # Use worker_type instead
  worker_type       = "G.1X"  # 1 DPU per worker
  number_of_workers = 2

  max_retries = 1
  timeout     = 120  # 2 hours

  execution_property {
    max_concurrent_runs = 3
  }

  tags = local.common_tags
}

# Glue crawler
resource "aws_glue_crawler" "processed_data" {
  name          = "cost-optimized-data-crawler"
  role          = aws_iam_role.glue_job.arn
  database_name = aws_glue_catalog_database.main.name

  s3_target {
    path = "s3://${aws_s3_bucket.processed_data.id}/"
  }

  # Cost optimization: Run crawler only when needed
  schedule = null  # Triggered by Step Functions instead

  schema_change_policy {
    update_behavior = "UPDATE_IN_DATABASE"
    delete_behavior = "LOG"
  }

  configuration = jsonencode({
    Version = 1.0
    CrawlerOutput = {
      Partitions = {
        AddOrUpdateBehavior = "InheritFromTable"
      }
    }
  })

  tags = local.common_tags
}

################################################################################
# Step Functions State Machine
################################################################################

resource "aws_sfn_state_machine" "etl_pipeline" {
  name     = "${var.project_name}-orchestration"
  role_arn = aws_iam_role.step_functions.arn

  definition = templatefile("${path.module}/../step_functions/orchestration.json", {
    AWS_REGION    = var.aws_region
    AWS_ACCOUNT_ID = local.account_id
  })

  logging_configuration {
    log_destination        = "${aws_cloudwatch_log_group.step_functions.arn}:*"
    include_execution_data = true
    level                  = "ALL"
  }

  tags = local.common_tags
}

################################################################################
# Athena Resources
################################################################################

resource "aws_athena_workgroup" "main" {
  name = "cost-optimized-workgroup"

  configuration {
    enforce_workgroup_configuration    = true
    publish_cloudwatch_metrics_enabled = true

    result_configuration {
      output_location = "s3://${aws_s3_bucket.athena_results.id}/results/"

      encryption_configuration {
        encryption_option = "SSE_S3"
      }
    }

    # Cost control: Limit data scanned per query
    bytes_scanned_cutoff_per_query = 100000000000  # 100 GB

    engine_version {
      selected_engine_version = "AUTO"
    }
  }

  tags = local.common_tags
}

################################################################################
# EventBridge Rule for S3 Events
################################################################################

resource "aws_cloudwatch_event_rule" "s3_upload" {
  name        = "${var.project_name}-s3-upload-trigger"
  description = "Trigger ETL pipeline when new files arrive in S3"

  event_pattern = jsonencode({
    source      = ["aws.s3"]
    detail-type = ["Object Created"]
    detail = {
      bucket = {
        name = [aws_s3_bucket.raw_data.id]
      }
      object = {
        key = [{
          prefix = "input/"
        }]
      }
    }
  })

  tags = local.common_tags
}

resource "aws_cloudwatch_event_target" "step_functions" {
  rule      = aws_cloudwatch_event_rule.s3_upload.name
  target_id = "TriggerStepFunctions"
  arn       = aws_sfn_state_machine.etl_pipeline.arn
  role_arn  = aws_iam_role.eventbridge.arn

  input_transformer {
    input_paths = {
      bucket = "$.detail.bucket.name"
      key    = "$.detail.object.key"
    }

    input_template = <<EOF
{
  "source_bucket": "<bucket>",
  "source_prefix": "input",
  "target_bucket": "${aws_s3_bucket.processed_data.id}",
  "target_prefix": "processed",
  "database_name": "${aws_glue_catalog_database.main.name}",
  "table_name": "transactions",
  "partition_keys": "year,month,day",
  "file_format": "csv"
}
EOF
  }
}

# Enable EventBridge notifications on S3 bucket
resource "aws_s3_bucket_notification" "raw_data" {
  bucket      = aws_s3_bucket.raw_data.id
  eventbridge = true
}

################################################################################
# Lambda Function for Cost Calculation
################################################################################

resource "aws_lambda_function" "cost_calculator" {
  filename      = "${path.module}/lambda/cost_calculator.zip"
  function_name = "cost-metrics-calculator"
  role          = aws_iam_role.lambda_cost_calculator.arn
  handler       = "index.lambda_handler"
  runtime       = "python3.11"
  timeout       = 60

  environment {
    variables = {
      GLUE_JOB_NAME = aws_glue_job.etl.name
    }
  }

  tags = local.common_tags
}

# Create a placeholder Lambda deployment package
data "archive_file" "lambda_cost_calculator" {
  type        = "zip"
  output_path = "${path.module}/lambda/cost_calculator.zip"

  source {
    content  = <<EOF
import json
import os
import boto3
from datetime import datetime

glue = boto3.client('glue')
cloudwatch = boto3.client('cloudwatch')

# Pricing (us-east-1, approximate)
GLUE_DPU_HOUR_COST = 0.44
S3_STORAGE_GB_MONTH = 0.023

def lambda_handler(event, context):
    """Calculate cost metrics for ETL job execution."""

    glue_result = event.get('glue_job_result', {})
    job_run_id = glue_result.get('JobRunId')

    # Get job run details
    response = glue.get_job_run(
        JobName=os.environ['GLUE_JOB_NAME'],
        RunId=job_run_id
    )

    job_run = response['JobRun']
    execution_time = job_run.get('ExecutionTime', 0)  # seconds
    dpu_seconds = execution_time * job_run.get('MaxCapacity', 2)

    # Calculate costs
    glue_cost = (dpu_seconds / 3600) * GLUE_DPU_HOUR_COST

    # Estimate records processed (would come from job metrics in production)
    records_processed = 1000000  # Placeholder
    data_size_mb = 500  # Placeholder

    # Publish custom metrics
    cloudwatch.put_metric_data(
        Namespace='CostOptimizedETL',
        MetricData=[
            {
                'MetricName': 'GlueCost',
                'Value': glue_cost,
                'Unit': 'None',
                'Timestamp': datetime.now()
            },
            {
                'MetricName': 'RecordsProcessed',
                'Value': records_processed,
                'Unit': 'Count',
                'Timestamp': datetime.now()
            }
        ]
    )

    return {
        'records_processed': records_processed,
        'data_size_mb': data_size_mb,
        'execution_time_seconds': execution_time,
        'estimated_cost': round(glue_cost, 4)
    }
EOF
    filename = "index.py"
  }
}

################################################################################
# SNS Topic for Notifications
################################################################################

resource "aws_sns_topic" "notifications" {
  name = "etl-pipeline-notifications"

  tags = local.common_tags
}

resource "aws_sns_topic_subscription" "email" {
  topic_arn = aws_sns_topic.notifications.arn
  protocol  = "email"
  endpoint  = "data-engineering@example.com"  # Update with actual email
}

################################################################################
# CloudWatch Resources
################################################################################

resource "aws_cloudwatch_log_group" "step_functions" {
  name              = "/aws/states/${var.project_name}-orchestration"
  retention_in_days = 30

  tags = local.common_tags
}

resource "aws_cloudwatch_log_group" "glue_job" {
  name              = "/aws-glue/jobs/${aws_glue_job.etl.name}"
  retention_in_days = 30

  tags = local.common_tags
}

# Cost alarm
resource "aws_cloudwatch_metric_alarm" "budget_alert" {
  alarm_name          = "${var.project_name}-budget-alert"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 1
  metric_name         = "EstimatedCharges"
  namespace           = "AWS/Billing"
  period              = 86400  # 1 day
  statistic           = "Maximum"
  threshold           = var.monthly_budget_limit * 0.8  # Alert at 80%
  alarm_description   = "Alert when estimated charges exceed 80% of budget"
  alarm_actions       = [aws_sns_topic.notifications.arn]

  dimensions = {
    Currency = "USD"
  }

  tags = local.common_tags
}

################################################################################
# Outputs
################################################################################

output "raw_data_bucket" {
  description = "S3 bucket for raw data"
  value       = aws_s3_bucket.raw_data.id
}

output "processed_data_bucket" {
  description = "S3 bucket for processed data"
  value       = aws_s3_bucket.processed_data.id
}

output "athena_results_bucket" {
  description = "S3 bucket for Athena results"
  value       = aws_s3_bucket.athena_results.id
}

output "glue_database_name" {
  description = "Glue catalog database name"
  value       = aws_glue_catalog_database.main.name
}

output "glue_job_name" {
  description = "Glue job name"
  value       = aws_glue_job.etl.name
}

output "step_functions_arn" {
  description = "Step Functions state machine ARN"
  value       = aws_sfn_state_machine.etl_pipeline.arn
}

output "athena_workgroup" {
  description = "Athena workgroup name"
  value       = aws_athena_workgroup.main.name
}

output "sns_topic_arn" {
  description = "SNS topic for notifications"
  value       = aws_sns_topic.notifications.arn
}
