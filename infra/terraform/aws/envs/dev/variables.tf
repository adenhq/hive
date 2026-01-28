variable "aws_region" {
  description = "AWS region to deploy into."
  type        = string
}

variable "name_prefix" {
  description = "Prefix for AWS resources."
  type        = string
}

variable "vpc_id" {
  description = "Existing VPC ID."
  type        = string
}

variable "public_subnet_ids" {
  description = "Public subnet IDs for the ALB."
  type        = list(string)
}

variable "private_subnet_ids" {
  description = "Private subnet IDs for ECS tasks."
  type        = list(string)
}

variable "image" {
  description = "Container image for Hive."
  type        = string
}

variable "container_port" {
  description = "Container port exposed by Hive."
  type        = number
  default     = 4000
}

variable "health_check_path" {
  description = "ALB health check path."
  type        = string
  default     = "/health"
}

variable "cpu" {
  description = "CPU units for the ECS task (e.g. 256, 512)."
  type        = number
  default     = 512
}

variable "memory" {
  description = "Memory (MiB) for the ECS task (e.g. 1024)."
  type        = number
  default     = 1024
}

variable "desired_count" {
  description = "Desired number of tasks."
  type        = number
  default     = 1
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

variable "log_retention_days" {
  description = "CloudWatch log retention in days."
  type        = number
  default     = 14
}