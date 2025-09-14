terraform {
  required_version = ">= 1.0"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

provider "aws" {
  region = var.aws_region
}

# Variables
variable "aws_region" {
  description = "AWS region for deployment"
  type        = string
  default     = "eu-central-1"
}

variable "project_name" {
  description = "Project name for tagging"
  type        = string
  default     = "edge-llm-greengrass"
}

# Data sources
data "aws_ami" "amazon_linux_2023" {
  most_recent = true
  owners      = ["amazon"]

  filter {
    name   = "name"
    values = ["al2023-ami-*-x86_64"]
  }

  filter {
    name   = "virtualization-type"
    values = ["hvm"]
  }
}

# SSH Key Pair
resource "aws_key_pair" "greengrass_key" {
  key_name   = "${var.project_name}-key"
  public_key = file("~/.ssh/greengrass-key.pub")

  tags = {
    Name    = "${var.project_name}-key"
    Project = var.project_name
  }
}

data "aws_availability_zones" "available" {
  state = "available"
}

# VPC
resource "aws_vpc" "greengrass_vpc" {
  cidr_block           = "10.0.0.0/16"
  enable_dns_hostnames = true
  enable_dns_support   = true

  tags = {
    Name    = "${var.project_name}-vpc"
    Project = var.project_name
  }
}

# Internet Gateway
resource "aws_internet_gateway" "greengrass_igw" {
  vpc_id = aws_vpc.greengrass_vpc.id

  tags = {
    Name    = "${var.project_name}-igw"
    Project = var.project_name
  }
}

# Public Subnet (1 AZ only)
resource "aws_subnet" "public_subnet" {
  vpc_id                  = aws_vpc.greengrass_vpc.id
  cidr_block              = "10.0.1.0/24"
  availability_zone       = data.aws_availability_zones.available.names[0]
  map_public_ip_on_launch = true

  tags = {
    Name    = "${var.project_name}-public-subnet"
    Project = var.project_name
    Type    = "Public"
  }
}

# Route Table for Public Subnet
resource "aws_route_table" "public_rt" {
  vpc_id = aws_vpc.greengrass_vpc.id

  route {
    cidr_block = "0.0.0.0/0"
    gateway_id = aws_internet_gateway.greengrass_igw.id
  }

  tags = {
    Name    = "${var.project_name}-public-rt"
    Project = var.project_name
  }
}

# Route Table Association
resource "aws_route_table_association" "public_rta" {
  subnet_id      = aws_subnet.public_subnet.id
  route_table_id = aws_route_table.public_rt.id
}

# S3 VPC Endpoint
resource "aws_vpc_endpoint" "s3" {
  vpc_id            = aws_vpc.greengrass_vpc.id
  service_name      = "com.amazonaws.${var.aws_region}.s3"
  vpc_endpoint_type = "Gateway"
  route_table_ids   = [aws_route_table.public_rt.id]

  tags = {
    Name    = "${var.project_name}-s3-endpoint"
    Project = var.project_name
  }
}

# Security Group
resource "aws_security_group" "greengrass_sg" {
  name        = "${var.project_name}-sg"
  description = "Security group for Greengrass EC2 instance"
  vpc_id      = aws_vpc.greengrass_vpc.id

  # SSH access
  ingress {
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
    description = "SSH access"
  }

  # Grafana
  ingress {
    from_port   = 3000
    to_port     = 3000
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
    description = "Grafana Dashboard"
  }

  # ChatBot UI
  ingress {
    from_port   = 8080
    to_port     = 8080
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
    description = "ChatBot Web UI"
  }

  # InfluxDB
  ingress {
    from_port   = 8086
    to_port     = 8086
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
    description = "InfluxDB"
  }

  # MQTT for IoT communication
  ingress {
    from_port   = 8883
    to_port     = 8883
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
    description = "MQTT/TLS"
  }

  # Outbound internet access
  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
    description = "Allow all outbound"
  }

  tags = {
    Name    = "${var.project_name}-sg"
    Project = var.project_name
  }
}

# IAM Role for EC2
resource "aws_iam_role" "greengrass_ec2_role" {
  name = "${var.project_name}-ec2-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "ec2.amazonaws.com"
        }
      }
    ]
  })

  tags = {
    Name    = "${var.project_name}-ec2-role"
    Project = var.project_name
  }
}

# IAM Role Policy Attachments
resource "aws_iam_role_policy_attachment" "ec2_ssm" {
  role       = aws_iam_role.greengrass_ec2_role.name
  policy_arn = "arn:aws:iam::aws:policy/AmazonSSMManagedInstanceCore"
}

resource "aws_iam_role_policy_attachment" "ec2_s3_read" {
  role       = aws_iam_role.greengrass_ec2_role.name
  policy_arn = "arn:aws:iam::aws:policy/AmazonS3ReadOnlyAccess"
}

resource "aws_iam_role_policy_attachment" "ec2_iot_full" {
  role       = aws_iam_role.greengrass_ec2_role.name
  policy_arn = "arn:aws:iam::aws:policy/AWSIoTFullAccess"
}

resource "aws_iam_role_policy_attachment" "ec2_iam_full" {
  role       = aws_iam_role.greengrass_ec2_role.name
  policy_arn = "arn:aws:iam::aws:policy/IAMFullAccess"
}

# IAM Policy for IoT Greengrass device provisioning
resource "aws_iam_role_policy" "ec2_iot_policy" {
  name = "${var.project_name}-ec2-iot-policy"
  role = aws_iam_role.greengrass_ec2_role.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "iot:GetPolicy",
          "iot:CreatePolicy",
          "iot:AttachPolicy",
          "iot:DetachPolicy",
          "iot:CreateKeysAndCertificate",
          "iot:AttachPrincipalPolicy",
          "iot:DetachPrincipalPolicy",
          "iot:AttachThingPrincipal",
          "iot:DetachThingPrincipal",
          "iot:CreateThing",
          "iot:UpdateThing",
          "iot:DescribeThing",
          "iot:DescribeEndpoint",
          "iot:DescribeThingGroup",
          "iot:AddThingToThingGroup",
          "iot:RemoveThingFromThingGroup",
          "greengrass:*",
          "sts:GetCallerIdentity"
        ]
        Resource = "*"
      }
    ]
  })
}

# IAM Instance Profile
resource "aws_iam_instance_profile" "greengrass_profile" {
  name = "${var.project_name}-profile"
  role = aws_iam_role.greengrass_ec2_role.name
}

# Elastic IP
resource "aws_eip" "greengrass_eip" {
  domain = "vpc"

  tags = {
    Name    = "${var.project_name}-eip"
    Project = var.project_name
  }
}

# EC2 Instance with GPU support (g4dn.xlarge is the cheapest GPU instance)
resource "aws_instance" "greengrass_device" {
  # g4dn.xlarge: 1 NVIDIA T4 GPU, 4 vCPUs, 16 GB RAM
  instance_type               = "g4dn.xlarge"
  ami                         = data.aws_ami.amazon_linux_2023.id
  iam_instance_profile        = aws_iam_instance_profile.greengrass_profile.name
  subnet_id                   = aws_subnet.public_subnet.id
  vpc_security_group_ids      = [aws_security_group.greengrass_sg.id]
  associate_public_ip_address = true
  key_name                    = aws_key_pair.greengrass_key.key_name

  # Increase root volume for model storage
  root_block_device {
    volume_size = 100
    volume_type = "gp3"
    encrypted   = true
  }

  user_data = base64encode(templatefile("${path.module}/user_data.sh", {
    project_name = var.project_name
    aws_region   = var.aws_region
  }))

  tags = {
    Name    = "${var.project_name}-greengrass-device"
    Project = var.project_name
    Type    = "GreengrassCore"
  }
}

# Associate Elastic IP with EC2 instance
resource "aws_eip_association" "greengrass_eip_assoc" {
  instance_id   = aws_instance.greengrass_device.id
  allocation_id = aws_eip.greengrass_eip.id
}

# S3 Bucket for Component Artifacts
resource "aws_s3_bucket" "component_artifacts" {
  bucket = "${var.project_name}-artifacts-${data.aws_caller_identity.current.account_id}"

  tags = {
    Name    = "${var.project_name}-artifacts"
    Project = var.project_name
  }
}

data "aws_caller_identity" "current" {}

# S3 Bucket Versioning
resource "aws_s3_bucket_versioning" "component_artifacts" {
  bucket = aws_s3_bucket.component_artifacts.id

  versioning_configuration {
    status = "Enabled"
  }
}

# IoT Thing for Greengrass
resource "aws_iot_thing" "greengrass_core" {
  name = "EdgeLLMDemoAWS-v2"

  attributes = {
    type = "GreengrassCore"
  }
}

# IoT Thing Group
resource "aws_iot_thing_group" "greengrass_group" {
  name = "${var.project_name}-group"

  properties {
    description = "Greengrass deployment group for ${var.project_name}"
  }

  tags = {
    Project = var.project_name
  }
}

# IAM Role for Greengrass
resource "aws_iam_role" "greengrass_role" {
  name = "${var.project_name}-greengrass-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Principal = {
          Service = "greengrass.amazonaws.com"
        }
        Action = "sts:AssumeRole"
      }
    ]
  })

  tags = {
    Name    = "${var.project_name}-greengrass-role"
    Project = var.project_name
  }
}

# Greengrass Role Policy
resource "aws_iam_role_policy" "greengrass_policy" {
  name = "${var.project_name}-greengrass-policy"
  role = aws_iam_role.greengrass_role.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "iot:*",
          "greengrass:*",
          "s3:GetObject",
          "s3:ListBucket",
          "logs:CreateLogGroup",
          "logs:CreateLogStream",
          "logs:PutLogEvents",
          "logs:DescribeLogStreams"
        ]
        Resource = "*"
      }
    ]
  })
}

# Token Exchange Role
resource "aws_iam_role" "token_exchange_role" {
  name = "${var.project_name}-TokenExchangeRole"

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

  tags = {
    Name    = "${var.project_name}-token-exchange-role"
    Project = var.project_name
  }
}

# Token Exchange Role Policy
resource "aws_iam_role_policy" "token_exchange_policy" {
  name = "${var.project_name}-token-exchange-policy"
  role = aws_iam_role.token_exchange_role.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "s3:GetObject",
          "s3:ListBucket",
          "s3:PutObject",
          "s3:GetBucketLocation",
          "logs:CreateLogGroup",
          "logs:CreateLogStream",
          "logs:PutLogEvents",
          "ecr:GetAuthorizationToken",
          "ecr:BatchGetImage",
          "ecr:GetDownloadUrlForLayer"
        ]
        Resource = "*"
      }
    ]
  })
}

# IoT Role Alias
resource "aws_iot_role_alias" "greengrass_role_alias" {
  alias    = "${var.project_name}-TokenExchangeRoleAlias"
  role_arn = aws_iam_role.token_exchange_role.arn
}

# Outputs
output "vpc_id" {
  value       = aws_vpc.greengrass_vpc.id
  description = "VPC ID"
}

output "subnet_id" {
  value       = aws_subnet.public_subnet.id
  description = "Public subnet ID"
}

output "ec2_public_ip" {
  value       = aws_eip.greengrass_eip.public_ip
  description = "Public IP address of the Greengrass EC2 instance"
}

output "ec2_instance_id" {
  value       = aws_instance.greengrass_device.id
  description = "EC2 instance ID"
}

output "s3_bucket_name" {
  value       = aws_s3_bucket.component_artifacts.id
  description = "S3 bucket for component artifacts"
}

output "iot_thing_name" {
  value       = aws_iot_thing.greengrass_core.name
  description = "IoT Thing name for Greengrass Core"
}

output "iot_thing_group_arn" {
  value       = aws_iot_thing_group.greengrass_group.arn
  description = "IoT Thing Group ARN for deployments"
}

output "token_exchange_role_alias" {
  value       = aws_iot_role_alias.greengrass_role_alias.alias
  description = "Token Exchange Role Alias for Greengrass"
}