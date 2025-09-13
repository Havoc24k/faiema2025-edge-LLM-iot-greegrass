# IoT Thing for Greengrass Core Device
resource "aws_iot_thing" "greengrass_core" {
  name = "${var.project_name}-${var.environment}-core"
  
  attributes = {
    Type = "GreengrassCore"
  }
}

# IoT Policy for Greengrass Core
resource "aws_iot_policy" "greengrass_core" {
  name = "${var.project_name}-${var.environment}-core-policy"

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "iot:Connect",
          "iot:Subscribe",
          "iot:Publish",
          "iot:Receive"
        ]
        Resource = "*"
      },
      {
        Effect = "Allow"
        Action = [
          "greengrass:Discover"
        ]
        Resource = "*"
      }
    ]
  })
}

# IAM Role for Greengrass Token Exchange
resource "aws_iam_role" "greengrass_token_exchange" {
  name = "${var.project_name}-${var.environment}-greengrass-ter"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Principal = {
          Service = "credentials.iot.amazonaws.com"
        }
        Action = "sts:AssumeRole"
      }
    ]
  })

  tags = var.common_tags
}

# IAM Policy for Token Exchange Role
resource "aws_iam_role_policy" "greengrass_token_exchange" {
  name = "greengrass-token-exchange-policy"
  role = aws_iam_role.greengrass_token_exchange.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "s3:GetObject",
          "s3:PutObject"
        ]
        Resource = "${var.artifacts_bucket}/*"
      },
      {
        Effect = "Allow"
        Action = [
          "s3:ListBucket"
        ]
        Resource = var.artifacts_bucket
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

# Greengrass V2 Core Device
resource "aws_iot_thing_group" "greengrass" {
  name = "${var.project_name}-${var.environment}-group"
  
  tags = var.common_tags
}