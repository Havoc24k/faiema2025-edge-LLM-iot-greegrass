#!/bin/bash
set -e

echo "========================================="
echo "Destroying Edge LLM IoT Greengrass Demo"
echo "========================================="

# Destroy Terraform infrastructure
cd terraform
terraform destroy -auto-approve
cd ..

echo "Infrastructure destroyed successfully"