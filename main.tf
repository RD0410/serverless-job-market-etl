terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 4.16"
    }
  }

  required_version = ">= 1.2.0"
}

provider "aws" {
  region = "us-east-1"
}

# 1. S3 Bucket for Raw Data Lake
resource "aws_s3_bucket" "raw_data_lake" {
  bucket = "ralph-job-market-lake-2026"  # Must be globally unique

  tags = {
    Name        = "Job Market Data Lake"
    Environment = "Dev"
    Project     = "Data Engineering Portfolio"
  }
}

# 2. Block Public Access (Security Best Practice)
resource "aws_s3_bucket_public_access_block" "raw_data_lake_block" {
  bucket = aws_s3_bucket.raw_data_lake.id

  block_public_acls       = true
  ignore_public_acls      = true
  block_public_policy     = true
  restrict_public_buckets = true
}

# 3. IAM Role for Lambda
resource "aws_iam_role" "lambda_exec_role" {
  name = "job_market_lambda_role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "lambda.amazonaws.com"
        }
      },
    ]
  })
}

# 4. IAM Policy for S3 PutObject, Logs, and Glue
resource "aws_iam_policy" "lambda_s3_write_policy" {
  name        = "lambda_s3_write_policy"
  description = "Allows Lambda to write to S3, log to CloudWatch, and trigger Glue"

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect   = "Allow"
        Action   = [
          "s3:PutObject",
          "s3:GetObject",
          "s3:ListBucket"
        ]
        Resource = [
          aws_s3_bucket.raw_data_lake.arn,
          "${aws_s3_bucket.raw_data_lake.arn}/*"
        ]
      },
      {
        Effect   = "Allow"
        Action   = [
          "logs:CreateLogGroup",
          "logs:CreateLogStream",
          "logs:PutLogEvents"
        ]
        Resource = "arn:aws:logs:*:*:*"
      },
      {
        Effect   = "Allow"
        Action   = [
          "glue:GetDatabase",
          "glue:GetTable",
          "glue:CreateTable",
          "glue:UpdateTable"
        ]
        Resource = "*"
      }
    ]
  })
}

# 5. Attach the Policy to the Role
resource "aws_iam_role_policy_attachment" "lambda_s3_attach" {
  role       = aws_iam_role.lambda_exec_role.name
  policy_arn = aws_iam_policy.lambda_s3_write_policy.arn
}

# 7. Create an EventBridge Rule (The Schedule)
resource "aws_cloudwatch_event_rule" "daily_job_trigger" {
  name                = "daily_job_market_trigger"
  description         = "Triggers the Job Fetcher Lambda daily"
  schedule_expression = "cron(0 8 * * ? *)" # Runs every day at 8:00 AM UTC
}

# 8. Set the Lambda as the Target for the Rule
resource "aws_cloudwatch_event_target" "trigger_lambda_on_schedule" {
  rule      = aws_cloudwatch_event_rule.daily_job_trigger.name
  target_id = "job_fetcher_lambda"
  arn       = aws_lambda_function.job_fetcher.arn
}

# 9. Give EventBridge Permission to Invoke your Lambda
resource "aws_lambda_permission" "allow_cloudwatch_to_call_lambda" {
  statement_id  = "AllowExecutionFromCloudWatch"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.job_fetcher.function_name
  principal     = "events.amazonaws.com"
  source_arn    = aws_cloudwatch_event_rule.daily_job_trigger.arn

}

# 10. Define the Lambda Layer
resource "aws_lambda_layer_version" "python_requests_layer" {
  filename            = "requests_layer.zip"
  layer_name          = "python_requests_library"
  compatible_runtimes = ["python3.9"]
}

# 11. The SINGLE Lambda Function Resource
resource "aws_lambda_function" "job_fetcher" {
  filename         = "lambda_function.zip"
  function_name    = "job_market_fetcher"
  role             = aws_iam_role.lambda_exec_role.arn
  handler          = "lambda_function.lambda_handler"
  runtime          = "python3.9"

  # This line attaches the requests library we just zipped up
  layers = [aws_lambda_layer_version.python_requests_layer.arn]

  # Ensures Terraform tracks code changes
  source_code_hash = filebase64sha256("lambda_function.zip")

  environment {
    variables = {
      BUCKET_NAME = aws_s3_bucket.raw_data_lake.id
      ADZUNA_APP_ID  = "4631dbc9"  
      ADZUNA_APP_KEY = "96fc960a44f1b5e474b5e52b81951794" 
    }
  }
}


# 12. S3 Bucket for Athena Query Results
resource "aws_s3_bucket" "athena_results" {
  bucket        = "ralph-job-market-query-results-2026" # Must be unique
  force_destroy = true
}

# 13. AWS Glue Database for Athena
resource "aws_glue_catalog_database" "job_market_db" {
  name = "job_market_database"
}


# 1. The Transformer Lambda Resource
resource "aws_lambda_function" "job_transformer" {
  filename      = "transformer_function.zip"
  function_name = "job_market_transformer"
  role          = aws_iam_role.lambda_exec_role.arn # Reusing your existing role
  handler       = "transformer_function.lambda_handler"
  runtime       = "python3.9"
  
  source_code_hash = filebase64sha256("transformer_function.zip")

  environment {
    variables = {
      BUCKET_NAME = aws_s3_bucket.raw_data_lake.id
    }
  }
}

# 2. Grant S3 permission to trigger the Lambda
resource "aws_lambda_permission" "allow_s3_to_call_transformer" {
  statement_id  = "AllowS3Invoke"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.job_transformer.function_name
  principal     = "s3.amazonaws.com"
  source_arn    = aws_s3_bucket.raw_data_lake.arn
}

# 3. The "Tripwire": Trigger on new files in /inbox
resource "aws_s3_bucket_notification" "bucket_notification" {
  bucket = aws_s3_bucket.raw_data_lake.id

  lambda_function {
    lambda_function_arn = aws_lambda_function.job_transformer.arn
    events              = ["s3:ObjectCreated:*"]
    filter_prefix       = "inbox/"
  }

  depends_on = [aws_lambda_permission.allow_s3_to_call_transformer]
}