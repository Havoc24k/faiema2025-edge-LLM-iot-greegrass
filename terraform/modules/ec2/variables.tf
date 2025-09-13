variable "project_name" {
  description = "Project name for resource naming"
  type        = string
}

variable "environment" {
  description = "Environment name"
  type        = string
}

variable "instance_type" {
  description = "EC2 instance type"
  type        = string
}

variable "greengrass_token_arn" {
  description = "ARN of the Greengrass token exchange role"
  type        = string
}

variable "artifacts_bucket_arn" {
  description = "ARN of the S3 bucket for artifacts"
  type        = string
}

variable "common_tags" {
  description = "Common tags for all resources"
  type        = map(string)
}