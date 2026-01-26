# Deploying Hive on AWS using ECS/Fargate (Terraform)

This document describes a recommended approach to self-host Hive on AWS using
ECS/Fargate and Terraform. The goal is to provide a production-ready but minimal
deployment path that can be easily extended.

---

## Architecture Overview

- AWS VPC (reusing the existing modular VPC setup)
- ECS Cluster (Fargate)
- Application Load Balancer (HTTP + WebSocket support)
- IAM Task Role (least privilege)
- AWS Secrets Manager for sensitive config
- CloudWatch Logs for observability

Hive runs as a containerized service behind an ALB. WebSocket connections are
handled natively by ALB.

---

## Prerequisites

- AWS account
- Terraform >= 1.5
- Docker
- An existing VPC provisioned via Terraform

---

## High-Level Deployment Steps

1. Provision networking (VPC, subnets, routing)
2. Create an ECS cluster
3. Define a Task Definition for Hive
4. Create an ECS Service (Fargate)
5. Attach an Application Load Balancer
6. Configure logging and secrets
7. Access Hive via the ALB DNS name

---

## Configuration Notes

### Container
- Hive runs as a single container per task
- CPU / memory are configurable via Terraform variables
- Environment variables and secrets are injected at runtime

### Load Balancer
- ALB supports WebSockets by default
- Health checks should target a lightweight HTTP endpoint (e.g. `/health`)

### Scaling
- Initial deployment targets a single replica
- ECS Service Auto Scaling can be added later

---

## Observability

- Application logs are sent to CloudWatch Logs
- Future work may include OpenTelemetry integration

---

## Status

This document defines the intended deployment model.
The Terraform implementation will be provided in a follow-up PR.
