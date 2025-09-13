output "artifacts_bucket_name" {
  description = "Name of the S3 bucket for artifacts"
  value       = aws_s3_bucket.artifacts.id
}

output "artifacts_bucket_arn" {
  description = "ARN of the S3 bucket for artifacts"
  value       = aws_s3_bucket.artifacts.arn
}