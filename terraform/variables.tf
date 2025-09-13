variable "aws_region" {
  description = "AWS region for deployment"
  type        = string
  default     = "us-east-1"
}

variable "project_name" {
  description = "Project name for resource naming"
  type        = string
  default     = "edge-llm-greengrass"
}

variable "environment" {
  description = "Environment name"
  type        = string
  default     = "demo"
}

variable "ec2_instance_type" {
  description = "EC2 instance type for Greengrass core"
  type        = string
  default     = "t3.medium"
}

variable "enable_grafana" {
  description = "Enable Grafana component deployment"
  type        = bool
  default     = true
}