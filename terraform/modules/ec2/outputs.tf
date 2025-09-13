output "instance_id" {
  description = "ID of the EC2 instance"
  value       = aws_instance.greengrass_core.id
}

output "public_ip" {
  description = "Public IP address of the EC2 instance"
  value       = aws_instance.greengrass_core.public_ip
}

output "private_ip" {
  description = "Private IP address of the EC2 instance"
  value       = aws_instance.greengrass_core.private_ip
}

output "security_group_id" {
  description = "ID of the security group"
  value       = aws_security_group.greengrass_core.id
}