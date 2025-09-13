# Data source for latest Amazon Linux 2 AMI
data "aws_ami" "amazon_linux_2" {
  most_recent = true
  owners      = ["amazon"]

  filter {
    name   = "name"
    values = ["amzn2-ami-hvm-*-x86_64-gp2"]
  }

  filter {
    name   = "virtualization-type"
    values = ["hvm"]
  }
}

# Security group for Greengrass Core
resource "aws_security_group" "greengrass_core" {
  name        = "${var.project_name}-${var.environment}-greengrass-sg"
  description = "Security group for Greengrass Core EC2 instance"

  ingress {
    description = "SSH"
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  ingress {
    description = "Grafana"
    from_port   = 3000
    to_port     = 3000
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  ingress {
    description = "ChatBot UI"
    from_port   = 8080
    to_port     = 8080
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  egress {
    description = "All outbound"
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = var.common_tags
}

# IAM Role for EC2 instance
resource "aws_iam_role" "greengrass_ec2" {
  name = "${var.project_name}-${var.environment}-greengrass-ec2"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Principal = {
          Service = "ec2.amazonaws.com"
        }
        Action = "sts:AssumeRole"
      }
    ]
  })

  tags = var.common_tags
}

# IAM Policy for EC2 instance
resource "aws_iam_role_policy" "greengrass_ec2" {
  name = "greengrass-ec2-policy"
  role = aws_iam_role.greengrass_ec2.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "greengrass:*",
          "iot:*"
        ]
        Resource = "*"
      },
      {
        Effect = "Allow"
        Action = [
          "s3:GetObject",
          "s3:PutObject"
        ]
        Resource = "${var.artifacts_bucket_arn}/*"
      },
      {
        Effect = "Allow"
        Action = [
          "s3:ListBucket"
        ]
        Resource = var.artifacts_bucket_arn
      },
      {
        Effect = "Allow"
        Action = [
          "sts:AssumeRole"
        ]
        Resource = var.greengrass_token_arn
      }
    ]
  })
}

# Instance profile for EC2
resource "aws_iam_instance_profile" "greengrass_ec2" {
  name = "${var.project_name}-${var.environment}-greengrass-profile"
  role = aws_iam_role.greengrass_ec2.name
}

# EC2 Instance for Greengrass Core
resource "aws_instance" "greengrass_core" {
  ami                    = data.aws_ami.amazon_linux_2.id
  instance_type          = var.instance_type
  vpc_security_group_ids = [aws_security_group.greengrass_core.id]
  iam_instance_profile   = aws_iam_instance_profile.greengrass_ec2.name

  root_block_device {
    volume_size = 30
    volume_type = "gp3"
    encrypted   = true
  }

  user_data = templatefile("${path.module}/user_data.sh", {
    project_name = var.project_name
    environment  = var.environment
  })

  tags = merge(
    var.common_tags,
    {
      Name = "${var.project_name}-${var.environment}-greengrass-core"
    }
  )
}