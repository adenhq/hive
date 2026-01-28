variable "name_prefix" {
  description = "Prefix used for log group naming."
  type        = string
}

variable "retention_in_days" {
  description = "CloudWatch log retention in days."
  type        = number
  default     = 14
}