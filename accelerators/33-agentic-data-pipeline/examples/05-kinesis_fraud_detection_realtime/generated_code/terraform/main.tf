terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

provider "aws" {
  region = "us-east-1"
}

# Kinesis Stream
resource "aws_kinesis_stream" "transaction_stream" {
  name             = "transaction-stream"
  shard_count      = 2
  retention_period = 24

  shard_level_metrics = [
    "IncomingBytes",
    "IncomingRecords",
    "OutgoingBytes",
    "OutgoingRecords",
  ]

  tags = {
    Environment = "production"
    Purpose     = "fraud-detection"
  }
}

# DynamoDB Tables
resource "aws_dynamodb_table" "user_profiles" {
  name           = "user-profiles"
  billing_mode   = "PAY_PER_REQUEST"
  hash_key       = "user_id"

  attribute {
    name = "user_id"
    type = "S"
  }

  tags = {
    Environment = "production"
  }
}

resource "aws_dynamodb_table" "fraud_alerts" {
  name           = "fraud-alerts"
  billing_mode   = "PAY_PER_REQUEST"
  hash_key       = "alert_id"

  attribute {
    name = "alert_id"
    type = "S"
  }

  attribute {
    name = "user_id"
    type = "S"
  }

  attribute {
    name = "timestamp"
    type = "S"
  }

  global_secondary_index {
    name            = "UserIdIndex"
    hash_key        = "user_id"
    range_key       = "timestamp"
    projection_type = "ALL"
  }

  tags = {
    Environment = "production"
  }
}

resource "aws_dynamodb_table" "merchant_blocklist" {
  name           = "merchant-blocklist"
  billing_mode   = "PAY_PER_REQUEST"
  hash_key       = "merchant_id"

  attribute {
    name = "merchant_id"
    type = "S"
  }

  tags = {
    Environment = "production"
  }
}

# SNS Topic
resource "aws_sns_topic" "fraud_alerts" {
  name = "fraud-alerts"

  tags = {
    Environment = "production"
  }
}

resource "aws_sns_topic_subscription" "fraud_email" {
  topic_arn = aws_sns_topic.fraud_alerts.arn
  protocol  = "email"
  endpoint  = "fraud-team@company.com"
}

# IAM Role for Lambda
resource "aws_iam_role" "lambda_fraud_detector" {
  name = "lambda-fraud-detector-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action = "sts:AssumeRole"
      Effect = "Allow"
      Principal = {
        Service = "lambda.amazonaws.com"
      }
    }]
  })
}

resource "aws_iam_role_policy" "lambda_fraud_detector_policy" {
  name = "lambda-fraud-detector-policy"
  role = aws_iam_role.lambda_fraud_detector.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "kinesis:GetRecords",
          "kinesis:GetShardIterator",
          "kinesis:DescribeStream",
          "kinesis:ListStreams"
        ]
        Resource = aws_kinesis_stream.transaction_stream.arn
      },
      {
        Effect = "Allow"
        Action = [
          "dynamodb:GetItem",
          "dynamodb:PutItem",
          "dynamodb:Query"
        ]
        Resource = [
          aws_dynamodb_table.user_profiles.arn,
          aws_dynamodb_table.fraud_alerts.arn,
          aws_dynamodb_table.merchant_blocklist.arn
        ]
      },
      {
        Effect = "Allow"
        Action = [
          "sns:Publish"
        ]
        Resource = aws_sns_topic.fraud_alerts.arn
      },
      {
        Effect = "Allow"
        Action = [
          "cloudwatch:PutMetricData"
        ]
        Resource = "*"
      },
      {
        Effect = "Allow"
        Action = [
          "logs:CreateLogGroup",
          "logs:CreateLogStream",
          "logs:PutLogEvents"
        ]
        Resource = "arn:aws:logs:*:*:*"
      }
    ]
  })
}

# Lambda Function
resource "aws_lambda_function" "fraud_detector" {
  filename      = "fraud_detector.zip"
  function_name = "fraud-detection-processor"
  role          = aws_iam_role.lambda_fraud_detector.arn
  handler       = "fraud_detector.lambda_handler"
  runtime       = "python3.11"
  memory_size   = 512
  timeout       = 60

  reserved_concurrent_executions = 10

  environment {
    variables = {
      USER_PROFILES_TABLE      = aws_dynamodb_table.user_profiles.name
      FRAUD_ALERTS_TABLE       = aws_dynamodb_table.fraud_alerts.name
      MERCHANT_BLOCKLIST_TABLE = aws_dynamodb_table.merchant_blocklist.name
      FRAUD_ALERTS_TOPIC       = aws_sns_topic.fraud_alerts.arn
    }
  }

  tags = {
    Environment = "production"
  }
}

# Event Source Mapping
resource "aws_lambda_event_source_mapping" "kinesis_lambda" {
  event_source_arn  = aws_kinesis_stream.transaction_stream.arn
  function_name     = aws_lambda_function.fraud_detector.arn
  starting_position = "LATEST"
  batch_size        = 100
}

# CloudWatch Log Group
resource "aws_cloudwatch_log_group" "lambda_logs" {
  name              = "/aws/lambda/fraud-detection-processor"
  retention_in_days = 30
}

# Outputs
output "kinesis_stream_name" {
  value = aws_kinesis_stream.transaction_stream.name
}

output "lambda_function_name" {
  value = aws_lambda_function.fraud_detector.function_name
}

output "sns_topic_arn" {
  value = aws_sns_topic.fraud_alerts.arn
}
