variable "project_name" {
  description = "The name of the project"
  type        = string
  default     = "aden-hive"
}

variable "vpc_cidr" {
  description = "The IP range for the VPC"
  type        = string
  default     = "10.0.0.0/16"
}

variable "region" {
  description = "The AWS region to deploy in"
  type        = string
  default     = "us-east-1"
}
