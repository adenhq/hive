variable "name_prefix" {
  description = "Prefix used for ECS resources."
  type        = string
}

variable "aws_region" {
  description = "AWS region for logging configuration."
  type        = string
}

variable "vpc_id" {
  description = "VPC ID for the ECS service security group."
  type        = string
}

variable "private_subnet_ids" {
  description = "Private subnet IDs for ECS tasks."
  type        = list(string)
}

variable "container_port" {
  description = "Container port exposed by the task."
  type        = number
}

variable "image" {
  description = "Container image for Hive."
  type        = string
}

variable "cpu" {
  description = "CPU units for the task definition."
  type        = number
}

variable "memory" {
  description = "Memory (MiB) for the task definition."
  type        = number
}

variable "desired_count" {
  description = "Number of desired ECS tasks."
  type        = number
}

variable "env_vars" {
  description = "Environment variables for the container."
  type        = map(string)
  default     = {}
}

variable "secrets" {
  description = "Secrets Manager ARNs exposed as container secrets."
  type = list(object({
    name = string
    arn  = string
  }))
  default = []
}

variable "task_execution_role_arn" {
  description = "IAM task execution role ARN."
  type        = string
}

variable "task_role_arn" {
  description = "IAM task role ARN."
  type        = string
}

variable "log_group_name" {
  description = "CloudWatch log group name."
  type        = string
}

variable "target_group_arn" {
  description = "Target group ARN for the service."
  type        = string
}

variable "alb_sg_id" {
  description = "ALB security group ID to allow inbound traffic."
  type        = string
}

variable "listener_arn" {
  description = "ALB listener ARN used to enforce creation order before ECS service attaches the target group."
  type        = string
}
