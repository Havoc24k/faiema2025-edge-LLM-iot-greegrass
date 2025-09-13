locals {
  common_tags = {
    Project     = var.project_name
    Environment = var.environment
    ManagedBy   = "Terraform"
  }
  
  # Official AWS Greengrass Labs component versions
  greengrass_components = {
    influxdb_grafana_version = "2.0.7"
    influxdb_publisher_version = "1.0.0"
  }
}

# S3 bucket for Greengrass component artifacts
module "s3" {
  source = "./modules/s3"
  
  project_name = var.project_name
  environment  = var.environment
  common_tags  = local.common_tags
}

# IoT Core and Greengrass configuration
module "iot" {
  source = "./modules/iot"
  
  project_name      = var.project_name
  environment       = var.environment
  artifacts_bucket  = module.s3.artifacts_bucket_name
  common_tags       = local.common_tags
}

# EC2 instance for Greengrass Core Device
module "ec2" {
  source = "./modules/ec2"
  
  project_name          = var.project_name
  environment           = var.environment
  instance_type         = var.ec2_instance_type
  greengrass_token_arn  = module.iot.greengrass_token_exchange_role_arn
  artifacts_bucket_arn  = module.s3.artifacts_bucket_arn
  common_tags           = local.common_tags
}