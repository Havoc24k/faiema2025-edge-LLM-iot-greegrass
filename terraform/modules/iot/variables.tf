variable "project_name" {
  description = "Project name for resource naming"
  type        = string
}

variable "environment" {
  description = "Environment name"
  type        = string
}

variable "artifacts_bucket" {
  description = "S3 bucket ARN for component artifacts"
  type        = string
}

variable "common_tags" {
  description = "Common tags for all resources"
  type        = map(string)
}