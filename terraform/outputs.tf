output "ec2_instance_id" {
  description = "ID of the EC2 instance running Greengrass Core"
  value       = module.ec2.instance_id
}

output "ec2_public_ip" {
  description = "Public IP of the EC2 instance"
  value       = module.ec2.public_ip
}

output "artifacts_bucket" {
  description = "S3 bucket for component artifacts"
  value       = module.s3.artifacts_bucket_name
}

output "greengrass_group_id" {
  description = "Greengrass group ID"
  value       = module.iot.greengrass_group_id
}

output "iot_thing_name" {
  description = "IoT Thing name for the Greengrass core device"
  value       = module.iot.thing_name
}