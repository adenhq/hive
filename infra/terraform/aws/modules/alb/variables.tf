variable "name_prefix" {
  description = "Prefix used for ALB resources."
  type        = string
}

variable "vpc_id" {
  description = "VPC ID for the ALB and target group."
  type        = string
}

variable "public_subnet_ids" {
  description = "Public subnet IDs for the ALB."
  type        = list(string)
}

variable "container_port" {
  description = "Container port the target group should route to."
  type        = number
}

variable "health_check_path" {
  description = "Health check path for the target group."
  type        = string
  default     = "/health"
}