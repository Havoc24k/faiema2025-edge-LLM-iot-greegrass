output "thing_name" {
  description = "IoT Thing name"
  value       = aws_iot_thing.greengrass_core.name
}

output "thing_arn" {
  description = "IoT Thing ARN"
  value       = aws_iot_thing.greengrass_core.arn
}

output "greengrass_group_id" {
  description = "Greengrass thing group ID"
  value       = aws_iot_thing_group.greengrass.id
}

output "greengrass_token_exchange_role_arn" {
  description = "ARN of the Greengrass token exchange role"
  value       = aws_iam_role.greengrass_token_exchange.arn
}

output "iot_policy_name" {
  description = "Name of the IoT policy"
  value       = aws_iot_policy.greengrass_core.name
}