variable "name_prefix" {
  description = "Prefix used for IAM role names."
  type        = string
}

variable "secrets_manager_arns" {
  description = "List of Secrets Manager ARNs the task can read."
  type        = list(string)
  default     = []
}