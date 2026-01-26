# AWS Terraform Module Structure for Hive

This document proposes a modular Terraform layout for deploying Hive on AWS.
The structure builds on the existing VPC module and keeps components loosely
coupled for future cloud expansion.

---

## Directory Layout

infra/terraform/aws/
  modules/
    network/        # Existing VPC module
    ecs/            # ECS cluster, task definition, service
    alb/            # Application Load Balancer
    iam/            # Task roles and policies
    observability/  # CloudWatch logs, metrics (optional)
  envs/
    dev/
      main.tf
      variables.tf
      outputs.tf
	  
---

## Module Responsibilities

### network
Responsible for all networking primitives required by the deployment.

VPC
Public / private subnets
Routing and NAT

### ecs
Defines the compute layer where Hive runs.

ECS Cluster
Task Definition
ECS Service (Fargate)

### alb
Manages ingress traffic to the Hive service.

Application Load Balancer
Listener and target group configuration
Health checks
Native WebSocket support

### iam
Provides identity and access management with least-privilege principles.

ECS task execution role
ECS task role
Fine-grained policies for logs and secrets access


### observability
Handles logging and basic observability concerns.

CloudWatch log groups
Log retention configuration

### Design Principles

Environment-agnostic modules
Minimal assumptions about runtime
Explicit inputs and outputs
Cloud-specific logic isolated inside modules

### Next Steps

Implement ECS, ALB, and IAM modules
Provide example dev environment
Add optional autoscaling and HTTPS support