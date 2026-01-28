# Deploying Hive on AWS using ECS/Fargate (Terraform)

This document describes a production-ready Terraform layout to run Hive on AWS
ECS/Fargate behind an Application Load Balancer, reusing an existing VPC.

---

## Architecture Overview

- Existing AWS VPC (provided as variables)
- Public subnets for the ALB
- Private subnets for ECS tasks
- ECS Cluster (Fargate)
- Application Load Balancer (HTTP + WebSocket support)
- IAM task roles with least privilege
- AWS Secrets Manager integration (optional)
- CloudWatch Logs for observability

Hive runs as a containerized service behind an ALB. WebSocket connections are
handled natively by ALB.

---

## Prerequisites

- AWS account
- Terraform >= 1.5
- Existing VPC + subnets (public + private)
- Container image for Hive (ECR or public registry)

---

## Terraform Layout

```
infra/terraform/aws/
  modules/
    alb/
    ecs/
    iam/
    observability/
  envs/
    dev/
```

---

## Configuration

Key variables to review in `infra/terraform/aws/envs/dev/terraform.tfvars`:

- `vpc_id`, `public_subnet_ids`, `private_subnet_ids`  
  Existing networking (VPC + subnets). ALB uses public subnets; ECS tasks use private subnets.

- `image`  
  Container image for Hive (ECR or public registry).

- `container_port`  
  The port exposed by the Hive container and used by the ALB target group.

- `health_check_path`  
  HTTP path used by the ALB health check (default is a placeholder; confirm the actual Hive endpoint).

- `env_vars`  
  Optional environment variables injected into the task.

- `secrets`  
  Optional Secrets Manager injection as ECS container secrets:
  `[{ name = "KEY", arn = "arn:aws:secretsmanager:..." }]`

---

## Networking & Security Model

- **ALB security group**: allows inbound HTTP (80) from `0.0.0.0/0`.
- **ECS task security group**: allows inbound traffic **only** on `container_port` and **only** from the ALB security group.
- **ECS tasks** run in **private subnets** (`assign_public_ip = false`).
- **ALB** runs in **public subnets**.

This setup keeps the service private while exposing only the ALB publicly.

---

## Observability (Logs)

- A CloudWatch Log Group is created with configurable retention (`log_retention_days`).
- ECS tasks are configured to send container logs to CloudWatch using the `awslogs` driver.

To view logs:

- AWS Console → CloudWatch Logs → Log groups → `/ecs/<name_prefix>`
- Or via CLI (optional): `aws logs tail ...`

---

## Secrets (Optional)

If you use AWS Secrets Manager, provide `secrets` in `terraform.tfvars`:

secrets = [
{ name = "OPENAI_API_KEY", arn = "arn:aws:secretsmanager:REGION:ACCOUNT:secret:mysecret" }
]

---

## Verification

After terraform apply, retrieve the URL:

```bash
terraform output alb_url
```

Basic checks:

Open alb_url in a browser and confirm the service responds.
Confirm target health: AWS Console → EC2 → Target Groups → Targets should be healthy.
Confirm ECS service is stable: ECS → Cluster → Service → Tasks running.

---

## Troubleshooting

### Targets are unhealthy

Verify container_port matches the actual port Hive listens on.
Verify health_check_path exists and returns 200-399.
Check CloudWatch logs for the task to confirm Hive started correctly.

### ECS service keeps restarting

Inspect task logs in CloudWatch.
Confirm the container image is valid and the entrypoint runs Hive successfully.

### No response from the ALB

Confirm ALB listener is on port 80.
Confirm security groups allow ALB → ECS on container_port.
Confirm tasks are running in the expected subnets.

---

## Deployment Steps (Dev)

1. Copy and edit the example variables file:

```bash
cd infra/terraform/aws/envs/dev
cp terraform.tfvars.example terraform.tfvars
```

2. Update values in `terraform.tfvars`:

- `vpc_id`, `public_subnet_ids`, `private_subnet_ids`
- `image` (container image)
- `container_port` and `health_check_path`
- `env_vars` and `secrets` (optional)

3. Initialize Terraform:

```bash
terraform init
```

4. Validate and plan:

```bash
terraform fmt
terraform validate
terraform plan
```

5. Apply:

```bash
terraform apply
```

6. Get the ALB URL:

```bash
terraform output alb_url
```

---

## Notes

- ALB listens on port 80 and forwards to the ECS target group.
- ECS tasks run in private subnets; ALB runs in public subnets.
- ECS tasks only allow inbound traffic from the ALB security group.
- The ECS task execution role includes `AmazonECSTaskExecutionRolePolicy`.
- Optional Secrets Manager access is controlled via `secrets` ARNs.
- Log retention defaults to 14 days (configurable).
- ALB supports WebSockets by default.
- The initial setup uses desired_count (default 1) to keep the deployment minimal. For production, increase desired_count and consider adding autoscaling.
- You must provide real VPC/subnet IDs from your AWS account.
- Defaults are placeholders, confirm the actual Hive port/endpoint.

---

## Status

Terraform implementation is available under `infra/terraform/aws/`.
